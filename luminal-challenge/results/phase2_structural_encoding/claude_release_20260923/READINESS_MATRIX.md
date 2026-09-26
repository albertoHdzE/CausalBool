# Pre-campaign readiness matrix

2026-09-24 · Claude Code release audit · plan §4. Logs are in `logs/`; each
`<label>.meta.json` holds argv, cwd, environment, UTC timestamps and exit code,
and `COMMANDS.jsonl` lists every command in order.

## Validation reproduced before any change (starting source = Luna checkpoint)

| Label | Command | Exit | Result |
|---|---|---:|---|
| a01 | `verify_package.py` (release, initial mode, starting hashes) | 0 | PASS: 11 delegation inputs, 17 starting source hashes |
| a02 | `plan/phase2_recovery/verify_package.py` | 0 | PASS: 7 recovery inputs; 12 package, 46 baseline locks |
| a03 | `check_structural_evidence --architecture` | 0 | PASS, 10 modules scanned |
| a04 | `unittest discover -s research_tests -v` | 0 | **269 tests, OK** (126.5 s) — reproduces the checkpoint count |

## Findings of `REPAIR_REVIEW.md` against code and tests

| # | Finding | Code inspected | Executable evidence | Disposition |
|---|---|---|---|---|
| 1 | P4 fixture/program identity through harness, commands, journals, checker | `Harness.run` identity guards; `run_model_measurement` refuses spec/fixture digest mismatch; `check_durable_journals` joins on fixture_id and program_sha256; `check_commands.task_identity` includes fixture_id | `test_p4_workers_return_fixture_identity_and_durable_journals` (real subprocess workers, all 4 arms, informative `many_ready_1` + `chain_0`; statuses NOT_APPLICABLE/INCONCLUSIVE/PASS accepted; checker reconciles journals) | CLOSED at checkpoint; verified |
| 2 | Wrong primary corpus and estimand | `build_recovery_comparison` primary = held-out P5 @0.1 vs accepted_budgeted, `_paired_repetition_log_quality` pairs repetitions then seeds then programs | Checkpoint tests: `test_paired_quality_uses_matched_log_products_not_log_of_means`, `..._refuses_a_missing_technical_pair`, `test_recovery_primary_is_heldout_p5...`, `test_p5_checker_rejects_forged_primary_budget...` | **Residual defects found and repaired** (R1–R3 below) |
| 3 | Physical-probe shared deadline/accounting | `physical_probes.run`: deadline checked around construction, machine check, every case, every codec encode/decode, decoded machine+case checks, and after the last round trip; partially validated objects are INTERRUPTED and never counted; discrepancy outranks expiry | `test_physical_probe_deadline_during_cases/roundtrip/codec_case_check_is_interrupted`, `test_known_case_failure_beats_simultaneous_deadline` | CLOSED; verified |
| 4 | Diversity and integrity evidence | `compilation_diversity`, P1 `original_random_coverage` / `amended_union_coverage`; checker recomputes both diversities and both coverage vectors from raw rows | `test_checker_rejects_false_original_and_amended_coverage_pass`, `test_physical_checker_rejects_summary_membership_and_elapsed_mutation` | CLOSED; verified |
| 5 | Mutation matrix of recovery-plan §8 | checker `check_physical_probes`, `check_commands`, `check_durable_journals`, `check_p5` | 13 mutation tests in `test_phase2_recovery.py` (omission/duplicate/reorder/forged identity/invalid-as-complete/erased counts/false PASS/amendment & import mismatch/missing & budgeted classical/crash/missing journal/forged primary) | CLOSED; verified. Forged *public* statistics are additionally covered by `R2IntervalRecomputation` |
| 6 | Durable partial evidence | `_append_jsonl_fsync` of command and row per worker exit in `Harness.run`; checker reconciles journals ↔ commands ↔ stage rows | `test_crashed_worker_is_fsynced_and_missing_journal_row_is_detected` | CLOSED; verified. Limitation: no in-run resume; an interruption requires a fresh run |
| 7 | P4 inference, shared budget, balanced order | `p4_contrasts` pairs repetition→seed→variant→program, reuses null-seed controls analytically; `run_model_measurement` gives cover `min(remaining, 10 s)`, meters encode/decode/cases/test evaluation on one deadline; oracle preprocessing reported separately | `test_p4_pairing_reuses_null_control...`, `test_p4_cover_deadline_uses_remaining_budget...`, `test_p4_decode_deadline...`, `test_p4_test_evaluation_deadline...`, `test_p4_known_case_failure_beats_deadline` | CLOSED; **test gap on `stage_p4` order filled** (R4) |

