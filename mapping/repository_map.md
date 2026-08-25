# Repository Map

## Purpose

This document is a cleanup-oriented map of the repository.

It does not decide deletions yet.
It identifies:

- which areas are core source code
- which areas are legacy or bridge code
- which areas are campaign-specific analysis code
- which areas are paper/manuscript workspaces
- which areas are data/results artifacts
- which areas look duplicated, generated, or externally vendored

## Top-Level Structure

### `src/`

Primary code root. This is the most important directory for future cleanup decisions.

- `src/Packages/Integration/`: Mathematica packaged API layer. This looks like the formalized package surface for the Boolean integration framework.
- `src/integration/`: mixed legacy and bridge layer. Contains older Mathematica implementation files, Python encoders/parsers, notebooks, scraping utilities, and several transition-era modules.
- `src/analysis/`: Python analysis scripts for cancer, DepMap, phase transitions, essentiality, and manuscript-facing figures.
- `src/experiments/`: phase or level runners for biological validation campaigns.
- `src/data/`: data-building and metadata-linking utilities.
- `src/dynamics/`: Boolean simulator implementation.
- `src/complexity/`: basin, attractor, and trajectory complexity tools.
- `src/stats/`: Bayesian and information-theoretic utilities.
- `src/pipeline/`: contingency or project-decision logic.
- `src/causal/`: older Mathematica notebook/package area for `CausalBool`.
- `src/external/ccapi/`: vendored third-party project, not native project code.

### `data/`

Research data workspace, not a pure source tree.

- `data/bio/raw/`: raw network sources from BioModels, GINsim, PyBoolNet, and related imports.
- `data/bio/processed/`: normalized JSON network corpus used by many analyses.
- `data/bio/curated/metadata.csv`: curated annotations, including essentiality labels.
- `data/bio/validation/`: validation inputs such as `essentiality_data.csv`.
- `data/DepMap/`: very large external data release with CRISPR, omics, and model tables.
- `data/cancer/`: cancer-specific metadata and dependency tables.

### `results/`

Generated outputs from tests, experiments, and validation runs.

- Contains mixed research outputs from Mathematica and Python.
- Contains several test-result trees that overlap conceptually with `tests/` and with output locations referenced from the Level 8 paper workspace.
- Should be treated as evidence/artifact storage until regeneration paths are fully documented.

### `tests/`

Mixed testing workspace.

- `tests/MUnit/`: formal Mathematica test suite.
- `tests/Bio/`, `tests/Lev4/`, `tests/Lev5/`, `tests/Lev6/`, `tests/Lev7/`, `tests/Nature/`: Python and Mathematica validation/test campaigns.
- `tests/results/`: test outputs stored inside the test tree.

### `doc/`

Long-lived documentation and manuscript history.

- `doc/Tesis-UNAM/`: thesis workspace with source, classes, figures, and compiled PDFs.
- `doc/causalBinpaper/`: signpost only; the method derivations were promoted to `papers/method/derivations/`.
- `doc/newIntPaper/`: major planning and manuscript-development area for the integration project.
- `doc/finalpaper/`: another mature paper assembly area with figures and scripts.

### `papers/`

Canonical paper-programme entry layer.

- `papers/common/` defines the shared scientific base that future paper writing should consult first.
- `papers/method/` is the first active paper track after cleanup and contains the promoted gate/formula derivations plus a dedicated manuscript workspace.
- `papers/nature/` is the clean paper-track entrypoint for the Nature programme, while operational reproducibility remains under `workspaces/claude-nature/`.

Important protocol-lineage note:

- `doc/newIntPaper/` is not a flat manuscript folder.
- It contains at least three different document roles:
  - foundational cross-level documents (`docProcess.tex`, `expProcess.tex`)
  - baseline biological programme documents (`bioPlan.md`, `bioProcess.tex`)
  - numbered Level 2-7 plan/process materials (`bioPlanLev-*`, `bioProcessLev*`)
- The level lineage is irregular rather than perfectly symmetric:
  - no clear standalone Level 1 bundle was found
  - Level 4 process content appears merged into `bioProcessLev3.tex`
  - explicit `protocol-level-*` documents exist only for selected stages
- See `mapping/protocol_lineage_review.md` before any cleanup of protocol or process documents.

### `docs/`

Short architecture/tooling documentation, smaller and cleaner than `doc/`.

### `4ClaudeCode/`

Parallel Nature-paper working area.

- `4ClaudeCode/claude-Nature/` is now a signpost only.
- The active Level 8 paper workspace was moved to `workspaces/claude-nature/`.

### `experiments/`

Older experiment area outside `src/`, mainly Mathematica or mixed prototypes.

