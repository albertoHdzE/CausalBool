# HID multilevel v1 feasibility — multilevel-feasibility-v1-r1

Exploratory, descriptive study on 96 previously exposed strings. Not confirmation, not held-out performance; no interval, test, fractal or causal claim.

**Engineering verdict:** VALID_COMPLETE  
**Conditional exploratory label:** NO_RETAINED_GAIN

A3 shorter than A0 on 0 of 96 strings; A3 shorter than A2 on 0; A2 shorter than A0 on 0.

## Counts

| item | value |
|---|---:|
| strings | 96 |
| baseline_jobs_intended | 96 |
| baseline_jobs_with_rows | 96 |
| baseline_reproduced | 96 |
| augmentation_jobs_intended | 288 |
| augmentation_jobs_with_rows | 288 |
| augmentation_rows_valid | 288 |
| search_complete | 288 |
| traces | 288 |
| derived_composite_records | 288 |
| imported_reference_records | 864 |
| imported_reference_problems | 0 |
| derived_portfolio_references | 96 |
| view_records_A3 | 6144 |
| new_encoder_jobs | 384 |

## Contrasts (saving = (bits(B) − bits(A)) / n; positive: A shorter)

| contrast | equal-cell mean | strings better/tie/worse | cells better/tie/worse |
|---|---:|---|---|
| A1_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/24/0 (of 24) |
| A2_vs_A1 | 0.000000 | 0/96/0 (of 96) | 0/24/0 (of 24) |
| A3_vs_A2 | 0.000000 | 0/96/0 (of 96) | 0/24/0 (of 24) |
| A2_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/24/0 (of 24) |
| A3_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/24/0 (of 24) |
| A1_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 22/0/2 (of 24) |
| A2_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 22/0/2 (of 24) |
| A3_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 22/0/2 (of 24) |
| A1_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 5/3/16 (of 24) |
| A2_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 5/3/16 (of 24) |
| A3_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 5/3/16 (of 24) |
| A0_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 22/0/2 (of 24) |
| A0_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 5/3/16 (of 24) |

## Workload and selections

* **A1** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 192}; stop {'completed': 96}
* **A2** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 1536}; stop {'completed': 96}
* **A3** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 4244, 'SATURATED_REPETITION_BRANCH': 1840, 'SINGLE_SYMBOL_BRANCH': 60}; stop {'completed': 96}

## Runtime (seconds)

* Physical A0 worker wall: sum 44.32, max 0.968
* A1: augmentation worker sum 7.06, max 0.093; attributed deployment (A0 + augmentation) median 0.403, max 1.046
* A2: augmentation worker sum 8.84, max 0.129; attributed deployment (A0 + augmentation) median 0.415, max 1.096
* A3: augmentation worker sum 14.07, max 0.262; attributed deployment (A0 + augmentation) median 0.467, max 1.171
* All new jobs, worker wall sum: 74.29

## Width-by-level map (A3 views; 192 instances per cell = 96 strings × 2 origins)

