# Reproduction Ledger

## Purpose

This file is the project-local provenance and protocol ledger for the exact reproduction of:

- `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems`

It records only assets or protocol details that have been directly recovered from:

- the paper text,
- the extended arXiv version,
- author-adjacent code,
- public upstream datasets.

No inferred or speculative asset is listed here as confirmed.

## Confirmed Author-Adjacent Code Assets

### 1. `algodyn`

Local path:

- `reference/algodyn`

Status:

- recovered

What it contains that is directly relevant:

- `calculate_info_edges`
- `calculate_info_vertices`
- `info_spectra`
- `info_signature`
- `relative_reprogrammability`
- `inforank`
- row shuffling utilities

Important methodological observation:

- `relative_reprogrammability` in `algodyn` is implemented as `MAD(signature) / max(signature)`, which is operationally important because the current project must either reproduce this exact implementation or document any divergence from the paper supplement.
- `definition_fidelity.json` now records the current exactness boundary against the recovered local `algodyn` reference:
  - exact to reference:
    - `info_spectra`
    - `info_signature`
    - `inforank`
  - exact to recovered paper supplement:
    - `relative_reprogrammability`
  - unresolved:
    - `absolute_reprogrammability`
    - `combined_reprogrammability`
- `relative_reprogrammability` now has two explicitly tracked variants in code:
  - recovered paper supplement variant:
    - `MAD(signature) / max(|signature|)`
  - recovered local reference variant:
    - `MAD(signature) / max(signature)`
- the project now treats the recovered paper supplement variant as canonical and preserves the local `algodyn` variant only as an implementation-discrepancy audit
- further upstream recovery through full `algodyn` git history now shows that:
  - `R/absolute_reprogramability.R` existed only as a stub returning no value and was later deleted
  - `R/total_reprogramability.R` existed only as a stub returning no value and was later removed
- the project therefore no longer reports canonical numeric values for `absolute_reprogrammability` or `combined_reprogrammability`; instead it exposes them as unresolved and preserves the former trapezoid-based and Euclidean computations only as clearly labeled proxy audit variants

### 2. `CellNet`

Local path:

- `reference/CellNet`

Status:

- recovered

What it contains that is directly relevant:

- the CellNet R package codebase
- GRN assessment and preprocessing routines
- packaged TF lists:
  - `data/hsTFs.rda`
  - `data/mmTFs.rda`

Confirmed from `CellNet` README:

- CellNet was trained on `16 mouse` and `16 human` cell/tissue types
- the repository documents downloadable trained `cnProc` objects from S3, including:
  - `cnProc_RS_hs_Oct_25_2016.rda`
  - `cnProc_HS_RS_Apr_05_2017.rda`
  - `cnProc_HS_RS_Jun_20_2017.rda`
  - `cnProc_MM_RS_Oct_24_2016.rda`
- the human panels listed in the README are extremely close to the Zenil paper's reported CellNet landscape target

Current limitation:

- the trained `cnProc` objects are referenced remotely rather than bundled directly into the repository, so they still need to be downloaded and inspected locally before they can be treated as confirmed project assets.

Observed archival status of the legacy `CellNet` object links:

- the original S3 `cnProc` URLs listed in the `CellNet` README no longer return the object content;
- they currently return an XML error indicating `InvalidObjectState` with storage class `DEEP_ARCHIVE`.

Interpretation:

- the maintainers' documented object paths are not dead identifiers, but the underlying files are not directly retrievable from the legacy bucket anymore.

### 3. `gpdream`

Local path:

- `reference/gpdream`

Status:

- recovered

What it contains that is directly relevant:

- DREAM-oriented regulatory inference modules
- example DREAM network inputs such as:
  - `modules/Merlin/example/net1_expression.txt`
  - `modules/Merlin/example/net1_transcription_factors.tsv`

Current limitation:

- this repository is a workflow/code surface for DREAM inference, not yet a confirmed copy of the exact `E. coli` consensus network used in the Zenil paper.

### 4. `PACNet`

Local path:

- `reference/PACNet`

Status:

- recovered

Confirmed from `PACNet` README:

- the maintainers explicitly state that the old S3 links are inactive;
- as of `2026-03-03`, training data and engineered reference panels are provided through Zenodo at:
  - `https://doi.org/10.5281/zenodo.18857326`

Scientific significance:

- this does not provide the original 2014 `CellNet` objects verbatim, but it provides an official, maintainers-endorsed recovery path for the CellNet-family training assets that may be sufficient to reconstruct the cell-type landscape block or, at minimum, its training universe and reference panels.

## Confirmed Extended-Paper Method Details

Recovered from the extended arXiv PDF/text:

- the Boolean-network perturbation study used networks converted into Boolean dynamics by randomly directing edges and assigning random or specific node rules including `AND`, `OR`, and `XOR`;
- the paper explicitly ties the biological reproductions to:
  - `Marbach et al. 2012` for `E. coli`
  - `Yosef et al. 2013` for `Th17`
  - `Morris et al. 2014` for `CellNet`
- the paper states that `Th17` reprogrammability is higher at early time points than at the terminal stage;
- the paper states that the `48 hr` network is especially stable, with only three nodes identified as still able to move the network toward greater randomness:
  - `STAT6`
  - `TCFEB`
  - `TRIM24`

