"""exp18_benford.py  (Level 5)

Do the occurrence gaps obey Benford's law?

Benford's law -- P(leading digit d) = log10(1 + 1/d) -- is the fingerprint of
scale-invariance: a quantity whose logarithm is spread uniformly across scales
shows it.  The representation-free pivot gaps (the waiting times dt and the move
sizes |dv|) are, by construction, differences taken under a relative threshold, so
they should be more scale-invariant than the raw values.  The experiment measures
the total-variation distance of each leading-digit histogram from Benford and
compares the gaps with the raw sequence.

A close fit of the gaps, against a poorer fit of the raw values, confirms that the
occurrence encoding captures the scale-invariant structure that a value
representation obscures -- the point of describing the series by occurrences rather
than by the digits of its numbers.
"""

from __future__ import annotations

import json
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

from occurrence_geometry import benford_distance, BENFORD  # noqa: E402
from pivots import directional_change_pivots, legs  # noqa: E402
from controls import load_long_sequences  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rows = []
    for name, s in seqs.items():
        lg = legs(directional_change_pivots(s, THETA))
        dt = [a for a, _ in lg]
        dv = [abs(b) for _, b in lg]
        rows.append({"name": name,
                     "raw_tv": benford_distance(s)["tv"],
                     "dt_tv": benford_distance(dt)["tv"],
                     "dv_tv": benford_distance(dv)["tv"], "n_legs": len(lg)})

    def m(k):
        return statistics.mean(r[k] for r in rows)

    # pooled leading-digit histogram of dt across all series
    all_dt = []
    for name, s in seqs.items():
        all_dt += [a for a, _ in legs(directional_change_pivots(s, THETA))]
    pooled = benford_distance(all_dt)

    out = {"experiment": "benford_gaps", "theta": THETA, "n_series": len(rows),
           "mean_raw_tv": m("raw_tv"), "mean_dt_tv": m("dt_tv"), "mean_dv_tv": m("dv_tv"),
           "pooled_dt_hist": pooled["hist"], "benford": BENFORD,
           "n_gaps_closer_than_raw": sum(1 for r in rows
                                         if r["dt_tv"] < r["raw_tv"] and r["dv_tv"] < r["raw_tv"]),
           "rows": rows}

    if not quiet:
        print(f"Benford total-variation distance (0 = perfect), {len(rows)} long series, "
              f"theta={THETA}\n")
        print(f"  raw values     : {m('raw_tv'):.3f}")
        print(f"  pivot waits dt : {m('dt_tv'):.3f}")
        print(f"  pivot sizes|dv|: {m('dv_tv'):.3f}")
        print(f"  gaps closer to Benford than raw on {out['n_gaps_closer_than_raw']}/{len(rows)} series")
        print("\n  pooled dt leading-digit frequency vs Benford:")
        print("   digit:   " + " ".join(f"{d:>4d}" for d in range(1, 10)))
        print("   dt   :   " + " ".join(f"{x:>4.2f}" for x in pooled["hist"]))
        print("   law  :   " + " ".join(f"{x:>4.2f}" for x in BENFORD))

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp18_benford.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp18_benford.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
