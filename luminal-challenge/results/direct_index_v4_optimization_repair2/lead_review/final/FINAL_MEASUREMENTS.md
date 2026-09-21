# Measured arms — final phase

Command: `benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization_repair2/lead_review/final`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 89.5 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.2937 | 0.6632 | 201.2134 | 0.5479 | 105.7414 |
| scalar_dual_chain | 0.1809 | 0.3899 | 215.6925 | 0.3410 | 125.3288 |
| vector_axpy | 0.1976 | 0.5017 | 227.3233 | 0.4268 | 133.1782 |
| vector_bitmix | 0.2360 | 0.6570 | 443.2952 | 0.5497 | 184.8406 |
| mixed_broadcast | 0.1538 | 0.3492 | 653.8342 | 0.3089 | 441.6796 |
| parallel_memory | 0.3510 | 0.9393 | 413.2939 | 0.7688 | 140.8535 |
| scalar_selects | 0.3357 | 0.7737 | 524.8696 | 0.7593 | 177.9620 |
| vector_reduction | 0.3945 | 0.9218 | 425.7438 | 0.7541 | 171.2852 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 2.1320x | 2.1268–2.1375 | 2.6823x | none |
| bootstrap_candidate_vs_frozen | 1.1629x | 1.1471–1.1690 | 1.1973x | none |
| full_candidate_vs_classical | 0.0015x | 0.0015–0.0015 | 0.0017x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.4832x | 0.4771–0.4862 | 0.4899x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0007x | 0.0007–0.0007 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.4155x | 0.4135–0.4185 | 0.4092x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_frozen | 0.0017x | 0.0017–0.0017 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_candidate | 0.0031x | 0.0031–0.0032 | 0.0035x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |

## Combined scores recomputed from raw integers

- `classical`: 1.9013791212645499
- `frozen_bootstrap`: 2.0084662022846569
- `frozen_full`: 2.0084662022846569
- `candidate_bootstrap`: 2.0084662022846569
- `candidate_full`: 2.0084662022846569

## Bootstrap versus full-direct metrics

- `frozen`: the hypothesis that bootstrap metrics equal full-direct metrics holds over 8 programs; 0 discrepancies.
- `candidate`: the hypothesis that bootstrap metrics equal full-direct metrics holds over 8 programs; 0 discrepancies.

## Definitions and limits

- **speedup**: baseline median compile time divided by candidate median
- **primary_aggregate**: equal-program geometric mean of per-program median ratios
- **pooled_median_ratio**: median of all baseline times divided by median of all candidate times; a different quantity from the primary aggregate and never mixed with it
- **paired_bootstrap_95**: percentile interval over repetition identifiers resampled within each program and used jointly for every arm; timing uncertainty on this fixed program suite only
- **serial_baseline**: combined scores use the protected historical serial integers; serial is not one of this harness's arms

Raw rows, the retained arm order and full provenance are in `runs.json`.
