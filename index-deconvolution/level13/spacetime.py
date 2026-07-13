"""spacetime.py  (Level 13)

The assessor's idea: rotate the oracle plot into a scale-free (price x time) grid and
treat it as the output repertoire of a Boolean / cellular-automaton network, then run
the programme's own deconvolution on it.

The precise obstruction this addresses. In bitacora 12 the whole-pattern deconvolution
failed on markets because raw prices never recur -- every configuration was unique, so
there was nothing to deconvolve. Coarse-graining the value axis (scale-free, in log
units, so a multiplicative rescaling only relabels the levels) *manufactures*
recurrence: coarse price levels repeat. The deconvolution becomes well-posed. Then the
honest question is whether the coarse level-dynamics obey a deterministic rule -- a
Boolean/CA law -- or whether they are as ruleless as the daily direction was.

This module builds the scale-free symbolisation and the determinism analyser (the same
logic that separated a rule-110 CA from a market in bitacora 06), plus two controls: a
deterministic logistic map (must read structured) and helpers for the null.

Standard library only; deterministic.
"""

from __future__ import annotations

import math


def logistic_series(n: int, r: float = 4.0, x0: float = 0.3) -> list[float]:
    """A deterministic chaotic control: the logistic map, mapped to a positive series."""
    x = x0
    out = []
    for _ in range(n):
        x = r * x * (1.0 - x)
        out.append(math.exp(x))              # positive, so the log-symboliser applies
    return out


def symbolise_log(series: list[float], h: float) -> list[int]:
    """Scale-free coarse-graining: symbol = floor(log(price) / h), relabelled to 0..K-1.

    Because it acts on log-price, a multiplicative rescaling of the series (pounds,
    dollars, grams) shifts every symbol by the same constant and leaves the transition
    structure identical -- the agnostic, scale-free encoding the idea asks for. ``h`` is
    the bin width in log units (the coarseness); sweep it, never fix it.
    """
    levels = [int(math.floor(math.log(p) / h)) for p in series if p > 0]
    if not levels:
        return []
    lo = min(levels)
    return [v - lo for v in levels]


def recurrence_and_determinism(symbols: list[int], w: int) -> dict:
    """Is the next symbol a deterministic function of the last ``w`` symbols?

    Returns:
      recurrence      -- fraction of length-w windows that recur (occur >= 2 times);
                         this is the b12 obstruction: 0 means nothing to deconvolve.
      contradiction   -- among recurring windows, the fraction that map to more than one
                         next symbol (0 = deterministic rule, 1 = pure noise).
      accuracy        -- best deterministic accuracy (majority next symbol per window).
      base_rate       -- accuracy of always predicting the commonest symbol.
      lift            -- accuracy - base_rate.
    """
    n = len(symbols)
    if n <= w + 1:
        return {"recurrence": 0.0, "contradiction": float("nan"),
                "accuracy": float("nan"), "base_rate": float("nan"),
                "lift": float("nan"), "n_windows": 0}
    from collections import Counter
    nexts: dict[tuple, Counter] = {}
    for t in range(n - w):
        key = tuple(symbols[t:t + w])
        nexts.setdefault(key, Counter())[symbols[t + w]] += 1
    total = n - w
    recurring = {k: c for k, c in nexts.items() if sum(c.values()) >= 2}
    n_recur_windows = sum(sum(c.values()) for c in recurring.values())
    recurrence = n_recur_windows / total if total else 0.0
    contradictory = sum(1 for c in recurring.values() if len(c) > 1)
    contradiction = contradictory / len(recurring) if recurring else float("nan")
    # best deterministic accuracy: majority next symbol per window
    correct = sum(c.most_common(1)[0][1] for c in nexts.values())
    accuracy = correct / total
    marg = Counter(symbols[w:])
    base = marg.most_common(1)[0][1] / total if marg else 0.0
    return {"recurrence": recurrence, "contradiction": contradiction,
            "accuracy": accuracy, "base_rate": base, "lift": accuracy - base,
            "n_windows": total}
