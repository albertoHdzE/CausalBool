"""task-compaction-v1 final audit closure (r4) -- read-only preflight and end-of-run identity check.

Verifies: this packet's manifest (packet files and every pinned input, which include the five
accepted active paths), every entry of the original (397), closure (153) and finalization (248)
output manifests, the finalization historical_inputs snapshot against its manifest and the
original freeze, and the original freeze's run_files/isolated groups.
Usage: python preflight_r4.py <out.json>
"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
BASE = os.path.join(REPO, "index-deconvolution/results/causal_task_compaction_v1")
ORIG = os.path.join(BASE, "task-compaction-v1-r1")
CLOS = os.path.join(BASE, "review_closure/task-compaction-v1-r1")
FIN = os.path.join(BASE, "finalization/task-compaction-v1-finalization-r1")
PKT = os.path.join(BASE, "delegation/task-compaction-v1-final-audit-closure")
ACTIVE = ["index-deconvolution/src/deconvolution.py", "index-deconvolution/tests/test_task_compaction.py",
          "index-deconvolution/tests/fixtures/task_compaction_v1.json", "index-deconvolution/TASK_COMPACTION_V1.md",
          "GOVERNANCE/CORE.md"]


def sha(p):
    h = hashlib.sha256()
    with open(p, "rb") as fh:
        for c in iter(lambda: fh.read(1 << 20), b""):
            h.update(c)
    return h.hexdigest()


def check(group, root, entries):
    bad = []
    for rel, want in sorted(entries.items()):
        p = os.path.join(root, rel)
        ws, wb = (want["sha256"], want.get("bytes")) if isinstance(want, dict) else (want, None)
        if not os.path.isfile(p):
            bad.append({"path": rel, "error": "missing"})
        elif sha(p) != ws or (wb is not None and os.path.getsize(p) != wb):
            bad.append({"path": rel, "error": "mismatch"})
    return {"group": group, "n": len(entries), "bad": bad, "ok": len(entries) > 0 and not bad}


def main(out):
    m = json.load(open(os.path.join(PKT, "manifest.json")))
    fr = json.load(open(os.path.join(ORIG, "freeze.json")))
    oms = {"original": (ORIG, 397), "closure": (CLOS, 153), "finalization": (FIN, 248)}
    res = [check("packet", PKT, m["packet"]), check("packet_inputs", REPO, m["inputs"]),
           check("freeze.run_files", ORIG, fr["run_files"]),
           check("freeze.isolated", os.path.join(ORIG, "isolated"), fr["isolated"])]
    counts = {}
    for name, (root, n) in oms.items():
        om = json.load(open(os.path.join(root, "output_manifest.json")))
        r = check(f"{name}_output_manifest", root, om["sha256"])
        r["ok"] &= om["files"] == n == len(om["sha256"])
        counts[name] = om["files"]
        res.append(r)
    hroot = os.path.join(FIN, "historical_inputs")
    hm = json.load(open(os.path.join(FIN, "historical_inputs_manifest.json")))["files"]
    have = sorted(os.path.relpath(os.path.join(d, f), hroot) for d, _, fs in os.walk(hroot) for f in fs)
    r = check("historical_inputs_vs_freeze", hroot, fr["inputs"])
    r["ok"] &= have == sorted(fr["inputs"]) == sorted(hm)
    res.append(r)
    active = {p: sha(os.path.join(REPO, p)) for p in ACTIVE}
    active_ok = all(active[p] == m["inputs"][p]["sha256"] for p in ACTIVE)
    old_manifests = {k: sha(os.path.join(v[0], "output_manifest.json")) for k, v in oms.items()}
    rep = {"results": res, "declared_counts": counts, "active_sha256": active, "active_match_packet": active_ok,
           "old_output_manifest_sha256": old_manifests}
    rep["ok"] = all(x["ok"] for x in res) and active_ok
    with open(out, "w") as fh:
        json.dump(rep, fh, indent=1, sort_keys=True)
    for x in res:
        print(f"{x['group']}: {x['n'] - len(x['bad'])}/{x['n']} ok")
    print(f"active paths match packet: {active_ok} (5)")
    print("PREFLIGHT", "PASS" if rep["ok"] else "FAIL")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
