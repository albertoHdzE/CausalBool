#!/usr/bin/env python3
"""AUDIT04-H2.3 — the response profile of the second declared inversion.

H2.1 measured the response profile of Variant A and BDM under node
relabelling for four families: chain, hub, checkerboard, and a random
graph. The H2.3 adjudication concerns the two declared inversions in
tests/analysis/test_complexity_measures_are_algorithmic.py:274-281:

    ("index_set", "checkerboard"):  ...
    ("index_set", "column_stripes"): ...

H2.1 covered the checkerboard. The column_stripes family is the
n = 16, 32-ones matrix whose every row is [1, 0, 1, 0, ...] — the
mechanism is the same alternating-row pathology the checkerboard
exhibits, so the H2.1 argument applies. This script measures the
column_stripes response profile under the same n, same number of
relabellings, same seed, so the second declared inversion can be
adjudicated by the same evidence chain.

Run:
    venv/bin/python audit/AUDIT04_H_measures/response_profile_column_stripes.py
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

N = 16
RELABELLINGS = 200
SEED = 20260908


def _column_stripes(n: int) -> np.ndarray:
    """Every row is [1, 0, 1, 0, ...], the second family whose Variant-A
    inversion is declared in DECLARED_INVERSIONS."""
    return np.tile(np.array([1, 0] * (n // 2), dtype=np.uint8), (n, 1))


def _relabel(matrix: np.ndarray, perm: np.ndarray) -> np.ndarray:
    return matrix[perm][:, perm]


def _variant_a(matrix: np.ndarray) -> float:
    return float(row_run_index_set_length(matrix))


def _bdm(matrix: np.ndarray, bdm: BDM) -> float:
    return float(bdm.bdm(matrix))


def main() -> int:
    print("AUDIT04-H2.3 — column_stripes response profile (H2.1 follow-up)")
    print(f"  n = {N}, relabellings = {RELABELLINGS}, seed = {SEED}")

    family = _column_stripes(N)
    bdm = BDM(ndim=2)
    rng = np.random.default_rng(SEED)

    a_canon = _variant_a(family)
    b_canon = _bdm(family, bdm)
    a_spread, b_spread = [], []
    for _ in range(RELABELLINGS):
        perm = rng.permutation(N)
        relabelled = _relabel(family, perm)
        a_spread.append(_variant_a(relabelled))
        b_spread.append(_bdm(relabelled, bdm))
    a_arr = np.asarray(a_spread, dtype=float)
    b_arr = np.asarray(b_spread, dtype=float)

    print(f"\n  family: column_stripes (n = {N}, 32 ones in the matrix)")
    print(f"  canonical Variant A: {a_canon:.4f} bits")
    print(f"  canonical BDM:       {b_canon:.4f} bits")
    print(f"  Variant A spread:    {a_arr.max() - a_arr.min():.4f} bits "
          f"(min {a_arr.min():.4f}, max {a_arr.max():.4f})")
    print(f"  BDM spread:          {b_arr.max() - b_arr.min():.4f} bits "
          f"(min {b_arr.min():.4f}, max {b_arr.max():.4f})")

    out = {
        "n": N,
        "relabellings": RELABELLINGS,
        "seed": SEED,
        "family": {
            "name": "column_stripes",
            "ones": int(family.sum()),
            "canonical_variant_a": a_canon,
            "canonical_bdm": b_canon,
            "variant_a_min": float(a_arr.min()),
            "variant_a_max": float(a_arr.max()),
            "variant_a_spread": float(a_arr.max() - a_arr.min()),
            "variant_a_median": float(np.median(a_arr)),
            "variant_a_sd": float(a_arr.std()),
            "bdm_min": float(b_arr.min()),
            "bdm_max": float(b_arr.max()),
            "bdm_spread": float(b_arr.max() - b_arr.min()),
            "bdm_median": float(np.median(b_arr)),
            "bdm_sd": float(b_arr.std()),
            "denominator_relabellings": RELABELLINGS,
        },
    }
    (HERE / "response_profile_column_stripes.json").write_text(
        json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'response_profile_column_stripes.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
