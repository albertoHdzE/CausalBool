"""Verify the immutable optimization protocol and inherited baseline policies."""
from pathlib import Path
import argparse
import hashlib
import json
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]


def verify(mapping):
    if not mapping:
        raise ValueError("empty hash mapping")
    for name, expected in mapping.items():
        path = (ROOT / name).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"outside project: {name}")
        if hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"hash mismatch: {name}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-only", action="store_true",
                        help="after authorized edits, verify policy and baselines only")
    args = parser.parse_args()
    lock = json.loads((HERE / "LOCK.json").read_text())
    if lock["package_id"] != "luminal-phase2-optimization-1.0":
        raise ValueError("unknown package")
    verify(lock["files"])
    state = json.loads((HERE / "STARTING_STATE.json").read_text())
    if not args.policy_only:
        verify(state["source_sha256"])
    result = subprocess.run(
        [sys.executable, str(ROOT / "plan/claude_phase2_release/verify_package.py"),
         "--policy-only"], cwd=ROOT)
    if result.returncode:
        return result.returncode
    print(f"PASS: {len(lock['files'])} optimization policy/evidence inputs; inherited locks verified; "
          + ("authorized source changes permitted" if args.policy_only else
             f"{len(state['source_sha256'])} starting source hashes verified"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: optimization package: {exc}", file=sys.stderr)
        raise SystemExit(1)
