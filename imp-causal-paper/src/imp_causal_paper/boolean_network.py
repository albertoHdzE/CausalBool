from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

import networkx as nx
import numpy as np
import pandas as pd

BooleanRule = Callable[[np.ndarray], int]


def boolean_operator(name: str) -> BooleanRule:
    if name == "and":
        return lambda values: int(np.all(values)) if values.size else 0
    if name == "or":
        return lambda values: int(np.any(values)) if values.size else 0
    if name == "xor":
        return lambda values: int(np.bitwise_xor.reduce(values)) if values.size else 0
    raise ValueError("name must be one of: and, or, xor")


@dataclass
class BooleanNetwork:
    graph: nx.DiGraph
    operator_name: str

    def __post_init__(self) -> None:
        self.operator = boolean_operator(self.operator_name)
        self.nodelist = list(sorted(self.graph.nodes()))
        self.predecessors = {node: list(sorted(self.graph.predecessors(node))) for node in self.nodelist}

    def next_state(self, state: tuple[int, ...]) -> tuple[int, ...]:
        state_map = {node: state[idx] for idx, node in enumerate(self.nodelist)}
        next_bits = []
        for node in self.nodelist:
            inputs = np.array([state_map[pred] for pred in self.predecessors[node]], dtype=int)
            next_bits.append(self.operator(inputs))
        return tuple(int(bit) for bit in next_bits)

    def transition_map(self) -> dict[tuple[int, ...], tuple[int, ...]]:
        transitions = {}
        width = len(self.nodelist)
        for index in range(2**width):
            bits = tuple((index >> shift) & 1 for shift in range(width - 1, -1, -1))
            transitions[bits] = self.next_state(bits)
        return transitions

    def attractors(self) -> list[list[tuple[int, ...]]]:
        transitions = self.transition_map()
        visited: set[tuple[int, ...]] = set()
        attractors: list[list[tuple[int, ...]]] = []
        for state in transitions:
            if state in visited:
                continue
            trail: list[tuple[int, ...]] = []
            seen_at: dict[tuple[int, ...], int] = {}
            current = state
            while current not in seen_at and current not in visited:
                seen_at[current] = len(trail)
                trail.append(current)
                current = transitions[current]
            visited.update(trail)
            if current in seen_at:
                attractors.append(trail[seen_at[current] :])
        return attractors


def analyze_boolean_perturbations(graph: nx.Graph, operator_name: str) -> pd.DataFrame:
    directed = graph.to_directed()
    base_network = BooleanNetwork(directed, operator_name)
    base_count = len(base_network.attractors())
    rows = []
    for edge in sorted(directed.edges()):
        perturbed = directed.copy()
        perturbed.remove_edge(*edge)
        attractor_count = len(BooleanNetwork(perturbed, operator_name).attractors())
        rows.append(
            {
                "edge": edge,
                "base_attractors": base_count,
                "perturbed_attractors": attractor_count,
                "delta_attractors": attractor_count - base_count,
            }
        )
    return pd.DataFrame(rows)
