"""task-compaction-v1 finalization -- single-owner check for a tree (the disposable stage before
adoption, the active repository after). Reuses the frozen original-run owner_check.scan, imported
by path and hash-checked, with roots <tree>/index-deconvolution/{src,tests} plus the read-only
imp-prices/vendor copy. A planted renamed copy and a same-name copy in a scratch directory must
make the check fail. Usage: python owner_check_r3.py <tree root>  (prints JSON; exit 0 iff the
real tree passes AND the planted check fails)."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, *[".."] * 6))
OCP = os.path.join(REPO, "index-deconvolution/results/causal_task_compaction_v1/task-compaction-v1-r1/src/owner_check.py")
if hashlib.sha256(open(OCP, "rb").read()).hexdigest() != json.load(open(os.path.join(
        os.path.dirname(os.path.dirname(OCP)), "freeze.json")))["run_files"]["src/owner_check.py"]:
    raise SystemExit("frozen owner_check.py identity mismatch")
_spec = importlib.util.spec_from_file_location("owner_check_v1", OCP)
OC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OC)

if __name__ == "__main__":
    tree = os.path.abspath(sys.argv[1])
    owner = os.path.join(tree, "index-deconvolution", "src", "deconvolution.py")
    roots = [os.path.join(tree, "index-deconvolution", d) for d in ("src", "tests")] + \
        [os.path.join(REPO, "imp-prices", "vendor")]
    real = OC.scan(roots, owner=owner)
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "renamed_copy.py"), "w").write(
            "def coarsen(p, transitions, x):\n    return (p[x]," + ") + tuple(p[t[x]] for t in transitions)\n")
        open(os.path.join(tmp, "same_name.py"), "w").write("def distinguishing_task_word(*a):\n    return None\n")
        planted = OC.scan(roots + [tmp], owner=owner)
        caught = (not planted["ok"] and len(planted["fragment_copies"]) == 1
                  and len(planted["definitions"]["distinguishing_task_word"]) == 2)

    def rel(p):
        return os.path.relpath(p, tree) if p.startswith(tree) else os.path.relpath(p, REPO)
    print(json.dumps({"tree": "repository" if tree == REPO else "stage", "files_scanned": real["files_scanned"],
                      "ok": real["ok"], "definitions": {k: [rel(p) for p in v] for k, v in real["definitions"].items()},
                      "fragment_copies": [rel(p) for p in real["fragment_copies"]],
                      "planted_check_failed_as_required": caught, "planted_files_scanned": planted["files_scanned"]},
                     indent=1))
    sys.exit(0 if real["ok"] and caught else 1)
