"""Investigate how adjacency matrix node ordering affects BDM sign agreement.

The paper's algodyn uses igraph, which may order nodes differently from our
alphabetical sorting. This script tests multiple orderings to find which
best reproduces the paper's ground truth (mmc2-mmc7).

Usage:
    .venv/bin/python scripts/investigate_node_ordering.py
"""
from __future__ import annotations

import csv
import json
import time
from pathlib import Path

import numpy as np
import networkx as nx
from pybdm import BDM

from imp_causal_paper.yosef_network import parse_yosef_networks

PROJECT_ROOT = Path(__file__).resolve().parents[1]
GT_DIR = PROJECT_ROOT / "data" / "raw" / "zenil_supplementary"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "th17" / "yosef_perturbation"

GT_MAPPING = {
    "EarlyNet": ("mmc2.csv", "mmc3.csv"),
    "IntermediateNet": ("mmc4.csv", "mmc5.csv"),
    "FinalNet": ("mmc6.csv", "mmc7.csv"),
}


def load_ground_truth(neg_file: str, pos_file: str) -> dict[str, float]:
    vals: dict[str, float] = {}
    for fname in [neg_file, pos_file]:
        with open(GT_DIR / fname) as f:
            for line in f:
                parts = line.strip().split(",")
                if len(parts) >= 2:
                    try:
                        vals[parts[0]] = float(parts[1])
                    except ValueError:
                        continue
    return vals


def run_perturbation(G: nx.DiGraph, nodelist: list[str], bdm: BDM) -> dict[str, float]:
    mat = nx.to_numpy_array(G, nodelist=nodelist, dtype=int)
    base_c = bdm.bdm(mat)
    deltas = {}
    for idx, node in enumerate(nodelist):
        p = np.delete(np.delete(mat, idx, axis=0), idx, axis=1)
        deltas[node] = base_c - bdm.bdm(p)
    return deltas


def sign_agreement(deltas: dict[str, float], gt: dict[str, float]) -> tuple[int, int, int]:
    agree = disagree = 0
    for node in gt:
        if node in deltas:
            if (deltas[node] > 0 and gt[node] > 0) or (deltas[node] < 0 and gt[node] < 0):
                agree += 1
            else:
                disagree += 1
    return agree, disagree, agree + disagree


def get_orderings(G: nx.DiGraph) -> dict[str, list[str]]:
    """Two critical orderings: sorted (our default) and in_degree_desc (algodyn match)."""
    return {
        "sorted": sorted(G.nodes()),
        "in_degree_desc": sorted(G.nodes(), key=lambda n: G.in_degree(n), reverse=True),
    }


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    nets = parse_yosef_networks()
    bdm = BDM(ndim=2)

    results = {}

    for net_name in ["EarlyNet", "IntermediateNet", "FinalNet"]:
        G = nets[net_name].graph
        gt = load_ground_truth(*GT_MAPPING[net_name])
        orderings = get_orderings(G)

        print(f"\n{'='*60}")
        print(f"{net_name} ({G.number_of_nodes()} nodes, {G.number_of_edges()} edges)")
        print(f"Ground truth: {len(gt)} genes")
        print(f"{'='*60}")

        net_results = {}
        for ord_name, nodelist in orderings.items():
            t0 = time.time()
            deltas = run_perturbation(G, nodelist, bdm)
            elapsed = time.time() - t0
            a, d, total = sign_agreement(deltas, gt)
            pct = a / total * 100 if total else 0
            print(f"  {ord_name:>25}: {a}/{total} ({pct:.0f}%) [{elapsed:.1f}s]")
            net_results[ord_name] = {
                "agree": a,
                "disagree": d,
                "total": total,
                "pct": round(pct, 1),
                "elapsed_s": round(elapsed, 1),
            }

        results[net_name] = net_results

        # Save the best ordering's spectra for EarlyNet
        if net_name == "EarlyNet":
            best_name = max(net_results, key=lambda k: net_results[k]["pct"])
            best_nodelist = orderings[best_name]
            best_deltas = run_perturbation(G, best_nodelist, bdm)
            print(f"\n  Best ordering: {best_name} ({net_results[best_name]['pct']}%)")

            # Save detailed results for the best ordering
            import pandas as pd
            from imp_causal_paper.perturbation import classify_delta
            from imp_causal_paper.complexity import log2_system_size

            threshold = log2_system_size(G)
            mat = nx.to_numpy_array(G, nodelist=best_nodelist, dtype=int)
            base_c = bdm.bdm(mat)
            rows = []
            for node, delta in best_deltas.items():
                rows.append({
                    "element": node,
                    "delta": delta,
                    "base_complexity": base_c,
                    "classification": classify_delta(delta, threshold),
                })
            df = pd.DataFrame(rows)
            spectra_path = OUTPUT_DIR / f"EarlyNet_{best_name}_node_spectra.csv"
            df.to_csv(spectra_path, index=False)
            print(f"  Saved: {spectra_path.name}")

            sig = df.sort_values("delta", ascending=False).reset_index(drop=True)
            sig.to_csv(OUTPUT_DIR / f"EarlyNet_{best_name}_node_signature.csv", index=False)

    # Save summary
    summary_path = OUTPUT_DIR / "ordering_investigation.json"
    with open(summary_path, "w") as f:
        json.dump(results, f, indent=2)
    print(f"\nSummary saved: {summary_path}")


if __name__ == "__main__":
    main()
