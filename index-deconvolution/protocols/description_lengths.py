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
      "none"       -> do not intercept; the caller checks size itself.
                      AUDIT03-C: this does NOT mean "always returns a number".
                      pybdm refuses a block smaller than its own 4x4 partition
                      and raises "Computed BDM is 0, dataset may have incorrect
                      dimensions". The previous wording, "compute for any
                      shape", was false and would have sent a caller who read it
                      into an unhandled exception. Pinned by
                      tests/analysis/test_description_lengths_values.py;
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


# --- 1-D CTM / BDM over binary strings ----------------------------------------
#
# Added for index-deconvolution notebook 15 (the shifted-zero probe of BDM).
# Same pin, same rule as bdm_2d: the partition is chosen by the caller, never
# silently. pybdm's default 1-D partition DROPS any remainder shorter than the
# block, so a 20-bit string under block 12 is scored on its first 12 bits only.
# That is refused here unless the caller asks for it.

_REMAINDER_POLICIES = ("raise", "drop", "recursive")


def _bits(bits):
    """Validate a binary object BEFORE any conversion and return an int array.

    Accepted: a ``str`` of '0'/'1', or a one-dimensional sequence/array whose
    elements are Python/NumPy integers or bools equal to 0 or 1. Refused with
    ValueError: floats (even 0.0/1.0 -- a historical ``dtype=int`` cast turned
    0.5 into 0 silently), other values, ragged or multidimensional data, empty
    input, and scalars. Strings are not stripped.
    """
    import numbers

    import numpy as np
    if isinstance(bits, str):
        if not bits:
            raise ValueError("expected a non-empty binary string, got ''")
        if set(bits) - {"0", "1"}:
            raise ValueError("binary string may contain only '0' and '1'")
        return np.frombuffer(bits.encode("ascii"), dtype=np.uint8).astype(int) - 48
    if isinstance(bits, (bytes, bytearray)) or np.isscalar(bits) or isinstance(
            bits, numbers.Number):
        raise ValueError(f"expected a 1-D binary sequence, got scalar {type(bits).__name__}")
    if isinstance(bits, np.ndarray):
        if bits.ndim != 1:
            raise ValueError(f"expected a 1-D binary sequence, got ndim={bits.ndim}")
        if bits.dtype.kind not in "biu":
            raise ValueError(f"binary data must be integer or bool, got dtype {bits.dtype}")
        items = bits.tolist()
    else:
        try:
            items = list(bits)
        except TypeError:
            raise ValueError(f"expected a 1-D binary sequence, got {type(bits).__name__}") from None
    if not items:
        raise ValueError("expected a non-empty 1-D binary sequence")
    for v in items:
        if isinstance(v, (bool, np.bool_)):
            continue
        if not isinstance(v, (numbers.Integral, np.integer)):
            raise ValueError(f"binary elements must be int or bool, got {type(v).__name__}"
                             " (ragged, nested or float data are refused)")
        if v not in (0, 1):
            raise ValueError(f"non-binary value {v!r}")
    return np.asarray([int(v) for v in items], dtype=int)


def _positive_int(name: str, value) -> int:
    import numbers
    if isinstance(value, bool) or not isinstance(value, numbers.Integral):
        raise ValueError(f"{name} must be an integer (bool excluded), got {value!r}")
    return int(value)


def ctm_1d(bits) -> float:
    """CTM (bits) of a binary string of length 1..12, looked up in pybdm's
    CTM-B2-D12 table (Soler-Toscano et al. 2014, D(5) machines)."""
    _check_pybdm()
    from pybdm import BDM
    a = _bits(bits)
    if a.size > 12:
        raise ValueError(f"CTM table covers lengths 1..12, got {a.size}")
    return float(BDM(ndim=1, shape=(a.size,)).bdm(a))


