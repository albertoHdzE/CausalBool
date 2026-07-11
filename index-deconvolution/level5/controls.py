"""controls.py  (Level 5)

Shared loaders and null models for the representation-free experiments.

The null that matters here is the return-shuffle: shuffle the log-increments of a
sequence and rebuild it.  This preserves the marginal distribution of increments
(the fat tails) exactly and destroys only their temporal order, so any structure
that is stronger on the real series than on this null is temporal, not a mechanical
consequence of the marginal.  It is the correct control for a construction (the
directional-change pivots) whose statistics are sensitive to the increment
distribution.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from finance import load_yahoo_close  # noqa: E402

LONG_DIR = os.path.join(ROOT, "finance", "data_long")


def load_long_sequences() -> dict[str, list[float]]:
    seqs = {}
    for f in sorted(os.listdir(LONG_DIR)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(LONG_DIR, f))
            seqs[f[:-5]] = [px[d] for d in sorted(px)]
    return seqs


def log_returns(series: list[float]) -> list[float]:
    return [math.log(series[t] / series[t - 1]) for t in range(1, len(series))
            if series[t - 1] > 0 and series[t] > 0]


def rebuild_from_returns(returns: list[float], x0: float = 100.0) -> list[float]:
    s = [x0]
    for r in returns:
        s.append(s[-1] * math.exp(r))
    return s


def return_shuffle(series: list[float], rng: random.Random) -> list[float]:
    r = log_returns(series)
    rng.shuffle(r)
    return rebuild_from_returns(r)


def geometric_random_walk(n: int, sigma: float, rng: random.Random,
                          x0: float = 100.0) -> list[float]:
    s = [x0]
    for _ in range(n):
        s.append(s[-1] * math.exp(sigma * rng.gauss(0, 1)))
    return s
