"""Reporting revision ``report-r2`` of search-diagnosis-v1-r1 (closure of Codex review R1-R3).

  run_report_r2.py identity   record the immutable revision identity (refuses to change it)
  run_report_r2.py report     regenerate rows, summaries, flags, key numbers and the decision
                              from a1's SAVED records; compare with a1's reporting outputs

The computations remain attempt a1 (identity 518ebc13...). This script runs no job, no
encoder and no generator: it imports the reporting source frozen in ``source/`` (the
patched adapters; job-executing adapters byte-identical to a1) and the unchanged
``hierarchy`` owners, reads a1, and writes ONLY below this directory (``identity.json``,
``closure.tar``, ``outputs/``). Run from anywhere with the CausalBool venv::

  PYTHONDONTWRITEBYTECODE=1 venv/bin/python <this file> report

``common`` derives its paths from its own location; because the frozen source lives
here, every Path constant of ``common`` rooted at the source copy is re-rooted, once and
explicitly, onto the real ``index-deconvolution/`` tree before anything is read.
"""
from __future__ import annotations

import hashlib
import io
import json
import sys
import tarfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CLOSURE = HERE.parent
ID = CLOSURE.parents[3]
REPO = ID.parent
SRC = HERE / "source"
OUT = HERE / "outputs"
REVISION = "report-r2"
A1_IDENTITY = "518ebc137118643bf564c76f8e597c15565a95411fe9a946a539cc05e7044a9e"
sys.path[:0] = [str(SRC), str(ID), str(REPO / "src")]

from search_diagnosis import common as K  # noqa: E402

_OLD = K.ID_ROOT
for _name, _val in list(vars(K).items()):                     # re-root, see docstring
    if isinstance(_val, Path) and _val.is_relative_to(_OLD) and _name not in ("PKG",):
        setattr(K, _name, ID / _val.relative_to(_OLD))
K.REPO = REPO
assert K.RUN_DIR == ID / "results/hierarchy_search_diagnosis/search-diagnosis-v1-r1"
assert K.PKG == SRC / "search_diagnosis"

from search_diagnosis import cli  # noqa: E402

REFERENCES = {   # protocol, review and acceptance packet the revision answers to
    "protocol": ID / "PROTOCOL_hierarchy_search_diagnosis.md",
    "contract": ID / "protocols/hierarchy_search_diagnosis/contract.json",
    "closure_kickoff": ID / "KICKOFF_hierarchy_search_diagnosis_closure.md",
    "review": K.RESULT_ROOT / "supervision/search-diagnosis-v1-r1/REVIEW.md",
    "closure_delegation_manifest":
        K.RESULT_ROOT / "supervision/search-diagnosis-v1-r1/closure_delegation_manifest.json",
    "a1_identity": K.RUN_DIR / "identity/identity.json",
}


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def rel(p: Path) -> str:
    return str(p.relative_to(REPO))


