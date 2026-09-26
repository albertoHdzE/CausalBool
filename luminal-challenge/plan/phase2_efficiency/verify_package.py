"""Validate the efficiency assignment and protected inputs; not future results."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def verify(mapping):
    if not mapping:
        raise ValueError("empty hash map")
    for name, expected in mapping.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"input outside project: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"hash mismatch: {name}")


def main():
    lock = json.loads((HERE / "LOCK.json").read_text())
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    identity = "luminal-phase2-assurance-efficiency-1.0"
    if lock["protocol_id"] != identity or protocol["protocol_id"] != identity:
        raise ValueError("unexpected protocol identity")
    verify(lock["package"])
    verify(lock["protected_inputs"])
    counts = {
        "ranker_isolation_replay": 30 * 14,
        "development_fixed_work": 100 * 3 * 2,
        "development_wall_primary": 100 * 3 * 2,
        "confirmation_fixed_work": 200 * 5 * 2,
        "confirmation_wall": 200 * 5 * 2 * 3,
        "public": 8 * 5 * (2 * 3 + 1),
        "export": (200 + 8) * 3,
    }
    if protocol["expected_rows"] != counts:
        raise ValueError("incorrect measurement counts")
    if protocol["new_learning_experiment_authorized"]:
        raise ValueError("learning experiment outside scope")
    print(json.dumps({"status": "PASS", "purpose": "assignment integrity only",
                      "package_files": len(lock["package"]),
                      "protected_inputs": len(lock["protected_inputs"]),
                      "expected_rows": counts}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (KeyError, ValueError, OSError) as exc:
        print(f"FAIL: efficiency assignment: {exc}", file=sys.stderr)
        raise SystemExit(1)
