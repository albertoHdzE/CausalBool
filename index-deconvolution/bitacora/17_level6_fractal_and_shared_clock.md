# Bitacora 17 — Level 6: The Clock is a Fractal Point Process, and Largely Shared

Date: 2026-07-10
Status: complete and verified

## Where Level 5 left the trail

Level 5 localised the information in an uncontrolled sequence: describing it by its
representation-free pivots, the move sizes carry no memory beyond their marginal,
but the timing of pivots -- the clock -- clusters and forecasts out of sample. The
assessor asked to push exactly this, to study the intra-pivot structure and see
whether it is self-similar. An elite-researcher instinct adds a second question the
data can answer: if the clock is a real object, is it idiosyncratic to each series,
or is it shared across many? Level 6 answers both. It is self-contained; Levels 1
to 5 are untouched.

## The clock is a self-similar fractal point process (exp21)

Treat the pivot times as a point process and measure the Fano factor F(T) =
Var[N_T] / Mean[N_T], the variance-to-mean of the event count in windows of length
T. A renewal process (independent inter-event times) has a flat F(T); a clustered
self-similar process has F(T) ~ T^alpha with 0 < alpha < 1.

Across the twelve multi-decade series, at four reversal scales theta, against the
return-shuffle null:

| theta | alpha real | alpha shuffle | excess | count Hurst | R^2 |
|---|---|---|---|---|---|
| 0.01 | 0.501 | -0.022 | +0.523 | 0.750 | 0.982 |
| 0.02 | 0.512 | -0.023 | +0.536 | 0.756 | 0.987 |
| 0.04 | 0.421 | -0.034 | +0.456 | 0.711 | 0.980 |
| 0.08 | 0.272 | -0.053 | +0.324 | 0.636 | 0.932 |

The shuffle sits at the renewal value (alpha near zero, slightly negative); the
real series sit near alpha = 0.5, a count Hurst of about 0.75, with clean power-law
fits (R^2 around 0.98). The exponent stays positive and away from the null at every
scale, and it is roughly constant across the finer scales -- the clustering of
pivot timing repeats at every reversal scale. This is the intra-pivot self-
similarity the assessor asked for, stated as a fractal-point-process exponent: the
clock is a self-similar clustered point process, not a renewal one.

## Is the clock multifractal? Weak, reported as such (exp22)

A single exponent may not suffice. Multifractal detrended fluctuation analysis of
the inter-pivot waiting-time sequence gives the generalised Hurst h(q); a spectrum
that narrows with q (positive width h(1) - h(5)) is multifractal. The waiting-time
long memory is confirmed (h(1) about 0.75, matching the count Hurst), and the mean
width is 0.137. But the return-shuffle null already produces a width of 0.098 --
the well-known finite-sample bias of the method -- so the excess is only +0.039,
positive on 8 of 12 series. A few instruments (SP500, NASDAQ, width excess about
0.15) look genuinely multifractal, but pooled the effect is not clearly above the
null. Honest verdict: modest, inconclusive; the monofractal count-Hurst is the
defensible description at this length.

## The clock is largely shared across instruments (exp23)

Aligning the twelve instruments on their common trading days and forming each one's
windowed activity signal:

- the mean pairwise correlation of the activity signals is 0.478 (up to 0.87): the
  clocks are strongly synchronous;
- the leave-one-out common signal (the mean activity of the other eleven) explains
  a mean R^2 of 0.446 of each instrument's own activity, with none of the target's
  data entering its own predictor: nearly half of one clock is the common clock.

So the activity clock is largely a shared, market-wide object, not idiosyncratic.
But the honest test is whether the shared part forecasts. Predicting an
instrument's next-window activity from its own past plus the common signal, out of
sample, and comparing with a null that time-shuffles the common signal: the mean
enhancement over own-past is +0.012, against a null of -0.004, but only 7 of 12
series beat their null (sign-test p = 0.39). The common clock explains
contemporaneous activity strongly, yet it does not add robust out-of-sample
forecast power beyond an instrument's own persistence. The clock is synchronous, not
lead-lag predictive -- a structural sharing, not a tradable one. This is the honest
boundary of the result.

## What Level 6 adds

- A named, closed-form column for the pivot distribution: the Fano exponent alpha
  (count Hurst (1+alpha)/2), which quantifies the clustering as a fractal-point-
  process dimension and shows it is scale-invariant across reversal scales.
- A structural discovery: the clock is largely shared across instruments (common
  R^2 about 0.45), with an explicit, honest limit -- the sharing is contemporaneous,
  not a forecast enhancement.
- Two honestly negative or weak results kept in view: the multifractal width barely
  exceeds its finite-sample null, and the shared clock does not beat own-past out of
  sample. Reporting these is the point; the fractal-clock exponent is what survives
  every null.

## Frontier

The recursion can go one level deeper: take the activity signal itself, find its
pivots, and ask whether the regimes of activity (bursts of bursts) are self-similar
-- a clock of the clock. And the joint (dt, dv) law, so far only its two marginals,
may couple: whether a long calm precedes a large move is the next test.

## Verification

`python level6/exp21_fractal_clock.py`, `exp22_multifractal.py`,
`exp23_shared_clock.py` reproduce the three results; each accepts `--quiet` and
writes to `results/`. Tests: `python -m pytest level6/ level5/ level4/ level3/
level2/ tests/ -q` is 60 / 60. Levels 1 to 5 are untouched.
