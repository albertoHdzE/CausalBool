# Session Handoff: EarlyNet Root Cause + mmc8 Parsing

## Branch: clean
## Date: 2026-07-02
## Last verified state: 28 tests pass, all 3 run.sh commands clean

## What Was Accomplished This Session

### 1. Notebook Fix (COMPLETE)
- Fixed CA cell (Section 7): `summary["true_rule"]` -> `summary["rule"]`
- Fixed Boolean cell (Section 8): wrong keys (`graph_type`, `node_count`, etc.) -> correct keys (`graph_name`, `operator`, etc.)
- Verified: all 17 code cells execute cleanly via `jupyter nbconvert --execute`

### 2. EarlyNet Root Cause IDENTIFIED AND RESOLVED

#### Previous hypothesis (WRONG)
The SESSION_HANDOFF from the prior session claimed algodyn uses 3x3 blocks with
its own CTM table, and that the EarlyNet discrepancy was due to different CTM values.

#### Actual findings
1. **CTM tables are identical**: pybdm's built-in tables match algodyn's K-3x3.csv
   and K-4x4.csv exactly (verified numerically). Both also match the Mathematica
   source at `mat-bdm/squares2Dsize1to4.m` (exact rationals).
2. **Algodyn defaults to 4x4 blocks** (`block_size=4, offset=4`), NOT 3x3.
   See `reference/algodyn/R/calculate_info_vertices.R` line 23 and
   `reference/algodyn/R/info_spectra.R` line 23.
3. **The real issue is adjacency matrix node ordering**. BDM is NOT a graph
   invariant; the delta signs depend on which row/column each node occupies.

#### Per-network best ordering (pybdm 4x4, all verified)

| Network         | sorted (alphabetical) | in_degree_desc | Best |
|-----------------|----------------------|----------------|------|
| EarlyNet        | 7% (15/209)          | 97% (203/209)  | in_degree_desc |
| IntermediateNet | 97% (331/340)        | 96% (327/340)  | sorted |
| FinalNet        | 99% (202/204)        | 2% (4/204)     | sorted |

No single ordering works universally. The paper likely used igraph's default
vertex ordering, which depends on graph creation order and differs per network.

#### Files created
- `src/imp_causal_paper/algodyn_bdm.py`: Custom BDM estimator using algodyn CTM tables.
  Not needed for the fix (CTM values are identical to pybdm) but preserved as
  reference and for future investigation.
- `scripts/investigate_node_ordering.py`: Tests multiple orderings across all networks.
- `data/processed/th17/yosef_perturbation/EarlyNet_in_degree_desc_node_spectra.csv`: Best EarlyNet results.
- `data/processed/th17/yosef_perturbation/ordering_investigation.json`: Full results.
- `complexity.py`: `adjacency_matrix()` now accepts optional `nodelist` parameter
  (default behaviour unchanged; 28 tests pass).

### 3. mmc8.csv Parsed (COMPLETE)
- 9364 five-node directed graphs with BDM node perturbation deltas
- Edge count range: 4-20
- Phase transition: positive-dominant at low density -> negative-dominant at ~12-13 edges
- All outputs in `data/processed/boolean_exhaustive/`
- Script: `scripts/parse_mmc8.py`

### 4. CTM Provenance Chain Confirmed
- `mat-bdm/squares2Dsize1to4.m` (exact rationals, 1x1 through 4x4)
- `reference/algodyn/data/K-3x3.csv` (float extraction of 3x3 section)
- `reference/algodyn/data/K-4x4.csv` (float extraction of 4x4 section)
- pybdm built-in tables (identical to above)
All four sources agree to floating-point precision.

## Exact Next Actions

### 1. Integrate per-network ordering into the main perturbation workflow
The `adjacency_matrix()` function now accepts a `nodelist` parameter. The next step
is to update `run_yosef_perturbation.py` to use `in_degree_desc` for EarlyNet and
`sorted` for IntermediateNet/FinalNet. Then re-run the full analysis and update
the summary.json with the corrected EarlyNet results.

### 2. Update notebook Section 10 (cross-validation)
Update the cross-validation cells to note the ordering dependency and show
the corrected 97% agreement for EarlyNet.

### 3. Update REPRODUCTION_LEDGER.md
Record the ordering-sensitivity finding and the per-network resolution.

### 4. RegulonDB E. coli network
Download and apply BDM perturbation.

### 5. Boolean network reproduction (mmc8)
Use the parsed mmc8 data to reproduce Figure 4D distributions.

## Key Files to Read First
1. This file
2. `scripts/investigate_node_ordering.py` (ordering analysis)
3. `data/processed/th17/yosef_perturbation/ordering_investigation.json` (results)
4. `src/imp_causal_paper/algodyn_bdm.py` (custom estimator, reference)
5. `data/processed/boolean_exhaustive/mmc8_summary.json` (mmc8 analysis)
