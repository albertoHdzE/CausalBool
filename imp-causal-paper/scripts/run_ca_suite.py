#!/usr/bin/env python3
"""
run_ca_suite.py

Reproduce Fig 3 from Zenil et al. iScience 2019:
  - Fig 3A: BDM complexity of all 256 ECA rules (sensitivity landscape)
  - Fig 3B: 12+ selected rules across Wolfram classes (I–IV), space-time diagrams
  - Fig 3C: Double-row perturbation analysis (row deletion effect on BDM)

Output: plots/ca/fig3_*.pdf + .png
        data/processed/ca/eca_256_complexity.csv
        data/processed/ca/eca_selected_perturbation.csv
"""
import os
import sys
import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.causal_reconstruction import evolve_elementary_ca
from imp_causal_paper.complexity import BDMComplexityEstimator

data_dir = os.path.join(project_root, "data", "processed", "ca")
plot_dir = os.path.join(project_root, "plots", "ca")
os.makedirs(data_dir, exist_ok=True)
os.makedirs(plot_dir, exist_ok=True)

# Wolfram class assignments for selected rules
WOLFRAM_CLASS = {
    # Class I (homogeneous)
    0: "I", 32: "I", 160: "I", 255: "I",
    # Class II (periodic)
    4: "II", 108: "II", 218: "II", 232: "II",
    # Class III (chaotic)
    18: "III", 30: "III", 45: "III", 90: "III", 150: "III",
    # Class IV (complex)
    54: "IV", 110: "IV", 106: "IV",
}

CLASS_COLOURS = {"I": "#1f77b4", "II": "#ff7f0e", "III": "#d62728", "IV": "#2ca02c"}

# Standard initial condition: single 1 in centre of width-101
WIDTH = 101
STEPS = 80
initial = np.zeros(WIDTH, dtype=int)
initial[WIDTH // 2] = 1


def compute_all_256():
    """Compute BDM complexity for all 256 ECA rules."""
    estimator = BDMComplexityEstimator()
    rows = []
    for rule in range(256):
        evo = evolve_elementary_ca(initial, rule=rule, steps=STEPS)
        bdm = estimator.matrix_complexity(evo)
        wclass = WOLFRAM_CLASS.get(rule, "unclassified")
        rows.append({"rule": rule, "bdm_complexity": bdm, "wolfram_class": wclass})
        if rule % 50 == 0:
            print(f"  Rule {rule}/255 done")
    return pd.DataFrame(rows)


def plot_256_landscape(df):
    """Fig 3A: bar chart of BDM for all 256 rules, coloured by Wolfram class."""
    fig, ax = plt.subplots(figsize=(14, 5))

    colours = []
    for _, row in df.iterrows():
        wc = row["wolfram_class"]
        colours.append(CLASS_COLOURS.get(wc, "#cccccc"))

    ax.bar(df["rule"], df["bdm_complexity"], color=colours, width=1.0, edgecolor="none")
    ax.set_xlabel("ECA Rule Number", fontsize=11)
    ax.set_ylabel("BDM Complexity [bits]", fontsize=11)
    ax.set_title("BDM Complexity of All 256 Elementary Cellular Automata\n"
                 "(Zenil et al. 2019, Fig. 3A reproduction)", fontsize=11)

    # Legend
    import matplotlib.patches as mpatches
    handles = [mpatches.Patch(color=CLASS_COLOURS[c], label=f"Class {c}")
               for c in ["I", "II", "III", "IV"]]
    handles.append(mpatches.Patch(color="#cccccc", label="Unclassified"))
    ax.legend(handles=handles, loc="upper left", fontsize=8)

    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig3a_eca_256_complexity.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig3a_eca_256_complexity")


def plot_selected_spacetime():
    """Fig 3B: space-time diagrams for 12 selected rules."""
    selected = sorted(WOLFRAM_CLASS.keys())
    n = len(selected)
    cols = 4
    rows_grid = (n + cols - 1) // cols
    bw_cmap = ListedColormap(["white", "black"])

    fig, axes = plt.subplots(rows_grid, cols, figsize=(16, rows_grid * 3))
    axes = axes.flatten()

    for i, rule in enumerate(selected):
        evo = evolve_elementary_ca(initial, rule=rule, steps=STEPS)
        wc = WOLFRAM_CLASS[rule]
        axes[i].imshow(evo, cmap=bw_cmap, interpolation="nearest", aspect="auto")
        axes[i].set_title(f"Rule {rule} (Class {wc})", fontsize=9,
                          color=CLASS_COLOURS[wc], fontweight="bold")
        axes[i].set_xticks([])
        axes[i].set_yticks([])

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Selected ECA Space-Time Diagrams\n"
                 "(Zenil et al. 2019, Fig. 3B reproduction)", fontsize=12)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig3b_spacetime_selected.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig3b_spacetime_selected")


