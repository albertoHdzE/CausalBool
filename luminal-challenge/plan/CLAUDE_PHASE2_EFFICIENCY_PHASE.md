# Phase 2: release assurance and propagation efficiency

Version 1.0 · 2026-09-25 · Lead: Codex · Implementer: Claude Code.
**READY_FOR_EXECUTION — NOT DISPATCHED.**

## 1. Goal and decision

First close the concrete findings in
`results/phase2_structural_encoding/lead_next_round_review_20260925/REVIEW.md`.
Then attempt at most one justified, semantics-preserving optimization of the
current best development-selected candidate: **A4 catalog with depth-first
traversal**, `cell_a4cat_dfs` from `next_round_20260925`.

That candidate's 2.18795650138 public score and modest generated-cohort gains
are retained evidence, not a new performance guarantee. The previous worklist
variant missed its selection threshold and is not the new baseline. The previous
practical enhancement target remains missed. No target is retroactively changed.

The per-query tree learner is closed for this phase. The mechanism lost to
Hamming on 30/30 informative fixtures, and its controller discards a query after
the first valid improvement, preventing the required training batch. No new
learning architecture, learning sweep, learning confirmation or manuscript work.

## 2. Authority, ownership and source versions

Read AGENTS.md, INDEX_ONLY_PLAN.md v1.1, STATUS.md, the glossary and pinned machine
semantics, the preceding next-round plan and handoff, then the lead review and
this plan with `phase2_efficiency/PROTOCOL.json`. Start from luminal-challenge:

    ../venv/bin/python plan/phase2_efficiency/verify_package.py

Capture starting status/environment/source hashes. Other agents share this
workspace: preserve their work. Do not edit existing research modules, tests,
old results or protocols, production, references or paper. No agents, process
termination, commit, push, external submission or publication under this assignment.

Own new `research/efficiency_*.py`, `research_tests/test_efficiency_*.py`, and a
fresh `results/phase2_structural_encoding/efficiency_20260925[_N]/`. Never overwrite
an occupied directory. `efficiency_search.py` is an explicitly versioned copy of
next_round_search.py for assurance repairs only (baseline R0). After R0 is frozen,
`efficiency_candidate.py` may derive from R0 for the single engineering attempt
(candidate E1). Retain exact parent bytes, hashes and minimal diffs. Share existing
codec, machine, generator and schema primitives; do not replace their semantics.

Own direct-index bootstrap and index-derived schedule/address decisions remain
mandatory. No classical/serial seed or fallback, BDD/SAT/CP backend, learned
pruning, public-case dispatch, persistent cache across compilations, lowered
validation or expanded budgets. Predictions never certify feasibility.

## 3. Gate R: finish assurance before engineering measurements

### R1. Cover every construction exit

Reproduce the lead's construction probe. The current initialization can spend
1 second against a .1-second allowance, terminate with a valid cap proof, and
still report zero construction interruptions. Repair deadline accounting for
terminal and nonterminal initialization, cap proofs, root conflicts/prunes,
Infeasible/DomainError exceptions and successful initialization.

Define separate fields for construction duration, deadline exceeded, interrupted
before search, mathematical terminal reason and final in-budget query status.
Count an overrun exactly once. After expiry, return the appropriate UNKNOWN
deadline/allowance status while retaining any mathematically derived proof as
late diagnostic evidence; never describe that proof as obtained within budget.
No post-deadline incumbent acceptance. Boundary tests include exact equality,
query versus global expiry, no overrun, repeated resumes and validation events.
Do not erase real validation discrepancies when a deadline also expires.

Preserve R1's already-correct candidate interruption totals. Explicitly document
whether totals include model-phase late validations; inspect the inherited
learner's `info['late_validations']` path and either account for it with a regression
or label the metric as search-phase-only. Do not advertise a total that omits a
supported path. No model performance campaign is needed to test that seam.

### R2. Make the auditor enforce its stated coverage

Reproduce the lead mutation: false mechanism/component PASS plus fabricated
learning upper confidence bounds must fail. The unchanged report must pass the
new numerical audit with the actual negative verdict.

Independently derive/check BOTH bounds of every declared primary interval; all
per-contrast, joint, practical-route and economics verdicts; expected stage keys,
program/fixture/family counts; seeded training code-to-J alignment; novel yields
from oracle plus returned ordering; the prescribed common-pool construction and
permutations; fixed sample counts and resample constants; public denominators;
export membership/correctness/hash evidence. Cover missing required reports/stages,
truncated/malformed rows, duplicates and timeouts. Never silently ignore a final
malformed JSONL row in completed-stage evidence. Optional unfinished stages must
be named explicitly; they cannot support PASS or a "nothing unaudited" assertion.

Make a field-to-check map. Mutation tests must demonstrate failure on both lower
and upper bounds, false flags, wrong economics denominator, altered training J,
invented pool membership, false per-row yield, missing export row, changed source,
missing required stage and wrong serial score. The numeric auditor must use
independently written estimators, not call the reporter's statistical functions.
Keep the historical auditor unchanged; write the successor audit to a NEW directory.

### R3. Resolve source and ranker provenance precisely

