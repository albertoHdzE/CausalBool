# Phase 2 next round: repair, comparative efficiency and learning feasibility

Version 1.0 · 2026-09-25 · Lead: Codex · Implementer: Claude Code.
**READY_FOR_EXECUTION; not dispatched, implemented or accepted.**

## 1. Decision and scientific purpose

Run one bounded round. Existing evidence justifies further work on joint direct-index
search: A4 improves geometric cycles × scratch (J) by 6.04% over frozen Phase 2
on its generator cohort. It does not establish a runtime advantage over classical,
nor superiority over the earlier cap512_wider optimizer. The learning experiments
did not answer their question: the new study's endpoint was saturated in all 30
fixtures. This was a protocol-design limitation, not an implementation failure to
produce a positive result.

The next round must answer four questions:

1. Can interruption accounting be repaired without changing search decisions?
2. Which of the two delivered optimizers offers better quality for a given cost?
3. Does A4 benefit from its neighborhood catalog, its traversal, or their interaction?
4. Can the existing schema ranker prioritize useful unseen objects, and can a real
   query afford the observations needed to use it?

No positive result is required. Closing an unproductive direction is a successful
research outcome. Do not run another full learned-compiler campaign in this assignment.

## 2. Authority, scope and immutable inputs

Read AGENTS.md, INDEX_ONLY_PLAN.md v1.1, STATUS.md, the glossary, pinned machine
semantics, both completed RELEASE_HANDOFF.md files, the focused lead review at
`results/phase2_structural_encoding/lead_objective_review_20260925/REVIEW.md`, and
the previous research protocol for inherited algorithm definitions. This document
replaces its future execution schedule, seeds, learning endpoint and gates only.
Keep every historical protocol and measured result intact.

First run `../venv/bin/python plan/phase2_next_round/verify_package.py` from
`luminal-challenge`. Capture starting Git status, source hashes and environment.
No process termination, new agents, commits, pushes, manuscript edits, production
integration or external submission. Other work shares the workspace; preserve it.

Own only new `research/next_round_*.py`, `research_tests/test_next_round_*.py`, and
`results/phase2_structural_encoding/next_round_20260925/` (use the next numeric
suffix if occupied; never overwrite). Keep existing research source immutable.
For the repaired solver, create `research/next_round_search.py` as an explicitly
versioned copy of the frozen objective_index_search owner, retaining attribution,
source hash and a minimal diff. Reuse existing codec, ranker, generator and machine
owners; do not duplicate them. New workers must explicitly import the new solver.
Do not monkey-patch production or frozen modules to implement the new version.

The earlier optimizer is its frozen `cap512_wider` configuration with cached
build, query cap 512, and its existing window order. The other reference is A4
with only the reporting repair below. Both remain research comparators pending
full independent acceptance, not newly accepted production baselines. Verify
their source identities and isolated imports; never substitute current defaults.

Method boundaries remain: own direct-index bootstrap; canonical decimal anchors,
free-coordinate masks and sumandos; no BDD/SAT/CP backend or classical/serial
seeding/allocation in candidate paths. Classical and serial are measurement
controls only. UNKNOWN never means UNSAT. Every accepted compilation requires
the pinned validator and cases. Preserve inclusive lifetimes and issue capacities.

## 3. Stage R: repair and finish correctness review before timing

Reproduce R1 with the lead probe on frozen source. In the successor version move
interrupted-validation accounting outside the learner-only branch. Report both
total interrupted validations and affected-query count with unambiguous names;
include per-query counts. Retain construction interruptions separately. Cover
before/during-validation expiry, no-learner and learner paths, query versus global
deadlines, multiple interrupted validations, and zero-interruption control cases.

Regression must fail on frozen source and pass on the successor. Verify no late
incumbent acceptance and unchanged valid results/statuses under a deterministic
clock and equal charged work. Historical missing counts remain unknown, not zero.
Old timing rows continue to describe old source; no retroactive rehashing.

Run all 392 inherited research tests plus new tests, applicable canonical direct
verification and independence checks, exhaustive domain/propagation tests affected
by any new traversal, and standalone acceptance on the 142-program corpus plus
unchanged public tests. Retain commands/logs/exits. Review both reference paths
for hidden fallback, source isolation and validator bypass. Any correctness
failure blocks measurements using that arm; report it, do not silently drop it.
Run historical evidence-checker tests in a verified original-source snapshot:
the old checker deliberately rejects any added research module. New modules do
not retroactively invalidate old source; do not weaken that checker to hide the
addition. Separately run reused semantic tests against the successor and the new
checker against its explicit new manifest. Record which source view each suite
actually exercises; passing historical tests alone does not test the successor.

