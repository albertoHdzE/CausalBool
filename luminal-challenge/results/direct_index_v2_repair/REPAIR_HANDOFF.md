# Repair handoff — findings R1 to R9

Date: 2026-09-20. **Status: READY_FOR_REVIEW. Nothing here is accepted.**

Repairs the nine findings of the independent lead review
([REVIEW.md](../direct_index_v1/REVIEW.md), verdict CHANGES_REQUIRED) of commit
`2ab4fa8`. The lead's evidence in `results/direct_index_v1/` is untouched; all
new evidence is in this directory.

The review's central charge was that the release gates did not gate. That is
what this round is about: every finding now has a regression that **fails on the
reviewed behaviour and passes after repair**, and each gate is exercised by an
injected defect and required to reject it.

## Starting and final state

| | |
|---|---|
| Starting revision | `2ab4fa8`, plan version 1.1 |
| Final state | working tree on `luminal-direct-index`, committed below |
| Export | `.build/direct_index/compiler.py`, 2,184 lines, SHA256 `33386bc6ecc2dd82a1787cef9a0c04c369a7aacbbaf9e763a0313356653a376e` |
| Protected controls | all four plan §2 hashes verified unchanged by `compare_direct.verify_protected()` |
| Unrelated work | 0xPARC and README edits left uncommitted and untouched |

Production source hashes (first 16) at the tested revision:

| File | SHA256 |
|---|---|
| `schema_index.py` | `214db99db0d8a48e` |
| `direct_contract.py` | `3b37ad0e7f5feb8a` (unchanged) |
| `direct_constraints.py` | `fac83796f7325b3f` |
| `direct_optimizer.py` | `bdbc0dd71b785d28` |
| `direct_compiler.py` | `4b0c531d1d060af2` |
| `export_direct.py` | `984ffb653535772b` (unchanged) |
| `verify_direct.py` | `2e84c2a2a92af0bf` |
| `compare_direct.py` | `00f5219d16a99124` |

## Findings

| # | Resolution | Files | Regression | Result |
|---|---|---|---|---|
| **R1** | After independent validation the optimiser now checks `actual_cycles <= target_cycles` and `actual_memory <= target_memory` and records any breach as a `target_discrepancy`. `compile_with_report` surfaces `discrepancy_count` at top level; the isolated corpus runner reads it from the same compilation it measured and fails on it. | `direct_optimizer.py`, `direct_compiler.py`, `verify_direct.py`, `compare_direct.py` | Lead's probe (patched `decode` returning the incumbent); injected target-discrepancy and machine-invalid exports driven through `run_isolated_corpus` | Probe now yields **4 target discrepancies** where it yielded 0; both injections make the corpus gate **FAIL** while retaining every record |
| **R2** | Six gates evaluated in `evaluate_gates`: all runs present, metrics valid, direct score > 1.0 in every repetition, frozen classical control within 1e-9, no discrepancies, no module leaks. Exit status and report wording are both derived from them. | `compare_direct.py` | `ReleaseGateTests` — synthetic complete results at exactly 1.0, below 1.0, a missing repetition, a drifted classical control | Each **fails**; the real results pass all six |
| **R3** | The `assertTrue(True)` branch is gone. Domains are now derived from the plan text, independently of the query object, and enumerated **before** construction is consulted; on `Infeasible` the test asserts the oracle found nothing. Acceptance is compared pointwise against machine plus targets, existentially quantifying lanes. Every filling of a small schema is decoded by plain shifts and validated against the machine. Vector-overlap and ordered-aliasing fixtures added. | `tests_direct/test_constraints.py` | Patch `JointQuery.expression` to raise `Infeasible` unconditionally | Test now **fails**, naming the 6 valid assignments denied (it passed before) |
| **R4** | Caps are enforced while structures grow: `relation_cover` checks the cover cap and charges a record per accepted cube, `normalise_cover` takes a meter and checks the deadline, and `solve` validates every incoming leaf cover before searching. New `Meter.cover_limit` checks a cap without double-charging. | `schema_index.py`, `direct_constraints.py` | Lead's three probes | Oversized atomic cover now **UNKNOWN** (was SAT); 10-bit comparison at `max_cover=4` stops after **40** visited cubes (lead observed 5,115); `max_records=1` stops after **26** (lead observed 255 accepted) |
| **R5** | The single 900 s corpus process is replaced by one fresh `python3 -I -S` process per input, from a neutral directory holding only the export and pinned `machine.py`, each under the external 20 s limit. Per-input hash, exit code, wall time, cases and diagnostics retained. | `verify_direct.py` | Forced timeout on one input via patched `subprocess.run` | Overall **FAIL**, the timed-out input named, and all other records retained |
| **R6** | A program that actually trades a cycle for scratch, frozen literally (10 operations, not by generator seed, and deliberately not added to the 142-corpus). Bootstrap 6 cycles × 24 words = 144; accepted witness 7 × 16 = 112. Cycles **worsen**, product improves, official score 1.970265 → 2.234071, both compilations validated on every case. | `tests_direct/test_optimizer.py` | `test_an_accepted_witness_actually_trades_a_cycle_for_scratch`; plus `test_the_traded_cycle_was_necessary_for_that_footprint`, which exhausts the window's domains and shows footprint 16 is unreachable at 6 cycles | Both pass; no such improvement existed in the corpus before |
| **R7** | Direct arm runs under `-I -S` in a neutral directory; the loaded `compiler.__file__` is asserted. The on-disk export is compared against a fresh `export_direct.assemble()` and a stale one is refused. The four plan §2 protected hashes are enforced. Query outcomes, budgets, discrepancies and bootstrap-versus-final metrics are recorded per measured compilation. A successful optimisation is driven **through the export** with `serial_compile` raising. | `compare_direct.py`, `tests_direct/test_independence.py` | `test_a_stale_export_is_refused`, `test_a_moved_protected_control_is_refused`, `ExportOptimisationTests` | All pass; stale export and moved hash both **refused** |
| **R8** | `windows_for` generates starts `range(0, count, 2)`, truncates each at the operation count, then stable-deduplicates, restoring the final shorter window. | `direct_optimizer.py` | `test_source_windows_for_six_operations_are_exact`, `test_source_windows_keep_the_final_shorter_tail` | For six operations the windows now include `(4, 5)`, which was omitted |
| **R9** | Public suite must report **exactly eleven**; its timeout is caught into a failure record; `summary.json` is claimed as `IN_PROGRESS` before any stage so an aborted rerun cannot leave a stale PASS. Comparator docstring corrected to the v1.1 significance order. `SUBMISSION.md` claims corrected. | `verify_direct.py`, `direct_constraints.py`, `SUBMISSION.md` | `PublicSuiteGateTests` | 10, 12, absent and timed-out counts all **FAIL**; an aborted run leaves no PASS |

