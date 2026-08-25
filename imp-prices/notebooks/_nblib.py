"""Minimal notebook builder, standard library only.

The notebooks in this package are generated rather than hand-edited, for the same
reason the results are: a hand-edited notebook drifts from the code it documents,
and a generated one cannot. Regenerate with ``python build_NN.py`` and then

    ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace <nb>

Executing is what produces the evidence; the builder only lays out the argument.
"""

from __future__ import annotations

import json
import os

KERNEL = {"display_name": "imp-prices", "language": "python", "name": "imp-prices"}

PREAMBLE = '''"""Path setup: makes the notebook runnable from anywhere."""
import os, sys, json, warnings
warnings.filterwarnings("ignore")

here = os.path.abspath(os.getcwd())
while here != "/" and not os.path.exists(os.path.join(here, "PROTOCOL_causal_timeseries.md")):
    here = os.path.dirname(here)
if here == "/":
    here = os.path.expanduser("~/Documents/projects/CausalBool/imp-prices")
ROOT = here
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))

import numpy as np, pandas as pd
import matplotlib
import matplotlib.pyplot as plt
plt.rcParams.update({"figure.dpi": 110, "font.size": 9, "axes.grid": True,
                     "grid.alpha": 0.3, "axes.spines.top": False,
                     "axes.spines.right": False})
print("root:", ROOT)
print("numpy", np.__version__, "| pandas", pd.__version__, "| matplotlib", matplotlib.__version__)
'''


def md(text):
    return {"cell_type": "markdown", "metadata": {},
            "source": text.strip("\n").splitlines(keepends=True)}


def code(text):
    return {"cell_type": "code", "execution_count": None, "metadata": {},
            "outputs": [], "source": text.strip("\n").splitlines(keepends=True)}


def write(path, cells, title):
    nb = {"cells": [md(title), code(PREAMBLE)] + cells,
          "metadata": {"kernelspec": KERNEL,
                       "language_info": {"name": "python"}},
          "nbformat": 4, "nbformat_minor": 5}
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    with open(path, "w") as fh:
        json.dump(nb, fh, indent=1)
    print(f"wrote {path} ({len(nb['cells'])} cells)")
