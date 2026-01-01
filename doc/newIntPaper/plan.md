# Programme Plan: Causal Boolean Integration (JIRA‑style)

## Refactor Note
This plan is refactored to address ordering invariance, canonical representation proofs, closure/compositionality of index‑set algebra, and to re‑open the ANALYSIS series with uniform documentation and validation. Some previously completed tickets are re‑opened to ensure ordering policy consistency, network‑aware index‑set equality, and manuscript updates.

## Epics and Phases
- Phase 0 — Architecture & Repository Restructure (EPIC‑ARCH)
- Phase 1 — Gate Set Expansion & Dispatch (EPIC‑GATES)
- Phase 2 — Foundations: Ordering, Canonical Representation, Closure/Compositionality (EPIC‑FOUNDATIONS)
- Phase 3 — Behavioural Compression Formalisation (EPIC‑THEORY)
- Phase 4 — Algorithms & Subsystem Search (EPIC‑ALGO)
- Phase 5 — Stochastic Variants & Noise (EPIC‑STOCH)
- Phase 6A — Pattern Formulae for Ordered Repertoires (EPIC‑PATTERN)
- Phase 6B — Per‑Gate Pattern Analysis and Documentation (EPIC‑ANALYSIS)
- Phase 7 — Mixed Dynamics Composition and Validation (EPIC‑MIXED)
- Phase 8 — Testing & Validation (EPIC‑TEST)
- Phase 9 — Experimental Programme (EPIC‑EXPER)
- Phase 10 — Comparators & Baselines (EPIC‑COMPARE)
- Phase 11 — Paper Writing & Artefacts (EPIC‑PAPER)
- Phase 12 — Reproducibility & Release (EPIC‑RELEASE)

## Ticket Format
- Ticket ID
- Phase / Epic
- Title
- Status
- File IDs (primary files impacted)
- Dependencies
- Acceptance Criteria
- Deliverables
 - Unit Test ID(s)
 - Test Location
 - Test Acceptance

## Execution Sequence (Refactored)
 - [x] TSK-ARCH-001 — Define professional folder structure
 - [x] TSK-ARCH-002 — Create experiment/data/results/figures/tests directories
 - [x] TSK-ARCH-003 — Establish Mathematica package structure and usage
 - [x] TSK-ARCH-004 — Toolchain configuration and deterministic kernel test
 - [x] TSK-GATES-001 — Catalogue gate families and semantics
 - [x] TSK-GATES-002 — Abstract gate dispatch in update routines
 - [x] TSK-GATES-003 — Stochastic gate noise toggles
 - [x] TSK-THEORY-005 — Ordering transform invariance for index‑set algebra (foundation)
 - [x] TSK-THEORY-004 — Canonical index‑set representation and minimality (foundation)
 - [x] TSK-THEORY-006 — Closure and compositionality of index‑set operations (foundation)
 - Sequence guard: Foundations proceed strictly in the order 005 → 004 → 006 before ANALYSIS tickets.
 - After completing 005, immediately execute 004 (canonical) and then 006 (closure/compositionality) prior to re‑opening ANALYSIS gate documents and tests.
- Refactor note: PATTERN series re-opened to align with ordering invariance (TSK‑THEORY‑005) and index‑algebra closure/compositionality (TSK‑THEORY‑006); tests now use dispatch and deterministic kernel runs.
- Sequence clarifier: PATTERN precedes ANALYSIS after Foundations. PATTERN provides repertoire-level taxonomy and summaries independent of per-gate derivations; ANALYSIS follows to derive exact, ordering-aware index formulae per gate and validate against dispatch repertoires.
- Analysis refactor note: XOR/XNOR/NAND/NOR tests migrated to dispatch and status logic fixed; IMPLIES, KOFN, CANALISING validated deterministically. Corresponding verification updates added to docProcess.
- Theory deepening note: Added formal theorem/lemma boxes and expanded discussions for THEORY‑001..006 in docProcess, reinforcing scientific rigor and manuscript readiness.
 - [x] TSK-PATTERN-001 — Generalise ordered repertoire pattern method beyond AND (re-opened)
 - [x] TSK-PATTERN-002 — Derive symbolic pattern formulae per gate family (re-opened)
 - [x] TSK-PATTERN-003 — Validate pattern formulae against generated repertoires (re-opened)
 - [x] TSK-PATTERN-004 — Integrate pattern formulae into manuscript (re-opened)
 - [x] TSK-ANALYSIS-AND — AND gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-OR — OR gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-XOR — XOR gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-NAND — NAND gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-NOR — NOR gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-XNOR — XNOR gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-NOT — NOT gate analysis and documentation (re‑opened)
 - [x] TSK-ANALYSIS-IMPLIES — IMPLIES/NIMPLIES analysis and documentation
 - [x] TSK-ANALYSIS-KOFN — k‑of‑n thresholds analysis and documentation
 - [x] TSK-ANALYSIS-CANALISING — Canalising/nested‑canalising analysis and documentation
 - [x] TSK-MIXED-001 — Define composition rules for mixed gate dynamics
 - [x] TSK-MIXED-002 — Validate mixed dynamics formulae against ensembles
 - [x] TSK-MIXED-003 — Integrate mixed dynamics results into manuscript
 - [x] TSK-THEORY-001 — Behavioural compression functional with axioms and bounds
 - [x] TSK-THEORY-002 — Sensitivity/influence relations and compression normalisation
 - [x] TSK-THEORY-003 — Decomposition across cut sets and canalisation compressibility effects
 - [x] TSK-ALGO-001 — Exact computation and caching for small n
 - [x] TSK-ALGO-002 — Monte Carlo/importance sampling approximations
 - [x] TSK-ALGO-003 — Subsystem search heuristics with branch‑and‑bound
 - [x] TSK-STOCH-001 — Asynchronous update regimes
 - [x] TSK-STOCH-002 — Noise robustness analyses
 - [x] TSK-TEST-001 — Unit tests for gate truth tables (expanded with ordering tests)
 - [x] TSK-TEST-002 — Property tests for axioms and invariances
 - [x] TSK-TEST-003 — Performance tests for repertoire generation
 - [x] TSK-TEST-004 — Acceptance tests to reproduce manuscript figures
 - [x] TSK-EXPER-001 — Ensemble generation for ER/scale‑free/small‑world graphs
 - [x] TSK-EXPER-002 — Gate mixture sweeps and bias control
 - [x] TSK-EXPER-003 — Update regime comparison (sync vs async)
 - [x] TSK-EXPER-004 — Subsystem search evaluation
 - [x] TSK-EXPER-005 — Noise robustness experiments
 - [x] TSK-COMPARE-002 — PID‑based synergy comparator
 - [x] TSK-COMPARE-003 — Transfer entropy and multi‑information comparators
 - [ ] TSK-PAPER-001 — Manuscript structure and figure list
 - [x] TSK-PAPER-002 — Methods section with algorithms and complexity
 - [x] TSK-PAPER-003 — Theory section with axioms and proofs
 - [x] TSK-PAPER-004 — Results section with validation and figures
 - [x] TSK-PAPER-005 — Discussion, limitations and future directions
 - [ ] TSK-RELEASE-001 — Replication package assembly
 - [ ] TSK-RELEASE-002 — Licensing, metadata and persistent identifiers
 - [ ] TSK-RELEASE-003 — Submission tailoring for target journals