def bdm_1d_partition(bits, block: int = 12, shift: int | None = None,
                     remainder: str = "raise") -> dict:
    """Score AND describe the partition actually used, so coverage is never implicit.

    Returns ``{"score", "n", "block", "shift", "remainder", "covered_bits",
    "dropped_bits", "parts"}`` where ``parts`` lists ``(start, length)`` of every
    scored block, and the score is pybdm's on exactly those parts.

    block      block length, an int 1..12 (the CTM table's range);
    shift      None -> non-overlapping blocks; an int 1..block -> sliding blocks
               with that step (a step larger than the block would leave gaps);
    remainder  "raise"     -> the blocks must cover every bit: non-overlap needs
                              n % block == 0, sliding needs (n-block) % shift == 0;
               "drop"      -> pybdm's own behaviour; trailing bits not covered are
                              ignored and reported in ``dropped_bits``;
               "recursive" -> non-overlap only; pybdm PartitionRecursive with
                              min_length=1, so the remainder is scored as shorter
                              blocks and no final bit disappears.
    For "raise" and "drop" a string shorter than the block is refused rather
    than scored as zero blocks.
    """
    _check_pybdm()
    from pybdm import BDM
    from pybdm.partitions import PartitionCorrelated, PartitionRecursive
    a = _bits(bits)
    n = int(a.size)
    block = _positive_int("block", block)
    if not 1 <= block <= 12:
        raise ValueError(f"block must be 1..12, got {block}")
    if shift is not None:
        shift = _positive_int("shift", shift)
        if not 1 <= shift <= block:
            raise ValueError(f"shift must be 1..block={block} (no internal gaps), got {shift}")
    if remainder not in _REMAINDER_POLICIES:
        raise ValueError(f"remainder must be one of {_REMAINDER_POLICIES}, got {remainder!r}")
    if remainder == "recursive":
        if shift is not None:
            raise ValueError("remainder='recursive' is defined only for shift=None")
        bdm = BDM(ndim=1, shape=(block,), partition=PartitionRecursive, min_length=1)
        parts, pos = [], 0
        for part in bdm.partition.decompose(a):
            parts.append((pos, int(part.size)))
            pos += int(part.size)
        if pos != n or "".join(map(str, a.tolist())) != "".join(
                "".join(map(str, p.tolist())) for p in bdm.partition.decompose(a)):
            raise RuntimeError("recursive partition does not cover the input exactly")
        return {"score": float(bdm.bdm(a)), "n": n, "block": block, "shift": None,
                "remainder": remainder, "covered_bits": n, "dropped_bits": 0,
                "parts": parts}
    if n < block:
        raise ValueError(f"length {n} is shorter than block {block}; "
                         "use remainder='recursive' to score a shorter block")
    step = block if shift is None else shift
    if remainder == "raise":
        tail = n % block if shift is None else (n - block) % step
        if tail:
            raise ValueError(f"length {n} not tiled by block {block} step {step}")
    starts = list(range(0, n - block + 1, step))
    covered = starts[-1] + block
    if shift is None:
        bdm = BDM(ndim=1, shape=(block,))
    else:
        bdm = BDM(ndim=1, shape=(block,), partition=PartitionCorrelated, shift=shift)
    if sum(1 for _ in bdm.partition.decompose(a)) != len(starts):
        raise RuntimeError("pybdm partition disagrees with the declared block starts")
    return {"score": float(bdm.bdm(a)), "n": n, "block": block, "shift": shift,
            "remainder": remainder, "covered_bits": covered,
            "dropped_bits": n - covered, "parts": [(s, block) for s in starts]}


def bdm_1d(bits, block: int = 12, shift: int | None = None,
           remainder: str = "raise") -> float:
    """pybdm 1-D BDM: sum over DISTINCT blocks of CTM(block) + log2(multiplicity).

    Arguments and validation as in :func:`bdm_1d_partition`, which also reports
    the coverage; this returns the score alone. Historical non-overlapping
    "raise"/"drop" scores and sliding scores are unchanged.
    """
    return bdm_1d_partition(bits, block=block, shift=shift, remainder=remainder)["score"]


# --- Archive size: the measured length of a transmitted byte archive ----------
#
# Distinct from variants A-E and from BDM: it is not a model of the object but
# the size of an actual decodable archive (index-deconvolution/hierarchy, HID-v1).
# This module measures; it never imports the codec that produced the bytes.

def encoded_bit_length(payload: bytes) -> int:
    """Exactly ``8 * len(payload)`` for a ``bytes`` object; anything else is refused."""
    if type(payload) is not bytes:
        raise TypeError(f"encoded_bit_length needs bytes, got {type(payload).__name__}")
    return 8 * len(payload)
