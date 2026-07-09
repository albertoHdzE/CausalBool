"""causalbool.py

Self-contained Python implementation of the CausalBool forward method for
synchronous Boolean networks, matching the canonical Wolfram Language
reference ``papers/method/code/lib/CausalBoolCore.wl`` exactly.

Conventions (identical to CausalBoolCore.wl / Gates.m):

  * Input enumeration is LSB-first.  For decimal ``x`` in ``0 .. 2**n - 1`` the
    input vector ``v`` has ``v[i] = (x >> i) & 1`` for ``i in 0 .. n-1`` so that
    ``v[0]`` is the least significant bit.  This reproduces the Wolfram
    expression ``Reverse[IntegerDigits[x, 2, n]]``.

  * The connectivity matrix ``C`` is ``n x n`` with ``C[k][i] = 1`` iff node
    ``i`` feeds node ``k`` (row ``k`` lists the inputs of node ``k``).  This
    reproduces ``cm[[i, j]] = 1 iff j -> i``.

  * For each node ``k`` the connected input positions are taken in ascending
    order and the node gate is applied to that ordered sub-vector.  This
    reproduces ``input[[Sort[Flatten[Position[cm[[node]], 1]]]]]``.

Node and bit indices are 0-based throughout this module (Wolfram is 1-based;
the translation is a fixed offset and does not affect any output value).

All gate semantics are taken verbatim from ``src/Packages/Integration/Gates.m``.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

# ---------------------------------------------------------------------------
# Gate semantics (verbatim from Gates.m)
# ---------------------------------------------------------------------------

GATE_TYPES = (
    "AND", "OR", "XOR", "NAND", "NOR", "XNOR",
    "NOT", "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING",
)


def apply_gate(gate: str, inputs: list[int], params: dict | None = None) -> int:
    """Evaluate a Boolean gate on a list of 0/1 inputs, returning 0/1.

    Semantics are identical to ``Integration`Gates`ApplyGate``.  The optional
    ``noiseFlipProb`` parameter of the Wolfram version is intentionally omitted:
    the deconvolution programme is deterministic by design.
    """
    p = params or {}
    if gate == "TRUE":
        return 1
    if gate == "FALSE":
        return 0
    if gate == "AND":
        return 1 if inputs.count(0) == 0 else 0
    if gate == "OR":
        return 1 if inputs.count(1) > 0 else 0
    if gate == "XOR":
        return sum(inputs) % 2
    if gate == "NAND":
        return 1 if inputs.count(0) > 0 else 0
    if gate == "NOR":
        return 1 if inputs.count(1) == 0 else 0
    if gate == "XNOR":
        return 1 - (sum(inputs) % 2)
    if gate == "NOT":
        return 1 - inputs[0]
    if gate == "IMPLIES":
        # myImplies: OR[{1 - a, b}]  (a -> b)
        return 1 if (inputs[0] == 0 or inputs[1] == 1) else 0
    if gate == "NIMPLIES":
        # myNImplies: AND[{a, 1 - b}]
        return 1 if (inputs[0] == 1 and inputs[1] == 0) else 0
    if gate == "MAJORITY":
        # Count[1] > Count[0]  (ties resolve to 0)
        return 1 if inputs.count(1) > inputs.count(0) else 0
    if gate == "KOFN":
        k = p.get("k", 1)
        return 1 if inputs.count(1) >= k else 0
    if gate == "CANALISING":
        # myCanalising: if inputs[ci] == v then out else OR[inputs]
        ci = p.get("canalisingIndex", 0)
        v = p.get("canalisingValue", 1)
        out = p.get("canalisedOutput", 0)
        return out if inputs[ci] == v else (1 if inputs.count(1) > 0 else 0)
    raise ValueError(f"unknown gate: {gate!r}")


def truth_table(gate: str, arity: int, params: dict | None = None) -> list[int]:
    """Return the length ``2**arity`` output vector of ``gate`` over all inputs.

    Inputs are enumerated LSB-first, consistent with :func:`repertoire`.
    """
    out = []
    for x in range(2 ** arity):
        vec = [(x >> i) & 1 for i in range(arity)]
        out.append(apply_gate(gate, vec, params))
    return out


# ---------------------------------------------------------------------------
# Network definition and forward method
# ---------------------------------------------------------------------------

@dataclass
class Network:
    """A synchronous Boolean network.

    Attributes
    ----------
    n : int
        Number of nodes.
    C : list[list[int]]
        ``n x n`` connectivity matrix, ``C[k][i] = 1`` iff node ``i`` feeds
        node ``k``.
    gates : list[str]
        Length ``n`` list of gate-type strings.
    params : list[dict]
        Length ``n`` list of per-node parameter dictionaries.  Parameter node
        indices (``canalisingIndex``) are 0-based positions **within the
        ordered connected sub-vector** of that node.
    """

    n: int
    C: list[list[int]]
    gates: list[str]
    params: list[dict] = field(default_factory=list)

    def __post_init__(self) -> None:
        if not self.params:
            self.params = [dict() for _ in range(self.n)]
        assert len(self.C) == self.n
        assert all(len(row) == self.n for row in self.C)
        assert len(self.gates) == self.n
        assert len(self.params) == self.n

    def connected_inputs(self, k: int) -> list[int]:
        """Ascending list of node indices feeding node ``k``."""
        return [i for i in range(self.n) if self.C[k][i] == 1]


def input_vector(x: int, n: int) -> list[int]:
    """LSB-first input vector for decimal ``x`` over ``n`` bits."""
    return [(x >> i) & 1 for i in range(n)]


def node_output_column(net: Network, k: int) -> list[int]:
    """Output column of node ``k`` over all ``2**n`` inputs (LSB-first order).

    This is the object the deconvolution consumes.  For a node with empty
    connectivity the gate is applied to an empty sub-vector; only constant
    gates are well defined there, matching the Wolfram behaviour where an
    empty ``Part`` yields a constant.
    """
    ic = net.connected_inputs(k)
    col = []
    for x in range(2 ** net.n):
        v = input_vector(x, net.n)
        sub = [v[i] for i in ic]
        col.append(apply_gate(net.gates[k], sub, net.params[k]))
    return col


def repertoire(net: Network) -> list[list[int]]:
    """Full output repertoire: a ``2**n x n`` matrix.

    Row ``x`` is the synchronous next-state vector for input ``x``; column
    ``k`` is :func:`node_output_column` for node ``k``.  Identical to the
    ``RepertoireOutputs`` field of ``CreateRepertoiresDispatch``.
    """
    cols = [node_output_column(net, k) for k in range(net.n)]
    return [[cols[k][x] for k in range(net.n)] for x in range(2 ** net.n)]