## Tickets

### EPIC‑ARCH (Phase 0)

- Ticket ID: TSK‑ARCH‑001
  - Phase/Epic: Phase 0 / EPIC‑ARCH
  - Title: Define professional folder structure for Mathematica project
  - Status: pending
  - File IDs: `docs/architecture.md`, `src/integration/Alpha.m`, `src/integration/Alpha.nb`, `src/integration/newAlpha.nb`
  - Dependencies: —
  - Acceptance Criteria: Folder layout documented; aligns with Mathematica packages, MUnit tests, experiments, data, results and figures; naming conventions defined.
  - Acceptance Checklist:
    - [ ] Folder layout documented
    - [ ] Aligns with packages, MUnit tests, experiments, data, results, figures
    - [ ] Naming conventions defined
  - Deliverables: Documented structure; path conventions; module boundaries.
  - Unit Test ID(s): `tests/MUnit/Arch/TSK-ARCH-001-Tests.nb`
  - Test Location: `tests/MUnit/Arch`
  - Test Acceptance: Verifies directory existence, write permissions, and discovery of tests.

- Ticket ID: TSK‑ARCH‑002
  - Phase/Epic: Phase 0 / EPIC‑ARCH
  - Title: Create experiment, data, results, figures, tests directories
  - Status: pending
  - File IDs: `experiments/`, `data/`, `results/`, `figures/`, `tests/`
  - Dependencies: TSK‑ARCH‑001
  - Acceptance Criteria: Directories exist; README stubs; write permissions verified; CSV export points to `results/`.
  - Acceptance Checklist:
    - [ ] Directories exist
    - [ ] README stubs present
    - [ ] Write permissions verified
    - [ ] CSV exports point to `results/`
  - Deliverables: Directory tree with short descriptions.
  - Unit Test ID(s): `tests/MUnit/Arch/TSK-ARCH-002-Tests.nb`
  - Test Location: `tests/MUnit/Arch`
  - Test Acceptance: Confirms creation and accessibility of `experiments/`, `data/`, `results/`, `figures/`, `tests/`.

- Ticket ID: TSK‑ARCH‑003
  - Phase/Epic: Phase 0 / EPIC‑ARCH
  - Title: Establish Mathematica package structure and usage patterns
  - Status: pending
  - File IDs: `src/Packages/Integration/Alpha.m`, `src/Packages/Integration/Gates.m`, `src/Packages/Integration/Experiments.m`
  - Dependencies: TSK‑ARCH‑001
  - Acceptance Criteria: Packages load via `Needs[]`; public symbols documented; tests discoverable by MUnit.
  - Acceptance Checklist:
    - [ ] Packages load via `Needs[]`
    - [ ] Public symbols documented
    - [ ] Tests discoverable by MUnit
  - Deliverables: Package skeletons and loading notes.
  - Unit Test ID(s): `tests/MUnit/Arch/TSK-ARCH-003-Tests.nb`
  - Test Location: `tests/MUnit/Arch`
  - Test Acceptance: Loads packages and asserts presence of public symbols.

- Ticket ID: TSK‑ARCH‑004
  - Phase/Epic: Phase 0 / EPIC‑ARCH
  - Title: Toolchain configuration and kernel path verification
  - Status: pending
  - File IDs: `docs/tooling.md`
  - Dependencies: TSK‑ARCH‑001
  - Acceptance Criteria: Instructions for Wolfram Framework/Workbench; PATH/KERNEL resolution documented; deterministic notebook settings.
  - Acceptance Checklist:
    - [ ] Framework/Workbench instructions documented
    - [ ] PATH/KERNEL resolution documented
    - [ ] Deterministic notebook settings configured
  - Deliverables: Tooling checklist and troubleshooting guide.
  - Unit Test ID(s): `tests/MUnit/Arch/TSK-ARCH-004-Tests.nb`
  - Test Location: `tests/MUnit/Arch`
  - Test Acceptance: Executes a minimal kernel run; asserts deterministic seed behaviour.

### EPIC‑GATES (Phase 1)

- Ticket ID: TSK‑GATES‑001
  - Phase/Epic: Phase 1 / EPIC‑GATES
  - Title: Catalogue gate families and semantics
  - Status: pending
  - File IDs: `src/Packages/Integration/Gates.m`, `docs/architecture.md`
  - Dependencies: TSK‑ARCH‑003
  - Acceptance Criteria: Definitions for AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES, k‑of‑n thresholds, canalising/nested‑canalising; truth tables specified.
  - Acceptance Checklist:
    - [ ] Gate definitions (AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES)
    - [ ] k‑of‑n thresholds and canalising/nested‑canalising specified
    - [ ] Truth tables specified
  - Deliverables: Gate API specification.
  - Unit Test ID(s): `tests/MUnit/Gates/TSK-GATES-001-Tests.nb`
  - Test Location: `tests/MUnit/Gates`
  - Test Acceptance: Truth-table verification across all gates.

- Ticket ID: TSK‑GATES‑002
  - Phase/Epic: Phase 1 / EPIC‑GATES
  - Title: Abstract gate dispatch in network update routines
  - Status: pending
  - File IDs: `src/integration/Alpha.m`, `src/Packages/Integration/Gates.m`
  - Dependencies: TSK‑GATES‑001
  - Acceptance Criteria: `dynamic` labels mapped via dispatch table; supports unary/multi‑input; parameterised thresholds.
  - Acceptance Checklist:
    - [ ] `dynamic` labels mapped via dispatch table
    - [ ] Supports unary and multi‑input gates
    - [ ] Parameterised thresholds supported
  - Deliverables: Updated routines with gate abstraction.
  - Unit Test ID(s): `tests/MUnit/Gates/TSK-GATES-002-Tests.nb`
  - Test Location: `tests/MUnit/Gates`
  - Test Acceptance: Dispatch correctness and parameter handling.

