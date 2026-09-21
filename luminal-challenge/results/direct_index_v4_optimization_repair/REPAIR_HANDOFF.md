# Repair of R1–R4 — handoff for lead review

Worker: Claude Opus 5, working linearly without subagents.
Responding to: [lead review](../direct_index_v4_optimization/REVIEW.md),
verdict CHANGES_REQUIRED, 2026-09-20. Plan: optimization v1.1.
Machine-readable gate table: [gates.json](gates.json).

**Nothing here is accepted. Only the lead accepts.** No submission, push or
publication. No new speed experiment was attempted and no target was altered.

---

## Summary

All three blocking defects are repaired and the reporting corrections are made.
Every defect was first reproduced, then covered by a regression that failed on
the reviewed code, then fixed.

| Finding | State | Observable, before → after |
|---|---|---|
| R1 deadline bypass on a terminal verdict | **CLOSED** | `UNSAT, elapsed=2.0` → `UNKNOWN, reason="time budget exhausted"` |
| R2 benchmark detects a failed control, exits 0 | **CLOSED** | exit `0` with 90 recorded discrepancies → exit `1`; silent corpus skip → exit `2` before measuring |
| R3 evidence checker accepts corrupted evidence | **CLOSED** | 4 of 4 mutations left `all_passed=True` → 6 of 6 mutations rejected, control passes |
| R4 reporting corrections | **DONE** | five corrections below, with the v4 handoff preserved and marked superseded |

The repaired candidate still passes everything it passed before: 300 direct
tests, 142 corpus programs, 277 cases, all seven official comparison gates, and
the combined public score **2.008466202284657** — the accepted v3 value.

**Both engineering targets remain missed and the measured speedups fell
slightly**, because R1's repair adds clock reads the defective version skipped:

| Target | Required | v4 (defective) | Repaired | 95% paired CI | Met |
|---|---:|---:|---:|---|---|
| Full-direct vs frozen v3 | ≥ 2.00x | 1.9889x | **1.9536x** | 1.9503 – 1.9567 | **NO** |
| Bootstrap vs frozen v3 | ≥ 1.20x | 1.1371x | **1.1380x** | 1.1327 – 1.1411 | **NO** |

The full-direct figure falls about 1.8%. That is the price of the correctness
repair and it is reported as such, not hidden.

---

## R1 — deadline bypass on the final conflicting cover

**Reproduced first.** The lead's probe, rerun unmodified before any edit,
returned `UNSAT` at `elapsed=2.0` against a one-second budget. Retained at
[`reproduction/probes_before_repair.json`](reproduction/probes_before_repair.json);
the lead's own `probes.json` was backed up and restored byte-identically.

**Cause.** `solve` charges a leaf's whole cover before scanning it, so the clock
is read before the scan and not during it. When that scan leaves no survivor it
empties the stack, and the loop fell through to `UNSAT` — a positive claim that
the declared domain holds no solution — without reading the clock again. My
rationale that "every popped state checks time" did not cover a path where
there is no next popped state. The lead is right that this is a resource
contract violation and not a wrong logical answer.

**Repair**, in `schema_index.py`:

- the clock is read immediately **after** each leaf scan, so the time that scan
  consumed is always observed;
- the clock is read again before the terminal `UNSAT` return, covering branches
  that empty the stack without scanning anything, such as a disjunction with no
  children.

The same class of defect was then found and fixed one level up: `relation_cover`
finished a cover, validated its size with `cover_limit` — which reads no clock —
and returned it as a completed relation. It now observes the deadline before
certifying, exactly as the solver does.

**Granularity is bounded and stated.** Between two clock observations lies at
most one cover scan, of at most `max_cover` alternatives, itself validated
against that cap before the search starts. No completed verdict is certified on
a meter whose deadline has already passed.

**Nothing else moved.** Visit and record caps are unchanged, the search order is
unchanged, and both v3 expression-cache retry regressions still pass.

**Eight regressions added** in `tests_direct/test_schema_index.py`, driven by an
injected deterministic clock so nothing depends on wall-clock timing. One of
them — the lead's exact scenario — failed on the reviewed code and passes now;
the other seven already held and are kept as durable statements of the property,
which is reported plainly rather than counted as newly caught.

