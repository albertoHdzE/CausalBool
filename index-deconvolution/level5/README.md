# Level 5 — Representation-Free Pivots and the Occurrence Geometry

Levels 1 to 4 all binarised the values first, taking for granted that a number's
representation (its digits) is where the information lives. Level 5 drops that
assumption. It describes a sequence only by where its salient points (pivots) fall
along two axes -- time and value -- so the numbers never need a representation. It
is self-contained and does not touch Levels 1 to 4.

## Construction

- `pivots.py` -- the directional-change decomposition. A pivot is confirmed when
  the series reverses from its running extreme by a relative amount theta; between
  pivots the series is a monotone leg with a time gap dt and a value gap dv. The
  relative threshold makes the whole construction invariant to any multiplicative
  rescaling of the values.
- `occurrence_geometry.py` -- three named, closed-form columns: the fractal
  dimension N(theta) ~ theta^-D, the Benford fit of the gaps, and the intrinsic-
  time memory of the clock (dt) and the driver (|dv|).
- `controls.py` -- the return-shuffle null (shuffle the log-increments, rebuild),
  which preserves the fat-tailed marginal and destroys temporal order; and a
  geometric random walk benchmark.

## Results (12 instruments, 8.7k-11.7k daily points, 1980s-2026)

- **Fractal dimension (exp17):** GBM D = 1.52, real mean D = 1.52, excess over the
  return-shuffle only +0.065 (10/12). Pivots proliferate roughly as in a random
  walk -- a weak separator, reported honestly.
- **Benford (exp18):** the occurrence gaps sit close to Benford (waiting-time TV
  0.041, size TV 0.060) and far closer than the raw values (0.207), on 12/12
  series. The occurrence encoding is naturally scale-invariant.
- **Intrinsic time (exp19, headline):** against the marginal-preserving null, the
  driver (move sizes) has no memory (-0.035, 4/12) but the clock (waiting times)
  does (+0.163, 12/12). The information is in *when* pivots happen, not *how big*
  they are -- a subordination (random-activity-clock) structure.
- **Clock forecast (exp20):** out of sample the short-wait clock unit beats its
  base rate by +0.103 and the return-shuffle null by +0.108, on 12/12 series,
  sign-test p = 2.4e-4.

## Honesty

The move-size memory of ~0.5 looks like clustering but is a fat-tail artefact of
the marginal (the return-shuffle carries it just as strongly); only the clock
survives the null. The fractal dimension barely separates real from random. What
is robust, representation-free, and forecastable is the clustering of pivot timing.

## Run

```
python level5/exp17_fractal_dimension.py
python level5/exp18_benford.py
python level5/exp19_intrinsic_time.py    # headline: clock vs driver
python level5/exp20_clock_forecast.py
python -m pytest level5/ -q              # 10 tests
```

Each experiment accepts `--quiet` and writes its summary to `results/`.
