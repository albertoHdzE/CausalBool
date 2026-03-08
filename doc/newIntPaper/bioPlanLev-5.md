# Programme Plan: Hybrid Encoding & Dynamical Integration (Nature Protocol Level 5)
**Document ID:** `PLAN-NATURE-LEV5-HYBRID`
**Status:** Active
**Owner:** Complexity Science Group (Oxford Persona)
**Target:** *Nature Communications* / *Physical Review E* (Pivot Target)
**Previous Protocol:** `PLAN-NATURE-LEV4-REFORM` (Outcome: PIVOT_HYBRID)

---

## 1. Strategic Evaluation & Theoretical Foundation

### 1.1 The Pivot: From Structure to Dynamics
The execution of the **Level 4 Contingency Protocol** resulted in a definitive **PIVOT_HYBRID** decision. The key findings were:
1.  **Structural Indistinguishability:** Biological networks had a global Z-score of $Z \approx -0.12$ under the $D_{v2}$ structural encoder, meaning they are algorithmically isomorphic to random graphs in terms of static topology.
2.  **Clinical Disconnect:** Structural complexity metrics ($D_{struct}$) showed negligible correlation ($\rho = -0.17$) with biological essentiality (DepMap).

**Conclusion:** The information content of biological control systems is not encoded in the *static wiring diagram* alone but in the *dynamical phase space* (attractor landscape) that the wiring enables.

### 1.2 The Hybrid Hypothesis
We propose the **Hybrid Complexity Hypothesis**:
$$ D_{bio} = \alpha \cdot D_{struct} + \beta \cdot D_{dyn} $$
Where:
*   $D_{struct}$: The Block Decomposition Entropy (Universal $D_{v2}$) - capturing wiring cost.
*   $D_{dyn}$: The Lempel-Ziv Complexity of the system's state trajectories - capturing functional richness.

We predict that while $D_{struct} \approx D_{rand}$, the dynamical complexity $D_{dyn}$ will show $D_{dyn}(Bio) \ll D_{dyn}(Rand)$ (High Order) or $D_{dyn}(Bio) \gg D_{dyn}(Rand)$ (High Richness), providing the missing separation.

### 1.3 Objectives & Success Metrics
*   **Primary Objective:** To develop and validate the `Hybrid_Encoder` ($D_{hybrid}$).
*   **Key Result 1:** Achieve $|Z_{hybrid}| > 2.0$ for separation between Bio and Nulls.
*   **Key Result 2:** Achieve Pearson correlation $\rho < -0.4$ with DepMap Essentiality scores.
*   **Key Result 3:** Identify the optimal weighting parameters ($\alpha, \beta$).

---

## 2. Epics and Phases

*   **Phase 1 — Dynamical Tools (EPIC-LEV5-DYNAMICS)**: Implement tools to simulate Boolean networks and compute Lempel-Ziv complexity on state trajectories.
*   **Phase 2 — Hybrid Integration (EPIC-LEV5-HYBRID)**: Develop the `Hybrid_Encoder` that combines structural and dynamical metrics.
*   **Phase 3 — Re-Validation (EPIC-LEV5-REVALIDATION)**: Re-run the High-Throughput (Phase 3) and Clinical (Phase 4) benchmarks using the new $D_{hybrid}$ metric.

---

## 3. Tickets (Execution Plan)

### EPIC-LEV5-DYNAMICS (Phase 1)

*   **Ticket ID**: TSK-LEV5-DYNAMICS-001
    *   **Title**: Implement Boolean Dynamics Simulator
    *   **Status**: pending
    *   **File IDs**: `src/dynamics/Boolean_Dynamics.py`
    *   **Description**: A high-performance simulator for synchronous and asynchronous Boolean updates.
    *   **Acceptance Criteria**:
        *   Input: Network JSON (adjacency + truth tables).
        *   Function: `simulate(network, steps=1000, initial_state='random', update_mode='synchronous')`.
        *   Output: State trajectory matrix $(T \times N)$.
        *   **Performance**: Must simulate 1000 steps for N=100 in < 0.1s.
        *   **Correctness**: Must reproduce the known attractor cycle of the "Mammalian Cell Cycle" model.
    *   **Unit Test**: `tests/Lev5/TSK-LEV5-DYNAMICS-001-Test.py`

