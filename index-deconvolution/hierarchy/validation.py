"""Study validation: the one gate that ``report`` and ``verify`` both pass through.

The expected population is built from a DECLARED design (split -> families x base
lengths x replicates x {base, ragged}, times the declared methods), never from the
rows that happen to be present. Every row is checked against that design, every
archive that a status promises is opened, hashed, measured and decoded, and every
portfolio row is checked against the constituent it claims to have selected.

The result keeps three things apart:

* engineering validity  -- a row, archive or identity is wrong (``invalid``);
* completeness          -- a declared row is absent or ``not_run`` (``incomplete``);
* censoring             -- a row is present and legitimate but its value is censored
                           (a baseline timeout or RSS breach); science decides what
                           that means, this module only lists it.

Nothing here computes an endpoint.
"""
from __future__ import annotations

import hashlib
from collections import defaultdict
from pathlib import Path

from . import codes as C

HID_DEPLOYED = ("ok", "timeout_raw", "rss_limit_raw")
BASELINE_CENSORED = ("censored_timeout", "censored_rss_limit")
PORTFOLIO_CENSORED = ("incomplete_constituents",)
FALLBACK_STATUSES = ("timeout_raw", "rss_limit_raw") + BASELINE_CENSORED
ARCHIVE_STATUSES = HID_DEPLOYED + BASELINE_CENSORED + PORTFOLIO_CENSORED
ROW_FIELDS = ("split", "family", "base_length", "replicate", "ragged")


def method_kind(method: str, design: dict | None = None) -> str:
    """Row kind for status rules. A design built from a study registry declares every
    method's kind; only a bare fixture design falls back to the legacy name rule."""
    kinds = (design or {}).get("kinds")
    if kinds:
        k = kinds[method]
        return "hid" if k in ("hid_v1", "hid_v2", "hid_v3a") else k
    if method == "baseline_best":
        return "portfolio"
    return "hid" if method.startswith("hid_") else "baseline"


ALLOWED_STATUSES = {
    "hid": set(HID_DEPLOYED) | {"error", "not_run"},
    "baseline": {"ok", "error", "not_run"} | set(BASELINE_CENSORED),
    "portfolio": {"ok", "error", "not_run"} | set(PORTFOLIO_CENSORED),
}


# ---------------------------------------------------------------------------
# Declared design
# ---------------------------------------------------------------------------

def make_design(splits: dict, methods, baselines, kinds: dict | None = None) -> dict:
    """``splits[split] = {"families", "base_lengths", "replicates"[, "case_prefix"]}``.

    ``methods`` is the full declared method list (including ``baseline_best`` when the
    portfolio is part of the study); ``baselines`` are the portfolio's constituents;
    ``kinds`` maps each method to its registry kind. ``case_prefix`` (default: the split
    name) is the case-id prefix, so development roles keep their original case ids.
    Unit tests pass tiny explicit designs; production uses :func:`production_design`.
    """
    out = {"splits": {}, "methods": tuple(methods), "baselines": tuple(baselines)}
    if kinds is not None:
        out["kinds"] = dict(kinds)
    for split, spec in splits.items():
        out["splits"][split] = {k: tuple(spec[k]) for k in ("families", "base_lengths",
                                                             "replicates")}
        out["splits"][split]["case_prefix"] = spec.get("case_prefix", split)
    if "baseline_best" in out["methods"] and not set(out["baselines"]) <= set(out["methods"]):
        raise ValueError("portfolio constituents must be declared methods")
    return out


def production_design(splits, study=None) -> dict:
    from .baselines import BASELINE_METHODS
    if study is None or study.registry == "hid-v1":
        from .benchmark import ALL_METHODS
        from .corpus import SPLITS
        return make_design({s: SPLITS[s] for s in splits}, ALL_METHODS, BASELINE_METHODS)
    return make_design(study.design_splits(splits), study.all_methods, study.baselines,
                       kinds=study.kinds())


def case_id(split, family, base_length, replicate, ragged) -> str:
    from .corpus import case_id as cid
    return cid(split, family, base_length, replicate, ragged)


def design_case_id(design: dict, split, family, base_length, replicate, ragged) -> str:
    prefix = design["splits"][split].get("case_prefix", split)
    return case_id(prefix, family, base_length, replicate, ragged)


def expected_cases(design: dict, split: str | None = None):
    """Yield (case_id, split, family, base_length, replicate, ragged, n_bits) in order."""
    for sp, spec in design["splits"].items():
        if split is not None and sp != split:
            continue
        for fam in spec["families"]:
            for bl in spec["base_lengths"]:
                for rep in spec["replicates"]:
                    for rg in (False, True):
                        yield (design_case_id(design, sp, fam, bl, rep, rg), sp, fam, bl,
                               rep, rg, bl + 3 if rg else bl)


