"""Read-only pre-edit packet audit. No package imports, decoding or inference.

Run from repository root: venv/bin/python -B <this file>.
Vacancy checks apply only before Claude starts; this is not a scientific lock validator.
"""
import ast
import hashlib
import json
from pathlib import Path

PACKET = Path(__file__).resolve().parent
REPO = PACKET.parents[2]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read(path):
    return json.loads(path.read_text())


def main():
    contract = read(PACKET / "contract.json")
    cases = read(PACKET / "CASES.json")["cases"]
    state = read(PACKET / "INITIAL_STATE.json")
    manifest = read(PACKET / "DELEGATION_MANIFEST.json")
    checks, warnings = {}, []
    checks["packet_hashes"] = all((REPO / p).is_file() and sha(REPO / p) == h
                                  for p, h in manifest["files"].items())
    checks["critical_hashes"] = all((REPO / p).is_file() and sha(REPO / p) == h
                                    for p, h in state["critical_files"].items())
    changed = [p for p, h in state["protected_notebooks"].items()
               if not (REPO / p).is_file() or sha(REPO / p) != h]
    permitted = set(state["external_drift_warning_only"])
    checks["protected_notebook_hashes"] = not (set(changed) - permitted)
    warnings.extend("external notebook drift: capture current bytes without reverting " + p
                    for p in changed if p in permitted)
    expected = [(f"confirmation-F{f:02d}-{n}-{r}-{v}", n + 3 * (v == "ragged"))
                for f in range(1, 13) for n in (1024, 4096)
                for r in (3000, 3001) for v in ("base", "ragged")]
    checks["96_exact_ordered_cases"] = [(c["case_id"], c["n_bits"]) for c in cases] == expected
    cells = {}
    for c in cases:
        cells.setdefault((c["family"], c["base_length"]), set()).add(c["replicate"])
    checks["24_cells_two_pairs_each"] = len(cells) == 24 and all(len(v) == 2 for v in cells.values())
    checks["source_rows_and_references"] = True
    cached = {}
    methods = ["hid_full"] + contract["baselines"] + ["baseline_best"]
    for c in cases:
        rp = REPO / c["source_rows_path"]
        if not rp.is_file() or sha(rp) != c["source_rows_sha256"]:
            checks["source_rows_and_references"] = False
            continue
        rows = read(rp)
        by_method = {r["method"]: r for r in rows}
        valid = len(by_method) == len(rows) and set(c["references"]) == set(methods)
        for m in methods:
            ref = c["references"][m]
            r = by_method.get(m, {})
            p = REPO / ref["archive_path"]
            if p not in cached:
                cached[p] = (sha(p), p.stat().st_size * 8) if p.is_file() else (None, None)
            valid &= cached[p] == (ref["archive_sha256"], ref["archive_bits"])
            valid &= all(r.get(k) == ref[k] for k in ("archive_sha256", "archive_bits"))
            valid &= r.get("input_sha256") == c["input_sha256"] and r.get("n_bits") == c["n_bits"]
            valid &= r.get("status") == "ok" and r.get("decode_ok") is True
        checks["source_rows_and_references"] &= valid
    counts = contract["counts"]
    checks["job_counts"] = counts == {"strings": 96, "paired_units": 48, "cells": 24,
        "baseline_jobs": 96, "augmentation_jobs": 288, "new_jobs": 384,
        "derived_composite_records": 288, "imported_baseline_records": 864,
        "derived_portfolio_references": 96}
    budget = contract["resources"]
    checks["six_hour_budget"] = sum(budget["category_caps_s"].values()) == budget["total_s"] == 21600
    checks["report_reserve"] = budget["report_finalization_reserve_s"] == budget["supervisor_review_reserve_s"] == 300
    arms = contract["arms"]
    checks["nested_ablations"] = (arms["A1"]["widths"] == [8]
        and arms["A1"]["max_level"] == arms["A2"]["max_level"] == 1
        and arms["A2"]["widths"] == arms["A3"]["widths"] == [4, 8, 12, 16, 24, 32, 48, 64]
        and arms["A3"]["max_level"] == 4)
    checks["view_proposal_bounds"] = (8 * 2 * 4 == contract["limits"]["views"] == 64
        and 64 * 4 == contract["limits"]["full_root_requests"] == 256)
    checks["exploratory_only"] = (contract["analysis"]["descriptive_only"]
        and not contract["analysis"]["bootstrap_draws"] and not contract["analysis"]["adaptive_scheduler"])
    owner = ast.parse((REPO / "index-deconvolution/hierarchy/baselines.py").read_text())
    baseline_order = next(ast.literal_eval(n.value) for n in owner.body
        if isinstance(n, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "BASELINE_METHODS" for t in n.targets))
    checks["baseline_owner_order"] = list(baseline_order) == contract["baselines"]
    old = read(REPO / "index-deconvolution/results/hierarchy_search_v2/search-confirm-v2-r1/freeze.json")
    checks["accepted_config_identity"] = old["method_configs"]["hid_full"] == {
        "kind": old["method_configs"]["hid_full"]["kind"],
        "config": contract["baseline_config"], "sha256": contract["baseline_config_sha256"]}
    checks["new_paths_unoccupied"] = all(not (REPO / p).exists() for p in (
        contract["results"], contract["ownership"]["new_code"], *contract["notebook"].values()))
    checks["existing_owner_edits_forbidden"] = (not contract["ownership"]["existing_code_edits"]
        and not contract["ownership"]["new_hierarchy_modules_allowed"])
    out = {"all_pass": all(checks.values()), "checks": checks, "warnings": warnings,
           "case_reference_records": len(cases) * len(methods),
           "distinct_reference_archives_hashed": len(cached),
           "scope": "static delegation/read-only reference check; no algorithm implemented or study run"}
    print(json.dumps(out, indent=2, sort_keys=True))
    return 0 if out["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
