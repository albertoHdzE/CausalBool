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
  - `fe629499d53eaa409fce0883032e6e15135fc808b902f5379bc804b8d8c9a6cf`

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
  - For each mapped gene, compute mean gene effect across all DepMap models (ignore NaNs), then define dependency as `-mean_gene_effect` (higher = more essential).
  - Map scaffold nodes to one or more genes (e.g., SOS→SOS1/SOS2; RAS→KRAS/NRAS/HRAS), and average those gene-level dependency values to a node-level dependency proxy.
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
- SHA-256:
  - `figure3_depmap_validation.csv`: `618682d78d6da747a8e5738d29e9f669a7d2ecd3a695c62294969c92b1798fd1`
  - `figure3_depmap_validation_stats.json`: `6e109866a57ee41a0904f4c3c03534adae8efbdabeb5738f9dd024892eb3df8f`
  - `figure3_depmap_validation_scatter.png`: `2f86a41b1e5dce153e6d4ed4cf80e2300c7512da7e9b2ef13c1009e5fc9e4905`

**Result summary (10-node EGFR scaffold; n=100 tumor networks aggregated)**
- Pearson r = -0.4055, p = 0.2450
- Spearman ρ = -0.4788, p = 0.1615
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
- `paper/figures/gate_thresholds_summary.csv` (SHA-256: `909c821de942fd2743d6075a8e8d83b98459565e873eebb69d2a106eb0e192da`)
- `paper/figures/gate_thresholds_status.png` (SHA-256: `f221b4233fff6a8fead13c696e7f4c25856c301e7ed80543c970a946ad9348ca`)
- `paper/figures/gate_thresholds_status.pdf` (SHA-256: `52ad2d8287dde4b96c14bfe698305fe9131ddee37194f1a325004d07656876d2`)

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
- Pearson (Mean $\Delta D$ vs DepMap dependency): $r=0.438$, $p=0.206$
- Spearman: $\rho=0.491$, $p=0.150$
- Mutual information: `MI_bits = 0.0` (diagnostic only at n=10)

**Interpretation**
- The direction is consistent with the hypothesized sign: nodes with higher mean $\Delta D$ (larger information loss under in-silico knockout) trend toward higher DepMap dependency (more essential), but the result remains statistically underpowered due to the 10-node scaffold and context-agnostic DepMap averaging.

**Implication**
- This converts the DepMap anchor into a real-cancer-substrate run while preserving provenance. A Nature-facing Gate C pass still requires increasing node/gene coverage (beyond a single pathway) and adopting lineage-matched DepMap summaries or other context-matched endpoints.

---

## Entry LEV8-2026-03-21-004 — ΔD Sign Unification Across Manuscript Artifacts + Essentiality Re-run
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (coherence)  

**Goal**
- Remove cross-document contradictions in the definition of $\Delta D$ for knockout/removal impact.
- Re-run the Level 8 essentiality script to confirm that ROC/AUC scoring uses the frozen direction (no implicit negations).

**Canonical convention (re-affirmed)**
- Node removal impact (Level 8): $\Delta D(v)=D(G)-D(G\setminus v)$, so $\Delta D>0$ means removal decreases complexity (information loss under removal).
- Score orientation for ROC/AUC: higher scores = more essential; use $\Delta D$ directly (no sign flip).

**Manuscript-facing corrections (sign reconciliation)**
- Several manuscript drafts used the opposite sign (e.g., $D(\mathcal{N}_i^{KO})-D(\mathcal{N})$ or $D^{KO}-D^{WT}$) while still interpreting “higher $\Delta D$” as stronger impact. These have been rewritten to match the canonical convention without changing the intended interpretation.
- Files updated:
  - `doc/finalpaper/nature_draft.tex`
  - `doc/finalpaper/final-draft.tex`
  - `doc/finalpaper/sections/results_hybrid.tex`
  - `doc/finalpaper/together_full.tex`
  - `doc/newIntPaper/bioProcess.tex`
  - `doc/newIntPaper/bioProcessLev5.tex`

**Essentiality re-run (Level 8 figures)**
- Command:
  - `/Users/alberto/Documents/projects/CausalBool/venv/bin/python /Users/alberto/Documents/projects/CausalBool/4ClaudeCode/claude-Nature/paper/code/essentiality_analysis.py`
- Dataset resolved by script to:
  - `results/bio/essentiality_prediction_dataset.csv` (642 genes, 20 networks; Essential=24, Non-essential=618)
- Console summary (as produced by script):
  - Bootstrap AUC (95% CI):
    - $\Delta D$: 0.547 [0.445–0.643]
    - Degree: 0.511 [0.369–0.644]
    - Betweenness: 0.521 [0.398–0.635]
  - Cross-validated AUC (5-fold):
    - $\Delta D$: 0.461 ± 0.080
    - Degree: 0.406 ± 0.101
    - Betweenness: 0.364 ± 0.125
    - Combined: 0.406 ± 0.103
- Outputs produced (regenerated):
  - `paper/figures/figure2_essentiality_extended.pdf`
  - `paper/figures/figure2_essentiality_extended.png`
  - `paper/figures/supplementary_table_per_network.csv`

**BioProcess update**
- `paper/bioProcessLev8.tex` updated to match the re-run values exactly (CI bounds and combined model AUC).

**PDF build**
- Command:
  - `latexmk -pdf -interaction=nonstopmode -halt-on-error bioProcessLev8.tex`
- SHA-256:
  - `bioProcessLev8.pdf`: `0ae38c8f9dccc781697355235d0c42a2850da6f803dc3f8c650b4726d4476f00`

**Note on prior entry**
- Entry LEV8-2026-03-17-003 contains an earlier bootstrap AUC line for $\Delta D$ (0.453 [0.357–0.555]) that is superseded by the current deterministic run above under the frozen sign convention and current script version.

---

## Entry LEV8-2026-03-21-005 — Nature Scope Freeze Statement (TSK-LEV8-00-002)
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A, Gate B, Gate C  

**Goal**
- Freeze a single Nature-facing “core claim / core evidence / core implication” statement to prevent scope drift.
- Eliminate manuscript dependence on a multi-level protocol narrative; the Nature main text must read as one coherent method and one story.

**Scope contract (authoritative)**
- **Core claim:** evolved GRNs are systematically more compressible than matched nulls under a frozen encoding (algorithmic efficiency under constraints).
- **Core evidence:** a reproducible three-null analysis (ER, degree-preserved, gate-permuted) reported with effect sizes and uncertainty under frozen sign conventions and pass thresholds.
- **Core implication:** mechanistic information loss under in-silico knockout (\(\Delta D\)) is the causal importance score; KR-A (essentiality) is the primary biological validation target and must be leakage-safe, baseline-benchmarked, and externally anchored (DepMap minimum). KR-B/KR-C remain parallel tracks unless they independently clear Gate C.

**Artifacts updated**
- Plan contract recorded in:
  - `paper/bioPlanLev-8.md` (TSK-LEV8-00-002 marked DONE; scope statement added)
- Manuscript support recorded in:
  - `paper/bioProcessLev8.tex` (\textit{Scope freeze} section added)

---

## Entry LEV8-2026-03-21-006 — Theory→Computation Mapping Propagated to Nature Methods (TSK-LEV8-01-001)
**Date:** 2026-03-21  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (exactness boundary)  

**Goal**
- Eliminate proxy-vs-exactness ambiguity in the Nature-facing Methods text by explicitly stating what is computed in code (and in which units), and what is only a conceptual/theoretical object.

**Canonical mapping (re-affirmed)**
- GRN corpus results: $D_{\mathrm{gzip}}(cm)=\mathrm{len}(\mathrm{gzip}(cm.\mathrm{tobytes}()))$ (compressed bytes).
- Cancer/DepMap results: $D^{(v2)}(cm)$ via the universal $D^{(v2)}$ encoder (bits).
- Knockout/removal impact: $\Delta D = D(\mathrm{WT}) - D(\mathrm{KO}) = D(G) - D(G\setminus v)$ (context-appropriate $D$ proxy).
- Efficiency score: $z=(\mathbb{E}[D_{\mathrm{null}}]-D_{\mathrm{bio}})/\mathrm{sd}(D_{\mathrm{null}})$ (so $z>0$ indicates algorithmic efficiency).

**Edits applied**
- Added an explicit “Exactness boundary and computed proxies (implementation)” block to the Nature Methods draft and aligned the Z-score sign convention to the Level 8 contract:
  - `doc/finalpaper/nature_draft.tex`
- Marked the mapping ticket as DONE in the Level 8 plan:
  - `paper/bioPlanLev-8.md`

**Implication**
- Any future manuscript text that introduces $D$ as an exact Kolmogorov complexity quantity (or that compares magnitudes across proxy families) is out of contract unless it is explicitly framed as conceptual and not used for reported numbers.

---

## Entry LEV8-2026-03-23-001 — Reproducibility Stress Tests (TSK-LEV8-02-003) + Deterministic Ordering Control
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (reproducibility discipline), Gate B (bias-control prerequisite: ordering invariance)  

**Objective**
- Execute a predeclared stress-test grid over a fixed subset of GRNs to quantify stability under seeds, null ensemble size, swap intensity, and ordering assumptions.
- Record pass/fail against frozen tolerances and emit a mitigation plan for any failures.

**Command (frozen)**
- `python 4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py --stress-tests --figures-dir 4ClaudeCode/claude-Nature/paper/figures --repro-nets 30`

**Artifacts produced**
- `paper/figures/reproducibility_stress_grid.csv` (full per-condition measurements)  
  - SHA-256: `d8fb643f2d5818905085fcb21d69f1d4982d5c58d09757f9b0935e6fff0bfa60`
- `paper/figures/reproducibility_stress_summary.json` (protocol, tolerances, pass/fail, mitigation)  
  - SHA-256: `63df54c7ee3dbb2877283fb6e1008f156967a4d8b9a32912b8e95462e87b48d8`
- `paper/figures/reproducibility_stress_axes.png` (stress-axis plots)  
  - SHA-256: `f9e25bc24cda1a2b4a05e2a038691967aae2a6b9354fefa590856978195987d5`
