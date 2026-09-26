# Gate R: assurance closure (efficiency phase)

2026-09-25 · Claude Code · plan `CLAUDE_PHASE2_EFFICIENCY_PHASE.md` §3 and
`phase2_efficiency/PROTOCOL.json`. The lead review
`lead_next_round_review_20260925/REVIEW.md` raised the findings closed here.
This document is not self-acceptance; only the lead accepts.

| Requirement | Result | Evidence |
|---|---|---|
| R1 construction exits | CLOSED in R0 | `repair/source/`, `research_tests/test_efficiency_search.py` (14) |
| R1 model-phase late validations | counted, with a regression | same file, `ModelPhaseLateValidations` |
| R2 auditor enforces its coverage | CLOSED | `assurance/successor_audit/`, `AUDIT_COVERAGE.json`, `research_tests/test_efficiency_audit.py` (22) |
| R3 source provenance | D1 approved on exact evidence | `assurance/checker/EFFICIENCY_CHECKER.json`, `research_tests/test_efficiency_checker.py` (9) |
| R3 ranker isolation | 420/420 guarded replays identical | `ranker_replay/`, `research_tests/test_efficiency_ranker.py` (5) |
| R4 learner closure | invariant documented and regressed | `LEARNER_CLOSURE.md`, `research_tests/test_efficiency_learner_closure.py` (4) |
| R exit | all criteria met; R0 frozen | `R0_FREEZE.json` (sha `f24d0da3…`), `r0_export/`, `r0_checks/` |

The lead's two probes, before and after the repairs
(`assurance/lead_probes/LEAD_PROBES_BEFORE_AFTER.json`):

| Probe | Before (parent solver, historical auditor) | After (R0, successor auditor) |
|---|---|---|
| Construction overrun: program 800000, clock 0→1 s inside a cap proof, 0.1 s allowance | interruptions **0**; the query reports `NO_STRICT_IMPROVEMENT` | interruptions **1**, overruns **1** (0.9 s past the deadline); status `UNKNOWN_DEADLINE`; proof kept as `late_terminal_reason`; 0 accepted |
| False mechanism PASS, component PASS and upper bounds set to 999 | **PASS**, 52,013 checks, 0 findings | **FAIL**, `LEARNING_CONTRASTS` ×6 |

## R1: construction and model-phase accounting (`research/efficiency_search.py`, R0)

R0 is a byte copy of `research/next_round_search.py` (sha `b982d4cf…`) with a new
header and two repairs. The parent bytes, the R0 bytes, their hashes and the
158-line unified diff are kept in `repair/source/`.

- **R1a.** One clock reading now closes initialization on **every** exit: cap
  proof, root conflict, root prune, `Infeasible`, `DomainError` and normal return.
  - That reading is passed to the search loop as its first reading, so R0 reads
    the clock exactly as often as the parent, in the same order.
  - Each query reports `construction_seconds`, `construction_deadline_exceeded`,
    `construction_past_deadline_seconds`, `interrupted_before_search`,
    `terminal_reason`, `late_terminal_reason` and the final in-budget `status`.
  - If a terminal outcome is derived at or after the deadline, the status becomes
    `UNKNOWN_DEADLINE` when the overall deadline has expired, and
    `UNKNOWN_ALLOWANCE` when only the query allowance has. The proof is kept as
    late diagnostic evidence only.
  - Each query is counted at most once in `construction_overrun_count` and at
    most once in `construction_interruption_count`.
- **R1b.** The inherited learner's `info["late_validations"]` (a model-phase
  candidate validated after its hard deadline) was missing from the parent's
  totals. It is now counted. `interrupted_validation_total` equals
  `…_search_total + …_model_total`. `…_queries` counts distinct (epoch, query)
  pairs.
- **Tests, all passing.** 14 tests in `test_efficiency_search.py`:
  - every exit crossed with {no overrun, exact equality, query-only expiry,
    overall expiry};
  - a nonterminal overrun;
  - repeated resumes, which are not interruptions;
  - a validator rejection kept when the deadline also expires;
  - an interrupted validation and an overrun counted separately;
  - the real `QueryLearner.step` seam, and the controller total including it;
  - the parent omitting both, as a power check;
  - decision parity with the parent: 13 programs × 2 traversals × 2 clock regimes;
    identical traces, incumbents, clock-reading counts, certificate streams,
    aggregates and interrupted-validation totals; statuses equal after mapping
    each late relabel back to its terminal reason.
- **Interpretation of the historical counts.** The next round's reported
  construction-interruption counts (for example 75 and 76 in `COMPARISON.json`)
  count only nonterminal-path interruptions, which is the lead's F1. The auditor
  confirms they equal the row sums. They are historical under that incomplete
  definition and are not restated.

