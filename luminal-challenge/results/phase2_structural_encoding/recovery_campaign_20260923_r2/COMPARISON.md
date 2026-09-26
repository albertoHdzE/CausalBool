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
| public | 0.01 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.8768 [0.8611, 0.8928] | 0.3036 [0.2287, 0.3961] | 0.9927 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.215 [0.1679, 0.2575] | 0.01778 [0.01354, 0.02294] | 0.917 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.061 [1.042, 1.081] | 5.439 [4.133, 7.051] | 1.003 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.01 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.497 [1.465, 1.529] | 12.48 [9.284, 16.18] | 1.176 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.3416 [0.3354, 0.3479] | 0.0325 [0.02437, 0.04257] | 0.9504 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2157 [0.1686, 0.258] | 0.0178 [0.01356, 0.02298] | 0.9162 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.065 [1.044, 1.085] | 5.447 [4.134, 7.063] | 1.003 | 0 | quality/runtime tradeoff must be read separately |
| public | 0.1 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.501 [1.468, 1.535] | 12.5 [9.292, 16.19] | 1.175 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_budgeted | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2179 [0.1709, 0.2608] | 0.01778 [0.01354, 0.02299] | 0.9172 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_default | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 0.2189 [0.1715, 0.2629] | 0.01781 [0.01357, 0.02299] | 0.9165 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | accepted_bootstrap | 8/8 | 0.02405 [0, 0.07214] | 1/7/0 | 10.75/10.75, 22/22.88, 244.8/255.2 | 1.081 [1.061, 1.099] | 5.448 [4.141, 7.066] | 1.003 | 0 | quality/runtime tradeoff must be read separately |
| public | 1.0 | classical | 8/8 | 0.1336 [-0.0865, 0.3352] | 4/3/1 | 10.75/10.88, 22/25.25, 244.8/290 | 1.524 [1.489, 1.554] | 12.5 [9.302, 16.2] | 1.176 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_budgeted | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 0.8989 [0.8921, 0.906] | 0.438 [0.4033, 0.4743] | 0.993 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.283 [0.2517, 0.3198] | 0.04232 [0.03428, 0.0529] | 0.9338 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.073 [1.064, 1.083] | 4.004 [3.442, 4.627] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.01 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.492 [1.477, 1.507] | 7.28 [6.017, 8.735] | 1.178 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_budgeted | 100/100 | 0.04389 [0.02513, 0.06596] | 26/74/0 | 13.97/13.96, 37.71/38.66, 661.5/670.5 | 0.431 [0.4083, 0.4569] | 0.07297 [0.06282, 0.0855] | 0.9421 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2836 [0.2521, 0.3202] | 0.04237 [0.03435, 0.05296] | 0.9337 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.075 [1.066, 1.085] | 4.009 [3.444, 4.631] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 0.1 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.495 [1.479, 1.51] | 7.288 [6.018, 8.743] | 1.178 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_budgeted | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2851 [0.2534, 0.3222] | 0.04238 [0.03435, 0.05298] | 0.9336 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_default | 100/100 | 0.04028 [0.0223, 0.06144] | 25/75/0 | 13.97/13.96, 37.71/38.63, 661.5/670.2 | 0.2863 [0.2545, 0.3237] | 0.0424 [0.03436, 0.05302] | 0.9337 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | accepted_bootstrap | 100/100 | 0.05662 [0.03294, 0.08464] | 31/69/0 | 13.97/13.98, 37.71/38.77, 661.5/672.3 | 1.086 [1.075, 1.096] | 4.011 [3.445, 4.633] | 1.005 | 0 | quality/runtime tradeoff must be read separately |
| heldout | 1.0 | classical | 100/100 | 0.0882 [0.05923, 0.1194] | 53/35/12 | 13.97/13.7, 37.71/41.93, 661.5/717.9 | 1.509 [1.492, 1.526] | 7.292 [6.026, 8.75] | 1.178 | 0 | quality/runtime tradeoff must be read separately |

Primary H2 is the fixed held-out P5 `structural_bound` versus `accepted_budgeted` comparison at 0.1 s, reported above with its family-stratified 95% interval. Every entry of this matrix, including the public ones, is descriptive and unadjusted. Programs are shown as paired/expected; a program without a complete paired schedule is listed in COMPARISON.json `unpaired_programs`, never silently dropped. `J=C×S`; the official composite score is not substituted for this endpoint.
