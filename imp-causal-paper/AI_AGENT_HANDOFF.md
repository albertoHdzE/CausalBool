# AI Agent Handoff For `imp-causal-paper`

## Purpose

This document is a full knowledge-transfer package for a new AI agent that must continue the work in `imp-causal-paper` from scratch, without relying on any external conversation history.

Read this file first, then read:

1. `README.md`
2. `EXACT_REPRODUCTION_PLAN.md`
3. `REPRODUCTION_LEDGER.md`
4. `definition_fidelity.json`
5. `imp-results.md`

This handoff is intentionally redundant. Redundancy is desirable here because the goal is zero ambiguity and zero hidden context.

## Mission

The target paper is:

- `doc/Zenil-Papers/004.AI4CausalDiscovery-zenil.pdf`
- title: `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems`
- citation target: Zenil et al., iScience 2019

The mission is not to build an inspired implementation or a pedagogical toy version.

The mission is:

- exact reproduction where possible,
- provenance-first recovery where exact assets are unavailable,
- claim-by-claim scientific corroboration,
- explicit non-claims where reproduction is incomplete.

This repository must remain a project-local, isolated reproduction environment. Do not make the scientific workflow depend on hidden shell state, personal folders, unpublished notes, or assumptions not recorded inside this project.

## Non-Negotiable Policies

These are project laws, not preferences.

- Never use mocks.
- Never fabricate biological data.
- Use real public assets whenever possible.
- Use deterministic synthetic data only for synthetic blocks that are already synthetic in the paper, and only when necessary.
- Never over-claim reproduction fidelity.
- Never describe a reduced analogue as an exact reproduction.
- Never merge distinct biological arms or studies unless the source metadata justifies it explicitly.
- Never silently replace an unresolved paper definition with an arbitrary proxy and present it as canonical.
- Never use icons or emojis in project documentation or outputs.
- Never depend on data or code that lives outside this project root for routine execution.
- Never rely on unstated user memory or prior chat history; if it matters, it must be written inside this repository.

## Scientific Attitude Required

The correct working style for this repository is:

- rigorous,
- conservative,
- provenance-aware,
- text-and-code aligned,
- hostile to hallucination,
- explicit about uncertainty,
- precise about what is exact, proxied, unresolved, or absent.

If you find a discrepancy between:

- the paper text,
- the supplement,
- local author-adjacent code,
- public upstream code,
- or current project code,

do not hide it. Surface it, classify it, and record it.

## Current Global Status

At the time of this handoff, the repository is useful, real, and scientifically nontrivial, but it is not yet a full reproduction of the paper.

What is already strong:

- isolated Python project with a functioning `.venv`,
- runnable CLI and `run.sh`,
- real-data `Th17` ingestion and preprocessing using local public assets,
- recovered `GPL8321` annotation integrated conservatively,
- arm-aware separation of Yosef and Wu biological branches,
- machine-readable primitive-definition fidelity tracking,
- paper-faithful canonical `relative_reprogrammability`,
- explicit downgrade of unresolved `absolute_reprogrammability` and `combined_reprogrammability`,
- deterministic outputs and tests for key implemented surfaces.

What remains unresolved or incomplete:

- operational definition of the interpolation function `S` in `PA(G)`,
- exact `absolute_reprogrammability`,
- exact `combined_reprogrammability`,
- paper-faithful `FinalNet` reconstruction for the Yosef Th17 block,
- `E. coli` validated network reproduction,
- full CellNet landscape reproduction,
- benchmark-complete MILS validation,
- benchmark-complete Boolean-network reproduction,
- long-horizon cellular automaton reproduction at paper scale.

## Self-Containment Requirement

This project must be operable from within the repository.

### What is already self-contained

- code lives inside `src/imp_causal_paper`
- tests live inside `tests`
- processed data live inside `data/processed`
- raw recovered data live inside `data/raw`
- reference code snapshots live inside `reference`
- the project contains its own `.venv`
- top-level orchestration exists in `run.sh`

### What still deserves review for stricter isolation

`run.sh` currently creates the environment with:

```bash
PYENV_VERSION=3.11.10 pyenv exec python -m venv "$VENV_DIR"
```

Implication:

- if `.venv` already exists, normal usage is effectively project-local;
- but initial environment creation currently assumes an external `pyenv`-managed Python 3.11.10 is available.

This is the main remaining infrastructure caveat against a purist interpretation of "depends on nothing outside the folder".

Recommended future hardening:

- make bootstrap prefer a local `python3.11` if available,
- fail with a precise message if Python 3.11 is absent,
- avoid requiring hidden shell tooling beyond a standard Python interpreter.

