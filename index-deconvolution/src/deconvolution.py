"""deconvolution.py

Index-set deconvolution for synchronous Boolean networks.

Given only the output repertoire of a network (a ``2**n x n`` binary matrix)
this module recovers, per node, the exact pair ``(I_c, f)`` where ``I_c`` is the
set of connected inputs and ``f`` is the Boolean function on those inputs, and
then names ``f`` with the canonical CausalBool gate family.

Method (see ``bitacora/01_deconvolution_method_design.md`` for the full
derivation).  The forward CausalBool transform factorises over nodes: output
column ``k`` is a function of the connected inputs only, with the disconnected
nodes acting purely as the free offset dimension ("sumandos").  Therefore
deconvolution factorises into independent per-column problems, each solved
exactly by:

  1. Essential-variable detection by single-bit perturbation.  Bit ``i`` is a
     connected input of node ``k`` iff flipping bit ``i`` of some input changes
     column ``k``.  Perturbing a disconnected node never changes the output;
     perturbing a connected node can.  This is the exact, deterministic analogue
     of the perturbation step in Zenil's algorithmic-information deconvolution.

  2. Gate identification.  Restrict the column to its essential variables to
     obtain a reduced truth table, then match it against every canonical gate
     signature (searching KOFN and CANALISING parameters).  Because the forward
     method is an exact index-set formula, this inversion is exact and the
     reconstructed network reproduces the repertoire byte for byte.

Node/bit indices are 0-based, matching :mod:`causalbool`.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from causalbool import Network, apply_gate, truth_table, repertoire


# ---------------------------------------------------------------------------
# Step 1 - essential-variable detection (pivots vs sumandos)
# ---------------------------------------------------------------------------

def essential_variables(column: list[int], n: int) -> list[int]:
    """Return the ascending list of bit positions on which ``column`` depends.

    Bit ``i`` is essential iff there exists an input ``x`` with
    ``column[x] != column[x ^ (1 << i)]``.  These are exactly the connected
    inputs (pivots); the remaining bits are the disconnected offset dimension
    (sumandos).
    """
    if len(column) != 2 ** n:
        raise ValueError("column length must be 2**n")
    essential = []
    for i in range(n):
        bit = 1 << i
        sensitive = False
        for x in range(2 ** n):
            if x & bit:
                continue  # visit each unordered pair once (x has bit i = 0)
            if column[x] != column[x | bit]:
                sensitive = True
                break
        if sensitive:
            essential.append(i)
    return essential


def reduce_column(column: list[int], n: int, essential: list[int]) -> list[int]:
    """Project ``column`` onto its essential variables.

    Returns a length ``2**m`` reduced truth table (``m = len(essential)``),
    enumerated LSB-first over the essential variables in ascending order.
    Raises ``AssertionError`` if the column is not in fact constant across the
    non-essential dimension, which would indicate the essential set is wrong.
    """
    m = len(essential)
    reduced: list[int] = [-1] * (2 ** m)
    for x in range(2 ** n):
        y = 0
        for j, e in enumerate(essential):
            if x & (1 << e):
                y |= (1 << j)
        val = column[x]
        if reduced[y] == -1:
            reduced[y] = val
        else:
            assert reduced[y] == val, (
                "non-essential variable affects output; essential set is wrong"
            )
    assert all(v != -1 for v in reduced)
    return reduced


# ---------------------------------------------------------------------------
# Step 2 - gate identification against the canonical family
# ---------------------------------------------------------------------------

# Canonical priority: simplest / most specific named gates first.  Any match
# reproduces the reduced truth table exactly, so this ordering only selects the
# representative reported as canonical; the full match list records ambiguity.
_CANONICAL_PRIORITY = (
    "AND", "OR", "NAND", "NOR", "XOR", "XNOR",
    "NOT", "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "REGULATORY", "CANALISING",
)


@dataclass
class GateMatch:
    gate: str
    params: dict = field(default_factory=dict)

    def as_dict(self) -> dict:
        return {"gate": self.gate, "params": dict(self.params)}


def _candidate_gates(m: int) -> list[GateMatch]:
    """Enumerate all (gate, params) candidates for arity ``m``."""
    cands: list[GateMatch] = []
    if m == 0:
        return cands  # constant handled separately
    for g in ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY"):
        cands.append(GateMatch(g))
    if m == 1:
        cands.append(GateMatch("NOT"))
    if m == 2:
        cands.append(GateMatch("IMPLIES"))
        cands.append(GateMatch("NIMPLIES"))
    for k in range(1, m + 1):
        cands.append(GateMatch("KOFN", {"k": k}))
    for ci in range(m):
        for cv in (0, 1):
            for co in (0, 1):
                cands.append(GateMatch(
                    "CANALISING",
                    {"canalisingIndex": ci, "canalisingValue": cv,
                     "canalisedOutput": co},
                ))
    return cands


def identify_gate(reduced: list[int]) -> tuple[list[GateMatch], GateMatch]:
    """Match a reduced truth table against the canonical gate family.

    Returns ``(matches, canonical)`` where ``matches`` is every candidate whose
    truth table equals ``reduced`` (the ambiguity/equivalence class) and
    ``canonical`` is the highest-priority representative.  Handles the constant
    (arity 0) case with the pseudo-gates ``TRUE`` / ``FALSE``.
    """
    m = (len(reduced)).bit_length() - 1  # log2 of length
    if 2 ** m != len(reduced):
        raise ValueError("reduced table length must be a power of two")

    if m == 0:
        g = "TRUE" if reduced[0] == 1 else "FALSE"
        match = GateMatch(g)
        return [match], match

    matches = [c for c in _candidate_gates(m)
               if truth_table(c.gate, m, c.params) == reduced]

    # Regulatory (activator/inhibitor) clause: the reduced truth table has a
    # single 1, whose position encodes which inputs are activators (bit 1) and
    # which are inhibitors (bit 0).  This names the mixed AND-NOT functions that
    # pervade gene-regulatory logic and have no other canonical name.
    if sum(reduced) == 1:
        ystar = reduced.index(1)
        activators = [j for j in range(m) if (ystar >> j) & 1]
        matches.append(GateMatch("REGULATORY", {"activators": activators, "arity": m}))

    if not matches:
        # No canonical gate reproduces this function.  Report as a raw truth
        # table so the caller can still reconstruct via an explicit LUT.
        lut = GateMatch("LUT", {"table": list(reduced)})
        return [lut], lut

    def priority(mm: GateMatch) -> tuple[int, int]:
        base = _CANONICAL_PRIORITY.index(mm.gate)
        # Prefer smaller k for KOFN, lower index for canalising: stable choice.
        secondary = mm.params.get("k", 0) + mm.params.get("canalisingIndex", 0)
        return (base, secondary)

    canonical = min(matches, key=priority)
    return matches, canonical


# ---------------------------------------------------------------------------
# Per-node and full-network deconvolution
# ---------------------------------------------------------------------------

@dataclass
class NodeReconstruction:
    node: int
    connected_inputs: list[int]
    reduced_truth_table: list[int]
    matches: list[GateMatch]
    canonical: GateMatch

    def as_dict(self) -> dict:
        return {
            "node": self.node,
            "connected_inputs": list(self.connected_inputs),
            "arity": len(self.connected_inputs),
            "reduced_truth_table": list(self.reduced_truth_table),
            "num_matches": len(self.matches),
            "matches": [m.as_dict() for m in self.matches],
            "canonical": self.canonical.as_dict(),
        }


def deconvolve_column(column: list[int], n: int, node: int) -> NodeReconstruction:
    """Deconvolve a single output column into ``(I_c, gate)``."""
    ic = essential_variables(column, n)
    reduced = reduce_column(column, n, ic)
    matches, canonical = identify_gate(reduced)
    return NodeReconstruction(node, ic, reduced, matches, canonical)


def deconvolve(rep: list[list[int]]) -> tuple[Network, list[NodeReconstruction]]:
    """Deconvolve a full ``2**n x n`` repertoire into a :class:`Network`.

    Returns the reconstructed network and the per-node reconstruction reports.
    The reconstructed network is built so that its canonical gate is applied to
    its connected inputs in ascending order, matching the forward method.
    """
    R = len(rep)
    n = len(rep[0])
    if 2 ** n != R:
        raise ValueError("repertoire must have 2**n rows and n columns")

    reports: list[NodeReconstruction] = []
    C = [[0] * n for _ in range(n)]
    gates: list[str] = ["FALSE"] * n
    params: list[dict] = [dict() for _ in range(n)]

    for k in range(n):
        column = [rep[x][k] for x in range(R)]
        rec = deconvolve_column(column, n, k)
        reports.append(rec)
        for i in rec.connected_inputs:
            C[k][i] = 1
        gates[k] = rec.canonical.gate
        params[k] = dict(rec.canonical.params)

    net = Network(n=n, C=C, gates=gates, params=params)
    return net, reports


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def _apply_reconstructed_column(rec: NodeReconstruction, n: int) -> list[int]:
    """Recompute a node column from its reconstruction (supports LUT gates)."""
    ic = rec.connected_inputs
    g = rec.canonical
    col = []
    for x in range(2 ** n):
        sub = [(x >> i) & 1 for i in ic]
        if g.gate == "TRUE":
            col.append(1)
        elif g.gate == "FALSE":
            col.append(0)
        elif g.gate == "LUT":
            y = 0
            for j in range(len(ic)):
                if sub[j]:
                    y |= (1 << j)
            col.append(g.params["table"][y])
        else:
            col.append(apply_gate(g.gate, sub, g.params))
    return col


def verify(original: list[list[int]], reports: list[NodeReconstruction]) -> dict:
    """Check that the reconstruction reproduces the original repertoire exactly.

    Reconstruction is done directly from the per-node reports (which may include
    LUT fall-backs), so verification is independent of gate naming.
    """
    R = len(original)
    n = len(original[0])
    exact = True
    mismatched_nodes = []
    for k in range(n):
        col_orig = [original[x][k] for x in range(R)]
        col_rec = _apply_reconstructed_column(reports[k], n)
        if col_orig != col_rec:
            exact = False
            mismatched_nodes.append(k)
    return {
        "exact": exact,
        "mismatched_nodes": mismatched_nodes,
        "n_nodes": n,
        "repertoire_rows": R,
    }
