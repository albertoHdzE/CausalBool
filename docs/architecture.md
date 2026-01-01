# Mathematica Project Architecture

## Structure
- `src/Packages/Integration/` — core packages for integration, gates, experiments
- `src/Notebooks/` — interactive notebooks for development and experiments
- `src/integration/` — legacy notebooks and scripts used by the thesis and paper
- `experiments/` — experiment drivers organised by topic
- `tests/MUnit/` — unit/property/performance/acceptance test notebooks and scripts
- `data/` — generated or stored inputs and topology artefacts
- `results/` — CSV/JSON outputs from runs
- `figures/` — plots and diagrams
- `docs/` — supplementary documentation and tooling notes
- `doc/newIntPaper/` — manuscript, planning and evaluation documents

## Modules
- Integration: repertoire generation, dynamic updates, subsystem analysis
- Gates: catalogue, dispatch, stochastic variants
- Experiments: ensembles, sweeps, regimes, mixed dynamics

## Conventions
- British English for all narrative documents
- Deterministic seeds for stochastic experiments
- Exports to `results/` and `figures/` with consistent naming
- Tests locateable under `tests/MUnit/` following epic/ticket naming