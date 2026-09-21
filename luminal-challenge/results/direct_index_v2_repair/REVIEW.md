# Lead re-review of repair commit f3391b6

Date: 2026-09-20. Plan: **1.1**. Verdict: **CHANGES_REQUIRED**.

Most original findings are repaired. The fresh measurements are valid and the
compiler passed all executed correctness checks. Three remaining P2 findings
below prevent final acceptance: incomplete comparison membership can pass,
historical integer metrics are not enforced, and construction record accounting
is incomplete. These are remaining parts of R2/R4/R7, not new method requirements.

The lead inspected optimizer/integration repairs and reran verification, defect
probes, comparison, and independent evidence checks. Two read-only reviewers
audited schema/oracle and release-tooling changes. Production files were not
edited. Original evidence and the worker's repair evidence remain intact; new
results are under [lead_review](lead_review/).

## Original finding disposition

| Finding | Decision | Evidence |
|---|---|---|
| R1 candidate discrepancies | CLOSED | Both target bounds checked; four formerly silent discrepancies now recorded; injected machine/target defects reject through the corpus gate; diagnostics come from the same compilation |
| R2 comparison score/completeness gates | PARTIAL | Equal/below-baseline scores reject correctly; exact measurement membership and all classical repetitions still not enforced (F1) |
| R3 independent joint oracle | CLOSED | Always-infeasible mutation now fails with six feasible assignments; pointwise and returned-filling checks exercise all 15 constructible cases, including vector and aliasing fixtures |
| R4 resource enforcement | PARTIAL | Original oversized-leaf and delayed-cover probes corrected; expression nodes and simplified-return paths still escape accounting (F3) |
| R5 isolated per-input timeout | CLOSED | All 142 fresh `-I -S` processes validate 277 cases; timeout injection rejects and retains other records |
| R6 actual tradeoff fixture | CLOSED | Real validated 6 cycles × 24 words → 7 × 16 trade; bounded independent oracle establishes alternatives; official-score calculation improves |
| R7 isolation/provenance/diagnostics | PARTIAL | Isolation, current export, protected hashes, same-run diagnostics and guarded export optimization repaired; historical per-program integer control remains absent (F2) |
| R8 final shorter source window | CLOSED | Source starts advance by two through the final nonempty tail; even/odd fixtures pass |
| R9 count/timeout/reporting | CLOSED | Exactly eleven public tests required; timeout captured; IN_PROGRESS replaces stale PASS before work; submission caveats corrected |

## Remaining required repairs

### F1 — P2: a duplicate classical measurement hides a missing measurement

