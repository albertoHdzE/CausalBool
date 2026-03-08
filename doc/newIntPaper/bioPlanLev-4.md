# Programme Plan: Contingency Activation Reformulation (Nature Protocol Level 4)
**Document ID:** `PLAN-NATURE-LEV4-REFORM`
**Status:** In-Progress
**Owner:** Complexity Science Group (Oxford Persona)
**Target:** *Nature* / *Nature Communications* (Internal Optimization Protocol)

---

## 1. Strategic Evaluation & Theoretical Foundation

### 1.1 The Rationale: From Binary to Bayesian
The previous contingency protocols (Level 3) relied on scalar thresholds (e.g., $D_{bio} \approx D_{rand}$ or $\rho < 0.3$) which are susceptible to Type I errors (false positives) in the presence of noise or finite-size effects. In Complex Adaptive Systems (CAS), "failure" to exhibit low algorithmic complexity ($D$) can sometimes indicate "criticality" (Edge of Chaos) rather than randomness.

**Level 4 Reformulation** addresses this by introducing a multi-dimensional validation framework:
1.  **Bayesian Evidence:** Moving from p-values to Bayes Factors ($BF_{01}$) to quantify the *strength* of evidence for the null hypothesis.
2.  **Non-Linearity:** Using Mutual Information (MI) to detect dependencies that linear correlation ($\rho$) misses.
3.  **Emergence Checks:** Distinguishing "Randomness" from "Criticality" using Lempel-Ziv complexity and Algorithmic Efficiency Ratios (AER).

### 1.2 The Objective
To implement a rigorous **"Go/No-Go" Decision Matrix** that mathematically distinguishes between:
*   **Stochastic Noise** (Keep iterating)
*   **Systemic Bias** (Refine null models)
*   **Theoretical Falsification** (Trigger Contingency)
*   **Emergent Complexity** (Publish as novel finding)

---

## 2. Epics and Phases

*   **Phase 1 — Statistical Foundation (EPIC-LEV4-FOUNDATION)**: Implement the core statistical engines for Bayesian Model Comparison and Mutual Information analysis.
*   **Phase 2 — Multi-Scale Validation (EPIC-LEV4-VALIDATION)**: Develop tools to assess scaling laws ($D(b) \sim b^\alpha$) and intrinsic Lempel-Ziv complexity.
*   **Phase 3 — Integration & Automation (EPIC-LEV4-INTEGRATION)**: Integrate these metrics into the main pipeline to automate the "Go/No-Go" decision process.

---

## 3. Tickets (Execution Plan)

### EPIC-LEV4-FOUNDATION (Phase 1)

*   **Ticket ID**: TSK-LEV4-FOUNDATION-001
    *   **Phase/Epic**: Phase 1 / EPIC-LEV4-FOUNDATION
    *   **Title**: Implement Bayesian Evidence Calculator
    *   **Status**: pending
    *   **File IDs**: `src/stats/Bayes_Factor_Calculator.py`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Implement `calculate_bayes_factor(data, null_model)` function.
        *   Support Gaussian ($H_1$) vs. Gaussian ($H_0$) comparison.
        *   Output $BF_{10}$ and $BF_{01}$ (log-scale support).
        *   **Validation**: $BF_{10}$ must exceed 100 for clearly separated distributions (e.g., $N(0,1)$ vs $N(5,1)$).
    *   **Unit Test ID**: `tests/Lev4/TSK-LEV4-FOUNDATION-001-Test.py`

*   **Ticket ID**: TSK-LEV4-FOUNDATION-002
    *   **Phase/Epic**: Phase 1 / EPIC-LEV4-FOUNDATION
    *   **Title**: Implement Mutual Information Analyzer
    *   **Status**: pending
    *   **File IDs**: `src/stats/Mutual_Information_Analyzer.py`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Implement `compute_MI(x, y)` using k-nearest neighbor estimators (Kraskov et al.) or binning.
        *   Handle continuous vs. discrete variables.
        *   **Validation**: Detect a sine wave relationship ($y = \sin(x)$) where Pearson $\rho \approx 0$ but $MI > 0.5$.
    *   **Unit Test ID**: `tests/Lev4/TSK-LEV4-FOUNDATION-002-Test.py`

### EPIC-LEV4-VALIDATION (Phase 2)

*   **Ticket ID**: TSK-LEV4-VALIDATION-001
    *   **Phase/Epic**: Phase 2 / EPIC-LEV4-VALIDATION
    *   **Title**: Scaling Exponent & Lempel-Ziv Tools
    *   **Status**: pending
    *   **File IDs**: `src/complexity/Scaling_LZ_Tools.py`
    *   **Dependencies**: None
    *   **Acceptance Criteria**:
        *   Implement `compute_scaling_exponent(matrix)`: Calculate $D_{v2}$ at block sizes $b \in \{3, 4, 5, 6\}$ and fit power law.
        *   Implement `compute_lz_complexity(string)`: Standard LZ76 algorithm.
        *   **Validation**: Random matrices should show $\alpha \approx 2$ (dimensionality), while fractal structures show $\alpha < 2$.
    *   **Unit Test ID**: `tests/Lev4/TSK-LEV4-VALIDATION-001-Test.py`

