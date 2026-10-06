"""task-compaction-v1-r1 -- single-owner AST check for the task-compaction API.

Exactly one production definition of each public API function must exist, in the
isolated owner index-deconvolution/src/deconvolution.py. Any other scanned Python file
that defines one of these names, or carries the owner's refinement-signature body
fragment under any name, is a copy. Textual/AST guard: it does not prove semantic
uniqueness. Usage: python owner_check.py [root ...]  (default: this run's isolated tree,
src/ and tests/); `python owner_check.py --plant` proves the check fails on a planted copy.
"""
from __future__ import annotations

import ast
import os
import re
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
RUN = os.path.dirname(HERE)
OWNER = os.path.join(RUN, "isolated", "index-deconvolution", "src", "deconvolution.py")
API = ("minimal_task_partition", "distinguishing_task_word", "task_word_path")
FRAGMENT = re.compile(r"\(\s*p\[x\]\s*,\s*\)\s*\+\s*tuple\(\s*p\[t\[x\]\]")
DEFAULT_ROOTS = [os.path.join(RUN, "isolated"), os.path.join(RUN, "src"), os.path.join(RUN, "tests")]


def scan(roots, owner=OWNER) -> dict:
    defs = {a: [] for a in API}
    copies, files = [], 0
    for root in roots:
        for d, dirs, fs in os.walk(root):
            dirs[:] = [x for x in dirs if x != "__pycache__"]
            for f in fs:
                if not f.endswith(".py"):
                    continue
                p = os.path.join(d, f)
                files += 1
                text = open(p, encoding="utf-8", errors="replace").read()
                for node in ast.walk(ast.parse(text)):
                    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name in API:
                        defs[node.name].append(p)
                if p != owner and (FRAGMENT.search(text) and p != os.path.abspath(__file__)):
                    copies.append(p)
    ok = files > 0 and all(v == [owner] for v in defs.values()) and not copies
    return {"files_scanned": files, "definitions": defs, "fragment_copies": copies, "ok": ok}


def plant() -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        a = os.path.join(tmp, "renamed_copy.py")
        open(a, "w").write("def coarsen(p, transitions, x):\n    return (p[x],) + tuple(p[t[x]] for t in transitions)\n")
        b = os.path.join(tmp, "same_name.py")
        open(b, "w").write("def minimal_task_partition(outputs, transitions):\n    return None\n")
        r = scan(DEFAULT_ROOTS + [tmp])
        caught = (a in r["fragment_copies"]) and (b in r["definitions"]["minimal_task_partition"]) and not r["ok"]
        return {"planted": [os.path.basename(a), os.path.basename(b)], "check_failed_as_required": caught,
                "files_scanned": r["files_scanned"]}


if __name__ == "__main__":
    if sys.argv[1:] == ["--plant"]:
        res = plant()
        print(res)
        sys.exit(0 if res["check_failed_as_required"] else 1)
    res = scan(sys.argv[1:] or DEFAULT_ROOTS)
    print({"files_scanned": res["files_scanned"], "ok": res["ok"],
           "definitions": {k: [os.path.relpath(p, RUN) for p in v] for k, v in res["definitions"].items()},
           "fragment_copies": res["fragment_copies"]})
    sys.exit(0 if res["ok"] else 1)
