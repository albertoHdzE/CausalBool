"""Surrogates — **nulls gate** (G2).

With ~400k sequences and a window search over each, a query runs on the order of 10^7
hypothesis tests. Noise *will* match, and beautifully: a random skewed integer sequence
already finds 9-11 term windows in the corpus. So a raw MDL gain is uninterpretable.
The reported statistic is always the gain **in excess of the null**, with the null's own
location stated separately — never only the difference, because a null centred away from
zero is telling you the pipeline has a cost the null pays too.

Nulls are ordered poorest to richest. Only the richest licenses a positive claim;
beating a poorer one means rediscovering a known law.

Finance (on the price path, so the surrogate pays the full pivot-extraction cost):
  1. ``geometric_random_walk``  matched volatility only
  2. ``return_shuffle``         matched increment marginal, temporal order destroyed
  3. ``block_shuffle``          matched marginal *and* short-range dependence  <- richest

Binary controls (CA, biological networks):
  1. ``bernoulli``              matched flip density
  2. ``gap_shuffle``            matched gap marginal, order destroyed          <- richest

``gap_shuffle`` also runs on the finance arm, so all three arms share one common null
and can be read on the same footing.
"""

from __future__ import annotations

import math
import random
from collections.abc import Sequence


def log_returns(series: Sequence[float]) -> list[float]:
    return [
        math.log(series[t] / series[t - 1])
        for t in range(1, len(series))
        if series[t - 1] > 0 and series[t] > 0
    ]


def rebuild_from_returns(returns: Sequence[float], x0: float = 100.0) -> list[float]:
    s = [x0]
    for r in returns:
        s.append(s[-1] * math.exp(r))
    return s


def return_shuffle(series: Sequence[float], rng: random.Random) -> list[float]:
    """Shuffle log-increments and rebuild: fat-tail marginal exact, order destroyed."""
    r = log_returns(series)
    rng.shuffle(r)
    return rebuild_from_returns(r)


def block_shuffle(series: Sequence[float], rng: random.Random, block: int = 20) -> list[float]:
    """Shuffle *blocks* of log-increments: keeps dependence up to ``block``.

    The richest finance null. Anything that survives this is structure on a timescale
    longer than the block, not a consequence of the marginal or of short-range memory.
    """
    r = log_returns(series)
    blocks = [r[i : i + block] for i in range(0, len(r), block)]
    rng.shuffle(blocks)
    return rebuild_from_returns([x for b in blocks for x in b])


def geometric_random_walk(
    n: int, sigma: float, rng: random.Random, x0: float = 100.0
) -> list[float]:
    s = [x0]
    for _ in range(n):
        s.append(s[-1] * math.exp(sigma * rng.gauss(0, 1)))
    return s


def realized_sigma(series: Sequence[float]) -> float:
    r = log_returns(series)
    if len(r) < 2:
        return 0.0
    mu = sum(r) / len(r)
    return math.sqrt(sum((x - mu) ** 2 for x in r) / (len(r) - 1))


def bernoulli(n: int, p: float, rng: random.Random) -> list[int]:
    """A binary series with matched flip density — the poorest control-arm null."""
    return [1 if rng.random() < p else 0 for _ in range(n)]


def gap_shuffle(gaps_: Sequence[int], rng: random.Random) -> list[int]:
    """Permute the target's own gaps: marginal exact, all temporal order destroyed.

    Applied to the target rather than to the source series, so it isolates order from
    every other property of the pipeline.
    """
    out = list(gaps_)
    rng.shuffle(out)
    return out


def flip_density(series: Sequence[int]) -> float:
    if len(series) < 2:
        return 0.0
    return sum(series[i] != series[i - 1] for i in range(1, len(series))) / (len(series) - 1)


def rank_p_value(observed: float, null_values: Sequence[float]) -> float:
    """One-sided rank p: P(null >= observed), with the standard +1 correction.

    Never smaller than ``1/(len(null_values)+1)`` — the resolution the surrogate count
    actually buys. Reported alongside the observed value and the null's location, not
    instead of them.
    """
    k = sum(1 for v in null_values if v >= observed)
    return (k + 1) / (len(null_values) + 1)