- Ticket ID: TSK‑GATES‑003
  - Phase/Epic: Phase 1 / EPIC‑GATES
  - Title: Add stochastic gate noise toggles
  - Status: pending
  - File IDs: `src/Packages/Integration/Gates.m`, `src/Packages/Integration/Experiments.m`
  - Dependencies: TSK‑GATES‑002
  - Acceptance Criteria: Per‑gate flip probability configurable; deterministic seeds.
  - Acceptance Checklist:
    - [ ] Per‑gate flip probability configurable
    - [ ] Deterministic seeds enforced
  - Deliverables: Noise parameters and handlers.
  - Unit Test ID(s): `tests/MUnit/Gates/TSK-GATES-003-Tests.nb`
  - Test Location: `tests/MUnit/Gates`
  - Test Acceptance: Noise application with seed reproducibility.

### EPIC‑THEORY (Phase 2)

- Ticket ID: TSK‑THEORY‑001
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Formalise behavioural compression functional with axioms and bounds
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`, `doc/newIntPaper/fullEvalIntPaper.md`
  - Dependencies: TSK‑GATES‑001
  - Acceptance Criteria: Define compression functional over ordered repertoires using per‑gate index‑set formulae; state axioms (non‑negativity, invariance under relabelling, monotone improvement under band collapse); provide bounds tied to subsystem size and arity (without dataset compression comparisons).
  - Acceptance Checklist:
    - [ ] Compression functional defined (exact formulae based)
    - [ ] Axioms stated (non‑negativity, invariance, monotone improvement)
    - [ ] Bounds tied to size/arity
  - Deliverables: Axioms, theorems outline, proof strategy rooted in index algebra and description length.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-001-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Property tests verifying axioms with deterministic repertoires and formulae.

- Ticket ID: TSK‑THEORY‑002
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Sensitivity/influence relations and compression normalisation
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: Derive bounds linking compression to average sensitivity/influence; define a normalised compression measure for cross‑gate comparisons.
  - Acceptance Checklist:
    - [ ] Sensitivity/influence bounds stated
    - [ ] Normalised compression measure defined
  - Deliverables: Derived relations and usage notes.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-002-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Numerical validation against sample networks.

- Ticket ID: TSK‑THEORY‑003
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Decomposition across cut sets and canalisation effects on compressibility
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: State conditions where compression factorises or vanishes; quantify canalising collapse and its impact on description length.
  - Acceptance Checklist:
    - [ ] Factorisation/vanishing conditions derived
    - [ ] Canalising collapse impact quantified
  - Deliverables: Decomposition lemmas and canalisation statements.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-003-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Factorisation and canalisation compressibility properties confirmed.

- Ticket ID: TSK‑THEORY‑004
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Canonical index‑set representation and minimality
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: Define canonical form for per‑node and network index‑sets; prove minimality/uniqueness up to ordering; provide constructive procedure and examples.
  - Acceptance Checklist:
    - [ ] Canonical form definition and proofs
    - [ ] Minimality/uniqueness statements
    - [ ] Constructive procedure with examples
  - Deliverables: Formal section, proofs, and validation examples.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-004-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Canonical construction reproduces outputs; minimality checks pass.

- Ticket ID: TSK‑THEORY‑005
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Ordering transform invariance for index‑set algebra
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: Define ordering transforms; prove invariance/equivalence of index‑set constructions under MSB/LSB and related orderings; provide mapping functions.
  - Acceptance Checklist:
    - [ ] Transform definitions and proofs
    - [ ] Mapping functions verified on examples
  - Deliverables: Formal section with proofs and examples.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-005-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Invariance tests pass across orderings.

- Ticket ID: TSK‑THEORY‑006
  - Phase/Epic: Phase 2 / EPIC‑THEORY
  - Title: Closure and compositionality of index‑set operations
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: Prove closure and compositionality for union/intersection/complement operations across gate families; formalise network‑level composition rules with examples.
  - Acceptance Checklist:
    - [ ] Closure/compositionality proofs
    - [ ] Network‑level composition formalised
    - [ ] Examples included and validated
  - Deliverables: Formal section and validated examples.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-006-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Composition tests pass deterministically.

### EPIC‑FOUNDATIONS (Phase 2)

- Ticket ID: TSK‑THEORY‑005
  - Phase/Epic: Phase 2 / EPIC‑FOUNDATIONS
  - Title: Ordering transform invariance for index‑set algebra
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`, `doc/causalBinpaper/01_causalBool_inputs.tex`, `doc/causalBinpaper/02_cb_and.tex`, `src/Packages/Integration/Experiments.m`, `src/Packages/Integration/Gates.m`
  - Dependencies: TSK‑GATES‑001..002
  - Acceptance Criteria: Formal MSB/LSB orderings; mapping functions and invariance proofs; parameterised ordering policy in docs/tests; examples updated.
  - Deliverables: Ordering policy section; updated LaTeX; mapping utilities; unit tests.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-005-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Invariance across orderings with equal outputs modulo mapping.

- Ticket ID: TSK‑THEORY‑004
  - Phase/Epic: Phase 2 / EPIC‑FOUNDATIONS
  - Title: Canonical index‑set representation and minimality
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`, `src/Packages/Integration/Gates.m`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Canonical triplets reconstruct outputs; minimality/uniqueness up to permutation and ordering; property tests.
  - Deliverables: Proofs; examples; reconstruction scripts; tests.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-004-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Reconstruction equals baseline; permutation invariance.

- Ticket ID: TSK‑THEORY‑006 (Foundations linkage)
  - Phase/Epic: Phase 2 / EPIC‑FOUNDATIONS
  - Title: Closure and compositionality of index‑set operations
  - Status: pending
  - File IDs: `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005..004
  - Acceptance Criteria: Closure proofs; network‑level composition rules; validation.
  - Deliverables: Proofs; examples; artefacts.
  - Unit Test ID(s): `tests/MUnit/Theory/TSK-THEORY-006-Tests.nb`
  - Test Location: `tests/MUnit/Theory`
  - Test Acceptance: Composition tests pass.

### EPIC‑ALGO (Phase 3)

- Ticket ID: TSK‑ALGO‑001
  - Phase/Epic: Phase 3 / EPIC‑ALGO
  - Title: Exact computation and caching for small n
  - Status: pending
  - File IDs: `src/Packages/Integration/Alpha.m`
  - Dependencies: TSK‑GATES‑002, TSK‑THEORY‑001
  - Acceptance Criteria: Exact formula-based reconstruction with mask/band precomputation and caching; correctness on test networks.
  - Acceptance Checklist:
    - [ ] Exhaustive interventions implemented
    - [ ] Memoisation applied
    - [ ] Correctness on test networks verified
  - Deliverables: Exact solver and cache layer.
  - Unit Test ID(s): `tests/MUnit/Algo/TSK-ALGO-001-Tests.nb`
  - Test Location: `tests/MUnit/Algo`
  - Test Acceptance: Exact outputs on small n; cache hit assertions.

