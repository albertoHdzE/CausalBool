# Model evaluation (optimization protocol 1.0)

## Original H4 (historical, unchanged)

- INCONCLUSIVE: only one fixture/family qualified in the OLD experiment.

## H4_NEW (new study, qualified fixtures)

- Selected depth: 1.
- Endpoint: best_test_J = min(min_training_J, validated new TEST objects); log(best_test_J_control / best_test_J_model); repetitions then uniform seeds then fixtures, equal family weights; 97.5% family-stratified bootstrap (.0125/.9875), 10000 resamples, seed 2026092403.
- Gate: `{"all_30_fixtures_accounted": true, "informative_families": 5, "at_least_3_families": true, "correctness_or_evidence_defects": 0, "lower_bounds": [0.0, 0.0], "both_lower_bounds_positive": false}`.
- **H4_NEW: INCONCLUSIVE**.

| budget | control | effect | 97.5% interval | 95% interval | W/T/L | fixtures |
|---|---|---|---|---|---|---|
| 0.01 | one_bit | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 0.01 | uniform_bits | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 0.01 | empirical_cover | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 0.1 | one_bit | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 0.1 | uniform_bits | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 0.1 | empirical_cover | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 1.0 | one_bit | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 1.0 | uniform_bits | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |
| 1.0 | empirical_cover | 0.000000 | [0.000000, 0.000000] | [0.000000, 0.000000] | 0/30/0 | 30 |

## Counts per arm and budget

```
{
 "empirical_cover@0.01": {
  "rows": 450,
  "attempted": 3660,
  "complete": 0,
  "complete_at_or_below_elite": 0,
  "dead_end": 0,
  "duplicate": 3660,
  "exhausted_rows": 390,
  "interrupted": 0,
  "invalid_code": 0,
  "not_better": 0,
  "novel": 0,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 1.9531789138673048
 },
 "empirical_cover@0.1": {
  "rows": 450,
  "attempted": 4785,
  "complete": 0,
  "complete_at_or_below_elite": 0,
  "dead_end": 0,
  "duplicate": 4785,
  "exhausted_rows": 450,
  "interrupted": 0,
  "invalid_code": 0,
  "not_better": 0,
  "novel": 0,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 2.2708294009935344
 },
 "empirical_cover@1.0": {
  "rows": 450,
  "attempted": 4785,
  "complete": 0,
  "complete_at_or_below_elite": 0,
  "dead_end": 0,
  "duplicate": 4785,
  "exhausted_rows": 450,
  "interrupted": 0,
  "invalid_code": 0,
  "not_better": 0,
  "novel": 0,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 2.260982025971316
 },
 "one_bit@0.01": {
  "rows": 450,
  "attempted": 23311,
  "complete": 4822,
  "complete_at_or_below_elite": 2268,
  "dead_end": 982,
  "duplicate": 5014,
  "exhausted_rows": 251,
  "interrupted": 0,
  "invalid_code": 12493,
  "not_better": 4822,
  "novel": 18297,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 3.4871921180165373
 },
 "one_bit@0.1": {
  "rows": 450,
  "attempted": 41505,
  "complete": 7875,
  "complete_at_or_below_elite": 4140,
  "dead_end": 1830,
  "duplicate": 7860,
  "exhausted_rows": 450,
  "interrupted": 0,
  "invalid_code": 23940,
  "not_better": 7875,
  "novel": 33645,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 6.962161495088367
 },
 "one_bit@1.0": {
  "rows": 450,
  "attempted": 41505,
  "complete": 7875,
  "complete_at_or_below_elite": 4140,
  "dead_end": 1830,
  "duplicate": 7860,
  "exhausted_rows": 450,
  "interrupted": 0,
  "invalid_code": 23940,
  "not_better": 7875,
  "novel": 33645,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 6.964841709923348
 },
 "selected_model@0.01": {
  "rows": 450,
  "attempted": 22895,
  "complete": 4725,
  "complete_at_or_below_elite": 2232,
  "dead_end": 936,
  "duplicate": 5091,
  "exhausted_rows": 239,
  "interrupted": 0,
  "invalid_code": 12143,
  "not_better": 4725,
  "novel": 17804,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 3.550847685921326
 },
 "selected_model@0.1": {
  "rows": 450,
  "attempted": 41715,
  "complete": 7875,
  "complete_at_or_below_elite": 4140,
  "dead_end": 1830,
  "duplicate": 8070,
  "exhausted_rows": 449,
  "interrupted": 0,
  "invalid_code": 23940,
  "not_better": 7875,
  "novel": 33645,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 7.128178618015227
 },
 "selected_model@1.0": {
  "rows": 450,
  "attempted": 41715,
  "complete": 7875,
  "complete_at_or_below_elite": 4140,
  "dead_end": 1830,
  "duplicate": 8070,
  "exhausted_rows": 450,
  "interrupted": 0,
  "invalid_code": 23940,
  "not_better": 7875,
  "novel": 33645,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 7.118824427067011
 },
 "uniform_bits@0.01": {
  "rows": 4500,
  "attempted": 3074574,
  "complete": 28426,
  "complete_at_or_below_elite": 8606,
  "dead_end": 25225,
  "duplicate": 2290994,
  "exhausted_rows": 0,
  "interrupted": 0,
  "invalid_code": 729904,
  "not_better": 28426,
  "novel": 783580,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 45.377105612835294
 },
 "uniform_bits@0.1": {
  "rows": 4500,
  "attempted": 702306249,
  "complete": 104482,
  "complete_at_or_below_elite": 30246,
  "dead_end": 319331,
  "duplicate": 695523978,
  "exhausted_rows": 0,
  "interrupted": 0,
  "invalid_code": 6358446,
  "not_better": 104482,
  "novel": 6782271,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 450.05491850003455
 },
 "uniform_bits@1.0": {
  "rows": 4500,
  "attempted": 13388178649,
  "complete": 133401,
  "complete_at_or_below_elite": 43328,
  "dead_end": 1643957,
  "duplicate": 13366205126,
  "exhausted_rows": 0,
  "interrupted": 0,
  "invalid_code": 20196163,
  "not_better": 133401,
  "novel": 21973523,
  "validated": 0,
  "validation_rejected": 0,
  "discoveries_absent": 0,
  "discoveries_test": 0,
  "discoveries_train": 0,
  "discoveries_validation": 0,
  "learner_seconds_total": 4500.06388593886
 }
}
```
