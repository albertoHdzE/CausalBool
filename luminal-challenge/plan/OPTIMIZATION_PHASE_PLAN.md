# Luminal direct-index optimization phase

Version: **1.1**. Date: **2026-09-20**. Owner: lead review; implementation may
be delegated to Claude Code. This document is self-contained and supplements
`INDEX_ONLY_PLAN.md` v1.1. It does not replace the correctness contract or the
accepted v3 implementation.

## 1. Objective

Reduce direct-index compilation time while preserving the exact direct-schema
method, all existing correctness guarantees, and the measured public score.
The first question is whether the current runtime penalty is caused by the
bootstrap compiler, by the optional optimizer, or by both. The current evidence
shows the following baseline on the eight public programs:

| Mode | Median compile time | Combined score |
|---|---:|---:|
| Frozen classical compiler | 0.2726 ms | 1.9013791213 |
| Direct bootstrap (`optimise=False`), preliminary diagnostic | ~0.638 ms | 2.0084662023 |
| Direct compiler with current optimizer | 424.270 ms | 2.0084662023 |

The classical and full-direct timings come from the accepted v3 fresh-process
comparison. The bootstrap number came from an exploratory in-process run with
external validation inside its timer and a median of per-program medians. It is
**not an equivalent benchmark**. The previously stated ~2.3x ratio is provisional
and must not be used as a final result or acceptance threshold. Baseline artifacts:
`results/direct_index_v3_repair/lead_review/comparison/runs.json` and
`results/direct_index_v3_repair/lead_review/verification_final/summary.json`.
The optimizer produced no accepted
public-program improvement in the accepted v3 run. The optimization phase must
therefore first establish whether the optimizer should remain in the official
path, then improve the expensive operations if it is retained.

Success means one of the following, reported honestly:

1. **Preferred:** both genuine optimizer and bootstrap improvements are measured
   independently. Target full-direct geometric-mean compile speedup >=2.0x versus
   freshly measured v3, with a paired 95% confidence interval lower bound >1.0.
   Target bootstrap speedup >=1.20x by the same criterion. Targets are engineering
   objectives, not permission to weaken semantics or manufacture a successful run.
2. **Honest fallback:** retain the best correct candidate and report targets not
   reached. Recommend, but do not implement, an official-mode change if justified.
   Disabling optimization is an ablation, not an algorithmic speedup. Runtime
   parity with classical is a stretch objective, not a required outcome.
3. **Failure:** any correctness, independence, score, or evidence gate regresses.
   Revert the offending change and report the cause.

No result in this phase may claim that direct-index compilation is faster than
classical compilation unless the fresh acceptance comparison demonstrates it.

## 2. Non-negotiable constraints

- Preserve the direct-index architecture. No BDD backend, SAT/SMT solver,
  exhaustive candidate enumeration, or classical fallback may enter the
  production direct path.
- Preserve the pinned reference, `common.py`, `results/comparison.json`, the
  accepted v3 evidence, and unrelated 0xPARC and README work.
- Preserve the public API and standalone export contract:
  `compiler.compile_program(program)` returns only the compilation object.
- Preserve exact semantics: a query that actually exhausts its budget must return
  UNKNOWN, never a fabricated SAT or UNSAT. Faster code may legitimately finish
  a formerly UNKNOWN query within the same limits and return proven SAT/UNSAT.
  Record those changes; equal wall-clock limits do not imply identical statuses.
- Do not weaken tests, enlarge timeouts, remove isolation checks, alter score
  formulas, or change the public corpus to obtain a better timing.
- Any optimization must be semantics-preserving and independently tested.
- Do not modify historical reports. Write new measurements under a new result
  directory such as `results/direct_index_v4_optimization/`.
- Preserve production `compile_program` with optimization enabled throughout
  this phase. Diagnostic bootstrap remains available via `optimise=False`.
  Default-mode changes require the final lead decision, not an intermediate stop.
- No submission, push, publication, or paper claim is authorized by this plan.

## 3. Required reading and baseline freeze

Before editing, read completely:

1. `AGENTS.md` and this file.
2. `plan/INDEX_ONLY_PLAN.md` and `plan/STATUS.md`.
3. `results/direct_index_v3_repair/REVIEW.md` and its `lead_review/` evidence.
4. `schema_index.py`, `direct_constraints.py`, `direct_compiler.py`,
   `direct_optimizer.py`, `compare_direct.py`, and `verify_direct.py`.

Record before changes:

