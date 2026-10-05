# HID dictionary relations v1 feasibility — dictionary-feasibility-v1-r1

Exploratory, descriptive study on 96 previously exposed strings. Not confirmation, not held-out performance; no interval, test, fractal or causal claim.

**Engineering verdict:** VALID_COMPLETE  
**Conditional exploratory label:** NO_RETAINED_GAIN

D2 shorter than D1 on 0 of 96 strings; D1 shorter than D0 on 0; D0 shorter than A0 on 0; D2 shorter than A0 on 0.

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
| watchdog_fallbacks | 0 |
| traces | 288 |
| new_encoder_jobs_intended | 384 |
| new_encoder_jobs_with_rows | 384 |
| derived_composite_records | 288 |
| imported_reference_records | 864 |
| imported_reference_problems | 0 |
| derived_portfolio_references | 96 |
| imported_old_a3_records | 96 |
| imported_old_a3_problems | 0 |
| view_records_D2 | 6144 |
| evaluated_views_D2 | 6096 |

## Contrasts (saving = (bits(B) − bits(A)) / n; positive: A shorter)

| contrast | equal-cell mean | strings better/tie/worse | pairs | cells |
|---|---:|---|---|---|
| D0_vs_oldA3 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D1_vs_D0 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D2_vs_D1 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D0_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D1_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D2_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |
| D0_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 44/0/4 (of 48) | 22/0/2 (of 24) |
| D1_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 44/0/4 (of 48) | 22/0/2 (of 24) |
| D2_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 44/0/4 (of 48) | 22/0/2 (of 24) |
| D0_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 11/6/31 (of 48) | 5/3/16 (of 24) |
| D1_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 11/6/31 (of 48) | 5/3/16 (of 24) |
| D2_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 11/6/31 (of 48) | 5/3/16 (of 24) |
| A0_vs_pair_grammar | 0.351713 | 87/0/9 (of 96) | 44/0/4 (of 48) | 22/0/2 (of 24) |
| A0_vs_portfolio | -0.045188 | 21/12/63 (of 96) | 11/6/31 (of 48) | 5/3/16 (of 24) |
| oldA3_vs_A0 | 0.000000 | 0/96/0 (of 96) | 0/48/0 (of 48) | 0/24/0 (of 24) |

## Workload and selections

* **D0** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 6096, 'INELIGIBLE_SHORT': 48}; stop {'completed': 96}; requests 17571, serialized 13338, decoded 9648, duplicates 3690, patch rejections 4233, graph rejections 0, relation comparisons 0
* **D1** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 6096, 'INELIGIBLE_SHORT': 48}; stop {'completed': 96}; requests 35142, serialized 26676, decoded 12183, duplicates 14493, patch rejections 8466, graph rejections 0, relation comparisons 0
* **D2** jobs {'ok': 96}; augmentation selected in 0 strings {}; views {'EVALUATED': 6096, 'INELIGIBLE_SHORT': 48}; stop {'completed': 96}; requests 70284, serialized 53352, decoded 19652, duplicates 33700, patch rejections 16932, graph rejections 0, relation comparisons 12398416

## Mode contributions (D2 traces; same view; descriptive)

| comparison | shorter | equal | longer | unavailable |
|---|---:|---:|---:|---:|
| P_vs_O | 368 | 4787 | 941 | 0 |
| R(O)_vs_O | 1243 | 2628 | 2225 | 0 |
| R(P)_vs_P | 1263 | 2628 | 2205 | 0 |
| R(P)_vs_O | 1359 | 2482 | 2255 | 0 |

Strings whose best mode-X archive (any view) beats the best O archive: {'P': 2, 'R(O)': 12, 'R(P)': 14}.

Construction: {'evaluated_views': 6096, 'dictionary_entries': 219053, 'period_replacements': 4195, 'views_with_period_replacement': 1392, 'non_dividing_proper_periods': 167147, 'relations_selected_R(O)': 130575, 'views_with_relation': 3514, 'relation_comparisons_R(O)': 6199208, 'hop_cap_rejections_R(O)': 354960, 'relations_selected_R(P)': 130575, 'relation_comparisons_R(P)': 6199208}; relation flags {0: 44455, 1: 25621, 2: 40699, 3: 19800}; hops {1: 21909, 2: 19151, 3: 17360, 4: 15165, 5: 13702, 6: 12517, 7: 12330, 8: 18441}.

## Runtime (seconds)

* Physical A0 worker wall: sum 45.16, max 0.980
* D0: augmentation worker sum 17.83, max 0.329; attributed deployment (A0 + augmentation) median 0.494, max 1.302
* D1: augmentation worker sum 25.27, max 0.507; attributed deployment (A0 + augmentation) median 0.538, max 1.471
* D2: augmentation worker sum 44.89, max 0.974; attributed deployment (A0 + augmentation) median 0.678, max 1.933
* All new jobs, worker wall sum: 133.16

## Width-by-level map (D2 views; 192 instances per cell = 96 strings × 2 origins)

