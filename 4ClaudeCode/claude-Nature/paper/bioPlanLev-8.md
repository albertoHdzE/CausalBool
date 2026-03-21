# BioPlan Level 8 (Nature-Grade Execution Plan)
## CausalBool — Algorithmic Efficiency in Gene Regulatory Networks (GRNs)

**Document ID:** BIOPLAN-LEV8  
**Location:** `/Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/bioPlanLev-8.md`  
**Target Journal:** Nature (primary); Nature Communications (secondary, fallback)  
**Primary Outcome:** A single coherent Nature submission with one core claim and one killer result, plus parallel tracks for two additional killer results (as Extended Data or follow-up papers depending on strength).  
**Operating Mode:** JIRA-style execution with strict acceptance criteria, dependency tracking, and a mandatory bitácora log for every run/decision.

---

## 0) Guiding Principles (Non-Negotiables)

### P0. One method, one story, one implication
- The Nature manuscript contains:
  - One method definition set (D, ΔD, nulls, z, effect sizes).
  - One primary killer result.
  - One primary biological implication.

### P1. Theorem-first, application-second
- The compact representation theorem and exact reconstruction are positioned as the foundational contribution.
- Biological results (universality, essentiality, disease) are applications that validate relevance.

### P2. No internal inconsistency
- There must be zero contradictions across:
  - theorem ↔ statistics ↔ code outputs ↔ manuscript text ↔ figure captions ↔ supplementary.

### P3. Defend against predictable reviewer objections
- Must preempt:
  - curation/selection bias (curated Boolean models may be pre-simplified),
  - proxy-vs-exactness confusion (what is computed exactly vs approximated),
  - null model adequacy (degree-preserved, gate-permuted, ER),
  - reproducibility (deterministic runs, seeds, archived outputs),
  - “biological significance beyond p-values” (effect sizes, interpretation).

### P4. Bitácora discipline
- Every analysis run and decision is logged:
  - dataset version, code version, random seeds, run command, output checksums, and interpretation.

---

## 0B) Nature Credibility Gates (A/B/C) — Always-On Constraints

These are not “late-stage checks”. They are constraints that apply throughout execution and are explicitly referenced in every ticket.

### Gate A (Coherence + Exactness Boundary)
- Objective: eliminate internal inconsistency and make the “exact vs proxy” boundary unambiguous.
- Must be true at all times:
  - a single canonical definition set exists for D, ΔD, null models, z, and effect sizes
  - every reported number is traceable to a stored artifact
  - every approximation (e.g., compression proxy) is explicitly labeled and justified

### Gate B (Universality Survives Bias)
- Objective: the universality claim is robust to curation/selection bias and alternative cohorts.
- Must be true at all times:
  - the strongest curation-bias critique is stated explicitly (“steelman”)
  - at least one independent cohort/control is executed (not only promised)
  - sensitivity analyses exist and are reported without cherry-picking

### Gate C (Biological Punch Beyond p-values)
- Objective: show functional relevance and incremental value beyond trivial baselines.
- Must be true at all times:
  - external validation exists (DepMap at minimum, wet-lab if available)
  - ΔD is benchmarked against strong baselines and simple ML without leakage
  - the manuscript explains biological meaning in effect sizes and actionable predictions

### Stop-the-line triggers (apply to every ticket)
- Any contradiction between theorem ↔ stats ↔ code ↔ figures triggers immediate freeze until resolved (Gate A).
- Any universality claim without explicit bias-defense evidence triggers freeze (Gate B).
- Any biological claim without incremental value or external anchor triggers freeze (Gate C).

---

## 0C) Ticket Definition of Done (DoD) — Applies to Every Ticket

Every ticket must include the following before it can be considered complete:
- **Gate Alignment:** which of Gate A / Gate B / Gate C this ticket supports (explicitly stated).
- **Frozen Decisions:** any thresholds, inclusion rules, and sign conventions used must be written and versioned.
- **Artifact Traceability:** outputs and intermediate artifacts must be stored with provenance and checksums when applicable.
- **Negative Controls:** when the ticket produces a “positive” result, at least one negative control is executed or justified as infeasible.
- **Bitácora Entry:** run/decision logged with dataset versions, seeds, commands, and output checksums.

## 1) Success Definition (Nature Bar)

### S1. Minimum viable submission (desk-review survival)
- Coherent narrative, consistent definitions, and reproducible figures.
- N ≥ 200 networks analyzed with robust null comparisons.
- Clear effect sizes + uncertainty, not only p-values.
- One killer result framed as broad biological insight.

### S2. Nature acceptance bar (higher)
- Novel principle that generalists can understand:
  - “Evolution selects for algorithmic efficiency in GRNs” is made concrete and falsifiable.
- Universality defended against bias with at least one independent cohort or control.
- External validation (DepMap or wet-lab collaboration) strengthens biological credibility.

### S3. Killer results portfolio (A/B/C)
- A must be strong enough to stand alone (primary killer).
- B and C are executed in parallel; if strong, promoted to:
  - Extended Data (for Nature), or
  - Follow-up Nature-family papers.

---

## 2) Scope & Killer Results (A/B/C)

