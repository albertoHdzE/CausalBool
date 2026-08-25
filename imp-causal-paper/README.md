# imp-causal-paper

Standalone and isolated implementation of the paper `An Algorithmic Information Calculus for Causal Discovery and Reprogramming Systems` by Zenil et al. (2019).

## Scope

This project implements the paper's core executable machinery in a self-contained Python project with its own virtual environment:

- BDM-based complexity estimation through `pybdm`
- perturbation spectra and information signatures for graph edges and vertices
- positive, neutral, and negative element classification using the paper's `log2 |V(G)|` threshold
- MILS (Minimal Information Loss Sparsification)
- MARPA (Maximal Algorithmic Randomness Preferential Attachment)
- relative, absolute, and combined reprogrammability indices
- reverse engineering of small cellular automata from disordered observations
- synchronous Boolean-network attractor analysis under perturbations
- reproducible parsing of the public `Th17` GEO series into project-local artifacts, distinguishing:
- expression-bearing microarray matrices (`GSE43955`, `GSE43956`, `GSE43957`, `GSE43969`)
- metadata-only sequencing series (`GSE43948`, `GSE43949`)
- supplementary bundle manifests (`GSE43948`, `GSE43949`, `GSE43956`, `GSE43957`, `GSE43970`)
- 48 h perturbation RNA-seq gene tables recovered from `GSE43948_RAW.tar`

## Reproducibility Boundary

The paper contains broad biological applications on `E. coli`, `Th17`, and `CellNet` data. This project now includes project-local ingestion of the public `Th17` GEO assets and supplementary bundle manifests, but it does not yet claim exact reproduction of the full biological panels. The remaining gap is no longer raw data discovery for `Th17`; it is paper-faithful preprocessing, network reconstruction, and claim-level corroboration across all biological blocks. The current local provenance also shows that `GSE43970` is a mixed SuperSeries spanning both the Yosef Th17 network-reconstruction assets and the Wu `SGK1` salt-pathogenicity subseries (`GSE43956`, `GSE43957`), so downstream network analyses must separate those biological arms explicitly.

For the cellular-automaton reconstruction demo, the row order is recovered exactly on the provided synthetic case. As in the paper's broader discussion of generative inference, finite observations can admit more than one compatible local rule, so the demo reports both the recovered ordering and the best-fitting rule on the observed window.

## Environment

- Isolated virtual environment: `.venv`
- Interpreter: Python 3.11
- Main numerical dependency: `pybdm==0.1.0`

## Step-by-Step Execution

```bash
./run.sh setup
./run.sh th17
./run.sh test
./run.sh graphs
./run.sh ca
./run.sh boolean
./run.sh all
```

Outputs are written under `results/`.
Plots are written under the root-level `plots/` folder, split by experiment (`plots/graphs`, `plots/ca`, `plots/boolean`).
Processed `Th17` outputs are written under `data/processed/th17`, with separate directories for series metadata, expression matrices, RNA-seq supplementary tables, and bundle manifests. The recovered Wu subseries raw archives (`GSE43956_RAW.tar`, `GSE43957_RAW.tar`) are now also summarized into deterministic tar-member manifests so that raw CEL provenance is tracked at the series level rather than only through the `GSE43970` SuperSeries bundle. Series-level outputs now carry explicit arm-aware provenance fields such as `study_arm`, `source_publication`, and `biological_program`, and bundle manifests expose `resolved_study_arm_counts` so downstream preprocessing can enforce the Yosef/Wu separation mechanically rather than by convention.

The `th17-prepare` pipeline now also materializes branch-specific cohort artifacts under `data/processed/th17`:
- `yosef_th17_network_cohort`
- `wu_sgk1_pathogenicity_cohort`
- `yosef_th17_network_design`
- `yosef_th17_network_evidence`
- `yosef_th17_network_regulator_summary`
- `yosef_th17_network_ranking_input`
- `yosef_th17_network_prioritization`
- `GPL8321_annotation`

These cohort directories provide combined `sample_metadata.csv`, per-series `series_metadata.csv`, and `summary.json` files so downstream network reconstruction can select a biologically coherent arm by construction rather than by ad hoc filtering.