The lead allows a narrow disposition of the previous report-only None-filter
change: preserve at-freeze and repaired bytes and their exact hashes, identify
the descriptive fields affected, and independently reproduce the primary/candidate
estimates. This does not waive any different source change or measurement drift.
The successor checker must report expected historical deviations distinctly from
unapproved failures; do not erase the old checker result or return blanket PASS
just because known finding codes are present. Require exact file/hash/scope matches.

For the 420 oracle-capability flags, establish an oracle-free dependency boundary
for a replay ranker. Extract the needed pure helpers into new efficiency modules,
preserving algorithm bodies and provenance/per-function hashes; do not change
training, pool construction, seeds, tree definition or tie-breaks. Reuse schema
primitives. Do not fake an oracle module or weaken import guards to make them pass.
Run in a minimal workspace with runtime denial of oracle/evaluator imports and
data access; distinguish allowed code/stdlib reads from ranker input reads.

Replay all 420 original ordering inputs exactly once and require identical ordered
indices and digests. No new fixture cohort, fitting policy or efficacy hypothesis.
Retain original rows and label replay as isolation verification, not fresh statistical
confirmation. Recount all learning outcomes independently; gates must remain negative.

### R4. Close the current learner on a precise invariant

Write `LEARNER_CLOSURE.md` explaining product-bound pruning at full assignments,
strict-improvement-only surviving valid leaves, stop_on_improvement, query-local
observation state, the half-time interruption exception and epoch disposal. State
assumptions (sound bounds and validator agreement). The conclusion concerns the
first model-preparation boundary, not every possible learner or observation hook.
Add an exhaustive small-domain or deterministic behavioral regression that counts
observations per query; reject the prior interpretation that mere propagation
speed can supply 20 labels to this controller. Keep 0/100 as historical diagnostic,
not a clean isolated timing study, because it overlapped oracle fixture generation.

### R exit criteria

Retain passing repair regressions, false-evidence mutations, immutable-source
checks, isolated ordering replay, and standalone R0 acceptance on all 142 programs /
277 cases plus unchanged public tests. Run applicable inherited semantic tests on
R0 explicitly; frozen evidence-checker tests need their original source view so new
module detection is not weakened. Record exact source view and suite counts; the
previous 443-test statement is not automatically a new R0 test result.

At R exit freeze R0, its exporter and assurance instruments. Worker may continue
eligible stages without routine lead permission, but cannot self-accept the release.
Any unresolved R requirement blocks P/E/C; finish a repair handoff instead.

## 4. Gate P: identify avoidable work, not just a broad profile label

Use existing development seeds 800000–800099 only. Primary policy is A4 catalog,
DFS, existing propagation/canonical ranks, .1 s optimization allowance, eight
resident queries, 2 ms/2,048-node slices, frontier 4,096, query .1 s active allowance,
aggregate 1,000,000 nodes and 100,000 validations. Bootstrap and complete compile
time remain separately charged/reported.

Profile separately on the first two seeds of each family. Subdivide propagation
into precedence, issue-capacity, address support, compulsory-live/product bounds,
state copying and certificate bookkeeping. Count calls, domain changes, repeated
input signatures, cacheable work and memory; reconcile exclusive time with total.
Use unprofiled matched-work timings to quantify profiler distortion. Do not run
profilers, tests or fixture generation beside measured workers.

The worklist implementation already saved only about 5%; do not assume another
worklist is the answer. Before implementation write ONE mechanism proposal with
measured avoided work, estimated overhead/memory and falsifiable parity conditions.
Allowed mechanisms: reuse of immutable/canonical computations, selective update of
exact bounds, or representation-level reduction of repeated domain/certificate work.
No new pruning rule, changed search order, removed certificate obligation or broader
neighborhood. A cache must include domain/epoch identity and every input affecting
the cached result, with deterministic bounded eviction and no cross-program reuse.

Proceed with E1 only if the measured component and repeat-work counts justify a
plausible >=20% reduction in TOTAL fixed-work compile-call time after overhead.
Document that this is a prediction, not a guaranteed speedup. If there is no such
case, stop as NO_JUSTIFIED_OPTIMIZATION and deliver the repaired baseline and
diagnosis; do not try several mechanisms until one looks favorable.

## 5. Gate E: one candidate, same work and same decisions

E1 may differ from R0 only by the proposed mechanism. Test exact feasible/improving
object sets and minima on all applicable exhaustible fixtures; canonical code/rank
round trips; bound/deletion soundness; deterministic incumbent/candidate order;
pruning outcomes; resumes; frontier/node limits; same mathematical certificates
(or independently replayable equivalent reasons if emission order changes).

Fixed-work mode is a diagnostic wrapper for BOTH versions: aggregate 10,000 nodes,
100,000 validations, existing per-query node/frontier/resident limits; suppress
optimization/query/slice wall expirations via the same deterministic clock for both,
retaining the 2,048-node cooperative slice. External fresh-process timeout remains
20 s. Canonical limit/status sequences and actually charged work must agree. Early
exhaustion is valid if both finish the same search; do not pad it to the ceiling.
Record actual unprofiled time with a separate real clock, including bootstrap,
setup, optimization and validation. Equal nodes alone is not a parity proof.

