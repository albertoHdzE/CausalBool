# Bitacora 19 — Level 8: From Structure to Strategy, and an Honest Ceiling

Date: 2026-07-10
Status: complete and verified

## The question

Can the seven levels of discovered structure be turned into a winning investment
strategy -- portfolio construction, risk measurement, capital allocation? The
answer has to respect what the programme actually proved, so it is a qualified yes:
a winning risk strategy, not a winning return strategy.

## What the programme licenses, and forbids

Forbidden: any bet on direction. The sign unit is inert under four independent
tests (contradiction rate, whole-pattern coverage, backbone search, behaviour
tables) and in Level 5 the pivot sizes carry no memory beyond their marginal. No
part of a defensible strategy may forecast whether a price will rise or fall.

Licensed: risk. The clock -- volatility and activity -- is forecastable (Levels 4
to 6), self-similar (fractal point process, Level 6), largely shared across
instruments (Level 6), and its increments are fat-tailed (Level 5). Risk is
therefore predictable and systematic, which is exactly the input a capital-
allocation and risk-measurement framework needs.

So the strategy allocates capital inversely to forecast risk and targets a constant
portfolio volatility; it de-risks ahead of the forecastable turbulent regimes. Its
aim is a better risk-adjusted outcome, not beating the market's return.

## The volatility forecast (exp26)

Out of sample, the multi-horizon HAR forecast -- the model the self-similar,
long-memory clock (Hurst about 0.75) motivates -- predicts next-block realised
volatility with correlation 0.624 against the single trailing window's 0.617, and a
19 % lower mean-squared error on all twelve instruments. A modest but consistent
gain: the long memory of the clock helps forecast risk, a little.

## The risk-measurement rationale (exp26)

Splitting days by whether the clock (trailing realised volatility) is in its top
third, the 5 % expected shortfall of the next day's return is -4.64 % when the clock
is high against -2.60 % when it is low: the tail is 1.8 times deeper in the high-
clock state, on all twelve instruments. The worst losses concentrate exactly where
the clock is high. This is the rationale for the whole strategy: because tail risk
is forecastable through the clock, de-risking on the clock removes the fat part of
the tail. Risk measurement here is regime-conditional and fat-tailed, not Gaussian.

## The portfolio backtest (exp27)

Walk-forward over the common 31-year window, twelve instruments, monthly rebalance,
10 basis points per unit turnover, 10 % annual volatility target, leverage capped at
1.5. Four schemes:

| scheme | ann return | ann vol | Sharpe | max drawdown | 5% CVaR | turnover |
|---|---|---|---|---|---|---|
| A buy & hold (equal weight) | 10.8 % | 15.5 % | 0.70 | -48 % | -2.33 % | 0.00 |
| B vol-target, trailing | 8.0 % | 10.9 % | 0.73 | -32 % | -1.64 % | 0.03 |
| C vol-target, clock (HAR) | 7.8 % | 11.0 % | 0.71 | -35 % | -1.64 % | 0.10 |
| D risk parity, clock | 7.7 % | 11.2 % | 0.69 | -34 % | -1.68 % | 0.13 |

The honest reading:

- Volatility targeting is a real, material risk improvement: it cuts the worst
  drawdown by a third (-48 % to -32 %) and the daily tail loss by 30 % (-2.33 % to
  -1.64 %), and holds the volatility at target. This is the win, and it is a risk
  win.
- The Sharpe ratio improves only marginally (0.70 to 0.73). At equal risk the
  vol-targeted book modestly beats buy-and-hold, but there is no large free lunch.
- The sophisticated clock (HAR) forecast does not beat the simple trailing vol once
  costs are paid: scheme C's extra turnover (0.10 vs 0.03) eats its 19 % forecast-
  error advantage, leaving it slightly behind B. Risk parity (D) adds nothing here.

## The ceiling, stated plainly

There is no return alpha in this strategy, and the programme predicts there cannot
be from this information: direction is unforecastable. What the discoveries buy is a
materially better risk profile -- a third off the maximum drawdown, a fifth to a
third off the tail loss -- for a similar risk-adjusted return, achieved purely by
timing risk on a forecastable clock and never betting on direction. The programme's
contribution is twofold: the understanding of why volatility targeting works (a
self-similar, shared, forecastable clock with fat-tailed increments), and the
regime-conditional, fat-tailed risk-measurement rationale. The elaborate multi-scale
machinery does not beat the simplest volatility timing net of costs, and that is
reported rather than hidden.

## The leg-shape science (exp28)

The Level 7 loose end: is the within-leg sub-diffusion exponent H stable across
reversal scales? The absolute H drifts with theta (0.45, 0.34, 0.27, 0.28), a
construction effect shared by the null (whose H also drifts, staying near Brownian).
But the departure from the null -- the sub-diffusive anomaly -- is scale-invariant:
the excess is -0.13, -0.14, -0.16, -0.16 across theta, essentially constant. The
excursions are anti-persistent relative to a random walk by the same amount at every
reversal scale, a within-leg analogue of the Level 6 clock scale-invariance.

## Verification

`python level8/exp26_vol_and_tailrisk.py`, `exp27_backtest.py`, `exp28_leg_shape.py`
reproduce the three results; each accepts `--quiet` and writes to `results/`. Tests:
`python -m pytest level8/ level7/ level6/ level5/ level4/ level3/ level2/ tests/ -q`
is 72 / 72. Levels 1 to 7 are untouched.
