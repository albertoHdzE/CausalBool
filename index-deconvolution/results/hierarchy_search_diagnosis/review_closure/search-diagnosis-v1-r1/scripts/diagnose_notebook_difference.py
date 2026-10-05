"""Diagnose the intermittent cell-9 text difference between guarded executions.

Compares every saved execution (verification/notebook/*.ipynb) with run1.notebook_dir two
ways: the reviewed harness's per-message comparison, and the concatenation of each cell's
stdout/text messages. Reads saved notebooks only; writes verification/notebook/diagnosis.json.
"""
import json
from pathlib import Path

import nbformat

V = Path(__file__).resolve().parents[1] / "verification" / "notebook"


def chunks(nb):
    out = []
    for c in nbformat.read(nb, as_version=4).cells:
        if c.cell_type == "code":
            out.append([o["text"] if o.get("output_type") == "stream" else
                        o.get("data", {}).get("text/plain", "") for o in c.outputs])
    return out


ref = chunks(V / "run1.notebook_dir.ipynb")
res = {}
for f in sorted(V.glob("run*.ipynb")):
    t = chunks(f)
    res[f.name] = {"message_level_differing_cells": [i for i, (a, b) in enumerate(zip(ref, t)) if a != b],
                   "concatenated_text_differing_cells": [i for i, (a, b) in enumerate(zip(ref, t))
                                                         if "".join(a) != "".join(b)],
                   "stdout_messages_in_cell_9": len(t[9])}
diag = {"executions": res,
        "all_concatenated_identical": all(not r["concatenated_text_differing_cells"] for r in res.values()),
        "reading": "Where cell 9 differs, the same stdout text arrives as two stream messages "
                   "(the first print argument flushed separately); concatenated text is identical."}
(V / "diagnosis.json").write_text(json.dumps(diag, indent=1) + "\n")
print(json.dumps(diag, indent=1))
