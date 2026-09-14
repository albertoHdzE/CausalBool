from __future__ import annotations

import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable

import networkx as nx
import numpy as np
import pandas as pd

BooleanRule = Callable[[np.ndarray], int]


@lru_cache(maxsize=1)
def _root_forward_model():
    """Import the root project's index-set forward model.

    AUDIT04-D (root repository). This module used to carry its own gate
    semantics. Measured elementwise against the owner before anything moved:
    the transition map agreed on 72 of 72 rows, and the gate dispatch on 92 of
    93 (gate, input) cases. The single disagreement was the EMPTY input set,
    where this module returned 0 and the owner returns 1 -- the empty
    conjunction is vacuously true.

    Zero disagreement is drift, not a second concept, so the copy is collapsed
    onto the owner rather than declared. The one disagreement was a defect, not
    a deliberate divergence: ``if values.size else 0`` returned 0 for EVERY
    empty fold, and happened to be right for ``or`` and ``xor`` only because
    their identity element is also 0. It would have been wrong for NAND and NOR
    (identity 1) the moment either was added.

    The case is live rather than theoretical. Of the 855 perturbed networks the
    experiment scripts build by removing edges, 80 (9.4 per cent) contain a node
    left with no inputs, and ``and`` is in the operator sweep.
    """
    src = Path(__file__).resolve().parents[3] / 'index-deconvolution' / 'src'
    if not src.is_dir():
        raise FileNotFoundError(f'expected the root index-set sources at {src}')
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import causalbool  # noqa: E402

    return causalbool


#: The root owner's family name for each operator this module exposes.
_GATE_NAMES = {"and": "AND", "or": "OR", "xor": "XOR"}


def boolean_operator(name: str) -> BooleanRule:
    """Return the gate as a callable, dispatched by the ROOT owner.

    The three families keep their lowercase names here because the scripts and
    figures are keyed on them; only the semantics are delegated.
    """
    if name not in _GATE_NAMES:
        raise ValueError("name must be one of: and, or, xor")
    gate = _GATE_NAMES[name]
    causalbool = _root_forward_model()
    return lambda values: int(
        causalbool.apply_gate(gate, [int(v) for v in np.asarray(values).ravel()], {})
    )


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
