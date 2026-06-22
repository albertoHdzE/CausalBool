# Protocol Lineage Review

## Purpose

This document records a second-pass forensic review of the protocol lineage across:

- protocol documents
- `bioPlan*` plans
- `bioProcess*` execution logs
- `docProcess` and `expProcess`
- bitacora-style provenance logs

This is a no-move, no-delete review.

The goal is to identify:

- what level structure actually exists
- where the chain is complete
- where the chain is partial, merged, or missing
- how the repository should be reorganized later without damaging provenance

## Executive Findings

### 1. The repository does not contain one uniform Level 1-8 document chain

The ideal pattern suggested by the project history is:

- `protocol-level-N`
- `bioPlanLev-N`
- `bioProcessLevN`
- `docProcess` / `expProcess` support
- bitacora or execution log

But the actual repository only fits that pattern partially.

### 2. Levels 2-7 mainly live in `doc/newIntPaper/`

Observed major files:

- `bioPlanLev-2.md`
- `bioPlanLev-3.md`
- `bioPlanLev-4.md`
- `bioPlanLev-5.md`
- `bioPlanLev-6.md`
- `bioPlanLev-7.md`
- `bioProcessLev2.tex`
- `bioProcessLev3.tex`
- `bioProcessLev5.tex`
- `bioProcessLev6.tex`
- `bioProcessLev7.tex`

There is also a baseline biological plan and process pair:

- `bioPlan.md`
- `bioProcess.tex`

### 3. Level 8 lives in a different, more disciplined workspace

Level 8 is primarily externalized into `4ClaudeCode/claude-Nature/` and `4ClaudeCode/claude-Nature/paper/`.

Observed chain:

- `4ClaudeCode/claude-Nature/protocol-level-8.md`
- `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md`
- `4ClaudeCode/claude-Nature/paper/bioProcessLev8.tex`
- `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md`

This is the cleanest and most explicit protocol lineage found in the repository.

### 4. `docProcess` and `expProcess` are not level-specific companions

They act as cross-level backbone documents:

- `docProcess.tex`: theory/process backbone for the deterministic framework
- `expProcess.tex`: medium-scale experimental and validation backbone

They are repeatedly referenced as foundational support rather than as one-level artifacts.

### 5. Level 4 is structurally discontinuous

There is a plan document:

- `doc/newIntPaper/bioPlanLev-4.md`

But there is no standalone `bioProcessLev4.tex` in the current tree.

Instead, `bioProcessLev3.tex` explicitly states that `bioProcessLev4.tex` was merged into it and slated for deletion.

This is a real lineage break and should be documented, not silently normalized.

### 6. Level 1 is conceptually present but not preserved as an explicit protocol bundle

Multiple documents refer to a completed "Level 1" foundation, but no clear standalone set was found for:

- `protocol-level-1`
- `bioPlanLev-1`
- `bioProcessLev1`
- `bitacora-lev1`

The closest Level 1 backbone appears to be distributed across:

- `docProcess.tex`
- `expProcess.tex`
- `bioPlan.md`
- `bioProcess.tex`

## Observed Document Roles

### A. Foundational cross-level documents

- `doc/newIntPaper/docProcess.tex`
  - formal theory/process backbone
  - repeatedly referenced by planning and manuscript files
  - best treated as the theory source-of-truth for the pre-Level-8 lineage

- `doc/newIntPaper/expProcess.tex`
  - experimental and validation backbone
  - complements `docProcess`
  - best treated as a cross-level validation source rather than a numbered level artifact

### B. Baseline biological programme documents

- `doc/newIntPaper/bioPlan.md`
  - broad biological application plan bridging `docProcess` to `bioProcess`
  - predates or sits beneath the numbered Level 2-7 sequence

- `doc/newIntPaper/bioProcess.tex`
  - cumulative biological process log
  - appears to be the pre-numbered biological execution log

### C. Numbered protocol plans

- `bioPlanLev-2.md`
  - Level 2 structural simplicity / universality programme

- `bioPlanLev-3.md`
  - Level 3 universal compression + cancer integration

- `bioPlanLev-4.md`
  - contingency reformulation and decision-matrix pivot

- `bioPlanLev-5.md`
  - hybrid structural + dynamical pivot

- `bioPlanLev-6.md`
  - basin-entropy pivot

- `bioPlanLev-7.md`
  - semantic basin fidelity

- `4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md`
  - Nature-grade execution plan with gates, artifact discipline, and explicit bitacora contract

### D. Numbered process logs

- `bioProcessLev2.tex`
  - dedicated Level 2 log

- `bioProcessLev3.tex`
  - mixed document covering Level 3 and merged Level 4 material

- `bioProcessLev5.tex`
  - dedicated Level 5 log

- `bioProcessLev6.tex`
  - dedicated Level 6 log

- `bioProcessLev7.tex`
  - dedicated Level 7 log

- `4ClaudeCode/claude-Nature/paper/bioProcessLev8.tex`
  - dedicated Level 8 log

### E. Protocol documents

- `doc/newIntPaper/towardsNature/protocols/protocol.md`
  - broad transitional protocol tied to `docProcess`

- `doc/newIntPaper/towardsNature/protocols/protocol-level-2.md`
  - explicit protocol draft for Level 2-era Nature framing

- `doc/newIntPaper/towardsNature/protocols/protocol-level-3.md`
  - explicit protocol draft for Level 3-era framing

- `4ClaudeCode/claude-Nature/protocol-level-8.md`
  - explicit Level 8 submission strategy