def sources() -> list[Path]:
    files = sorted(p for p in SRC.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    return files + [Path(__file__).resolve()]


def consumed() -> dict:
    """Every a1 / accepted-run file the reporting pipeline reads, with its SHA-256."""
    d2 = K.section_ids("D2")
    ids2 = sorted(d2["targets"] + d2["controls"])
    ids4 = K.section_ids("D4")["targets"]
    rp = cli.R.record_path
    files = [rp(K.RUN_DIR, "D2", c, k) for c in ids2 for k in ("B0", "B8")]
    files += [rp(K.RUN_DIR, "D3", c, "D3") for c in d2["targets"]]
    files += [rp(K.RUN_DIR, "D4", c, "D4") for c in ids4]
    files += [K.RUN_DIR / "d1" / n for n in ("d1_cases.json", "d1_tables.json", "d1_checks.json")]
    files += [K.BASE_RUN / "rows" / f"{c}.json" for c in sorted(set(ids2 + ids4))]
    files += [K.REFERENCES, K.CONTRACT, K.RUN_DIR / "identity/identity.json"]
    return {rel(p): (sha(p) if p.exists() else None) for p in files}


def core() -> dict:
    inp = consumed()
    return {"reporting_revision": REVISION, "run_id": K.RUN_ID,
            "compute_attempt": "a1", "compute_identity_sha256": A1_IDENTITY,
            "status": "post-hoc reporting revision of retained computations; disclosed "
                      "exception to protocol §3 accepted by Codex review (a1 kept)",
            "sources": {rel(p): sha(p) for p in sources()},
            "references": {k: {"path": rel(p), "sha256": sha(p)} for k, p in REFERENCES.items()},
            "consumed_records": len(inp),
            "consumed_missing": sorted(k for k, v in inp.items() if v is None),
            "consumed_sha256": K.canonical_sha(inp)}


def closure_tar() -> bytes:
    buf = io.BytesIO()
    with tarfile.open(fileobj=buf, mode="w", format=tarfile.PAX_FORMAT) as tar:
        for p in sorted(sources()):
            data = p.read_bytes()
            ti = tarfile.TarInfo("report-r2-closure/" + str(p.relative_to(CLOSURE)))
            ti.size, ti.mtime, ti.mode, ti.uid, ti.gid = len(data), 0, 0o644, 0, 0
            tar.addfile(ti, io.BytesIO(data))
    return buf.getvalue()


def cmd_identity() -> int:
    c = core()
    if c["consumed_missing"]:
        print("consumed records missing:", c["consumed_missing"][:5], file=sys.stderr)
        return 2
    ident = K.canonical_sha(c)
    p = HERE / "identity.json"
    if p.exists():
        old = json.loads(p.read_text())
        if old["identity_sha256"] != ident:
            print(f"identity changed ({old['identity_sha256'][:12]} -> {ident[:12]}); a revised "
                  "reporting source needs a NEW revision name; refusing", file=sys.stderr)
            return 2
        print("identity unchanged", ident)
        return 0
    tar = closure_tar()
    (HERE / "closure.tar").write_bytes(tar)
    (HERE / "consumed_records.json").write_text(json.dumps(consumed(), indent=1, sort_keys=True) + "\n")
    K.write_json(p, dict(c, identity_sha256=ident, closure_tar_sha256=hashlib.sha256(tar).hexdigest(),
                         recorded_utc=K.utc()))
    print("identity", ident, "| sources", len(c["sources"]), "| consumed", c["consumed_records"])
    return 0


def _leaves(x, path=()):
    if isinstance(x, dict):
        for k, v in x.items():
            yield from _leaves(v, path + (str(k),))
    elif isinstance(x, list):
        for i, v in enumerate(x):
            yield from _leaves(v, path + (str(i),))
    else:
        yield path, x


RENAMED = {   # a1 key path prefix -> report-r2 key path prefix (R2 relabel)
    ("descriptive_B0_cut_location", "supplied_cut_with_B0_cut_within_8_bits"):
        ("descriptive_returned_B0_cut_proximity", "supplied_cut_with_returned_B0_cut_within_8_bits"),
    ("descriptive_B0_cut_location", "supplied_cut_without"):
        ("descriptive_returned_B0_cut_proximity", "supplied_cut_without_returned_B0_cut_within_8_bits"),
    ("d3_B0_cut_location", "supplied_cut_with_B0_cut_within_8_bits"):
        ("d3_returned_B0_cut_proximity", "supplied_cut_with_returned_B0_cut_within_8_bits"),
    ("d3_B0_cut_location", "supplied_cut_without"):
        ("d3_returned_B0_cut_proximity", "supplied_cut_without_returned_B0_cut_within_8_bits"),
}


def _rename(path):
    for i in range(len(path)):
        for old, new in RENAMED.items():
            if path[i:i + len(old)] == old:
                return path[:i] + new + path[i + len(old):]
    return path


def compare(a1: dict, r2: dict) -> dict:
    """Every a1 leaf against report-r2: numeric/boolean leaves must be equal; text may be
    corrected; keys only in r2 are additions."""
    new = dict(_leaves(r2))
    same = numeric_changed = text_changed = 0
    missing, changes = [], []
    for path, v in _leaves(a1):
        q = _rename(path)
        if q not in new:
            missing.append("/".join(path))
            continue
        w = new.pop(q)
        if v == w:
            same += 1
        elif isinstance(v, str) and isinstance(w, str):
            text_changed += 1
            changes.append({"path": "/".join(path), "a1": v, "report_r2": w})
        else:
            numeric_changed += 1
            changes.append({"path": "/".join(path), "a1": v, "report_r2": w, "NUMERIC": True})
    return {"a1_leaves": same + numeric_changed + text_changed + len(missing),
            "identical": same, "numeric_or_boolean_changed": numeric_changed,
            "text_changed": text_changed, "a1_leaves_absent_in_r2": missing,
            "renamed": {"/".join(k): "/".join(v) for k, v in RENAMED.items()},
            "added_in_r2": sorted("/".join(p) for p in new), "changes": changes}


def cmd_report() -> int:
    ident = json.loads((HERE / "identity.json").read_text())
    c = core()
    if K.canonical_sha(c) != ident["identity_sha256"]:
        print("sources, references or consumed a1 records differ from identity.json; refusing",
              file=sys.stderr)
        return 2
    b = cli.report_build(K.RUN_DIR)
    names = ("d2_rows", "d2_summary", "d3_rows", "d4_rows", "d4_summary", "resources",
             "flags", "key_numbers")
    for n in names:
        K.write_json(OUT / f"{n}.json", b[n])
    K.write_json(OUT / "DECISION.json", b["decision"])
    a1 = {n: json.loads((K.RUN_DIR / "analysis" / f"{n}.json").read_text()) for n in names}
    a1["DECISION"] = json.loads((K.RUN_DIR / "DECISION.json").read_text())
    r2 = {n: b[n] for n in names}
    r2["DECISION"] = b["decision"]
    cmp = {n: compare(a1[n], r2[n]) for n in a1}
    after = K.canonical_sha(consumed())
    summary = {"reporting_revision": REVISION, "identity_sha256": ident["identity_sha256"],
               "consumed_unchanged_after": after == ident["consumed_sha256"],
               "recommendation": b["decision"]["recommendation"],
               "files": {n: {k: v for k, v in x.items() if k not in ("changes", "added_in_r2",
                                                                      "renamed")}
                         | {"added": len(x["added_in_r2"])} for n, x in cmp.items()},
               "numeric_or_boolean_changed_total": sum(x["numeric_or_boolean_changed"]
                                                      for x in cmp.values()),
               "a1_leaves_absent_total": sum(len(x["a1_leaves_absent_in_r2"]) for x in cmp.values())}
    K.write_json(OUT / "comparison_with_a1.json", {"summary": summary, "detail": cmp})
    print(json.dumps(summary, indent=1))
    ok = (summary["consumed_unchanged_after"] and summary["numeric_or_boolean_changed_total"] == 0
          and summary["a1_leaves_absent_total"] == 0)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit({"identity": cmd_identity, "report": cmd_report}[sys.argv[1]]())
