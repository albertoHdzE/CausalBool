# Bitacora 16 — Level 5: Representation-Free Pivots, and Where the Information Falls

Date: 2026-07-10
Status: complete and verified

## The reframing the assessor proposed

Every level so far, including the multi-bit Level 4, began by binarising the
values. That takes for granted that the representation of a number -- the digits it
is written in -- is where the information is distributed. The assessor challenged
exactly this: perhaps the number's representation is the wrong object. Consider the
pivots not through their digits but through their occurrences along two axes, time
and value. A pivot is then a pure event with two coordinates: how long since the
last pivot (a time gap) and how far in value from it (a value gap). The numbers are
freed of any representation and described only by where their salient points fall.
The assessor linked this to Benford's law: digit distributions in natural series
are a fingerprint of scale-invariance, and an occurrence encoding should be scale-
invariant by construction.

Level 5 builds this and lets the data speak. It is self-contained; Levels 1 to 4
are untouched.

## The construction (agnostic, scale-invariant)

`level5/pivots.py` -- the directional-change decomposition. Walking the sequence,
hold the running extreme in the current direction; when the series reverses away
from that extreme by at least a relative amount theta, confirm a pivot at the
extreme and flip direction. Between two pivots the series is net monotone: a leg
with two occurrence coordinates, the time gap dt and the signed value gap dv. The
whole series becomes a list of (dt, dv) pairs -- no binarisation, no base, no
representation of the numbers. The threshold is relative, so the pivots of a
sequence and of any multiplicative rescaling of it are identical: the scale-
invariance that makes the description agnostic, and that underlies Benford.

`level5/occurrence_geometry.py` -- three named, closed-form process columns read
from the pivots: the fractal dimension of pivot proliferation, the Benford fit of
the gaps, and the intrinsic-time memory of the clock and the driver.

## Result 1 — the fractal dimension is a weak separator (exp17)

The pivot count scales as N(theta) ~ theta^(-D). Fitted over a geometric grid of
scales (R^2 around 0.975), a geometric random walk gives D = 1.52 and the twelve
long series give a mean D = 1.52 as well, only +0.065 above their own return-
shuffle (10 of 12 positive). Pivots proliferate with scale roughly as in a random
walk; the self-similarity dimension carries a small roughness excess and little
more. This is an honest near-null, and it points the search elsewhere.

## Result 2 — the occurrence gaps obey Benford, the raw values less so (exp18)

The leading-digit histogram of the gaps sits close to Benford: total-variation
distance 0.041 for the waiting times dt and 0.060 for the sizes |dv|, against 0.207
for the raw values, and the gaps are closer to Benford than the raw values on all
twelve series. The pooled waiting-time digits (0.27, 0.17, 0.13, 0.10, 0.09, ...)
track the Benford law (0.30, 0.18, 0.12, 0.10, 0.08, ...) closely. The assessor's
hunch holds: the occurrence encoding captures the scale-invariant structure that a
value representation obscures. Describing the series by where its pivots fall,
rather than by the digits of its numbers, is the more natural, scale-free
description.

## Result 3 — the information is in the clock, not the driver (exp19, the headline)

Re-index time by pivot events, so each leg is one tick. Measure the lag-1 memory of
the driver (the move sizes |dv|) and of the clock (the waiting times dt), each
against the return-shuffle null, which preserves the fat-tailed marginal and
destroys only temporal order.

- driver memory excess over the null: -0.035, positive on only 4 of 12 series. The
  move sizes carry no memory beyond their marginal; their apparent autocorrelation
  (around 0.5) is a mechanical consequence of the heavy tails, present just as
  strongly in the shuffle.
- clock memory excess over the null: +0.163, positive on all 12 series (the null's
  clock memory is consistently slightly negative; the real is consistently
  positive). The waiting times cluster: pivots arrive in bursts.

The temporal information is entirely in when the pivots happen, not in how big they
are. This is a subordination picture -- a random activity clock with memory driving
increments that are, in intrinsic time, close to memoryless -- recovered here
without any binarisation and invariant to any rescaling of the values. It is the
same volatility clustering the earlier levels saw, but localised: a clock
phenomenon, not a size phenomenon.

## Result 4 — the clock forecasts out of sample (exp20)

Binarise the clock into a short-wait unit (1 if the waiting time is below its
median) and forecast it from a short trailing window, committing on the first 60 %
of the legs and evaluating on the held-out last 40 %; the null rebuilds the whole
pipeline on the return-shuffle. Out of sample the clock beats its base rate by
+0.103 and the marginal-preserving null by +0.108, on all twelve series, sign-test
p = 2.4 x 10^-4. The timing of pivots is forecastable even though their sizes are
not.

## Two honesty notes

Both headline claims were nearly artefacts, and the controls caught them. On the
long series the additive volatility unit was trend-contaminated (a step function
following the price level); the scale-free relative difference and a contamination
guard fixed it (bitacora 15). Here the driver memory of ~0.5 looked like clustering
but was a fat-tail artefact of the marginal, exposed by the return-shuffle null,
which carries it just as strongly; the real structure is the clock, which the same
null does not carry. The residual is reported honestly: the sizes are unforecastable
beyond their marginal, and the fractal dimension barely separates real from random.
What survives every null is the clustering of pivot timing.

## Against the protocol's five criteria, representation-free

1. Behaviour tables with identified process columns -- the fractal dimension, the
   Benford fit, and the clock/driver memory decomposition, none of them a
   binarisation.
2. Behaviour rules that compress -- the short-wait persistence rule that forecasts
   the clock.
3. Named closed-form columns -- N(theta) ~ theta^(-D); Benford P(d) = log10(1 +
   1/d); the intrinsic-time memory split.
4. The pivot distribution characterised -- self-similar in time (clustered clock),
   memoryless in size beyond the marginal, and scale-invariant (Benford).
5. Out-of-sample forecast beating a null -- the clock forecast, +0.108 over the
   return-shuffle, p = 2.4 x 10^-4.

The frontier now is the intra-pivot recursion (decompose each leg at a finer theta
and test whether the clock statistics are self-similar across theta) and a joint
(dt, dv) law rather than the two marginals.

## Verification

`python level5/exp17_fractal_dimension.py`, `exp18_benford.py`,
`exp19_intrinsic_time.py`, `exp20_clock_forecast.py` reproduce the four results;
each accepts `--quiet` and writes to `results/`. Tests:
`python -m pytest level5/ level4/ level3/ level2/ tests/ -q` is 53 / 53. Levels 1
to 4 are untouched.
