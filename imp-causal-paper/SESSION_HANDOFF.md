# Session Handoff: Deblocking CellNet + DREAM5 Gold Standard

## Branch: clean
## Date: 2026-07-03
## Last verified: 28 tests pass. Latest commit: ab218fd
## Git log --oneline -5 to confirm on resume.

---

## Full Reproduction Status

### DONE (three core paper sections)
| Section | Status |
|---------|--------|
| Th17 Yosef BDM perturbation (EarlyNet/IntermediateNet/FinalNet) | ✅ 97/97/99% sign agreement, per-network ordering |
| E. coli RegulonDB BDM perturbation | ✅ 949 nodes, C subset, version gap documented |
| Boolean exhaustive mmc8 / Figure 4D | ✅ Phase-transition reproduced, crossover at 14 edges |

### REMAINING (two hard blockers + one quick fix)
| Item | Blocker type |
|------|-------------|
| CellNet cell-type landscape | External — need trained cnProc objects |
| DREAM5 gold standard (MILS benchmark) | External — need D5C4_goldstandard.zip from Synapse |
| Notebook Section 10 update | Quick fix, ~15 min, no blocker |

---

## Hard Blocker 1 — CellNet cnProc Trained Objects

### What we need
Prebuilt trained CellNet model objects (`cnProc_HS_RS_Jun-20-2017.rda` or equivalent)
encoding GRN scores for 15–16 human cell types. These power the complexity–programmability
cell-type landscape in the Zenil paper.

### What we already have locally
- `reference/CellNet/` — CellNet R package source code
- `data/raw/cellnet/Hs_stTrain_Jun-20-2017.rda` — training metadata (1003×23, 15 cell types)
- `data/raw/cellnet/Hs_expTrain_Jun-20-2017.rda` — training expression matrix (34934×1003)

### Why blocked
Original S3 links in CellNet README return `InvalidObjectState` (AWS DEEP_ARCHIVE).
Cannot restore without bucket owner credentials.

### Resources the user found — evaluate in this priority order

**Priority 1 — PACNet Zenodo release**
URL: https://doi.org/10.5281/zenodo.18857326
Action: Fetch the Zenodo API to list ALL files in this release.
```bash
curl -s "https://zenodo.org/api/records/18857326" | python3 -m json.tool | grep '"key"'
```
If any file is named `cnProc_*.rda` or similar → download it directly, it is the trained object.
If only expression/metadata files → Zenodo does NOT ship trained objects, escalate to Priority 2.

**Priority 2 — Kaggle dataset**
URL: https://www.kaggle.com/datasets/johncapocyan/cellnet-beta-version
Use Kaggle CLI: `kaggle datasets download johncapocyan/cellnet-beta-version --dry-run`
to inspect file list BEFORE downloading. If it contains `cnProc_*.rda` → download.
If it is expression matrices only → skip.

**Priority 3 — Email Cahan lab**
If Priority 1 and 2 both lack trained objects, email Patrick Cahan (pcahan1@jhmi.edu)
requesting `cnProc_HS_RS_Jun-20-2017.rda`. Single email, high chance of success.

**Priority 4 — Retrain from local data**
We already have training expression + metadata. Can retrain CellNet in R using
`reference/CellNet/` code. Produces equivalent (not bit-identical) model.
Use only if all above fail.

### NOT useful
- https://cellnet.updatestar.com/ — Windows network management software, completely wrong.

---

## Hard Blocker 2 — DREAM5 Gold Standard (MILS Benchmark)

### What we need
`D5C4_goldstandard.zip` from Synapse (syn4564722) — the true regulatory network
used as ground truth in the DREAM5 E. coli network inference challenge.

### What we already have locally
Path: `data/raw/dream5/manual_download/`
Files present: expression data + gene/TF name lists (ecoli, yeast, saureus)
Files ABSENT: gold standard network, challenge templates

### Why actually needed
Clarification needed: The MILS benchmark in the Zenil paper may or may not
use DREAM5 data. The DREAM5 gap was originally conflated with the E. coli
network source (now corrected to RegulonDB). FIRST ACTION next session:
read the Zenil paper supplement MILS section to confirm whether DREAM5
gold standard is actually required for MILS validation specifically.
If not needed → close this gap entirely.

### If DREAM5 gold standard IS needed
1. Register free account at synapse.org (15 min)
2. Download: `synapse get syn4564722` (D5C4_goldstandard.zip)

### arboreto fixed_scoring.py assessment (user found this)
URL: https://github.com/aertslab/arboreto/blob/master/notebooks/dream5/fixed_scoring.py
This is DREAM5 network inference SCORING code (computes AUROC/AUPR of predicted
networks against gold standard). It is NOT a substitute for the gold standard data.
It IS useful as reference code once we have the gold standard, to understand
the scoring methodology. Do not confuse for data.

---

## Quick Fix (do anytime, ~15 min)

### Notebook Section 10 — EarlyNet ordering
`notebooks/paper_walkthrough.ipynb` Section 10 still shows old EarlyNet result
(7% sign agreement with alphabetical ordering). Update to:
- in_degree_desc ordering gives 97% for EarlyNet
- Brief explanation of ordering sensitivity
- Corrected cross-validation table (97/97/99%)

---

## Exact Next Session Action Plan

1. Run `git log --oneline -3` to confirm clean state
2. Run `pytest -q --tb=no` to confirm 28 tests pass
3. Fetch Zenodo PACNet file list (curl command above) → decide Priority 1/2/3/4
4. Read Zenil paper MILS supplement to confirm DREAM5 gold standard need
5. If MILS does NOT need DREAM5 → close that gap, update REPRODUCTION_LEDGER.md
6. If MILS DOES need DREAM5 → register Synapse, download syn4564722
7. Update notebook Section 10

---

## Key File Paths (quick reference)
- Ledger: `imp-causal-paper/REPRODUCTION_LEDGER.md`
- Notebook: `imp-causal-paper/notebooks/paper_walkthrough.ipynb`
- CellNet local: `imp-causal-paper/data/raw/cellnet/`
- DREAM5 local: `imp-causal-paper/data/raw/dream5/manual_download/`
- E. coli results: `imp-causal-paper/data/processed/ecoli/`
- Yosef results: `imp-causal-paper/data/processed/th17/yosef_perturbation/`
- mmc8 results: `imp-causal-paper/data/processed/boolean_exhaustive/`
