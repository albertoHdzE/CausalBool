# Experiment 3 — Scalability Resource Envelope

**Paper reference**: Section "Scalability and Resource Envelope" / Tables tab:exact-method,
tab:naive-envelope, tab:synthesis.

Benchmarks the exact index-set method against the naive exhaustive baseline across
network sizes `n = 30, 60, 80, 200` with three query tasks:
- T1 (single-node query)
- T2 (4-node query)
- T3 (8-node query, `|C_q| ≈ 10`)

Each size runs 5 replicates with pinned seeds for full reproducibility.

## Script

### `scalability_resource_envelope.py`

Pure Python, standard library only.  Generates a ring-topology network for each
(n, replicate) pair, runs each query task via `exact_query_representation`, measures
wall time and peak memory, then aggregates across replicates.

Key result: median `|C_q| = 10` for T3 at all four sizes; all wall times sub-millisecond.

Outputs written:
- `exact_runs.json` / `exact_runs.csv` — per-run measurements
- `exact_aggregated.csv` — medians per (n, task)
- `naive_envelope.json` / `naive_envelope.csv` — brute-force resource envelope
- `network_ensemble.json` — network specifications used
- `scalability_summary.json` — top-level summary
- `exact_method_rows.tex`, `naive_envelope_rows.tex`, `synthesis_rows.tex` — paper tables
- `session_excerpt.txt` — human-readable run log

## Run

```bash
python3 scalability_resource_envelope.py
```

No arguments needed. Expected runtime: under 5 seconds on any modern CPU.
