# Third improvement round: shared propagation state, then paper readiness

Version 1.0 · 2026-09-25 · Lead: Codex · Implementer: Claude Code.
**READY_FOR_EXECUTION — NOT DISPATCHED.**

## 1. Decision and purpose

The user requests another planned improvement round before moving to the paper.
Authorize ONE bounded attempt at a shared propagation-state mechanism on the
accepted research baseline R0. This is a new engineering hypothesis. The earlier
worklist and isolated rule-2 filter do not justify another sweep, and their
negative outcomes remain unchanged.

The question is: **Can a query-local representation of changing domains reuse
derived information across multiple propagation operations, reducing the cost
of the same search by at least 20%, while maintaining solution quality at the
same wall allowance?** Establish the mechanism with measurements before building
the full candidate. A justified rejection is a completed scientific outcome.

This is the final improvement decision in this assignment before a paper
readiness handoff. Success, a justified stop, or a failed practical target all
lead to that handoff and independent lead review. Do not automatically start a
fourth round, reopen learning, revise the paper, or promote a compiler.

Authority: AGENTS.md, INDEX_ONLY_PLAN.md v1.1, pinned machine semantics, glossary,
this plan, and `phase2_third_round/PROTOCOL.json`. The new plan supersedes only
the unexecuted engineering/confirmation stages of the efficiency assignment;
all historical requirements, measurements and dispositions retain their meaning.

## 2. Accepted starting point and ownership

Read the current STATUS, the efficiency handoff, and
`results/phase2_structural_encoding/lead_efficiency_review_20260925/REVIEW.md`.
Start by running:

    ../venv/bin/python plan/phase2_third_round/verify_package.py

Baseline **R0** is the unmodified `research/efficiency_search.py`, A4 catalog,
DFS, hash `d0fcd441886cc5c3d34a6e1df7b2828ea219b6575ffd2049913b4d4901b92fbf`.
Its standalone export hash is
`74c87b69e63063595d3283bb66986162297519bb1a8a2a87f2853fd7134d9ea9`.
The lead accepted the assurance repairs, reran 93 tests and standalone acceptance
on 142 programs / 277 cases, and resolved the snapshot path failure. Do not redo
the 420-ranker replay or historical learning campaign. The old checker FAIL has
exactly scoped dispositions; it must not become a blanket source-drift waiver.

Own only new `research/third_round_*.py`,
`research_tests/test_third_round_*.py`, and a fresh
`results/phase2_structural_encoding/third_round_20260925[_N]/` directory.
Never overwrite an occupied result directory. Shared workspace: preserve others'
edits. No subagents, commits, pushes, process termination, production integration,
manuscript edits or external submission/publication under this assignment.

Retain starting environment, status and source/result hashes. Reuse existing
codec, schema primitives, generator, machine and export owners. Import R0 directly
for the control. A versioned candidate may copy its source, with exact parent
bytes/hash and a minimal diff. Adapters may bind new representation/helpers;
never monkeypatch baseline behavior during a measured control compilation.

All decisions remain direct-index-derived. No classical/serial seed, BDD, SAT/CP
backend, case-dependent dispatch, learned pruning, enlarged neighborhoods,
weakened validation or larger search budgets. Serial compilation is confined to
the isolated public comparator. UNKNOWN is never UNSAT.

## 3. Stage M: one mechanism with a measured case

### M0. Identify what is actually shared

Use existing development programs only: seeds 800000–800099. Diagnostic programs
are 800000–800029: six per generator family, including the earlier ten. They are
development evidence, not a fresh inferential cohort. The earlier profile has
90 retained rows, not 80; its component ratios are diagnostics, not impossibility
bounds for other representations or populations.

Inspect these R0 operations and their callers:

- `Propagation.times_fixpoint`: repeated precedence sweeps and reconstruction
  of selected singleton engine occupancy plus cycle-support scans.
- `Propagation.compulsory_peak`, `product_bound`, `prune`: repeated affected-value
  lifetime summaries, event construction and lower-bound witnesses.