- git commit and working-tree status;
- SHA256 hashes of all production and test files that will be compared;
- export hash and line count;
- Python version, platform, and pinned reference commit;
- the exact v3 comparison summary and raw-run path.

Use commit `35d2608d0d2ed4fde47916b7df79c138b007908d` as the immutable v3 source
snapshot; check its production/test hashes against the accepted evidence. HEAD
may contain later notebook or documentation work. Snapshot the relevant baseline
sources and assembled export into the new results directory before editing; do
not switch or reset the user's checkout. Save full SHA256 values, not prefixes.
All four protected hashes in `INDEX_ONLY_PLAN.md` section 2 must match.
If correctness, source hashes, or frozen integer controls fail, report the exact
discrepancy before dependent work. Timing need not reproduce historical values;
record hardware/load differences. Do not require identical time-bounded search
status counts or accepted-improvement counts.

## 4. Measurement protocol

Create a new results directory and never overwrite v3 artifacts. Every timing
experiment must record:

- command, commit, source hashes, export hash, interpreter and platform;
- per-program compile time for all eight public programs;
- process time separately from compile time;
- cycles, scratch, combined score, correctness, and failure reason;
- whether optimization was enabled and its limits;
- median and arithmetic/geometric aggregates exactly as the existing comparator
  defines them.

Use three repetitions for the unchanged official comparison, plus the controlled
performance experiment below. Use the same subprocess and
isolation protocol as `compare_direct.py`; do not compare an in-process direct
measurement with a subprocess classical measurement. Warm-up measurements must
be documented and excluded or included consistently for every arm.

Required baseline modes:

- serial;
- frozen classical;
- direct bootstrap with `optimise=False`;
- current direct path with `optimise=True`.

The first experiment must not change production code. Build a **retained** harness
at `benchmark_optimization.py` and test the hypothesis that bootstrap cycles and
scratch equal full-direct measurements, per program. Report discrepancies, not
only aggregate equality. Byte-identical schedules are not required. Measure the
optimizer's contribution rather than assuming the hypothesis must be true.

### Controlled performance experiment

- Benchmark five arms: frozen classical, frozen v3 bootstrap, frozen v3 full,
  candidate bootstrap, candidate full. The official comparator separately retains
  serial and its three unchanged arms. Direct arms load their standalone export;
  source-module timings are diagnostic only.
- Each `(arm, program, repetition)` executes in a fresh isolated process. Use
  `compile_with_report(program, optimise=...)` for all four direct arms, and
  `classical_compile` for classical. Time only the call, including any validation
  internally performed by it. External reference validation and all case checks
  occur after the timer for every arm. Time imports/process startup separately.
  Do not disable internal safety checks to equalize the implementations.
- Run 15 repetitions per program and arm, serially without competing benchmarks;
  randomize the arm order within each program/repetition using seed 20260920 and
  retain the order. No discarded warmups, outlier removal, or silent retries.
  Failed rows remain in the dataset and invalidate a success claim.
- Public-program membership comes from the existing comparator's pinned set, not
  a glob truncated to eight. Store the expected full key set and reject missing,
  duplicated, foreign, mislabeled or failed records. Validate response identity.
- Report all per-program medians and raw times. Define speedup as baseline time
  divided by candidate time. Primary aggregate is the equal-program geometric
  mean of per-program median ratios; also report the existing pooled-median
  statistic explicitly. Do not mix these quantities.
- Compute a paired bootstrap 95% percentile interval with 10,000 resamples, seed
  20260920: resample repetition IDs within each program, jointly for all arms,
  recompute medians and the aggregate. This interval measures timing uncertainty
  on this fixed program suite; it does not establish generalization to programs.
- A faster-than-classical claim requires the lower interval bound >1.0 for the
  candidate-vs-classical ratio, retained correctness and score, and disclosure of
  each losing program. A single pooled median is insufficient.
- Keep profiling runs separate. Profiling changes wall-clock search behavior;
  profiler times are not performance results. Report cold-cache behavior in the
  fresh-process runs; any warm-cache experiment is separately labeled.
- Before tuning, freeze a separate deterministic evaluation corpus (seed 20260921,
  >=20 programs from each of the five existing generator families). Store program
  JSON and hashes. Use existing public/regression programs for tuning; run the
  extra corpus only for final evaluation, 3 repetitions per arm, with reference
  validation of every case. Do not call it statistically independent of the
  generator. Keep and report regressions, without discarding hard inputs or tuning
  to the extra corpus after inspecting results.

## 5. Profiling requirements

Profile representative small, medium, and largest public programs. Use a
deterministic profiler or equivalent instrumentation and retain reports. At
minimum report cumulative time and call counts for:

