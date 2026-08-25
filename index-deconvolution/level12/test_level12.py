"""test_level12.py

Correctness of the symbolic-action decomposition.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from actions import buy_sell_times, action_order_entropy, shortlong_forecast  # noqa: E402
from pivots import directional_change_pivots  # noqa: E402


def _wave(n_cycles=10, leg=6, amp=0.05):
    prices, v, up = [], 100.0, True
    for _ in range(n_cycles):
        for _ in range(leg):
            v *= (1 + amp) if up else 1 / (1 + amp)
            prices.append(v)
        up = not up
    return prices


def test_buy_sell_partition_covers_pivots():
    s = _wave()
    piv = [p.index for p in directional_change_pivots(s, 0.05)]
    buys, sells = buy_sell_times(s, 0.05)
    assert sorted(buys + sells) == piv
    assert set(buys).isdisjoint(sells)


def test_buys_are_troughs_sells_are_peaks():
    s = _wave()
    theta = 0.05
    piv = {p.index: p.kind for p in directional_change_pivots(s, theta)}
    buys, sells = buy_sell_times(s, theta)
    assert all(piv[i] == -1 for i in buys)      # troughs
    assert all(piv[i] == +1 for i in sells)     # peaks


def test_action_order_entropy_is_near_zero():
    # forced alternation buy/sell -> conditional entropy of the next action ~ 0 bits
    s = _wave(n_cycles=30)
    ent = action_order_entropy(s, 0.05)
    assert ent["order_entropy_bits"] < 0.05
    assert ent["n_actions"] > 10


def test_shortlong_forecast_handles_short_input():
    out = shortlong_forecast([0, 1, 2, 3])
    assert out["n_test"] == 0 and math.isnan(out["lift"])


def test_shortlong_forecast_beats_base_on_clustered_gaps():
    # gaps come in long RUNS of short then long (persistent) -> a persistence-window
    # forecast should beat the base rate; the anti-persistent case would defeat it,
    # which is the honest behaviour of a persistence predictor.
    times = [0]
    short, long = 1, 9
    for block in range(20):
        g = short if block % 2 == 0 else long
        for _ in range(10):
            times.append(times[-1] + g)
    out = shortlong_forecast(times, window=3)
    assert out["acc"] > out["base"]
    assert out["n_test"] > 0


def test_determinism():
    s = _wave(n_cycles=25)
    a = action_order_entropy(s, 0.05)
    b = action_order_entropy(s, 0.05)
    assert a == b
