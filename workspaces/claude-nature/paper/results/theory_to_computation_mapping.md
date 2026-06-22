# Theory → Computation Mapping (LEV8)

**Document ID:** LEV8-THEORY-MAP-2026-04-06  
**Date:** 2026-04-06  
**Purpose:** Remove any ambiguity between theorem objects and what is computed in this repository, including explicit proxy boundaries.

## Core objects and computed quantities

|Theoretical object|Symbol|Computed quantity (repo)|Where computed|Units|Exact vs proxy|Key assumptions / caveats|
|---|---:|---|---|---:|---|---|
|Structural description length of a wiring diagram|\(D(G)\)|Compression proxy \(D_{\text{gzip}}(G)=\mathrm{len}(\mathrm{gzip}(\mathrm{cm.tobytes()}))\)|`paper/code/analysis_pipeline.py`: `compute_compression_complexity`|bytes|Proxy|Adjacency matrix only; canonicalizes node order by degree (tie-breaker optional WL); proxy for Kolmogorov complexity.|
|Universality null comparison (biological vs randomized)|—|`compute_D_bio_vs_random` outputs `D_bio`, `D_random_mean`, `z_score`, `p_value`|`paper/code/analysis_pipeline.py`: `compute_D_bio_vs_random`|bytes, z, p|Proxy|Null families: ER, degree-preserved (Maslov–Sneppen swaps), gate-permuted (requires node features). `p_value` is empirical one-sided fraction of null ≤ bio.|
|Fold reduction / algorithmic efficiency|—|\(D_{\text{null}}/D_{\text{bio}}\) (`fold_reduction`)|Derived from `D_random_mean / D_bio` in outputs|unitless|Proxy|Interprets fold>1 as “bio more compressible than null”.|
|ΔD for node removal (information lost if node removed)|\(\Delta D(v)\)|In corpus/essentiality: \(D^{(v2)}(G)-D^{(v2)}(G\setminus v)\) stored as `Delta_D`|`src/analysis/Essentiality_Prediction_v3.py`|bits (encoder units)|Proxy (universal encoder approximation)|Uses `UniversalDv2Encoder` on adjacency; node removal by deleting row/col; this is the ΔD used in KR-A essentiality.|
|Mean ΔD across cohorts (DepMap validation)|Mean\_ΔD|`Mean_Delta_D` per node in `figure3_depmap_validation*.csv`|`src/analysis/DepMap_Validation.py`|bits (encoder units)|Proxy (universal encoder approximation)|Mean over synthetic tumor cohort networks; node→gene mapping required for DepMap join; confound conditioning available (expression/copy number/constraint).|
|Cancer corruption (paired tumor vs normal)|\(\Delta D^{(v2)}\)|`Delta_D = D_tumor - D_normal` in paired TCGA tables|`src/analysis/Cancer_Corruption.py`|bits (encoder units)|Proxy (universal encoder approximation)|Normal scaffold fixed; tumor scaffold modified by deterministic state-fixing and incoming-edge severing triggered by tumor-vs-baseline expression deltas.|
|Essentiality predictiveness (KR-A)|AUC/AP|ROC-AUC / PR-AUC with network-resampled bootstrap CIs|`paper/code/analysis_pipeline.py`: `generate_figure2`|unitless|Statistical estimate|Predictors are node-level scores; combined model uses network-held-out CV; stratified performance computed by Organism/Size/Source.|

## Proxy boundary (the critical point)

- This repository currently uses **two distinct computable proxies** for “description length”:
  - \(D_{\text{gzip}}\): gzip length of adjacency (used for the universality / null-family corpus meta-analysis in Figure 1 and bias defense).
  - \(D^{(v2)}\): `UniversalDv2Encoder` output on adjacency (used for node-removal ΔD in essentiality and for corruption/DepMap benchmarks).
- These are conceptually aligned (both estimate “compressibility / algorithmic structure”), but they are **not numerically interchangeable**. Claims and captions must therefore label which proxy is used.

## Ordering assumptions (frozen)

- Canonical ordering for adjacency-based complexity uses **degree sort**, with optional WL tie-break (`tie_breaker="wl"`). The Gate A checksum manifest locks deterministic PNG/CSV/JSON artifacts generated under this policy.

