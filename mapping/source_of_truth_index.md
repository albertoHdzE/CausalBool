# Source Of Truth Index

## Purpose

This index identifies the current best source-of-truth files for the document, protocol, manuscript, and reproducibility layers.

It is still preparatory work.
It does not authorize deletion by itself.

## Interpretation Rule

`source-of-truth` here is purpose-specific.

A file can be canonical for one purpose and non-canonical for another.

Examples:

- a `.tex` file can be the canonical manuscript source
- its `.pdf` can still be an important archival artifact
- a condenser file can be non-canonical for writing but critical for historical reconstruction

## Index Table

| Domain | Purpose | Canonical Source | Supporting Sources | Non-Canonical But Important | Notes | Cleanup Implication |
| --- | --- | --- | --- | --- | --- | --- |
| `foundation-theory` | Formal deterministic theory/process backbone | `doc/newIntPaper/docProcess.tex` | `doc/newIntPaper/documents.md`, `doc/newIntPaper/plan.md` | `doc/newIntPaper/docProcess.pdf`, `doc/finalpaper/sections/theory.tex`, `doc/finalpaper/together_full.tex` | `docProcess.tex` is the most repeatedly referenced theory/process source across planning and manuscript assembly. | Keep as protected source; derived integrations should not replace it silently. |
| `foundation-experiments` | Cross-level experimental/method backbone | `doc/newIntPaper/expProcess.tex` | `doc/newIntPaper/plan.md`, `doc/newIntPaper/FigureIndex.md` | `doc/newIntPaper/expProcess.pdf`, `doc/finalpaper/sections/methods.tex`, `doc/finalpaper/together_full.tex` | `expProcess.tex` acts as a foundational experimental log, not a numbered level artifact. | Keep as protected source; treat compiled PDF as companion artifact. |
| `bio-baseline-plan` | Base biological programme definition before numbered levels | `doc/newIntPaper/bioPlan.md` | `doc/newIntPaper/bioProcess.tex` | `doc/finalpaper/together.tex`, `doc/finalpaper/together_full.tex` | This is the baseline bridge from deterministic framework to biological application. | Keep and index; do not bury it under numbered levels. |
| `bio-baseline-process` | Base biological execution log before numbered levels | `doc/newIntPaper/bioProcess.tex` | `doc/newIntPaper/bioPlan.md` | `doc/newIntPaper/bioProcess.pdf`, `doc/finalpaper/together.tex` | Pre-numbered cumulative biological process log. | Keep and index; PDF is companion, not primary. |
| `levels-2-7-plans` | Numbered Level 2-7 plan lineage | `doc/newIntPaper/bioPlanLev-2.md` through `bioPlanLev-7.md` | `mapping/protocol_manifest.md`, `mapping/protocol_lineage_review.md` | `doc/finalpaper/together.tex`, `doc/finalpaper/together_full.tex` | These are the primary numbered pre-Level-8 plans. | Keep as level sources; do not replace with condensers. |
| `levels-2-7-process` | Numbered Level 2-7 process lineage | `doc/newIntPaper/bioProcessLev2.tex`, `bioProcessLev3.tex`, `bioProcessLev5.tex`, `bioProcessLev6.tex`, `bioProcessLev7.tex` | associated plan files | compiled PDFs, `together.tex`, `together_full.tex` | Level 4 process content is represented through merged material in `bioProcessLev3.tex`. | Keep as protected lineage; do not infer missing symmetry. |
| `transitional-protocols` | Transitional Nature-framing protocols | `doc/newIntPaper/towardsNature/protocols/protocol.md`, `protocol-level-2.md`, `protocol-level-3.md` | `doc/newIntPaper/towardsNature/planning/masterplan.md`, review notes | manuscript condensers and archived AI drafts | These are transitional protocol artifacts, not the main numbered plan chain. | Archive-class, but preserve until the lineage is fully stabilized. |
| `level-8-protocol` | Mature Nature protocol specification | `4ClaudeCode/claude-Nature/protocol-level-8.md` | `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md` | `doc/finalpaper/nature_draft.tex` | Best explicit protocol-stage artifact in the repository. | Treat as protected reference model. |
| `level-8-plan` | Mature Nature execution plan | `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md` | `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md`, `bioProcessLev8.tex` | `doc/finalpaper/nature_draft.tex` | The strongest execution-contract document in the project. | Treat as protected reference model. |
| `level-8-process` | Mature Nature process report | `4ClaudeCode/claude-Nature/paper/bioProcessLev8.tex` | `bioPlanLev-8.md`, `bitacora-lev8.md` | compiled `bioProcessLev8.pdf` when present | Process artifact for Level 8 with locked definitions and artifact mapping. | Treat as protected reference model. |
| `level-8-provenance` | Run-by-run execution provenance | `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md` | `bioPlanLev-8.md`, `bioProcessLev8.tex`, `paper/code/*.py` | none of the pre-Level-8 logs are equivalent | This is the only fully explicit numbered bitacora chain. | Never collapse into summary docs without preserving checksum-grade provenance. |
| `nature-manuscript-active` | Current active Nature-facing manuscript text | `doc/finalpaper/nature_draft.tex` | `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md`, `bitacora-lev8.md` | `nature_draft.pdf`, `nature_final.tex`, `paper3_algorithmic_corruption.tex` | Level 8 plan and bitacora explicitly point to `nature_draft.tex` as the manuscript receiving locked text. | Treat as current Nature manuscript source unless superseded by an explicit later contract. |
| `nature-manuscript-sidebranch` | Alternate standalone Nature manuscript branch | `doc/finalpaper/nature_final.tex` | `doc/finalpaper/nature_final.pdf` | `nature_draft.tex` | Distinct manuscript branch centered on a larger corpus and "Algorithmic Cost of Function" framing; not the branch the Level 8 plan explicitly targets. | Preserve as a side branch until manuscript-branch policy becomes explicit. |
| `sectioned-manuscript` | Section-based manuscript assembly in `finalpaper` | `doc/finalpaper/final.tex` | `doc/finalpaper/sections/*.tex`, `references.bib` | `final.pdf`, `final-draft.tex`, `transform_to_academic.py` | `final.tex` is the canonical section-based assembly source in `doc/finalpaper/`. | Keep sections + `final.tex` together; avoid deleting sections after text extraction assumptions. |
| `section-files` | Modular section text for `final.tex` | `doc/finalpaper/sections/abstract.tex` through `discussion.tex` | `final.tex` | `together.tex`, `together_full.tex` | These are primary for the sectioned manuscript branch, not mere copies. | Protect as active source for the `final.tex` branch. |
| `manuscript-condensers` | Historical integrated manuscript condensers | `doc/finalpaper/together.tex`, `doc/finalpaper/together_full.tex` | `assemble_manuscript.py` | compiled `together_full.pdf` | These are not canonical writing sources, but they preserve cross-level aggregation and lineage evidence. | Keep until extraction/indexing is complete; do not delete as “duplicates.” |
| `assembly-scripts` | Manuscript assembly/transformation logic | `doc/finalpaper/assemble_manuscript.py`, `transform_to_academic.py`, `compile.sh` | `final.tex`, `together.tex`, `together_full.tex` | generated PDFs | These scripts encode how different manuscript branches are built or transformed. | Keep until manuscript branch policy is finalized. |
| `active-paper-code` | Executable reproducibility code for the Nature paper branch | `4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py`, `reproduce_all.py` | `essentiality_analysis.py`, `requirements.txt` | overlapping `src/analysis/*.py` scripts | This is the operational code root of the Level 8 paper workspace. | Treat as protected active reproducibility code until source/code branch boundaries are decided. |
| `active-paper-figures` | Locked manuscript-facing outputs for the Nature paper branch | `4ClaudeCode/claude-Nature/paper/figures/*` | `bitacora-lev8.md`, `analysis_pipeline.py` | analogous figures under `doc/finalpaper/figures/` | These are evidence and outputs, not primary textual sources. | Do not prune before reproducibility/output policy is formalized. |
| `level-8-paper-support-results` | Restored paper-support outputs with explicit provenance value | `4ClaudeCode/claude-Nature/paper/results/wetlab_readiness_pack.md`, `krb_route_decision.md`, `theory_to_computation_mapping.md`, `nature_readiness_assessment.md`, `submission_pack/*` | corresponding `.json` files, `bioPlanLev-8.md`, `bitacora-lev8.md` | duplicated `paper/results/tests/*` when present | These are not raw build clutter; they encode frozen decisions, theory/computation boundaries, collaboration packets, and submission support explicitly referenced by Level 8 governance documents. | Keep as protected paper-support artifacts; treat separately from bulk duplicated test outputs. |
| `paper-tex-sidebranch` | Alternative paper manuscript branch in Level 8 workspace | `4ClaudeCode/claude-Nature/paper/paper3_algorithmic_corruption.tex` | `paper/README.md` | compiled PDF companion when present | Important manuscript branch, but not currently the main source referenced by the Level 8 plan in the same way as `nature_draft.tex`. | Keep as active side branch until paper-branch policy is explicit. |
| `generated-pdf-companions` | Compiled companions of `.tex` sources | corresponding `.pdf` next to `.tex` | source `.tex` files | none | Important for review/provenance, but generally not the writing source. | Decide later whether they are archival evidence or reproducible byproducts. |

