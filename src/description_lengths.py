"""description_lengths -- AUDIT01/T4.5 single shared cost-model interface.

GOVERNANCE/DESCRIPTION_LENGTHS.md is the authority document; this module is the
one supported Python entry point. Consumers import from here or carry a
documented exception in that file (subproject venvs currently pin their own
mirrors; see the doc's consumer table).

Pinned third-party dependency: pybdm == 0.1.0 (root venv). The BDM edge
semantics differ per historical consumer: imp-pathinfo returns None below 4
atoms; other callers want a number or an exception. Select explicitly via
``bdm_2d(..., below_floor=...)`` -- never silently.
"""
from __future__ import annotations

import math

PYBDM_PIN = "0.1.0"

GATE_LABELS = ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "NOT",
               "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING")


def _check_pybdm() -> None:
    import pybdm
    version = getattr(pybdm, "__version__", "0.1.0")
    if version != PYBDM_PIN:
        raise RuntimeError(f"pybdm {version} != pinned {PYBDM_PIN}")


# --- Variant A: index-set row-run encoding (imp-causalNet-paper semantics) ----

def _runs(bits) -> int:
    runs, prev = 0, None
    for b in bits:
        if b != prev:
            runs += 1
        prev = b
    return runs


def _row_cost(bits, unit: float) -> float:
    r = _runs(bits)
    if r <= 1:
        return unit
    if r <= 3:
        return 2 * unit
    return r * unit


def row_run_index_set_length(adjacency) -> float:
    """Variant A: rows as neighbour index sets + log2(n+1) header."""
    M = list(map(list, adjacency))
    n = len(M)
    if n == 0:
        return 0.0
    unit = math.log2(n + 1)
    return math.log2(n + 1) + sum(_row_cost(row, unit) for row in M)


# --- Variant B: gate + index-set per-node (BioMetrics/pathinfo family) --------

def node_description_cost(n: int, degree: int, gate: str,
                          include_header: bool = False) -> float:
    """Per-node cost. ``include_header=True`` adds the log2(n) graph header that
    imp-pathinfo's graph_description_length charges but BioMetrics' D does not
    (V5's cross-repo nonidentity)."""
    cost = math.log2(len(GATE_LABELS))
    if include_header:
        cost += math.log2(max(1, n))
    cost += math.log2(max(1, math.comb(n, degree)))
    if gate == "KOFN":
        cost += math.log2(degree + 1) + 1
    elif gate == "CANALISING":
        cost += math.log2(max(1, n)) + 2
    elif gate in ("IMPLIES", "NIMPLIES"):
        cost += math.log2(max(1, degree * (degree - 1)))
    elif gate == "NOT":
        cost += math.log2(max(1, degree))
    else:
        cost += 1
    return cost


def graph_gate_index_length(degree_by_node, gates_by_node,
                            include_header: bool = True) -> float:
    """Variant B over {node -> (degree, gate)} maps."""
    n = len(degree_by_node)
    if n == 0:
        return 0.0
    total = math.log2(max(1, n)) if include_header else 0.0
    for v in range(n):
        total += node_description_cost(n, degree_by_node[v], gates_by_node[v])
    return total


# --- Variant C: mechanism DNF model cost (delegates to causalnet measure) -----

def model_dnf_bits(truth_table, n_inputs: int) -> float:
    """Variant C. Requires imp-causalNet-paper on sys.path (documented exception
    in DESCRIPTION_LENGTHS.md §consumers until its mirror is folded in)."""
    from imp_causalnet_paper.measure import model_description_length
    return float(model_description_length(list(truth_table), n_inputs).bits)


# --- BDM wrapper with explicit edge semantics ---------------------------------

def bdm_2d(array, below_floor: str = "none") -> float | None:
    """pybdm BDM of a 2-D binary array.

    below_floor:
      "none"       -> compute for any shape (caller checks size itself);
      "pathinfo"   -> return None when any dimension < 4 atoms (the historical
                      imp-pathinfo behaviour, preserved verbatim);
      "raise"      -> raise ValueError below the floor.
    """
    _check_pybdm()
    import numpy as np
    from pybdm import BDM
    a = np.asarray(array, dtype=int)
    if below_floor == "pathinfo" and (a.shape[0] < 4 or a.shape[1] < 4):
        return None
    if below_floor == "raise" and (a.shape[0] < 4 or a.shape[1] < 4):
        raise ValueError(f"BDM floor violated: shape {a.shape}")
    return float(BDM(ndim=2).bdm(a))
