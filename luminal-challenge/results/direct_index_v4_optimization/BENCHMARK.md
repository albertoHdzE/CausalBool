# Benchmark: what was measured, and what it means

Worker record. Plan section 4. Nothing here is accepted; only the lead accepts.

## Commands

All run from `luminal-challenge` with `python3` 3.13.12 on
macOS-26.6.2-arm64, 28 logical CPUs, serially and with no competing benchmark.

```sh
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase baseline \
  --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization/baseline
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase profile \
  --baseline results/direct_index_v4_optimization/baseline \
  --output results/direct_index_v4_optimization/profile
PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 \
  --output results/direct_index_v4_optimization/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/direct_index_v4_optimization/comparison
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase final \
  --baseline results/direct_index_v4_optimization/baseline --repeats 15 \
  --seed 20260920 --output results/direct_index_v4_optimization/final
python3 check_optimization_evidence.py --root results/direct_index_v4_optimization
git diff --check -- luminal-challenge
```

Every exit code is in [REVIEW_HANDOFF.md](REVIEW_HANDOFF.md). Raw rows:
[`baseline/runs.json`](baseline/runs.json), [`final/runs.json`](final/runs.json).
The first attempt at the final phase failed in its aggregation step and is
retained at [`final_round1_failed/`](final_round1_failed).

## Protocol

Five arms, each `(arm, program, repetition)` in a fresh isolated process under a
20-second external timeout: frozen classical, and the frozen v3 export and the
candidate export each at `optimise=False` and `optimise=True`. **Frozen and
candidate are measured together in the same run**, so no candidate time is
divided by a historical number. Fifteen repetitions on the eight public
programs; arm order shuffled within each `(program, repetition)` from seed
`20260920` and retained in `runs.json`.

Only the compiler call is timed, including any validation it performs
internally. Reference validation and every case check happen after the timer,
for every arm alike. No internal safety check was disabled to make the
implementations comparable. Imports and whole-process time are recorded
separately. **No warmups were discarded, no outliers removed, no run retried.**
There were no failed rows to keep: 600 of 600 public rows and 1,500 of 1,500
corpus rows succeeded.

Membership comes from the official comparator's pinned public set, not a
truncated glob. Every worker response is checked against the arm, the program
*and* the compilation mode that were requested.

Statistics, kept apart and never mixed:

- **speedup** = baseline median compile time ÷ candidate median;
- **primary aggregate** = equal-program geometric mean of per-program median
  ratios;
- **pooled median ratio** = median of all baseline times ÷ median of all
  candidate times — a different quantity, reported explicitly;
- **95% interval** = paired bootstrap, 10,000 resamples, seed `20260920`,
  resampling repetition identifiers within each program and applying the same
  draw to every arm. This measures timing uncertainty **on this fixed suite of
  programs**. It says nothing about programs outside it.

## Headline result

| Comparison | Geomean of per-program median ratios | 95% paired interval | Pooled median | Programs slower |
|---|---:|---|---:|---:|
| `candidate_full` vs frozen v3 full | **1.9889x** | 1.9841 – 1.9913 | 2.4775x | 0 of 8 |
| `candidate_bootstrap` vs frozen v3 bootstrap | **1.1371x** | 1.1334 – 1.1406 | 1.1776x | 0 of 8 |
| `candidate_full` vs classical | 0.0014x | 0.0014 – 0.0014 | 0.0015x | 8 of 8 |
| `candidate_bootstrap` vs classical | 0.4674x | 0.4654 – 0.4699 | 0.4618x | 8 of 8 |
| frozen v3 full vs classical | 0.0007x | 0.0007 – 0.0007 | 0.0006x | 8 of 8 |
| frozen v3 bootstrap vs classical | 0.4110x | 0.4096 – 0.4131 | 0.3922x | 8 of 8 |

### Both engineering targets were missed

| Target (plan section 1) | Required | Measured | Interval lower bound | Met? |
|---|---:|---:|---:|---|
| Full-direct geometric-mean speedup vs freshly measured v3 | ≥ 2.00x, CI low > 1.0 | 1.9889x | 1.9841 | **NO** |
| Bootstrap speedup by the same criterion | ≥ 1.20x, CI low > 1.0 | 1.1371x | 1.1334 | **NO** |

Both speedups are real — each interval excludes 1.0 by a wide margin, and the
baseline phase measured the harness's own noise floor at 1.0001x (0.9996–1.0005)
for the full path, so neither is an artefact. But the full-direct interval
*also excludes 2.00*, and the bootstrap interval excludes 1.20. The targets are
missed, narrowly in the first case and clearly in the second. **They are
reported as missed. They were not adjusted after the measurements.**

### No claim that direct compilation is faster than classical

It is not, and this phase does not claim it is. The candidate full path is
about **714 times slower** than classical by these medians (171.1 ms against
0.264 ms pooled) and the candidate bootstrap about **2.14 times slower**
(0.572 ms against 0.264 ms). Both improved — from 1,449x and 2.43x — and both
remain far from parity. Section 4's paired criterion for a faster-than-classical
claim is not met and no such claim is made.

