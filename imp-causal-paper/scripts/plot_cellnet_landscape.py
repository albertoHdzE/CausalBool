#!/usr/bin/env python3
"""
plot_cellnet_landscape.py

Reproduce the CellNet Waddington landscape from Zenil et al. Fig. 6g:
  x-axis: BDM complexity C(G)  (algorithmic complexity)
  y-axis: relative reprogrammability Pr(G)

Cell types with full perturbation (≤600 nodes) are plotted with labels.
Large networks without perturbation are marked with open circles and
complexity only (no y-position).

Output: plots/cellnet/cellnet_landscape.pdf + .png
"""
import os
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
summary_file = os.path.join(project_root, "data", "processed", "cellnet",
                            "cellnet_complexity_summary.csv")
plots_dir = os.path.join(project_root, "plots", "cellnet")
os.makedirs(plots_dir, exist_ok=True)

df = pd.read_csv(summary_file)
computed = df[df["perturbation_status"] == "computed"].copy()
skipped  = df[df["perturbation_status"].str.startswith("skipped")].copy()

# Broad cell lineage groupings for colour
LINEAGE = {
    "lung":              ("Epithelial/stromal",  "#1f77b4"),
    "intestine_colon":   ("Epithelial/stromal",  "#1f77b4"),
    "kidney":            ("Epithelial/stromal",  "#1f77b4"),
    "fibroblast":        ("Epithelial/stromal",  "#1f77b4"),
    "endothelial_cell":  ("Epithelial/stromal",  "#1f77b4"),
    "heart":             ("Muscle",              "#ff7f0e"),
    "skeletal_muscle":   ("Muscle",              "#ff7f0e"),
    "esc":               ("Stem",                "#2ca02c"),
    "hspc":              ("Stem",                "#2ca02c"),
    "b_cell":            ("Immune",              "#d62728"),
    "t_cell":            ("Immune",              "#d62728"),
    "monocyte_macrophage":("Immune",             "#d62728"),
    "liver":             ("Parenchymal",         "#9467bd"),
    "neuron":            ("Neural",              "#8c564b"),
}

fig, ax = plt.subplots(figsize=(9, 7))

# Plot fully-computed cell types
for _, row in computed.iterrows():
    ct = row["cell_type"]
    c  = LINEAGE.get(ct, ("Other", "#7f7f7f"))[1]
    ax.scatter(row["complexity_bdm"], row["relative_reprogrammability"],
               color=c, s=80, zorder=5)
    label = ct.replace("_", "\n")
    ax.annotate(label, (row["complexity_bdm"], row["relative_reprogrammability"]),
                fontsize=7, ha="center", va="bottom",
                xytext=(0, 6), textcoords="offset points")

# Plot large networks along bottom (Pr unknown) as open circles
if len(skipped) > 0:
    pr_min = computed["relative_reprogrammability"].min()
    y_placeholder = pr_min * 0.4
    for _, row in skipped.iterrows():
        ct = row["cell_type"]
        c  = LINEAGE.get(ct, ("Other", "#7f7f7f"))[1]
        ax.scatter(row["complexity_bdm"], y_placeholder,
                   color=c, s=80, marker="o", facecolors="none",
                   edgecolors=c, linewidths=1.5, zorder=5)
        label = ct.replace("_", "\n")
        ax.annotate(label, (row["complexity_bdm"], y_placeholder),
                    fontsize=7, ha="center", va="top",
                    xytext=(0, -8), textcoords="offset points", color="grey")
    ax.axhline(y=y_placeholder, color="grey", linestyle=":", linewidth=0.7,
               label="Large networks (Pr not computed)")

# Legend for lineages
lineage_handles = {}
for ct, (lin, col) in LINEAGE.items():
    if lin not in lineage_handles:
        lineage_handles[lin] = mpatches.Patch(color=col, label=lin)
legend1 = ax.legend(handles=list(lineage_handles.values()),
                    loc="upper left", fontsize=8, title="Cell lineage")
ax.add_artist(legend1)

ax.set_xlabel("BDM Complexity  C(G)  [bits]", fontsize=11)
ax.set_ylabel("Relative Reprogrammability  Pr(G)", fontsize=11)
ax.set_title("CellNet Waddington Landscape\n"
             "Algorithmic complexity vs reprogrammability across human cell types\n"
             "(Zenil et al. 2019, Fig. 6g reproduction)", fontsize=11)

plt.tight_layout()
for ext in ("pdf", "png"):
    out = os.path.join(plots_dir, f"cellnet_landscape.{ext}")
    plt.savefig(out, dpi=150, bbox_inches="tight")
    print(f"Saved: {out}")

print("\nCell types plotted (with reprogrammability):")
print(computed[["cell_type", "n_nodes", "complexity_bdm",
               "relative_reprogrammability"]].to_string(index=False))
if len(skipped) > 0:
    print(f"\nLarge networks (complexity only, no perturbation):")
    print(skipped[["cell_type", "n_nodes", "complexity_bdm"]].to_string(index=False))