The Yosef-specific design artifact is the current network-ready preprocessing boundary. It materializes:
- `sample_design.csv`: unified Yosef-only sample table across `GSE43948`, `GSE43949`, `GSE43955`, and `GSE43969`
- `perturbation_screen_design.csv`: the `32` recovered `GSE43948` RNA-seq perturbation samples
- `perturbation_screen_expression_matrix.tsv.gz`: the aligned `27723 x 32` RNA-seq perturbation matrix
- `chip_binding_design.csv`: the `2` `GSE43949` ChIP-seq tracks
- `dynamic_timecourse_design.csv`: the `78` expression-bearing time-course samples from `GSE43955` and `GSE43969`
- `dynamic_timecourse_expression_matrix.tsv.gz`: the aligned `22690 x 78` GPL8321 microarray matrix
- `exact_48h_expression_design.csv`: the exact `48.0 hr` expression-bearing subset (`36` samples total)
- `exact_48h_expression_manifest.csv`: a modality-aware manifest for the exact `48.0 hr` subset, kept unmerged across RNA-seq and microarray panels

This artifact standardizes assay modality, experimental axis, treatment, genotype, cell type, and perturbation status without collapsing unresolved biological distinctions that are absent from GEO metadata.

The Yosef evidence artifact is the next layer above the design table. It materializes:
- `perturbation_control_reference.csv`: mean and standard deviation over the `20` non-targeting controls
- `perturbation_target_design.csv`: the `12` targeted perturbation samples
- `perturbation_target_expression_matrix.tsv.gz`: the targeted RNA-seq panel (`27723 x 12`)
- `perturbation_target_delta_matrix.tsv.gz`: target-minus-control effects in expression space
- `perturbation_target_log2_fc_matrix.tsv.gz`: target-versus-control log2 fold-change effects
- `perturbation_self_response.csv`: direct self-target observability summary, where `11/12` targets are observed and `POU2F1A` is the only missing exact gene symbol
- `late_time_gpl8321_design.csv` and `late_time_gpl8321_expression_matrix.tsv.gz`: the late-time GPL8321 panel (`38` samples)
- `exact_48h_gpl8321_design.csv` and `exact_48h_gpl8321_expression_matrix.tsv.gz`: the exact `48.0 hr` GPL8321 subset (`4` samples)

This evidence layer still preserves RNA-seq and microarray modality boundaries. It is designed for downstream ranking and stability analyses, not for cross-platform matrix fusion.

The Yosef regulator-summary artifact is the current highest preprocessing layer before explicit ranking logic. It materializes:
- `rnaseq_target_summary.csv`: one row per targeted perturbation with self-response values and whole-transcriptome effect summaries
- `gpl8321_late_time_contrast_manifest.csv`: `26` same-series, same-time late-time contrast definitions derived from observed metadata only
- `gpl8321_late_time_contrast_matrix.tsv.gz`: the corresponding `22690 x 26` probe-level GPL8321 contrast matrix
- `gpl8321_late_time_contrast_summary.csv`: per-contrast probe-level extrema and aggregate effect sizes
- `candidate_regulator_evidence.csv`: a modality-aware candidate table for the `12` targeted perturbation regulators plus the paper-highlighted `48 hr` candidates `STAT6`, `TCFEB`, and `TRIM24`

The `GPL8321_annotation` artifact is now recovered directly from the GEO platform full text export (`GPL8321_full.txt`) and provides the authoritative probe table used for microarray mapping. This allows candidate-level GPL8321 support to move beyond pure probe-space bookkeeping:
- `STAT6` has exact GPL8321 probe support
- `TRIM24` has exact GPL8321 probe support
- `TCFEB` is recovered through the platform-declared alias path `Gene Symbol = Tfeb`, `GEN = Tcfeb`
- `POU2F1A` remains unresolved because the platform supports `Pou2f1`, but does not declare `POU2F1A` as an exact platform alias

The mapping remains conservative: microarray support is accepted only when the GPL8321 row itself declares the exact symbol or a platform-native alias.

