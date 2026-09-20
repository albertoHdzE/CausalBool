# Repair handoff — findings F1, F2, F3

Date: 2026-09-20. **Status: READY_FOR_REVIEW. Nothing here is accepted.**

Repairs the three remaining findings of the lead re-review
([direct_index_v2_repair/REVIEW.md](../direct_index_v2_repair/REVIEW.md), verdict
CHANGES_REQUIRED) of commit `f3391b6`, which closed six of the original nine and
left R2, R4 and R7 partial. All previous evidence, including both `lead_review`
directories, is untouched.

All three findings were about safeguards that were absent rather than results
that were wrong: a duplicated measurement could hide a missing one, frozen
integers could move while their product held, and an expression could exceed its
record cap before anyone checked. Each is now rejected, and each rejection is
pinned by a durable regression driven through the real release path.

## State

| | |
|---|---|
| Starting revision | `f3391b6`, plan version 1.1 |
| Export | 2,255 lines, SHA256 `e30a1ed8090be9b4…` (full value in the verification summary) |
| Protected controls | four plan §2 hashes verified unchanged before any measurement |
| Unrelated work | 0xPARC and README edits untouched |

Changed source (first 16): `schema_index.py` `5f934d2d7820bbb5`,
`direct_constraints.py` `7d34dbbddd3a2237`, `compare_direct.py`
`a0eb3c66317ccb8f`. Unchanged: `verify_direct.py` `2e84c2a2a92af0bf`,
`direct_optimizer.py` `bdbc0dd71b785d28`, `direct_compiler.py`
`4b0c531d1d060af2`.

## Findings

| # | Resolution | Files | Regression | Result |
|---|---|---|---|---|
| **F1** | Membership is now exact rather than counted. `run_all` verifies each worker response's arm and program against the invocation before the parent stamps a repetition on it, and retains a failure record on mismatch. `all_runs_present` requires precisely one record for every `(arm, program, repetition)` over the eight pinned program names, rejecting duplicates, omissions, unexpected identities and out-of-range repetitions. The classical control additionally requires exactly the expected repetition IDs. | `compare_direct.py` | `ComparisonMembershipTests`, replaying recorded responses through the real `run_all`; plus a CLI test | Duplicate scenario now `all_passed=False` (was `True`); foreign-arm response rejected and retained; **CLI exits nonzero** |
| **F2** | Per-program serial and classical cycles and scratch are read from the already-protected `results/comparison.json` and compared against every measured repetition. Either integer changing is rejected even when the product, and therefore every ratio, is unchanged. The aggregate check is kept as an additional control, not a replacement. | `compare_direct.py` | `test_a_product_preserving_metric_drift_is_rejected`, `test_a_serial_metric_drift_is_rejected` | Product-preserving drift now `all_passed=False` (was `True`), with the aggregate gate still passing — which is exactly why the aggregate was not enough |
| **F3** | Expression nodes are charged as they are built, so construction stops instead of returning an over-cap expression. `solve` bills an expression once via `Meter.charge_expression`, so construction and search no longer double-count. The simplified constant and identical-field returns check the clock and charge their result. | `schema_index.py`, `direct_constraints.py` | `ConstructionBudgetTests` (9 tests), `IncomingExpressionBudgetTests` (5 tests) | See the table below |

### F3 measured before and after

| Scenario | Reviewed | Now |
|---|---|---|
| Construction under `max_records=533` | returned an expression of **554** records | **stops at 534**, raising rather than returning |
| Meter against expression, generous cap | meter 533, expression 554 | **554 and 554**, exactly equal |
| Same meter through `solve` | 533 → **1,087** (double-billed) | 554 → **554**, billed once |
| `relation_cover` on an expired meter, constants | returned a cube, recorded **0** work | **raises**, time budget exhausted |
| Same, identical fields | returned a cube | **raises** |
| Externally supplied expression | — | still billed and still able to exhaust |

The lead's `budget_probes.py` now exits nonzero: it was written to demonstrate
construction returning an over-cap expression, and construction now refuses to.
The transcript is retained at
[injected/budget_probe_now_refuses.txt](injected/budget_probe_now_refuses.txt).

