# Measured arms — final phase

Command: `benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --quiet --output results/direct_index_v4_optimization_repair/final`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 90.7 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.2925 | 0.6760 | 201.2618 | 0.5723 | 117.9643 |
| scalar_dual_chain | 0.1776 | 0.3887 | 217.0184 | 0.3468 | 140.5220 |
| vector_axpy | 0.1941 | 0.4992 | 229.5456 | 0.4360 | 137.2967 |
| vector_bitmix | 0.2360 | 0.6659 | 447.4836 | 0.5739 | 209.0565 |
| mixed_broadcast | 0.1535 | 0.3493 | 659.9554 | 0.3131 | 460.4353 |
| parallel_memory | 1.3935 | 0.9668 | 414.5972 | 0.8113 | 157.3567 |
| scalar_selects | 1.3763 | 0.7993 | 527.6080 | 0.7877 | 199.7500 |
| vector_reduction | 0.3932 | 0.9399 | 434.5972 | 0.7931 | 192.6444 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 1.9536x | 1.9503–1.9567 | 2.4283x | none |
| bootstrap_candidate_vs_frozen | 1.1380x | 1.1326–1.1411 | 1.1706x | none |
| full_candidate_vs_classical | 0.0019x | 0.0019–0.0020 | 0.0015x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.6576x | 0.6540–0.6612 | 0.4593x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0010x | 0.0010–0.0010 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.5778x | 0.5754–0.5817 | 0.3923x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
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