## R2: the successor auditor (`research/efficiency_audit.py`)

It uses only the standard library and imports nothing from `research`, the
production tree or the reporter. Its estimators are written in the file itself:
program-within-family bootstrap, paired logs, medians, geometric times, factorial
contrasts, targets, public score, the training draw, the common pool, a depth-3
exact-Gini tree, yields and sensitivity.

- **Unchanged release.** PASS: **162,982 checks, 0 findings, 0 unmapped fields**,
  with the negative verdicts intact (`FAIL_OR_INCONCLUSIVE`,
  `ECONOMICALLY_UNAVAILABLE`, `TARGET_NOT_REACHED`).
- **What is recomputed and compared**:
  - both endpoints of every interval (primary, the 4 candidate endpoints, the 3
    learning contrasts, every descriptive and factorial interval, engineering
    uncertainty);
  - every flag and verdict (per contrast, joint mechanism, routes, economics,
    selection, engineering, design gates);
  - expected stage keys, re-derived from the protocol order rule;
  - program, family and fixture counts;
  - training code-to-J alignment, pair by pair, from the oracle;
  - the common pool, rebuilt from the training set and seed and compared as a
    set, by hash and by its statistics;
  - every closed-form ordering (ascending, Hamming, 10 random, shuffled labels,
    both trees) against the returned ordering;
  - novel yields from the oracle plus the ordering;
  - the resample count and percentile constants against the locked protocol;
  - the public denominators;
  - export membership (624), correctness, J = C·S, the compiler hash and the
    export public scores.
- **Raw evidence is read strictly.** Any malformed line, including a torn final
  line, is `MALFORMED_ROW`. Duplicate, missing, unexpected, failed and timed-out
  rows are findings. A missing required report or stage is `MISSING_REQUIRED`.
- **Field-to-check map (`AUDIT_COVERAGE.json`).** 8,591 report leaves:
  - **6,421** compared by a named check;
  - **2,170** in declared-unchecked classes, each with a reason: timestamps, free
    text, paths, source-hash tables owned by the checker, cohort legality
    metadata, and `decode_mismatches`, which needs the codec;
  - **0** unmapped.

  `complete_coverage_claimed` is `false`.
- **Mutations.** 22 tests, 21 of them mutations, all required to FAIL:
  - both bounds;
  - false route and contrast flags;
  - the economics denominator and verdict;
  - a per-row yield, in the report and in a raw ordering row;
  - altered training J;
  - invented pool membership;
  - a missing export row;
  - a missing required stage;
  - a wrong serial denominator;
  - a torn row, a duplicate row, a timed-out row;
  - an unmapped field;
  - a missing report;
  - a wrong public score.

  A changed source is caught by the checker (R3).

## R3: provenance and the oracle-free replay

**Checker (`research/efficiency_checker.py`).** It runs the historical checker
unchanged in its own process and keeps its **complete** finding list: 420
`ORACLE_LEAK` and 1 `FROZEN_SOURCE_CHANGED`. The historical checker's own report
lists only 200. Its FAIL stands and is not rewritten.

Each finding is matched against two dispositions, exactly on code, detail and
count, and all of the stated evidence must hold now:

- **D1 (`next_round_analysis.py`).** Approved. The evidence:
  - the at-freeze snapshot hashes `a5ba2988…`, which equals the freeze's
    `reporting` hash;
  - the live file hashes `b6b69684…`, as disclosed;
  - the only AST difference is one `if value is None: continue` in
    `per_program_median`;
  - the affected fields are the unbudgeted controls' cost entries only;
  - the successor auditor reproduces the primary and candidate estimates.
- **D2 (`ORACLE_LEAK` ×420).** Approved. The finding keys equal the 420
  `L_orderings` keys, the guarded replay passes 420/420, and the replay rows and
  the extraction hash are unchanged.

Anything else is `UNAPPROVED`, including a changed pre-existing source or
historical result, since both are checked against this phase's starting
manifests. Result: `PASS_WITH_APPROVED_HISTORICAL_DEVIATIONS`, 0 unapproved.

The 9 checker tests confirm the approval is narrow. Each of these makes the
checker fail:

- an unknown code;
- 419 leaks instead of 420;
- the same code on another file;
- a replay rows hash that changed;
- a stale extraction;
- a failed audit;
- a wider analysis change, or a second None-skip;
- a planted source hash.

