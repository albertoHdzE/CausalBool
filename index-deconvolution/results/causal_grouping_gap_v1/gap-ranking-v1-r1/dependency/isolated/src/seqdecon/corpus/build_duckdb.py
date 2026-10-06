"""Phase 0: normalize the pinned `oeisdata` mirror into DuckDB.

Produces three tables:

  corpus_meta   one row per provenance key (pinned oeisdata SHA, commit date, counts)
  sequences     one row per A-number, with the singleton fields lifted out
  fields        one row per `%` line in the corpus — lossless long form, all codes

`fields` is the substrate the later phases depend on (%F formulas, %C comments,
%Y cross-references, %p/%t/%o programs, %H links, %D references, %K keywords).
"""

from __future__ import annotations

import json
import multiprocessing as mp
import os
import subprocess
import time
from pathlib import Path

import duckdb
import pyarrow as pa
import pyarrow.parquet as pq

from seqdecon.corpus.oeis_parse import FIELD_CODES, SeqRecord, iter_seq_files, parse_file

PARSER_VERSION = "0.1.0"

_SEQ_SCHEMA = pa.schema(
    [
        ("seq_id", pa.int32()),
        ("a_number", pa.string()),
        ("name", pa.string()),
        ("offset", pa.string()),
        ("keywords", pa.list_(pa.string())),
        ("author", pa.string()),
        ("terms_raw", pa.string()),
        ("terms_signed", pa.bool_()),
        ("n_terms", pa.int32()),
        ("terms_i64", pa.list_(pa.int64())),
        ("n_parse_errors", pa.int32()),
    ]
)

_FIELD_SCHEMA = pa.schema(
    [
        ("seq_id", pa.int32()),
        ("code", pa.string()),
        ("ordinal", pa.int32()),
        ("line_no", pa.int32()),
        ("content", pa.string()),
    ]
)

_ERR_SCHEMA = pa.schema([("seq_id", pa.int32()), ("message", pa.string())])


def _parse_bucket(bucket: Path) -> list[SeqRecord]:
    return [parse_file(p) for p in sorted(bucket.glob("*.seq"))]


def _seq_batch(recs: list[SeqRecord]) -> pa.RecordBatch:
    return pa.RecordBatch.from_arrays(
        [
            pa.array([r.seq_id for r in recs], pa.int32()),
            pa.array([r.a_number for r in recs], pa.string()),
            pa.array([r.name for r in recs], pa.string()),
            pa.array([r.offset for r in recs], pa.string()),
            pa.array([r.keywords for r in recs], pa.list_(pa.string())),
            pa.array([r.author for r in recs], pa.string()),
            pa.array([r.terms_raw for r in recs], pa.string()),
            pa.array([r.terms_signed for r in recs], pa.bool_()),
            pa.array([r.n_terms for r in recs], pa.int32()),
            pa.array([r.terms_i64 for r in recs], pa.list_(pa.int64())),
            pa.array([len(r.parse_errors) for r in recs], pa.int32()),
        ],
        schema=_SEQ_SCHEMA,
    )


def _field_batch(recs: list[SeqRecord]) -> pa.RecordBatch:
    sid, code, ordinal, line_no, content = [], [], [], [], []
    for r in recs:
        for c, o, ln, txt in r.fields:
            sid.append(r.seq_id)
            code.append(c)
            ordinal.append(o)
            line_no.append(ln)
            content.append(txt)
    return pa.RecordBatch.from_arrays(
        [
            pa.array(sid, pa.int32()),
            pa.array(code, pa.string()),
            pa.array(ordinal, pa.int32()),
            pa.array(line_no, pa.int32()),
            pa.array(content, pa.string()),
        ],
        schema=_FIELD_SCHEMA,
    )


def _err_batch(recs: list[SeqRecord]) -> pa.RecordBatch:
    sid, msg = [], []
    for r in recs:
        for m in r.parse_errors:
            sid.append(r.seq_id)
            msg.append(m)
    return pa.RecordBatch.from_arrays(
        [pa.array(sid, pa.int32()), pa.array(msg, pa.string())], schema=_ERR_SCHEMA
    )


def pin_provenance(mirror: Path) -> dict[str, str]:
    """Read the pinned SHA and commit date out of the cloned mirror."""

    def git(*args: str) -> str:
        return subprocess.run(
            ["git", "-C", str(mirror), *args], capture_output=True, text=True, check=True
        ).stdout.strip()

    return {
        "oeisdata_remote": git("config", "--get", "remote.origin.url"),
        "oeisdata_sha": git("rev-parse", "HEAD"),
        "oeisdata_commit_date": git("log", "-1", "--format=%cI"),
        "oeisdata_commit_subject": git("log", "-1", "--format=%s"),
    }


