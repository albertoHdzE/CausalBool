# Stage D: 2x2 catalog x traversal factorial (development, descriptive)

Rows 4500/4500, failed 0, timed out 0. 100 development programs (seeds 800000-800099, 20 per family) x 3 repetitions. log J differences, family-weighted; negative = the first-named level has LOWER J. Intervals: 95% program-within-family bootstrap, descriptive only (development data).

## Budget 0.01 s

| Contrast | Estimate | 95% interval |
|---|---:|---|
| catalog_effect_a4_minus_a3 | -0.00946 | [-0.02216, +0.00142] |
| traversal_effect_heap_minus_dfs | +0.00296 | [-0.00023, +0.00654] |
| interaction | +0.01075 | [+0.00318, +0.01976] |
| catalog_effect_under_heap | -0.00409 | [-0.01851, +0.00887] |
| catalog_effect_under_dfs | -0.01483 | [-0.02715, -0.00419] |
| traversal_effect_under_a4 | +0.00833 | [+0.00193, +0.01550] |
| traversal_effect_under_a3 | -0.00242 | [-0.00655, +0.00000] |

| Arm | mean log J | geo. compile s | geo. optimisation s | geo. bootstrap s | geo. process s |
|---|---:|---:|---:|---:|---:|
| cell_a3cat_dfs | 5.77954 | 0.0042 | 0.0026 | 0.0012 | 0.0563 |
| cell_a3cat_heap | 5.77712 | 0.0043 | 0.0026 | 0.0012 | 0.0565 |
| cell_a4cat_dfs | 5.76471 | 0.0113 | 0.0093 | 0.0012 | 0.0626 |
| cell_a4cat_heap | 5.77304 | 0.0113 | 0.0093 | 0.0012 | 0.0626 |
| earlier_cap512_wider | 5.75925 | 0.0118 | 0.0097 | 0.0012 | 0.0619 |

## Budget 0.1 s

| Contrast | Estimate | 95% interval |
|---|---:|---|
| catalog_effect_a4_minus_a3 | -0.06235 | [-0.08429, -0.04304] |
| traversal_effect_heap_minus_dfs | +0.00202 | [-0.00343, +0.00700] |
| interaction | +0.00748 | [-0.00304, +0.01718] |
| catalog_effect_under_heap | -0.05861 | [-0.08101, -0.03928] |
| catalog_effect_under_dfs | -0.06609 | [-0.08924, -0.04546] |
| traversal_effect_under_a4 | +0.00576 | [-0.00458, +0.01518] |
| traversal_effect_under_a3 | -0.00172 | [-0.00516, +0.00000] |

| Arm | mean log J | geo. compile s | geo. optimisation s | geo. bootstrap s | geo. process s |
|---|---:|---:|---:|---:|---:|
| cell_a3cat_dfs | 5.77519 | 0.0043 | 0.0027 | 0.0012 | 0.0567 |
| cell_a3cat_heap | 5.77347 | 0.0044 | 0.0027 | 0.0012 | 0.0568 |
| cell_a4cat_dfs | 5.70910 | 0.0555 | 0.0526 | 0.0012 | 0.1196 |
| cell_a4cat_heap | 5.71486 | 0.0577 | 0.0548 | 0.0012 | 0.1219 |
| earlier_cap512_wider | 5.73528 | 0.0549 | 0.0527 | 0.0012 | 0.1142 |

## Budget 1.0 s

| Contrast | Estimate | 95% interval |
|---|---:|---|
| catalog_effect_a4_minus_a3 | -0.07910 | [-0.10676, -0.05585] |
| traversal_effect_heap_minus_dfs | +0.00279 | [-0.00244, +0.00824] |
| interaction | +0.00902 | [-0.00119, +0.01987] |
| catalog_effect_under_heap | -0.07459 | [-0.10168, -0.05171] |
| catalog_effect_under_dfs | -0.08361 | [-0.11278, -0.05883] |
| traversal_effect_under_a4 | +0.00730 | [-0.00251, +0.01784] |
| traversal_effect_under_a3 | -0.00172 | [-0.00516, +0.00000] |

| Arm | mean log J | geo. compile s | geo. optimisation s | geo. bootstrap s | geo. process s |
|---|---:|---:|---:|---:|---:|
| cell_a3cat_dfs | 5.77519 | 0.0043 | 0.0027 | 0.0012 | 0.0567 |
| cell_a3cat_heap | 5.77347 | 0.0044 | 0.0027 | 0.0012 | 0.0568 |
| cell_a4cat_dfs | 5.69158 | 0.0909 | 0.0869 | 0.0012 | 0.1745 |
| cell_a4cat_heap | 5.69888 | 0.0978 | 0.0937 | 0.0012 | 0.1821 |
| earlier_cap512_wider | 5.72688 | 0.0874 | 0.0847 | 0.0012 | 0.1641 |

## Targets (J <= floor((1-r) J_bootstrap)); every row in the denominator

