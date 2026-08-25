# Bitacora 24 — Level 12: The Action Is in the When, Not the What (and the Two Clocks Are One)

Date: 2026-07-13
Status: complete and verified

## The assessor's idea

A deliberately simple, almost-crazy proposal: stop trying to predict the *direction* of
prices; treat the *actions* -- buy, sell, hold, wait -- as symbols with a frequency or a
hidden pattern, in the spirit of the behaviour tables and Holland's schemata. If the
clock of actions is predictable, "half the game is won". This bitacora tests exactly
that, and reports both what is right about it and what it costs to say honestly.

Level 12 is self-contained; Levels 1 to 11 are untouched.

## Part 1 — the 'what' carries zero information (the idea, made exact)

The sharp form of the idea is a fact about trading: you must alternate. A buy is always
followed by a sell and a sell by a buy; you cannot buy twice running. So the
action-type sequence is forced, buy, sell, buy, sell, and its content is nil. Measured
on the twelve long series, the conditional entropy of the next action given the previous
is 0.0000 bits, while a coarse timing symbol (is the next gap shorter or longer than the
median) carries 0.9924 bits. The information in the actions is entirely in *when* they
happen, not in *which* they are. This is the assessor's intuition confirmed to the
letter, and it is the same thesis the whole programme reached from the other side: the
order is in the when, not the what.

## Part 2 — two clocks, and the honest surprise that they are one

The genuinely new object the idea suggests: the single pivot clock is really two
interleaved clocks -- the BUY clock (the troughs, where the perfect entry falls) and the
SELL clock (the peaks, where the perfect exit falls). We had only ever studied the
pooled clock. Do buy and sell have their *own* frequency and predictability?

Against the return-shuffle, on the twelve long series:

    self-excitation   buy clock  n = 0.572     sell clock  n = 0.572
    OOS forecast lift  buy +0.093 (12/12)       sell +0.098 (12/12)

The two clocks are statistically indistinguishable. Their branching ratios coincide to
six decimal places on every series -- not a bug (the two are genuinely different data:
their Hawkes log-likelihoods differ, e.g. -2174.28 versus -2173.77 on SP500) but grid
quantisation: both sub-clocks land on the same coarse-grid self-excitation optimum. Both
forecast the next event's timing equally well out of sample, beating the shuffle on all
twelve series each. So the decomposition the idea proposed collapses back to one clock:
entry timing and exit timing are equally clustered and equally predictable. There is no
buy/sell timing asymmetry to exploit differently for entries and exits.

This is the honest, mildly deflating answer, and it makes sense: a peak is a trough of
the sign-flipped series, and the directional-change construction is symmetric under that
flip, so it cannot manufacture an asymmetry. The market's opportunity clock is a single
symmetric object, not a pair of distinct buy and sell rhythms. Reported as such: the new
decomposition is real to build but null in content -- one clock, seen twice.

## Part 3 — 'half the game', costed honestly

The idea's slogan -- a predictable clock is half the game -- is emotionally true and
economically not, and it matters to say so. Profit is direction times timing, not
direction plus timing. Knowing that a turning point is due soon (timing, which we can
forecast, +0.09 over the shuffle on every series) does not tell you whether it is a peak
or a trough (direction, which is unforecastable, proven four ways). The two halves do
not add; they multiply, and one factor is zero. So the standalone worth of a predictable
clock is risk control -- sizing down before clustered turbulence, the Level 8 ceiling
(drawdown and tail cut by about a third, Sharpe barely moved) -- and not half the return.
The clock is genuinely won; the game is not half-won, because the other factor is dead.

## What Level 12 adds

- A crisp, quantified confirmation of the assessor's thesis: the action-type order
  carries 0.00 bits, the timing carries ~1 bit; the secret is the when, not the what.
- A new decomposition (buy clock versus sell clock) that turns out null: the two are
  statistically identical in self-excitation and out-of-sample predictability, so the
  opportunity clock is a single symmetric object. An honest negative on the asymmetry,
  a positive on the symmetry.
- The economic correction kept on the page: a predictable clock is risk control, not
  half the money, because profit needs the direction factor the programme proved dead.

## Verification

Reproduce: `python level12/exp33_action_symbols.py` (writes
`results/exp33_action_symbols.json`). Tests:
`python -m pytest level12 level11 level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 101 / 101 (6 new in `level12/test_level12.py`: the buy/sell partition covers the
pivots and splits troughs from peaks, the action-order entropy is ~0, the persistence
forecaster beats base on clustered gaps and is honest on anti-persistent ones, and
determinism). Levels 1 to 11 untouched.
