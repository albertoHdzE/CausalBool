from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import networkx as nx
import numpy as np
import pandas as pd

from .complexity import BDMComplexityEstimator, adjacency_matrix, log2_system_size

ElementType = Literal["edges", "vertices"]


@dataclass(slots=True)
class GraphPerturbationAnalyzer:
    estimator: BDMComplexityEstimator

    def spectra(
        self,
        graph: nx.Graph | nx.DiGraph,
        what: ElementType = "edges",
        nodelist: list | None = None,
    ) -> pd.DataFrame:
        threshold = log2_system_size(graph)
        rows: list[dict[str, object]] = []
        if what == "edges":
            base_complexity = self.estimator.graph_complexity(graph)
            for edge in sorted(graph.edges()):
                perturbed = graph.copy()
                perturbed.remove_edge(*edge)
                perturbed_complexity = self.estimator.graph_complexity(perturbed)
                delta = base_complexity - perturbed_complexity
                rows.append(
                    {
                        "element_type": "edge",
                        "element": edge,
                        "source": edge[0],
                        "target": edge[1],
                        "base_complexity": base_complexity,
                        "perturbed_complexity": perturbed_complexity,
                        "delta": delta,
                        "classification": classify_delta(delta, threshold),
                    }
                )
        elif what == "vertices":
            if nodelist is not None:
                # Fixed-ordering approach: build the adjacency matrix once with the
                # requested node ordering, then remove rows/columns via np.delete.
                # This matches algodyn's per-node deletion semantics and is required
                # for EarlyNet where alphabetical ordering inverts sign agreement.
                mat = adjacency_matrix(graph, nodelist=nodelist)
                base_complexity = self.estimator.matrix_complexity(mat)
                for idx, node in enumerate(nodelist):
                    p = np.delete(np.delete(mat, idx, axis=0), idx, axis=1)
                    perturbed_complexity = self.estimator.matrix_complexity(p)
                    delta = base_complexity - perturbed_complexity
                    rows.append(
                        {
                            "element_type": "vertex",
                            "element": node,
                            "source": node,
                            "target": None,
                            "base_complexity": base_complexity,
                            "perturbed_complexity": perturbed_complexity,
                            "delta": delta,
                            "classification": classify_delta(delta, threshold),
                        }
                    )
            else:
                base_complexity = self.estimator.graph_complexity(graph)
                for node in sorted(graph.nodes()):
                    perturbed = graph.copy()
                    perturbed.remove_node(node)
                    perturbed_complexity = self.estimator.graph_complexity(perturbed)
                    delta = base_complexity - perturbed_complexity
                    rows.append(
                        {
                            "element_type": "vertex",
                            "element": node,
                            "source": node,
                            "target": None,
                            "base_complexity": base_complexity,
                            "perturbed_complexity": perturbed_complexity,
                            "delta": delta,
                            "classification": classify_delta(delta, threshold),
                        }
                    )
        else:
            raise ValueError("Parameter 'what' must be 'edges' or 'vertices'.")
        return pd.DataFrame(rows)

    def signature(self, graph: nx.Graph | nx.DiGraph, what: ElementType = "edges") -> pd.DataFrame:
        spectra = self.spectra(graph, what=what)
        return spectra.sort_values(by=["delta", "source", "target"], ascending=[False, True, True]).reset_index(
            drop=True
        )

    def inforank(self, graph: nx.Graph | nx.DiGraph, what: ElementType = "edges") -> pd.DataFrame:
        signature = self.signature(graph, what=what).copy()
        signature["inforank"] = signature["delta"].rank(method="min", ascending=False)
        return signature


def classify_delta(delta: float, threshold: float) -> str:
    if delta < -threshold:
        return "negative"
    if delta > threshold:
        return "positive"
    return "neutral"
