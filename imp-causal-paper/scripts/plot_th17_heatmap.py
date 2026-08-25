#!/usr/bin/env python3
"""
plot_th17_heatmap.py

Reproduce Fig 5F from Zenil et al. iScience 2019:
  Heatmap of normalised BDM perturbation (delta) values for genes
  across the three Th17 time points (EarlyNet, IntermediateNet, FinalNet).

Shows top genes by absolute delta, normalised per-network.

Output: plots/th17/th17_gene_heatmap.pdf + .png
"""
import os
import sys
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
data_dir = os.path.join(project_root, "data", "processed", "th17", "yosef_perturbation")
plots_dir = os.path.join(project_root, "plots", "th17")
os.makedirs(plots_dir, exist_ok=True)

FILES = {
    "EarlyNet": "EarlyNet_in_degree_desc_node_spectra.csv",
    "IntermediateNet": "IntermediateNet_node_spectra.csv",
    "FinalNet": "FinalNet_node_spectra.csv",
}

# Load and merge
dfs = {}
for net, fname in FILES.items():
    df = pd.read_csv(os.path.join(data_dir, fname))
    # Normalise delta to [-1, 1] range per network
    max_abs = df["delta"].abs().max()
    df["delta_norm"] = df["delta"] / max_abs if max_abs > 0 else 0
    dfs[net] = df.set_index("element")[["delta_norm", "delta", "classification"]]

# Find genes present in all three networks
common_genes = set(dfs["EarlyNet"].index)
for net in ["IntermediateNet", "FinalNet"]:
    common_genes &= set(dfs[net].index)

print(f"Common genes across all 3 networks: {len(common_genes)}")

# Build matrix
matrix = pd.DataFrame(index=sorted(common_genes))
for net in FILES:
    matrix[net] = dfs[net].loc[matrix.index, "delta_norm"]

# Select top genes by max absolute delta across networks
matrix["max_abs"] = matrix[list(FILES.keys())].abs().max(axis=1)
top_n = 40
top_genes = matrix.nlargest(top_n, "max_abs").index
heatmap_data = matrix.loc[top_genes, list(FILES.keys())]

# Plot
fig, ax = plt.subplots(figsize=(6, 12))
im = ax.imshow(heatmap_data.values, cmap="RdBu_r", aspect="auto",
               vmin=-1, vmax=1, interpolation="nearest")

ax.set_xticks(range(len(FILES)))
ax.set_xticklabels(list(FILES.keys()), fontsize=9, rotation=30, ha="right")
ax.set_yticks(range(len(top_genes)))
ax.set_yticklabels(top_genes, fontsize=6)

cbar = plt.colorbar(im, ax=ax, shrink=0.5, pad=0.02)
cbar.set_label("Normalised $\\Delta C$", fontsize=9)

ax.set_title(f"Top {top_n} genes by BDM perturbation\nacross Th17 differentiation time points\n"
             "(Zenil et al. 2019, Fig. 5F reproduction)", fontsize=10)

plt.tight_layout()
for ext in ("pdf", "png"):
    out = os.path.join(plots_dir, f"th17_gene_heatmap.{ext}")
    plt.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")
