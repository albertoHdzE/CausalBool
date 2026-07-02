from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import networkx as nx

from .complexity import BDMComplexityEstimator


@dataclass(slots=True)
class MARPAResult:
    graph: nx.Graph | nx.DiGraph
    added_edges: list[tuple[int, int]]


@dataclass(slots=True)
class MARPABuilder:
    estimator: BDMComplexityEstimator

    def build(self, node_count: int, target_edge_count: int) -> MARPAResult:
        if node_count < 1:
            raise ValueError("node_count must be positive.")
        graph = nx.Graph()
        graph.add_nodes_from(range(node_count))
        added_edges: list[tuple[int, int]] = []
        while graph.number_of_edges() < target_edge_count:
            edge = self._best_next_edge(graph)
            graph.add_edge(*edge)
            added_edges.append(edge)
        return MARPAResult(graph=graph, added_edges=added_edges)

    def _best_next_edge(self, graph: nx.Graph) -> tuple[int, int]:
        base = self.estimator.graph_complexity(graph)
        best_edge: tuple[int, int] | None = None
        best_gain: tuple[float, tuple[int, int]] | None = None
        for edge in combinations(sorted(graph.nodes()), 2):
            if graph.has_edge(*edge):
                continue
            candidate = graph.copy()
            candidate.add_edge(*edge)
            gain = self.estimator.graph_complexity(candidate) - base
            score = (-gain, edge)
            if best_gain is None or score < best_gain:
                best_gain = score
                best_edge = edge
        if best_edge is None:
            raise ValueError("Target edge count exceeds the number of available undirected edges.")
        return best_edge
