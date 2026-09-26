# Fresh compiler comparison

Selected (frozen on development): **A4_multiscale_search**. Fresh cohort seeds 910000-910199 (200 programs, 40 per family), 15 repetitions.

Completeness: {'expected': 63000, 'observed_rows': 63000, 'distinct_observed': 63000, 'missing': 0, 'duplicates': 0, 'unexpected': 0, 'failed': 0, 'complete': True}.

## Primary: output quality at 0.1 s (Bonferroni 98.33%)

Mean paired log(J_control / J_selected); positive favours the selected solver.

| control | programs | point | interval | wins/ties/losses |
|---|---|---|---|---|
| A0_frozen_phase2 | 200 | +0.0623 | [+0.0460, +0.0806] | 102/98/0 |
| accepted_budgeted | 200 | +0.0917 | [+0.0710, +0.1134] | 127/73/0 |
| classical | 200 | +0.1118 | [+0.0876, +0.1375] | 138/42/20 |

Claim: **best average output quality among A0, accepted_budgeted and classical at 0.1 s on this fresh population**.

## Compile and process time (selected / control; Bonferroni 98.33%)

| comparison | geometric ratio | interval |
|---|---|---|
| A0_frozen_phase2:compile_seconds | 11.650 | [10.035, 13.530] |
| A0_frozen_phase2:process_seconds | 2.211 | [2.085, 2.342] |
| accepted_budgeted:compile_seconds | 0.817 | [0.681, 0.975] |
| accepted_budgeted:process_seconds | 0.943 | [0.876, 1.016] |
| classical:compile_seconds | 76.199 | [62.411, 92.745] |
| classical:process_seconds | 3.329 | [3.137, 3.524] |

## Ladder steps (unadjusted 95%, descriptive)

| budget | step | quality point | interval | compile ratio |
|---|---|---|---|---|
| 0.01 | A0_frozen_phase2->A1_deadline_control | +0.0051 | [+0.0023, +0.0082] | 1.106 |
| 0.01 | A1_deadline_control->A2_product_search | -0.0010 | [-0.0027, +0.0003] | 0.849 |
| 0.01 | A2_product_search->A3_propagated_search | -0.0001 | [-0.0003, +0.0001] | 0.849 |
| 0.01 | A3_propagated_search->A4_multiscale_search | +0.0074 | [-0.0023, +0.0179] | 2.799 |
| 0.1 | A0_frozen_phase2->A1_deadline_control | +0.0055 | [+0.0025, +0.0091] | 1.175 |
| 0.1 | A1_deadline_control->A2_product_search | -0.0011 | [-0.0028, +0.0000] | 0.825 |
| 0.1 | A2_product_search->A3_propagated_search | +0.0000 | [+0.0000, +0.0000] | 0.825 |
| 0.1 | A3_propagated_search->A4_multiscale_search | +0.0579 | [+0.0442, +0.0726] | 14.574 |
| 1.0 | A0_frozen_phase2->A1_deadline_control | +0.0055 | [+0.0025, +0.0091] | 1.174 |
| 1.0 | A1_deadline_control->A2_product_search | -0.0011 | [-0.0028, +0.0000] | 0.825 |
| 1.0 | A2_product_search->A3_propagated_search | +0.0000 | [+0.0000, +0.0000] | 0.825 |
| 1.0 | A3_propagated_search->A4_multiscale_search | +0.0742 | [+0.0596, +0.0899] | 24.713 |