- `direct_optimizer.optimise`;
- `JointQuery.expression`;
- `relation_cover`;
- `_scratch_safety`;
- `_engine_capacity`;
- `schema_index.restrict`, `Cube` construction, and budget accounting;
- solver traversal and cover intersection.

Do not optimize from intuition alone. Each proposed change must identify the
profiled hotspot, its semantic invariant, and the test that detects a wrong
answer.

## 6. Ordered implementation stages

### Stage A — isolate the official path decision

Add no production behavior yet. Build a benchmark/report that invokes the
existing compiler with optimization enabled and disabled on the same inputs.
Test whether disabled optimization produces the same public metrics and valid
compilations. If true, document bootstrap as a possible mode for lead review.

Continue through B–D without waiting for an intermediate review. The official
entry point remains optimization-enabled for this phase.

### Stage B — low-risk representation and reuse improvements

Only after Stage A, implement narrowly scoped optimizations supported by the
profile, for example:

- memoize immutable relation covers keyed by predicate, field layout, width,
  offsets, and operand terms;
- reuse expression subtrees whose semantics and budget accounting are identical;
- avoid reconstructing identical `Term`, `Field`, and constant objects where this
  is proven safe;
- reduce repeated validation and allocation while retaining public validation;
- short-circuit constant, identical-field, and disjoint-range predicates before
  cover construction;
- preserve deterministic cube ordering and exact duplicate elimination.

Every cache must include all semantic inputs in its key. A cache hit must not
bypass time or record budgets. Cached mutable state is forbidden unless it is
isolated per query and tested for cross-query contamination.

Record cache lifetime, entry/record cap, eviction, hit/miss counts and retained
memory. Prefer compilation-local caches; never use an unbounded process-global
cache. Never cache a partial cover after exhaustion. Charge each query for its
reachable expression records under the existing accounting contract even on
cache hits. Check the clock before reuse. Tests must cover different widths,
fields, offsets, relation operators, program instances and (when relevant)
incumbents, domains, windows and target bounds. Retain both v3 cache-retry tests.

Also profile and improve bootstrap scheduling/allocation cube operations;
optimizer-only work does not address runtime parity for the faster mode. Preserve
minimum-witness semantics and existing operation/value ordering. Keep a result
for each independent change before combining changes, so ablations identify
where speedup came from. Do not remove validation or budget checks as a shortcut.

### Stage C — optimizer algorithm improvements

Only profile-backed changes are allowed. Preserve target/window enumeration,
ordering, domains and all `Limits` defaults. Candidate areas include reusing
structural subexpressions across nearby queries, proving a query infeasible
before expensive expression creation,
and avoiding scratch predicates that are provably irrelevant to a fixed query.

For every reduction, give an equivalence argument and exhaustively compare the
acceptance set on small bounded domains with the frozen v3 implementation and
the independent machine oracle. Use generous deterministic budgets for these
semantic tests. Separately force clock/record/cover/visit exhaustion and require
UNKNOWN with no witness. An optimization that completes within budget can resolve
a previously UNKNOWN query. Report that as additional completed work, not drift.
A pruned query needs a sound infeasibility certificate or recorded reason; skipping
a promising window or lowering a budget is a search-policy change and outside
this phase. State equivalence relative to the declared domains if simplifying
against them. Never reuse a target-specific expression for a different target.

### Stage D — recommend the mode and hand off

Deliver the corrected and optimized full path, the separate bootstrap results,
and a recommendation. Evaluate benefit on the generated corpus as well as public
programs: the accepted optimizer improved some generated programs. No public
gain does not imply no usefulness. Report score/cost tradeoffs, query completion
rates and accepted improvements on both suites. Leave official mode selection
to final lead review; do not stall implementation for that decision.

## 7. Acceptance gates

All gates below are required for a candidate to be offered for lead review:

1. Existing direct tests pass, plus any new optimization tests.
2. `verify_direct.py --stage all --timeout 20` passes with the unchanged public
   suite, all 142 corpus programs, all 277 cases, and the independence checks.
3. Export is fresh, standalone, standard-library compatible, and its hash is
   recorded.
4. All direct outputs pass the pinned machine validator.
5. The exact seven comparison gates pass over three repetitions:
   membership, frozen integer metrics, metric validity, direct-vs-serial score,
   frozen classical control, no candidate discrepancies, and direct isolation.
