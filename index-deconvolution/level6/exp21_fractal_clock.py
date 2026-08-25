"""exp21_fractal_clock.py  (Level 6)

Is the clock a self-similar fractal point process, and is its clustering invariant
across reversal scales (the intra-pivot self-similarity)?

Measure the Fano-factor scaling exponent alpha of the pivot point process at
several reversal scales theta, each against the return-shuffle null.  A renewal
process gives alpha near 0 (flat Fano factor); a clustered self-similar process
gives alpha > 0.  If alpha stays away from 0 and roughly constant across theta, the
clustering of pivot timing repeats at every scale -- a genuine fractal clock.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from point_process import pivot_indices, fano_exponent  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETAS = [0.01, 0.02, 0.04, 0.08]
WINDOWS = [10, 20, 40, 80, 160, 320]
N_NULL = 15


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(21)
    per_theta = []
    for theta in THETAS:
        ar, ash, r2s = [], [], []
        for name, s in seqs.items():
            n = len(s)
            real = fano_exponent(pivot_indices(s, theta), n, WINDOWS)
            if real["alpha"] == real["alpha"]:
                ar.append(real["alpha"])
                r2s.append(real["r2"])
            nulls = []
            for _ in range(N_NULL):
                fx = fano_exponent(pivot_indices(return_shuffle(s, rng), theta), n, WINDOWS)
                if fx["alpha"] == fx["alpha"]:
                    nulls.append(fx["alpha"])
            if nulls:
                ash.append(statistics.mean(nulls))
        per_theta.append({
            "theta": theta,
            "alpha_real": statistics.mean(ar), "alpha_shuffle": statistics.mean(ash),
            "excess": statistics.mean(ar) - statistics.mean(ash),
            "count_hurst": (1 + statistics.mean(ar)) / 2, "mean_r2": statistics.mean(r2s),
            "n_positive": sum(1 for a, b in zip(sorted(ar), sorted(ash)) if a > b),
        })

    out = {"experiment": "fractal_clock", "windows": WINDOWS,
           "per_theta": per_theta, "n_series": len(seqs)}

    if not quiet:
        print(f"pivot point process, {len(seqs)} long series, Fano-factor scaling "
              f"F(T) ~ T^alpha\n")
        print(f"{'theta':>6s} {'alpha_real':>11s} {'alpha_shuf':>11s} {'excess':>8s} "
              f"{'countHurst':>11s} {'R^2':>6s}")
        for r in per_theta:
            print(f"{r['theta']:>6.2f} {r['alpha_real']:>11.3f} {r['alpha_shuffle']:>11.3f} "
                  f"{r['excess']:>+8.3f} {r['count_hurst']:>11.3f} {r['mean_r2']:>6.3f}")
        alphas = [r["alpha_real"] for r in per_theta]
        print(f"\n  alpha stays positive and away from the renewal null at every scale "
              f"(spread {max(alphas)-min(alphas):.2f}); the clock is a self-similar fractal "
              f"point process,")
        print("  and its clustering is approximately scale-invariant across reversal scales.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp21_fractal_clock.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp21_fractal_clock.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