### KR-A (Primary, recommended): Essentiality from algorithmic contribution (ΔD)
- Claim: ΔD captures causal/algorithmic importance beyond graph centrality.
- Evidence: ROC/PR with bootstrapped CI, AUC comparisons, stratified analysis.

### KR-B (Parallel): Algorithmic corruption in disease (Cancer vs healthy)
- Claim: disease networks are measurably less algorithmically efficient (higher D / lower compressibility).
- Evidence: matched comparisons + clinical validation anchors (DepMap dependency, survival/annotation if available).

### KR-C (Parallel): Evolution vs human design
- Claim: human-designed synthetic circuits are less algorithmically efficient than evolved networks (matched controls).
- Evidence: carefully matched datasets (size, density, gate distribution) + effect sizes.

---

## 3) Roles (Operational)

### R1. Head Scientist (You)
- Final authority on scope, scientific claims, and decision gates.

### R2. Analysis Lead
- Owns execution of pipelines, statistics, figures, and reproducibility artifacts.

### R3. Methods/Theory Lead
- Owns theorem framing, exactness boundaries, and definition consistency contract.

### R4. Biology Liaison (Oxford lab collaboration)
- Owns experimental feasibility, wet-lab design, and validation pathway.

### R5. Release Manager
- Owns “submission readiness”: consistent manuscript, figures, and supplementary package.

---

## 4) Artifacts (What Must Exist)

### A. Definition Contract (single source of truth)
- One canonical definition set used everywhere:
  - D, ΔD, null models, z-score convention, effect sizes, fold-reduction definition, statistical tests.

### B. Reproducibility Packet
- Scripts that regenerate all figures from raw inputs.
- Archived outputs and run metadata with checksums.

### C. Bias Defense Packet
- Quantitative tests + controls addressing curation/selection bias.
- Independent cohort or control dataset supporting universality claim.

### D. Validation Packet
- DepMap integration results (minimum).
- Wet-lab plan (if collaboration becomes available).

---

## 5) Chronological JIRA Plan (Epics → Tickets)

### EPIC-LEV8-00: Program Governance & Freeze
**Objective:** prevent protocol drift; lock scope, definitions, and “one story”.

#### TSK-LEV8-00-001: Create Definition Contract v1
**Gate Alignment:** Gate A  
**Description:** Draft the canonical definitions block covering D, ΔD, nulls, z-score sign, effect sizes, and units.  
**Status:** DONE — Implemented as the frozen contract in `bitacora-lev8.md` (Entry LEV8-2026-03-17-004).  
**Acceptance Criteria:**
- One page max, referenced by all subsequent tickets.
- Includes “exact vs approximate” boundaries explicitly.
- Includes z-score sign convention and interpretation.

#### TSK-LEV8-00-002: Freeze Manuscript Scope (Nature core)
**Gate Alignment:** Gate A, Gate B, Gate C  
**Description:** Decide primary killer (A recommended) and what B/C become (Extended Data vs follow-ups).  
**Status:** DONE — A single “Core claim / evidence / implication” freeze statement is recorded below and must be treated as the scope contract for Level 8.  
**Acceptance Criteria:**
- One paragraph: “Core claim, core evidence, core implication.”
- Excludes all mention of “7 protocol levels” from planned Nature main text.

**Scope freeze statement (Nature core; authoritative)**
- **Core claim:** Evolved gene-regulatory networks exhibit measurable algorithmic efficiency: under a frozen encoding and null family, biological wiring diagrams are systematically more compressible than matched random controls, consistent with selection for mechanistic simplicity under constraints.
- **Core evidence:** A single, reproducible pipeline evaluates \(D\) and \(z\) for \(N\ge 200\) curated GRNs against three null families (ER, degree-preserved, gate-permuted) and reports effect sizes with uncertainty (fold-reduction with CI, Cohen’s \(d\), paired tests, robustness vs null ensemble size) under frozen sign conventions and thresholds.
- **Core implication:** Mechanistic information loss under in-silico knockouts (\(\Delta D\)) provides a principled causal importance score; the primary biological validation target is **KR-A (essentiality)** with leakage-safe benchmarking vs strong baselines and an external anchor (DepMap minimum). Disease corruption (KR-B) and evolution-vs-design (KR-C) are executed in parallel but are treated as Extended Data or follow-up results unless they independently clear Gate C.

#### TSK-LEV8-00-003: Bitácora Template for Runs
**Gate Alignment:** Gate A, Gate B, Gate C  
**Description:** Standardize run logging format (datasets, seeds, versions, outputs).  
**Status:** DONE — A structured execution log exists and is used in `bitacora-lev8.md` (multiple entries with commands, outputs, checksums).  
**Acceptance Criteria:**
- A repeatable checklist used for every computational run.

#### TSK-LEV8-00-004: Freeze quantitative pass thresholds for Gate A/B/C (mandatory)
**Gate Alignment:** Gate A, Gate B, Gate C  
**Description:** Define and freeze numeric thresholds used to decide “pass/fail” at each gate and to prevent subjective interpretation drift.  
**Status:** DONE — Frozen numeric thresholds are emitted as a single executable spec and summarized to `paper/figures/gate_thresholds_summary.csv`, with a manuscript-facing plot at `paper/figures/gate_thresholds_status.png` and execution provenance in `bitacora-lev8.md`.  
**Acceptance Criteria:**
- Gate A thresholds frozen:
  - sign conventions and units for D/ΔD/z fixed and referenced everywhere
  - reproducibility tolerance specified (what counts as “same result”)