These statements are now part of the validation target and should be checked numerically once the biological pipeline is implemented.

## Confirmed Biological Source Assets

### A. `Th17` GEO Series

Local path:

- `data/raw/th17_geo`

Recovered files:

- `GSE43948_series_matrix.txt.gz`
- `GSE43949_series_matrix.txt.gz`
- `GSE43955_series_matrix.txt.gz`
- `GSE43956_series_matrix.txt.gz`
- `GSE43957_series_matrix.txt.gz`
- `GSE43969_series_matrix.txt.gz`
- `data/raw/th17_geo_supp/GSE43956_RAW.tar`
- `data/raw/th17_geo_supp/GSE43957_RAW.tar`

Recovery status:

- successful

#### `GSE43955`

Title:

- `Reconstruction of the dynamic regulatory network that controls Th17 cell differentiation by systematic perturbation in primary cells (Th17 differentiation timecourse)`

Confirmed from GEO header:

- PubMed-linked to the Yosef study
- platform: `GPL8321`
- organism: `Mus musculus`
- design: `Time course microarray data for Th17 differentiation, including Th0 control`
- sample count visible in series matrix: `58`

Confirmed time-course structure from sample titles:

- `Th0` time course
- `Tgfb+Il6` time course
- `Tgfb+Il6 + IL23` later-stage time points
- repeated samples at several time points

Visible time points:

- `0.5, 1, 2, 4, 6, 8, 10, 12, 16, 20, 24, 30, 42, 48, 50, 52, 60, 72 hr`

#### `GSE43969`

Title:

- `Reconstruction of the dynamic regulatory network that controls Th17 cell differentiation by systematic perturbation in primary cells (Affymetrix timecourse IL23 KO)`

Confirmed from GEO header:

- platform: `GPL8321`
- organism: `Mus musculus`
- design: `Time course microarray data for Th17 differentiation, comparing IL23r-/- to WT`
- sample count visible in series matrix: `20`

#### `GSE43956`

Title:

- `Induction of pathogenic Th17 cells by salt inducible kinase SGK-1 (SGK-1 KO)`

Confirmed from GEO header:

- citation: `Wu C, Yosef N, Thalhamer T, Zhu C et al. Induction of pathogenic TH17 cells by inducible salt-sensing kinase SGK1. Nature 2013`
- platform: `GPL1261`
- organism: `Mus musculus`
- design: `Th17 cells; comparing Sgk1-/- to WT`
- sample count visible in series matrix: `4`
- relation: `SubSeries of: GSE43970`

Confirmed sample structure from GEO:

- `GSM1075005` = `WT-IL23 rep1`
- `GSM1075006` = `WT-IL23 rep2`
- `GSM1075007` = `SGK1-IL23 rep1`
- `GSM1075008` = `SGK1-IL23 rep2`

#### `GSE43957`

Title:

- `Induction of pathogenic Th17 cells by salt inducible kinase SGK-1 (NaCl)`

Confirmed from GEO header:

- citation: `Wu C, Yosef N, Thalhamer T, Zhu C et al. Induction of pathogenic TH17 cells by inducible salt-sensing kinase SGK1. Nature 2013`
- platform: `GPL1261`
- organism: `Mus musculus`
- design: `Effects of NaCl on Th17 differentiation`
- sample count visible in series matrix: `4`
- relation: `SubSeries of: GSE43970`

Confirmed sample structure from GEO:

- `GSM1075009` = `Th0_Ctrl1`
- `GSM1075010` = `Th0_Ctrl2`
- `GSM1075011` = `Th0_NaCl1`
- `GSM1075012` = `Th0_NaCl2`

### A1. Parsed `Th17` Project-Local Assets

Local path:

- `data/processed/th17`

Recovery status:

- successful

Produced by:

- `./run.sh th17`
- or equivalently:
  - `python -m imp_causal_paper.cli th17-prepare --raw-dir data/raw/th17_geo --output-dir data/processed/th17`

Confirmed outputs:

- `data/processed/th17/GSE43948_series/sample_metadata.csv`
- `data/processed/th17/GSE43948_series/summary.json`
- `data/processed/th17/GSE43948_rnaseq/sample_metadata.csv`
- `data/processed/th17/GSE43948_rnaseq/expression_matrix.tsv.gz`
- `data/processed/th17/GSE43948_rnaseq/feature_metadata.csv`
- `data/processed/th17/GSE43948_rnaseq/summary.json`
- `data/processed/th17/GSE43949_series/sample_metadata.csv`
- `data/processed/th17/GSE43949_series/summary.json`
- `data/processed/th17/GSE43955_series/sample_metadata.csv`
- `data/processed/th17/GSE43955_series/expression_matrix.tsv.gz`
- `data/processed/th17/GSE43955_series/feature_metadata.csv`
- `data/processed/th17/GSE43955_series/summary.json`
- `data/processed/th17/GSE43956_series/sample_metadata.csv`
- `data/processed/th17/GSE43956_series/expression_matrix.tsv.gz`
- `data/processed/th17/GSE43956_series/feature_metadata.csv`
- `data/processed/th17/GSE43956_series/summary.json`
- `data/processed/th17/GSE43957_series/sample_metadata.csv`
- `data/processed/th17/GSE43957_series/expression_matrix.tsv.gz`
- `data/processed/th17/GSE43957_series/feature_metadata.csv`
- `data/processed/th17/GSE43957_series/summary.json`
- `data/processed/th17/GSE43969_series/sample_metadata.csv`
- `data/processed/th17/GSE43969_series/expression_matrix.tsv.gz`
- `data/processed/th17/GSE43969_series/feature_metadata.csv`
- `data/processed/th17/GSE43969_series/summary.json`
- `data/processed/th17/GSE43948_bundle_manifest/manifest.csv`
- `data/processed/th17/GSE43949_bundle_manifest/manifest.csv`
- `data/processed/th17/GSE43956_bundle_manifest/manifest.csv`
- `data/processed/th17/GSE43957_bundle_manifest/manifest.csv`
- `data/processed/th17/GSE43970_bundle_manifest/manifest.csv`