6. For every public program, each candidate result's cycle-times-scratch product
   must not exceed frozen v3's per-program product, and the combined score must
   be >=2.0084662022846573 within 1e-12. Bootstrap metrics must remain identical
   to the freshly verified v3 bootstrap. Full-mode improvements are allowed if
   independently validated and explained. Report corpus score distributions and
   every per-program regression; bounded-search variation is not automatically
   a defect but may prevent accepting the candidate's performance claim.
7. No optimization mislabels an exhausted query or bypasses a budget. Add
   explicit regression tests for every cache and pruning change.
8. Timing is reported for bootstrap and full-direct separately using section 4,
   with optimizer stage times and status counts as diagnostics. A faster number
   without equal correctness evidence is
   not an accepted result.
9. Scoped `git diff --check -- luminal-challenge` passes and unrelated files are
   untouched. Record existing unrelated whitespace failures without fixing them.
10. Harness regressions reject injected identity swaps, missing/duplicate rows,
    invalid output, stale export, protected-hash drift, and product-preserving
    classical integer drift. A failed subprocess must make the runner exit nonzero.
11. Report whether each numerical engineering target in section 1 was met.
    Correctness passing does not certify a speedup. Failure to reach parity is a
    valid research outcome, not permission to change targets after measurements.

## 7a. Commands and bounded execution

Run from `luminal-challenge` with the same recorded Python interpreter. Capture
stdout, stderr, actual argv, exit code and elapsed time for every command in
separate files using the experiment runner. Implement the new runner interfaces
below as part of this assignment; they do not exist merely because listed here.
Each output subdirectory must be new; on rerun use a new numbered round and
retain the failed attempt. `baseline/` must run before production edits.

```sh
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase baseline --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization/baseline
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase profile --baseline results/direct_index_v4_optimization/baseline --output results/direct_index_v4_optimization/profile
# Implement and validate B/C, then run:
PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v4_optimization/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v4_optimization/comparison
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization/final
python3 check_optimization_evidence.py --root results/direct_index_v4_optimization
git diff --check -- luminal-challenge
```

The final runner must remeasure frozen baseline and candidate together; do not
divide a current candidate time by a historical timing. Use a 20-second external
timeout for every worker in every arm. The evidence checker must independently
verify reference/protected/source/test/export hashes, exact membership, reference
validation outcomes, frozen baseline integers and all aggregates from raw rows.
It must recompute final export assembly freshness and link every result to the
source snapshot it actually ran; a report's PASS text is not sufficient.

Complete baseline and profiles, then at most three profile-supported optimization
experiments (individual change sets with before/after evidence). Retain correct
improvements; reject unsafe or slower changes with evidence. Finish with the full
matrix and handoff even if targets are unmet. Do not iterate indefinitely seeking
classical parity. Any source/test change after final hashes requires the relevant
rerun matrix in `INDEX_ONLY_PLAN.md` section 9. Record duration and limitations.

## 7b. Ownership and authority

Claude owns scoped edits to `schema_index.py`, `direct_constraints.py`,
`direct_compiler.py`, `direct_optimizer.py`, related tests in `tests_direct/`,
the two new benchmark/evidence scripts, and v4 result artifacts. Changes to
`direct_contract.py` or `export_direct.py` are allowed only if needed by a
profiled optimization, with equivalence tests and explicit rationale. Keep
`compare_direct.py` and `verify_direct.py` acceptance semantics intact; necessary
compatibility edits must be additive, tested and explained. The existing public
test suite, corpus generator, inputs and historical results are protected.

Append an optimization task record to `STATUS.md`; never mark your own work
ACCEPTED or alter historical verdicts. Add tests without deleting assertions or
changing expected results merely to fit a candidate. Commit only explicitly
owned files, never `git add .`; leave pre-existing lead documentation edits and
unrelated changes out of worker commits. You are not alone in this repository:
preserve others' work and do not reset or revert it. A targeted reversal of your
own failed experiment is allowed. No agent delegation is required.

This v1.1 document resolves its predecessor's contradictory UNKNOWN and mode
instructions. Original direct-schema semantics, solver ordering, machine facts,
query-policy and budget contracts remain authoritative. Record out-of-scope
ideas in the handoff and continue authorized work; do not silently implement
them or pause for ordinary implementation choices.

## 8. Required deliverables

The implementing agent must produce:

- source and test changes with atomic commits;
- `results/direct_index_v4_optimization/BASELINE.md`;
- `PROFILE.md` with representative profiles and interpretation;
- `BENCHMARK.md` with commands, raw paths, tables, and limitations;
- `REVIEW_HANDOFF.md` listing changed files, invariants, tests, hashes, and
  unresolved risks;
