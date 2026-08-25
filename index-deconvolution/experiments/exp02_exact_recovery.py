"""exp02_exact_recovery.py

Main deconvolution result.  For a batch of generated networks the original
definition is hidden; only the output repertoire is passed to the deconvolution.
The recovered network is then compared against the hidden original on three
levels:

  1. Repertoire equivalence - does the reconstructed network reproduce the
     output repertoire byte for byte?  (the decisive success criterion)
  2. Connectivity recovery - is the connected set of every node recovered?
  3. Gate recovery - does the recovered canonical gate lie in the same function
     as the original, and how large is the ambiguity class?

Results, including any failures, are written to JSON.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from causalbool import Network, repertoire, truth_table, node_output_column
from deconvolution import deconvolve, verify
from network_generator import random_network

RESULTS_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "results")


def _reduced_truth_table_of_original(net: Network, k: int) -> list[int]:
    """The true reduced truth table of node k over its connected inputs."""
    ic = net.connected_inputs(k)
    m = len(ic)
    tt = []
    for y in range(2 ** m):
        sub = [(y >> j) & 1 for j in range(m)]
        from causalbool import apply_gate
        tt.append(apply_gate(net.gates[k], sub, net.params[k]))
    return tt


def run(sizes=(7, 8, 9, 10), seeds_per_size=50):
    records = []
    n_networks = 0
    n_exact_repertoire = 0
    n_nodes = 0
    n_conn_exact = 0
    n_gate_function_correct = 0
    ambiguity_hist = {}

    for n in sizes:
        for seed in range(seeds_per_size):
            n_networks += 1
            original = random_network(n=n, seed=10_000 + seed, gate_pool="all")
            rep = repertoire(original)  # only object exposed to deconvolution

            recovered, reports = deconvolve(rep)
            vr = verify(rep, reports)
            if vr["exact"]:
                n_exact_repertoire += 1

            net_record = {
                "n": n, "seed": seed, "exact_repertoire": vr["exact"],
                "mismatched_nodes": vr["mismatched_nodes"], "nodes": [],
            }

            for k in range(n):
                n_nodes += 1
                true_ic = original.connected_inputs(k)
                rec = reports[k]
                conn_exact = rec.connected_inputs == true_ic
                if conn_exact:
                    n_conn_exact += 1

                # Gate function correctness: does the recovered reduced truth
                # table match the original's reduced truth table on the SAME
                # recovered inputs?  (verify() already guarantees repertoire
                # equivalence; this is an independent semantic cross-check.)
                true_tt = _reduced_truth_table_of_original(original, k) if conn_exact else None
                gate_ok = (true_tt is not None and rec.reduced_truth_table == true_tt)
                if gate_ok:
                    n_gate_function_correct += 1

                amb = len(rec.matches)
                ambiguity_hist[amb] = ambiguity_hist.get(amb, 0) + 1

                net_record["nodes"].append({
                    "node": k,
                    "true_gate": original.gates[k],
                    "true_params": original.params[k],
                    "true_connected": true_ic,
                    "recovered_connected": rec.connected_inputs,
                    "connectivity_exact": conn_exact,
                    "recovered_canonical": rec.canonical.as_dict(),
                    "ambiguity_class_size": amb,
                    "gate_function_correct": gate_ok,
                })
            records.append(net_record)

    summary = {
        "experiment": "exact_recovery",
        "sizes": list(sizes),
        "seeds_per_size": seeds_per_size,
        "n_networks": n_networks,
        "n_exact_repertoire": n_exact_repertoire,
        "exact_repertoire_rate": n_exact_repertoire / n_networks,
        "n_nodes": n_nodes,
        "connectivity_exact_rate": n_conn_exact / n_nodes,
        "gate_function_correct_rate": n_gate_function_correct / n_nodes,
        "ambiguity_histogram": ambiguity_hist,
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp02_exact_recovery_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    with open(os.path.join(RESULTS_DIR, "exp02_exact_recovery_records.json"), "w") as f:
        json.dump(records, f, indent=2)

    print("=== Experiment 2: exact recovery ===")
    print(f"networks                          : {n_networks}")
    print(f"exact repertoire reproduction     : {n_exact_repertoire}/{n_networks}"
          f" ({100 * summary['exact_repertoire_rate']:.2f}%)")
    print(f"connectivity recovered exactly    : {100 * summary['connectivity_exact_rate']:.2f}% of nodes")
    print(f"gate function recovered exactly   : {100 * summary['gate_function_correct_rate']:.2f}% of nodes")
    print(f"ambiguity class size histogram    : {dict(sorted(ambiguity_hist.items()))}")
    print(f"written: results/exp02_exact_recovery_summary.json (+ records)")
    return summary


if __name__ == "__main__":
    run()