## Per-program medians, final phase (milliseconds)

| Program | classical | frozen bootstrap | frozen full | candidate bootstrap | candidate full |
|---|---:|---:|---:|---:|---:|
| scalar_pipeline | 0.2949 | 0.6783 | 201.2629 | 0.5701 | 115.4619 |
| scalar_dual_chain | 0.1802 | 0.3878 | 216.9460 | 0.3458 | 139.2151 |
| vector_axpy | 0.1953 | 0.5011 | 229.4438 | 0.4386 | 135.9883 |
| vector_bitmix | 0.2349 | 0.6667 | 447.6576 | 0.5733 | 203.3079 |
| mixed_broadcast | 0.1517 | 0.3478 | 660.0376 | 0.3138 | 458.1485 |
| parallel_memory | 0.3567 | 0.9642 | 414.5824 | 0.8112 | 152.9145 |
| scalar_selects | 0.3441 | 0.7959 | 527.5735 | 0.7865 | 196.3730 |
| vector_reduction | 0.3964 | 0.9420 | 435.5208 | 0.7960 | 188.3239 |

No public program got slower on either path.

## Correctness is unchanged, program by program

Combined score recomputed from the raw integers, identical for all four direct
arms in both the baseline and the final phase:

**2.008466202284657** — the accepted v3 value, within 4e-16.

| Arm | Combined score |
|---|---:|
| classical | 1.9013791212645499 |
| frozen bootstrap / frozen full / candidate bootstrap / candidate full | 2.008466202284657 |

The accepted v3 review records `2.0084662022846573` and the official comparator
records `2.008466202284657`. Those are the same number to one unit in the last
place; the difference is the order in which the logarithms are summed by two
equivalent formulas, not a difference in any measured integer.

Gate 6 requires that no candidate per-program `cycles × scratch` product exceed
frozen v3's. **Zero violations**, and every product is not merely bounded but
identical:

| Program | frozen full | candidate full | frozen bootstrap | candidate bootstrap |
|---|---|---|---|---|
| scalar_pipeline | 14×6=84 | 14×6=84 | 14×6=84 | 14×6=84 |
| scalar_dual_chain | 8×3=24 | 8×3=24 | 8×3=24 | 8×3=24 |
| vector_axpy | 10×24=240 | 10×24=240 | 10×24=240 | 10×24=240 |
| vector_bitmix | 10×40=400 | 10×40=400 | 10×40=400 | 10×40=400 |
| mixed_broadcast | 10×24=240 | 10×24=240 | 10×24=240 | 10×24=240 |
| parallel_memory | 13×40=520 | 13×40=520 | 13×40=520 | 13×40=520 |
| scalar_selects | 9×6=54 | 9×6=54 | 9×6=54 | 9×6=54 |
| vector_reduction | 12×40=480 | 12×40=480 | 12×40=480 | 12×40=480 |

Bootstrap metrics are identical to the freshly verified v3 bootstrap, as gate 6
requires.

## Why the naive ceiling argument was wrong, and what actually happened

This is the part of the result worth the lead's attention.

The baseline measurement suggested the phase could not succeed at all. Of the
424 ms median full-direct compile, **82.5% was spent on 3.5 queries per
compilation that exhausted their 100 ms wall-clock budget and returned
UNKNOWN** — no information, and a cost pinned by a clock. A query stopped by a
clock still costs 100 ms after the code beneath it is made *k* times faster; it
merely searches further in the same time. On that reading the maximum
achievable speedup is

    1 / (0.825 + 0.175/k)  →  1.21x  as k → ∞

and the 2.00x target would be unreachable by any amount of constant-factor
work. Profiling one such query to exhaustion under a generous budget supported
the pessimism: it needs **19.7 seconds** of search to finish. No plausible
speedup rescues that.

The measured result is 1.9889x, which exceeds that ceiling, so the premise was
wrong. The reason is that the budget system has **two kinds of limit**, and
only one of them is a clock. The declared limits are 100 ms, 50,000 visited
cubes, 20,000 expression records and 4,096 cubes per atomic cover. A query
stopped by the clock is incompressible. A query stopped by a *countable* cap
finishes in wall time proportional to the cost per unit of work, and therefore
compresses exactly as the code does.

Making the search faster migrated queries from the first kind to the second.
Across the eight public programs, the candidate's UNKNOWN searches now stop like
this:

| Reason the search stopped | Count |
|---|---:|
| visited-cube budget exhausted (50,000 cubes — a declared, countable cap) | 22 |
| time budget exhausted (100 ms) | 4 |

In the baseline essentially all of them stopped on the clock, having reached
only 21,000–33,000 cubes. They now reach the full declared 50,000 — **more of
the space explored, not less** — and reach it sooner in wall-clock terms.