def unit_label(split, family, base_length, replicate) -> str:
    return f"{split}|{family}|{base_length}|{replicate}"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def portfolio_choice(archives: dict[str, bytes]) -> str:
    """Deterministic minimum: length, then codec id, then archive bytes."""
    return min(archives, key=lambda m: (len(archives[m]), archives[m][4], archives[m]))


def validate_study(rows, design: dict, *, run_dir: Path, run_id: str | None = None,
                   freeze_sha: str | None = None, inputs: dict | None = None,
                   config_shas: dict | None = None, decode: bool = True) -> dict:
    """Validate ``rows`` against ``design``. Returns a JSON-serialisable report plus
    ``index`` ({case_id: {method: row}}, unique known rows only) under key ``_index``.

    ``inputs`` maps case_id -> exact bit string (production: the regenerated corpus);
    without it the decoded hash is compared with the row's own input hash only.
    """
    from .decode import decode_archive
    invalid: list[str] = []
    incomplete: list[str] = []
    censored: list[str] = []
    methods = design["methods"]
    exp = {c[0]: c for c in expected_cases(design)}
    if not exp or not methods:
        invalid.append("declared design is empty: nothing can be validated")
    seen: dict = defaultdict(dict)
    dup_keys = set()
    unknown = []
    for r in rows:
        cid, m = r.get("case_id"), r.get("method")
        if cid not in exp or m not in methods:
            unknown.append(f"{cid}:{m}")
            continue
        if m in seen[cid]:
            dup_keys.add((cid, m))
            continue
        seen[cid][m] = r
    for cid, m in sorted(dup_keys):
        invalid.append(f"{cid}:{m} duplicate row key")
        del seen[cid][m]                # never silently keep either copy
    for u in unknown:
        invalid.append(f"{u} not in the declared design")

    decoded_cache: dict[str, tuple[int, str] | str] = {}
    bytes_cache: dict[str, bytes] = {}
    missing: list[str] = []
    status_counts: dict = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    archives_checked = 0

    def read_archive(r) -> bytes | None:
        p = run_dir / r["archive_path"]
        if r["archive_path"] in bytes_cache:
            return bytes_cache[r["archive_path"]]
        if not p.is_file():
            return None
        data = p.read_bytes()
        bytes_cache[r["archive_path"]] = data
        return data

    for cid, sp, fam, bl, rep, rg, n in exp.values():
        have = seen.get(cid, {})
        want_sha = None
        if inputs is not None:
            if cid not in inputs:
                invalid.append(f"{cid}: no regenerated input supplied")
            else:
                want_sha = _sha(inputs[cid].encode("ascii"))
                if len(inputs[cid]) != n:
                    invalid.append(f"{cid}: regenerated input has {len(inputs[cid])} bits, "
                                   f"design says {n}")
        case_shas = {r.get("input_sha256") for r in have.values()}
        if len(case_shas) > 1:
            invalid.append(f"{cid}: methods disagree on input_sha256")
        for m in methods:
            r = have.get(m)
            if r is None:
                missing.append(f"{cid}:{m}")
                status_counts[sp][m]["absent"] += 1
                continue
            st = r.get("status")
            status_counts[sp][m][str(st)] += 1
            tag = f"{cid}:{m}"
            for k, v in zip(ROW_FIELDS, (sp, fam, bl, rep, rg)):
                if r.get(k) != v:
                    invalid.append(f"{tag} field {k}={r.get(k)!r}, design says {v!r}")
            if r.get("n_bits") != n:
                invalid.append(f"{tag} n_bits={r.get('n_bits')!r}, design says {n}")
            if run_id is not None and r.get("run_id") != run_id:
                invalid.append(f"{tag} run_id {r.get('run_id')!r} != {run_id!r}")
            if freeze_sha is not None and r.get("freeze_sha256") != freeze_sha:
                invalid.append(f"{tag} freeze hash differs from the run's freeze")
            if config_shas is not None and r.get("config_sha256") != config_shas.get(m):
                invalid.append(f"{tag} config_sha256 differs from the frozen method config")
            if want_sha is not None and r.get("input_sha256") != want_sha:
                invalid.append(f"{tag} input_sha256 differs from the regenerated input")
            kind = method_kind(m, design)
            if st not in ALLOWED_STATUSES[kind]:
                invalid.append(f"{tag} status {st!r} not allowed for a {kind} row")
                continue
            if st == "error":
                invalid.append(f"{tag} error row ({r.get('exception_type')})")
                continue
            if st == "not_run":
                incomplete.append(f"{tag} not_run")
                continue
            if st in BASELINE_CENSORED or st in PORTFOLIO_CENSORED:
                censored.append(f"{tag}:{st}")
            # every remaining status promises a deployed archive
            if not r.get("archive_path"):
                invalid.append(f"{tag} status {st} but no archive_path")
                continue
            data = read_archive(r)
            if data is None:
                invalid.append(f"{tag} archive file missing")
                continue
            archives_checked += 1
            h = _sha(data)
            if h != r.get("archive_sha256"):
                invalid.append(f"{tag} archive hash differs from the row")
                continue
            if r.get("archive_bits") != 8 * len(data):
                invalid.append(f"{tag} archive_bits {r.get('archive_bits')} != measured "
                               f"{8 * len(data)}")
            if len(data) < 5 or r.get("selected_codec_id") != data[4]:
                invalid.append(f"{tag} selected_codec_id differs from the archive's codec")
            if st in FALLBACK_STATUSES and (len(data) < 5 or data[4] != C.CODEC_LITERAL):
                invalid.append(f"{tag} {st} fallback is not a literal archive")
            if r.get("decode_ok") is not True:
                invalid.append(f"{tag} decode_ok is {r.get('decode_ok')!r}")
            if decode:
                got = decoded_cache.get(h)
                if got is None:
                    try:
                        s = decode_archive(data)
                        got = (len(s), _sha(s.encode("ascii")))
                    except Exception as exc:          # noqa: BLE001 -- reported
                        got = f"decoder raised {type(exc).__name__}"
                    decoded_cache[h] = got
                if isinstance(got, str):
                    invalid.append(f"{tag} {got}")
                elif got != (n, r.get("input_sha256")) or (want_sha and got[1] != want_sha):
                    invalid.append(f"{tag} archive decodes to a different input")
            if kind == "hid" and r.get("raw_archive_bits") is not None and \
                    8 * len(data) > r["raw_archive_bits"]:
                invalid.append(f"{tag} HID archive longer than the literal archive")
        _check_portfolio(cid, have, design, invalid, read_archive)
    missing_units, missing_by_method = _summarise_missing(design, seen)
    complete = bool(exp) and bool(methods) and not missing and not incomplete
    return {"engineering_valid": not invalid, "complete": complete,
            "invalid": invalid, "incomplete": incomplete + missing,
            "missing_case_methods": missing, "missing_units": missing_units,
            "missing_methods": missing_by_method, "censored": censored,
            "duplicates": [f"{c}:{m}" for c, m in sorted(dup_keys)], "unknown": unknown,
            "expected_rows": len(exp) * len(methods),
            "present_rows": sum(len(v) for v in seen.values()),
            "archives_checked": archives_checked,
            "distinct_archives_decoded": len(decoded_cache),
            "status_counts": {s: {m: dict(v) for m, v in per.items()}
                              for s, per in status_counts.items()},
            "_index": {cid: dict(v) for cid, v in seen.items()}}


