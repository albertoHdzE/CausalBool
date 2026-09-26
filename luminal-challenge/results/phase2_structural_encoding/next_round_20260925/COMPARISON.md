# Stage C: head-to-head confirmation (200 fresh programs, 5 repetitions)

Rows 11000/11000, failed 0, timed out 0.

## Primary (prespecified, one comparison)

Mean paired log(J_earlier / J_A4) at 0.1 s = **+0.03124**, 95% [+0.01815, +0.04598] over 200 programs: **FAVOURS_A4**. A4 wins/ties/losses [55, 123, 22]; geometric compile ratio A4/earlier 0.978.

## Frozen candidate endpoints (98.75% intervals, Bonferroni over four)

| Reference | J ratio | 98.75% | compile ratio | 98.75% | W/T/L |
|---|---:|---|---:|---|---|
| earlier_cap512_wider | 0.95859 | [0.93906, 0.97566] | 0.9162 | [0.7822, 1.0623] | [70, 116, 14] |
| cell_a4cat_heap | 0.98902 | [0.97823, 0.99972] | 0.9372 | [0.8943, 0.9751] | [29, 161, 10] |

Routes: {'quality_route': False, 'efficiency_route': False} -> **TARGET_NOT_REACHED**.

## Descriptive (unadjusted 95%)

| Contrast | Estimate | 95% |
|---|---:|---|
| log(J_earlier_cap512_wider/J_cell_a4cat_heap)@0.01 | -0.00047 | [-0.01319, +0.01449] |
| log(J_earlier_cap512_wider/J_cell_a4cat_dfs)@0.01 | +0.02052 | [+0.00537, +0.03850] |
| log(J_cell_a4cat_heap/J_cell_a4cat_dfs)@0.01 | +0.02098 | [+0.01207, +0.03117] |
| log(J_classical/J_earlier_cap512_wider@0.01) | +0.07061 | [+0.04673, +0.09552] |
| log(J_classical/J_cell_a4cat_heap@0.01) | +0.07014 | [+0.04699, +0.09500] |
| log(J_classical/J_cell_a4cat_dfs@0.01) | +0.09113 | [+0.06756, +0.11656] |
| log(J_accepted_bootstrap/J_earlier_cap512_wider@0.01) | +0.06445 | [+0.04577, +0.08507] |
| log(J_accepted_bootstrap/J_cell_a4cat_heap@0.01) | +0.06398 | [+0.04448, +0.08644] |
| log(J_accepted_bootstrap/J_cell_a4cat_dfs@0.01) | +0.08496 | [+0.06273, +0.11052] |
| log(J_earlier_cap512_wider/J_cell_a4cat_heap)@0.1 | +0.03124 | [+0.01815, +0.04598] |
| log(J_earlier_cap512_wider/J_cell_a4cat_dfs)@0.1 | +0.04229 | [+0.02818, +0.05832] |
| log(J_cell_a4cat_heap/J_cell_a4cat_dfs)@0.1 | +0.01105 | [+0.00283, +0.01966] |
| log(J_classical/J_earlier_cap512_wider@0.1) | +0.11324 | [+0.08975, +0.13845] |
| log(J_classical/J_cell_a4cat_heap@0.1) | +0.14448 | [+0.12042, +0.17092] |
| log(J_classical/J_cell_a4cat_dfs@0.1) | +0.15553 | [+0.13098, +0.18224] |
| log(J_accepted_bootstrap/J_earlier_cap512_wider@0.1) | +0.10707 | [+0.08649, +0.13037] |
| log(J_accepted_bootstrap/J_cell_a4cat_heap@0.1) | +0.13831 | [+0.11447, +0.16499] |
| log(J_accepted_bootstrap/J_cell_a4cat_dfs@0.1) | +0.14936 | [+0.12504, +0.17680] |
| log(J_earlier_cap512_wider/J_cell_a4cat_heap)@1.0 | +0.03175 | [+0.02017, +0.04413] |
| log(J_earlier_cap512_wider/J_cell_a4cat_dfs)@1.0 | +0.03593 | [+0.02473, +0.04794] |
| log(J_cell_a4cat_heap/J_cell_a4cat_dfs)@1.0 | +0.00418 | [-0.00386, +0.01171] |
| log(J_classical/J_earlier_cap512_wider@1.0) | +0.13061 | [+0.10717, +0.15610] |
| log(J_classical/J_cell_a4cat_heap@1.0) | +0.16236 | [+0.13773, +0.18925] |
| log(J_classical/J_cell_a4cat_dfs@1.0) | +0.16654 | [+0.14170, +0.19362] |
| log(J_accepted_bootstrap/J_earlier_cap512_wider@1.0) | +0.12444 | [+0.10192, +0.14987] |
| log(J_accepted_bootstrap/J_cell_a4cat_heap@1.0) | +0.15619 | [+0.13155, +0.18371] |
| log(J_accepted_bootstrap/J_cell_a4cat_dfs@1.0) | +0.16037 | [+0.13518, +0.18836] |

## Costs (geometric median over programs of per-program medians, s)

| Arm @ budget | compile | optimisation | bootstrap | validate | process |
|---|---:|---:|---:|---:|---:|
| earlier_cap512_wider@0.01 | 0.0113 | 0.0091 | 0.0012 | 0.0006 | 0.0603 |
| earlier_cap512_wider@0.1 | 0.0584 | 0.0549 | 0.0012 | 0.0005 | 0.1177 |
| earlier_cap512_wider@1.0 | 0.1005 | 0.0954 | 0.0012 | 0.0005 | 0.1807 |
| cell_a4cat_heap@0.01 | 0.0110 | 0.0090 | 0.0011 | 0.0006 | 0.0611 |
| cell_a4cat_heap@0.1 | 0.0571 | 0.0540 | 0.0011 | 0.0006 | 0.1206 |
| cell_a4cat_heap@1.0 | 0.0992 | 0.0947 | 0.0011 | 0.0006 | 0.1847 |
| cell_a4cat_dfs@0.01 | 0.0110 | 0.0090 | 0.0011 | 0.0006 | 0.0610 |
| cell_a4cat_dfs@0.1 | 0.0535 | 0.0506 | 0.0011 | 0.0005 | 0.1172 |
| cell_a4cat_dfs@1.0 | 0.0891 | 0.0849 | 0.0011 | 0.0006 | 0.1732 |
| classical@None | 0.0008 | n/a | n/a | 0.0006 | 0.0368 |
| accepted_bootstrap@None | 0.0013 | n/a | 0.0012 | 0.0006 | 0.0514 |

## Repaired interruption accounting

- earlier_cap512_wider: {'interrupted_validation_total': 0, 'affected_queries': 0, 'construction_interruptions': 0, 'rows_with_successor_accounting': 0}
- cell_a4cat_heap: {'interrupted_validation_total': 9, 'affected_queries': 9, 'construction_interruptions': 75, 'rows_with_successor_accounting': 3000}
- cell_a4cat_dfs: {'interrupted_validation_total': 22, 'affected_queries': 22, 'construction_interruptions': 76, 'rows_with_successor_accounting': 3000}

The earlier optimizer's source is frozen and reports its own counters only.

