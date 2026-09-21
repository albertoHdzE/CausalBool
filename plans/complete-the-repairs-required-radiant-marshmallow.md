# Repair plan — Luminal direct-index compiler, findings R1–R9

## Context

The independent lead review of commit `2ab4fa8`
([REVIEW.md](../luminal-challenge/results/direct_index_v1/REVIEW.md)) returned
**CHANGES_REQUIRED** with nine findings. The review found no mathematical
counterexample in the cube algebra or the comparison covers, and it confirmed
the public scores recompute correctly. What it found instead is that the
**release gates do not gate**: a query/validator disagreement can pass, a
worse-than-baseline score can pass, and two of the independent tests can pass
without testing anything. The lead demonstrated three of these with runnable
probes in `results/direct_index_v1/lead_review/audit.py`.

The purpose of this work is therefore not to make the compiler faster or score
better. It is to make the evidence trustworthy: every finding gets a regression
that **fails on the reviewed behaviour and passes after repair**, and the
release path must reject the defects the lead injected.

Plan version **1.1** already approves the comparator split order that is
implemented, so that is documentation work, not an algorithm change.

## Starting state

- Revision `2ab4fa8` on branch `luminal-direct-index`; working tree has
  uncommitted 0xPARC/README edits (unrelated — leave untouched) plus the lead's
  `REVIEW.md`, `lead_review/`, and the v1.1 plan/STATUS updates.
- Protected and unchanged: `.reference/**`, `common.py`, `reference.json`,
  `results/comparison.json`, `GOVERNANCE/GLOSSARY.md`, everything under
  `results/direct_index_v1/`.
- New evidence goes to **`results/direct_index_v2_repair/`**. Nothing under
  `direct_index_v1/` is overwritten.
- Current: 147 direct tests across 7 modules; 142-program corpus; export 2,104
  lines, SHA256 `f31ac937…`.

## Step 0 — shared diagnostics contract (do first, everything else depends on it)

`direct_optimizer.optimise` currently reports `validation_errors` only. Extend
the record, once, before touching the runners:

```
"target_discrepancies": [ {window, target, actual_cycles, actual_memory, reason} ],
"validation_errors":    [ {window, target, error} ],
"discrepancy_count":    int,     # sum of both
```

`direct_compiler.compile_with_report` surfaces the same under
`report["optimisation"]`, and adds a top-level `report["discrepancy_count"]` so
a runner need not know the nesting. `compile_program` keeps its exact official
shape and stays a thin wrapper — R7 requires each compilation be **measured
once**, so runners call `compile_with_report` and use its compilation.

## Repairs

