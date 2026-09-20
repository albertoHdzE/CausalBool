# Measured arms — baseline phase

Command: `benchmark_optimization.py --phase baseline --repeats 15 --seed 20260920 --output results/direct_index_v4_optimization/baseline`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 113.8 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.2995 | 0.6786 | 201.2823 | 0.6775 | 201.2895 |
| scalar_dual_chain | 0.1841 | 0.3912 | 217.0926 | 0.3962 | 216.9935 |
| vector_axpy | 0.1968 | 0.5018 | 229.5430 | 0.5012 | 229.5216 |
| vector_bitmix | 0.2377 | 0.6665 | 447.5166 | 0.6669 | 447.6396 |
| mixed_broadcast | 0.1550 | 0.3545 | 659.8103 | 0.3492 | 660.2217 |
| parallel_memory | 0.3601 | 0.9692 | 414.7361 | 0.9615 | 414.6006 |
| scalar_selects | 0.3433 | 0.7963 | 527.7725 | 0.8008 | 527.6466 |
| vector_reduction | 0.3979 | 0.9493 | 434.8152 | 0.9460 | 434.6878 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 1.0001x | 0.9996–1.0005 | 1.0011x | mixed_broadcast, scalar_pipeline, vector_bitmix |
| bootstrap_candidate_vs_frozen | 1.0013x | 0.9970–1.0073 | 0.9979x | scalar_dual_chain, scalar_selects, vector_bitmix |
| full_candidate_vs_classical | 0.0007x | 0.0007–0.0007 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.4139x | 0.4113–0.4164 | 0.4023x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0007x | 0.0007–0.0007 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.4134x | 0.4103–0.4159 | 0.4031x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_frozen | 0.0017x | 0.0017–0.0017 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_candidate | 0.0017x | 0.0017–0.0017 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |

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