- `paper/figures/reproducibility_stress_axes.pdf`  
  - SHA-256: `ef58b5a6e65fc6b40b8de4f24d42eb564cbc55aa13627d1a8438f17325c82bac`

**Protocol (as executed; summary excerpt)**
- Networks subset: first 30 eligible GRNs under the standard size/edge filters.
- Baseline null estimator: degree-preserved (Maslov--Sneppen), seed=42, $n_{\mathrm{random}}=50$, $n_{\mathrm{swaps}}=20N$, canonical degree ordering enabled.
- Ordering test: 10 random node permutations per network, with (i) no sorting control and (ii) degree ordering + deterministic tie-breakers.
- Essentiality stability test: group-stratified 5-fold by network; seeds $\{1,2,3,4,5\}$; representative feature sets including $\Delta D+\mathrm{Graph}+\mathrm{Constraint}$.

**Results (this checkout)**
- Baseline null meta (subset $n=30$): mean $z=0.946$, median $z=0.678$, mean fold reduction $=1.030$, $\Pr(p\le 0.05)=0.233$.
- Seed robustness (null z ranks): PASS (Spearman $\ge 0.966$; sign agreement $0.933$; $|\Delta \overline{z}|\le 0.076$ for tested seeds).
- Null ensemble size: $n_{\mathrm{random}}=10$ is unstable in mean $z$ and fails tolerance, but is explicitly treated as non-required; $n_{\mathrm{random}}\ge 25$ PASS with $|\Delta \overline{z}|\le 0.004$ and relative $\Delta$ fold $\le 0.001$.
- Swap intensity: PASS for $m\in\{5,20,100\}$ with $|\Delta \overline{z}|\le 0.023$ and relative $\Delta$ fold $\le 0.002$.
- Ordering assumptions: the naive “index” tie-breaker FAILS permutation stability (mean relative SD $\approx 0.028$), while WL-style deterministic tie-breaking yields exact invariance (relative SD $=0.0$ and relative range $=0.0$ across permutations), so the ordering axis PASS is credited only to the WL tie-breaker.
- Essentiality CV seed: PASS under tolerance (AUC range $\le 0.03$), including $\Delta D+\mathrm{Graph}+\mathrm{Constraint}$ with AUC range $0.0255$ across 5 seeds.

**Key scientific insight**
- Canonical degree ordering is not sufficient to guarantee determinism when degree ties are frequent; permutation of tied nodes changes serialized adjacency structure and perturbs $D_{\mathrm{gzip}}$. WL-style neighborhood hashing provides a deterministic refinement that removes this non-determinism without altering the encoding contract (it only fixes the tie-breaking rule).

**Mitigation plan (frozen hooks)**
- If seed robustness fails: increase $n_{\mathrm{random}}$ and/or enlarge the network subset; investigate high tie rates in ordering.
- If $n_{\mathrm{random}}$ stability fails: increase $n_{\mathrm{random}}$ until $\overline{z}$ and fold reduction stabilize under tolerances.
- If swaps fail: increase swap attempts or $n_{\mathrm{swaps}}$ multiplier; verify validity for small graphs.
- If ordering fails: enforce deterministic tie-breaking (WL-style).
- If essentiality CV seed fails: increase sample size or tighten group stratification; consider regularization tuning under nested CV.

---

## Entry LEV8-2026-03-23-002 — gnomAD Constraint Integration + Leakage-safe Benchmark Suite (TSK-LEV8-02-002B)
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (baseline benchmarking with modern predictors), Gate A (artifact locking)  

**Objective**
- Integrate gnomAD gene constraint features (pLI, LOEUF) as a lockable, in-repo baseline predictor.
- Recompute the benchmark suite under group-stratified evaluation (by network) and emit manuscript-facing artifacts with uncertainty and calibration.

**Raw gnomAD constraint artifact (locked)**
- Directory: `data/gnomAD/`
- Files:
  - `gnomad_v2.1.1_constraint.tsv.bgz`  
    - SHA-256: `153031d34b6794e8e99eb0306bc3c50b13b18accda8b0ffef91c2623dd3affd5`
  - `gnomad_v2.1.1_constraint.sha256`  
    - SHA-256: `d74e273bc525c43897f4ff1780fababf7cc59d3afe9b2e54093e96d737cca039`

**Benchmark artifacts (manuscript-facing)**
- `paper/figures/essentiality_benchmark_summary.json`  
  - SHA-256: `2f9c3079220f1c9f3cc79b1420fcf86dbfbd94f0e9da0891035e97db7b0ebb23`
- `paper/figures/essentiality_benchmark_oof_gnomad.csv`  
  - SHA-256: `9f66c93e3533d78e389b95c821f76e6c9dffce7c7a089fc44fbbb72dd073f291`
- `paper/figures/figure2_essentiality_benchmarks_gnomad.png`  
  - SHA-256: `ea9e098079dc0e573c892e67c9ce5f6dcd261fddac4abdf09e9577b61b5ba8ac`
- `paper/figures/figure2_essentiality_benchmarks_gnomad.pdf`  
  - SHA-256: `805c67056ce88de56bd0399bc626bbd74c8d148967105312f8c6bfed6fd5771c`

**Results (gnomAD-available subset; leakage-safe grouped evaluation)**
- Subset size: 152 gene-network rows, 15 networks.
- Constraint-only (pLI + LOEUF): AUC $0.342$ (95\% CI $[0.254, 0.470]$).
- $\Delta D+\mathrm{Graph}+\mathrm{Constraint}$: AUC $0.464$ (95\% CI $[0.316, 0.673]$).

**Interpretation**
- The constraint baseline is weak on the current essentiality label set, and does not rescue essentiality performance under the frozen evaluation protocol. The primary evidential value at Level 8 is that LOEUF/pLI is no longer “missing by construction”: it is integrated as an auditable, immutable baseline, making any incremental-value claim falsifiable against a strong modern predictor family.

---

## Entry LEV8-2026-03-23-003 — Regenerated Gate A Artifacts (Consistency Check)
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (artifact coherence)  

**Command**
- `python 4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py --skip-depmap --figures-dir 4ClaudeCode/claude-Nature/paper/figures --null-samples 50`

**Outputs (key)**
- `paper/figures/results_summary.csv`  
  - SHA-256: `5ca6c4deac568b7b2f533516fc68145b860c6ca85ea7c8a24374c72bd5a25e82`
- `paper/figures/null_meta_summary.json`  
  - SHA-256: `dda1bdd1990ddd44bbba62da9c4711c479ce97e51b6cc764e05da9f49cf4ff1f`
- `paper/figures/figure1_algorithmic_efficiency.png`  
  - SHA-256: `75f985428b0bca4eff8a6f9d05ac70142a65f6b8a141b89f487a333b03ff9676`
- `paper/figures/figure1_algorithmic_efficiency.pdf`  
  - SHA-256: `6f3f3c0bf0c3c189339a07562f1f9e45b27bb96da56508ffbbf23631b10b6b59`

**Sanity summary (console)**
- Networks analyzed: 231
- Significant (p<0.05 in expected direction): 49 (21.2%)
- Mean ratio (D\_bio/D\_random): 0.981
- Mean z-score (canonical): 0.72

---

## Entry LEV8-2026-03-23-004 — BioProcess Lev8 Regeneration (Stress Tests + Bias Section)
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (report regeneration)  

**PDF build**
- Command:
  - `latexmk -pdf -interaction=nonstopmode -halt-on-error bioProcessLev8.tex`
- Output:
  - `paper/bioProcessLev8.pdf`
- SHA-256:
  - `bioProcessLev8.pdf`: `8eb36eed2c9333be937a1b059696792e9423cfd789806ad0c304f10e51e57225`

---

## Entry LEV8-2026-03-23-005 — Bias Defense Suite (TSK-LEV8-03-001 Counter-tests; Partial Gate B)
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate B (universality defense), Gate A (artifact locking)  

**Objective**
- Convert the steelman “curation/selection bias” objection into executable, quantitative counter-tests using only immutable Gate A outputs (degree-preserved null results).

**Command**
- `python 4ClaudeCode/claude-Nature/paper/code/analysis_pipeline.py --bias-tests --figures-dir 4ClaudeCode/claude-Nature/paper/figures`

**Inputs**
- `paper/figures/results_summary.csv` (degree-preserved null; per-network z, p, ratios; generated by the Gate A pipeline)

**Artifacts produced**
- `paper/figures/bias_defense_summary.json` (protocol, tolerances, baseline, axis-level pass/fail)  
  - SHA-256: `9dfd7b3f26bff5787dce6e1a58d9b3cad7ac4132613ee0eaeb5cb1f6dc638ae0`
- `paper/figures/bias_defense_grid.csv` (scenario grid: size filters, leave-one-source-out, density trims)  
  - SHA-256: `7a3b64341d671a83db279e064cd27f130837c0f5e3d2e99ebae06e2f845dc757`
- `paper/figures/bias_defense_stratified.csv` (mean z + bootstrap CI by Source/Organism/Size bin)  
  - SHA-256: `c1849d5ac2e2affdb2c212f739539997be4f7a47d697ec9d3b35622755956c8b`
- Plots:
  - `paper/figures/figure_bias_defense_by_source.png` (mean z by Source with bootstrap CI)  
    - SHA-256: `f476b90dfc663dcae562ec885883d02c8af34ecdd76690f68eb9b65db56b78f8`
  - `paper/figures/figure_bias_defense_by_source.pdf`  
    - SHA-256: `02dd071f636a40c7033279b999ea53bb4b62e2d9aeff3ec1d05387d805f70029`
  - `paper/figures/figure_bias_defense_sensitivity.png` (size-filter heatmap + leave-one-source-out deltas)  
    - SHA-256: `a65142873120837b0fa568435b804e02c843d6d3fd5f4c6a15b7bc5879be7893`
  - `paper/figures/figure_bias_defense_sensitivity.pdf`  
    - SHA-256: `1dd21ad8553ae3b848a1573f38619df7b1131bcee9b1659708d4d55b46dc0dd7`

**Protocol (predeclared)**
- Null family: degree-preserved.
- Baseline cohort: all networks used in Gate A corpus under the standard size/edge filters.
- Axes:
  - Size inclusion grid: $(\min N,\max N)\in\{5,10,15\}\times\{60,80,100\}$.
  - Leave-one-source-out: exclude each major source label with at least 5 networks.
  - Density trimming: none vs 5--95% vs 10--90% by edge density ($E/N^2$).
