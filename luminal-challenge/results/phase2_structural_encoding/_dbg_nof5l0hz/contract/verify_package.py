#!/usr/bin/env python3
"""Read-only validation of the lead-authored phase 2 delegation inputs.

This is not the future experimental evidence checker. It neither implements a
candidate codec nor declares any scientific gate passed.
"""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

PACKAGE = Path(__file__).resolve().parent
ROOT = PACKAGE.parents[2]


def main() -> int:
    errors = []
    counts = {}
    try:
        for name in ("PACKAGE_LOCK.json", "BASELINE_LOCK.json"):
            lock = json.loads((PACKAGE / name).read_text())
            files = lock["files"]
            if not files:
                raise ValueError(f"{name}: empty hash map")
            for relative, expected in files.items():
                path = (ROOT / relative).resolve()
                if not path.is_relative_to(ROOT):
                    raise ValueError(f"path outside repository: {relative}")
                if not path.is_file():
                    errors.append(f"missing: {relative}")
                elif hashlib.sha256(path.read_bytes()).hexdigest() != expected:
                    errors.append(f"hash mismatch: {relative}")
            counts[name] = len(files)
        protocol = json.loads((PACKAGE / "PROTOCOL.json").read_text())
        if protocol["plan_version"] != "2.1":
            errors.append("unexpected plan version")
        fixtures = json.loads((PACKAGE / "FIXTURES.json").read_text())["fixtures"]
        if len(fixtures) != 12 or len({f["id"] for f in fixtures}) != 12:
            errors.append("expected twelve distinct fixtures")
        for fixture in fixtures:
            domains = list(fixture["time_domains"].values()) + list(fixture["address_domains"].values())
            if any(not a or a != sorted(set(a)) for a in domains):
                errors.append(f"malformed domains: {fixture['id']}")
            size = math.prod(map(len, domains))
            if size != fixture["cartesian_assignments"] or size > protocol["budgets"]["oracle_cartesian_max"]:
                errors.append(f"wrong domain size: {fixture['id']}")
        checks = json.loads((PACKAGE / "ACCEPTANCE_MATRIX.json").read_text())["checks"]
        if len(checks) != 30 or len({c["id"] for c in checks}) != 30:
            errors.append("expected thirty distinct acceptance checks")
        counts.update(fixtures=len(fixtures), acceptance_checks=len(checks))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        errors.append(str(exc))
    print(json.dumps({"purpose": "delegation input validation only", "status": "FAIL" if errors else "PASS", "counts": counts, "errors": errors}, indent=2))
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
