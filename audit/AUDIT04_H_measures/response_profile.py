#!/usr/bin/env python3
"""AUDIT04-H2.1 — the response profile: how much do the two reported measures
vary under node relabelling, an isomorphism that changes no information?

GOVERNANCE/DESCRIPTION_LENGTHS.md names five variants; only two are reported:
Variant A (row-run index-set length) and BDM. Both operate on the adjacency
matrix as a 2-D pattern rather than on the abstract graph, so a permutation
of node labels permutes rows AND columns, and the cost the measure returns
moves. The size of that move is the response profile the plan asks for.

The plan values for cross-check, n = 16 and 200 relabellings:

    family            Variant A spread   BDM spread
    random, p = 0.2        98.10            92.46
    chain                   0.00           133.84
    hub                     0.00             1.44

This script is the producer. It is not a guard: it is the measurement
the H2.3 adjudication rests on.

Run:
    venv/bin/python audit/AUDIT04_H_measures/response_profile.py
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

import numpy as np
from pybdm import BDM

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from src.description_lengths import row_run_index_set_length  # noqa: E402

LINE = "-" * 78

N = 16                # nodes per matrix, as in the plan
RELABELLINGS = 200    # permutations applied to each matrix
SEED = 20260908       # fixed; same seed used for both the random matrix and the
                      # 200 relabellings, so the result is reproducible from
                      # the seed alone
P_RAND = 0.2          # random graph density, as in the plan
HUB_DEGREE = 5        # how many leaves the hub connects to; chosen so the
                      # canonical hub is dense enough to be visually obvious
                      # at n=16 (single hub of degree 5 means 5 spokes; 11
                      # nodes unconnected)


def _chain(n: int) -> np.ndarray:
    """0 -- 1 -- 2 -- ... -- (n-1), undirected."""
    m = np.zeros((n, n), dtype=np.uint8)
    for i in range(n - 1):
        m[i, i + 1] = m[i + 1, i] = 1
    return m


def _hub(n: int, hub_degree: int) -> np.ndarray:
    """One hub (node 0) connected to the first hub_degree non-hub nodes."""
    m = np.zeros((n, n), dtype=np.uint8)
    for j in range(1, 1 + hub_degree):
        m[0, j] = m[j, 0] = 1
    return m


def _checkerboard(n: int) -> np.ndarray:
    """A[i, j] = 1 iff i + j is even. The DECLARED_INVERSIONS family for
    Variant A: an alternating row costs n/2 runs, the code's maximum, and
    the family is in the existing test suite's FAMILIES map at
    tests/analysis/test_complexity_measures_are_algorithmic.py:265."""
    return np.fromfunction(lambda i, j: ((i + j) % 2 == 0).astype(np.uint8),
                           (n, n), dtype=np.uint8)


def _random_erdos_renyi(n: int, p: float, rng: np.random.Generator) -> np.ndarray:
    """Erdos-Renyi G(n, p), symmetrised, no self-loops."""
    m = (rng.random((n, n)) < p).astype(np.uint8)
    m = np.triu(m, k=1)
    m = m + m.T
    return m


def _relabel(matrix: np.ndarray, perm: np.ndarray) -> np.ndarray:
    """Permute node labels: A'[i, j] = A[perm[i], perm[j]].

    A node-relabelling isomorphism on the underlying graph; the graph is
    unchanged, the matrix layout is not.
    """
    return matrix[perm][:, perm]


def _variant_a(matrix: np.ndarray) -> float:
    return float(row_run_index_set_length(matrix))


def _bdm(matrix: np.ndarray, bdm: BDM) -> float:
    return float(bdm.bdm(matrix))


def _family_table(name: str, canonical: np.ndarray,
                  bdm: BDM, rng: np.random.Generator) -> dict:
    """200 random relabellings of one canonical matrix, both measures each.

    The seed is consumed for the 200 permutations, so two families with the
    same seed get the same 200 permutations in the same order. That is a
    feature: it lets the reader see the measures' responses to the SAME
    isomorphism set, not to two unrelated isomorphism sets.
    """
    a_spread, bdm_spread = [], []
    a_canonical = _variant_a(canonical)
    bdm_canonical = _bdm(canonical, bdm)
    for _ in range(RELABELLINGS):
        perm = rng.permutation(N)
        relabelled = _relabel(canonical, perm)
        a_spread.append(_variant_a(relabelled))
        bdm_spread.append(_bdm(relabelled, bdm))
    a_arr = np.asarray(a_spread, dtype=float)
    bdm_arr = np.asarray(bdm_spread, dtype=float)
    return {
        "name": name,
        "edges": int(canonical.sum() // 2),
        "canonical_variant_a": a_canonical,
        "canonical_bdm": bdm_canonical,
        "variant_a_min": float(a_arr.min()),
        "variant_a_max": float(a_arr.max()),
        "variant_a_spread": float(a_arr.max() - a_arr.min()),
        "variant_a_median": float(np.median(a_arr)),
        "variant_a_sd": float(a_arr.std()),
        "bdm_min": float(bdm_arr.min()),
        "bdm_max": float(bdm_arr.max()),
        "bdm_spread": float(bdm_arr.max() - bdm_arr.min()),
        "bdm_median": float(np.median(bdm_arr)),
        "bdm_sd": float(bdm_arr.std()),
        "denominator_relabellings": RELABELLINGS,
    }


def _part(t: str) -> None:
    print(f"\n{LINE}\n{t}\n{LINE}")


def main() -> int:
    print("AUDIT04-H2.1 — the response profile under node relabelling")
    print(f"  n = {N}, relabellings per family = {RELABELLINGS}, seed = {SEED}")
    print("  Both measures operate on the adjacency matrix as a 2-D pattern;")
    print("  the same graph, presented to the same measure under different")
    print("  orderings of its rows and columns, returns different numbers.")
    print("  The size of that move is the response profile this script")
    print("  publishes; the H2.3 adjudication of DECLARED_INVERSIONS rests on it.")

    rng_struct = np.random.default_rng(SEED)
    perm_rng = np.random.default_rng(SEED)  # see _family_table docstring

    chain = _chain(N)
    hub = _hub(N, HUB_DEGREE)
    checkerboard = _checkerboard(N)
    random_er = _random_erdos_renyi(N, P_RAND, rng_struct)

    bdm = BDM(ndim=2)

    _part("G1 — THE CANONICAL MATRICES")
    print(f"  chain at n={N}: {int(chain.sum() // 2)} edges, "
          f"structured pattern 0-1-2-...-15")
    print(f"  hub at n={N}, hub_degree={HUB_DEGREE}: "
          f"{int(hub.sum() // 2)} edges, node 0 is the hub")
    print(f"  checkerboard at n={N}: {int(checkerboard.sum() // 2)} ones, "
          f"A[i, j] = 1 iff i + j is even; the family whose Variant-A "
          f"inversion is declared in DECLARED_INVERSIONS")
    print(f"  random G({N}, p={P_RAND}): "
          f"{int(random_er.sum() // 2)} edges, symmetrised, no self-loops")

    _part("G2 — THE MEASURES")
    chain_canon = _variant_a(chain)
    chain_bdm = _bdm(chain, bdm)
    hub_canon = _variant_a(hub)
    hub_bdm = _bdm(hub, bdm)
    cb_canon = _variant_a(checkerboard)
    cb_bdm = _bdm(checkerboard, bdm)
    rand_canon = _variant_a(random_er)
    rand_bdm = _bdm(random_er, bdm)
    print("  Variant A (row-run index-set) and BDM, evaluated on each")
    print("  canonical matrix in the CANONICAL labelling:")
    print(f"    {'family':<14}{'edges':>8}{'Variant A (bits)':>20}{'BDM (bits)':>14}")
    print(f"    {'chain':<14}{int(chain.sum() // 2):>8}{chain_canon:>20.4f}"
          f"{chain_bdm:>14.4f}")
    print(f"    {'hub':<14}{int(hub.sum() // 2):>8}{hub_canon:>20.4f}"
          f"{hub_bdm:>14.4f}")
    print(f"    {'checkerboard':<14}{int(checkerboard.sum() // 2):>8}{cb_canon:>20.4f}"
          f"{cb_bdm:>14.4f}")
    print(f"    {'random p=0.2':<14}{int(random_er.sum() // 2):>8}{rand_canon:>20.4f}"
          f"{rand_bdm:>14.4f}")

    _part("G3 — THE RESPONSE PROFILE (the measurement H2.1 requires)")
    results = [
        _family_table("chain", chain, bdm, perm_rng),
        _family_table("hub", hub, bdm, perm_rng),
        _family_table("checkerboard", checkerboard, bdm, perm_rng),
        _family_table("random_p0.2", random_er, bdm, perm_rng),
    ]
    print(f"  {'family':<14}{'edges':>7}{'Var.A spread':>15}{'BDM spread':>13}"
          f"{'Var.A min':>12}{'Var.A max':>12}{'BDM min':>11}{'BDM max':>11}")
    for r in results:
        print(f"  {r['name']:<14}{r['edges']:>7}"
              f"{r['variant_a_spread']:>15.4f}{r['bdm_spread']:>13.4f}"
              f"{r['variant_a_min']:>12.4f}{r['variant_a_max']:>12.4f}"
              f"{r['bdm_min']:>11.4f}{r['bdm_max']:>11.4f}")
    print(f"\n  Denominator: {RELABELLINGS} random relabellings per family,")
    print(f"  same permutation set across families, seed {SEED}.")

    out = {
        "n": N,
        "relabellings": RELABELLINGS,
        "seed": SEED,
        "families": results,
    }
    (HERE / "response_profile.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'response_profile.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