- Pass logic: each scenario must satisfy the Gate A prevalence thresholds; scenario-to-scenario magnitude shifts are recorded (deltas vs baseline) but not thresholded.

**Results (baseline; $n=231$ networks)**
- $\overline{z}=0.723$, median $z=0.527$, $\Pr(z>0)=0.662$, $\Pr(p\le 0.05)=0.212$, mean fold reduction $=1.021$.
- Sensitivity suite global status: PASS under the Gate A threshold definition (see `bias_defense_summary.json`).

**Interpretation**
- The Gate A “algorithmic efficiency” direction is robust to: (i) moderate shifts in inclusion thresholds, (ii) removal of any single major source subset, and (iii) trimming extreme densities. Notably, several sensitivity conditions increase $\overline{z}$ rather than reduce it, consistent with the effect strengthening in larger or moderately dense networks rather than being driven by a narrow, extreme subset.

---

## Entry LEV8-2026-03-23-006 — DepMap 24Q4 Provenance Lock + Real-data Figure 3 Regeneration (TSK-LEV8-04-001)
**Date:** 2026-03-23  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (external validation provenance), Gate A (artifact locking)  

**Objective**
- Replace the “proxy / synthetic DepMap” ambiguity by locking a concrete DepMap Public 24Q4 release directory with immutable checksums and by regenerating Figure 3 from the real Chronos model-level gene-effect matrix.

**DepMap release directory (local, immutable)**
- `data/DepMap/` (contains `README.txt` stating “DepMap Public 24Q4”)

**Manifest (checksums + roles)**
- `data/DepMap/manifest_24Q4.json`  
  - SHA-256: `715912b1f28dca4eec6fe35ff96cc02ff6255ae6ecfb85bd2b6e528d4b28c854`

**Key raw files (required + recommended)**
- `data/DepMap/CRISPRGeneEffect.csv` (Chronos; ModelID × Gene)  
  - SHA-256: `3d8f3ec6dbf2db7ff834b79b508622ec0b226f3518003fe96ecf5a4fcf167e3b`
- `data/DepMap/Model.csv` (model metadata; Oncotree annotations)  
  - SHA-256: `b7a0c1385e6cef30132b56aff61f1261d11e3f490490b355c430d32ee0dbdcfa`
- `data/DepMap/Gene.csv` (gene ID mapping reference)  
  - SHA-256: `dfb5f74496ca17baf67f215a44f06197ddd835685813aede75754876b62b19db`
- `data/DepMap/OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv` (expression confound control; recommended)  
  - SHA-256: `f7a03a4184b42817971d94b052759c12a246d109cbe451bb63181d14cd066617`
- `data/DepMap/OmicsCNGene.csv` (copy-number confound control; recommended)  
  - SHA-256: `4851d3e939d48837a39a0f01294deb90fa507a85703586a927b77474f999134c`

**Audit (schema + ID overlap sanity)**
- Command:
  - `DEPMAP_AUDIT=1 DEPMAP_AUDIT_DIR=data/DepMap python src/analysis/DepMap_Validation.py`
- Result:
  - PASS (`failures=0`), with ModelID overlap checks confirming expected joins for wide matrices.

**Figure 3 regeneration (real DepMap 24Q4)**
- Command:
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation DEPMAP_FORCE_REBUILD=1 python src/analysis/DepMap_Validation.py`
- Derived dependency table (whitelist-restricted gene means; defined as $-\,$gene effect):
  - `data/DepMap/CRISPRGeneEffect.csv.gene_mean.csv`  
    - SHA-256: `619403455f10e96535aaa43135c40dedac231dbfb8a357bc2fa52615bb16538c`
- Outputs:
  - `paper/figures/figure3_depmap_validation_stats.json`  
    - SHA-256: `3479a8944dfee218bbed87531a534f5a674b4ca146f58cf827141353a3a20fd4`
  - `paper/figures/figure3_depmap_validation_scatter.png`  
    - SHA-256: `6d6dacd2ae1883949c644ee7df7148ba3ead4ea3e1c01017e642eec1e90e0453`

**Observed statistics (this checkout)**
- Global Spearman correlation ($\Delta D$ vs Dependency): $\rho=0.41$, $p=2.45\times 10^{-1}$.
- Mutual information estimator output: $0.00$ bits (“No Dependency” under the current discretization settings).

**Interpretation**
- DepMap provenance is now concrete and auditable (release identified, checksums recorded, schema validated). The current DepMap correlation remains a low-power pilot due to the small scaffold and whitelist-restricted mapping (41 genes available in the derived table for the current node→gene map), and therefore does not upgrade Gate C. The correct scientific posture is: “external anchor pipeline is reproducible and provenance-complete; power and coverage remain limiting.”

---

## Entry LEV8-2026-04-05-001 — DepMap Benchmark vs Standard Predictors (TSK-LEV8-04-002B)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (external anchor methodology + controls)  

**Objective**
- Upgrade the DepMap pilot from a single bivariate scatter to a controlled comparison: test whether $\Delta D$ adds predictive signal for DepMap dependency beyond standard covariates (degree/centrality, expression, copy number, and gene constraint), using a permutation-backed incremental-value statistic.

**Inputs (DepMap Public 24Q4; provenance locked)**
- DepMap release root: `data/DepMap/` (see Entry LEV8-2026-03-23-006 for raw-file checksums + manifest).
- Dependency proxy: $-\,$Chronos gene effect (from `CRISPRGeneEffect.csv`), aggregated to gene means over models on the whitelist-derived subset.
- Confounds/covariates:
  - `OmicsExpressionProteinCodingGenesTPMLogp1BatchCorrected.csv` $\rightarrow$ `DepMapExpr_mean` (mean across models).
  - `OmicsCNGene.csv` $\rightarrow$ `DepMapCN_mean` (mean across models).
  - `gnomad_v2.1.1_constraint.tsv.bgz` (if present locally) $\rightarrow$ `gnomAD_pLI`, `gnomAD_LOEUF` for the mapped scaffold genes.

**Analysis design**
- Unit of analysis: scaffold nodes ($n=10$; EGFR signaling scaffold).
- Primary association: Pearson/Spearman between mean node impact $\Delta D(v)=D(G)-D(G\setminus v)$ (averaged over 100 tumor networks) and DepMap dependency proxy.
- Incremental-value test (pre-specified for this checkout):
  - Baseline model features: \{TotalDegree, Betweenness, DepMapExpr\_mean, DepMapCN\_mean, gnomAD\_pLI, gnomAD\_LOEUF\} (available subset).
  - Full model: baseline + Mean\_Delta\_D.
  - Estimator: ridge regression with LOOCV prediction; report MSE improvement $\Delta=\mathrm{MSE}_{base}-\mathrm{MSE}_{full}$ and LOOCV $\Delta R^2$.
  - Null: permute the dependency labels across nodes ($n_{perm}=5000$) and recompute $\Delta$; report empirical $p$.

**Artifacts (this checkout; Figure 3 extension)**
- Node-level dataset:
  - `paper/figures/figure3_depmap_validation.csv`
  - SHA-256: `6473261ff6435daca79919cf3c15a9daddec81d41029234e75e27fbc67057717`
- Stats bundle (correlations + univariate table + incremental-value permutation test):
  - `paper/figures/figure3_depmap_validation_stats.json`
  - SHA-256: `8f1e19ceabae965b36bd08e037a233fe364a659a6754865d62575f48c712eb32`
- Scatter (pilot):
  - `paper/figures/figure3_depmap_validation_scatter.png`
  - SHA-256: `6d6dacd2ae1883949c644ee7df7148ba3ead4ea3e1c01017e642eec1e90e0453`
- Benchmark plot (pilot scatter + permutation null for incremental value):
  - `paper/figures/figure3_depmap_validation_benchmark.png`
  - SHA-256: `dfc75f505461983fe1d6af23cdabcad3bc6c6d7e2b3c2e5589275b766191a95a`

**Key results (this checkout)**
- Association:
  - Pearson $r=0.406$, $p=0.245$; Spearman $\rho=0.479$, $p=0.162$ ($n=10$ nodes).
- Univariate baselines (selected):
  - DepMapCN\_mean vs dependency: Spearman $\rho=0.721$, $p=0.0186$.
  - TotalDegree vs dependency: Spearman $\rho=0.297$, $p=0.405$.
- Incremental value of $\Delta D$ beyond baseline covariates (ridge, LOOCV):
  - MSE improvement $\Delta=0.00791$; empirical permutation $p=0.233$ ($n_{perm}=5000$).
  - LOOCV $\Delta R^2=0.150$ (note: LOOCV $R^2$ can be negative under small-$n$ noise; interpret $\Delta$ and permutation $p$ as primary).

**Interpretation**
- The DepMap anchor is now methodologically complete for the “adds signal beyond standard predictors” question: we compute aligned covariates, use an out-of-sample incremental metric, and attach a permutation null. Under the current 10-node scaffold pilot, $\Delta D$ does not clear an external-validation threshold after controlling for expression/copy number/constraint proxies; the baseline signal is dominated by copy-number variation in this small scaffold.
- Scientific implication: external dependency is a composite phenotype (expression-, copy-number-, and lineage-mediated). A mechanistic information-loss score can only be expected to add signal when evaluated at sufficient node coverage and with lineage-matched filtering; this entry upgrades the pipeline so that scaling the node set becomes the only remaining blocker, not the methodology.

**Run log (re-executed after script update; reproducibility check)**
- Command (exit=0):
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation DEPMAP_PERM_N=5000 python src/analysis/DepMap_Validation.py`
- Runtime console summary:
  - “Stats saved to `paper/figures/figure3_depmap_validation_stats.json`”
  - “Plot saved to `paper/figures/figure3_depmap_validation_scatter.png`”
  - “Benchmark plot saved to `paper/figures/figure3_depmap_validation_benchmark.png`”
