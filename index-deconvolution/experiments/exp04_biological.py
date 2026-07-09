"""exp04_biological.py

Apply the index-set deconvolution to real gene-regulatory Boolean networks
(PyBoolNet .bnet models under data/bio/raw).  For each network the model is
hidden, the exhaustive repertoire is generated, and the network is recovered by
deconvolution and checked for exact reproduction.  The recovered gates are
classified, quantifying how much of real regulatory logic the canonical family
(now including the REGULATORY activator/inhibitor gate) names, versus the
explicit look-up-table fall-back.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import repertoire
from deconvolution import deconvolve, verify
from bnet import parse_bnet

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BNET_DIR = os.path.join(ROOT, "data", "bio", "raw")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")

# Curated, well-studied biological models small enough for the exhaustive
# repertoire (n <= 16).  Larger models (grieco_mapk 54, remy_tumorigenesis 35)
# require the trajectory-based route and are left for a later entry.
MODELS = [
    ("Arabidopsis root stem cell", "pyboolnet_arellano_rootstem.bnet"),
    ("Fission yeast cell cycle", "pyboolnet_davidich_yeast.bnet"),
    ("Mammalian cell cycle", "pyboolnet_faure_cellcycle.bnet"),
    ("IRMA synthetic yeast", "pyboolnet_irma.bnet"),
    ("Myeloid differentiation", "pyboolnet_krumsiek_myeloid.bnet"),
    ("Guard cell ABA signalling", "pyboolnet_saadatpour_guardcell.bnet"),
    ("Apoptosis", "pyboolnet_tournier_apoptosis.bnet"),
    ("WNT5A melanoma", "pyboolnet_xiao_wnt5a.bnet"),
    ("Budding yeast cell cycle", "pyboolnet_irons_yeast.bnet"),
    ("T-cell receptor", "pyboolnet_klamt_tcr.bnet"),
]

MAX_N = 16


def run():
    records = []
    n_exact = 0
    n_considered = 0
    gate_totals: dict[str, int] = {}

    for label, fname in MODELS:
        path = os.path.join(BNET_DIR, fname)
        if not os.path.exists(path):
            print(f"skip {label}: file not found ({fname})")
            continue
        net, names = parse_bnet(path)
        if net.n > MAX_N:
            print(f"skip {label}: n={net.n} exceeds exhaustive limit {MAX_N}")
            records.append({"label": label, "n": net.n, "skipped": "too_large"})
            continue

        n_considered += 1
        rep = repertoire(net)
        recovered, reports = deconvolve(rep)
        vr = verify(rep, reports)
        if vr["exact"]:
            n_exact += 1

        # classify recovered gates and functional connectivity
        hist: dict[str, int] = {}
        n_named = 0
        n_regulatory = 0
        conn_subset = 0
        for k in range(net.n):
            g = reports[k].canonical.gate
            hist[g] = hist.get(g, 0) + 1
            gate_totals[g] = gate_totals.get(g, 0) + 1
            if g != "LUT":
                n_named += 1
            if g == "REGULATORY":
                n_regulatory += 1
            if set(reports[k].connected_inputs) <= set(net.connected_inputs(k)):
                conn_subset += 1

        rec = {
            "label": label, "file": fname, "n": net.n,
            "exact_repertoire": vr["exact"],
            "named_fraction": n_named / net.n,
            "n_regulatory": n_regulatory,
            "connectivity_subset_of_referenced": conn_subset == net.n,
            "gate_histogram": hist,
        }
        records.append(rec)
        print(f"{label:32s} n={net.n:2d} exact={str(vr['exact']):5s} "
              f"named={n_named:2d}/{net.n:2d} regulatory={n_regulatory:2d}  {hist}")

    summary = {
        "experiment": "biological_deconvolution",
        "n_models_considered": n_considered,
        "n_exact_repertoire": n_exact,
        "gate_totals": gate_totals,
        "records": records,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp04_biological.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print(f"\nexact repertoire reproduction: {n_exact}/{n_considered} models")
    print(f"gate totals across all nodes : {dict(sorted(gate_totals.items()))}")
    print("written: results/exp04_biological.json")
    return summary


if __name__ == "__main__":
    run()