Locations: [compare_direct.py:410](../../compare_direct.py#L410)–419 and
[compare_direct.py:447](../../compare_direct.py#L447)–458.

`all_runs_present` checks only the number of rows per arm. The classical control
accepts any nonempty list of matching aggregate scores, without requiring all
repetitions. The parent also trusts the worker's returned identity instead of
checking it against the requested arm/program.

The saved probe replays real recorded worker responses through **actual
`run_all(3,20)`**, replacing one classical response in repetition 1 with a response
for another program. Aggregates are recomputed by the runner, not forged in the
finished report. Result: **72 rows, 71 unique keys, only two classical repetition
aggregates, and `all_passed=True`**. The unmodified replay control has 72 unique
keys and three classical aggregates.

Repair and acceptance:

- Require exactly one record for every expected `(arm, program, repetition)`
  from the pinned eight program names and requested repetitions. Reject duplicates,
  omissions, unexpected identities and out-of-range repetitions.
- Verify each worker response's arm/program against the invocation before adding
  parent-owned repetition metadata. Retain a failure record on mismatch.
- Require exactly the expected repetition IDs for every arm's aggregate.
- Add a regression through fresh `run_all` for this duplicate/missing response;
  require overall failure and nonzero CLI status, not merely an internal warning.
- Keep valid real results passing. Do not change the score threshold.

### F2 — P2: aggregate equality permits changed frozen integer metrics

Location: [compare_direct.py:447](../../compare_direct.py#L447)–458.

The protected historical file is hash-checked, but measured serial/classical
cycles and scratch are never compared with its per-program values. Only the
classical combined aggregate is checked. The saved second probe doubles cycles
and halves even scratch values in classical worker responses. Each affected
product is unchanged; fresh aggregation still reports **all gates PASS** despite
the historical integer disagreement.

Repair and acceptance:

- Read expected per-program serial/classical cycle and scratch integers from
  the already-protected historical results. Compare every measured repetition.
- Reject either integer changing even if their product or aggregate score stays
  equal. Record arm/program/repetition, expected and observed integers.
- Exercise both serial and classical drift through the real comparison path,
  including a product-preserving change. Require nonzero overall status.
- Recompute scores from validated raw measurements; retain the aggregate check
  as an additional control, not a replacement for integer equality.

The actual worker and lead rerun measurements have complete unique membership
and match historical integers. F1/F2 concern missing safeguards against faulty
future worker output, not evidence that current published local numbers are wrong.

### F3 — P2: construction returns an expression exceeding its record cap

Locations: [direct_constraints.py:177](../../direct_constraints.py#L177)–180,
[direct_constraints.py:599](../../direct_constraints.py#L599), line 612;
[schema_index.py:693](../../schema_index.py#L693).

Using the existing `two_constants` fixture, window `(0,1)`, incumbent targets,
and `max_records=533`, `JointQuery.expression()` returns an expression containing
**554 records** while its construction meter says **533**. Leaf/conjunction/
disjunction bookkeeping is not consistently charged. Only the later `solve`
call notices exhaustion, after adding the full expression count again: records
become **1,087**, double-counting already charged construction records.

Separately, `relation_cover('le', constant(0), constant(1), ...)` returns an
accepted cube and records zero work under an already-expired meter. The constant
and identical-field simplification paths bypass the clock/accounting checks.

Repair and acceptance:

- Define consistent accounting for cubes and expression nodes and charge them
  as structures grow, including leaves, conjunctions, disjunctions and simplified
  results. Construction must stop before returning an over-cap expression.
- Check the clock on simplified early returns as well as branch loops.
- Avoid billing already-charged construction records a second time when solve
  receives the same meter; still validate and budget externally supplied expressions.
  Do not weaken declared budgets to accommodate the bug.
- Add durable unit regressions for: oversized incoming atomic leaves; early
  cover stopping; early record stopping; this 533/554 mismatch; expired constant
  and identical-field calls; and consistent construction-plus-solve accounting.
- Tests must assert early stopping and UNKNOWN/exhaustion semantics. Existing
  `RelationBudgetTests` only assert eventual exceptions and were unchanged in
  this repair; saved ad-hoc probe results do not replace those regressions.

These defects cause incorrect resource enforcement or premature UNKNOWN; this
review found no resulting mathematically invalid accepted compilation.

## Independent reruns and evidence

Commands run from `luminal-challenge`, each with exit 0:

```sh
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 \
  --output results/direct_index_v2_repair/lead_review/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/direct_index_v2_repair/lead_review/comparison
python3 results/direct_index_v2_repair/lead_review/gate_probes.py
PYTHONPATH=.reference:. python3 results/direct_index_v2_repair/lead_review/budget_probes.py
python3 results/direct_index_v2_repair/lead_review/check_evidence.py
```

The earlier lead's `audit.py` probe function was also loaded with its output
directory redirected here, preserving its original artifacts. The mutation test's
failure in [probes.json](lead_review/probes.json) is the desired observation: an
always-infeasible implementation is now caught. Diagnostic probe commands exit 0
when they run successfully; the still-incorrect observations in F1–F3 are not
release passes.

Observed results:

- **168 direct tests + 11 unchanged public tests = 179 PASS**. All seven direct
  test modules run through the staged verifier; no redundant full second run.
- **142/142 isolated inputs, 277 cases**, zero failures/discrepancies; slowest
  process **1.283334 seconds**, below 20 seconds. Eight public CLI inputs pass.
- All **72 real comparison runs** present and independently checked for unique
  membership. All serial/classical integer metrics match protected history.
- Direct combined score **2.0084662022846573** and classical
  **1.9013791212645499** in every repetition, independently recomputed from raw
  integer metrics. Direct scores about 5.63% higher, with median compilation
  **420.58 ms versus 0.266 ms** (about 1,583 times slower).
- Public gains still come from construction. The lead corpus accepted **seven**
  improvements versus the worker's six; bounded time-sensitive searches may
  reach different outcomes. The worker's stated decline after R8 is an observation
  of that run, not a demonstrated deterministic regression caused solely by R8.
- Protected reference/classical/history/glossary hashes and current source/test
  hashes verified; export matches assembly and recorded SHA256
  `33386bc6ecc2dd82a1787cef9a0c04c369a7aacbbaf9e763a0313356653a376e`.

Evidence: [verification](lead_review/verification/summary.json),
[isolated corpus](lead_review/verification/isolated_corpus.json),
[comparison](lead_review/comparison/runs.json),
[independent evidence checks](lead_review/evidence_checks.json),
[comparison defect reproductions](lead_review/gate_probes.json),
[budget defect reproductions](lead_review/budget_probes.json).

## Focused next handoff

Fix F1/F2 in `compare_direct.py` and its release-gate tests. Fix F3 in
`schema_index.py`, `direct_constraints.py` and their budget tests. If delegated,
these ownership boundaries are independent; workers must preserve each other's
changes and all unrelated work. No architecture redesign is requested.

Preserve this report and every previous evidence directory. Use a new repair
output directory. Add regressions that reject all three saved defect scenarios;
update the checklist and truthful submission/status notes. Since budget accounting
changes search outcomes, rebuild the export and rerun all direct tests, full
isolated acceptance, unchanged public tests, and three-repeat comparison.
Recheck protected hashes, exact run membership, per-program historical integer
controls and independently recompute scores. Mark tasks READY_FOR_REVIEW and
return for lead sign-off; do not self-accept, publish or submit.
