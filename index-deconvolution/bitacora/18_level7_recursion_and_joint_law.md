# Bitacora 18 — Level 7: The Clock of the Clock, and the Joint Law of a Leg

Date: 2026-07-10
Status: complete and verified

## Two frontier questions

Level 6 established that the clock -- the timing of representation-free pivots -- is
a self-similar fractal point process, and largely shared across instruments. Two
questions remained. First, does the clustering recur one level deeper: are there
bursts of bursts, a clock of the clock? Second, the joint law of a leg's two
occurrence coordinates, its duration dt and its value change dv, which Level 5 only
studied as separate marginals: do they couple, and in particular does a long calm
precede a large move? Level 7 answers both, honestly. Self-contained; Levels 1 to 6
untouched.

## The clock of the clock: a hierarchy, but attenuating (exp24)

The base clock is the pivot point process of the values, Fano exponent alpha_base.
Its activity signal (the windowed pivot count) is a series in its own right; the
pivots of that signal are the meta-clock, Fano exponent alpha_meta. If the two
exponents matched, the clustering would be self-similar across recursion depth.

Across the twelve series:

- base clock exponent alpha_base = 0.512;
- meta clock exponent alpha_meta = 0.129, against a return-shuffle null of -0.053,
  an excess of +0.182, positive on 10 of 12 series.

So the meta-clock does cluster beyond the null: the regimes of activity themselves
come in bursts, a genuine hierarchy. But the meta exponent is far smaller than the
base exponent (0.13 against 0.51): the clustering attenuates sharply with recursion
depth. It is a partial hierarchy, not a scale-invariant cascade. The honest
statement is that the clustering repeats once more, weakly, and two instruments
(FTSE, XOM) do not show it at all. Self-similarity holds across reversal scale
(Level 6, exp21) but not across recursion depth.

## The joint law: real legs are sub-diffusive (exp25)

Within a leg, the distance travelled scales with the duration as |dv| ~ dt**H. The
return-shuffle null, whose legs are those of a random walk with the same increment
marginal, pins the Brownian reference exactly: null H = 0.485, essentially the
theoretical 1/2. The real series depart from it robustly:

- within-leg diffusion exponent H = 0.343, against the null 0.485, an excess of
  -0.142, sub-diffusive on 10 of 12 series.

Real excursions between reversals travel less than a random walk of the same
duration would: the intra-leg dynamics are anti-persistent. This is a genuine,
physics-grounded, named departure from the random-walk null, and the null's own H
sitting at 1/2 is the control that makes it credible.

Across legs, the coupling is absent. The correlation of a leg's duration with the
size of the next move (a long calm preceding a big move) is +0.008, against a null
of 0.000; the correlation of a move's size with the next waiting time is -0.035,
against -0.002. Both are negligible. The specific hypothesis that a long calm
precedes a large move does not hold: the size-duration coupling lives within a leg,
not across legs. This is reported as an honest negative.

## What Level 7 settles

- The hierarchy of clustering is real but shallow: activity regimes cluster (10/12
  beat the null), yet the clustering weakens sharply one level up (alpha 0.13 vs
  0.51). The fractal clock is self-similar across reversal scale, not across
  recursion depth.
- The joint law has a clean within-leg signature: sub-diffusion, H = 0.34 against a
  Brownian null of 0.49, on 10/12 series -- a named exponent with a validated
  reference.
- The cross-leg coupling is a genuine null: a long calm does not precede a big move.

Two positive results and one honest negative, each against a null that pins the
random-walk reference. The programme's robust core remains what survives every
null: the clustering of pivot timing (Level 6) and now its within-leg sub-diffusion.

## Frontier

The size-duration coupling being intra-leg suggests the natural next object is the
leg shape itself -- the path a value traces between two reversals, not only its
endpoints -- and whether its sub-diffusive exponent is stable across reversal
scales (a within-leg analogue of the Level 6 scale-invariance). The joint (dt, dv)
density, beyond the two correlations measured here, could also be modelled directly.

## Verification

`python level7/exp24_clock_of_clock.py` and `exp25_joint_law.py` reproduce the two
results; each accepts `--quiet` and writes to `results/`. Tests:
`python -m pytest level7/ level6/ level5/ level4/ level3/ level2/ tests/ -q` is
66 / 66. Levels 1 to 6 are untouched.
