# imp-causal-paper

Standalone and isolated implementation of the paper `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems` by Zenil et al. (2019).

## Scope

This project implements the paper's core executable machinery in a self-contained Python project with its own virtual environment:

- BDM-based complexity estimation through `pybdm`
- perturbation spectra and information signatures for graph edges and vertices
- positive, neutral, and negative element classification using the paper's `log2 |V(G)|` threshold
- MILS (Minimal Information Loss Sparsification)
- MARPA (Maximal Algorithmic Randomness Preferential Attachment)
- relative, absolute, and combined reprogrammability indices
- reverse engineering of small cellular automata from disordered observations
- synchronous Boolean-network attractor analysis under perturbations
- reproducible parsing of the public `Th17` GEO series into project-local artifacts, distinguishing:
- expression-bearing microarray matrices (`GSE43955`, `GSE43956`, `GSE43957`, `GSE43969`)
- metadata-only sequencing series (`GSE43948`, `GSE43949`)
- supplementary bundle manifests (`GSE43948`, `GSE43949`, `GSE43956`, `GSE43957`, `GSE43970`)
- 48 h perturbation RNA-seq gene tables recovered from `GSE43948_RAW.tar`

## Reproducibility Boundary

The paper contains broad biological applications on `E. coli`, `Th17`, and `CellNet` data. This project now includes project-local ingestion of the public `Th17` GEO assets and supplementary bundle manifests, but it does not yet claim exact reproduction of the full biological panels. The remaining gap is no longer raw data discovery for `Th17`; it is paper-faithful preprocessing, network reconstruction, and claim-level corroboration across all biological blocks. The current local provenance also shows that `GSE43970` is a mixed SuperSeries spanning both the Yosef Th17 network-reconstruction assets and the Wu `SGK1` salt-pathogenicity subseries (`GSE43956`, `GSE43957`), so downstream network analyses must separate those biological arms explicitly.

For the cellular-automaton reconstruction demo, the row order is recovered exactly on the provided synthetic case. As in the paper's broader discussion of generative inference, finite observations can admit more than one compatible local rule, so the demo reports both the recovered ordering and the best-fitting rule on the observed window.

## Environment

- Isolated virtual environment: `.venv`
- Interpreter: Python 3.11
- Main numerical dependency: `pybdm==0.1.0`

## Step-by-Step Execution

```bash
./run.sh setup
./run.sh th17
./run.sh test
./run.sh graphs
./run.sh ca
./run.sh boolean
./run.sh all
```

Outputs are written under `results/`.
Plots are written under the root-level `plots/` folder, split by experiment (`plots/graphs`, `plots/ca`, `plots/boolean`).
Processed `Th17` outputs are written under `data/processed/th17`, with separate directories for series metadata, expression matrices, RNA-seq supplementary tables, and bundle manifests. The recovered Wu subseries raw archives (`GSE43956_RAW.tar`, `GSE43957_RAW.tar`) are now also summarized into deterministic tar-member manifests so that raw CEL provenance is tracked at the series level rather than only through the `GSE43970` SuperSeries bundle. Series-level outputs now carry explicit arm-aware provenance fields such as `study_arm`, `source_publication`, and `biological_program`, and bundle manifests expose `resolved_study_arm_counts` so downstream preprocessing can enforce the Yosef/Wu separation mechanically rather than by convention.

Each plot directory also contains a `plot_manifest.json` file stating the exact correspondence boundary with the original paper figures. This is intentional: the implementation reproduces the paper's core algorithms and generates faithful reduced analogues of key visualizations, but it does not claim that every saved plot is pixel-identical to the published panels.

## Tests

The test suite uses real computations only, with no mocks:

- graph signature ordering
- MILS edge-count reduction
- MARPA edge-addition growth
- CA order reconstruction from scrambled observations
- Boolean-network attractor computation
- full CLI integration producing experiment outputs
