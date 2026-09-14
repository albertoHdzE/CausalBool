"""Connectivity perturbations under the parent CausalBool convention.

Three perturbation kinds are supported:

  EDGE_FLIP    -- every entry of A may be flipped (default)
  EDGE_ADD     -- only 0 -> 1 transitions are allowed
  EDGE_REMOVE  -- only 1 -> 0 transitions are allowed

The ball is enumerated in a deterministic, indexable order.  The index
of a perturbed matrix is the lexicographic rank of its perturbation
vector under the chosen kind.

For EDGE_FLIP at radius k, the ball contains C(N^2, k) matrices and is
enumerated by the combinations of perturbation positions.  The total
catalogue size is therefore at most sum_{i=0..k} C(N^2, i).
"""
from __future__ import annotations

from itertools import combinations
from typing import Literal

PerturbationKind = Literal["EDGE_FLIP", "EDGE_ADD", "EDGE_REMOVE"]


def _valid_kinds() -> set[str]:
    return {"EDGE_FLIP", "EDGE_ADD", "EDGE_REMOVE"}


def validate_matrix(A: list[list[int]]) -> None:
    """Validate a binary square matrix using ``A[target][source]``."""
    n = len(A)
    if any(len(row) != n for row in A):
        raise ValueError("adjacency matrix must be square")
    if any(value not in (0, 1, False, True) for row in A for value in row):
        raise ValueError("adjacency matrix entries must be binary")


def indegrees(A: list[list[int]]) -> list[int]:
    """Number of inputs to each target node (row sums).

    The parent engine's contract is ``A[target][source] == 1``.  Keeping this
    helper here prevents topology generators and admissibility checks from
    silently switching to the transpose convention.
    """
    validate_matrix(A)
    return [sum(row) for row in A]


def outdegrees(A: list[list[int]]) -> list[int]:
    """Number of outgoing edges from each source node (column sums)."""
    validate_matrix(A)
    n = len(A)
    return [sum(A[target][source] for target in range(n)) for source in range(n)]


def zero_indegree_nodes(A: list[list[int]]) -> list[int]:
    """Return the node indices with empty regulatory input."""
    return [i for i, d in enumerate(indegrees(A)) if d == 0]


def has_zero_indegree_nodes(A: list[list[int]]) -> bool:
    """Whether the network contains at least one empty-input node."""
    return bool(zero_indegree_nodes(A))


def is_admissible_perturbation(
    A: list[list[int]],
    *,
    forbid_zero_indegree_nodes: bool = True,
    max_indegree: int | None = None,
    allow_self_loops: bool = True,
    gates: list[str] | None = None,
) -> bool:
    """Return whether a perturbed network is admissible for experimentation.

    The current experimental rule excludes networks with empty-input nodes,
    because they leave the mechanistic class we want to compare against the
    base network.
    """
    validate_matrix(A)
    n = len(A)
    if not allow_self_loops and any(A[i][i] for i in range(n)):
        return False
    degrees = indegrees(A)
    if forbid_zero_indegree_nodes and any(d == 0 for d in degrees):
        return False
    if max_indegree is not None and any(d > max_indegree for d in degrees):
        return False
    if gates is not None:
        if len(gates) != n:
            return False
        if any(not gate_arity_allowed(gate, degree) for gate, degree in zip(gates, degrees)):
            return False
    return True


def gate_arity_allowed(gate: str, arity: int) -> bool:
    """Return whether a gate is admissible at a node with ``arity`` inputs.

    The challenge's default domain excludes empty inputs.  Constants remain
    available for explicit experiments, while unary/binary gates are not
    accidentally assigned incompatible arities.
    """
    if arity < 0:
        return False
    if gate in {"TRUE", "FALSE"}:
        return arity == 0
    if gate in {"NOT"}:
        return arity == 1
    if gate in {"IMPLIES", "NIMPLIES"}:
        return arity == 2
    if gate in {"LUT", "REGULATORY", "REGULATORY_DNF", "KOFN", "CANALISING"}:
        return arity >= 1
    return arity >= 1


def changed_edges(A0: list[list[int]], A: list[list[int]]) -> list[dict[str, int | str]]:
    """Return stable, semantic edge labels for all changed entries."""
    validate_matrix(A0)
    validate_matrix(A)
    if len(A0) != len(A):
        raise ValueError("matrices must have equal dimensions")
    out: list[dict[str, int | str]] = []
    for target, (r0, r1) in enumerate(zip(A0, A)):
        for source, (v0, v1) in enumerate(zip(r0, r1)):
            if v0 != v1:
                out.append({
                    "target": target,
                    "source": source,
                    "operation": "add" if v1 else "remove",
                })
    return out


def perturbation_id(A0: list[list[int]], A: list[list[int]], kind: str = "EDGE_FLIP") -> str:
    """Canonical content identifier, independent of enumeration or run order."""
    if kind not in _valid_kinds():
        raise ValueError(f"unknown perturbation kind: {kind!r}")
    edges = changed_edges(A0, A)
    if kind == "EDGE_ADD" and any(e["operation"] != "add" for e in edges):
        raise ValueError("matrix is not an edge-addition perturbation")
    if kind == "EDGE_REMOVE" and any(e["operation"] != "remove" for e in edges):
        raise ValueError("matrix is not an edge-removal perturbation")
    if not edges:
        return f"{kind}:identity"
    label = ";".join(f"{e['target']},{e['source']}:{e['operation']}" for e in edges)
    return f"{kind}:{label}"


