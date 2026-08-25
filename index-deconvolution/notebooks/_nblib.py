"""_nblib.py -- tiny helper to build the didactic notebooks programmatically.

Each notebook is a list of cells; a cell is markdown or code.  We emit valid
nbformat v4 JSON, so nothing here needs to be installed to *build* the notebooks;
executing them needs the ``CausalBool`` kernel (the repo venv, which has
matplotlib and numpy).
"""

from __future__ import annotations

import itertools
import json
import os

_counter = itertools.count()


def md(text: str) -> dict:
    return {"cell_type": "markdown", "id": f"md{next(_counter)}",
            "metadata": {}, "source": _lines(text)}


def code(text: str) -> dict:
    return {"cell_type": "code", "id": f"cd{next(_counter)}", "metadata": {},
            "execution_count": None, "outputs": [], "source": _lines(text)}


def _lines(text: str) -> list[str]:
    text = text.strip("\n")
    lines = text.split("\n")
    return [ln + "\n" for ln in lines[:-1]] + [lines[-1]] if lines else [""]


def write_notebook(cells: list[dict], path: str) -> None:
    nb = {
        "cells": cells,
        "metadata": {
            "kernelspec": {"display_name": "CausalBool", "language": "python",
                           "name": "causalbool"},
            "language_info": {"name": "python", "version": "3.13"},
        },
        "nbformat": 4, "nbformat_minor": 5,
    }
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(nb, f, indent=1)
    print("wrote", os.path.basename(path), f"({len(cells)} cells)")


# The from-anywhere bootstrap, inlined as the first code cell of every notebook.
# It searches upward from the working directory for the repository marker, with a
# fallback to the known install location, then puts every code layer on the path.
BOOTSTRAP = r'''
# --- Run me first: make this notebook executable from anywhere -----------------
import os, sys

def _find_root(start=None):
    d = os.path.abspath(start or os.getcwd())
    while True:
        if os.path.isfile(os.path.join(d, "PROTOCOL_order_discovery.md")):
            return d
        parent = os.path.dirname(d)
        if parent == d:
            break
        d = parent
    for cand in [os.path.expanduser("~/Documents/projects/CausalBool/index-deconvolution")]:
        if os.path.isfile(os.path.join(cand, "PROTOCOL_order_discovery.md")):
            return cand
    raise RuntimeError("Could not locate the index-deconvolution root. "
                       "Set ROOT = '/path/to/index-deconvolution' by hand and re-run.")

ROOT = _find_root()
for _sub in ["src", "level2", "level3", "level4", "level5", "level6", "level7", "level8"]:
    _p = os.path.join(ROOT, _sub)
    if _p not in sys.path:
        sys.path.insert(0, _p)

DATA       = os.path.join(ROOT, "finance", "data")          # 23 tickers, 3 years
DATA_LONG  = os.path.join(ROOT, "finance", "data_long")     # 12 instruments, ~30+ years
BIO        = os.path.join(os.path.dirname(ROOT), "data", "bio", "raw")  # .bnet networks

import matplotlib.pyplot as plt
import numpy as np

# a clean, consistent didactic style
plt.rcParams.update({
    "figure.figsize": (9, 4.2), "figure.dpi": 110,
    "axes.grid": True, "grid.alpha": 0.25, "axes.spines.top": False,
    "axes.spines.right": False, "font.size": 11, "axes.titlesize": 12,
    "axes.titleweight": "bold", "image.cmap": "magma",
})
INK, HL, OK, BAD = "#20222b", "#c1121f", "#2a9d8f", "#e07a1f"
print("repo root :", ROOT)
print("ready. matplotlib + numpy loaded; code layers on the path.")
'''.strip()