- `Propagation.addresses_fixpoint`: repeated support tests as address domains
  shrink; its existing min/max support identity is already exact and cheap.
- `Expander.children`: parent-to-child changes, state/domain copying, canonical
  options and time-to-address transitions.

Measure changes and reused subcomputations, not just identical whole-call inputs.
Record which facts depend on which domain entries; distinguish unchanged facts
from recomputed equal results. Measure construction, conversion, invalidation,
copy/restore, disposal, certificate emission and cache lookup costs. Keep a cost
ownership map so nested/shared work is charged once. Explain whether each family
has an opportunity; never select programs by observed speedup.

On all 30 diagnostic programs collect three unprofiled fixed-work compile calls
and one each of exclusive timers, workload/counter trace, peak-memory probe and
instrumentation-parity probe: **210 rows**. Each is a fresh isolated process.
Instrumentation must preserve the decisions/status/work/certificate fingerprints
of the uninstrumented call. Reconcile exclusive time to total and report overhead.
Keep zero-call components as zero when comparing the complete 30-program sample.
Never infer a total saving by adding overlapping component shares.

### M1. Nominate a shared-state design before timing it

Write `MECHANISM_SPEC.json` before any candidate microkernel or integration.
The permitted mechanism is ONE query-local domain-state representation with
reusable derived facts, consumed by at least two of the above propagation
operations. Possible implementation choices include immutable branch summaries,
copy-on-write summaries, or bounded revision-keyed support information. Choose
one design, including its consumers, before implementation; do not benchmark a
menu of designs or combine unrelated optimizations until a threshold passes.
Count distinct cost components: precedence, issue capacity, live/product bounds,
or address support. `prune` calling `product_bound` is one component, not two.

The representation must describe actual finite domains exactly. If local integer
bitmaps are used, distinguish value-set membership from the codec's free-coordinate
mask; bound complements and integer widths. A bitmap over one finite domain is
not permission to enumerate full-program assignments or replace the schema codec.

Specify every dependency and invalidation condition: program, query, epoch,
incumbent-sensitive data, fixed context, affected domains, branch/sibling/resume,
and the transition from partial times to fixed lifetimes and address search.
Do not retain mutable summaries across siblings without verified restoration.
No reuse across compilations. Keys must include every semantic input; a digest
alone is not a collision-free equality test. Bound storage/eviction and include
their costs. Preserve rule order, canonical ranks, tie-breaking and witness
selection; skipping work requires proof that its result and emitted events match.

Explicitly distinguish the design from the previous worklist implementation and
the rejected rule-2-only filter. Merely wrapping either in a cache is insufficient.
If no shared mechanism can be specified, stop `NO_JUSTIFIED_MECHANISM` at M0.

### M2. Validate a small kernel and predict total savings

One isolated kernel prototype for the nominated design is allowed. Replay the
captured baseline workload, including updates/restores, using baseline and kernel
implementations: 30 programs × three repetitions × two versions = **180 rows**.
The kernel must have identical observable outputs and required certificates.
Programs with no applicable calls remain in the denominator with zero predicted
saving. Fix the workload and its hashes before observing kernel timings.

Retain all outputs, commands, timings and the prediction calculation. Include
initialization, cold state, invalidations, memory/eviction, conversion at remaining
tuple interfaces and disposal. No assumed nanosecond constants or unrecorded
`timeit` figures. Explain any costs that the kernel cannot measure; use an explicit
upper estimate, not zero. A kernel speedup is not a compiler speedup.