## Working Conclusions

### 1. There is not one single manuscript source of truth for the whole repository

There are at least four distinct canonical layers:

- foundational theory/process
- baseline and numbered biological programme
- active Nature manuscript text
- active Level 8 reproducibility code/provenance

### 2. `nature_draft.tex` is currently the strongest candidate for the active Nature manuscript source

Reason:

- Level 8 planning and provenance explicitly point to it as the manuscript being updated with locked narrative and definitions.

### 3. `final.tex` is canonical only inside the section-based `doc/finalpaper/` assembly branch

It should not be confused with the current Level 8 Nature-facing manuscript source.

### 4. `together.tex` and `together_full.tex` are important, but not canonical writing sources

They are best treated as:

- condensers
- historical synthesis artifacts
- lineage-preservation documents

### 5. `4ClaudeCode/claude-Nature/paper/code/` is the active reproducibility root for Level 8

It should not be treated as just auxiliary code until the source/code overlap with `src/analysis/` is explicitly resolved.

## Recommended Next Step

Before any reorganization or deletion in document/manuscript areas:

1. freeze a paper-tree policy:
   - which branch is active writing
   - which branch is active reproducibility
   - which branches are historical synthesis
2. decide PDF retention policy:
   - archival evidence
   - or reproducible byproduct
3. only then propose moves or removals