def build(
    mirror: Path,
    db_path: Path,
    staging: Path,
    workers: int | None = None,
    quiet: bool = False,
) -> dict[str, object]:
    """Parse every `.seq` file under `mirror/seq` and load the result into DuckDB."""
    seq_root = mirror / "seq"
    if not seq_root.is_dir():
        raise FileNotFoundError(f"no seq/ directory under {mirror}")

    prov = pin_provenance(mirror)
    n_files = sum(1 for _ in iter_seq_files(seq_root))
    buckets = sorted(p for p in seq_root.iterdir() if p.is_dir())
    workers = workers or max(1, (os.cpu_count() or 4) - 1)

    staging.mkdir(parents=True, exist_ok=True)
    for old in staging.glob("*.parquet"):
        old.unlink()

    t0 = time.time()
    n_seq = n_fields = n_errs = 0
    w_seq = pq.ParquetWriter(staging / "sequences.parquet", _SEQ_SCHEMA, compression="zstd")
    w_fld = pq.ParquetWriter(staging / "fields.parquet", _FIELD_SCHEMA, compression="zstd")
    w_err = pq.ParquetWriter(staging / "errors.parquet", _ERR_SCHEMA, compression="zstd")
    try:
        with mp.Pool(workers) as pool:
            for i, recs in enumerate(pool.imap(_parse_bucket, buckets, chunksize=1), 1):
                if not recs:
                    continue
                sb, fb, eb = _seq_batch(recs), _field_batch(recs), _err_batch(recs)
                w_seq.write_batch(sb)
                w_fld.write_batch(fb)
                if eb.num_rows:
                    w_err.write_batch(eb)
                n_seq += sb.num_rows
                n_fields += fb.num_rows
                n_errs += eb.num_rows
                if not quiet and i % 50 == 0:
                    print(
                        f"  {i}/{len(buckets)} buckets  {n_seq} seqs  {n_fields} field lines",
                        flush=True,
                    )
    finally:
        w_seq.close()
        w_fld.close()
        w_err.close()
    parse_s = time.time() - t0

    if db_path.exists():
        db_path.unlink()
    con = duckdb.connect(str(db_path))
    con.execute(
        "CREATE TABLE sequences AS SELECT * FROM read_parquet(?)",
        [str(staging / "sequences.parquet")],
    )
    con.execute(
        "CREATE TABLE fields AS SELECT * FROM read_parquet(?)",
        [str(staging / "fields.parquet")],
    )
    con.execute(
        "CREATE TABLE parse_errors AS SELECT * FROM read_parquet(?)",
        [str(staging / "errors.parquet")],
    )
    con.execute("CREATE INDEX idx_fields_seq ON fields(seq_id)")
    con.execute("CREATE INDEX idx_fields_code ON fields(code)")

    meta = {
        **prov,
        "parser_version": PARSER_VERSION,
        "built_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "n_seq_files": str(n_files),
        "n_sequences": str(n_seq),
        "n_field_lines": str(n_fields),
        "n_parse_errors": str(n_errs),
        "parse_seconds": f"{parse_s:.1f}",
    }
    con.execute("CREATE TABLE corpus_meta (key VARCHAR, value VARCHAR)")
    con.executemany("INSERT INTO corpus_meta VALUES (?, ?)", list(meta.items()))
    con.close()
    return meta


