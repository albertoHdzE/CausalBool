"""Validate the objective-directed research delegation, never its future results."""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def verify(mapping):
    if not mapping:
        raise ValueError("empty required hash mapping")
    for name, expected in mapping.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"path outside project: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"hash mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-only", action="store_true",
                        help="verify policy; immutable accepted control snapshots are still checked")
    args = parser.parse_args()
    lock = json.loads((HERE / "LOCK.json").read_text())
    if lock["package_id"] != "luminal-objective-index-research-1.0":
        raise ValueError("unknown delegation package")
    verify(lock["files"])
    state = json.loads((HERE / "STARTING_STATE.json").read_text())
    verify(state["accepted_snapshot_sha256"])
    result = subprocess.run([sys.executable,
        str(ROOT / "plan/phase2_optimization/verify_package.py"), "--policy-only"], cwd=ROOT)
    if result.returncode:
        return result.returncode
    print(f"PASS: {len(lock['files'])} research policy/evidence inputs and inherited locks; "
          + ("policy-only mode" if args.policy_only else
             f"{len(state['accepted_snapshot_sha256'])} immutable accepted-control source hashes"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: scientific research package: {exc}", file=sys.stderr)
        raise SystemExit(1)
