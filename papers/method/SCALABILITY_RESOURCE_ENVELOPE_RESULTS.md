# Scalability and Resource-Envelope Results

## Purpose

This document records the first executed results of the scalability/resource-envelope phase defined
in `SCALABILITY_RESOURCE_ENVELOPE_PLAN.md`. It is not yet the manuscript section. It is a stable
research note summarizing what was actually run, what was measured, and what conclusions are already
supported.

---

## Executed Benchmark

### Implementation Path

The executed benchmark is paper-local and lives in:

- `papers/method/code/scalability_resource_envelope/scalability_resource_envelope.py`

It uses a Python implementation because the current Wolfram environment on this machine is not
reliable for long benchmark execution.

### Benchmark Regime

The run targeted exact query-focused causal evaluation in large ambient networks.

Network sizes:

- `n = 30`
- `n = 60`
- `n = 80`
- `n = 200`

Replicates:

- `5` deterministic networks per size

Network family:

- ring-local heterogeneous Boolean networks
- local window `4`
- maximum in-degree `4`
- gate catalogue:
  - AND
  - OR
  - XOR
  - NAND
  - NOR
  - XNOR
  - NOT
  - IMPLIES
  - NIMPLIES
  - MAJORITY
  - KOFN

### Query Tasks

- `T1_single`: one queried node
- `T2_small`: four queried nodes
- `T3_medium`: eight queried nodes

For each network, the requested output pattern was taken from a witness state, so every query was
guaranteed to be satisfiable.

---

## Scientific Interpretation of the Benchmark

The benchmark does not compare:

- a full exhaustive table produced by our method

against

- a full exhaustive table produced naively.

Instead, it compares:

- naive exhaustive materialization of the global search space

against

- exact compressed causal evaluation of a query whose relevant support remains local

This is the intended regime of the method and is scientifically consistent with the overlap and
support-union framework already established in the manuscript.

---

## Main Executed Findings

## 1. Support size stayed essentially bounded while ambient size grew

For the medium query task `T3_medium`, the median support-union size remained approximately `10`
across all sizes:

| `n` | median support size for `T3_medium` |
| --- | ---: |
| `30` | `10` |
| `60` | `10` |
| `80` | `10` |
| `200` | `10` |

This is the key structural observation of the run.

It means the exact query object is governed by local causal support rather than by the ambient
network size.

## 2. Exact runtime remained in the sub-millisecond to millisecond regime

Median exact-method wall times:

| `n` | `T1_single` | `T2_small` | `T3_medium` |
| --- | ---: | ---: | ---: |
| `30` | `0.000060 s` | `0.000237 s` | `0.000447 s` |
| `60` | `0.000057 s` | `0.000199 s` | `0.000996 s` |
| `80` | `0.000103 s` | `0.000196 s` | `0.000548 s` |
| `200` | `0.000057 s` | `0.000212 s` | `0.001106 s` |

The times fluctuate mildly with overlap structure, but they remain tiny even when `n = 200`.

## 3. Peak memory remained very small

Median peak memory for `T3_medium`:

| `n` | median peak memory |
| --- | ---: |
| `30` | `14.398 KB` |
| `60` | `33.414 KB` |
| `80` | `18.156 KB` |
| `200` | `34.906 KB` |

This confirms that the exact method is operating on the query support rather than on the global
state space.

## 4. Naive exhaustive materialization explodes immediately

Raw lower bounds for full output materialization:

| `n` | rows `2^n` | raw output bits `n2^n` | raw lower-bound storage |
| --- | ---: | ---: | ---: |
| `30` | `1.074e+09` | `3.221e+10` | `3.750 GB` |
| `60` | `1.153e+18` | `6.918e+19` | `7.500 EB` |
| `80` | `1.209e+24` | `9.671e+25` | `10.000 YB` |
| `200` | `1.607e+60` | `3.214e+62` | `4.017e+61 B` |

At an idealized throughput of `10^9` rows per second, naive enumeration would still require:

| `n` | idealized naive time |
| --- | ---: |
| `30` | `1.074 s` |
| `60` | `36.534 y` |
| `80` | `3.831e+07 y` |
| `200` | `5.092e+43 y` |

These are lower-bound envelope figures, not empirical measurements.

---

## Current Conclusion

The executed results already support the core intended conclusion of the new section:

> exact causal evaluation remains feasible at very large ambient sizes because the computed object is
> support-local and compressed, whereas naive exhaustive materialization is dominated by the global
> `2^n` state explosion.

This conclusion is strong enough to motivate a new manuscript section, but the manuscript wording
should still remain disciplined:

- the method does not beat the cost of materializing the full exhaustive object
- it avoids that cost by computing a different exact object

---

## Artifacts

### Main raw outputs

- `papers/method/code/scalability_resource_envelope/scalability_summary.json`
- `papers/method/code/scalability_resource_envelope/exact_runs.json`
- `papers/method/code/scalability_resource_envelope/naive_envelope.json`
- `papers/method/code/scalability_resource_envelope/network_ensemble.json`

### Tabular outputs

- `papers/method/code/scalability_resource_envelope/exact_runs.csv`
- `papers/method/code/scalability_resource_envelope/exact_aggregated.csv`
- `papers/method/code/scalability_resource_envelope/naive_envelope.csv`

### Manuscript-facing rows

- `papers/method/code/scalability_resource_envelope/exact_method_rows.tex`
- `papers/method/code/scalability_resource_envelope/naive_envelope_rows.tex`
- `papers/method/code/scalability_resource_envelope/synthesis_rows.tex`

### Session log

- `papers/method/code/scalability_resource_envelope/session_excerpt.txt`

---

## Recommended Next Step

The next step should not be more ad hoc experimentation. It should be manuscript design.

The paper should now replace the broad complexity section with a new section structured around:

1. exact object versus exhaustive object
2. exhaustive materialization lower bound
3. support-local exact scalability
4. executed benchmark table
5. interpretation of the operational regime

