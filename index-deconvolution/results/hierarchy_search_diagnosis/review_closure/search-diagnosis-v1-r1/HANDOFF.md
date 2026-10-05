# search-diagnosis-v1-r1 — review closure R1–R3: handoff for Codex

Date: 2026-10-03. Executor: Claude Code. Supervisor: Codex. Git HEAD
`53c41d8f3b97106fd176f24d575e0934848dddd6` (`main`), dirty tree with other people's edits
preserved. **Ready for Codex review; not yet accepted.** Nothing committed, pushed or
published. No D2–D4 job was resumed or launched; no encoder, generator, search or
diagnostic job ran. The accepted search-v2 verdict stays inconclusive.

Paths below are relative to this directory unless stated otherwise. The original run
`../../search-diagnosis-v1-r1/` and its reports are untouched historical artifacts; the
corrected copies are in `corrected/`.

## 0. Before work

* Closure delegation manifest: **23/23** SHA-256 values matched before any work.
* No collision: `review_closure/` did not exist. A scratch dry-run folder
  `report-r2-dryrun/`, created and deleted by me inside this directory, preceded the
  immutable revision (§2).

## 1. Disposition

| finding | disposition | where |
|---|---|---|
| **R1** impossibility/optimality claims; H = T vs identical proposals | corrected in every affected copy; byte identity now measured and reported (282 = **261** identical + **21** different bytes, matching `audit.json`); universal exact-repeat floor removed; Draft B now predicts only per-proposal T′ with full serialization accounting, and says H′ is measured, not predicted; "combining makes attribution impossible" became a design preference; `BOTH_SEPARATELY` kept as exploratory | `corrected/DECISION.md`, `REPORT.md`, `NEXT_PROTOCOL_DRAFT.md`, `HANDOFF_a1.md`, `bitacora_42_…md`; `report-r2` field `T_bytes_equal_H`, keys `d4_hid_loses_H_eq_T_identical_bytes` / `_different_bytes`; corrected `reading` text and rule |
| **R2** returned-cut proximity is not proposal coverage | 129/252 relabelled as proximity to cuts of B0's **returned** archive in the 68 strictly reachable witnesses (key `descriptive_returned_B0_cut_proximity`, with `strings: 68` and a scope text); "never proposes", the mechanism ranking and the leaf/language-as-sole-cause falsification removed; the B0→B8 result qualified as one cap increase; Draft A rationale is a hypothesis and its gate requires a direct proposal log (not run; no telemetry jobs); Draft A marked not executable until it has a finite total budget and specified scheduling/ties; F06/F07/F11 = D2 controls only, F08–F10 = D1 only | same corrected copies; notebook §§3–4 and closing caveats |
| **R3** KeyError on unavailable records | reporting pipeline repaired in a copy: one `report.build` (records → rows → summaries → flags → decision); evidence gate before success-only quantities; INVALID (wrong decode, source/input mismatch, B0 mismatch, reference not reproduced, identity failure, D1 problem) takes precedence over INCOMPLETE (missing, not_run, timeout, RSS, worker error, graph-limited); partial quantities keep intended and available denominators and never become zero | `patches/R3_reporting_pipeline.patch`; tests `test_reporting_pipeline.py` |

## 2. Reporting revision `report-r2`

* Identity SHA-256 **`89fa52872009f39bac0ff457213fbbfcd9070a042cd3a3e6eee1f48e814860f4`**
  (`report-r2/identity.json`, recorded 2026-10-03T23:15:09Z; `identity` refuses any later
  change and requires a new revision name). Status recorded in it: post-hoc reporting
  revision of retained computations; disclosed exception to protocol §3.
* It covers 15 source files — the patched package copy `report-r2/source/search_diagnosis/`
  (job-executing adapters byte-identical to a1's: `common`, `kernels`, `runner`, `worker`,
  `__init__`), all tests, the corrected builder `report-r2/source/build_18.py` and
  `report-r2/run_report_r2.py` — plus the protocol, contract, closure kickoff, REVIEW.md,
  closure delegation manifest and a1 `identity.json` by hash, and the hashes of all
  **1,950 consumed a1/accepted-run files** (`report-r2/consumed_records.json`, aggregate
  `7a560f9d…01f0`): 416 + 176 + 576 job records, D1 tables, 776 saved row files,
  references, contract. Executable closure `report-r2/closure.tar` SHA-256 `fab79dd5…f545`.