### Residual defects repaired in this audit (all Finding 2 scope unless noted)

| ID | Defect (demonstrated) | Consequence if unrepaired | Repair | Regression |
|---|---|---|---|---|
| R1 | `hypothesis_dispositions` labelled **H2 from the public P2 contrast** even under the amendment | `hypotheses.json`/`HANDOFF.md` would report H2 from development data, contradicting the frozen held-out primary | Under the amendment H2 is read from `COMPARISON.json.primary_h2` (held-out P5 @0.1); NOT_RUN if absent; never `supported` unless the P5 gate is PASS. Legacy path unchanged. Checker recomputes with the same flag | `AmendedH2IsTheHeldoutPrimary` (4 tests) |
| R2 | Amended `stage_p2` and the checker's P2 recomputation used `_quality_table` → **log of mean products** | Public P2 descriptive contrasts would use the estimand the lead rejected | `paired_repetitions=run.amendment is not None` in `stage_p2`; checker pairs for `p2` and `p5` labels when amended. Legacy unchanged | `AmendedP2UsesThePairedEstimand` (4 tests; fixture where the estimands differ by >1e-3) |
| R3 | `COMPARISON.md` never rendered `primary_h2` and its footer claimed the primary used "the original confirmatory P2 interval"; entries showed no expected denominator; the paired endpoint label in `paired_log_ratio_analysis` was overwritten by the generic label (dict key order) | Human-readable table misstates the confirmatory analysis; an unpaired program would reduce n silently | Primary section rendered; footer corrected; `expected_programs` and `unpaired_programs` added to every entry and the primary; programs shown as paired/expected; label order fixed | `ComparisonMarkdownAndDenominators` (2 tests) |
| R4 (F7) | No test exercised `stage_p4`'s balanced order | Order regression undetectable | Test only | `P4BalancedArmOrder`: 7,020 specs equal an independent statement of contract §9; no arm measured as a block first |
| R5 | Run HANDOFF template attributed the amended run to "Codex delegated research implementation" | False provenance | Attribution names Claude Code (Opus 5.5) | none (text) |

Evidence that the regressions detect the defects: `logs/b02_new_regressions_on_starting_source.log`
— the 11 new tests run against the untouched starting source give **4 failures + 4
errors** (the 3 passes are the fixture sanity check, the legacy-unchanged guard
and the P4 order coverage test). `logs/b03_*`: 11/11 pass on the repaired source.

### Observations recorded, not changed

- `p4_contrasts.families_with_informative_tests` filters `test_proposals >= 0`,
  which is always true; the effective rule is "family has a PASS row", i.e. an
  informative fixture whose row did not expire. This is conservative and matches
  the contract definition of an informative fixture (≥10 train, ≥5 test). No
  change, to avoid moving the gate; flagged for Codex.
- In `physical_probes.run` an INVALID_PHYSICAL verdict obtained after the deadline
  is still counted as INVALID_PHYSICAL; it cannot add coverage, so the coverage
  gate is unaffected.
- The checker's P5 comparison recomputation calls the runner's own function; its
  independence comes from the lead's `independent_compare.py` (plan §6).