*   **Ticket ID**: TSK-LEV5-DYNAMICS-002
    *   **Title**: Implement Trajectory Lempel-Ziv
    *   **Status**: pending
    *   **File IDs**: `src/complexity/Trajectory_LZ.py`
    *   **Description**: A tool to compute LZ76 complexity on multi-dimensional time series.
    *   **Acceptance Criteria**:
        *   Function: `compute_trajectory_lz(trajectory_matrix)`.
        *   Method: Binarize/Flatten trajectory or compute LZ on each node's time series and sum.
        *   **Validation**: Periodic attractor ($LZ \to 0$) vs. Chaotic attractor ($LZ \to 1$).
    *   **Unit Test**: `tests/Lev5/TSK-LEV5-DYNAMICS-002-Test.py`

### EPIC-LEV5-HYBRID (Phase 2)

*   **Ticket ID**: TSK-LEV5-HYBRID-001
    *   **Title**: Implement Hybrid Encoder Class
    *   **Status**: pending
    *   **File IDs**: `src/integration/Hybrid_Encoder.py`
    *   **Description**: The master class integrating structural and dynamical metrics.
    *   **Acceptance Criteria**:
        *   Class `HybridEncoder` inheriting from `UniversalDv2Encoder`.
        *   Method `compute_hybrid_complexity(network, alpha=0.5)`.
        *   Output dictionary with `d_struct`, `d_dyn`, `d_hybrid`.
        *   Must cache `d_struct` to avoid re-computation.

### EPIC-LEV5-REVALIDATION (Phase 3)

*   **Ticket ID**: TSK-LEV5-REVALIDATION-001
    *   **Title**: Re-run DepMap Validation with Hybrid Metric
    *   **Status**: pending
    *   **File IDs**: `src/analysis/DepMap_Hybrid_Validation.py`
    *   **Description**: Re-execute the clinical validation pipeline using $D_{hybrid}$.
    *   **Acceptance Criteria**:
        *   Compute correlation between $\Delta D_{hybrid}$ and Dependency Scores.
        *   **Success Threshold**: $\rho < -0.4$ (Moderate Correlation).
        *   Generate comparison plot: $\rho(D_{struct})$ vs $\rho(D_{hybrid})$.

---

## 4. Technical Preconditions & Resources

### 4.1 Resource Requirements
*   **Compute**: High-Performance Cluster (HPC) access for dynamical simulations (computationally more expensive than static analysis).
    *   Estimate: 50 CPU-hours per 100 networks (Simulating 1000 steps x 1000 initial conditions).
*   **Storage**: 50GB for storing trajectory data (optional: store only metrics to save space).

### 4.2 Dependencies
*   **Python Libraries**: `numpy`, `scipy`, `networkx`, `boolean2` (optional).
*   **Data**: Existing Phase 2 dataset ($N=231$ networks).

---

## 5. Risk Management

*   **Risk**: Computational Explosion ($O(2^N)$ state space).
    *   **Mitigation**: Use Monte Carlo sampling of start states (N=100) instead of full enumeration. Do not attempt full attractor landscape mapping for $N > 20$.
*   **Risk**: Chaotic Nulls.
    *   **Mitigation**: Random Boolean Networks (RBNs) are often chaotic (Kauffman). Ensure null models are also simulated under the same update rules to provide a fair baseline.
*   **Risk**: Zero Dynamics (Fixed Points).
    *   **Mitigation**: Many biological networks settle to fixed points quickly ($LZ=0$). Use asynchronous updates or perturbation analysis (flipping bits) to probe transient complexity.

---

## 6. Unit Testing Framework

All components must pass the `Lev5` test suite before integration.

```python
# tests/Lev5/TSK-LEV5-DYNAMICS-001-Test.py
def test_mammalian_cycle():
    net = load_mammalian_cycle()
    traj = simulate(net, steps=20)
    assert traj[-1] == traj[0] # Checks for cycle closure
```

```python
# tests/Lev5/TSK-LEV5-HYBRID-001-Test.py
def test_hybrid_weighting():
    encoder = HybridEncoder()
    # Case 1: Pure Structure
    res_struct = encoder.compute(net, alpha=1.0, beta=0.0)
    assert res_struct['d_hybrid'] == res_struct['d_struct']
    # Case 2: Pure Dynamics
    res_dyn = encoder.compute(net, alpha=0.0, beta=1.0)
    assert res_dyn['d_hybrid'] == res_dyn['d_dyn']
```

---

**Signed:**
*Complexity Science Group (AI Agent)*
*Date: 2026-02-08*