Do not change this casually unless you verify that bootstrap remains deterministic and reproducible.

## Repository Structure

### Root files

- `README.md`: user-facing project summary and current reproduction boundary
- `EXACT_REPRODUCTION_PLAN.md`: strategic source-of-truth plan
- `REPRODUCTION_LEDGER.md`: provenance ledger; only confirmed facts belong there
- `definition_fidelity.json`: machine-readable exactness boundary for primitive definitions
- `imp-results.md`: paper-vs-implementation scientific audit
- `run.sh`: top-level orchestrator
- `pyproject.toml`: packaging and dependencies
- `requirements.txt`: Python requirements used by `run.sh`

### Source tree

- `src/imp_causal_paper/complexity.py`: BDM-related complexity functionality
- `src/imp_causal_paper/perturbation.py`: spectra, signature, and InfoRank
- `src/imp_causal_paper/reprogrammability.py`: relative, absolute, and combined programmability surfaces and proxy variants
- `src/imp_causal_paper/mils.py`: MILS-like graph reduction logic
- `src/imp_causal_paper/marpa.py`: MARPA-like graph construction logic
- `src/imp_causal_paper/causal_reconstruction.py`: cellular automaton reconstruction logic
- `src/imp_causal_paper/boolean_network.py`: Boolean-network attractor logic
- `src/imp_causal_paper/bio_ingestion.py`: the largest biological preprocessing layer; this is central
- `src/imp_causal_paper/experiments.py`: experiment runners and output payload generation
- `src/imp_causal_paper/cli.py`: CLI entry point

### Tests

- `tests/test_complexity_and_graphs.py`: synthetic/graph/primitive fidelity tests
- `tests/test_bio_ingestion.py`: real-data Th17 ingestion tests

### Data

- `data/raw`: authoritative local copies of recovered public assets
- `data/processed`: deterministic project-local outputs

### References

- `reference/algodyn`: author-adjacent R implementation surface
- `reference/CellNet`: recovered CellNet codebase
- `reference/PACNet`: recovered PACNet assets and README provenance

## How To Run The Project

Use only the repository-local runner unless you have a strong reason not to.

### Standard commands

```bash
./run.sh setup
./run.sh test
./run.sh th17
./run.sh graphs
./run.sh ca
./run.sh boolean
./run.sh all
```

### What they do

- `setup`: creates/updates `.venv`, installs dependencies, installs package editable
- `test`: runs the full pytest suite
- `th17`: parses and materializes local Th17 raw assets into `data/processed/th17`
- `graphs`: runs graph perturbation, MILS, MARPA, and reprogrammability outputs into `results/graphs`
- `ca`: runs cellular automaton reconstruction outputs into `results/ca`
- `boolean`: runs Boolean-network outputs into `results/boolean`
- `all`: runs `graphs`, `ca`, and `boolean`

### Direct CLI

Equivalent direct entry point:

```bash
.venv/bin/python -m imp_causal_paper.cli <command> ...
```

The supported commands in `cli.py` are:

- `graphs`
- `ca`
- `boolean`
- `th17-prepare`
- `all`

## Relationship Between Local Data And The Target Paper

This section matters. A future agent must know exactly why each local asset exists and how it relates to the paper.

### Th17 block

The paper's Th17 biological provenance anchor is `Yosef et al. 2013`.

Recovered local raw assets:

- `data/raw/th17_geo/GSE43948_series_matrix.txt.gz`
- `data/raw/th17_geo/GSE43949_series_matrix.txt.gz`
- `data/raw/th17_geo/GSE43955_series_matrix.txt.gz`
- `data/raw/th17_geo/GSE43956_series_matrix.txt.gz`
- `data/raw/th17_geo/GSE43957_series_matrix.txt.gz`
- `data/raw/th17_geo/GSE43969_series_matrix.txt.gz`
- `data/raw/th17_geo_supp/GSE43948_RAW.tar`
- `data/raw/th17_geo_supp/GSE43956_RAW.tar`
- `data/raw/th17_geo_supp/GSE43957_RAW.tar`
- file lists and manifests for supplementary bundles

Recovered interpretation:

- `GSE43948`: RNA-seq perturbation screen related to the Yosef Th17 network work
- `GSE43949`: ChIP-seq metadata-only series related to Yosef
- `GSE43955`: GPL8321 microarray Th17 differentiation time course
- `GSE43969`: GPL8321 microarray IL23R KO vs WT Th17 time course
- `GSE43956`: Wu et al. SGK1 knockout arm, not Yosef network reconstruction proper
- `GSE43957`: Wu et al. NaCl arm, not Yosef network reconstruction proper
- `GSE43970`: mixed SuperSeries spanning both Yosef and Wu material

