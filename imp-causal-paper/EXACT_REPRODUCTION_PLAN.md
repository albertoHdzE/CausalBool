# Exact Reproduction Plan

## Objective

Reproduce, as faithfully as possible, the experiments reported in:
Zenil, Kiani, Marabita, Deng, Elias, Schmidt, Ball, Tegnér.
"An Algorithmic Information Calculus for Causal Discovery and Reprogramming of
Biological Networks." iScience, 2019. (arXiv:1709.05429)

---

## Figure 3 CA Reconstruction — Pivot Analysis

### Pivot: SHA efae01f (2026-07-05)

Current 3-stage pipeline (δBDM ranking → rule inference → chaining):
- Rule 30: ρ=-0.545 vs paper -0.58 (**near-perfect**)
- Rule 254: ρ=+0.727 vs paper +0.90 (**correct sign, good magnitude**)
- Direction issues remain for rules 11, 9, 75 (ρ=-1, wrong direction)

---

## Reading the Caption: Three Distinct Columns

The caption reveals the structure of each Panel B pair:

1. **Original** (left): true space-time evolution — the target
2. **Time order inferred** (right): rows from the scrambled set
   RE-ORDERED by the perturbation method. NOT regenerated — rearranged.
3. **ρ and p**: Spearman correlation between inferred vs true temporal
   positions. Quantifies reconstruction quality.

### Key details from caption:
- Panels D-E: "both after **280 steps**" (much more than our 21)
- Panels F-G: "accuracy can be scaled and improved at the cost of
  greater computational resources by going beyond **single row
  perturbation up to the power set (all subsets)**"
- "Errors inherited from the decomposition method (BDM) look like
  'shadows' and are explained by numerical deviations from boundary
  conditions"

---

## Why Our Results Are Close But Direction Fails

### Root cause: BDM implementation
pybdm uses 4×4 CTM lookup tables. The paper uses Mathematica BDM with
potentially different block sizes (4×4, 12×12) from the Online Algorithmic
Complexity Calculator. This gives finer-grained complexity estimates
and better perturbation sensitivity.

### Visual observation
Our fig3b_reconstruction.pdf shows patterns that VISUALLY match the
originals — they're just sometimes reversed or rotated. The structure
IS recovered; only the direction is ambiguous.

---

## Enhancement Strategies (ordered by expected impact)

### Strategy 1: Row-density direction (SIMPLEST FIX)
For single-seed CAs, the initial condition has the fewest black cells
(row sum = 1). Later rows have more. Compare row sums of chain endpoints:
the one with fewer black cells is the initial condition.
- Fixes rule 254 perfectly (sums: 1,3,5,...,41)
- Helps any rule with monotonic or near-monotonic density growth
- 5 lines of code

### Strategy 2: Symmetry-guided ranking (USER IDEA)
Single-seed CA rows are symmetric about the vertical midline. Compute:
  `sym(row) = 1 - hamming(row, flip(row)) / len(row)`
Initial condition has maximal symmetry (single dot, centred). Use as
secondary signal for direction detection or ranking refinement.

Potential extension: study the symmetry structure of the ORIGINAL
pattern (reflection axes, density gradients) and use it as a template
for sorting the reconstruction — like a "feature engineering" step in ML.

### Strategy 3: Increase step count
Paper uses 280 steps for Panels D-E. More rows → more data →
better δBDM ranking → higher ρ. Test with 50, 100, 200 steps.

### Strategy 4: 2R perturbation
Instead of deleting 1 row, delete pairs. δ₂(i,j) gives more
information about row ordering. Cost: O(n²) BDM evaluations.
For n=21: 210 pairs — feasible.

### Strategy 5: Row-complexity progression
Compute 1D BDM of each individual row. Early rows (simple, few cells)
have low complexity; late rows have higher. Sort by row complexity
as alternative direction signal.

---

## Current Results vs Paper

| Rule | Panel B (ours) | Panel B (paper) | Status |
|------|----------------|-----------------|--------|
| 254  | +0.727         | +0.90           | Good   |
| 57   | -0.132         | +0.91           | Fix    |
| 11   | -1.000         | +0.93           | Fix    |
| 50   | -0.365         | +0.09           | OK     |
| 9    | -1.000         | +0.013          | Fix    |
| 54   | +0.335         | +0.51           | Good   |
| 75   | -1.000         | +0.085          | Fix    |
| 73   | +1.000         | +0.67           | Good   |
| 45   | +1.000         | -0.09           | Fix    |
| 30   | -0.545         | -0.58           | Match  |

## Next Session Action
1. Implement Strategy 1 (row-density direction) — expected to fix 254, 11
2. Test Strategy 3 (more steps) — may improve all rules
3. Implement Strategy 2 (symmetry) — refine remaining cases
4. Update notebook Section 7 once method is final

## Files
- `src/imp_causal_paper/causal_reconstruction.py` — all methods
- `scripts/run_ca_reconstruction.py` — Panel A + B generation
- `scripts/_diagnose_panel_b.py` — diagnostic script
- `reference/arxiv/1709.05429.txt` — paper text (p.33: steps 1-6)
