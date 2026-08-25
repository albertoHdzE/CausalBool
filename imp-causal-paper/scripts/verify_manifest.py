#!/usr/bin/env python
"""Verify every file listed in a MANIFEST.sha256 (D-5 option (i), AUDIT01/T2.4).

    python scripts/verify_manifest.py imp-causal-paper/results/index_method_comparison

Exit 0 iff every entry matches and no tracked file is missing. Unlisted extra
files are reported but do not fail the check.
"""

from __future__ import annotations

import hashlib
import os
import sys


def main(argv):
    if len(argv) != 2:
        print("usage: verify_manifest.py <dir-containing-MANIFEST.sha256>")
        return 2
    d = argv[1]
    mpath = os.path.join(d, "MANIFEST.sha256")
    if not os.path.exists(mpath):
        print(f"FAIL: no manifest at {mpath}")
        return 1
    bad = missing = 0
    entries = [l.split(None, 1) for l in open(mpath).read().splitlines() if l.strip()]
    for digest, rel in entries:
        rel = rel.strip()
        p = os.path.join(d, rel)
        if not os.path.exists(p):
            print(f"MISSING: {rel}")
            missing += 1
            continue
        h = hashlib.sha256(open(p, "rb").read()).hexdigest()
        if h != digest:
            print(f"CHANGED: {rel}")
            bad += 1
    listed = {rel for _, rel in entries}
    extra = [f for f in sorted(os.listdir(d))
             if f != "MANIFEST.sha256" and f not in listed]
    for f in extra:
        print(f"unlisted (informational): {f}")
    if bad or missing:
        print(f"VERIFY: FAIL ({bad} changed, {missing} missing)")
        return 1
    print(f"VERIFY: PASS — {len(entries)} files match manifest")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