Critical biological law:

- Yosef and Wu arms must remain separated.

This is already encoded into processed outputs via fields such as:

- `study_arm`
- `source_publication`
- `biological_program`

Never collapse those arms for convenience.

### GPL8321 platform annotation

Recovered local raw asset:

- `data/raw/platforms/GPL8321_full.txt`

Processed artifact:

- `data/processed/th17/GPL8321_annotation/probe_annotation.csv`

Why it matters:

- it enables conservative gene/probe support grounding for microarray evidence,
- it moved candidate support from hand-wavy probe bookkeeping to platform-backed mapping,
- it provided support for paper-relevant candidates such as `STAT6`, `TRIM24`, and alias-aware `TCFEB`.

Mapping policy already adopted:

- accept exact support when the platform row declares the exact symbol,
- accept alias support only when the platform itself declares the alias,
- do not import external heuristic aliasing unless explicitly recorded and justified.

### DREAM5 / E. coli block

Local raw assets:

- `data/raw/dream5/manual_download/*`

These include:

- `ecoli_data.tsv`
- `ecoli_experiments.tsv`
- `ecoli_gene_names.tsv`
- `ecoli_tf_names.tsv`

Interpretation:

- these are legitimate DREAM5-related upstream files,
- but they should currently be treated as original expression-side compendia, not automatically as the exact final challenge-distributed evaluation surface used by every downstream paper step.

This is enough to begin expression-side preprocessing and provenance work.
It is not yet enough to claim the exact validated network object analyzed in the Zenil paper.

### CellNet / PACNet block

Local raw assets:

- `data/raw/cellnet/Hs_expTrain_Jun-20-2017.rda`
- `data/raw/cellnet/Hs_stTrain_Jun-20-2017.rda`
- `data/raw/cellnet/cnProc_HS_RS_Jun_20_2017.rda`
- `data/raw/cellnet/cnProc_RS_hs_Oct_25_2016.rda`

Local reference code:

- `reference/CellNet`
- `reference/PACNet`

Interpretation:

- the CellNet-family recovery path is real and materially useful,
- but exact paper-equivalent cell-type landscape reconstruction still requires more careful verification of which objects correspond to the paper's reported network set and how the complexity-programmability coordinates were derived.

## Processed Th17 Outputs And What They Mean

These are already high-value assets. A new agent should not redo them blindly.

### Cohort layer

Important processed directories:

- `data/processed/th17/yosef_th17_network_cohort`
- `data/processed/th17/wu_sgk1_pathogenicity_cohort`

Purpose:

- explicit branch separation,
- deterministic combined sample metadata for each biological arm.

### Design layer

Important directory:

- `data/processed/th17/yosef_th17_network_design`

Purpose:

- creates a unified Yosef-only design table across:
  - `GSE43948`
  - `GSE43949`
  - `GSE43955`
  - `GSE43969`
- preserves modality separation:
  - RNA-seq
  - microarray
  - ChIP-seq
- materializes exact `48.0 hr` subsets conservatively.

### Evidence layer

Important directory:

- `data/processed/th17/yosef_th17_network_evidence`

Purpose:

- perturbation-target matrices,
- target-minus-control effects,
- target log2 fold changes,
- late-time microarray subsets,
- exact `48.0 hr` microarray subsets.

This is not a final network reconstruction.
It is a paper-facing evidence table layer.

### Regulator summary layer

Important directory:

- `data/processed/th17/yosef_th17_network_regulator_summary`

Purpose:

- compresses evidence to candidate-facing summaries,
- ties RNA-seq perturbation evidence to GPL8321 late-time evidence,
- preserves conservative candidate support status.

### Ranking-input layer

Important directory:

- `data/processed/th17/yosef_th17_network_ranking_input`

Purpose:

- exposes the current strongest regulator-level paper-facing features,
- separates:
  - strict exact `48.0 hr` proxies
  - broad late-time proxies

This distinction is essential.
Do not merge them into a single terminal-state notion.

### Prioritization layer

Important directory:

- `data/processed/th17/yosef_th17_network_prioritization`

Purpose:

- conservative support audit over recovered features,
- not exact paper `FinalNet`,
- not exact paper final ranking procedure.

Current high-level result:

- recovered real-data proxies do not uniquely isolate `STAT6`, `TCFEB`, and `TRIM24` under simple aggregation,
- but they do provide partial support patterns,
- which means the bottleneck is now ranking-procedure reconstruction, not raw data discovery.

## What Is Correctly Done

