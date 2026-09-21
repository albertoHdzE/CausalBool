# Profiles and their interpretation

Worker record. Plan section 5. Raw reports:
[`profile/reports/`](profile/reports); machine-readable summary
[`profile/profile.json`](profile/profile.json).

```sh
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase profile \
  --baseline results/direct_index_v4_optimization/baseline \
  --output results/direct_index_v4_optimization/profile
```

Programs are the smallest, median and largest public program by operation
count: `05_mixed_broadcast` (8), `01_scalar_pipeline` (16), `07_scalar_selects`
(20). Each was profiled with `optimise=False` and `optimise=True`.

**A deterministic profiler perturbs wall-clock behaviour and these times are
not performance results.** That caveat is not decorative here: it changed what
the first profile could see, and noticing that is what produced the second set
of profiles below.

## What the ordinary profile shows: construction

With `optimise=True` the cost is overwhelmingly the **construction** of
acceptance expressions, not the search over them.

`05_mixed_broadcast`, profiled total 0.763 s:

| Function | Cumulative | Own | Calls |
|---|---:|---:|---:|
| `direct_optimizer.optimise` | 0.807 | 0.001 | 1 |
| `JointQuery.expression` | 0.799 | 0.000 | 20 |
| `relation_cover` | 0.769 | 0.129 | 670 |
| `JointQuery._scratch_safety` | 0.728 | 0.000 | 10 |
| `schema_index.restrict` | 0.386 | 0.061 | 96,650 |
| `Term.bounds` | 0.100 | 0.069 | 194,480 |
| `Meter.check_time` | 0.042 | 0.019 | 128,887 |
| `normalise_cover` | 0.042 | 0.017 | 1,346 |
| `JointQuery._engine_capacity` | 0.039 | 0.000 | 10 |
| `schema_index.solve` | 0.010 | 0.002 | 6 |

`07_scalar_selects` is the same shape at larger scale: `relation_cover` 0.556
of 0.594 cumulative over 1,615 calls, `_scratch_safety` 0.489, `restrict`
66,766 calls, `Term.bounds` 136,050 calls.

The chain is **`_scratch_safety` → `relation_cover` → `restrict` + `bounds`**.
`_scratch_safety` compares every affected value against every other value, and
each comparison is an exact cover built by splitting cubes; each split builds
two cubes through `restrict`, and each node evaluates both operands' extrema
through `Term.bounds`.

`normalise_cover` is called 1,346 times for 670 covers — twice per cover, once
where the cover is finished and again inside `Leaf.__post_init__`, sorting and
de-duplicating an already canonical tuple.

With `optimise=False` the whole compilation is 1–2.6 ms and the profile is flat:
`interval`, `_subtract_cover`, `difference`, and — telling for a path that does
so little — 1,651 calls to `_require_index`, 1,651 to `_plain_int`, 538 to
`universe_mask` and 4,593 to `isinstance` for a twenty-operation program.

## Why that profile was not the whole picture

`schema_index.solve` appears at 0.010 s of 0.807 — under 2%. That is an
artefact. The per-query budget is **100 ms of wall clock**, and the profiler
slows construction by roughly fivefold, so the clock expires while the
expression is still being built and the search never runs. Profiling under the
production budget can only ever see construction.

So the queries that the production budget cannot finish were profiled again
with a deterministic but generous budget — the only way to see solver
traversal and cover intersection at all.

| Program | Window | Width | Status on exhaustion | Profiled search | Visited | Intersections |
|---|---|---:|---|---:|---:|---:|
| `mixed_broadcast` | 0,2,3,4 | 56 | UNSAT | 89.73 s | 656,373 | 48,950,288 |
| `mixed_broadcast` | 2,3,4,5 | 56 | UNSAT | 33.27 s | 223,527 | 18,167,151 |
| `scalar_pipeline` | 3,4,6,9 | 56 | UNSAT | 76.38 s | 4,391,932 | 35,625,921 |
| `scalar_selects` | 8,9,12,13 | 58 | UNKNOWN | 119.92 s (cap) | 13,017,227 | 48,668,481 |
| `scalar_selects` | 10,11,12,13 | 58 | UNKNOWN | 119.92 s (cap) | 7,471,493 | 54,301,916 |

Unprofiled, the first of these exhausts in **19.7 s** and another in 412 ms.
Against a 100 ms budget, neither can finish.

The search profile of the first, by own time out of 89.73 s:

