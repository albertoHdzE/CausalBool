# Bitacora 21 — Level 10: The Oracle Behaviour Table, and the Cost-Threshold Theorem

Date: 2026-07-13
Status: complete and verified

## The dare, and the discipline

The flagship of the behaviour-table programme (TRANSFERENCE section 6) is the
oracle, or perfect trader: the in-hindsight optimal buy and sell points that maximise
terminal wealth. With no transaction cost this is trivial and useless -- capture
every up-tick. With a realistic per-round-trip cost c it is sparse, and the assessor's
hypothesis was that this sparse set of perfect trades *is* the directional-change
pivot clock (Levels 5 to 9), specialised to a scale fixed by the cost. If so, the
whole clock programme inherits an economic meaning, and its self-exciting Hawkes
generator (bitacora 20) becomes a statement about when tradable opportunity arrives.

The bodyguard rule for this idea is specific and non-negotiable: the oracle is
computed with look-ahead *by construction*. It is the answer key. It may be used only
as a target to explain and to forecast out of sample, never as a predictor feature.
The Level 10 forecast sees only past oracle event times.

Level 10 is self-contained; Levels 1 to 9 are untouched.

## The instrument

`level10/oracle.py` -- the perfect trader as an exact O(N) two-state dynamic
programme (the classic trade-with-fee recursion, carried in log-wealth so it is
stable over multi-decade paths):

    flat[t] = max( flat[t-1],  long[t-1] + log p[t] + log(1-kappa) )   # stay / sell
    long[t] = max( long[t-1],  flat[t-1] - log p[t] + log(1-kappa) )   # stay / buy

with `kappa` a proportional cost on each transaction's traded value. Backtracking the
arg-max recovers the exact buy and sell days. The relative round-trip cost is
c = (1-kappa)^-2 - 1, since a round trip multiplies capital by
(p_sell / p_buy)(1-kappa)^2 and clears cost when p_sell / p_buy >= (1-kappa)^-2.

All results are on the twelve multi-decade daily series in `finance/data_long/`, each
against the return-shuffle null, with a geometric-random-walk (GBM) instrument check.

## Result A — the cost-threshold theorem (the headline, and it is exact)

I expected the perfect trades to match the pivots only up to an order-one constant,
because the directional-change threshold measures a one-sided retracement from an
extreme while the trade-profitability test measures a two-sided swing from a bought
low to a sold high. The data corrected me, cleanly, and a proof followed.

At round-trip cost c = 0.02, the directional-change pivots at reversal threshold
theta = c are **exactly a subset of the oracle action points**: mean containment
1.000, exact on 11 of 12 series (index for index, tolerance zero). Sweeping theta
around c, the best set overlap sits at theta = 0.99 c with a Jaccard of 0.992; the
oracle is a slight superset, its residual only 0.004 -- four in a thousand oracle
points are not pivots.

The proof of the containment direction. The directional-change construction confirms
a trough at value L only once the series has risen from L to L(1+theta); it then seeks
a peak, and the confirmed peak H is the running maximum reached before a theta
retracement, so H >= L(1+theta). Two consecutive pivots therefore span
H / L >= 1 + theta = 1 + c >= (1-kappa)^-2, which is exactly the oracle's
profitability threshold. Every directional-change round trip is thus weakly
profitable, so a wealth-maximising schedule includes it: the pivots are oracle trade
points. This is not a fit; it is a guarantee built into the pivot construction.

The single apparent exception is instructive rather than a defect. On KO one pivot
pair -- a trough at 5.46875 and a peak at 5.578125 -- has ratio 5.578125 / 5.46875 =
1.02000, exactly 1 + c. Its net profit is exactly zero, a degenerate optimum, and the
dynamic programme's tie-break simply omits a trade it is indifferent to. Containment
holds for *an* optimal schedule; only measure-zero, exactly-break-even swings can be
dropped by a particular optimum. The theorem is airtight.

The reverse inclusion is where the honest residual lives. The oracle is a *globally*
optimal schedule; the directional-change construction is *greedy and causal*. The
0.4 % of oracle points that are not pivots are swings a look-ahead optimiser catches
that the greedy, one-pass construction misses -- the price paid for causality. Lowering
theta a hair (to 0.98 c) recovers them, which is why the best Jaccard sits just below
c. So the precise statement is: the perfect trader's action points are the
directional-change pivots at threshold equal to the transaction cost, exactly in one
direction and to better than one part in two hundred in the other.

The economic reading is the prize. A trader's transaction cost is a renormalisation
scale. It selects a reversal threshold theta = c, hence a clock. Different traders,
with different costs, see different -- but nested -- opportunity clocks, all cut from
the same self-similar pivot process.

## Result B and C — the oracle clock is the Level 9 clock (honest confirmation, not news)

Because the oracle set is, to within 0.4 %, the pivot set at theta = c, its behaviour
table must reproduce bitacora 20, and it does. At c = 0.02, against the return-shuffle:

- branching ratio n = 0.685 (bitacora 20 found 0.69 on the raw pivots), against a
  shuffle of 0.016, self-exciting on all twelve series;
