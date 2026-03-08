# Programme Plan: Asynchronous Dynamics & Basin Entropy (Nature Protocol Level 6)
**Document ID:** `PLAN-NATURE-LEV6-BASIN`
**Status:** Active
**Owner:** Complexity Science Group (Oxford Persona)
**Target:** *Nature Communications* / *Physical Review E* (Pivot Target)
**Previous Protocol:** `PLAN-NATURE-LEV5-HYBRID` (Outcome: PIVOT_BASIN)

---

## 1. Strategic Evaluation & Theoretical Foundation

### 1.1 The Pivot: From Trajectories to Basins
The execution of the **Level 5 Contingency Protocol** resulted in a **PIVOT_BASIN** decision. The key findings were:
1.  **Trajectory Failure:** Synchronous trajectory complexity ($D_{dyn}$) failed to predict essentiality (AUC 0.48), performing worse than random guessing.
2.  **Structural Dominance:** The structural metric ($D_{struct}$) remained the best predictor (AUC 0.62).
3.  **Attractor Simplicity:** Biological attractors under synchronous updates are often trivial fixed points with negligible LZ complexity.

**Conclusion:** The information content of biological control systems is not in the *single* trajectory but in the *global landscape* of the state space—specifically, the size, number, and stability of the **Basins of Attraction**.

### 1.2 The Basin Entropy Hypothesis
We propose the **Basin Entropy Hypothesis**:
Biological networks optimize their **Basin Entropy** ($H_B$) to balance **Robustness** (large basins for functional states) and **Plasticity** (multiple reachable attractors).
$$ H_B = - \sum_{i=1}^{k} p_i \log_2 p_i $$
Where $p_i$ is the relative size of the $i$-th basin of attraction.

We hypothesize that:
1.  **Tuned Entropy:** Biological networks have an intermediate $H_B$ compared to random nulls (which may shatter into many small basins or collapse to one).
2.  **Essentiality Correlation:** Essential genes are those whose knockout causes a **Collapse of the Basin Landscape** (drastic change in $H_B$ or loss of the primary functional basin).

### 1.3 Objectives & Success Metrics
*   **Primary Objective:** To develop and validate the `Basin_Encoder`.
*   **Key Result 1:** Demonstrate that $H_B$ separates Biological Networks from Null Models.
*   **Key Result 2:** Achieve Pearson correlation $\rho < -0.5$ (or AUC > 0.70) with DepMap Essentiality scores using $\Delta H_B$.

---

## 2. Epics and Phases

*   **Phase 1 — Asynchronous Dynamics (EPIC-LEV6-ASYNC)**: Upgrade the simulator to support General Asynchronous (GA) updates and Monte Carlo sampling for basin estimation.
*   **Phase 2 — Basin Metrics (EPIC-LEV6-METRICS)**: Implement `Basin_Entropy` and `Basin_Encoder` to quantify landscape properties.
*   **Phase 3 — Landscape Validation (EPIC-LEV6-VALIDATION)**: Validate the metric against the DepMap essentiality dataset.

---

## 3. Tickets (Execution Plan)

### EPIC-LEV6-ASYNC (Phase 1)

*   **Ticket ID**: TSK-LEV6-ASYNC-001
    *   **Title**: Implement Asynchronous Boolean Dynamics
    *   **Status**: pending
    *   **File IDs**: `src/dynamics/Boolean_Dynamics.py`
    *   **Description**: Upgrade `BooleanDynamics` to support `update_mode='asynchronous'`.
    *   **Acceptance Criteria**:
        *   Randomly select *one* node to update per step (General Asynchronous).
        *   Support `simulate_ensemble(steps, samples)` to run multiple stochastic trajectories from the *same* initial state (to check for non-determinism) or *different* initial states.

### EPIC-LEV6-METRICS (Phase 2)

*   **Ticket ID**: TSK-LEV6-METRICS-001
    *   **Title**: Implement Basin Entropy Estimator
    *   **Status**: pending
    *   **File IDs**: `src/complexity/Basin_Entropy.py`
    *   **Description**: A tool to estimate basin sizes via Monte Carlo sampling.
    *   **Acceptance Criteria**:
        *   Function `estimate_basin_entropy(network, samples=1000)`.
        *   Algorithm:
            1.  Sample $S$ random initial states.
            2.  Evolve each to an attractor (fixed point or limit cycle).
            3.  Identify unique attractors (hash state vectors).
            4.  Count frequency $n_i$ of each attractor.
            5.  Compute $p_i = n_i / S$ and $H_B$.

*   **Ticket ID**: TSK-LEV6-METRICS-002
    *   **Title**: Implement Basin Encoder
    *   **Status**: pending
    *   **File IDs**: `src/integration/Basin_Encoder.py`
    *   **Description**: Wrapper class for the pipeline.
    *   **Acceptance Criteria**:
        *   Method `compute_basin_metrics()` returning $\{H_B, N_{attractors}, p_{max}\}$.

### EPIC-LEV6-VALIDATION (Phase 3)

*   **Ticket ID**: TSK-LEV6-VALIDATION-001
    *   **Title**: Run Basin Essentiality Validation
    *   **Status**: pending
    *   **File IDs**: `src/experiments/run_level6_validation.py`
    *   **Description**: Execute the knockout validation using $\Delta H_B$.
    *   **Acceptance Criteria**:
        *   For each gene, compute $\Delta H_B = H_B^{WT} - H_B^{KO}$.
        *   Compare against DepMap essentiality (AUC calculation).

---

## 4. Technical Preconditions & Resources
*   **Sampling Depth:** For $N \approx 20-50$, $S=1000$ samples is sufficient to estimate major basins ($p > 0.01$).
*   **Convergence:** Need to detect when an attractor is reached. Use a window-based detection (if state repeats within window $W$).
