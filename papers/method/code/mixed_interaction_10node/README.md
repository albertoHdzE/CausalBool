# Experiment 2 — 10-Node Mixed Interaction

**Paper reference**: Section "Mixed-Gate Network" / Tables for full queries F1–F4 and
subsystem queries S1–S2.

A 10-node synchronous Boolean network with all 10 gate families:
`{AND, OR, XOR, KOFN(k=2), NOR, XNOR, NOT, IMPLIES, NIMPLIES, MAJORITY}`.

## Scripts

### `mixed_interaction_10node.wl`

Computes the analytic index set for every individual node, then evaluates six
mixed query patterns (F1–F4 full, S1–S2 subsystem) by intersecting per-node
one-sets. Verifies each against the exhaustive baseline built from
`CreateRepertoiresDispatch` (provided by `../lib/CausalBoolCore.wl`).

Key quantities reproduced:
- `d_q = 21`, `c_q = 10`, `μ_q = 11`, `R_q = 2048` (full 10-node query)
- `d_q = 10`, `c_q = 7`, `μ_q = 3`, `R_q = 8` (S1 subsystem)
- `d_q = 14`, `c_q = 10`, `μ_q = 4`, `R_q = 16` (S2 subsystem)

Outputs written:
- `full_case_rows.tex`, `subsystem_case_rows.tex`
- `full_case_summary_rows.tex`, `subsystem_case_summary_rows.tex`
- `summary.json`, `full_case_rows.csv`, `subsystem_case_rows.csv`
- `session_excerpt.txt`, `session_excerpt_full.txt`, `session_excerpt_subsystem.txt`

**Verification**: all 10 node one-sets exact; all 6 query patterns verified.

### `dynamical_landscape_10node.wl` / `dynamical_landscape_10node.py`

Enumerates the full state-transition graph (2^10 = 1024 states) and identifies
attractors, basin sizes, and the reachability/recurrence status of every query
output state.

Key quantities reproduced:
- `|Im(F)| = 206`
- 4 attractors with basin sizes 488, 320, 204, 12

Outputs written:
- `dynamical_cycle_rows.tex`, `dynamical_case_rows.tex`, `dynamical_sample_rows.tex`
- `dynamical_summary.json`
- `dynamical_session_excerpt.txt`

## Run

```bash
wolframscript -file mixed_interaction_10node.wl
wolframscript -file dynamical_landscape_10node.wl
python3 dynamical_landscape_10node.py
```
