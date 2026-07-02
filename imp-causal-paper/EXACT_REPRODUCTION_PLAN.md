# Exact Reproduction Plan

## Objective

Reproduce, as faithfully as possible, the experiments reported in:

- `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems` (Zenil et al., iScience 2019)

The target is **not** a conceptual reimplementation or toy analogue. The target is:

- same experiment families,
- same scale classes,
- same datasets or closest recoverable authoritative sources,
- same methodological definitions from the supplement,
- same output types, trends, and claims,
- explicit corroboration of every paper statement that depends on computation.

## Operating Principle

No claim of replication will be made unless supported by one of:

1. direct reproduction from author-adjacent code and data,
2. a reconstructed pipeline using the same public source data and the same stated methodology,
3. a clearly documented near-reproduction where the paper asset is unavailable but the provenance chain is strong and deviations are explicitly quantified.

## Current State

The existing project already contains:

- an isolated Python environment and runner,
- partial implementations of BDM-driven perturbation ideas,
- reduced synthetic demonstrations,
- a comparison audit showing that the current code is not yet a full reproduction.

The current codebase should now be treated as a scaffold, not as the final scientific reproduction.

## Author-Adjacent Assets Already Recovered

Recovered local reference:

- `reference/algodyn`

This repository provides:

- BDM wrappers,
- graph edge/vertex information contribution functions,
- spectra and signatures,
- reprogrammability routines,
- shuffling utilities relevant to perturbation experiments.

This is important because it suggests the exact reproduction should reuse or mirror the authors' operational definitions where possible, especially for:

- `calculate_info_edges`
- `calculate_info_vertices`
- `info_spectra`
- `info_signature`
- `relative_reprogrammability`
- `inforank`

## Reproduction Ledger

### Block A: Core Definitions and Supplement Fidelity

Must reproduce exactly from supplement and author code:

- positive / negative / neutral information element definitions using `log2 |V(G)|`
- information spectrum and information signature
- relative, absolute, and combined reprogrammability
- simply directed graph construction
- MILS tie handling and determinism
- MARPA objective and stopping logic
- exhaustive 5-node Boolean-network perturbation protocol
- CA row perturbation / order inference protocol

Deliverables:

- a machine-readable specification file mapping each paper definition to code symbols,
- validation scripts showing that our implementation matches `algodyn` on overlapping primitives,
- replacement of any ad hoc approximation currently in the project.

### Block B: Cellular Automata Experiments

Paper target:

- Figure 3 and related supplementary material
- exact or near-exact reproduction of reconstruction from disordered observations
- rules including simple and random-looking ECAs
- longer trajectories such as 200-step and 280-step cases
- single-row and double-row perturbation settings where stated
- Spearman row-order comparisons and any reported trend summaries

Tasks:

1. recover the exact ECA rule set used in the paper panels,
2. recover the exact trajectory lengths, initial conditions, and scramble protocol,
3. identify whether the extended arXiv version or supplement contains panel-specific settings,
4. implement brute-force or optimized search exactly matching the paper’s search space,
5. generate the same metrics and figure structure,
6. corroborate row-order quality and generating-rule claims.

Success criterion:

- panel-by-panel CA reconstruction results that numerically agree or are demonstrably within explainable tolerance of the paper.

### Block C: Graph Perturbation, MILS, and MARPA

Paper target:

- complete-graph perturbation away from randomness,
- random-graph perturbation toward simplicity,
- ER/MAR behavior and density effects,
- information signatures and reprogrammability,
- MILS benchmark behavior including preservation of graph properties,
- comparisons against transitive and spectral sparsification.

Tasks:

1. reconstruct the exact graph families and sizes,
2. recover the benchmark network list if possible,
3. identify the 20 gold-standard networks referenced by the paper/supplement,
4. reconstruct the exact metrics compared after sparsification:
   - information signature
   - degree distribution
   - clustering coefficient
   - edge betweenness
   - largest eigenvalue / eigenvalue counts if applicable
5. verify whether `algodyn` plus supplementary pseudocode is sufficient or whether additional code must be written.

Success criterion:

- reproduction of the reported graph intervention trends and benchmark superiority claims, or explicit demonstration of any irreproducible gap due to missing original assets.

### Block D: Boolean-Network Simulations

