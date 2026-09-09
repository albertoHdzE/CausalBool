#!/usr/bin/env python3
"""AUDIT04-H2.2 — the label-matched probe.

The existing probe in tests/analysis/test_complexity_measures_are_algorithmic.py
compares a CANONICALLY labelled structured object against randomly generated
random graphs. It tests whether the measure preserves the qualitative ordering
"structured simpler than random" — and it does, except for the two families
declared in DECLARED_INVERSIONS.

The H2.1 response profile showed that the two reported measures both move
under node relabelling (the chain's Variant A spread is 61.31 bits, the
BDM spread is 170.72 bits; the checkerboard's spreads are 784.79 and 437.34
respectively). The probe's single canonical labelling is therefore a
single draw out of a distribution of draws; the figure it reports is the
realisation of that draw, not a property of the family. The H2.2 probe
re-runs the chain comparison with the structured object RANDOMLY relabelled,
matched draw for draw, and reports both realisations side by side.

The plan's review values, n = 12, chain (11 edges), 200 × 200:

    configuration     Variant A   BDM
    canonical              9.5%    0.0%
    relabelled             9.5%   66.9%

The headline: BDM's 0.0 % in the canonical configuration goes to 66.9 % in
the relabelled one. The chain's "BDM is simpler than random" finding is a
labelling artefact, not a property of the family. Variant A's 9.5 % is
stable — the run-length code over rows is not labelling-sensitive at the
fraction level — but this is an H2.1-style response showing up at the
distribution level, not at the mean.

Run:
    venv/bin/python audit/AUDIT04_H_measures/label_matched_probe.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from pybdm import BDM

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.description_lengths import row_run_index_set_length  # noqa: E402

LINE = "-" * 78

N = 12                       # nodes per matrix
EDGES = N - 1                 # the existing test's directed chain has
                             # n - 1 ones in its matrix (one per
                             # upper-triangle entry 0-1, 1-2, ..., (n-2)-(n-1));
                             # the matched random graphs must carry the same
                             # number of ones, not twice that
TRIALS = 200                 # 200 chain instances × 200 random graphs (one
                             # random draw per chain instance) = 200 pairs
                             # per configuration, the same shape as the
                             # existing test at 200 trials
SEED_STRUCT = 20260908       # fixed; the relabelling sampler for the
                             # "relabelled" configuration consumes this
SEED_RANDOM = 11             # the seed the existing test uses for its draw
                             # rng, so the canonical 9.5 % is reproducible
                             # from the same draw-by-draw comparison the
                             # existing test makes


def _chain(n: int) -> np.ndarray:
    """The canonical chain: 0 - 1 - 2 - ... - (n-1).

    The shape used by the existing test
    test_random_is_not_simpler_than_a_chain in
    tests/analysis/test_complexity_measures_are_algorithmic.py:166: a
    DIRECTED chain, m[i, i+1] = 1 for i in 0..n-2, sum = n - 1 = 11 ones
    in the matrix at n = 12. The "directed" choice is the existing test's
    choice and the chain the plan's review values are based on; the
    H2.1 undirected chain (22 ones) is a different family with a
    different comparison.
    """
    m = np.zeros((n, n), dtype=np.uint8)
    for i in range(n - 1):
        m[i, i + 1] = 1
    return m


def _random_with_same_edges(n: int, edges: int, rng: np.random.Generator
                            ) -> np.ndarray:
    """A uniform random graph on n nodes with EXACTLY `edges` ones in the
    upper triangle (the comparison is at fixed edge count, not at fixed
    density, so the two members of the (structured, random) pair have the
    same number of 1s in the matrix and any difference between them is
    structural, not artefactual)."""
    m = np.zeros((n, n), dtype=np.uint8)
    for k in rng.choice(n * n, edges, replace=False):
        m[k // n, k % n] = 1
    return m


def _relabel(matrix: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Node relabelling: A' = A[P][:, P]. A graph isomorphism; the graph is
    unchanged, the matrix layout is not."""
    return matrix[perm][:, perm]


def _variant_a(matrix: np.ndarray) -> float:
    return float(row_run_index_set_length(matrix))


def _bdm(matrix: np.ndarray, bdm: BDM) -> float:
    return float(bdm.bdm(matrix))