### SUBMISSION.md corrections made

- "a query that cannot finish is a compilation failure" — now split: true for
  construction; during optimisation UNKNOWN preserves a validated incumbent.
- "4 stress fixtures that fill the scratchpad exactly" — now three at 256 words;
  `stress_memory_chain` reaches 64 and tests ordering instead.
- "no list scheduler / no first-fit allocator" — replaced. The policies *are*
  earliest-feasible-cycle and lowest-legal-address; the claim is now that every
  decision is taken by an exact query, not that the policy is novel.
- "evidence that the harness itself is sound" — now "one control passing, which
  rules out a class of harness errors".
- "the per-query search budget, not the method, limits the optimiser's reach" —
  replaced; budget, window size, target order and representation cost all bind,
  and the evidence does not isolate one.
- Review status now records CHANGES_REQUIRED and this repair round.

## Acceptance results

All commands run from `luminal-challenge`.

| Command | Exit | Result |
|---|---:|---|
| `PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'` | 0 | **168 tests OK** (was 147) |
| `PYTHONPATH=.reference python3 export_direct.py` | 0 | 2,184 lines, SHA256 `33386bc6…` |
| `PYTHONPATH=.reference:. python3 verify_direct.py --stage all --timeout 20 --output results/direct_index_v2_repair/verification` | 0 | **PASS**, 179 tests, 0 failing, 159 s |
| `PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 --output results/direct_index_v2_repair/comparison` | 0 | 72 runs, 0 failures, **all six gates PASS** |

Verification stages: schema 34, contract 31, constraints 22, construction 19,
optimizer 22, independence 13, export 27 — **168 direct tests** — plus
acceptance: **142 programs / 277 cases** in 142 fresh isolated processes, the
unchanged public suite at **exactly 11**, and the documented command line on all
eight public programs. Maximum isolated process time **1.208 s** against the
20 s limit.

### Independently recomputed scores

Recomputed from all 72 raw measurements, not read from the summary:

| Arm | Combined score, identical in all three repetitions | Median compile |
|---|---:|---:|
| serial | 1.0000000000000000 | 0.022 ms |
| classical | 1.9013791212645499 | 0.271 ms |
| direct index | 2.0084662022846573 | 423.9 ms |

The classical control reproduces its historical aggregate to a difference of
**0.000e+00** with identical integer metrics. Largest whole-process time 0.69 s.
The direct compiler scores about 5.6% above classical and is about **1,560
times slower** to run.

### Compiler runtime and query outcomes

Over the 142-program corpus, from the same compilations that were measured:

| Outcome | Count |
|---|---:|
| SAT, validated and accepted | 6 |
| UNSAT, neighbourhood exhausted | 197 |
| UNKNOWN, construction over budget | 9 |
| UNKNOWN, search over budget | 464 |
| Infeasible as posed | 3,315 |
| **Candidate discrepancies** | **0** |

On the eight public programs: 165 of 218 queries infeasible, 0 SAT. **The entire
public score comes from construction**; joint optimisation contributes nothing
there.

## Remaining limitations and open issues

- **Accepted improvements fell from 7 to 6** across the corpus after R8. Adding
  the missing tail window changes which windows are reached before the 32-query
  cap, so some programs now exhaust the cap before the window that previously
  helped. This is a real effect of the repair, reported rather than tuned away.
- 464 corpus searches still exhaust the per-query budget as UNKNOWN. UNKNOWN is
  never reported as UNSAT.
- UNSAT remains local to the queried neighbourhood; no global optimality,
  private-grader result, compactness ratio or complexity claim is established.
- Construction still places operations in source order with no priority
  function.
- The pointwise predicate-versus-machine comparison in R3 runs only where the
  domain has at most 512 assignments; larger cases check SAT/UNSAT agreement and
  witness validity but not every point.
- The R6 fixture was found by scanning generated programs. It is frozen and
  reproducible, but it is one example, not evidence that trades are common.

## Commands for the lead to rerun

```sh
cd luminal-challenge

# the lead's own probes must now reproduce as failures
python3 results/direct_index_v1/lead_review/audit.py probes

# targeted regressions
PYTHONPATH=.reference:. python3 -m unittest discover -s tests_direct -p 'test_*.py'

# rebuild and full acceptance
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference:. python3 verify_direct.py --stage all --timeout 20 \
    --output results/direct_index_v2_repair/verification
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
    --output results/direct_index_v2_repair/comparison
```

Evidence: [verification summary](verification/summary.json),
[per-input isolated corpus](verification/isolated_corpus.json),
[corpus manifest](verification/corpus_manifest.json),
[all 72 comparison runs](comparison/runs.json),
[comparison report and gate table](comparison/COMPARISON.md).
