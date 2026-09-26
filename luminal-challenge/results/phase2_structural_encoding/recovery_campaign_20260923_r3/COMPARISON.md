# Phase 2 recovery comparison

Quality is paired log(control J / candidate J); positive values favor the candidate. Runtime ratios are candidate / control, so values above 1 are slower. Quality and cost are reported separately. Secondary intervals are descriptive, unadjusted 95%; null-crossing intervals are inconclusive. Public and held-out programs are not pooled.

## Primary H2 (confirmatory)

Corpus `heldout`, budget 0.1 s, `structural_bound` versus `accepted_budgeted`. Endpoint: mean paired log(J_control / J_candidate) over repetitions, then seeds, then programs.

| Programs (paired/expected) | Families | Estimate [95% interval] | W/T/L | Reading |
|---:|---|---|---:|---|
| 100/100 | {'aliasing': 20, 'dependency': 20, 'mixed': 20, 'scalar': 20, 'vector': 20} | 0.04389 [0.02513, 0.06596] | 26/74/0 | interval above zero: the candidate has lower J |

## Descriptive matrix (24 entries)

| Corpus | Budget | Control | Programs | Quality log ratio (95% interval) | W/T/L | Mean C/S/J candidate vs control | Process ratio | Compile ratio | Peak RSS ratio | Failures | Interpretation |
|---|---:|---|---:|---|---:|---|---:|---:|---:|---:|---|
| public | 0.01 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.8778 [0.861, 0.8951] | 0.3062 [0.2303, 0.4011] | 0.9924 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2187 [0.1761, 0.259] | 0.01786 [0.01376, 0.02292] | 0.918 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.065 [1.034, 1.106] | 5.452 [4.12, 7.15] | 1.003 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.497 [1.459, 1.546] | 12.6 [9.333, 16.48] | 1.177 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.3517 [0.3421, 0.3629] | 0.03288 [0.02458, 0.04332] | 0.9507 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2234 [0.174, 0.2686] | 0.01794 [0.01366, 0.02318] | 0.918 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.088 [1.057, 1.124] | 5.475 [4.151, 7.085] | 1.003 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.529 [1.481, 1.586] | 12.66 [9.419, 16.41] | 1.177 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2204 [0.1727, 0.2641] | 0.0178 [0.01359, 0.02298] | 0.9162 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2202 [0.1722, 0.2645] | 0.0178 [0.01358, 0.02291] | 0.9172 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.072 [1.055, 1.09] | 5.434 [4.131, 7.036] | 1.002 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.507 [1.487, 1.528] | 12.56 [9.365, 16.28] | 1.176 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_budgeted | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 0.8968 [0.8901, 0.9038] | 0.4356 [0.4011, 0.4717] | 0.993 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2811 [0.2496, 0.3181] | 0.04214 [0.03411, 0.05268] | 0.9338 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.072 [1.063, 1.081] | 4.004 [3.442, 4.625] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.492 [1.478, 1.507] | 7.276 [6.013, 8.73] | 1.179 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_budgeted | 100/100 | 0.04389 [0.02513, 0.06596] | 26/74/0 | 13.97/13.96, 37.71/38.66, 661.5/670.5 | 0.4284 [0.4057, 0.4544] | 0.07258 [0.06248, 0.08506] | 0.9416 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2819 [0.2503, 0.3188] | 0.0422 [0.03418, 0.05276] | 0.9332 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.075 [1.066, 1.084] | 4.009 [3.446, 4.632] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.497 [1.482, 1.512] | 7.286 [6.02, 8.742] | 1.179 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_budgeted | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2835 [0.2519, 0.3203] | 0.04224 [0.03421, 0.05281] | 0.9332 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2847 [0.2529, 0.3218] | 0.04223 [0.03419, 0.05279] | 0.9335 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.086 [1.076, 1.096] | 4.012 [3.449, 4.636] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.511 [1.496, 1.527] | 7.292 [6.025, 8.747] | 1.179 | 0 | quality/runtime tradeoff must be read separately |

Primary H2 is the fixed held-out P5 `structural_bound` versus `accepted_budgeted` comparison at 0.1 s, reported above with its family-stratified 95% interval. Every entry of this matrix, including the public ones, is descriptive and unadjusted. Programs are shown as paired/expected; a program without a complete paired schedule is listed in COMPARISON.json `unpaired_programs`, never silently dropped. `J=C×S`; the official composite score is not substituted for this endpoint.
