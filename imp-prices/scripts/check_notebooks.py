#!/usr/bin/env python
"""Verify that an executed notebook is actually evidence.

Three failure modes, each of which has actually occurred here:

1. **Errors.** The obvious one.
2. **Unexecuted cells.** An unexecuted notebook has no error outputs and passes
   an error-only check. A silently aborted nbconvert run leaves exactly that.
3. **Widget outputs.** ``application/vnd.jupyter.widget-view+json`` cannot be
   rendered outside the session that produced it; a reader sees "Could not render
   content" where an output should be. A notebook offered as evidence must not
   contain any.

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
    widgets=sum(1 for c in code for o in c.get("outputs",[])
                for k in o.get("data",{}) if "widget" in k)
    bad = bool(errs or unexec or widgets)
    print(f"{'PROBLEM' if bad else 'OK':8s} {f.split('/')[-1]}: {len(code)} code cells, "
          f"{len(errs)} errors, {len(unexec)} unexecuted, {widgets} unrenderable "
          f"widget outputs, {imgs} figures")
    for e in errs: print("      error:", e)
    if widgets: print("      widget outputs cannot be rendered by a reader; suppress at source")
    ok = ok and not bad
sys.exit(0 if ok else 1)
