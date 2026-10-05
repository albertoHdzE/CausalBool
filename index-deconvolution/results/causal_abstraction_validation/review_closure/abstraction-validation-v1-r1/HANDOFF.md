# Correction handoff — causal state grouping, run abstraction-validation-v1-r1

2026-10-05. Executes `supervision/abstraction-validation-v1-r1/NEXT_CLAUDE.md`. The supervisor has accepted the V/D/X scientific evidence, and this closure leaves it alone. It repairs the two implementation robustness findings, R1 and R2, in isolated copies only, and delivers them as **unapplied patches**. No active or frozen file was modified. Nothing was committed, pushed, published or scheduled. No V/D/X job, Track G work, install or sibling-repository edit was made.

**Status: ready for Codex review; not yet accepted.**

## R1 — evidence availability and failure precedence (`study.py::evaluate_classes`)

The patch is `patches/R1_study_historical_reference.patch`, a source reference against the frozen run's `study.py`. It is for a separately adopted corrected copy and must never be applied in place to the frozen run.

- If the representative record is absent, the class is now missing evidence even when the class is a singleton. A missing singleton gives COARSE-INCOMPLETE, never COARSE-NO-HOLDOUT or COARSE-HOLDS.
- A present member is judged on its own existence even when its representative is missing. A member with no map becomes `MEMBER-NOEXIST` (reason: "member has no induced map; representative record absent"). It counts as a structural failure and also as a missing comparison. Row precedence is unchanged: DISAGREE > STRUCT-FAIL > INCOMPLETE > NO-HOLDOUT > HOLDS. A known structural failure or an observed disagreement therefore outranks missingness.
- A present member with a map whose representative is missing gives `outcome: MISSING`, `own_e3: PASS` and reason "representative record absent". Mismatch values stay null, and no representative is substituted.
- **New field, kept apart from the old ones:** `availability = {missing_records, missing_comparisons}`.
  - Unit of `missing_records`: distinct q indices with no record, counted once per index.
  - Unit of `missing_comparisons`: representative–member comparisons not made because a record is absent. It equals `counts["MISSING"]`. A singleton contributes no comparisons, so it is not counted as a micro-state comparison.
  - All old keys and their semantics on complete inputs are unchanged. The one behavioural difference on incomplete inputs is the member reason string above.

## R2 — incomplete supplied-map domains (`deconvolution.py::commutation_failures`)

The patch is `patches/R2_deconvolution.patch`. It adds the same guard as `induced_map`: `alpha` and `image` must be non-empty and of equal length, otherwise `ValueError` is raised before any iteration. The signature and return value are unchanged.

## Tests (declared first in `fixtures_declared.json`, F1–F7 and R2 cases)

| Run | Result | Log |
|---|---|---|
| Patched mirror: 63 existing + 10 new | **73 passed**, exit 0 | `logs/patched_suite.log` |
| New R1 tests vs frozen `study.py` | 7/7 fail | `logs/neg_old_study.log` |
| New R2 tests vs active `deconvolution.py` | 3/3 negative fail; the valid case (same failure indices `[2]`) passes | `logs/neg_old_deconvolution.log` |
| Restore B1: label ignores missing records | missing-singleton test fails (1) | `logs/neg_B1_*.log` |
| Restore B2: missing rep masks member existence | failed-member test fails (1) | `logs/neg_B2_*.log` |
| Restore B3: drop length check | 3 negative tests fail | `logs/neg_B3_*.log` |
| Active, unpatched suite (preservation) | 63 passed | `logs/active_suite_unchanged.log` |

The new R1 tests are in `R1_test_study_historical_reference.patch`. The R2 tests (parametrised: empty, image_short, alpha_short, plus one extra valid case with a failure index) are in `R2_test_abstraction.patch`.

Disclosure: against the old `study.py`, part of each of the 7 failures is a `KeyError` on the new `availability` field, not only the wrong label. The B1 and B2 restorations isolate the behavioural branches and run with the field present.

Interpreter and options: `venv/bin/python`, `PYTHONDONTWRITEBYTECODE=1`, `-p no:cacheprovider`, `PYTHONPATH=<mirror>/index-deconvolution/src`, `STUDY_DIR=<mirror run dir>`. The import origins are all in the mirror (`logs/import_origins.log`).