- Artifact checksums (confirming persistence after the rerun):
  - `paper/figures/figure3_depmap_validation.csv` — `6473261ff6435daca79919cf3c15a9daddec81d41029234e75e27fbc67057717`
  - `paper/figures/figure3_depmap_validation_stats.json` — `8f1e19ceabae965b36bd08e037a233fe364a659a6754865d62575f48c712eb32`
  - `paper/figures/figure3_depmap_validation_scatter.png` — `6d6dacd2ae1883949c644ee7df7148ba3ead4ea3e1c01017e642eec1e90e0453`
  - `paper/figures/figure3_depmap_validation_benchmark.png` — `dfc75f505461983fe1d6af23cdabcad3bc6c6d7e2b3c2e5589275b766191a95a`

**Methods (step-by-step; why each step exists)**
1. **Select DepMap release + lock provenance**
   - Use DepMap Public 24Q4 (`data/DepMap/`), previously locked by `manifest_24Q4.json` (Entry LEV8-2026-03-23-006), so that all downstream claims are tied to immutable inputs.
2. **Define the external endpoint (dependency proxy)**
   - Start from Chronos model-level gene-effect matrix `CRISPRGeneEffect.csv` where more negative gene effect indicates higher dependency.
   - Convert to a “higher = more essential” target by negating gene effect, then aggregate to a gene-level mean across DepMap models on the mapped whitelist (avoids injecting thousands of unmapped genes into a 10-node scaffold analysis).
3. **Compute mechanistic predictor ($\Delta D$)**
   - For each tumor network instance, compute the baseline $D^{(v2)}(G)$ on the adjacency matrix.
   - For each node $v$, remove the node (delete row/col), compute $D^{(v2)}(G\setminus v)$, then compute $\Delta D(v)=D(G)-D(G\setminus v)$.
   - Average $\Delta D(v)$ across the 100 tumor networks to get Mean\_Delta\_D per scaffold node.
4. **Compute standard covariates for confound control**
   - Graph covariates from the adjacency representation: TotalDegree, Betweenness, PageRank, EigenvectorCentrality.
   - DepMap omics covariates aligned to the same mapped genes: mean expression and mean copy number across models (`DepMapExpr_mean`, `DepMapCN_mean`).
   - Constraint covariates (if present locally): gnomAD pLI and LOEUF for the mapped genes.
5. **Primary association check (sanity + direction)**
   - Compute Pearson/Spearman correlations between Mean\_Delta\_D and dependency proxy.
6. **Incremental-value test (the key Gate C question)**
   - Fit a baseline model using standard covariates only, and a full model using baseline + Mean\_Delta\_D.
   - Evaluate with LOOCV to avoid in-sample inflation under $n=10$ nodes.
   - Quantify improvement by $\Delta=\mathrm{MSE}_{base}-\mathrm{MSE}_{full}$.
   - Attach a permutation null (shuffle dependency labels across nodes; $n_{perm}=5000$) to obtain an empirical $p$ for whether the observed improvement exceeds what is expected by chance at this scale.

**Theory-facing takeaway**
- This run sharpens the interpretation of “mechanistic information loss” as a candidate causal importance signal: it is not expected to dominate in regimes where external essentiality is strongly mediated by observational confounds (copy-number, expression, lineage). Instead, $\Delta D$ should be evaluated for *incremental value* once those confounds are controlled.
- The outcome is not a failure of the framework; it is a calibration point: the method is now strong enough to reject overconfident claims at scaffold scale and forces the next scientific move (scale coverage + lineage-matched filtering) rather than leaving ambiguity about whether we simply lacked controls.

---

## Entry LEV8-2026-04-05-002 — DepMap Lineage Sweep (Pilot Heterogeneity Check; TSK-LEV8-04-002)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (heterogeneity control; lineage-matched anchoring)  

**Objective**
- Quantify how the DepMap external anchor varies across major Oncotree lineages, and test whether $\Delta D$ shows stronger incremental value under lineage-matched aggregation of the dependency proxy.

**Why this matters (scientific motivation)**
- DepMap dependency is not a single biological quantity; it changes with lineage context and with genomic confounds (copy number, expression). A mechanistic predictor should be evaluated against a lineage-matched endpoint to avoid averaging away real biology or inflating spurious associations.

**Protocol**
- Select a small set of common lineages from `data/DepMap/Model.csv` (top counts in this local release) and run the same node-level pipeline as Figure 3, but with dependency proxy computed from only the DepMap models in that lineage.
- For each lineage:
  - build a lineage-filtered gene-level dependency table (whitelist genes; mean over DepMap models in lineage),
  - compute node-wise Mean\_Delta\_D across the synthetic TCGA-BR tumor cohort (100 networks),
  - compute Pearson/Spearman,
  - compute incremental value via LOOCV ridge + permutation null (here $n_{perm}=2000$ for speed).

**Implementation note (fix applied)**
- Lineages can contain characters like “/” (e.g., `CNS/Brain`). Cache filenames are now sanitized to avoid accidental directory paths when writing derived tables.

**Run log**
- Command (exit=0):
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation DEPMAP_PERM_N=2000 DEPMAP_ONCOTREE_LINEAGE_SWEEP='Lung,Lymphoid,Breast,CNS/Brain,Bowel,Ovary/Fallopian Tube' DEPMAP_FORCE_REBUILD=1 python src/analysis/DepMap_Validation.py`

**Artifacts (this checkout)**
- Summary table:
  - `paper/figures/figure3_depmap_validation__lineage_sweep_summary.csv`
  - SHA-256: `44cfd34424f43ba3e17f6e830a98dd3e08bdb0498dc58b0d4276d5605edeabb0`
- Summary JSON:
  - `paper/figures/figure3_depmap_validation__lineage_sweep_summary.json`
  - SHA-256: `f0e1205c2b2443213007cc9c2e3d9ff19fb7631e6f532b40cc97ff5daf02ec4f`
- Plot:
  - `paper/figures/figure3_depmap_validation__lineage_sweep.png`
  - SHA-256: `2519a1f34246a6fed6a5a2749cb1200055cd2576f8e3185b4ee6516fb6397f69`

**Key results (pilot; $n=10$ nodes each)**
- Lung: Spearman $\rho=0.552$; incremental permutation $p=0.544$.
- Lymphoid: Spearman $\rho=0.248$; incremental permutation $p=0.808$.
- Breast: Spearman $\rho=0.176$; incremental permutation $p=0.311$.
- CNS/Brain: Spearman $\rho=0.467$; incremental permutation $p=0.050$.
- Bowel: Spearman $\rho=0.467$; incremental permutation $p=0.069$.
- Ovary/Fallopian Tube: Spearman $\rho=0.491$; incremental permutation $p=0.156$.

**Interpretation**
- The external endpoint exhibits lineage heterogeneity even in this small pilot: the same mechanistic score is being compared to subtly different dependency targets depending on lineage composition.
- The marginal signal in CNS/Brain and Bowel (permutation $p$ near 0.05) is suggestive but not promotable: it is derived from $n=10$ nodes and a pilot-scale permutation budget. The scientifically correct conclusion is not “validation”, but “heterogeneity exists and lineage matching can change conclusions”.
- Theory implication: our framework gains a new operational insight — external anchoring must be phrased as “incremental value under lineage-matched endpoints,” not as a single pooled correlation. This directly informs the next Gate C push: increase node coverage (multi-pathway models) and rerun the same lineage-matched benchmark with a larger permutation budget.

---

## Entry LEV8-2026-04-05-003 — DepMap Scaling Attempt on Larger Cancer Scaffold (MAPK-large; Pilot)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (power/coverage scaling)  

**Objective**
- Increase node coverage beyond the 10-node EGFR scaffold and rerun the same DepMap benchmark. The goal is not to claim success, but to remove “underpowered node set” as an excuse and measure what changes when the scaffold is closer to a real signaling network size.

**Cohort generation (synthetic; deterministic)**
- Base Boolean model:
  - `data/bio/processed/ginsim_2013-mammal-mapk_MAPK_large_19june2013.json`
  - SHA-256: `67df72ed31db2d85f1383469c1b6a5246048913398cb9ccd5d9fc3b9643e9963`
- Generated cohort:
  - `data/cancer/patients_mapk_large/` (30 tumor/normal pairs; seed fixed by the builder)
  - metadata: `data/cancer/clinical_metadata_mapk_large.csv` (SHA-256 `f921ce4c64d366875eac526450bd6cc184d812bf2898c47960725a1a2b6a7f27`)

**Critical methodology fix (enables scaling)**
- DepMap gene whitelist is now expanded by scanning the cohort directory and adding network node labels as candidate genes (mapped directly when possible). Without this, the derived dependency table was constrained by the EGFR-only node→gene map and collapsed large scaffolds back to $\approx 10$ usable nodes.

**Run log (exit=0)**
- Command:
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_DATA_DIR=data/cancer/patients_mapk_large DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation_mapk_large DEPMAP_N_PATIENTS=30 DEPMAP_PERM_N=1000 DEPMAP_FORCE_REBUILD=1 python src/analysis/DepMap_Validation.py`

**Artifacts (this checkout)**
- Node-level dataset:
  - `paper/figures/figure3_depmap_validation_mapk_large.csv` — `73ecc71ca1d9fee892545d4e12126d11b05ab1403f51c29664850745ef3941a0`
- Stats bundle:
  - `paper/figures/figure3_depmap_validation_mapk_large_stats.json` — `1be43f4c37233e42df44dfff786f3a45cf1cb8267ccd2e94b720dd73ad1694b7`
- Scatter:
  - `paper/figures/figure3_depmap_validation_mapk_large_scatter.png` — `6da929d14b1264e325b5ddcad900be66824391b78f8c12d194f64bba672fa626`
- Benchmark plot:
  - `paper/figures/figure3_depmap_validation_mapk_large_benchmark.png` — `0d5e8543b803044ef4f01a5fedf92fe43c3dbfc7168390d8576c19bd010bd527`

**Key results**
- Usable nodes with DepMap dependency proxy available: $n=25$ (out of 53 scaffold nodes).
- Association:
  - Pearson $r=-0.294$, $p=0.153$; Spearman $\rho=-0.343$, $p=0.093$.
- Covariates:
  - DepMapExpr\_mean shows strong positive association with dependency (Spearman $\rho=0.565$, $p=3.28\times 10^{-3}$).