The following work is materially sound and should be preserved unless new evidence disproves it.

### 1. Provenance discipline

- Real raw data were recovered and stored locally.
- Processed outputs are deterministic and project-local.
- The ledger and audit files separate confirmed fact from unresolved inference.

### 2. Yosef/Wu separation

- This is correct and necessary.
- It should not be relaxed.

### 3. GPL8321 recovery

- Recovering the full platform text export and using platform-native aliases was the correct move.
- This materially improved scientific credibility.

### 4. Primitive fidelity classification

- `info_spectra`, `info_signature`, and `inforank` are tracked against recovered `algodyn`.
- canonical `relative_reprogrammability` now follows the recovered supplement.
- the conflicting `algodyn` formula is preserved only as an audit variant.

This is exactly the right pattern: canonical surface plus explicit discrepancy audit.

### 5. Stronger treatment of unresolved `PA(G)`

This was an important correction.

Current canonical stance:

- `absolute_reprogrammability` is unresolved
- `combined_reprogrammability` is unresolved

Current proxy stance:

- trapezoid-based absolute and Euclidean combined formulas are preserved only as explicit noncanonical proxy audit variants

This is more scientifically honest than returning plausible numbers without provenance.

## What Is Stuck

These are the key stuck points.

### 1. `PA(G)` interpolation function `S`

Paper-level state:

- the supplement defines `PA(G)` symbolically with an interpolation function `S`,
- but no operational definition of `S` has yet been recovered.

Author-adjacent code state:

- upstream `algodyn` history contained only stub placeholder files for absolute and total reprogrammability,
- those stubs were later removed,
- no operational author-adjacent implementation has been recovered.

Conclusion:

- do not invent canonical `PA(G)`,
- do not pretend the current proxy is exact.

### 2. Exact Th17 `FinalNet`

Current state:

- raw data: largely recovered
- preprocessing: substantial
- candidate-facing evidence: substantial
- exact final ranking / network reconstruction used in the paper: still unresolved

The likely bottleneck is no longer data acquisition.
The bottleneck is methodological reconstruction.

### 3. `E. coli` validated network object

Current state:

- DREAM5-related expression assets exist,
- exact validated network object used by the paper is still not confirmed locally.

### 4. CellNet landscape object set

Current state:

- useful CellNet/PACNet assets exist locally,
- but the exact object set and coordinate-generation path for the paper's landscape are not yet fully closed.

## Recommended Strategy From This Point

Do not restart the project. Continue from the strongest verified boundary.

### Priority 1: Preserve the integrity boundary

Before adding new scientific outputs:

- read `definition_fidelity.json`
- read `REPRODUCTION_LEDGER.md`
- read `imp-results.md`

Do not weaken those boundaries for convenience.

### Priority 2: Th17 network reconstruction

This is the most defensible next major block because the raw and processed inputs are already strong.

Suggested next steps:

1. reconstruct the paper's information-spectrum workflow on the Yosef-only arm,
2. determine exactly what graph object the paper calls the Th17 network at each time point,
3. identify whether the paper uses prebuilt networks, inferred networks, or a filtered regulatory scaffold before perturbation analysis,
4. reconstruct the exact positive/negative partition logic used for enrichment and candidate extraction,
5. determine how the paper's `FinalNet` was defined operationally.

Strong hypothesis:

- the missing piece is not another GEO accession,
- the missing piece is the graph-construction and ranking procedure connecting recovered expression evidence to the final perturbation calculus.

### Priority 3: `E. coli`

Suggested next steps:

1. identify the exact Marbach-derived validated TF network object referenced by the Zenil paper,
2. recover it locally,
3. connect it to the perturbation calculus code path,
4. rebuild the enrichment side against `GO`, `KEGG`, and `EcoCyc`.

### Priority 4: CellNet landscape

Suggested next steps:

1. inspect the locally recovered `cnProc` objects and training assets in detail,
2. determine which cell-type network objects correspond to the paper's 16 human cell lines,
3. reconstruct the complexity-programmability coordinate generation step,
4. only then attempt the landscape.

### Priority 5: Synthetic blocks after biological progress

The synthetic blocks are useful, but the biggest scientific value now lies in biological reconstruction.
Do not spend disproportionate effort polishing toy graph panels while the main biological blocks remain incomplete.

## Exact Primitive Status

This summary is critical.

### Exact enough to use canonically now

- `info_spectra`
- `info_signature`
- `inforank`
- `relative_reprogrammability` according to the recovered supplement

### Preserved only as audit variants

- `relative_reprogrammability_algodyn_reference`
- `absolute_reprogrammability_trapezoid_proxy`
- `combined_reprogrammability_trapezoid_proxy`