Notably absent:

- no explicit `protocol-level-4.md`
- no explicit `protocol-level-5.md`
- no explicit `protocol-level-6.md`
- no explicit `protocol-level-7.md`

### F. Bitacora / provenance logs

- `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md`
  - the only clearly formalized bitacora in the level lineage
  - includes commands, outputs, checksums, and interpretation

For Levels 2-7, provenance is mainly embedded inside:

- `bioProcessLev*.tex`
- planning text
- manuscript assembly documents such as `doc/finalpaper/together.tex` and `together_full.tex`

## Current Relationship Model

The best-fit lineage model is:

1. Foundational layer
   - `docProcess`
   - `expProcess`

2. Baseline biological programme
   - `bioPlan.md`
   - `bioProcess.tex`

3. Numbered protocol lineage
   - `bioPlanLev-2` through `bioPlanLev-8`
   - `bioProcessLev2`, `bioProcessLev3+4`, `bioProcessLev5`, `bioProcessLev6`, `bioProcessLev7`, `bioProcessLev8`

4. Transitional Nature protocol drafts
   - `towardsNature/protocols/*`

5. Mature Nature execution regime
   - `protocol-level-8`
   - `bioPlanLev-8`
   - `bioProcessLev8`
   - `bitacora-lev8`

## Structural Irregularities That Matter For Cleanup

### 1. Missing standalone Level 1 bundle

Risk:

- A later cleanup might incorrectly assume Level 1 was lost or irrelevant.

Interpretation:

- Level 1 likely survives indirectly inside the foundational `docProcess` / `expProcess` / base biological plan-process pair.

### 2. Level 4 process log was merged away

Evidence:

- `bioProcessLev3.tex` explicitly states that `bioProcessLev4.tex` was merged into it and slated for deletion.

Risk:

- A naive folder cleanup could try to "complete" the numbering by inventing false symmetry.

Interpretation:

- The current source-of-truth for Level 4 process content is probably `bioProcessLev3.tex`, not a missing file that must be recreated.

### 3. Protocol files are not present for every level

Risk:

- Protocol naming suggests a complete numbered series, but the repository does not contain one.

Interpretation:

- `protocol-level-*` documents were produced at selected turning points, not as a strict every-level rule.

### 4. Bitacora discipline becomes explicit only at Level 8

Risk:

- A future cleanup could mistakenly search for `bitacora-lev2` through `bitacora-lev7` as if they should exist.

Interpretation:

- Pre-Level-8 provenance is diffuse and embedded in process logs, plans, and manuscript assembly files.

### 5. `doc/finalpaper/together.tex` and `together_full.tex` act as lineage condensers

Role:

- They summarize and re-integrate multiple `bioPlan` and `bioProcess` levels into a single manuscript assembly stream.

Risk:

- They are not primary protocol files, but they do preserve cross-level relationships that may no longer be explicit elsewhere.

## Proposed Future Reorganization

This is a proposal only.
It should not be executed automatically without review.

### Proposed conceptual order

1. `foundation/`
   - `docProcess`
   - `expProcess`

2. `bio-baseline/`
   - `bioPlan.md`
   - `bioProcess.tex`

3. `levels/level-2/` through `levels/level-8/`
   - each level containing:
     - plan
     - process log
     - protocol if one exists
     - provenance log if one exists

4. `transitional-protocols/`
   - `towardsNature/protocols/*`

5. `manuscript-synthesis/`
   - `doc/finalpaper/together.tex`
   - `doc/finalpaper/together_full.tex`
   - related assembly notes

### Proposed normalized mapping per level

- Level 1:
  - mark as `implicit / distributed`
  - do not invent missing files

- Level 2:
  - plan + process + transitional protocol draft

- Level 3:
  - plan + process + transitional protocol draft

- Level 4:
  - plan present
  - process merged into Level 3 process log
  - mark as `merged process lineage`

- Level 5:
  - plan + process

- Level 6:
  - plan + process

- Level 7:
  - plan + process

- Level 8:
  - protocol + plan + process + explicit bitacora

## Cleaning Recommendation

### What should happen now

- Keep the current files in place.
- Preserve the evidence of uneven evolution.
- Record the lineage explicitly in mapping docs before any move or deletion.

### What should not happen yet

- Do not flatten everything into a fake level-symmetric directory.
- Do not delete `together.tex` / `together_full.tex` before extracting their lineage role.
- Do not assume missing `protocol-level-4/5/6/7` or `bitacora-lev2..7` files are accidental clutter.
- Do not create placeholder files just to make the numbering look tidy.

### Best future cleanup strategy

1. Add metadata or README-level indexes first.
2. Mark each level as:
   - explicit
   - merged
   - implicit
   - transitional
3. Only after that, consider directory normalization or archival moves.
4. Treat Level 8 as the model for provenance discipline, but not as evidence that earlier levels should be retrofitted into the same file pattern.

## Safe Conclusions

- The protocol lineage is real, but irregular.
- The most complete execution chain is Level 8.
- `docProcess` and `expProcess` are foundational cross-level documents, not numbered duplicates.
- Level 4 is represented by a plan file plus merged process content inside `bioProcessLev3.tex`.
- Level 1 is conceptually present but not preserved as a standalone numbered bundle.

## Companion Manifest

For cleanup-ready classification at the artifact level, use:

- `mapping/protocol_manifest.md`
- `mapping/protocol_manifest.csv`

These provide per-artifact roles, lineage status, source-of-truth assessment, and suggested later actions.