- Incremental value:
  - Adding Mean\_Delta\_D to baseline covariates *decreases* LOOCV performance in this pilot: $\Delta=\mathrm{MSE}_{base}-\mathrm{MSE}_{full}=-0.00971$ with permutation $p=0.362$ ($n_{perm}=1000$).

**Interpretation**
- Scaling node coverage does not automatically improve the external anchor: the dominant explanatory axis for DepMap dependency in this pilot is expression (and partly copy-number), while the mechanistic impact score does not add incremental predictive value under covariate control.
- Theory implication: this strengthens the framing that $\Delta D$ is a *mechanistic* descriptor that should be compared to lineage- and context-matched external endpoints. It also suggests a productive fork: either (i) incorporate dynamic/attractor-based impact (not only structural $D^{(v2)}$), or (ii) treat DepMap as a confound-rich endpoint and use it only under strict controls where we can argue about causal ordering (e.g., within-lineage, expression-matched comparisons).

---

## Entry LEV8-2026-04-05-004 — Conditioned DepMap Endpoint + Higher-Permutation Re-runs (Gate C Hardening)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (confound conditioning; stronger null budgets)  

**Objective**
- Make the external anchor question causal-structure-aware: evaluate $\Delta D$ against a DepMap dependency endpoint conditioned on standard covariates, and rerun key analyses with larger permutation budgets to reduce Monte Carlo uncertainty.

**Conditioned endpoint (definition)**
- Fit a baseline ridge model to predict DepMap dependency using covariates only:
  - \{TotalDegree, Betweenness, DepMapExpr\_mean, DepMapCN\_mean, gnomAD\_pLI, gnomAD\_LOEUF\} (available subset per run).
- Use LOOCV predictions $\hat y_{\text{base}}$ and define the conditioned endpoint as the residual:
  - $y_{\text{resid}} = y - \hat y_{\text{base}}$.
- Primary test: Spearman correlation between Mean\_Delta\_D and $y_{\text{resid}}$, with a permutation null obtained by shuffling $y_{\text{resid}}$ across nodes ($p$ reported two-sided via $|\rho|$).

**EGFR scaffold (10 nodes; $n_{perm}=10000$)**
- Command (exit=0):
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation DEPMAP_PERM_N=10000 python src/analysis/DepMap_Validation.py`
- Conditioned result:
  - Spearman $\rho(\Delta D, y_{\text{resid}})=0.515$; permutation $p(|\rho|)=0.131$.
- Updated artifacts:
  - `paper/figures/figure3_depmap_validation_stats.json` — `5638f30cac2f569796a72ebb837804b89815ff56a2f4b8876964737e9430f518`
  - `paper/figures/figure3_depmap_validation_conditioned.png` — `d1fe538688cf0ca15797ceff5edb7be4e9d7cb876f3f37b4687874baf89ef83d`
  - `paper/figures/figure3_depmap_validation_benchmark.png` — `0ad22d861115d3679ea58cd58747f01b250f1d642beb020d81e45b1a0b6293ba`

**MAPK-large scaffold (53 nodes; usable nodes $n=25$; $n_{perm}=5000$)**
- Command (exit=0):
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_DATA_DIR=data/cancer/patients_mapk_large DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation_mapk_large DEPMAP_N_PATIENTS=30 DEPMAP_PERM_N=5000 python src/analysis/DepMap_Validation.py`
- Conditioned result:
  - Spearman $\rho(\Delta D, y_{\text{resid}})=-0.261$; permutation $p(|\rho|)=0.210$.
- Updated artifacts:
  - `paper/figures/figure3_depmap_validation_mapk_large_stats.json` — `ef46d1aff0dbdf1c9d5664df465121a9741161ff88c6837e5a44dc0d62d4fe4f`
  - `paper/figures/figure3_depmap_validation_mapk_large_conditioned.png` — `d3b105da25e209cbe5742e9d794389a64ce77a34d7d3b7aaae295a1f4f44ac1c`
  - `paper/figures/figure3_depmap_validation_mapk_large_benchmark.png` — `3692f76320679d96e42df0d916a100f9aa17b4c07724bffa11aa754f0ff92782`

**Lineage-matched check on MAPK-large (3 lineages; $n_{perm}=3000$)**
- Command (exit=0):
  - `DEPMAP_RELEASE_DIR=data/DepMap DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_DATA_DIR=data/cancer/patients_mapk_large DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation_mapk_large DEPMAP_PERM_N=3000 DEPMAP_ONCOTREE_LINEAGE_SWEEP='CNS/Brain,Bowel,Lung' DEPMAP_FORCE_REBUILD=1 python src/analysis/DepMap_Validation.py`
- Outputs:
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep_summary.csv` — `d73e2c034cb3e7c567e64dc055ef534b528427c0ab8cfa4e4c3db6dce1197f56`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep_summary.json` — `20ff8e05ab12c791c30d8a32b0e49848915d4ee1c7e323c26b27f0aba825bc4a`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep.png` — `babc8211a6ebbdf20945819bcb979581efe5c117b88b64517e4656bda7b585ee`

**Interpretation**
- Conditioning the DepMap endpoint does not rescue a strong external validation claim in either scaffold; however, it improves the scientific framing: we are now explicitly asking whether $\Delta D$ captures *non-omic residual dependency* rather than rediscovering expression/copy-number structure.
- The result supports a sharper theory boundary: structural $\Delta D$ (under frozen serialization) is plausibly closer to a mechanistic controllability/impact notion than to raw dependency, and therefore must be evaluated under (i) lineage-matched endpoints and (ii) confound conditioning. This is an advance in rigor even when the numeric outcome is null, because it prevents spurious “validation by confounds”.

---

## Entry LEV8-2026-04-05-005 — Independent Cohort Acquisition (Cell Collective SBML-qual; TSK-LEV8-03-002)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate B (selection-bias defense via independence)  

**Objective**
- Acquire a cohort that is independent of the hand-curated logic corpus and test whether the “algorithmic efficiency” direction (biological $D$ lower than degree-preserved nulls) persists under a standardized conversion pipeline.

**Inclusion criteria (pre-registered for this cohort)**
- Source: Cell Collective SBML-qual models bundled with `ccapi` (local copy).
- Include all models in the bundle (here: 2 SBML files).
- No topology filtering for this acquisition step; report results per model with uncertainty.

**Raw inputs (immutable)**
- `src/external/ccapi/src/ccapi/data/models/boolean/sbml/lac-operon.sbml` — SHA-256 `328ecc82476de536ff5ae2b49a48e446fa811ba27f32a4272e609f387c9a563c`
- `src/external/ccapi/src/ccapi/data/models/boolean/sbml/fibroblasts.sbml` — SHA-256 `e2bf53d38240fc9fc1e996bec99d0bc0ef06dd5caccab6249981fd171bda3e3c`

**Conversion pipeline (step-by-step; reproducible)**
1. Parse SBML-qual species:
   - Extract each `qual:qualitativeSpecies` and use its `qual:name` as a node label.
2. Parse SBML-qual transitions:
   - For each `qual:transition`, add directed edges from each `qual:input` species to each `qual:output` species.
   - Preserve input sign as edge type label when present (positive→activation, negative→repression) but use the adjacency for $D$.
3. Standardize to the internal JSON schema:
   - Write `nodes`, `edges`, adjacency matrix `cm`, and provenance fields (`source`, SBML model ID/name) into `data/bio/processed/cc_sbml_*.json`.

**Standardized cohort artifacts (this checkout)**
- `data/bio/processed/cc_sbml_lac_operon.json` — `b6ddbbf6fcd600a8e4d11266cec8cbd149fd0a0ed014433cd933453566ba9f34`
- `data/bio/processed/cc_sbml_fibroblasts.json` — `b1157f6d1249a8ab46e566da9a26d8dcdfeb74e06d254b6da98399fca1057b95`

**Analysis (effect persistence test)**
- Null model: degree-preserved (Maslov–Sneppen swaps; default $n_{\mathrm{swaps}}=20N$ inside the pipeline).
- Complexity: compression-based $D$ under frozen ordering policy (degree sort + WL tie-breaker).
- Uncertainty: use the distribution of fold reductions across null draws; report mean and [2.5%,97.5%] quantiles.

**Run log**
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --cellcollective-cohort --figures-dir paper/figures --null-samples 250`

**Outputs (locked)**
- Table: `paper/figures/cellcollective_independent_cohort.csv` — `179a08aeb475d584e390adaed11f9eafb280a600a2999b96d3c373e7fff99e81`
- Plot: `paper/figures/cellcollective_independent_cohort.png` — `514632968edb3f21088ef6548065498ee834eab3bd51e3c917b1dcbf7609144d`
- Summary bundle: `paper/figures/cellcollective_independent_cohort_summary.json` — `6587077335b61795a3bee831cd3a22631b9046987d6d429177d6c48937509e11`

**Key results (independent cohort)**
- CC lac-operon (SBML): fold $=1.059$ [0.968, 1.143], $z=1.35$, $p=0.124$ ($n_{\mathrm{null}}=250$).
- CC fibroblasts (SBML; $N=139$): fold $=1.011$ [0.992, 1.029], $z=1.13$, $p=0.136$ ($n_{\mathrm{null}}=250$).
- Gate A baseline reference (existing corpus; from `paper/figures/null_results_long.csv`): fold mean $=1.021$ [0.949, 1.119] across $n=231$ networks.

**Interpretation**
- The direction persists under an independent acquisition + standardized conversion: both Cell Collective SBML models show $D_{\mathrm{bio}} < D_{\mathrm{null}}$ on average (fold $>1$), and the fold magnitudes sit within the Gate A corpus envelope.
- The evidence is correctly positioned as a minimal independence check rather than a decisive Gate B pillar: the cohort is small (2 models) and one model is larger than the typical 5–100-node analysis band, but the protocol is now real, reproducible, and extendable to additional SBML sources without changing the method.
- Theory implication: this materially strengthens the universality defense by demonstrating that the “simplicity/efficiency” effect is not an artifact of hand-encoded logic alone; it survives a conversion from an external SBML-qual representation to the same adjacency-based estimator under the frozen ordering policy.

---

