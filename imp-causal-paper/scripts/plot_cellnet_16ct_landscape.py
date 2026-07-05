#!/usr/bin/env python3
"""
plot_cellnet_16ct_landscape.py

Reproduce Fig 5G Waddington landscape from Zenil et al. iScience 2019:
  x-axis: Normalised complexity C(G)/max(C)
  y-axis: Combined reprogrammability sqrt(Pr² + PA²)

Uses 16 cell types from Oct 2016 cnProc:
  - 14 types that match the paper (reproduction)
  - 2 novel types (monocyte, dendritic_cell) as independent validation

Output: plots/cellnet/cellnet_16ct_landscape.pdf + .png
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
data_file = os.path.join(project_root, "data", "processed", "cellnet_16ct",
                         "cellnet_landscape_data.csv")
plot_dir = os.path.join(project_root, "plots", "cellnet")
os.makedirs(plot_dir, exist_ok=True)

df = pd.read_csv(data_file)

# Lineage colour mapping
LINEAGE = {
    "lung":              ("Epithelial/stromal", "#1f77b4"),
    "intestine_colon":   ("Epithelial/stromal", "#1f77b4"),
    "kidney":            ("Epithelial/stromal", "#1f77b4"),
    "fibroblast":        ("Epithelial/stromal", "#1f77b4"),
    "endothelial_cell":  ("Epithelial/stromal", "#1f77b4"),
    "heart":             ("Muscle",             "#ff7f0e"),
    "skeletal_muscle":   ("Muscle",             "#ff7f0e"),
    "esc":               ("Stem",               "#2ca02c"),
    "hspc":              ("Stem",               "#2ca02c"),
    "b_cell":            ("Immune",             "#d62728"),
    "t_cell":            ("Immune",             "#d62728"),
    "macrophage":        ("Immune",             "#d62728"),
    "liver":             ("Parenchymal",        "#9467bd"),
    "neuron":            ("Neural",             "#8c564b"),
    # Validation types (novel)
    "monocyte":          ("Immune (novel)",     "#e377c2"),
    "dendritic_cell":    ("Immune (novel)",     "#e377c2"),
}

# Which types are validation (novel)
VALIDATION_TYPES = {"monocyte", "dendritic_cell"}

fig, ax = plt.subplots(figsize=(10, 8))

for _, row in df.iterrows():
    ct = row["cell_type"]
    lineage_name, colour = LINEAGE.get(ct, ("Other", "#7f7f7f"))
    is_validation = ct in VALIDATION_TYPES

    marker = "D" if is_validation else "o"
    edge_col = "black" if is_validation else colour
    size = 120 if is_validation else 80

    ax.scatter(row["normalised_complexity"], row["combined_reprogrammability"],
               color=colour, s=size, marker=marker, edgecolors=edge_col,
               linewidths=1.5 if is_validation else 0.5, zorder=5)

    label = ct.replace("_", " ")
    fontweight = "bold" if is_validation else "normal"
    ax.annotate(label,
                (row["normalised_complexity"], row["combined_reprogrammability"]),
                fontsize=7, ha="center", va="bottom",
                xytext=(0, 7), textcoords="offset points",
                fontweight=fontweight)

# Legend for lineages
seen = {}
for ct, (lin, col) in LINEAGE.items():
    if lin not in seen:
        seen[lin] = col
handles = [mpatches.Patch(color=col, label=lin) for lin, col in seen.items()]
legend1 = ax.legend(handles=handles, loc="upper left", fontsize=8,
                    title="Cell lineage", title_fontsize=9)
ax.add_artist(legend1)

# Marker legend
from matplotlib.lines import Line2D
marker_handles = [
    Line2D([0], [0], marker="o", color="w", markerfacecolor="grey",
           markersize=8, label="Paper types (14)"),
    Line2D([0], [0], marker="D", color="w", markerfacecolor="grey",
           markeredgecolor="black", markersize=8, label="Validation types (2)"),
]
ax.legend(handles=marker_handles, loc="lower right", fontsize=8)

ax.set_xlabel("Normalised BDM Complexity  $C(G)/\\max(C)$", fontsize=11)
ax.set_ylabel("Combined Reprogrammability  $\\sqrt{Pr^2 + PA^2}$", fontsize=11)
ax.set_title("CellNet Waddington Landscape (16 cell types)\n"
             "Algorithmic complexity vs combined reprogrammability\n"
             "(Zenil et al. 2019, Fig. 5G reproduction + validation)",
             fontsize=11)

plt.tight_layout()
for ext in ("pdf", "png"):
    out = os.path.join(plot_dir, f"cellnet_16ct_landscape.{ext}")
    plt.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")

print(f"\n{len(df)} cell types plotted:")
print(df[["cell_type", "n_nodes", "normalised_complexity",
          "combined_reprogrammability"]].to_string(index=False))
