"""exp01_pivots_sumandos.py

Empirical verification of the structural fact stated in the formal manuscript:
connected nodes act as pivots, disconnected nodes as sumandos.

Operationally, for every node of every generated network we check:

  (a) every disconnected input is insensitive: flipping it never changes the
      output column (it lies in the free offset dimension - a sumando);
  (b) the set of sensitive inputs recovered by single-bit perturbation equals
      the true connected set (the pivots), for non-degenerate gates.

A single counterexample to (a) would refute the factorisation on which the
deconvolution rests.  The experiment aggregates over many seeds and network
sizes and writes a JSON summary.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import node_output_column
from deconvolution import essential_variables
from network_generator import random_network

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def run(sizes=(7, 8, 9, 10), seeds_per_size=50):
    total_nodes = 0
    disconnected_insensitive_ok = 0
    connectivity_exact = 0
    connectivity_subset = 0  # recovered subset of true (degenerate gate dropped an input)
    per_gate = {}

    for n in sizes:
        for seed in range(seeds_per_size):
            net = random_network(n=n, seed=seed, gate_pool="all")
            for k in range(n):
                total_nodes += 1
                true_ic = set(net.connected_inputs(k))
                col = node_output_column(net, k)
                sensitive = set(essential_variables(col, n))

                # (a) no disconnected node may be sensitive
                disconnected = set(range(n)) - true_ic
                if sensitive & disconnected == set():
                    disconnected_insensitive_ok += 1

                # (b) sensitive vs true connectivity
                if sensitive == true_ic:
                    connectivity_exact += 1
                if sensitive <= true_ic:
                    connectivity_subset += 1

                g = net.gates[k]
                d = per_gate.setdefault(g, {"nodes": 0, "exact": 0, "dropped_input": 0})
                d["nodes"] += 1
                if sensitive == true_ic:
                    d["exact"] += 1
                elif sensitive < true_ic:
                    d["dropped_input"] += 1

    summary = {
        "experiment": "pivots_vs_sumandos",
        "sizes": list(sizes),
        "seeds_per_size": seeds_per_size,
        "total_nodes": total_nodes,
        "disconnected_insensitive_ok": disconnected_insensitive_ok,
        "disconnected_insensitive_rate": disconnected_insensitive_ok / total_nodes,
        "connectivity_exact": connectivity_exact,
        "connectivity_exact_rate": connectivity_exact / total_nodes,
        "connectivity_subset": connectivity_subset,
        "connectivity_subset_rate": connectivity_subset / total_nodes,
        "per_gate": per_gate,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, "exp01_pivots_sumandos.json")
    with open(path, "w") as f:
        json.dump(summary, f, indent=2)

    print("=== Experiment 1: pivots vs sumandos ===")
    print(f"total nodes examined              : {total_nodes}")
    print(f"disconnected always insensitive   : {disconnected_insensitive_ok}/{total_nodes}"
          f" ({100 * summary['disconnected_insensitive_rate']:.2f}%)")
    print(f"connectivity recovered exactly    : {connectivity_exact}/{total_nodes}"
          f" ({100 * summary['connectivity_exact_rate']:.2f}%)")
    print(f"sensitive set subset of true      : {connectivity_subset}/{total_nodes}"
          f" ({100 * summary['connectivity_subset_rate']:.2f}%)")
    print("per gate (nodes / exact / dropped_input):")
    for g, d in sorted(per_gate.items()):
        print(f"  {g:11s}: {d['nodes']:4d} / {d['exact']:4d} / {d['dropped_input']:4d}")
    print(f"written: {path}")
    return summary


if __name__ == "__main__":
    run()
