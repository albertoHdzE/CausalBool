# Level 8 — From Structure to Strategy

Can the discovered structure make money? A qualified yes: a winning **risk**
strategy, not a return strategy. Direction is unforecastable (established across
Levels 1-7), so nothing here bets on it; what is forecastable is the clock
(volatility/activity), which is self-similar, shared, and fat-tailed. The strategy
allocates capital inversely to forecast risk and targets constant volatility,
de-risking ahead of the forecastable turbulent regimes. Self-contained; Levels 1-7
untouched.

## Modules

- `strategy.py` — volatility forecasts (trailing, and HAR multi-scale motivated by
  the long-memory clock), a walk-forward cost-aware backtest engine (buy&hold,
  vol-target, risk-parity), and performance/risk metrics (Sharpe, Sortino, max
  drawdown, 5% CVaR, turnover).

## Results (12 instruments, ~32 years, monthly rebalance, 10 bps costs)

- **Volatility forecast (exp26):** HAR lowers next-block vol-forecast MSE by 19%
  (12/12) over trailing — the long-memory clock helps forecast risk, modestly.
- **Tail-risk timing (exp26):** the 5% expected shortfall is 1.8× deeper on
  high-clock days (−4.64% vs −2.60%, 12/12). The fat tail lives where the clock is
  high, so de-risking on the clock removes it — the risk rationale.
- **Backtest (exp27):** volatility targeting cuts the worst drawdown from −48% to
  −32% and the daily tail loss from −2.33% to −1.64%, at a marginally better Sharpe
  (0.70 → 0.73). The elaborate clock (HAR) forecast does **not** beat simple
  trailing vol net of costs. No return alpha — as the programme predicts.
- **Leg shape (exp28):** the within-leg sub-diffusion *anomaly* (excess over the
  Brownian null) is scale-invariant (−0.13 to −0.16 across θ), even though absolute
  H drifts.

## The ceiling, honestly

There is no return alpha; the win is a materially better risk profile (a third off
the drawdown, up to a third off the tail) at a similar risk-adjusted return, from
timing risk on a forecastable clock. The sophisticated machinery does not beat the
simplest volatility timing net of costs.

## Run

```
python level8/exp26_vol_and_tailrisk.py   # vol forecast + tail-risk timing
python level8/exp27_backtest.py           # the portfolio backtest
python level8/exp28_leg_shape.py          # within-leg sub-diffusion scale-invariance
python -m pytest level8/ -q               # 6 tests
```

Each experiment accepts `--quiet` and writes its summary to `results/`.