### `figures/`

Generated or exported figures from tests and self-checks.

### `archive/`

Repository-level archive area for low-risk historical material moved out of active roots.

- `archive/root_scratch/`: former top-level debug, inspection, and exploratory scripts preserved for historical troubleshooting context.
- `archive/root_wrappers/`: former top-level wrapper scripts preserved when they are stale or operationally weaker than the module entrypoints they wrap.
- `archive/root_build_artifacts/`: root-level build byproducts (e.g., LaTeX `.aux`/`.log`/`.out`/`.toc`, accidental PDFs, and Office temp files) moved out of the active top-level namespace.
- `archive/generated_web_bundles/`: former root-level generated Vite/Cell Collective bundles preserved as artifacts rather than active source.
- `archive/analysis_drafts/`: superseded or incomplete analysis scripts moved out of active `src/` locations.

### `mat-bdm/` and `mathematicabdm/`

Mathematica BDM-related workspaces with notebooks and lookup tables. These look historically important and partially overlapping.

- `mat-bdm/` currently contains:
  - `IntegratedInformationByAlgorithmicDynamics.nb`
  - `squares2Dsize1to4.m`
- `mathematicabdm/` currently contains:
  - `BDMandNormalizedBDM.nb`
  - `StringNBDM.nb`
  - `D3.m`
  - `D4.m`
  - `D5.m`
  - `reducedD2.m`
  - `squares2Dsize1to4.m`
- The two copies of `squares2Dsize1to4.m` are exact duplicates.
- `mat-bdm/IntegratedInformationByAlgorithmicDynamics.nb` is unique and loads `squares2Dsize1to4.m` locally from its own directory.
- `src/integration/NatureBDM.wl` points directly to `mathematicabdm/D5.m`, which makes `mathematicabdm/` operationally more anchored to the current repo than `mat-bdm/`.
- Some Python verification scripts reference these workspaces through stale absolute paths under `CausalBoolIntegration/`, which confirms historical usage but does not provide a safe modern relocation path.

Interpretation:

- `mathematicabdm/` is the richer table/notebook workspace.
- `mat-bdm/` is thinner, but it is not empty redundancy because its unique notebook still depends on the colocated lookup table.
- Folder-level collapse is not yet safe without either rewriting that notebook dependency or formalizing a BDM workspace policy.

### Top-level loose files

- `run_scraper.py`: small orchestration wrapper.
- `process_data.py` is no longer kept at root; it was moved to `archive/root_wrappers/` after review showed it was an unreferenced stale wrapper that did not bootstrap `src/`.
- Large generated JS bundles are no longer kept at root; they were moved to `archive/generated_web_bundles/`.

## Core Source Map

### 1. Mathematica Packaged Core: `src/Packages/Integration/`

This appears to be the formalized Mathematica API surface.

- `Gates.m`: canonical gate semantics, truth tables, index-set helpers, and dispatch for AND/OR/XOR/NAND/NOR/XNOR/NOT/IMPLIES/NIMPLIES/MAJORITY/KOFN/CANALISING.
- `IndexAlgebra.m`: compact index-set algebra layer for complements, unions, intersections, bit-order mapping, and one/zero band indices.
- `BioMetrics.m`: description-length routines including `ComputeDescriptionLength` and `ComputeDescriptionLengthV2`.
- `BioExperiments.m`: network randomization, knockout deltas, attractor routines, and essentiality comparison helpers.
- `SelfTest.m`: very small self-check utility that exports validation outputs and a plot.
- `Alpha.m`: packaged facade that still delegates to legacy `src/integration/Alpha.m`.
- `Experiments.m`: packaged wrapper that also still calls into legacy `src/integration/Alpha.m`.

Interpretation:

- This is the closest thing to the official Mathematica core.
- It is not fully independent from the legacy layer yet.

### 2. Legacy / Bridge Layer: `src/integration/`

This is a hybrid directory containing several generations of implementation.

- Core structural encoder:
  - `Universal_D_v2_Encoder.py`
- Hybrid/alternative encoders:
  - `Hybrid_Encoder.py`
  - `HierarchyEncoder.py`
  - `MotifEncoder.py`
  - `Basin_Encoder.py`
  - `BDM_Wrapper.py`
- Data ingestion/parsing:
  - `grn_data_pipeline.py`
  - `SBMLParser.py`
  - `GINMLParser.py`
  - `BNetParser.py`
  - `LogicParser.py`
- Data acquisition / curation:
  - `BulkScraper.py`
  - `CurateNatureDataset.py`
  - `BioBridge.py`
