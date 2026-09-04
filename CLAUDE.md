# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Identity

CausalBool is a deterministic, physics-inspired programme of algorithmic information theory for Boolean causal networks. It derives closed-form index-set formulae that reconstruct synchronous network outputs exactly, without probabilistic assumptions. The core theory is implemented in Wolfram Language (Mathematica); Python layers handle biological data ingestion, analysis pipelines, and statistical validation.

## Key Commands

### Running Tests (Mathematica MUnit)
```
# All tests
zsh tests/MUnit/run-tests.sh --all

# By section (Analysis, Gates, Pattern, Theory, Algo, Mixed)
zsh tests/MUnit/run-tests.sh --section Analysis

# By gate within a section
zsh tests/MUnit/run-tests.sh --section Analysis --gate NOT
```

Tests require a local WolframKernel at `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.

### Compiling LaTeX
```
cd doc/newIntPaper && pdflatex -interaction=nonstopmode docProcess.tex
```

### Active Manuscripts (D-4, AUDIT_FIXING_PLAN_01)

Both are canonical, with distinct scopes — regenerate their numbers via
`tools/snapshot_paper_numbers.py --check` before citing:
- `papers/method/manuscript_formal/method_paper.tex` — theory/method paper.
- `papers/method/manuscript_computational/comp_paper.tex` — computational/validation paper
  (its output generator is `generate_paper_outputs.wl`, which now exits non-zero on any
  failed verification).

### Branch status

Live branch: **`clean`**. `main` is stale by policy until plan task T0.4 retags it;
do not trust `main` for current state.

### Governance

**Start here: `GOVERNANCE/CORE.md`** — one owner per concept, every declared
exception with its reason, and the guard protecting each. Under the
`monolithic-code` law, find the owner **before** writing code, never after.

Test membership is DECLARED in `tests/MUnit/MANIFEST.tsv`, not discovered by a
glob: 65 test / 11 quarantine (they export a literal `"OK"` and cannot fail) /
2 producer. `tools/check_test_manifest.sh` goes red on any unclassified file.

Definitions: `GOVERNANCE/GLOSSARY.md` (synchronized from `series-deconvolution`; check
with `tools/check_glossary_sync.sh`). Test truth: `tests/MUnit/BASELINE.md`.

Description lengths: `GOVERNANCE/DESCRIPTION_LENGTHS.md`. Variants A–E are named and
scoped there; the owners are `src/description_lengths.py` (Python) and
`Integration`BioMetrics`` (Wolfram), guarded by `tools/check_single_engine.sh`.
**`D_schema` is the primary mechanism-side measure; `D_formula` is a length under
the twelve-family catalogue.** No description length may be entropy-derived —
enforced by `tests/analysis/test_description_length_is_algorithmic.py`.

Large binaries: `GOVERNANCE/LARGE_BINARIES.md`. Nothing over 10 MB enters history;
external datasets are ignored and reached by manifest plus fetch script.

### Python (venv-based)
```
source venv/bin/activate
```
No pyproject.toml or setup.py at root; Python code is script-based, not an installable package.

## Architecture

### Dual-Language Stack

**Mathematica core** (`src/Packages/Integration/`): the formalized API surface.
- `Gates.m` — gate semantics, truth tables, index sets, dispatch for 12 gate types (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, MAJORITY, KOFN, CANALISING)
- `IndexAlgebra.m` — index-set algebra: complement, union, intersection, bit-reversal mapping (Phi), band indices
- `Alpha.m` / `Experiments.m` — repertoire creation and one-step dynamic update (delegate to legacy `src/integration/Alpha.m`)
- `BioMetrics.m` — description-length D and D_v2 computation
- `BioExperiments.m` — degree-preserving randomization, knockout deltas, attractors, essentiality comparison

**Legacy/bridge Mathematica** (`src/integration/`): older implementation files still loaded by packaged code. Contains `Alpha.m` (core repertoire logic), `NatureBDM.wl`, notebooks, and Python parsers/encoders.

**Python layers** (not packaged, script-based):
- `src/analysis/` — manuscript-facing analysis: DepMap validation, cancer corruption, phase transitions, essentiality prediction
- `src/complexity/` — basin entropy, attractor classification, trajectory LZ complexity
- `src/dynamics/` — Boolean dynamics simulator
- `src/stats/` — Bayesian meta-analysis, mutual information, Bayes factors
- `src/data/` — data validation and metadata linking
- `src/experiments/` — level-specific validation campaign runners
- `src/integration/` — Python parsers (SBML, GINML, BNet, Logic), encoders (Universal_D_v2, Hybrid, Hierarchy, Motif, Basin, BDM), data pipelines, and scraping

### Test Structure

`tests/MUnit/` contains deterministic Mathematica tests organized by concern:
- `Analysis/` — per-gate tests (AND, OR, XOR, ..., CANALISING, KOFN, NOT network tests, bio metrics)
- `Gates/` — gate dispatch and truth-table coverage tests (TSK-GATES-*, TSK-TEST-*)
- `Mixed/` — mixed-gate network formula-vs-exhaustive comparison tests
- `Pattern/`, `Theory/`, `Algo/`, `Sampling/`, `Stoch/` — additional test sections

Python tests and validation campaigns live under `tests/Bio/`, `tests/Lev4/`–`tests/Lev7/`, `tests/Nature/`.

### Paper Programme (`papers/`)

The canonical entry layer for paper-oriented work:
- `papers/common/` — shared scientific base; points to canonical upstream sources
- `papers/method/` — first paper track: formal method, gate formulae, validation. Active manuscript at `papers/method/manuscript/method_paper.tex`
- `papers/method/derivations/` — LaTeX derivation documents per gate
- `papers/method/code/` — reproducible computation packages (corroboration_6node, mixed_interaction_10node, scalability)
- `papers/nature/` — Nature-oriented track entrypoint

Historical execution artifacts remain under `doc/newIntPaper/` (theory/process backbone), `doc/finalpaper/` (manuscript assembly), and `workspaces/claude-nature/` (Level 8 reproducibility workspace).

### Data

- `data/bio/raw/` — raw network sources (BioModels, GINsim, PyBoolNet)
- `data/bio/processed/` — normalized JSON network corpus
- `data/bio/curated/metadata.csv` — curated annotations with essentiality labels
- `data/DepMap/` — external CRISPR/omics data (gitignored, large)
- `data/cancer/` — cancer-specific metadata

### External Vendored Code

`src/external/ccapi/` is a vendored third-party project (Cell Collective API). Treat as a dependency boundary; do not modify.

## Conventions

- **Determinism**: all tests and experiments are deterministic. When stochastic toggles are used for robustness studies, seeds must be pinned and recorded.
- **Repertoire ordering**: the project is ordering-aware (MSB/LSB via Phi bit-reversal mapping). Index sets and truth tables follow 1-based indexing with `Reverse[IntegerDigits[...]]` convention.
- **Gate dispatch**: use `Integration`Gates`ApplyGate[gate, inputs, params]` for gate evaluation; `IndexSet` and `IndexSetNetwork` for index algebra.
- **Results artifacts**: outputs go to `results/`, figures to `figures/`. Do not duplicate raw results into paper directories.
- **Historical vs active**: `doc/newIntPaper/` and `doc/finalpaper/` are provenance archives. New paper work starts from `papers/`.
- **Archive policy**: superseded scripts go to `archive/` subdirectories, not deleted outright, to preserve debugging context and provenance.
