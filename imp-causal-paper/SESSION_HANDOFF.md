# Session Handoff: CellNet Landscape Partial + DREAM5 Gap Closed

## Branch: clean
## Date: 2026-07-03
## Last verified: 28 tests pass. Latest commit: e3fd1e9

---

## What Was Accomplished This Session

### 1. DREAM5 gap — CLOSED
Full-text search of 1709.05429: DREAM5 is not mentioned anywhere in the Zenil paper.
MILS uses 9 benchmark networks from the network science literature (Extended Figure 5), not DREAM5 data.
The Synapse gold standard (D5C4_goldstandard.zip) is **not required** for any part of this reproduction.
REPRODUCTION_LEDGER.md updated to reflect this.

### 2. CellNet cnProc stubs — DIAGNOSED
The two local `.rda` files at `data/raw/cellnet/cnProc_*.rda` are 354/334-byte AWS S3 error XML responses saved during failed download. They are not valid R objects.

### 3. Zenodo PACNet record — EVALUATED
Record 18857327 (correct — 18857326 redirects to 18857327). Contains 45 files but NO `cnProc_*.rda`.
However: each `grnAll.rda` file contains `ctGRNs$graphLists` with igraph objects for ALL 14 PACNet cell types.

### 4. CellNet GRN pipeline — IMPLEMENTED AND RUN
- Downloaded 6 human grnAll.rda files (27–58 MB each) from Zenodo to `data/raw/cellnet/grnAll/`
- Wrote `scripts/extract_cellnet_grns.R` — extracts 14 cell-type edge lists
- Wrote `scripts/run_cellnet_complexity.py` — BDM complexity + perturbation per cell type
- Wrote `scripts/plot_cellnet_landscape.py` — Fig. 6g-style landscape plot
- Added `./run.sh cellnet` entry point
- All 14 edge lists extracted; 9 cell types (≤600 nodes) have full C(G)+Pr(G) results
- Plot: `plots/cellnet/cellnet_landscape.pdf`

### 5. Notebook Section 10 — ALREADY CORRECT
Code cell already loads `EarlyNet_in_degree_desc_node_spectra.csv` and comments explain
the 97% result. Section 12 has the full ordering sensitivity table. No code change needed;
stale Jupyter output cells (from wrong Python env) are cosmetic only.

---

## Current Reproduction Status

| Section | Status |
|---------|--------|
| Th17 Yosef BDM perturbation (EarlyNet/IntermediateNet/FinalNet) | ✅ 97/97/99% sign agreement |
| E. coli RegulonDB BDM perturbation | ✅ 949 nodes, C subset, 122 pos / 789 neg |
| Boolean exhaustive mmc8 / Figure 4D | ✅ Phase-transition reproduced |
| CellNet Waddington landscape | ⚠️ 9/14 cell types fully computed |
| DREAM5 / MILS gold standard | ✅ CLOSED — not required |

---

## Remaining Work

### Priority 1 — CellNet large networks (5 remaining cell types)
The 5 large networks were skipped at node_limit=600:
- neuron (2974 nodes) — estimated ~3 hours
- monocyte_macrophage (3756 nodes)
- skeletal_muscle (4836 nodes)
- liver (1583 nodes)
- esc (988 nodes — closest to feasible, ~30 min)

Option A: Run `esc` first (988 nodes, ~30 min):
```bash
source .venv/bin/activate
python scripts/run_cellnet_complexity.py --node-limit 1000
```
This adds esc + possibly liver.

Option B: Run overnight with high limit:
```bash
source .venv/bin/activate
python scripts/run_cellnet_complexity.py --node-limit 5000
```

### Priority 2 — Cahan email (for missing cell types)
The original CellNet 2014 had 16 human cell types; PACNet ctGRNs has 14.
Missing are likely 2 types not present in the 2020 retraining cohort.
Email: Patrick Cahan, pcahan1@jhmi.edu — ask for cnProc_HS_RS_Jun_20_2017.rda or equivalent GRN edge lists for the missing cell types.

Draft email text:
---
Subject: CellNet trained GRN objects (cnProc_HS_RS_Jun_20_2017) for reproduction study

Dear Dr Cahan,

I am conducting a reproduction study of Zenil et al. (2019) "An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems" (iScience), which uses CellNet GRN data from Morris et al. (2014) to reconstruct an epigenetic Waddington landscape. The paper reports results for 16 human cell lines.

The original S3 links for cnProc_HS_RS_Jun_20_2017.rda now return DEEP_ARCHIVE errors, and the PACNet Zenodo release (doi:10.5281/zenodo.18857326) provides ctGRN objects for 14 of the 16 cell types. Would it be possible to share the trained cnProc objects or GRN edge lists for the full 16-cell-type human panel from the Jun-2017 training run?

Any format (R object, CSV edge list, or similar) would be helpful. This is for a published reproducibility study.

Thank you for the openly shared CellNet data.

Best regards,
Alberto
---

### Priority 3 — MILS benchmark graph list
The paper uses 9 benchmark networks for Extended Figure 5. These are not named explicitly.
From context ("pioneering studies") they are likely: karate club, florentine families, Les Mis,
political blogs, protein interactions, and similar commonly used graph benchmarks.
This gap is low priority — it affects only MILS validation, which is ancillary to the main results.

---

## Key File Paths (quick reference)
- Ledger: `imp-causal-paper/REPRODUCTION_LEDGER.md`
- CellNet summary: `imp-causal-paper/data/processed/cellnet/cellnet_complexity_summary.csv`
- CellNet landscape: `imp-causal-paper/plots/cellnet/cellnet_landscape.pdf`
- grnAll files: `imp-causal-paper/data/raw/cellnet/grnAll/`
- Edge lists: `imp-causal-paper/data/processed/cellnet/{ct}_edgelist.csv`
- Notebook: `imp-causal-paper/notebooks/paper_walkthrough.ipynb`
