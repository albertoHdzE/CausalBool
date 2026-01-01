# Causal Boolean Integration
A deterministic, physics‑inspired programme of algorithmic information theory for interacting entities. It develops short, elegant, and exact formulae that reproduce and explain the behaviour of Boolean causal networks. The emphasis is on canonical derivations, ordering‑aware invariances, and closed‑form index algebra that reconstruct network outputs without probabilistic assumptions. The resulting theory enables prediction and forecasting with reduced memory, computation, and time, and scales beyond regimes where probabilistic or enumeration‑heavy approaches break down.

## Scientific Overview
- Theory first: ordered repertoires and closed‑form index sets per gate compose to reconstruct the synchronous network map exactly, with formal policies for ordering and bit‑reversal invariance.
- Algorithmic framing: the programme is an instance of algorithmic information theory applied to deterministic mechanisms, prioritising compressive, compositional formulae over probabilistic models.
- Determinism: predictive equality to exhaustive repertoires is proved and validated; evaluations are seed‑controlled when stochastic toggles are used for robustness studies.
- Information signatures: deterministic repertoires yield PID, Transfer Entropy, and Total Correlation that diagnose redundancy, uniqueness, and synergy without requiring probabilistic fitting.
- Subsystems and factorisation: compression functionals factorise over graph blocks; undirected adjacency supports conservative subsystem inference and block‑diagonal guarantees.

## Why It Scales
- Exhaustive enumeration scales as \(2^n\); closed‑form and per‑node semantics reconstruct outputs row‑wise with cost proportional to in‑degree, avoiding truth‑table explosion.
- Importance sampling validates equality and profiles performance at larger sizes where exhaustive baselines are impractical; predictive evaluation remains exact under ordering policies.
- Subsystem factorisation reduces analysis to blocks when connectivity admits decomposition, enabling principled compression and tractable evaluation on large graphs.
- Deterministic pipelines minimise memory and runtime, replacing expensive table construction and search with direct formulae.

## Context vs IIT
- Integrated Information Theory faces combinatorial limits on network size and exhaustive partitions; practical evaluation often requires heavy approximations.
- This programme sidesteps those limits with deterministic formulae, ordering‑aware invariances, and block factorisation, delivering exact reconstructions and information signatures at sizes beyond naive enumeration.
- The scientific stance is predictive and constructive: derive canonical mechanisms, prove invariances, and validate equality, then measure compression and robustness.

## Why It Matters
- Exactness: closed‑form index sets and exhaustive repertoires ensure correctness beyond sampling.
- Reproducibility: deterministic tests, pinned seeds, and exported artefacts for every run.
- Insight: PID, TE, and TC reveal complementary vs synergistic structure in canonical gates and motifs.
- Ready to share: manuscript, figures, and summaries generated automatically from experiments.

## Validation References
- Foundations, ordering invariance, index algebra, and acceptance policies: [docProcess.tex](doc/newIntPaper/docProcess.tex)
- Medium‑scale exact reconstruction and performance profiling: [expProcess.tex](doc/newIntPaper/expProcess.tex)
- Ordering invariance and truth‑table coverage (up to arity 6): [expProcess.tex:TEST‑001](doc/newIntPaper/expProcess.tex#L190-L255)
- Importance sampling with exact predictive equality at large sizes: [expProcess.tex:ALGO‑002](doc/newIntPaper/expProcess.tex#L107-L135)
- Subsystem factorisation and block guarantees: [expProcess.tex:ALGO‑003](doc/newIntPaper/expProcess.tex#L75-L106)

## Quick Start
- Kernel path: `/Applications/Wolfram.app/Contents/MacOS/WolframKernel`.
- Run all tests: `zsh tests/MUnit/run-tests.sh --all`
- By section: `zsh tests/MUnit/run-tests.sh --section Analysis`
- By gate: `zsh tests/MUnit/run-tests.sh --section Analysis --gate NOT`
- Mixed dynamics: see `experiments/mixed/Mixed.m`, outputs under `results/mixed/validation/`.

## Results At A Glance
- Canonical gates: AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES/NIMPLIES, KOFN (strict/non‑strict), CANALISING.
- Information signatures: PID (unique/shared/synergy), Transfer Entropy, Total Correlation.
- Artefacts: CSV/JSON summaries under `results/`, figures under `figures/`, compiled paper in `doc/newIntPaper/`.

## Gate Catalogue and Dispatch
- `Integration`Gates`ApplyGate[gate, inputs, params]` supports AND, OR, XOR, NAND, NOR, XNOR, NOT, IMPLIES, NIMPLIES, MAJORITY, KOFN, CANALISING.
- Optional noise: `params["noiseFlipProb" -> p]` flips outputs with probability `p` (use deterministic seeds).
- Index sets: `Integration`Gates`IndexSet[gate, arity, params]` and network‑aware `IndexSetNetwork[gate, n, Ic, params]` for connected inputs `Ic`.

## Documentation
- Supplement: `doc/newIntPaper/docProcess.tex` compiles to `doc/newIntPaper/docProcess.pdf`.
- Policies: testing and documentation enforced via `doc/newIntPaper/plan.md`.
- Compile: `cd doc/newIntPaper && pdflatex -interaction=nonstopmode docProcess.tex`.

## Structure
- `src/Packages/Integration/` core packages: `Alpha.m`, `Gates.m`, `Experiments.m`, `SelfTest.m`.
- `src/integration/` legacy notebooks/routines: `Alpha.m`, `Alpha.nb`, `newAlpha.nb`.
- `tests/MUnit/` deterministic tests by section: `Analysis/`, `Gates/`, `Pattern/`, `Arch/`, `Mixed/`.
- `results/` CSV/JSON outputs from experiments and tests; `figures/` plots.
- `doc/newIntPaper/` manuscript support: `docProcess.tex`, `plan.md`, `documents.md`, `fullEvalIntPaper.md`.
- `experiments/` reproducible study scripts (e.g., mixed dynamics).

## Current Status (Highlights)
- Analysis completed for canonical gates and thresholds; dispatch integrated.
- Network‑aware index helpers provided (KOFN, IMPLIES/NIMPLIES, NOT, CANALISING).
- Documentation compiled; artefacts exported for implemented tickets.

## Reproducibility
- Deterministic tests and experiments; record seeds for any stochastic runs.
- Artefacts saved to `results/`, plots to `figures/`; summaries recorded alongside outputs.
