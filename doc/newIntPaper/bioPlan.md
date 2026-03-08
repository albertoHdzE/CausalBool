# Programme Plan: Biological Application for Nature (JIRA-style)

## Executive Summary
This plan details the execution path to validate the "Deterministic Causal Boolean Integration" framework on biological systems. It bridges the existing theoretical core (`docProcess`) with empirical biological validation (`bioProcess`), aiming for a publication in *Nature*.

## Refinements & Recommendations (Approved)
1.  **Hybrid Workflow**: Python will handle Data Ingestion (Cell Collective/GINsim) and Behavioral Complexity (BDM via `pybdm`). Mathematica will handle Structural Complexity ($D$-measure), Repertoire Generation, and Causal Calculus.
2.  **Unified Data Exchange**: JSON will be the primary interchange format for network definitions; CSV for repertoires.
3.  **Continuous Documentation**: Every ticket requires an update to `bioProcess.tex` with results, ensuring the manuscript evolves in real-time.

## Epics and Phases
-   **Phase 1 — Setup & Infrastructure (EPIC-BIO-SETUP)**: Bridges, BDM, and Environment.
-   **Phase 2 — Data Acquisition (EPIC-BIO-DATA)**: Pipelines for Cell Collective, GINsim, and Literature.
-   **Phase 3 — Core Metrics (EPIC-BIO-METRICS)**: $D$-measure and BDM implementation.
-   **Phase 4 — Exp 1: Simplicity (EPIC-BIO-EXP1)**: Biological vs. Random ($D$ comparison).
-   **Phase 5 — Exp 2: Prediction (EPIC-BIO-EXP2)**: Knockouts and Essentiality.
-   **Phase 6 — Exp 3: Universality (EPIC-BIO-EXP3)**: Phase Transitions.
-   **Phase 7 — Paper & Artefacts (EPIC-BIO-PAPER)**: Final compilation.

---

## Tickets

### EPIC-BIO-SETUP (Phase 1)

-   **Ticket ID**: TSK-BIO-SETUP-001
    -   **Phase/Epic**: Phase 1 / EPIC-BIO-SETUP
    -   **Title**: Establish Python-Mathematica Bridge and Project Structure
    -   **Status**: completed
    -   **File IDs**: `src/integration/BioBridge.py`, `src/integration/BioLink.m`
    -   **Dependencies**: None
    -   **Acceptance Criteria**:
        -   Python script can call Mathematica kernel (or share files via `data/interchange`).
        -   Directory structure `data/bio/raw`, `data/bio/processed` established.
        -   `bioProcess.tex` compiles.
    -   **Deliverables**: `BioLink` module, folder structure.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-SETUP-001-Test.nb`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: Python script writes a JSON, Mathematica reads it, computes $1+1$, writes JSON back, Python verifies.
    -   **Documentation Requirement**: Append "Infrastructure Verification" section to `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-SETUP-002
    -   **Phase/Epic**: Phase 1 / EPIC-BIO-SETUP
    -   **Title**: Integrate BDM Library (`pybdm`)
    -   **Status**: completed
    -   **File IDs**: `src/integration/BDM_Wrapper.py`
    -   **Dependencies**: TSK-BIO-SETUP-001
    -   **Acceptance Criteria**:
        -   `pybdm` installed and importable.
        -   Wrapper function `compute_bdm(matrix)` returns BDM value and block decomposition.
    -   **Deliverables**: BDM utility module.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-SETUP-002-Test.py`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: Compute BDM for a 4x4 zero matrix and a random matrix; assert BDM(random) > BDM(zero).
    -   **Documentation Requirement**: Document BDM baseline values in `bioProcess.tex`.

### EPIC-BIO-DATA (Phase 2)

-   **Ticket ID**: TSK-BIO-DATA-001
    -   **Phase/Epic**: Phase 2 / EPIC-BIO-DATA
    -   **Title**: Implement Cell Collective & GINsim Loaders
    -   **Status**: completed
    -   **File IDs**: `src/integration/grn_data_pipeline.py`
    -   **Dependencies**: TSK-BIO-SETUP-001
    -   **Acceptance Criteria**:
        -   Script downloads/parses SBML-qual or JSON from repositories.
        -   Extracts: Connectivity Matrix (CM), Logic Gates, Gene Names.
        -   Converts to standardized JSON format.
    -   **Deliverables**: `GRNLoader` class, `data/bio/processed/lambda_phage.json` (and others).
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-DATA-001-Test.py`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: Verify Lambda Phage network has 4 nodes and correct edges matches literature (Gardner 2000).
    -   **Documentation Requirement**: Table of downloaded networks (Nodes, Edges, Reference) added to `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-DATA-002
    -   **Phase/Epic**: Phase 2 / EPIC-BIO-DATA
    -   **Title**: Implement Truth Table Generator & Validator
    -   **Status**: completed
    -   **File IDs**: `src/integration/LogicParser.py`
    -   **Dependencies**: TSK-BIO-DATA-001
    -   **Acceptance Criteria**:
        -   Parses boolean strings (e.g., "A AND NOT B") into Truth Tables.
        -   Classifies tables into `Integration` gates (AND, OR, CANALISING, etc.).
        -   Validates against `Integration'Gates'TruthTable`.
    -   **Deliverables**: Validated network files with explicit gate types.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-DATA-002-Test.py`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: "A AND NOT B" correctly identified as CANALISING or custom; truth table matches.
    -   **Documentation Requirement**: Gate distribution histogram (e.g., % Canalising vs % XOR) added to `bioProcess.tex`.