For each program derive a predicted complete compile cost from its unprofiled
R0 median, exclusively owned replaced work and measured replacement overhead.
Use `T0 - O + N` and the conservative `T0 - O + 1.5*N`, where `O` is calibrated
exclusive old work and `N` includes all replacement/extra costs and upper estimates
for integration costs. Require `0 <= O <= T0` and positive predicted costs; an
unreconciled instrumented `O` is not a valid model. Retain the derivation of both
`O` and `N`, including measured call counts, rather than only final ratios.
Aggregate log cost ratios with equal family weights. Also recompute the prediction
with replacement/extra overhead multiplied by **1.5**. Integration is eligible
only when the conservative predicted ratio is **<=0.80**, all kernel parity
checks pass and the prediction is not based on profiler distortion. This is a
development model, not a confidence bound or a promised 20% improvement.

If the evidence cannot justify that gate, stop `NO_JUSTIFIED_MECHANISM`. Do not
integrate a second design, change consumers to chase timings, or lower the target.
Correctness fixes within the nominated design are allowed before the development
freeze; retain attempts. Its final consumer scope must match the mechanism spec.

## 4. Stage D: one compiler candidate, exact decisions

Only after M passes, implement **C1** using that shared mechanism. R0 remains
unchanged. Do not alter product caps, catalog, traversal, pruning mathematics,
acceptor, query budgets or deadline accounting. Preserve the accepted construction
and search/model validation accounting. No fresh learner is part of C1.

Run exhaustive small-domain parity against R0 and the independent oracle where
applicable: all feasible/improving objects, minima, domains after propagation,
canonical codes/ranks, node/candidate/incumbent order, bound witnesses, deletions,
certificate sequence, validation counts, frontier peaks and status/limit sequence.
Check siblings, epoch changes, resume, empty/singleton domains, exact deadlines,
late terminal proofs, validation discrepancies, vector alignment, inclusive
lifetimes and cold/repeated independent compilations. Include mutations that fail
for a stale domain summary, stale incumbent-sensitive value, sibling contamination
and omitted consumer dependency. Test invalidation, not just final minima.

Use the inherited applicable semantic tests bound explicitly to C1. Do not edit
those tests. Preserve original source views for frozen evidence-checker tests;
temporary test results must use real directories, avoiding the resolved/symlink
run-path mismatch diagnosed by the lead. Record selected/excluded tests and why;
no broad skip because a test fails.

Fixed-work mode for both versions uses a constant logical clock for global/query/
slice expiry, aggregate 10,000 nodes, 100,000 validations, 2,048-node slices and
all existing non-time limits. A separate real clock measures the complete compile
call including bootstrap, setup, conversion, search and validation. External
fresh-process timeout is 20 s. Exact certificate and decision fingerprints must
match per pair; equal node counts alone are insufficient. Early exhaustion is
allowed when both versions exhaust the same search. Do not pad work to a ceiling.

Wall mode uses the unchanged .1 s optimization allowance, .1 s active query
allowance, 2 ms/2,048-node slices, eight resident queries, 4,096 frontier,
1,000,000 aggregate nodes and 100,000 validations; other limits are R0's defaults.
Time checks stay at the existing logical boundaries. Wall outputs need not be
identical because the amount of completed search can change; correctness remains
mandatory, and all overhead is charged.

After semantic tests, freeze the development candidate/configuration and run:

- 100 programs × three reps × R0/C1, fixed work: **600 rows**.
- Same complete matrix, .1 s wall allowance: **600 rows**.
- Diagnostic 30 programs × R0/C1, separate peak-memory/parity measurements:
  **60 rows**, never concurrent with timing workers.

Require zero correctness/timeout/missing/duplicate failures, exact fixed-work
parity, fixed-work geometric ratio of per-program median total compile times
**<=0.90**, and equal-family mean paired log(J_C1/J_R0) at .1 s **<=0**.
`J = cycles × scratch`. Include every prescribed program and repetition.
Report absolute time, memory and per-family regressions; do not hide losses.

Failure stops `DEVELOPMENT_TARGET_NOT_REACHED`. After development timing starts,
no performance retuning, replacement mechanism or second development selection.
A correctness/instrumentation defect invalidates the affected selection; retain
it and stop `INCOMPLETE_WITH_EVIDENCE` for lead review. Do not quietly rerun a
favorable replacement matrix under the same freeze.

