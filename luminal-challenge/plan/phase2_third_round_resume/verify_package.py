"""Validate the scoped continuation and parent contract, not future results."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
IDENTITY = "luminal-phase2-third-improvement-resume-1.0"


def require(condition, message):
    if not condition:
        raise ValueError(message)


def hashes(mapping):
    require(bool(mapping), "empty hash map")
    for name, digest in mapping.items():
        path = (ROOT / name).resolve()
        require(path.is_relative_to(ROOT), f"outside project: {name}")
        require(hashlib.sha256(path.read_bytes()).hexdigest() == digest,
                f"changed protected/package input: {name}")


def check_protocol(p, parent):
    require(p["protocol_id"] == IDENTITY, "wrong identity")
    a = p["adapter"]
    require((a["first_seed"], a["last_seed"], a["programs"], a["repetitions"],
             a["expected_rows"], a["max_implementations"]) == (800000, 800029, 30, 3, 90, 1),
            "adapter membership/attempts")
    require(a["expected_rows"] == a["programs"] * a["repetitions"], "adapter row count")
    require(p["accounting"]["conservative_ratio_max"] == 0.8 and
            p["accounting"]["overhead_multiplier"] == 1.5, "M gate changed")
    require(set(p["accounting"]["matched_timer_components"]) == {
        "tfix_shell", "tfix_copy", "precedence", "issue_capacity", "bounds_live",
        "bounds_product", "address_support", "child_domain_copy", "certificates",
        "propagation_setup", "address_pairs"}, "cost scope changed")
    for stage, count in p["inherited_expected_rows"].items():
        require(parent["expected_rows"][stage] == count, f"parent count changed: {stage}")
    require(set(p["inherited_expected_rows"]) == {s for s in parent["expected_rows"]
                                                if s.startswith(("D_", "C_"))}, "stage set")
    for stage in ("development", "confirmation"):
        require(all(parent[f"{stage}_gate"][k] == v for k, v in
                    p[f"inherited_{stage}_gate"].items()), f"{stage} gate changed")
    require(p["inherited_confirmation_seeds"] == [parent["confirmation"]["first_seed"],
                                                 parent["confirmation"]["last_seed"]],
            "confirmation seeds changed")
    require(p["combined_budget"] == {"measurement_wall_hours": 24,
                                     "active_development_hours": 16,
                                     "include_parent_run": True}, "budget reset")
    require(p["preserved_mechanism"]["max_designs"] == 1 and
            p["preserved_mechanism"]["max_compiler_candidates"] == 1, "candidate scope")
    require(not any(p["authorization"][key] for key in
                    ("new_mechanism", "new_learning", "production", "paper_edits",
                     "subagents", "commit_push", "publication")), "unauthorized expansion")


def main():
    lock = json.loads((HERE / "LOCK.json").read_text())
    p = json.loads((HERE / "PROTOCOL.json").read_text())
    parent = json.loads((ROOT / p["parent_protocol"]).read_text())
    require(lock["protocol_id"] == IDENTITY, "wrong lock")
    hashes(lock["package"])
    hashes(lock["protected_inputs"])
    check_protocol(p, parent)
    result = subprocess.run([sys.executable, "plan/phase2_third_round/verify_package.py"],
                            cwd=ROOT, capture_output=True, text=True)
    require(result.returncode == 0, "parent package failed: " + result.stderr[-500:])
    print(json.dumps({"status": "PASS", "purpose": "assignment integrity only",
                      "package_files": len(lock["package"]),
                      "protected_inputs": len(lock["protected_inputs"]),
                      "new_adapter_rows": 90,
                      "conditional_inherited_rows": p["inherited_expected_rows"]}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: third-round continuation: {exc}", file=sys.stderr)
        raise SystemExit(1)
