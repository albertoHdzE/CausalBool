"""Reproduce Figure 4D: phase transition in BDM perturbation sign vs edge density.

Uses the pre-parsed mmc8_classification_by_edges.csv (authors' own deltas from
Data S7 of Zenil et al. iScience 2019). For each edge count (4–20) in the
exhaustive 5-node directed graph corpus, computes the fraction of node-level
BDM perturbation deltas that are positive, neutral, and negative.

The paper's Figure 4D shows the transition from positive-dominant behaviour at
low edge density to negative-dominant at ~12–13 edges (threshold = log2(5)).

Usage:
    .venv/bin/python scripts/figure4d_mmc8.py
"""
from __future__ import annotations

import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[1]
DATA_FILE = PROJECT_ROOT / "data" / "processed" / "boolean_exhaustive" / "mmc8_classification_by_edges.csv"
OUTPUT_DIR = PROJECT_ROOT / "data" / "processed" / "boolean_exhaustive"
PLOT_DIR = PROJECT_ROOT / "plots" / "boolean_exhaustive"


def main() -> None:
    PLOT_DIR.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(DATA_FILE)
    df = df.sort_values("num_edges").reset_index(drop=True)

    # Fractions
    df["frac_positive"] = df["positive"] / df["total_nodes"]
    df["frac_neutral"] = df["neutral"] / df["total_nodes"]
    df["frac_negative"] = df["negative"] / df["total_nodes"]

    edges = df["num_edges"].to_numpy()
    frac_pos = df["frac_positive"].to_numpy()
    frac_neu = df["frac_neutral"].to_numpy()
    frac_neg = df["frac_negative"].to_numpy()

    # Phase-transition crossover: first edge count where negative >= positive
    crossover = None
    for i, e in enumerate(edges):
        if frac_neg[i] >= frac_pos[i]:
            crossover = int(e)
            break

    print(f"Phase-transition crossover (neg >= pos): {crossover} edges")
    print(f"\nEdge | %pos   | %neu   | %neg")
    print(f"-----+--------+--------+--------")
    for _, row in df.iterrows():
        print(
            f"  {int(row['num_edges']):2d} | {row['frac_positive']*100:5.1f}% | "
            f"{row['frac_neutral']*100:5.1f}% | {row['frac_negative']*100:5.1f}%"
        )

    # ── Figure 4D ──────────────────────────────────────────────────────────────
    fig, ax = plt.subplots(figsize=(7, 4.5))

    ax.plot(edges, frac_pos * 100, "o-", color="#2176AE", linewidth=1.8,
            markersize=5, label="Positive (delta > log₂5)")
    ax.plot(edges, frac_neu * 100, "s--", color="#888888", linewidth=1.4,
            markersize=4, label="Neutral")
    ax.plot(edges, frac_neg * 100, "^-", color="#C1292E", linewidth=1.8,
            markersize=5, label="Negative (delta < −log₂5)")

    if crossover is not None:
        ax.axvline(crossover, color="#C1292E", linewidth=0.9, linestyle=":",
                   alpha=0.7, label=f"Crossover at {crossover} edges")

    ax.set_xlabel("Number of edges (5-node directed graph)", fontsize=11)
    ax.set_ylabel("Fraction of nodes (%)", fontsize=11)
    ax.set_title("Figure 4D — BDM perturbation sign vs edge density\n"
                 "(exhaustive 5-node directed graphs, n = 9364, authors' deltas)",
                 fontsize=10)
    ax.set_xticks(edges)
    ax.set_xlim(edges[0] - 0.5, edges[-1] + 0.5)
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9, loc="upper left")
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()

    plot_path = PLOT_DIR / "figure4d_mmc8_phase_transition.pdf"
    fig.savefig(plot_path, dpi=150)
    png_path = PLOT_DIR / "figure4d_mmc8_phase_transition.png"
    fig.savefig(png_path, dpi=150)
    plt.close(fig)
    print(f"\nSaved: {plot_path.name}")
    print(f"Saved: {png_path.name}")

    # ── Stacked area version (alternative representation) ─────────────────────
    fig2, ax2 = plt.subplots(figsize=(7, 4.5))
    ax2.stackplot(
        edges,
        frac_pos * 100,
        frac_neu * 100,
        frac_neg * 100,
        labels=["Positive", "Neutral", "Negative"],
        colors=["#2176AE", "#CCCCCC", "#C1292E"],
        alpha=0.85,
    )
    if crossover is not None:
        ax2.axvline(crossover, color="black", linewidth=1.0, linestyle=":",
                    label=f"Crossover at {crossover} edges")
    ax2.set_xlabel("Number of edges", fontsize=11)
    ax2.set_ylabel("Fraction of nodes (%)", fontsize=11)
    ax2.set_title("Figure 4D (stacked) — BDM perturbation sign vs edge density",
                  fontsize=10)
    ax2.set_xticks(edges)
    ax2.set_xlim(edges[0] - 0.5, edges[-1] + 0.5)
    ax2.set_ylim(0, 100)
    ax2.legend(fontsize=9, loc="upper left")
    fig2.tight_layout()
    stacked_path = PLOT_DIR / "figure4d_mmc8_stacked.png"
    fig2.savefig(stacked_path, dpi=150)
    plt.close(fig2)
    print(f"Saved: {stacked_path.name}")

    # ── Summary JSON ──────────────────────────────────────────────────────────
    result = {
        "source": "mmc8.csv (iScience 2019 Data S7) — authors' BDM deltas",
        "total_graphs": 9364,
        "nodes_per_graph": 5,
        "threshold": float(np.log2(5)),
        "crossover_edge_count": crossover,
        "interpretation": (
            "Below the crossover, positive nodes dominate (removing a node "
            "reduces BDM — the node carries causal information). Above it, "
            "negative nodes dominate (removing a node increases BDM — the "
            "node suppresses complexity). The crossover marks the algorithmic "
            "phase transition from ordered to random-like dynamics."
        ),
        "per_edge_fractions": [
            {
                "num_edges": int(row["num_edges"]),
                "graphs": int(row["total_nodes"] // 5),
                "frac_positive": round(float(row["frac_positive"]), 4),
                "frac_neutral": round(float(row["frac_neutral"]), 4),
                "frac_negative": round(float(row["frac_negative"]), 4),
            }
            for _, row in df.iterrows()
        ],
    }
    summary_path = OUTPUT_DIR / "figure4d_summary.json"
    with open(summary_path, "w") as f:
        json.dump(result, f, indent=2)
    print(f"Saved: {summary_path.name}")
    print(f"\nCrossover edge count: {crossover} (positive → negative dominance)")


if __name__ == "__main__":
    main()