### EPIC-BIO-METRICS (Phase 3)

-   **Ticket ID**: TSK-BIO-METRICS-001
    -   **Phase/Epic**: Phase 3 / EPIC-BIO-METRICS
    -   **Title**: Implement Mechanistic Description Length ($D$)
    -   **Status**: completed
    -   **File IDs**: `src/Packages/Integration/BioMetrics.m`
    -   **Dependencies**: TSK-BIO-DATA-002
    -   **Acceptance Criteria**:
        -   Mathematica function `ComputeDescriptionLength[net]` implementing Protocol Def 2.1.
        -   Handles all gate types (KOFN, Canalising parameters).
    -   **Deliverables**: Mathematica package update.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-METRICS-001-Test.nb`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: $D$ calculation for a known simple network matches hand-calculated value.
    -   **Documentation Requirement**: Formula explanation and validation case added to `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-METRICS-002
    -   **Phase/Epic**: Phase 3 / EPIC-BIO-METRICS
    -   **Title**: Implement Degree-Preserving Randomization
    -   **Status**: completed
    -   **File IDs**: `src/Packages/Integration/BioExperiments.m`
    -   **Dependencies**: TSK-BIO-METRICS-001
    -   **Acceptance Criteria**:
        -   Algorithm to swap edges while preserving in/out degree.
        -   Function to generate $N$ random variants of a network.
    -   **Deliverables**: Randomization module.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-METRICS-002-Test.nb`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: Verify degree distribution remains identical after 1000 swaps; edges are different.
    -   **Documentation Requirement**: Proof of degree preservation (histogram comparison) added to `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-METRICS-003
    -   **Phase/Epic**: Phase 3 / EPIC-BIO-METRICS
    -   **Title**: Evaluate Zenil's Compression-Based Metrics
    -   **Status**: completed
    -   **File IDs**: `experiments/bio/ZenilTruthTableCompression.py`
    -   **Dependencies**: TSK-BIO-DATA-002
    -   **Acceptance Criteria**:
        -   Compute BDM and Compression Ratio for Truth Tables (Single Gene and Concatenated).
        -   Compare with $D$ metric and Essentiality.
    -   **Deliverables**: Evaluation Report `zenil_evaluation.txt`.
    -   **Unit Test ID**: N/A
    -   **Test Location**: `experiments/bio`
    -   **Test Acceptance**: Clear conclusion on applicability to GRNs.
    -   **Documentation Requirement**: "Evaluation of Algorithmic Complexity Metrics" section in `bioProcess.tex`.