- Fano clustering exponent 0.510 (bitacora 17 found about 0.5), against a null of
  -0.022;
- out of sample, the Hawkes fitted on the first 70 % of oracle event times beats a
  Poisson on the held-out 30 % by +0.055 nats per event, positive on all twelve.

This is reported as what it is: a confirmation of the Level 9 result on the
oracle-relabelled point set, not a fresh discovery. I flagged before running it that
"the oracle clock forecasts" would largely re-derive bitacora 20, since the oracle is
the pivot clock; it does. The value here is not a new forecast but the fact that the
*same* three-number self-exciting generator now carries a trading interpretation: the
optimal opportunities arrive in self-exciting bursts, and their timing -- not their
direction -- is forecastable out of sample, exactly the honest tradable question the
programme licenses.

The GBM instrument check behaves: the oracle clock of a driftless geometric random
walk has branching ratio 0.021 and an out-of-sample gain of -0.000 -- it reads as the
null. The self-excitation is a property of the real series, not a mechanical artefact
of running an optimiser on any monotone-ish path.

## Result D — cost as a renormalisation scale, and a non-monotone hump (the new object)

The genuinely new object is the branching ratio as a function of the trader's cost,
n(c). It is non-monotone:

| c (round-trip) | mean events | branching ratio n |
|---|---|---|
| 0.005 | 3684 | 0.400 |
| 0.010 | 2531 | 0.647 |
| 0.020 | 1398 | 0.685 |
| 0.040 |  619 | 0.602 |
| 0.080 |  226 | 0.484 |

The clustering of opportunity is strongest at an intermediate cost, around a 2 %
round trip, and weakens at both finer and coarser scales. The coarse-scale softening
(n falling from 0.69 to 0.48 as c grows) is the RG-flow drift already seen in bitacora
20 and is robust. The fine-scale softening (n falling to 0.40 at c = 0.005) is new --
bitacora 20 stopped at theta = 0.01 -- but must be read with a caveat: at c = 0.005 the
series has a pivot every three days, and the Hawkes decay grid tops out at a 250-day
timescale, so a genuinely fast excitation could be partly clipped by the instrument.
I therefore report the hump as real at the well-sampled scales (c in 0.01 to 0.08) and
the finest point as suggestive but instrument-limited. The honest claim is that the
opportunity clock is most self-exciting for a trader operating at percent-level costs,
and that this maximal-clustering scale is a candidate fixed neighbourhood of the
self-similar generator, not a true critical point (n stays well below 1 throughout,
consistent with bitacora 20's sub-critical verdict at daily resolution).

## What Level 10 adds, stated plainly

- A theorem, proved and verified: the in-hindsight optimal trades under a per-round-
  trip cost c are the directional-change pivots at reversal threshold theta = c --
  exact containment of the pivots in the oracle (guaranteed by the confirmation
  geometry), the oracle a 0.4 % superset (the greedy-versus-global residual). This
  gives the entire clock programme an economic meaning and closes the flagship.
- The reinterpretation of transaction cost as a renormalisation scale, and the n(c)
  curve, with a non-monotone hump peaking at percent-level costs -- a new, if
  instrument-limited at the finest scale, behaviour rule of the opportunity clock.
- An honest confirmation that the oracle clock is the Level 9 self-exciting fractal,
  reported as confirmation rather than dressed as a new forecast.

The residual is reported: the reverse inclusion is not exact (0.4 %), the fine-scale
n(c) point is instrument-limited, and the out-of-sample forecast is a re-derivation of
bitacora 20, not an independent win. What is new and strong is the equivalence theorem
and the cost-as-scale picture.

## Against the protocol's five criteria

1. Behaviour table with identified process columns -- the oracle occurrence set, its
   Fano exponent and its three-number Hawkes generator, all inherited from and
   identical to the pivot clock.
2. Behaviour rule that compresses -- three Hawkes numbers stand in for ~1400 optimal
   trade times per series, the same collapse as bitacora 20, now with a trading meaning.
3. Named closed-form column -- the cost-threshold identity theta = c, a closed-form
   map from a trader's cost to the reversal scale of their opportunity clock.
4. The pivot distribution characterised -- self-exciting (n = 0.685), fractal
   (Fano 0.51), with a new n(c) dependence on the cost scale.
5. Out-of-sample forecast beating a null -- the Hawkes forward intensity forecasts the
   next oracle event's timing, +0.055 nats/event over Poisson, 12/12, against the
   return-shuffle; confirmatory of bitacora 20.

## Verification

`python level10/exp30_oracle_clock.py` reproduces the four results; it accepts
`--quiet` and writes `results/exp30_oracle_clock.json`. Tests:
`python -m pytest level10 level9 level8 level7 level6 level5 level4 level3 level2 tests -q`
is 87 / 87 (9 new in `level10/test_level10.py`: dynamic-programme correctness, the
cost conversion, the local-extremum property, determinism, set matching, and the
sawtooth equivalence). Levels 1 to 9 are untouched.
