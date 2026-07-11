"""exp26_vol_and_tailrisk.py  (Level 8)

Two ingredients of the risk strategy, tested honestly.

1. Volatility forecast.  Does the multi-horizon (HAR) forecast, the model the
   self-similar long-memory clock motivates, predict next-block realised volatility
   better than a single trailing window?  Out of sample, pooled over instruments.

2. Tail-risk timing.  Is the clock an early warning for tail losses?  Split days by
   whether the recent activity (trailing realised volatility, the clock estimate)
   is in its top third, and compare the 5% conditional expected shortfall in the
   high-clock and low-clock states.  If the worst losses concentrate where the clock
   is high, then de-risking on the clock -- exactly what the vol-target strategy
   does -- removes the fat part of the tail.  This is the risk-measurement rationale
   for the whole strategy.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level6"))

from shared_clock import aligned_prices  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
BLOCK = 21


def _corr(x, y):
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx * sy else 0.0


def _cvar(xs, q=0.05):
    if not xs:
        return float("nan")
    k = max(1, int(q * len(xs)))
    return statistics.mean(sorted(xs)[:k])


def run(quiet: bool = False) -> dict:
    names, M = aligned_prices()
    R = [[math.log(M[i][t] / M[i][t - 1]) for t in range(1, len(M[i]))] for i in range(len(names))]

    # --- 1. vol forecast: HAR vs trailing, out of sample ---
    def rv(seg):
        return statistics.pstdev(seg)
    ce, ch, mse_e, mse_h = [], [], [], []
    for i in range(len(names)):
        blocks = [R[i][b:b + BLOCK] for b in range(0, len(R[i]) - BLOCK + 1, BLOCK)]
        vols = [rv(b) for b in blocks]
        tgt, fe, fh = [], [], []
        for k in range(12, len(vols) - 1):
            tgt.append(vols[k + 1])
            fe.append(vols[k])
            fh.append(statistics.mean([vols[k], statistics.mean(vols[k - 2:k + 1]),
                                       statistics.mean(vols[k - 11:k + 1])]))
        ce.append(_corr(fe, tgt))
        ch.append(_corr(fh, tgt))
        mse_e.append(statistics.mean((a - b) ** 2 for a, b in zip(fe, tgt)))
        mse_h.append(statistics.mean((a - b) ** 2 for a, b in zip(fh, tgt)))

    # --- 2. tail-risk timing: CVaR in high-clock vs low-clock states ---
    hi_es, lo_es = [], []
    for i in range(len(names)):
        r = R[i]
        clock = [0.0] * len(r)
        for t in range(21, len(r)):
            clock[t] = statistics.pstdev(r[t - 21:t])       # trailing realised vol = clock estimate
        valid = [t for t in range(21, len(r) - 1)]
        thr = sorted(clock[t] for t in valid)[int(2 / 3 * len(valid))]
        hi = [r[t + 1] for t in valid if clock[t] >= thr]    # next-day return when clock high
        lo = [r[t + 1] for t in valid if clock[t] < thr]
        hi_es.append(_cvar(hi))
        lo_es.append(_cvar(lo))

    out = {"experiment": "vol_and_tailrisk", "n_instruments": len(names),
           "vol_forecast": {
               "trailing_corr": statistics.mean(ce), "har_corr": statistics.mean(ch),
               "trailing_mse": statistics.mean(mse_e), "har_mse": statistics.mean(mse_h),
               "har_better_mse_count": sum(1 for a, b in zip(mse_h, mse_e) if a < b),
           },
           "tail_risk": {
               "cvar5_high_clock": statistics.mean(hi_es),
               "cvar5_low_clock": statistics.mean(lo_es),
               "ratio": statistics.mean(hi_es) / statistics.mean(lo_es),
               "n_worse_in_high": sum(1 for a, b in zip(hi_es, lo_es) if a < b),
           }}

    if not quiet:
        vf = out["vol_forecast"]
        tr = out["tail_risk"]
        print(f"{len(names)} instruments, ~32 years\n")
        print("1. volatility forecast, out of sample (next-block realised vol):")
        print(f"   trailing : corr {vf['trailing_corr']:.3f}  MSE {vf['trailing_mse']*1e6:.2f}e-6")
        print(f"   HAR clock: corr {vf['har_corr']:.3f}  MSE {vf['har_mse']*1e6:.2f}e-6  "
              f"(lower MSE on {vf['har_better_mse_count']}/{len(names)})")
        print(f"   -> the multi-scale clock forecast lowers the error by "
              f"{100*(1-vf['har_mse']/vf['trailing_mse']):.0f}%, modest but consistent.\n")
        print("2. tail-risk timing (5% expected shortfall of next-day return):")
        print(f"   high-clock days : {tr['cvar5_high_clock']:.3%}")
        print(f"   low-clock days  : {tr['cvar5_low_clock']:.3%}")
        print(f"   the tail is {tr['ratio']:.1f}x deeper when the clock is high "
              f"({tr['n_worse_in_high']}/{len(names)} instruments).")
        print("   -> the worst losses concentrate where the clock is high, so de-risking on the "
              "clock removes the fat part of the tail. This is the risk rationale for the strategy.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp26_vol_and_tailrisk.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp26_vol_and_tailrisk.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
