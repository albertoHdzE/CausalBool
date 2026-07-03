# Session Handoff: E. coli completed; ordering integrated; three priorities remaining

## Branch: clean
## Date: 2026-07-03
## Last verified state: 28 tests pass, all run.sh commands clean
## Latest commit: see `git log --oneline -3`

## What Was Accomplished This Session

### 1. Committed prior-session work (DONE)
- Committed all staged files from previous session: notebooks, scripts, yosef
  perturbation data, mmc8 outputs, EarlyNet in_degree_desc results.
- Commit `6b8f787`: "Resolve EarlyNet BDM ordering dependency; add mmc8 parser
  and ordering invariance documentation"

### 2. Perturbation pipeline updated with per-network ordering (DONE)
- `perturbation.py` `spectra()` now accepts `nodelist` parameter.
  When provided, builds adjacency matrix once with fixed ordering and uses
  `np.delete` per node removal (matching algodyn's deletion semantics).
- `run_yosef_perturbation.py` defines `NETWORK_ORDERINGS`:
  - EarlyNet → `in_degree_desc` (97% sign agreement)
  - IntermediateNet → `sorted` (97%)
  - FinalNet → `sorted` (99%)
- Commit `7016486`: "Integrate per-network node ordering into perturbation pipeline"

### 3. REPRODUCTION_LEDGER.md corrected (DONE)
- Cross-validation section updated: EarlyNet root cause is ordering (NOT BDM
  implementation difference). Corrected conclusion recorded.

### 4. RegulonDB E. coli TF network downloaded and analysed (DONE)
- RegulonDB 14.5 (2026-07-03) downloaded via GraphQL API.
  Files: `data/raw/regulondb/NetworkRegulatorGene.txt` (+ ConfGene, TF-RISet).
- Canonical subset: Confirmed (C) only — 949 nodes, 1148 edges.
- BDM perturbation completed in ~186s:
  - Positive: 122, Neutral: 38, Negative: 789
  - Relative reprogrammability: 0.2437
  - Top positive: ArgR, CRP, MarA, Ada, AraC (all global TFs — expected)
  - Top negative: crr, csgD, crp (embedded/target genes)
- Version gap: paper used ~RegulonDB 9.x (2018); 14.5 is best available proxy.
  No ground-truth supplementary data for E. coli (unlike Th17).
- Scripts: `parse_ecoli_network.py`, `run_ecoli_perturbation.py`.
  Entry point: `./run.sh ecoli [C|CS|all]`
- Commits `3cfca97` + follow-on for perturbation output.

## Exact Next Actions

### 1. Commit E. coli perturbation output
- Force-add and commit `data/processed/ecoli/` (spectra, signature, summary CSVs).
- These are gitignored by default; use `git add -f`.

### 2. Update notebook Section 10 (cross-validation)
- `notebooks/paper_walkthrough.ipynb` Section 10 currently shows the old
  EarlyNet results (7% sign agreement with alphabetical ordering).
- Update to show: in_degree_desc ordering gives 97% for EarlyNet.
- Add a brief note on ordering sensitivity.

### 3. Boolean network reproduction (mmc8 / Figure 4D)
- `data/processed/boolean_exhaustive/mmc8_summary.json` has the parsed data.
- The paper's Figure 4D shows distributions of positive/negative gene counts
  vs edge density for 5-node exhaustive Boolean graphs.
- Need to: load mmc8 data, compute classification fractions per edge count,
  reproduce the phase-transition plot (positive → negative dominance at ~12–13 edges).
- Script: `scripts/parse_mmc8.py` already generates the CSVs.
  Next step: add a plotting/analysis script for Figure 4D.

### 4. RegulonDB ordering sensitivity investigation (optional)
- For E. coli, we used alphabetical ordering (no ground truth to verify against).
- If the paper mentions specific positive/negative genes for E. coli, compare
  against our results to assess ordering correctness.
- The paper mentions GO/KEGG/EcoCyc enrichment as the validation, not specific
  gene lists, so this may not be necessary.

### 5. CellNet / cell-type landscape (longer-term)
- See REPRODUCTION_LEDGER.md for current state of CellNet asset recovery.
- Training data recovered from Zenodo (PACNet); cnProc objects in DEEP_ARCHIVE.
- Not yet started; lowest priority.

## Key Files
1. `REPRODUCTION_LEDGER.md` — authoritative provenance and protocol record
2. `scripts/run_yosef_perturbation.py` — canonical Th17 perturbation with ordering
3. `scripts/run_ecoli_perturbation.py` — E. coli perturbation
4. `data/processed/ecoli/` — E. coli BDM results (commit pending)
5. `notebooks/paper_walkthrough.ipynb` — needs Section 10 update

## Test Status
28 tests pass (`pytest -q --tb=no`).