- raw comparison, verifier, and evidence-check outputs in the same result tree;
- a concise recommendation: official bootstrap, improved optimizer, or changes
  required.

The handoff must say **READY_FOR_REVIEW**, never ACCEPTED. Only the lead may set
the final verdict after independently checking the source, rerunning the gates,
and reviewing whether the timing comparison is fair.

`READY_FOR_REVIEW` describes handoff completeness, not gate success. Include a
separate machine-readable gate table with PASS/FAIL/NOT_RUN, reasons and evidence
paths, plus `performance_targets_met` for each target. If baseline provenance is
blocked, use `BLOCKED_BASELINE` and report what prevents safe dependent work.
If all experiments fail, retain the original correct implementation and hand off
the negative results; do not label the optimization itself successful.

## 9. Lead review procedure after delegation

The lead will:

1. inspect the diff and changed-file ownership;
2. verify the baseline and source/export provenance;
3. inspect profiles for measurement errors and benchmark asymmetry;
4. rerun focused semantic, budget, cache, and optimizer tests;
5. rerun the complete verification and three-repetition comparison;
6. independently recompute scores and compare bootstrap versus optimized output;
7. reject any claim that exceeds the evidence or any optimization that weakens
   the direct-schema contract;
8. record `ACCEPTED`, `ACCEPTED WITH LIMITATIONS`, or `CHANGES_REQUIRED` in a
   new lead review and update `STATUS.md`.

Only after that review should the paper use the new performance measurements.

## 10. Delegation prompt

Copy the following prompt to Claude Code exactly:

> Implement the optimization phase in
> `luminal-challenge/plan/OPTIMIZATION_PHASE_PLAN.md`.
>
> You are the implementing worker, not the lead reviewer. Read `AGENTS.md`,
> `INDEX_ONLY_PLAN.md`, `STATUS.md`, the accepted v3 review, and this complete
> optimization plan before editing. Work in the shared repository and preserve
> all unrelated user changes. Do not modify pinned reference files, classical
> source, historical v1/v2/v3 evidence, or the 0xPARC manuscript.
>
> Follow version 1.1 of this plan, including sections 7a/7b. First snapshot the
> accepted v3 source and reproduce its integer metrics. Test, without assuming,
> whether bootstrap (`optimise=False`) matches full-direct public metrics. Treat
> the historical ~2.3x bootstrap/classical timing ratio as provisional. Build the
> retained harness, profile, then perform at most three measured optimization
> experiments covering both bootstrap and optimizer costs. Preserve the official
> optimization-enabled entry point; report bootstrap as a separate ablation.
> Continue all stages without an intermediate approval pause. Do not weaken
> budgets, timeout rules,
> exact SAT/UNSAT/UNKNOWN semantics, isolation checks, or comparison gates.
> Faster completion may legitimately resolve a previously UNKNOWN query; actual
> exhaustion must still return UNKNOWN. Do not shorten search to claim speedup.
>
> Every cache key must include all semantic inputs; no cache hit may bypass time
> or record-budget checks. Every pruning or expression-reuse change must have a
> regression test proving equivalent acceptance behavior and correct UNKNOWN
> behavior under exhaustion. Do not use a BDD, SAT/SMT solver, exhaustive
> production enumeration, or classical fallback.
>
> Use a new results directory `results/direct_index_v4_optimization/`. Preserve
> raw profiles, commands, source hashes, export hashes, per-program timings,
> cycles, scratch, scores, and failures. Run the complete existing test suite,
> `verify_direct.py --stage all --timeout 20`, and the exact three-repetition
> comparison with all seven gates. Also run the randomized 15-repetition paired
> baseline/candidate performance experiment and frozen extra evaluation corpus.
> Independently verify export freshness, protected hashes, exact measurement
> membership and aggregates. Run `git diff --check -- luminal-challenge`.
>
> Commit implementation changes atomically. Write `BASELINE.md`, `PROFILE.md`,
> `BENCHMARK.md`, and `REVIEW_HANDOFF.md`. The handoff must be factual, list all
> changed files, actual commands/exit codes, rerun instructions, measured target
> outcomes and limitations, and end with `READY_FOR_REVIEW`. Commit only your
> owned files; preserve pre-existing lead documentation edits. Do not declare
> acceptance, do not write the paper, do not push or submit anything, and do not
> claim that direct compilation is faster than classical unless section 4's
> paired performance criterion is met. Unmet speed targets are valid outcomes.
> Stop after producing the handoff so the lead can inspect
> and rerun everything independently.