- Legacy Mathematica and notebooks:
  - `Alpha.m`
  - `Alpha.nb`
  - `newAlpha.nb`
  - `BioBridge_v2.m`
  - `BioLink.m`
  - `NatureBDM.wl`
- CLI / experimental runners:
  - `cli_dv2.py`
  - `bio_D_experiment.py`
  - `phase_transition_experiment.py`

Interpretation:

- This is not one cohesive subsystem.
- It mixes current reusable pieces with historical notebooks, bridge scripts, and ingestion utilities.
- Cleanup here must be dependency-aware.

### 3. Python Analysis Layer: `src/analysis/`

This directory contains manuscript- and study-facing analysis scripts.

- `DepMap_Validation.py`: large cohort validation pipeline connecting Delta D, DepMap, omics, gnomAD, and predictor benchmarking.
- `Cancer_Corruption.py`: tumor-normal corruption analysis with TCGA-style pairing and figure export.
- `KRB_Corruption_Anchors.py`: targeted corruption anchor / negative control analysis.
- `Essentiality_Prediction_v3.py`: earlier essentiality prediction pipeline.
- `Hybrid_Essentiality_Validator.py`: hybrid complexity essentiality validator.
- `Phase_Transition.py`: synthetic topology and gate sweep.
- `Phase_Transition_Bio_Overlay.py`: overlays real biological networks on synthetic phase-transition analysis.
- `analyze_level7_full.py`: post-processing utility for level-7 fidelity results.
- `optimize_alpha.py`: mature alpha sweep/optimization utility.

Interpretation:

- This is active science code, but not all files are equally mature.
- Several scripts are one-off campaign drivers rather than reusable libraries.
- One previously obvious draft variant, `optimize_alpha_draft.py`, has been moved to `archive/analysis_drafts/` after comparison confirmed it was incomplete and superseded.

### 4. Experiment Campaign Runners: `src/experiments/`

These are campaign scripts organized by project phase or validation level.

- `Benchmark_D_v2.py`: benchmark of biological networks against randomized controls.
- `Null_Generator_HPC.py`: large null-generation pipeline with checkpointing.
- `SimplicityV2_Nature.py`: simplicity-v2 pipeline tied to contingency monitoring and manuscript logic.
- `run_level5_validation.py`: hybrid validation campaign.
- `run_level6_validation.py`: basin-entropy validation campaign.
- `run_level7_validation.py`: attractor-fidelity validation campaign.

Interpretation:

- This area captures a chronology of campaign-specific analyses.
- It is useful evidence of how claims were generated, but it is not a clean reusable library.

### 5. Data / Dynamics / Complexity / Stats Support

- `src/data/cancer_network_builder.py`: central cancer network instantiation and cohort builder.
- `src/data/validate_gold_standard.py`: metadata consistency validator.
- `src/data/verify_and_link_metadata.py`: metadata-linking helper, likely semi-manual or one-off.
- `src/dynamics/Boolean_Dynamics.py`: Boolean dynamics simulator.
- `src/complexity/Trajectory_LZ.py`: Lempel-Ziv trajectory complexity.
- `src/complexity/Basin_Entropy.py`: basin entropy estimator.
- `src/complexity/Attractor_Classifier.py`: attractor/fidelity comparison logic.
- `src/complexity/Scaling_LZ_Tools.py`: scaling helper toolkit, appears partially historical.
- `src/stats/Mutual_Information_Analyzer.py`: MI utility.
- `src/stats/Bayes_Factor_Calculator.py`: Bayes factor helper.
- `src/stats/Bayesian_Meta_Analysis.py`: self-contained Bayesian meta-analysis utility.
- `src/pipeline/Contingency_Monitor.py`: protocol-decision logic, closer to governance automation than scientific core.

### 6. Older Causal Package Area: `src/causal/`

- `CausalBool.m`
- `CausalBool.nb`
- `CausalBool.vsnb`

Interpretation:

- This looks like an earlier Mathematica-centered package/notebook workspace predating the current `src/Packages/Integration/` layout.
- It should be treated as potentially historical until traced against current package usage.

## Paper and Documentation Map

### `doc/newIntPaper/`

Major planning and manuscript-development archive.

- Contains phase plans (`bioPlanLev-*`), manuscript text, figures, process PDFs, references, and contingency/planning documents.
- `towardsNature/` contains planning notes plus an older `grn_data_pipeline.py`, indicating documentation and code were co-evolving in this area.

### `doc/finalpaper/`

More consolidated manuscript workspace.

