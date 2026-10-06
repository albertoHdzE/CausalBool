"""task-compaction-v1-r1 review closure -- single-owner check for the corrected isolated owner.

Reuses the frozen ../../task-compaction-v1-r1/src/owner_check.py scan (imported by path, not
copied) with this closure's roots: exactly one definition of each of the three public names
(minimal_task_partition, distinguishing_task_word, task_word_path), in the closure's
isolated deconvolution.py, and no copy of the refinement-signature fragment elsewhere.
--plant adds a renamed copy and a same-name copy in a disposable directory; the check must fail.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import tempfile

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
CLOSURE = os.path.dirname(HERE)
ORIG = os.path.abspath(os.path.join(CLOSURE, "..", "..", "task-compaction-v1-r1"))
_spec = importlib.util.spec_from_file_location("owner_check_v1", os.path.join(ORIG, "src", "owner_check.py"))
OC = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(OC)
OWNER = os.path.join(CLOSURE, "isolated", "index-deconvolution", "src", "deconvolution.py")
ROOTS = [os.path.join(CLOSURE, d) for d in ("isolated", "src", "tests")]


def rel(r):
    return {"files_scanned": r["files_scanned"], "ok": r["ok"], "api": list(OC.API),
            "definitions": {k: [os.path.relpath(p, CLOSURE) for p in v] for k, v in r["definitions"].items()},
            "fragment_copies": r["fragment_copies"]}


if __name__ == "__main__":
    real = OC.scan(ROOTS, owner=OWNER)
    with tempfile.TemporaryDirectory() as tmp:
        open(os.path.join(tmp, "renamed_copy.py"), "w").write(
            "def coarsen(p, transitions, x):\n    return (p[x]," + ") + tuple(p[t[x]] for t in transitions)\n")
        open(os.path.join(tmp, "same_name.py"), "w").write("def task_word_path(t, x, w):\n    return [x]\n")
        planted = OC.scan(ROOTS + [tmp], owner=OWNER)
        caught = (not planted["ok"] and len(planted["fragment_copies"]) == 1
                  and len(planted["definitions"]["task_word_path"]) == 2)
    print(json.dumps({"closure_tree": rel(real), "planted_check_failed_as_required": caught,
                      "planted_files_scanned": planted["files_scanned"]}, indent=1))
    sys.exit(0 if real["ok"] and caught else 1)