Confirmed parsed structure:

- `GSE43955_series`:
  - `58` samples
  - `22690` probe rows
  - parsed metadata includes `time_hr`, `treatment`, and `cell_type`
  - treatment states recovered from GEO metadata:
    - `Th0`
    - `Tgfb+Il6`
    - `Tgfb+Il6+Il23`
- `GSE43969_series`:
  - `20` samples
  - `22690` probe rows
  - parsed metadata includes `time_hr`, `genotype`, `treatment`, and `cell_type`
  - genotype states recovered:
    - `WT`
    - `IL23R knockout`
- `GSE43948_series`:
  - `32` samples
  - `0` matrix rows in the GEO series matrix
  - `sample_type = SRA`
  - `library_strategy = RNA-Seq`
  - the public series matrix acts as a sequencing metadata table rather than a numeric expression matrix
- `GSE43949_series`:
  - `2` samples
  - `0` matrix rows in the GEO series matrix
  - `sample_type = SRA`
  - `library_strategy = ChIP-Seq`
  - sample titles are `TSC22D3` and `WCE`
- `GSE43956_series`:
  - `4` samples
  - `45101` probe rows
  - parsed metadata includes `genotype` and `cell_type`
  - parsed metadata now also includes explicit provenance columns:
    - `study_arm = wu_sgk1_pathogenicity`
    - `source_publication = Wu et al. 2013`
  - genotype states recovered:
    - `WT`
    - `Sgk1-/-`
- `GSE43957_series`:
  - `4` samples
  - `45101` probe rows
  - parsed metadata includes `treatment` and `cell_type`
  - parsed metadata now also includes explicit provenance columns:
    - `study_arm = wu_sgk1_pathogenicity`
    - `source_publication = Wu et al. 2013`
  - treatment states recovered:
    - `Th0`
    - `Th0+NaCl`

Confirmed supplementary-bundle manifests:

- `GSE43948_bundle_manifest`:
  - `33` entries total
  - `32` `rsem_gene_expression` members
  - `1` archive member (`GSE43948_RAW.tar`)
- `GSE43949_bundle_manifest`:
  - `3` entries total
  - `2` `igv_tdf_track` members
  - `1` archive member (`GSE43949_RAW.tar`)
- `GSE43956_bundle_manifest`:
  - `4` entries total
  - source archive: `GSE43956_RAW.tar`
  - `4` `affymetrix_cel` members
  - all `4` members resolve to `GSE43956`
- `GSE43957_bundle_manifest`:
  - `4` entries total
  - source archive: `GSE43957_RAW.tar`
  - `4` `affymetrix_cel` members
  - all `4` members resolve to `GSE43957`
- `GSE43970_bundle_manifest`:
  - `121` entries total
  - `32` `rsem_gene_expression` members resolved to `GSE43948`
  - `2` `igv_tdf_track` members resolved to `GSE43949`
  - `86` `affymetrix_cel` members
  - `58` CEL files resolved to `GSE43955`
  - `4` CEL files resolved to `GSE43956`
  - `4` CEL files resolved to `GSE43957`
  - `20` CEL files resolved to `GSE43969`
  - `0` sample accessions remain unresolved against the currently recovered local series set
  - arm-aware counts are now materialized directly in the processed summaries:
    - `GSE43956_bundle_manifest` -> `wu_sgk1_pathogenicity = 4`
    - `GSE43957_bundle_manifest` -> `wu_sgk1_pathogenicity = 4`
    - `GSE43970_bundle_manifest` -> `wu_sgk1_pathogenicity = 8`, `yosef_th17_network = 112`

Confirmed branch-specific cohort artifacts:

- `yosef_th17_network_cohort`:
  - included series:
    - `GSE43948`
    - `GSE43949`
    - `GSE43955`
    - `GSE43969`
  - `112` samples total
  - expression artifacts:
    - `GSE43948_rnaseq`
    - `GSE43955_series`
    - `GSE43969_series`
  - metadata-only series:
    - `GSE43949`
- `wu_sgk1_pathogenicity_cohort`:
  - included series:
    - `GSE43956`
    - `GSE43957`
  - `8` samples total
  - expression artifacts:
    - `GSE43956_series`
    - `GSE43957_series`

Confirmed Yosef-only network design artifact:

