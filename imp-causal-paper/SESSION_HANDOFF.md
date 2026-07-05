# Session Handoff: All Figures Implemented

## Branch: clean
## Date: 2026-07-05
## Tests: 28 pass

---

## COMPLETED THIS SESSION

### Fig 3 — CA Reconstruction (CORE of the paper)
Two methods implemented in `causal_reconstruction.py`:
- **`reconstruct_min_complexity()`** — Panel A: brute-force all 9! permutations, pick minimum-BDM arrangement. Limited to ≤9 rows.
- **`reconstruct_by_rule_inference()`** — Panel B: infer ECA rule from all row pairs, build forward transition chain. Scales to any size.
- Script: `scripts/run_ca_reconstruction.py` — generates Panel A and B for 10 rules.

**BACKGROUND TASK MAY STILL BE RUNNING**: Panel A brute-force (9! × BDM per rule).
Check: `ls plots/ca/fig3a_reconstruction.png`
If not complete: `source .venv/bin/activate && python scripts/run_ca_reconstruction.py`

### Fig 3C-H — CA Sensitivity (from previous run, still valid)
- `plots/ca/fig3a_eca_256_complexity` — all 256 rules BDM landscape
- `plots/ca/fig3b_spacetime_selected` — space-time diagrams
- `plots/ca/fig3c_sensitivity_all256` — early/inter/late boxplots
- `plots/ca/fig3c_row_perturbation` — row-deletion profiles
- `plots/ca/fig3h_individual_sensitivity` — per-rule sensitivity

### Fig 4 — Boolean Networks
- `plots/boolean/fig4ac_complexity_sweep` — MILS/MARPA/ER
- `plots/boolean/fig4eg_attractor_perturbation` — K8/ER/SF attractor counts
- `plots/boolean/fig4_mean_delta_attractors` — mean delta summary

### Fig 5 — Biological Applications
- `plots/th17/th17_spectra` — Fig 5B-D: EarlyNet/IntermediateNet/FinalNet spectra
- `plots/th17/th17_gene_heatmap` — Fig 5F: top 40 genes heatmap across time points
- `plots/cellnet/cellnet_16ct_landscape` — Fig 5G: 16 cell types, combined reprogrammability
- E. coli enrichment data: `data/processed/ecoli/`

### Notebook
- Section 7 rewritten: full reconstruction method (Panel A + B) with step-by-step demo
- Sections 13-15 added: E. coli, mmc8 phase transition, CellNet landscape
- Summary table updated: all components marked as implemented

### Data computed
- `data/processed/cellnet_16ct/cellnet_landscape_data.csv` — 16 cell types, full BDM + perturbation
- `data/processed/ca/eca_256_complexity.csv` — all 256 rules
- `data/processed/boolean/graph_complexity_sweep.csv`, `boolean_attractor_perturbation.csv`

---

## KEY FINDINGS

1. **CA Reconstruction**: Rule inference method correctly identifies generating rules and chains rows. Brute-force min-BDM gives perfect reconstruction for structured rules (254: ρ=1).
2. **CellNet landscape**: Most cell types cluster at combined Pr ≈ 1.0. Macrophage (0.21) and kidney (0.40) are outliers.
3. **Th17 spectra**: Pr increases from 0.040 (EarlyNet) to 0.460 (FinalNet) — matches paper's differentiation trajectory.
4. **Sensitivity**: Early CA rows have higher normalised δ than late rows (0.401 vs 0.379) across all 256 rules.

---

## Key File Paths
- Reconstruction methods: `src/imp_causal_paper/causal_reconstruction.py`
- Reconstruction script: `scripts/run_ca_reconstruction.py`
- All plot scripts: `scripts/plot_th17_spectra.py`, `plot_th17_heatmap.py`, `plot_cellnet_16ct_landscape.py`
- CA suite: `scripts/run_ca_suite.py`
- Boolean experiments: `scripts/run_boolean_experiments.py`
- Notebook: `notebooks/paper_walkthrough.ipynb`