def ball(A0: list[list[int]], k: int, kind: str = "EDGE_FLIP") -> list[list[list[int]]]:
    """Return the list of perturbed adjacency matrices in P_k(A_0)."""
    if kind not in _valid_kinds():
        raise ValueError(f"unknown perturbation kind: {kind!r}")
    if k < 0:
        raise ValueError("k must be non-negative")
    validate_matrix(A0)
    n = len(A0)
    flat: list[int] = [v for row in A0 for v in row]
    positions = list(range(n * n))

    out: list[list[list[int]]] = []
    if kind == "EDGE_FLIP":
        candidates = [p for p in positions if True]
    elif kind == "EDGE_ADD":
        candidates = [p for p in positions if flat[p] == 0]
    else:  # EDGE_REMOVE
        candidates = [p for p in positions if flat[p] == 1]

    # Always include the identity first, with perturbation_index = -1,
    # so callers can detect A_0.
    out.append([row[:] for row in A0])
    for r in range(1, k + 1):
        for combo in combinations(candidates, r):
            pert = [v for v in flat]
            for p in combo:
                if kind == "EDGE_FLIP":
                    pert[p] ^= 1
                elif kind == "EDGE_ADD":
                    pert[p] = 1
                else:
                    pert[p] = 0
            mat = [pert[i * n:(i + 1) * n] for i in range(n)]
            out.append(mat)
    return out


def admissible_ball(
    A0: list[list[int]],
    k: int,
    kind: str = "EDGE_FLIP",
    *,
    forbid_zero_indegree_nodes: bool = True,
    max_indegree: int | None = None,
    allow_self_loops: bool = True,
    gates: list[str] | None = None,
) -> list[list[list[int]]]:
    """Return the perturbation ball after experimental admissibility filtering."""
    return [
        A for A in ball(A0, k, kind)
        if is_admissible_perturbation(
            A,
            forbid_zero_indegree_nodes=forbid_zero_indegree_nodes,
            max_indegree=max_indegree,
            allow_self_loops=allow_self_loops,
            gates=gates,
        )
    ]


def index(A0: list[list[int]], A: list[list[int]], kind: str = "EDGE_FLIP") -> int:
    """Return the perturbation index of A relative to A_0, or -1 for A_0 itself."""
    if kind not in _valid_kinds():
        raise ValueError(f"unknown perturbation kind: {kind!r}")
    validate_matrix(A0)
    validate_matrix(A)
    n = len(A0)
    flat0 = [v for row in A0 for v in row]
    flat = [v for row in A for v in row]

    if flat0 == flat:
        return -1

    if kind == "EDGE_FLIP":
        diffs = tuple(i for i, (a, b) in enumerate(zip(flat0, flat)) if a != b)
    elif kind == "EDGE_ADD":
        if any(a != b and not (a == 0 and b == 1) for a, b in zip(flat0, flat)):
            raise ValueError("matrix contains a non-addition change")
        diffs = tuple(i for i, (a, b) in enumerate(zip(flat0, flat))
                      if a == 0 and b == 1)
    else:  # EDGE_REMOVE
        if any(a != b and not (a == 1 and b == 0) for a, b in zip(flat0, flat)):
            raise ValueError("matrix contains a non-removal change")
        diffs = tuple(i for i, (a, b) in enumerate(zip(flat0, flat))
                      if a == 1 and b == 0)
    # The order in which ``ball`` enumerates the perturbations is
    # the lexicographic order of combinations of the candidate
    # positions.  Compute the rank accordingly.
    if kind == "EDGE_FLIP":
        candidates = list(range(n * n))
    elif kind == "EDGE_ADD":
        candidates = [i for i, v in enumerate(flat0) if v == 0]
    else:
        candidates = [i for i, v in enumerate(flat0) if v == 1]
    r = len(diffs)
    if r == 0:
        return -1
    # A shell-local rank was previously used, causing collisions for k>1.
    # Offset each shell by all preceding combinations.  This rank is stable
    # for every radius k >= r and is unique within a perturbation kind.
    offset = 1
    for shell in range(1, r):
        offset += _n_choose_k(len(candidates), shell)
    target = tuple(sorted(diffs))
    for local_rank, combo in enumerate(combinations(candidates, r)):
        if combo == target:
            return offset + local_rank
    raise ValueError("matrix is not a valid perturbation of the requested kind")


def _n_choose_k(n: int, k: int) -> int:
    if k < 0 or k > n:
        return 0
    k = min(k, n - k)
    value = 1
    for i in range(1, k + 1):
        value = value * (n - k + i) // i
    return value


def graph_distance(A0: list[list[int]], A: list[list[int]]) -> int:
    """Edit distance on adjacency matrices (number of differing entries)."""
    validate_matrix(A0)
    validate_matrix(A)
    if len(A0) != len(A):
        raise ValueError("matrices must have equal dimensions")
    flat0 = [v for row in A0 for v in row]
    flat = [v for row in A for v in row]
    return sum(1 for a, b in zip(flat0, flat) if a != b)
