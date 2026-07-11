"""exp20_clock_forecast.py  (Level 5)

Turn the clock structure of exp19 into an out-of-sample forecast.

In event time the waiting times dt between pivots cluster: short waits follow short
waits (activity bursts).  Binarise the clock into a short-wait unit (1 if the
waiting time is below its median) and forecast the next value from a short trailing
window, committing window and threshold on the first 60 % of the legs and
evaluating on the held-out last 40 %.  The null rebuilds the same pipeline on the
return-shuffle, which preserves the marginal of the increments and destroys their
order, so the clock clustering is removed.

A positive edge that survives the null shows the timing of pivots is forecastable
even though (exp19) their sizes are not -- a representation-free forecast of market
activity, committed and validated against a marginal-preserving control.
"""

from __future__ import annotations

import json
import math
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level4"))

from pivots import directional_change_pivots, legs  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402
from exp13_forecast import fit_and_test  # noqa: E402  (reuse committed forecaster)

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
N_NULL = 20


def short_wait_bits(series: list[float], theta: float) -> list[int]:
    lg = legs(directional_change_pivots(series, theta))
    dt = [a for a, _ in lg]
    if len(dt) < 20:
        return []
    med = statistics.median(dt)
    return [1 if x < med else 0 for x in dt]   # 1 = short wait = high activity


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(20)
    rows = []
    for name, s in seqs.items():
        bits = short_wait_bits(s, THETA)
        if len(bits) < 40:
            continue
        real = fit_and_test(bits)["edge"]
        nulls = []
        for _ in range(N_NULL):
            nb = short_wait_bits(return_shuffle(s, rng), THETA)
            if len(nb) >= 40:
                nulls.append(fit_and_test(nb)["edge"])
        null = statistics.mean(nulls) if nulls else 0.0
        rows.append({"name": name, "n_legs": len(bits), "edge": real,
                     "null_edge": null, "edge_vs_null": real - null})

    def m(k):
        return statistics.mean(r[k] for r in rows)

    n = len(rows)
    kpos = sum(1 for r in rows if r["edge_vs_null"] > 0)
    p_sign = sum(math.comb(n, i) for i in range(kpos, n + 1)) / (2 ** n) if n else 1.0
    out = {"experiment": "clock_forecast", "theta": THETA, "n_series": n,
           "mean_edge": m("edge"), "mean_null_edge": m("null_edge"),
           "mean_edge_vs_null": m("edge_vs_null"), "n_beat_null": kpos,
           "sign_test_p": p_sign, "rows": rows}

    if not quiet:
        print(f"clock (short-wait) forecast on {n} long series, theta={THETA}, "
              f"train 60 / test 40, null=return-shuffle\n")
        print(f"{'series':8s} {'legs':>5s} {'edge':>8s} {'null':>8s} {'edge-null':>10s}")
        for r in rows:
            print(f"{r['name']:8s} {r['n_legs']:>5d} {r['edge']:>+8.4f} {r['null_edge']:>+8.4f} "
                  f"{r['edge_vs_null']:>+10.4f}")
        print(f"\n  mean OOS edge over base rate {m('edge'):+.4f}; null {m('null_edge'):+.4f}; "
              f"edge over null {m('edge_vs_null'):+.4f}")
        print(f"  beats null on {kpos}/{n} series, sign-test p = {p_sign:.4g}")
        verdict = ("YES - pivot timing is forecastable out of sample beyond the marginal-preserving null."
                   if m("edge_vs_null") > 0 and p_sign < 0.05 else
                   "No significant clock forecast beyond the null.")
        print(f"  verdict: {verdict}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp20_clock_forecast.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp20_clock_forecast.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
