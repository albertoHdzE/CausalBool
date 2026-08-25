"""exp24_clock_of_clock.py  (Level 7)

Does the clustering repeat one recursion deeper -- are there bursts of bursts?

For each series: the base clock is the pivot point process of the values, with Fano
exponent alpha_base (Level 6).  Its activity signal is formed, and the meta-clock is
the pivot point process of that activity signal, with Fano exponent alpha_meta.  If
alpha_meta is positive and comparable to alpha_base, the clustering is self-similar
across recursion depth: the regimes of activity themselves cluster the way the
events do.  The null return-shuffles the base series, so under it the activity is
near-flat and the meta-clock should not cluster.
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
sys.path.insert(0, os.path.join(ROOT, "level6"))

from controls import load_long_sequences, return_shuffle  # noqa: E402
from point_process import pivot_indices, fano_exponent, activity_signal  # noqa: E402
from recursion import meta_clock_exponent  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
WINDOW = 10
BASE_WINDOWS = [10, 20, 40, 80, 160, 320]
META_WINDOWS = [4, 8, 16, 32, 64]
N_NULL = 12


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(24)
    rows = []
    for name, s in seqs.items():
        alpha_base = fano_exponent(pivot_indices(s, THETA), len(s), BASE_WINDOWS)["alpha"]
        act = [float(x) for x in activity_signal(s, THETA, WINDOW)]
        meta = meta_clock_exponent(act, META_WINDOWS)
        alpha_meta = meta["alpha"]
        nulls = []
        for _ in range(N_NULL):
            na = [float(x) for x in activity_signal(return_shuffle(s, rng), THETA, WINDOW)]
            am = meta_clock_exponent(na, META_WINDOWS)["alpha"]
            if am == am:
                nulls.append(am)
        alpha_meta_null = statistics.mean(nulls) if nulls else float("nan")
        rows.append({"name": name, "alpha_base": alpha_base, "alpha_meta": alpha_meta,
                     "alpha_meta_null": alpha_meta_null,
                     "meta_excess": alpha_meta - alpha_meta_null,
                     "n_meta_pivots": meta["n_meta_pivots"]})

    def m(k):
        vals = [r[k] for r in rows if r[k] == r[k]]
        return statistics.mean(vals) if vals else float("nan")

    n_pos = sum(1 for r in rows if r["meta_excess"] == r["meta_excess"] and r["meta_excess"] > 0)
    out = {"experiment": "clock_of_clock", "theta": THETA, "window": WINDOW,
           "mean_alpha_base": m("alpha_base"), "mean_alpha_meta": m("alpha_meta"),
           "mean_alpha_meta_null": m("alpha_meta_null"), "mean_meta_excess": m("meta_excess"),
           "n_meta_positive": n_pos, "n_series": len(rows), "rows": rows}

    if not quiet:
        print(f"clock of the clock, {len(rows)} long series (theta={THETA}, window={WINDOW})\n")
        print(f"{'series':8s} {'alpha_base':>10s} {'alpha_meta':>10s} {'meta_null':>10s} "
              f"{'excess':>8s} {'meta_piv':>8s}")
        for r in rows:
            print(f"{r['name']:8s} {r['alpha_base']:>10.3f} {r['alpha_meta']:>10.3f} "
                  f"{r['alpha_meta_null']:>10.3f} {r['meta_excess']:>+8.3f} {r['n_meta_pivots']:>8d}")
        print(f"\n  base clock exponent   : {m('alpha_base'):.3f}")
        print(f"  meta clock exponent   : {m('alpha_meta'):.3f}  (null {m('alpha_meta_null'):.3f}, "
              f"excess {m('meta_excess'):+.3f}, {n_pos}/{len(rows)} positive)")
        clusters = m("meta_excess") > 0.05 and n_pos >= 0.66 * len(rows)
        attenuates = m("alpha_meta") < 0.5 * m("alpha_base")
        if clusters and attenuates:
            verdict = ("a hierarchy exists -- activity regimes cluster beyond the null "
                       f"({n_pos}/{len(rows)}) -- but the clustering ATTENUATES with depth "
                       f"(meta {m('alpha_meta'):.2f} << base {m('alpha_base'):.2f}), so it is a "
                       "partial hierarchy, not a scale-invariant cascade.")
        elif clusters:
            verdict = "activity regimes cluster beyond the null; clustering roughly preserved across depth."
        else:
            verdict = "the meta-clock clustering is not clearly above the null; no robust hierarchy."
        print(f"  reading: {verdict}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp24_clock_of_clock.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp24_clock_of_clock.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
