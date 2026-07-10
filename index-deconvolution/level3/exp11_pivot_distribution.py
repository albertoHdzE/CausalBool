"""exp11_pivot_distribution.py  (Level 3)

The whole-picture view: instead of asking for one global rule, measure how local
structure (the pivots, the islands of determinism) is distributed along time.

A long binary series is cut into non-overlapping windows; the Lempel-Ziv
complexity of each window is a local structure score.  If markets were structure-
less at every scale, the window scores would be uniform (as in a time-shuffled
series).  If local structure clusters in time (calm and turbulent regimes), the
window scores vary far more than in the shuffle.  The dispersion of the local-
complexity profile, real versus shuffle, is therefore a direct, honest test of
whether the distribution of local determinism is itself structured.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import align_prices, daily_returns, sign_states  # noqa: E402
from behaviour_table import lz76_complexity  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "SPY"]
WINDOW = 30


def window_profile(series, w):
    return [lz76_complexity(series[i:i + w]) for i in range(0, len(series) - w + 1, w)]


def run():
    paths = {t: os.path.join(DATA_DIR, f"{t}.json") for t in TICKERS
             if os.path.exists(os.path.join(DATA_DIR, f"{t}.json"))}
    tk, dates, M = align_prices(paths)
    S = sign_states(daily_returns(M))
    rng = random.Random(5)

    real_disp = []
    shuf_disp = []
    for j in range(len(tk)):
        series = [S[i][j] for i in range(len(S))]
        prof = window_profile(series, WINDOW)
        if len(prof) < 3:
            continue
        real_disp.append(statistics.pstdev(prof))
        # shuffle control: destroy temporal order, keep density
        ds = []
        for _ in range(30):
            sh = series[:]
            rng.shuffle(sh)
            ds.append(statistics.pstdev(window_profile(sh, WINDOW)))
        shuf_disp.append(sum(ds) / len(ds))

    mean_real = sum(real_disp) / len(real_disp)
    mean_shuf = sum(shuf_disp) / len(shuf_disp)
    ratio = mean_real / mean_shuf if mean_shuf else float("nan")
    n_series_above = sum(1 for r, s in zip(real_disp, shuf_disp) if r > s)

    print(f"tickers: {len(tk)}, days: {len(S)}, window: {WINDOW}, "
          f"windows/series: {len(window_profile([0]*len(S), WINDOW))}")
    print("\n=== distribution of local structure along time (pivots) ===")
    print(f"  dispersion of local-complexity profile, REAL   : {mean_real:.3f}")
    print(f"  dispersion of local-complexity profile, SHUFFLE: {mean_shuf:.3f}")
    print(f"  ratio real/shuffle: {ratio:.3f}   "
          f"({n_series_above}/{len(real_disp)} series more clustered than shuffle)")
    verdict = ("YES - local structure clusters in time (a structured pivot "
               "distribution) even though the direction is not predictable."
               if ratio > 1.05 else
               "No detectable clustering of local structure at this window/resolution.")
    print(f"  verdict: {verdict}")

    out = {"experiment": "pivot_distribution", "window": WINDOW,
           "mean_dispersion_real": mean_real, "mean_dispersion_shuffle": mean_shuf,
           "ratio": ratio, "series_more_clustered_than_shuffle": n_series_above,
           "n_series": len(real_disp)}
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp11_pivot_distribution.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwritten: results/exp11_pivot_distribution.json")
    return out


if __name__ == "__main__":
    run()
