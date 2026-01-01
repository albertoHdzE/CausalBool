# Causal Boolean Integration
Deterministic analysis of causal integration in Boolean networks, with formal gate semantics, index formulae, exhaustive validation, reproducible artefacts, and manuscript assembly.

## Overview
- Implements synchronous one‑step updates and exhaustive repertoires for Boolean networks.
- Provides a gate catalogue (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES, MAJORITY, KOFN thresholds, canalising) with dispatch and optional noise.
- Derives closed‑form index sets for output=1 under ordered inputs; validates against empirical repertoires.
- Assembles documentation and figures under `doc/newIntPaper` with British English narrative.

## Structure
- `src/Packages/Integration/` core packages: `Alpha.m`, `Gates.m`, `Experiments.m`, `SelfTest.m`.
- `src/integration/` legacy notebooks and routines: `Alpha.m`, `Alpha.nb`, `newAlpha.nb`.
- `tests/MUnit/` deterministic tests by section: `Analysis/`, `Gates/`, `Pattern/`, `Arch/`, `Mixed/`.
- `results/` CSV/JSON outputs from experiments and tests; `figures/` plots.
- `doc/newIntPaper/` manuscript support: `docProcess.tex`, `plan.md`, `documents.md`, `fullEvalIntPaper.md`.
- `experiments/` reproducible study scripts (e.g., mixed dynamics).

## Gate Catalogue and Dispatch
- `Integration`Gates`ApplyGate[gate, inputs, params]` with gates: AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, MAJORITY, KOFN, CANALISING.
- Noise: `params["noiseFlipProb" -> p]` flips outputs with probability `p` (use deterministic seeds in experiments).
- Index sets: `Integration`Gates`IndexSet[gate, arity, params]` and network‑aware `IndexSetNetwork[gate, n, Ic, params]` for connected inputs `Ic`.

## Tests
- Location: `tests/MUnit/*` with `.m` scripts; each exports artefacts under `results/tests/*` and returns an `Association["Status" -> "OK"|"FAIL"]`.
- Unified runner: `tests/MUnit/run-tests.sh`
  - Run all: `zsh tests/MUnit/run-tests.sh --all`
  - By section: `zsh tests/MUnit/run-tests.sh --section Analysis`
  - By gate name: `zsh tests/MUnit/run-tests.sh --section Analysis --gate NOT`
- Summary written to `results/tests/runall/Status.txt`.

## Documentation
- Supplement: `doc/newIntPaper/docProcess.tex` compiles to `doc/newIntPaper/docProcess.pdf`.
- Policies: global testing, documentation, index formulae, and mathematical formulae enforced via `doc/newIntPaper/plan.md`.
- Compile PDF: `cd doc/newIntPaper && pdflatex -interaction=nonstopmode docProcess.tex`.

## Quick Start
- Kernel path: `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.
- Run analysis tests: `zsh tests/MUnit/run-tests.sh --section Analysis`.
- Generate mixed dynamics validation: see `experiments/mixed/Mixed.m` and outputs under `results/mixed/validation/`.

## Current Status (Highlights)
- Analysis completed: AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES, KOFN (strict and non‑strict), CANALISING.
- Gate dispatch integrated; network‑aware index helpers provided for KOFN, IMPLIES/NIMPLIES, NOT, CANALISING.
- Documentation updated and compiled; artefacts exported for all tickets implemented.

## Reproducibility
- All tests and experiments are deterministic; set and record seeds for any stochastic runs.
- Artefacts saved to `results/` and plots to `figures/`; summary statuses recorded alongside outputs.
