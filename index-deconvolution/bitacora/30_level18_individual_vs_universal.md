# Bitacora 30 — Level 18: Individual versus Universal Clock Model, and an Honest Practical Comparison

Date: 2026-07-14
Status: complete and verified

## The assessor's request

Save one model per stock, plot them by sector, keep all the insights; then fit the
universal model; then play trading with the individual models and with the universal one,
and compare which is better in practice. The comparison must respect what the programme
has proved: direction is unforecastable, so trading here can only mean risk timing, and
the head-to-head is a risk-adjusted comparison, never a return bet. Level 18 is
self-contained; Levels 1 to 17 are untouched.

## The two models

`level18/models.py`. The individual model fits the three Hawkes numbers (mu, alpha, beta)
to each stock's own training turns -- tailored, but each fit sees only about seven hundred
events, so it is noisy. The universal model shares the shape across all stocks: a single
branching ratio n and decay beta, taken as the median of the per-stock training fits, with
only the baseline mu set per stock from its own rate (mu = (1 - n) * rate). One law, one
per-stock scale number. The recovered universal shape is n = 0.590, beta = 0.0101, a decay
timescale of about ninety-nine days -- the clock's memory is roughly a quarter.

## The per-stock models by sector

The fitted self-excitation, grouped by the eleven sectors, mostly overlaps: the sector
medians sit close together around the universal value, with only mild spread. There is no
sharply distinct sector clock. That overlap is itself an argument for a universal model --
the clock is a broad market property, not a per-sector one.

## Result 1 — forecast: the universal model wins (one law beats a hundred fits)

Out of sample, scoring how much better than a memoryless baseline each model forecasts the
timing of turns:

    per-event log-likelihood gain : individual +0.0471   universal +0.0500
    forecast ROC-AUC              : individual 0.591      universal 0.590

The universal model's average held-out gain is marginally higher, and it beats the
per-stock model on sixty-six of the hundred stocks; the AUCs are essentially identical. So
tailoring does not beat pooling. This is the bias-variance trade landing where Level 17
predicted: per-stock Hawkes fits on a few hundred events are noisy, the shape is genuinely
universal, and sharing it across the panel forecasts at least as well with a fraction of
the parameters. One law is better than a hundred fits.

## Result 2 — trading: neither beats buy-and-hold (the honest negative)

The risk-timing backtest scales exposure down when the model forecasts a burst of turns,
and compares the held-out risk-adjusted outcome with simply holding:

    mean Sharpe        : individual 0.339   universal 0.337   buy-and-hold 0.358
    mean max drawdown  : individual -62.8%  universal -63.0%  buy-and-hold -57.7%
    beat buy-and-hold Sharpe : individual 27/100   universal 27/100

Both clock models come out slightly worse than buy-and-hold, on both Sharpe and drawdown,
and each beats holding on only about a quarter of the stocks. The reason is honest and
specific: the clock forecasts turn frequency, not volatility magnitude, and a period of
many small turns is not a period of large losses. Timing exposure on turn frequency
therefore adds turnover and noise without removing the fat part of the tail; unlike the
realised-volatility timing of Level 8, which won modestly, turn-frequency timing does not.
So in practical trading terms the individual-versus-universal question is moot: the winner
is buy-and-hold, and the clock models are a small drag.

## The practical verdict

- As a model of the clock, the universal one is better: it forecasts turn timing as well or
  better than per-stock fits, on two shared numbers plus a per-stock scale rather than three
  fitted per stock, and it is more robust. This vindicates the earlier instinct that one law
  should replace a hundred descriptions.
- As a money-making trade, neither works. Direction stays unforecastable, and the clock's
  turn-timing is too weak a risk proxy to beat holding. The honest recommendation is the
  universal model for describing and forecasting the clock, and buy-and-hold for the money.

The negative is the point as much as the positive: the practical comparison was run
properly, on held-out data and against buy-and-hold, and it says the clock is a good
scientific object and a poor trading signal. Both halves are reported.

## The notebook

`notebooks/14_individual_vs_universal.ipynb` shows the per-stock self-excitation by sector,
the forecast head-to-head (a scatter on the diagonal and the marginal universal win), and
the trading head-to-head (Sharpe and drawdown for both models against buy-and-hold, the
honest negative). Executed end to end from a foreign working directory: three embedded
plots, zero errors.

## Verification

Reproduce: `python level18/exp40_individual_vs_universal.py` (writes
`results/exp40_individual_vs_universal.json`, which saves every per-stock model and the
universal shape); `python notebooks/build_14.py` rebuilds the notebook. Tests:
`python -m pytest level18 level17 level16 level15 level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 143 / 143 (6 new in `level18/test_level18.py`: the universal median shape, the
rate-reproducing instantiation, the causal intensity's rise after events and its
causality, the Sharpe and drawdown helpers, and the risk-timing backtest). Levels 1 to 17
untouched.
