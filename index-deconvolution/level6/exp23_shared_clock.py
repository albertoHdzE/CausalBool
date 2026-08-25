"""exp23_shared_clock.py  (Level 6)

Is the activity clock shared, and does the shared part carry forecast power?

Three measurements on the aligned instruments:

  1. the mean pairwise correlation of the activity signals -- how synchronous the
     clocks are;
  2. the variance of each instrument's activity explained by the leave-one-out
     common signal (a nowcast R^2) -- how much of one clock is the common clock;
  3. the out-of-sample forecast enhancement: does adding the common signal at
     window m to an instrument's own activity at m improve the prediction of the
     instrument's activity at m+1, beyond its own past?  The rule is learnt on the
     first 60 % of windows and evaluated on the last 40 %.  The null shuffles the
     common signal in time, breaking its alignment with the target's future; if the
     enhancement survives that null, the shared clock carries genuine predictive
     information, not a coincidence of marginals.
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

from shared_clock import activity_matrix, pearson, leave_one_out_common  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
WINDOW = 30
TRAIN_FRAC = 0.6


def _binarise(x):
    med = statistics.median(x)
    return [1 if v > med else 0 for v in x]


def _fit_lookup(features, target, lo, hi):
    """Majority target per feature tuple over [lo, hi); returns the map."""
    counts = {}
    for t in range(lo, hi):
        counts.setdefault(features[t], [0, 0])[target[t]] += 1
    return {k: (1 if c1 >= c0 else 0) for k, (c0, c1) in counts.items()}


def _accuracy(features, target, table, lo, hi, default):
    correct = total = 0
    for t in range(lo, hi):
        pred = table.get(features[t], default)
        correct += (pred == target[t])
        total += 1
    return correct / total if total else 0.0


def _oos_enhancement(own_bit, common_bit, rng, shuffle_common=False):
    """OOS accuracy of (own+common) minus (own only) for predicting own_bit[m+1]."""
    n = len(own_bit)
    if shuffle_common:
        common_bit = common_bit[:]
        rng.shuffle(common_bit)
    target = own_bit[1:]                       # predict m+1
    own = own_bit[:-1]
    com = common_bit[:-1]
    m = len(target)
    split = int(m * TRAIN_FRAC)
    default = 1 if sum(own_bit[:split]) >= split - sum(own_bit[:split]) else 0
    f_own = [(o,) for o in own]
    f_both = [(o, c) for o, c in zip(own, com)]
    t_own = _fit_lookup(f_own, target, 0, split)
    t_both = _fit_lookup(f_both, target, 0, split)
    a_own = _accuracy(f_own, target, t_own, split, m, default)
    a_both = _accuracy(f_both, target, t_both, split, m, default)
    return a_both - a_own


def run(quiet: bool = False) -> dict:
    names, acts = activity_matrix(THETA, WINDOW)
    rng = random.Random(23)

    # 1. pairwise correlation
    cors = [pearson(acts[i], acts[j]) for i in range(len(names)) for j in range(i + 1, len(names))]

    # 2. nowcast R^2 from the leave-one-out common signal
    r2s = []
    for j in range(len(names)):
        common = leave_one_out_common(acts, j)
        r2s.append(pearson(acts[j], common) ** 2)

    # 3. OOS forecast enhancement vs a time-shuffled-common null
    enh, enh_null = [], []
    for j in range(len(names)):
        own_bit = _binarise(acts[j])
        common_bit = _binarise(leave_one_out_common(acts, j))
        enh.append(_oos_enhancement(own_bit, common_bit, rng))
        nulls = [_oos_enhancement(own_bit, common_bit, rng, shuffle_common=True) for _ in range(20)]
        enh_null.append(statistics.mean(nulls))

    n = len(names)
    n_pos = sum(1 for a, b in zip(enh, enh_null) if a > b)
    import math
    kpos = sum(1 for e in enh if e > 0)
    p_sign = sum(math.comb(n, i) for i in range(n_pos, n + 1)) / (2 ** n)
    out = {"experiment": "shared_clock", "theta": THETA, "window": WINDOW, "n_series": n,
           "mean_pairwise_corr": statistics.mean(cors),
           "max_pairwise_corr": max(cors), "min_pairwise_corr": min(cors),
           "mean_common_R2": statistics.mean(r2s),
           "mean_enhancement": statistics.mean(enh),
           "mean_enhancement_null": statistics.mean(enh_null),
           "n_enhancement_beats_null": n_pos, "sign_test_p": p_sign,
           "per_series": [{"name": names[j], "common_R2": r2s[j],
                           "enhancement": enh[j], "enhancement_null": enh_null[j]}
                          for j in range(n)]}

    if not quiet:
        print(f"{n} instruments aligned on common trading days, theta={THETA}, "
              f"window={WINDOW}\n")
        print(f"  1. mean pairwise activity correlation : {out['mean_pairwise_corr']:.3f} "
              f"(min {out['min_pairwise_corr']:.2f}, max {out['max_pairwise_corr']:.2f})")
        print(f"  2. activity variance explained by the common (leave-one-out) clock : "
              f"mean R^2 = {out['mean_common_R2']:.3f}")
        print(f"  3. out-of-sample forecast enhancement from the common clock:")
        print(f"       mean enhancement over own-past       : {out['mean_enhancement']:+.4f}")
        print(f"       mean enhancement under time-shuffle  : {out['mean_enhancement_null']:+.4f}")
        print(f"       beats null on {n_pos}/{n} instruments, sign-test p = {p_sign:.4g}")
        verdict = ("YES - the clock is largely shared and the common part forecasts each "
                   "instrument's activity beyond its own past."
                   if out["mean_enhancement"] > out["mean_enhancement_null"] and p_sign < 0.05 else
                   "the common clock explains contemporaneous activity but its out-of-sample "
                   "forecast edge over own-past is not clearly above the null.")
        print(f"\n  verdict: {verdict}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp23_shared_clock.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp23_shared_clock.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
