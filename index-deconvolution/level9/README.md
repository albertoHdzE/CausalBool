# Level 9 — A Three-Number Generative Program for the Clock

The Algorithmic-Probability idea, done right. Compressing the raw price path is
hopeless (it is incompressible — direction is unforecastable). But the *clock* — the
self-similar pivot point process of Levels 5–7 — **is** compressible, and it has a
canonical short program: the exponential **Hawkes** self-exciting process, three
numbers `(mu, alpha, beta)`. Self-contained; Levels 1–8 untouched.

## Module

- `hawkes.py` — exact Hawkes log-likelihood (Ogata O(N) recursion), a coarse-to-fine
  grid maximum-likelihood fit, the Poisson null, held-out (out-of-sample)
  log-likelihood, and an Ogata-thinning simulator. The **branching ratio**
  `n = alpha/beta` is the order parameter (0 = memoryless, 1 = critical).

## Results (12 instruments, ~30+ years, exp29)

- **Self-exciting: n = 0.69 vs shuffle 0.01, 12/12.** The clock is strongly
  self-exciting — but **sub-critical** (0.69, not ~1). The moon-shot "edge of
  instability" is *not* reached at daily resolution (tick studies find ~0.9).
- **Predicts out of sample:** the 3-number Hawkes beats Poisson by +0.059 nats/event
  on the held-out 30%, 12/12.
- **Compresses:** 3 numbers replace ~1,382 event times per series.
- **Regenerates the fractal:** simulating the fit reproduces the clustering exponent
  (Fano 0.41 vs real 0.49).
- **RG flow:** the branching ratio is ~0.62–0.69 across fine reversal scales,
  softening at coarse ones — an approximate self-similar generator.

## Honesty

The bold half — criticality, a clean RG fixed point — is **not** supported at daily
scale. The grounded half is decisive: the discovered clock has an explicit short
generating program that beats the shuffle everywhere, forecasts held-out events, and
regenerates the clustering. A single-exponential kernel under-captures the full
self-similarity (0.41 vs 0.49); a multi-scale/power-law kernel is the honest next
step.

## Run

```
python level9/exp29_hawkes_clock.py       # fit, branching ratio, OOS, regeneration, RG flow
python -m pytest level9/ -q               # 6 tests
```

Accepts `--quiet`; writes `results/exp29_hawkes_clock.json`.
