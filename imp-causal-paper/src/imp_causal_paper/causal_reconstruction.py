from __future__ import annotations

from dataclasses import dataclass
from itertools import permutations

import numpy as np
import pandas as pd

from .complexity import BDMComplexityEstimator


def elementary_ca_next(row: np.ndarray, rule: int) -> np.ndarray:
    bits = np.array([(rule >> i) & 1 for i in range(8)], dtype=int)
    left = np.roll(row, 1)
    right = np.roll(row, -1)
    neighborhoods = (left << 2) | (row << 1) | right
    return bits[neighborhoods]


def evolve_elementary_ca(initial_row: np.ndarray, rule: int, steps: int) -> np.ndarray:
    rows = [np.asarray(initial_row, dtype=int)]
    for _ in range(steps - 1):
        rows.append(elementary_ca_next(rows[-1], rule))
    return np.vstack(rows)


@dataclass(slots=True)
class CAReconstructionResult:
    ordered_rows: np.ndarray
    permutation: tuple[int, ...]
    complexity: float
    inferred_rule: int
    transition_matches: int
    ranking: pd.DataFrame


@dataclass(slots=True)
class CAReconstructor:
    estimator: BDMComplexityEstimator

    def reconstruct(self, observations: np.ndarray) -> CAReconstructionResult:
        observations = np.asarray(observations, dtype=int)
        if observations.ndim != 2:
            raise ValueError("observations must be a binary 2D array.")
        indices = tuple(range(observations.shape[0]))
        if len(indices) > 8:
            raise ValueError("Brute-force CA reconstruction is intentionally restricted to <= 8 observations.")

        best_perm: tuple[int, ...] | None = None
        best_matrix: np.ndarray | None = None
        best_rule: int | None = None
        best_matches: int | None = None
        best_score: tuple[int, float, tuple[int, ...]] | None = None
        for perm in permutations(indices):
            candidate = observations[list(perm), :]
            inferred_rule, matches = infer_best_rule(candidate)
            complexity = self.estimator.matrix_complexity(candidate)
            score = (-matches, complexity, perm)
            if best_score is None or score < best_score:
                best_score = score
                best_perm = perm
                best_matrix = candidate
                best_rule = inferred_rule
                best_matches = matches

        assert (
            best_perm is not None
            and best_matrix is not None
            and best_score is not None
            and best_rule is not None
            and best_matches is not None
        )
        base = best_score[1]
        ranking_rows = []
        for index in range(best_matrix.shape[0]):
            reduced = np.delete(best_matrix, index, axis=0)
            delta = base - self.estimator.matrix_complexity(reduced)
            ranking_rows.append({"row_index": index, "delta": delta})
        ranking = pd.DataFrame(ranking_rows).sort_values(by=["delta", "row_index"]).reset_index(drop=True)
        return CAReconstructionResult(
            ordered_rows=best_matrix,
            permutation=best_perm,
            complexity=best_score[1],
            inferred_rule=best_rule,
            transition_matches=best_matches,
            ranking=ranking,
        )


def infer_best_rule(rows: np.ndarray) -> tuple[int, int]:
    best_rule = 0
    best_matches = -1
    for rule in range(256):
        matches = 0
        for index in range(rows.shape[0] - 1):
            if np.array_equal(elementary_ca_next(rows[index], rule), rows[index + 1]):
                matches += 1
        if matches > best_matches:
            best_rule = rule
            best_matches = matches
    return best_rule, best_matches