### EPIC-BIO-EXP1 (Phase 4)

-   **Ticket ID**: TSK-BIO-EXP1-001
    -   **Phase/Epic**: Phase 4 / EPIC-BIO-EXP1
    -   **Title**: Execute Simplicity Experiment ($D_{bio}$ vs $D_{rand}$)
    -   **Status**: completed
    -   **File IDs**: `experiments/bio/Exp1_Simplicity.nb`
    -   **Dependencies**: TSK-BIO-METRICS-002
    -   **Acceptance Criteria**:
        -   Run on at least 5 biological networks (Lambda, Lac, Cell Cycle, etc.).
        -   Generate 1000 null models per network.
        -   Compute Z-scores and p-values.
    -   **Deliverables**: Results CSV, Plots.
    -   **Unit Test ID**: N/A (Experiment)
    -   **Test Location**: `experiments/bio`
    -   **Test Acceptance**: Reproducible run script.
    -   **Documentation Requirement**: "The Algorithmic Simplicity of Biology" section in `bioProcess.tex` with Box Plots and T-test tables.

-   **Ticket ID**: TSK-BIO-EXP1-002
    -   **Phase/Epic**: Phase 4 / EPIC-BIO-EXP1
    -   **Title**: Correlate $D$ with BDM
    -   **Status**: completed
    -   **File IDs**: `experiments/bio/Exp1_Simplicity.nb`
    -   **Dependencies**: TSK-BIO-EXP1-001, TSK-BIO-SETUP-002
    -   **Acceptance Criteria**:
        -   Generate repertoires (attractors) for all networks.
        -   Compute BDM on repertoires.
        -   Correlate Mechanistic $D$ with Behavioral BDM.
    -   **Deliverables**: Scatter plots ($D$ vs BDM).
    -   **Unit Test ID**: N/A
    -   **Test Location**: `experiments/bio`
    -   **Test Acceptance**: Positive correlation confirmed.
    -   **Documentation Requirement**: "Mechanism vs Behavior" analysis added to `bioProcess.tex`.

### EPIC-BIO-EXP2 (Phase 5)

-   **Ticket ID**: TSK-BIO-EXP2-001
    -   **Phase/Epic**: Phase 5 / EPIC-BIO-EXP2
    -   **Title**: Implement In-Silico Knockout & Phenotype Impact
    -   **Status**: completed
    -   **File IDs**: `src/Packages/Integration/BioExperiments.m`
    -   **Dependencies**: TSK-BIO-EXP1-001
    -   **Acceptance Criteria**:
        -   Function to set node $i$ to constant 0 (KO).
        -   Measure "Collapse": $\Delta D$ (change in description length) or $\Delta \text{Attractor}$ (state space change).
    -   **Deliverables**: Knockout simulation engine.
    -   **Unit Test ID**: `tests/Bio/TSK-BIO-EXP2-001-Test.nb`
    -   **Test Location**: `tests/Bio`
    -   **Test Acceptance**: KO of a root node changes attractors; KO of a leaf node might not.
    -   **Documentation Requirement**: Knockout methodology section in `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-EXP2-002
    -   **Phase/Epic**: Phase 5 / EPIC-BIO-EXP2
    -   **Title**: Validate Predictions against Essentiality Data
    -   **Status**: completed
    -   **File IDs**: `experiments/bio/Exp2_Prediction.nb`
    -   **Dependencies**: TSK-BIO-EXP2-001
    -   **Acceptance Criteria**:
        -   Load essentiality data (e.g., E. coli DEG).
        -   Rank genes by $\Delta D$.
        -   Compute ROC/AUC for predicting essential genes.
    -   **Deliverables**: ROC Curves, "Causal Criticality" ranking.
    -   **Unit Test ID**: N/A
    -   **Test Location**: `experiments/bio`
    -   **Test Acceptance**: AUC > 0.7.
    -   **Documentation Requirement**: "Predictive Power of Causal Integration" section in `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-EXP2-004
    -   **Phase/Epic**: Phase 5 / EPIC-BIO-EXP2
    -   **Title**: Full Statistical Pipeline for $\Delta D$ Essentiality
    -   **Status**: completed
    -   **File IDs**: `src/scripts/GlobalStatsPipeline.m`
    -   **Dependencies**: TSK-BIO-EXP2-002
    -   **Acceptance Criteria**:
        -   Compute Cohen's d, Mann-Whitney U, and AUC for global dataset.
        -   Store results in `results/bio/validation/global_stats.json`.
    -   **Deliverables**: Statistical report JSON, updated `bioProcess.tex`.
    -   **Documentation Requirement**: Statistical Assessment section in `bioProcess.tex`.

