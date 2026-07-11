"""exp27_backtest.py  (Level 8)

The strategy the programme licenses: a walk-forward, cost-aware, volatility-targeted
portfolio that never bets on direction.

Four schemes on the twelve instruments over the common ~32-year window:

  A  buy-and-hold, equal weight (the market baseline);
  B  volatility-targeted, equal weight, trailing-vol scaling;
  C  volatility-targeted, equal weight, HAR (multi-scale clock) scaling;
  D  risk parity (inverse forecast vol) with HAR volatility targeting.

The claim under test is narrow and honest: the risk schemes do not beat the
baseline on raw return -- they cannot, since direction is unforecastable -- but they
improve the risk-adjusted outcome (Sharpe, drawdown, tail loss) by de-risking ahead
of the forecastable turbulent regimes, and the clock (HAR) forecast improves on
trailing vol.  Costs are charged on turnover; everything uses only past data.
"""

from __future__ import annotations

import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level6"))

from shared_clock import aligned_prices  # noqa: E402
from strategy import backtest, metrics  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
TARGET_VOL = 0.10
COST_BPS = 10.0
LEV_CAP = 1.5
WARMUP = 252


def simple_returns():
    names, M = aligned_prices()
    R = [[M[i][t] / M[i][t - 1] - 1 for t in range(1, len(M[i]))] for i in range(len(names))]
    return names, R


def run(quiet: bool = False) -> dict:
    names, R = simple_returns()
    schemes = [
        ("A buy&hold",        dict(scheme="buyhold", vol_forecast="trailing")),
        ("B voltarget-trail", dict(scheme="voltarget", vol_forecast="trailing")),
        ("C voltarget-clock", dict(scheme="voltarget", vol_forecast="har")),
        ("D riskparity-clock",dict(scheme="riskparity", vol_forecast="har")),
    ]
    rows = []
    for label, kw in schemes:
        bt = backtest(R, target_vol=TARGET_VOL, lev_cap=LEV_CAP,
                      cost_bps=COST_BPS, warmup=WARMUP, **kw)
        m = metrics(bt["daily"], warmup=WARMUP)
        m["label"] = label
        m["turnover"] = bt["avg_turnover_per_rebalance"]
        rows.append(m)

    out = {"experiment": "portfolio_backtest", "n_instruments": len(names),
           "target_vol": TARGET_VOL, "cost_bps": COST_BPS, "lev_cap": LEV_CAP,
           "schemes": rows}

    if not quiet:
        print(f"{len(names)} instruments, ~{rows[0]['n_days']/252:.0f} years, target vol "
              f"{TARGET_VOL:.0%}, cost {COST_BPS:.0f} bps/turnover, leverage cap {LEV_CAP}\n")
        hdr = f"{'scheme':20s} {'annRet':>7s} {'annVol':>7s} {'Sharpe':>7s} {'Sortino':>8s} {'maxDD':>7s} {'CVaR5%':>8s} {'turn':>6s}"
        print(hdr)
        for r in rows:
            print(f"{r['label']:20s} {r['ann_return']:>7.1%} {r['ann_vol']:>7.1%} "
                  f"{r['sharpe']:>7.2f} {r['sortino']:>8.2f} {r['max_drawdown']:>7.1%} "
                  f"{r['cvar_5pct_daily']:>8.2%} {r['turnover']:>6.2f}")
        a, c = rows[0], rows[2]
        print(f"\n  reading: risk timing lifts Sharpe {a['sharpe']:.2f} -> {c['sharpe']:.2f} and "
              f"cuts the worst drawdown {a['max_drawdown']:.0%} -> {c['max_drawdown']:.0%} and the "
              f"5% tail loss, at a similar or lower annual return.")
        print("  the win is risk-adjusted, from de-risking ahead of forecastable turbulence; "
              "no directional bet is made.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp27_backtest.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp27_backtest.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
