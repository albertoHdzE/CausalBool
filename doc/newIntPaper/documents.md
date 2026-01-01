# Architecture and Development Documents

## Repository Structure (Mathematica‑focused)
- `src/Packages/Integration/` — core Mathematica packages
  - `Alpha.m` — repertoire generation, network update routines
  - `Gates.m` — gate catalogue and dispatch (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES, k‑of‑n thresholds, canalising)
  - `Experiments.m` — ensemble generators, parameter sweeps, subsystem search, stochastic regimes
- `src/Notebooks/` — interactive notebooks
  - `Alpha.nb`, `newAlpha.nb` — development and exploration notebooks
  - `Experiments/*.nb` — experiment drivers (topologies, gates, regimes, noise, comparators)
- `tests/MUnit/` — unit/property/performance/acceptance notebooks
  - `GatesTests.nb` — truth tables and gate semantics
  - `IntegrationProperties.nb` — axioms, invariances, bounds checks
  - `Performance.nb` — repertoire scale, caching efficacy
  - `Acceptance.nb` — end‑to‑end reproduction of artefacts
- `experiments/` — experiment sources
  - `topologies/Topologies.nb` — ER/scale‑free/small‑world generators
  - `gates/GateSweeps.nb` — gate mixtures and bias control
  - `regimes/Regimes.nb` — sync vs async updates
  - `subsystems/Subsets.nb` — branch‑and‑bound subsystem search
  - `noise/Noise.nb` — stochastic gate flips and robustness
  - `compare/Phi.nb`, `compare/PID.nb`, `compare/TE_MI.nb` — comparators
- `data/` — stored inputs and topology artefacts (`*.mx`, `*.csv`)
- `results/` — generated CSV outputs
- `figures/` — final plots and diagrams
- `docs/` — supplementary documentation
  - `architecture.md` — module boundaries, API and conventions
  - `tooling.md` — Wolfram Framework/Workbench usage, kernel path resolution
  - `repro.md` — replication workflows and versioning
  - `metadata.json` — dataset and parameter metadata
  - `journalSubmissionChecklist.md` — submission compliance items
- `doc/newIntPaper/` — manuscript and planning
  - `fullEvalIntPaper.md` — evaluation and articulation strategy
  - `plan.md` — JIRA‑style plan and tickets
  - `theory.md`, `methods.md`, `results.md`, `discussion.md` — manuscript components
  - `docProcess.tex` — supplementary documentation of process and experiments (updated per ticket)

## Pattern Formulae Documents
- LaTeX derivations reside in `doc/causalBinpaper/`:
  - `01_causalBool_inputs.tex` — ordered exhaustive repertoire patterns and methodology
  - `02_cb_and.tex` — application to `AND` dynamics
  - `exam.tex` — exploratory generalisations
- Extend these documents to cover: `OR`, `XOR`, `NAND`, `NOR`, `XNOR`, `NOT`, `IMPLIES/NIMPLIES`, `k‑of‑n` thresholds, canalising/nested‑canalising functions.
- Summarise formulae in manuscript sections (`theory.md` and `results.md`) with links to sensitivity/influence and canalisation properties.

### Per‑Gate Analysis Document Naming
- `doc/causalBinpaper/02_cb_or.tex` — OR dynamics
- `doc/causalBinpaper/02_cb_xor.tex` — XOR dynamics (parity)
- `doc/causalBinpaper/02_cb_nand.tex` — NAND dynamics (monotone complement)
- `doc/causalBinpaper/02_cb_nor.tex` — NOR dynamics (monotone complement)
- `doc/causalBinpaper/02_cb_xnor.tex` — XNOR dynamics (equivalence)
- `doc/causalBinpaper/02_cb_not.tex` — NOT unary inversion
- `doc/causalBinpaper/02_cb_impl.tex` — IMPLIES/NIMPLIES asymmetric entailment
- `doc/causalBinpaper/02_cb_kofn.tex` — k‑of‑n threshold bands
- `doc/causalBinpaper/02_cb_canalising.tex` — canalising/nested‑canalising collapse

### Index Formulae Derivations
- Each per‑gate document should include a closed‑form index formula describing the set of repertoire indices where the gate outputs 1 over ordered inputs (e.g., `pivot + offset` for AND/NAND, unions for OR/NOR, parity constraints for XOR/XNOR, band conditions for KOFN, canalising collapse for specified parameters).
- Provide numeric and symbolic examples with matrices and tables; verify against empirical repertoires.

### Mixed Dynamics Composition
- Use `doc/causalBinpaper/exam.tex` to present intuitive composition across mixed gate networks:
  - Combine per‑gate formulae via network connectivity and subsystem partitions.
  - Explain interaction effects (synergy, redundancy, canalisation) in mixed settings.
  - Provide examples and figures with ordered inputs and outputs.

