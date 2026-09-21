# Measured arms — final phase

Command: `benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --quiet --output results/direct_index_v4_optimization/final`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 90.4 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.2949 | 0.6783 | 201.2629 | 0.5701 | 115.4619 |
| scalar_dual_chain | 0.1802 | 0.3878 | 216.9460 | 0.3458 | 139.2151 |
| vector_axpy | 0.1953 | 0.5011 | 229.4438 | 0.4386 | 135.9883 |
| vector_bitmix | 0.2349 | 0.6667 | 447.6576 | 0.5733 | 203.3079 |
| mixed_broadcast | 0.1517 | 0.3478 | 660.0376 | 0.3138 | 458.1485 |
| parallel_memory | 0.3567 | 0.9642 | 414.5824 | 0.8112 | 152.9145 |
| scalar_selects | 0.3441 | 0.7959 | 527.5735 | 0.7865 | 196.3730 |
| vector_reduction | 0.3964 | 0.9420 | 435.5208 | 0.7960 | 188.3239 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 1.9889x | 1.9841–1.9913 | 2.4775x | none |
| bootstrap_candidate_vs_frozen | 1.1371x | 1.1334–1.1406 | 1.1776x | none |
| full_candidate_vs_classical | 0.0014x | 0.0014–0.0014 | 0.0015x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.4674x | 0.4654–0.4699 | 0.4618x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0007x | 0.0007–0.0007 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.4110x | 0.4096–0.4131 | 0.3922x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_frozen | 0.0017x | 0.0017–0.0017 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_candidate | 0.0030x | 0.0030–0.0030 | 0.0033x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |

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