- Gate B thresholds frozen:
  - minimum independent cohort/control requirement (what counts as “independent”)
  - minimum sensitivity analyses set (which perturbations must be reported)
- Gate C thresholds frozen:
  - minimum incremental value requirement (ΔD vs baselines) and how it is measured
  - minimum external validation requirement (DepMap endpoints + negative controls)

**Dependencies:** none.

---

### EPIC-LEV8-01: Definition Unification (Theorem ↔ Stats ↔ Code)
**Objective:** eliminate internal contradictions that would trigger desk rejection.

#### TSK-LEV8-01-001: Map Theory Objects → Computed Quantities
**Gate Alignment:** Gate A  
**Description:** Produce a mapping table: theorem objects → what is computed in code → units → limitations.  
**Status:** PARTIAL — A canonical mapping table is now stored in `bioProcessLev8.tex` (objects → computed quantities → units → artifacts), but multiple D proxies remain in use across code paths (gzip bytes vs D(v2) bits) and the mapping still needs to be propagated into the Nature manuscript Methods text.  
**Acceptance Criteria:**
- Table includes D and ΔD, and explicitly states what is exact and what is a proxy.
- The mapping is reflected in Methods language.

#### TSK-LEV8-01-002: Resolve ΔD Directionality & Classifier Direction
**Gate Alignment:** Gate A, Gate C  
**Description:** Choose the sign convention and ensure ROC/PR uses it consistently.  
**Status:** PARTIAL — ΔD direction is now unified across the GRN corpus, essentiality pipeline, and DepMap validation as ΔD(v)=D(G\setminus v)−D(G), but it is not yet fully unified across manuscript-facing Methods/Results artifacts and ROC scoring direction is not locked across all evaluation scripts.  
**Acceptance Criteria:**
- ΔD definition is identical in Methods, Results, and figure captions.
- ROC scoring direction is consistent with the biological interpretation.
- Dataset columns match the definition (no implicit negations).

#### TSK-LEV8-01-003: Standardize z-score Convention Across Artifacts
**Gate Alignment:** Gate A, Gate B  
**Description:** Ensure all reported z-scores follow the same sign convention.  
**Status:** DONE — Z sign/meaning unified across LaTeX artifacts and verified by exact recomputation from stored null summary stats (logged in `bitacora-lev8.md`, Entry LEV8-2026-03-21-001).  
**Acceptance Criteria:**
- Summary JSON, plots, and manuscript text all agree on sign and meaning.
- Recomputations from stored null distributions reproduce the same z.

**Dependencies:** EPIC-LEV8-00 complete.

---

### EPIC-LEV8-02: Results Consolidation (Protocol 8 Phase 1)
**Objective:** re-derive all figures/results with rigorous uncertainty and reproducibility.

#### TSK-LEV8-02-001: Null Model Meta-analysis (All networks)
**Gate Alignment:** Gate A, Gate B  
**Description:** Compute and report:
- fold-reduction (D_random / D_bio) with 95% CI,
- effect sizes (Cohen’s d),
- paired tests,
- robustness vs null ensemble size.  
**Status:** PARTIAL — Null statistics exist (`results/bio/null_stats.json`, `null_summary.json`), but the manuscript-facing Figure 1 suite and robustness/CI requirements are not yet implemented as specified (3-panel ER/deg/gate + robustness panel/Extended Data).  
**Acceptance Criteria:**
- Final “Figure 1” has 3 panels: ER, degree-preserved, gate-permuted.
- Report mean fold reduction + CI, and a clear interpretation.
- Includes a robustness panel or Extended Data plot.
- Uses the frozen pass thresholds from TSK-LEV8-00-004.

#### TSK-LEV8-02-002: Essentiality (KR-A) Full Reanalysis
**Gate Alignment:** Gate C  
**Description:** Compute ROC and PR curves for ΔD vs degree vs betweenness and combined model; quantify uncertainty.  
**Status:** PARTIAL — An extended essentiality analysis script and outputs exist, but the required stratified analyses and manuscript-grade protocol lock are not complete.  
**Acceptance Criteria:**
- AUC with bootstrap 95% CI for each predictor.
- Proper statistical comparison of AUCs (predefined test).
- Stratified analysis:
  - by organism group,
  - by network size bins,
  - by source dataset (GINsim/BioModels/PyBoolNet).

