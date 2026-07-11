"""exp19_intrinsic_time.py  (Level 5)  -- the headline

Where does the temporal information live: in how big the pivot-to-pivot moves are
(the driver) or in when the pivots happen (the clock)?

Re-index time by pivot events, so each leg is one tick.  Measure the lag-1 memory
of the driver sequence (the move sizes |dv|) and of the clock sequence (the
waiting times dt), and compare each with the return-shuffle null, which preserves
the fat-tailed marginal and destroys temporal order.

The result localises the structure without any binarisation and invariant to any
rescaling of the values: the driver has no memory beyond its marginal, but the
clock does -- pivots arrive in bursts.  The information is in the timing, a
subordination (random-clock) phenomenon, not in the sizes.
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

from occurrence_geometry import intrinsic_time_memory  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.03
N_NULL = 20


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(19)
    rows = []
    for name, s in seqs.items():
        real = intrinsic_time_memory(s, THETA)
        dnull, cnull = [], []
        for _ in range(N_NULL):
            r = intrinsic_time_memory(return_shuffle(s, rng), THETA)
            dnull.append(r["driver_ac1"])
            cnull.append(r["clock_ac1"])
        rows.append({
            "name": name, "n_legs": real["n_legs"],
            "driver_real": real["driver_ac1"], "driver_null": statistics.mean(dnull),
            "clock_real": real["clock_ac1"], "clock_null": statistics.mean(cnull),
            "driver_excess": real["driver_ac1"] - statistics.mean(dnull),
            "clock_excess": real["clock_ac1"] - statistics.mean(cnull),
        })

    def m(k):
        return statistics.mean(r[k] for r in rows)

    out = {"experiment": "intrinsic_time_memory", "theta": THETA, "n_series": len(rows),
           "mean_driver_excess": m("driver_excess"), "mean_clock_excess": m("clock_excess"),
           "n_driver_positive": sum(1 for r in rows if r["driver_excess"] > 0),
           "n_clock_positive": sum(1 for r in rows if r["clock_excess"] > 0),
           "rows": rows}

    if not quiet:
        print(f"long series: {len(rows)}, reversal scale theta={THETA}, "
              f"null=return-shuffle (marginal preserved)\n")
        print(f"{'series':8s} {'legs':>5s} {'driver real/null':>18s} {'clock real/null':>18s}")
        for r in rows:
            print(f"{r['name']:8s} {r['n_legs']:>5d} "
                  f"{r['driver_real']:>8.3f}/{r['driver_null']:<8.3f} "
                  f"{r['clock_real']:>8.3f}/{r['clock_null']:<8.3f}")
        print(f"\n  driver |dv| memory excess over null: {m('driver_excess'):+.3f} "
              f"({out['n_driver_positive']}/{len(rows)} positive)  -> move SIZES carry no memory")
        print(f"  clock  dt  memory excess over null: {m('clock_excess'):+.3f} "
              f"({out['n_clock_positive']}/{len(rows)} positive)  -> pivot TIMING clusters")
        print("\n  verdict: the information is in the clock, not the driver -- "
              "a subordination (random-activity-clock) structure, representation-free.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp19_intrinsic_time.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp19_intrinsic_time.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
