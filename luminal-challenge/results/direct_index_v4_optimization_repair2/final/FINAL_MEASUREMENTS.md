# Measured arms — final phase

Command: `benchmark_optimization.py --phase final --baseline results/direct_index_v4_optimization/baseline --repeats 15 --seed 20260920 --quiet --output results/direct_index_v4_optimization_repair2/final`

Seed 20260920, 15 repetitions, 600 rows, 0 failures, 91.6 s elapsed.

## Median compile time per program (milliseconds)

| Program | classical | frozen_bootstrap | frozen_full | candidate_bootstrap | candidate_full |
|---|---|---|---|---|---|
| scalar_pipeline | 0.2994 | 0.6994 | 201.4072 | 0.6025 | 121.4361 |
| scalar_dual_chain | 0.1790 | 0.3893 | 216.9893 | 0.3492 | 140.1648 |
| vector_axpy | 0.1999 | 0.5112 | 230.1494 | 0.4465 | 138.0901 |
| vector_bitmix | 0.2368 | 0.6761 | 447.6733 | 0.5844 | 208.8618 |
| mixed_broadcast | 0.1529 | 0.3490 | 660.0019 | 0.3124 | 460.4084 |
| parallel_memory | 1.4115 | 0.9661 | 414.6513 | 0.8163 | 157.1985 |
| scalar_selects | 1.3822 | 0.7953 | 527.5779 | 0.7850 | 200.3192 |
| vector_reduction | 0.3945 | 0.9413 | 434.7220 | 0.7918 | 192.2086 |

## Aggregate ratios

| Comparison | Geomean of per-program median ratios | 95% paired CI | Pooled median ratio | Slower programs |
|---|---:|---|---:|---|
| full_candidate_vs_frozen | 1.9471x | 1.9396–1.9509 | 2.3891x | none |
| bootstrap_candidate_vs_frozen | 1.1337x | 1.1280–1.1428 | 1.1699x | none |
| full_candidate_vs_classical | 0.0020x | 0.0020–0.0020 | 0.0015x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_candidate_vs_classical | 0.6560x | 0.6524–0.6649 | 0.4583x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
| full_frozen_vs_classical | 0.0010x | 0.0010–0.0010 | 0.0006x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
| bootstrap_frozen_vs_classical | 0.5786x | 0.5748–0.5855 | 0.3917x | mixed_broadcast, scalar_dual_chain, scalar_pipeline, vector_axpy, vector_bitmix, vector_reduction |
| optimizer_cost_frozen | 0.0017x | 0.0017–0.0018 | 0.0016x | mixed_broadcast, parallel_memory, scalar_dual_chain, scalar_pipeline, scalar_selects, vector_axpy, vector_bitmix, vector_reduction |
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
