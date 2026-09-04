#!/usr/bin/env python3
"""
run_cellnet_cnproc_landscape.py

Compute BDM complexity, perturbation spectra, and combined reprogrammability
for all 14 CellNet cell types from the Jun 2017 cnProc ctGRNs.

Produces the data needed for the Waddington landscape (Fig 5G):
  x-axis: Normalised complexity C(G)/max(C)
  y-axis: Combined reprogrammability sqrt(Pr² + PA²)

Output: data/processed/cellnet_cnproc/cellnet_landscape_data.csv
"""
import os
import sys
import time

import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.complexity import BDMComplexityEstimator, adjacency_matrix
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.reprogrammability import (
    relative_reprogrammability,
    absolute_reprogrammability,
    combined_reprogrammability,
)

import networkx as nx


# AUDIT03 (monolithic-code): four byte-identical copies of this reader
# collapsed onto the ingestion owner. Parity 50/50 on the real edge lists
# before the change; the owner additionally raises on a renamed column.
from imp_causal_paper.bio_ingestion import load_edgelist


def main():
    processed_dir = os.path.join(project_root, "data", "processed", "cellnet_cnproc")
    stats_file = os.path.join(processed_dir, "network_stats.csv")
    stats = pd.read_csv(stats_file)
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)

    rows = []
    for _, row in stats.iterrows():
        ct = row["cell_type"]
        edge_file = os.path.join(processed_dir, f"{ct}_edgelist.csv")
        if not os.path.exists(edge_file):
            continue

        t0 = time.time()
        G = load_edgelist(edge_file)
        n = G.number_of_nodes()
        e = G.number_of_edges()

        mat = adjacency_matrix(G)
        bdm = estimator.matrix_complexity(mat)

        sig = analyzer.signature(G, what="vertices")
        spectra = analyzer.spectra(G, what="vertices")
        pr = relative_reprogrammability(sig)
        pa = absolute_reprogrammability(sig)
        cr = combined_reprogrammability(sig)

        pos = int((spectra["classification"] == "positive").sum())
        neg = int((spectra["classification"] == "negative").sum())
        neu = int((spectra["classification"] == "neutral").sum())

        elapsed = time.time() - t0
        print(f"  {ct:<25s} n={n:4d} e={e:6d} C={bdm:10.1f} Pr={pr:.4f} PA={pa:.4f} Comb={cr:.4f} [{elapsed:.1f}s]")

        spectra.to_csv(os.path.join(processed_dir, f"{ct}_node_spectra.csv"), index=False)

        rows.append({
            "cell_type": ct, "n_nodes": n, "n_edges": e,
            "complexity_bdm": bdm,
            "relative_reprogrammability": pr,
            "absolute_reprogrammability": pa,
            "combined_reprogrammability": cr,
            "positive": pos, "negative": neg, "neutral": neu,
            "elapsed_s": round(elapsed, 1),
        })

    df = pd.DataFrame(rows)
    # Normalise complexity
    max_c = df["complexity_bdm"].max()
    df["normalised_complexity"] = df["complexity_bdm"] / max_c

    out = os.path.join(processed_dir, "cellnet_landscape_data.csv")
    df.to_csv(out, index=False)
    print(f"\nLandscape data: {out}")
    print(df[["cell_type", "n_nodes", "normalised_complexity", "combined_reprogrammability"]].to_string(index=False))


if __name__ == "__main__":
    main()
