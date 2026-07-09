# Bitacora 08 — Market Simulation and Further Approaches

Date: 2026-07-09
Status: complete and verified

## Aim

Ask how close the deconvolution comes to reproducing the market, with a fair
out-of-sample comparison of a real path against a model-generated one, statistics
to quantify the skill, and an evaluation of the idea of focusing on disruptive
changes. A wider multi-sector sample is used (23 instruments across technology,
energy, gold and materials, finance, consumer and agriculture, healthcare, and
the index).

## Method

Daily closes for the 23 instruments over three years are aligned and turned into
daily returns. Two characterisations are compared: all days binarised by the sign
of the return, and only the disruptive days (top thirty per cent of
cross-sectional mean absolute return) binarised by sign, the latter implementing
the idea of keeping the key datapoints and discarding the quiet moves between.

For the simulation, the deconvolution fits for each instrument the best
small-support deterministic directional rule (the per-node conditional-majority
function) on the first sixty per cent of the sample, and that rule then generates
a directed path on the held-out last forty per cent, keeping the real magnitude of
each move but the model's predicted sign. Out-of-sample evaluation is essential:
any in-sample edge is overfitting, and indeed the in-sample directed path looked
strongly profitable purely because the model had seen the data.

## Results

Experiment `experiments/exp06_market_simulation.py`.

Determinism, all days versus disruptive days:

- all days: contradiction rate 0.518, best in-sample accuracy 0.567, base 0.532.
- disruptive days: contradiction rate 0.582, best in-sample accuracy 0.612,
  base 0.527.

The disruptive-day series has a higher in-sample accuracy but also a higher
contradiction rate, and it has far fewer samples, so the apparent gain is
overfitting rather than genuine structure; at the overfit-resistant level (the
contradiction rate on recurring patterns) the disruptive days are, if anything,
less deterministic. Focusing on disruptive changes does not, by itself, expose a
deterministic law here.

Out-of-sample directional prediction (train sixty per cent, test forty per cent):

- mean out-of-sample directional accuracy: 0.509
- mean base rate on the test period: 0.536
- mean out-of-sample edge over the base rate: minus 0.027

The fitted model does not beat the naive base rate out of sample; the edge is
slightly negative and no instrument is predicted reliably. The representative
instrument (SPY) has an out-of-sample accuracy of 0.533 against a base rate of
0.563. The comparison plot (real versus model-generated cumulative path) and the
per-instrument accuracy chart are in the notebook
`experiments/market_simulation_demo.nb`, with a rendered copy at
`finance/market_comparison.pdf`.

## Answer to the question of "hacking" the market

Markets are indeed driven by rules and algorithms, but those rules are adaptive,
strategic, and reactive, and the aggregate price is close to a martingale: any
simple, stable, deterministic pattern is arbitraged away, which is precisely why
it does not persist out of sample. The deconvolution confirms this quantitatively.
It is an exact inverse for genuinely deterministic systems (it recovers cellular
automata and gene-regulatory networks perfectly), and applied to daily markets it
reports honestly that no small deterministic Boolean rule reproduces them out of
sample. The method is therefore a rigorous detector of deterministic causal
structure, and its verdict on daily price direction is that such structure is
absent, not that we have failed to find it. This is the scientifically defensible
position; a claim of market prediction would require out-of-sample evidence, which
is absent.

## Two further approaches, evaluated

The daily up/down binarisation is the crudest possible view. Two directions are
worth pursuing, and are recorded here as a concrete plan; the disruptive-event
characterisation above is the first step already taken.

1. Physics-style coarse-graining and regimes. Treat the market as a system with
   slow and fast variables. Identify change points (volatility regime shifts,
   structural breaks) as the key datapoints, model the slow regime process as a
   small deterministic or near-deterministic automaton over regime labels, and
   treat the fast within-regime motion as noise. The deconvolution would then be
   applied to the regime-label sequence, where determinism is more plausible than
   in daily returns. Tools: change-point detection, hidden-regime segmentation,
   and the existing minimal-support inference on the coarse-grained sequence.

2. Machine-learning preprocessing and sector clustering. Characterise each
   instrument by features (return sign, volatility bucket, cross-sectional rank,
   lead-lag correlations), cluster instruments by the similarity of their binary
   dynamics, and deconvolve within clusters where co-movement is strong, so that
   the functional support is drawn from economically related instruments rather
   than the whole market. A learned binarisation (for example the sign of a
   denoised or filtered return, or a two-bit up or down and calm or turbulent
   code) may expose more structure than the raw sign. The deconvolution machinery
   is unchanged; only the state encoding and the candidate support change.

Both keep the method intact and change only the representation of the data, which
is the honest lever: the deconvolution is exact once the data are genuinely
deterministic, so the research question is whether a representation exists in
which binarised market dynamics become deterministic. The present evidence is
that the daily-sign representation is not such a representation.

## Verification

The Python test suite is 18 / 18. The market notebook is generated by
`experiments/build_market_notebook.wl` and verified by
`crosscheck/verify_market_notebook.wl`, which evaluates its input cells with no
messages, confirms both plots are valid graphics, and exports the comparison
plot to a PDF.