**Oracle-free boundary (`research/efficiency_ranker.py`).** It holds the 13
definitions that `next_round_ranker.order` executes, extracted from their owners:
`stable_seed`, `elite_threshold`, `labels`, `_gini`, `Leaf`, `SchemaTree`,
`fit_tree`, `shuffled_labels`, `order_pool`, `ordering_digest`, `seeds`,
`training_labels` and `order`.

- Each is AST-identical to its owner once qualified owner names are renamed.
  The per-function hashes are in `ranker_replay/PROVENANCE_HASHES.json`.
- Its only imports are the standard library and `schema_index`, which itself
  imports only the standard library.
- On all 420 retained inputs, in-process, it returns what the owner returns.

**Guarded replay (`research/efficiency_replay.py`).**

- The minimal workspace holds exactly `efficiency_ranker.py`, `schema_index.py`
  (byte copies), a guard, and hash-checked copies of the 30 `RANKER_INPUT.json`
  files. No `EVALUATOR.json` is copied.
- Each replay is a fresh `python -I -S` process. It refuses any import that is
  neither standard library nor one of the two modules, and any `open` that is
  neither code nor the declared input. Code opens and ranker-input opens are
  recorded separately.
- Two planted violations are both refused (`GUARD_CONTROLS.json`): importing
  `research.structural_oracle`, and opening an `EVALUATOR.json`.
- All 420 inputs were replayed **once**. Every ordered index list, ordering
  digest and model description equals its original row. Each process read
  exactly its one declared input. The only non-standard-library modules loaded
  were `__main__`, `efficiency_ranker` and `schema_index`.
- The original rows remain the evidence of record. This replay verifies
  isolation only and is not a fresh statistical confirmation. The successor
  auditor recounts the learning outcomes independently; the gates remain
  negative.
- **Disclosure: harness predicate bug in attempt 1.** The run's pass predicate
  matched oracle markers as substrings, so the standard library's
  `importlib.machinery` matched `machine` and `REPLAY_REPORT.json` records
  `passed: 0`. The replays were not repeated. `REPLAY_EVALUATION.json`
  re-evaluates the retained rows with the corrected, component-exact predicate
  (`--evaluate` never re-executes) and gives 420/420. Both reports are kept.

## R4: the learner

See `LEARNER_CLOSURE.md`. In summary:

- exact product bounds at full leaves (4,213 leaves checked);
- strict-improvement-only observations;
- `stop_on_improvement`;
- query-local learners, disposed of with each epoch;
- one observation through the half-time exception.

Together these give at most 1 observation at the first model preparation, under a
constant clock and under stepping clocks alike. The architecture is retired, and
0/100 stays historical only.

## R exit

| Criterion | Result |
|---|---|
| New tests, live tree (`r0_checks/efficiency_suite_live.log`) | **93 OK**, 424 s |
| Inherited semantic tests explicitly on R0 (`test_efficiency_inherited.py`; `nrs`/`ois` rebound to R0; applicable and excluded classes declared, with reasons) | 38 OK (inside the 93) |
| Full suite, live tree, after all instruments (`r0_checks/full_suite_live_tree.log`) | **536 OK** (443 inherited + 93 new), 1,181 s |
| Inherited suite in the verified original-source view (`r0_checks/inherited_suite_snapshot.log`; 74/74 files hash-equal to the starting manifest, no `efficiency_*` file) | 443 run: **442 OK, 1 FAIL** (see below) |
| Standalone R0 export, isolated CLI acceptance (`r0_export/acceptance/ACCEPTANCE.json`) | **PASS: 142 programs / 277 cases.** Fresh process per program, empty PYTHONPATH, 20 s timeout, inputs unchanged, workspace = compiler + pinned machine, score, tests and inputs; pinned public tests and score exit 0; deterministic regeneration |
| Unchanged public tests (`r0_checks/public_tests.log`) | 11 OK |
| Immutable sources and historical results (checker) | 0 changed, against the starting manifests (109 sources, 877 result files) |

The one failure is
`test_phase2_repair.R3DependencyGate.test_a_real_resumed_run_retains_checker_resolvable_transitive_links`,
and it fails **only in the snapshot view**. It passes on its own in the live tree,
fails deterministically in the snapshot, and passes in the 536-test live run
(`r0_checks/snapshot_failure_rerun_*.log`). It compares the hash of a fresh
evidence-checker report with the report that authorised an import. That checker
runs in a repository-shaped snapshot whose `.git` is an empty directory and whose
entries are symlinks. It is not an efficiency file and not an assurance defect;
it is recorded here, not waived.

**R0 is frozen**, with its exporter and instruments: `R0_FREEZE.json` holds the
hashes of 15 source and test files and the R0 export `74c87b69…`.
