# Bitacora 26 — Level 14: The Behaviour Tables and Formulae of the Buy and Sell Patterns

Date: 2026-07-13
Status: complete and verified

## The assessor's framing

Refined from the helix idea: the two strands are not clock and price but the BUY pattern
and the SELL pattern. Each is an occurrence set -- the troughs where a perfect entry
falls, the peaks where a perfect exit falls -- and the task is to build its behaviour
table (the arithmetic of where its events fall) and read off its behaviour formula (a
compressed generator), exactly as the programme does for a cellular automaton, then to
show, probe and test that map rigorously on one stock, on all one hundred, and under a
microscope. Together the two patterns mark the direction; whether that direction is
forecastable is held separate and tested honestly. This bitacora delivers the tested map
and the dedicated notebook; the fusion of the two formulae into one bivariate equation is
scoped as the next step.

Level 14 is self-contained; Levels 1 to 13 are untouched.

## The two readings of a behaviour formula, and the honest boundary

`level14/behaviour.py` builds, for an occurrence set, the four-column behaviour table --
ordinal, position, gap, gap-ratio -- and tests it two ways. The controlled reading asks
for an exact formula: a constant gap column is a period, a constant ratio column is a
geometric self-similar law, and three symbols then reproduce the set to the last event.
The uncontrolled reading asks for a statistical formula: the three-number self-exciting
Hawkes generator of Level 9.

The instrument recognises the controlled regime: a periodic occurrence set scores
cv(gaps) ~ 0 and is flagged exact; a near-geometric set has cv(ratios) ~ 0.08. The market
patterns do not: on all one hundred stocks, both the buy and the sell pattern score an
exact formula on 0 of 100, with cv(gaps) about 0.77 -- their gaps are noisy, their ratio
column scatters. So a market turning-point pattern has no closed-form behaviour formula,
unlike a cellular automaton. This is the honest boundary the PROTOCOL draws between the
solved controlled regime and the uncontrolled one, shown here on the data.

## What the patterns do have: a statistical formula that compresses, regenerates, forecasts

Both patterns obey the three-number Hawkes law, and it earns its name on every test,
against the return-shuffle, across the panel of one hundred stocks:

    pattern   compression   Hawkes n   KS(gaps)   Fano real/sim   OOS gain   beats shuffle
    BUY          129x         0.456      0.189      0.42 / 0.16     +0.0260      82 / 100
    SELL         129x         0.455      0.195      0.42 / 0.16     +0.0263      83 / 100

- Compression: three numbers stand in for the hundreds of event positions, about 130 to
  one. A genuine behaviour formula, not a transcription.
- Self-excitation: the branching ratio is 0.46 (0.61 on the detailed survivor KO, in the
  familiar survivor-versus-panel gap of bitacora 22), far above the shuffle.
- Regeneration: simulating the formula reproduces the gap distribution to a KS distance
  of about 0.19 and recovers roughly half the Fano clustering (0.16 simulated against
  0.42 real) -- a fair match, with the honest shortfall in clustering already diagnosed in
  bitacora 23 as the single-exponential kernel's limit.
- Forecast: the formula fitted on the first seventy per cent of events forecasts the next
  event's timing on the held-out thirty per cent, beating the shuffle (which sits exactly
  at zero) on 82 of 100 stocks for buys and 83 of 100 for sells.
- Symmetry: the buy and sell formulae are statistically identical (n = 0.456 vs 0.455,
  matched forecasts), the same symmetry Level 12 found -- one clock, seen from both sides.

## The direction question, kept honest

Together the buy and sell patterns mark the direction: between a trough and the next peak
the market rose, between a peak and the next trough it fell. But this is a hindsight
decomposition -- the patterns are the turning points -- and it does not license a forward
direction call. To trade direction one must predict the next turn's time and side in
advance; the side is only the trivial alternation (Level 12, zero bits) and the timing
forecast is the weak clock edge, worth risk control and not return (Level 8 ceiling). So
the map is a rigorous description and compression of the turning-point structure, not a
direction predictor, and the notebook says so plainly.

## The next step, scoped: the fusion equation

The two formulae are two separate univariate equations. The physical way to merge them is
a mutually-exciting bivariate Hawkes process, one coupled system in which a buy lifts the
intensity of the next sell and a sell lifts the intensity of the next buy, with a
two-by-two excitation matrix whose off-diagonal terms are the base-pairing between the
strands. Fitting those cross-terms is the honest test of whether the join carries more
than the two patterns apart -- the fusion equation the assessor is reaching for. It is the
subject of the next level, not claimed here.

## The notebook

`notebooks/10_buy_sell_behaviour_formulae.ipynb` is a self-contained, from-anywhere,
naive-readable notebook devoted to this map: the two patterns on one stock, the behaviour
table, the exact-formula test with a geometric control that passes it, the statistical
Hawkes formula with its intensity overlaid on the real events (the match), the
regeneration and compression checks, the 100-stock panel (compression, out-of-sample
forecast against the shuffle, buy-sell symmetry), a zoom-in showing the fitted intensity
tracking the real events, and an explicit statement of the ceiling and the fusion next
step. It was executed end to end from a foreign working directory: seven embedded plots,
zero errors.

## Verification

Reproduce: `python level14/exp36_behaviour_formulae.py` (writes
`results/exp36_behaviour_formulae.json`); `python notebooks/build_10.py` rebuilds the
notebook. Tests:
`python -m pytest level14 level13 level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 115 / 115 (8 new in `level14/test_level14.py`: buy/sell disjoint and interleaved, the
behaviour-table columns, exact-formula detection on periodic and geometric sets, the
market having no exact formula, the compression ratio, the KS statistic, and the
intensity rising after events). Levels 1 to 13 untouched.
