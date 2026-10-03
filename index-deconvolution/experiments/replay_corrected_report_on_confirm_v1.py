"""Corrected validation/report code applied to the RETAINED confirm-v1 rows (read-only).

Shows that the new validity gates leave the complete-data endpoint arithmetic
unchanged: every estimate and interval is compared with the supervisor's independent
audit (results/hierarchy_v1_supervision/confirm-v1/audit.json) to 1e-12. Uses only
the owners (hierarchy.validation, hierarchy.report). The original freeze no longer
matches the corrected tree, so it is NOT re-validated here; rows are checked against
the original freeze hash they carry. Writes one JSON outside the original run.

    PYTHONPATH=index-deconvolution:src venv/bin/python \
        index-deconvolution/experiments/replay_corrected_report_on_confirm_v1.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "index-deconvolution"))
from hierarchy import benchmark as B  # noqa: E402
from hierarchy import report as R  # noqa: E402
from hierarchy import validation as V  # noqa: E402
from hierarchy.corpus import split_cases  # noqa: E402

RUN = ROOT / "index-deconvolution/results/hierarchy_v1/confirm-v1"
AUDIT = ROOT / "index-deconvolution/results/hierarchy_v1_supervision/confirm-v1/audit.json"
OUT = ROOT / "index-deconvolution/results/hierarchy_v1_corrections/original_rows_under_corrected_report.json"
TOL = 1e-12


def main() -> int:
    fsha = (RUN / "freeze.sha256").read_text().strip()
    splits = ["confirmation", "transfer"]
    inputs = {c.case_id: c.bits for s in splits for c in split_cases(s)[0]}
    design = V.production_design(splits)
    rows = R.load_rows(RUN)
    val = V.validate_study(rows, design, run_dir=RUN, run_id="confirm-v1", freeze_sha=fsha,
                           inputs=inputs,
                           config_shas={m: B.method_config_sha(m) for m in design["methods"]})
    s = R.summarise(val, design, "confirmation")
    audit = json.loads(AUDIT.read_text())
    checks = []

    def cmp(name, got, want):
        diff = max(abs(a - b) for a, b in zip(_flat(got), _flat(want)))
        checks.append({"quantity": name, "corrected_report": got, "supervisor_audit": want,
                       "max_abs_difference": diff, "within_1e-12": diff <= TOL})

    p = s["primary"]
    cmp("primary estimate", p["estimate_mean_saving_per_input_bit"], audit["primary"]["estimate"][0])
    cmp("primary ci95", p["ci95"], audit["primary"]["interval"][0])
    for i, a in enumerate(audit["ablation_order"]):
        cmp(f"{a} estimate", s["ablations"][a]["incremental_gain_per_input_bit"],
            audit["ablations"]["estimate"][i])
        cmp(f"{a} ci99", s["ablations"][a]["ci99"], audit["ablations"]["interval"][i])
    t = s["transfer_structured_aggregate"]
    cmp("transfer estimate", t["estimate"], audit["transfer_descriptive"]["estimate"][0])
    cmp("transfer ci95", t["ci95_descriptive"], audit["transfer_descriptive"]["interval"][0])
    a12 = s["all_families_confirmation_aggregate"]
    cmp("all-12 estimate", a12["estimate"], audit["all12_confirmation_descriptive"]["estimate"][0])
    cmp("all-12 ci95", a12["ci95_descriptive"], audit["all12_confirmation_descriptive"]["interval"][0])
    orig = json.loads((RUN / "summary.json").read_text())
    cmp("controls aggregate vs original summary", [s["controls_aggregate"]["estimate"]]
        + list(s["controls_aggregate"]["ci95_descriptive"]),
        [orig["controls_aggregate"]["estimate"]] + list(orig["controls_aggregate"]["ci95_descriptive"]))
    fam_new = [(r["mean_saving_per_input_bit"], *r["ci95_descriptive"]) for r in s["families_confirmation"]]
    fam_old = [(r["mean_saving_per_input_bit"], *r["ci95_descriptive"]) for r in orig["families_confirmation"]]
    cmp("36 family cells vs original summary", fam_new, fam_old)
    tr_new = [(r["mean_saving_per_input_bit"], *r["ci95_descriptive"]) for r in s["transfer"]]
    tr_old = [(r["mean_saving_per_input_bit"], *r["ci95_descriptive"]) for r in orig["transfer"]]
    cmp("24 transfer cells vs original summary", tr_new, tr_old)
    out = {"run_id": "confirm-v1", "rows": len(rows),
           "note": "corrected validation/report on retained rows; original freeze not "
                   "re-validated against the corrected tree",
           "validation": {k: V.public(val)[k] for k in (
               "engineering_valid", "complete", "expected_rows", "present_rows",
               "archives_checked", "distinct_archives_decoded", "duplicates", "unknown")},
           "invalid_reasons": val["invalid"][:50], "censored": val["censored"][:50],
           "primary_verdict": p["verdict"], "primary_gate": p["gate"],
           "controls_vs_statistical_codes": s["controls_vs_statistical_codes"],
           "all_families_confirmation_aggregate": a12,
           "checks": checks, "all_within_1e-12": all(c["within_1e-12"] for c in checks)}
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ("validation", "primary_verdict", "all_within_1e-12")},
                     indent=1))
    for c in checks:
        print(f"{c['quantity']:<40} max|diff| = {c['max_abs_difference']:.3e}")
    return 0 if out["all_within_1e-12"] and val["engineering_valid"] and val["complete"] else 1


def _flat(x):
    if isinstance(x, (list, tuple)):
        return [y for e in x for y in _flat(e)]
    return [float(x)]


if __name__ == "__main__":
    sys.exit(main())
