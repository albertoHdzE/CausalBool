"""test_level14.py

Correctness of the behaviour-table / behaviour-formula machinery for buy and sell.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from behaviour import (buy_sell_occurrences, behaviour_table, exact_formula_score,  # noqa: E402
                       compression, _ecdf_ks, intensity, hawkes_formula)


def _wave(n_cycles=12, leg=6, amp=0.05):
    prices, v, up = [], 100.0, True
    for _ in range(n_cycles):
        for _ in range(leg):
            v *= (1 + amp) if up else 1 / (1 + amp)
            prices.append(v)
        up = not up
    return prices


def test_buy_sell_disjoint_and_interleave():
    s = _wave()
    buys, sells = buy_sell_occurrences(s, 0.05)
    assert set(buys).isdisjoint(sells)
    merged = sorted([(t, "b") for t in buys] + [(t, "s") for t in sells])
    kinds = [k for _, k in merged]
    # perfect interleaving: no two consecutive of the same kind
    assert all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))


def test_behaviour_table_columns():
    tbl = behaviour_table([0, 3, 6, 12, 24])
    assert tbl[0]["gap"] is None and tbl[0]["ratio"] is None
    assert tbl[1]["gap"] == 3 and tbl[1]["ratio"] is None
    assert tbl[2]["gap"] == 3 and tbl[2]["ratio"] == 1.0
    assert tbl[3]["gap"] == 6 and tbl[3]["ratio"] == 2.0


def test_exact_formula_detects_periodic():
    periodic = list(range(0, 1000, 7))                 # constant gap 7
    sc = exact_formula_score(periodic)
    assert sc["cv_gaps"] < 0.05 and sc["exact"]


def test_exact_formula_detects_geometric():
    geo = [0]
    g = 2
    for _ in range(15):
        geo.append(geo[-1] + g)
        g = int(round(g * 1.5))
    sc = exact_formula_score(geo)
    assert sc["cv_ratios"] < 0.15                       # ratios ~ constant (1.5)


def test_market_has_no_exact_formula():
    import random
    rng = random.Random(0)
    p = [100.0]
    for _ in range(6000):
        p.append(p[-1] * math.exp(0.02 * rng.gauss(0, 1)))
    buys, _ = buy_sell_occurrences(p, 0.02)
    sc = exact_formula_score(buys)
    assert not sc["exact"]                               # noisy gaps: no closed form
    assert sc["cv_gaps"] > 0.3


def test_compression_ratio_large():
    times = list(range(0, 10000, 13))
    c = compression(times, 10000.0)
    assert c["ratio"] > 5                                # formula much smaller than raw set


def test_ks_zero_for_identical():
    assert _ecdf_ks([1.0, 2, 3, 4], [1.0, 2, 3, 4]) == 0.0
    assert _ecdf_ks([1.0, 1, 1], [9.0, 9, 9]) == 1.0


def test_intensity_rises_after_events():
    times = [100, 101, 102]
    fit = {"mu": 0.01, "alpha": 0.5, "beta": 0.1}
    lam = intensity(times, fit, [99.0, 103.0])
    assert lam[1] > lam[0]                               # intensity higher just after a burst
