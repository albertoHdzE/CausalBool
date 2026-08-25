from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import networkx as nx

from .complexity import BDMComplexityEstimator
from .perturbation import GraphPerturbationAnalyzer


@dataclass(slots=True)
class MILSResult:
    graph: nx.Graph | nx.DiGraph
    removed_edges: list[tuple[int, int]]


@dataclass(slots=True)
class MILSReducer:
    estimator: BDMComplexityEstimator

    def reduce(
        self,
        graph: nx.Graph | nx.DiGraph,
        target_edge_count: int,
        method: str = "greedy",
        max_exact_edges: int = 12,
    ) -> MILSResult:
        if target_edge_count < 0:
            raise ValueError("target_edge_count must be non-negative.")
        if target_edge_count >= graph.number_of_edges():
            return MILSResult(graph=graph.copy(), removed_edges=[])
        working = graph.copy()
        removed: list[tuple[int, int]] = []
        if method == "greedy":
            while working.number_of_edges() > target_edge_count:
                edge = self._least_informative_edge(working)
                working.remove_edge(*edge)
                removed.append(edge)
            return MILSResult(graph=working, removed_edges=removed)
        if method == "exact":
            if working.number_of_edges() > max_exact_edges:
                raise ValueError("Exact MILS is intentionally restricted to small graphs.")
            needed = working.number_of_edges() - target_edge_count
            best_subset = self._best_edge_subset(working, needed)
            working.remove_edges_from(best_subset)
            removed.extend(best_subset)
            return MILSResult(graph=working, removed_edges=removed)
        raise ValueError("method must be 'greedy' or 'exact'.")

    def _least_informative_edge(self, graph: nx.Graph | nx.DiGraph) -> tuple[int, int]:
        analyzer = GraphPerturbationAnalyzer(self.estimator)
        spectra = analyzer.spectra(graph, what="edges")
        spectra["abs_delta"] = spectra["delta"].abs()
        row = spectra.sort_values(by=["abs_delta", "source", "target"]).iloc[0]
        return int(row["source"]), int(row["target"])

    def _best_edge_subset(self, graph: nx.Graph | nx.DiGraph, subset_size: int) -> list[tuple[int, int]]:
        base = self.estimator.graph_complexity(graph)
        best_subset: list[tuple[int, int]] | None = None
        best_score: tuple[float, list[tuple[int, int]]] | None = None
        edges = list(sorted(graph.edges()))
        for subset in combinations(edges, subset_size):
            candidate = graph.copy()
            candidate.remove_edges_from(subset)
            delta = base - self.estimator.graph_complexity(candidate)
            key = (abs(delta), list(subset))
            if best_score is None or key < best_score:
                best_score = key
                best_subset = list(subset)
        assert best_subset is not None
        return best_subset
