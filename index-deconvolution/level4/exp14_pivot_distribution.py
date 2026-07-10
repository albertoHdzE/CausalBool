"""exp14_pivot_distribution.py  (Level 4)

Characterise how the pivots -- the occurrences of the surviving volatility unit --
are distributed along the index: uniform, clustered, or self-similar.

Three complementary readings, each against the time-shuffle null (which, by
destroying arrangement while keeping density, is memoryless: geometric gaps, a
flat index of dispersion, Hurst 1/2):

  * gap dispersion.  The coefficient of variation of the inter-occurrence gaps.
    A memoryless (geometric) occurrence process has CV = 1.  CV > 1 means
    over-dispersed gaps -- bursts of close occurrences separated by long calms,
    the signature of clustering.

  * index of dispersion across scales.  Variance-to-mean of the occurrence count
    in windows of growing size w.  For a memoryless process it stays near 1 at
    every scale; if it grows with w, the clustering is present at many scales at
    once -- self-similar.

  * Hurst exponent.  A single self-similarity index for the whole unit; H > 1/2 is
    persistent long memory.

Together these say what kind of behaviour rule governs the pivot distribution, the
higher-level object the protocol asks for when the direct sequence is noisy.
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
from binarise import top_magnitude_bit  # noqa: E402
from occurrence_arithmetic import gaps, hurst_aggregated_variance  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
SCALES = [5, 10, 20, 40]


def load_sequences():
    seqs = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_DIR, f))
            seqs[f[:-5]] = [px[d] for d in sorted(px)]
    return seqs


def gap_cv(bits):
    g = gaps(bits)
    if len(g) < 2:
        return float("nan")
    m = statistics.mean(g)
    return statistics.pstdev(g) / m if m else float("nan")


def index_of_dispersion(bits, w):
    counts = [sum(bits[i:i + w]) for i in range(0, len(bits) - w + 1, w)]
    if len(counts) < 2:
        return float("nan")
    m = statistics.mean(counts)
    return (statistics.pvariance(counts) / m) if m else float("nan")


def run(quiet: bool = False) -> dict:
    seqs = load_sequences()
    rng = random.Random(23)
    rows = []
    for name, s in seqs.items():
        bits = top_magnitude_bit(s)
        real = {"cv": gap_cv(bits), "hurst": hurst_aggregated_variance(bits),
                "disp": {w: index_of_dispersion(bits, w) for w in SCALES}}
        # shuffle null
        cvs, hs, disp = [], [], {w: [] for w in SCALES}
        b = bits[:]
        for _ in range(50):
            rng.shuffle(b)
            cvs.append(gap_cv(b))
            hs.append(hurst_aggregated_variance(b))
            for w in SCALES:
                disp[w].append(index_of_dispersion(b, w))
        rows.append({"name": name, "real": real,
                     "shuf_cv": statistics.mean(cvs), "shuf_hurst": statistics.mean(hs),
                     "shuf_disp": {w: statistics.mean(disp[w]) for w in SCALES}})

    mean_cv = statistics.mean(r["real"]["cv"] for r in rows)
    mean_shuf_cv = statistics.mean(r["shuf_cv"] for r in rows)
    mean_h = statistics.mean(r["real"]["hurst"] for r in rows)
    mean_shuf_h = statistics.mean(r["shuf_hurst"] for r in rows)
    disp_real = {w: statistics.mean(r["real"]["disp"][w] for r in rows) for w in SCALES}
    disp_shuf = {w: statistics.mean(r["shuf_disp"][w] for r in rows) for w in SCALES}
    n_cv_above = sum(1 for r in rows if r["real"]["cv"] > r["shuf_cv"])
    n_h_above = sum(1 for r in rows if r["real"]["hurst"] > r["shuf_hurst"])

    out = {"experiment": "pivot_distribution_volatility",
           "mean_gap_cv_real": mean_cv, "mean_gap_cv_shuffle": mean_shuf_cv,
           "n_cv_above_shuffle": n_cv_above,
           "mean_hurst_real": mean_h, "mean_hurst_shuffle": mean_shuf_h,
           "n_hurst_above_shuffle": n_h_above,
           "index_of_dispersion_real": disp_real,
           "index_of_dispersion_shuffle": disp_shuf, "n": len(rows)}

    if not quiet:
        print(f"sequences: {len(rows)}\n")
        print("=== pivot (volatility-occurrence) distribution vs shuffle ===")
        print(f"  gap coefficient of variation : real {mean_cv:.3f}  shuffle {mean_shuf_cv:.3f}  "
              f"({n_cv_above}/{len(rows)} over-dispersed vs shuffle)")
        print(f"  Hurst exponent               : real {mean_h:.3f}  shuffle {mean_shuf_h:.3f}  "
              f"({n_h_above}/{len(rows)} above shuffle)")
        print("  index of dispersion across scales (var/mean of window counts):")
        print(f"    {'window':>8s} {'real':>8s} {'shuffle':>8s}")
        for w in SCALES:
            print(f"    {w:>8d} {disp_real[w]:>8.3f} {disp_shuf[w]:>8.3f}")
        growing = disp_real[SCALES[-1]] > disp_real[SCALES[0]]
        print(f"\n  reading: gaps {'over-dispersed (clustered)' if mean_cv > mean_shuf_cv else 'not over-dispersed'}; "
              f"memory {'self-similar, H>1/2' if mean_h > 0.55 else 'weak'}; "
              f"dispersion {'grows with scale (multi-scale clustering)' if growing else 'flat'}.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp14_pivot_distribution.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp14_pivot_distribution.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
