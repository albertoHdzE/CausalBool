# Level 6 — The Clock as a Fractal Point Process, and Whether It Is Shared

Level 5 found that the information in an uncontrolled sequence lives in the clock
(the timing of representation-free pivots), not the driver (their sizes). Level 6
characterises that clock as a point process and asks whether it is idiosyncratic or
shared across instruments. Self-contained; Levels 1 to 5 untouched.

## Modules

- `point_process.py` — the Fano-factor scaling exponent alpha (F(T) ~ T^alpha;
  alpha near 0 is renewal, alpha > 0 is a self-similar clustered process, count
  Hurst = (1+alpha)/2); the windowed activity signal; and an MFDFA generalised
  Hurst h(q).
- `shared_clock.py` — align instruments on common trading days, form each one's
  activity signal, and build the leave-one-out common signal.

## Results (12 instruments, multi-decade daily)

- **Fractal clock (exp21):** alpha ≈ 0.5 (count Hurst ≈ 0.75) against a renewal
  null of ≈ 0, on clean power-law fits (R² ≈ 0.98), positive at every reversal
  scale theta and roughly scale-invariant. The clock is a self-similar fractal
  point process — the intra-pivot self-similarity, made a closed-form exponent.
- **Multifractal (exp22):** the waiting-time long memory is confirmed (h(1) ≈
  0.75), but the multifractal width excess over the finite-sample null is only
  +0.039 (8/12). Weak and inconclusive; reported as such.
- **Shared clock (exp23):** the activity signals correlate 0.478 on average, and a
  leave-one-out common signal explains R² ≈ 0.45 of each instrument's activity. The
  clock is largely shared. But it does not forecast an instrument's future activity
  beyond its own past (enhancement +0.012 vs null −0.004, 7/12, p = 0.39): the
  sharing is contemporaneous, not lead-lag predictive.

## Honesty

Only the fractal-clock exponent survives every null cleanly. The multifractality is
at the edge of the finite-sample bias, and the shared clock is a structural, not a
predictive, fact. Both are kept in view rather than dropped.

## Run

```
python level6/exp21_fractal_clock.py      # fractal point-process exponent
python level6/exp22_multifractal.py       # mono vs multifractal (weak)
python level6/exp23_shared_clock.py       # shared clock + forecast enhancement
python -m pytest level6/ -q               # 7 tests
```

Each experiment accepts `--quiet` and writes its summary to `results/`.
