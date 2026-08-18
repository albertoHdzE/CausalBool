"""Positive and negative controls for the feasibility analyser (protocol rules R3, R4).

An analyser applied to market data is worthless until it has been shown, in the
same run and unchanged, to recover a deterministic system and to reject a random
one. These two controls are the standing pair:

``rule110_frame``
    A cellular automaton is a Boolean network — cell as node, neighbourhood as
    connectivity, rule as shared gate — so its trajectory is a deterministic
    system of exactly the shape the analyser expects. Contradiction must be zero
    and the lookup table exact at the true in-degree.

``random_frame``
    Independent uniform symbols. Contradiction must be high and no parent set may
    beat the shuffle null. This is the falsifiability requirement: a
    representation that fits anything measures nothing.
"""

from __future__ import annotations

import numpy as np
import pandas as pd


def rule110_frame(width: int = 7, steps: int = 200, seed: int = 42) -> pd.DataFrame:
    """Elementary cellular automaton 110 on a periodic lattice.

    Columns are named like the panel's series so that the identical analyser
    call works on both without special-casing. The successor of cell *i* depends
    on cells *i−1*, *i*, *i+1* at the previous step, so the true in-degree is
    three and a search to ``max_indegree=3`` can find it exactly.
    """
    rng = np.random.default_rng(seed)
    state = rng.integers(0, 2, size=width)
    rows = [state.copy()]
    for _ in range(steps - 1):
        left, right = np.roll(state, 1), np.roll(state, -1)
        nxt = np.empty_like(state)
        for i in range(width):
            nxt[i] = (110 >> (4 * left[i] + 2 * state[i] + right[i])) & 1
        state = nxt
        rows.append(state.copy())
    return pd.DataFrame(np.asarray(rows), columns=[f"c{i}" for i in range(width)])


def random_frame(width: int = 7, steps: int = 200, n_values: int = 3,
                 seed: int = 42) -> pd.DataFrame:
    """Independent uniform symbols: the negative control."""
    rng = np.random.default_rng(seed)
    data = rng.integers(0, n_values, size=(steps, width))
    return pd.DataFrame(data, columns=[f"c{i}" for i in range(width)])


def persistent_random_frame(width: int = 7, steps: int = 200, n_values: int = 3,
                            stay: float = 0.75, seed: int = 42) -> pd.DataFrame:
    """A sharper negative control: persistent but causally empty.

    Each column is an independent Markov chain that stays put with probability
    ``stay``. It therefore reproduces the persistence of the real decoded
    regimes — the property the sticky prior was introduced to create — while
    containing no cross-variable structure whatever. If the analyser reports
    structure here, it is reporting autocorrelation and calling it causality.
    """
    rng = np.random.default_rng(seed)
    data = np.empty((steps, width), dtype=np.int64)
    data[0] = rng.integers(0, n_values, size=width)
    for t in range(1, steps):
        keep = rng.random(width) < stay
        jump = rng.integers(0, n_values, size=width)
        data[t] = np.where(keep, data[t - 1], jump)
    return pd.DataFrame(data, columns=[f"c{i}" for i in range(width)])
