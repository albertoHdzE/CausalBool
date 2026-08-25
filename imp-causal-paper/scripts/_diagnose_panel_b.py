#!/usr/bin/env python3
"""Diagnose why Panel B gives perfect rho=1.0 for all rules."""
import sys, os
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from imp_causal_paper.causal_reconstruction import (
    evolve_elementary_ca, infer_rule_from_unordered, elementary_ca_next,
    reconstruct_by_rule_inference,
)
from imp_causal_paper.complexity import BDMComplexityEstimator
from scipy import stats

RULES = [254, 57, 11, 50, 9, 54, 75, 73, 45, 30]
WIDTH, STEPS = 41, 21

print("=== DIAGNOSIS: Why is Panel B giving perfect rho? ===\n")

for rule in RULES:
    ic = np.zeros(WIDTH, dtype=int)
    ic[WIDTH // 2] = 1
    orig = evolve_elementary_ca(ic, rule=rule, steps=STEPS)
    n = orig.shape[0]

    # Check for duplicate rows
    unique_rows = set()
    dups = 0
    for i in range(n):
        key = tuple(orig[i])
        if key in unique_rows:
            dups += 1
        unique_rows.add(key)

    # Scramble
    rng = np.random.RandomState(42 + rule)
    perm = rng.permutation(n)
    scrambled = orig[perm]

    # Infer rule from unordered rows
    inferred, pair_count = infer_rule_from_unordered(scrambled)

    # Count forward transitions for inferred rule
    fwd_matches = 0
    for i in range(n):
        pred = elementary_ca_next(scrambled[i], inferred)
        for j in range(n):
            if i != j and np.array_equal(pred, scrambled[j]):
                fwd_matches += 1

    # Count forward transitions for TRUE rule
    true_fwd = 0
    for i in range(n):
        pred = elementary_ca_next(scrambled[i], rule)
        for j in range(n):
            if i != j and np.array_equal(pred, scrambled[j]):
                true_fwd += 1

    print(f"Rule {rule:3d}: inferred={inferred:3d} correct={str(rule==inferred):5s} "
          f"pair_count={pair_count:3d} fwd_inf={fwd_matches:2d} "
          f"fwd_true={true_fwd:2d} dup_rows={dups} n={n}")

print("\n=== KEY QUESTION: Is perfect chaining a tautology? ===")
print("If ALL rows are unique and the rule is deterministic,")
print("then knowing the rule + having all rows => perfect chain.")
print("This is mathematically guaranteed, NOT a bug.\n")

# Now test: what happens if we DON'T know the direction?
print("=== TEST: What if we don't know forward vs backward? ===\n")
for rule in RULES:
    ic = np.zeros(WIDTH, dtype=int)
    ic[WIDTH // 2] = 1
    orig = evolve_elementary_ca(ic, rule=rule, steps=STEPS)
    n = orig.shape[0]

    rng = np.random.RandomState(42 + rule)
    perm = rng.permutation(n)
    scrambled = orig[perm]

    # Our method: forward chaining (knows direction)
    result = reconstruct_by_rule_inference(scrambled)

    # Compute rho properly
    true_pos = perm.copy()
    inf_pos = np.zeros(n, dtype=int)
    for rank, idx in enumerate(result.permutation):
        inf_pos[idx] = rank
    rho_fwd, _ = stats.spearmanr(true_pos, inf_pos)

    # What if we reversed the chain?
    rev_order = list(result.permutation)[::-1]
    inf_pos_rev = np.zeros(n, dtype=int)
    for rank, idx in enumerate(rev_order):
        inf_pos_rev[idx] = rank
    rho_rev, _ = stats.spearmanr(true_pos, inf_pos_rev)

    print(f"Rule {rule:3d}: rho_forward={rho_fwd:+.3f}  rho_reverse={rho_rev:+.3f}  "
          f"paper_B_approx={'varies'}")

print("\n=== CONCLUSION ===")
print("Forward chaining with correct rule is a TAUTOLOGY (rho=1).")
print("The paper's Panel B likely does NOT know the direction,")
print("or uses a different method (e.g., complexity-based ordering")
print("of rule-generated candidates, not pure chaining).")
print("\nThe paper's lower rho values (e.g., -0.58 for rule 30)")
print("suggest the method sometimes picks the wrong direction")
print("or the wrong rule, producing rho near -1 instead of +1.")
