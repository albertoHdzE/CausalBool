# Level 7 — The Clock of the Clock, and the Joint Law of a Leg

Level 6 characterised the pivot-timing clock as a self-similar fractal point
process. Level 7 asks two further questions and reports both honestly. Self-
contained; Levels 1 to 6 untouched.

## Modules

- `recursion.py` — the meta-clock: the pivots of the activity signal itself
  (absolute directional-change threshold, since the activity is a non-negative
  count), and its Fano exponent.
- `joint_law.py` — the within-leg diffusion exponent (|dv| ~ dt^H) and the
  cross-leg couplings of duration and size.

## Results (12 instruments, multi-decade daily)

- **Clock of the clock (exp24):** the meta-clock clusters beyond the null (Fano
  excess +0.182, 10/12), so a hierarchy of bursts exists — but the meta exponent
  (0.13) is far below the base (0.51): the clustering **attenuates with recursion
  depth**. A partial hierarchy, not a scale-invariant cascade. Self-similarity
  holds across reversal scale (Level 6), not across depth.
- **Joint law (exp25):** the null legs are Brownian (H = 0.485 ≈ 1/2, a validated
  reference) and the **real legs are sub-diffusive: H = 0.343, on 10/12** —
  excursions travel less than a random walk of the same duration. The cross-leg
  couplings are ≈ 0: a long calm does **not** precede a big move (honest negative).

## Honesty

One shallow-but-real hierarchy, one clean sub-diffusion result with a
Brownian-validated null, and one genuine negative. The robust core of the whole
programme remains what survives every null: the clustering of pivot timing and its
within-leg sub-diffusion.

## Run

```
python level7/exp24_clock_of_clock.py     # bursts of bursts (partial hierarchy)
python level7/exp25_joint_law.py          # within-leg sub-diffusion; cross-leg null
python -m pytest level7/ -q               # 6 tests
```

Each experiment accepts `--quiet` and writes its summary to `results/`.
