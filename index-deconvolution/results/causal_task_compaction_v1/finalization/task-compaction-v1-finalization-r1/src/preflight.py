"""task-compaction-v1 finalization -- preflight: verify packet, its inputs, the original freeze
inputs/run_files/isolated, and every entry of the original (397) and closure (153) output manifests.
Usage: python preflight.py <out.json>   (read-only)"""
from __future__ import annotations

import hashlib
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
FIN = os.path.dirname(HERE)
REPO = os.path.abspath(os.path.join(FIN, *[".."] * 5))
BASE = os.path.join(REPO, "index-deconvolution/results/causal_task_compaction_v1")
ORIG = os.path.join(BASE, "task-compaction-v1-r1")
CLOS = os.path.join(BASE, "review_closure/task-compaction-v1-r1")
PKT = os.path.join(BASE, "delegation/task-compaction-v1-finalization")


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
        if isinstance(want, dict):
            ws, wb = want["sha256"], want.get("bytes")
        else:
            ws, wb = want, None
        if not os.path.isfile(p):
            bad.append({"path": rel, "error": "missing"})
            continue
        if sha(p) != ws or (wb is not None and os.path.getsize(p) != wb):
            bad.append({"path": rel, "error": "mismatch"})
    return {"group": group, "n": len(entries), "bad": bad, "ok": len(entries) > 0 and not bad}


def main(out):
    m = json.load(open(os.path.join(PKT, "manifest.json")))
    fr = json.load(open(os.path.join(ORIG, "freeze.json")))
    om = json.load(open(os.path.join(ORIG, "output_manifest.json")))
    cm = json.load(open(os.path.join(CLOS, "output_manifest.json")))
    res = [check("packet", PKT, m["packet"]), check("packet_inputs", REPO, m["inputs"]),
           check("freeze.inputs", REPO, fr["inputs"]), check("freeze.run_files", ORIG, fr["run_files"]),
           check("freeze.isolated", os.path.join(ORIG, "isolated"), fr["isolated"]),
           check("original_output_manifest", ORIG, om["sha256"]),
           check("closure_output_manifest", CLOS, cm["sha256"])]
    mne = {p: os.path.exists(os.path.join(REPO, p)) for p in m["must_not_exist"]}
    rep = {"results": res, "declared_counts": {"original": om["files"], "closure": cm["files"]},
           "must_not_exist_present": mne, "finalization_dir_note": "created by this run before preflight"}
    rep["ok"] = all(r["ok"] for r in res) and om["files"] == 397 and cm["files"] == 153 and \
        len(om["sha256"]) == 397 and len(cm["sha256"]) == 153 and \
        not any(v for k, v in mne.items() if "finalization" not in k)
    json.dump(rep, open(out, "w"), indent=1, sort_keys=True)
    for r in res:
        print(f"{r['group']}: {r['n'] - len(r['bad'])}/{r['n']} ok")
    print("PREFLIGHT", "PASS" if rep["ok"] else "FAIL")
    return 0 if rep["ok"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