Deliver `REPAIR.md`, source snapshots/diffs, hashes, before/after probe output,
and a requirement-to-evidence table. Fix the known empty attempted_queries
summary in the NEW report owner; no post-freeze report monkey-patch is planned.

## 4. Stage D: development diagnosis and a controlled ablation

Use only existing development seeds 800000–800099, five equal families. Public
programs and previous evaluation results are development-visible, never fresh
confirmation. Do not use public outcomes in the numeric selection rule.

Implement the following 2×2 ablation in the successor controller:

| Factor | Level 0 | Level 1 |
|---|---|---|
| Catalog | A3 product_window_plan, radius 2 | Existing A4 build_catalog |
| Within-query traversal | Canonical depth-first, low rank first | Existing discrepancy heap |

Hold product caps, propagation, canonical variable order, validation, aggregate
guards, resident-query count, round-robin slice scheduling and epoch restart fixed
at repaired A4 values. This intentionally differs from A3's old sequential
controller; do not label that cell as a reproduction of old A3. Stack and heap
each stop UNKNOWN at >4,096 queued prefixes; no silent beam dropping. Preserve
the 2 ms / 2,048-node slice, eight residents, cumulative 0.1 s query allowance,
1,000,000 aggregate nodes and 100,000 validations. The 1/1 cell must match repaired
A4 under a deterministic clock/work limit. Test exhaustive object-set/minimum
agreement and resumed versus uninterrupted prefixes for both traversals.

Measure four cells and the earlier cap512_wider reference: 100 programs × three
budgets (.01/.1/1 s) × three repetitions × five arms = **4,500 rows**. Record
all costs and losses. The budget is the optimization allowance, not a promise
that total compilation including bootstrap finishes in that allowance. Report
bootstrap, optimization, complete compile-call and fresh-process time separately.

Use separate profiling runs on the first two seeds of each family. Attribute
cost to domain construction, propagation, frontier management, encoding/digest,
validation and orchestration, reconciling with total measured time. No profiling
during timing runs. Record incumbent improvements with elapsed time and J.

Record time-to-reach 1% and 5% improvement over each program's own direct-bootstrap
J; a target is `J <= floor((1-r)*J_bootstrap)`. Unreached targets are censored and
remain in denominators. No average over successful hits alone. Report attainment
at each budget, and capped hitting-time distributions, explicitly retaining failures.
These are descriptive diagnostics, not proof of speed equivalence.

For the four cells run fixed-work diagnostics on the same ten profiling programs
at aggregate node limits 1,000/10,000/50,000, without wall cutoff except the 20 s
external safety limit. One deterministic run per cell/limit/program = **120 rows**.
Define a charged node consistently before measurement; separately count propagation
work and validations. Equal node count is not equal CPU work. Timeouts stay visible.

Compute descriptive factorial effects and interaction on per-program log J;
retain family breakdown and compile costs. Do not infer a catalog effect merely
from old A3-versus-A4 rows, where scheduling also changed.

## 5. Stage E: at most one cost-focused engineering candidate

Select the strongest of the five development arms at .1 s by minimum equal-family
mean log J, repetitions averaged within program; ties within 1e-12 use lower
geometric median compile time, then lexicographic arm ID. Existing methods can win.

Permit one semantics-preserving engineering change to that selected arm, chosen
from the largest measured cost component. Examples: remove repeated immutable
construction, incremental bookkeeping, or avoid repeated digest serialization.
Write a concrete mechanism and expected saving BEFORE measuring it. No new
neighborhood heuristic, per-program dispatch, learner, lowered budget, reduced
validation, persistent cross-program cache or iterative configuration sweep.

Require deterministic candidate-sequence, pruning-decision and incumbent parity
at equal work on the development corpus and exhaustive fixtures. If that cannot
be shown, mark this candidate INELIGIBLE rather than calling it a pure speedup.
Measure at the same three budgets/repetitions: at most **900 extra rows**.

Freeze one final candidate: engineer variant only if it passes correctness,
does not worsen development mean log J at .1 s, and reduces geometric median
compile time there by at least 10%; otherwise retain its parent. Do not claim
this exploratory gate proves a population benefit. Record development uncertainty
and expected detectable effects; fixed sample sizes remain fixed.

## 6. Stage C: honest head-to-head confirmation

Before any new evaluation outcome, freeze source, controls, export, reporters,
checker/auditor, expected keys, candidate selection and all datasets/configuration.
This compiler freeze covers its own datasets. The later learning track has a
separate fixture/pool manifest freeze before evaluating orderings; shared measured
source remains frozen throughout. Constructing that manifest is not authorization
to change algorithms after seeing compiler confirmation results.
Use seeds **960000–960199**, 200 programs / 40 per family. Verify semantic
disjointness against all prior cohorts and no outcome exposure. A collision or
prior exposure stops this confirmation as DESIGN_INVALID; no silent replacement.

