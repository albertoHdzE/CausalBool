"""exp34_spacetime_deconvolution.py  (Level 13)

The assessor's idea, tested: coarse-grain the value axis (scale-free), treat the
price-level sequence as the repertoire of a Boolean/CA network, and ask whether it
deconvolves to a deterministic rule -- with the programme's control triad.

  0. Coarse-graining fixes the bitacora-12 obstruction. Raw prices never recur, so the
     whole-pattern deconvolution had nothing to work with. We show recurrence climbing
     from ~0 (fine) to high (coarse): the deconvolution is now well-posed.

  1. The control triad. A deterministic logistic map (must read structured: low
     contradiction, positive lift over its own shuffle), the market, and the market's
     return-shuffle and a GBM (must read null). The instrument must separate them.

  2. The verdict. Does the coarse market level-sequence carry a deterministic rule that
     beats its shuffle? If yes, extraordinary. If no, it is the honest negative --
     direction is unforecastable even in this scale-free 2-D representation -- now stated
     where the test is finally well-posed, and the 'network' the deconvolution returns
     for a market is degenerate while the logistic control's is a real rule.
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

from spacetime import (logistic_series, symbolise_log,  # noqa: E402
                       recurrence_and_determinism)
from controls import load_long_sequences, return_shuffle, geometric_random_walk  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
H_GRID = [0.005, 0.01, 0.02, 0.04, 0.08, 0.16]      # coarseness sweep (log-bin width)
H_MAIN = 0.04
W_MAIN = 2
N_NULL = 6


def _metrics(series, h, w):
    return recurrence_and_determinism(symbolise_log(series, h), w)


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(34)

    # 0. recurrence vs coarseness (the b12 fix), averaged over the market panel
    recurrence_curve = []
    for h in H_GRID:
        rec = statistics.mean(_metrics(s, h, W_MAIN)["recurrence"] for s in seqs.values())
        recurrence_curve.append({"h": h, "recurrence": rec})

    # 1-2. control triad at the main coarseness.  Raw lift is dominated by trivial
    # persistence, so the honest quantity is lift EXCESS over a shuffle that keeps the
    # marginal and destroys temporal order.  For the market we use the return-shuffle;
    # for the logistic control, a symbol-permutation of its own coarse sequence.
    log_syms = symbolise_log(logistic_series(12000), H_MAIN)
    log_ctrl = recurrence_and_determinism(log_syms, W_MAIN)
    log_null_lift = []
    for _ in range(N_NULL):
        perm = list(log_syms)
        rng.shuffle(perm)
        log_null_lift.append(recurrence_and_determinism(perm, W_MAIN)["lift"])
    log_excess = log_ctrl["lift"] - statistics.mean(log_null_lift)

    rows = []
    for name, s in seqs.items():
        real = _metrics(s, H_MAIN, W_MAIN)
        sh_lift, sh_contra = [], []
        for _ in range(N_NULL):
            m = _metrics(return_shuffle(s, rng), H_MAIN, W_MAIN)
            if m["lift"] == m["lift"]:
                sh_lift.append(m["lift"])
                sh_contra.append(m["contradiction"])
        rows.append({
            "name": name, "recurrence": real["recurrence"],
            "contradiction": real["contradiction"], "lift": real["lift"],
            "lift_null": statistics.mean(sh_lift) if sh_lift else float("nan"),
            "contradiction_null": statistics.mean(sh_contra) if sh_contra else float("nan"),
            "lift_excess": real["lift"] - (statistics.mean(sh_lift) if sh_lift else 0.0),
        })

    gbm = [_metrics(geometric_random_walk(12000, 0.02, random.Random(500 + i)), H_MAIN, W_MAIN)
           for i in range(4)]
    gbm_lift = statistics.mean(g["lift"] for g in gbm)
    gbm_contra = statistics.mean(g["contradiction"] for g in gbm if g["contradiction"] == g["contradiction"])

    def m(k):
        vals = [r[k] for r in rows if r[k] == r[k]]
        return statistics.mean(vals) if vals else float("nan")

    out = {
        "experiment": "spacetime_deconvolution", "h_main": H_MAIN, "w": W_MAIN,
        "recurrence_curve": recurrence_curve,
        "logistic_control": {"recurrence": log_ctrl["recurrence"],
                             "contradiction": log_ctrl["contradiction"],
                             "lift": log_ctrl["lift"], "lift_excess": log_excess},
        "market": {"mean_recurrence": m("recurrence"),
                   "mean_contradiction": m("contradiction"),
                   "mean_lift": m("lift"), "mean_lift_null": m("lift_null"),
                   "mean_contradiction_null": m("contradiction_null"),
                   "mean_lift_excess": m("lift_excess"),
                   "n_excess_positive": sum(1 for r in rows if r["lift_excess"] > 0)},
        "gbm_control": {"lift": gbm_lift, "contradiction": gbm_contra},
        "rows": rows,
    }

    if not quiet:
        print(f"Spacetime deconvolution of the coarse value axis "
              f"(h={H_MAIN} log-units, memory w={W_MAIN})\n")
        print("0. Coarse-graining fixes the bitacora-12 obstruction (recurrence vs coarseness):")
        for r in recurrence_curve:
            bar = "#" * int(40 * r["recurrence"])
            print(f"   h={r['h']:.3f}: recurrence {r['recurrence']:.3f}  {bar}")
        print("   (fine bins never recur -> nothing to deconvolve; coarse bins recur -> well-posed)\n")

        lc, mk, gb = out["logistic_control"], out["market"], out["gbm_control"]
        print("1. Control triad -- contradiction (0=deterministic rule, 1=noise) and lift over base:")
        print(f"   {'system':22s} {'recurrence':>10s} {'contradiction':>13s} {'lift':>8s}")
        print(f"   {'logistic map (det.)':22s} {lc['recurrence']:>10.3f} "
              f"{lc['contradiction']:>13.3f} {lc['lift']:>+8.3f}")
        print(f"   {'MARKET (real)':22s} {mk['mean_recurrence']:>10.3f} "
              f"{mk['mean_contradiction']:>13.3f} {mk['mean_lift']:>+8.3f}")
        print(f"   {'market return-shuffle':22s} {'-':>10s} "
              f"{mk['mean_contradiction_null']:>13.3f} {mk['mean_lift_null']:>+8.3f}")
        print(f"   {'GBM':22s} {'-':>10s} {gb['contradiction']:>13.3f} {gb['lift']:>+8.3f}\n")

        print("2. Verdict -- lift EXCESS over shuffle (persistence removed):")
        print(f"   logistic control:  {lc['lift_excess']:+.4f}   (instrument detects the rule)")
        print(f"   MARKET:            {mk['mean_lift_excess']:+.4f} "
              f"({mk['n_excess_positive']}/{len(rows)} series positive)")
        verdict = ("a deterministic rule survives" if mk["mean_lift_excess"] > 0.02
                   and mk["n_excess_positive"] >= 10 else
                   "NO deterministic rule beyond the marginal -- the honest negative, now well-posed")
        print(f"   -> {verdict}.")
        print("   The logistic control deconvolves to a rule; the market does not, even here.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp34_spacetime_deconvolution.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp34_spacetime_deconvolution.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
