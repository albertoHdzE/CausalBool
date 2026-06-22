# Duplication Register

## Purpose

This register lists overlap zones that matter for a future cleanup.

The key question is not only "what is duplicated?" but also:

- which copy is the likely source of truth
- whether the overlap is active, historical, generated, or vendored
- what must be verified before deleting or merging anything

## High-Risk Overlap Zones

### 1. Packaged Mathematica facade vs legacy implementation

Files:

- `src/Packages/Integration/Alpha.m`
- `src/Packages/Integration/Experiments.m`
- `src/integration/Alpha.m`

Evidence:

- `src/Packages/Integration/Alpha.m` is a package facade that still calls `Get["src/integration/Alpha.m"]`.
- `src/Packages/Integration/Experiments.m` also imports `src/integration/Alpha.m`.

Interpretation:

- This is not redundant duplication yet; it is an active dependency bridge.
- Deleting `src/integration/Alpha.m` would likely break packaged Mathematica workflows.

Cleanup rule:

- Do not remove legacy `Alpha.m` until its implementation is migrated or the packaged layer is rewritten to be self-contained.

### 2. Current GRN ingestion pipeline vs manuscript-era pipeline copy

Files:

- `src/integration/grn_data_pipeline.py`
- `doc/newIntPaper/towardsNature/grn_data_pipeline.py`

Evidence:

- Both are GRN acquisition/processing pipelines.
- The `doc/newIntPaper/towardsNature/` version is embedded in a planning/manuscript workspace and presents itself as a Nature paper data acquisition pipeline.
- The `src/integration/` version is the operational loader used by top-level wrappers like `process_data.py`.

Interpretation:

- Very likely an ancestor/branch duplication, with one version preserved inside documentation/planning history.

Cleanup rule:

- Treat `doc/newIntPaper/towardsNature/grn_data_pipeline.py` as a historical code artifact unless a live workflow still depends on it.

### 3. Main Python analysis layer vs paper-code layer

Files:

- `src/analysis/*.py`
- `workspaces/claude-nature/paper/code/analysis_pipeline.py`
- `workspaces/claude-nature/paper/code/essentiality_analysis.py`
- `workspaces/claude-nature/paper/code/reproduce_all.py`

Evidence:

- `src/analysis/` contains cancer, DepMap, phase-transition, and essentiality scripts.
- `workspaces/claude-nature/paper/code/analysis_pipeline.py` reimplements many figure-generation and benchmark tasks for the paper branch.
- `essentiality_analysis.py` is another paper-facing analysis layer around essentiality.

Interpretation:

- This is one of the biggest structural overlaps in the repository.
- The paper branch is not just consuming `src/analysis/`; it contains parallel executable analysis code.

Cleanup rule:

- Before any deletion, decide whether the source of truth is:
  - reusable `src/analysis/` code
  - paper-specific reproducibility code under `workspaces/claude-nature/`
  - or a hybrid where `workspaces/claude-nature/` is a frozen reproducibility branch

### 4. Planning/manuscript duplication across `doc/newIntPaper/`, `doc/finalpaper/`, and `4ClaudeCode/`

Directories:

- `doc/newIntPaper/`
- `doc/finalpaper/`
- `workspaces/claude-nature/paper/`

Evidence:

- All three contain manuscript text, figures, planning/protocol material, and compiled outputs.
- `doc/newIntPaper/` contains many phased plan documents.
- `doc/finalpaper/` contains a more consolidated paper assembly.
- `workspaces/claude-nature/paper/` contains another mature manuscript branch with figures and result packs.

Interpretation:

- This is likely a timeline of manuscript evolution plus branch-specific execution, not trivial duplicate garbage.

Cleanup rule:

- Choose a manuscript source-of-truth policy before deleting old paper trees.

### 4B. Protocol-lineage condensation vs source documents

Files:

- `doc/newIntPaper/bioPlan.md`
- `doc/newIntPaper/bioProcess.tex`
- `doc/newIntPaper/bioPlanLev-2.md` through `bioPlanLev-7.md`
- `doc/newIntPaper/bioProcessLev2.tex`, `bioProcessLev3.tex`, `bioProcessLev5.tex`, `bioProcessLev6.tex`, `bioProcessLev7.tex`
- `doc/newIntPaper/docProcess.tex`
- `doc/newIntPaper/expProcess.tex`
- `doc/finalpaper/together.tex`
- `doc/finalpaper/together_full.tex`
- `workspaces/claude-nature/protocol-level-8.md`
- `workspaces/claude-nature/paper/bioPlanLev-8.md`
- `workspaces/claude-nature/paper/bioProcessLev8.tex`
- `workspaces/claude-nature/paper/bitacora-lev8.md`

