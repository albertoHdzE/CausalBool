# Programme Plan: Structural Algorithmic Simplicity (Nature Protocol)
**Document ID:** `PLAN-NATURE-LEV2`
**Status:** Approved / In-Progress
**Owner:** Complexity Science Group (Oxford Persona)
**Target:** *Nature* / *Nature Communications*

---

## 1. Strategic Evaluation & Theoretical Foundation

### 1.1 The Verdict: Why We Pivoted
The previous metric, $D_{v1}$ (Mechanistic Description Length), measured the complexity of *components* (node biases) but was blind to the *assembly* (wiring). This is a critical flaw: random networks with identical degree sequences yield similar $D_{v1}$ values to biological ones, suggesting that biology is only "simple" because its parts are simple, not because its architecture is elegant.

To claim **"Universality of Algorithmic Simplicity,"** we must prove that the *wiring diagram itself* is algorithmically compressible. We introduce **Structural Description Length ($D_{v2}$)**, which encodes the network via:
1.  **Motifs**: Compressing repeated sub-circuits (FFLs, Bifans).
2.  **Hierarchy**: Compressing the flow structure (Feed-forward layers vs. Feedback loops).

### 1.2 The "Tri-Phylum" Dataset Strategy
To demonstrate universality, we cannot rely on "more of the same." We define an "Exotic" dataset strategy to cover three fundamental modes of biological information processing:
1.  **The Maintainers (Homeostasis):** Stable, robust networks (e.g., Metabolism, Stress Response).
2.  **The Deciders (Fate):** Bistable, irreversible switches (e.g., Cell Cycle, Differentiation).
3.  **The Signal Processors (Exotic):** Fast, transient, spatial logic (e.g., Wnt/EGFR signaling, Drosophila patterning, simple neural circuits).

**Hypothesis:** $D_{v2}$ will minimize efficiently across all three classes, revealing a universal design principle independent of biological function.

### 1.3 The "Strong" Null Hypothesis
We elevate the statistical rigor by comparing Biology not against "Random" (Erdős-Rényi), but against **Degree-Preserving Randomization**.
*   **Null Model:** Randomized networks that preserve the exact in/out-degree sequence of the biological original.
*   **Prediction:** $D_{v2}(Bio) \ll D_{v2}(Null_{degree})$.
*   **Meaning:** Even with the same "parts list" and "connectivity budget," Evolution selects a specific, highly compressible architecture.

---

## 2. Epics and Phases

*   **Phase 1 — Structural Encoding (EPIC-NATURE-SETUP)**: Implementing the Python encoders for Motifs and Hierarchy.
*   **Phase 2 — The Unified Metric (EPIC-NATURE-METRICS)**: Implementing $D_{v2}$ in Mathematica.
*   **Phase 3 — Dataset Expansion (EPIC-NATURE-DATA)**: Curating the Tri-Phylum dataset (15-20 networks).
*   **Phase 4 — Validation (EPIC-NATURE-EXP)**: Simplicity V2 and The Generative Test.
*   **Phase 5 — Manuscript (EPIC-NATURE-PAPER)**: Writing the "Protocol Level 2" paper.

---

## 3. Tickets (Execution Plan)

### EPIC-NATURE-SETUP (Phase 1)

*   **Ticket ID**: TSK-NATURE-SETUP-001
    *   **Phase/Epic**: Phase 1 / EPIC-NATURE-SETUP
    *   **Title**: Implement `MotifEncoder` Engine
    *   **Status**: pending
    *   **File IDs**: `src/integration/MotifEncoder.py`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Class `MotifEncoder` accepts an adjacency matrix.
        *   Identifies occurrences of 3-node motifs (FFL, Feedback Loop, Bifan).
        *   Returns a dictionary of motifs and a calculated `motif_cost` (bits).
        *   **Unit Test**: Detects 1 FFL in a hardcoded 3-node FFL graph.
    *   **Unit Test ID**: `tests/Nature/TSK-NATURE-SETUP-001-Test.py`
    *   **Context**: This is the "dictionary" part of the compression. Frequent subgraphs become short codes.

*   **Ticket ID**: TSK-NATURE-SETUP-002
    *   **Phase/Epic**: Phase 1 / EPIC-NATURE-SETUP
    *   **Title**: Implement `HierarchyEncoder` Engine
    *   **Status**: pending
    *   **File IDs**: `src/integration/HierarchyEncoder.py`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Class `HierarchyEncoder` accepts an adjacency matrix.
        *   Performs topological sort / condensation to assign nodes to layers.
        *   Identifies "Feedback Edges" (violating the feed-forward flow).
        *   Returns `hierarchy_cost` (bits).
        *   **Unit Test**: A pure DAG has 0 feedback edges; A cycle has 1+.
    *   **Unit Test ID**: `tests/Nature/TSK-NATURE-SETUP-002-Test.py`
    *   **Context**: Measures how close the network is to a "Feed-Forward" pipeline.

