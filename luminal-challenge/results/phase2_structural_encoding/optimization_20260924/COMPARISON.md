# Fresh compiler comparison (optimization protocol 1.0)

Population: fresh compiler cohort, seeds 810000-810199, 40 per family; new instances of the same generator, not the private grader.

Completeness: 36000 rows observed, 36000 expected, missing 0, failed 0.

## Primary (single optimization primary)

- Endpoint: mean paired log(J_frozen_phase2 / J_selected_nonmodel) at 0.1 s; repetitions within program, equal family weights; positive favours new.
- Effect 0.045131, 95% family-stratified bootstrap interval [0.033652, 0.057543] (10000 resamples, seed 2026092403).
- Geometric J reduction 4.41% (interval 3.31% to 5.59%).
- Wins/ties/losses over 200 programs: 73/126/1.
- Verdict: **SUPPORTS_IMPROVEMENT**.

## Per family (primary)

| family | programs | mean log ratio | wins | losses |
|---|---|---|---|---|
| aliasing | 40 | 0.032624 | 12 | 0 |
| dependency | 40 | 0.030906 | 10 | 0 |
| mixed | 40 | 0.048003 | 17 | 1 |
| scalar | 40 | 0.058156 | 20 | 0 |
| vector | 40 | 0.055964 | 14 | 0 |

## Descriptive contrasts (unadjusted 95% intervals)

| contrast | effect | interval | W/T/L | compile ratio (cand/ctrl) | process ratio |
|---|---|---|---|---|---|
| selected_nonmodel@0.01_vs_accepted_budgeted@0.01 | 0.05339 | [0.03745, 0.07104] | 62/138/0 | 0.9894 | 0.9847 |
| selected_nonmodel@0.1_vs_accepted_budgeted@0.1 | 0.07519 | [0.06020, 0.09131] | 105/95/0 | 0.8283 | 0.9057 |
| selected_nonmodel@1.0_vs_accepted_budgeted@1.0 | 0.07836 | [0.06369, 0.09391] | 109/91/0 | 0.8292 | 0.9226 |
| selected_nonmodel@0.01_vs_accepted_default@None | 0.03858 | [0.02721, 0.05159] | 56/144/0 | 0.09494 | 0.308 |
| selected_nonmodel@0.1_vs_accepted_default@None | 0.07125 | [0.05678, 0.08658] | 102/98/0 | 0.4827 | 0.5992 |
| selected_nonmodel@1.0_vs_accepted_default@None | 0.07836 | [0.06369, 0.09391] | 109/91/0 | 0.8293 | 0.9241 |
| selected_nonmodel@0.01_vs_accepted_bootstrap@None | 0.05339 | [0.03745, 0.07104] | 62/138/0 | 8.95 | 1.178 |
| selected_nonmodel@0.1_vs_accepted_bootstrap@None | 0.08605 | [0.06823, 0.10522] | 108/92/0 | 45.5 | 2.291 |
| selected_nonmodel@1.0_vs_accepted_bootstrap@None | 0.09317 | [0.07536, 0.11230] | 115/85/0 | 78.18 | 3.534 |
| selected_nonmodel@0.01_vs_classical@None | 0.05652 | [0.03479, 0.07826] | 94/73/33 | 14.98 | 1.649 |
| selected_nonmodel@0.1_vs_classical@None | 0.08918 | [0.06856, 0.11063] | 118/60/22 | 76.18 | 3.208 |
| selected_nonmodel@1.0_vs_classical@None | 0.09630 | [0.07553, 0.11768] | 122/58/20 | 130.9 | 4.948 |
| selected_nonmodel@0.01_vs_frozen_phase2@0.01 | 0.01316 | [0.00426, 0.02317] | 26/161/13 | 2.348 | 1.103 |
| selected_nonmodel@0.1_vs_frozen_phase2@0.1 | 0.04513 | [0.03365, 0.05754] | 73/126/1 | 11.86 | 2.136 |
| selected_nonmodel@1.0_vs_frozen_phase2@1.0 | 0.05225 | [0.04045, 0.06480] | 83/117/0 | 20.4 | 3.285 |
| frozen_phase2@0.01_vs_accepted_budgeted@0.01 | 0.04023 | [0.02643, 0.05558] | 51/149/0 | 0.4213 | 0.893 |
| frozen_phase2@0.1_vs_accepted_budgeted@0.1 | 0.03006 | [0.01973, 0.04151] | 47/153/0 | 0.06981 | 0.4241 |
| frozen_phase2@1.0_vs_accepted_budgeted@1.0 | 0.02611 | [0.01687, 0.03675] | 44/156/0 | 0.04065 | 0.2808 |
| frozen_phase2@0.01_vs_accepted_default@None | 0.02542 | [0.01618, 0.03598] | 44/156/0 | 0.04042 | 0.2793 |
| frozen_phase2@0.1_vs_accepted_default@None | 0.02611 | [0.01687, 0.03675] | 44/156/0 | 0.04068 | 0.2806 |
| frozen_phase2@1.0_vs_accepted_default@None | 0.02611 | [0.01687, 0.03675] | 44/156/0 | 0.04065 | 0.2813 |
| frozen_phase2@0.01_vs_accepted_bootstrap@None | 0.04023 | [0.02643, 0.05558] | 51/149/0 | 3.811 | 1.068 |
| frozen_phase2@0.1_vs_accepted_bootstrap@None | 0.04092 | [0.02709, 0.05631] | 51/149/0 | 3.835 | 1.073 |
| frozen_phase2@1.0_vs_accepted_bootstrap@None | 0.04092 | [0.02709, 0.05631] | 51/149/0 | 3.832 | 1.076 |
| frozen_phase2@0.01_vs_classical@None | 0.04336 | [0.02294, 0.06411] | 81/87/32 | 6.38 | 1.496 |
| frozen_phase2@0.1_vs_classical@None | 0.04405 | [0.02369, 0.06464] | 81/88/31 | 6.421 | 1.502 |
| frozen_phase2@1.0_vs_classical@None | 0.04405 | [0.02369, 0.06464] | 81/88/31 | 6.416 | 1.506 |