The Yosef ranking-input artifact is the current paper-facing preprocessing boundary. It materializes:
- `terminal_proxy_manifest.csv`: the full `26`-contrast late-time GPL8321 panel, with each contrast labeled as either `strict_exact_48h` or `broad_late_time`
- `strict_exact_48h_proxy_manifest.csv`: the strict terminal proxy subset with exactly `2` admissible `48.0 hr` contrasts
- `candidate_probe_feature_table.csv`: `27` regulator-probe rows with late-time and exact-`48.0 hr` effect summaries
- `candidate_ranking_input.csv`: `15` regulator rows combining RNA-seq perturbation features with candidate-specific GPL8321 late-time and exact-`48.0 hr` summaries

This artifact formalizes two distinct terminal-state notions that should not be conflated:
- strict terminal proxy: only the exact `48.0 hr` GPL8321 contrasts (`GSE43955` treatment-vs-`Th0`, `GSE43969` `WT`-vs-`IL23R_KO` under `TGFb+IL6`)
- broad late-time proxy: the full admissible `>=48 hr` same-series, same-time GPL8321 contrast panel

For the paper-highlighted `48 hr` candidates:
- `STAT6` best strict exact-`48.0 hr` probe: `1426353_at`
- `TCFEB` best strict exact-`48.0 hr` probe: `1422566_at`
- `TRIM24` best strict exact-`48.0 hr` probe: `1427258_at`

These are ranking inputs, not final paper-equivalent rankings. They expose defensible candidate features while keeping the gap between preprocessing and exact reconstruction explicit.

The Yosef prioritization artifact is the current paper-facing comparison layer above those inputs. It materializes:
- `candidate_priority_table.csv`: the `15`-candidate table augmented with conservative multi-view consensus scores
- `strict_exact_48h_consensus.csv`, `broad_late_time_consensus.csv`, and `three_axis_consensus.csv`: sorted candidate orderings for three evidence-combination regimes
- `strict_exact_48h_consensus_pareto_front.csv`, `broad_late_time_consensus_pareto_front.csv`, and `three_axis_consensus_pareto_front.csv`: non-dominated candidate sets under each regime
- `paper_finalnet_claim_audit.csv`: explicit ranks and frontier membership for the paper-highlighted `48 hr` candidates `STAT6`, `TCFEB`, and `TRIM24`

This artifact is deliberately conservative:
- it does not claim to reconstruct the paper's hidden `FinalNet` ranking procedure
- it exposes where simple evidence aggregation recovers the paper-highlighted candidates and where it does not
- on the current recovered inputs, only `STAT6` reaches the strict exact-`48.0 hr` top-5 consensus, while only `TCFEB` remains on all three Pareto fronts

Definition-fidelity status is now tracked explicitly in `definition_fidelity.json`:
- `info_spectra`, `info_signature`, and `inforank` are currently treated as exact to the recovered local `algodyn` reference
- `relative_reprogrammability` is now implemented according to the recovered paper supplement: `MAD(sigma) / max(|sigma|)`
- the recovered local `algodyn` code disagrees on this point by using `MAD(sigma) / max(sigma)`, and is retained only as an audit variant
- upstream `algodyn` git history contains only stub placeholders for absolute and total reprogrammability, then removes them; no operational author-adjacent implementation of `S` has yet been recovered
- `absolute_reprogrammability` and `combined_reprogrammability` are therefore exposed canonically as unresolved, while the former trapezoid-area and Euclidean formulas are preserved only as explicitly labeled proxy audit variants

Each plot directory also contains a `plot_manifest.json` file stating the exact correspondence boundary with the original paper figures. This is intentional: the implementation reproduces the paper's core algorithms and generates faithful reduced analogues of key visualizations, but it does not claim that every saved plot is pixel-identical to the published panels.

## Tests

The test suite uses real computations only, with no mocks:

- graph signature ordering
- MILS edge-count reduction
- MARPA edge-addition growth
- CA order reconstruction from scrambled observations
- Boolean-network attractor computation
- full CLI integration producing experiment outputs