## 5. Stage C: conditional fresh confirmation

Only D pass permits this stage. Seeds **980000–980199** were reserved but never
generated or measured in the preceding efficiency phase. Reuse that untouched
reservation explicitly; do not assume its availability from the reservation alone.
Inventory prior corpus manifests/files and outcome records first. Any exposure
of this cohort to candidate development or semantic collision with prior public,
development or evaluation inputs yields `DESIGN_INVALID`; no silent reseeding.
Generate only at this stage, record canonical program hashes excluding names
but including semantically relevant inputs, and require 40 programs per family.
Retain the inherited full-program and name-stripped semantic digests. In addition,
check a compilation-input digest that removes top-level `name` and `cases` while
preserving all other fields: changing only test memories must not create a fresh
compiler workload. Exact duplicate compilation inputs within the new cohort or
against prior cohorts invalidate the design. This is an exact-content check,
not a claim to decide arbitrary program equivalence.

Before candidate outcomes on these programs, freeze R0/C1 and all transitive
measured sources, both exports, corpus, expected keys, analysis, auditor, checker,
protocol and configurations. Freeze hashes are immutable. Source/tool changes
afterward invalidate affected confirmation; preserve evidence and stop that claim.

Run fresh processes sequentially in a deterministic randomized cell order within
each program/repetition. Only one measurement worker at a time; no tests, profiler,
fixture generation or kernel measurement alongside it. Record environment and
external load; do not terminate unrelated processes. Sort cell keys by the stable
seed function in PROTOCOL, with a lexicographic tie-break. Programs are ordered
by `(family index, seed)`, public programs by pinned filename. Repetitions are
0-based throughout. Stage/mode keys separate diagnostic, development and
confirmation streams.

Complete matrices:

| Stage | Matrix | Rows |
|---|---|---:|
| Fixed work | 200 × 5 × 2 | 2,000 |
| Wall allowances .01/.1/1 s | 200 × 5 × 2 × 3 | 6,000 |
| Public suite | 8 × 5 × (R0/C1 at three allowances + serial) | 280 |
| Standalone exports | (200 fresh + 8 public) × 3 × 2 | 1,248 |

Both standalone exports use the primary .1 s policy. The R0 export must reproduce
its accepted bytes exactly. Before launch, also validate both on the inherited
142-program / 277-case corpus and unchanged public tests, in minimal workspaces
with pinned machine, empty PYTHONPATH/no user site and a 20 s process timeout:
**284 corpus rows**, plus separately logged pinned tests. Require input immutability,
stdout JSON-only, allowed imports and deterministic export regeneration.
This corpus is correctness evidence, not additional confirmatory samples.

The two confirmatory endpoints compare C1 with R0 only:

1. Cost: per-program median total compile-call time over five fixed-work runs;
   log(C1 median / R0 median), equal-family mean, then exponentiate.
2. Quality: at .1 s, paired repetition log(J_C1/J_R0), average within program,
   equal-family mean, then exponentiate.

Resample programs within each family 10,000 times with the locked bootstrap seed;
use paired program identities for both endpoints on each draw. Each draw samples
40 program IDs with replacement in each family. Within a family use canonical
program-hash order. Two-sided 97.5% percentile intervals use .0125/.9875 linear
interpolation on the sorted 10,000 estimates (position `(N-1)*p`). Exponentiate
the log endpoints. This is Bonferroni adjustment for the two primary endpoints.

Practical success requires **cost-ratio upper bound <=0.80 AND quality-ratio
upper bound <=1.01**, complete evidence and exact fixed-work parity. Otherwise
`TARGET_NOT_REACHED`. The 1% quality tolerance is not Pareto dominance. Report
point estimates, both endpoints, absolute median/p95/max times, family effects,
memory, overshoot, UNKNOWN, construction/validation counts and every public score
repetition. Other budgets and public scores are descriptive. Import and subprocess
time are separate from compile-call time. Claim no classical runtime superiority
or private-grader result. Equal wall allowances may spend the same time while
finding a different J; the 20% cost endpoint is for identical fixed work.

