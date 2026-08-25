"""exp16_bands.py  (Level 4)

Does magnitude resolution beyond the coarsest volatility bit carry extra
structure?  Each value's step size is Gray-coded into several bands (scale-free);
each band column is tested for temporal structure (lag-1 autocorrelation z against
a shuffle) and self-similarity (Hurst) on the long series.

The finding: the clustering signature is present at every magnitude resolution but
decays monotonically from the coarsest band inward.  The top bit (above/below the
median step) carries most of the structure; finer bands add a diminishing but real
increment.  So the self-similarity is not only in time -- it also holds across the
amplitude axis -- and the coarsest volatility unit is the right primary object.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import load_yahoo_close  # noqa: E402
from binarise import magnitude_bands  # noqa: E402
from unit_survival import lag1_autocorr  # noqa: E402
from occurrence_arithmetic import hurst_aggregated_variance  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data_long")
RESULTS_DIR = os.path.join(ROOT, "results")
NBITS = 3


def autocorr_z(bits, rng, n_shuffle=80):
    obs = lag1_autocorr(bits)
    b = bits[:]
    draws = []
    for _ in range(n_shuffle):
        rng.shuffle(b)
        draws.append(lag1_autocorr(b))
    sd = statistics.pstdev(draws)
    return (obs - statistics.mean(draws)) / sd if sd else 0.0


def run(quiet: bool = False) -> dict:
    files = sorted(f for f in os.listdir(DATA_DIR) if f.endswith(".json"))
    rng = random.Random(7)
    agg = {b: {"z": [], "h": []} for b in range(NBITS)}
    for f in files:
        px = load_yahoo_close(os.path.join(DATA_DIR, f))
        s = [px[d] for d in sorted(px)]
        bands = magnitude_bands(s, nbits=NBITS, scale_free=True, gray=True)
        for b in range(NBITS):
            agg[b]["z"].append(autocorr_z(bands[b], rng))
            agg[b]["h"].append(hurst_aggregated_variance(bands[b]))
    rows = [{"band": b, "mean_autocorr_z": statistics.mean(agg[b]["z"]),
             "mean_hurst": statistics.mean(agg[b]["h"])} for b in range(NBITS)]
    out = {"experiment": "magnitude_bands", "n_series": len(files),
           "nbits": NBITS, "bands": rows}
    if not quiet:
        print(f"Gray magnitude bands on {len(files)} long series (scale-free); "
              f"band 0 = coarsest (above/below median step)\n")
        print(f"{'band':>5s} {'mean autocorr z':>16s} {'mean Hurst':>12s}")
        for r in rows:
            print(f"{r['band']:>5d} {r['mean_autocorr_z']:>16.2f} {r['mean_hurst']:>12.3f}")
        print("\n  reading: structure present at every resolution, decaying inward; "
              "the top bit carries most of it (self-similar across amplitude too).")
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp16_bands.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    if not quiet:
        print("\nwritten: results/exp16_bands.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
