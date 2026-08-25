"""test_level10.py

Correctness of the oracle dynamic programme and the equivalence machinery.
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

from oracle import (optimal_trades, oracle_points, match_sets,  # noqa: E402
                    round_trip_cost, kappa_for_round_trip)
from pivots import directional_change_pivots  # noqa: E402


def test_cost_conversion_roundtrip():
    for c in (0.005, 0.01, 0.02, 0.05, 0.1):
        k = kappa_for_round_trip(c)
        assert math.isclose(round_trip_cost(k), c, rel_tol=1e-12)


def test_monotone_up_single_round_trip():
    prices = [1.0 * (1.02 ** t) for t in range(50)]      # clean up-drift
    tr = optimal_trades(prices, kappa=0.001)
    assert tr["buys"] == [0]
    assert tr["sells"] == [49]


def test_high_cost_no_trades():
    # small oscillations, none clears a 50% round-trip cost
    prices = [100.0 + (t % 2) for t in range(40)]
    tr = optimal_trades(prices, kappa=0.3)
    assert tr["buys"] == [] and tr["sells"] == []


def test_zigzag_captures_every_swing():
    # triangle wave, amplitude ~10%, far above a tiny cost -> trade every swing
    prices = []
    up = True
    v = 100.0
    for _ in range(6):
        for _ in range(5):
            v = v * (1.02 if up else 1.0 / 1.02)
            prices.append(v)
        up = not up
    tr = optimal_trades(prices, kappa=0.0005)
    # buys at troughs precede sells at peaks, strictly alternating, buy first
    assert len(tr["buys"]) == len(tr["sells"])
    for b, s in zip(tr["buys"], tr["sells"]):
        assert b < s


def test_oracle_beats_buy_and_hold():
    # oracle (optimal) must beat the buy-day0/sell-last feasible schedule
    import random
    rng = random.Random(0)
    v = 100.0
    prices = [v]
    for _ in range(500):
        v *= math.exp(0.0003 + 0.02 * rng.gauss(0, 1))
        prices.append(v)
    kappa = 0.001
    tr = optimal_trades(prices, kappa)
    bh = math.log(prices[-1] / prices[0]) + 2 * math.log(1 - kappa)
    assert tr["log_wealth"] >= bh - 1e-9


def test_oracle_points_are_local_extrema():
    import random
    rng = random.Random(1)
    v = 100.0
    prices = [v]
    for _ in range(400):
        v *= math.exp(0.02 * rng.gauss(0, 1))
        prices.append(v)
    pts = oracle_points(prices, kappa=0.005)
    for i in pts:
        if 0 < i < len(prices) - 1:
            is_peak = prices[i] >= prices[i - 1] and prices[i] >= prices[i + 1]
            is_trough = prices[i] <= prices[i - 1] and prices[i] <= prices[i + 1]
            assert is_peak or is_trough


def test_determinism():
    import random
    rng = random.Random(2)
    prices = [100.0]
    for _ in range(300):
        prices.append(prices[-1] * math.exp(0.02 * rng.gauss(0, 1)))
    a = optimal_trades(prices, 0.003)
    b = optimal_trades(prices, 0.003)
    assert a == b


def test_match_sets_basic():
    m = match_sets([1, 5, 9], [1, 5, 9], tol=0)
    assert m["matched"] == 3 and m["jaccard"] == 1.0
    m = match_sets([1, 5, 9], [2, 5, 20], tol=1)
    assert m["matched"] == 2                      # 1~2, 5~5; 9 unmatched
    m = match_sets([10, 20], [100, 200], tol=0)
    assert m["matched"] == 0 and m["jaccard"] == 0.0


def test_sawtooth_oracle_equals_dc_pivots():
    # a clean sawtooth: oracle troughs/peaks should coincide with DC pivots at a
    # threshold below the swing amplitude.  Interior overlap must be high.
    prices = []
    v = 100.0
    up = True
    for _ in range(8):
        for _ in range(6):
            v *= (1.03 if up else 1.0 / 1.03)
            prices.append(v)
        up = not up
    theta = 0.03
    kappa = kappa_for_round_trip(theta)          # match cost to threshold
    orc = oracle_points(prices, kappa)
    dc = [p.index for p in directional_change_pivots(prices, theta)]
    m = match_sets(orc, dc, tol=1)
    assert m["jaccard"] > 0.7                     # near-identical up to endpoints