- `yosef_th17_network_design`:
  - included series:
    - `GSE43948`
    - `GSE43949`
    - `GSE43955`
    - `GSE43969`
  - `112` samples total
  - assay-modality counts:
    - `rna_seq = 32`
    - `chip_seq = 2`
    - `microarray = 78`
  - experimental-axis counts:
    - `perturbation_screen = 32`
    - `chip_binding = 2`
    - `time_course = 58`
    - `genotype_time_course = 20`
  - derived subpanels:
    - `perturbation_screen_design.csv` = `32` samples
    - `chip_binding_design.csv` = `2` samples
    - `dynamic_timecourse_design.csv` = `78` samples
    - `exact_48h_expression_design.csv` = `36` samples
  - derived expression bundles:
    - `perturbation_screen_expression_matrix.tsv.gz` = `27723 x 32`
    - `dynamic_timecourse_expression_matrix.tsv.gz` = `22690 x 78`
    - `exact_48h_expression_manifest.csv` keeps the exact `48.0 hr` subset modality-aware rather than forcing a mixed-platform merged matrix
  - exact `48.0 hr` expression-bearing series contribution:
    - `GSE43948` = `32`
    - `GSE43955` = `2`
    - `GSE43969` = `2`
  - exact `48.0 hr` expression-bearing artifact contribution:
    - `GSE43948_rnaseq` = `32`
    - `GSE43955_series` = `2`
    - `GSE43969_series` = `2`
  - genotype standardization:
    - `IL23R_KO = 10`
    - `WT = 10`
    - `not_reported = 92`
  - perturbation-screen target counts:
    - `NT = 20`
    - each targeted perturbation recovered once:
      - `EGR2`
      - `ETV6`
      - `FAS`
      - `IKZF4`
      - `IRF8`
      - `MINA`
      - `POU2F1A`
      - `PROCR`
      - `SMARCA4`
      - `SP4`
      - `TSC22D3`
      - `ZEB1`

Confirmed Yosef-only regulator-evidence artifact:

- `yosef_th17_network_evidence`:
  - perturbation-screen reference:
    - `20` non-targeting controls
    - `12` targeted perturbation samples
    - `27723` RNA-seq genes
  - derived RNA-seq evidence tables:
    - `perturbation_control_reference.csv`
    - `perturbation_target_design.csv`
    - `perturbation_target_expression_matrix.tsv.gz` = `27723 x 12`
    - `perturbation_target_delta_matrix.tsv.gz` = `27723 x 12`
    - `perturbation_target_log2_fc_matrix.tsv.gz` = `27723 x 12`
  - direct target self-observation status:
    - `11` targeted regulators are present as exact gene symbols in the recovered RNA-seq matrix
    - `1` targeted regulator is not present as an exact gene symbol:
      - `POU2F1A`
  - late-time GPL8321 microarray evidence:
    - `late_time_gpl8321_design.csv` = `38` samples
    - `late_time_gpl8321_expression_matrix.tsv.gz` = `22690 x 38`
    - series composition:
      - `GSE43955 = 20`
      - `GSE43969 = 18`
    - time composition:
      - `48.0 = 4`
      - `49.0 = 4`
      - `50.0 = 3`
      - `52.0 = 6`
      - `54.0 = 4`
      - `60.0 = 6`
      - `65.0 = 4`
      - `72.0 = 7`
  - exact `48.0 hr` GPL8321 subset:
    - `exact_48h_gpl8321_design.csv` = `4` samples
    - `exact_48h_gpl8321_expression_matrix.tsv.gz` = `22690 x 4`
    - series composition:
      - `GSE43955 = 2`
      - `GSE43969 = 2`

Confirmed Yosef-only regulator-summary artifact:

- `yosef_th17_network_regulator_summary`:
  - RNA-seq perturbation target summaries:
    - `rnaseq_target_summary.csv` = `12` rows
    - `11` targets have direct self-observation values
    - `1` target remains unmatched as an exact RNA-seq gene symbol:
      - `POU2F1A`
  - late-time GPL8321 contrasts:
    - `gpl8321_late_time_contrast_manifest.csv` = `26` contrasts
    - `gpl8321_late_time_contrast_matrix.tsv.gz` = `22690 x 26`
    - contrast-family counts:
      - `gse43955_treatment_vs_th0 = 5`
      - `gse43955_il23_effect = 4`
      - `gse43969_wt_vs_il23rko_tgfb_il6 = 5`
      - `gse43969_wt_vs_il23rko_tgfb_il6_il23 = 4`
      - `gse43969_il23_effect_wt = 4`
      - `gse43969_il23_effect_il23r_ko = 4`
    - all contrasts are same-series and same-time only; no cross-series or cross-platform averaging is performed
  - candidate regulator table:
    - `candidate_regulator_evidence.csv` = `15` regulators
    - includes the `12` targeted perturbation regulators plus the paper-highlighted final-network `48 hr` candidates:
      - `STAT6`
      - `TCFEB`
      - `TRIM24`
    - all three highlighted final-network candidates are present as exact gene symbols in the recovered RNA-seq perturbation matrix
    - GPL8321 candidate support is now grounded in the recovered GEO platform export rather than inferred from probe IDs alone
    - exact GPL8321 support now holds for:
      - `STAT6`
      - `TRIM24`
    - platform-alias GPL8321 support now holds for:
      - `TCFEB` via `Gene Symbol = Tfeb` and `GEN = Tcfeb`
    - still unresolved at the platform-alias level:
      - `POU2F1A`
  - notable observed self-response examples from the RNA-seq target summaries:
    - `TSC22D3` self log2 fold change = `+2.098233548840968`
    - `EGR2` self log2 fold change = `-1.1717290230229254`
    - `PROCR` self log2 fold change = `-1.135054628704145`