The mirror lives at `/tmp/cag_closure_20261005/repo` and reproduces the repository layout, because `deconvolution._program_module` resolves `parents[2]/doppel-challenge`. `doppel-challenge` and `hierarchy` are read-only symlinks. Two earlier attempts in a flat copy failed for layout reasons, not because of the patch (`attempts.jsonl`):

- attempt 1: `fixtures.json` was not copied;
- attempt 2: 14 failed, 13 because the `repertoire_program` path did not resolve and 1 owner-guard failure (it scanned 1 root, and a backup `deconvolution_orig.py` sat inside the scanned `src/`).

## Patch verification and source identities

- `git apply --check` passes for all four patches against the current bytes. Applying them to copies of the originals reproduces the corrected copies byte for byte (`logs/patch_apply_check.log`).
- The active and frozen sources were not changed: `source_before.sha256` equals `source_after_check.sha256`.
- Corrected sources: `source_corrected.sha256`. Copies are stored as `corrected_source/*.py.txt`. The `.txt` suffix is deliberate, because a `.py` file under `causal_abstraction_validation/` would trip the live single-owner guard.

| File | Before | Corrected |
|---|---|---|
| src/deconvolution.py | 233e066f… | bd549796… |
| tests/test_abstraction.py | 520b7518… | 51322d6e… |
| run study.py | 3ecda463… | 9ab57cb8… |
| run test_study.py | 8e93f6ab… | 81a8a342… |

## Comparison on complete evidence (`comparison_complete_evidence.json`)

The comparison is a differential of the frozen `evaluate_classes` against the corrected copy, on 20,000 seeded (20261005) random **complete** inputs. All 20,000 agree on every old field and have zero availability counts. All four complete-evidence labels were exercised: DISAGREE 8,293, STRUCT-FAIL 5,135, NO-HOLDOUT 4,419, HOLDS 2,153.

The 2,510 saved D coarse evaluations (STRUCT-FAIL 2,361, HOLDS 96, DISAGREE 53) were **not recomputed**. Their maps are not stored, and recomputing them would be a production rerun. They are complete by construction (`study.py` line 429 passes every q as present) and contain 0 missing events, which is the regime the differential covers. Coverage is therefore by branch and by random input, not row by row against saved D.

## Preservation

- Freeze and output-manifest hash entries: 69 verified, 0 mismatches. Another 5 manifest keys did not resolve to file paths with my path heuristic; they are disclosed, not checked.
- `git status --porcelain` is identical before and after (`git_status_diff.txt` is empty). The parent `causal_abstraction_validation/` was already wholly untracked, so this closure directory does not show up separately.
- No `results_v/d/x`, report table, notebook (including 19/build_19), governance file or original artifact was touched.

## Clarifications (closure prose only)

- **FULL is kept** on the 11 constant-dynamics rows. Validity (an exact induced map exists under the declared interventions) and usefulness (the reduced dynamics informs some target) are separate questions. No prospective rule excluded those rows, and this closure adds no usefulness criterion.
- The constant/nonconstant analysis is a **post-hoc descriptive** characterisation, not a prespecified endpoint. `render_nonf3.py` is a **supplemental recomputation** of the induced maps from the frozen owners, not a formatter of saved fields.
- **Timing note:** the last note in the historical time ledger mentions a reporting overrun, but its measured interval is 219 s, under the 300 s cap. The intervals and the total of 1,089 s are arithmetically consistent, and the note refers to an interim estimate that was later replaced. The frozen ledger was not edited.
- **Medians:** no patch is needed, because every actual median agrees with the conventional median. Future-use caution: the report code takes the upper middle item for even samples, so future reports should use `statistics.median`.

## Time (executor cap 600 s; the 180 s Codex reserve was not used)

| Category | Used | Cap |
|---|---|---|
| fixtures/development (incl. failed attempts 1–2) | 138 s | 300 |
| tests/patch verification | 60 s | 180 |
| preservation/handoff | see manifest.json | 120 |

## Unresolved

1. The saved D coarse rows were covered only indirectly (see Comparison).
2. 5 manifest hash keys were not resolved to paths by my check.
3. Adoption of the corrected `study.py` needs a separately identified copy. That is a supervisor decision.

ready for Codex review; not yet accepted.