#### TSK-LEV8-02-002B: Benchmark against strong non-CausalBool baselines (mandatory)
**Gate Alignment:** Gate C  
**Description:** Compare ΔD against modern baseline predictors and simple ML models, with strict evaluation design.  
**Status:** NOT STARTED — No locked comparison against external predictors (e.g., LOEUF/pLI, expression, copy number) with leakage-safe evaluation is present as a stored artifact.  
**Baselines (minimum):**
- graph baselines: degree, betweenness (already), plus closeness/eigenvector if stable
- curated constraint: LOEUF / pLI (gnomAD) where applicable
- expression-based: mean expression in relevant tissues/cell lines (when available)
**Models (minimum):**
- logistic regression using standardized features
- one non-linear model as a sanity check (e.g., tree-based), only if it can be evaluated reproducibly without leakage  
**Acceptance Criteria:**
- Evaluation protocol predeclared:
  - train/test split strategy (or nested cross-validation) that prevents leakage across networks/species
  - calibration check (reliability curve / Brier score)
- Report:
  - ROC + PR with 95% CI
  - ablation: ΔD alone vs ΔD + baselines vs baselines alone
- Result interpretation:
  - explicit statement of what ΔD adds beyond standard predictors (incremental value, not only absolute AUC)
- Uses the frozen pass thresholds from TSK-LEV8-00-004 (incremental value requirement).

#### TSK-LEV8-02-003: Reproducibility Stress Tests
**Gate Alignment:** Gate A  
**Description:** Evaluate stability under:
- seeds,
- null swaps,
- null sample count,
- ordering assumptions (if any).  
**Status:** NOT STARTED — No predeclared stress-test grid with tolerance thresholds is stored.  
**Acceptance Criteria:**
- Δ in effect sizes and AUC is within predefined tolerance thresholds.
- Failures trigger a defined mitigation path (increase null ensemble or adjust method).

**Dependencies:** EPIC-LEV8-01 complete.

---

### EPIC-LEV8-03: Universality Defense & Curation/Selection Bias (Mandatory)
**Objective:** preempt the strongest predictable objection: curated Boolean models are pre-simplified.

#### TSK-LEV8-03-001: Formalize the Bias Objection (Steelman)
**Gate Alignment:** Gate B  
**Description:** Write the strongest possible reviewer critique about curation bias and define the counter-tests.  
**Status:** NOT STARTED — No dedicated steelman objection artifact and counter-test plan is stored.  
**Acceptance Criteria:**
- Bias critique is explicitly stated.
- Each critique has at least one quantitative counter-test.

#### TSK-LEV8-03-002: Independent Cohort Acquisition (Cell Collective)
**Gate Alignment:** Gate B  
**Description:** Acquire and standardize an additional cohort from Cell Collective (or equivalent) to test persistence of the effect.  
**Status:** NOT STARTED — No independent cohort acquisition/conversion pipeline is present.  
**Acceptance Criteria:**
- Clear inclusion criteria and conversion steps.
- Show effect direction persists with comparable magnitude (with uncertainty).
- If conversion quality varies, include a pre-registered filtering rule and sensitivity analysis.
- Uses the frozen pass thresholds from TSK-LEV8-00-004 (independence + sensitivity requirements).

#### TSK-LEV8-03-003: Human-designed vs Evolved (KR-C, minimal viable)
**Gate Alignment:** Gate B  
**Description:** Compile a matched set of synthetic circuits and compare D distributions.  
**Status:** NOT STARTED — No synthetic-circuit cohort and matching protocol is stored as an executable pipeline + results.  
**Acceptance Criteria:**
- Matching protocol documented (size, edge density, gate distribution).
- Effect size + CI reported.
- If sample is small: positioned as pilot/Extended Data, not core claim.

**Dependencies:** EPIC-LEV8-01 complete; EPIC-LEV8-02 recommended but not strictly required to start acquisition.

---

### EPIC-LEV8-04: External Validation (DepMap + Collaboration)
**Objective:** add biological credibility beyond internal metrics.

#### TSK-LEV8-04-001: DepMap Data Acquisition & Provenance
**Gate Alignment:** Gate C  
**Description:** Download and version DepMap datasets required for validation and cancer anchoring.  
**Status:** PARTIAL — DepMap-facing analysis outputs exist, but raw DepMap 24Q4 artifacts + immutable manifests/checksums are not present in-repo at the expected `data/depmap/...` locations; the currently referenced `data/cancer/depmap_crispr.csv` is a small synthetic/proxy table, not the 24Q4 raw release.  
**Datasets (minimum):**
- CRISPR gene effect matrix (Chronos; gene-by-cell-line)
- Cell line metadata (lineage/subtype, tissue, disease)
- Gene identifiers reference (HGNC symbol mapping and aliases)
**Datasets (recommended, for confounds and stronger biology):**
- Expression (RNA-seq) for the same cell lines
- Copy number / ploidy proxies (to control known biases)
**Provenance requirements (mandatory):**
- Store raw files immutable (no in-place edits)
- Create a dataset manifest with:
  - public release name/date
  - original filenames
  - checksums
  - download source URL
  - minimal schema notes (key columns)
**Acceptance Criteria:**
- All datasets have immutable version IDs.
- Mapping from DepMap gene identifiers ↔ network gene symbols is documented.

