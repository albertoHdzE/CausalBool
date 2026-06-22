# Move Delete Candidates

## Purpose

This register is the first action-oriented cleanup map.

It does not assume that every candidate should be deleted.
It separates:

- delete-ready items
- archive-ready items
- move-ready items
- verify-first items
- hold items

Each entry is evaluated against the current mapping, source-of-truth index, and paper-tree policy.

## Status Labels

- `delete-ready`: low-risk removal candidate
- `archive-ready`: not primary, but should be preserved in an archive location rather than deleted
- `move-ready`: can be reorganized with low risk once target structure is chosen
- `verify-first`: plausible cleanup candidate, but evidence is still insufficient
- `hold`: should not be moved or deleted in the next cleanup wave

## Candidate Register

| Candidate | Area | Current Role | Proposed Action | Risk | Verification Gate | Rationale |
| --- | --- | --- | --- | --- | --- | --- |
| `doc/finalpaper/final-draft.tex` | manuscript | historical manuscript branch | `archive-ready` | low-medium | preserve explicit provenance references before move | `bitacora-lev8.md` still references it as the previous manuscript comparison branch, so deletion would be wrong; archival isolation is appropriate later. |
| `doc/finalpaper/final-draft.pdf` | manuscript | review-support historical output | `archive-ready` | low-medium | keep paired with `final-draft.tex` | Historical comparison artifact mentioned in review material and provenance context. |
| `doc/finalpaper/nature_final.tex` | manuscript | alternate Nature manuscript branch | `verify-first` | medium | compare text role versus `nature_draft.tex`; check if any script or review loop still targets it | Appears manuscript-like and important, but current policy identifies `nature_draft.tex` as the strongest active source. |
| `doc/finalpaper/nature_final.pdf` | manuscript | compiled companion of alternate Nature branch | `verify-first` | medium | resolve status of `nature_final.tex` first | The PDF cannot be classified until its source branch is resolved. |
| `doc/finalpaper/supInfo.txt` | manuscript support | auxiliary supplementary text | `verify-first` | medium | determine whether it feeds any active supplementary manuscript workflow | Looks secondary, but may contain unique supplementary wording or assembly hints. |
| `doc/finalpaper/together.tex` | manuscript synthesis | condenser | `hold` | high | none before extraction/indexing plan | Historical synthesis artifact, not a safe deletion or move candidate yet. |
| `doc/finalpaper/together_full.tex` | manuscript synthesis | condenser | `hold` | high | none before extraction/indexing plan | Preserves cross-level integration and assembly logic not cleanly encoded elsewhere. |
| `doc/finalpaper/together_full.pdf` | manuscript synthesis | review-support compiled condenser | `verify-first` | medium | decide whether condensers keep PDF companions as archival evidence | May be deletable later, but only after condenser retention policy is formalized. |
| `4ClaudeCode/claude-Nature/paper/paper3_algorithmic_corruption.tex` | Level 8 paper tree | side-branch manuscript | `verify-first` | medium | choose explicit paper-branch policy for Level 8 manuscript variants | Important alternative manuscript branch, but not currently the strongest active source-of-truth. |
| `index.js` | root artifact | generated frontend bundle candidate | `archive-ready` | low-medium | check for repository references before moving | Large Vite-style bundle with no repository references found; preserved as artifact rather than active source. |
| `cc_index.js` | root artifact | generated frontend bundle candidate | `archive-ready` | low-medium | same as `index.js` | Same bundle family and file size as `index.js`, with no repository references found. |
| `debug_ccapi.py` | root scratch scripts | ad hoc diagnostic script | `archive-ready` | low-medium | skim for unique operational notes before moving | Likely non-production, but may preserve debugging knowledge worth retaining in an archive bucket. |
| `debug_sbml.py` | root scratch scripts | ad hoc diagnostic script | `archive-ready` | low-medium | skim for unique parser/format knowledge before moving | Fits scratch-tool pattern better than production code. |
| `debug_lambda.m` | root scratch scripts | Mathematica debug script | `archive-ready` | low-medium | skim for unique symbolic or logic notes before moving | Strong scratch/debug signal from naming and location. |
| `debug_symbolic.m` | root scratch scripts | Mathematica debug script | `archive-ready` | low-medium | skim for unique symbolic notes before moving | Same rationale as `debug_lambda.m`. |
| `explore_ccapi.py` | root scratch scripts | exploratory vendor wrapper script | `archive-ready` | low-medium | confirm no workflow docs still instruct its use | Appears exploratory rather than stable pipeline code. |
| `inspect_ccapi.py` | root scratch scripts | exploratory vendor inspection script | `archive-ready` | low-medium | confirm no workflow docs still instruct its use | Better treated as archived troubleshooting support than active code. |
| `inspect_ccapi_methods.py` | root scratch scripts | exploratory vendor inspection script | `archive-ready` | low-medium | confirm no workflow docs still instruct its use | Same exploratory pattern as other ccapi inspection helpers. |
| `test_bdm.py` | root scratch scripts | top-level diagnostic test script | `archive-ready` | low-medium | check for repository references before moving | Small standalone BDM probe with no repository references found; preserved in archive with its data fixture. |
| `test_bdm_debug.m` | root scratch scripts | top-level Mathematica debug test | `archive-ready` | low-medium | skim for unique benchmark or failure context before moving | Appears debugging-oriented and separate from formal test harnesses. |
| `test_bdm.json` | root scratch scripts | data fixture for BDM probe | `archive-ready` | low-medium | move together with `test_bdm.py` | Tiny fixture file paired with the standalone BDM probe. |
| `test_ccapi_search.py` | root scratch scripts | exploratory/vendor diagnostic script | `archive-ready` | low-medium | confirm no documented workflow depends on it | Fits the exploratory test utility pattern. |
| `process_data.py` | root utility scripts | thin wrapper entrypoint | `verify-first` | medium | decide whether top-level wrappers are desired project interface or clutter | Tiny wrapper around `GRNLoader`; may be intentionally convenient. |
| `report_dataset.py` | root utility scripts | thin reporting utility | `verify-first` | low-medium | confirm whether users still run it manually | Small but potentially useful operator utility; not enough evidence for deletion. |
| `run_process.py` | root utility scripts | thin runner script | `verify-first` | medium | inspect whether it duplicates another entrypoint exactly | Entry-point duplication is plausible, but not yet proven. |
| `run_scraper.py` | root utility scripts | thin runner script | `verify-first` | medium | inspect whether it duplicates code under `src/integration/` or paper code | Could be a valid convenience launcher or stale wrapper. |
| `mat-bdm/` | math workspace | historical computational workspace | `verify-first` | high | compare contents against `mathematicabdm/` and check for unique lookup tables/notebooks | Historical overlap is suspected but not yet measured well enough for action. |
| `mathematicabdm/` | math workspace | historical computational workspace | `verify-first` | high | compare contents against `mat-bdm/` and check for unique lookup tables/notebooks | Same overlap concern as `mat-bdm/`. |
| `src/analysis/optimize_alpha_draft.py` | analysis code | incomplete draft | `archive-ready` | low-medium | compare line-by-line with `optimize_alpha.py` before moving | Comparison shows it stops at an unresolved data-shape question and is superseded by the working `optimize_alpha.py`. |
| `results/tests/` vs `4ClaudeCode/claude-Nature/paper/results/tests/` | test outputs | overlapping provenance/output trees | `verify-first` | high | determine canonical source tests vs canonical outputs vs paper snapshots | Three-way provenance problem; not ready for pruning. |