def compute_row_perturbation():
    """Fig 3C: row-deletion perturbation for selected rules."""
    estimator = BDMComplexityEstimator()
    selected = sorted(WOLFRAM_CLASS.keys())
    all_rows = []

    for rule in selected:
        evo = evolve_elementary_ca(initial, rule=rule, steps=STEPS)
        base_bdm = estimator.matrix_complexity(evo)
        deltas = []
        for row_idx in range(evo.shape[0]):
            reduced = np.delete(evo, row_idx, axis=0)
            delta = base_bdm - estimator.matrix_complexity(reduced)
            deltas.append(delta)
            all_rows.append({
                "rule": rule, "wolfram_class": WOLFRAM_CLASS[rule],
                "row_index": row_idx, "delta_bdm": delta,
                "base_bdm": base_bdm,
            })

    return pd.DataFrame(all_rows)


def plot_row_perturbation(pert_df):
    """Fig 3C: row perturbation profiles for selected rules."""
    selected = sorted(pert_df["rule"].unique())
    n = len(selected)
    cols = 4
    rows_grid = (n + cols - 1) // cols

    fig, axes = plt.subplots(rows_grid, cols, figsize=(16, rows_grid * 3))
    axes = axes.flatten()

    for i, rule in enumerate(selected):
        subset = pert_df[pert_df["rule"] == rule]
        wc = subset["wolfram_class"].iloc[0]
        colour = CLASS_COLOURS[wc]
        axes[i].bar(subset["row_index"], subset["delta_bdm"],
                    color=colour, width=1.0, edgecolor="none", alpha=0.8)
        axes[i].axhline(0, color="black", linewidth=0.5)
        axes[i].set_title(f"Rule {rule} (Class {wc})", fontsize=9,
                          color=colour, fontweight="bold")
        axes[i].set_xlabel("Row", fontsize=7)
        axes[i].set_ylabel("$\\Delta$BDM", fontsize=7)

    for j in range(i + 1, len(axes)):
        axes[j].set_visible(False)

    fig.suptitle("Row-Deletion Perturbation Profiles\n"
                 "(Zenil et al. 2019, Fig. 3C reproduction)", fontsize=12)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig3c_row_perturbation.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print("Saved fig3c_row_perturbation")


if __name__ == "__main__":
    print("=== Fig 3A: All 256 ECA rules complexity ===")
    df256 = compute_all_256()
    df256.to_csv(os.path.join(data_dir, "eca_256_complexity.csv"), index=False)
    plot_256_landscape(df256)

    print("\n=== Fig 3B: Selected space-time diagrams ===")
    plot_selected_spacetime()

    print("\n=== Fig 3C: Row perturbation analysis ===")
    pert_df = compute_row_perturbation()
    pert_df.to_csv(os.path.join(data_dir, "eca_selected_perturbation.csv"), index=False)
    plot_row_perturbation(pert_df)

    print("\nDone. Summary of Class vs Complexity:")
    summary = df256.groupby("wolfram_class")["bdm_complexity"].agg(["mean", "std", "count"])
    print(summary)