#### TSK-LEV8-04-002: DepMap Validation for KR-A
**Gate Alignment:** Gate C  
**Description:** Test whether ΔD-ranked genes are enriched for high dependency in relevant cell lines.  
**Status:** PARTIAL — DepMap validation plots/results exist (e.g., `results/cancer*` and `paper/figures/figure3_depmap_validation_24Q4.png`), but cannot be treated as “external validation” until rerun against the actual DepMap release under the provenance requirements of TSK-LEV8-04-001 and with the specified baselines/controls.  
**Acceptance Criteria:**
- Primary endpoint pre-specified (rank correlation or enrichment statistic).
- Permutation baseline included.
- Confound controls included at minimum (degree, expression if available).

#### TSK-LEV8-04-002B: DepMap comparison with standard dependency predictors (mandatory)
**Gate Alignment:** Gate C  
**Description:** Establish whether ΔD adds signal beyond common predictors in DepMap-scale data.  
**Status:** NOT STARTED — No locked regression/ranking comparison against standard predictors with negative controls is stored as a manuscript-grade artifact.  
**Comparison set (minimum):**
- ΔD (your predictor)
- network baselines (degree, betweenness)
- expression (CCLE RNA-seq) and copy number (when available)
- gene constraint (LOEUF/pLI) where appropriate
**Acceptance Criteria:**
- A predeclared regression or ranking model comparing predictors side-by-side (no p-hacking).
- Report incremental contribution:
  - partial correlation / incremental AUC/PR gain
  - permutation-based significance for the incremental term
- Negative controls included:
  - permuted ΔD across genes (break mapping) should destroy signal
  - lineage-mismatched cell lines should weaken signal (if biology is specific)
- Uses the frozen pass thresholds from TSK-LEV8-00-004 (external validation + incremental value requirement).

#### TSK-LEV8-04-003: Cancer “Algorithmic Corruption” Pilot (KR-B)
**Gate Alignment:** Gate C  
**Description:** Minimum viable cancer vs healthy analysis with matched networks.  
**Status:** PARTIAL — Cancer corruption analysis code and outputs exist (e.g., `src/analysis/Cancer_Corruption.py`, multiple `results/cancer*` outputs, and plots under `paper/figures/`), but the plan’s dataset acquisition/provenance requirements (paired TCGA/CCLE route) are not yet satisfied in-repo.  
**Acceptance Criteria:**
- Matched comparison protocol (gene set control or explicit mapping).
- ACI (or equivalent) defined consistently with D conventions.
- At least one external anchor (DepMap dependency stratification or known oncogene enrichment).

#### TSK-LEV8-04-004: Wet-lab Collaboration Readiness Pack
**Gate Alignment:** Gate C  
**Description:** Prepare a collaborator-facing packet with 5–10 testable predictions and experimental plan.  
**Status:** NOT STARTED — No collaborator-facing prediction pack exists as a stored artifact.  
**Acceptance Criteria:**
- Clear experimental design, controls, and success criteria.
- Predefined decision rule for whether wet-lab results support the claim.

**Dependencies:** EPIC-LEV8-00 and EPIC-LEV8-01 complete. EPIC-LEV8-02 strengthens selection of which genes/cases to validate.

---

### EPIC-LEV8-04B: Cancer Dataset Acquisition (TCGA/CCLE) and Network Construction (KR-B scale-up)
**Objective:** turn KR-B into a dataset-driven, massively tested validation that reads as biomedical rather than purely theoretical.

#### TSK-LEV8-04B-001: Choose the KR-B data route (declare one primary)
**Gate Alignment:** Gate B, Gate C  
**Description:** Select the primary strategy for cancer/healthy network pairs.
- Route 1 (fast, curation-heavy): literature-curated cancer/healthy logical models.
- Route 2 (slower, scale-heavy): infer networks from TCGA (tumor + matched normal) and validate with CCLE/DepMap.  
**Status:** PARTIAL — Implementations exist that can run either synthetic/literature-style cohorts or paired TCGA-style inputs (via environment variables), but no single declared primary route + written failure modes/mitigations is frozen as an artifact.  
**Acceptance Criteria:**
- One route declared primary; the other becomes contingency.
- Expected failure modes written explicitly and paired to mitigation actions.
- “Success” defined quantitatively (effect size + uncertainty + anchor test).

#### TSK-LEV8-04B-002: Download TCGA tumor + normal expression (immutable provenance)
**Gate Alignment:** Gate B, Gate C  
**Description:** Acquire TCGA expression for selected cancer types with matched normal when available; freeze preprocessing.  
**Status:** NOT STARTED — No `data/cancer/tcga_paired/...` cohort with immutable manifests/checksums is present.  
**Acceptance Criteria:**
- Initial cancer-type set frozen (start with 3, expand to 10 after pass gate).
- For each cancer type:
  - tumor and normal sample counts logged
  - inclusion/exclusion rules frozen (missingness, QC)
  - versioned manifests and checksums stored

#### TSK-LEV8-04B-003: Download CCLE expression and align with DepMap cell lines
**Gate Alignment:** Gate B, Gate C  
**Description:** Acquire CCLE expression and harmonize to DepMap dependency matrices via a single canonical cell-line identifier.  
**Status:** NOT STARTED — No CCLE expression dataset and alignment report is stored.  
**Acceptance Criteria:**
- One canonical “cell_line_id” used across CCLE + DepMap + metadata.
- Alignment report produced (coverage, drop reasons, ambiguous matches).

