"""test_level8.py

Deterministic tests for the strategy engine: the metrics must be correct on known
paths, the volatility forecasts must use only the past, and volatility targeting
must actually reduce realised volatility relative to buy-and-hold on a volatile
synthetic.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from strategy import (trailing_vol, har_vol, backtest, metrics, TRADING_DAYS)


def test_metrics_max_drawdown_known():
    m = metrics([0.10, -0.50, 0.10])
    # cumulative 1.10, 0.55, 0.605; peak 1.10 -> trough 0.55 -> dd -0.5
    assert abs(m["max_drawdown"] - (0.55 / 1.10 - 1)) < 1e-9


def test_metrics_sharpe_positive_constant():
    m = metrics([0.001] * 500)
    assert m["ann_vol"] == 0.0
    assert m["sharpe"] == 0.0            # guarded divide by zero
    assert abs(m["ann_return"] - 0.001 * TRADING_DAYS) < 1e-9


def test_cvar_is_mean_of_worst_tail():
    d = [(-0.05 if i < 5 else 0.01) for i in range(100)]
    m = metrics(d)
    assert abs(m["cvar_5pct_daily"] - (-0.05)) < 1e-9    # worst 5% are the -0.05 days


def test_vol_forecasts_use_only_past_and_are_positive():
    rng = random.Random(1)
    r = [0.01 * rng.gauss(0, 1) for _ in range(600)]
    # forecast at t must not depend on r[t:] : mutate the future, forecast unchanged
    v1 = har_vol(r, 300)
    r2 = r[:300] + [999.0] * 300
    v2 = har_vol(r2, 300)
    assert abs(v1 - v2) < 1e-12
    assert trailing_vol(r, 300) > 0 and har_vol(r, 300) > 0


def test_voltarget_reduces_realised_vol():
    # two synthetic instruments with a calm then turbulent regime
    rng = random.Random(2)
    n, T = 2, 3000
    R = [[0.0] * T for _ in range(n)]
    for i in range(n):
        for t in range(T):
            sig = 0.005 if t < T // 2 else 0.03      # volatility regime shift
            R[i][t] = sig * rng.gauss(0, 1)
    bh = backtest(R, scheme="buyhold", warmup=252)
    vt = backtest(R, scheme="voltarget", vol_forecast="trailing",
                  target_vol=0.10, warmup=252)
    m_bh = metrics(bh["daily"], warmup=252)
    m_vt = metrics(vt["daily"], warmup=252)
    assert m_vt["ann_vol"] < m_bh["ann_vol"]          # targeting caps the turbulent regime


def test_backtest_length_and_warmup_zero():
    rng = random.Random(3)
    R = [[0.001 * rng.gauss(0, 1) for _ in range(1000)] for _ in range(3)]
    bt = backtest(R, scheme="buyhold", warmup=252)
    assert len(bt["daily"]) == 1000
    assert all(x == 0.0 for x in bt["daily"][:252])   # no position during warm-up