| Arm | r | budget | attainment | median capped hitting time (s) |
|---|---:|---:|---:|---:|
| cell_a3cat_dfs | 0.01 | 0.01 | 0.370 | censored |
| cell_a3cat_dfs | 0.01 | 0.1 | 0.400 | censored |
| cell_a3cat_dfs | 0.01 | 1.0 | 0.400 | censored |
| cell_a3cat_dfs | 0.05 | 0.01 | 0.260 | censored |
| cell_a3cat_dfs | 0.05 | 0.1 | 0.280 | censored |
| cell_a3cat_dfs | 0.05 | 1.0 | 0.280 | censored |
| cell_a3cat_heap | 0.01 | 0.01 | 0.380 | censored |
| cell_a3cat_heap | 0.01 | 0.1 | 0.400 | censored |
| cell_a3cat_heap | 0.01 | 1.0 | 0.400 | censored |
| cell_a3cat_heap | 0.05 | 0.01 | 0.270 | censored |
| cell_a3cat_heap | 0.05 | 0.1 | 0.280 | censored |
| cell_a3cat_heap | 0.05 | 1.0 | 0.280 | censored |
| cell_a4cat_dfs | 0.01 | 0.01 | 0.400 | censored |
| cell_a4cat_dfs | 0.01 | 0.1 | 0.670 | 0.0169 |
| cell_a4cat_dfs | 0.01 | 1.0 | 0.710 | 0.0168 |
| cell_a4cat_dfs | 0.05 | 0.01 | 0.340 | censored |
| cell_a4cat_dfs | 0.05 | 0.1 | 0.520 | 0.0697 |
| cell_a4cat_dfs | 0.05 | 1.0 | 0.540 | 0.0696 |
| cell_a4cat_heap | 0.01 | 0.01 | 0.350 | censored |
| cell_a4cat_heap | 0.01 | 0.1 | 0.650 | 0.0228 |
| cell_a4cat_heap | 0.01 | 1.0 | 0.690 | 0.0228 |
| cell_a4cat_heap | 0.05 | 0.01 | 0.300 | censored |
| cell_a4cat_heap | 0.05 | 0.1 | 0.470 | censored |
| cell_a4cat_heap | 0.05 | 1.0 | 0.530 | 0.1672 |
| earlier_cap512_wider | 0.01 | 0.01 | 0.380 | no trajectory |
| earlier_cap512_wider | 0.01 | 0.1 | 0.590 | no trajectory |
| earlier_cap512_wider | 0.01 | 1.0 | 0.600 | no trajectory |
| earlier_cap512_wider | 0.05 | 0.01 | 0.290 | no trajectory |
| earlier_cap512_wider | 0.05 | 0.1 | 0.430 | no trajectory |
| earlier_cap512_wider | 0.05 | 1.0 | 0.450 | no trajectory |

Hitting times are descriptive diagnostics, not proof of speed equivalence. The earlier optimizer records no incumbent trajectory: attainment only.

## Fixed-work diagnostic (10 profiling programs, no wall allowance)

| Cell @ node limit | mean log J | charged nodes | certificates | validations | geo. compile s | stopped because |
|---|---:|---:|---:|---:|---:|---|
| cell_a3cat_dfs@1000 | 5.59265 | 165 | 731 | 6 | 0.0043 | {'pass_complete': 10} |
| cell_a3cat_dfs@10000 | 5.59265 | 165 | 731 | 6 | 0.0044 | {'pass_complete': 10} |
| cell_a3cat_dfs@50000 | 5.59265 | 165 | 731 | 6 | 0.0043 | {'pass_complete': 10} |
| cell_a3cat_heap@1000 | 5.59265 | 187 | 811 | 6 | 0.0044 | {'pass_complete': 10} |
| cell_a3cat_heap@10000 | 5.59265 | 187 | 811 | 6 | 0.0044 | {'pass_complete': 10} |
| cell_a3cat_heap@50000 | 5.59265 | 187 | 811 | 6 | 0.0044 | {'pass_complete': 10} |
| cell_a4cat_dfs@1000 | 5.49749 | 4042 | 69007 | 23 | 0.0521 | {'pass_complete': 8, 'aggregate_nodes': 2} |
| cell_a4cat_dfs@10000 | 5.48696 | 8827 | 176500 | 25 | 0.0658 | {'pass_complete': 10} |
| cell_a4cat_dfs@50000 | 5.48696 | 8827 | 176500 | 25 | 0.0666 | {'pass_complete': 10} |
| cell_a4cat_heap@1000 | 5.52442 | 3585 | 62562 | 19 | 0.0512 | {'pass_complete': 8, 'aggregate_nodes': 2} |
| cell_a4cat_heap@10000 | 5.51107 | 10424 | 224583 | 20 | 0.0624 | {'pass_complete': 10} |
| cell_a4cat_heap@50000 | 5.51107 | 10424 | 224583 | 20 | 0.0621 | {'pass_complete': 10} |

equal charged-node limits; equal node count is not equal CPU work -- propagation certificates and validations are counted separately