| Probe | Before | After |
|---|---|---|
| final all-conflicting cover, clock expired | UNSAT, elapsed 2.0 | **UNKNOWN**, "time budget exhausted" |
| same query, inside budget | UNSAT | UNSAT (unchanged) |

---

## R2 — a detected control failure must reach the exit code

**Reproduced first.** Replaying real rows through the real `phase_final` with
classical cycles doubled and scratch halved: the report recorded **90 historical
integer discrepancies** and the phase returned **exit 0**.

**Cause.** `phase_final` derived success from membership alone. Its own
frozen-integer control was computed correctly, recorded a real failure, and was
never consulted. It also recorded a frozen-snapshot mismatch *after* measuring
instead of refusing before.

**Repair**, in `benchmark_optimization.py`:

- `acceptance_gates()` defines one mandatory conjunction for both phases:
  membership, row validity, frozen classical integers, per-program product
  nonregression, bootstrap metric equality, the score floor, and — for a final
  run — that the frozen evaluation corpus was actually measured;
- `report_gates()` prints every gate and derives the exit status from the
  conjunction and nothing else;
- a frozen-snapshot mismatch is **refused before a single measurement is taken**;
- `--skip-extra-corpus` is refused outright unless `--diagnostic` is given, and
  a diagnostic run is stamped `acceptance_claimed: false` with a prominent
  notice, so a reduced run cannot be cited as acceptance evidence.

**A missed speed target is deliberately not a gate.** It is an outcome of the
experiment, reported under `performance_targets`. Both targets are missed and
both runs still pass their correctness conjunction, which is the intended
behaviour.

| Probe | Before | After |
|---|---|---|
| product-preserving classical drift | exit **0**, 90 discrepancies recorded | exit **1** |
| clean replay, corpus skipped, diagnostic | (not distinguished) | exit **1**, `acceptance_claimed: false` |
| corpus skipped without `--diagnostic` | (not distinguished) | exit **2**, **0 measurements started** |

**Eleven regressions** in `tests_direct/test_benchmark_harness.py` drive each
gate to failure individually and check the real phase entry point's exit codes.
Two mutations confirm they are not vacuous: making `report_gates` ignore the
conjunction fails 3 tests, and removing the snapshot refusal fails 1.

A latent crash was found and fixed while writing these: `analyse` asked for the
median of an empty list when an arm's rows carried no optimiser timing.

---

## R3 — the evidence checker accepts missing or corrupted evidence

**Reproduced first.** All four of the lead's mutations left
`Checker.run()['all_passed'] == True`.

**Cause.** The checker read several of the report's own assertions instead of
recomputing them, derived the expected arms, programs and repetition counts
from the report under examination — so a reduced contract passed itself — and
never audited the extra corpus at all.

**Repair.** `check_optimization_evidence.py` is rewritten:

- **The contract is fixed here and in the pinned inputs, never read from the
  report.** Arms from the harness module, programs from the pinned reference
  directory, repetition counts and corpus size from the plan. A report that
  measured less now fails instead of redefining what was required.
- Required field and key coverage is enforced for every report, every row and
  the corpus manifest.
- Both exports are **hashed from disk**; the snapshot linkage is established by
  comparing those hashes, not by reading a stored boolean. The candidate export
  is reassembled from source and compared.
- The harness and the checker itself are now part of the required hash set,
  because they produce and audit the numbers.
- Scores, per-program products, bootstrap metric equality, aggregate ratios,
  **confidence intervals** and **target decisions** are all recomputed from the
  raw rows with the declared seed. The resample count is taken from the report,
  so `--resamples` cannot weaken the comparison.
- Stored gate flags are recomputed and compared, never trusted.
- The extra corpus is fully audited: manifest fields, per-family counts, every
  input re-hashed from disk, exact row membership, per-program case counts, and
  the score distribution recomputed from the manifest's own serial integers.
- Rows must carry positive finite timings. When rows fail validation, no
  statistic is recomputed from them and that refusal is itself recorded.
- `--baseline` accepts an external frozen baseline, so a repair round reuses an
  earlier round's snapshot and corpus without overwriting them.