| width | level | evaluated | ineligible | saturated-branch | single-branch | median k/m | median weak support | shorter than A0 | no shorter | no admissible | median (best−A0)/n |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1 | 192 | 0 | 0 | 0 | 0.016 | 0.001 | 0 | 192 | 0 | 0.6716 |
| 4 | 2 | 192 | 0 | 0 | 0 | 0.162 | 0.046 | 0 | 192 | 0 | 1.2292 |
| 4 | 3 | 192 | 0 | 0 | 0 | 0.512 | 0.321 | 0 | 192 | 0 | 1.9113 |
| 4 | 4 | 168 | 0 | 24 | 0 | 0.828 | 0.735 | 0 | 168 | 0 | 2.5284 |
| 8 | 1 | 192 | 0 | 0 | 0 | 0.163 | 0.048 | 0 | 192 | 0 | 0.8320 |
| 8 | 2 | 192 | 0 | 0 | 0 | 0.513 | 0.328 | 0 | 192 | 0 | 1.5527 |
| 8 | 3 | 170 | 0 | 22 | 0 | 0.843 | 0.750 | 0 | 170 | 0 | 2.2443 |
| 8 | 4 | 122 | 0 | 66 | 4 | 0.857 | 0.719 | 0 | 122 | 0 | 2.0234 |
| 12 | 1 | 192 | 0 | 0 | 0 | 0.346 | 0.205 | 0 | 192 | 0 | 1.0297 |
| 12 | 2 | 188 | 0 | 4 | 0 | 0.726 | 0.520 | 0 | 188 | 0 | 1.7806 |
| 12 | 3 | 146 | 0 | 46 | 0 | 0.905 | 0.813 | 0 | 146 | 0 | 1.8851 |
| 12 | 4 | 100 | 0 | 92 | 0 | 0.929 | 0.859 | 0 | 100 | 0 | 1.0602 |
| 16 | 1 | 192 | 0 | 0 | 0 | 0.526 | 0.336 | 0 | 192 | 0 | 0.9894 |
| 16 | 2 | 166 | 0 | 26 | 0 | 0.828 | 0.719 | 0 | 166 | 0 | 1.6031 |
| 16 | 3 | 122 | 0 | 66 | 4 | 0.867 | 0.750 | 0 | 122 | 0 | 1.6148 |
| 16 | 4 | 82 | 0 | 106 | 4 | 0.903 | 0.812 | 0 | 82 | 0 | 0.9453 |
| 24 | 1 | 192 | 0 | 0 | 0 | 0.738 | 0.546 | 0 | 192 | 0 | 0.9600 |
| 24 | 2 | 154 | 0 | 38 | 0 | 0.941 | 0.883 | 0 | 154 | 0 | 1.3549 |
| 24 | 3 | 96 | 0 | 96 | 0 | 0.929 | 0.859 | 0 | 96 | 0 | 0.8698 |
| 24 | 4 | 48 | 0 | 140 | 4 | 0.800 | 0.625 | 0 | 48 | 0 | 0.6201 |
| 32 | 1 | 192 | 0 | 0 | 0 | 0.905 | 0.817 | 0 | 192 | 0 | 0.7748 |
| 32 | 2 | 122 | 0 | 66 | 4 | 0.933 | 0.875 | 0 | 122 | 0 | 1.1197 |
| 32 | 3 | 80 | 0 | 108 | 4 | 0.889 | 0.781 | 0 | 80 | 0 | 0.8620 |
| 32 | 4 | 42 | 0 | 142 | 8 | 0.867 | 0.750 | 0 | 42 | 0 | 0.5141 |
| 48 | 1 | 192 | 0 | 0 | 0 | 0.971 | 0.947 | 0 | 192 | 0 | 0.5625 |
| 48 | 2 | 102 | 0 | 90 | 0 | 0.929 | 0.859 | 0 | 102 | 0 | 0.8125 |
| 48 | 3 | 48 | 0 | 140 | 4 | 0.800 | 0.625 | 0 | 48 | 0 | 0.5371 |
| 48 | 4 | 36 | 0 | 152 | 4 | 1.000 | 1.000 | 0 | 36 | 0 | 0.5603 |
| 64 | 1 | 192 | 0 | 0 | 0 | 1.000 | 1.000 | 0 | 192 | 0 | 0.4453 |
| 64 | 2 | 76 | 0 | 112 | 4 | 0.875 | 0.750 | 0 | 76 | 0 | 0.6748 |
| 64 | 3 | 42 | 0 | 142 | 8 | 0.867 | 0.750 | 0 | 42 | 0 | 0.5141 |
| 64 | 4 | 22 | 0 | 162 | 8 | 0.571 | 0.251 | 0 | 22 | 0 | 0.2656 |

These maps are diagnostics of this vocabulary on exposed data; they do not locate a universal word length or threshold.

## Explanations: 0 selected augmentation archives (explanations.jsonl)


Nested view equality: 96 strings, 0 mismatches.