def _check_portfolio(cid, have, design, invalid, read_archive) -> None:
    best = have.get("baseline_best")
    if best is None or best.get("status") not in ("ok",) + PORTFOLIO_CENSORED:
        return
    tag = f"{cid}:baseline_best"
    cons = {m: have.get(m) for m in design["baselines"]}
    if best["status"] == "ok":
        bad = [m for m, r in cons.items() if r is None or r.get("status") != "ok"]
        if bad:
            invalid.append(f"{tag} status ok but constituents not ok: {bad}")
            return
    else:
        if all(r is not None and r.get("status") == "ok" for r in cons.values()):
            invalid.append(f"{tag} incomplete_constituents but every constituent is ok")
    avail = {}
    for m, r in cons.items():
        if r is not None and r.get("status") == "ok" and r.get("archive_path"):
            data = read_archive(r)
            if data is None:
                return                      # already reported as a missing archive
            avail[m] = data
    if not avail:
        invalid.append(f"{tag} no available constituent")
        return
    want = portfolio_choice(avail)
    sel = best.get("selected_method")
    if sel != want:
        invalid.append(f"{tag} selected {sel!r}, deterministic minimum is {want!r}")
        return
    w = cons[want]
    for k in ("archive_path", "archive_sha256", "archive_bits", "selected_codec_id"):
        if best.get(k) != w.get(k):
            invalid.append(f"{tag} {k} differs from the selected constituent {want}")
    if best.get("archive_bits") != 8 * min(len(a) for a in avail.values()):
        invalid.append(f"{tag} archive is not the constituent minimum size")