### Documentation Format Requirements (per‑gate)
- Follow the structure exemplified by `doc/causalBinpaper/02_cb_and.tex` for every gate document:
  - Abstract, Intuition, Problem Definition, Data Structure, Mathematical Formulation, Index Formula, Step‑by‑Step Explanation, Examples, Discussion, Conclusion
- Use professional typesetting in `docProcess.tex` (bmatrix, align, booktabs) for all examples.
- Ensure proofs/derivations are complete and link to empirical validations.

## Coding Conventions
- Packages load via `Needs["Integration`"]` with clear public/private symbols.
- Gate labels are strings; dispatch resolves to functions handling unary/multi‑input and thresholds.
- Deterministic seeds for stochastic experiments; explicit parameter registries.
- Exports use `Export[..., "CSV"]` to `results/`; figures saved to `figures/` with consistent naming.
- Notebook cells tagged for MUnit; acceptance notebooks orchestrate end‑to‑end runs.

## Gate Abstraction API
- `ApplyGate[gate_String, inputs_List, params_Association: <||>]` → `0|1`
- Supported gates: AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, `KOfN` with `"k"` param, `Canalising` with `"canalisingValue"` and `"canalisedOutput"`.
- Stochastic variant: `"noiseFlipProb" -> p` applies Bernoulli flips; seeded via `"seed"`.

## Network Update and Repertoires
- `RunDynamic[cm_, dynamic_List, opts_Association]` — one‑step update over full repertoires; supports sync/async regimes.
- `CreateRepertoires[cm_, dynamic_]` — inputs/outputs associations; cached for small n.
- `RunDynamicHD[...]` — high‑density exports to CSV; artefact paths parameterised.

## Experiments Pipeline
- Topology generation with seeds and saved metadata.
- Gate mixture and bias sweeps producing heatmaps and CSVs.
- Regime comparisons (sync/async) under deterministic schedules.
- Subsystem search with branch‑and‑bound and cut‑set pruning; report approximation gaps.
- Noise robustness studies with CI bands and sensitivity plots.
- Comparators: Φ (under stated assumptions), PID synergy, transfer entropy and multi‑information; correlation analyses.

## Pattern Derivation Approach
- Use the pattern alphabet `{0, 1, *}` on columns of ordered inputs and outputs; `*` denotes mixed presence.
- For monotone gates, derive patterns via Hamming weight inequalities; for `XOR/XNOR`, by parity/equivalence; for thresholds, by banded weight regions; for canalising, by fixed value collapse.
- Validate formulae against repertoires computed by `CreateRepertoires` (`src/integration/Alpha.m:354`) and pattern extraction via `elementsInColumn` (`src/integration/Alpha.m:645`) and `findPatternsInInputsPerAttTotal` (`src/integration/Alpha.m:662`).

## Testing Strategy (MUnit)
- Unit tests: gate truth tables and dispatch correctness.
- Property tests: non‑negativity, separability zero, relabelling invariance, monotonicity under factorisation.
- Performance tests: repertoire generation scaling, caching/memoisation effectiveness.
- Acceptance tests: full reproduction of manuscript artefacts from clean environments; checksums recorded.
 - Per‑ticket unit tests: every ticket must ship or update a corresponding MUnit notebook that verifies its acceptance criteria using deterministic seeds and documented parameters.
 - Naming convention: `tests/MUnit/<Epic>/<TicketID>Tests.nb` or simplified per‑gate names (e.g., `tests/MUnit/Analysis/ANDTests.nb`).
 - Scientific validation: experimental tests include quantitative agreement metrics, confidence intervals where applicable, and invariance checks; failing tests block progression.

## Performance and Scalability
- Memoisation of local update rules; parallelisation across interventions.
- Importance sampling near critical regimes; deterministic upper/lower bounds.
- Exploit sparsity and bounded in‑degree; stop criteria and convergence diagnostics.

## Tooling and Environment
- Wolfram Framework and Workbench with MUnit; notebooks configured for deterministic execution.
- Kernel path resolution documented; environment variables and PATH setup instructions included.
- Exported CSVs validated for schema consistency; figures generated via standard plotting functions.

## Documentation and Artefacts
- API reference in `architecture.md` with symbol usage and examples.
- Reproducibility workflows in `repro.md`; versioned datasets and scripts.
- Submission checklist ensures journal compliance (figure formats, word limits, data availability).

## Risks and Mitigations
- Scalability: use approximations and pruning with bounds; report runtime and error bars.
- Novelty clarity: explicit positioning vs Φ and PID; formal statements.
- Tooling dependency: provide portable instructions; minimise reliance on proprietary features.

## Timeline Alignment
- Mirrors milestones in `plan.md`; integrates theory, code, experiments, testing, comparators, manuscript assembly and release.