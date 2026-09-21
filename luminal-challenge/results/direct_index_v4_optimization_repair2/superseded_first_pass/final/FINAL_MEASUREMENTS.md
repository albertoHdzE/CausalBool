# Measured arms — final phase

Command: `benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --quiet --output results/direct_index_v4_optimization_repair2/final`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 93.4 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.3329 | 0.7607 | 201.4863 | 0.6455 | 131.2949 |
| scalar_dual_chain | 0.1830 | 0.4024 | 217.6494 | 0.3581 | 145.6848 |
| vector_axpy | 0.2006 | 0.5131 | 230.5074 | 0.4491 | 138.2407 |
| vector_bitmix | 0.2459 | 0.6892 | 449.0577 | 0.5894 | 215.9792 |
| mixed_broadcast | 0.1573 | 0.3616 | 667.2201 | 0.3211 | 468.0589 |
| parallel_memory | 1.4702 | 0.9897 | 415.1057 | 0.8352 | 161.7279 |
| scalar_selects | 1.4647 | 0.8245 | 528.4940 | 0.8331 | 206.4703 |
| vector_reduction | 0.4078 | 0.9707 | 443.3444 | 0.8125 | 198.3853 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 1.8951x | 1.8888–1.8985 | 2.3609x | none |
| bootstrap_candidate_vs_frozen | 1.1369x | 1.1260–1.1592 | 1.1532x | scalar_selects |
| full_candidate_vs_classical | 0.0020x | 0.0020–0.0020 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.6631x | 0.6536–0.6677 | 0.4635x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0010x | 0.0010–0.0011 | 0.0007x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.5833x | 0.5706–0.5864 | 0.4019x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_frozen | 0.0018x | 0.0018–0.0018 | 0.0017x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_candidate | 0.0030x | 0.0030–0.0030 | 0.0035x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |

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