- Ticket ID: TSK‑ALGO‑002
  - Phase/Epic: Phase 3 / EPIC‑ALGO
  - Title: Monte Carlo/importance sampling approximations
  - Status: pending
  - File IDs: `src/Packages/Integration/Experiments.m`
  - Dependencies: TSK‑ALGO‑001
  - Acceptance Criteria: Convergence bounds; error estimates; seeds and stopping criteria; compression-aware sampling targets (parity/band-heavy subsets).
  - Acceptance Checklist:
    - [ ] Convergence bounds established
    - [ ] Error estimates computed
    - [ ] Seeds and stopping criteria defined
  - Deliverables: Sampling estimators.
  - Unit Test ID(s): `tests/MUnit/Algo/TSK-ALGO-002-Tests.nb`
  - Test Location: `tests/MUnit/Algo`
  - Test Acceptance: Convergence diagnostics and bound checks.

- Ticket ID: TSK‑ALGO‑003
  - Phase/Epic: Phase 3 / EPIC‑ALGO
  - Title: Subsystem search heuristics with branch‑and‑bound
  - Status: pending
  - File IDs: `src/Packages/Integration/Experiments.m`
  - Dependencies: TSK‑ALGO‑001
  - Acceptance Criteria: Pruning via cut sets; quality guarantees; runtime metrics; compression-guided branching/pruning heuristics.
  - Acceptance Checklist:
    - [ ] Cut‑set pruning implemented
    - [ ] Quality guarantees documented
    - [ ] Runtime metrics reported
  - Deliverables: Heuristic search framework.
  - Unit Test ID(s): `tests/MUnit/Algo/TSK-ALGO-003-Tests.nb`
  - Test Location: `tests/MUnit/Algo`
  - Test Acceptance: Pruning efficacy and quality metrics verified.

### EPIC‑STOCH (Phase 4)

- Ticket ID: TSK‑STOCH‑001
  - Phase/Epic: Phase 4 / EPIC‑STOCH
  - Title: Asynchronous update regimes
  - Status: pending
  - File IDs: `src/Packages/Integration/Experiments.m`
  - Dependencies: TSK‑ALGO‑001
  - Acceptance Criteria: Synchronous vs asynchronous toggles; reproducible schedules; compression comparison.
  - Acceptance Checklist:
    - [ ] Sync/async toggles available
    - [ ] Reproducible schedules defined
    - [ ] Integration comparison performed
  - Deliverables: Regime controllers and documentation.
  - Unit Test ID(s): `tests/MUnit/Stoch/TSK-STOCH-001-Tests.nb`
  - Test Location: `tests/MUnit/Stoch`
  - Test Acceptance: Schedule reproducibility and integration differences.

- Ticket ID: TSK‑STOCH‑002
  - Phase/Epic: Phase 4 / EPIC‑STOCH
  - Title: Noise robustness analyses
  - Status: pending
  - File IDs: `experiments/noise/*.nb`, `results/noise/*.csv`
  - Dependencies: TSK‑GATES‑003
  - Acceptance Criteria: Sensitivity of compression components to flip noise; confidence intervals; summary figures.
  - Acceptance Checklist:
    - [ ] Integration sensitivity to flip noise quantified
    - [ ] Confidence intervals computed
    - [ ] Summary figures generated
  - Deliverables: Noise study notebooks and outputs.
  - Unit Test ID(s): `tests/MUnit/Stoch/TSK-STOCH-002-Tests.nb`
  - Test Location: `tests/MUnit/Stoch`
  - Test Acceptance: Noise robustness metrics and CI computation.

### EPIC‑TEST (Phase 5)

- Ticket ID: TSK‑TEST‑001
  - Phase/Epic: Phase 5 / EPIC‑TEST
  - Title: Unit tests for gate truth tables
  - Status: pending
  - File IDs: `tests/MUnit/GatesTests.nb`
  - Dependencies: TSK‑GATES‑001
  - Acceptance Criteria: All gates pass truth‑table MUnit tests; deterministic execution.
  - Acceptance Checklist:
    - [ ] All gates pass truth‑table tests
    - [ ] Deterministic execution verified
  - Deliverables: MUnit notebook and results.

- Ticket ID: TSK‑TEST‑002
  - Phase/Epic: Phase 5 / EPIC‑TEST
  - Title: Property tests for axioms and invariances
  - Status: pending
  - File IDs: `tests/MUnit/IntegrationProperties.nb`
  - Dependencies: TSK‑THEORY‑001
  - Acceptance Criteria: Non‑negativity, separability zero, relabelling invariance verified on ensembles.
  - Acceptance Checklist:
    - [ ] Non‑negativity verified on ensembles
    - [ ] Separability zero verified
    - [ ] Relabelling invariance verified
  - Deliverables: Property test notebook.

- Ticket ID: TSK‑TEST‑003
  - Phase/Epic: Phase 5 / EPIC‑TEST
  - Title: Performance tests for repertoire generation
  - Status: pending
  - File IDs: `tests/MUnit/Performance.nb`
  - Dependencies: TSK‑ALGO‑001
  - Acceptance Criteria: Scale and runtime targets documented; caching efficacy measured.
  - Acceptance Checklist:
    - [ ] Scale and runtime targets documented
    - [ ] Caching efficacy measured
  - Deliverables: Performance metrics and plots.

- Ticket ID: TSK‑TEST‑004
  - Phase/Epic: Phase 5 / EPIC‑TEST
  - Title: Acceptance tests to reproduce manuscript figures
  - Status: pending
  - File IDs: `tests/MUnit/Acceptance.nb`, `experiments/*`, `results/*`, `figures/*`
  - Dependencies: TSK‑EXPER‑001..005, TSK‑COMPARE‑001..003
  - Acceptance Criteria: One‑click run produces all CSVs and figures; checksums recorded.
  - Acceptance Checklist:
    - [ ] One‑click run produces all CSVs and figures
    - [ ] Checksums recorded
  - Deliverables: Acceptance suite and artefacts.

