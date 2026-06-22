# Protocol Manifest

## Purpose

This manifest converts the protocol-lineage review into a cleanup-ready artifact register.

It does not recommend immediate movement or deletion.
It exists to support later decisions with explicit classifications.

## Column Definitions

- `Artifact ID`: stable manifest identifier
- `Level Scope`: `foundation`, `baseline`, `L2`, `L3`, `L4`, `L5`, `L6`, `L7`, `L8`, or `multi-level`
- `Role`: one of `foundational`, `baseline`, `plan`, `process-log`, `protocol`, `provenance-log`, `condenser`, `generated-companion`, or `implicit-gap-marker`
- `Lineage Status`: one of `explicit`, `merged`, `implicit`, `transitional`, or `compiled-companion`
- `Source-of-Truth`: current best assessment of whether the file is primary, secondary, archival, or generated
- `Later Action`: suggested future handling, not an instruction for immediate cleanup

## Manifest Table

| Artifact ID | Level Scope | Role | Lineage Status | Source-of-Truth | Later Action | Path | Notes |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `FOUND-DOC-001` | `foundation` | `foundational` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/docProcess.tex` | Theory/process backbone repeatedly referenced by plans and manuscript assembly. |
| `FOUND-DOC-001-PDF` | `foundation` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/docProcess.pdf` | Compiled companion of `docProcess.tex`; useful provenance but not primary text source. |
| `FOUND-EXP-001` | `foundation` | `foundational` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/expProcess.tex` | Experimental/validation backbone complementing `docProcess.tex`. |
| `FOUND-EXP-001-PDF` | `foundation` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/expProcess.pdf` | Compiled companion of `expProcess.tex`. |
| `BASE-BIOPLAN-001` | `baseline` | `baseline` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlan.md` | Broad biological programme plan bridging foundational theory to biological application. |
| `BASE-BIOPROC-001` | `baseline` | `baseline` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioProcess.tex` | Pre-numbered cumulative biological process log. |
| `BASE-BIOPROC-001-PDF` | `baseline` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcess.pdf` | Compiled companion of `bioProcess.tex`. |
| `L1-IMPLICIT-001` | `L1` | `implicit-gap-marker` | `implicit` | `distributed` | `document-only` | `<no standalone file>` | Level 1 is conceptually present but distributed across foundational and baseline documents. |
| `L2-PLAN-001` | `L2` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-2.md` | First clearly numbered Nature-track level plan. |
| `L2-PROC-001` | `L2` | `process-log` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioProcessLev2.tex` | Dedicated Level 2 process log. |
| `L2-PROC-001-PDF` | `L2` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcessLev2.pdf` | Compiled companion of `bioProcessLev2.tex`. |
| `L2-PROT-001` | `L2` | `protocol` | `transitional` | `secondary` | `archive-as-transitional` | `doc/newIntPaper/towardsNature/protocols/protocol-level-2.md` | Transitional Nature protocol draft, not the same role as the main level plan. |
| `L3-PLAN-001` | `L3` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-3.md` | Numbered Level 3 plan introducing universal compression and cancer integration. |
| `L3-PROC-001` | `L3-L4` | `process-log` | `merged` | `primary` | `keep-and-cross-reference` | `doc/newIntPaper/bioProcessLev3.tex` | Acts as the current source of truth for Level 3 plus merged Level 4 process content. |
| `L3-PROC-001-PDF` | `L3-L4` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcessLev3.pdf` | Compiled companion of `bioProcessLev3.tex`. |
| `L3-PROT-001` | `L3` | `protocol` | `transitional` | `secondary` | `archive-as-transitional` | `doc/newIntPaper/towardsNature/protocols/protocol-level-3.md` | Transitional protocol draft for Level 3-era Nature framing. |
| `L4-PLAN-001` | `L4` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-4.md` | Level 4 contingency reformulation plan. |
| `L4-PROC-IMPLICIT-001` | `L4` | `implicit-gap-marker` | `merged` | `redirected` | `document-only` | `<merged into bioProcessLev3.tex>` | No standalone `bioProcessLev4.tex` is present; process lineage was merged into Level 3 process log. |
| `L4-PROT-IMPLICIT-001` | `L4` | `implicit-gap-marker` | `implicit` | `absent` | `document-only` | `<no standalone file found>` | No standalone `protocol-level-4.md` was found. |
| `L5-PLAN-001` | `L5` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-5.md` | Level 5 hybrid-encoding pivot plan. |
| `L5-PROC-001` | `L5` | `process-log` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioProcessLev5.tex` | Dedicated Level 5 process log. |
| `L5-PROC-001-PDF` | `L5` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcessLev5.pdf` | Compiled companion of `bioProcessLev5.tex`. |
| `L5-PROT-IMPLICIT-001` | `L5` | `implicit-gap-marker` | `implicit` | `absent` | `document-only` | `<no standalone file found>` | No standalone `protocol-level-5.md` was found. |
| `L6-PLAN-001` | `L6` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-6.md` | Level 6 basin-entropy pivot plan. |
| `L6-PROC-001` | `L6` | `process-log` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioProcessLev6.tex` | Dedicated Level 6 process log. |
| `L6-PROC-001-PDF` | `L6` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcessLev6.pdf` | Compiled companion of `bioProcessLev6.tex`. |
| `L6-PROT-IMPLICIT-001` | `L6` | `implicit-gap-marker` | `implicit` | `absent` | `document-only` | `<no standalone file found>` | No standalone `protocol-level-6.md` was found. |
| `L7-PLAN-001` | `L7` | `plan` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioPlanLev-7.md` | Level 7 semantic fidelity plan. |
| `L7-PROC-001` | `L7` | `process-log` | `explicit` | `primary` | `keep-and-index` | `doc/newIntPaper/bioProcessLev7.tex` | Dedicated Level 7 process log. |
| `L7-PROC-001-PDF` | `L7` | `generated-companion` | `compiled-companion` | `generated` | `keep-until-output-policy` | `doc/newIntPaper/bioProcessLev7.pdf` | Compiled companion of `bioProcessLev7.tex`. |
| `L7-PROT-IMPLICIT-001` | `L7` | `implicit-gap-marker` | `implicit` | `absent` | `document-only` | `<no standalone file found>` | No standalone `protocol-level-7.md` was found. |
| `TRANS-PROT-001` | `multi-level` | `protocol` | `transitional` | `secondary` | `archive-as-transitional` | `doc/newIntPaper/towardsNature/protocols/protocol.md` | Transitional protocol text tied to the foundational framework and the move toward Nature framing. |
| `L8-PROT-001` | `L8` | `protocol` | `explicit` | `primary` | `keep-as-reference-model` | `workspaces/claude-nature/protocol-level-8.md` | Most explicit protocol-stage document in the repository. |
| `L8-PLAN-001` | `L8` | `plan` | `explicit` | `primary` | `keep-as-reference-model` | `workspaces/claude-nature/paper/bioPlanLev-8.md` | Mature Nature-grade plan with gates and bitacora discipline. |
| `L8-PROC-001` | `L8` | `process-log` | `explicit` | `primary` | `keep-as-reference-model` | `workspaces/claude-nature/paper/bioProcessLev8.tex` | Dedicated Level 8 process log with artifact-aware execution framing. |
| `L8-BIT-001` | `L8` | `provenance-log` | `explicit` | `primary` | `keep-as-reference-model` | `workspaces/claude-nature/paper/bitacora-lev8.md` | Only clearly formalized bitacora in the numbered lineage. |
| `COND-MAN-001` | `multi-level` | `condenser` | `explicit` | `secondary` | `keep-until-extracted` | `doc/finalpaper/together.tex` | Manuscript assembly condenser summarizing multiple plans and process logs. |
| `COND-MAN-002` | `multi-level` | `condenser` | `explicit` | `secondary` | `keep-until-extracted` | `doc/finalpaper/together_full.tex` | Larger lineage condenser with integrated cross-level narrative and historical references. |

## Manifest-Based Conclusions

### 1. The cleanest complete chain is Level 8

Level 8 is the only level with a clearly explicit set of:

- protocol
- plan
- process log
- provenance log

This makes it a reference model for future indexing, not a template that earlier levels should be forced to imitate retroactively.

### 2. Level 4 should be treated as merged, not missing

The absence of `bioProcessLev4.tex` should not trigger reconstruction or placeholder creation.

The manifest classifies Level 4 process state as:

- planned explicitly
- processed via merge into `bioProcessLev3.tex`

### 3. Level 1 should be treated as distributed, not absent

The manifest marks Level 1 as an `implicit-gap-marker`.

This is deliberate:

- the intellectual content is present
- the standalone numbered artifact bundle is not

### 4. Condensers are not duplicates in the narrow sense

`together.tex` and `together_full.tex` should not be treated as disposable copies until their extracted source boundaries are defined.

They preserve cross-level aggregation that is not encoded cleanly elsewhere.

## Proposed Future Usage

This manifest should be used before any future reorganization of protocol/manuscript materials.

Recommended next action after this manifest:

1. add a `source_of_truth_index.md` for protocol/manuscript areas
2. decide whether generated PDF companions are archival or disposable
3. only then consider folder normalization
