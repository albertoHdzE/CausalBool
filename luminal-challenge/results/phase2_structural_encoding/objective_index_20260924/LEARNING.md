# Fixture learning study (H_LEARN)

**Verdict: FAIL.** Complete 30-fixture membership: True; defects 0; failed rows 0.

Mean log(best_test_J control / best_test_J tree) at 0.1 s; positive favours the tree. Intervals are Bonferroni two-sided 98.33% (percentiles 1/120, 119/120), 10,000 fixture-within-family resamples, seed 2026092504.

| control | fixtures | point | interval | wins/ties/losses |
|---|---|---|---|---|
| hamming | 30 | +0.0000 | [+0.0000, +0.0000] | 0/30/0 |
| random | 30 | +0.0000 | [+0.0000, +0.0000] | 0/30/0 |
| shuffled_tree | 30 | +0.0000 | [+0.0000, +0.0000] | 0/30/0 |

## Design diagnostic fixed before evaluation (oracle and split only)

Evaluation fixtures with any TEST object strictly below the best training label: 0 of 30. best_test_J equals min_training_J for every arm on every fixture with no such object; if the count is 0 every H_LEARN contrast is identically 0 and H_LEARN cannot pass.

## Descriptive (unadjusted 95%)

| contrast | point | interval |
|---|---|---|
| tree vs ascending@0.01 | +0.0000 | [+0.0000, +0.0000] |
| tree vs empirical_cover@0.01 | +0.0000 | [+0.0000, +0.0000] |
| tree vs hamming@0.01 | +0.0000 | [+0.0000, +0.0000] |
| tree vs random@0.01 | +0.0000 | [+0.0000, +0.0000] |
| tree vs shuffled_tree@0.01 | +0.0000 | [+0.0000, +0.0000] |
| tree vs ascending@0.1 | +0.0000 | [+0.0000, +0.0000] |
| tree vs empirical_cover@0.1 | +0.0000 | [+0.0000, +0.0000] |
| tree vs hamming@0.1 | +0.0000 | [+0.0000, +0.0000] |
| tree vs random@0.1 | +0.0000 | [+0.0000, +0.0000] |
| tree vs shuffled_tree@0.1 | +0.0000 | [+0.0000, +0.0000] |
| tree vs ascending@1.0 | +0.0000 | [+0.0000, +0.0000] |
| tree vs empirical_cover@1.0 | +0.0000 | [+0.0000, +0.0000] |
| tree vs hamming@1.0 | +0.0000 | [+0.0000, +0.0000] |
| tree vs random@1.0 | +0.0000 | [+0.0000, +0.0000] |
| tree vs shuffled_tree@1.0 | +0.0000 | [+0.0000, +0.0000] |

## Fixed-work prefixes (descriptive; nested, not independent)

| arm | prefix | mean complete | mean test complete | mean elite-level test |
|---|---|---|---|---|
| ascending | 128 | 12.60 | 6.40 | 3.27 |
| ascending | 32 | 4.47 | 2.07 | 1.13 |
| ascending | 8 | 1.93 | 0.67 | 0.43 |
| ascending | whole_pool | 26.87 | 13.60 | 5.93 |
| hamming | 128 | 21.87 | 11.47 | 5.33 |
| hamming | 32 | 10.03 | 5.13 | 3.33 |
| hamming | 8 | 3.63 | 1.63 | 1.10 |
| hamming | whole_pool | 26.87 | 13.60 | 5.93 |
| random | 128 | 9.51 | 4.83 | 1.95 |
| random | 32 | 2.46 | 1.26 | 0.51 |
| random | 8 | 0.62 | 0.33 | 0.12 |
| random | whole_pool | 26.87 | 13.60 | 5.93 |
| shuffled_tree | 128 | 11.07 | 5.40 | 2.57 |
| shuffled_tree | 32 | 3.23 | 1.33 | 0.80 |
| shuffled_tree | 8 | 1.40 | 0.67 | 0.40 |
| shuffled_tree | whole_pool | 26.87 | 13.60 | 5.93 |
| tree | 128 | 12.30 | 6.37 | 4.40 |
| tree | 32 | 4.10 | 2.00 | 1.73 |
| tree | 8 | 1.83 | 0.77 | 0.57 |
| tree | whole_pool | 26.87 | 13.60 | 5.93 |

Original H4: INCONCLUSIVE (the accepted recovery_campaign_20260923_r3 H4 is unchanged; H_LEARN is a separate, new fixture hypothesis).
End-to-end learned compiler: BLOCKED_BY_H_LEARN.
