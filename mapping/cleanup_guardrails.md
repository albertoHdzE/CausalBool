# Cleanup Guardrails

## Goal

Future cleanup must be surgical.

The repository mixes:

- source code
- legacy code
- vendor code
- datasets
- generated results
- compiled manuscripts
- scratch diagnostics

Because of that, deleting by "looks unused" would be unsafe.

## Hard No-Delete Rules For Now

### 1. Do not delete legacy `Alpha.m` yet

Protected file:

- `src/integration/Alpha.m`

Reason:

- Packaged Mathematica files in `src/Packages/Integration/` still import it directly.

Required before deletion:

- Migrate implementation into the packaged layer or replace imports.

### 2. Do not delete `src/external/ccapi/` as if it were local duplication

Protected directory:

- `src/external/ccapi/`

Reason:

- It is a vendored external project with its own internal structure.

Required before deletion:

- Confirm whether any local workflows still depend on it and whether it should be replaced by a dependency manager reference.

### 3. Do not delete `data/` or `results/` based only on size or clutter

Protected directories:

- `data/`
- `results/`
- `workspaces/claude-nature/paper/results/`

Reason:

- These may be the only provenance evidence for published or manuscript-level analyses.

Required before deletion:

- Regeneration path, provenance, and reproducibility scope must be documented.

### 4. Do not delete paper branches before choosing a source of truth

Protected directories:

- `doc/newIntPaper/`
- `doc/finalpaper/`
- `workspaces/claude-nature/paper/`

Reason:

- These are overlapping but not interchangeable.
- Some are planning archives, some are manuscript assembly trees, and some include executable analysis code.

Required before deletion:

- Decide whether the repo keeps:
  - one active paper tree plus archival snapshots
  - or one frozen reproducibility tree plus one manuscript tree

### 4B. Do not normalize protocol levels into a fake symmetric series

Protected areas:

- `doc/newIntPaper/`
- `doc/finalpaper/`
- `workspaces/claude-nature/`
- `workspaces/claude-nature/paper/`

Reason:

- The protocol lineage is historically real but structurally uneven.
- Level 1 appears distributed rather than preserved as a standalone bundle.
- Level 4 process content appears merged into `bioProcessLev3.tex`.
- Explicit `protocol-level-*` documents exist only for selected stages.
- Level 8 introduces a much stricter provenance regime than earlier levels.

Required before deletion or reorganization:

- Use `mapping/protocol_lineage_review.md` to classify each document as:
  - foundational
  - baseline
  - level-specific
  - merged
  - condenser
  - provenance log
- Preserve historical asymmetry unless there is an explicit archival plan.
- Do not create placeholder files or force a Level 1-8 one-folder-per-level structure before the lineage is formally indexed.

## Low-Risk Candidates Later, But Not Yet Auto-Delete

### 5. Top-level debug and inspection scripts

Examples:

- `debug_ccapi.py`
- `debug_sbml.py`
- `debug_lambda.m`
- `debug_symbolic.m`
- `explore_ccapi.py`
- `inspect_ccapi.py`
- `inspect_ccapi_methods.py`
- `test_bdm.py`
- `test_bdm_debug.m`
- `test_bdm.json`

Why they are lower risk:

- They look like ad hoc diagnostics rather than shared production modules.

Why they are still not zero risk:

- They may preserve the only record of how previous bugs were investigated.

Required before deletion:

- Check whether their knowledge should be converted into docs, tests, or issue notes first.

### 6. Draft and incomplete analysis files

Example:

- `src/analysis/optimize_alpha_draft.py`

Why lower risk:

- It appears incomplete.

Required before deletion:

- Compare to `optimize_alpha.py` and confirm there is no unique experimental path or note inside.

### 7. Build and compile byproducts

Examples:

- `.aux`
- `.log`
- `.fls`
- `.fdb_latexmk`
- `.synctex.gz`

Why lower risk:

- These are generated intermediates.

Required before deletion:

- Confirm they are not being intentionally archived as evidence in a paper branch.

## Special Handling Zones

### 8. `index.js` and `cc_index.js`

Handling:

- Treat as generated bundles first, not source files.

Before deletion:

- Identify who produced them.
- Check whether a static demo or documentation page still expects them.

### 9. `mat-bdm/` and `mathematicabdm/`

Handling:

- Treat as historical mathematical workspace until content overlap is measured.

Before deletion:

- Compare repeated tables, notebooks, and lookup files such as `squares2Dsize1to4.m`.

### 10. `src/causal/`

Handling:

- Treat as legacy conceptual ancestor unless a live import path references it.

Before deletion:

- Search for references in Mathematica workflows, notebooks, scripts, and docs.

### 11. `tests/` vs `results/tests/` vs `4ClaudeCode/.../results/tests/`

Handling:

- Treat as a three-way provenance problem.

Before deletion:

- Determine which directories contain:
  - source tests
  - canonical outputs
  - paper snapshots

## Recommended Cleanup Order

1. Freeze paper-tree policy and source-of-truth roles.
2. Classify source-of-truth analysis code tree.
3. Decouple packaged Mathematica code from legacy imports.
4. Separate vendored code from native code in cleanup planning.
5. Mark generated artifacts reproducible vs archival.
6. Only then prune drafts, scratch scripts, compiled outputs, and stale copies.

Working policy references:

- `mapping/paper_tree_policy.md`
- `mapping/source_of_truth_index.md`
- `mapping/protocol_manifest.md`

## Minimum Verification Checklist Per Deletion Candidate

For each candidate file or directory, answer all of these:

1. Is it source, legacy, external, generated, or archival?
2. Is it imported, executed, or referenced by another active file?
3. Does it contain unique logic or just a copy/export of something else?
4. Does it preserve provenance for a figure, result, or manuscript claim?
5. Can it be regenerated exactly?
6. If removed, what workflow breaks?

If any answer is unknown, the candidate is not ready for deletion.

## Current Safe Conclusions

These are safe conclusions from the mapping pass so far.

- `src/Packages/Integration/` is important and should be preserved.
- `src/integration/` contains both critical reusable modules and cleanup candidates.
- `workspaces/claude-nature/paper/` is operational, not merely archival text.
- `src/external/ccapi/` must be handled as vendor code.
- `index.js` and `cc_index.js` are likely build artifacts.
- top-level debug scripts are likely scratch utilities.
- manuscript and result trees are too entangled to clean safely without a second pass focused on provenance.
