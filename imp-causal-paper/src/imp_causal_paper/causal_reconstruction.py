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


def reconstruct_min_complexity(
    observations: np.ndarray, estimator: BDMComplexityEstimator
) -> CAReconstructionResult:
    """Panel A method: brute-force search for the permutation with minimum BDM.

    Tries all n! row permutations and returns the one with lowest matrix
    complexity. Limited to ≤9 rows (9! = 362,880 permutations).
    """
    observations = np.asarray(observations, dtype=int)
    n = observations.shape[0]
    if n > 9:
        raise ValueError(
            f"Brute-force min-complexity reconstruction limited to ≤9 rows, got {n}."
        )

    best_perm: tuple[int, ...] | None = None
    best_matrix: np.ndarray | None = None
    best_c = float("inf")

    for perm in permutations(range(n)):
        candidate = observations[list(perm), :]
        c = estimator.matrix_complexity(candidate)
        if c < best_c:
            best_c = c
            best_perm = perm
            best_matrix = candidate

    assert best_perm is not None and best_matrix is not None
    inferred_rule, matches = infer_best_rule(best_matrix)

    ranking_rows = []
    for i in range(best_matrix.shape[0]):
        reduced = np.delete(best_matrix, i, axis=0)
        delta = best_c - estimator.matrix_complexity(reduced)
        ranking_rows.append({"row_index": i, "delta": delta})
    ranking = (
        pd.DataFrame(ranking_rows)
        .sort_values(by=["delta", "row_index"])
        .reset_index(drop=True)
    )

    return CAReconstructionResult(
        ordered_rows=best_matrix,
        permutation=best_perm,
        complexity=best_c,
        inferred_rule=inferred_rule,
        transition_matches=matches,
        ranking=ranking,
    )


def infer_rule_from_unordered(rows: np.ndarray) -> tuple[int, int]:
    """Infer best ECA rule by checking ALL pairs of rows (not just consecutive).

    For each candidate rule, count how many ordered pairs (i, j) satisfy
    elementary_ca_next(rows[i], rule) == rows[j].
    """
    n = rows.shape[0]
    best_rule = 0
    best_count = -1
    for rule in range(256):
        count = 0
        for i in range(n):
            predicted = elementary_ca_next(rows[i], rule)
            for j in range(n):
                if i != j and np.array_equal(predicted, rows[j]):
                    count += 1
        if count > best_count:
            best_count = count
            best_rule = rule
    return best_rule, best_count


def reconstruct_by_rule_inference(
    observations: np.ndarray, estimator: BDMComplexityEstimator | None = None
) -> CAReconstructionResult:
    """Panel B method: infer the generating rule, then chain rows.

    1. Try all 256 ECA rules; for each, count how many row→row transitions
       in the scrambled set match the rule (checking all pairs).
    2. Pick the best rule.
    3. Build a transition graph: edge from row i to row j if rule(row_i) = row_j.
    4. Find the longest chain (the temporal sequence).
    5. Remaining rows appended by BDM delta ranking.

    Scales to any number of rows (linear in n per rule).
    """
    observations = np.asarray(observations, dtype=int)
    n = observations.shape[0]

    # Step 1-2: Infer the generating rule
    best_rule, _ = infer_rule_from_unordered(observations)

    # Step 3: Build forward transition graph
    # successor[i] = j means rule(row_i) = row_j
    successor: dict[int, int] = {}
    has_predecessor: set[int] = set()

    for i in range(n):
        predicted = elementary_ca_next(observations[i], best_rule)
        for j in range(n):
            if i != j and np.array_equal(predicted, observations[j]):
                successor[i] = j
                has_predecessor.add(j)
                break

    # Step 4: Find the longest chain starting from a root (no predecessor)
    roots = [i for i in range(n) if i not in has_predecessor]
    if not roots:
        roots = list(range(n))  # cycle — start anywhere

    best_chain: list[int] = []
    for root in roots:
        chain = [root]
        visited = {root}
        current = root
        while current in successor and successor[current] not in visited:
            current = successor[current]
            chain.append(current)
            visited.add(current)
        if len(chain) > len(best_chain):
            best_chain = chain

    # Step 5: Append uncovered rows
    covered = set(best_chain)
    remaining = [i for i in range(n) if i not in covered]

    if remaining and estimator is not None:
        # Order remaining rows by BDM delta (descending)
        base_c = estimator.matrix_complexity(observations)
        deltas = []
        for i in remaining:
            reduced = np.delete(observations, i, axis=0)
            d = base_c - estimator.matrix_complexity(reduced)
            deltas.append((d, i))
        deltas.sort(reverse=True)
        remaining = [i for _, i in deltas]

    order = best_chain + remaining
    reconstructed = observations[order]

    # Compute ranking
    complexity = 0.0
    if estimator is not None:
        complexity = estimator.matrix_complexity(reconstructed)
        ranking_rows = []
        for i in range(n):
            reduced = np.delete(reconstructed, i, axis=0)
            delta = complexity - estimator.matrix_complexity(reduced)
            ranking_rows.append({"row_index": i, "delta": delta})
        ranking = (
            pd.DataFrame(ranking_rows)
            .sort_values(by=["delta", "row_index"])
            .reset_index(drop=True)
        )
    else:
        ranking = pd.DataFrame(columns=["row_index", "delta"])

    matches = 0
    for i in range(len(order) - 1):
        if np.array_equal(
            elementary_ca_next(reconstructed[i], best_rule), reconstructed[i + 1]
        ):
            matches += 1

    return CAReconstructionResult(
        ordered_rows=reconstructed,
        permutation=tuple(order),
        complexity=complexity,
        inferred_rule=best_rule,
        transition_matches=matches,
        ranking=ranking,
    )
