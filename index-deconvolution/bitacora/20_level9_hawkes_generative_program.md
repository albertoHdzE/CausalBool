# Bitacora 20 — Level 9: A Three-Number Generative Program for the Clock

Date: 2026-07-11
Status: complete and verified

## The dare, and the discipline

The assessor pushed for a bold shot: not merely to *describe* the clock but to find
the short *program* that *generates* it, in the spirit of Algorithmic Probability.
The bodyguard rule kept the shot honest. Algorithmic Probability applied to the raw
price path is a dead end, because the path is incompressible (direction is
unforecastable, proven four ways): the shortest program that reproduces incompressible
data is the data itself. So the program search must be aimed at the one object the
programme proved *is* compressible -- the self-similar pivot clock (Levels 5 to 7).

The canonical short program for a clustered point process is the exponential Hawkes
self-exciting process: three numbers -- a baseline rate mu, an excitation alpha, and
a decay rate beta -- with intensity

    lambda(t) = mu + sum_{t_i < t} alpha * exp(-beta * (t - t_i)).

Its branching ratio n = alpha / beta is the order parameter: n = 0 is memoryless
(Poisson), n -> 1 is critical (a single event triggers long, self-similar cascades).
The moon-shot hypothesis was that markets sit near criticality, and that our Level 6
scale-invariance is a renormalisation-group fixed point rather than a coincidence.

## The result (exp29, twelve multi-decade series)

The pivot times of each instrument were fitted by exact maximum likelihood (Ogata's
O(N) recursion, a coarse-to-fine grid over mu, n, beta). Every claim is set against
the return-shuffle null.

1. **Self-excitation is real and strong.** The branching ratio is n = 0.69 on
   average, against a shuffle of 0.01, clearly self-exciting on all twelve series.
   The clock is far from memoryless.

2. **It is sub-critical, not critical.** n = 0.69 is well below 1. The moon-shot
   claim -- markets at the edge of instability -- is *not* confirmed at daily
   resolution. This is honest and expected: fine-tick studies in the literature find
   n near 0.9, and daily coarsening washes out part of the self-excitation. The
   market clock is strongly self-exciting but comfortably sub-critical at this scale.

3. **It predicts out of sample.** Fitted on the first 70% of time, the three-number
   Hawkes beats a Poisson process on the held-out 30% by +0.059 nats per event, on
   all twelve series. The excitation is not an in-sample artefact; it forecasts the
   held-out event stream.

4. **It compresses.** Three numbers stand in for about 1,382 event times per series.
   This is the description-length collapse the Algorithmic-Probability instinct
   wants -- achieved on the structure, not the noise.

5. **It regenerates the fractal.** Simulating the fitted Hawkes and re-measuring the
   Fano-factor clustering exponent gives 0.41 against the real clock's 0.49. The
   three-number program reproduces most of the self-similar clustering it was never
   directly shown -- though not all of it.

6. **RG flow.** The fitted branching ratio across reversal scales theta is 0.66,
   0.69, 0.62, 0.49 (for theta = 0.01, 0.02, 0.04, 0.08). It is approximately
   scale-invariant across the finer scales and softens at the coarsest, consistent
   with a self-similar generator sitting near, but not exactly at, a fixed point.

## Honest reading

The dare half-landed, which is the best kind of result. The bold half -- criticality,
n -> 1, a clean RG fixed point -- is *not* supported at daily resolution: n is 0.69
and the RG flow drifts at coarse scales. But the grounded half is decisive and new:
the self-similar clock discovered across Levels 5 to 7 has an explicit, short,
generating program -- a strongly self-exciting Hawkes process -- that beats the
shuffle on every series, predicts out of sample, compresses hundreds of events into
three numbers, and regenerates the fractal clustering. That is the Algorithmic-
Probability idea realised correctly: compress the signal, never the noise.

The single-exponential kernel under-reproduces the clustering exponent (0.41 vs
0.49), which points to the honest next step: a multi-scale kernel (a sum of
exponentials, or a power-law kernel) would capture the full self-similarity, and its
approach to criticality could be re-examined at finer sampling. That is the
nearly-unstable, multifractal Hawkes of the current market-microstructure literature,
reached here from representation-free pivots rather than from order-book ticks.

## Where this leaves the programme

The arc is now closed at the level of mechanism. Levels 1 to 3 built an exact inverse
for deterministic networks. Level 3 met markets and failed honestly. Levels 4 to 7
found that the information lives in a self-similar, shared clock, representation-free.
Level 8 turned that into a risk strategy with an honest ceiling. Level 9 now names the
*generator*: the clock is a self-exciting cascade, three numbers, sub-critical but
strong. Not the edge of chaos -- but its close, well-behaved neighbour.

## Verification

`python level9/exp29_hawkes_clock.py` reproduces the six results; it accepts
`--quiet` and writes to `results/`. Tests:
`python -m pytest level9/ level8/ level7/ level6/ level5/ level4/ level3/ level2/
tests/ -q` is 78 / 78. Levels 1 to 8 are untouched.