### Canonically unresolved

- `absolute_reprogrammability`
- `combined_reprogrammability`

Never blur these categories.

## How The Current Tests Should Be Interpreted

The tests are valuable, but they do not imply full paper reproduction.

What they do verify:

- graph signature ordering,
- InfoRank semantics,
- current primitive-definition boundary,
- graph summary metadata statuses,
- real-data Th17 ingestion and derived artifact structure,
- CLI generation of processed outputs.

What they do not verify:

- full paper-equivalent biological conclusions,
- exact E. coli reproduction,
- exact CellNet landscape,
- exact `FinalNet`,
- exact `PA(G)`.

## Development Rules For Future Changes

### When editing code

- preserve deterministic behavior,
- preserve provenance fields,
- prefer explicit status fields over hidden assumptions,
- keep paper-faithful and proxy variants clearly separated.

### When editing docs

- never overstate exactness,
- record unresolved items explicitly,
- update the ledger only with confirmed facts,
- update the audit if any scientific status changes materially.

### When adding new data

- store under `data/raw/...`,
- record origin precisely,
- prefer original filenames where possible,
- add or update a manifest if the source is an archive or a recovered bundle.

### When adding processed outputs

- place under `data/processed/...` if they are preprocessing products,
- place under `results/...` if they are experiment outputs,
- keep outputs deterministic,
- avoid writing ephemeral or user-specific paths into scientific artifacts.

### When adding tests

- no mocks,
- prefer real-data tests if the data are already local,
- use focused deterministic assertions,
- do not add ornamental tests that merely restate the implementation.

## Suggested Investigation Checklist

Use this as a practical continuation queue.

### Th17

- inspect `bio_ingestion.py` function by function
- identify the current graph-construction gap
- trace every paper Th17 claim back to a missing or present local artifact
- determine whether enrichment in the paper operates on regulators, genes, or network neighborhoods
- reconstruct the exact meaning of `FinalNet`

### `PA(G)`

- search for stronger source material beyond the currently recovered supplement
- inspect archived paper versions if they can be brought inside the project
- inspect talks, notebooks, author repositories, or historical snapshots only if they can be locally archived and cited
- do not promote any new formula to canonical unless its provenance is strong

### `E. coli`

- resolve the exact network source object
- determine whether the paper used a DREAM5-derived object directly or a Marbach validated TF network exported elsewhere
- build a local provenance chain before computing enrichment

### CellNet

- inspect the local `cnProc` and training objects
- identify exact network-bearing objects
- verify whether the recovered objects are sufficient for the complexity-programmability map without remote S3 access

## Things That Need Review

These are not necessarily wrong, but they deserve future scrutiny.

### 1. Infrastructure bootstrap purity

As noted earlier, `run.sh` still assumes `pyenv` for initial `.venv` creation.

### 2. Synthetic graph block

The graph experiments are useful but still small and qualitatively scoped.
Keep them honest.

### 3. MILS tie handling

The current implementation is useful, but the paper's deterministic set-removal treatment under ties is not yet reproduced.

### 4. Cellular automaton block

The current CA block demonstrates row-order recovery on a toy example, but not the paper's full scale, rule set, or robustness regime.

### 5. Boolean-network block

The current Boolean block is a narrow example, not the exhaustive 5-node paper program.

## Minimal Reading Order For A New Agent

If you have only one hour to orient yourself, do this in order:

1. read this file
2. read `definition_fidelity.json`
3. read `REPRODUCTION_LEDGER.md`
4. read `imp-results.md`
5. read `README.md`
6. inspect `src/imp_causal_paper/bio_ingestion.py`
7. inspect `src/imp_causal_paper/reprogrammability.py`
8. run:

```bash
./run.sh test
./run.sh th17
./run.sh graphs
```

9. inspect:

- `data/processed/th17/yosef_th17_network_design`
- `data/processed/th17/yosef_th17_network_evidence`
- `data/processed/th17/yosef_th17_network_prioritization`
- `results/graphs/summary.json`

## Final Instruction To The Next Agent

Continue the project with discipline.

Do not restart from toy assumptions.
Do not erase provenance boundaries.
Do not simplify away the unresolved pieces.

The repository already contains real scientific progress:

- real biological data recovery,
- real preprocessing,
- real author-adjacent code comparison,
- real definition-fidelity tracking,
- real evidence about what is and is not yet exact.

Your job is to extend that progress without corrupting it.

When in doubt:

- choose the more conservative claim,
- choose the more explicit provenance record,
- choose the implementation that makes uncertainty visible,
- and keep the project self-contained.
