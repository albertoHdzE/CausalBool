"""exp17_fractal_dimension.py  (Level 5)

The pivot-count scaling law N(theta) ~ theta**(-D) and its exponent D, the
representation-free self-similarity dimension of the salient points.

D is read as minus the slope of log N against log theta over a geometric grid of
reversal scales.  Two references frame it: a geometric random walk (the memoryless
benchmark) and the return-shuffle of each real series (the same marginal, no
temporal order).  If real markets proliferate pivots the way a random walk does,
D carries little; the honest reading here is that D barely separates them -- the
self-similarity of pivot proliferation is close to the random-walk value, and the
structure lives elsewhere (the clock; see exp19).
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

from occurrence_geometry import fractal_dimension  # noqa: E402
from controls import (load_long_sequences, return_shuffle,  # noqa: E402
                      geometric_random_walk)

RESULTS_DIR = os.path.join(ROOT, "results")
THETAS = [0.01 * 1.5 ** k for k in range(9)]   # 0.010 .. 0.384
N_NULL = 15


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(17)
    gbm = geometric_random_walk(12000, 0.011, rng)
    gbm_D = fractal_dimension(gbm, THETAS)

    rows = []
    for name, s in seqs.items():
        real = fractal_dimension(s, THETAS)
        nulls = [fractal_dimension(return_shuffle(s, rng), THETAS)["D"] for _ in range(N_NULL)]
        rows.append({"name": name, "D": real["D"], "r2": real["r2"],
                     "D_null": statistics.mean(nulls), "D_excess": real["D"] - statistics.mean(nulls)})

    def m(k):
        return statistics.mean(r[k] for r in rows)

    out = {"experiment": "fractal_dimension", "thetas": THETAS,
           "gbm_D": gbm_D["D"], "gbm_r2": gbm_D["r2"],
           "mean_D": m("D"), "mean_r2": m("r2"), "mean_D_excess": m("D_excess"),
           "n_D_excess_positive": sum(1 for r in rows if r["D_excess"] > 0),
           "n_series": len(rows), "rows": rows}

    if not quiet:
        print(f"pivot-count scaling N(theta) ~ theta^-D on {len(rows)} long series\n")
        print(f"  GBM benchmark: D = {gbm_D['D']:.2f} (R^2 {gbm_D['r2']:.3f})\n")
        print(f"{'series':8s} {'D':>6s} {'R^2':>6s} {'D_null':>7s} {'D_excess':>9s}")
        for r in rows:
            print(f"{r['name']:8s} {r['D']:>6.2f} {r['r2']:>6.3f} {r['D_null']:>7.2f} {r['D_excess']:>+9.3f}")
        print(f"\n  mean D {m('D'):.2f} (R^2 {m('r2'):.3f}); excess over return-shuffle "
              f"{m('D_excess'):+.3f} ({out['n_D_excess_positive']}/{len(rows)} positive)")
        print("  reading: pivots proliferate roughly as in a random walk; D is a weak "
              "separator, a small roughness excess only.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp17_fractal_dimension.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp17_fractal_dimension.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