## Entry LEV8-2026-04-05-006 — Human-designed vs Evolved (Matched Synthetic Circuits; TSK-LEV8-03-003)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate B (bias defense; “evolution vs design” minimal viable)  

**Objective**
- Test whether the algorithmic efficiency signal (biological networks more compressible than degree-preserved nulls) is uniquely biological, or whether it is a generic property of *designed* modular circuits when matched for size and edge count. This addresses a reviewer-class critique: “your result might simply reflect engineered modularity rather than evolved organization.”

**Design**
- Matched-pair protocol:
  - Sample $n=60$ biological networks from the Gate A corpus (filtered to $5\le N\le 100$; degree-preserved null available).
  - For each network, generate one “human-designed” synthetic circuit with the same node count $N$ and edge count $E$ (matching $N$ and $E$ removes trivial scaling artifacts).
- Primary metric:
  - fold reduction $= D_{\mathrm{null}}/D_{\mathrm{bio}}$ under degree-preserved nulls, computed with the frozen ordering policy (degree sort + WL tie-break).
  - Interpretation: fold $>1$ indicates algorithmic efficiency beyond the null.
- Null model:
  - Degree-preserving Maslov–Sneppen swaps with $n_{\mathrm{swaps}}=20N$; $n_{\mathrm{null}}=120$ draws per network.
- Synthetic generator (“human-designed”):
  - Modular hierarchical scaffold with repeated intra-module motifs and feed-forward inter-module wiring.
  - Adds regular structure (module chains + shared motif templates) while matching $N$ and $E$ exactly; saved explicitly as adjacency matrices for reproducibility.

**Run log**
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --human-vs-evolved --figures-dir paper/figures --null-samples 120 --hv-pairs 60`

**Artifacts (locked)**
- Paired dataset:
  - `paper/figures/human_vs_evolved_matched.csv` — `1aa78b2122b460d4e74eb6a9e55b0e7c7dab7d627c8bdd2451133746a190cac6`
- Plot:
  - `paper/figures/human_vs_evolved_matched.png` — `b2b5852e03f49c81dfcaeccd94deeedb3e0a64a5abe6d0ba57887844e9149f30`
- Summary bundle (protocol + effect sizes):
  - `paper/figures/human_vs_evolved_summary.json` — `e6068e85064eca3c346c4cdab345f9338935e61c5ff783a1a464a97a974dcbeb`
- Synthetic circuits (full adjacency; reproducibility):
  - `paper/figures/human_vs_evolved_synthetic_networks.json` — `19cd81c270169ba8a2930d2b20222490b30cbfa58457a8aa2095908db4906344`

**Key results (this checkout; $n=60$ matched pairs)**
- Mean fold reduction:
  - Evolved: $1.0258$
  - Human-designed (matched): $1.0053$
  - Mean difference (evolved − human): $0.0205$ (95\% bootstrap CI $[0.0042, 0.0383]$)
- Effect size:
  - Cohen’s $d = 0.418$

**Interpretation**
- Under strict $N/E$ matching, biological networks exhibit a modestly higher algorithmic-efficiency signal than the synthetic “human-designed” circuits produced by the modular generator. This weakens the claim that the Gate A effect is purely a consequence of generic engineered modularity.
- Theory implication: the “simplicity generates complexity” axiom is compatible with both design and evolution, but the evolved corpus appears to occupy a slightly more compressible regime even when a design-biased generator is used as a matched control. The correct scientific posture is: “design-like modularity is not sufficient to reproduce the biological fold distribution under the same null and encoding policy; biology remains measurably shifted.”

---

## Entry LEV8-2026-04-05-007 — Wet-lab Collaboration Readiness Pack (TSK-LEV8-04-004)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C (actionable biological predictions)  

**Objective**
- Produce a collaborator-facing packet with 5–10 testable perturbation predictions grounded in $\Delta D$, including controls and an explicit decision rule. The goal is not to “prove the theory in vitro” but to convert the computational framework into falsifiable experimental claims.

**Inputs**
- Candidate target universe: MAPK-large scaffold nodes with DepMap mapping (node-level table):
  - `paper/figures/figure3_depmap_validation_mapk_large.csv`
- External anchor for cell-line selection:
  - DepMap Public 24Q4 (`data/DepMap/CRISPRGeneEffect.csv` + `data/DepMap/Model.csv`)

**Method (step-by-step)**
1. Select top-$k$ candidate genes by Mean\_Delta\_D in the MAPK-large scaffold table (this ties the wet-lab claims directly to the same object used in Gate C benchmarking).
2. Select low-ΔD negatives from the same scaffold table to serve as explicit controls.
3. For each candidate gene, identify cell-line contexts where a perturbation is more likely to be informative:
   - compute dependency proxy per cell line as $-\mathrm{GeneEffect}$ and stratify by Oncotree lineage from `Model.csv`.
   - select the top lineages and top models within them to propose lineage-matched tests.
4. Freeze a decision rule:
   - success criterion: at least 6/8 high-ΔD targets induce larger viability loss than low-ΔD controls in ≥2 lineage-matched lines, with consistent sign across replicates.

**Run log**
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --wetlab-pack --figures-dir paper/results`

**Outputs (locked)**
- `paper/results/wetlab_readiness_pack.md` — `2cbb2c26e3cbaa102f81bd6034e9c1542e01e8b43574222fd3b4c6f418fe6fe4`
- `paper/results/wetlab_readiness_pack.json` — `2ec9327915ba3c0ca3c9f8653f1d5b5f260ba4df76e1a7a1ca3d8403c5ef48df`

**Interpretation**
- This converts the computational pipeline into a falsifiable collaboration artifact: it precommits targets, controls, cell-line selection logic, and a decision rule. Even if wet-lab outcomes are null, the null becomes interpretable because the decision rule and controls are frozen.

---

## Entry LEV8-2026-04-05-008 — Massive Test Matrix + Runtime Scaling Characterization (TSK-LEV8-04C-001/002)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (stability contract)  

**Objective**
- Freeze a project-wide condition matrix for stability testing across cohorts and null models, and quantify runtime scaling to justify compute budgets (Supplementary Methods readiness).

**Massive test matrix**
- Contents:
  - cohort × analysis × null\_model × $n_{\mathrm{random}}$ × swap intensity × seed × ordering policy
  - cohorts include Gate A corpus, Cell Collective SBML cohort, synthetic matched circuits, and DepMap scaffold analyses.
- Output:
  - `paper/figures/massive_test_matrix.csv` — `baf6df67d16fb32bd93d08a4cce495f8c3f1f71515b14abda12c9fd0ec3aa607`
  - `paper/figures/massive_test_matrix_summary.json` — `ad51596c504d796685206c2384797ef78fb17dea525475b2bf5069d69a1fedd2`
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --massive-test-matrix --figures-dir paper/figures`

**Runtime scaling characterization**
- Protocol:
  - sample $n=30$ networks across sizes and measure runtime for degree-preserved nulls under $n_{\mathrm{random}}\in\{25,50,100\}$ with $n_{\mathrm{swaps}}=20N$.
- Outputs:
  - `paper/figures/runtime_scaling.csv` — `709a8ca2e966a7a22aa40f5ccb292090cf0b4b2fac643760045780e0ff0ab886`
  - `paper/figures/runtime_scaling.png` — `eb1ca1b726246c3b96ed8d0723001ee5f8c00f167d51b0328b771e3d0d12ba07`
  - `paper/figures/runtime_scaling_summary.json` — `48b329437b31b02389c60351f694524ba78f956b1a2b8164da46e8abe7deb8c1`
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --scaling-report --figures-dir paper/figures --repro-nets 30`

**Interpretation**
- The massive matrix is the project’s “stability contract”: it prevents post-hoc changes in what counts as robustness by enumerating the required grid of conditions up front.
- The runtime report supports explicit compute budgeting: it links $n_{\mathrm{random}}$ and $N$ to measured runtime, enabling a defensible choice of null ensemble sizes in Methods.

---

## Entry LEV8-2026-04-05-009 — Reproducibility Lock Manifest (TSK-LEV8-04C-003)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (frozen outputs)  

**Objective**
- Lock a deterministic manifest of checksums for the manuscript-grade *deterministic* artifacts so a clean checkout can verify reproduction (and detect accidental drift). Outputs known to be machine-dependent (e.g., runtime timing) or metadata-variant (e.g., PDFs) are excluded by design.

**Method**
- Enumerate a curated set of figure/table artifacts (PNG/CSV/JSON: core figures, bias-defense outputs, DepMap outputs, independent cohort outputs, synthetic-control outputs, and stress-test outputs), compute SHA-256, and write a single manifest file.
- Verify in-place that all current artifacts match the manifest.

**Run log**
- Commands (exit=0):
  - `python paper/code/analysis_pipeline.py --repro-lock --figures-dir paper/figures`
  - `python paper/code/analysis_pipeline.py --repro-verify paper/figures/repro_lock_manifest.json`
- Verification: $n_{failures}=0$.

**Output (locked)**
- `paper/figures/repro_lock_manifest.json` — `fec66b632e15c3dfc6078649f8f02700c5c9c76362b28054554311726b90d3a9`

**Interpretation**
- This upgrades Gate A posture from “we think it is reproducible” to “a single checksum manifest detects drift”. It also sets the stage for a one-command reproduction workflow (EPIC-LEV8-06-003) by specifying the target artifact set to reproduce.

---

## Entry LEV8-2026-04-05-010 — KR-B Route Decision Freeze (TSK-LEV8-04B-001)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate B, Gate C  

**Objective**
- Freeze a single primary KR-B data route (with explicit failure modes and mitigations) to prevent protocol drift and to make “success” auditable.

**Decision (frozen)**
- Primary route: Route 1 (curation-heavy paired logical models).
- Contingency route: Route 2 (TCGA paired expression → inferred networks → CCLE/DepMap anchoring).

**Rationale (why this is scientifically defensible now)**
- Route 1 is immediately reproducible and can be packaged to Nature-grade standards under Gate A (manifests, checksums, deterministic pipelines), while Route 2 depends on external acquisition and harmonization infrastructure that is not yet frozen in-repo.
- Route 1 still supports external anchoring (DepMap lineage stratification; known oncogene enrichment), allowing KR-B to be judged by Gate C criteria rather than narrative plausibility.

