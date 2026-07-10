"""unit_survival.py  (Level 4)

Decide which candidate units (bit columns) carry any temporal structure at all,
by comparing a battery of structure statistics against a time-shuffle null.

A unit that never departs from its own shuffle is inert and contributes no rule;
it is discarded.  A unit whose statistics fall far from the shuffle carries order,
and its occurrence set is worth decomposing.  The shuffle preserves the marginal
(the number of ones) and destroys only the temporal arrangement, so any surviving
signal is a property of the arrangement, not of the density.

Three structure statistics, each sensitive to a different kind of arrangement:

  * LZ76 complexity        -- low means compressible / repetitive.
  * longest run of ones    -- high means the ones cluster into bursts.
  * lag-1 autocorrelation  -- high positive means persistence (a one tends to be
                              followed by a one), the direct signature of
                              clustering and the quantity a forecast exploits.

All statistics are reported as z-scores against the shuffle distribution, so they
are comparable across units and across sequences of different density.
"""

from __future__ import annotations

import os
import random
import statistics
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "level3"))

from behaviour_table import lz76_complexity  # noqa: E402


def longest_run_of_ones(bits: list[int]) -> int:
    best = cur = 0
    for b in bits:
        cur = cur + 1 if b else 0
        best = max(best, cur)
    return best


def lag1_autocorr(bits: list[int]) -> float:
    """Pearson autocorrelation at lag 1.  0 under independence."""
    n = len(bits)
    if n < 2:
        return 0.0
    mean = sum(bits) / n
    var = sum((b - mean) ** 2 for b in bits)
    if var == 0:
        return 0.0
    cov = sum((bits[t] - mean) * (bits[t + 1] - mean) for t in range(n - 1))
    return cov / var


_STATS = {
    "lz": lz76_complexity,
    "max_run": longest_run_of_ones,
    "autocorr1": lag1_autocorr,
}


def shuffle_z(bits: list[int], stat, n_shuffle: int, rng: random.Random) -> float:
    """z-score of ``stat(bits)`` against ``n_shuffle`` time-shuffles."""
    obs = stat(bits)
    b = bits[:]
    draws = []
    for _ in range(n_shuffle):
        rng.shuffle(b)
        draws.append(stat(b))
    mu = statistics.mean(draws)
    sd = statistics.pstdev(draws)
    if sd == 0:
        return 0.0
    return (obs - mu) / sd


def survival_report(bits: list[int], n_shuffle: int = 200, seed: int = 0) -> dict:
    """Structure z-scores for one unit, plus a boolean survival verdict.

    A unit survives if any of its structure statistics is at least two shuffle
    standard deviations from the null (|z| >= 2), the usual two-sigma bar.
    """
    rng = random.Random(seed)
    ones = sum(bits)
    if ones == 0 or ones == len(bits):
        return {"ones": ones, "degenerate": True, "survives": False,
                "z": {k: 0.0 for k in _STATS}}
    z = {name: shuffle_z(bits, stat, n_shuffle, rng) for name, stat in _STATS.items()}
    survives = any(abs(v) >= 2.0 for v in z.values())
    return {"ones": ones, "degenerate": False, "survives": survives, "z": z}
