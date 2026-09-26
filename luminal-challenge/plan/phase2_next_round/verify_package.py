"""Read-only validation of the next-round assignment, never future acceptance."""
import hashlib
import json
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def verify(mapping):
    if not mapping:
        raise ValueError("empty required hash map")
    for name, digest in mapping.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"path outside project: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != digest:
            raise ValueError(f"hash mismatch: {name}")


def main():
    lock = json.loads((HERE / "LOCK.json").read_text())
    protocol = json.loads((HERE / "PROTOCOL.json").read_text())
    expected_id = "luminal-phase2-next-round-1.0"
    if lock["protocol_id"] != expected_id or protocol["protocol_id"] != expected_id:
        raise ValueError("unexpected protocol identity")
    verify(lock["package"])
    verify(lock["protected_inputs"])
    counts = protocol["expected_rows"]
    calculated = {
        "development_factorial": 100 * 3 * 3 * 5,
        "fixed_work_diagnostic": 10 * 3 * 4,
        "engineering_candidate_max": 100 * 3 * 3,
        "compiler_confirmation_two_arms": 200 * 5 * 3 * 2,
        "compiler_confirmation_three_arms": 200 * 5 * 3 * 3,
        "compiler_classical_bootstrap": 200 * 5 * 2,
        "public_two_arms": 8 * 5 * (3 * 2 + 3),
        "public_three_arms": 8 * 5 * (3 * 3 + 3),
        "export": (200 + 8) * 3,
        "learning_acquisition_diagnostic": 100,
        "learning_evaluation_orderings": 30 * 14,
        "learning_timing_max": 30 * 14 * 5,
    }
    if counts != calculated:
        raise ValueError("row arithmetic does not match the assignment")
    if protocol["learned_compiler_confirmation_authorized"]:
        raise ValueError("this round authorizes only a learning pilot")
    print(json.dumps({"status": "PASS", "purpose": "assignment integrity only",
                      "package_files": len(lock["package"]),
                      "protected_inputs": len(lock["protected_inputs"]),
                      "matrix_counts": counts}, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: next-round assignment: {exc}", file=sys.stderr)
        raise SystemExit(1)
