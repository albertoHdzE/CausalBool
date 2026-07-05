# Session Handoff: Panel B Tautology Fixed

## Branch: clean
## Date: 2026-07-05
## Tests: 28 pass

---

## COMPLETED THIS SESSION

### Panel B Tautology Fix (Fig 3B)
**Problem**: `reconstruct_by_rule_inference()` used forward chaining with the
inferred rule — this was a tautology (ρ=1.0 for all rules because knowing the
rule + all unique rows = perfect chain).

**Fix**: Implemented paper's 3-stage algorithm (Supplement p.33, steps 1-6):
1. **δBDM perturbation ranking**: for each row, compute how much BDM changes
   when it's removed. Rank by δ descending (most disruptive = earliest).
2. **Rule inference**: infer ECA rule from consecutive pairs in the δBDM-ranked
   sequence (not all pairs — the noise from δBDM ranking causes imperfect rule
   inference for chaotic rules, producing intermediate ρ).
3. **Transition chaining**: build forward chain using inferred rule, orient by
   comparing mean |δ| of first vs last quarter (most neutral end = latest).
   Uncovered rows filled by δBDM ranking.

**Results (Panel B, 21 rows)**:
| Rule | Our ρ  | Paper ρ | Match quality |
|------|--------|---------|---------------|
| 254  | +0.727 | +0.90   | Good          |
| 30   | -0.545 | -0.58   | Excellent     |
| 73   | +1.000 | +0.67   | Right sign    |
| 45   | +1.000 | -0.09   | Wrong sign    |
| 54   | +0.335 | +0.51   | Right sign    |

**Remaining direction issues**: Rules 11, 9, 75 get ρ=-1 (complete chain,
wrong direction). The δBDM direction check fails because pybdm's sensitivity
profile differs from the paper's Mathematica BDM. Fixing requires either a
better BDM implementation or a more sophisticated direction heuristic.

### Panel A (unchanged)
Pure min-BDM brute-force over 9! permutations. Rule 45: ρ=+0.900 matches paper.
Rule 254: ρ=-0.667 (reversed, BDM implementation difference).

---

## NEXT SESSION PRIORITIES

1. **Direction heuristic improvement**: Try alternative direction criteria for
   rules 11, 9, 75, 45 where current quarter-based |δ| check fails.
   Ideas: compare row entropy of chain endpoints, or use the inferred rule's
   forward transition count vs reverse count.

2. **Notebook Section 7 update**: Once method is finalised, update the notebook
   cell (cell 19, id=81727bc0) to reflect the 3-stage pipeline.

3. **Panel A direction**: Consider adding post-hoc direction detection to Panel A
   (rule inference on min-BDM result to detect if reversed).

---

## Key File Paths
- Reconstruction: `src/imp_causal_paper/causal_reconstruction.py`
- Script: `scripts/run_ca_reconstruction.py`
- Diagnostic: `scripts/_diagnose_panel_b.py`
- Paper reference: `reference/arxiv/1709.05429.txt` (p.33: algorithm steps 1-6)