## Global Documentation Policy
- Each ticket must update `doc/newIntPaper/docProcess.tex` with a subsection covering objective, methods, inputs, outputs, acceptance tests, and artefacts.
- Include at least one example with explicit ordering policy, `cm`, `dynamic`, `I_c`, and sample inputs/outputs.
- Compile `docProcess.tex` and ensure `docProcess.pdf` is generated without errors; store the PDF alongside the source.
- Cross‑link per‑gate LaTeX in `doc/causalBinpaper/*` to the ordering policy.

### Documentation Acceptance Checklist (applies to every ticket)
- [ ] `docProcess.tex` updated with ticket subsection
- [ ] Representative example included (network `cm`, `dynamic`, sample inputs/outputs)
- [ ] `docProcess.tex` compiled to `docProcess.pdf` without fatal errors

### EPIC‑EXPER (Phase 6)

- Ticket ID: TSK‑EXPER‑001
  - Phase/Epic: Phase 6 / EPIC‑EXPER
  - Title: Ensemble generation for ER, scale‑free, small‑world graphs
  - Status: pending
  - File IDs: `experiments/topologies/Topologies.nb`, `data/topologies/*.mx`
  - Dependencies: TSK‑ARCH‑002
  - Acceptance Criteria: Parameterised generators with seeds; saved graphs; metadata.
  - Acceptance Checklist:
    - [ ] Generators parameterised with seeds
    - [ ] Graphs saved
    - [ ] Metadata recorded
  - Deliverables: Topology datasets.

- Ticket ID: TSK‑EXPER‑002
  - Phase/Epic: Phase 6 / EPIC‑EXPER
  - Title: Gate mixture sweeps and bias control
  - Status: pending
  - File IDs: `experiments/gates/GateSweeps.nb`, `results/gates/*.csv`
  - Dependencies: TSK‑GATES‑002
  - Acceptance Criteria: Heatmaps of compression vs gate proportions and output bias.
  - Acceptance Checklist:
    - [ ] Integration heatmaps vs gate mix and output bias
  - Deliverables: Sweep outputs and figures.

- Ticket ID: TSK‑EXPER‑003
  - Phase/Epic: Phase 6 / EPIC‑EXPER
  - Title: Update regime comparison (sync vs async)
  - Status: pending
  - File IDs: `experiments/regimes/Regimes.nb`, `results/regimes/*.csv`
  - Dependencies: TSK‑STOCH‑001
  - Acceptance Criteria: Comparative statistics; reproducible schedules.
  - Acceptance Checklist:
    - [ ] Comparative statistics computed
    - [ ] Reproducible schedules used
  - Deliverables: Regime study outputs.

- Ticket ID: TSK‑EXPER‑004
  - Phase/Epic: Phase 6 / EPIC‑EXPER
  - Title: Subsystem search evaluation
  - Status: pending
  - File IDs: `experiments/subsystems/Subsets.nb`, `results/subsystems/*.csv`
  - Dependencies: TSK‑ALGO‑003
  - Acceptance Criteria: Size‑compression trade‑off curves; approximation gap analysis.
  - Acceptance Checklist:
    - [ ] Size‑integration trade‑off curves produced
    - [ ] Approximation gap analysis completed
  - Deliverables: Subsystem figures and tables.

- Ticket ID: TSK‑EXPER‑005
  - Phase/Epic: Phase 6 / EPIC‑EXPER
  - Title: Noise robustness experiments
  - Status: pending
  - File IDs: `experiments/noise/Noise.nb`, `results/noise/*.csv`
  - Dependencies: TSK‑STOCH‑002
  - Acceptance Criteria: CI bands, sensitivity plots; summary statistics.
  - Acceptance Checklist:
    - [ ] Confidence interval bands generated
    - [ ] Sensitivity plots produced
    - [ ] Summary statistics reported
  - Deliverables: Noise figures and CSVs.

### EPIC‑COMPARE (Phase 7)

- Ticket ID: TSK‑COMPARE‑002
  - Phase/Epic: Phase 7 / EPIC‑COMPARE
  - Title: PID‑based synergy comparator
  - Status: pending
  - File IDs: `experiments/compare/PID.nb`
  - Dependencies: TSK‑THEORY‑002
  - Acceptance Criteria: Synergy computed on selected subsystems; correlation analysis vs integration.
  - Acceptance Checklist:
    - [ ] Synergy computed on selected subsystems
    - [ ] Correlation analysis vs integration performed
  - Deliverables: PID comparison figures.

- Ticket ID: TSK‑COMPARE‑003
  - Phase/Epic: Phase 7 / EPIC‑COMPARE
  - Title: Transfer entropy and multi‑information comparators
  - Status: pending
  - File IDs: `experiments/compare/TE_MI.nb`
  - Dependencies: TSK‑EXPER‑001..003
  - Acceptance Criteria: Estimates across ensembles; quantitative comparisons and tables.
  - Acceptance Checklist:
    - [ ] Estimates computed across ensembles
    - [ ] Quantitative comparisons and tables prepared
  - Deliverables: Comparator datasets and plots.

### EPIC‑PAPER (Phase 8)

- Ticket ID: TSK‑PAPER‑001
  - Phase/Epic: Phase 8 / EPIC‑PAPER
  - Title: Manuscript structure and figure list
  - Status: pending
  - File IDs: `doc/newIntPaper/fullIntPaperOutline.md`
  - Dependencies: TSK‑EXPER‑001..005, TSK‑COMPARE‑002..003
  - Acceptance Criteria: Outline aligned to journal style; figure/table inventory mapped to artefacts.
  - Acceptance Checklist:
    - [ ] Outline aligned to journal style
    - [ ] Figure/table inventory mapped to artefacts
  - Deliverables: Outline document.

- Ticket ID: TSK‑PAPER‑002
  - Phase/Epic: Phase 8 / EPIC‑PAPER
  - Title: Methods section with algorithms and complexity
  - Status: pending
  - File IDs: `doc/newIntPaper/methods.md`
  - Dependencies: TSK‑ALGO‑001..003
  - Acceptance Criteria: Clear algorithms (formula-based reconstruction); complexity analysis; compression measure definition; implementation notes.
  - Acceptance Checklist:
    - [ ] Algorithms clearly presented
    - [ ] Complexity analysis provided
    - [ ] Implementation notes documented
  - Deliverables: Methods draft.

- Ticket ID: TSK‑PAPER‑003
  - Phase/Epic: Phase 8 / EPIC‑PAPER
  - Title: Theory section with axioms and proofs
  - Status: pending
  - File IDs: `doc/newIntPaper/theory.md`
  - Dependencies: TSK‑THEORY‑001..003
  - Acceptance Criteria: Statements and proof sketches for compression axioms and bounds; assumptions explicit.
  - Acceptance Checklist:
    - [ ] Statements and proof sketches included
    - [ ] Assumptions explicit
  - Deliverables: Theory draft.

