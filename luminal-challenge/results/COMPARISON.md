# Public pilot comparison

| Method | Cycle speedup | Scratch reduction | Combined score | Median compile ms |
|---|---:|---:|---:|---:|
| serial | 1.000x | 1.000x | 1.000x | 0.022 |
| classical | 1.494x | 2.420x | 1.901x | 0.267 |
| index | 1.494x | 2.420x | 1.901x | 8.009 |
| exhaustive | 1.494x | 2.420x | 1.901x | 81.279 |

32 identical-query controls; 32 completed in both solvers, 32 agreed exactly.

Status counts: {"index": {"SAT": 16, "UNSAT": 16}, "exhaustive": {"SAT": 16, "UNSAT": 16}}.

Scores are relative to the frozen serial compiler. Index and exhaustive are bounded
improvement passes over the same classical compiler. Equal scores do not establish
global optimality. This pilot does not establish an index-method advantage over
conventional compiler optimization.

See comparison.json for all runs, source hashes, query timings, node allocations,
witness anchors/free masks, process memory, and limitations.