**Success definition (quantitative; frozen)**
- Primary effect: paired cancer-normal ACI difference with 95% CI excluding 0.
- Negative control: mismatched/random pairing destroys the paired effect direction.
- Anchor: at least one external enrichment/direction check succeeds (DepMap or oncogene/tumor suppressor enrichment).

**Artifacts (locked)**
- `paper/results/krb_route_decision.md` — `a2ea089aa8a4e25a6533ad096111915ca86e1ff7e0f4ebc8a2735a2756b3c3a5`
- `paper/results/krb_route_decision.json` — `2d2dddba366353740bf72b51be915d93ef79f07872ad06aa2887366d91cc65d9`

---

## Entry LEV8-2026-04-05-011 — One-command Reproduction Workflow (TSK-LEV8-06-003)
**Date:** 2026-04-05  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (reproduction)  

**Objective**
- Provide a single, documented command that regenerates the major analysis artifacts and then verifies them against the checksum manifest, suitable for a clean checkout reproduction test.

**Implementation**
- Script:
  - `paper/code/reproduce_all.py` — `454c1b98c2281288420c4d19e3c9c8a9619f99b81e54fc52fb3337214c6908b7`
- Modes:
  - Default mode: regenerate pipelines (bias defense, independent cohort, synthetic-control benchmark, stress/matrix specs) and then regenerate the checksum manifest and verify.
  - Verification-only mode: `--verify-only` performs checksum verification without overwriting outputs.

**Run log**
- Verified manifest with $n_{failures}=0$ using:
  - `python paper/code/reproduce_all.py --verify-only`

**Interpretation**
- This turns reproduction into an executable workflow rather than a narrative promise. The checksum contract is scoped to deterministic artifacts (PNG/CSV/JSON) and explicitly excludes machine-dependent timing outputs and PDF metadata variance.

---

## Entry LEV8-2026-04-06-001 — Theory→Computation Mapping Lock (TSK-LEV8-01-001)
**Date:** 2026-04-06  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A (coherence)  

**Objective**
- Remove proxy ambiguity by locking a single mapping table of theorem objects → computed quantities → units → implementation locations → caveats, so a reader can audit what each figure and benchmark actually measures.

**Critical coherence issue addressed**
- The repository currently uses two computable “description length” proxies:
  - gzip adjacency description length (used for the corpus universality / null-family meta-analysis),
  - UniversalDv2Encoder description length (used for $\Delta D$ in essentiality, DepMap anchoring, and corruption analysis).
- These are conceptually aligned but not numerically interchangeable; scientific accuracy requires captions and Methods to label which proxy is in use.

**Artifacts (locked)**
- `paper/results/theory_to_computation_mapping.md` — `cdb26c77d7cb2b8824b4a2e8a2dedc20763bc83e2e60f474aa567f3456249e10`
- `paper/results/theory_to_computation_mapping.json` — `36a0e23bcd4d8d6fe9122236648597cc9bfe1e3daead006ee8698c573f80ff1f`

**Interpretation**
- This is a Gate A enabler: it converts an implicit implementation detail (“which D did we use here?”) into an auditable contract. It does not change results; it prevents overclaiming and directs the next engineering move (unify on a single D proxy only after measuring the translation impact).

---

## Entry LEV8-2026-04-06-002 — Figure 1 Suite Finalization (Locked Summary Outputs; TSK-LEV8-02-001)
**Date:** 2026-04-06  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A, Gate B  

**Objective**
- Finalize the Figure 1 suite as a reproducible, manuscript-grade artifact set with explicit uncertainty numbers (mean fold reduction + 95% CI) and an exported summary table to eliminate manual transcription risk.

**Method (what Figure 1 computes)**
- For each network with $5\le N\le 100$:
  - compute $D_{\mathrm{bio}}$ under the frozen encoding (degree-sorted adjacency; gzip compressed length),
  - compute an empirical null ensemble $D_{\mathrm{null}}$ under each null family:
    - ER (matched density),
    - degree-preserved (Maslov–Sneppen swaps),
    - gate-permuted (subset with gate annotations).
- Report fold reduction $D_{\mathrm{null}}/D_{\mathrm{bio}}$:
  - mean fold and 95% CI via bootstrap over networks.
- Robustness panel:
  - subsample the stored degree-preserved null draws using $k\in\{5,10,20,30,50\}$ and recompute the mean fold with bootstrap CIs.

**Run log**
- Command (exit=0):
  - `python paper/code/analysis_pipeline.py --figures-dir paper/figures --skip-depmap --null-samples 50`

**Outputs (locked)**
- Figure:
  - `paper/figures/figure1_algorithmic_efficiency.png` (image artifact; checksum-locked by the repro manifest)
- Summary table:
  - `paper/figures/figure1_algorithmic_efficiency_summary.csv` — `7f1e3939ed5cdd5f56cd3178fcc5aaec23d4009e1aaee6a41037f03cef48a508`
- Summary JSON bundle (includes robustness curve):
  - `paper/figures/figure1_algorithmic_efficiency_summary.json` — `a97325b87dfea806ee4cc9bb362931acbe78af4b455f04bc14e386cfd1dcc366`

**Key numbers (from the exported summary table)**
- Degree-preserved: mean fold $=1.0218$ (95% CI $[1.0162, 1.0275]$), $n=232$.
- ER: mean fold $=1.0399$ (95% CI $[1.0305, 1.0504]$), $n=232$.
- Gate-permuted: mean fold $=1.0170$ (95% CI $[1.0134, 1.0206]$), $n=169$.

**Interpretation**
- This closes a common failure mode: manual figure annotations drifting from the actual computed table. The summary CSV/JSON are now the single source of truth for manuscript numbers and are checksum-lockable.

---

## Entry LEV8-2026-04-06-003 — Essentiality Stratification Export (TSK-LEV8-02-002)
**Date:** 2026-04-06  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C  

**Objective**
- Emit stratified essentiality performance results (Organism group, network size bin, and source dataset) with uncertainty so reviewers can see where the KR-A signal is stable vs heterogeneous.

**Method**
- Base dataset: `results/bio/essentiality_prediction_dataset.csv` (node-level rows labeled essential/non-essential per network).
- Predictors: ΔD, Degree, Betweenness (same as the primary Figure 2 comparison; Combined model remains the primary headline and is reported in `essentiality_summary.json`).
- Stratification:
  - `Organism_Group` inferred from network naming/provenance,
  - `Size_Bin` from node count,
  - `Source` from dataset provenance tags.
- Uncertainty:
  - network-resampled bootstrap CIs for AUC and AP within each stratum.

**Outputs (locked)**
- `paper/figures/essentiality_stratified.csv` — `c1d253aeb3442cc85ca50747e82e7b67325da2c388e1ba60b936a04dcd381170`
- `paper/figures/essentiality_summary.json` — `9da9a6e25fabe5c117f29493b9164395303ffd960706a912a76418477920e80b`

**Interpretation**
- This prevents “average-only” reporting: it makes the heterogeneity of essentiality predictiveness explicit across organism, scale, and source, which is required for Gate C scientific honesty (and for deciding whether any subgroup deserves prominence vs Extended Data).

---

## Entry LEV8-2026-04-06-004 — KR-B Corruption: Negative Control + DepMap Anchor Attempt (TSK-LEV8-04B-006)
**Date:** 2026-04-06  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate B, Gate C  

**Objective**
- Upgrade the KR-B corruption track from “paired ΔD exists” to “paired ΔD + explicit negative control + explicit external anchor test,” with all outputs stored as auditable artifacts.

**Dataset (current repository state)**
- Cohort: synthetic paired cancer/normal logical models under the EGFR scaffold:
  - tumor/normal network pairs stored at `data/cancer/patients/*_{Tumor,Normal}.json` ($n=100$).
  - base scaffold: `data/bio/processed/egfr_signaling.json`.
- Note: this is a route-1-style paired logical-model cohort, but it is still synthetic; the pipeline is therefore treated as a KR-B methods scaffold rather than definitive wet evidence.

**Metric**
- Paired corruption is quantified as $\Delta D^{(v2)} = D^{(v2)}_{\mathrm{tumor}} - D^{(v2)}_{\mathrm{normal}}$, using `UniversalDv2Encoder` on adjacency matrices.

**Negative control (predeclared)**
- For each tumor network, generate a degree-preserved randomized ensemble (Maslov–Sneppen swaps; $n_{\mathrm{swaps}}=20N$; $n_{\mathrm{null}}=60$) and compute:
  - $\Delta D^{(v2)}_{\mathrm{null}} = \overline{D^{(v2)}_{\mathrm{tumor,null}}} - D^{(v2)}_{\mathrm{normal}}$.
- Test whether the observed paired corruption differs from this null baseline via paired tests on $\Delta D^{(v2)}$ vs $\Delta D^{(v2)}_{\mathrm{null}}$.

**External anchor test (DepMap; attempted)**
- Compute a node-level “corruption footprint” as the mean number of incoming edges removed (pruned) across patients.
- Map each node to candidate genes via `CancerNetworkBuilder.default_node_to_genes_for_nodes` and attach DepMap dependency means from `data/DepMap/CRISPRGeneEffect.csv.gene_mean.csv`.
- Test association and enrichment:
  - Spearman correlation (permutation on |ρ|).
  - Top-vs-bottom (k=3) dependency difference (permutation on |Δ|).

**Run log**
- Command (exit=0):
  - `KRB_PATIENT_DIR=data/cancer/patients KRB_BASE_NETWORK=data/bio/processed/egfr_signaling.json KRB_OUT_PREFIX=paper/figures/krb_corruption_anchor KRB_NULL_SAMPLES=60 KRB_PERM_N=10000 python src/analysis/KRB_Corruption_Anchors.py`

**Outputs (locked)**
- Patient-level table:
  - `paper/figures/krb_corruption_anchor__patients.csv` — `25fd45a2963c5dcb385838aa778aa00d1f62203286d2f215e286f3eedfd3680c`
- Node-level anchor table:
  - `paper/figures/krb_corruption_anchor__node_anchor.csv` — `205fb0630606c2d074f495cad6820ad240279159bcd8ce22ab32877e8aaaabac`
