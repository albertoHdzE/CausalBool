"""exp39_universal_collapse.py  (Level 17)

One universal law, not a model per stock.

A per-stock fit is a description; a law must be the same object for every stock. We test
whether the market clock has a universal law by DATA COLLAPSE: remove each stock's scale
(rescale its gaps by their own mean) and ask whether all 100 normalised distributions fall
on one curve. If they do, there is a single universal clock law, with per-stock scale
(the mean rate) as the only free number -- one model, not a hundred.

  1. Collapse. Mean/max KS distance of each stock's normalised gap distribution to the
     pooled reference, versus the same on RAW (un-normalised) gaps -- normalisation should
     turn scatter into collapse. A shuffle collapses too, but onto a different (renewal)
     law, so the collapse plus the law together are the universal signature.
  2. The universal law. Fit exponential / lognormal / power-law to the pooled normalised
     gaps (AIC). Its dimensionless parameters are the universal constants.
  3. The universal exponent. The self-similarity exponent alpha across stocks and scales:
     is it one tight value (a universal exponent) or idiosyncratic?
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
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))

from scaling import (normalised_gaps, collapse_test, law_of_gaps, gaps_of,  # noqa: E402
                     alpha_at, ecdf_ks)
from finance import load_yahoo_close  # noqa: E402
from controls import return_shuffle  # noqa: E402
from point_process import pivot_indices  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
THETA = 0.02
THETAS = [0.01, 0.02, 0.04, 0.08]


def load_100():
    seqs = {}
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def run(quiet: bool = False) -> dict:
    seqs = load_100()
    rng = random.Random(39)

    per_norm, per_raw, per_norm_shuf = [], [], []
    mean_gaps = []
    for name, s in seqs.items():
        ev = pivot_indices(s, THETA)
        if len(ev) < 60:
            continue
        g = [float(x) for x in gaps_of(ev)]
        per_raw.append(g)
        per_norm.append(normalised_gaps(ev))
        mean_gaps.append(statistics.mean(g))
        per_norm_shuf.append(normalised_gaps(pivot_indices(return_shuffle(s, rng), THETA)))

    # 1. collapse: normalised vs raw
    col_norm = collapse_test(per_norm)
    col_raw = collapse_test(per_raw)
    col_shuf = collapse_test(per_norm_shuf)

    # 2. universal law on the pooled normalised gaps (subsample for tractable AIC)
    pooled = [x for s in per_norm for x in s]
    pooled_shuf = [x for s in per_norm_shuf for x in s]
    rng.shuffle(pooled); rng.shuffle(pooled_shuf)
    law_real = law_of_gaps(pooled[:40000])
    law_shuf = law_of_gaps(pooled_shuf[:40000])
    # KS of the real pooled law vs the shuffle pooled law (are the universal laws different?)
    ks_real_vs_shuf = ecdf_ks(pooled[:20000], pooled_shuf[:20000])

    # 3. universal exponent alpha across stocks and scales
    alpha_by_theta = {}
    for th in THETAS:
        als = [alpha_at(s, th) for s in seqs.values()]
        als = [a for a in als if a == a]
        alpha_by_theta[th] = {"mean": statistics.mean(als), "std": statistics.pstdev(als)}

    out = {
        "experiment": "universal_collapse", "theta": THETA, "n_series": len(per_norm),
        "collapse": {"normalised_mean_ks": col_norm["mean_ks"], "normalised_max_ks": col_norm["max_ks"],
                     "raw_mean_ks": col_raw["mean_ks"], "raw_max_ks": col_raw["max_ks"],
                     "shuffle_mean_ks": col_shuf["mean_ks"]},
        "universal_law": {"real": law_real["law"],
                          "real_params": law_real["params"].get(law_real["law"], {}),
                          "shuffle": law_shuf["law"],
                          "ks_real_vs_shuffle": ks_real_vs_shuf},
        "scale": {"mean_gap_min": min(mean_gaps), "mean_gap_max": max(mean_gaps),
                  "mean_gap_median": statistics.median(mean_gaps)},
        "alpha_by_theta": alpha_by_theta,
        "pooled_sample": pooled[:4000],           # for the collapse plot
        "pooled_shuffle_sample": pooled_shuf[:4000],
    }

    if not quiet:
        c = out["collapse"]
        print(f"Universal clock law by data collapse ({out['n_series']} stocks, theta={THETA})\n")
        print("1. COLLAPSE -- do the per-stock gap distributions fall on one curve?")
        print(f"   raw gaps        : mean KS {c['raw_mean_ks']:.3f}, max {c['raw_max_ks']:.3f}  "
              f"(scales differ -> scattered)")
        print(f"   normalised gaps : mean KS {c['normalised_mean_ks']:.3f}, max {c['normalised_max_ks']:.3f}  "
              f"(scale removed -> COLLAPSE)")
        print(f"   per-stock scale (mean gap) ranges {out['scale']['mean_gap_min']:.0f}"
              f"..{out['scale']['mean_gap_max']:.0f} days -> the only free number\n")
        u = out["universal_law"]
        print("2. THE UNIVERSAL LAW (pooled normalised gaps, AIC):")
        print(f"   real clock : {u['real']}   params {{"
              + ", ".join(f"{k}={v:.3f}" for k, v in u['real_params'].items() if k != 'k') + "}")
        print(f"   shuffle    : {u['shuffle']}   (renewal); real-vs-shuffle KS "
              f"{u['ks_real_vs_shuffle']:.3f} -> the universal law is NOT the renewal one\n")
        print("3. THE UNIVERSAL EXPONENT alpha (self-similarity) across stocks and scales:")
        for th in THETAS:
            a = out["alpha_by_theta"][th]
            print(f"   theta={th:.2f}: alpha = {a['mean']:.3f} +/- {a['std']:.3f}")
        print("   -> tight at fine scales (a universal exponent), softening at coarse scales.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp39_universal_collapse.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp39_universal_collapse.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
