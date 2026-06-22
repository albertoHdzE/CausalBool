## Purpose

This document records whether and how `4ClaudeCode/claude-Nature/` should be integrated into a common workspace structure, without breaking the active Level 8 reproducibility tree.

This is a planning and risk-analysis artifact. It does not itself imply that a move is safe.

## Current role (source-of-truth)

- `4ClaudeCode/claude-Nature/paper/` is the current active reproducibility workspace for the Level 8 Nature-facing programme.
- It contains executable pipelines, provenance documents, and locked figure/result packets.
- Per policy, this tree must not be collapsed into `doc/finalpaper/`.

## What “integration into a common folder” means here

The goal is not to merge semantics. The goal is to standardize workspace layout so the repo has a small number of top-level “workspaces” with consistent naming, while keeping:

- the active reproducibility tree intact
- provenance references intact (or migrated with mechanical updates)
- execution paths stable

Candidate common destination:

- `workspaces/claude-nature/` (or `workspaces/level8-paper/`) as a first-class workspace root

## Evidence: why an immediate move is unsafe

The tree is referenced by code and documents using the literal path `4ClaudeCode/claude-Nature/...`.

Confirmed examples:

- `src/analysis/KRB_Corruption_Anchors.py` defaults to output under `4ClaudeCode/claude-Nature/paper/figures/...`.
- `src/analysis/Cancer_Corruption.py`, `src/analysis/Phase_Transition_Bio_Overlay.py`, and `src/stats/Bayesian_Meta_Analysis.py` reference the paper figures directory under that path.
- `4ClaudeCode/claude-Nature/paper/bitacora-lev8.md` contains many commands referencing the exact folder location.
- Some paper-support artifacts include absolute file paths under `/Users/.../CausalBool/4ClaudeCode/claude-Nature/...`.

Consequence:

- a naive folder move would silently break defaults, scripts, and provenance paths
- the risk is not data loss, but reproducibility regression and provenance ambiguity

## First migration step (executed)

To make future relocation feasible, the paper pipeline has been adjusted to be location-relative in two minimal ways:

- `paper/code/reproduce_all.py` now derives default `--figures-dir` and `--results-dir` from the script location instead of hardcoding `4ClaudeCode/claude-Nature/...`.
- `paper/code/analysis_pipeline.py` now defaults wetlab-pack outputs to a paper-local `results/` directory rather than hardcoding the full repo path.

These changes preserve current behavior, but reduce path-coupling to the `4ClaudeCode/` prefix.

## Proposed staged integration plan

Stage 0 (done):

- map the dependency surface and record known hard-coded references
- start making the paper workspace self-relative where safe

Stage 1 (next):

- centralize “paper workspace root” discovery for scripts outside `4ClaudeCode/` that currently hardcode `4ClaudeCode/claude-Nature/paper/figures`
- update those scripts to use an environment variable (e.g., `CAUSALBOOL_PAPER_ROOT`) or a shared helper that resolves a default paper workspace path

Stage 2:

- create `workspaces/` as the canonical home for paper workspaces
- move `4ClaudeCode/claude-Nature/` into the chosen `workspaces/...` location
- leave behind a minimal compatibility `4ClaudeCode/claude-Nature/README.md` pointing to the new location (no duplicate code), if needed for human navigation

Stage 3:

- update provenance documents in a controlled way:
  - preserve original recorded commands as historical logs
  - add an explicit “path migration note” section explaining the new workspace location
  - avoid rewriting historical absolute paths unless the repository establishes a formal provenance migration policy

## Current recommendation

- Yes: integrate into a common workspace folder, but only after Stage 1 (path abstraction) is complete.
- No: do not perform a direct move today; it would degrade reproducibility and confuse provenance.