Measure earlier cap512_wider, repaired A4 and the selected candidate (deduplicate
exact source/config aliases): 200 × five reps × three budgets × K, K=2 or 3,
thus **6,000 or 9,000 rows**. Also classical and original direct bootstrap once
per repetition, unbudgeted: **2,000 rows**. Public: 8 × five reps ×
(3K+3), including these controls and serial, **360 or 480 rows**. Keep generated
and public results separate. Randomize arm/budget order within program/repetition
with the stable hash defined in PROTOCOL.json. Workers run sequentially.

Primary head-to-head: mean paired log(J_earlier/J_A4) at .1 s, five repetition
logs averaged per program, equal-family means. Bootstrap programs within family
10,000 times; two-sided 95%. Lower >0 favors A4; upper <0 favors earlier;
otherwise INCONCLUSIVE. Report per-program losses and costs regardless of winner.
This is one prespecified comparison, not selection using confirmation data.

If a distinct new candidate was frozen, four additional confirmatory endpoints
are its J ratio and compile-time ratio against EACH reference. Quality uses paired
repetition logs; cost uses the ratio of per-program median compile times. Use
two-sided 98.75% intervals for all four (Bonferroni for this separate four-endpoint
family). Prefer a practically useful result defined in advance as either:

- Quality route: upper J ratio <=0.98 AND upper compile ratio <=1.10 versus BOTH.
- Efficiency route: upper compile ratio <=0.80 AND upper J ratio <=1.01 versus BOTH.

These 2%/20% targets and 1% quality/10% cost tolerances are engineering decisions,
not known achievable effects. If neither route passes, report target not reached.
Do not relabel an existing-reference alias as a newly improved method. Other
budgets, fixed targets, classical comparisons and factorial effects are descriptive.
No claim of broad Pareto dominance follows from a tolerated quality regression.

Recompute public score exactly from eight programs in each repetition, reconcile
with exp(mean(log J_control/J_candidate)/2), and show all per-program C/S/J.
Private-grader, cross-generator and general-complexity claims remain unsupported.
Export the frozen selected candidate at .1 s and validate in isolation on public
and fresh programs, three reps each: **624 rows**, plus unchanged public tests.

## 7. Stage L: learning mechanism and economics pilot, with early stops

Do not reuse the impossible best-test-below-training-minimum endpoint as the
primary endpoint. Keep the old FAIL/INCONCLUSIVE results unchanged. Keep the
existing depth-3 tree, training labels, candidate-pool algorithm, Hamming order,
shuffled labels and ten random-order controls; no learner tuning this round.

First use the existing 15 development fixtures. For each, take **20 feasible
objects uniformly without replacement** from sorted physical identities using
the new fixed seed keyed by fixture hash. This is oracle-supplied training for a
controlled mechanism test, NOT free training available to a compiler. Hold out
all remaining identities. Oracle/test labels stay in the evaluator process;
ranker inputs are only training codes/J, domain metadata and unlabeled pool.
Freeze the common pool and permutations before evaluating any ordering.

Primary endpoint is **novel elite yield at 32 proposals**: number of distinct
held-out feasible objects in that prefix with J <= the training-derived elite
threshold, divided by 32. Invalid proposals consume positions, short pools have
empty remaining positions. No oracle filtering of pools, no training reuse counted
as novelty. Report best J relative to training minimum as a secondary endpoint,
and explain if it remains saturated. Higher yield is prioritization, not proven
strict optimization improvement or speedup.

Before evaluating orders, compute endpoint sensitivity from the common pool:
with N entries, M useful entries, k=min(32,N), the maximal attainable count is
min(k,M), minimal max(0,k-(N-M)). Their difference must be positive to distinguish
orderings. Record constant labels, no useful pool objects, short pools and this
range; never drop them from denominators. Require >=10/15 informative development
fixtures with every family represented. Otherwise stop learning as
DESIGN_INSUFFICIENT and explain the exact failure without another resplit.

Also trace actual paid observation acquisition on the 100 development programs
at .1 s, one run each with the frozen existing conditional learner controller
and repaired accounting. Record the fraction of programs with >=1 query reaching
20 distinct case-validated observations by its search-half boundary, remaining
query/global time, and total construction/validation/fitting/order costs. Do not
inject oracle training. These **100 diagnostic runs** are not efficacy evidence.
If fewer than 10% of programs have such a query, label the current per-query
learning architecture ECONOMICALLY_UNAVAILABLE. Finish the small mechanism test
if informative; do not launch a learned-compiler comparison. Constant trees and
failed economics are retained, not repaired by looking at fresh outcomes.