### EPIC-LEV4-INTEGRATION (Phase 3)

*   **Ticket ID**: TSK-LEV4-INTEGRATION-001
    *   **Phase/Epic**: Phase 3 / EPIC-LEV4-INTEGRATION
    *   **Title**: Automated Decision Matrix
    *   **Status**: pending
    *   **File IDs**: `src/pipeline/Contingency_Monitor.py`
    *   **Dependencies**: All previous tickets
    *   **Acceptance Criteria**:
        *   Input: Simulation results ($D_{bio}$, $D_{nulls}$, DepMap correlations).
        *   Logic: Implement the "Go/No-Go" table (see Section 4).
        *   Output: `Action_Code` (CONTINUE, ITERATE, PIVOT, PUBLISH_EMERGENCE).
        *   Generate a `Contingency_Report.md` automatically.
    *   **Unit Test ID**: `tests/Lev4/TSK-LEV4-INTEGRATION-001-Test.py`

---

## 4. Reformulated Contingency Protocols

### 4.1 The "Go/No-Go" Decision Matrix

| Metric | Condition | Interpretation | Action |
| :--- | :--- | :--- | :--- |
| **Z-Score ($Z_{deg}$)** | $Z > -2.0$ (Global Mean) | **Falsification** | **TRIGGER PIVOT** (Hybrid Encoding) |
| **Bayes Factor** | $BF_{01} > 10$ (Null Favored) | **Falsification** | **TRIGGER PIVOT** |
| **DepMap Correlation** | $\rho < 0.2$ AND $MI \approx 0$ | **Weakness** | **TRIGGER PIVOT** (Cell Lines) |
| **DepMap Correlation** | $0.2 < \rho < 0.4$ | **Noise** | **ITERATE** (Refine Features, Increase N) |
| **Criticality Check** | $D_{bio}$ High but $AER > 1.0$ | **Emergence** | **NO ACTION** (Publish as "Edge of Chaos") |
| **Scaling Law** | $\alpha_{bio} \approx \alpha_{rand}$ | **Fractal Randomness** | **TRIGGER PIVOT** |

### 4.2 Detailed Action Plans

#### Plan A: Iterative Refinement (Action: ITERATE)
*   **Trigger**: Weak signals ($\rho \approx 0.3$) or ambiguous Bayes Factors ($1 < BF < 3$).
*   **Steps**:
    1.  Increase sample size ($N \to 2N$).
    2.  Switch to "Consensus Nulls" (intersection of Degree and Gate preserving).
    3.  Re-run analysis.

#### Plan B: Scientific Pivot (Action: PIVOT)
*   **Trigger**: Strong Falsification ($BF_{01} > 10$ or $Z > -2.0$).
*   **Steps**:
    1.  **Stop** current Phase 3 compute jobs.
    2.  **Activate** `Hybrid_Encoder_v1` (70% BDM + 30% Motifs).
    3.  **Retarget** manuscript to *Nature Communications* or *Physical Review E*.

#### Plan C: Emergence Publication (Action: PUBLISH_EMERGENCE)
*   **Trigger**: High Complexity ($D$) but High Efficiency ($AER$).
*   **Steps**:
    1.  Reframe hypothesis from "Minimization of Description Length" to "Maximization of Algorithmic Efficiency."
    2.  Highlight the "Edge of Chaos" phase transition as the primary finding.

---

## 5. Quality Assurance & Validation

### 5.1 Preconditions
*   All existing Level 3 scripts (`Universal_D_v2_Encoder.py`, `Null_Generator_HPC.py`) must be passing tests.
*   Python environment must support `pymc` or `scipy.stats` for Bayesian analysis.

### 5.2 Success Criteria
*   The `Contingency_Monitor` correctly identifies a "Random" network as **TRIGGER PIVOT**.
*   The `Contingency_Monitor` correctly identifies a "Critical" network (e.g., Ising model at $T_c$) as **PUBLISH_EMERGENCE**.
*   The `Contingency_Monitor` correctly identifies a "Noisy Linear" relationship as **ITERATE**.

### 5.3 Risk Mitigation
*   **Complexity Overload**: Bayesian computation can be slow. *Mitigation:* Use conjugate priors (analytical solutions) where possible instead of full MCMC.
*   **False Negatives**: MI requires sufficient data points. *Mitigation:* Enforce $N > 50$ samples before trusting MI results.

---

**Signed:**
*Complexity Science Group (AI Agent)*
*Date: 2026-02-07*