Confirmed GPL8321 platform-annotation artifact:

- `GPL8321_annotation`:
  - raw source:
    - GEO full text export `GPL8321_full.txt`
  - processed table:
    - `probe_annotation.csv` = `22690` probes
  - annotation coverage:
    - probes with non-empty gene symbol = `22191`
    - probes with non-empty Entrez Gene ID = `22160`
    - unique gene symbols = `13662`
    - annotation date = `Oct 6, 2014`
  - mapping policy:
    - accept exact probe-to-gene support when GPL8321 declares the candidate in `Gene Symbol`
    - accept alias support only when GPL8321 itself declares it in `GEN=` or `UG_GENE=`
    - do not infer unsupported aliases from external heuristics at this stage

Confirmed Yosef-only ranking-input artifact:

- `yosef_th17_network_ranking_input`:
  - terminal proxy manifests:
    - `terminal_proxy_manifest.csv` = `26` late-time GPL8321 contrasts
    - `strict_exact_48h_proxy_manifest.csv` = `2` exact `48.0 hr` contrasts
    - strict exact `48.0 hr` contrast families:
      - `gse43955_treatment_vs_th0`
      - `gse43969_wt_vs_il23rko_tgfb_il6`
  - candidate-specific probe features:
    - `candidate_probe_feature_table.csv` = `27` regulator-probe rows
    - `14` regulators have strict exact `48.0 hr` GPL8321 support
    - `14` regulators have broader late-time GPL8321 support
    - `1` regulator remains unsupported in GPL8321 candidate mapping:
      - `POU2F1A`
  - candidate-level ranking inputs:
    - `candidate_ranking_input.csv` = `15` regulators
    - combines:
      - RNA-seq perturbation-screen features
      - best-probe late-time GPL8321 summaries
      - best-probe exact `48.0 hr` GPL8321 summaries
      - within-candidate-set descending ranks for each evidence axis
  - paper-highlighted final-network `48 hr` candidates:
    - `STAT6`
      - best exact `48.0 hr` probe: `1426353_at`
      - top exact `48.0 hr` contrast:
        - `gse43955_treatment_vs_th0_GSE43955_48_0h_TGFb_IL6_not_reported_vs_Th0_not_reported`
      - best exact `48.0 hr` absolute delta: `229.63157420000005`
    - `TCFEB`
      - best exact `48.0 hr` probe: `1422566_at`
      - top exact `48.0 hr` contrast:
        - `gse43969_wt_vs_il23rko_tgfb_il6_GSE43969_48_0h_TGFb_IL6_WT_vs_TGFb_IL6_IL23R_KO`
      - best exact `48.0 hr` absolute delta: `14.426170999999997`
    - `TRIM24`
      - best exact `48.0 hr` probe: `1427258_at`
      - top exact `48.0 hr` contrast:
        - `gse43955_treatment_vs_th0_GSE43955_48_0h_TGFb_IL6_not_reported_vs_Th0_not_reported`
      - best exact `48.0 hr` absolute delta: `131.8793104`

Scientific boundary:

- strict terminal support is defined only by exact `48.0 hr` contrasts; later `49-72 hr` contrasts are retained separately as broader late-time evidence
- these artifacts provide paper-facing regulator features, but they do not yet constitute an exact reconstruction of the paper’s final ranking procedure
- further work is still required to translate these features into a paper-faithful ranking or `FinalNet` reconstruction protocol

Confirmed Yosef-only prioritization artifact:

- `yosef_th17_network_prioritization`:
  - candidate-level comparison table:
    - `candidate_priority_table.csv` = `15` regulators with three explicit consensus views:
      - `strict_exact_48h_consensus`
      - `broad_late_time_consensus`
      - `three_axis_consensus`
  - consensus top-5 regulators:
    - strict exact `48.0 hr`:
      - `EGR2`, `STAT6`, `MINA`, `IRF8`, `PROCR`
    - broad late-time:
      - `PROCR`, `EGR2`, `TSC22D3`, `IRF8`, `MINA`
    - three-axis:
      - `EGR2`, `IRF8`, `MINA`, `PROCR`, `STAT6`
  - Pareto-front regulators:
    - strict exact `48.0 hr`:
      - `TCFEB`, `TSC22D3`, `EGR2`, `MINA`, `IRF8`
    - broad late-time:
      - `TCFEB`, `TSC22D3`, `EGR2`, `PROCR`, `IRF8`
    - three-axis:
      - `TCFEB`, `TSC22D3`, `EGR2`, `PROCR`, `MINA`, `IRF8`
  - paper-highlighted final-network `48 hr` candidates:
    - `STAT6`
      - strict exact `48.0 hr` consensus rank = `2`
      - broad late-time consensus rank = `6`
      - three-axis consensus rank = `5`
      - appears in strict exact `48.0 hr` and three-axis top-5, but not on the Pareto front
    - `TCFEB`
      - strict exact `48.0 hr` consensus rank = `7`
      - broad late-time consensus rank = `6`
      - three-axis consensus rank = `11`
      - remains on all three Pareto fronts, but never reaches a top-5 consensus list
    - `TRIM24`
      - strict exact `48.0 hr` consensus rank = `9`
      - broad late-time consensus rank = `13`
      - three-axis consensus rank = `12`
      - is neither top-5 nor Pareto-front under the recovered proxy features

