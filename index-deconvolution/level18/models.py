"""models.py  (Level 18)

Individual (per-stock) versus universal clock models, and an honest practical comparison.

Two ways to model the clock:

  per-stock  -- fit the three Hawkes numbers (mu, alpha, beta) to each stock's own train
                events. Tailored, but each fit sees only ~700 events, so it is noisy.
  universal  -- share the shape across all stocks: a single branching ratio n and decay
                beta (the median of the per-stock train fits), with only the baseline
                mu set per stock from its own rate. One law, one per-stock scale number.

We compare them out of sample on two honest metrics: the held-out forecast quality (does
tailoring beat pooling, or does pooling win by robustness?) and a risk-timing backtest
(scale exposure down when the model forecasts a burst of turns -- the one licensed use;
direction stays unforecastable, so this is a risk comparison, never a return one).

Standard library only; deterministic. Reuses the Level 9 Hawkes.
"""

from __future__ import annotations

import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level9"))

from hawkes import fit_hawkes  # noqa: E402


def universal_shape(train_fits: list[dict]) -> dict:
    """The pooled universal shape: median branching ratio n and decay beta over stocks."""
    ns = [f["branching_ratio"] for f in train_fits if f["n_events"] >= 10]
    betas = [f["beta"] for f in train_fits if f["n_events"] >= 10]
    return {"n": statistics.median(ns) if ns else 0.0,
            "beta": statistics.median(betas) if betas else 1.0}


def universal_for_stock(rate: float, shape: dict) -> dict:
    """Instantiate the universal model for a stock: shared (n, beta), per-stock baseline.

    With branching ratio n, a fraction (1 - n) of the intensity is baseline, so
    mu = (1 - n) * rate reproduces the stock's average rate; alpha = n * beta.
    """
    n, beta = shape["n"], shape["beta"]
    return {"mu": (1.0 - n) * rate, "alpha": n * beta, "beta": beta}


def causal_intensity(event_times: list[int], n_days: int,
                     mu: float, alpha: float, beta: float) -> list[float]:
    """The causal Hawkes intensity lambda(t) on each day, built only from the past."""
    ev = sorted(event_times)
    lam = [0.0] * n_days
    A = 0.0
    last = 0
    ei = 0
    for t in range(n_days):
        A *= math.exp(-beta * (t - last))
        while ei < len(ev) and ev[ei] <= t - 1:
            A += math.exp(-beta * (t - ev[ei]))
            ei += 1
        last = t
        lam[t] = mu + alpha * A
    return lam


def _sharpe(rets: list[float]) -> float:
    if len(rets) < 2:
        return 0.0
    m = statistics.mean(rets)
    sd = statistics.pstdev(rets)
    return (m / sd) * math.sqrt(252) if sd > 0 else 0.0


def _max_drawdown(equity: list[float]) -> float:
    peak = equity[0]
    mdd = 0.0
    for v in equity:
        peak = max(peak, v)
        mdd = min(mdd, v / peak - 1.0)
    return mdd


def risk_timing_backtest(returns: list[float], lam: list[float], t_start: int,
                         leverage_cap: float = 2.0, cost: float = 0.0005) -> dict:
    """Scale exposure inversely to the forecast turn-intensity (de-risk in bursts).

    On the held-out window (from ``t_start``), exposure_t = clip(ref / lam_t, 0, cap),
    where ref is the trailing median intensity; strategy return = exposure_t *
    return_{t+1}, net of a turnover cost. Returns Sharpe, max drawdown and terminal
    wealth of the timed book and of buy-and-hold, on the same window.
    """
    n = min(len(returns), len(lam))
    if t_start >= n - 10:
        return {}
    ref = statistics.median([l for l in lam[max(0, t_start - 250):t_start] if l > 0] or [1.0])
    strat, bh = [], []
    eq_s, eq_b = [1.0], [1.0]
    prev_e = 1.0
    for t in range(t_start, n - 1):
        lt = lam[t] if lam[t] > 0 else ref
        e = max(0.0, min(leverage_cap, ref / lt))
        r = returns[t + 1]
        sr = e * r - cost * abs(e - prev_e)
        prev_e = e
        strat.append(sr)
        bh.append(r)
        eq_s.append(eq_s[-1] * (1 + sr))
        eq_b.append(eq_b[-1] * (1 + r))
    return {"sharpe_timed": _sharpe(strat), "sharpe_bh": _sharpe(bh),
            "mdd_timed": _max_drawdown(eq_s), "mdd_bh": _max_drawdown(eq_b),
            "wealth_timed": eq_s[-1], "wealth_bh": eq_b[-1],
            "equity_timed": eq_s, "equity_bh": eq_b}


def fit_train(event_times: list[int], t_train: int) -> dict:
    tr = [float(e) for e in event_times if e <= t_train]
    return fit_hawkes(tr, float(t_train))
