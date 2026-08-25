from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable

import networkx as nx
import numpy as np
from pybdm import BDM


class ComplexityError(ValueError):
    """Raised when an object cannot be evaluated with the binary BDM estimator."""


@dataclass
class BDMComplexityEstimator:
    """Thin wrapper around pybdm for the binary 1D/2D cases used in the paper."""

    def __post_init__(self) -> None:
        self._bdm_1d = BDM(ndim=1)
        self._bdm_2d = BDM(ndim=2)

    def sequence_complexity(self, sequence: Iterable[int]) -> float:
        array = np.asarray(list(sequence), dtype=int)
        if array.ndim != 1:
            raise ComplexityError("Expected a 1D binary sequence.")
        self._validate_binary(array)
        return float(self._bdm_1d.bdm(array))

    def matrix_complexity(self, matrix: np.ndarray) -> float:
        array = np.asarray(matrix, dtype=int)
        if array.ndim != 2:
            raise ComplexityError("Expected a 2D binary matrix.")
        self._validate_binary(array)
        return float(self._bdm_2d.bdm(array))

    def graph_complexity(self, graph: nx.Graph | nx.DiGraph) -> float:
        return self.matrix_complexity(adjacency_matrix(graph))

    @staticmethod
    def _validate_binary(array: np.ndarray) -> None:
        unique = np.unique(array)
        if not np.all(np.isin(unique, [0, 1])):
            raise ComplexityError(f"BDM wrapper only supports binary data, received symbols {unique!r}.")


def adjacency_matrix(
    graph: nx.Graph | nx.DiGraph,
    nodelist: list | None = None,
) -> np.ndarray:
    if graph.number_of_nodes() == 0:
        return np.zeros((1, 1), dtype=int)
    if nodelist is None:
        nodelist = list(sorted(graph.nodes()))
    matrix = nx.to_numpy_array(graph, nodelist=nodelist, dtype=int)
    return matrix.astype(int)


def log2_system_size(graph: nx.Graph | nx.DiGraph) -> float:
    return math.log2(max(graph.number_of_nodes(), 1))
