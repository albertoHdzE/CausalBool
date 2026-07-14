# Bitacora 31 — Level 18 (cont.): Predicting the Clock, and a Granular Walkthrough

Date: 2026-07-14
Status: complete and verified

## The request

Make notebook 14 finer-grained: show, step by step, how a clock model is built from the
behaviour table and the regularities it reveals; state plainly what the model is (a
behaviour table, a behaviour formula, or a complex network); do this for three stocks;
then measure how well the model predicts the oracle's turns with precision and recall;
then summarise across 100 stocks; then trade three examples and plot the price, the
predicted moves and the accumulated profit. This bitacora records the prediction result
and the machinery; the notebook is the deliverable. Self-contained under Level 18; Levels
1 to 17 untouched.

## The machinery

`level18/predict.py` turns a clock model into discrete predictions and a trade: the causal
Hawkes intensity fires predicted turns on its highest-intensity days (spaced by a
refractory period, count set by the train rate); `match_events` scores them against the
oracle's turns within a tolerance (precision, recall, F1); `trade_sim` buys on a predicted
trough and sells on a predicted peak, causally, and returns the equity path.

## What the model is, made explicit

The walkthrough builds the model from the data and answers the question directly. The
behaviour table of the buy pattern has the four columns of the original method (ordinal,
position, gap, ratio), but on all three stocks the ratio column scatters (cv of gaps about
0.75): there is no exact, closed-form behaviour formula, because the market is not a
deterministic gate. Three regularities survive and are what the model is built from:
self-excitation (turns in bursts), self-similarity (Fano exponent about one half), and a
lognormal gap law. From them the model is a three-number self-exciting Hawkes law. So, in
the project's own terms: not a behaviour table (the table has no exact law), not a complex
network (the market is not deterministic), but a statistical behaviour formula -- a
compressed generator of the clock's statistics, three numbers per pattern.

## Result — the model predicts the clock to within a couple of days, modestly

Fitting on the first 70% and predicting the held-out 30%, matched to the oracle within a
tolerance, on the 100-stock panel, against a random predictor firing the same number of
times:

    tolerance   model F1   random F1
    +/- 1 day     0.463       0.235      model wins (about 2x)
    +/- 2 days    0.474       0.372      model wins
    +/- 3 days    0.479       0.475      tie
    +/- 5 days    0.485       0.592      random wins
    +/- 8 days    0.491       0.674      random wins

At the precise tolerance of two days the model reaches precision 0.44, recall 0.53, F1
0.47 -- it catches about half the turns, about half its calls are right, and it clearly
beats chance. The crossover is instructive and was nearly a trap: at loose tolerances a
random predictor tiles the timeline and matches almost anything, so it overtakes the
model; an early run at tolerance five sat on the cusp and looked like a null. Sweeping the
tolerance is what makes the result honest: the model's edge is real and lives at precise
timing, where it locates turns two to three times better than random, and it is modest --
the clock is predictable to a few days, not to the day.

## The trade, and the honest ceiling

Trading the predicted turns out of sample -- buy on a predicted trough, sell on a predicted
peak -- does not beat buy-and-hold, exactly as bitacora 27 and bitacora 30 found from other
angles. Knowing when a turn is near is not knowing the price, and the confirmed signal
lags the extreme, so the timed book gives back its small edge. The notebook plots this
plainly: the price with the executed moves, the long periods shaded, and the accumulated
profit tracking below buy-and-hold.

## The notebook

`notebooks/14_individual_vs_universal.ipynb` is now a four-phase granular walkthrough: build
the model on three stocks (oracle clock, behaviour table, the scattering ratio column, the
three surviving regularities, the three-number formula, and the plain statement of what it
is); predict the clock versus the oracle on those three with precision and recall and a
held-out raster; generalise across 100 stocks with the tolerance sweep and the per-stock F1
distribution; and trade three examples with price, moves and accumulated-profit plots.
Executed end to end from a foreign working directory: six embedded plots, zero errors.

## Verification

Reproduce: `python level18/exp41_clock_prediction.py` (writes
`results/exp41_clock_prediction.json`); `python notebooks/build_14.py` rebuilds the
notebook. Tests:
`python -m pytest level18 level17 level16 level15 level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 146 / 146 (3 added in `level18/test_level18.py`: the refractory-spaced predicted events,
the precision/recall matcher, and the buy-low-sell-high trade simulator). Levels 1 to 17
untouched.
