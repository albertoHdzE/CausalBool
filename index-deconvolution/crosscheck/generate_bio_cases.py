"""generate_bio_cases.py

Export the output repertoires of a few small biological Boolean networks, with
the Python deconvolution's gate classification, so the Wolfram implementation
can deconvolve the same repertoires and be checked for agreement.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import repertoire
from deconvolution import deconvolve
from bnet import parse_bnet

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BNET_DIR = os.path.join(ROOT, "data", "bio", "raw")
HERE = os.path.dirname(os.path.abspath(__file__))

MODELS = [
    ("Fission yeast cell cycle", "pyboolnet_davidich_yeast.bnet"),
    ("IRMA synthetic yeast", "pyboolnet_irma.bnet"),
    ("WNT5A melanoma", "pyboolnet_xiao_wnt5a.bnet"),
    ("Myeloid differentiation", "pyboolnet_krumsiek_myeloid.bnet"),
    ("Apoptosis", "pyboolnet_tournier_apoptosis.bnet"),
]


def main():
    cases = []
    for label, fname in MODELS:
        path = os.path.join(BNET_DIR, fname)
        net, names = parse_bnet(path)
        rep = repertoire(net)
        _, reports = deconvolve(rep)
        hist = {}
        for r in reports:
            hist[r.canonical.gate] = hist.get(r.canonical.gate, 0) + 1
        cases.append({
            "label": label, "n": net.n, "repertoire": rep,
            "py_gate_histogram": hist,
            "py_regulatory": hist.get("REGULATORY", 0),
        })
        print(f"{label}: n={net.n} regulatory={hist.get('REGULATORY', 0)} hist={hist}")
    with open(os.path.join(HERE, "bio_cases.json"), "w") as f:
        json.dump(cases, f)
    print(f"wrote {len(cases)} cases")


if __name__ == "__main__":
    main()