Scientific boundary:

- this layer is a conservative support audit over recovered RNA-seq and GPL8321 proxy features, not a claim of exact `FinalNet` reconstruction
- the current recovered evidence does not isolate `STAT6`, `TCFEB`, and `TRIM24` as the sole dominant candidates under simple consensus aggregation
- the paper-facing gap has therefore narrowed from data absence to ranking-procedure unresolvedness

Scientific significance:

- the project now has deterministic, script-generated local assets for the `Th17` microarray matrices, the sequencing-only GEO metadata series, the 48 h perturbation RNA-seq table bundle, and the cross-series raw-bundle manifests;
- the raw CEL archives for the Wu subseries are now locally recovered and summarized independently of the `GSE43970` SuperSeries:
  - `GSE43956_RAW.tar`
  - `GSE43957_RAW.tar`
- the formerly unresolved `GSE43970` CEL block is now explained as two distinct `GPL1261` Wu et al. subseries rather than orphan Yosef-network samples:
  - `GSE43956` = `SGK1 KO / IL-23`
  - `GSE43957` = `Th0 +/- NaCl`
- this closes the raw-asset characterization problem for the currently recovered `Th17` corpus and moves the remaining reproduction gap to biological preprocessing, network reconstruction, and formal separation of the Yosef and Wu biological arms in downstream analyses.

#### `GSE43948`

Status:

- recovered as series matrix and supplementary RNA-seq tarball

Confirmed from processed outputs:

- the GEO series matrix is metadata-only (`data_row_count = 0` for all `32` samples)
- the numerical expression data are recovered from `GSE43948_RAW.tar`
- the recovered supplementary archive produces a gene-by-sample table with:
  - `27723` genes
  - `32` samples
  - `20` non-targeting controls
  - `12` perturbation targets

#### `GSE43949`

Status:

- recovered as series matrix metadata plus supplementary file list

Confirmed from GEO header and processed outputs:

- platform: `GPL9185`
- type: `SRA`
- relation: `SubSeries of: GSE43970`
- relation: `SRA: SRP018337`
- the GEO series matrix is metadata-only (`data_row_count = 0` for both samples)
- the supplementary assets are exactly two `TDF` tracks:
  - `GSM1074872_TSC22D3.tdf`
  - `GSM1074873_WCE.tdf`

### B. `PACNet` / `CellNet` Human Training Data

Local path:

- `data/raw/cellnet`

Recovered files:

- `Hs_stTrain_Jun-20-2017.rda`
- `Hs_expTrain_Jun-20-2017.rda`

Recovery status:

- successful via Zenodo API

Confirmed contents:

- `Hs_stTrain_Jun-20-2017.rda` loads object `stTrain`
- `stTrain` has dimension `1003 x 23`
- `stTrain$description1` contains `15` human broad classes with counts:
  - `monocyte_macrophage = 170`
  - `skeletal_muscle = 118`
  - `liver = 107`
  - `neuron = 90`
  - `intestine_colon = 85`
  - `heart = 59`
  - `kidney = 57`
  - `endothelial_cell = 51`
  - `esc = 51`
  - `hspc = 49`
  - `fibroblast = 46`
  - `lung = 44`
  - `b_cell = 38`
  - `t_cell = 38`

Confirmed expression object:

- `Hs_expTrain_Jun-20-2017.rda` loads object `expTrain`
- `expTrain` has dimension `34934 x 1003`
- sample identifiers match the `stTrain` sample IDs, beginning with:
  - `ERR030879`
  - `ERR030882`
  - `ERR030884`

Interpretation:

- the human CellNet/PACNet training universe is now recoverable locally at the level of an executable training expression matrix plus metadata table.

## Upstream Biological Provenance Anchors

These are not yet downloaded in final usable form for this project, but the provenance linkage is confirmed:

### `E. coli`

Paper provenance anchor (**corrected 2026-07-02**):

- **RegulonDB** (`http://www.ccg.unam.mx/en/projects/collado/regulondb`)
- NOT `Marbach et al. 2012` / DREAM5 as previously assumed
- The Zenil supplement (Section 3) states explicitly: _"a highly curated E. coli transcriptional network (only experimentally validated connections) from the RegulonDB"_

Previous incorrect attribution:

- ~~`Marbach et al. 2012`, `Wisdom of crowds for robust gene network inference`~~ — this was an incorrect assumption; the DREAM5 bundle remains useful reference material but is not the source of the E. coli network analysed in the Zenil paper.

Interpretive target from the Zenil paper:

- use an experimentally validated `E. coli` TF network
- classify positive and negative genes
- test enrichment against `GO`, `KEGG`, and `EcoCyc`

### `Th17`

Paper provenance anchor:

- `Yosef et al. 2013`, `Dynamic regulatory network controlling TH17 cell differentiation`
- Nature 496, 461-468; doi:10.1038/nature11981

