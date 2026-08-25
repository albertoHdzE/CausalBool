# Superseded artefacts — read before using anything in this directory

Corrected 2026-08-14.

`Complexity.json` and `MixedFormulaVsZIP.tex` in this directory were produced by an
earlier revision of `tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m` and carry
two invalid figures. They are retained for provenance only and must not be cited.

| quantity | archived here | authoritative |
|---|---|---|
| `D_formula` | 101.07 bits | **135.66 bits** |
| `ZIP_bits`  | 1600 bits   | **10016 bits** |
| `Formula_over_ZIP` | 0.06317 | **0.01354** |
| `Formula_over_Shannon` | 0.00988 | **0.01326** |
| `C_formula` | 23 | 23 (unchanged) |
| `shannonOverall` / `shannonPerNode` | valid | unchanged |

**Why they are wrong.**

*ZIP:* `zipSizeBytes = 200` measured a Wolfram ZIP file that contained only a 64-byte
path-reference string, not the compressed output table. The ZIP code path has since been
removed from the test, so these values cannot be regenerated from the current suite.

*D_formula:* the encoding charged `log2(C(n,d))` for the input set without transmitting
`d`. A decoder cannot determine the width of that field, nor read it as an index into
the d-subsets of [n], so the code was not uniquely decodable and the figure was not a
description length. `encodeCostBits` now charges a `log2(n+1)` in-degree field.

**Authoritative source.** `papers/method/code/complexity_analysis/`:
`complexity_analysis.py` -> `complexity_results.json`, and `bdm_comparison.py` ->
`bdm_results.json`. Both are re-verified by
`papers/method/manuscript_computational/notebooks/replication_comp_paper.ipynb`.

Neither correction alters any scientific conclusion.
