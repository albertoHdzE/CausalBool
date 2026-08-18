#!/usr/bin/env python
"""Verify that an executed notebook is actually evidence.

An error check alone is not enough: an *unexecuted* notebook has no error
outputs and passes it. This checks for errors and for unexecuted code cells,
which is how a silently aborted nbconvert run was caught.

    .venv/bin/python scripts/check_notebooks.py notebooks/*.ipynb
"""
import json, sys

ok=True
for f in sys.argv[1:]:
    nb=json.load(open(f))
    code=[c for c in nb["cells"] if c["cell_type"]=="code"]
    errs=[o.get("evalue") for c in code for o in c.get("outputs",[]) if o.get("output_type")=="error"]
    unexec=[i for i,c in enumerate(code) if c.get("execution_count") is None]
    imgs=sum(1 for c in code for o in c.get("outputs",[]) if "image/png" in o.get("data",{}))
    status = "OK" if not errs and not unexec else "PROBLEM"
    print(f"{status:8s} {f.split('/')[-1]}: {len(code)} code cells, {len(errs)} errors, "
          f"{len(unexec)} unexecuted, {imgs} figures")
    for e in errs: print("      error:", e)
    ok = ok and not errs and not unexec
sys.exit(0 if ok else 1)
