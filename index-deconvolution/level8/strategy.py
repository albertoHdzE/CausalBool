"""strategy.py  (Level 8)

From the structure discovered in Levels 1-7 to a portfolio strategy, and an honest
account of what it can and cannot do.

What the programme licenses:
  * direction is unforecastable (the sign unit is inert under four independent
    tests), so no part of the strategy bets on the direction of a price;
  * the clock -- volatility / activity -- is forecastable, self-similar and largely
    shared across instruments, so risk is predictable and systematic;
  * sizes are fat-tailed with no memory beyond their marginal, so tail risk must be
    measured directly, not assumed Gaussian.

The strategy that follows is therefore a risk strategy, not a return strategy: it
allocates capital inversely to forecast risk and targets a constant portfolio
volatility, so it de-risks ahead of the forecastable turbulent regimes.  Its aim is
a better risk-adjusted outcome (Sharpe, drawdown, tail loss), not beating the market
on raw return, which the programme says is not possible from this information.

Everything is walk-forward: at each rebalance only past data is used.  Rebalancing
costs a fixed number of basis points per unit of turnover.  Standard library only.
"""

from __future__ import annotations

import math
import statistics

TRADING_DAYS = 252


# ---------------------------------------------------------------------------
# Volatility forecasts (all use only the past)
# ---------------------------------------------------------------------------

def _rvol(daily: list[float]) -> float:
    return statistics.pstdev(daily) if len(daily) > 1 else 0.0


def trailing_vol(daily_returns: list[float], t: int, short: int = 63) -> float:
    """Trailing realised volatility over the last ``short`` days (annualised)."""
    lo = max(0, t - short)
    return _rvol(daily_returns[lo:t]) * math.sqrt(TRADING_DAYS)


def har_vol(daily_returns: list[float], t: int,
            horizons=(21, 63, 252)) -> float:
    """HAR-style multi-horizon realised-volatility forecast (annualised).

    An equal blend of realised volatilities over a short, medium and long horizon.
    This is the model the self-similar, long-memory clock (Level 6, Hurst ~ 0.75)
    motivates, and it lowers the forecast error relative to a single trailing
    window.  No parameters are fitted, so there is no look-ahead.
    """
    vols = []
    for h in horizons:
        lo = max(0, t - h)
        if t - lo >= 2:
            vols.append(_rvol(daily_returns[lo:t]) * math.sqrt(TRADING_DAYS))
    return statistics.mean(vols) if vols else 0.0


# ---------------------------------------------------------------------------
# Backtest engine
# ---------------------------------------------------------------------------

def _portfolio_daily(returns, weights, t0, t1):
    """Daily portfolio simple returns over [t0, t1) under fixed weights."""
    out = []
    for t in range(t0, t1):
        out.append(sum(weights[i] * returns[i][t] for i in range(len(weights))))
    return out


def backtest(returns, scheme: str, vol_forecast: str = "har",
             rebalance: int = 21, target_vol: float = 0.10,
             lev_cap: float = 1.5, cost_bps: float = 10.0,
             warmup: int = 252) -> dict:
    """Walk-forward backtest.

    scheme:
      * "buyhold"   -- equal weights, fully invested, no vol target (baseline);
      * "voltarget" -- equal weights, gross exposure scaled to the portfolio vol
                       forecast (risk timing);
      * "riskparity"-- inverse-forecast-vol weights, then scaled to target vol.
    vol_forecast: "trailing" or "har" (used for scaling and, in riskparity, for the
    cross-sectional weights).
    Returns the net daily return series and the realised weight path.
    """
    n = len(returns)
    T = len(returns[0])
    vf = har_vol if vol_forecast == "har" else trailing_vol

    net = [0.0] * warmup            # no position during warm-up
    prev_w = [0.0] * n
    turnover_total = 0.0
    n_rebal = 0

    t = warmup
    while t < T:
        t_end = min(t + rebalance, T)
        # --- cross-sectional weights (past data only) ---
        if scheme == "riskparity":
            inv = []
            for i in range(n):
                vi = vf(returns[i], t) or 1e-6
                inv.append(1.0 / vi)
            s = sum(inv)
            base = [x / s for x in inv]
        else:  # buyhold, voltarget
            base = [1.0 / n] * n

        # --- volatility targeting (risk timing) ---
        if scheme == "buyhold":
            lev = 1.0
        else:
            port_hist = _portfolio_daily(returns, base, max(0, t - TRADING_DAYS), t)
            if vol_forecast == "har":
                # blend of short/medium/long realised vol of the base portfolio
                blocks = []
                for h in (21, 63, 252):
                    seg = _portfolio_daily(returns, base, max(0, t - h), t)
                    if len(seg) >= 2:
                        blocks.append(_rvol(seg) * math.sqrt(TRADING_DAYS))
                pv = statistics.mean(blocks) if blocks else 0.0
            else:
                pv = _rvol(port_hist) * math.sqrt(TRADING_DAYS)
            lev = min(lev_cap, target_vol / pv) if pv > 0 else 0.0

        w = [lev * b for b in base]

        # --- turnover cost at rebalance ---
        turnover = sum(abs(w[i] - prev_w[i]) for i in range(n))
        turnover_total += turnover
        n_rebal += 1
        cost = turnover * (cost_bps / 10000.0)

        daily = _portfolio_daily(returns, w, t, t_end)
        if daily:
            daily[0] -= cost      # charge the cost on the first day of the period
        net.extend(daily)
        prev_w = w
        t = t_end

    return {"daily": net[:T], "warmup": warmup,
            "avg_turnover_per_rebalance": turnover_total / n_rebal if n_rebal else 0.0,
            "n_rebalances": n_rebal}


# ---------------------------------------------------------------------------
# Performance and risk metrics
# ---------------------------------------------------------------------------

def metrics(daily: list[float], warmup: int = 0) -> dict:
    d = daily[warmup:]
    d = [x for x in d]
    if len(d) < 2:
        return {}
    ann_ret = statistics.mean(d) * TRADING_DAYS
    ann_vol = statistics.pstdev(d) * math.sqrt(TRADING_DAYS)
    downside = [x for x in d if x < 0]
    dvol = statistics.pstdev(downside) * math.sqrt(TRADING_DAYS) if len(downside) > 1 else float("nan")
    # cumulative and max drawdown
    cum = 1.0
    peak = 1.0
    mdd = 0.0
    for x in d:
        cum *= (1 + x)
        peak = max(peak, cum)
        mdd = min(mdd, cum / peak - 1)
    # 5% daily CVaR (expected shortfall)
    k = max(1, int(0.05 * len(d)))
    worst = sorted(d)[:k]
    cvar = statistics.mean(worst)
    return {
        "ann_return": ann_ret, "ann_vol": ann_vol,
        "sharpe": ann_ret / ann_vol if ann_vol else 0.0,
        "sortino": ann_ret / dvol if dvol and dvol == dvol else float("nan"),
        "max_drawdown": mdd, "cvar_5pct_daily": cvar,
        "total_return": cum - 1, "n_days": len(d),
    }