def coverage_report(db_path: Path) -> dict[str, object]:
    """Per-field coverage counts — the Phase 0 gate."""
    con = duckdb.connect(str(db_path), read_only=True)
    meta = dict(con.execute("SELECT key, value FROM corpus_meta").fetchall())
    total = con.execute("SELECT count(*) FROM sequences").fetchone()[0]

    rows = con.execute(
        """
        SELECT code, count(*) AS n_lines, count(DISTINCT seq_id) AS n_seqs
        FROM fields GROUP BY code
        """
    ).fetchall()
    by_code = {c: {"n_lines": nl, "n_sequences": ns} for c, nl, ns in rows}
    fields = {}
    for code in FIELD_CODES:
        d = by_code.get(code, {"n_lines": 0, "n_sequences": 0})
        fields[code] = {**d, "pct_sequences": round(100.0 * d["n_sequences"] / total, 3)}
    unknown = {c: v for c, v in by_code.items() if c not in FIELD_CODES}

    terms = con.execute(
        """
        SELECT count(*) FILTER (WHERE terms_raw IS NOT NULL),
               count(*) FILTER (WHERE terms_i64 IS NOT NULL),
               count(*) FILTER (WHERE terms_signed),
               min(n_terms) FILTER (WHERE terms_raw IS NOT NULL),
               median(n_terms) FILTER (WHERE terms_raw IS NOT NULL),
               max(n_terms)
        FROM sequences
        """
    ).fetchone()

    kw = con.execute(
        """
        SELECT k, count(*) AS n FROM (SELECT unnest(keywords) AS k FROM sequences)
        GROUP BY k ORDER BY n DESC
        """
    ).fetchall()
    con.close()

    return {
        "meta": meta,
        "n_sequences": total,
        "fields": fields,
        "unknown_codes": unknown,
        "terms": {
            "with_terms": terms[0],
            "int64_representable": terms[1],
            "signed_variant": terms[2],
            "min_terms": terms[3],
            "median_terms": terms[4],
            "max_terms": terms[5],
        },
        "keywords": dict(kw),
    }


def format_report(rep: dict) -> str:
    """Human-readable coverage table."""
    labels = {
        "I": "ID / M-N numbers",
        "S": "terms (unsigned, line 1)",
        "T": "terms (unsigned, cont.)",
        "U": "terms (unsigned, cont.)",
        "V": "terms (signed, line 1)",
        "W": "terms (signed, cont.)",
        "X": "terms (signed, cont.)",
        "N": "name",
        "C": "comments",
        "D": "references",
        "H": "links",
        "F": "formulas",
        "e": "examples",
        "p": "Maple program",
        "t": "Mathematica program",
        "o": "other programs",
        "Y": "cross-references",
        "K": "keywords",
        "O": "offset",
        "A": "author",
        "E": "extensions/errors",
    }
    m, n = rep["meta"], rep["n_sequences"]
    out = [
        f"oeisdata SHA : {m['oeisdata_sha']}",
        f"commit date  : {m['oeisdata_commit_date']}",
        f"sequences    : {n:,}",
        f"field lines  : {int(m['n_field_lines']):,}",
        f"parse errors : {int(m['n_parse_errors']):,}",
        "",
        f"{'%':<3} {'field':<26} {'sequences':>10} {'% of corpus':>12} {'lines':>12}",
        "-" * 68,
    ]
    for code, d in rep["fields"].items():
        out.append(
            f"{code:<3} {labels.get(code, ''):<26} {d['n_sequences']:>10,} "
            f"{d['pct_sequences']:>11.2f}% {d['n_lines']:>12,}"
        )
    if rep["unknown_codes"]:
        out.append(f"\nUNDECLARED CODES: {rep['unknown_codes']}")
    t = rep["terms"]
    out += [
        "",
        (
            f"terms present     : {t['with_terms']:,}  (signed variant "
            f"{t['signed_variant']:,}, int64-representable {t['int64_representable']:,})"
        ),
        f"terms per seq     : min {t['min_terms']}, median {t['median_terms']}, max {t['max_terms']}",
        f"distinct keywords : {len(rep['keywords'])}",
    ]
    return "\n".join(out)


def main() -> None:
    import argparse

    root = Path(__file__).resolve().parents[3]
    ap = argparse.ArgumentParser(description="Phase 0: build the OEIS corpus DuckDB.")
    ap.add_argument("--mirror", type=Path, default=root / "corpus" / "oeisdata")
    ap.add_argument("--db", type=Path, default=root / "corpus" / "oeis.duckdb")
    ap.add_argument("--staging", type=Path, default=root / "corpus" / "_staging")
    ap.add_argument("--report", type=Path, default=root / "results" / "phase0_coverage.json")
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--quiet", action="store_true", help="suppress per-bucket progress")
    ap.add_argument("--report-only", action="store_true", help="skip build, re-report")
    args = ap.parse_args()

    if not args.report_only:
        meta = build(args.mirror, args.db, args.staging, args.workers, args.quiet)
        if not args.quiet:
            print(f"built in {meta['parse_seconds']}s", flush=True)

    rep = coverage_report(args.db)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(rep, indent=2, ensure_ascii=False))
    print(format_report(rep))
    print(f"\nJSON: {args.report}")


if __name__ == "__main__":
    main()
