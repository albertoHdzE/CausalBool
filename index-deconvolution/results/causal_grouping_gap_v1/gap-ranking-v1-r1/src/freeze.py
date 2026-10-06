"""gap-ranking-v1-r1 -- freeze (before production) and freeze verification.

Usage: python freeze.py write <freeze.json> | python freeze.py verify <freeze.json>
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(RUN, *[".."] * 4))
FROZEN_DIRS = ("protocol", "src", "tests", "dependency")
FROZEN_FILES = ("fixtures.json", "declarations.json", "run.sh")


def sha(p):
    with open(p, "rb") as fh:
        return hashlib.sha256(fh.read()).hexdigest()


def frozen_files():
    out = {}
    for d in FROZEN_DIRS:
        for dp, dns, fns in os.walk(os.path.join(RUN, d)):
            dns[:] = sorted(x for x in dns if x != "__pycache__")
            for f in sorted(fns):
                p = os.path.join(dp, f)
                out[os.path.relpath(p, RUN)] = sha(p)
    for f in FROZEN_FILES:
        out[f] = sha(os.path.join(RUN, f))
    return out


def main(mode, path):
    if mode == "write":
        if os.path.exists(path):
            raise SystemExit("freeze exists; refusing to overwrite")
        sys.path.insert(0, HERE)
        import routes
        man = json.load(open(os.path.join(RUN, "protocol", "manifest.json")))
        tc = json.load(open(os.path.join(RUN, "dependency", "ticket_closure.json")))
        fz = {"run_id": "gap-ranking-v1-r1", "files": frozen_files(),
              "imported_source_identities": routes.EXPECTED_SHA,
              "expected_inputs": man["inputs_relative_to_repository_root"],
              "operator_group": {"version": tc["operator_group_version"]["new"],
                                 "hash": tc["operator_group_hash"]["new"]}}
        json.dump(fz, open(path, "w"), indent=1, sort_keys=True)
        print(len(fz["files"]), "files frozen")
        return 0
    fz = json.load(open(path))
    now = frozen_files()
    bad = sorted(k for k in set(fz["files"]) | set(now) if fz["files"].get(k) != now.get(k))
    inputs_bad = []
    for rel, h in fz["expected_inputs"].items():
        p = os.path.join(REPO, rel)
        if not os.path.exists(p) or sha(p) != h:
            inputs_bad.append(rel)
    print(json.dumps({"frozen_files": len(fz["files"]), "changed": bad,
                      "inputs_checked": len(fz["expected_inputs"]), "inputs_bad": inputs_bad}))
    return 0 if not bad and not inputs_bad else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
