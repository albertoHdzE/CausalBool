#!/usr/bin/env python3
"""
run_cellnet_overall_complexity.py

Compute BDM complexity for CellNet overallGRN networks (correct data layer).

These are large networks (5k-20k nodes, 200k-2.3M edges). Full node
perturbation is computationally infeasible. We compute:
  - Base BDM complexity C(G) only
  - Network statistics

For the Waddington landscape (Fig 5G), we need combined reprogrammability
which requires full perturbation. This is only feasible for the smallest
networks (intestine_colon at 5112 nodes is borderline).

Output: data/processed/cellnet_overall/cellnet_overall_complexity.csv
"""
import os
import sys
import time

import numpy as np
import pandas as pd

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.complexity import BDMComplexityEstimator, adjacency_matrix

import networkx as nx


# AUDIT03 (monolithic-code): four byte-identical copies of this reader
# collapsed onto the ingestion owner. Parity 50/50 on the real edge lists
# before the change; the owner additionally raises on a renamed column.
from imp_causal_paper.bio_ingestion import load_edgelist


def main():
    processed_dir = os.path.join(project_root, "data", "processed", "cellnet_overall")
    stats_file = os.path.join(processed_dir, "network_stats.csv")
    if not os.path.exists(stats_file):
        print(f"ERROR: {stats_file} not found. Run extract_overallGRN.R first.",
              file=sys.stderr)
        sys.exit(1)

    stats = pd.read_csv(stats_file)
    estimator = BDMComplexityEstimator()

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

        print(f"  {ct}: {n_nodes} nodes, {n_edges} edges — computing BDM...",
              end="", flush=True)

        mat = adjacency_matrix(G)
        base_complexity = estimator.matrix_complexity(mat)
        elapsed = time.time() - t0

        print(f" C(G)={base_complexity:.1f} [{elapsed:.1f}s]")

        rows.append({
            "cell_type": ct,
            "n_nodes": n_nodes,
            "n_edges": n_edges,
            "complexity_bdm": base_complexity,
            "elapsed_s": round(elapsed, 1),
            "source": row["source"],
            "data_layer": "overallGRN",
        })

    summary = pd.DataFrame(rows)
    out_file = os.path.join(processed_dir, "cellnet_overall_complexity.csv")
    summary.to_csv(out_file, index=False)
    print(f"\nSummary written to {out_file}")
    print(summary[["cell_type", "n_nodes", "n_edges", "complexity_bdm"]].to_string(index=False))


if __name__ == "__main__":
    main()
