# Readiness matrix: Phase 2 next round 1.0

Each plan requirement, where its evidence is, and its state. "Done" means the
evidence exists and was checked. It does not mean the lead has accepted it.

## Stage R (plan §3)

| Requirement | Evidence | State |
|---|---|---|
| R1 reproduced on frozen source with the lead probe | `repair/PROBE_objective_index_search.json` | done |
| Versioned successor, frozen owner retained, minimal diff, hash recorded | `research/next_round_search.py`, `repair/source/` | done |
| Totals, affected-query count, per-query counts, construction separate | record fields; `REPAIR.md` | done |
| All interruption scenarios and zero-interruption controls | `test_next_round_search.py::InterruptionAccounting` | 9/9 |
| Regression fails on frozen, passes on successor | `repair/REGRESSION_POWER.json` | done |
| No late acceptance; same decisions at equal work | `DecisionParityWithFrozenOwner` | pass |
| 392 inherited plus new tests | `final_checks/all_research_tests.log` | see handoff |
| Standalone acceptance, 142 programs, and unchanged public tests | `repair/acceptance/`, `repair/production/` | PASS |
| Historical checker in a verified snapshot | `repair/historical_checkers/` | reconciled (`REPAIR.md`) |
| Reference-path review | `REPAIR.md` | no finding |
| Empty `attempted_queries` fixed in the new report owner | `next_round_report` never assumes the field; the post-freeze crash was a different field (`POST_FREEZE_CHANGES.json`) | done, with disclosure |

## Stage D (plan §4)

| Requirement | Evidence | State |
|---|---|---|
| 2×2 cells in the successor; 1/1 equals repaired A4 | `next_round_search.py` (`catalog`, `traversal`); parity tests | done |
| Stack/heap UNKNOWN when more than 4,096 prefixes are queued | frontier tests | done |
| Exhaustive agreement, resumed vs uninterrupted prefixes | `TraversalExhaustiveAgreement`, `AblationController` | pass |
| 4,500 rows, all costs, bootstrap/optimisation/compile/process kept separate | `stages/D_factorial/` | 4,500/4,500, 0 failed |
| Profiling on first two seeds per family, never during timing | `stages/D_profile/`, `BOTTLENECKS.md/.json` | 150 rows |
| 1%/5% targets with censoring, every row in the denominator | `FACTORIAL.json` `targets` | done (the earlier optimizer has attainment only) |
| Fixed-work: 1,000/10,000/50,000 nodes, 120 rows | `stages/D_fixed_work/`, `FACTORIAL.md` | 120/120 |
| Factorial effects with family breakdown | `FACTORIAL.json/.md` | done |

## Stage E (plan §5)

| Requirement | Evidence | State |
|---|---|---|
| Selection rule at 0.1 s | `SELECTION.json` | `cell_a4cat_dfs` |
| Mechanism and expected saving written before measurement | `ENGINEERING_PLAN.json` | done |
| Parity (candidate sequence, pruning, incumbent) | `test_next_round_engineered.py` (6) | pass |
| ≤900 rows | `stages/E_engineering/` | 900/900 |
| Freeze rule | `ENGINEERING_DECISION.json` | variant 4.8% faster, below the 10% gate; parent frozen |

## Stage C (plan §6)

| Requirement | Evidence | State |
|---|---|---|
| Freeze before any outcome (sources, controls, export, reporters, checker/auditor, ledgers) | `FROZEN_SELECTION.json`, `frozen_expected/`, `SOURCE_MANIFESTS/frozen/` | done |
| Fresh cohort 960000–960199, semantic disjointness, no exposure | `CONFIRMATION_COHORT.json` | PASS, 0 collisions |
| K = 3 arms × 3 budgets × 5 repetitions, plus classical and bootstrap | `stages/C_confirmation/` | 11,000/11,000 |
| Public, including serial | `stages/C_public/` | 480/480 |
| Primary and four candidate endpoints | `COMPARISON.json/.md` | FAVOURS_A4; TARGET_NOT_REACHED |
| Exact public score, reconciled | `PUBLIC_SCORE.json/.md` | done |
| Export, 624 rows, isolated | `export/candidate/EXPORT_VALIDATION.json` | PASS |

## Stage L (plan §7)

| Requirement | Evidence | State |
|---|---|---|
| Development sensitivity: ≥10/15 informative, every family | `learning/DESIGN_DEVELOPMENT.json` | 15/15 PASS |
| Fresh fixtures by the unchanged recipe, pool 970000–970399 | `learning/fixtures/evaluation/` | 30 (6/family), 0 collisions |
| Evaluation sensitivity: ≥20/30, ≥3 per family | `learning/DESIGN_EVALUATION.json` | 30/30 PASS |
| Pool and permutations frozen before evaluation | `LEARNING_FREEZE.json` | done |
| 14 orderings × 30 fixtures = 420 | `stages/L_orderings/` | 420/420 |
| Three contrasts, 98.333% intervals | `LEARNING_FEASIBILITY.json/.md` | FAIL_OR_INCONCLUSIVE |
| 100 acquisition runs, repaired controller, no oracle training | `stages/L_acquisition/` | 0/100 → ECONOMICALLY_UNAVAILABLE |
| Oracle labels stay in the evaluator | `final_checks/ranker_file_audit/RANKER_FILE_AUDIT.json` | only RANKER_INPUT files opened |

## Evidence and stop rules (plan §8)

| Requirement | Evidence | State |
|---|---|---|
| Rows carry command, hashes, timings, identity, stdout hash, stderr tail, exit | `stages/*/{rows,commands}.jsonl` | done |
| Immutable stage manifests, resume under identical hashes only | `stages/*/STAGE_MANIFEST.json`, `resume_log.jsonl` | done |
| Independent numerical audit, no experiment imports | `INDEPENDENT_AUDIT.json` | PASS, 52,013 checks |
| Checker | `CHECKER_REPORT.json` | 2 finding classes, both explained in the handoff |
| 24 h cap, checked before each launch | `MEASUREMENT_WALL_LEDGER.jsonl` | 0.598 h over 18,294 rows |
| No commits, pushes, agents, production or manuscript edits | `SOURCE_MANIFESTS/{starting,final}` | git status unchanged |
