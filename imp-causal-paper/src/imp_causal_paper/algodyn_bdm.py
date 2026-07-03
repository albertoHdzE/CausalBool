"""BDM complexity estimator using algodyn's exact CTM lookup tables.

Algodyn (the R package used in Zenil et al. iScience 2019) ships its own CTM
tables at reference/algodyn/data/K-{3x3,4x4}.csv.  These differ from pybdm's
built-in tables, which causes systematic sign inversions in the perturbation
deltas for EarlyNet.  This module re-implements the BDM computation using
algodyn's exact values and partitioning logic so that our perturbation results
can be compared directly against the paper's supplementary data.
"""
from __future__ import annotations

import csv
import math
from collections import Counter
from pathlib import Path

import networkx as nx
import numpy as np

from .complexity import adjacency_matrix

_DATA_DIR = Path(__file__).resolve().parents[2] / "reference" / "algodyn" / "data"


def _load_ctm(path: Path) -> dict[str, float]:
    """Load a CTM lookup table from algodyn CSV format (binary_string,value)."""
    ctm: dict[str, float] = {}
    with open(path) as f:
        for row in csv.reader(f):
            ctm[row[0]] = float(row[1])
    return ctm


def _partition_blocks(matrix: np.ndarray, block_size: int) -> list[str]:
    """Non-overlapping block partition with row-major stringification.

    Matches algodyn's ``my_partition`` + ``stringify``: non-overlapping blocks
    (offset == block_size), boundary rows/columns that do not form a complete
    block are dropped.  Stringification is row-major (same as algodyn's
    ``paste0(c(t(block)), collapse="")``, which flattens the transposed block
    in R's column-major order — equivalent to row-major of the original).
    """
    n_rows, n_cols = matrix.shape
    blocks: list[str] = []
    for i in range(0, n_rows - block_size + 1, block_size):
        for j in range(0, n_cols - block_size + 1, block_size):
            block = matrix[i:i + block_size, j:j + block_size]
            blocks.append("".join(str(int(x)) for row in block for x in row))
    return blocks


def bdm_from_ctm(
    matrix: np.ndarray,
    ctm: dict[str, float],
    block_size: int,
) -> float:
    """Compute BDM using a given CTM table and block size.

    BDM = sum_over_unique_blocks(CTM(block_i)) + sum_over_unique_blocks(log2(count_i))

    This matches algodyn's ``bdm2D`` function exactly.
    """
    blocks = _partition_blocks(matrix, block_size)
    tally = Counter(blocks)
    total = 0.0
    for block_str, count in tally.items():
        if block_str not in ctm:
            raise KeyError(
                f"Block '{block_str}' ({len(block_str)} bits) not in CTM table "
                f"({len(ctm)} entries, block_size={block_size})"
            )
        total += ctm[block_str] + math.log2(count)
    return total


class AlgodynBDMEstimator:
    """BDM estimator using algodyn's exact CTM tables.

    Provides the same interface as ``BDMComplexityEstimator`` (specifically
    ``graph_complexity`` and ``matrix_complexity``), so it can be used as a
    drop-in replacement with ``GraphPerturbationAnalyzer``.
    """

    def __init__(self, block_size: int = 3) -> None:
        self.block_size = block_size
        if block_size == 3:
            self._ctm = _load_ctm(_DATA_DIR / "K-3x3.csv")
        elif block_size == 4:
            self._ctm = _load_ctm(_DATA_DIR / "K-4x4.csv")
        else:
            raise ValueError(f"Unsupported block size: {block_size}")

    def matrix_complexity(self, matrix: np.ndarray) -> float:
        return bdm_from_ctm(matrix, self._ctm, self.block_size)

    def graph_complexity(self, graph: nx.Graph | nx.DiGraph) -> float:
        return self.matrix_complexity(adjacency_matrix(graph))
