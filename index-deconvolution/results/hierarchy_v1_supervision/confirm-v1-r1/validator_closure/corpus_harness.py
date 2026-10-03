"""Read-only validation of the retained confirm-v1-r1 corpus by a chosen source tree.

NOT production verification. The archives and rows were ENCODED by the frozen
confirm-v1-r1 sources (freeze f970efff...); this harness VALIDATES them with the
sources of ``--tree`` (the unmodified baseline copy, or the patched copy). The
freeze source check is run and reported as it stands: under the patched tree it
names the changed files, and that mismatch is neither overridden nor hidden. The
field ``outcome_excluding_declared_source_change`` is a separately labelled
reading that removes only those named source-hash entries.

Nothing is written under the run directory: every file there is hashed before and
after. The only output is ``--out`` (inside validator_closure/).

    cd <tree> && PYTHONPATH=index-deconvolution:src python corpus_harness.py \
        --tree <tree> --results <repo>/index-deconvolution/results/hierarchy_v1 --out X.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

RID = "confirm-v1-r1"
SPLITS = ["confirmation", "transfer"]


def tree_snapshot(d: Path) -> str:
    h = hashlib.sha256()
    n = 0
    for p in sorted(d.rglob("*")):
        if p.is_file():
            h.update(str(p.relative_to(d)).encode() + b"\0" + p.read_bytes() + b"\0")
            n += 1
    return f"{n} files sha256 {h.hexdigest()}"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--tree", required=True)
    ap.add_argument("--results", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    tree = Path(a.tree).resolve()
    from hierarchy import benchmark as B
    from hierarchy import cli
    from hierarchy import report as R
    from hierarchy import validation as V
    assert Path(V.__file__).resolve().is_relative_to(tree), V.__file__
    B.RESULTS = Path(a.results).resolve()
    d = B.run_dir(RID)
    before = tree_snapshot(d)
    t0 = time.time()
    val, ctx = V.validate_run(RID, SPLITS, frozen=True)
    t_val = time.time() - t0
    pub = V.public(val)
    stored = json.loads((d / "summary.json").read_text())
    fresh = R.summarise(val, ctx["design"], primary_split=SPLITS[0])
    keys = cli.SUMMARY_KEYS_CHECKED
    arithmetic = {k: json.loads(json.dumps(fresh.get(k), default=float)) == stored.get(k)
                  for k in keys}
    rows = sorted((r for m in val["_index"].values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    ledgers = json.dumps(R.representative_ledgers(d, rows), indent=1).encode()
    diag = json.loads((d / "diagnostics.json").read_text())
    led = json.loads(json.dumps(R.claim_ledger(stored, diag, RID), default=float))
    sample = cli._separate_process_sample(d, rows)
    after = tree_snapshot(d)
    declared = [p for p in val["invalid"] if p.startswith("freeze: source changed since freeze: ")]
    other_invalid = [p for p in val["invalid"] if p not in declared]
    # Labelled reading: the same validation with ONLY the named source-hash entries
    # removed, to show that the endpoint arithmetic is untouched by the patch.
    relabel = dict(val, invalid=other_invalid, engineering_valid=not other_invalid)
    fresh_ex = R.summarise(relabel, ctx["design"], primary_split=SPLITS[0])
    arithmetic_ex = {k: json.loads(json.dumps(fresh_ex.get(k), default=float)) == stored.get(k)
                     for k in keys}
    out = {
        "status": "harness reading, NOT production verification",
        "run_id": RID, "results_dir": str(d),
        "encoding_provenance": {"freeze_sha256_stored": (d / "freeze.sha256").read_text().strip(),
                                "freeze_sha256_recomputed": ctx["freeze_sha256"]},
        "validation_code": {"tree": str(tree), "sha256": {
            f"index-deconvolution/hierarchy/{n}": B.sha256_file(tree / "index-deconvolution"
                                                               / "hierarchy" / n)
            for n in ("validation.py", "cli.py", "report.py")}},
        "python": sys.version.split()[0],
        "validate_run_seconds": round(t_val, 1),
        "scope": ctx.get("scope", "not recorded by this tree"),
        "freeze_problems": ctx.get("freeze_problems"),
        "production_exit_code": cli._exit_code(val),
        "engineering_valid": val["engineering_valid"], "complete": val["complete"],
        "invalid_count": len(val["invalid"]), "invalid_first": val["invalid"][:20],
        "declared_source_change_entries": declared,
        "outcome_excluding_declared_source_change": {
            "other_invalid": other_invalid[:20], "other_invalid_count": len(other_invalid),
            "complete": val["complete"],
            "exit_code_if_sources_matched": (cli.EXIT_INVALID if other_invalid else
                                             cli.EXIT_OK if val["complete"]
                                             else cli.EXIT_INCOMPLETE)},
        "counts": {k: pub[k] for k in ("expected_rows", "present_rows", "archives_checked",
                                       "distinct_archives_decoded")},
        "duplicates": pub["duplicates"], "unknown": pub["unknown"],
        "incomplete_count": len(pub["incomplete"]), "censored_count": len(pub["censored"]),
        "rows_files": len(list((d / "rows").iterdir())),
        "summary_arithmetic_equal_to_stored": arithmetic,
        "scientific_verdict": {"recomputed": fresh["primary"]["verdict"],
                               "stored": stored.get("scientific_verdict")},
        "summary_arithmetic_excluding_declared_source_change": arithmetic_ex,
        "primary_excluding_declared_source_change": {
            "verdict": fresh_ex["primary"]["verdict"],
            "estimate": fresh_ex["primary"].get("estimate_mean_saving_per_input_bit"),
            "ci95": fresh_ex["primary"].get("ci95")},
        "ablations_excluding_declared_source_change": {
            k: {"incremental_gain_per_input_bit": v.get("incremental_gain_per_input_bit"),
                "ci99": v.get("ci99"), "component_advantage": v.get("component_advantage")}
            for k, v in fresh_ex.get("ablations", {}).items()},
        "ledgers_json_byte_identical": ledgers == (d / "ledgers.json").read_bytes(),
        "claim_ledger_equal_to_stored": led == json.loads((d / "claim_ledger.json").read_text()),
        "separate_process_sample": sample,
        "run_dir_snapshot": {"before": before, "after": after, "unchanged": before == after},
    }
    Path(a.out).write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ("production_exit_code", "engineering_valid",
                                          "complete", "invalid_count", "counts",
                                          "ledgers_json_byte_identical",
                                          "claim_ledger_equal_to_stored")}
                     | {"arithmetic_all_equal": all(arithmetic.values()),
                        "arithmetic_all_equal_excluding_declared_source_change":
                        all(arithmetic_ex.values()),
                        "run_dir_unchanged": before == after,
                        "other_invalid": out["outcome_excluding_declared_source_change"]
                        ["other_invalid_count"]}, default=float))
    return 0


if __name__ == "__main__":
    sys.exit(main())