## 6. Evidence, independent checking and limits

Use one source of truth for protocol constants; the checker and numerical auditor
must independently verify them. Reporter/auditor statistical estimators must not
share implementation. Reuse validated I/O owners where appropriate, not reporter
verdicts. Check expected keys, all corpus/family/repetition denominators, fingerprints,
source/export identity, both CI bounds, thresholds and joint verdict. Preserve
raw stdout/stderr/exit/timeouts, source hashes and ordered commands.

Before either timing freeze, dry-run reporting/checking on synthetic complete,
negative and incomplete matrices, including None-valued optional control fields.
Mutations must reject missing/duplicate/torn final rows, missing required stage,
changed source/export, stale/mismatched work fingerprints, fabricated lower/upper
CI, false component/joint PASS, wrong family weight or serial denominator and
invalid export results. Failure/timeout rows cannot be dropped. Numerical agreement
does not establish code provenance; keep both checks. Optional stages must have
explicit dependency-based NOT_RUN states and cannot support a performance PASS.

Freeze expected row keys before each measurement stage. Exactly one authoritative
row per key, with an append-only attempt ledger: do not retry failed/timed-out
keys or select fastest attempts. Interrupted stages may resume only missing keys
under identical frozen inputs, preserving partial/malformed evidence and treating
such incompleteness as a failed gate until independently resolved by the lead.

Budgets: at most **24 hours of total measurement-process wall time** including
diagnostics, kernel probes, failed attempts, acceptance and replays; exclude
implementation/tests. At most **two working days (16 hours) of active development**
before handoff, excluding unattended measurement/test time; maintain a best-effort
work log and disclose interruptions. One nominated design, one integrated
candidate, one development selection and one fresh confirmation. Check remaining
measurement budget before each launch. No threshold changes or extra samples.

Stage failures block dependents. Missing evidence is `INCOMPLETE_WITH_EVIDENCE`;
a properly evidenced negative practical result is a valid completed round.
Continue eligible stages autonomously without routine permission. Only the lead
accepts the release.

## 7. Deliverables and paper transition

Deliver starting/final manifests, `WORK_LOG.md`, measurement ledger,
`DIAGNOSIS.md`, dependency/cost-ownership map, workload hashes, `MECHANISM_SPEC.json`,
kernel parity/timing/prediction evidence, and `MECHANISM_DECISION.json`. Conditional
deliverables include candidate parent/diff, regressions, development freeze and
`DEVELOPMENT.json`, confirmation freeze and `COMPARISON.json`, public scores,
exports/acceptance, independent checker/auditor with field map and mutation outputs.
Every absent conditional deliverable has an explicit NOT_RUN reason.

Always deliver `PAPER_HANDOFF.md` with a claims-to-evidence table covering:

- accepted R0 correctness and the exact source/export identities;
- earlier generated/public improvements with their original comparators, budgets,
  uncertainty and practical-target failures, distinguished from this round;
- this round's mechanism, selection/stop, parity and conditional confirmation;
- the negative learning results and controller-specific label-acquisition limit;
- limitations: development exposure, local machine, no private grader/general
  complexity claim, and what the direct-index method does and does not establish.

Link frozen evidence for every numeric claim. Include unsuccessful attempts and
state whether C1 is eligible for lead acceptance or R0 remains the baseline.
Prepare an outline of necessary manuscript updates without editing the manuscript.
Do not imply a negative result invalidates the whole method or a positive result
proves novelty. After the lead reviews this round, the next planned activity is
paper revision from accepted evidence, regardless of optimization success.

Return `RELEASE_HANDOFF.md` with its exact path, marked READY_FOR_CODEX_REVIEW
or INCOMPLETE_WITH_EVIDENCE, all stage verdicts, counts, deviations and rerun
commands. Preparing this assignment has not launched Claude.
