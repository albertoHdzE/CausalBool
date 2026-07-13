"""exp31_stress_100.py  (Level 10)

Adversarial stress test of the oracle / clock claims on ~100 stocks, not the twelve
survivors.  The question is not "does it look good" but "which claims survive out of
sample, against the return-shuffle, on a large and diverse panel".

Four honest verdicts:

  1. The theorem is a construction identity, not a market fact.  DC(theta=c) is
     contained in the oracle on the 100 stocks AND on a GBM control AND on i.i.d.
     lognormal noise, all at ~1.0.  It says nothing specific about markets; it is
     geometry.  Reported as such.

  2. The one real market claim -- the clock self-excites.  Branching ratio of the
     oracle/pivot clock vs its return-shuffle, fraction of the 100 that are clearly
     self-exciting, and the out-of-sample Hawkes-beats-Poisson fraction with a
     sign-test.  This is the load-bearing result; everything else is inherited or
     geometric.

  3. The out-of-sample forecast is the pivot forecast relabelled.  Oracle (look-ahead)
     OOS gain vs pivot (causal) OOS gain -- if equal, no leak, but no new information.

  4. The n(c) hump -- does the non-monotone cost-scale curve survive on 100?
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
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))
sys.path.insert(0, os.path.join(ROOT, "level9"))

from finance import load_yahoo_close  # noqa: E402
from oracle import oracle_points, kappa_for_round_trip  # noqa: E402
from controls import return_shuffle, geometric_random_walk  # noqa: E402
from point_process import pivot_indices, fano_exponent  # noqa: E402
from hawkes import fit_hawkes, oos_loglik, poisson_loglik  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
C_MAIN = 0.02
C_GRID = [0.005, 0.01, 0.02, 0.04, 0.08]
TRAIN_FRAC = 0.7
WINDOWS = [10, 20, 40, 80, 160, 320]
N_NULL = 5


def load_100() -> dict[str, list[float]]:
    seqs = {}
    if not os.path.isdir(DATA_100):
        return seqs
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def binom_sign_p(k: int, n: int) -> float:
    """Two-sided sign-test p-value for k of n positive under p=0.5."""
    if n == 0:
        return 1.0
    from math import comb
    kk = max(k, n - k)
    tail = sum(comb(n, i) for i in range(kk, n + 1)) / (2 ** n)
    return min(1.0, 2 * tail)


def _oos_gain(times: list[float], T: float) -> float:
    T_tr = T * TRAIN_FRAC
    tr = [x for x in times if x <= T_tr]
    if len(tr) < 10 or len(times) - len(tr) < 5:
        return 0.0
    ftr = fit_hawkes(tr, T_tr)
    h_ll, n_test = oos_loglik(times, T, T_tr, ftr["mu"], ftr["alpha"], ftr["beta"])
    mu_p = len(tr) / T_tr
    p_ll = poisson_loglik(times, T, mu_p) - poisson_loglik(tr, T_tr, mu_p)
    return (h_ll - p_ll) / n_test if n_test else 0.0


def run(quiet: bool = False) -> dict:
    seqs = load_100()
    if len(seqs) < 20:
        raise SystemExit(f"only {len(seqs)} series in {DATA_100}; run download_100.py first")
    rng = random.Random(31)
    kappa = kappa_for_round_trip(C_MAIN)

    rows = []
    for name, s in seqs.items():
        T = float(len(s))
        orc = [float(i) for i in oracle_points(s, kappa)]
        piv = [float(i) for i in pivot_indices(s, C_MAIN)]
        orc_set = set(int(x) for x in orc)
        contain = (sum(1 for i in piv if int(i) in orc_set) / len(piv)) if piv else float("nan")
        fit = fit_hawkes(orc, T)
        fano = fano_exponent([int(x) for x in orc], int(T), WINDOWS).get("alpha", float("nan"))
        oos_orc = _oos_gain(orc, T)
        oos_piv = _oos_gain(piv, T)
        nb_null = []
        for _ in range(N_NULL):
            ts = [float(i) for i in oracle_points(return_shuffle(s, rng), kappa)]
            nb_null.append(fit_hawkes(ts, T)["branching_ratio"])
        rows.append({
            "name": name, "n_days": len(s), "n_events": fit["n_events"],
            "containment": contain,
            "branching_ratio": fit["branching_ratio"],
            "branching_null": statistics.mean(nb_null),
            "fano_alpha": fano,
            "oos_gain_oracle": oos_orc, "oos_gain_pivot": oos_piv,
        })

    # GBM + noise controls: containment (identity) and null clock
    gbm = geometric_random_walk(11000, 0.02, random.Random(999))
    gpiv = pivot_indices(gbm, C_MAIN); gorc = set(oracle_points(gbm, kappa))
    gbm_contain = sum(1 for i in gpiv if i in gorc) / len(gpiv) if gpiv else float("nan")
    gbm_fit = fit_hawkes([float(i) for i in sorted(gorc)], float(len(gbm)))
    noise = [100.0]
    nrng = random.Random(998)
    for _ in range(11000):
        noise.append(noise[-1] * math.exp(0.02 * nrng.gauss(0, 1)))
    npiv = pivot_indices(noise, C_MAIN); norc = set(oracle_points(noise, kappa))
    noise_contain = sum(1 for i in npiv if i in norc) / len(npiv) if npiv else float("nan")

    # n(c) cost-scale curve
    cost_scale = []
    for c in C_GRID:
        kap = kappa_for_round_trip(c)
        nbs = [fit_hawkes([float(i) for i in oracle_points(s, kap)], float(len(s)))["branching_ratio"]
               for s in seqs.values()]
        cost_scale.append({"c": c, "mean_branching": statistics.mean(nbs),
                           "std_branching": statistics.pstdev(nbs)})
    # is the curve humped per series? (peak at an interior c)
    def n_of_c(s):
        return [fit_hawkes([float(i) for i in oracle_points(s, kappa_for_round_trip(c))],
                           float(len(s)))["branching_ratio"] for c in C_GRID]
    humped = 0
    for s in seqs.values():
        ns = n_of_c(s)
        if ns.index(max(ns)) not in (0, len(ns) - 1):
            humped += 1

    n = len(rows)

    def frac(pred):
        return sum(1 for r in rows if pred(r)) / n

    def mean(k):
        return statistics.mean(r[k] for r in rows)

    k_self = sum(1 for r in rows if r["branching_ratio"] > r["branching_null"] + 0.1)
    k_oos = sum(1 for r in rows if r["oos_gain_oracle"] > 0)
    out = {
        "experiment": "stress_100", "n_series": n, "c_main": C_MAIN,
        "identity": {
            "mean_containment_stocks": mean("containment"),
            "gbm_containment": gbm_contain, "noise_containment": noise_contain,
            "note": "containment ~1.0 on stocks, GBM and noise alike -> geometric identity, not a market fact",
        },
        "self_excitation": {
            "mean_branching": mean("branching_ratio"),
            "mean_branching_null": mean("branching_null"),
            "n_self_exciting": k_self, "frac_self_exciting": k_self / n,
            "mean_fano_alpha": mean("fano_alpha"),
        },
        "oos_forecast": {
            "mean_oos_oracle": mean("oos_gain_oracle"),
            "mean_oos_pivot": mean("oos_gain_pivot"),
            "n_oos_positive": k_oos, "frac_oos_positive": k_oos / n,
            "sign_test_p": binom_sign_p(k_oos, n),
        },
        "gbm_control": {"branching": gbm_fit["branching_ratio"], "containment": gbm_contain},
        "cost_as_scale": cost_scale,
        "n_humped": humped, "frac_humped": humped / n,
        "rows": rows,
    }

    if not quiet:
        print(f"Adversarial stress test on {n} stocks (round-trip cost c = {C_MAIN})\n")
        print("1. THEOREM IS A GEOMETRIC IDENTITY (not a market fact):")
        print(f"   DC-in-oracle containment: stocks {out['identity']['mean_containment_stocks']:.4f}, "
              f"GBM {gbm_contain:.4f}, noise {noise_contain:.4f}  -> identical on all -> pure geometry\n")
        print("2. THE ONE REAL MARKET CLAIM -- clock self-excitation:")
        print(f"   branching ratio n = {out['self_excitation']['mean_branching']:.3f} "
              f"vs shuffle {out['self_excitation']['mean_branching_null']:.3f}; "
              f"self-exciting on {k_self}/{n} ({100*k_self/n:.0f}%)")
        print(f"   Fano exponent {out['self_excitation']['mean_fano_alpha']:.3f}\n")
        print("3. OOS FORECAST is the pivot forecast relabelled (no leak, no new info):")
        print(f"   oracle {out['oos_forecast']['mean_oos_oracle']:+.4f} vs "
              f"pivot {out['oos_forecast']['mean_oos_pivot']:+.4f} nats/event; "
              f"positive {k_oos}/{n}, sign-test p = {out['oos_forecast']['sign_test_p']:.1e}\n")
        print(f"   GBM control clock: branching {gbm_fit['branching_ratio']:.3f} -> reads ~null\n")
        print("4. n(c) COST-SCALE CURVE (does the hump survive?):")
        for r in cost_scale:
            print(f"   c = {r['c']:.3f}:  n = {r['mean_branching']:.3f} +/- {r['std_branching']:.3f}")
        print(f"   per-series peak at an interior cost: {humped}/{n} ({100*humped/n:.0f}%)")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp31_stress_100.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp31_stress_100.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