No budget was weakened to obtain this. `max_visited` is 50,000 in `Limits`
before and after; the searches that stop on it return UNKNOWN exactly as
before. What changed is that they arrive at that declared cap in 30 ms instead
of never arriving within 100 ms.

The remaining three effects are ordinary:

- 30 of 420 formerly time-exhausted searches now **complete** and return proven
  UNSAT (UNSAT rises 375 → 405, UNKNOWN_SEARCH falls 420 → 390 over 120
  compilations). The plan anticipates this: faster code may legitimately finish
  a formerly UNKNOWN query within the same limits. It is additional completed
  work, not drift, and the optimiser's behaviour is identical either way since
  both outcomes continue to the next query.
- Construction became cheap enough that `UNKNOWN_CONSTRUCTION` fell from 24 to
  6 on the evaluation corpus (it was already 0 on the public programs).
- Cover reuse hit 65%–76% per compilation, never refused an entry, and retained
  at most 18,747 cubes.

The number of attempted queries is **unchanged at 3,270** and the infeasible
count is **unchanged at 2,475**. No window was skipped, no budget lowered, no
search shortened. The search policy is byte-for-byte the policy the lead
accepted.

## Frozen evaluation corpus

100 programs, twenty per family, seed `20260921`, frozen before tuning and
re-hashed before use (**integrity: 100 of 100 verified**). Three repetitions per
arm, 1,500 rows, 0 failures, every case validated against the reference.

This corpus was **not tuned against**. Tuning used the public and regression
programs; the corpus was run once, at the end, and its results are reported as
they came out. It is produced by the same generator as the acceptance corpus and
is **not statistically independent** of it.

| Comparison | Geomean | 95% interval | Programs slower |
|---|---:|---|---:|
| `candidate_full` vs frozen full | 1.9662x | 1.9606 – 1.9674 | 0 of 100 |
| `candidate_bootstrap` vs frozen bootstrap | 1.1458x | 1.1397 – 1.1549 | **1 of 100** |
| `candidate_bootstrap` vs classical | 0.7256x | 0.7199 – 0.7308 | 67 of 100 |
| `candidate_full` vs classical | 0.0066x | 0.0066 – 0.0067 | 100 of 100 |

**One program regressed** on the bootstrap path. It is retained and reported
rather than discarded. The bootstrap is closer to classical here (1.38x slower)
than on the public programs (2.14x slower).

### The optimiser earns its place here, and only here

| Arm | Programs | Score geomean | Median | Min | Max | Accepted improvements |
|---|---:|---:|---:|---:|---:|---:|
| classical | 100 | 2.370890 | 2.3198 | 1.3891 | 4.1980 | — |
| bootstrap (frozen and candidate) | 100 | 2.362098 | 2.3050 | 1.3891 | 4.3459 | 0 |
| full (frozen and candidate) | 100 | **2.376597** | 2.3254 | 1.3891 | 4.3459 | **18** |

On the eight public programs the optimiser accepts nothing and bootstrap and
full-direct are metrically identical. **On this corpus that hypothesis is
false**: six distinct programs improve, consistently across all three
repetitions, and the score rises from 2.362098 to 2.376597. The six, with
bootstrap against full:

| Program | Bootstrap | Full |
|---|---|---|
| `additional_211921` | 8 × 64 | 8 × **56** |
| `additional_241372` | 6 × 24 | 6 × **16** |
| `additional_283497` | 12 × 24 | **11** × 24 |
| `additional_321817` | 7 × 40 | 7 × **33** |
| `additional_375932` | 6 × 9 | 6 × **8** |
| `additional_293789` | 9 × 24 | 9 × **18** |

The frozen and candidate arms accept the **same 18 improvements on the same six
programs**, so the optimization did not change what the optimiser finds. Every
arm's metrics were deterministic across repetitions on this corpus (`varying`
is zero for all five arms), which is worth noting because time-bounded search
need not be.

Full-direct also edges classical on score here — 2.376597 against 2.370890 —
at roughly 150 times the runtime.

## Limitations

- Eight public programs for the headline result, 100 generated programs for the
  evaluation corpus. The private grader is unavailable; nothing is inferred
  about it.
- The paired interval is uncertainty over repetitions **on these fixed program
  suites**. It does not establish generalization to other programs.
- These are single-machine measurements under ordinary load. The classical and
  frozen full-direct medians happen to reproduce the accepted v3 figures
  closely, which is reported as observed and was not required.
- Profiler times in [PROFILE.md](PROFILE.md) are not performance results, and
  the profiling runs were kept entirely separate from the timed runs.
- All timings are cold-cache, fresh-process. No warm-cache experiment was run,
  so none is labelled as one.
- The combined scores here use the protected historical serial integers; serial
  is not one of this harness's arms. `compare_direct.py` measures serial itself
  and its `frozen_integer_metrics` gate is what keeps that record honest — it
  passed, 48 measurements, 0 disagreements.
- Nothing here establishes global optimality, private-grader performance,
  general compactness, or any complexity-theoretic result.