Paper target:

- exhaustive 5-node Boolean-network experiments,
- AND / OR / XOR node-rule families,
- complete, ER, and scale-free topologies,
- larger-network validation,
- attractor-count changes under perturbations,
- perturbation category comparisons: negative vs positive vs neutral vs random controls.

Tasks:

1. recover the exact graph enumeration protocol for 5-node connected graphs,
2. implement the same simply directed graph transformation if used,
3. reproduce the node-function assignment protocol,
4. implement attractor enumeration and reachable-state statistics,
5. identify whether automorphism correction was applied for small graphs and reproduce it if so,
6. generate the paper’s distributions and trend panels.

Success criterion:

- exact match to exhaustive small-graph summary statistics and qualitative agreement on larger-topology perturbation trends.

### Block E: Biological Networks

This is the hardest and most important gap.

Paper target includes:

- validated `E. coli` transcription-factor network,
- differentiating `Th17` cell regulatory networks over time,
- `CellNet` regulatory networks for 16 human cell lines,
- GO / KEGG / EcoCyc enrichment results,
- complexity-programmability mapping and reconstructed epigenetic landscape.

Tasks:

1. identify the exact `E. coli` TF network source from `Marbach et al. 2012`,
2. identify the exact Th17 network/time-point source from `Yosef et al. 2013`,
3. identify the exact CellNet release / cell-line subset from `Morris et al. 2014`,
4. reconstruct preprocessing from raw source data to the graphs used in the paper,
5. reconstruct the enrichment pipeline:
   - gene universe,
   - positive/negative partition rules,
   - GO / KEGG / EcoCyc databases,
   - clustering method,
   - any significance thresholds,
6. reproduce the complexity-programmability coordinates and Waddington-like landscape.

Success criterion:

- either direct reproduction of the biological plots and gene-level trends, or a fully evidenced explanation of any divergence due to version drift in upstream public databases.

## Staging Strategy

### Stage 1: Source Recovery

Outputs:

- exact experiment inventory
- recovered official / author-adjacent code
- recovered public datasets
- provenance log for every asset

Priority:

- extended arXiv / supplement assets
- `algodyn`
- network sources from Marbach, Yosef, Morris
- any archived raw files named in the supplement

### Stage 2: Primitive Fidelity

Outputs:

- unit-level equivalence tests between our code and `algodyn`
- verified formulas for spectra, signature, reprogrammability, MILS, MARPA

### Stage 3: Synthetic Experiments

Outputs:

- exact CA reproduction
- exact graph/Boolean synthetic reproductions

### Stage 4: Biological Reproduction

Outputs:

- full data acquisition scripts
- preprocessing scripts
- biological result replication notebooks/scripts

### Stage 5: Corroboration

Outputs:

- claim-by-claim comparison table
- figure-by-figure overlays
- numerical discrepancy log

## Immediate Next Actions

1. Inspect `algodyn` function-by-function and identify which paper result blocks it already covers.
2. Recover the long-form supplement / extended arXiv material and parse every panel-specific parameter.
3. Search for raw experiment files or archived code references named in the supplement.
4. Build a machine-readable reproduction ledger mapping:
   - paper figure
   - source dataset
   - code path
   - parameter set
   - expected output
5. Only after that, start replacing the reduced implementation modules.

## Non-Negotiable Standards

- No mocks.
- No synthetic biological stand-ins unless the paper itself used synthetic systems for that block.
- No “close enough” language without quantitative evidence.
- No collapsing of distinct claims into a single toy experiment.
- Every missing asset must be documented with the attempted recovery path.

## Expected Risks

- biological source versions may have drifted since publication,
- supplementary raw files may no longer be directly linked,
- some benchmark network lists may need archival reconstruction,
- exact panel aesthetics may be reproducible only after the numerical pipeline is matched.

These are not reasons to stop; they are reasons to keep provenance strict.

## Definition Of Done

The reproduction is only complete when all of the following are true:

1. every computational claim in the paper is mapped to code and data,
2. every figure family has either been reproduced or explicitly marked irrecoverable with evidence,
3. every discrepancy is quantified,
4. the project can regenerate the reproduced outputs from a clean checkout,
5. the final audit can honestly state which results are exact matches, near-matches, or unresolved.