* Compute identity unchanged: attempt `a1`, `518ebc13…4a9e`. a1's
  `identity/reporting_revisions.json`, tables and reports were not written.
* Reproducible command (from the repository root; reads a1, writes only `report-r2/`):

  ```sh
  C=index-deconvolution/results/hierarchy_search_diagnosis/review_closure/search-diagnosis-v1-r1
  PYTHONDONTWRITEBYTECODE=1 venv/bin/python $C/report-r2/run_report_r2.py identity   # "identity unchanged"
  PYTHONDONTWRITEBYTECODE=1 venv/bin/python $C/report-r2/run_report_r2.py report
  ```

  `common.py` derives paths from its own location, so the runner re-roots every `Path`
  constant of `common` that lies under the source copy onto the real tree, once, and
  asserts `RUN_DIR`; no source file is altered for this. It re-hashes all consumed files
  after the run (`consumed_unchanged_after: true`).

## 3. Numerical comparison with a1 (`report-r2/outputs/comparison_with_a1.json`)

Every leaf of a1's nine reporting outputs (`analysis/*.json`, `DECISION.json`) was
compared with `report-r2`: **209,545 a1 leaves, 209,540 identical, 0 numeric or boolean
changes, 0 absent**. The two R2 key renames are mapped explicitly. Five text leaves
changed, all R1/R2 wording: `DECISION.rule`, `DECISION.basis[0–2]`, and the D4
decomposition `reading`. 1,256 leaves were added: `T_bytes_equal_H` on the 1,152 D4
rows, the evidence block and availability denominators in `flags`, ten key numbers and
two decision fields. Recommendation unchanged: **`BOTH_SEPARATELY`**; gates: complete
and valid.

## 4. Tests, negative probes, lint

* Focused tests (isolated copy, byte-identical to the frozen source):
  **44 passed** = 27 existing + 17 new (`verification/pytest_focused.log`). The new tests
  run the real pipeline on deep copies of the retained a1 records, read once; nothing on
  disk is altered. Unavailable: missing D2 control B8, D2 target B8 timeout (cell stays
  partial, never zero), D3 timeout / error / rss_limit / not_run / missing, D4
  graph-limited translation of a losing portfolio winner, D4 missing job. Invalid,
  separately: B0 deterministic mismatch, reference not reproduced, wrong decode, input
  hash mismatch, D1 problem, and invalid + missing together (INVALID wins). Complete:
  every a1 key number and flag table reproduced; 261/21 byte split.
* Negative probes (`verification/negative_probes.json`, `scripts/negative_probes.py`,
  fresh temporary trees): **8/8 pass**.
  * a1's reporting code (the active `analysis.py`/`report.py` plus only the pipeline glue):
    15 of 17 new tests fail, and the three supervisor probes recur exactly —
    `KeyError: 'B8_bits'`, `KeyError: 'cheapest_all'`, `KeyError: 'T'`.
  * Six single mutations, each caught: unavailable B8 → zero opportunity (1 failure);
    INCOMPLETE before INVALID (3); unavailable translation counted as H = T (1); wrong
    decode treated as unavailable (1); equal length read as equal bytes (2); rule
    evaluated on partial evidence (9). Unmutated control: 17/17 pass.
* Ruff (repository `ruff.toml`): clean on the patched package, builder, runner and all
  closure scripts (`verification/ruff.log`).
* Owner suite not rerun: no owner changed (preservation §6).

## 5. Patches (delivered, not applied)

| file | SHA-256 | `git apply --check` (repo root) |
|---|---|---|
| `patches/R3_reporting_pipeline.patch` — `analysis.py`, `report.py`, `cli.py`, new `tests/test_reporting_pipeline.py` | `e992665f8c98b892…` | pass |
| `patches/R1R2_build_18_report_r2.patch` — `notebooks/build_18.py` | `0c1d04cb3a7e0295…` | pass |
| `patches/R1R2_prose_corrections.informational.diff` — originals → corrected copies, for reading only | `289c60cb98b0547b…` | not meant to be applied |

