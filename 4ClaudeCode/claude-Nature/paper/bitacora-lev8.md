# Bitácora — BioPlan Level 8 (Execution Log)

## Entry LEV8-2026-03-17-001 — Environment Smoke Tests
**Date:** 2026-03-17  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A  

**Python**
- Interpreter: Python 3.13.12
- Venv interpreter: `/Users/alberto/Documents/projects/CausalBool/venv/bin/python`
- Imports: numpy, pandas, matplotlib OK

**Mathematica**
- CLI: `wolframscript` available
- Smoke test: `wolframscript -code "2+2"` → `4`

**Implication**
- Both Python and Mathematica execution are available for Level 8 runs.

---

## Entry LEV8-2026-03-17-002 — Paper Pipeline Run (analysis_pipeline.py)
**Date:** 2026-03-17  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A, Gate B  

**Command**
- `/Users/alberto/Documents/projects/CausalBool/venv/bin/python /Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py`

**Fix Applied Before Run**
- Updated output directory resolution to write into `figures` rather than `../figures`, which caused a PermissionError.
- File changed: [analysis_pipeline.py](file:///Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py#L437-L512)

**Console Summary**
- Loaded networks: 232 (skipped 2 non-network JSON files)
- Essentiality CSV loaded by pipeline: 31 gene entries across 4 networks
- Networks analyzed (post filters): 231
- Significant (p<0.05): 49 / 231 (21.2%)
- Mean ratio: D_bio / D_random = 0.981
- Mean z-score: -0.72
- Paired t-test p-value: 5.14e-12

**Outputs Produced**
- `figures/figure1_algorithmic_efficiency.pdf`
- `figures/figure1_algorithmic_efficiency.png`
- `figures/figure2_essentiality_prediction.pdf`
- `figures/figure2_essentiality_prediction.png`
- `figures/results_summary.csv`

**Checksums (SHA-256)**
- figure1_algorithmic_efficiency.pdf: `935e5e4dc92577499cf1c1d5588b1a9c2cdef36589e4b328884068ae2dabcdca`
- figure1_algorithmic_efficiency.png: `43ff15064930d8e7a82e78c97acb81890d88a7d10605ec178bf4bcc530eb8e96`
- figure2_essentiality_prediction.pdf: `7b4da3517c97f332bc3fd837e5cbd678c2c597902834fe9db9042958c79f818a`
- figure2_essentiality_prediction.png: `c7aedc597186c1ecc3cc3d0c1f27b47a34c9eb686b833f3b0c6e263f05cc2e7d`
- results_summary.csv: `89e8dfff35cc0632feaab7e005127e1225e13f4f1078b49f692576e0919ce772`

**Interpretation**
- The “universality” direction appears present (mean ratio < 1; strong paired p-value).
- The reported z-score sign is negative; this must be reconciled with any other artifacts that report positive z-scores (definition contract required).

**Gate A Note (action required)**
- z-score sign convention is not yet unified across artifacts. This is a hard stop for manuscript coherence until standardized.

---

## Entry LEV8-2026-03-17-003 — Extended Essentiality Analysis Run (essentiality_analysis.py)
**Date:** 2026-03-17  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A, Gate C  

**Command**
- `/Users/alberto/Documents/projects/CausalBool/venv/bin/python /Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/code/essentiality_analysis.py`

**Fix Applied Before Run**
- Updated default input/output paths to resolve relative to `figures`.
- File changed: [essentiality_analysis.py](file:///Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/code/essentiality_analysis.py#L14-L60)

**Dataset Loaded**
- `figures/essentiality_prediction_dataset.csv`
- Loaded: 642 genes from 20 networks
- Essential: 24
- Non-essential: 618

**Console Summary (as produced by script)**
- Bootstrap AUC (95% CI):
  - ΔD: 0.453 [0.357–0.555]
  - Degree: 0.511 [0.369–0.644]
  - Betweenness: 0.521 [0.398–0.635]
- Cross-validated AUC (5-fold):
  - ΔD: 0.461 ± 0.080
  - Degree: 0.406 ± 0.101
  - Betweenness: 0.364 ± 0.125
  - Combined: 0.460 ± 0.055

**Outputs Produced**
- `figures/figure2_essentiality_extended.pdf`
- `figures/figure2_essentiality_extended.png`
- `figures/supplementary_table_per_network.csv`

**Checksums (SHA-256)**
- essentiality_prediction_dataset.csv: `77799372819839ab6dda8c49e752bc0f72f07fa13de70c58918116a12b4fc008`
- figure2_essentiality_extended.pdf: `e767072ca18f4e39d86b322b1f333c914ad65df6166f1e154767e760e9fcf68a`
- figure2_essentiality_extended.png: `7e758509507ccc8d274d3b2ac52d2035ba8b4fed31f6082e7c1a58d06e65397e`
- supplementary_table_per_network.csv: `ceb8154346749e90ec88d2d9f20680fddf9a61e11d4f89a7db08e7123aae754d`

**Interpretation**
- As currently implemented, the extended analysis reports AUC < 0.5 for ΔD, which implies either:
  - the scoring direction is inverted for this dataset, or
  - the dataset semantics differ from the pipeline’s essentiality CSV, or
  - ΔD is not predictive in this merged dataset and the earlier AUC claim is dataset-specific.

**Gate A Note (action required)**
- There are at least two essentiality datasets in play:
  - pipeline essentiality CSV (31 genes / 4 networks),
  - `essentiality_prediction_dataset.csv` (642 genes / 20 networks).
- Definitions of “essential” and the sign convention for ΔD must be unified before claims are written.

**Gate C Note (action required)**
- Before any Nature-facing claim, the evaluation must be made leakage-safe and direction-consistent, and must include incremental value vs baselines.

---

## Entry LEV8-2026-03-17-004 — Level 8 Definition Contract (Frozen)
**Date:** 2026-03-17  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (coherence), Gate B (bias control), Gate C (biological punch)  

**Scope**
- This contract is the single source of truth for sign conventions, units, null models, and evaluation protocol used in Level 8 runs and manuscript artifacts.

**Definitions (canonical)**
- **Adjacency representation:** directed 0/1 matrix `cm` from processed JSON.
- **Canonical node ordering:** sort nodes by total degree (in+out) descending before compression.
- **Algorithmic complexity proxy:**  
  - **D(cm) = len(gzip(cm.tobytes()))**  
  - Units: **compressed bytes**.
- **Degree-preserved null ensemble:** Maslov–Sneppen edge swaps, `n_swaps = N * 20`, seeded runs with `seed = 42 + i`.
- **Efficiency z-score (Figure 1):**  
  - **z = (mean(D_null) − D_bio) / std(D_null)**  
  - Interpretation: **z > 0 means biological networks are more compressible (more efficient) than null**.
- **One-sided empirical p-value (Figure 1):**  
  - **p = fraction(D_null ≤ D_bio)**  
  - Interpretation: small p supports **D_bio unusually low** under the degree-preserved null.
- **Differential complexity (node contribution):**  
  - **ΔD(node) = D(network without node) − D(network)**  
  - Interpretation: **ΔD > 0 means removing the node increases complexity; the node contributes to efficiency**.

**Essentiality evaluation (canonical)**
- **Label semantics:** `Essentiality = 1` means essential.
- **Score orientation:** higher score means “more essential” for ROC/AUC:
  - **ΔD:** use **ΔD directly** (no sign flip).
  - **Degree / Betweenness / Clustering:** use metric directly.
- **Join key (no mixing):** merge node metrics with labels on **(Network, Gene)** after normalizing `Network` by stripping `.json`.
- **Primary validation protocol (leakage-safe):** **network-held-out 5-fold** (grouped by `Network`), with folds constructed to balance essential counts across folds when possible.
- **Secondary (exploratory) protocol:** gene-level stratified 5-fold CV (not leakage-safe across networks; reported only as a sensitivity check).

**Stop-the-line triggers**
- Any manuscript figure/table that uses a different z definition, ΔD definition, or score orientation than above is invalid until reconciled.
- Any essentiality evaluation that merges only on Gene (ignoring Network) is invalid (label leakage / mixing).

**Implication**
- This resolves the previously observed “negative mean z” ambiguity: after adopting the canonical z above, the same numerical separation yields **positive** mean z when biological networks are more efficient.

---

## Entry LEV8-2026-03-21-001 — Z-Score Convention Standardization (Artifacts + Null Stats)
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (coherence)  

**Scope**
- Standardize the z-score sign convention and interpretation across manuscript artifacts and stored null summaries.
- Verify that z-scores recompute exactly from stored null summary statistics.

**Canonical convention (re-affirmed)**
- **z = (mean(D_null) − D_bio) / std(D_null)**  
- Interpretation: **z > 0 means biological networks are more compressible (more efficient) than null**; **z < 0 means less compressible (more complex) than null**.

**DV2 null model artifact (GRN corpus)**
- Source artifact: `results/bio/null_stats.json` (generated by `src/experiments/Null_Generator_HPC.py` using `UniversalDv2Encoder`).
- Stored fields per network include `D_bio`, `mu_*`, `sd_*`, `z_*` for `* ∈ {deg, er, gate}`.
- Internal recomputation check:
  - For all 231 networks and for each null family, recomputed `z = (mu − D_bio)/sd` matches stored `z` exactly (max absolute difference = 0.0).
  - Stored global means in `results/bio/null_summary.json` match recomputed means exactly:
    - `z_deg_mean = -1.7048356960`
    - `z_er_mean  = -3.0661374751`
    - `z_gate_mean = -2.5878679478`

**Manuscript coherence (sign + meaning)**
- Updated manuscript LaTeX to match the canonical definition and interpretation (positive = efficiency; negative = complexity tax), including corrected sign in example tables and narrative phrasing.

---

## Entry LEV8-2026-03-21-002 — Theory→Computation Mapping + ΔD Direction Unification (Regression + Reruns)
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (coherence), Gate C (validation semantics)  

**Scope**
- Make DepMap validation runs provenance-safe (avoid silently generating synthetic inputs).
- Make the script easier to run against a real DepMap release when those files are present.
- Re-run the proxy-table pilot and emit manuscript-facing artifacts.

**Code changes**
- File: [DepMap_Validation.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/DepMap_Validation.py)
- Behavior changes:
  - If `DEPMAP_PATH` is missing, try to infer `CRISPRGeneEffect.csv` / `Model.csv` from `DEPMAP_RELEASE_DIR` or `data/depmap/24Q4`.
  - If still missing, abort unless `DEPMAP_ALLOW_SYNTHETIC=1` (smoke-test only); synthetic input is written under `results/cancer/`.
  - Derived “gene mean” cache can be redirected via `DEPMAP_CACHE_DIR`.
  - Output directory for `DEPMAP_OUT_PREFIX` is created automatically.

**Pilot run (proxy DepMap table in-repo)**
- Command:
  - `DEPMAP_OUT_PREFIX=4ClaudeCode/claude-Nature/paper/figures/figure3_depmap_validation DEPMAP_PATH=data/cancer/depmap_crispr.csv /Users/alberto/Documents/projects/CausalBool/venv/bin/python src/analysis/DepMap_Validation.py`
- Inputs:
  - Patient networks: `data/cancer/patients/*_Tumor.json`
  - Dependency table: `data/cancer/depmap_crispr.csv`
- Outputs:
  - `paper/figures/figure3_depmap_validation.csv`
  - `paper/figures/figure3_depmap_validation_stats.json`
  - `paper/figures/figure3_depmap_validation_scatter.png`
- Result summary:
  - Pearson r = 0.13, p = 7.12e−01; MI = 0.00 bits (“No Dependency”) (superseded by Entry LEV8-2026-03-21-003)

**PDF build**
- Command:
  - `latexmk -pdf -interaction=nonstopmode -halt-on-error bioProcessLev8.tex`
- Output:
  - `paper/bioProcessLev8.pdf`
- SHA-256:
  - `19f2be1d127543c2d257c85c76a53d7cc3d5b7261113cc11df63f8141ce8776c`

**Note**
- In this checkout, DepMap Public 24Q4 is present under `data/depmap/` (not under `data/depmap/24Q4/`); use the paths and checksums in Entry LEV8-2026-03-21-003 as the execution provenance for this checkout.

---

## Entry LEV8-2026-03-21-003 — DepMap Public 24Q4 (Real) Integration Run + Figure 3 Regeneration
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (provenance), Gate C (external validation anchor)  

**DepMap release presence**
- DepMap Public 24Q4 is present in-repo under:
  - `/Users/alberto/Documents/projects/CausalBool/data/depmap/`
- Release README:
  - `/Users/alberto/Documents/projects/CausalBool/data/depmap/README.txt`

**Raw artifacts (sizes + SHA-256)**
- `CRISPRGeneEffect.csv` (~409M):
  - `3d8f3ec6dbf2db7ff834b79b508622ec0b226f3518003fe96ecf5a4fcf167e3b`
- `Gene.csv` (~16M):
  - `dfb5f74496ca17baf67f215a44f06197ddd835685813aede75754876b62b19db`
- `Model.csv` (~631K):
  - `b7a0c1385e6cef30132b56aff61f1261d11e3f490490b355c430d32ee0dbdcfa`
- `ModelCondition.csv` (~214K):
  - `b0f22ddb886b241a3ff48674f58edba3e71c021c717aa40924e2cce67bf5200b`

**Derived dependency summary**
- Goal: reduce the model-level `CRISPRGeneEffect.csv` matrix to the legacy `Gene,Dependency` table used by the Level 8 validation pipeline.
- Method:
  - For each mapped gene, compute mean gene effect across all DepMap models (ignore NaNs).
  - Map scaffold nodes to one or more genes (e.g., SOS→SOS1/SOS2; RAS→KRAS/NRAS/HRAS), and average those gene effects to a node-level dependency value.
- Cache location:
  - `DEPMAP_CACHE_DIR=results/cancer/depmap_cache`

**DepMap release audit (format + join-key invariants)**
- Goal: verify that major DepMap matrices in `data/depmap/` conform to expected schema patterns and that model-keyed matrices join cleanly against `Model.csv`.
- Command:
  - `DEPMAP_AUDIT=1 DEPMAP_AUDIT_DIR=data/depmap DEPMAP_MODEL_PATH=data/depmap/Model.csv /Users/alberto/Documents/projects/CausalBool/venv/bin/python src/analysis/DepMap_Validation.py`
- Checks performed (logged to console):
  - header schema (n\_cols, id column name, sample columns)
  - ID sampling (unique IDs in first 2000 rows)
  - overlap of sampled IDs with `Model.csv` (join-key sanity)
  - numeric parse sanity on a small sample of value columns
- Outcome:
  - `CRISPRGeneEffect.csv`, `CRISPRGeneDependency.csv`, `OmicsExpressionProteinCodingGenesTPMLogp1.csv`, `OmicsCNGene.csv`: ID overlap = 1.000 against `Model.csv`
  - `OmicsFusionFiltered.csv`: `ModelID` overlap = 1.000 against `Model.csv`
  - `OmicsSomaticMutationsProfile.csv`: variant table keyed by genomic coordinates (expected non-overlap with `Model.csv`), and mixed numeric/categorical columns behave as expected in sampling
  - audit failures = 0

**Execution (real DepMap)**
- Command:
  - `DEPMAP_OUT_PREFIX=4ClaudeCode/claude-Nature/paper/figures/figure3_depmap_validation DEPMAP_PATH=data/depmap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/depmap/Model.csv DEPMAP_CACHE_DIR=results/cancer/depmap_cache DEPMAP_FORCE_REBUILD=1 /Users/alberto/Documents/projects/CausalBool/venv/bin/python src/analysis/DepMap_Validation.py`

**Outputs (manuscript-facing)**
- `paper/figures/figure3_depmap_validation.csv`
- `paper/figures/figure3_depmap_validation_stats.json`
- `paper/figures/figure3_depmap_validation_scatter.png`

**Result summary (10-node EGFR scaffold; n=100 tumor networks aggregated)**
- Pearson r = 0.4055, p = 0.2450
- Spearman ρ = 0.4788, p = 0.1615
- MI = 0.00 bits (“No Dependency”)

## Entry LEV8-2026-03-21-004 — Freeze Gate A/B/C Quantitative Thresholds (TSK-LEV8-00-004)
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A/B/C (operational decision thresholds)  

**Objective**
- Freeze a single numeric pass/fail specification for Gate A/B/C and evaluate it deterministically from the stored Level 8 artifacts in this checkout.

**Execution**
- Command:
  - `/Users/alberto/Documents/projects/CausalBool/venv/bin/python paper/code/analysis_pipeline.py --evaluate-gates --figures-dir paper/figures --bootstrap 20000`
- Inputs (artifact-derived):
  - `paper/figures/results_summary.csv` (Gate A: null efficiency criteria)
  - `paper/figures/figure3_depmap_validation_stats.json` (Gate C: DepMap anchor)
  - `results/bio/essentiality_prediction_dataset.csv` (Gate C: incremental value vs degree baseline)
  - `results/cancer/corruption_metrics.csv` (Gate C: paired corruption; synthetic in this checkout)

**Outputs (manuscript-facing)**
- `paper/figures/gate_thresholds_summary.csv` (SHA-256: `fdf450308b13d9981ff14ecb0150b7ac9aa11e965e812c195c61595d9f0e5175`)
- `paper/figures/gate_thresholds_status.png` (SHA-256: `f221b4233fff6a8fead13c696e7f4c25856c301e7ed80543c970a946ad9348ca`)
- `paper/figures/gate_thresholds_status.pdf` (SHA-256: `f6eaf2bc8e07ae48632b9feace4f2b4adb00ee62082c74b3fa9ae756b05d29bb`)

**Result summary (frozen thresholds evaluated on this checkout)**
- Gate A: PASS (all frozen criteria satisfied; mean $z=0.723$, $\Pr(z>0)=0.662$, $\Pr(p\le 0.05)=0.212$, $n=231$ networks).
- Gate B: not evaluated in this checkout (no independent cohort/control suite is implemented yet).
- Gate C: PARTIAL (paired corruption clears numeric thresholds but is synthetic; DepMap anchor and essentiality incremental value fail under frozen criteria).
  - Seed robustness (Gate A): on the first 30 eligible networks, Spearman$(z)$ across seeds $=0.972$, $\Delta\mathrm{mean}(z)=0.076$, sign agreement $=0.933$ (PASS under frozen tolerances).

**Robustness check (bootstrap stability for essentiality incremental value)**
- On `results/bio/essentiality_prediction_dataset.csv` with seed=42, the $\Delta\mathrm{AUC}(\Delta D-\mathrm{Degree})$ 95\% CI is stable across bootstrap sizes:
  - $n_{\mathrm{boot}}=5{,}000$: $\Delta\mathrm{AUC}=0.035$, CI $[-0.101, 0.165]$
  - $n_{\mathrm{boot}}=20{,}000$: $\Delta\mathrm{AUC}=0.035$, CI $[-0.099, 0.166]$
  - $n_{\mathrm{boot}}=50{,}000$: $\Delta\mathrm{AUC}=0.035$, CI $[-0.098, 0.168]$

## Entry LEV8-2026-03-18-001 — DepMap 24Q4 Acquisition + Pilot External Validation (KR-A anchor)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (provenance), Gate C (external validation)  

**Objective**
- Acquire DepMap 24Q4 public release artifacts with immutable provenance.
- Build a gene-level dependency summary usable by the current validation pipeline.
- Run a pilot ΔD-vs-DepMap validation against the existing “tumor cohort” networks in `data/cancer/patients`.

**Primary sources consulted (provenance)**
- DepMap 24Q4 release announcement (context on pipeline updates + metadata): https://forum.depmap.org/t/announcing-the-24q4-release/3564
- Figshare+ DepMap 24Q4 Public item (distribution): https://plus.figshare.com/articles/dataset/DepMap_24Q4_Public/27993248
- Figshare API endpoint (file manifest / stable file IDs): https://api.figshare.com/v2/articles/27993248

**Acquisition**
- Raw download directory created:
  - `/Users/alberto/Documents/projects/CausalBool/data/depmap/24Q4/raw`
- Files downloaded (Figshare file IDs via `ndownloader.figshare.com/files/<id>`):
  - `CRISPRGeneEffect.csv` (file id 51064667)
  - `Gene.csv` (file id 51065183)
  - `Model.csv` (file id 51065297)
  - `ModelCondition.csv` (file id 51065300)
- Correction note (important):
  - An initial attempt downloaded `Gene.csv` into `Model.csv` due to using the wrong file id; the Figshare API manifest was then used to disambiguate and re-download the correct `Model.csv` and `ModelCondition.csv`, renaming the mis-downloaded file to `Gene.csv`.

**Checksums (SHA-256, raw + derived)**
- Raw (24Q4):
  - `CRISPRGeneEffect.csv` (428,678,699 bytes): `3d8f3ec6dbf2db7ff834b79b508622ec0b226f3518003fe96ecf5a4fcf167e3b`
  - `Gene.csv` (16,564,061 bytes): `dfb5f74496ca17baf67f215a44f06197ddd835685813aede75754876b62b19db`
  - `Model.csv` (645,696 bytes): `b7a0c1385e6cef30132b56aff61f1261d11e3f490490b355c430d32ee0dbdcfa`
  - `ModelCondition.csv` (219,100 bytes): `b0f22ddb886b241a3ff48674f58edba3e71c021c717aa40924e2cce67bf5200b`
- Derived:
  - `depmap_24Q4_gene_effect_mean.csv` (483,512 bytes): `89d8db657b227aa4f9554281e460e214955403df815cfd8252610463e3ffa0e1`

**Derived dataset construction**
- Goal: convert the DepMap gene-effect matrix into the legacy “Gene, Dependency” table expected by `src/analysis/DepMap_Validation.py`.
- Input:
  - `CRISPRGeneEffect.csv` with first column = cell line identifier, remaining columns = genes named like `TP53 (7157)`.
- Transform:
  - For each gene column, compute the mean gene effect across all cell lines (ignoring NaNs).
  - Normalize gene symbols by stripping trailing ` (EntrezID)` suffix.
- Output:
  - `/Users/alberto/Documents/projects/CausalBool/data/depmap/24Q4/derived/depmap_24Q4_gene_effect_mean.csv`
- Important limitation (frozen in log):
  - This is an across-all-lineages average, not context-specific and not corrected for known confounds (expression, copy number, lineage composition). It is suitable only as a pilot Gate C anchor, not as a final Nature-grade result.

**Code changes (DepMap integration)**
- File modified: [DepMap_Validation.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/DepMap_Validation.py)
- Functional upgrades:
  - Accept either (a) a `Gene,Dependency` table or (b) a DepMap gene-effect matrix path and auto-derive `*.gene_mean.csv`.
  - Normalize gene symbols by stripping ` (EntrezID)` suffix.
  - Precompute a `Gene → mean dependency` dictionary for O(1) lookups.
  - Compute both Pearson and Spearman correlation in `compute_correlation`.
  - Allow `DEPMAP_PATH` override via environment variable in CLI example.

**Pilot validation run**
- Networks analyzed:
  - `data/cancer/patients_zanudo_prolif/*_Tumor.json` (paired TCGA tumor instances instantiated on the fixed 17-node oncogenic signaling scaffold)
  - Patients used: 50 (10 projects × 5 paired cases; tumor instances only)
- DepMap predictor:
  - `Dependency(gene)`: mean DepMap 24Q4 gene effect across cell lines (more negative = more essential)
- CausalBool predictor:
  - `Mean_Delta_D(gene)`: mean ΔD_v2 across patient tumor networks (as implemented in `DepMap_Validation.py`)
- Outputs saved:
  - `results/cancer_zanudo_prolif/depmap_validation_zanudo_prolif.csv`
  - `results/cancer_zanudo_prolif/depmap_validation_zanudo_prolif_stats.json`
  - `figures/figure3_depmap_validation_24Q4.png` (SHA-256: `5d4bd5049b341ac5569f4bbc7f733986565848c414a5bab5d23272cef91987b1`)
  - `figures/figure3_depmap_validation_24Q4.pdf` (SHA-256: `6934dc69fcd40596d1887f49d62556aa61b8d7fa64d03d30c32a62e9a5261301`)

**Results (pilot)**
- Overlap size:
  - `n_nodes_used = 15` (DepMap-covered scaffold nodes after mapping/aggregation)
- Pearson:
  - `r = -0.352`, `p = 0.198`
- Spearman:
  - `rho = -0.307`, `p = 0.265`
- Mutual information (KNN estimator wrapper):
  - `MI_bits = 0.253` (“Weak Dependency” classification)
- Permutation test (Dependency permuted across genes; one-sided in expected negative direction):
  - `n_perm = 500`, `p_left = 0.214`

**Interpretation**
- Directionally consistent with the biological expectation (more “structurally important” genes should trend toward stronger essentiality / more negative gene effect), but this pilot is massively underpowered because:
  - the validation operates at node-level with only 15 DepMap-covered nodes,
  - the DepMap dependency summary used is context-agnostic (mean across all lineages),
  - no confound controls are included yet (degree, expression, CNV).

**Gate C status**
- Not passed (pilot-only). External anchor exists with full provenance, but the analysis does not yet demonstrate incremental value beyond baselines under a leakage-safe, context-specific evaluation design.

---

## Entry LEV8-2026-03-18-006 — Lineage-matched DepMap validation on real TCGA paired-tumor models (BRCA/Breast)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (protocol discipline), Gate C (context matching), Gate B (sensitivity check)  

**Objective**
- Replace the context-agnostic DepMap mean with a lineage-matched dependency summary when validating against the real paired TCGA tumor-instantiated pathway models.

**Design**
- Tumor model cohort:
  - `data/cancer/tcga_patients_paired/*/*_Tumor.json` (real TCGA RNA-seq–conditioned EGFR pathway Boolean models; $n=50$ tumors across 10 projects)
- External anchor:
  - DepMap 24Q4 `CRISPRGeneEffect.csv` filtered to `OncotreeLineage = Breast` using `Model.csv`, then averaged across the filtered models to produce `Gene,Dependency` for the whitelist genes used by the pathway mapping.
- Statistic:
  - Pearson correlation between node-wise `Mean_Delta_D` and lineage-matched DepMap dependency (negative values = more essential).

**Command (frozen)**
- `DEPMAP_DATA_DIR="data/cancer/tcga_patients_paired" DEPMAP_RECURSIVE=1 DEPMAP_PATH="data/depmap/24Q4/raw/CRISPRGeneEffect.csv" DEPMAP_MODEL_PATH="data/depmap/24Q4/raw/Model.csv" DEPMAP_ONCOTREE_LINEAGES="Breast" DEPMAP_N_PATIENTS=50 DEPMAP_OUT_PREFIX="results/cancer/depmap_validation_tcga_paired_24Q4__lineage_BREAST" python -u src/analysis/DepMap_Validation.py`

**Outputs saved**
- `results/cancer/depmap_validation_tcga_paired_24Q4__lineage_BREAST.csv`
- `results/cancer/depmap_validation_tcga_paired_24Q4__lineage_BREAST_stats.json`
- `results/cancer/depmap_validation_tcga_paired_24Q4__lineage_BREAST_scatter.png`
- Derived DepMap dependency table created on-demand:
  - `data/depmap/24Q4/raw/CRISPRGeneEffect.csv.gene_mean__lineage_BREAST.csv`

**Results**
- Overlap size:
  - `n_nodes_used = 10` (EGFR pathway nodes; fixed by scaffold)
- Pearson:
  - `r = -0.332`, `p = 0.349`
- Spearman:
  - `rho = -0.248`, `p = 0.489`
- Mutual information (KNN estimator wrapper):
  - `MI_bits = 0.0` (“No Dependency” classification)

**Interpretation**
- The expected negative direction is preserved under lineage matching, but the result remains underpowered at $n=10$ nodes and sensitive to aggregation (gene-family nodes such as Ras/SOS/ERK).

**Consistency with thesis + prior numbers**
- Direction: consistent with the theory-facing expectation that higher structural importance (larger mean $\Delta D$ under in-silico KO) should align with stronger essentiality (more negative DepMap gene effect), i.e., a negative association.
- Magnitude: the lineage-matched $r=-0.332$ is weaker than the context-agnostic real-TCGA paired-node result previously logged in the manuscript ($r=-0.438$), which is expected under a filter that changes the dependency baseline and reduces the effective sample of cell lines.
- Inference status: neither the context-agnostic nor lineage-matched external anchor is statistically significant at $n=10$ nodes, so these results remain supportive as a directionality check and provenance anchor, not as confirmatory validation.

**Implications (research-level)**
- What the new result adds: it removes a major interpretability objection (“DepMap is averaged across irrelevant tissues”) by demonstrating that context matching does not flip the direction.
- What it does not add: it does not materially strengthen evidential weight for the external-validation claim because the dominant limitation remains node coverage (EGFR scaffold only) and gene-family aggregation.
- What it suggests next: scale node coverage (larger pathways / multi-pathway models) and run the same lineage-matched evaluation with confound controls (degree, expression proxies, CNV) before any incremental-value claim.

---

## Entry LEV8-2026-03-18-007 — Multi-lineage DepMap sensitivity sweep on real TCGA paired-tumor models
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (context matching), Gate B (robustness)  

**Objective**
- Test whether the external-anchor direction (ΔD vs essentiality) is stable across the relevant TCGA project lineages, not just Breast.

**Design**
- Same cohort and scaffold as LEV8-2026-03-18-006 (real TCGA paired-tumor pathway models; $n=50$ tumors; 10 nodes).
- Recompute DepMap dependency by filtering DepMap models by `OncotreeLineage` and averaging CRISPR gene effect across the lineage-filtered models.
- Lineages tested (matching the 10-project TCGA pilot): Breast, Lung, Bowel, Prostate, Kidney, Head and Neck, Thyroid, Liver.

**Command (frozen)**
- `DEPMAP_DATA_DIR="data/cancer/tcga_patients_paired" DEPMAP_RECURSIVE=1 DEPMAP_PATH="data/depmap/24Q4/raw/CRISPRGeneEffect.csv" DEPMAP_MODEL_PATH="data/depmap/24Q4/raw/Model.csv" DEPMAP_ONCOTREE_LINEAGE_SWEEP="Breast,Lung,Bowel,Prostate,Kidney,Head and Neck,Thyroid,Liver" DEPMAP_N_PATIENTS=50 DEPMAP_OUT_PREFIX="results/cancer/depmap_validation_tcga_paired_24Q4" python -u src/analysis/DepMap_Validation.py`

**Outputs saved**
- `results/cancer/depmap_validation_tcga_paired_24Q4__lineage_sweep_summary.csv`
- `results/cancer/depmap_validation_tcga_paired_24Q4__lineage_sweep_summary.json`

**Results (Pearson, n=10 nodes in all lineages)**
- All lineages show negative $r$ (direction preserved).
- Range across tested lineages:
  - $r \in [-0.531, -0.284]$
  - Smallest $p$ observed: Lung ($r=-0.453$, $p=0.188$); Bowel ($r=-0.531$, $p=0.114$)

**Interpretation**
- The external-anchor sign is stable under tissue matching across multiple lineages, which strengthens the thesis-level coherence claim (no direction reversal under context matching).
- This sweep does not resolve statistical validation: with only 10 pathway nodes, all lineage-matched tests remain underpowered, and heterogeneity in effect magnitude is plausible given lineage-specific essentiality baselines.

---

## Entry LEV8-2026-03-18-003 — DepMap Baselines vs ΔD (TSK-LEV8-04-002B, repository-wide bio models)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (reproducibility), Gate C (external anchor), Gate B (baseline controls)  

**Goal**
- Measure whether ΔD contributes incremental signal beyond simple structural baselines when predicting DepMap dependency.

**Design (current pass)**
- Population: genes pooled across `data/bio/processed/*.json` networks (not cancer-specific).
- ΔD: `Mean_Delta_D(gene)` computed by in-silico node deletion per-network, aggregated across all networks containing that gene.
- External anchor: DepMap 24Q4 mean gene effect across all cell lines (derived dataset; more negative = more essential).
- Baselines (structural):
  - InDegree, OutDegree, TotalDegree (from adjacency matrix)
  - PageRank (power-iteration on adjacency matrix)
  - Eigenvector centrality (power-iteration on adjacency matrix)
- Multivariate model: linear regression with 5-fold CV on standardized predictors.

**Outputs saved**
- `results/depmap/24Q4/depmap_predictor_comparison_bio_models.csv` (SHA-256: `fe4f3a6cad0235051a0356170c5b118cc2ffcfb5b5ad7f0d11cb05fce007abe8`)
- `results/depmap/24Q4/depmap_predictor_comparison_bio_models.json` (SHA-256: `ce07839fdb9f5fe32d7accc41cc7969ea806e9b0b06608fcd2a7aef8bb0469b3`)

**Cohort summary**
- `n_genes_total = 1844` (genes appearing in ≥1 bio model with ≥5 nodes)
- `n_with_dependency = 475` (genes overlapping DepMap 24Q4 derived dependency table)

**Results (global, pooled)**
- Univariate (Pearson r; negative = more essential for larger predictor values):
  - ΔD: `r = -0.0075`, `p = 0.871` (no signal)
  - OutDegree: `r = -0.1656`, `p = 2.90e-04`
  - TotalDegree: `r = -0.1699`, `p = 1.98e-04`
  - InDegree: `r = -0.1091`, `p = 1.74e-02`
- Multivariate (5-fold CV R²):
  - Baselines-only: `mean R² = -0.00495`
  - Baselines + ΔD: `mean R² = -0.00851`
  - ΔR² (full − base): `-0.00356` (no incremental value in this pooled evaluation)

**Interpretation**
- In this pooled, cross-pathway mixture, ΔD does not explain DepMap essentiality beyond noise; degree-like baselines show small but detectable associations.
- This result does not falsify the theory claim in its intended domain (disease-context networks) because:
  - The external anchor is context-agnostic (mean across all cell lines).
  - The network population is a heterogeneous mixture of curated pathways with no lineage matching.
  - Pooling genes across many unrelated pathways collapses mechanistic context and introduces heavy confounding.

**Next scientific move implied by this result**
- Re-run TSK-LEV8-04-002B in a context-matched design (cancer type / lineage matched networks + CCLE expression/CNV controls) before claiming incremental value.

---

## Entry LEV8-2026-03-18-004 — Real TCGA RNA-seq acquisition (TSK-LEV8-04B-002, frozen pilot cohorts)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (immutable provenance), Gate C (domain substrate), Gate B (protocol discipline)  

**Goal**
- Replace synthetic “TCGA-BR” cohorts with real tumor/normal RNA-seq count data suitable for downstream context-matched validation.

**Acquisition protocol (frozen)**
- Source: NCI GDC API `https://api.gdc.cancer.gov`
- Data type: `Gene Expression Quantification`
- Workflow: `STAR - Counts` (GDC “augmented_star_gene_counts.tsv”)
- Sample types: `Primary Tumor` and `Solid Tissue Normal`
- Pilot scale: `n=5` tumor + `n=5` normal per cancer type (frozen small-N for pipeline wiring; expand only after Gate A/B pass)
- Implementation: [gdc_tcga_downloader.py](file:///Users/alberto/Documents/projects/CausalBool/src/data/gdc_tcga_downloader.py)

**On-disk locations**
- Root: `data/cancer/tcga/`
  - `data/cancer/tcga/TCGA-BRCA/`
  - `data/cancer/tcga/TCGA-LUAD/`
  - `data/cancer/tcga/TCGA-COAD/`
- Each project directory contains:
  - `manifest.csv` (file IDs + sample types + local paths)
  - `meta.json` (query parameters + counts)
  - `raw/<SampleType>/*.tsv` (downloaded STAR count tables)
  - `processed/counts_tumor.csv`, `processed/counts_normal.csv` (gene × sample matrices; gene index = HGNC symbol when available)
  - `processed/qc.json` (sample counts, gene counts, and first-10 library sizes)

**QC summary (all three projects)**
- Each project has:
  - `tumor_n_samples = 5`, `normal_n_samples = 5`
  - `tumor_n_genes = 59427`, `normal_n_genes = 59427`
- Notes:
  - These matrices are raw unnormalized counts (unstranded); no filtering beyond removing control summary rows and empty gene names.
  - This is sufficient for provenance-complete acquisition + frozen preprocessing; differential expression normalization is a separate ticket.

**Checksums (SHA-256, acquisition artefacts)**
- TCGA-BRCA:
  - `manifest.csv`: `3901135a86c69848d3d6aec73403914d2da9b6776d74b251cb07dd98103ca271`
  - `meta.json`: `e60e1c402ffc949b54cc4d9f4650802568a348d654410f1d98389c486b588cb1`
  - `processed/counts_tumor.csv`: `cbd16b83f50024e2146a9fc72bae62da05c519433f4ddba928b61aaa05e8ee24`
  - `processed/counts_normal.csv`: `13f99e009137bd6b934c9bfd0664e1bc45ded7b54dc496032620dfd59c5404dc`
  - `processed/qc.json`: `d56e425c120e59a041b546e06576d0ce50ccfac2db59a283db59c8ae59ea62c7`
- TCGA-LUAD:
  - `manifest.csv`: `bbc31d9b90078907a5a049f66bd970a54c3ac3f6b62596e12150fba4ccc5bb1f`
  - `meta.json`: `185fafc919ff92f41311bbdca6c2a6778863a13207cb641f634c2a6c63433e2f`
  - `processed/counts_tumor.csv`: `e693b44dd8294046f80f5148648f5f3afd6281c2315656c739941f3a821eb449`
  - `processed/counts_normal.csv`: `80cd718c4823f0635f586b49d4553c0280b5b7a09f9099151a51e1eb8feb827f`
  - `processed/qc.json`: `91ed03b21dbac236cbd4df5dfa5425b62f90f4e6c36de4af9f188367e239aeb3`
- TCGA-COAD:
  - `manifest.csv`: `f84b7a02e5c7f6ee3da14775b88e852642e07d56c8eb7e0998a4f4afeeff1c02`
  - `meta.json`: `63a69852dd02083ccbc78ebcf3cd5bb935673ecce7ef3c1d0ef7778bb318a226`
  - `processed/counts_tumor.csv`: `5545f4e3d92f9c7d5db8404c8b0c487ffe1abedbc726edf4946e2b315030d422`
  - `processed/counts_normal.csv`: `54db065bc6ea344cb050438e8a3f096e4e095aca0ffd37266266257aa0287f9b`
  - `processed/qc.json`: `06f6e5053e5e6cb954a310bbc08cd446cbdc1f6cfd99021c076d78cb863c1df8`

**Acceptance / verification**
- Static correctness: `python -m compileall src tests` (OK)
- Unit test: [TSK-NATURE-LEV8-04B-002-Test.py](file:///Users/alberto/Documents/projects/CausalBool/tests/Nature/TSK-NATURE-LEV8-04B-002-Test.py) (OK)

**Implication**
- This satisfies the “immutable provenance” requirement for TCGA acquisition and provides real tumor/normal substrates for the next Gate C pass, but it does not yet create causal Boolean networks from expression (separate construction ticket).

---

## Entry LEV8-2026-03-18-005 — TCGA pilot cohort expansion to 10 projects (provenance freeze)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (immutable provenance), Gate C (domain substrate), Gate B (protocol discipline)  

**Goal**
- Expand the TCGA pilot acquisition from 3 projects to 10 projects while keeping the frozen preprocessing contract unchanged (small-N wiring pass).

**Expanded project set (frozen)**
- TCGA-BRCA, TCGA-LUAD, TCGA-COAD, TCGA-PRAD, TCGA-KIRC, TCGA-HNSC, TCGA-THCA, TCGA-LUSC, TCGA-LIHC, TCGA-KIRP

**On-disk locations**
- Root: `data/cancer/tcga/`
- Per-project:
  - `data/cancer/tcga/<PROJECT>/manifest.csv`
  - `data/cancer/tcga/<PROJECT>/meta.json`
  - `data/cancer/tcga/<PROJECT>/raw/<SampleType>/*.tsv`
  - `data/cancer/tcga/<PROJECT>/processed/counts_tumor.csv`
  - `data/cancer/tcga/<PROJECT>/processed/counts_normal.csv`
  - `data/cancer/tcga/<PROJECT>/processed/qc.json`

**QC summary (all 10 projects)**
- `tumor_n_samples = 5`, `normal_n_samples = 5`
- `tumor_n_genes = 59427`, `normal_n_genes = 59427`

**Checksums (SHA-256)**
- Full per-file checksum table (all 10 projects; manifest/meta/processed matrices/qc):
  - `results/cancer/tcga_10_cohort_checksums.txt`
  - SHA-256: `00c5644735d5fb01983c764ed6b485a1d4b9eca374c5b94890662d07a8083073`

**Interpretation**
- This completes the provenance freeze for the expanded TCGA pilot set and is now sufficient substrate for the next step: a context-matched cancer network construction protocol and downstream Gate C validation.

---

## Entry LEV8-2026-03-18-002 — Full Test Execution (Python + Mathematica)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (reproducibility), Gate B (regression control)  

**Python test suite (ticketed scripts)**
- Rationale: filenames contain `-` so default `unittest discover` does not import them; executed each `*-Test.py` script directly.
- Command pattern:
  - `find tests -name "*-Test.py" -print0 | while read -d "" f; do python "$f"; done`
- Result:
  - `python_test_files = 25`
  - All executed scripts reported `OK` / `PASSED`.
  - Run log: `results/tests/python_runall_status.txt`

**Mathematica / WolframKernel MUnit suite**
- Runner: `tests/MUnit/run-tests.sh --all`
- Result (source of truth):
  - `results/tests/runall/Status.txt` contains: `OK=87 FAIL=0 TOTAL=87`

**Static correctness**
- Python bytecode compilation:
  - `python -m compileall src tests`
  - Result: `COMPILEALL_OK` (no syntax errors across repository Python)

---

## Entry LEV8-2026-03-18-006 — Expression-to-network construction (TCGA pilot, frozen protocol)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (deterministic rebuild), Gate B (frozen thresholds + mapping), Gate C (real RNA-seq substrate)  

**Goal**
- Instantiate patient-specific Boolean pathway networks from real TCGA tumor/normal RNA-seq counts in a reproducible, leakage-minimizing way suitable for downstream Gate C validation.

**Frozen construction protocol**
- Inputs: `data/cancer/tcga/<PROJECT>/processed/counts_tumor.csv` and `counts_normal.csv` (unstranded raw counts).
- Transform: `x = log2(count + 1)`.
- Baseline: for each model node, compute the median `x` across all normal samples in the same TCGA project.
- Node mapping (HGNC symbols, aggregated by `max` within node):
  - `EGF → {EGF}`
  - `EGFR → {EGFR}`
  - `GRB2 → {GRB2}`
  - `SOS → {SOS1,SOS2}`
  - `Ras → {KRAS,NRAS,HRAS}`
  - `Raf → {BRAF,RAF1}`
  - `MEK → {MAP2K1,MAP2K2}`
  - `ERK → {MAPK1,MAPK3}`
  - `PI3K → {PIK3CA,PIK3CB,PIK3CD}`
  - `AKT → {AKT1,AKT2,AKT3}`
- Discretization (per tumor sample, per node):
  - If `x_tumor(node) - median_normal(node) ≥ 1.0`, apply `GoF` → set logic to `1` and sever incoming edges for that node.
  - If `x_tumor(node) - median_normal(node) ≤ -1.0`, apply `LoF` → set logic to `0` and sever incoming edges for that node.
  - Otherwise, leave node unchanged.
- Normal networks: reference (no mutations) per normal sample, to preserve a clean control topology.

**Implementation**
- Constructor: [cancer_network_builder.py](file:///Users/alberto/Documents/projects/CausalBool/src/data/cancer_network_builder.py)
  - Method: `CancerNetworkBuilder.generate_tcga_expression_cohort(...)`

**On-disk outputs**
- Patient networks (per project):
  - Root: `data/cancer/tcga_patients/<PROJECT>/`
  - Files: `<PROJECT>__<sample_uuid>_Tumor.json` and `<PROJECT>__<sample_uuid>_Normal.json`
- Cohort index (source of truth):
  - `results/cancer/tcga_expression_networks_index.csv`
  - SHA-256: `1df33dc6a7e84d353294fe4edea3dde6bc15a8f19b5e5c1d6768d3b16f7b8592`

**Sanity metrics (tumor networks)**
- Across all 10 projects (n=50 tumor samples): `mutation_count` mean `3.46`, median `3`, max `10`.
- Per-project mean mutation count spans `~1.6` (TCGA-PRAD) to `~5.0` (TCGA-COAD), consistent with lineage-specific pathway activation differences under this simple thresholding rule.

**Implication**
- This provides the first end-to-end, real-data-dependent mechanism that generates structural variability in patient pathway models from TCGA RNA-seq alone. It is a conservative scaffold for Gate C: it may underfit real regulation, but it is deterministic, auditable, and can be replaced later by a richer construction without breaking provenance.

---

## Entry LEV8-2026-03-18-007 — Paired TCGA tumor/normal corruption analysis (paired index, EGFR pathway)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (pairing correctness), Gate B (paired design), Gate C (domain signal)  

**Goal**
- Enforce within-patient tumor/normal pairing (hard requirement for $\Delta D_{\mathrm{tumor-normal}}$) and measure whether tumor networks differ from matched normal controls under the frozen EGFR expression-to-network corruption protocol.

**Paired cohort acquisition (new)**
- Rationale: the earlier pilot acquisition (Entry LEV8-2026-03-18-004/005) freezes equal counts of tumor and normal samples per project, but does not guarantee that samples are paired within the same patient/case.
- Implementation: [gdc_tcga_downloader.py](file:///Users/alberto/Documents/projects/CausalBool/src/data/gdc_tcga_downloader.py)
  - Function: `download_tcga_counts_paired_cohort(...)` (selects case IDs present in both Primary Tumor and Solid Tissue Normal search results, then downloads both)
- On-disk location:
  - `data/cancer/tcga_paired/<PROJECT>/raw/<SampleType>/*.tsv`
  - `data/cancer/tcga_paired/<PROJECT>/processed/counts_tumor.csv`
  - `data/cancer/tcga_paired/<PROJECT>/processed/counts_normal.csv`
  - `data/cancer/tcga_paired/<PROJECT>/manifest.csv`

**Paired expression-to-network construction**
- Implementation: [cancer_network_builder.py](file:///Users/alberto/Documents/projects/CausalBool/src/data/cancer_network_builder.py)
  - Method: `CancerNetworkBuilder.generate_tcga_expression_cohort(..., manifest_csv=...)`
- On-disk outputs:
  - Patient networks: `data/cancer/tcga_patients_paired/<PROJECT>/<PATIENT_ID>_{Tumor,Normal}.json`
  - Paired cohort index (source of truth): `results/cancer/tcga_expression_networks_index_paired.csv`
  - Index summary: `rows = 100` (10 projects × 5 pairs × 2 tissues), `complete_pairs = 50`

**Corruption analysis (paired $\Delta D$)**
- Implementation: [Cancer_Corruption.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/Cancer_Corruption.py)
- Inputs:
  - `TCGA_INDEX_PATH=results/cancer/tcga_expression_networks_index_paired.csv`
- Outputs:
  - Metrics table: `results/cancer/tcga_corruption_metrics_paired.csv`
  - Figures:
    - `figures/tcga_corruption_metrics_paired__tcga_delta_d_dist.png`
    - `figures/tcga_corruption_metrics_paired__tcga_mutcount_corr.png`
    - `figures/tcga_corruption_metrics_paired__delta_d_by_project.png`

**Results (n=50 paired tumor/normal patients; 10 projects × 5 pairs)**
- Summary (global):
  - Mean $D^{(v2)}_{\mathrm{normal}} = 46.52$
  - Mean $D^{(v2)}_{\mathrm{tumor}} = 40.70$
  - Mean $\Delta D^{(v2)} = D^{(v2)}_{\mathrm{tumor}} - D^{(v2)}_{\mathrm{normal}} = -5.83$
  - Paired t-test ($\Delta D^{(v2)}$ vs 0): $t = -5.69$, $p = 7.00 \times 10^{-7}$
  - Pearson correlation ($\Delta D^{(v2)}$ vs mutation\_count): $r = -0.91$, $p = 2.29 \times 10^{-20}$

**Interpretation**
- Under the frozen corruption model (constitutive GoF/LoF discretization + severed incoming edges), matched tumor networks are significantly more compressible than normal controls (negative $\Delta D$), consistent with a structural loss-of-integration signature.
- The magnitude of corruption scales strongly with the inferred mutation\_count, implying that expression-driven state-fixing events dominate the algorithmic complexity proxy in this construction.

**Implication for the research goal**
- This is a decisive substrate upgrade relative to the earlier synthetic cohorts: it delivers a paired design on real TCGA RNA-seq *samples* and yields a strong, reproducible within-patient signal in the resulting EGFR scaffold models.
- The key scientific constraint surfaced is that “corruption” in this current scaffold manifests as structural simplification (lower $D$) rather than added structural complexity; the manuscript narrative must align with this mechanistic fact for coherence.

**Threshold sensitivity (rerun; robustness check)**
- Implementation: [Cancer_Corruption.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/Cancer_Corruption.py) (paired sweep mode)
- Outputs:
  - `results/cancer/tcga_corruption_metrics_paired__tcga_paired_sweep.csv`
  - `results/cancer/tcga_corruption_metrics_paired__tcga_paired_sweep_summary.csv`
  - `figures/tcga_corruption_metrics_paired__tcga_sweep_mean_delta_d.png`
  - `figures/tcga_corruption_metrics_paired__tcga_sweep_corr_vs_thr.png`
- Global (n=50 pairs) stability across discretization thresholds:
  - Threshold 0.5: mean $\Delta D^{(v2)}=-11.50$; $t=-9.80$, $p=4.0\times 10^{-13}$; $r(\Delta D^{(v2)},\mathrm{mutation\_count})=-0.89$, $p=3.8\times 10^{-18}$; mean mutation\_count $=5.84$
  - Threshold 1.0: mean $\Delta D^{(v2)}=-5.83$; $t=-5.69$, $p=7.0\times 10^{-7}$; $r(\Delta D^{(v2)},\mathrm{mutation\_count})=-0.91$, $p=2.3\times 10^{-20}$; mean mutation\_count $=3.34$
  - Threshold 1.5: mean $\Delta D^{(v2)}=-2.33$; $t=-3.24$, $p=2.2\times 10^{-3}$; $r(\Delta D^{(v2)},\mathrm{mutation\_count})=-0.83$, $p=9.2\times 10^{-14}$; mean mutation\_count $=1.98$

**Nature-facing plots and summary tables**
- Plots:
  - `figures/tcga_corruption_metrics_paired__tcga_delta_d_dist.png`
  - `figures/tcga_corruption_metrics_paired__tcga_mutcount_corr.png`
  - `figures/tcga_corruption_metrics_paired__delta_d_by_project.png`
  - `figures/tcga_corruption_metrics_paired__tcga_dv2_tumor_vs_normal.png`
- Summary tables:
  - Per-pair metrics: `results/cancer/tcga_corruption_metrics_paired.csv`
  - Per-project summary: `results/cancer/tcga_corruption_metrics_paired__tcga_paired_per_project_summary.csv`
  - Sensitivity sweep: `results/cancer/tcga_corruption_metrics_paired__tcga_paired_sweep_summary.csv`

---

## Entry LEV8-2026-03-18-007B — Paired TCGA tumor/normal corruption analysis (paired index, 17-node oncogenic signaling scaffold)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (pairing correctness), Gate B (paired design), Gate C (domain signal)  

**Goal**
- Repeat the paired tumor/normal corruption analysis on the frozen 17-node oncogenic signaling scaffold (Zañudo proliferation model), using the same paired TCGA RNA-seq substrate and discretization protocol.

**Corruption analysis (paired $\Delta D$; Zanudo scaffold)**
- Implementation: [Cancer_Corruption.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/Cancer_Corruption.py) (paired sweep mode)
- Inputs:
  - `TCGA_INDEX_PATH=data/cancer/tcga_index_zanudo_prolif_byproject.csv`
  - `TCGA_COUNTS_ROOT=data/cancer/tcga_paired`
  - `TCGA_BASE_NETWORK_PATH=data/bio/processed/ginsim_default_2018_zanudo_proliferation.json`
- Outputs:
  - Metrics table (all thresholds): `results/cancer_zanudo_prolif/corruption_metrics_zanudo_prolif__tcga_paired_sweep.csv`
  - Metrics table (threshold=1.0 slice): `results/cancer_zanudo_prolif/corruption_metrics_zanudo_prolif.csv`
  - Per-project summary (threshold=1.0 slice): `results/cancer_zanudo_prolif/corruption_metrics_zanudo_prolif__tcga_paired_per_project_summary.csv`
  - Summary (per project, per threshold): `results/cancer_zanudo_prolif/corruption_metrics_zanudo_prolif__tcga_paired_sweep_summary.csv`
  - Figures:
    - `figures/corruption_metrics_zanudo_prolif__tcga_delta_d_dist.png` (thr=1.0)
    - `figures/corruption_metrics_zanudo_prolif__tcga_mutcount_corr.png` (thr=1.0)
    - `figures/corruption_metrics_zanudo_prolif__delta_d_by_project.png` (thr=1.0)
    - `figures/corruption_metrics_zanudo_prolif__tcga_dv2_tumor_vs_normal.png` (thr=1.0)
    - `figures/corruption_metrics_zanudo_prolif__tcga_sweep_mean_delta_d.png`
    - `figures/corruption_metrics_zanudo_prolif__tcga_sweep_corr_vs_thr.png`

**Results (n=50 paired tumor/normal patients; 10 projects × 5 pairs; threshold=1.0)**
- Summary (global):
  - Mean $D^{(v2)}_{\mathrm{normal}} = 107.96$
  - Mean $D^{(v2)}_{\mathrm{tumor}} = 92.29$
  - Mean $\Delta D^{(v2)} = -15.66$
  - Paired t-test ($\Delta D^{(v2)}$ vs 0): $t=-9.53$, $p=9.81\\times 10^{-13}$
  - Pearson correlation ($\Delta D^{(v2)}$ vs mutation\_count): $r=-0.95$, $p=3.77\\times 10^{-25}$

**Threshold sensitivity (global; n=50 pairs)**
- Threshold 0.5: mean $\Delta D^{(v2)}=-31.61$; $t=-17.83$, $p=4.65\\times 10^{-23}$; $r=-0.96$, $p=2.34\\times 10^{-28}$; mean mutation\_count $=9.40$
- Threshold 1.0: mean $\Delta D^{(v2)}=-15.66$; $t=-9.53$, $p=9.81\\times 10^{-13}$; $r=-0.95$, $p=3.77\\times 10^{-25}$; mean mutation\_count $=4.92$
- Threshold 1.5: mean $\Delta D^{(v2)}=-9.61$; $t=-8.58$, $p=2.49\\times 10^{-11}$; $r=-0.89$, $p=2.38\\times 10^{-18}$; mean mutation\_count $=2.80$

---

## Entry LEV8-2026-03-18-008 — DepMap external anchor on real TCGA paired tumor networks (EGFR pathway)
**Date:** 2026-03-18  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (mapping coherence), Gate C (external anchor), Gate B (no mixing)  

**Goal**
- Replace the synthetic tumor cohort used in the DepMap pilot with tumor models instantiated from real paired TCGA RNA-seq samples (on the same fixed EGFR pathway scaffold), while keeping the external dependency anchor (DepMap 24Q4) provenance-frozen.

**Cohort**
- Models: all tumor instances under `data/cancer/tcga_patients_paired/**/**_Tumor.json` (n=50 tumors; fixed 10-node EGFR pathway scaffold, with node state-fixing driven by tumor-vs-normal expression deltas).

**DepMap-to-node mapping (frozen for this run)**
- Rationale: pathway nodes include abstractions (e.g., Ras, PI3K) that do not exist as single HGNC symbols in DepMap.
- Implementation: [DepMap_Validation.py](file:///Users/alberto/Documents/projects/CausalBool/src/analysis/DepMap_Validation.py)
  - Mapping used for node-level dependency (mean across mapped genes when available):
    - SOS → {SOS1,SOS2}
    - Ras → {KRAS,NRAS,HRAS}
    - Raf → {BRAF,RAF1}
    - MEK → {MAP2K1,MAP2K2}
    - ERK → {MAPK1,MAPK3}
    - PI3K → {PIK3CA,PIK3CB,PIK3CD}
    - AKT → {AKT1,AKT2,AKT3}

**Outputs**
- Validation table: `results/cancer/depmap_validation_tcga_paired_24Q4.csv`
- Stats JSON: `results/cancer/depmap_stats_tcga_paired_24Q4.json`
- Figure: `figures/figure5_depmap_validation_tcga_paired_24Q4.png`

**Results (node-level; n=10)**
- Pearson (Mean $\Delta D$ vs DepMap dependency): $r=-0.438$, $p=0.206$
- Spearman: $\rho=-0.491$, $p=0.150$
- Mutual information: `MI_bits = 0.0` (diagnostic only at n=10)

**Interpretation**
- The direction is consistent with the hypothesized sign: nodes with higher mean $\Delta D$ (more structurally important under in-silico knockout) trend toward more negative DepMap gene effect (more essential), but the result remains statistically underpowered due to the 10-node scaffold and context-agnostic DepMap averaging.

**Implication**
- This converts the DepMap anchor into a real-cancer-substrate run while preserving provenance. A Nature-facing Gate C pass still requires increasing node/gene coverage (beyond a single pathway) and adopting lineage-matched DepMap summaries or other context-matched endpoints.