- Ticket ID: TSK‑PAPER‑004
  - Phase/Epic: Phase 8 / EPIC‑PAPER
  - Title: Results section with validation and figures
  - Status: pending
  - File IDs: `doc/newIntPaper/results.md`
  - Dependencies: TSK‑EXPER‑001..005, TSK‑COMPARE‑002..003
  - Acceptance Criteria: Complete figures with captions (compression vs exhaustive outputs); statistical analyses reported.
  - Acceptance Checklist:
    - [ ] Complete figures with captions
    - [ ] Statistical analyses reported
  - Deliverables: Results draft.

- Ticket ID: TSK‑PAPER‑005
  - Phase/Epic: Phase 8 / EPIC‑PAPER
  - Title: Discussion, limitations and future directions
  - Status: pending
  - File IDs: `doc/newIntPaper/discussion.md`
  - Dependencies: TSK‑PAPER‑004
  - Acceptance Criteria: Balanced interpretation; limitations and scope clearly stated.
  - Acceptance Checklist:
    - [ ] Balanced interpretation
    - [ ] Limitations and scope clearly stated
  - Deliverables: Discussion draft.

### EPIC‑RELEASE (Phase 9)

- Ticket ID: TSK‑RELEASE‑001
  - Phase/Epic: Phase 9 / EPIC‑RELEASE
  - Title: Replication package assembly
  - Status: pending
  - File IDs: `results/`, `figures/`, `experiments/`, `tests/`, `docs/repro.md`
  - Dependencies: TSK‑TEST‑004, TSK‑PAPER‑004
  - Acceptance Criteria: Single script/notebook reproduces compression artefacts and figures; data and code versions recorded.
  - Acceptance Checklist:
    - [ ] Single script/notebook reproduces artefacts
    - [ ] Data and code versions recorded
  - Deliverables: Release candidate.

- Ticket ID: TSK‑RELEASE‑002
  - Phase/Epic: Phase 9 / EPIC‑RELEASE
  - Title: Licensing, metadata and persistent identifiers
  - Status: pending
  - File IDs: `LICENSE`, `CITATION.cff`, `docs/metadata.json`
  - Dependencies: TSK‑RELEASE‑001
  - Acceptance Criteria: Appropriate licence; citation file; DOI plan.
  - Acceptance Checklist:
    - [ ] Appropriate licence selected
    - [ ] Citation file present
    - [ ] DOI plan prepared
  - Deliverables: Licensing and citation files.

- Ticket ID: TSK‑RELEASE‑003
  - Phase/Epic: Phase 9 / EPIC‑RELEASE
  - Title: Submission tailoring for target journals
  - Status: pending
  - File IDs: `doc/newIntPaper/journalSubmissionChecklist.md`
  - Dependencies: TSK‑PAPER‑001..005
  - Acceptance Criteria: Cover letter, compliance checks, figure formats, word limits.
  - Acceptance Checklist:
    - [ ] Cover letter drafted
    - [ ] Compliance checks completed
    - [ ] Figure formats correct
    - [ ] Word limits satisfied
  - Deliverables: Submission pack.

## Dependencies Graph (Summary)
- ARCH → GATES → THEORY → ALGO → STOCH → TEST → EXPER → COMPARE → PAPER → RELEASE

## Acceptance Criteria Summary
- All tests deterministic and passing; artefacts reproducible end‑to‑end; theory stated clearly with bounds; experiments cover ensembles, regimes and comparators; paper components cohesive and compliant; replication package complete.

## Milestones
- M0: Architecture defined and directories created
- M1: Gate catalogue and dispatch integrated
- M2: Behavioural compression functional formalised
- M3: Algorithms and subsystem search validated
- M4: Stochastic variants and robustness complete
- M5: Full test suite passing
- M6: Experimental programme completed
- M7: Comparator analyses published to results
- M8: Manuscript assembled
- M9: Release candidate ready
### EPIC‑PATTERN (Phase 4A)

- Ticket ID: TSK‑PATTERN‑001
  - Phase/Epic: Phase 4A / EPIC‑PATTERN
  - Title: Generalise ordered repertoire pattern method beyond AND
  - Status: pending
  - File IDs: `doc/causalBinpaper/01_causalBool_inputs.tex`, `doc/causalBinpaper/02_cb_and.tex`, `doc/newIntPaper/fullEvalIntPaper.md`
  - Dependencies: TSK‑GATES‑001, TSK‑THEORY‑001
  - Acceptance Criteria: Pattern alphabet and derivation method specified for all gate families (monotone, non‑monotone, unary, directional, threshold, canalising); documented linkage to compression (description length), sensitivity and canalisation.
  - Acceptance Checklist:
    - [ ] Pattern alphabet specified
    - [ ] Derivation method specified for all gate families
    - [ ] Linkage to sensitivity and canalisation documented
  - Deliverables: Updated documentation sections; derivation outline.
  - Unit Test ID(s): `tests/MUnit/Pattern/TSK-PATTERN-001-Tests.nb`
  - Test Location: `tests/MUnit/Pattern`
  - Test Acceptance: Method applied to sample gates and matches repertoire patterns.

- Ticket ID: TSK‑PATTERN‑002
  - Phase/Epic: Phase 4A / EPIC‑PATTERN
  - Title: Derive symbolic pattern formulae per gate family
  - Status: pending
  - File IDs: `doc/causalBinpaper/*`, `doc/newIntPaper/fullEvalIntPaper.md`
  - Dependencies: TSK‑PATTERN‑001
  - Acceptance Criteria: Closed‑form or piecewise formulae for ordered exhaustive repertoires per gate; parity/equivalence rules for XOR/XNOR; Hamming weight bands for thresholds; canalising collapse conditions; mapping to compression components (bands, parity masks, thresholds, collapse).
  - Acceptance Checklist:
    - [ ] Closed‑form/piecewise formulae per gate
    - [ ] Parity/equivalence rules for XOR/XNOR
    - [ ] Hamming weight bands for thresholds
    - [ ] Canalising collapse conditions
  - Deliverables: LaTeX derivations and summary tables.
  - Unit Test ID(s): `tests/MUnit/Pattern/TSK-PATTERN-002-Tests.nb`
  - Test Location: `tests/MUnit/Pattern`
  - Test Acceptance: Symbolic formulae vs empirical patterns across gates.