#### TSK-LEV8-04B-004: Build and freeze a regulatory prior (TF→target edges)
**Gate Alignment:** Gate B, Gate C  
**Description:** Assemble a transcriptional regulatory prior from curated sources and freeze a versioned edge list as an input artifact.  
**Status:** NOT STARTED — No frozen TF→target prior edge list artifact exists.  
**Acceptance Criteria:**
- Edge list columns frozen:
  - source TF symbol
  - target symbol
  - evidence score (or discrete confidence label)
  - source database label
- Filtering rule frozen (confidence threshold, organism constraints).

#### TSK-LEV8-04B-005: Infer tumor and normal networks per cancer type (massive scale)
**Gate Alignment:** Gate B, Gate C  
**Description:** Using expression + regulatory prior, infer cancer-specific and healthy-like networks; export them to the same JSON schema as existing networks.  
**Status:** NOT STARTED — No TCGA/CCLE inferred tumor/normal networks exist as JSON artifacts with frozen inference protocol.  
**Acceptance Criteria:**
- Each inferred network includes provenance fields:
  - cancer type, cohort (tumor/normal), inference method, thresholds
- Network size controlled with a frozen rule (e.g., top-K regulators/targets, 50–150 nodes).
- Logic/gate assignment policy documented (even if initially simplified).

#### TSK-LEV8-04B-006: Compute ACI and validate with external anchors
**Gate Alignment:** Gate B, Gate C  
**Description:** Compute algorithmic corruption metrics and validate directionality with anchors.  
**Status:** PARTIAL — Corruption metrics exist in `results/cancer*`, but the “external anchors” requirement is not met under real DepMap/TCGA provenance (pending TSK-LEV8-04-001 and TSK-LEV8-04B-002).  
**Acceptance Criteria:**
- ACI (or equivalent) computed for each tumor/normal pair with uncertainty.
- At least one anchor shows expected enrichment/direction:
  - DepMap dependency enrichment for high-ΔD or high-ACI genes in matched lineages
  - known oncogene/tumor suppressor enrichment among algorithmic “drivers”
- Uses the frozen pass thresholds from TSK-LEV8-00-004 (anchor requirement + sensitivity reporting).

#### TSK-LEV8-04B-007: Commit one KR-B or KR-C output as Extended Data-grade pillar
**Gate Alignment:** Gate B, Gate C  
**Description:** Prevent “optional extras” from remaining vague by forcing one non-KR-A track into a concrete, reviewable, Extended Data-quality result.  
**Status:** NOT STARTED — No explicit selection and “Extended Data-grade” locked pillar is frozen as an artifact.  
**Acceptance Criteria:**
- Exactly one of the following is selected as the Extended Data pillar (the other remains a follow-up track):
  - KR-B (cancer algorithmic corruption) with TCGA/CCLE/DepMap anchors
  - KR-C (evolution vs human design) with matched controls
- The selected pillar has:
  - dataset manifest + inclusion criteria
  - a primary effect size with 95% CI
  - at least one negative control and one sensitivity analysis
- The result is ready to be inserted into Extended Data without further methodological invention.

---

### EPIC-LEV8-04C: Massive Stress Testing of Current Implementation (Scale, Runtime, Robustness)
**Objective:** demonstrate instrument stability under a predeclared grid of conditions and new datasets.

#### TSK-LEV8-04C-001: Freeze the “massive test matrix”
**Gate Alignment:** Gate A  
**Description:** Define a full grid of runs across datasets and null models; predeclare stability tolerances.  
**Status:** NOT STARTED — No frozen condition matrix with pass/fail tolerances is stored.  
**Acceptance Criteria:**
- A fixed condition matrix:
  - null model type × n_null × n_swaps × seed set × ordering policy
  - cohort (existing 230 / Cell Collective / TCGA-inferred / synthetic circuits)
- Each cell has pass/fail stability thresholds (effect size drift, AUC drift, z drift).

#### TSK-LEV8-04C-002: Runtime/memory scaling characterization
**Gate Alignment:** Gate A  
**Description:** Measure runtime scaling vs n_nodes, n_edges, and null counts; define acceptable compute budgets and when HPC is required.  
**Status:** NOT STARTED — No scaling characterization report exists as a stored artifact.  
**Acceptance Criteria:**
- A scaling report exists (tables/plots) suitable for Supplementary Methods.
- A rule exists for selecting n_null and n_swaps as a function of network size.

#### TSK-LEV8-04C-003: Reproducibility lock (frozen outputs)
**Gate Alignment:** Gate A  
**Description:** Demonstrate that a clean checkout reproduces the same figures and summary numbers within tolerance.  
**Status:** PARTIAL — Some figures exist under `paper/figures/`, but a complete “clean checkout” reproduction workflow with deterministic checksums for all target outputs is not locked.  
**Acceptance Criteria:**
- Deterministic checksums for all frozen figures.
- Any remaining nondeterminism is bounded and explained.

### EPIC-LEV8-05: Manuscript Refactor (Protocol 8 Phase 2)
**Objective:** create a Nature-shaped manuscript (clean narrative, minimal clutter).

