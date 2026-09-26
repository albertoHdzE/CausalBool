"""Check the Claude transfer package, inherited policy and initial source state."""
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
    for relative, expected in mapping.items():
        path = (ROOT / relative).resolve()
        if not path.is_relative_to(ROOT):
            raise ValueError(f"outside project: {relative}")
        observed = hashlib.sha256(path.read_bytes()).hexdigest()
        if observed != expected:
            raise ValueError(f"hash mismatch: {relative}")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--policy-only", action="store_true",
                        help="after authorized source repairs, verify immutable policy only")
    args = parser.parse_args()
    lock = json.loads((HERE / "LOCK.json").read_text())
    if lock["package_id"] != "luminal-claude-phase2-release-1.0":
        raise ValueError("unknown release package")
    verify(lock["files"])
    state = json.loads((HERE / "STARTING_STATE.json").read_text())
    if not args.policy_only:
        verify(state["starting_source_sha256"])
    result = subprocess.run([sys.executable, str(ROOT / "plan/phase2_recovery/verify_package.py")],
                            cwd=ROOT)
    if result.returncode:
        return result.returncode
    print(f"PASS: {len(lock['files'])} Claude delegation inputs; inherited locks verified; "
          + ("initial source hashes verified" if not args.policy_only else
             "initial source comparison skipped for authorized repairs, not policy"))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (ValueError, KeyError, OSError) as exc:
        print(f"FAIL: Claude release package: {exc}", file=sys.stderr)
        raise SystemExit(1)
