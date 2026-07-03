#!/usr/bin/env python3
"""
run_cellnet_complexity.py

Compute BDM complexity and relative reprogrammability for each CellNet
cell-type GRN extracted by extract_cellnet_grns.R.

For each cell type:
  - Load the edge list from data/processed/cellnet/{ct}_edgelist.csv
  - Build directed NetworkX graph
  - Compute base BDM complexity C(G)
  - Compute node perturbation spectra (skipped for networks > NODE_LIMIT nodes)
  - Compute relative reprogrammability Pr(G)

Outputs:
  data/processed/cellnet/cellnet_complexity_summary.csv
  data/processed/cellnet/{ct}_node_spectra.csv   (when computed)

Usage:
  python scripts/run_cellnet_complexity.py [--node-limit N] [--quiet]
"""
import sys
import os
import time
import argparse
import json

import pandas as pd
import numpy as np

# Ensure project src is on path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.complexity import BDMComplexityEstimator, adjacency_matrix
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.reprogrammability import relative_reprogrammability

import networkx as nx

DEFAULT_NODE_LIMIT = 1000  # skip full perturbation for networks larger than this


def load_edgelist(path):
    df = pd.read_csv(path)
    G = nx.DiGraph()
    G.add_edges_from(zip(df["TF"], df["TG"]))
    return G


def compute_base_complexity(G, estimator):
    mat = adjacency_matrix(G)
    return estimator.matrix_complexity(mat)


def compute_perturbation(G, estimator, analyzer):
    spectra = analyzer.spectra(G, what="vertices")
    sig = analyzer.signature(G, what="vertices")
    pr = relative_reprogrammability(sig)
    return spectra, sig, pr


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--node-limit", type=int, default=DEFAULT_NODE_LIMIT,
                        help="Skip perturbation for networks larger than this (default 1000)")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args()

    processed_dir = os.path.join(project_root, "data", "processed", "cellnet")
    stats_file = os.path.join(processed_dir, "network_stats.csv")
    if not os.path.exists(stats_file):
        print(f"ERROR: {stats_file} not found. Run extract_cellnet_grns.R first.", file=sys.stderr)
        sys.exit(1)

    stats = pd.read_csv(stats_file)
    estimator = BDMComplexityEstimator()
    analyzer = GraphPerturbationAnalyzer(estimator)

    rows = []
    for _, row in stats.iterrows():
        ct = row["cell_type"]
        edge_file = os.path.join(processed_dir, f"{ct}_edgelist.csv")
        if not os.path.exists(edge_file):
            print(f"  WARNING: {edge_file} not found, skipping.")
            continue

        t0 = time.time()
        G = load_edgelist(edge_file)
        n_nodes = G.number_of_nodes()
        n_edges = G.number_of_edges()

        # Base complexity
        base_complexity = compute_base_complexity(G, estimator)

        # Perturbation
        if n_nodes <= args.node_limit:
            spectra, sig, pr = compute_perturbation(G, estimator, analyzer)
            pos = int((spectra["classification"] == "positive").sum())
            neg = int((spectra["classification"] == "negative").sum())
            neu = int((spectra["classification"] == "neutral").sum())
            spectra.to_csv(os.path.join(processed_dir, f"{ct}_node_spectra.csv"), index=False)
            perturbation_status = "computed"
        else:
            pr = float("nan")
            pos = neg = neu = -1
            perturbation_status = f"skipped (n_nodes={n_nodes} > {args.node_limit})"

        elapsed = time.time() - t0

        if not args.quiet:
            pr_str = f"{pr:.4f}" if not np.isnan(pr) else "n/a"
            print(f"  {ct:<25} nodes={n_nodes:4d}  edges={n_edges:7d}  "
                  f"C(G)={base_complexity:.1f}  Pr={pr_str}  "
                  f"[{elapsed:.1f}s]  {perturbation_status}")

        rows.append({
            "cell_type": ct,
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "complexity_bdm": base_complexity,
            "relative_reprogrammability": pr,
            "positive_count": pos,
            "negative_count": neg,
            "neutral_count": neu,
            "perturbation_status": perturbation_status,
            "source": row["source"],
            "elapsed_s": round(elapsed, 1),
        })

    summary = pd.DataFrame(rows)
    out_file = os.path.join(processed_dir, "cellnet_complexity_summary.csv")
    summary.to_csv(out_file, index=False)

    print(f"\nSummary written to {out_file}")
    computed = summary[summary["perturbation_status"] == "computed"]
    if not args.quiet and len(computed) > 0:
        print("\nCell types with full perturbation:")
        print(computed[["cell_type", "n_nodes", "complexity_bdm",
                        "relative_reprogrammability"]].to_string(index=False))


if __name__ == "__main__":
    main()