Evidence:

- `together.tex` and `together_full.tex` explicitly re-integrate multiple `bioPlan` and `bioProcess` levels.
- `docProcess.tex` and `expProcess.tex` are repeatedly referenced as cross-level foundations rather than level-specific duplicates.
- Level 8 has a much cleaner protocol chain than Levels 2-7.
- `bioProcessLev3.tex` states that `bioProcessLev4.tex` was merged into it and slated for deletion.

Interpretation:

- These are not simple duplicates.
- They form a layered lineage:
  - foundational theory/process
  - baseline biological plan/process
  - numbered level plans/process logs
  - manuscript condensers
  - explicit Level 8 provenance chain

Cleanup rule:

- Do not delete or merge protocol-lineage documents by filename similarity alone.
- First classify each file as one of:
  - foundational
  - baseline
  - level-specific
  - merged
  - condenser
  - provenance log
- Use `mapping/protocol_lineage_review.md` as the decision map before any move or deletion in these areas.

### 5. Test result duplication across `results/` and the Level 8 paper workspace

Directories:

- `results/tests/*`
- paper-side outputs under `workspaces/claude-nature/paper/results/*`

Evidence:

- `results/tests/*` is present on disk and is heavily referenced by manuscript condensers such as `doc/finalpaper/together_full.tex`.
- The Level 8 paper workspace retains paper-support outputs under `workspaces/claude-nature/paper/results/`.
- The historical duplicated paper-side `paper/results/tests/` subtree is intentionally absent.

Interpretation:

- This is no longer a missing-materialization problem.
- Paper-support artifacts have been restored and are now explicitly retained under `workspaces/claude-nature/paper/results/`.
- Historical comparison now shows that the old `paper/results/tests/` subtree was a strict subset of the current root `results/tests/` tree: 114 historical paper-side files matched on path against current `results/tests/`, with 0 paper-side uniques and 121 additional files now present only in root `results/tests/`.

Cleanup rule:

- Do not prune `results/tests/` based on a presumed paper-tree duplicate until the status of `paper/results/` is explicitly reconciled.
- Preserve the restored paper-support documents, but keep the historical paper-side `tests/` mirror absent unless a paper-packaging reason emerges that is stronger than the current redundancy evidence.

## Medium-Risk Overlap Zones

### 6. `optimize_alpha.py` vs `optimize_alpha_draft.py`

Files:

- `src/analysis/optimize_alpha.py`
- `src/analysis/optimize_alpha_draft.py`

Evidence:

- The draft file is visibly incomplete and ends with `pass`.
- The non-draft version appears to be the usable implementation.

Interpretation:

- Strong candidate for later cleanup, but low urgency.

Cleanup rule:

- Preserve until the draft is confirmed to contain no unique notes, experiments, or partially migrated logic.

### 7. `mat-bdm/` vs `mathematicabdm/`

Directories:

- `mat-bdm/`
- `mathematicabdm/`

Evidence:

- Both are Mathematica BDM-related workspaces.
- `squares2Dsize1to4.m` appears in both places and the two copies are exact duplicates.
- `mat-bdm/` currently contains only a unique notebook plus that duplicated lookup table.
- `mat-bdm/IntegratedInformationByAlgorithmicDynamics.nb` loads `squares2Dsize1to4.m` from its own directory, so the duplicate table is functionally tied to the notebook's current local execution pattern.
- `mathematicabdm/` is the richer workspace, containing `BDMandNormalizedBDM.nb`, `StringNBDM.nb`, `D3.m`, `D4.m`, `D5.m`, `reducedD2.m`, and its own copy of `squares2Dsize1to4.m`.
- `src/integration/NatureBDM.wl` points to `mathematicabdm/D5.m`.
- Historical Python verification scripts reference both workspaces through stale absolute paths under `CausalBoolIntegration/`, which shows lineage overlap but not a safe modern canonical replacement path.

Interpretation:

- This is confirmed partial duplication, not just suspected overlap.
- `mathematicabdm/` looks like the richer historical table workspace.
- `mat-bdm/` looks like a thinner satellite workspace centered on a unique notebook.
- The duplicate lookup table does not make `mat-bdm/` disposable by itself, because removing or moving it would break the notebook's local load pattern unless the notebook or execution wrapper is modernized.

