#!/usr/bin/env python3
"""
run_ca_reconstruction.py — Reproduce Fig 3A-B from Zenil et al. iScience 2019.

Panel A: Brute-force minimum-BDM reconstruction (9 rows = 9! permutations)
Panel B: Rule-inference + forward chaining (scales to any number of rows)
"""
import os, sys
import numpy as np
from scipy import stats
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import ListedColormap

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(project_root, "src"))

from imp_causal_paper.causal_reconstruction import (
    evolve_elementary_ca,
    reconstruct_min_complexity,
    reconstruct_by_rule_inference,
)
from imp_causal_paper.complexity import BDMComplexityEstimator

plot_dir = os.path.join(project_root, "plots", "ca")
os.makedirs(plot_dir, exist_ok=True)
BW = ListedColormap(["white", "black"])
RULES = [254, 57, 11, 50, 9, 54, 75, 73, 45, 30]


def make_initial(width):
    ic = np.zeros(width, dtype=int)
    ic[width // 2] = 1
    return ic


def spearman_for_reconstruction(perm, inferred_order, n):
    """Compute Spearman rho between true and inferred temporal positions."""
    true_pos = perm.copy()
    inf_pos = np.zeros(n, dtype=int)
    for rank, idx in enumerate(inferred_order):
        inf_pos[idx] = rank
    return stats.spearmanr(true_pos, inf_pos)


def plot_panel(panel, rules, estimator):
    """Generate Panel A (brute-force) or Panel B (rule inference)."""
    if panel == "A":
        width, steps = 21, 9  # 9 rows → 9! = 362,880
    else:
        width, steps = 41, 21

    fig, axes = plt.subplots(5, 4, figsize=(16, 20))
    for idx, rule in enumerate(rules):
        row = idx // 2
        col_base = (idx % 2) * 2

        initial = make_initial(width)
        original = evolve_elementary_ca(initial, rule=rule, steps=steps)
        n = original.shape[0]

        rng = np.random.RandomState(42 + rule)
        perm = rng.permutation(n)
        scrambled = original[perm]

        if panel == "A":
            result = reconstruct_min_complexity(scrambled, estimator)
        else:
            result = reconstruct_by_rule_inference(scrambled, estimator)

        rho, p = spearman_for_reconstruction(perm, list(result.permutation), n)

        axes[row, col_base].imshow(original, cmap=BW, interpolation="nearest", aspect="auto")
        axes[row, col_base].set_title(f"Rule {rule}", fontsize=9, fontweight="bold")
        axes[row, col_base].set_ylabel("original", fontsize=8)
        axes[row, col_base].set_xticks([]); axes[row, col_base].set_yticks([])

        label = "reconstructed" if panel == "A" else "δBDM ranking"
        axes[row, col_base + 1].imshow(result.ordered_rows, cmap=BW, interpolation="nearest", aspect="auto")
        axes[row, col_base + 1].set_title(f"\u03c1 = {rho:.3f}  p = {p:.2g}", fontsize=8)
        axes[row, col_base + 1].set_ylabel(label, fontsize=8)
        axes[row, col_base + 1].set_xticks([]); axes[row, col_base + 1].set_yticks([])

        print(f"  Rule {rule:3d}: \u03c1={rho:+.3f}, p={p:.2g}, rule_inferred={result.inferred_rule}, matches={result.transition_matches}/{n-1}")

    title = ("Fig 3A: Min-BDM Reconstruction (9 rows, brute-force 9!)"
             if panel == "A" else
             "Fig 3B: Row-Perturbation Ranking (21 rows)")
    fig.suptitle(title, fontsize=14, y=1.01)
    plt.tight_layout()
    for ext in ("pdf", "png"):
        fig.savefig(os.path.join(plot_dir, f"fig3{panel.lower()}_reconstruction.{ext}"),
                    dpi=200, bbox_inches="tight")
    plt.close(fig)
    print(f"Saved fig3{panel.lower()}_reconstruction")


if __name__ == "__main__":
    estimator = BDMComplexityEstimator()

    print("=== Panel A: Brute-force min-BDM (9 rows) ===")
    plot_panel("A", RULES, estimator)

    print("\n=== Panel B: Row-perturbation ranking (21 rows) ===")
    plot_panel("B", RULES, estimator)

    print("\nDone.")
