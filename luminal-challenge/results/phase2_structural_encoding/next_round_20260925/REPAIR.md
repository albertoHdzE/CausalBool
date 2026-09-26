# Stage R: interruption-accounting repair and correctness review

Protocol `luminal-phase2-next-round-1.0`, plan section 3. Implementer: Claude Code,
2026-09-25. Not self-accepted.

## What was wrong (R1, reproduced before any edit)

`research/objective_index_search.py` (sha256 `8cda157f…c4c7f5`, frozen, unchanged)
counted a query's interrupted candidate validations only inside
`if query.learner is not None` in `multiscale_optimise.finish`. The non-model A4
therefore returned zero. The lead's probe function, imported read-only (its
`PROBES.json` is not rewritten), on generated program 800004:

| Source | internal count | returned count | accepted | statuses |
|---|---:|---:|---:|---|
| frozen `objective_index_search.py` | 1 | **0** | 0 | 9 × UNKNOWN_DEADLINE |
| successor `next_round_search.py` | 1 | **1** | 0 | 9 × UNKNOWN_DEADLINE |

Files: `repair/PROBE_objective_index_search.json`, `repair/PROBE_next_round_search.json`,
driver `repair/run_lead_probe.py`. The first runs are kept in `repair/superseded/`
(the driver gained `create=True` for the successor afterwards; results unchanged).

## The successor

`research/next_round_search.py`, `VERSION = "next_round_search 1.1"`, sha256
`b982d4cf…c9647`, is a copy of the frozen owner that records the frozen hash
(`FROZEN_SOURCE_SHA256`) and lists its changes in the header. Diff:
`repair/source/next_round_search.diff` (183 changed lines, of which the ablation
parameters are most). Snapshots of both files are in `repair/source/`.

- **R1 (repair).** Interrupted validations are accounted for every query. New,
  unambiguous names in the record: `interrupted_validation_total` (validations),
  `interrupted_validation_queries` (affected queries),
  `interrupted_validations_per_query` (query, epoch, window, policy, status, count),
  and separately `construction_interruption_count` / `construction_interruptions`
  (allowance consumed by construction before any node, or no time at
  initialisation). Each query summary also carries its own
  `interrupted_validations` and `construction_interrupted`.
- **R2 (reporting).** Each accepted improvement carries `elapsed_seconds`, read
  from the last clock reading (no extra reading, so a deterministic test clock
  advances exactly as for the frozen owner).
- **D (ablation, section 4).** `catalog` ∈ {`a4`, `a3`} and `traversal` ∈ {`heap`,
  `dfs`}; defaults are the repaired A4.
- An optional `timers` argument (Stage L economics only) times construction;
  `None` adds no clock reading.

Historical measurements keep describing their own source; no hash was refreshed,
and missing historical interruption counts remain unknown, not zero.

## Requirement-to-evidence table

