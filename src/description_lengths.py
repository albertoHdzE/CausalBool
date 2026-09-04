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
#
# AUDIT03. This module REIMPLEMENTED variant A -- _runs, _row_cost and the
# summation -- while GOVERNANCE/DESCRIPTION_LENGTHS.md declares the canonical
# implementation to be imp-causalNet-paper's
# causalbool_mirror.index_set_description_length. A wrapper that reimplements
# the thing it declares canonical is the same one-concept-many-homes defect the
# audit removed for variant B, and it is worse here because the doc named an
# owner and the code ignored it.
#
# It now delegates, exactly as variant C already did. Proven equal before the
# change rather than after: 300 random adjacency matrices at n = 1..9, zero
# disagreements.

def row_run_index_set_length(adjacency) -> float:
    """Variant A: rows as neighbour index sets + log2(n+1) header.

    Delegates to the declared canonical implementation. The dependency on
    imp-causalNet-paper is deliberate and is the documented exception recorded
    in DESCRIPTION_LENGTHS.md section 4, not an accident.
    """
    import sys as _sys
    from pathlib import Path as _Path
    _root = _Path(__file__).resolve().parents[1]
    _p = str(_root / "imp-causalNet-paper" / "src")
    if _p not in _sys.path:
        _sys.path.insert(0, _p)
    import numpy as _np
    from imp_causalnet_paper.causalbool_mirror import index_set_description_length
    return float(index_set_description_length(_np.asarray(adjacency)))


# --- Variant B: gate + index-set per-node (BioMetrics/pathinfo family) --------

def node_description_cost(n: int, degree: int, gate: str,
                          include_header: bool = False,
                          in_degree_field: bool = True) -> float:
    """Per-node cost. ``include_header=True`` adds the log2(n) graph header that
    imp-pathinfo's graph_description_length charges but BioMetrics' D does not
    (V5's cross-repo nonidentity).

    AUDIT03/R2b. ``in_degree_field`` charges log2(n+1) for the in-degree d, and
    defaults to True because WITHOUT IT THIS IS NOT A DESCRIPTION LENGTH. A
    decoder handed the code cannot know how many bits to read for the input set
    nor how to interpret them as an index into the d-subsets of {1..n}; the
    per-node code then has Kraft sum n+1 rather than 1, so it is not uniquely
    decodable and prices nothing. Measured, with both negative controls, in
    audit/AUDIT03_R3_description_length/verify_description_length.py.

    ``in_degree_field=False`` reproduces the pre-AUDIT03 value and exists for
    exactly one purpose: regenerating tables published under the old code, in
    particular imp-pathinfo-paper's, whose mirror is a documented exception in
    GOVERNANCE/DESCRIPTION_LENGTHS.md. It is a legacy switch, not a modelling
    choice, and the difference it makes is pinned by the T4.5 fixture so that
    the two cannot drift apart unnoticed.
    """
    cost = math.log2(len(GATE_LABELS))
    if include_header:
        cost += math.log2(max(1, n))
    if in_degree_field:
        cost += math.log2(n + 1)
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
                            include_header: bool = True,
                            in_degree_field: bool = True) -> float:
    """Variant B over {node -> (degree, gate)} maps."""
    n = len(degree_by_node)
    if n == 0:
        return 0.0
    total = math.log2(max(1, n)) if include_header else 0.0
    for v in range(n):
        total += node_description_cost(n, degree_by_node[v], gates_by_node[v],
                                       in_degree_field=in_degree_field)
    return total


# --- Variant E: schema normal form, the catalogue-free length -----------------

def schema_normal_form_length(truth_table, n: int) -> float:
    """Variant E: D_schema for ONE node, in bits.

    AUDIT03/R3 made this the primary mechanism-side measure and it belongs with
    the others rather than in an audit script, so that the papers have a
    supported producer for it. Variant B names a gate by its index in a
    catalogue of twelve; this one transmits no catalogue at all, writing the
    node's schemata out instead.

    Code: a self-delimiting count of schemata, then per schema the number of
    fixed coordinates, which coordinates those are, and their values.

    The merge is Quine-McCluskey via ``minimal_dnf`` in
    index-deconvolution/src/deconvolution.py -- imported, deliberately not
    reimplemented here, since a second copy of that routine is precisely the
    defect AUDIT03/R2 exists to remove.

    ``truth_table`` is the node's LOCAL table over its d connected inputs,
    indexed y = sum_i bit_i << i, and ``n`` is the ambient network size.
    """
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[1]
    p = str(root / "index-deconvolution" / "src")
    if p not in sys.path:
        sys.path.insert(0, p)
    from deconvolution import minimal_dnf

    clauses = minimal_dnf(list(truth_table))
    if not clauses:
        return float(_gamma_len(1))
    bits = float(_gamma_len(len(clauses) + 1))
    for c in clauses:
        k = len(c["activators"]) + len(c["inhibitors"])
        bits += math.log2(n + 1) + math.log2(max(1, math.comb(n, k))) + k
    return bits


def _gamma_len(x: int) -> int:
    """Elias gamma code length for x >= 1."""
    return 2 * (x.bit_length() - 1) + 1


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