| Mutation | Before | After (failing check) |
|---|---|---|
| remove the whole extra-corpus payload | passed | **rejected** — `extra_corpus:final` |
| erase source and test hash maps | passed | **rejected** — `recorded_hashes:final` |
| replace every interval with [999, 1000] | passed | **rejected** — `confidence_intervals:final` |
| product-preserving classical drift | passed | **rejected** — `comparison_gates` |
| drop an arm from the contract | not tested | **rejected** — `contract:final` |
| forge a stored gate flag | not tested | **rejected** — `gate_flags_recomputed:final` |

Control: the unmutated repair tree passes all 42 checks, exit 0.

**Twenty-four regressions** in `tests_direct/test_evidence_checker.py` run every
mutation through the real entry point on a temporary copy, so no recorded
evidence is touched.

---

## R4 — reporting corrections

### 1. "Ruled out: further constant-factor work on the search" — withdrawn

That claim is withdrawn in full. The lead is right that this phase shows the
opposite: queries migrating from the time limit to count limits, and some
completing that previously did not. What the evidence supports is that *under
the current declared limits* the remaining time-exhausted queries need seconds
rather than milliseconds, so a constant-factor gain is unlikely to finish them.
It says nothing about whether future speedups are possible and it is not a wall
of the method.

### 2. Geometric means and pooled medians, separated and labelled

The v4 handoff's "714x slower" was obtained by inverting a number already
rounded to four decimals. It corresponds to no statistic. Corrected, from
unrounded raw data, with each statistic named:

| Comparison | Geomean of per-program median ratios (inverted) | Pooled median ratio (inverted) |
|---|---:|---:|
| candidate full vs classical | **513.24x slower** | **663.38x slower** |
| candidate bootstrap vs classical | **1.5207x slower** | **2.1774x slower** |
| frozen v3 full vs classical | 1002.67x slower | 1610.90x slower |
| frozen v3 bootstrap vs classical | 1.7306x slower | 2.5490x slower |

These two columns are different statistics and are never mixed. The bootstrap
figures differ noticeably from the v4 round because the classical arm was
slower in this run on two programs — `parallel_memory` 1.3935 ms and
`scalar_selects` 1.3763 ms against roughly 0.35 ms in the earlier round. That is
machine variation in the *baseline* arm, not a change in the candidate, and it
is why a classical-relative ratio must be read with its run.

### 3. The 82.5% / 1.21x ceiling — replaced with a measured attribution

It was a heuristic built from aggregated medians and an assumption that every
unfinished query costs the whole timeout, and it was presented as a
decomposition. It is withdrawn and replaced by a direct per-query measurement
over all eight public programs, produced by
[`attribution/measure_attribution.py`](attribution/measure_attribution.py),
which replays the optimiser's enumeration outside the production path and times
each query individually. Production code is neither modified nor instrumented.

| Query outcome | Queries | Share of optimiser wall-clock |
|---|---:|---:|
| UNKNOWN, visited-cube cap reached (a countable declared limit) | 25 | **62.00%** |
| UNKNOWN, time budget exhausted (the clock) | 4 | **22.68%** |
| UNSAT, search completed | 35 | 15.13% |
| Infeasible as posed | 194 | 0.18% |

So on the repaired candidate, 22.68% of optimiser time is pinned by the clock
and the remaining 77.32% is spent on work that ends at a countable limit or
completes — and therefore compresses with the code. This is a measured
attribution from one in-process diagnostic run, not a performance result and
not a bound.

### 4. Row counts corrected

The v4 handoff said "2,100 benchmark direct rows". 2,100 is the whole final
phase including the classical arm. The direct rows are **1,680** — 480 public
and 1,200 corpus. The repair round's counts are in [gates.json](gates.json).

### 5. "All eleven gates pass" superseded

Superseded by the lead review. The v4 handoff is preserved unedited apart from a
short header pointing at the review and at this document; its body is left as
the historical record it is.

---

## Results of the repaired round

All commands from `luminal-challenge`, Python 3.13.12, macOS-26.6.2-arm64.

