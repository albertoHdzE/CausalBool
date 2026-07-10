# Bitacora 15 — Level 4: Multi-Bit Binarisation and the Behaviour Table of an Uncontrolled Sequence

Date: 2026-07-10
Status: complete and verified

## The move the protocol demanded

Levels 1 to 3 all reached the same negative on one object: the daily up/down sign
of a market series carries no deterministic structure (contradiction rate 0.66,
whole-pattern coverage nil, no backbone, LZ at shuffle baseline). Every one of
those analyses used a single binarisation — the sign bit. The protocol
(`PROTOCOL_order_discovery.md`, sections 2 and 5) is explicit that the method must
try more than one binarisation, write each value in a fixed number of bits, treat
each bit position as a candidate unit, and discover which units carry structure.
Level 4 does exactly that, and the negative dissolves into a clean positive on a
different unit.

## Level 4, implemented (self-contained; Levels 1-3 untouched)

- `level4/binarise.py` — agnostic multi-bit binarisation of any numeric sequence.
  Rank (quantile) coding writes each value in a fixed number of bits, scale-free
  (invariant to any monotone rescaling); a neutral first difference detrends;
  three binarisations are produced (`raw`, `diff_sign`, `diff_mag`) and the
  survival test, not the analyst, decides which bit columns matter.
- `level4/unit_survival.py` — a battery of structure statistics (LZ76 complexity,
  longest run of ones, lag-1 autocorrelation), each as a z-score against a
  time-shuffle that keeps the density and destroys the arrangement. A unit
  survives only if some statistic sits at least two shuffle sigmas from the null.
- `level4/occurrence_arithmetic.py` — the one-dimensional behaviour table: the
  identified process columns (density, persistence, memory), the run-length
  reading, the closed-form geometric run-length law, and a description-length
  compression figure.

## What the units say (exp12)

Pooled over 23 sequences, aligned length 753, each bit column scored for survival:

| binarisation | bit | mean autocorr z | survive / n | reading |
|---|---|---|---|---|
| `raw` | 0-2 | +17 to +26 | 23/23 | the slow level/trend — order, but a trivial monotone ramp |
| `diff_sign` | 0 | +0.21 | 3/23 | the direction unit — inert, at the shuffle baseline |
| `diff_mag` | 0 | +1.40 | 12/23 | the volatility unit — genuine, non-trivial clustering |

Two controls through the identical pipeline: a rule-110 cellular-automaton column
survives (autocorr z +5.5) and compresses (+3.7 bits); a pseudo-random column does
not survive and does not compress (-19.1 bits). The instrument is calibrated.

The raw bits are structured but trivially so: a near-monotone trend compresses to
"count up" and carries little information. The direction unit is inert, confirming
the earlier levels through a fourth lens. The volatility unit — the top magnitude
bit of the first difference — is the discovery.

## The behaviour table of the volatility unit

Process columns, as means over the 23 sequences:

- density p ≈ 0.5 (the marginal place-value);
- persistence p11 − p = +0.024 (a one is more likely to be followed by a one than
  the base rate: the ones cluster);
- memory, Hurst H = 0.665 by aggregated variance (H = 1/2 is memoryless), against
  a shuffle Hurst of 0.477 — above shuffle on **23 of 23** sequences.

The closed-form run-length column checks out exactly: the observed mean run of
ones is 2.11 and the geometric-law prediction 1/(1−p11) is 2.11. The behaviour
rule is therefore nameable — a geometric run-length law P(run = L) =
p11^(L−1)(1−p11), the direct analogue of the controlled regime's constant-ratio
column (the ratio p11 between successive run-length probabilities is fixed, the
self-similar spacing).

## The pivot distribution is self-similar (exp14)

The occurrences of the volatility unit are the pivots. Against the shuffle:

- gap coefficient of variation 0.815 vs 0.704 (19/23 over-dispersed): bursts of
  close occurrences separated by long calms;
- Hurst 0.665 vs 0.477 (23/23 above): persistent long memory;
- index of dispersion (variance-to-mean of window counts) grows 0.60 → 0.75 →
  0.99 → 1.53 across windows 5 → 10 → 20 → 40, while the shuffle stays flat near
  0.49. Clustering is present at every scale at once — self-similar, the
  soft-fractal signature the thesis found in controlled generators, now recovered
  in an uncontrolled sequence.

## The forecast beats the shuffle (exp13)

Committed on the first 60 % of each series, evaluated on the held-out last 40 %, a
minimal rule (predict the next volatility bit from the count of ones in a short
trailing window, window and threshold learnt on train only):

- volatility unit: out-of-sample edge over the base rate **+0.095**, of which
  **+0.087 survives the time-shuffle** (shuffle edge +0.008); **20 of 23**
  sequences beat their own shuffle; sign-test p = 2.4 × 10⁻⁴;
- sign unit, identical procedure: edge −0.013, nothing beyond shuffle, 12/23 (pure
  chance). The internal control fails exactly where the theory says it must.

## Honest account of the residual

The structure is in the arrangement of the volatility unit, and it is real, but it
is not large in bits. A naive two-state minimum-description-length code compresses
the daily volatility unit only +3.0 bits over its shuffle on average and on just
10 of 23 sequences: the per-symbol persistence (p11 − p ≈ 0.024) is genuine but
weak, and at n ≈ 750 the model cost nearly cancels it. The daily volatility bit
still carries close to one bit per symbol of irreducible entropy. What is robust is
not the global bit-count but (i) the survival, Hurst and multi-scale dispersion of
the unit against the shuffle, and (ii) the out-of-sample forecast. The direction
remains unforecastable; only the size of the move is.

## Where this stands against the protocol's five criteria

1. Behaviour tables with identified process columns — yes (density, persistence,
   memory), gate-agnostic.
2. Behaviour rules that compress the occurrence set — yes relative to raw
   enumeration; beyond the marginal the temporal compression is small but positive
   (+3 bits vs shuffle), and reported as such.
3. Named closed-form columns — yes: the geometric run-length law and the Hurst
   self-similarity index.
4. The pivot distribution characterised — yes: clustered, over-dispersed,
   self-similar across scales.
5. Out-of-sample forecast beating a shuffle — yes: +0.087 edge, p = 2.4 × 10⁻⁴.

The open frontier is a longer sequence (the 753-day window limits both the Hurst
range and the two-state compression) and richer binarisations (finer magnitude
bands, Gray coding) to see whether the self-similar column sharpens into a
stronger compression, not only a stronger forecast.

## Verification

`python level4/exp12_multibit.py` reports the unit survival table and the
controls; `python level4/exp13_forecast.py` the forecast; `python
level4/exp14_pivot_distribution.py` the pivot distribution. Tests:
`python -m pytest level4/ level3/ level2/ tests/ -q` is 41 / 41 (11 new Level 4
tests plus the existing 30). Levels 1 to 3 are untouched.
