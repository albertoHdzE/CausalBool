# Bitacora 06 — Financial Data

Date: 2026-07-09
Status: complete and verified

## Aim

Apply the deconvolution to real financial data: download open price series,
binarise them, and try to recover a Boolean network that reproduces the
behaviour. The scientific purpose is to use the exact deconvolution machinery as
a test for deterministic causal structure, and to report honestly what it finds.

## Data

Daily closing prices for nine liquid instruments (AAPL, MSFT, GOOGL, AMZN, NVDA,
META, JPM, XOM, SPY) over three years (2023-07-10 to 2026-07-09), downloaded from
the public Yahoo Finance v8 chart endpoint and stored under `finance/data/` so
the experiment is reproducible from the exact data used. Prices are aligned on
their common trading days (752 daily transitions) and binarised by the sign of
the daily change: state 1 for an up day, 0 otherwise. Each instrument is a node;
the sequence of daily binary vectors is the observed trajectory.

## The overfitting trap and how it is avoided

With nine predictors a specific nine-bit pattern almost never recurs, so any next
value is trivially "reproduced". That is memorisation, not a causal law. The
analysis therefore does not report exact reproduction with the full support.
Instead it measures two overfitting-resistant quantities:

1. the contradiction rate among predictor patterns that recur (occur at least
   twice) under the full support: the fraction that map to both an up and a down
   next day, an intrinsic measure of non-determinism; and
2. the best predictive accuracy of a small functional support (size at most two),
   compared with the base rate (always predicting the more common next value).

A positive control is run through the identical analyser: a rule-110
cellular-automaton trajectory of the same shape, a genuinely deterministic system
in which every cell depends on three neighbours.

## Results

Experiment `experiments/exp05_financial.py`.

Real market data (752 transitions, nine nodes):

- mean contradiction rate among recurring patterns: 0.663
- mean base rate: 0.541
- mean best small-support accuracy (support size at most two): 0.562
- mean lift over the base rate: 0.021
- nodes reproduced exactly: 0 / 9

Deterministic control (rule-110 cellular automaton, same shape):

- mean contradiction rate: 0.000
- mean best small-support accuracy (support size at most three): 1.000
- nodes reproduced exactly: 9 / 9

The Wolfram side (`crosscheck/verify_finance_wl.wl`) recomputes the two headline
metrics and agrees with Python to numerical precision: market contradiction
0.6627 and 0 exact nodes; control contradiction 0 and 9 exact nodes.

## Interpretation

Binarised daily market moves do not admit a deterministic Boolean-network
explanation. Two thirds of the predictor patterns that recur are self-
contradictory, and the best small-support rule beats the base rate by only about
two percentage points, with no instrument reproduced exactly. The same analyser
recovers the cellular automaton as an exact deterministic network. The contrast
is the point: the deconvolution is an exact inverse for deterministic causal
systems (cellular automata, gene-regulatory networks) and, applied to markets,
quantifies their departure from determinism rather than manufacturing a spurious
network. This is the honest and scientifically meaningful outcome; no
deterministic law is claimed where the data do not support one.

## Caveats and open questions

1. The up/down binarisation at the daily scale is one of many; other
   thresholds, horizons (intraday, weekly), or three-state quantisations may
   expose more structure. The pipeline accepts any binarisation.
2. Lead-lag structure (predicting node i at t+1 from others at t) is only weakly
   present at the daily up/down scale; a fuller study would test multiple lags
   and correct for multiple comparisons before asserting any edge.
3. The method could be turned into a deterministic-structure score for arbitrary
   binarised time series, calibrated on the deterministic controls of this
   programme.
