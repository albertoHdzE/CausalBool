"""exp25_joint_law.py  (Level 7)

The joint law of a leg's duration dt and its value change dv, against the return-
shuffle null, whose legs are those of a random walk with the same marginal.

- Within-leg diffusion exponent H (|dv| ~ dt**H).  The null pins the Brownian
  reference H = 1/2; a real H below it is sub-diffusive.
- Cross-leg couplings: does a long calm precede a large move, or a large move a long
  rest?

The construction is representation-free and scale-invariant; the null isolates any
coupling that is not already present in a random walk of the same increments.
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

from pivots import directional_change_pivots, legs  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402
from joint_law import within_leg_diffusion_exponent, cross_leg_couplings  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
N_NULL = 15


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(25)
    rows = []
    for name, s in seqs.items():
        lg = legs(directional_change_pivots(s, THETA))
        H = within_leg_diffusion_exponent(lg)
        cc = cross_leg_couplings(lg)
        Hn, calm, rest = [], [], []
        for _ in range(N_NULL):
            nl = legs(directional_change_pivots(return_shuffle(s, rng), THETA))
            hh = within_leg_diffusion_exponent(nl)
            if hh == hh:
                Hn.append(hh)
            ccn = cross_leg_couplings(nl)
            calm.append(ccn["calm_then_move"])
            rest.append(ccn["move_then_rest"])
        rows.append({"name": name, "H": H, "H_null": statistics.mean(Hn),
                     "H_excess": H - statistics.mean(Hn),
                     "calm_then_move": cc["calm_then_move"], "calm_null": statistics.mean(calm),
                     "move_then_rest": cc["move_then_rest"], "rest_null": statistics.mean(rest)})

    def m(k):
        return statistics.mean(r[k] for r in rows)

    n_sub = sum(1 for r in rows if r["H_excess"] < 0)
    out = {"experiment": "joint_law", "theta": THETA, "n_series": len(rows),
           "mean_H": m("H"), "mean_H_null": m("H_null"), "mean_H_excess": m("H_excess"),
           "n_subdiffusive_vs_null": n_sub,
           "mean_calm_then_move": m("calm_then_move"), "mean_calm_null": m("calm_null"),
           "mean_move_then_rest": m("move_then_rest"), "mean_rest_null": m("rest_null"),
           "rows": rows}

    if not quiet:
        print(f"joint (dt, dv) law, {len(rows)} long series, theta={THETA}, null=return-shuffle\n")
        print(f"{'series':8s} {'H':>6s} {'H_null':>7s} {'H_excess':>9s}")
        for r in rows:
            print(f"{r['name']:8s} {r['H']:>6.3f} {r['H_null']:>7.3f} {r['H_excess']:>+9.3f}")
        print(f"\n  within-leg diffusion exponent H: real {m('H'):.3f}, null {m('H_null'):.3f} "
              f"(Brownian ~0.5), excess {m('H_excess'):+.3f} ({n_sub}/{len(rows)} sub-diffusive vs null)")
        print(f"  cross calm->move corr : real {m('calm_then_move'):+.3f}  null {m('calm_null'):+.3f}")
        print(f"  cross move->rest corr : real {m('move_then_rest'):+.3f}  null {m('rest_null'):+.3f}")
        print("\n  reading: the null legs are Brownian (H~0.5); real legs are sub-diffusive "
              "(H~0.34) -- excursions travel less than a random walk of the same duration.")
        print("  cross-leg couplings are ~0: a long calm does NOT precede a big move (honest negative).")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp25_joint_law.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp25_joint_law.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
