# Handoff: follow-up closure of Codex closure review R3a–R3b (report-r3)

Date: 2026-10-04 (UTC). Status: **ready for Codex review; not yet accepted.** Patches are
delivered unapplied. Nothing was committed or pushed, no diagnostic job was launched or
resumed, and no recurring task was created.

Budget: the user approved raising report_verification from 1,800 to 2,400 s on 2026-10-03.
The 14,400 s overall ceiling, every other category cap, the original 72.984045 s overrun and
the 60 s supervisor charge all stand. Actual use is in `execution_ledger.jsonl` and
`resource_totals.json`.

## What changed

Both fixes live in the reporting layer only (`analysis._evidence`, `report.decision`). Job
kernels are byte-identical to a1 and to the active tree: `kernels.py`, `worker.py`,
`runner.py`, `common.py`.

- **R3a.** D4 job status is now counted once per intended case. Conversion status is still
  counted per method. If one case's rows ever disagree on `job_status`, it fails loudly.
  - Complete run: 576 jobs ok out of 576 intended; 1,152 conversions ok out of 1,152.
  - In-memory missing-job probe: jobs {ok 575, missing 1}; conversions {ok 1,150, missing 2}.
  - Invalid-job probe (wrong decode): jobs {ok 575, invalid_decode 1}, still out of 576.
  - Each status count sums to its own intended denominator.
- **R3b.** A selected-B archive-byte comparison that is explicitly `False` is now invalid
  evidence. It goes into `flags.evidence.invalid.B0_selected_bytes_mismatch` and the new
  gate field `DECISION.gates.B0_selected_bytes_mismatches`, both listing case IDs, and it
  sets `invalid.any`. As a result INVALID wins over INCOMPLETE and neither signal is
  evaluated (`search_signal` and `representation_signal` stay `None`). An absent comparison
  is not treated as a failure. A comparison is absent when B0 is unavailable or the final
  archive came from another stage.

## Evidence

| Check | Result |
|---|---|
| Focused tests, report-r3 (`scripts/run_tests.py r3`) | 51 passed (44 existing + 7 new) |
| New tests against report-r2 (`r2+r3tests`, temp copy) | 7 failed, 44 passed |
| ruff (report-r3, scripts) | clean |
| report-r3 vs a1 (`outputs/comparison_with_a1.json`) | 0 numeric/boolean changes, 0 a1 leaves absent |
| report-r3 vs report-r2 (`outputs/comparison_with_r2.json`) | 210,800 of 210,801 leaves identical. The one change is intended: `flags/evidence/status/D4_jobs/ok` 1,152 → 576. 0 unexplained, 0 removed. Two new gate fields: `flags/evidence/invalid/B0_selected_bytes_mismatch` = [] and `DECISION/gates/B0_selected_bytes_mismatches` = [] |
| Recommendation | BOTH_SEPARATELY, unchanged |
| `git apply --check` + apply in a copy (`verification/git_apply_check.log`) | both patches apply; the result is byte-identical to report-r3 source |
| Notebook 18 (report-r3), guarded, once from each working directory | 8/8 checks pass; 0 differences after coalescing adjacent same-name streams (`verification/notebook/run1.*`) |
| Preservation before/after (`verification/preservation_comparison.json`) | unchanged: 4 owner trees, 60 files, 4 extra trees (a1 run 8,152 files; supervision; active adapters; the whole first closure including report-r2), 7 extra files, delegation manifest 20/20 hashes match |

The 7 new tests fail on report-r2 in two ways:

- **Assertion failures (the defect itself):**
  - three D4 count tests;
  - the false-bytes test, which still returns `valid` (BOTH_SEPARATELY);
  - the false-bytes-plus-missing test (`INCOMPLETE` ≠ `INVALID`).
- **KeyError on the new gate field:** two tests fail only because report-r2 does not have
  the field. These are the retained-pass test and the absent-comparison test. Their
  behavioural assertions are new coverage, not reproductions of the defect.

The tests use the record-to-decision pipeline (`report.build`) on deep copies of the
retained a1 records. No retained file was edited. The R3b fixture copies the review's
probe: it changes only `archives.output.sha256` of
`confirmation-F12-1024-3000-base` B0, and `B0_deterministic_mismatch` stays `[]`.

All actual D1–D4 measurement values are unchanged. So are the 261/21 byte split, the
returned-cut proximity and BOTH_SEPARATELY. The accepted R1/R2 language is untouched, and
no new scientific interpretation is offered.

## Files (this directory only)

- `report-r3/`: immutable revision.
  - `identity.json`: identity `7b1590bb4a63dd0f…`, closure tar `aa33d9dfcd68efff…`, 15 sources, 1,950 consumed records.
  - Also `closure.tar`, `consumed_records.json`, `run_report_r3.py`, `source/` and `outputs/` (9 reporting objects plus both comparisons).
  - Reproduce from the repository root:
    `PYTHONDONTWRITEBYTECODE=1 venv/bin/python index-deconvolution/results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1-followup/report-r3/run_report_r3.py report`.
    It reads a1 and writes only to `report-r3/outputs/`.
- `patches/R3_R3a_R3b_reporting_pipeline.patch`: active `experiments/search_diagnosis` → report-r3 source. It **replaces** the first closure's `R3_reporting_pipeline.patch` and is made against the current active tree.
- `patches/R1R2_build_18_report_r3.patch`: active `notebooks/build_18.py` → the report-r3 builder. It replaces `R1R2_build_18_report_r2.patch`.
- `corrected/18_hierarchy_search_diagnosis.report-r3{,.executed}.ipynb`: the notebook, unexecuted and executed.
- `scripts/`:
  - `run_tests.py`, `make_patches.py`, `execute_notebook_r3.py` and `preservation.py` are adapted copies of the first closure's drivers.
  - The notebook driver uses the reviewed artifact-only harness unchanged.
- `verification/`: `tests_and_lint.txt` (transcribed: tests were run once, not rerun to capture a log), apply log, preservation records, notebook records, `hashes.sha256`.

## Disclosures

- Running the tests left a `__pycache__` (two `.pyc` files) inside `report-r3/source/`. I
  removed it before finishing. Identity and tar both exclude bytecode, and `identity`
  re-verified as unchanged afterwards. No bytecode appeared in report-r2 or the active tree.
- The approved historical median repair stays unapplied. The prose-correction diff of the
  first closure is still valid and is not regenerated here.
- The next supervisor review keeps its 60 s reserve.