- Has manuscript assembly scripts and section files.
- Includes figure-generation scripts and compiled outputs.
- Contains both source files and generated LaTeX byproducts in places.
- `nature_draft.tex` remains the strongest current Nature-facing manuscript source.
- `nature_final.tex` is not just a compiled byproduct companion; it is a distinct standalone manuscript branch with a different framing and result scale.
- `final-draft.tex` is no longer kept at the top level; it was moved to `doc/finalpaper/archive/historical_manuscripts/` as a historical predecessor branch.
- `supInfo.txt` was also removed from the top level and archived there as `supInfo.tex` after confirming it is standalone LaTeX supplementary source rather than plain text notes.

### `workspaces/claude-nature/paper/`

Parallel paper-production workspace with operational code.

- `paper/code/analysis_pipeline.py`: large end-to-end paper analysis pipeline for figures, validation, reproducibility, and stress tests.
- `paper/code/essentiality_analysis.py`: extended essentiality analysis.
- `paper/code/reproduce_all.py`: orchestration wrapper around the pipeline.
- `paper/figures/`: many generated figures and CSV/JSON companions.
- `paper/results/`: paper-support outputs (readiness packs, route decisions, submission pack); historical `paper/results/tests/` mirror is intentionally not present.
- `bioPlanLev-8.md`, `bitacora-lev8.md`, and other paper files show this area is active governance plus execution, not merely notes.
- `paper3_algorithmic_corruption.tex` is a real side-branch manuscript inside this active workspace, not an obviously disposable draft.

Interpretation:

- This is a second serious code-and-reproducibility universe inside the repo.
- It overlaps conceptually with `src/analysis/`, `results/`, and `doc/newIntPaper/`.

## Data and Artifact Map

### Likely core datasets

- `data/bio/raw/*`
- `data/bio/processed/*`
- `data/bio/curated/metadata.csv`
- `data/bio/validation/essentiality_data.csv`
- `data/DepMap/*`
- `data/cancer/*`

### Likely generated artifacts

- `results/**/*`
- `figures/**/*`
- compiled PDFs under `doc/**/*`
- LaTeX intermediates such as `.aux`, `.fls`, `.fdb_latexmk`, `.log`, `.synctex.gz`
- `index.js` and `cc_index.js`

### External vendored code

- `src/external/ccapi/**/*`

This subtree has its own docs, tests, CI config, packaging files, and internal sample data. It should be handled as a vendored dependency boundary.

## Top-Level Loose Scripts Map

### Thin wrappers

- `run_process.py`: calls `BulkScraper.process_raw_files()`.
- `run_scraper.py`: runs BioModels, GINsim, PyBoolNet scraping and then processing.
- `report_dataset.py`: reports processed network inventory.

Interpretation:

- `run_scraper.py` remains the clearest intentional repository-root entrypoint because historical planning documents still reference it explicitly.
- `run_process.py` remains plausible as a process-only convenience wrapper, even though it overlaps operationally with module entrypoints.
- `report_dataset.py` is a standalone operator utility rather than a wrapper into the same code path.

### Scratch / debugging utilities

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

Interpretation:

- These files look exploratory and diagnostic, not production pipeline components.
- They should be mapped as probable cleanup candidates later, but only after checking whether they preserve unique debugging knowledge.

### Built JavaScript artifacts

- `index.js`
- `cc_index.js`

Interpretation:

- These are extremely large build outputs, likely from a Vite-based frontend bundle related to Cell Collective material.
- They should not be treated as authored source code.

## Current Cleanup-Relevant Classification

### High-confidence core

- `src/Packages/Integration/`
- key reusable pieces under `src/integration/`
- `src/data/`
- `src/dynamics/`
- `src/complexity/`
- `src/stats/`

### Mixed active + historical

- `src/analysis/`
- `src/experiments/`
- `tests/`
- `doc/newIntPaper/`
- `doc/finalpaper/`
- `workspaces/claude-nature/paper/`

### Historical / transitional / likely messy

- `src/causal/`
- notebook files under `src/integration/`
- top-level debug and inspect scripts
- `experiments/` outside `src/`
- `mat-bdm/` and `mathematicabdm/`

### External / vendored

- `src/external/ccapi/`

### Generated / artifact-heavy

- `results/`
- `figures/`
- compiled manuscript outputs under `doc/` and `4ClaudeCode/`
- top-level `index.js` and `cc_index.js`

## Immediate Mapping Conclusions

1. The repository is not one codebase but a layered research workspace.
2. There are at least two strong code centers:
   - `src/`
   - `workspaces/claude-nature/paper/code/`
3. Mathematica packaged code is not fully detached from legacy implementation files.
4. Documentation, manuscript production, and executable analysis are spread across multiple parallel trees.
5. Cleanup should be staged by boundary:
   - core code
   - legacy bridge code
   - vendored external code
   - datasets
   - generated outputs
   - paper-production artifacts
