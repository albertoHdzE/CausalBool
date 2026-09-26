# Public score (exact fixed suite)

sqrt(GM(C_serial/C_arm) * GM(S_serial/S_arm)), eight public programs, one score per repetition.

| arm | min | max | geometric mean over 15 repetitions |
|---|---|---|---|
| A0_frozen_phase2@0.01 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A0_frozen_phase2@0.1 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A0_frozen_phase2@1.0 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A1_deadline_control@0.01 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A1_deadline_control@0.1 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A1_deadline_control@1.0 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A2_product_search@0.01 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A2_product_search@0.1 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A2_product_search@1.0 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A3_propagated_search@0.01 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A3_propagated_search@0.1 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A3_propagated_search@1.0 | 2.0327602339 | 2.0327602339 | 2.0327602339 |
| A4_multiscale_search@0.01 | 2.0366734585 | 2.0366734585 | 2.0366734585 |
| A4_multiscale_search@0.1 | 2.0889454903 | 2.0889454903 | 2.0889454903 |
| A4_multiscale_search@1.0 | 2.1027466544 | 2.1027466544 | 2.1027466544 |
| accepted_bootstrap@None | 2.0084662023 | 2.0084662023 | 2.0084662023 |
| accepted_budgeted@0.01 | 2.0084662023 | 2.0084662023 | 2.0084662023 |
| accepted_budgeted@0.1 | 2.0084662023 | 2.0084662023 | 2.0084662023 |
| accepted_budgeted@1.0 | 2.0084662023 | 2.0084662023 | 2.0084662023 |
| accepted_default@None | 2.0084662023 | 2.0084662023 | 2.0084662023 |
| classical@None | 1.9013791213 | 1.9013791213 | 1.9013791213 |

Selected: A4_multiscale_search@0.1.

| versus | improving | tied | worsening | strict every repetition |
|---|---|---|---|---|
| A0_frozen_phase2@0.1 | 15 | 0 | 0 | True |
| accepted_budgeted@0.1 | 15 | 0 | 0 | True |
| accepted_default@None | 15 | 0 | 0 | True |
| classical@None | 15 | 0 | 0 | True |