#### TSK-LEV8-05-001: Abstract Rewrite (≤150 words)
**Gate Alignment:** Gate A, Gate B, Gate C  
**Status:** NOT STARTED — No Nature-shaped abstract rewrite is frozen as an artifact.  
**Acceptance Criteria:**
- One claim, one main statistic, one implication.
- No mention of protocol history.

#### TSK-LEV8-05-002: Introduction Rewrite (Generalist-readable)
**Gate Alignment:** Gate A, Gate C  
**Status:** NOT STARTED — No locked generalist-readable introduction rewrite is frozen as an artifact.  
**Acceptance Criteria:**
- States the problem (compactness paradox) and why algorithmic complexity is the right lens.
- Theorem framing is precise and bounded.

#### TSK-LEV8-05-003: Results Rewrite (One primary killer)
**Gate Alignment:** Gate B, Gate C  
**Status:** NOT STARTED — No manuscript Results section is locked to a single primary killer with supporting Extended Data.  
**Acceptance Criteria:**
- Result 1: universality across 230 networks (with bias defense pointer).
- Result 2: KR-A essentiality as primary killer (with uncertainty).
- Optional: KR-B or KR-C in Extended Data or limited Results paragraph depending on strength.

#### TSK-LEV8-05-004: Methods Rewrite (Replicable)
**Gate Alignment:** Gate A, Gate B, Gate C  
**Status:** NOT STARTED — No consolidated replicable Methods rewrite is frozen as an artifact.  
**Acceptance Criteria:**
- Every dataset source and filtering rule is explicit.
- Null model procedures are fully specified.
- Statistical tests and multiple comparisons handling are explicit.

**Dependencies:** EPIC-LEV8-01 and EPIC-LEV8-02 complete; EPIC-LEV8-03/04 provide Extended Data content.

---

### EPIC-LEV8-06: Figures, Supplementary, and Repro Pack (Protocol 8 Phase 3–4)
**Objective:** reviewer-proof packaging.

#### TSK-LEV8-06-001: Final Figure Suite
**Gate Alignment:** Gate A, Gate B, Gate C  
**Status:** PARTIAL — Multiple draft figures exist, but the final publication-formatted suite and complete contract compliance across all panels is not locked.  
**Acceptance Criteria:**
- All figures consistent with Definition Contract.
- Publication formatting: consistent fonts, sizes, and panels.

#### TSK-LEV8-06-002: Extended Data Suite for Bias + Validation
**Gate Alignment:** Gate B, Gate C  
**Status:** NOT STARTED — No bias-defense cohort replication figures and real DepMap validation figures are locked as Extended Data artifacts.  
**Acceptance Criteria:**
- Bias defense figures (cohort replication, sensitivity).
- DepMap validation figures.

#### TSK-LEV8-06-003: Reproduction Workflow + Frozen Outputs
**Gate Alignment:** Gate A  
**Status:** NOT STARTED — No one-command (or documented two-step) reproduction workflow is locked for all target artifacts.  
**Acceptance Criteria:**
- One-command or documented two-step reproduction.
- All outputs checksummed and logged in bitácora.

#### TSK-LEV8-06-004: Submission Pack
**Gate Alignment:** Gate A, Gate B, Gate C  
**Status:** NOT STARTED — No submission pack (cover letter + reviewer suggestions) exists as a stored artifact.  
**Acceptance Criteria:**
- Cover letter hooks novelty and broad impact.
- Suggested reviewers list aligns with complexity biology and systems biology.

**Dependencies:** EPIC-LEV8-05 complete.

---

## 6) Decision Gates (Go/No-Go)

These gates are the operational checkpoint form of Gate A/B/C. Quantitative thresholds are defined and frozen in TSK-LEV8-00-004 and must be referenced at each gate review.

### GATE-A (maps to former GATE-1): Coherence + Exactness Boundary
**Pass condition:**
- Definition Contract exists and is used verbatim in manuscript, figures, and code outputs.
- Theory-to-computation mapping table exists (exact vs proxy boundary is explicit).
- Recomputations from stored artifacts reproduce reported statistics within the frozen tolerance.
- No unresolved contradictions remain across theorem ↔ stats ↔ code ↔ figures.

### GATE-B (maps to former GATE-2): Universality Defense Survives Bias
**Pass condition:**
- Steelman curation/selection-bias critique is explicitly written and addressed with data.
- At least one independent cohort/control is executed and reported with uncertainty.
- Sensitivity analyses required by the frozen threshold spec are completed and reported.
- Effect direction is stable (no selective reporting of subcohorts).

### GATE-C (maps to former GATE-3 and GATE-4): Biological Punch Beyond p-values
**Pass condition:**
- KR-A meets robustness requirements and is benchmarked against strong baselines without leakage.
- DepMap validation is completed and shows incremental value beyond standard predictors, with negative controls.
- One of KR-B or KR-C has been promoted into an Extended Data-grade pillar or is explicitly removed from the Nature package.
- Biological meaning is expressed as interpretable effect sizes and actionable predictions, not only p-values.

### GATE-R (maps to former GATE-5): Submission Readiness
**Pass condition:**
- Gate A, Gate B, and Gate C are all passed.
- All main figures and Extended Data figures are frozen with checksums and reproducible within tolerance.
- Methods are sufficient for reviewer replication without private knowledge.