## Immediate Safe Zone

The safest next operational actions are not manuscript deletions.

They are:

1. archive-oriented reclassification of top-level scratch/debug scripts
2. line-by-line comparison of obvious draft/code duplicates
3. dependency check for generated bundle artifacts

### Execution note

The first item in this safe zone has now been executed on the `clean` branch.

Archived from repository root to `archive/root_scratch/`:

- `debug_ccapi.py`
- `debug_sbml.py`
- `debug_lambda.m`
- `debug_symbolic.m`
- `explore_ccapi.py`
- `inspect_ccapi.py`
- `inspect_ccapi_methods.py`
- `test_bdm_debug.m`
- `test_ccapi_search.py`

These items remain historically preserved, but they no longer occupy the active repository root.

The next two items in this safe zone have now also been executed on the `clean` branch.

Archived from repository root to `archive/root_scratch/`:

- `test_bdm.py`
- `test_bdm.json`

Archived from repository root to `archive/generated_web_bundles/`:

- `index.js`
- `cc_index.js`

Archived from `src/analysis/` to `archive/analysis_drafts/`:

- `optimize_alpha_draft.py`

## Not Ready For Action

The following remain protected for now:

- `doc/newIntPaper/`
- `4ClaudeCode/claude-Nature/paper/`
- `src/Packages/Integration/`
- `src/integration/Alpha.m`
- `src/external/ccapi/`
- `data/`
- `results/`

## Recommended Next Cleanup Execution Order

1. Resolve `nature_final.*` and `paper3_algorithmic_corruption.tex` as manuscript side branches.
2. Review remaining top-level wrappers (`process_data.py`, `run_process.py`, `run_scraper.py`, `report_dataset.py`).
3. Compare `mat-bdm/` against `mathematicabdm/`.
4. Inspect overlapping test-output trees before any provenance pruning.
5. Only after those checks, perform the next mixed document/code cleanup wave.