- Pre-existing lint (unused locals/imports) in untouched modules was not churned.

## Validation after repairs (final frozen source)

| Label | Command | Exit | Result |
|---|---|---:|---|
| c01 | `verify_package.py --policy-only` | 0 | PASS: policy inputs verified; initial-source comparison skipped for authorised repairs |
| c02 | recovery `verify_package.py` | 0 | PASS |
| c03 | `--architecture` | 0 | PASS |
| c04 | full research suite | 0 | **280 tests, OK** (132.7 s) = 269 + 11 new; none deleted |

Frozen source: `final_source/`, `FINAL_SOURCE_SHA256.txt` (sha256 of that list
`88a72d46…2944`). Changed files: `research/run_structural_experiments.py`,
`research/check_structural_evidence.py`, new `research_tests/test_phase2_release.py`;
full diff `SOURCE_CHANGES.patch`. Gate passed; campaign launched after freezing.

## Addendum — checker defects exposed at runtime by `_r2` (post-launch)

`recovery_campaign_20260923_r2` ran to completion under source v1 (all 1,800 P2,
7,020 P4 and 24,300 P5 rows, 0 failed rows). Its checker (`logs/e01_checker_r2.*`)
exited 1 with 22 findings. Both root causes are in the **checker**, not in any
measurement code; runner, workers and probes are byte-identical in v1 and v2
(`SOURCE_CHANGES_V1_TO_V2.patch` touches only `check_structural_evidence.py` and
the test file).

| ID | Defect (demonstrated at runtime) | Repair | Regression (fails on v1 checker / passes on v2) |
|---|---|---|---|
| R6 (F3 residue) | `check_physical_probes` had no path that recomputes INTERRUPTED. Two genuine 60 s deadline interruptions (`01_scalar_pipeline` #1649 at 60.008 s, `07_scalar_selects` #1773 at 60.002 s, both mid round trip) were re-completed by the deadline-free replay and **credited to coverage** — the opposite of the amendment's "count only fully validated objects" — producing 17 findings and 5 cascaded gate reconciliations | A recorded INTERRUPTED row is accepted only if it is the final row of its program, its elapsed time is at or past the policy deadline, and the independent replay is VALIDATED_COMPLETE (or INVALID with phase `construction`); every codec result it did record must equal the independent one; a discrepancy anywhere still fails; the object is never credited | `CheckerAcceptsGenuineDeadlineInterruption` (5 tests, a real bounded prefix with injected mid-round-trip expiry): `logs/f02_*` 3 FAIL on v1, `logs/f01_*` 5/5 pass on v2 |
| R7 (H4 residue, masked by R6's cascade) | `check_p4` never derived INCONCLUSIVE when the recomputed H4 gate did not advance, so the legitimately INCONCLUSIVE P4 was derived PASS and reported as a reconciliation finding (`logs/g05_*`) | When the gate recomputed from raw rows does not advance, record `p4.h4_gate` as inconclusive (never from the summary label); a forged advancement label remains a finding | `P4BalancedArmOrder.test_the_checker_derives_inconclusive_when_the_recomputed_h4_gate_fails`: `logs/h02_*` FAIL on v1, `logs/h01_*` pass on v2 |

Post-repair gate: `logs/h03_research_tests_full_v3` **286 tests OK** (exit 0);
`logs/g02/g03/g04` verifiers and architecture exit 0. Dry run of the v2 checker
on `_r2` (`logs/h04_*`): every stage verdict reconciles; only the expected
`provenance.source_snapshot` findings remain, because `_r2` recorded the v1
checker. A checker whose own source differs from the run's snapshot cannot give
that run a self-contained verdict, so v2 was frozen (`final_source_v2/`,
`FINAL_SOURCE_V2_SHA256.txt`) and a fresh self-contained `_r3` was run with the
identical command. `_r2` is preserved unchanged; it is not merged with `_r3`.