| Requirement (plan §3) | Evidence | Result |
|---|---|---|
| Reproduce R1 on frozen source | `repair/PROBE_objective_index_search.json` | defect reproduced |
| Accounting outside the learner branch; totals and affected-query count, per-query counts; construction kept separate | `research/next_round_search.py` `finish()`, record fields above | done |
| Before-validation expiry, during-validation expiry, no-learner and learner paths, query vs global deadline, multiple interruptions, zero-interruption controls | `research_tests/test_next_round_search.py::InterruptionAccounting` (9 tests) | 9/9 pass on successor |
| Regression fails on frozen, passes on successor | `repair/REGRESSION_POWER.json` (same class, module swapped) | frozen 5 failures + 4 errors of 9; successor 0 of 9 |
| No late incumbent acceptance; unchanged results and statuses under deterministic clock at equal work | `DecisionParityWithFrozenOwner` (13 programs × 2 regimes: identical traces, incumbents, statuses, aggregates, certificate streams; 3 interruption scenarios: identical decisions) | pass; >10,000 pops compared |
| 1/1 cell equals repaired A4 | same test (default cell = frozen owner statement for statement) | pass |
| Exhaustive object-set / minimum agreement for both traversals | `TraversalExhaustiveAgreement` (original + 10 recipe fixtures, every threshold, oracle vs stack vs heap) | pass |
| Stack is canonical depth-first, low rank first | recursive reference vs `dfs_enumerate` pop order, >1,000 nodes | pass |
| Resumed vs uninterrupted prefixes, both traversals, both catalogs | `AblationController::test_resumed_prefixes_equal_uninterrupted_for_every_cell` (50 programs per cell) | pass |
| Frontier >4,096 is UNKNOWN, never UNSAT, for the stack | `test_frontier_limit_is_unknown_never_unsat_for_the_stack` | pass |
| Aggregate ceilings, validator rejections, validated incumbents no worse than bootstrap for every cell | `AblationController` (4 tests; 20 programs × 4 cells incl. 8 public) | pass |
| 392 inherited research tests plus new tests | `repair/tests/current_tree_all_tests.log`: 414 tests OK, 631 s (392 + 22 new); final pre-freeze run in `prefreeze_checks/` | OK |
| Standalone acceptance on the 142-program corpus | `repair/acceptance/*.json`: 142 programs, 277 cases, 0 failures for all four cells and the engineered variant | PASS ×5 |
| Unchanged public tests | `repair/production/public_tests.*` (11 tests OK); pinned tests again inside the export check | OK |
| Canonical direct verification | `repair/production/verify_direct_all.*` (`--stage all`, exit 0, status PASS) | PASS |
| Historical checker in a verified original-source snapshot | `repair/historical_checkers/` (see below) | reconciled |
| Reused semantic tests against the successor; new checker on its manifest | `test_next_round_*.py`; `next_round_checker` on this run | pass |
| Review both reference paths for hidden fallback, isolation and validator bypass | below | no finding |

## Historical checkers and which source each suite exercises

- The frozen objective-index checker on the **live tree** reports exactly 11
  `POST_FREEZE_SOURCE_ADDED` findings, one per new `next_round_*` research or
  test file (`historical_checkers/objective_checker_current_tree.json`). It
  deliberately rejects added modules; it was not weakened.
- In a **verified original-source snapshot** (`historical_checkers/make_snapshot.py`,
  `SNAPSHOT_VERIFICATION.json`: 55/55 research and test files hash-equal to the
  starting manifest, every `next_round_*` file excluded) the same checker reports
  only 41,040 `NEW_ARM_WRONG_SOURCE`: exactly the 41,040 new-arm rows whose recorded
  import path is the live tree. That check compares absolute paths, so a relocated
  snapshot cannot pass it. The two views partition the findings exactly; every
  other check passes in both. The frozen numerical auditor passes in the snapshot
  (163,281 checks, 0 findings), and the historical evidence tests pass there
  (`snapshot_evidence_tests.log`: 116 tests OK). The earlier release's checker
  passes on the live tree.
- Historical tests exercise the **frozen** sources. The successor is exercised
  only by `test_next_round_search.py`, `test_next_round_engineered.py`,
  `test_next_round_learning.py` and `test_next_round_evidence.py`; passing
  historical tests alone does not test the successor.

## Reference-path review

- **Earlier `cap512_wider`.** Measured by the unchanged `research.optimization_worker`
  calling `optimization_search.optimise(config="cap512_wider", build="cached",
  search_arm="structural_bound")`; `optimization_search.py` hashes `296ecd2d…`,
  equal to its release freeze; the isolation probe
  (`isolation/probe_*.json`) confirms the worker loads the current tree's module
  with that hash. Candidates are validated by `machine.check_compilation` and
  every `check_case` inside `structural_search`; the worker re-validates the
  final compilation on every case.
- **Repaired A4 and the other cells.** Measured by `research.next_round_worker`,
  which imports only the successor (probe: `research.objective_index_search` not
  loaded). Acceptance validates every candidate before it can become incumbent;
  the worker re-validates the output.
- **Fallback.** No candidate path in `next_round_search.py`,
  `optimization_search.py` or `structural_search.py` references classical,
  serial, BDD or SAT code (grep in this review); classical, serial and the
  accepted bootstrap run only as controls in the frozen workspace.