| Function | Own | Cumulative | Calls |
|---|---:|---:|---:|
| `schema_index.intersect` | 15.54 | 56.80 | 48,950,288 |
| `schema_index.solve` | 10.65 | 89.73 | 1 |
| `builtins.isinstance` | 8.44 | 8.44 | 198,440,708 |
| `_require_same_width` | 8.28 | 12.08 | 48,950,288 |
| `_require_index` | 8.23 | 20.87 | 49,520,230 |
| `universe_mask` | 8.17 | 28.84 | 49,092,774 |
| `Meter.intersection` | 7.31 | 21.71 | 48,950,288 |
| `Meter.check_time` | 6.71 | 14.59 | 49,587,430 |
| `Meter.elapsed` | 4.79 | 7.88 | 49,587,431 |
| `time.monotonic` | 3.09 | 3.09 | 49,587,431 |
| `Cube.__post_init__` | 0.075 | 0.35 | **142,485** |

Read that last row against the first. `intersect` was called **48,950,288**
times and constructed **142,485** cubes: **99.7% of calls return `None`.** The
work that matters — one exclusive-or, one and, one comparison — is a rounding
error. What the search actually spent its time on was revalidating widths it
had already validated (`universe_mask` at 28.84 s cumulative, 32% of the run),
re-typechecking cubes this module itself had just built (198 million
`isinstance` calls), and consulting the clock 49.6 million times.

## What each proposed change is anchored to

| Change | Profiled hotspot | Invariant it must preserve | Test that detects a wrong answer |
|---|---|---|---|
| Derive cubes without revalidating | `Cube.__post_init__`, `_require_index`, `universe_mask` | anchor ≤ U, free ≤ U, anchor ∧ free = 0 | `DerivedCubeInvariantTests` feeds every produced cube back through the public constructor, exhaustively for widths 0–5 |
| Drop the universe mask from `intersect` | `universe_mask` 28.84 s cumulative | `x ∧ ¬y ≡ x ∧ (U ⊕ y)` for `x, y ≤ U` | `test_intersection_results_are_valid_cubes`, and the pre-existing exhaustive set comparison over all 66,430 cube pairs |
| Pending chain instead of tuple copying | `solve` own time 10.65 s | identical exploration order | `SolverEquivalenceTests`, including the first-witness order |
| Charge a leaf's cover once | `Meter.intersection` 21.71 s, `check_time` 14.59 s | the accumulated counter is unchanged; overshoot bounded by one cover | `test_every_alternative_is_still_charged_to_the_meter`, `test_an_expired_clock_still_stops_the_search` |
| Precomputed deadline | `Meter.elapsed` 7.88 s | `monotonic() > started + seconds ≡ elapsed > seconds` | `MeterDeadlineTests`, plus the two pre-existing expired-meter fixtures |
| `split` for both cofactors | `restrict` 96,650 calls | the two parts partition the cube exactly | `SplitTests` against `restrict` for every free coordinate at widths 1–5 |
| Hoisted operand extrema | `Term.bounds` 194,480 calls | same extrema, constants included | the pre-existing index-by-index cover oracle |
| Single-pass normalisation | `normalise_cover` called twice per cover | canonical order and exact de-duplication | `NormalisationFastPathTests`, including mixed widths and non-cubes |
| Reuse relation covers | `relation_cover` 0.769 of 0.807 | key carries every semantic input; a hit costs what the miss cost | `CoverCacheTests` (nine tests) and `CacheFreeJointQueryEquivalenceTests` |
| Incremental full-cycle index | bootstrap `_earliest_cycle` rescans the calendar | the same blocked set, in the same order | `ScheduleBookkeepingTests` against a full rescan, per operation |
| One compatibility test in subtraction | bootstrap `_subtract_cover` → `compatible` twice | identical cover, in identical order | `SubtractionTests` over every cube at widths 1–4 |

Each of those tests was confirmed to **fail** on a planted defect before being
relied upon; the mutations and their verdicts are listed in
[REVIEW_HANDOFF.md](REVIEW_HANDOFF.md).

## The measurement the profile could not give

The profile says where the time goes. It does not say how much wall clock can
be recovered, because the dominant queries are stopped by a **clock**, not by
finishing. A query that burns its 100 ms budget still burns 100 ms after the
code beneath it is made faster — it merely searches further in the same time.
That accounting, and what actually happened when the changes were measured, is
in [BENCHMARK.md](BENCHMARK.md).