- Ticket ID: TSK‑PATTERN‑003
  - Phase/Epic: Phase 4A / EPIC‑PATTERN
  - Title: Validate pattern formulae against generated repertoires
  - Status: pending
  - File IDs: `experiments/patterns/Patterns.nb`, `results/patterns/*.csv`
  - Dependencies: TSK‑EXPER‑001, TSK‑GATES‑002
  - Acceptance Criteria: Empirical agreement across ensembles; error rates reported; invariance under relabelling confirmed; compression components validated against outputs.
  - Acceptance Checklist:
    - [ ] Empirical agreement across ensembles
    - [ ] Error rates reported
    - [ ] Relabelling invariance confirmed
  - Deliverables: Validation outputs and figures.
  - Unit Test ID(s): `tests/MUnit/Pattern/TSK-PATTERN-003-Tests.nb`
  - Test Location: `tests/MUnit/Pattern`
  - Test Acceptance: Agreement metrics and invariance checks.

- Ticket ID: TSK‑PATTERN‑004
  - Phase/Epic: Phase 4A / EPIC‑PATTERN
  - Title: Integrate pattern formulae into manuscript
  - Status: pending
  - File IDs: `doc/newIntPaper/theory.md`, `doc/newIntPaper/results.md`, `doc/causalBinpaper/*`
  - Dependencies: TSK‑PATTERN‑002..003
  - Acceptance Criteria: Pattern section added with derivations, examples, and compression perspective; figures and tables included.
  - Acceptance Checklist:
    - [ ] Pattern section added with derivations and examples
    - [ ] Comparisons to causal integration
    - [ ] Figures and tables included
  - Deliverables: Manuscript updates.
  - Unit Test ID(s): `tests/MUnit/Pattern/TSK-PATTERN-004-Tests.nb`
  - Test Location: `tests/MUnit/Pattern`
  - Test Acceptance: Acceptance suite regenerates figures and tables.
### EPIC‑ANALYSIS (Phase 6B, Re‑opened Series)

Policy (applies to all ANALYSIS tickets): reformat `doc/newIntPaper/docProcess.tex` sections; add ordering policy references; derive network‑aware index sets with explicit `I_c` and ordering; validate exact equality to `CreateRepertoiresDispatch`; deterministic tests with artefacts.

- Ticket ID: TSK‑ANALYSIS‑AND
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: AND — pivot‑plus‑offset formalisation (network‑aware)
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_and.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Pivot/offset with ordering; connected‑bit constraints enforced; equality to empirical indices for multiple `I_c` and `n`; docProcess updated.
  - Deliverables: Updated LaTeX; validation artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/ANDTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Analytic indices equal empirical under ordering mapping.

- Ticket ID: TSK‑ANALYSIS‑OR
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: OR — band‑union formalisation (network‑aware)
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_or.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Union of one‑bands per connected index; ordering consistency; equality to empirical across ensembles; docProcess updated.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/ORTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Band‑union indices equal empirical.

- Ticket ID: TSK‑ANALYSIS‑XOR
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: XOR — odd parity (network‑aware)
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_xor.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Odd parity sets with ordering mapping; equality to empirical; sensitivity properties included.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/XORTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Parity indices equal empirical.

- Ticket ID: TSK‑ANALYSIS‑NAND
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: NAND — complement of AND one‑set
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_nand.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: NAND zero‑set equals AND one‑set; ordering consistent; equality to empirical.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/NANDTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Complement indices validated.

- Ticket ID: TSK‑ANALYSIS‑NOR
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: NOR — complement of OR one‑set
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_nor.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: One‑set where all connected inputs are zero; ordering consistent; equality to empirical.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/NORTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Complement indices validated.

- Ticket ID: TSK‑ANALYSIS‑XNOR
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: XNOR — even parity (network‑aware)
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_xnor.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Even parity index sets with ordering mapping; equality to empirical.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/XNORTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Equivalence indices equal empirical.

- Ticket ID: TSK‑ANALYSIS‑NOT
  - Phase/Epic: Phase 6B / EPIC‑ANALYSIS
  - Title: NOT — unary inversion band (network‑aware)
  - Status: re‑opened
  - File IDs: `doc/causalBinpaper/02_cb_not.tex`, `doc/newIntPaper/docProcess.tex`
  - Dependencies: TSK‑THEORY‑005
  - Acceptance Criteria: Zero‑band of designated bit with ordering mapping; equality to empirical; docProcess updated.
  - Deliverables: Updated LaTeX; artefacts.
  - Unit Test ID(s): `tests/MUnit/Analysis/NOTTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Unary inversion indices validated.

- Ticket ID: TSK‑ANALYSIS‑IMPLIES
  - Phase/Epic: Phase 4B / EPIC‑ANALYSIS
  - Title: IMPLIES/NIMPLIES — asymmetric entailment patterns and formulae
  - Status: pending
  - File IDs: `doc/causalBinpaper/02_cb_impl.tex`
  - Dependencies: TSK‑PATTERN‑001
  - Acceptance Criteria: Asymmetric region characterisation; validation.
  - Acceptance Checklist:
    - [ ] Asymmetric region characterisation provided
    - [ ] Validation completed
  - Deliverables: LaTeX derivation and validation.
  - Unit Test ID(s): `tests/MUnit/Analysis/IMPLIESTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Asymmetric entailment validated.

