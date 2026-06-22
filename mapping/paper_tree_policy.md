# Paper Tree Policy

## Purpose

This policy defines how the repository should treat the overlapping paper-related trees before any further reorganization or deletion.

It is intended to answer four questions:

1. Which tree is the active writing tree?
2. Which tree is the active reproducibility tree?
3. Which trees are historical synthesis or archive?
4. How should compiled PDFs be handled?

This policy is still preparatory.
It does not itself move or delete files.

## Policy Summary

### Active writing tree

The current active Nature-facing writing source should be treated as:

- `doc/finalpaper/nature_draft.tex`

Supporting writing branch:

- `doc/finalpaper/final.tex`
- `doc/finalpaper/sections/*.tex`

Interpretation:

- `nature_draft.tex` is the strongest current manuscript source for the Nature-facing narrative because Level 8 plan/provenance files explicitly point to it as the manuscript receiving locked text and definition updates.
- `final.tex` is a valid manuscript branch, but it is not currently the strongest Nature-facing source-of-truth in the same way.

### Active reproducibility tree

The current active reproducibility tree should be treated as:

- `4ClaudeCode/claude-Nature/paper/`

Especially:

- `4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py`
- `4ClaudeCode/claude-Nature/paper/code/reproduce_all.py`
- `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md`
- `4ClaudeCode/claude-Nature/paper/bioProcessLev8.tex`
- `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md`

Interpretation:

- This branch is the operational paper workspace.
- It is the best current home of executable paper pipelines, figure-generation logic, and explicit provenance.

### Historical synthesis tree

The current historical synthesis / integration tree should be treated as:

- `doc/finalpaper/together.tex`
- `doc/finalpaper/together_full.tex`
- `doc/finalpaper/assemble_manuscript.py`

Interpretation:

- These files are not the primary writing source.
- They are valuable condensers that preserve cross-level integration and assembly logic.
- They should not be deleted until their lineage-preserving role is fully extracted or superseded.

### Foundational and pre-Level-8 history tree

The current foundational and pre-Level-8 planning/process tree should be treated as:

- `doc/newIntPaper/`

Especially:

- `docProcess.tex`
- `expProcess.tex`
- `bioPlan.md`
- `bioProcess.tex`
- `bioPlanLev-*`
- `bioProcessLev*`
- `towardsNature/`

Interpretation:

- This is not the active reproducibility branch for the current Level 8 paper.
- It is the primary historical and conceptual lineage tree and remains essential for context, theory, and protocol evolution.

## Role Assignment

### Tree A: Active writing

Directory:

- `doc/finalpaper/`

Primary file:

- `nature_draft.tex`

Secondary active branch:

- `final.tex`

Allowed future actions:

- reorganize only after preserving branch distinctions
- keep section files paired with `final.tex`
- do not merge `nature_draft.tex` and `final.tex` by assumption alone

### Tree B: Active reproducibility

Directory:

- `4ClaudeCode/claude-Nature/paper/`

Primary functions:

- run analysis pipelines
- generate locked figures and result packets
- preserve Level 8 provenance

Allowed future actions:

- remove generated clutter only when reproducibility is confirmed
- do not collapse this tree into `doc/finalpaper/`
- do not treat code here as archival notes
- do not relocate this workspace into a “common folder” until path-coupling has been reduced and a migration note is defined for provenance documents

### Tree C: Historical synthesis

Directory:

- `doc/finalpaper/`

Files:

- `together.tex`
- `together_full.tex`
- assembly scripts

Primary functions:

- cross-level condensation
- manuscript synthesis
- historical integration evidence

Allowed future actions:

- archive only after explicit extraction/indexing
- never delete as duplicates without lineage-preservation review

### Tree D: Foundational lineage

Directory:

- `doc/newIntPaper/`

Primary functions:

- theory backbone
- experimental backbone
- baseline biological programme
- Level 2-7 planning and process evolution
- transitional Nature protocols

Allowed future actions:

- index and classify
- archive structurally if needed later
- do not flatten into a fake level-symmetric tree

## PDF Retention Policy

Compiled PDFs are not all the same.

They should be separated into three classes.

### Class 1: Protected provenance PDFs

Examples:

- `bioProcessLev8.pdf` when paired with bitacora/checksum use
- any PDF explicitly referenced in provenance or manuscript-readiness decisions

Policy:

- keep until provenance extraction or locked-manifest migration is complete

### Class 2: Review-support PDFs

Examples:

- `doc/newIntPaper/docProcess.pdf`
- `doc/newIntPaper/expProcess.pdf`
- `doc/newIntPaper/bioProcessLev*.pdf`
- `doc/finalpaper/final.pdf`
- `doc/finalpaper/nature_draft.pdf`

Policy:

- keep for now
- later choose one of two models:
  - `archival evidence`
  - `reproducible byproduct`

Condition before deletion:

- the corresponding `.tex` source must be canonical or preserved
- the build path must be documented
- the PDF must not be the only reviewed or cited version still in use

### Class 3: Disposable build byproducts

Examples:

- `.aux`
- `.log`
- `.fls`
- `.fdb_latexmk`
- `.run.xml`
- `.toc`

Policy:

- safe cleanup candidates once not intentionally archived

## Operational Rules For Next Cleanup Phase

### Rule 1

Do not delete any `.tex` manuscript file until its role is classified as one of:

- active writing
- historical synthesis
- foundational lineage
- side branch
- obsolete archive

### Rule 2

Do not delete any PDF solely because a `.tex` exists.

Check whether the PDF is:

- provenance-bearing
- review-supporting
- or only a disposable build output

### Rule 3

Do not merge the active writing tree and active reproducibility tree into one directory.

Reason:

- their functions are different
- the Level 8 branch explicitly couples code, figures, plan, and bitacora
- the `doc/finalpaper/` branch is manuscript-centered

### Rule 4

Do not delete `together.tex` or `together_full.tex` before extracting their synthesis role.

Reason:

- they preserve lineage relationships that are not fully encoded elsewhere

### Rule 5

Do not demote `doc/newIntPaper/` to mere clutter.

Reason:

- it remains the foundational lineage tree for theory, experiments, and the Level 2-7 protocol evolution

## Proposed Future Implementation Order

1. Freeze this policy as the working repository rule.
2. Produce a deletion/move candidate table against this policy.
3. Start with the safest actions:
   - disposable build byproducts
   - clearly obsolete archived variants
   - redundant generated outputs with documented regeneration
4. Only then consider structural moves in manuscript/history trees.
5. Leave cross-tree code consolidation for a later pass after the document tree is stabilized.

## Concrete Current Recommendation

### Keep as active writing

- `doc/finalpaper/nature_draft.tex`

### Keep as active alternate writing branch

- `doc/finalpaper/final.tex`
- `doc/finalpaper/sections/*.tex`

### Keep as active reproducibility

- `4ClaudeCode/claude-Nature/paper/`

### Keep as historical synthesis

- `doc/finalpaper/together.tex`
- `doc/finalpaper/together_full.tex`
- associated assembly scripts

### Keep as foundational lineage

- `doc/newIntPaper/`

### Treat as future policy decision, not immediate deletion

- compiled manuscript PDFs

## Decision Boundary

After this policy, the repository is ready for the next stage:

- a controlled move/delete proposal aligned to explicit roles

That proposal should cite this document together with:

- `mapping/protocol_lineage_review.md`
- `mapping/protocol_manifest.md`
- `mapping/source_of_truth_index.md`
