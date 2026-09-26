# Diagnosis (protocol section 2) — development data only

Every number here comes from retained raw evidence or from untimed diagnosis runs on
DEVELOPMENT programs. No evaluation cohort was touched, and nothing was profiled while a
timing matrix ran. Files: `stage_a/` (commands in `logs/stage_a*`).

## 1. Accepted public-score recount, reproduced

`stage_a/PUBLIC_RECOUNT_REPRODUCTION.json` recomputes the accepted run's public scores from
`recovery_campaign_20260923_r3/p5/public_rows.jsonl` and the frozen serial records, using
the retained-evidence owner `optimization_stage_a.public_recount`.

| arm | protocol value | recomputed (all 15 repetitions identical) | absolute difference |
|---|---|---|---|
| Phase 2 `structural_bound` @0.1 | 2.0327602339438613 | 2.0327602339438613 | 0 |
| original direct (default) | 2.0084662022846573 | 2.008466202284657 | 4.4e-16 (summation order) |
| classical | 1.9013791212645499 | 1.9013791212645499 | 0 |

These are exact fixed-suite values. They say nothing about unseen programs: with eight
programs, of which only one (vector_reduction, J 480→396) differs between Phase 2 and the
original, a program-resampling interval legitimately touches zero while the suite ratio is
an exact arithmetic gain. Both statements hold at once.

## 2. The old 32-query cap (accepted run, 100 old held-out programs × 15 repetitions)

`stage_a/STOPPING_AUDIT.json`:

| budget | rows stopped by the 32-query cap | by the deadline | pass complete | programs capped in every repetition | ties vs budgeted that were capped in every repetition |
|---|---|---|---|---|---|
| 0.01 s | 939 / 1500 | 21 | 540 | 62 / 100 | 44 of 69 ties |
| 0.1 s | 960 / 1500 | 0 | 540 | 64 / 100 | 45 of 74 ties |
| 1.0 s | 960 / 1500 | 0 | 540 | 64 / 100 | 45 of 75 ties |

The reported "64 capped programs / 45 capped ties" reproduce from raw rows. At 0.1 s and
1.0 s the accepted controller never reached its deadline: it stopped on the cap or finished
its pass, so extra budget could not be used. All 510 accepted improvements came from
four-operation windows.

## 3. Target coverage

`stage_a/TARGET_COVERAGE.json` (untimed, 1.0 s, all 100 development programs). For every
accepted improvement we asked whether its new (C, S) lies in the union of the OLD target
rectangles of the incumbent it improved:

| arm | improvements | inside old rectangles | outside |
|---|---|---|---|
| A2 product search | 44 | 44 | 0 |
| A4 multiscale search | 163 | 159 | 4 |

The four A4 improvements outside every old rectangle are real, validated compilations, for
example seed 800016 (vector): (C, S) = (7, 32), J = 224 → (9, 24), J = 216, while the old
targets were (6, 32), (7, 31), (8, 27), (6, 37). A2's radius-2 windows produced no such
trade-off on development programs; the product domain admits them, but the development
data show them only when A4's larger neighborhoods are searched.

## 4. Where the time goes (cProfile, development population of the owner's profiler)

First two old held-out programs per family plus the eight public programs; cumulative
phase shares overlap and are not additive (`stage_a/PROFILE.json`). At 0.1 s:

- A0-equivalent (accepted controller, cap 32; profiled from the current tree, never
  measured as A0): domain construction 40% (`Domain.from_record`, of which program
  re-validation 20% and fact derivation 16%), search 49%, validation 13%.
- A1: search 68%, construction 16% (the domain memo removes most re-validation), option
  generation 10%, digests/serialisation 10% each.
- A2: search 65%, construction 17%, cap computation 4%.
- A3: propagated search 63% (child generation 22%, time propagation 11%, product bound
  8%), whole-domain digests 13%, serialisation 12%.
- A4: child generation 81%, time propagation 48% (dominated by rebuilding the fixed-issue
  table on every child), product bound 21%.

Two semantics-preserving engineering changes were made in response, BEFORE any measured
row: each domain digest is computed once per query and reused, and the engine-capacity rule
counts fixed issues once per query instead of copying the table per child. The complete
exhaustive soundness/parity suite passed before and after (45/45 tests).

Option checks were not a bottleneck in any arm (≤10%). State copying was below the 5%
reporting threshold everywhere.

## 5. What development then showed (DEV_compiler, 5,700 rows, 0 failures)

`DEVELOPMENT.json`. At 0.1 s, paired log(J_A0 / J_arm), equal family weights:

| arm | effect vs A0 | 95% (descriptive) | wins/ties/losses | compile time vs A0 |
|---|---|---|---|---|
| A1 deadline control | +0.0063 | [+0.0016, +0.0125] | 10/90/0 | 1.18× |
| A2 product search | +0.0063 | same | 10/90/0 | 0.96× |
| A3 propagated search | +0.0063 | same | 10/90/0 | 0.80× |
| A4 multiscale search | +0.0663 | [+0.0454, +0.0905] | 46/54/0 | 10.8× |

Removing the cap is worth +0.0063 and is all that A1–A3 gain in quality: at every budget
the A1→A2 and A2→A3 steps are exactly 0 at 0.1 s and 1.0 s (A2→A3 −0.0007 [−0.0020, 0.0000]
at 0.01 s). Propagation made the same search 17–20% cheaper without changing any result at
0.1 s. The whole A3→A4 step (+0.060 at 0.1 s, +0.076 at 1.0 s) bundles larger windows,
the catalog and the discrepancy traversal; this design does not separate their
contributions.