| width | level | evaluated | ineligible | old mask would skip | median k/m | median (best−A0)/n | P<O | P>O | R(O)<O | R(O)>O | views with relation |
|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| 4 | 1 | 192 | 0 | 0 | 0.016 | 0.6716 | 0 | 173 | 0 | 192 | 192 |
| 4 | 2 | 192 | 0 | 0 | 0.162 | 1.2253 | 93 | 43 | 50 | 140 | 192 |
| 4 | 3 | 192 | 0 | 0 | 0.512 | 1.8723 | 18 | 60 | 100 | 92 | 192 |
| 4 | 4 | 192 | 0 | 24 | 0.891 | 2.3638 | 10 | 25 | 121 | 67 | 188 |
| 8 | 1 | 192 | 0 | 0 | 0.163 | 0.8320 | 0 | 157 | 0 | 192 | 192 |
| 8 | 2 | 192 | 0 | 0 | 0.513 | 1.5037 | 38 | 24 | 30 | 152 | 192 |
| 8 | 3 | 192 | 0 | 22 | 0.905 | 2.0420 | 8 | 32 | 112 | 70 | 188 |
| 8 | 4 | 192 | 0 | 70 | 1.000 | 2.6456 | 10 | 4 | 64 | 20 | 88 |
| 12 | 1 | 192 | 0 | 0 | 0.346 | 1.0297 | 1 | 127 | 0 | 192 | 192 |
| 12 | 2 | 192 | 0 | 4 | 0.738 | 1.7640 | 12 | 36 | 58 | 134 | 192 |
| 12 | 3 | 192 | 0 | 46 | 0.971 | 1.9892 | 0 | 20 | 72 | 52 | 126 |
| 12 | 4 | 192 | 0 | 92 | 1.000 | 2.7773 | 8 | 4 | 36 | 0 | 38 |
| 16 | 1 | 192 | 0 | 0 | 0.526 | 0.9894 | 0 | 75 | 0 | 188 | 192 |
| 16 | 2 | 192 | 0 | 26 | 0.906 | 1.5473 | 14 | 26 | 56 | 130 | 188 |
| 16 | 3 | 192 | 0 | 70 | 1.000 | 2.0412 | 10 | 4 | 62 | 24 | 88 |
| 16 | 4 | 192 | 0 | 110 | 1.000 | 2.4093 | 10 | 2 | 32 | 0 | 32 |
| 24 | 1 | 192 | 0 | 0 | 0.738 | 0.9600 | 0 | 44 | 0 | 192 | 192 |
| 24 | 2 | 192 | 0 | 38 | 0.988 | 1.3574 | 4 | 18 | 66 | 58 | 128 |
| 24 | 3 | 192 | 0 | 96 | 1.000 | 1.6942 | 8 | 4 | 34 | 0 | 34 |
| 24 | 4 | 192 | 0 | 144 | 1.000 | 1.8235 | 4 | 8 | 16 | 0 | 16 |
| 32 | 1 | 192 | 0 | 0 | 0.905 | 0.7748 | 0 | 17 | 24 | 162 | 188 |
| 32 | 2 | 192 | 0 | 70 | 1.000 | 1.1484 | 8 | 8 | 60 | 18 | 84 |
| 32 | 3 | 192 | 0 | 112 | 1.000 | 1.3359 | 8 | 4 | 36 | 0 | 36 |
| 32 | 4 | 192 | 0 | 150 | 1.000 | 1.4297 | 12 | 4 | 24 | 0 | 24 |
| 48 | 1 | 192 | 0 | 0 | 0.971 | 0.5625 | 18 | 0 | 30 | 100 | 130 |
| 48 | 2 | 192 | 0 | 90 | 1.000 | 0.7969 | 8 | 4 | 32 | 0 | 32 |
| 48 | 3 | 192 | 0 | 144 | 1.000 | 0.9297 | 4 | 8 | 16 | 0 | 16 |
| 48 | 4 | 192 | 0 | 156 | 1.000 | 0.9502 | 12 | 4 | 8 | 0 | 8 |
| 64 | 1 | 192 | 0 | 0 | 1.000 | 0.4453 | 16 | 0 | 42 | 50 | 92 |
| 64 | 2 | 192 | 0 | 116 | 1.000 | 0.6310 | 8 | 4 | 36 | 0 | 36 |
| 64 | 3 | 192 | 0 | 150 | 1.000 | 0.7197 | 16 | 0 | 18 | 0 | 18 |
| 64 | 4 | 144 | 48 | 122 | 1.000 | 0.7712 | 10 | 2 | 8 | 0 | 8 |

These maps are diagnostics of this vocabulary on exposed data; they do not locate a universal word length, threshold or mechanism.

## Explanations (0 selected archives; 384 representative best candidates; explanations.jsonl)


Nesting invariants: checked {'D0<=oldA3': 96, 'D1<=D0': 96, 'D2<=D1': 96, 'old_view': 4244, 'D1_O_equals_D0': 96, 'D2_O_equals_D0': 96}; 0 violations.

