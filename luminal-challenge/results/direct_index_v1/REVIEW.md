# Independent lead review — Luminal direct-index compiler

Date: 2026-09-19. **Verdict: CHANGES_REQUIRED.**

Reviewed implementation: commit `2ab4fa8`, canonical plan version 1.0, with the
version 1.1 comparator-order amendment recorded in `plan/STATUS.md`. This review
does not accept L07 or authorize submission. Production code and the worker's
original evidence were preserved. New evidence is under [lead_review](lead_review/).

The implementation is substantial: direct cube decisions construct schedules
and allocations, joint constraints embed feasibility and objective bounds, and
the public scores in the worker's records recompute correctly. No mathematical
counterexample was found in cube algebra or comparison-cover semantics. These
observations do not resolve the release-gate and independent-test defects below.

## Findings and required repairs

Priorities: P1 blocks trustworthy release decisions; P2 is a required correctness,
contract, or evidence repair; P3 is a reporting/robustness correction. All listed
repairs must be resolved before final sign-off; priorities set repair order.

### R1 — P1: candidate discrepancies do not reliably block release

Locations: [direct_optimizer.py](../../direct_optimizer.py#L226), especially the
measurement/rejection at line 244; [direct_compiler.py](../../direct_compiler.py#L438);
[verify_direct.py](../../verify_direct.py#L183);
[compare_direct.py](../../compare_direct.py#L73).

After decoding, validation checks machine legality but does not explicitly check
`actual_cycles <= target_cycles` and `actual_memory <= target_memory`. A legal
candidate missing the query target is silently rejected when its product does
not improve. The saved probe substitutes the valid incumbent for decoded SAT
witnesses: four SAT results, zero improvements, **zero validation errors**.
Every generated target requires strict product improvement, so this is a query
contract discrepancy, not an ordinary unsuccessful optimization.

Machine-invalid candidates are recorded in diagnostics, but the official
`compile_program` drops those diagnostics and the corpus/comparison runners use
that interface. Thus those runners can PASS after a query/validator discrepancy.
Keeping a valid incumbent after UNKNOWN is allowed; hiding a predicate defect
from the release decision is not.

**Repair/acceptance:** check both target bounds after independent validation;
record every disagreement. Make release verification and benchmarking consume
diagnostics from the same measured compilation and fail if discrepancies exist.
Test both machine-invalid and machine-valid-but-out-of-target witnesses; invoke
the actual release gate and require nonzero exit plus a retained failure record.
Do not modify the frozen validator or conflate UNKNOWN with a defect.

### R2 — P1: comparison success does not enforce the score gate

Locations: [compare_direct.py](../../compare_direct.py#L328), line 383.

The process exit code depends only on execution failures. The report states that
every repetition exceeded 1.0 unconditionally. Correct-but-serial-equivalent or
worse results can therefore produce a successful report. Current recorded scores
really do exceed 1.0; this finding concerns the executable acceptance gate.

**Repair/acceptance:** require all expected runs, valid positive metrics, and a
combined direct score strictly greater than 1.0 in every repetition. Generate
wording from evaluated gates. Synthetic complete results at 1.0 and below must
fail, as must a missing repetition; the actual passing results must pass.

### R3 — P2: the joint oracle test can pass without testing infeasibility

Locations: [tests_direct/test_constraints.py](../../tests_direct/test_constraints.py#L392),
lines 416–421 and 439–442.

The exhaustive test discards the query on `Infeasible` and then executes
`assertTrue(True)`. Replacing every `JointQuery.expression` with an unconditional
`Infeasible` leaves the test passing. Returned free-bit fillings are checked
against the implementation's expression, not independently against the machine.
The twelve advertised fixture/target combinations use three scalar programs;
joint vector-overlap and aliasing coverage is missing.

**Repair/acceptance:** derive bounded domains independently, including after
construction rejects a query; enumerate whether any oracle-valid assignment
exists. Compare predicate acceptance pointwise with independent machine/target
checks (existentially quantifying lanes). Independently decode and validate every
filling of small returned schemata. Include vector alignment/overlap and ordered
aliasing fixtures. The always-infeasible mutation must fail the repaired test.

The independent schema reviewer additionally checked nine small joint windows,
360 time/address assignments with existential lane enumeration, against the
frozen machine and targets without finding a mismatch. This limited corroboration
does not replace the missing durable tests.

### R4 — P2: resource limits are checked after expensive construction, or omitted

Locations: [direct_constraints.py](../../direct_constraints.py#L207), lines 215–226;
[schema_index.py](../../schema_index.py#L655), lines 671–677.

Comparison covers accumulate before `meter.cover` is called, after normalization.
The schema reviewer observed 5,115 visited partial cubes for a 10-bit comparison
with `max_cover=4`, and 255 accepted cubes constructed before a record-limit
failure with `max_records=1`. Incoming atomic leaf covers are not checked by
`solve`: the saved probe returns SAT for a 16-singleton leaf under `max_cover=1`.

**Repair/acceptance:** enforce the declared cover/record budgets while growing
structures, validate incoming leaves, and check deadlines during normalization
and expression traversal. Budget exhaustion must be UNKNOWN, never UNSAT.
Add deterministic small-cap tests demonstrating early stopping; do not replace
this with a larger cap or a wall-clock-only assertion.

### R5 — P2: corpus acceptance does not enforce a fresh 20-second process per input

Locations: [verify_direct.py](../../verify_direct.py#L180), lines 225–231;
[tests_direct/test_export.py](../../tests_direct/test_export.py#L219).

All 142 programs run in a single process with a 900-second timeout. Only the
eight public CLI inputs get individual external limits. A slow corpus input can
pass this gate, and per-input import/startup costs are not tested.

**Repair/acceptance:** use a fresh isolated process per corpus input with the
requested external timeout, validate every case, retain all failures and input
hashes, and account for startup/import/serialization. A forced timeout on one
input must fail overall without losing the other records. The lead's separate
isolated corpus audit supplies current-input evidence, but does not repair the
reusable runner.

### R6 — P2: actual cycle/memory tradeoff fixture is missing

Location: [tests_direct/test_optimizer.py](../../tests_direct/test_optimizer.py#L135).

Tests prove that target tuples and hypothetical score arithmetic permit a
tradeoff. They do not show the optimizer producing a valid compiled result
whose cycles or footprint worsens while their product improves. This omission
was candidly disclosed in STATUS; it is still an explicit T05 requirement.
The separate joint-necessity fixture is present and uses bounded independent
enumeration; it should be retained.

**Repair/acceptance:** freeze a small reproducible program/incumbent for which an
actual accepted joint witness worsens one measured metric and improves the
product. Check it with the frozen machine and every case, independently establish
the fixture's relevant alternatives, and recompute the official score from the
actual before/after integer metrics. A target-generation assertion is insufficient.

### R7 — P2: benchmark isolation, provenance gates, and query evidence are incomplete

Locations: [compare_direct.py](../../compare_direct.py#L49), lines 103–108,
127–133 and 363; [tests_direct/test_independence.py](../../tests_direct/test_independence.py#L151).

Benchmark workers retain the development directory and inherited environment in
their import paths. They record no query counters or validation discrepancies.
The runner checks reference contents against a mutable manifest but does not
enforce the plan's frozen manifest/classical/history hashes or classical integer
metrics. It only checks that an export exists, so a stale export can be measured
alongside hashes of newer source. Current hashes and historical metrics match;
this is a missing protection against future invalid comparisons.

The guarded successful optimization test exercises the development compiler,
not the standalone export.

**Repair/acceptance:** isolate the direct arm in a neutral process with only the
standard library, current export, and pinned machine available; assert the loaded
compiler path/hash. Rebuild or compare export contents with current assembly;
fail on frozen-control drift. Record query outcomes, budgets, discrepancies and
construction/optimization contributions from the same measured compilation.
Exercise a successful optimization through the export with forbidden calls and
imports blocked. Retain the unchanged classical arm as an independent control.

### R8 — P2: the final shorter source window is omitted

Location: [direct_optimizer.py](../../direct_optimizer.py#L101).

The loop breaks when a four-operation window reaches the end, before advancing
by two to retain the last nonempty shorter window required by section 5.4. For
six operations, source windows should include `(0,1,2,3)`, `(2,3,4,5)`, `(4,5)`
before deduplication with priority windows. The current loop omits `(4,5)`.

**Repair/acceptance:** generate starts `range(0, count, 2)`, truncate each at the
operation count, then perform the specified stable deduplication. Test exact
ordered windows for even and odd counts, including cases where priority windows
do not mask the missing tail. This affects search coverage, not output legality.

### R9 — P3: public-suite failure handling and submission wording need correction

Locations: [verify_direct.py](../../verify_direct.py#L279), line 297;
[SUBMISSION.md](../../SUBMISSION.md).

The public suite accepts any positive test count despite expecting eleven; its
timeout is not caught into a fresh failure summary. Require exactly eleven and
write a failed/in-progress result so an aborted rerun cannot leave a previous
PASS looking current.

Correct submission claims: optimizer UNKNOWN preserves an incumbent (so “a
query that cannot finish is a compilation failure” is overbroad); not all four
stress fixtures fill scratch exactly; source-order earliest scheduling and
minimum-address placement use familiar greedy policies implemented by schema
queries, so categorical “no list scheduler/no first-fit allocator” wording
overstates the distinction. Public score gains come entirely from construction.
Search budgets, window restrictions, target selection and representation costs
all constrain optimization; evidence does not establish that only budget limits
its reach. Passing historical metrics alone does not prove the whole harness
sound. Update the outstanding-review section to this verdict.

## Comparator split-order ruling

**Approved as plan version 1.1**, not as a waiver of other requirements.
The next coordinate is selected by descending bit significance within either
operand field; ties use descending absolute coordinate; the zero branch is
visited first. Each split still partitions the current cube into disjoint,
exhaustive children, and interval decisions use nonwrapping arithmetic. Thus
the change preserves denotation and exactness while changing cover size/cost.
No general compactness or complexity guarantee follows. Existing recorded
performance concerns this implemented order; claims about the unimplemented
absolute-coordinate order must be kept separate. Fix the stale function docstring.

## Commands, evidence, and observed results

All commands below run from `luminal-challenge`. The original worker artifacts
are preserved in `verification/` and `comparison/`; lead reruns have separate
paths. The lead preflight checked every pinned reference file and all four
protected SHA256 values in plan section 2 successfully. Review used two scoped,
read-only assistant audits of schema semantics and the harness; the lead inspected
integration and independently reran verification, comparison, and defect probes.

| Command | Exit | Observed result |
|---|---:|---|
| `PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v1/lead_review/verification` | 0 | 147 direct tests, 11 unchanged public tests, 142 programs/277 cases, 8 public CLI inputs PASS; subject to runner gaps R1–R9 |
| `python3 results/direct_index_v1/lead_review/audit.py probes` | 0 | Reproduced silent target discrepancy, vacuous infeasibility oracle, and oversized atomic cover accepted despite cap; exit 0 means probes ran, not release acceptance |
| `python3 results/direct_index_v1/lead_review/audit.py corpus` | 0 | 142 fresh isolated processes, 277 cases, zero failures, zero recorded discrepancies; maximum process time 1.231403 s |
| `PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v1/lead_review/comparison` | 0 | 72 measured runs, no failures, all three repetitions reproduce scores |
| `python3 results/direct_index_v1/lead_review/audit.py summary` | 0 | Protected hashes, reference contents, current production-source hashes, export hash and independently recomputed score gates PASS |
| `git diff --check -- luminal-challenge` (repository root) | 0 | Review document changes have no whitespace errors |

The staged verifier runs all seven direct test modules rather than a duplicate
second discovery run. It regenerated and tested the 2,104-line standalone export.
The isolated audit uses `python -I -S`, a temporary directory containing only the
export and frozen `machine.py`, the same `compile_with_report` implementation
wrapped by the official entry point, a blocked `serial_compile`, input immutability
checks, independent machine/case validation, and retained query diagnostics. It
accepted seven joint improvements across the corpus. Outcomes were SAT 7,
UNSAT 180, UNKNOWN_CONSTRUCTION 3, UNKNOWN_SEARCH 483, and INFEASIBLE 3,197.
Budget-dependent outcome counts differ from the worker's run; this is reported,
not treated as an infeasibility proof or deterministic performance result.

| Arm | Combined score, each repetition | Median compilation time |
|---|---:|---:|
| Frozen serial | 1.0000000000000000 | 0.080 ms |
| Frozen classical | 1.9013791212645499 | 0.286 ms |
| Direct index | 2.0084662022846573 | 433.925 ms |

The direct public score is about 5.63% higher than classical in this comparison,
while compilation is about 1,516 times slower by the medians. The largest measured
public direct process took 0.702 s. Scores measure generated-program cycles and
scratch, not compiler execution speed. These public score gains are attributable
to construction; they do not establish a public benefit from joint optimization.
Neither the private grader nor a general compactness ratio was evaluated.

Evidence:

- [Verifier logs and source/test hashes](lead_review/verification/summary.json).
- [Reproducible defect probes](lead_review/audit.py) and [observed probe results](lead_review/probes.json).
- [Every isolated input, hash, timing and diagnostics](lead_review/isolated_corpus.json).
- [All 72 comparison runs](lead_review/comparison/runs.json).
- [Independent score recomputation and protected hashes](lead_review/audit_summary.json).

Reviewed export SHA256:
`f31ac937e4d1735092ffbab93482a438b9187546dbbcde824b9f8752b7bb46c5`.
The source/test hash manifest identifies the exact tested implementation.
Pre-existing whitespace in the unrelated 0xPARC paper was left unchanged; the
Luminal-scoped diff check passes. No solver, compiler, reference, or baseline
source was changed by this review.

## Repair handoff and repeat-review contract

Read this report, `plan/INDEX_ONLY_PLAN.md` version 1.1, and `plan/STATUS.md`.
Preserve reference/classical/historical files and unrelated repository edits.
Do not change method boundaries, score thresholds or timeout requirements.

Suggested exclusive ownership, if workers are delegated:

| Work | Owned files | Findings |
|---|---|---|
| Schema/constraints | `schema_index.py`, `direct_constraints.py`, their tests | R3, R4; comparator docstring |
| Optimizer/integration | `direct_optimizer.py`, `direct_compiler.py`, optimizer tests | R1 target checks, R6, R8 |
| Release tooling | `verify_direct.py`, `compare_direct.py`, export/independence tests, `SUBMISSION.md` | R1 diagnostics gate, R2, R5, R7, R9 |

Workers are not alone in the repository: do not revert each other's work.
Coordinate diagnostics interfaces before parallel edits. Each finding needs a
regression that fails on the reviewed implementation and passes after repair;
exceptions are documentation-only corrections. Record exact commands, exit codes,
source hashes and evidence paths; report READY_FOR_REVIEW, never self-accept.

After targeted regressions pass, rebuild the export and rerun all direct tests,
the full 142-program isolated acceptance, unchanged eleven public tests, and the
three-repetition comparison. A schema or window-policy change invalidates prior
performance evidence: regenerate it and recompute scores. Preserve the present
review and worker evidence, using a new output directory for repair runs.
The lead must inspect the tests themselves, confirm injected defects now fail
the release gate, recheck protected hashes and export freshness, and issue a new
versioned review. No global-optimality, private-grader, compactness-ratio or
complexity-theory claim is established by these experiments.