| Command | Exit | Result |
|---|---:|---|
| `python3 -m unittest discover -s tests_direct -p 'test_*.py'` | 0 | **300 tests OK** (was 253) |
| `export_direct.py` | 0 | 2,652 lines, `d14bf39b450aaa5f…` |
| `verify_direct.py --stage all --timeout 20` | 0 | **PASS**, 0 failing, 142/142 programs, 277 cases |
| `compare_direct.py --repeats 3 --timeout 20` | 0 | 72 runs, **all seven gates PASS** |
| `benchmark_optimization.py --phase final --repeats 15 --seed 20260920` | 0 | 600 public + 1,500 corpus rows, 0 failures, **all mandatory gates PASS** |
| `check_optimization_evidence.py --root …_repair --baseline …/baseline` | 0 | **42 checks, 0 failing** |
| `reproduction/repair_probes.py` | 0 | control passes, all six mutations rejected, R1 and R2 probes closed |
| `attribution/measure_attribution.py` | 0 | measured attribution above |
| `git diff --check -- luminal-challenge` | 0 | clean |

Verification stages: schema 65, contract 31, constraints 43, construction 22,
optimizer 22, independence 13, export 33, benchmark 47, **evidence 24** — 300
direct tests — plus the unchanged public suite at exactly 11, the documented
CLI on all eight public programs, and 142 corpus programs in 142 isolated
processes covering 277 cases.

### Per-program median compile time, repaired round (milliseconds)

| Program | classical | frozen bootstrap | frozen full | candidate bootstrap | candidate full |
|---|---:|---:|---:|---:|---:|
| scalar_pipeline | 0.2925 | 0.6760 | 201.2618 | 0.5723 | 117.9643 |
| scalar_dual_chain | 0.1776 | 0.3887 | 217.0184 | 0.3468 | 140.5220 |
| vector_axpy | 0.1941 | 0.4992 | 229.5456 | 0.4360 | 137.2967 |
| vector_bitmix | 0.2360 | 0.6659 | 447.4836 | 0.5739 | 209.0565 |
| mixed_broadcast | 0.1535 | 0.3493 | 659.9554 | 0.3131 | 460.4353 |
| parallel_memory | 1.3935 | 0.9668 | 414.5972 | 0.8113 | 157.3567 |
| scalar_selects | 1.3763 | 0.7993 | 527.6080 | 0.7877 | 199.7500 |
| vector_reduction | 0.3932 | 0.9399 | 434.5972 | 0.7931 | 192.6444 |

No public program is slower on either direct path. The two anomalous classical
medians are noted in R4 correction 2.

### Correctness

Combined public score recomputed from the raw integers, identical for all four
direct arms: **2.008466202284657**, the accepted v3 value. Classical
1.9013791212645499 in every repetition. Every public program's cycles and
scratch are identical between the frozen and candidate arms, so **no
per-program `cycles × scratch` product moved at all**.

### Frozen evaluation corpus

100 programs, integrity re-verified on all 100 before use, 1,500 rows, 0
failures.

| Arm | Score geomean | Accepted improvements |
|---|---:|---:|
| classical | 2.370890 | — |
| bootstrap (frozen and candidate) | 2.362098 | 0 |
| full (frozen and candidate) | **2.376597** | **18** |

Frozen and candidate accept the same 18 improvements on the same six programs.
**Reported against interest:** one corpus program, `additional_351501`, is
slower on the bootstrap path with the candidate. It is retained and reported.
The v4 round also reported one slower program and the middle repair round
reported none, so this is run-to-run variation rather than a stable regression;
it is reported as observed in each run.

---

## Changed files

| File | SHA256 |
|---|---|
| `schema_index.py` | `f7bec20681cec044bc0c550b319dddee6acd325e2338a11810209c972e660820` |
| `direct_constraints.py` | `8743e82f75356de4be8b622a73c0f24e9c58536e2695184b87f5d3470299f376` |
| `verify_direct.py` | `fb435a9bcf55ab1f56fc4d1bd9fbf586898ac9b89ad0dc6f4a4ca6bf9f40c041` |
| `benchmark_optimization.py` | `da523e13fb7042c0e0ad6b6f520811f4d8362bf3a84259bdf388f58d63c9ea3a` |
| `check_optimization_evidence.py` | `07eed38720d0d4178b366673bdea4926cfc5c596f07c97caddcddc5c6c67bf4a` |
| `tests_direct/test_schema_index.py` | `9e36426b667fd9b5cd17c3dd9520aae1d77610e832b978100e72ba68c0089d7d` |
| `tests_direct/test_benchmark_harness.py` | `8296369967994a489aed5566667a13fbb630cc257d6b610d2e45be1b140d3f9c` |
| `tests_direct/test_evidence_checker.py` (new) | `5c53fa34883cf9a8b6262ebc9295e62d4784324c83359439d3d1c3fc53f2e64d` |
| export | `d14bf39b450aaa5fe73c41a3236980e219089e527ae43007781d78e0059a5864`, 2,652 lines |