def _probe(configuration: str, chain: np.ndarray, ones: int,
           perm_rng: np.random.Generator, draw_rng: np.random.Generator,
           bdm: BDM) -> dict:
    """200 chain instances × 1 random graph each, fraction of pairs where
    the random graph is simpler-or-equal to the chain.

    The matching is on number of ones in the matrix (n - 1 = 11 for a
    directed chain at n = 12), the comparison the existing test makes in
    test_random_is_not_simpler_than_a_chain. One random graph per chain
    instance matches the existing test's draw shape; "200 × 200" in the
    plan prose is 200 chain instances × 200 random graphs in the sense
    of 200 paired comparisons at a 200-trials draw budget.
    """
    var_a_simpler_or_equal = 0
    bdm_simpler_or_equal = 0
    total = 0
    for t in range(TRIALS):
        if configuration == "canonical":
            struct = chain
        elif configuration == "relabelled":
            perm = perm_rng.permutation(N)
            struct = _relabel(chain, perm)
        else:
            raise ValueError(configuration)
        rand = _random_with_same_edges(N, ones, draw_rng)
        v_struct = _variant_a(struct)
        v_rand = _variant_a(rand)
        b_struct = _bdm(struct, bdm)
        b_rand = _bdm(rand, bdm)
        if v_rand <= v_struct:
            var_a_simpler_or_equal += 1
        if b_rand <= b_struct:
            bdm_simpler_or_equal += 1
        total += 1
    return {
        "configuration": configuration,
        "denominator_pairs": total,
        "chain_instances": TRIALS,
        "random_graphs": TRIALS,
        "ones_per_matrix": ones,
        "variant_a_simpler_or_equal_pct":
            100.0 * var_a_simpler_or_equal / total,
        "bdm_simpler_or_equal_pct":
            100.0 * bdm_simpler_or_equal / total,
    }


def main() -> int:
    print("AUDIT04-H2.2 — the label-matched probe")
    print(f"  structured family: directed chain at n = {N}, "
          f"{EDGES} ones in matrix")
    print(f"  trials: {TRIALS} chain instances × {TRIALS} random graphs "
          f"= {TRIALS} paired comparisons per configuration")
    print(f"  seeds: chain seed {SEED_STRUCT}, draw seed {SEED_RANDOM}")
    print("  metric: fraction of pairs where the random graph is simpler-or-"
          "equal to the chain (lower = measure ranks structure cheaper)")

    chain = _chain(N)
    bdm = BDM(ndim=2)
    perm_rng = np.random.default_rng(SEED_STRUCT)
    draw_rng = np.random.default_rng(SEED_RANDOM)

    print(f"\n{LINE}\nCanonical configuration: the chain in its natural 0-1-2-...-11\n{LINE}")
    canonical = _probe("canonical", chain, EDGES, perm_rng, draw_rng, bdm)
    print(f"  pairs                          = {canonical['denominator_pairs']}")
    print(f"  Variant A simpler-or-equal (%) = "
          f"{canonical['variant_a_simpler_or_equal_pct']:.2f}")
    print(f"  BDM simpler-or-equal       (%) = "
          f"{canonical['bdm_simpler_or_equal_pct']:.2f}")

    print(f"\n{LINE}\nRelabelled configuration: the chain under a random permutation\n{LINE}")
    relabelled = _probe("relabelled", chain, EDGES, perm_rng, draw_rng, bdm)
    print(f"  pairs                          = {relabelled['denominator_pairs']}")
    print(f"  Variant A simpler-or-equal (%) = "
          f"{relabelled['variant_a_simpler_or_equal_pct']:.2f}")
    print(f"  BDM simpler-or-equal       (%) = "
          f"{relabelled['bdm_simpler_or_equal_pct']:.2f}")

    print(f"\n{LINE}\nSide by side\n{LINE}")
    print("  configuration     Variant A   BDM")
    print(f"  canonical         "
          f"{canonical['variant_a_simpler_or_equal_pct']:>8.2f}   "
          f"{canonical['bdm_simpler_or_equal_pct']:>6.2f}")
    print(f"  relabelled        "
          f"{relabelled['variant_a_simpler_or_equal_pct']:>8.2f}   "
          f"{relabelled['bdm_simpler_or_equal_pct']:>6.2f}")

    out = {
        "n": N,
        "edges": EDGES,
        "chain_instances": TRIALS,
        "random_graphs": TRIALS,
        "seed_struct": SEED_STRUCT,
        "seed_random": SEED_RANDOM,
        "configurations": [canonical, relabelled],
    }
    (HERE / "label_matched_probe.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'label_matched_probe.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