def _summarise_missing(design, seen) -> tuple[dict, dict]:
    units: dict = {}
    by_method: dict = {}
    for sp, spec in design["splits"].items():
        mu = []
        mm = defaultdict(int)
        for fam in spec["families"]:
            for bl in spec["base_lengths"]:
                for rep in spec["replicates"]:
                    gone = False
                    for rg in (False, True):
                        have = seen.get(design_case_id(design, sp, fam, bl, rep, rg), {})
                        for m in design["methods"]:
                            if m not in have:
                                mm[m] += 1
                                gone = True
                    if gone:
                        mu.append(unit_label(sp, fam, bl, rep))
        units[sp] = mu
        by_method[sp] = dict(mm)
    return units, by_method


def public(report: dict) -> dict:
    """The report without its row index (for JSON output)."""
    return {k: v for k, v in report.items() if not k.startswith("_")}


# ---------------------------------------------------------------------------
# The production path shared by ``report`` and ``verify``
# ---------------------------------------------------------------------------

def rows_file_problems(records, cid: str, design_case: tuple, methods) -> list[str]:
    """Structural problems of one ``rows/<case_id>.json``, checked before it is keyed
    by method: a list of row objects, each with a declared method, no method twice
    (identical copies included), and every row carrying this case's design metadata.
    ``design_case`` is (split, family, base_length, replicate, ragged, n_bits)."""
    if not isinstance(records, list):
        return [f"is a JSON {type(records).__name__}, not a list of rows"]
    if not all(isinstance(r, dict) for r in records):
        return ["holds an entry that is not a row object"]
    out = []
    count: dict = defaultdict(int)
    for r in records:
        count[r.get("method")] += 1
    for m, k in count.items():
        if m not in methods:
            out.append(f"method {m!r} not in the declared design")
        if k > 1:
            out.append(f"method {m!r} appears {k} times")
    want = dict(zip(ROW_FIELDS + ("n_bits", "case_id"), design_case + (cid,)))
    for r in records:
        for k, v in want.items():
            if r.get(k) != v:
                out.append(f"{r.get('method')!r} field {k}={r.get(k)!r}, design says {v!r}")
    return out


def validate_run(run_id: str, splits, *, frozen: bool = True, decode: bool = True,
                 purpose: str | None = None, study=None,
                 unfrozen_sha: str = "development-unfrozen") -> tuple[dict, dict]:
    """Validate a WHOLE stored run against the production design of ``splits``.

    ``splits`` is the run's complete declared split set: every row in cases.jsonl and
    every rows/ file is validated, and one outside the design (another split, case or
    method) is engineering invalidity, never filtered out. There is no subset mode.

    Returns (validation, context). Freeze/source/protocol problems, a regenerated
    corpus that differs from the stored manifest, and rows/ files that are malformed
    or disagree with cases.jsonl are engineering invalidity. ``purpose`` additionally
    enforces the frozen environment (``report``); ``verify`` passes None and only
    reports it. ``study`` selects the method registry, roles and inputs (legacy by
    default); an unfrozen development run of a non-legacy study passes its development
    fingerprint as ``unfrozen_sha``.
    """
    import json

    from . import benchmark as B
    from .corpus import split_cases
    from .report import load_rows
    legacy = study is None or study.registry == "hid-v1"
    d = B.run_dir(run_id) if legacy else study.run_dir(run_id)
    extra_invalid: list[str] = []
    ctx: dict = {"run_dir": str(d), "splits": list(splits), "scope": "whole_run"}
    fr, fsha = None, None
    if frozen:
        try:
            fr, fsha, fp = B.load_and_validate_freeze(run_id, purpose=purpose, study=study)
        except FileNotFoundError as exc:
            fp = [f"freeze missing: {exc.filename}"]
        extra_invalid += [f"freeze: {p}" for p in fp]
        ctx["freeze_problems"] = fp
    else:
        fsha = unfrozen_sha
    ctx["freeze_sha256"] = fsha
    ctx["freeze"] = fr
    inputs = {}
    for split in splits:
        cases, manifest = split_cases(split) if legacy else study.role_cases(split, d)
        inputs.update({c.case_id: c.bits for c in cases})
        mp = d / f"corpus_manifest.{split}.jsonl"
        text = "\n".join(json.dumps(m, sort_keys=True) for m in manifest) + "\n"
        if not mp.exists():
            extra_invalid.append(f"corpus manifest missing for {split}")
        elif mp.read_text() != text:
            extra_invalid.append(f"regenerated {split} corpus differs from the stored manifest")
    rows = load_rows(d)                   # all of them: undeclared rows are invalid
    design = production_design(splits, study)
    config_shas = {m: B.method_config_sha(m, study) for m in design["methods"]}
    v = validate_study(rows, design, run_dir=d, run_id=run_id, freeze_sha=fsha,
                       inputs=inputs, config_shas=config_shas, decode=decode)
    # rows/<case_id>.json: well formed on its own, then equal to the merged cases.jsonl
    declared = {c[0]: c[1:] for c in expected_cases(design)}
    for cid, design_case in declared.items():
        p = d / "rows" / f"{cid}.json"
        merged = v["_index"].get(cid, {})
        if not p.exists():
            if merged:
                extra_invalid.append(f"{cid}: rows file missing but cases.jsonl has rows")
            continue
        try:
            records = json.loads(p.read_text())
        except ValueError:
            extra_invalid.append(f"{cid}: rows file unreadable")
            continue
        bad = rows_file_problems(records, cid, design_case, design["methods"])
        if bad:
            extra_invalid += [f"{cid}: rows file {b}" for b in bad]
            continue
        if {r["method"]: r for r in records} != merged:
            extra_invalid.append(f"{cid}: rows file differs from cases.jsonl")
    if (d / "rows").is_dir():
        for p in sorted((d / "rows").iterdir()):
            if p.suffix != ".json" or p.stem not in declared:
                extra_invalid.append(f"rows/{p.name} is not a declared case of {list(splits)}")
    if not legacy and study.registry == "search-v2":
        v["search_v2_checks"] = search_v2_checks(v["_index"], design)
        extra_invalid += v["search_v2_checks"]["invalid"]
    if not legacy and study.trace_sidecars:
        from .report_v3a import trace_checks
        v["trace_checks"] = trace_checks(v["_index"], d, study.hid_methods)
        extra_invalid += v["trace_checks"]["invalid"]
    if extra_invalid:
        v["invalid"] = extra_invalid + v["invalid"]
        v["engineering_valid"] = False
    ctx["design"] = design
    return v, ctx


