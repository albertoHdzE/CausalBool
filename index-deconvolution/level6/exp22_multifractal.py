"""exp22_multifractal.py  (Level 6)

Is the clock monofractal or multifractal?

One Hurst exponent describes a process whose scaling is uniform.  Many natural
activity processes are richer: different moments scale with different exponents, so
a spectrum h(q) is needed.  Using multifractal detrended fluctuation analysis on
the inter-pivot waiting-time sequence (the clock's own intervals, which have a good
dynamic range), we estimate h(q) for a range of positive moment orders q and report
the width h(q_min) - h(q_max).  Small q weights small fluctuations, large q the
large ones; a decreasing h(q) means large bursts scale differently from calm
stretches.  A width near zero (and near the return-shuffle's) is monofractal; a
width clearly above the null is multifractal -- a richer description of the clock
than a single exponent.
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

from point_process import generalised_hurst, pivot_indices  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
QS = [1.0, 2.0, 3.0, 4.0, 5.0]
SCALES = [8, 16, 32, 64, 128]
N_NULL = 10


def waiting_times(series, theta):
    idx = pivot_indices(series, theta)
    return [float(idx[i + 1] - idx[i]) for i in range(len(idx) - 1)]


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(22)
    rows = []
    for name, s in seqs.items():
        sig = waiting_times(s, THETA)
        if len(sig) < 256:
            continue
        h = generalised_hurst(sig, QS, SCALES)
        width = h[QS[0]] - h[QS[-1]]     # h(q_min) - h(q_max); positive if multifractal
        nulls = []
        for _ in range(N_NULL):
            nsig = waiting_times(return_shuffle(s, rng), THETA)
            hn = generalised_hurst(nsig, QS, SCALES)
            nulls.append(hn[QS[0]] - hn[QS[-1]])
        rows.append({"name": name, "h": {str(q): h[q] for q in QS},
                     "width": width, "width_null": statistics.mean(nulls),
                     "width_excess": width - statistics.mean(nulls)})

    def m(k):
        return statistics.mean(r[k] for r in rows)

    out = {"experiment": "multifractal_clock", "theta": THETA, "signal": "waiting_times",
           "qs": QS, "mean_width": m("width"), "mean_width_null": m("width_null"),
           "mean_width_excess": m("width_excess"),
           "n_wider_than_null": sum(1 for r in rows if r["width_excess"] > 0),
           "n_series": len(rows), "rows": rows}

    if not quiet:
        print(f"multifractal width of the activity signal, {len(rows)} long series, "
              f"q in {QS}\n")
        print(f"{'series':8s} {'h(q=1)':>7s} {'h(q=5)':>7s} {'width':>7s} {'null':>7s} {'excess':>8s}")
        for r in rows:
            print(f"{r['name']:8s} {r['h'][str(QS[0])]:>7.3f} {r['h'][str(QS[-1])]:>7.3f} "
                  f"{r['width']:>7.3f} {r['width_null']:>7.3f} {r['width_excess']:>+8.3f}")
        print(f"\n  mean multifractal width {m('width'):.3f}; null {m('width_null'):.3f}; "
              f"excess {m('width_excess'):+.3f} ({out['n_wider_than_null']}/{len(rows)} wider than null)")
        verdict = ("the clock is multifractal: several moments scale with different exponents, "
                   "beyond the shuffle." if m("width_excess") > 0.05 and out["n_wider_than_null"] >= 0.7 * len(rows)
                   else "the multifractal width is modest / not clearly above the null; treat as weak.")
        print(f"  reading: {verdict}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp22_multifractal.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp22_multifractal.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
