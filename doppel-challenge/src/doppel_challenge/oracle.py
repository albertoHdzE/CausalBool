"""Independent small-state oracle for the long-run observable.

The oracle intentionally uses a per-initial-state trajectory walk rather than
the production cache.  It is slow but transparent and is used to freeze exact
small-network validation cases.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from .adapters import Network, input_vector, step


def independent_repertoire(net: Network) -> dict[str, Any]:
    n_states = 1 << net.n
    masses: dict[int, Fraction] = {}
    cycles: set[tuple[int, ...]] = set()
    basin_by_cycle: dict[tuple[int, ...], int] = {}
    transition: list[int] = []

    def successor(x: int) -> int:
        bits = step(net, input_vector(x, net.n))
        return sum((bit & 1) << i for i, bit in enumerate(bits))

    for x in range(n_states):
        transition.append(successor(x))
    for start in range(n_states):
        order: list[int] = []
        position: dict[int, int] = {}
        x = start
        while x not in position:
            position[x] = len(order)
            order.append(x)
            x = transition[x]
        cycle = tuple(order[position[x]:])
        canonical = tuple(sorted(cycle))
        cycles.add(canonical)
        basin_by_cycle[canonical] = basin_by_cycle.get(canonical, 0) + 1
        for state in cycle:
            masses[state] = masses.get(state, Fraction()) + Fraction(1, len(cycle))

    denominator = n_states
    support = sorted(masses)
    # Each contribution is divided by n_states; Fraction keeps the result exact.
    probs = [masses[state] / denominator for state in support]
    common = 1
    for p in probs:
        common = common * p.denominator // _gcd(common, p.denominator)
    counts = [p.numerator * (common // p.denominator) for p in probs]
    ordered_cycles = sorted(cycles)
    phase_weights = [
        {"numerator": basin_by_cycle[cycle],
         "denominator": n_states * len(cycle)}
        for cycle in ordered_cycles
    ]
    return {
        "rows": n_states,
        "cols": net.n,
        "matrix_lsb_first": True,
        "support": support,
        "counts": counts,
        "probability_denominator": common,
        "probs": [float(p) for p in probs],
        "probability_fractions": [
            {"numerator": p.numerator, "denominator": p.denominator}
            for p in probs
        ],
        "transition_map": transition,
        "attractor_cycles": [list(c) for c in ordered_cycles],
        "basin_sizes": [basin_by_cycle[cycle] for cycle in ordered_cycles],
        "phase_weights": phase_weights,
        "observable": "basin_weighted_attractor_repertoire",
    }


def _gcd(a: int, b: int) -> int:
    while b:
        a, b = b, a % b
    return a


def exact_repertoire_equal(left: dict[str, Any], right: dict[str, Any]) -> bool:
    """Compare exact distribution and transition fields, ignoring float noise."""
    fields = ("support", "counts", "probability_denominator",
              "probability_fractions", "transition_map", "attractor_cycles",
              "basin_sizes", "phase_weights")
    return all(left.get(field) == right.get(field) for field in fields)