V2_ARMS = ("hid_legacy", "hid_first_local", "hid_consensus_local", "hid_dense_local",
           "hid_global", "hid_full")


def search_v2_checks(index: dict, design: dict) -> dict:
    """HID-search-v2 invariants on present rows (SEARCH.md section 1).

    * every ``ok`` arm carries telemetry for exactly its registered stages;
    * stage L of every ``ok`` arm is byte-identical to the ``ok`` ``hid_legacy`` archive
      of the same input (independent legacy reruns must agree);
    * nesting: an ``ok`` arm is never longer than an ``ok`` predecessor on the same input.
      A resource fallback (``timeout_raw``/``rss_limit_raw``) may break nesting; that is
      counted, never repaired. A violation between completed arms is invalidity.
    """
    from .search_v2 import ARMS
    invalid, breaks = [], []
    checked = 0
    for cid, have in sorted(index.items()):
        rows = [have.get(a) for a in V2_ARMS]
        legacy = rows[0]
        legacy_sha = legacy["archive_sha256"] if legacy and legacy.get("status") == "ok" else None
        for a, r in zip(V2_ARMS, rows):
            if r is None or r.get("status") != "ok":
                continue
            tele = r.get("search_counters") or {}
            want = list(ARMS[a].stages)
            if tele.get("stages_included") != want or sorted(tele.get("stages", {})) != sorted(want):
                invalid.append(f"{cid}:{a} telemetry stages {tele.get('stages_included')} != {want}")
                continue
            lsha = tele["stages"]["L"].get("archive_sha256")
            if legacy_sha is not None and lsha != legacy_sha:
                invalid.append(f"{cid}:{a} stage L archive differs from hid_legacy")
            if a == "hid_legacy" and r.get("archive_sha256") != lsha:
                invalid.append(f"{cid}:hid_legacy archive is not its stage-L archive")
        for (pa, pr), (a, r) in zip(zip(V2_ARMS, rows), zip(V2_ARMS[1:], rows[1:])):
            if pr is None or r is None or pr.get("archive_bits") is None \
                    or r.get("archive_bits") is None:
                continue
            checked += 1
            if r["archive_bits"] > pr["archive_bits"]:
                if pr.get("status") == "ok" and r.get("status") == "ok":
                    invalid.append(f"{cid}: completed {a} longer than completed {pa}")
                else:
                    breaks.append({"case_id": cid, "arm": a, "predecessor": pa,
                                   "statuses": [pr.get("status"), r.get("status")],
                                   "bits": [pr["archive_bits"], r["archive_bits"]]})
    return {"invalid": invalid, "nesting_pairs_checked": checked,
            "resource_nesting_breaks": breaks, "resource_nesting_break_count": len(breaks)}