### EPIC-NATURE-METRICS (Phase 2)

*   **Ticket ID**: TSK-NATURE-METRICS-001
    *   **Phase/Epic**: Phase 2 / EPIC-NATURE-METRICS
    *   **Title**: Implement Structural Description Length ($D_{v2}$)
    *   **Status**: completed
    *   **File IDs**: `src/integration/BioMetrics.m`
    *   **Dependencies**: TSK-NATURE-SETUP-001, TSK-NATURE-SETUP-002
    *   **Acceptance Criteria**:
        *   Mathematica function `ComputeDescriptionLengthV2[cm, dynamic]` implemented.
        *   Calls Python `MotifEncoder` and `HierarchyEncoder` via `BioBridge`.
        *   Sum: $D_{v2} = D_{size} + D_{motif} + D_{hierarchy} + D_{gates} + D_{params}$.
    *   **Unit Test ID**: `tests/Nature/TSK-NATURE-METRICS-001-Test.nb`
    *   **Context**: The master formula. Must replace $D_{v1}$ in all future experiments.

*   **Ticket ID**: TSK-NATURE-METRICS-002
    *   **Phase/Epic**: Phase 2 / EPIC-NATURE-METRICS
    *   **Title**: Integrate Mathematica BDM (Legacy/Robust)
    *   **Status**: completed
    *   **File IDs**: `src/integration/NatureBDM.wl`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Locate/Wrap the original `mathematicabdm/BDMandNormalizedBDM.nb` logic.
        *   Implement `ComputeBDM[matrix]` in Mathematica using `D5.m` lookup.
        *   Ensure it matches the user's requirement for "old implementation".
    *   **Context**: User explicitly requested using the Mathematica implementation for BDM instead of `pybdm`.

### EPIC-NATURE-DATA (Phase 3)

*   **Ticket ID**: TSK-NATURE-DATA-001
    *   **Phase/Epic**: Phase 3 / EPIC-NATURE-DATA
    *   **Title**: Curate "Tri-Phylum" Dataset (15-20 Networks)
    *   **Status**: completed
    *   **File IDs**: `data/bio/processed/*.json`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Select 15-20 high-quality networks from Cell Collective.
        *   **Stratification**:
            *   5+ Maintainers (Metabolism).
            *   5+ Deciders (Differentiation).
            *   5+ Exotic/Signal (Signaling, Patterning).
        *   All networks downloaded, cleaned, and validated (no disconnected nodes).
    *   **Deliverables**: `nature_dataset.json` list.
    *   **Context**: The fuel for our universality claim.

### EPIC-NATURE-EXP (Phase 4)

*   **Ticket ID**: TSK-NATURE-EXP-001
    *   **Phase/Epic**: Phase 4 / EPIC-NATURE-EXP
    *   **Title**: Run Simplicity V2 Experiment (Real vs Null)
    *   **Status**: completed
    *   **File IDs**: `src/experiments/SimplicityV2_Nature.py`
    *   **Dependencies**: TSK-NATURE-METRICS-001, TSK-NATURE-METRICS-002, TSK-NATURE-DATA-001
    *   **Acceptance Criteria**:
        *   Load all 10 curated networks.
        *   Compute $D_{v2}$ (Struct) and $K_{BDM}$ (Behav) for each.
        *   Generate 100 degree-preserving nulls per network.
        *   Compute Z-scores for $D_{v2}$ and $K_{BDM}$.
        *   Plot Mechanism vs Behaviour landscape.
    *   **Progress**: Real data analysis completed. Null model generation completed. Documentation updated.

### EPIC-NATURE-WRITE (Phase 5)

*   **Ticket ID**: TSK-NATURE-PAPER-001
    *   **Phase/Epic**: Phase 5 / EPIC-NATURE-PAPER
    *   **Title**: Draft "Protocol Level 2" Manuscript
    *   **Status**: completed
    *   **File IDs**: `doc/newIntPaper/towardsNature/nature_draft.tex`
    *   **Dependencies**: TSK-NATURE-EXP-001
    *   **Acceptance Criteria**:
        *   Abstract, Methods ($D_{v2}$), Results (Tri-Phylum).
        *   Discussion: The "Language of Biological Networks."
    *   **Context**: The final artifact.