Run development on all 100 programs × three reps × two versions in fixed-work
mode: **600 rows**. Run the same 100 × three reps × two versions at the .1 s
optimization allowance: **600 rows**. Any missing/incorrect/timed-out row blocks
the affected gate; no conditioning on successful pairs. Engineering selection:
all semantic gates pass, fixed-work geometric ratio of per-program median TOTAL
compile-call times <=0.90, and mean log(J_E1/J_R0) at .1 s <=0. Freeze E1 only
then; otherwise stop E1 as DEVELOPMENT_TARGET_NOT_REACHED. No second attempt.

## 6. Gate C: fresh confirmation, only if E qualifies

Reserve seeds **980000–980199**, five equal generator families. Verify no prior
candidate exposure or semantic collision with prior public/development/evaluation
cohorts. A collision or exposure yields DESIGN_INVALID; no silent reseeding.
Freeze source, both exports, corpus, limits, expected keys, analysis, checker,
auditor and all gates BEFORE any candidate outcome on this cohort.

Measure R0 and E1 sequentially, with stable randomized cell order inside program /
repetition. Five repetitions, complete matrices:

- Fixed-work primary, 200 × 5 × 2 = **2,000 rows**.
- Wall allowances .01/.1/1 s, 200 × 5 × 2 × 3 = **6,000 rows**.
- Public suite, 8 × 5 × (2×3 + serial) = **280 rows**.
- Selected E1 standalone export on public plus fresh programs, three reps each =
  **624 rows**, with unchanged public tests, input immutability and isolated imports.

This study compares only E1 with repaired R0, not classical runtime superiority.
Do not pool the old cohort or regard five runs of one program as five programs.

Two confirmatory endpoints (one family):

1. Fixed-work total compile-call cost E1/R0: per-program medians over repetitions,
   log ratios, equal-family mean, exponentiated.
2. Output J E1/R0 at the .1 s allowance: paired repetition log ratios averaged
   within program, then equal-family mean, exponentiated.

Bootstrap programs within family 10,000 times with the locked seed. Use two-sided
97.5% intervals, percentiles .0125/.9875 (Bonferroni over two endpoints). Practical
success requires cost-ratio upper bound <=0.80 AND J-ratio upper bound <=1.01,
complete paired membership, matched fixed-work decisions, and zero correctness
failures. Otherwise TARGET_NOT_REACHED; do not lower the margins or increase N.

The 1% quality tolerance is explicit and is not Pareto dominance. State any losses,
absolute median/p95/max compile times, overhead, memory, overshoot, UNKNOWN and
construction/validation counts. Other budgets, families and public scores are
descriptive. Exact public arithmetic uses every program in each repetition and
the original serial denominator; report all differences, not just a mean score.

Faster work at a fixed effort may instead produce better J while spending the
same .1 s wall allowance. Do not require or advertise a 20% shorter wall-limited
compile when the policy deliberately spends its full allowance. The speed claim
is specifically for identical fixed-work searches; wall-budget quality is separate.

## 7. Evidence and stop rules

Real subprocess commands, durable raw rows/stdout/stderr/exits, environment/source
hashes, immutable manifests, exact expected-key membership, failure counts and
resume rules are mandatory. The checker independently validates row/source identity;
the numerical auditor independently recomputes estimates, both CI endpoints and
verdicts. The report must pass a complete dry run containing None-valued optional
control diagnostics before freeze. Post-freeze source changes invalidate affected
confirmation; retain evidence and stop that claim, never quietly update hashes.

24 hours maximum total measurement-process wall time, including failed attempts
and verification replays, excluding implementation and tests. Check remaining
budget before each launch, retain interruptions and exact incomplete denominators.
No more than one candidate or fresh compiler cohort; no new learning experiment.
No production promotion, paper edits or outside publication. Passing worker checks
permits this prescribed local sequence, not final lead acceptance.

Deliver `ASSURANCE_CLOSURE.md`, `LEARNER_CLOSURE.md`, `AUDIT_COVERAGE.json`,
before/after lead probes and mutation outputs, guarded ordering replay, snapshots
and diffs, `PROFILE.md`, `MECHANISM_PROPOSAL.json`, `DEVELOPMENT.json`, applicable
freeze/comparison/public/export artifacts, raw measurements and checker/auditor
outputs, and `RELEASE_HANDOFF.md` marked READY_FOR_CODEX_REVIEW or
INCOMPLETE_WITH_EVIDENCE. A justified stop with no engineering candidate is a
valid result; an unresolved assurance finding is not an accepted release.

## 8. Why this direction

The local profile identifies propagation as the dominant measured component;
the preceding worklist result shows that category alone is insufficient to choose
an optimization. Schulte and Stuckey's primary research,
[Efficient Constraint Propagation Engines](https://www.gecode.dev/publications/2009-02-23-efficient-constraint-propagation-engines/),
studies avoiding redundant propagator execution and tracking fixpoints. It informs
the measurement questions here; no Gecode backend or published speedup is imported,
and no benefit for this implementation is assumed. Source consulted 2026-09-25.