-   **Ticket ID**: TSK-BIO-EXP2-005
    -   **Phase/Epic**: Phase 5 / EPIC-BIO-EXP2
    -   **Title**: Behavioural $\Delta$BDM Knockouts
    -   **Status**: completed
    -   **File IDs**: `src/scripts/BehavioralKnockoutAnalysis.m`
    -   **Dependencies**: TSK-BIO-EXP2-004
    -   **Acceptance Criteria**:
        -   Compute BDM for original and knockout networks.
        -   Calculate $\Delta \text{BDM}$ for each gene.
        -   Correlate $\Delta \text{BDM}$ with $\Delta D$ and Essentiality.
    -   **Deliverables**: `results/bio/knockouts/bdm_knockouts.json`, Plots.
    -   **Documentation Requirement**: "Behavioural Impact of Knockouts" section in `bioProcess.tex`.

### EPIC-BIO-EXP3 (Phase 6)

-   **Ticket ID**: TSK-BIO-EXP3-001
    -   **Phase/Epic**: Phase 6 / EPIC-BIO-EXP3
    -   **Title**: Execute Phase Transition Sweep
    -   **Status**: completed
    -   **File IDs**: `src/scripts/PhaseTransitionExperiment.m`
    -   **Dependencies**: TSK-BIO-METRICS-002
    -   **Acceptance Criteria**:
        -   Generate synthetic networks with varying XOR/Canalising ratios (0% to 100%).
        -   Measure $D$ and BDM.
        -   Identify critical threshold (Phase Transition).
    -   **Deliverables**: `results/bio/phase_transition/phase_transition.json`, Phase diagrams.
    -   **Unit Test ID**: N/A
    -   **Test Location**: `src/scripts`
    -   **Test Acceptance**: "Edge of Chaos" peak visible.
    -   **Documentation Requirement**: "Universality and Phase Transitions" section in `bioProcess.tex`.

### EPIC-BIO-PAPER (Phase 7)

-   **Ticket ID**: TSK-BIO-PAPER-001
    -   **Phase/Epic**: Phase 7 / EPIC-BIO-PAPER
    -   **Title**: Compile Final Bio-Process Document
    -   **Status**: completed
    -   **File IDs**: `doc/newIntPaper/bioProcess.pdf`
    -   **Dependencies**: All previous tickets
    -   **Acceptance Criteria**:
        -   Full compilation of `bioProcess.tex` with all appended sections.
        -   Executive summary written.
        -   Ready for conversion to Nature manuscript format.
    -   **Deliverables**: `bioProcess.pdf`.
    -   **Unit Test ID**: N/A
    -   **Test Location**: `doc/newIntPaper`
    -   **Test Acceptance**: PDF exists and is readable.
    -   **Documentation Requirement**: Final sign-off.
