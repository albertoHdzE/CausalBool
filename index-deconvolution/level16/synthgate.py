"""synthgate.py  (Level 16)

The clock as a synthetic gate-network: matching the occurrence set to the fractal branch
of the original method.

The original index-set method reads a gate's output as an occurrence set with an exact
behaviour formula: a pivot plus an offset family (AND), or a band-union (OR), over the
dyadically-ordered exhaustive repertoire. The self-similarity there is deterministic and
comes from the NESTED dyadic structure -- node i ticks at 2^i, each scale nested inside
the next -- which the behaviour table exposes as a constant (n+1)/n ratio column and a
nested run-length ("repetitions of repetitions") compression: the fractal phi_K branch.

A market clock is not deterministic, so it cannot have an exact index-set formula. But we
can ask which synthetic construction reproduces its self-similar SIGNATURE. Three
candidates, mapping to three readings of the gate picture:

  superpose  -- a flat OR / band-union of independent multi-scale clocks (a union of bands
                at geometric rates). Palm-Khinchin makes this Poisson: Fano exponent ~ 0.
  branching  -- a self-exciting cascade (each event begets events): the Hawkes reading.
                Produces clustering but under-shoots the self-similarity.
  nested     -- the fractal phi_K reading: repetitions of repetitions, coarse bursts each
                subdivided into finer bursts by a geometric ratio r. Self-similar by
                construction, tunable through the market's exponent.

The signature is the Fano-factor exponent alpha (F(T) ~ T^alpha; 0 = renewal/flat,
0<alpha<1 = self-similar). Standard library only; deterministic and seeded.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level6"))

from point_process import fano_exponent  # noqa: E402

WINDOWS = [10, 20, 40, 80, 160, 320]


def superpose(n_events: int, K: int, r: float, T: int, seed: int) -> list[int]:
    """Flat OR of K independent Poisson sub-clocks at geometric rates (band-union)."""
    rng = random.Random(seed)
    weights = [r ** k for k in range(K)]
    wsum = sum(weights)
    ev = set()
    for k in range(K):
        rate = (n_events * weights[k] / wsum) / T
        t = 0.0
        while t < T:
            t += rng.expovariate(rate) if rate > 0 else T
            if t < T:
                ev.add(int(t))
    return sorted(ev)


def branching(n_seeds: int, p_child: float, decay: float, T: int, seed: int) -> list[int]:
    """Self-exciting cascade (Hawkes-like cluster process): each event may beget a child."""
    rng = random.Random(seed)
    ev = [rng.uniform(0, T) for _ in range(n_seeds)]
    out = list(ev)
    i = 0
    while i < len(ev) and len(ev) < 40000:
        p = ev[i]
        i += 1
        if rng.random() < p_child:
            c = p + rng.expovariate(1.0 / decay)
            if c < T:
                ev.append(c)
                out.append(c)
    return sorted(int(x) for x in out if 0 <= x < T)


def nested(levels: int, b: int, r: float, span: float, T: int, seed: int) -> list[int]:
    """Fractal phi_K construction: coarse bursts, each subdivided b-fold by ratio r.

    Repetitions of repetitions: seeds at spacing ``span``; each seed spawns b children at
    a finer scale span/r, recursively for ``levels`` levels. This is the nested run-length
    structure of the behaviour table, made stochastic.
    """
    rng = random.Random(seed)
    n_seeds = max(1, int(T / span))
    ev = [rng.uniform(0, T) for _ in range(n_seeds)]
    width = span
    for _ in range(levels):
        width /= r
        new = []
        for e in ev:
            for _ in range(b):
                new.append(e + rng.uniform(-width, width))
        ev = ev + new
    return sorted(int(x) for x in ev if 0 <= x < T)


def alpha_of(events: list[int], T: int) -> float:
    return fano_exponent(events, T, WINDOWS).get("alpha", float("nan"))


def fit_nested_alpha(target_alpha: float, n_events: int, T: int,
                     seeds: int = 3) -> dict:
    """Find nested (levels, r) whose Fano exponent matches ``target_alpha``.

    Coarse search over depth and geometric ratio; branching b and span are set to land
    near ``n_events``. Returns the best (levels, r), the achieved alpha and the residual.
    """
    best = None
    for levels in (3, 4, 5, 6):
        b = 2
        # choose span so that n_seeds * (b+1)^levels ~ n_events
        target_seeds = max(1, n_events / ((b + 1) ** levels))
        span = max(2.0, T / target_seeds)
        for r in (1.6, 1.8, 2.0, 2.4, 2.8, 3.2, 3.8):
            alphas = [alpha_of(nested(levels, b, r, span, T, s), T) for s in range(seeds)]
            alphas = [a for a in alphas if a == a]
            if not alphas:
                continue
            a = sum(alphas) / len(alphas)
            resid = abs(a - target_alpha)
            if best is None or resid < best["residual"]:
                best = {"levels": levels, "b": b, "r": r, "span": span,
                        "alpha": a, "residual": resid}
    return best or {"levels": 0, "r": 0.0, "alpha": float("nan"), "residual": float("nan")}