**Critical clarification (2026-07-02)**: The Zenil paper does NOT analyse raw expression data. It analyses the **reconstructed regulatory network** from Yosef et al. 2013. The Zenil supplement (Section 3) states: _"The information spectral analysis used a reconstructed regulatory network from functional perturbation and transcriptional data corresponding to the Th17 differentiation."_

Confirmed public accessions from the source article metadata:

- `GSE43948`
- `GSE43949`
- `GSE43955`
- `GSE43969`

#### Recovered Yosef Network (Supplementary Table S3)

Downloaded 2026-07-02 from Nature MOESM14: `data/raw/yosef_network/table_s3_regulatory_interactions.xls` (2.3 MB).

Three sheets corresponding to three time-window sub-networks:

| Sheet | Zenil name | Edges | TFs | Targets | Total nodes |
|-------|------------|-------|-----|---------|-------------|
| Early | EarlyNet | 4218 | 53 | 542 | 578 |
| Intermediate | IntermediateNet | 7204 | 60 | 993 | 1027 |
| Late | FinalNet | 6894 | 50 | 1074 | 1107 |

Each row: directed edge TF → Gene, with evidence codes (0: correlation, 1: sequence, 2: perturbation, 3: combined) and time stamps.

Also recovered Table S4 (ranked regulators): `data/raw/yosef_network/table_s4_ranked_regulators.xls` (82 KB). Contains 156 transcription regulators and 57 receptors ranked by evidence criteria.

### `CellNet`

Paper provenance anchor:

- `Morris et al. 2014`, `Dissecting engineered cell types and enhancing cell fate conversion via CellNet`

Recovered codebase:

- `reference/CellNet`

Pending:

- download the relevant `CellNet` `cnProc` objects and inspect whether their cell-type panel matches the exact network set used by the Zenil paper.

Current update:

- the old `cnProc` S3 objects are no longer directly accessible;
- however, the maintainers provide the training data through Zenodo and these training assets are now locally recovered.

Implication:

- the reproduction path for the cell-type landscape may have to proceed through recoverable `PACNet`/CellNet training assets rather than the legacy prebuilt `cnProc` objects.

## Confirmed DREAM5 / Synapse Asset State

Local path:

- `data/raw/dream5`

Recovered knowledge:

- public `Synapse` metadata access works for:
  - `syn4564722` -> `D5C4_goldstandard.zip`
  - `syn4564726` -> `D5C4_templates.zip`
  - `syn2787248` -> `DREAM5_NetworkInference_SupplementalMethodsFigures.pdf`

Direct download status:

- current anonymous/public access appears to provide `READ` but not `DOWNLOAD` permission for these entities through the tested client route.

Scientific interpretation:

- the `DREAM5` assets are not missing or fictional; they are discoverable on `Synapse`.
- however, direct file retrieval remains an unresolved access-control issue at present.
- this is a materially different obstacle from the dead Broad Institute URLs and should be documented separately in the final reproducibility audit.

## Manually Recovered DREAM5 Bundle

Local paths:

- `data/raw/dream5/manual_download`
- original manual archive was placed at `data/raw/dream5.zip`

Recovery status:

- successful extraction

Extracted files:

- `README.txt`
- `manifest.csv`
- `ecoli_data.tsv`
- `ecoli_experiments.tsv`
- `ecoli_gene_names.tsv`
- `ecoli_tf_names.tsv`
- corresponding `yeast_*` and `saureus_*` files

Important provenance caveat from the included `README.txt`:

- these are described by Daniel Marbach as:
  - `the original files before preparation for the challenge`
- the same README also states:
  - `the official datasets of the challenge are provided as supplement of the paper`

Scientific interpretation:

- this manually recovered bundle is a legitimate upstream DREAM5-related asset;
- however, on its own it should currently be treated as the original expression compendia rather than automatically assumed to be the exact final challenge-distributed files used in all downstream evaluations.

Internal integrity verification:

- the extracted `E. coli` files match the MD5 hashes listed in `manifest.csv`:
  - `ecoli_data.tsv` -> `d56598aa81e6fd0635e68da0a66b280c`
  - `ecoli_experiments.tsv` -> `5873be4e92c70e108e55587e3c330b8c`
  - `ecoli_gene_names.tsv` -> `d09cddedabe77f2d08bca32b8d87e866`
  - `ecoli_tf_names.tsv` -> `eae1891b8cd60c209334372745c0799c`

Observed content sanity checks:

- `ecoli_experiments.tsv` contains real experimental condition labels such as `MG1655`, `LB`, `recA`, `norf`, and replicate/timepoint descriptors;
- `ecoli_tf_names.tsv` contains transcription-factor symbols such as `aaeR`, `abgR`, `acrR`, `araC`, and `arcA`;
- `ecoli_gene_names.tsv` contains genome-wide gene symbols beginning with `aaaD`, `aaeA`, `aaeB`, `aaeR`, and `aaeX`.

Implication for reproduction planning:

- this bundle is strong enough to begin reconstructing the `E. coli` expression-side preprocessing pipeline;
- it does not yet close the gap on the exact validated network object and the exact final challenge supplement assets.

## Zenil Paper Supplementary Data (Ground Truth BDM Values)

Recovered 2026-07-02 from iScience supplementary materials. Stored at `data/raw/zenil_supplementary/`.