If development sensitivity passes, construct fresh fixtures with the exact
previous deterministic structural qualification recipe, using pool seeds
**970000–970399**, first six qualifying programs per family, 30 total. Structural
qualification is independent of learner outcomes, headroom and prefix utility.
Check semantic collisions; no ad hoc replacements or outcome-based selection.
Apply the same 20-object draw and common-pool sensitivity diagnostic before order
evaluation. Require >=20/30 informative fixtures with >=3 in every family;
otherwise record DESIGN_INSUFFICIENT and stop before the ordering matrix. Retain
all 30 in primary aggregates when eligible, including uninformative fixtures.

Run tree, Hamming, shuffled-tree, ascending and ten seeded random permutations:
**14 orderings × 30 fixtures = 420 deterministic rows**; repeat timing five times
separately if needed (2,100 rows maximum), never treating repeats as new fixtures.
Primary contrasts are paired yield differences tree minus Hamming, random mean,
and shuffled-tree. Equal-family means; 10,000 fixture-within-family bootstraps;
two-sided 98.333333% intervals. A mechanism signal requires ALL lower bounds >0
and ALL point gains >=0.05 absolute yield. Fail/INCONCLUSIVE does not prove no
learning algorithm could help. New-query economic availability and this mechanism
signal are distinct gates; neither establishes end-to-end compiler benefit.

No additional learned-compiler campaign is authorized this round, even after a
signal. Handoff proposes a specifically costed subsequent test only if BOTH
mechanism and economic gates pass. If Hamming wins or economics fails, retain
the non-model compiler and redirect effort to the measured solver bottleneck.

## 8. Evidence, stop rules and deliverables

Every measured row needs correctness, case counts, command, source/config hashes,
timings, failure/timeout, exact key, program/domain identity, and real stdout/stderr
and exit status. Use immutable stage manifests and durable per-worker journals;
resume missing keys only under identical hashes. Independently derive expected
denominators and detect duplicates, missing rows, source drift, fabricated counts,
leaked labels, false gates and wrong score denominators. The numeric auditor must
not import the experiment's estimator or runner. Recompute estimates from raw rows.

Any known correctness discrepancy blocks the affected comparison, irrespective of
deadline. A source fix after confirmation exposure invalidates affected inference;
retain evidence and finish unaffected stages, never reseed silently. Locked plans
are not edited by the implementer. New findings may narrow claims, not relax gates.

Bounded budget: at most one engineering candidate, one fresh compiler cohort and
one fresh learning fixture pool; no extra sweep. At most **24 hours of measurement
process wall time**, excluding development and tests. Check before launching a
worker and stop cleanly at the cap; incomplete stages cannot pass. Prioritize R,
D, E, C, then L. Count all failed attempts and reruns against the cap. Freeze a
preflight time estimate; the cap is not permission to omit expensive failures.

Deliver `REPAIR.md`, `BOTTLENECKS.md`, `FACTORIAL.json/.md`, `SELECTION.json`,
`FROZEN_SELECTION.json`, `COMPARISON.json/.md`, `PUBLIC_SCORE.json/.md`,
`LEARNING_FEASIBILITY.json/.md`, `READINESS_MATRIX.md`, source snapshots/diffs,
full rows/logs/commands, standalone validation, checker/auditor results, and
`RELEASE_HANDOFF.md` marked READY_FOR_CODEX_REVIEW or INCOMPLETE_WITH_EVIDENCE.
Explicitly separate reporting repair, correctness evidence, measured enhancement,
mechanism-only learning, economic availability and unresolved questions.

Proceed through eligible stages without routine confirmation. Stop only the
dependent track when a gate fails; continue independent authorized work. Only
Codex accepts. A gate failure is a result, not permission to keep searching until
something looks positive.

## 9. Research basis and limits of inference

Primary sources checked 2026-09-25:

- Castañeda Lozano et al., [Combinatorial Register Allocation and Instruction
  Scheduling](https://arxiv.org/abs/1804.02452): joint compiler optimization can
  trade compilation effort for output quality. This supports the research question;
  their results do not establish our method's novelty or performance.
- Gasse et al., [Exact Combinatorial Optimization with Graph Convolutional Neural
  Networks](https://proceedings.neurips.cc/paper/2019/hash/d14c2267d848abeb81fd590f371d39bd-Abstract.html):
  learned policies can guide search. Our small schema tree, training cost and
  domain-specific coding must be tested independently; their gains do not transfer.
- Hansen et al., [COCO performance assessment](https://numbbo.github.io/coco-doc/perf-assessment/):
  time/evaluations needed to reach quality targets complement fixed-budget results.
  Here compiler wall time, node work and validation cost are distinct; censoring
  and budget-dependent policies prevent treating successful runs alone as speed evidence.