Cleanup rule:

- Do not remove or collapse either directory yet.
- If future cleanup targets this zone, treat `mathematicabdm/` as the more anchored workspace and resolve the `mat-bdm/IntegratedInformationByAlgorithmicDynamics.nb` dependency first.

### 8. Older causal workspace vs packaged integration workspace

Directories:

- `src/causal/`
- `src/Packages/Integration/`

Evidence:

- Both represent Mathematica-centered formulations of the project.
- The naming suggests `src/causal/` may be an older project-era package/notebook area.

Interpretation:

- Not a literal file-by-file duplicate, but a conceptual predecessor/sibling.

Cleanup rule:

- Trace whether `src/causal/` is referenced anywhere before treating it as archival.

### 9. Top-level process wrappers

Files:

- `process_data.py`
- `run_process.py`
- `run_scraper.py`

Evidence:

- All are thin orchestration entry points into the ingestion/scraping layer.
- They are not duplicates in strict behavior, but they are operationally overlapping wrappers.

Interpretation:

- Possible future consolidation opportunity.

Cleanup rule:

- Keep until a single documented CLI or task runner replaces them.

### 10. Top-level debugging / probing scripts

Files:

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

Evidence:

- These are small, ad hoc, focused inspection scripts.

Interpretation:

- They are likely not duplicates of production logic, but they overlap strongly as exploratory support material.

Cleanup rule:

- Map them as scratch utilities first; decide later whether to archive, merge into docs, or delete.

## Artifact and Generated Duplication

### 11. Large JavaScript bundles

Files:

- `index.js`
- `cc_index.js`

Evidence:

- Both are very large bundled artifacts with Vite-style structure and Cell Collective UI strings.

Interpretation:

- Strong chance of generated near-duplicate outputs.

Cleanup rule:

- Treat them as build artifacts until proven otherwise.
- Compare provenance before deletion if they feed a static demo workflow.

### 12. LaTeX compiled outputs and byproducts

Locations:

- `doc/**/*`
- `workspaces/claude-nature/paper/*`

Evidence:

- Multiple `.pdf`, `.aux`, `.log`, `.fls`, `.fdb_latexmk`, `.synctex.gz` files live beside source `.tex`.

Interpretation:

- Much of this material is generated and duplicative by design.

Cleanup rule:

- Safe cleanup may be possible later, but only after deciding which compiled deliverables must remain archived.

## External Boundary That Must Not Be Misclassified

### 13. Vendored third-party subtree

Directory:

- `src/external/ccapi/`

Evidence:

- Includes its own packaging metadata, CI, tests, docs, requirements, Docker files, and internal sample models.

Interpretation:

- This is not project duplication in the normal sense. It is a vendored external repository.

Cleanup rule:

- Separate all cleanup reasoning for this subtree from the rest of the repo.

## Preliminary Source-of-Truth Hypotheses

These are hypotheses, not deletion decisions.

### Likely source of truth

- Mathematica packaged API: `src/Packages/Integration/`
- reusable Python ingestion/encoder code: `src/integration/`
- reusable support modules: `src/data/`, `src/dynamics/`, `src/complexity/`, `src/stats/`
- current large data corpus: `data/`

### Likely campaign-specific or branch-specific

- `src/analysis/`
- `src/experiments/`
- `workspaces/claude-nature/paper/code/`
- `workspaces/claude-nature/paper/results/`
- `doc/newIntPaper/`
- `doc/finalpaper/`

### Likely historical or scratch

- `src/causal/`
- top-level debug scripts
- notebook files in `src/integration/`
- `optimize_alpha_draft.py`
- parts of `mat-bdm/` and `mathematicabdm/`

## Required Verification Before Cleanup

1. Trace file references into `src/integration/Alpha.m`.
2. Compare `src/integration/grn_data_pipeline.py` and `doc/newIntPaper/towardsNature/grn_data_pipeline.py`.
3. Decide whether paper-code in `workspaces/claude-nature/` is frozen reproducibility code or still active development code.
4. Compare test-result policies under `results/` versus the paper workspace (the historical paper-side test mirror is currently absent by design).
5. Check whether `src/causal/` is still referenced.
6. Compare `mat-bdm/` and `mathematicabdm/` contents before any pruning.
7. Verify whether `index.js` and `cc_index.js` are both needed.