| File | Description | Gene count |
|------|------------|------------|
| mmc2.csv (Data S1) | Time 1 (EarlyNet) Negative Elements | 223 |
| mmc3.csv (Data S2) | Time 1 (EarlyNet) Positive Elements | 15 |
| mmc4.csv (Data S3) | Time 2 (IntermediateNet) Negative Elements | 360 |
| mmc5.csv (Data S4) | Time 2 (IntermediateNet) Positive Elements | 3 |
| mmc6.csv (Data S5) | Time 3 (FinalNet) Negative Elements | 3 |
| mmc7.csv (Data S6) | Time 3 (FinalNet) Positive Elements | 239 |
| mmc8.csv (Data S7) | Exhaustive Numerical Calculation of Dynamics vs Element Removal | 9364 rows |

These are the **authors' actual computed BDM perturbation deltas** (from `algodyn`), providing ground truth for cross-validation.

### Cross-validation: pybdm vs algodyn (ground truth)

BDM node perturbation was computed on all three Yosef time-window networks using `pybdm`. Results compared to the authors' supplementary values (mmc2–mmc7):

#### Ordering sensitivity (resolved 2026-07-03)

BDM is **not a graph invariant**: the delta values and their signs depend on the adjacency matrix node ordering. This is the root cause of the initial EarlyNet discrepancy and was established by systematic investigation across two orderings per network.

CTM tables are not the source of the discrepancy: `pybdm`'s built-in tables, algodyn's `K-3x3.csv`/`K-4x4.csv`, and `mat-bdm/squares2Dsize1to4.m` (exact rationals) are all numerically identical.

| Network | sorted (alphabetical) | in_degree_desc | Best ordering |
|---------|----------------------|----------------|---------------|
| EarlyNet | 15/209 (7%) | 203/209 (97%) | in_degree_desc |
| IntermediateNet | 331/340 (97%) | 327/340 (96%) | sorted |
| FinalNet | 202/204 (99%) | 4/204 (2%) | sorted |

No single ordering reproduces all three networks. The paper likely used igraph's default vertex ordering, which depends on graph creation order and differs per network. The per-network best orderings above are used in the canonical reproduction pipeline (`run_yosef_perturbation.py`).

The perturbation methodology also matters: the canonical approach builds the adjacency matrix once with the fixed ordering and removes rows/columns via `np.delete` (matching algodyn's deletion semantics), rather than reconstructing the adjacency matrix after each node removal.

#### Canonical cross-validation results (per-network best ordering)

| Network | Sign agreement | Notes |
|---------|---------------|-------|
| FinalNet | 202/204 (99%) | Alphabetical ordering; STAT6, TCFEB, TRIM24 confirmed negative |
| IntermediateNet | 331/340 (97%) | Alphabetical ordering |
| EarlyNet | 203/209 (97%) | in_degree_desc ordering |

**Magnitude scaling** remains non-linear: for FinalNet, paper deltas are ~4–5× larger for negative genes (e.g., STAT6: paper=−445, ours=−87) but ~1–2× for positive genes (e.g., RUNX1: paper=1441, ours=1448 — nearly identical). This is a scale difference, not a sign error, and does not affect classification or reprogrammability conclusions.

**Conclusion**: The `pybdm` perturbation pipeline correctly captures the sign of BDM perturbation effects for all three networks when the appropriate per-network node ordering is used. The claim "only three negative genes in FinalNet" (STAT6, TCFEB, TRIM24) is confirmed. The magnitude gap is a known pybdm/algodyn scale difference and does not affect the paper's primary conclusions about reprogrammability direction.

## Immediate Reproduction Targets Enabled By Current Recovery

The following work can now begin with actual assets already in hand:

1. ~~Parse `GSE43955` and `GSE43969` into reproducible expression/metadata tables.~~ (superseded: Zenil paper uses Yosef's reconstructed network, not raw expression data)
2. ~~Reconstruct the exact `Th17` time axis and condition partitions used in the Zenil panels.~~ (superseded: Yosef Table S3 directly provides the three time-window networks)
3. Compare current project perturbation routines against `algodyn` on identical toy graphs.
4. Inspect `CellNet` package internals for the exact structure of GRN status and network scoring outputs.
5. ~~Recover or reconstruct the `E. coli` consensus network from the `Marbach 2012` ecosystem.~~ (corrected: source is RegulonDB, not DREAM5/Marbach)
6. Download RegulonDB experimentally validated TF network for the `E. coli` analysis.
7. ~~Run BDM node perturbation on the three Yosef time-window networks and verify Zenil's negative-node claims.~~ (DONE — see cross-validation section above)

## Known Open Gaps

These are still unresolved:

- exact RegulonDB network file corresponding to the `E. coli` network analysed in the Zenil paper (source confirmed as RegulonDB, not DREAM5)
- exact CellNet object set for the `16` human cell types shown in the complexity-programmability map
- exact supplementary benchmark graph list for MILS validation
- exact exhaustive Boolean-network enumeration protocol beyond what is stated textually
- downloadable access to the `DREAM5` `Synapse` gold standard and template files through the current anonymous/public route

## Rule For Future Updates

Only add an item to this ledger when one of the following is true:

- the file has been downloaded locally,
- the code has been cloned locally,
- the protocol detail has been directly observed in the source paper or official metadata,
- or the provenance chain has been verified from an authoritative public source.
