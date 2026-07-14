"""test_level18.py

Correctness of the individual/universal model machinery and the risk-timing backtest.
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
sys.path.insert(0, os.path.join(ROOT, "level9"))

from models import (universal_shape, universal_for_stock, causal_intensity,  # noqa: E402
                    risk_timing_backtest, _sharpe, _max_drawdown)


def test_universal_shape_median():
    fits = [{"branching_ratio": 0.4, "beta": 0.1, "n_events": 100},
            {"branching_ratio": 0.6, "beta": 0.2, "n_events": 100},
            {"branching_ratio": 0.5, "beta": 0.15, "n_events": 100}]
    sh = universal_shape(fits)
    assert abs(sh["n"] - 0.5) < 1e-9 and abs(sh["beta"] - 0.15) < 1e-9


def test_universal_for_stock_reproduces_rate():
    sh = {"n": 0.5, "beta": 0.2}
    m = universal_for_stock(0.1, sh)
    assert abs(m["mu"] - 0.05) < 1e-12          # (1-n)*rate
    assert abs(m["alpha"] - 0.1) < 1e-12         # n*beta


def test_causal_intensity_rises_after_events():
    lam = causal_intensity([100, 101, 102], 200, mu=0.01, alpha=0.5, beta=0.1)
    assert lam[103] > lam[50]                    # elevated just after a burst
    assert all(l >= 0 for l in lam)


def test_causal_intensity_is_causal():
    # an event at day 150 must not affect intensity before it
    a = causal_intensity([150], 200, 0.01, 0.5, 0.1)
    assert abs(a[100] - 0.01) < 1e-9             # baseline only, before the event


def test_sharpe_and_drawdown():
    assert _sharpe([0.02, 0.01, 0.015, 0.005]) > 0        # positive mean, some variance
    assert _sharpe([-0.02, -0.01, -0.015]) < 0
    assert _max_drawdown([1.0, 1.2, 0.6, 0.9]) <= -0.49   # 1.2 -> 0.6 is -50%


def test_risk_timing_runs_and_derisks():
    rng = random.Random(0)
    rets = [0.0003 + 0.01 * rng.gauss(0, 1) for _ in range(1000)]
    lam = [0.05 + 0.02 * rng.random() for _ in range(1000)]
    out = risk_timing_backtest(rets, lam, t_start=700)
    assert "sharpe_timed" in out and "sharpe_bh" in out
    assert len(out["equity_timed"]) == len(out["equity_bh"])