The lead's note that `RelationBudgetTests` only asserted eventual exceptions is
addressed: the new tests assert **when** the stop happens. Under `max_cover=4` a
ten-bit comparison must halt with fewer than 100 visited cubes, and under
`max_records=1` with at most 2 records charged.

## Acceptance results

All commands from `luminal-challenge`, all exit 0.

| Command | Result |
|---|---|
| `python3 -m unittest discover -s tests_direct -p 'test_*.py'` | **189 tests OK** (was 168) |
| `export_direct.py` | 2,255 lines |
| `verify_direct.py --stage all --timeout 20` | **PASS**, 200 tests, 0 failing |
| `compare_direct.py --repeats 3 --timeout 20` | 72 runs, **all seven gates PASS** |

Stages: schema 39, contract 31, constraints 32, construction 19, optimizer 22,
independence 13, export 33 — **189 direct tests** — plus 142 programs / 277 cases
in 142 fresh isolated processes, the unchanged public suite at exactly 11, and
the documented command line on all eight public programs. Slowest isolated
process **1.190 s** against the 20 s limit.

Gates, all passing: `all_runs_present`, **`frozen_integer_metrics`** (new, 48
baseline measurements checked against historical per-program integers),
`metrics_valid`, `direct_beats_baseline`, `frozen_classical_control`,
`no_candidate_discrepancies`, `direct_arm_isolated`.

### Independently recomputed scores

From all 72 raw integer measurements, identical in every repetition:

| Arm | Combined score | Median compile |
|---|---:|---:|
| serial | 1.0000000000000000 | — |
| classical | 1.9013791212645499 | 0.265 ms |
| direct index | 2.0084662022846573 | 430.5 ms |

Largest whole-process time 0.69 s. The direct compiler is about **1,625 times
slower** to run by these medians.

### Effect of the budget change on search

The lead warned that budget accounting changes search outcomes, so this was
remeasured rather than assumed. Over the corpus: SAT 6, UNSAT 198,
UNKNOWN_CONSTRUCTION 9, UNKNOWN_SEARCH 463, INFEASIBLE 3,315 — within noise of
the previous round. Node charges are small against the 20,000 record cap.

**On the 7-versus-6 question:** this round's isolated corpus run accepted
**seven** improvements, where the previous round's accepted six, with the same
code path. That supports the lead's reading over mine: the difference is
run-to-run variation in time-bounded search, not a deterministic consequence of
the R8 window change. My earlier statement attributing the decline to R8 was
wrong, and the handoff for that round should be read with this correction.

## Remaining limitations

- Optimisation outcomes are **not deterministic** across runs, because
  per-query time budgets bound the search. Counts of accepted improvements are
  observations of a run, not properties of the compiler.
- The optimiser still contributes nothing to the public score; all of it comes
  from construction.
- UNSAT remains local to the queried neighbourhood. No global optimality,
  private-grader result, compactness ratio or complexity claim is established.
- `frozen_integer_metrics` covers the serial and classical arms only, since
  only those have pinned history. The direct arm has no historical control by
  construction, and is governed by the score and discrepancy gates instead.
- The pointwise predicate-versus-machine comparison still runs only where a
  domain has at most 512 assignments.

## Commands for the lead to rerun

```sh
cd luminal-challenge

# the lead's own probes: F1/F2 must report all_passed=False, F3 must exit nonzero
PYTHONPATH=.reference python3 results/direct_index_v2_repair/lead_review/gate_probes.py
PYTHONPATH=.reference:. python3 results/direct_index_v2_repair/lead_review/budget_probes.py

PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference:. python3 verify_direct.py --stage all --timeout 20 \
    --output results/direct_index_v3_repair/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
    --output results/direct_index_v3_repair/comparison
```

Both probe scripts write into `results/direct_index_v2_repair/lead_review/`.
Their outputs were backed up and restored byte-identically here; the observed
results are copied to [injected/](injected/).

Evidence: [verification](verification/summary.json),
[isolated corpus](verification/isolated_corpus.json),
[comparison and gates](comparison/runs.json),
[comparison report](comparison/COMPARISON.md),
[probe observations after repair](injected/).
