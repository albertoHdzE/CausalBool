"""Verify the lead's immutable recovery package and original protected inputs."""
from pathlib import Path
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def main():
    lock = json.loads((HERE / "LOCK.json").read_text())
    files = lock["files"]
    if not files:
        raise ValueError("empty recovery lock")
    for name, expected in files.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"path outside project: {name}")
        actual = hashlib.sha256(path.read_bytes()).hexdigest()
        if actual != expected:
            raise ValueError(f"recovery input changed: {name}")
    amendment = json.loads((HERE / "AMENDMENT.json").read_text())
    assert amendment["amendment_id"] == lock["amendment_id"]
    base = json.loads((ROOT / "plan/phase2/PROTOCOL.json").read_text())
    assert amendment["base_protocol_id"] == base["protocol_id"]
    comparisons = amendment["comparisons"]
    assert comparisons["budgets_seconds"] == base["budgets"]["optimisation_seconds"]
    assert comparisons["timing_repetitions"] == base["statistics"]["timing_repetitions"]
    per_program = comparisons["timing_repetitions"] * (
        len(comparisons["unbudgeted_arms"]) + len(comparisons["budgets_seconds"]) *
        len(comparisons["budgeted_arms"]))
    assert comparisons["p2_expected_measurements"] == comparisons["public_programs"] * per_program
    assert comparisons["p5_expected_nonmodel_measurements"] == (
        comparisons["public_programs"] + comparisons["heldout_programs"]) * per_program
    result = subprocess.run([sys.executable, str(ROOT / "plan/phase2/verify_package.py")], cwd=ROOT)
    if result.returncode:
        return result.returncode
    print(f"PASS: {len(files)} recovery inputs; inherited protocol and measurement counts agree")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError, AssertionError) as exc:
        print(f"FAIL: recovery package: {exc}", file=sys.stderr)
        raise SystemExit(1)
