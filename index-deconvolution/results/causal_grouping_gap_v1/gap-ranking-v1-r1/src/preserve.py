"""gap-ranking-v1-r1 -- before/after preservation of protected files.

Usage: python preserve.py snapshot <out.json> | python preserve.py compare <before> <after> <diff.json>
Scope: index-deconvolution (src, tests, notebooks, bitacora, protocols, results except this
run), GOVERNANCE, and the sibling series-deconvolution src/tests/pyproject/CLAUDE/TRANSFERENCE.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(RUN, *[".."] * 4))
SIB = os.path.join(os.path.dirname(REPO), "series-deconvolution")
SCOPE = [os.path.join(REPO, "index-deconvolution", d) for d in
         ("src", "tests", "notebooks", "bitacora", "protocols", "results")] + \
        [os.path.join(REPO, "GOVERNANCE")] + \
        [os.path.join(SIB, p) for p in ("src", "tests", "pyproject.toml", "CLAUDE.md",
                                        "TRANSFERENCE.md")]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def snapshot():
    out = {}
    for root in SCOPE:
        if os.path.isfile(root):
            out[os.path.relpath(root, os.path.dirname(REPO))] = sha(root)
            continue
        for dp, dns, fns in os.walk(root):
            dns[:] = [d for d in dns if d != "__pycache__" and
                      os.path.abspath(os.path.join(dp, d)) != RUN]
            for f in fns:
                p = os.path.join(dp, f)
                out[os.path.relpath(p, os.path.dirname(REPO))] = sha(p)
    return out


def main(argv):
    if argv[0] == "snapshot":
        s = snapshot()
        json.dump({"files": len(s), "sha256": s}, open(argv[1], "w"), indent=0, sort_keys=True)
        print(len(s))
        return 0
    b = json.load(open(argv[1]))["sha256"]
    a = json.load(open(argv[2]))["sha256"]
    diff = {"before": len(b), "after": len(a),
            "changed": sorted(k for k in b if k in a and a[k] != b[k]),
            "removed": sorted(set(b) - set(a)), "added": sorted(set(a) - set(b))}
    diff["unchanged"] = not (diff["changed"] or diff["removed"] or diff["added"])
    json.dump(diff, open(argv[3], "w"), indent=1)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in diff.items()}))
    return 0 if diff["unchanged"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
