# Experiment 1 — 6-Node Corroboration

**Paper reference**: Section "Worked Example" / Table 2 (exhaustive repertoire).

A 6-node synchronous Boolean network with gates `{OR, NOT, OR, IMPLIES, AND, XOR}`.

## Scripts

### `corroboration_6node.wl`

Derives closed-form index sets for node 5 (AND) and node 6 (XOR) using the
deconvolution operator `givePlaces[baseLocations, sumandos]`, then verifies
exact equality with the exhaustive output baseline.

Outputs written:
- `exhaustive_rows.tex` — 64-row LaTeX table used in the paper
- `summary.json` — machine-readable verification record
- `inputs_outputs.csv` — full 64-row input/output table with highlights
- `session_excerpt_and.txt`, `session_excerpt_xor.txt` — session logs

**Verification**: `verified061Q = True`, `verified062Q = True`

### `ordering_invariance_6node.wl` / `ordering_invariance_6node.py`

Verifies Theorem 2 (ordering invariance) by transporting the LSB-first one-sets
through the bit-reversal involution φ and checking exact agreement with the
independently computed MSB-first baseline.

Outputs written:
- `ordering_invariance_summary_rows.tex`
- `ordering_invariance_summary.json`
- `ordering_invariance_session.txt`

**Verification**: `verifiedAnd06Q = True`, `verifiedXor06Q = True`, `verifiedPhiInvolution06Q = True`

## Run

```bash
wolframscript -file corroboration_6node.wl
wolframscript -file ordering_invariance_6node.wl
python3 ordering_invariance_6node.py
```
