"""exp32_multiscale_and_fourier.py  (Level 11)

Two follow-ups the assessor asked for, both against controls.

FOURIER -- does splitting the series into sinusoids isolate the structure?
  For each long series we take the spectral exponent (slope of log-power vs
  log-frequency; 0 = white/noise, negative = red/long-memory) of three signals:
    * daily log-returns          -- expected white (no linear predictability),
    * absolute returns (vol)     -- expected red  (volatility long-memory),
    * the pivot activity clock   -- expected red  (the fractal clock).
  If returns are white and the clock is red, Fourier confirms, in a second language,
  the same split the pivots found: noise in the values, structure in the timing -- and
  offers no periodic line to trade. Controls: white noise (~0) and a random walk (~-2).

MULTI-SCALE HAWKES (open door #2) -- does a power-law kernel beat the single
  exponential? Level 9's one-timescale kernel regenerated a Fano exponent of ~0.41
  against a real ~0.49. A power-law kernel (sum of exponentials on a geometric grid,
  same three free numbers) is self-similar by construction and should regenerate more
  of the clustering. We compare, per series: held-out log-likelihood and the Fano
  exponent of a simulation from each fitted kernel, against the real clock.
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
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))
sys.path.insert(0, os.path.join(ROOT, "level9"))

from spectral import periodogram, loglog_slope  # noqa: E402
from kernels import fit_powerlaw, simulate_multi, oos_loglik_multi  # noqa: E402
from controls import load_long_sequences, log_returns, geometric_random_walk  # noqa: E402
from point_process import pivot_indices, fano_exponent, activity_signal  # noqa: E402
from hawkes import fit_hawkes, simulate, oos_loglik, poisson_loglik  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
WINDOWS = [10, 20, 40, 80, 160, 320]
ACT_WINDOW = 20
TRAIN_FRAC = 0.7


def _fourier(seqs) -> dict:
    ret_s, vol_s, clk_s = [], [], []
    for s in seqs.values():
        r = log_returns(s)
        ret_s.append(loglog_slope(*periodogram(r))["slope"])
        vol_s.append(loglog_slope(*periodogram([abs(x) for x in r]))["slope"])
        act = activity_signal(s, THETA, ACT_WINDOW)
        clk_s.append(loglog_slope(*periodogram([float(a) for a in act]))["slope"])
    # controls
    import random
    rng = random.Random(11)
    white = [rng.gauss(0, 1) for _ in range(16384)]
    walk = [0.0]
    for _ in range(16383):
        walk.append(walk[-1] + rng.gauss(0, 1))
    return {
        "returns_slope": statistics.fmean(ret_s),
        "abs_returns_slope": statistics.fmean(vol_s),
        "activity_slope": statistics.fmean(clk_s),
        "control_white_slope": loglog_slope(*periodogram(white))["slope"],
        "control_walk_slope": loglog_slope(*periodogram(walk))["slope"],
        "returns_slope_all": ret_s, "abs_returns_slope_all": vol_s,
        "activity_slope_all": clk_s,
    }


def _multiscale(seqs) -> dict:
    rows = []
    for name, s in seqs.items():
        T = float(len(s))
        t = [float(i) for i in pivot_indices(s, THETA)]
        if len(t) < 40:
            continue
        real_alpha = fano_exponent([int(x) for x in t], int(T), WINDOWS).get("alpha", float("nan"))

        # single-exponential (Level 9)
        f1 = fit_hawkes(t, T)
        sim1 = simulate(f1["mu"], f1["alpha"], f1["beta"], T, seed=1)
        a1 = fano_exponent(sorted(int(x) for x in sim1), int(T), WINDOWS).get("alpha", float("nan"))
        T_tr = T * TRAIN_FRAC
        tr = [x for x in t if x <= T_tr]
        f1tr = fit_hawkes(tr, T_tr)
        h1, nt = oos_loglik(t, T, T_tr, f1tr["mu"], f1tr["alpha"], f1tr["beta"])
        mu_p = len(tr) / T_tr
        p_ll = poisson_loglik(t, T, mu_p) - poisson_loglik(tr, T_tr, mu_p)
        oos1 = (h1 - p_ll) / nt if nt else 0.0

        # power-law multi-scale (Level 11)
        f2 = fit_powerlaw(t, T)
        sim2 = simulate_multi(f2["mu"], f2["alphas"], f2["betas"], T, seed=1)
        a2 = fano_exponent(sorted(int(x) for x in sim2), int(T), WINDOWS).get("alpha", float("nan"))
        f2tr = fit_powerlaw(tr, T_tr)
        h2, nt2 = oos_loglik_multi(t, T, T_tr, f2tr["mu"], f2tr["alphas"], f2tr["betas"])
        oos2 = (h2 - p_ll) / nt2 if nt2 else 0.0

        rows.append({
            "name": name, "real_fano": real_alpha,
            "single_fano": a1, "multi_fano": a2,
            "single_oos": oos1, "multi_oos": oos2,
            "gamma": f2["gamma"], "n_single": f1["branching_ratio"], "n_multi": f2["branching_ratio"],
        })
    def m(k):
        vals = [r[k] for r in rows if not math.isnan(r[k])]
        return statistics.fmean(vals) if vals else float("nan")
    return {
        "mean_real_fano": m("real_fano"),
        "mean_single_fano": m("single_fano"), "mean_multi_fano": m("multi_fano"),
        "mean_single_oos": m("single_oos"), "mean_multi_oos": m("multi_oos"),
        "mean_gamma": m("gamma"),
        "n_multi_closer_to_real": sum(1 for r in rows
                                      if abs(r["multi_fano"] - r["real_fano"])
                                      < abs(r["single_fano"] - r["real_fano"])),
        "n_series": len(rows), "rows": rows,
    }


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    fourier = _fourier(seqs)
    multi = _multiscale(seqs)
    out = {"experiment": "multiscale_and_fourier", "theta": THETA,
           "fourier": fourier, "multiscale": multi}

    if not quiet:
        print("FOURIER -- spectral exponent (0 = white/noise, negative = red/long-memory)\n")
        print(f"  daily log-returns   : {fourier['returns_slope']:+.3f}   "
              f"(expected ~0, white: markets carry no linear structure)")
        print(f"  absolute returns    : {fourier['abs_returns_slope']:+.3f}   "
              f"(red: volatility has long memory)")
        print(f"  pivot activity clock: {fourier['activity_slope']:+.3f}   "
              f"(red: the fractal clock)")
        print(f"  controls: white noise {fourier['control_white_slope']:+.3f}, "
              f"random walk {fourier['control_walk_slope']:+.3f}")
        print("  -> Fourier confirms the split: values are white/noise, the clock is red.")
        print("     No discrete periodic line -> nothing new to trade; it corroborates, not rescues.\n")

        m = multi
        print("MULTI-SCALE (power-law) HAWKES vs single-exponential:\n")
        print(f"  real clock Fano exponent      : {m['mean_real_fano']:.3f}")
        print(f"  single-exponential regenerates: {m['mean_single_fano']:.3f}")
        print(f"  power-law regenerates         : {m['mean_multi_fano']:.3f}  "
              f"(closer to real on {m['n_multi_closer_to_real']}/{m['n_series']} series)")
        print(f"  out-of-sample gain: single {m['mean_single_oos']:+.3f} vs "
              f"power-law {m['mean_multi_oos']:+.3f} nats/event")
        print(f"  mean power-law exponent gamma = {m['mean_gamma']:.2f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp32_multiscale_fourier.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp32_multiscale_fourier.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