`direct_optimizer.py` `a5f71a40…`, `direct_compiler.py` `523fccd1…`,
`direct_contract.py`, `export_direct.py` and `compare_direct.py` are unchanged
by this repair round.

`verify_direct.py` gained one additive stage for the evidence-checker
regressions and two entries in its source list, so the harness and the checker
are hashed as evidence. No existing stage's acceptance semantics changed.

The lead's uncommitted edits to `AGENTS.md`, `plan/OPTIMIZATION_PHASE_PLAN.md`
and `results/direct_index_v3_repair/REVIEW.md`, the review at
`results/direct_index_v4_optimization/REVIEW.md`, the whole `lead_review/`
directory, and the unrelated 0xPARC, `README.md` and `plans/` changes are
untouched and in no worker commit. My `STATUS.md` entry is appended in the
working tree and left uncommitted for the same ownership reason as last round.

---

## Unresolved risks and limitations

1. **Both targets remain missed**, and the full-direct figure fell from 1.9889x
   to 1.9536x because R1's repair restores clock reads the defective version
   skipped. Correctness bought that 1.8%.
2. **The lead's retained `probes.py` can no longer run to completion.** It sets
   `skip_extra_corpus=True` without the `--diagnostic` option that did not exist
   when it was written, so `phase_final` now refuses before measuring, returns
   exit 2 and writes no report — the correct new behaviour — and the script then
   fails trying to read a report that was rightly never written. `phase_final`
   reads the new option with `getattr` so an older caller does not crash on a
   missing attribute, but the probe's assumption that a phase always produces a
   report no longer holds. The equivalent updated probe is
   [`reproduction/repair_probes.py`](reproduction/repair_probes.py), which
   covers the lead's three probes and three more.
3. **The evidence tests substitute the verification summary.** They run inside a
   staged verification run, so the summary they would read is the one that run
   is still writing. They build a correct one from the live tree; its hashes are
   computed from the files on disk, so it cannot mask a real hash drift, but the
   lead should know the substitution exists.
4. **The checker now hashes itself and the harness.** Any edit to either after a
   measurement invalidates that measurement's provenance. This is intended, and
   it is why the final chain was rerun after the last source change; it also
   means the lead must not edit those files before rerunning.
5. **Row-level statistics are not recomputed when rows fail validation**, by
   design. A tree with invalid rows reports the row failure and an explicit
   refusal to derive statistics, not a second derived number.
6. `additional_351501` is slower on the bootstrap path in this run.
7. Single machine, ordinary load, eight public programs and 100 generated ones.
   The private grader is unavailable and nothing is inferred about it.
8. The evaluation corpus shares its generator with the acceptance corpus and is
   **not statistically independent** of it.

---

## Rerun instructions

```sh
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 \
  --output results/direct_index_v4_optimization_repair/lead_review/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/direct_index_v4_optimization_repair/lead_review/comparison
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase final \
  --baseline results/direct_index_v4_optimization/baseline --repeats 15 \
  --seed 20260920 --output results/direct_index_v4_optimization_repair/lead_review/final
python3 check_optimization_evidence.py \
  --root results/direct_index_v4_optimization_repair \
  --baseline results/direct_index_v4_optimization/baseline
PYTHONPATH=.reference:. python3 \
  results/direct_index_v4_optimization_repair/reproduction/repair_probes.py
git diff --check -- luminal-challenge
```

The frozen v4 baseline, its snapshot `c0574395d339dae3…` and its 100-program
evaluation corpus are reused unchanged and were not overwritten.

---

**READY_FOR_REVIEW.**

This states that the repair handoff is complete, not that the optimization
succeeded. Both engineering targets remain missed. Only the lead may record
`ACCEPTED`, `ACCEPTED WITH LIMITATIONS` or `CHANGES_REQUIRED`.
