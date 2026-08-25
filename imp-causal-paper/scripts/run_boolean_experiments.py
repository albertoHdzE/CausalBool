#!/usr/bin/env python3
"""
run_boolean_experiments.py

Reproduce Fig 4 from Zenil et al. iScience 2019:
  - Fig 4A-C: MILS/MARPA moving K10 and ER graphs toward/away from randomness,
    tracking BDM complexity and edge-count sensitivity.
  - Fig 4E-G: Attractor count changes for complete, ER, and scale-free
    Boolean networks under edge perturbation.

Output: plots/boolean/fig4_*.pdf + .png
        data/processed/boolean/graph_complexity_sweep.csv
        data/processed/boolean/boolean_attractor_perturbation.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.complexity import BDMComplexityEstimator, adjacency_matrix
from imp_causal_paper.perturbation import GraphPerturbationAnalyzer
from imp_causal_paper.mils import MILSReducer
from imp_causal_paper.marpa import MARPABuilder
from imp_causal_paper.boolean_network import BooleanNetwork

import networkx as nx

data_dir = os.path.join(project_root, "data", "processed", "boolean")
plot_dir = os.path.join(project_root, "plots", "boolean")
os.makedirs(data_dir, exist_ok=True)
os.makedirs(plot_dir, exist_ok=True)

RNG = np.random.RandomState(42)


# --- Fig 4A-C: Graph complexity under MILS/MARPA ---

def graph_complexity_sweep():
    """Track complexity as MILS removes edges from K10, and MARPA adds edges."""
    estimator = BDMComplexityEstimator()
    reducer = MILSReducer(estimator)
    builder = MARPABuilder(estimator)

    rows = []

    # MILS: start from K10, remove edges one at a time
    print("MILS sweep from K10...")
    g = nx.complete_graph(10)
    mat = adjacency_matrix(g)
    base_c = estimator.matrix_complexity(mat)
    rows.append({"method": "MILS", "step": 0, "n_edges": g.number_of_edges(),
                 "complexity": base_c})

    current = g.copy()
    for step in range(1, min(36, current.number_of_edges())):
        # Greedy: remove edge causing largest complexity drop
        best_edge = None
        best_c = float("inf")
        for u, v in list(current.edges()):
            trial = current.copy()
            trial.remove_edge(u, v)
            if not nx.is_connected(trial):
                continue
            c = estimator.matrix_complexity(adjacency_matrix(trial))
            if c < best_c:
                best_c = c
                best_edge = (u, v)
        if best_edge is None:
            break
        current.remove_edge(*best_edge)
        rows.append({"method": "MILS", "step": step,
                     "n_edges": current.number_of_edges(), "complexity": best_c})
        if step % 5 == 0:
            print(f"  MILS step {step}: edges={current.number_of_edges()}, C={best_c:.1f}")

    # MARPA: start from sparse graph, add edges to maximise complexity
    print("MARPA sweep...")
    sparse = nx.path_graph(10)
    mat = adjacency_matrix(sparse)
    base_c = estimator.matrix_complexity(mat)
    rows.append({"method": "MARPA", "step": 0, "n_edges": sparse.number_of_edges(),
                 "complexity": base_c})

    current = sparse.copy()
    all_possible = set()
    for u in range(10):
        for v in range(u + 1, 10):
            all_possible.add((u, v))

    for step in range(1, 30):
        missing = all_possible - set(current.edges())
        if not missing:
            break
        best_edge = None
        best_c = -float("inf")
        for u, v in missing:
            trial = current.copy()
            trial.add_edge(u, v)
            c = estimator.matrix_complexity(adjacency_matrix(trial))
            if c > best_c:
                best_c = c
                best_edge = (u, v)
        current.add_edge(*best_edge)
        rows.append({"method": "MARPA", "step": step,
                     "n_edges": current.number_of_edges(), "complexity": best_c})
        if step % 5 == 0:
            print(f"  MARPA step {step}: edges={current.number_of_edges()}, C={best_c:.1f}")

    # ER baseline comparison
    print("ER baseline sweep...")
    for p_idx, p in enumerate(np.linspace(0.1, 1.0, 20)):
        for trial_i in range(5):
            g = nx.erdos_renyi_graph(10, p, seed=int(p_idx * 5 + trial_i + 100))
            if g.number_of_edges() == 0:
                continue
            c = estimator.matrix_complexity(adjacency_matrix(g))
            rows.append({"method": "ER", "step": p_idx,
                         "n_edges": g.number_of_edges(), "complexity": c})

    return pd.DataFrame(rows)


def plot_complexity_sweep(df):
    """Fig 4A-C: complexity vs edges for MILS, MARPA, ER."""
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))

    # Panel A: MILS trajectory
    mils = df[df["method"] == "MILS"]
    axes[0].plot(mils["n_edges"], mils["complexity"], "o-", color="#1f77b4", markersize=4)
    axes[0].set_xlabel("Number of edges", fontsize=10)
    axes[0].set_ylabel("BDM Complexity [bits]", fontsize=10)
    axes[0].set_title("MILS: K10 edge removal\n(toward simplicity)", fontsize=10)
    axes[0].invert_xaxis()

    # Panel B: MARPA trajectory
    marpa = df[df["method"] == "MARPA"]
    axes[1].plot(marpa["n_edges"], marpa["complexity"], "s-", color="#2ca02c", markersize=4)
    axes[1].set_xlabel("Number of edges", fontsize=10)
    axes[1].set_ylabel("BDM Complexity [bits]", fontsize=10)
    axes[1].set_title("MARPA: path graph edge addition\n(toward complexity)", fontsize=10)

    # Panel C: ER scatter
    er = df[df["method"] == "ER"]
    axes[2].scatter(er["n_edges"], er["complexity"], alpha=0.5, color="#d62728", s=20)
    axes[2].set_xlabel("Number of edges", fontsize=10)
    axes[2].set_ylabel("BDM Complexity [bits]", fontsize=10)
    axes[2].set_title("ER(10, p) random graphs\n(baseline)", fontsize=10)

    fig.suptitle("Graph Complexity Under Algorithmic Interventions\n"
                 "(Zenil et al. 2019, Fig. 4A-C reproduction)", fontsize=12, y=1.02)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig4ac_complexity_sweep.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig4ac_complexity_sweep")


# --- Fig 4E-G: Boolean network attractor perturbation ---

def boolean_attractor_sweep():
    """Attractor counts for complete, ER, and scale-free Boolean networks."""
    rows = []

    operators = ["and", "or", "xor"]
    # Small n to keep 2^n state space feasible
    n_nodes = 8

    # Complete graph
    print("Complete graph Boolean networks...")
    g = nx.complete_graph(n_nodes)
    dg = g.to_directed()
    for op in operators:
        bn = BooleanNetwork(dg, op)
        base_att = len(bn.attractors())
        # Perturb: remove each edge
        deltas = []
        for u, v in sorted(dg.edges()):
            pg = dg.copy()
            pg.remove_edge(u, v)
            try:
                pbn = BooleanNetwork(pg, op)
                att = len(pbn.attractors())
                deltas.append(att - base_att)
            except Exception:
                pass
        rows.append({
            "graph_type": "complete", "operator": op, "n_nodes": n_nodes,
            "n_edges": dg.number_of_edges(), "base_attractors": base_att,
            "mean_delta": np.mean(deltas) if deltas else 0,
            "std_delta": np.std(deltas) if deltas else 0,
            "max_delta": max(deltas) if deltas else 0,
            "min_delta": min(deltas) if deltas else 0,
        })
        print(f"  Complete/{op}: {base_att} attractors, mean_delta={np.mean(deltas):.2f}")

    # ER graphs
    print("ER graph Boolean networks...")
    for p in [0.2, 0.4, 0.6, 0.8]:
        for seed in range(5):
            g = nx.erdos_renyi_graph(n_nodes, p, seed=seed + 200, directed=True)
            if g.number_of_edges() < n_nodes:
                continue
            for op in operators:
                bn = BooleanNetwork(g, op)
                base_att = len(bn.attractors())
                deltas = []
                edges = sorted(g.edges())
                # Sample up to 30 edges for speed
                sample = edges[:30] if len(edges) > 30 else edges
                for u, v in sample:
                    pg = g.copy()
                    pg.remove_edge(u, v)
                    pbn = BooleanNetwork(pg, op)
                    att = len(pbn.attractors())
                    deltas.append(att - base_att)
                rows.append({
                    "graph_type": f"ER_p{p}", "operator": op, "n_nodes": n_nodes,
                    "n_edges": g.number_of_edges(), "base_attractors": base_att,
                    "mean_delta": np.mean(deltas), "std_delta": np.std(deltas),
                    "max_delta": max(deltas), "min_delta": min(deltas),
                })

    # Scale-free
    print("Scale-free Boolean networks...")
    for m in [1, 2, 3]:
        for seed in range(5):
            g = nx.barabasi_albert_graph(n_nodes, m, seed=seed + 300)
            dg = g.to_directed()
            for op in operators:
                bn = BooleanNetwork(dg, op)
                base_att = len(bn.attractors())
                deltas = []
                edges = sorted(dg.edges())
                sample = edges[:30] if len(edges) > 30 else edges
                for u, v in sample:
                    pg = dg.copy()
                    pg.remove_edge(u, v)
                    pbn = BooleanNetwork(pg, op)
                    att = len(pbn.attractors())
                    deltas.append(att - base_att)
                rows.append({
                    "graph_type": f"SF_m{m}", "operator": op, "n_nodes": n_nodes,
                    "n_edges": dg.number_of_edges(), "base_attractors": base_att,
                    "mean_delta": np.mean(deltas), "std_delta": np.std(deltas),
                    "max_delta": max(deltas), "min_delta": min(deltas),
                })

    return pd.DataFrame(rows)


def plot_attractor_sweep(df):
    """Fig 4E-G: attractor perturbation by graph type and operator."""
    graph_types = ["complete", "ER_p0.4", "SF_m2"]
    type_labels = ["Complete K8", "ER(8, 0.4)", "BA(8, m=2)"]

    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    colours = {"and": "#1f77b4", "or": "#ff7f0e", "xor": "#2ca02c"}

    for ax, gt, label in zip(axes, graph_types, type_labels):
        subset = df[df["graph_type"] == gt]
        x = np.arange(len(subset))
        width = 0.25
        for i, op in enumerate(["and", "or", "xor"]):
            op_data = subset[subset["operator"] == op]
            if len(op_data) == 0:
                continue
            ax.bar(x[:len(op_data)] + i * width, op_data["base_attractors"].values,
                   width, label=op.upper(), color=colours[op], alpha=0.8)
        ax.set_title(f"{label}\nAttractor counts", fontsize=10)
        ax.set_xlabel("Instance", fontsize=9)
        ax.set_ylabel("Attractor count", fontsize=9)
        ax.legend(fontsize=8)

    fig.suptitle("Boolean Network Attractor Counts Under Edge Perturbation\n"
                 "(Zenil et al. 2019, Fig. 4E-G reproduction)", fontsize=12, y=1.02)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig4eg_attractor_perturbation.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig4eg_attractor_perturbation")

    # Also plot mean delta by graph type
    fig2, ax2 = plt.subplots(figsize=(10, 5))
    grouped = df.groupby(["graph_type", "operator"])["mean_delta"].mean().reset_index()
    for op in ["and", "or", "xor"]:
        sub = grouped[grouped["operator"] == op]
        ax2.bar(sub["graph_type"] + f"\n({op})", sub["mean_delta"],
                color=colours[op], alpha=0.8, label=op.upper())
    ax2.axhline(0, color="black", linewidth=0.5)
    ax2.set_ylabel("Mean $\\Delta$ attractor count", fontsize=10)
    ax2.set_title("Mean Attractor Change Under Single-Edge Removal", fontsize=11)
    ax2.legend()
    plt.xticks(rotation=45, ha="right", fontsize=7)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig2.savefig(os.path.join(plot_dir, f"fig4_mean_delta_attractors.{ext}"),
                     dpi=200, bbox_inches="tight")
    plt.close(fig2)
    print("Saved fig4_mean_delta_attractors")


if __name__ == "__main__":
    print("=== Fig 4A-C: Graph complexity sweep ===")
    sweep_df = graph_complexity_sweep()
    sweep_df.to_csv(os.path.join(data_dir, "graph_complexity_sweep.csv"), index=False)
    plot_complexity_sweep(sweep_df)

    print("\n=== Fig 4E-G: Boolean attractor perturbation ===")
    att_df = boolean_attractor_sweep()
    att_df.to_csv(os.path.join(data_dir, "boolean_attractor_perturbation.csv"), index=False)
    plot_attractor_sweep(att_df)

    print("\nDone.")