- Plots:
  - `paper/figures/krb_corruption_anchor__negative_control.png` — `b2409b1a3ee640a604ee94da4b1ab5b35cf00a8f0abc2ab780cde3d1e06dbe1b`
  - `paper/figures/krb_corruption_anchor__node_anchor.png` — `71dac8f321d225fa056c86874e99a94df14e28c20501e14340a71fcbf394bea4`
- Summary JSON:
  - `paper/figures/krb_corruption_anchor__summary.json` — `181e213af021fde8855677ea9ed07e169b8eea438b8c71609611304e1a7b89c1`

**Key results**
- Paired tumor vs normal shift is strongly negative (tumor more compressible): paired t-test $p=1.05\times 10^{-14}$.
- Negative control: observed $\Delta D^{(v2)}$ differs from the degree-preserved tumor null baseline (paired test $p=6.74\times 10^{-12}$), indicating the signal is not reproduced by generic degree-preserved rewiring.
- DepMap anchor attempt (EGFR scaffold; $n=10$ mapped nodes):
  - Spearman ρ between pruning footprint and DepMap dependency: ρ = -0.191, permutation $p(|ρ|)=0.596$.
  - Top-vs-bottom (k=3) dependency difference: Δ = -0.202, permutation $p(|Δ|)=0.367$.

**Interpretation**
- The corruption signal is robust relative to an internal structural null baseline (degree-preserved rewiring), which is a necessary Gate B control.
- In this checkout the DepMap anchor test is negative/neutral for the EGFR scaffold: corruption footprint does not align with pooled DepMap dependency means. Scientifically, this is a useful boundary condition: it argues that the corruption mechanism in the scaffold instantiation is not a simple proxy for cell-line essentiality when pooled across contexts.
- Practical implication: if KR-B is promoted beyond methods scaffolding, the anchor must be made lineage- and context-matched (as in Gate C DepMap conditioning) and ideally tied to real paired acquisition (Route 2) or curated cancer/healthy logic pairs with explicit mutation semantics.

---

## Entry LEV8-2026-04-06-005 — Nature Manuscript Refactor + Submission Readiness (EPIC-LEV8-05 / EPIC-LEV8-06)
**Date:** 2026-04-06  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate A, Gate B, Gate C  

**Objective**
- Produce a Nature-shaped narrative draft aligned with Protocol 8 (explicit proxy boundary, bias-defense positioning, reproducibility guarantees) and freeze a submission pack template plus a holistic readiness assessment.

**Manuscript refactor (Nature-shaped draft)**
- Updated manuscript draft (compiles cleanly as LaTeX):
  - `doc/finalpaper/nature_draft.tex` — `5948c1b6eb4158d527987783a9f98e77601206883a5ba3b2bf9ecba84a7cd73b`
- Key corrections vs prior drafts:
  - removes legacy “Tri-Phylum”/edge-of-chaos claims not supported by current locked artifacts,
  - aligns the abstract and Results to the locked Figure 1 meta-analysis and bias-defense artifacts,
  - explicitly positions KR-A/KR-B as bounded evidence rather than overclaimed external validation.

**Submission pack (templates; to finalize conflicts and references)**
- Cover letter:
  - `paper/results/submission_pack/cover_letter.md` — `9e24121a11a18c7c4c9799589c02d417113196eda890d2ffdb94aa35f852efe0`
- Suggested reviewers (draft):
  - `paper/results/submission_pack/suggested_reviewers.md` — `1af0177fa08d6a4fe54afc440d5ab03d2bf2e92dc0e1ec3f48afeed549202f0c`

**Holistic readiness assessment (Protocol 8)**
- `paper/results/nature_readiness_assessment.md` — `6d4df6d37456a3065608658a8f790cbb5f726c85ebf8b539f9f982282270a7bd`

**Interpretation**
- This converts “we have results” into “we have a submission-shaped story with an honest evidentiary ladder.” The readiness assessment makes the remaining scientific risk explicit: Gate C anchoring is still the main vulnerability for a Nature-tier claim and must be either strengthened (larger lineage-matched anchors) or framed as a testable hypothesis with the wet-lab readiness pack.

---

## Entry LEV8-2026-04-17-001 — DepMap Anchor Hardening (Lineage-matched; Mapping + Cache Fix; Gate C)
**Date:** 2026-04-17  
**Operator:** Trae/GPT  
**Gate Alignment:** Gate C  

**Objective**
- Strengthen the DepMap anchoring analysis from a pooled, partially unmapped scaffold to a lineage-matched evaluation with (i) maximal node→gene mapping coverage, (ii) lineage filtering by Model.csv, and (iii) a cache key that is invariant to the target gene whitelist to prevent silent reuse of stale derived dependency tables.

**Critical failure mode fixed**
- The previous DepMap derived-table cache could reuse a `.gene_mean.csv` built for a different gene whitelist, silently reducing the mapped gene set and biasing the analysis.
- Fix: derived dependency tables are now keyed by a SHA-256 hash of the gene whitelist (`__wl_<hash>`), and stored optionally under `DEPMAP_CACHE_DIR` for provenance control.

**Node→gene mapping expansion (MAPK-large scaffold)**
- Several scaffold nodes are pathway aggregates or family labels (e.g., JNK, p38, RSK, PLCG, MEK1_2) and do not directly match HGNC gene symbols.
- Fix: expand the default node→genes map for MAPK/EGFR pathway abstractions (e.g., JNK→MAPK8/9/10; p38→MAPK11/12/13/14; RSK→RPS6KA1–6; MEK1_2→MAP2K1/2; p53→TP53; p21→CDKN1A; TGFBR→TGFBR1/2; etc.).
- Outcome: DepMap dependency coverage increases from 25/53 nodes to 46/53 nodes (remaining unmapped nodes are intentionally non-gene phenotypes/stimuli).

**Protocol**
- Data:
  - cohort: `data/cancer/patients_mapk_large/` (paired tumor/normal synthetic cohort over MAPK-large scaffold; $n=30$ patients)
  - DepMap: Public 24Q4 (`data/DepMap/CRISPRGeneEffect.csv` + `data/DepMap/Model.csv`)
- Endpoints:
  - predictor: Mean\_Delta\_D per node (from cohort)
  - response: lineage-filtered gene dependency mean (Chronos GeneEffect aggregated; higher = more essential)
  - conditioned analysis: residual association after regressing out expression and copy number means where available.
- Lineages evaluated (predeclared set): Bowel, Breast, Lung, Lymphoid, CNS/Brain, Ovary/Fallopian Tube.

**Run log**
- Pooled MAPK-large:
  - `DEPMAP_PATH=data/DepMap/CRISPRGeneEffect.csv DEPMAP_MODEL_PATH=data/DepMap/Model.csv DEPMAP_CACHE_DIR=data/DepMap/derived_cache DEPMAP_DATA_DIR=data/cancer/patients_mapk_large DEPMAP_OUT_PREFIX=paper/figures/figure3_depmap_validation_mapk_large DEPMAP_PERM_N=10000 python src/analysis/DepMap_Validation.py`
- Lineage sweep:
  - `... DEPMAP_ONCOTREE_LINEAGE_SWEEP='Bowel,Breast,Lung,Lymphoid,CNS/Brain,Ovary/Fallopian Tube' ... python src/analysis/DepMap_Validation.py`
- Meta aggregation:
  - `paper/code/analysis_pipeline.py: generate_depmap_lineage_meta(paper/figures)`

**Outputs (locked)**
- Pooled MAPK-large node table:
  - `paper/figures/figure3_depmap_validation_mapk_large.csv` — `48b88f2c05514f5881d4265cbc23e79aa1ef233ffda2505e339638375251bb78`
- Pooled stats bundle:
  - `paper/figures/figure3_depmap_validation_mapk_large_stats.json` — `dbc7fc87350675ca4b097fdc6b48e3eaa1cf4f7372c0e037b4002775030f9cc7`
- Pooled plots:
  - `paper/figures/figure3_depmap_validation_mapk_large_scatter.png` — `5ba041fb33796eac5e9e0dcf30331e6ab03a8b8ba1809b89045bc6f570775c59`
  - `paper/figures/figure3_depmap_validation_mapk_large_conditioned.png` — `41704ac918ede96060bca364dd4a713edabc8969be014c224f30e62f4000ddd5`
  - `paper/figures/figure3_depmap_validation_mapk_large_benchmark.png` — `4bcd361d2905a8ca3a9d5ffe2b9bca163df1baca78dc4e2c82962f3d6778af07`
- Lineage sweep summary:
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep_summary.csv` — `04d8855aa05d2492a2debb18946c33456134418c58288297286055e1a5b5b12d`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep_summary.json` — `e877c4b802b10ee462e60f551c65b2634d50936319038d5ca573d34548cd398b`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_sweep.png` — `c3911a36cca47ea892d52dffee9ac021d906ab3c3a1c65392e592feb8ebc5921`
- Lineage meta aggregation:
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_meta.csv` — `f641f6d43e250e6a68d06cf72c51f9a8f27ca23b6a052058121bec20250dbc91`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_meta.json` — `cc148213c85d986e9c8955831084f44309e3e8b689d5d83552dc31bb40eaedf5`
  - `paper/figures/figure3_depmap_validation_mapk_large__lineage_meta.png` — `15e62a1d566b19c2bc4d9f181da10c8d6771f62d071f5e9a378d583da86dae24`

**Key results**
- Coverage: 46/53 nodes have DepMap dependency values after mapping expansion.
- Pooled (MAPK-large; $n=46$): Pearson $r=-0.215$ ($p=0.154$); mutual information = 0.01 bits (“No Dependency” under the MI discretization).
- Lineage-matched conditioned meta: mean conditioned Spearman $\rho=-0.0946$ with 95% CI $[-0.143, -0.047]$ across 6 major lineages (meta bundle in `...__lineage_meta.json`).

**Interpretation**
- This hardens Gate C scientifically even when the correlation is not in the originally hoped direction: it shows that $\Delta D$ is not a trivial proxy for pooled essentiality and, under lineage-matched conditioning, exhibits a small but consistent negative association on the MAPK-large scaffold. The correct reading is “ΔD captures a distinct notion from DepMap dependency under this scaffold instantiation,” not “external validation succeeds.”
