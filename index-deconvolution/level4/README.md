# Level 4 — Multi-Bit Binarisation and Behaviour-Table Discovery

The level that answers the order-discovery protocol on uncontrolled data. Levels 1
to 3 studied a single binarisation (the up/down sign bit) and found no structure.
Level 4 follows the protocol's instruction to write each value in a fixed number of
bits, treat every bit position as a candidate unit, discover which units carry
structure, and read the behaviour table of the survivors. It is self-contained and
does not touch Levels 1 to 3.

## The pipeline (agnostic; knows nothing about the data)

1. `binarise.py` — rank-code each value in a fixed number of bits (scale-free) and
   also binarise the neutral first difference into a sign unit and magnitude units.
2. `unit_survival.py` — score each bit column (LZ76, longest run, lag-1
   autocorrelation) as a z-score against a time-shuffle; keep only units that
   depart from the shuffle by at least two sigma.
3. `occurrence_arithmetic.py` — for a surviving unit, build the behaviour table:
   the process columns (density, persistence p11, Hurst memory), the closed-form
   geometric run-length law, and the description-length compression.

## Result

- The direction unit (sign of the step) is inert — at the shuffle baseline, as the
  earlier levels found. The raw-value bits are structured but trivially (a monotone
  trend). The **volatility unit** (top magnitude bit of the first difference) is the
  discovery: it survives the shuffle, has Hurst 0.665 (above shuffle on 23/23
  sequences), over-dispersed gaps, and an index of dispersion that grows with scale
  — self-similar, multi-scale clustering.
- Behaviour rule, closed form: geometric run-length law P(run = L) =
  p11^(L−1)(1−p11); observed mean run 2.11 equals the prediction 2.11.
- Forecast: committed on the first 60 % and tested on the last 40 %, the volatility
  unit gives an out-of-sample edge over the base rate of +0.095, of which +0.087
  survives the time-shuffle (20/23 sequences, sign-test p = 2.4 × 10⁻⁴). The
  direction unit gives nothing. Only the size of the next move is forecastable, not
  its direction.
- Controls through the identical pipeline: a rule-110 cellular automaton survives
  and compresses; a pseudo-random unit does neither.

## Honesty

The temporal compression beyond the marginal is small (+3 bits vs shuffle, 10/23):
the daily volatility bit is close to one bit per symbol of entropy. The robust
evidence is the survival, the self-similar pivot distribution, and the forecast,
not a large global bit-saving. The direction is unpredictable; only the magnitude
clusters.

## Run

```
python level4/exp12_multibit.py           # unit survival + behaviour table + controls
python level4/exp13_forecast.py           # out-of-sample forecast vs shuffle
python level4/exp14_pivot_distribution.py # gap law, Hurst, index of dispersion
python -m pytest level4/ -q               # 11 tests
```

Each experiment accepts `--quiet` and writes its summary to `results/`.
