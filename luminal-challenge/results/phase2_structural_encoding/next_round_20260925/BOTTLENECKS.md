# Stage D bottlenecks (separate cProfile runs; never timing rows)

Ten profiling programs (first two seeds of each family), one run per arm and budget. Every function's exclusive time is attributed to one category; built-ins and shared helpers are split over their callers. `reconciliation` = profiled exclusive time / wall time of the profiled call. Profiling inflates call-heavy code, so shares, not seconds, are compared.

| Arm @ budget | reconciliation | domain | propagation | frontier | encoding | validation | orchestration | largest |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| cell_a3cat_dfs@0.01 | 0.995 | 0.332 | 0.236 | 0.064 | 0.124 | 0.172 | 0.072 | domain_construction |
| cell_a3cat_dfs@0.1 | 0.995 | 0.302 | 0.266 | 0.071 | 0.116 | 0.172 | 0.073 | domain_construction |
| cell_a3cat_dfs@1.0 | 0.995 | 0.301 | 0.267 | 0.071 | 0.116 | 0.172 | 0.073 | domain_construction |
| cell_a3cat_heap@0.01 | 0.995 | 0.331 | 0.236 | 0.068 | 0.121 | 0.172 | 0.071 | domain_construction |
| cell_a3cat_heap@0.1 | 0.996 | 0.294 | 0.282 | 0.078 | 0.110 | 0.166 | 0.071 | domain_construction |
| cell_a3cat_heap@1.0 | 0.996 | 0.294 | 0.283 | 0.077 | 0.110 | 0.165 | 0.071 | domain_construction |
| cell_a4cat_dfs@0.01 | 0.996 | 0.272 | 0.443 | 0.038 | 0.098 | 0.095 | 0.055 | propagation |
| cell_a4cat_dfs@0.1 | 0.999 | 0.096 | 0.751 | 0.055 | 0.034 | 0.035 | 0.029 | propagation |
| cell_a4cat_dfs@1.0 | 0.999 | 0.071 | 0.800 | 0.052 | 0.025 | 0.028 | 0.024 | propagation |
| cell_a4cat_heap@0.01 | 0.996 | 0.275 | 0.439 | 0.038 | 0.098 | 0.096 | 0.054 | propagation |
| cell_a4cat_heap@0.1 | 0.999 | 0.084 | 0.782 | 0.054 | 0.029 | 0.024 | 0.026 | propagation |
| cell_a4cat_heap@1.0 | 1.000 | 0.057 | 0.825 | 0.055 | 0.020 | 0.021 | 0.022 | propagation |
| earlier_cap512_wider@0.01 | 0.994 | 0.143 | 0.262 | 0.288 | 0.111 | 0.137 | 0.059 | frontier |
| earlier_cap512_wider@0.1 | 0.998 | 0.069 | 0.403 | 0.424 | 0.039 | 0.027 | 0.038 | frontier |
| earlier_cap512_wider@1.0 | 0.999 | 0.053 | 0.429 | 0.449 | 0.024 | 0.013 | 0.033 | frontier |