- Ticket ID: TSK‑ANALYSIS‑KOFN
  - Phase/Epic: Phase 4B / EPIC‑ANALYSIS
  - Title: k‑of‑n thresholds — banded Hamming weight formulae
  - Status: pending
  - File IDs: `doc/causalBinpaper/02_cb_kofn.tex`
  - Dependencies: TSK‑PATTERN‑001
  - Acceptance Criteria: Piecewise band formulae and validation.
  - Acceptance Checklist:
    - [ ] Piecewise band formulae provided
    - [ ] Validation completed
  - Deliverables: LaTeX document and results.
  - Unit Test ID(s): `tests/MUnit/Analysis/KOFNTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Threshold band patterns validated.

- Ticket ID: TSK‑ANALYSIS‑CANALISING
  - Phase/Epic: Phase 4B / EPIC‑ANALYSIS
  - Title: Canalising/nested‑canalising — collapse rules and formulae
  - Status: pending
  - File IDs: `doc/causalBinpaper/02_cb_canalising.tex`
  - Dependencies: TSK‑PATTERN‑001
  - Acceptance Criteria: Canalising value conditions, collapse effects; validation.
  - Acceptance Checklist:
    - [ ] Canalising value conditions stated
    - [ ] Collapse effects described
    - [ ] Validation completed
  - Deliverables: LaTeX derivation and validation.
  - Unit Test ID(s): `tests/MUnit/Analysis/CANALISINGTests.nb`
  - Test Location: `tests/MUnit/Analysis`
  - Test Acceptance: Canalising collapse validated.

### EPIC‑MIXED (Phase 6B)

- Ticket ID: TSK‑MIXED‑001
  - Phase/Epic: Phase 6B / EPIC‑MIXED
  - Title: Define composition rules for mixed gate dynamics in networks
  - Status: pending
  - File IDs: `doc/causalBinpaper/exam.tex`, `doc/newIntPaper/fullEvalIntPaper.md`
  - Dependencies: TSK‑ANALYSIS‑AND..CANALISING
  - Acceptance Criteria: Composition framework linking per‑gate formulae to network‑level mixed dynamics; intuitive explanations.
  - Acceptance Checklist:
    - [ ] Composition framework defined
    - [ ] Links per‑gate formulae to network‑level dynamics
    - [ ] Intuitive explanations provided
  - Deliverables: Extended exam.tex and manuscript sections.
  - Unit Test ID(s): `tests/MUnit/Mixed/TSK-MIXED-001-Tests.nb`
  - Test Location: `tests/MUnit/Mixed`
  - Test Acceptance: Composition rules correct on benchmark mixed networks.

- Ticket ID: TSK‑MIXED‑002
  - Phase/Epic: Phase 6B / EPIC‑MIXED
  - Title: Validate mixed dynamics formulae against ensembles
  - Status: pending
  - File IDs: `experiments/mixed/Mixed.nb`, `results/mixed/*.csv`
  - Dependencies: TSK‑MIXED‑001, TSK‑EXPER‑001..004
  - Acceptance Criteria: Empirical agreement on mixed networks; error metrics and figures.
  - Acceptance Checklist:
    - [ ] Empirical agreement on mixed networks
    - [ ] Error metrics reported
    - [ ] Figures generated
  - Deliverables: Validation artefacts and plots.
  - Unit Test ID(s): `tests/MUnit/Mixed/TSK-MIXED-002-Tests.nb`
  - Test Location: `tests/MUnit/Mixed`
  - Test Acceptance: Agreement metrics across ensembles.

- Ticket ID: TSK‑MIXED‑003
  - Phase/Epic: Phase 6B / EPIC‑MIXED
  - Title: Integrate mixed dynamics results into manuscript
  - Status: pending
  - File IDs: `doc/newIntPaper/theory.md`, `doc/newIntPaper/results.md`, `doc/newIntPaper/discussion.md`
  - Dependencies: TSK‑MIXED‑002
  - Acceptance Criteria: Clear narrative and figures; compression perspective articulated.
  - Acceptance Checklist:
    - [ ] Clear narrative and figures
    - [ ] Links to integration functional
    - [ ] Compression perspective articulated
  - Deliverables: Manuscript updates.
  - Unit Test ID(s): `tests/MUnit/Mixed/TSK-MIXED-003-Tests.nb`
  - Test Location: `tests/MUnit/Mixed`
  - Test Acceptance: Acceptance suite reproduces mixed dynamics figures.
## Global Testing Policy
- Every ticket must create or update an MUnit unit test notebook that verifies its acceptance criteria using deterministic seeds and documented parameters.
- Naming convention: `tests/MUnit/<Epic>/<TicketID>Tests.nb` (or a close variant). Examples:
  - Gates: `tests/MUnit/Gates/TSK-GATES-001-Tests.nb`
  - Theory: `tests/MUnit/Theory/TSK-THEORY-001-Tests.nb`
  - Algorithms: `tests/MUnit/Algo/TSK-ALGO-001-Tests.nb`
  - Pattern: `tests/MUnit/Pattern/TSK-PATTERN-002-Tests.nb`
  - Analysis (per-gate): `tests/MUnit/Analysis/ANDTests.nb`, `tests/MUnit/Analysis/ORTests.nb`, etc.
  - Mixed: `tests/MUnit/Mixed/TSK-MIXED-002-Tests.nb`
- Failing tests block progression; tickets cannot be marked complete until corresponding tests pass.
- Scientific context: tests for experiments must include statistical validation (e.g., pattern match rates, bootstrap confidence intervals where applicable) and exact artefact reproduction checksums.
- ## Global Documentation Policy
- Each ticket must update the supplementary LaTeX document `doc/newIntPaper/docProcess.tex` with a subsection covering objective, methods, inputs, outputs, acceptance tests, and artefacts.
- Use the template provided in `docProcess.tex` and include paths to `results/` and `figures/` artefacts.
- Documentation updates are part of acceptance; tickets cannot close without corresponding documentation entries.
 - Compilation requirement: after updating documentation, compile `docProcess.tex` and ensure `docProcess.pdf` is generated without errors; store the PDF alongside the source.
## Global Index Formulae Policy
- Derive closed‑form network‑aware index formulae for ordered exhaustive inputs with explicit ordering and `I_c` dependence.
- Validate index formulae by exact equality to empirical index sets from `CreateRepertoiresDispatch` under MSB‑first and LSB‑first (via mapping functions).
- Include derivations and representative examples in `doc/newIntPaper/docProcess.tex`; extend per‑gate LaTeX under `doc/causalBinpaper/`.
- Documentation Acceptance Checklist additions (analysis tickets):
  - [ ] Index formulae derived clearly with ordering and `I_c`
  - [ ] Empirical index sets equal analytic sets (both orderings)
  - [ ] Examples with matrices, derivations and tables
  - [ ] `docProcess.tex` compiled successfully with the new section

## Global Mathematical Formulae Policy
- Derive formal gate functionals (conjunction/disjunction/parity/threshold/canalising) and property proofs (monotonicity, sensitivity, thresholds, canalising).
- Link properties to observed repertoire behaviour and index‑set derivations under explicit ordering.
- Validate against truth tables and repertoire outputs deterministically.
- Follow per‑gate documentation format exemplified by `doc/causalBinpaper/02_cb_and.tex` with ordering references.

### Per‑Gate Analysis Acceptance Checklist (applies to TSK‑ANALYSIS‑AND/OR/XOR/NAND/NOR/XNOR/NOT/IMPLIES/KOFN/CANALISING)
- [ ] Formal mathematical gate formula derived
- [ ] Network‑aware index formulae with ordering and `I_c`
- [ ] Property proofs included
- [ ] Truth tables and repertoire outputs match analytic formulae
- [ ] Empirical index sets equal analytic sets (both orderings via mapping)
- [ ] `docProcess.tex` section updated with full examples
- [ ] Per‑gate LaTeX updated per `02_cb_and.tex`
- [ ] Deterministic tests passing; artefacts exported
- [ ] `docProcess.tex` compiled successfully to PDF
