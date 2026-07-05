#!/usr/bin/env python3
"""
plot_th17_spectra.py

Reproduce Fig 5B-D from Zenil et al. iScience 2019:
  Three panels showing BDM perturbation spectra (delta distributions)
  for EarlyNet, IntermediateNet, FinalNet of Th17 differentiation.

Each panel: histogram of delta values coloured by classification
(positive=blue, negative=red, neutral=grey).

Output: plots/th17/th17_spectra.pdf + .png
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

# Use the best-matching spectra for each network
FILES = {
    "EarlyNet": "EarlyNet_in_degree_desc_node_spectra.csv",
    "IntermediateNet": "IntermediateNet_node_spectra.csv",
    "FinalNet": "FinalNet_node_spectra.csv",
}

COLOURS = {"positive": "#2166ac", "negative": "#b2182b", "neutral": "#999999"}
LABELS = {
    "EarlyNet": "EarlyNet (578 nodes)",
    "IntermediateNet": "IntermediateNet (1027 nodes)",
    "FinalNet": "FinalNet (1107 nodes)",
}

fig, axes = plt.subplots(1, 3, figsize=(14, 4), sharey=False)

for ax, (net, fname) in zip(axes, FILES.items()):
    df = pd.read_csv(os.path.join(data_dir, fname))

    for cls in ["positive", "negative", "neutral"]:
        subset = df[df["classification"] == cls]["delta"]
        if len(subset) == 0:
            continue
        ax.hist(subset, bins=50, alpha=0.7, color=COLOURS[cls],
                label=f"{cls} ({len(subset)})", edgecolor="none")

    ax.axvline(x=0, color="black", linewidth=0.8, linestyle="--", alpha=0.5)
    ax.set_xlabel("$\\Delta C$ (BDM perturbation)", fontsize=10)
    ax.set_title(LABELS[net], fontsize=10, fontweight="bold")
    ax.legend(fontsize=7, loc="upper right")

axes[0].set_ylabel("Count", fontsize=10)

fig.suptitle("Th17 Differentiation: BDM Perturbation Spectra\n"
             "(Zenil et al. 2019, Fig. 5B-D reproduction)", fontsize=11)
plt.tight_layout()

for ext in ("pdf", "png"):
    out = os.path.join(plots_dir, f"th17_spectra.{ext}")
    plt.savefig(out, dpi=200, bbox_inches="tight")
    print(f"Saved: {out}")

# Print summary statistics
for net, fname in FILES.items():
    df = pd.read_csv(os.path.join(data_dir, fname))
    pos = (df["classification"] == "positive").sum()
    neg = (df["classification"] == "negative").sum()
    neu = (df["classification"] == "neutral").sum()
    pr = pos / (pos + neg) if (pos + neg) > 0 else 0
    print(f"{net}: pos={pos} neg={neg} neu={neu} Pr={pr:.3f}")
