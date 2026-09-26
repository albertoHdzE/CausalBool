"""Verify assignment identity, protected bytes and locked arithmetic; not results."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDENTITY = "luminal-phase2-third-improvement-1.0"


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def verify_hashes(mapping):
    require(bool(mapping), "empty hash map")
    for name, digest in mapping.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), f"path outside project: {name}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"hash mismatch: {name}")


def verify_protocol(p):
    require(p["protocol_id"] == IDENTITY, "protocol identity")
    n = p["diagnostic"]["programs"]
    d = p["development"]["programs"]
    c = p["confirmation"]["programs"]
    dr, cr = p["development"]["repetitions"], p["confirmation"]["repetitions"]
    require((n, d, c, dr, cr) == (30, 100, 200, 3, 5), "sample sizes")
    for group, first, last in (("diagnostic", 800000, 800029),
                               ("development", 800000, 800099),
                               ("confirmation", 980000, 980199)):
        cfg = p[group]
        require((cfg["first_seed"], cfg["last_seed"]) == (first, last), group + " seeds")
        require(last - first + 1 == cfg["programs"] == cfg["per_family"] * 5,
                group + " membership")
    counts = {
        "M_diagnosis": n * (3 + 4), "M_kernel": n * 3 * 2,
        "D_fixed_work": d * dr * 2, "D_wall": d * dr * 2,
        "D_memory": n * 2, "C_acceptance": 142 * 2,
        "C_fixed_work": c * cr * 2, "C_wall": c * cr * 2 * 3,
        "C_public": 8 * cr * (2 * 3 + 1), "C_export": (c + 8) * 3 * 2,
    }
    require(p["expected_rows"] == counts, "expected row counts")
    require(p["wall_budgets_seconds"] == [0.01, 0.1, 1.0], "wall allowances")
    require(p["primary_wall_budget_seconds"] == 0.1, "primary allowance")
    require(p["seeds"] == {"arm_order": 2026092801, "bootstrap": 2026092802}, "seeds")
    require(p["statistics"]["percentiles"] == [0.0125, 0.9875], "confidence endpoints")
    require(p["statistics"]["resamples"] == 10000, "resamples")
    require(p["mechanism_gate"]["conservative_predicted_compile_ratio_max"] == 0.8,
            "mechanism target")
    require(p["mechanism_gate"]["replacement_and_extra_overhead_multiplier"] == 1.5,
            "overhead sensitivity")
    require(p["development_gate"]["fixed_work_compile_ratio_max"] == 0.9 and
            p["development_gate"]["wall_primary_mean_log_J_ratio_max"] == 0.0,
            "development target")
    require(p["confirmation_gate"]["fixed_work_compile_ratio_upper_max"] == 0.8 and
            p["confirmation_gate"]["wall_primary_J_ratio_upper_max"] == 1.01,
            "confirmation target")
    require(all(p["candidate"][k] == 1 for k in
                ("max_designs", "max_integrated_candidates", "max_development_selections",
                 "max_confirmation_cohorts")), "one attempt")
    require(p["authorization"] == {
        "new_learning_experiment": False, "historical_ranker_replay": False,
        "production_integration": False, "manuscript_edits": False,
        "paper_handoff": True, "subagents": False, "commit_push": False,
        "external_publication": False}, "authorized scope")
    require((p["external_timeout_seconds"], p["measurement_wall_cap_hours"],
             p["active_development_cap_hours"]) == (20, 24, 16), "resource caps")
    require(p["failed_row_retry_allowed"] is False, "retry policy")
    return counts


def main():
    lock = json.loads((HERE / "LOCK.json").read_text())
    p = json.loads((HERE / "PROTOCOL.json").read_text())
    require(lock["protocol_id"] == IDENTITY, "lock identity")
    verify_hashes(lock["package"])
    verify_hashes(lock["protected_inputs"])
    counts = verify_protocol(p)
    require(lock["protected_inputs"][p["baseline"]["solver"]] == p["baseline"]["sha256"],
            "baseline source identity")
    require(lock["protected_inputs"][p["baseline"]["export"]] == p["baseline"]["export_sha256"],
            "baseline export identity")
    print(json.dumps({"status": "PASS", "purpose": "assignment integrity only",
                      "package_files": len(lock["package"]),
                      "protected_inputs": len(lock["protected_inputs"]),
                      "conditional_expected_rows": counts}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: third-round assignment: {exc}", file=sys.stderr)
        raise SystemExit(1)