Applying both patches to copies of the active files reproduces `report-r2/source/`
byte for byte (`verification/git_apply_check.log`). The historical R1 median source
patch of search-v2 remains unapplied.

## 6. Notebook

`corrected/18_hierarchy_search_diagnosis.report-r2.ipynb` (built by the corrected
builder, 21 cells) reads rows/flags/decision from `report-r2/outputs/` and jobs/archives
from a1. It was executed 5 times under the reviewed artifact-only guard (reused `run` from
`search-confirm-v2` `review_closure/scripts/execute_notebook_artifact_only.py`) from its own
directory and from the repository root; all 10 executed notebooks are kept in
`verification/notebook/`. In every run: exit 0, 0 error outputs, 0 unexecuted cells,
guard active, 0 refusals, only allowlisted `hierarchy` modules, no inference/generation/
job/subprocess tokens, saved values displayed (revision identity, accepted primary,
recommendation, the 282/261/21 line, the returned-cut proximity line, the D2 witness,
the evidence gate).

**The text mismatch recurred** in runs 2 and 4 (cell 9, repository-root execution only);
the strict check fails there. Investigated (`verification/notebook/diagnosis.json`): the
same stdout text arrives as two stream messages instead of one (`'…re-bucketed:'` and
`' 1152\n…'`); concatenated text is identical in all 10 executions. Most likely an
ipykernel stdout flush splitting the cell's first `print` after its file-reading loop;
not proven. Delivered: `corrected/18_hierarchy_search_diagnosis.report-r2.executed.ipynb`
= run 1, notebook directory, all checks pass.

## 7. Guards

`check_test_manifest`, `check_core_index`, `check_glossary_sync`,
`check_glossary_conformance`: pass. `check_single_engine`: exit 1 with the same 9
pre-existing FAIL lines as a1's record, none mentioning this closure
(`verification/guards/`). `make ci-local` not run (dirty-tree exception, as before).

## 8. Preservation (`verification/preservation_{before,after,comparison}.json`)

Before (first action after the hash check) and after (end of work): **0 differences**
across the phase owner's 4 trees and 60 files, plus the whole a1 run (8,152 files),
the supervision record, the active `experiments/search_diagnosis/` (bytecode excluded)
and 6 named files (phase ledger, active builder, notebook 18, bitacora 42, closure
kickoff, the unapplied R1 median patch). The git-status delta is exactly this
directory's new files. No `__pycache__` was created outside the temporary trees.

## 9. Resources (`execution_ledger.jsonl`, this closure's own ledger)

Basis as in a1: conservative wall-clock spans. Supervisor's separate 120 s counted once.

| category | cap | a1 phase ledger | supervisor | closure | cumulative | remaining |
|---|--:|--:|--:|--:|--:|--:|
| fixtures_development | 1,800 s | 599.9 | — | 625.0 | 1,224.9 | 575.1 |
| diagnostic_jobs | 10,800 s | 82.3 | — | 0 | 82.3 | 10,717.7 |
| report_verification | 1,800 s | 1,095.0 | 120 | 658.0 | 1,873.0 | -73.0 |
| total | 14,400 s | 1,777.2 | 120 | 1,283.0 | 3,180.2 | 11,219.8 |

**`report_verification` is over its cap by 73.0 s** (1,873.0 of 1,800 s). All correction evidence was complete when the cap was reached at about 2026-10-03T23:24:54Z (closure report/verification charge 585 s); the work after that point was collecting hashes and writing this handoff, the ledger and `resource_totals.json` (the guards and the preservation after-check had finished before it; these three files were written after the after-check, inside this directory only). The charge is recorded, not moved to another category. Nothing remains to be run for R1–R3; what remains is Codex review (§10). For reference, the automated commands themselves (tests, probes, notebook executions, guards, preservation, regeneration) took a few minutes of machine time; the wall-clock basis is kept for consistency with a1.

## 10. Remaining for review

* Accept or reject the `report-r2` revision, the R3 patch and the corrected copies.
* Whether to apply the patches to the active owners (would change the active adapter
  hashes; a1's identity remains the computation record).
* Draft A still needs a finite total budget and specified scheduling/ties before it can
  be a protocol; neither draft is approved.

**Ready for Codex review; not yet accepted.**