| # | Files | Repair | Regression that must fail first |
|---|---|---|---|
| R1 | `direct_optimizer.py`, `direct_compiler.py`, `verify_direct.py`, `compare_direct.py` | After independent validation, check `actual_cycles <= target_cycles` **and** `actual_memory <= target_memory`; record any breach as a target discrepancy. Runners consume diagnostics from the measured compilation and exit nonzero on any discrepancy. | Patch `JointQuery.decode` to return the unchanged incumbent (the lead's probe): must produce ≥1 target discrepancy and a **nonzero release-gate exit**, where today it yields 4 SAT / 0 errors. Second case: a machine-invalid witness must fail the same gate. |
| R2 | `compare_direct.py` | Gate on: all expected runs present, all metrics positive integers, and direct combined score **> 1.0 in every repetition**. Exit status and report wording both generated from the evaluated gates, never asserted unconditionally. | Synthetic complete results at exactly 1.0 and below 1.0 must fail; a missing repetition must fail; the real results must pass. |
| R3 | `tests_direct/test_constraints.py` | Delete the `assertTrue(True)` branch. On `Infeasible`, still derive the domains independently and assert **no** oracle-valid assignment exists. Compare acceptance pointwise against machine+target, existentially quantifying lanes. Decode and machine-validate *every* filling of small schemata. Add vector alignment/overlap and ordered memory-aliasing fixtures. | Patching `JointQuery.expression` to raise `Infeasible` unconditionally must make the test **fail** (today it passes). |
| R4 | `schema_index.py`, `direct_constraints.py` | Enforce cover/record caps **while growing**, not after normalising: check in the `relation_cover` accumulation loop, give `normalise_cover` a deadline check, and validate incoming `Leaf` cover sizes inside `solve`. Exhaustion stays UNKNOWN. | `solve(Leaf(16 singletons), 4, Budget(max_cover=1))` must return UNKNOWN (today SAT). A 10-bit comparison under `max_cover=4` must stop early rather than visiting 5,115 cubes; `max_records=1` must stop before 255 accepted cubes. |
| R5 | `verify_direct.py`, `tests_direct/test_export.py` | Replace the single 900 s corpus process with **one fresh isolated process per input**, each under the external 20 s limit, reusing the lead's proven pattern (`python3 -I -S`, temp directory holding only `compiler.py` and `machine.py`). Retain per-input hash, exit code, timing, case count, diagnostics. | A forced timeout on one input must fail overall **while retaining the other 141 records**. |
| R6 | `tests_direct/test_optimizer.py` | Freeze the program from `additional_program(2112)` **literally** (10 operations) as a new fixture — not by seed, and not added to the 142-corpus. Verified: bootstrap C=6 S=24 P=144 → accepted C=7 S=16 P=112. Cycles **worsen**, product improves, official score 1.970265 → 2.234071, validated on both cases. Establish the alternatives by independent bounded enumeration and recompute the score from actual before/after integers. | A test asserting an accepted improvement with a worsened measured metric fails today (zero such improvements exist in the current corpus). |
| R7 | `compare_direct.py`, `tests_direct/test_independence.py` | Direct arm runs in a neutral temp directory under `-I -S` with only the export and pinned `machine.py`; assert the loaded `compiler.__file__` and its hash. Compare on-disk export against a fresh `export_direct.assemble()` and fail on drift. Enforce the four plan-§2 protected hashes and the classical arm's historical integer metrics. Record query outcomes, budgets, discrepancies, and construction-vs-optimisation contribution per measured compilation. Exercise a **successful** optimisation through the export with `serial_compile` blocked. | Stale export vs current sources must fail; a mutated protected hash must fail; the guarded-optimisation test must run against the export, not the development module. |
| R8 | `direct_optimizer.py` | `windows_for`: generate starts `range(0, count, 2)`, truncate each at `count`, then stable-deduplicate. Restores the final shorter window. | For 6 operations, expect exactly `(0,1,2,3), (2,3,4,5), (4,5)`; today `(4,5)` is missing. Test even and odd counts, and a case where priority windows do not mask the tail. |
| R9 | `verify_direct.py`, `SUBMISSION.md`, `direct_constraints.py` docstring | Require **exactly 11** public tests; catch the suite timeout into a fresh failure record; write an `IN_PROGRESS` summary at start so an aborted run cannot leave a stale PASS. Fix the stale comparator docstring to the v1.1 significance order. | Documentation-only parts need no artificial test; the "exactly 11" and abort-handling parts do. |

### SUBMISSION.md corrections required by R9

Each of these is currently overstated and must be replaced with what the
evidence supports:

- "a query that cannot finish is a compilation failure" — true for the
  bootstrap only; optimiser UNKNOWN **preserves a validated incumbent**.
- "4 stress fixtures that fill the scratchpad exactly" — only three reach 256
  words; `stress_memory_chain` does not.
- "no list scheduler / no first-fit allocator" — the policies *are* earliest-
  feasible-cycle and lowest-legal-address, i.e. familiar greedy policies, whose
  decisions are made by schema queries. Claim the implementation, not a
  categorical distinction.
- "That is the evidence that the harness itself is sound" — reproducing
  historical metrics is one control, not proof of harness soundness.
- "the per-query search budget, not the method, limits the optimiser's reach" —
  unsupported; window size, target selection and representation cost also bind.
- Review status: record **CHANGES_REQUIRED** and this repair round.

## Evidence layout

```
results/direct_index_v2_repair/
  verification/   summary.json, logs/, corpus_manifest.json, isolated_corpus.json
  comparison/     runs.json, COMPARISON.md
  injected/       results of each injected-failure test
  REPAIR_HANDOFF.md
```

## Final acceptance matrix

Run from `luminal-challenge`, retaining command, exit code, output and hashes:

1. `PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'`
2. `PYTHONPATH=.reference python3 export_direct.py --output .build/direct_index/compiler.py`
3. `PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v2_repair/verification`
4. 142 corpus inputs, one fresh isolated 20 s process each (inside stage 3)
5. Exactly 11 unchanged public tests against the export
6. `PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v2_repair/comparison`
7. Independent score recomputation from all 72 raw measurements
8. Protected-hash / export-freshness checks
9. Injected-failure suite: target discrepancy, invalid candidate, score ≤ 1.0,
   missing measurement, timeout — each must produce a nonzero exit

Performance evidence is **regenerated**, not reused: R4 and R8 change schema
budgets and window policy, which the rerun matrix says invalidates prior
performance numbers.

## Verification

Order: Step 0 → R4/R3 (schema and constraints) → R1/R8/R6 (optimiser) →
R2/R5/R7/R9 (release tooling), running each finding's regression against the
**unrepaired** code first to confirm it fails, then after the repair.

End-to-end: re-run the lead's own probes
(`python3 results/direct_index_v1/lead_review/audit.py probes`) and confirm all
three reproduce as *failures* now — the silent target discrepancy, the vacuous
infeasibility test, and the oversized atomic cover.

## Handoff

`results/direct_index_v2_repair/REPAIR_HANDOFF.md` with one row per R1–R9
(resolution, files, regression, command, result, evidence path), start and end
revisions, tested source/export hashes, full acceptance results, independently
recomputed scores, runtime and query outcomes, construction-vs-optimisation
contributions, every remaining limitation, and the exact commands for the lead
to rerun.

`STATUS.md` gains a new repair round section; historical records are not
rewritten. Repaired tasks move to **READY_FOR_REVIEW** — never ACCEPTED. No
push, no submission. No claim of final acceptance, private-grader success,
global optimality, or general complexity advantage.