---

## 7) Risk Register (with Mitigations)

### Risk R-01: Metric ambiguity (proxy vs exact)
- **Mitigation:** Definition Contract + mapping table + explicit Methods language.

### Risk R-02: Curation bias invalidates universality
- **Mitigation:** independent cohort + human-designed controls + sensitivity analyses.

### Risk R-03: KR-A AUC seen as “not competitive with ML”
- **Mitigation:** frame as theory-driven, show orthogonality to centrality, and add external validation (DepMap).

### Risk R-04: Reproducibility gaps (seed sensitivity)
- **Mitigation:** stress tests + frozen outputs + bitácora logging.

### Risk R-05: No wet-lab validation
- **Mitigation:** DepMap as external anchor; prepare collaboration-ready packet immediately.

---

## 8) Bitácora (Execution Log Specification)

### Required fields for every run
- Run ID
- Date/time
- Operator
- Dataset IDs and versions
- Code version identifier
- Random seeds (all)
- Command executed
- Outputs produced (paths)
- Output checksums
- Summary interpretation
- Next action triggered

### Run taxonomy
- CONSOLIDATION (null stats, essentiality)
- BIAS-DEFENSE (cohort replication, synthetic vs evolved)
- VALIDATION (DepMap, disease pilots)
- FIGURE-LOCK (final figure export and checksum freeze)

---

## 9) Minimal Dataset Acquisition Checklist (DepMap + Cohorts)

### DepMap (KR-A validation, KR-B anchor)
- Acquire:
  - CRISPR gene effect (Chronos)
  - Cell line metadata
  - Optional confounds: expression, copy number
- Requirements:
  - Version IDs recorded
  - Stable gene identifier mapping rule
  - Predefined matching from networks/tissues to cell line subsets

### TCGA / CCLE (KR-B scale-up)
- Acquire:
  - TCGA tumor + matched normal expression for selected cancer types
  - CCLE expression for cell lines
  - A regulatory prior edge list (TF→target) from curated sources
- Requirements:
  - Immutable manifests and checksums per source
  - Harmonized identifiers:
    - TCGA sample IDs
    - CCLE/DepMap cell line IDs
    - gene symbol ↔ Ensembl mapping policy
  - Frozen network inference protocol and thresholds
  - Exported networks conform to the same JSON schema as the existing 230 networks

### Cell Collective (bias defense)
- Acquire:
  - model list + metadata
  - model formats and conversion plan
- Requirements:
  - Inclusion criteria and conversion failures logged
  - Sensitivity analysis for conversion ambiguity

### Synthetic circuits (KR-C)
- Acquire:
  - curated synthetic circuit models from literature
  - conversion protocol to comparable Boolean/logical representation
- Requirements:
  - matching criteria to evolved networks documented
  - small-N treated as pilot unless sufficiently scaled

---

## 10) Final Output Targets (What “Done” Looks Like)

### Nature Submission Package
- Manuscript (clean narrative, consistent definitions)
- 4 main figures + Extended Data figures
- Reproducibility packet (scripts + frozen outputs + checksums)
- Bias defense packet (quantitative)
- DepMap validation results (minimum)
- Wet-lab readiness packet (prepared regardless of collaborator response timing)

---

**End of BIOPLAN-LEV8**

UPDATED STATUS:

Updated the plan file itself with explicit per-ticket status lines: bioPlanLev-8.md .

What’s Actually DONE (per repo artifacts)

- TSK-LEV8-00-001 (Definition Contract v1): DONE (frozen in bitacora-lev8.md )
- TSK-LEV8-00-003 (Bitácora template/discipline): DONE (bitácora exists and is used)
- TSK-LEV8-01-003 (z-score convention): DONE (standardized + recomputation verified; logged in bitácora)
PARTIAL (work exists, but does not meet plan acceptance criteria)

- TSK-LEV8-01-001: PARTIAL (no explicit theory→computed mapping table; multiple D proxies still exist across codepaths)
- TSK-LEV8-01-002: PARTIAL (ΔD convention exists in code/contract, not fully unified into manuscript artifacts)
- TSK-LEV8-02-001: PARTIAL (null stats exist, but not the specified Figure 1 suite + CI/robustness deliverables)
- TSK-LEV8-02-002: PARTIAL (extended essentiality analysis exists, stratified analyses not completed)
- TSK-LEV8-04-001 / 04-002 / 04-003 / 04B-001 / 04B-006 / 04C-003 / 06-001: PARTIAL (results/scripts exist, but provenance + “Nature-grade lock” requirements are not satisfied; notably DepMap raw 24Q4 data is not present in data/depmap/... and TCGA paired acquisition route is not present as specified)
NOT STARTED (no repo artifact satisfying the ticket)

- TSK-LEV8-00-002, 00-004
- TSK-LEV8-02-002B, 02-003
- All of EPIC-LEV8-03
- TSK-LEV8-04-002B, 04-004
- TSK-LEV8-04B-002..005, 04B-007
- TSK-LEV8-04C-001..002
- TSK-LEV8-05-001..004
- TSK-LEV8-06-002..004