## Absolute runtime

| arm | compile median | p95 | max | process median | overshoot max | peak RSS max |
|---|---|---|---|---|---|---|
| accepted_bootstrap@None | 0.001186 | 0.006779 | 0.007994 | 0.05007 | nan | 28508160 |
| accepted_default@None | 0.1734 | 0.4072 | 0.6622 | 0.222 | nan | 36356096 |
| classical@None | 0.0008137 | 0.005369 | 0.008723 | 0.03564 | nan | 24412160 |
| accepted_budgeted@0.01 | 0.01116 | 0.01726 | 0.01904 | 0.06023 | nan | 28901376 |
| accepted_budgeted@0.1 | 0.1008 | 0.1039 | 0.1078 | 0.1492 | nan | 31997952 |
| accepted_budgeted@1.0 | 0.1742 | 0.4062 | 0.6593 | 0.2234 | nan | 36356096 |
| frozen_phase2@0.01 | 0.005336 | 0.009948 | 0.01501 | 0.05421 | nan | 28786688 |
| frozen_phase2@0.1 | 0.005333 | 0.009981 | 0.03722 | 0.05429 | nan | 28721152 |
| frozen_phase2@1.0 | 0.005311 | 0.009973 | 0.03729 | 0.0545 | nan | 28786688 |
| selected_nonmodel@0.01 | 0.0111 | 0.017 | 0.02209 | 0.05917 | 0.005423 | 28639232 |
| selected_nonmodel@0.1 | 0.1004 | 0.1069 | 0.1081 | 0.1479 | 0.0004148 | 29147136 |
| selected_nonmodel@1.0 | 0.1244 | 0.7029 | 1.008 | 0.1725 | 0.0003215 | 29671424 |

## Conditional model compiler

```
{
 "status": "BLOCKED_BY_H4_NEW_OR_NOT_RUN"
}
```
