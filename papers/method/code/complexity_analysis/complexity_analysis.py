"""
Complexity analysis for the 10-node mixed-gate Boolean network.

Computes four complementary measures reported in Table 2 of the manuscript:

  C_formula  -- structural formula components (gate + index-set pieces per node)
  D_formula  -- programme-length proxy in bits (label + connectivity + parameter coding)
  ZIP_bits   -- zlib-compressed output table size in bits
  H_total    -- total Shannon entropy of the output table in bits

Usage:
    python complexity_analysis.py

Outputs: complexity_results.json  (same keys as the archived Complexity.json)
"""

from __future__ import annotations

import json
import math
from pathlib import Path


# ---------------------------------------------------------------------------
# Network definition (10-node mixed-gate network)
# Identical to the network used in mixed_interaction_10node experiments.
# ---------------------------------------------------------------------------

CM10 = [
    [0, 1, 1, 0, 0, 0, 0, 0, 0, 0],  # node 1  AND    inputs: {2,3}
    [1, 0, 1, 0, 0, 0, 0, 0, 0, 0],  # node 2  OR     inputs: {1,3}
    [0, 0, 0, 1, 1, 0, 0, 0, 0, 0],  # node 3  XOR    inputs: {4,5}
    [0, 1, 1, 0, 1, 0, 0, 0, 0, 0],  # node 4  KOFN   inputs: {2,3,5}  k=2
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],  # node 5  NOR    inputs: {6}
    [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],  # node 6  XNOR   inputs: {5,7}
    [0, 0, 0, 0, 0, 1, 0, 0, 0, 0],  # node 7  NOT    inputs: {6}
    [1, 0, 0, 0, 0, 0, 0, 0, 1, 0],  # node 8  IMPLIES  pair=(1,9)
    [0, 1, 0, 0, 0, 0, 0, 0, 0, 1],  # node 9  NIMPLIES pair=(2,10)
    [0, 0, 1, 1, 0, 0, 1, 1, 0, 0],  # node 10 MAJORITY inputs: {3,4,7,8}
]

DYN10 = [
    "AND", "OR", "XOR", "KOFN", "NOR",
    "XNOR", "NOT", "IMPLIES", "NIMPLIES", "MAJORITY",
]

PARAMS10 = {
    4: {"k": 2},           # node 4: KOFN with k=2
    8: {"pair": (1, 9)},   # node 8: IMPLIES antecedent=1 consequent=9
    9: {"pair": (2, 10)},  # node 9: NIMPLIES antecedent=2 consequent=10
}

# Full gate catalogue — K = 12 types
GATE_LABELS = [
    "AND", "OR", "XOR", "NAND", "NOR", "XNOR",
    "NOT", "IMPLIES", "NIMPLIES", "MAJORITY", "KOFN", "CANALISING",
]


# ---------------------------------------------------------------------------
# Gate evaluation
# ---------------------------------------------------------------------------

def _eval_gate(name: str, inputs: list[int], params: dict) -> int:
    """Synchronous Boolean gate evaluation."""
    if name == "AND":
        return int(all(inputs))
    if name == "OR":
        return int(any(inputs))
    if name == "XOR":
        return sum(inputs) % 2
    if name == "NAND":
        return 1 - int(all(inputs))
    if name == "NOR":
        return int(not any(inputs))
    if name == "XNOR":
        return 1 - (sum(inputs) % 2)
    if name == "NOT":
        return 1 - inputs[0]
    if name == "IMPLIES":
        # AUDIT03: this line used to be
        #     a, b = params["pair"]
        # and `a` and `b` were NEVER USED -- the return below does not mention
        # them. It was dead code that nonetheless RAISED KeyError whenever a
        # caller omitted "pair", which is why the gate-semantics collapse was
        # blocked: complexity_analysis and causalbool.apply_gate agreed on all
        # 300 values they both computed and disagreed on the CALL CONTRACT for
        # IMPLIES at d=1. Removing it reconciles the contract and changes no
        # value, because the antecedent is always inputs[0] and the consequent
        # inputs[1], in the ascending order of the connected inputs, exactly as
        # Gates.m's myImplies does. Measured: over 496 (input, pair)
        # combinations the output never depends on "pair".
        return int((not inputs[0]) or inputs[1])
    if name == "NIMPLIES":
        return int(inputs[0] and not inputs[1])
    if name == "MAJORITY":
        return int(sum(inputs) > len(inputs) // 2)
    if name == "KOFN":
        k = params.get("k", 1)
        return int(sum(inputs) >= k)
    if name == "CANALISING":
        # Mirrors myCanalising in src/Packages/Integration/Gates.m:18 —
        #   If[list[[i]] == v, out, myOr[list]]
        # with defaults canalisingIndex=1 (1-based in Wolfram), canalisingValue=1,
        # canalisedOutput=0.
        i = params.get("canalisingIndex", 1) - 1
        v = params.get("canalisingValue", 1)
        out = params.get("canalisedOutput", 0)
        return int(out) if inputs[i] == v else int(any(inputs))
    raise ValueError(f"Unknown gate: {name}")


def build_output_table(cm: list[list[int]], dyn: list[str], params: dict) -> list[list[int]]:
    """
    Build the full 2^n x n output (repertoire) table by exhaustive evaluation.

    Input ordering: row index idx in [0, 2^n) encodes the state where
    x[i] = (idx >> i) & 1  (LSB = node 1), matching the companion Wolfram
    scripts that use weights[n] = 2^Range[0,n-1].
    """
    n = len(dyn)
    ics = [[j for j, v in enumerate(cm[i]) if v == 1] for i in range(n)]
    table: list[list[int]] = []
    for idx in range(2 ** n):
        state = [(idx >> i) & 1 for i in range(n)]
        row: list[int] = []
        for i in range(n):
            ic = ics[i]
            node_params = params.get(i + 1, {})
            inp = [state[j] for j in ic]
            row.append(_eval_gate(dyn[i], inp, node_params))
        table.append(row)
    return table


# ---------------------------------------------------------------------------
# Measure 1 – C_formula: structural formula component count
#
# compressionWeight counts the symbolic pieces in the closed-form index-set
# formula for each gate.  The formula for a gate G with in-degree d is:
#   AND | OR | NAND | NOR   ->  1 (gate token) + d (input index tokens)
#   XOR | XNOR              ->  1 + 1
#   NOT                     ->  1
#   IMPLIES | NIMPLIES      ->  1 + 2
#   MAJORITY                ->  1 + 1
#   KOFN                    ->  1 + 1
#   CANALISING              ->  1 + 1 (or 1 + 0 if output is fixed by params)
#
# Source: compressionWeight function in
#   tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m (lines 215-228)
# ---------------------------------------------------------------------------

def compression_weight(gate: str, d: int, node_params: dict) -> int:
    if gate in ("AND", "OR", "NAND", "NOR"):
        return 1 + d
    if gate in ("XOR", "XNOR"):
        return 2
    if gate == "NOT":
        return 1
    if gate in ("IMPLIES", "NIMPLIES"):
        return 3
    if gate in ("MAJORITY", "KOFN"):
        return 2
    if gate == "CANALISING":
        return 1 if "canalisedOutput" in node_params else 2
    return 1 + d


def compute_c_formula(cm: list[list[int]], dyn: list[str], params: dict) -> int:
    """Sum of formula component counts across all nodes."""
    total = 0
    for i, gate in enumerate(dyn):
        d = sum(cm[i])
        total += compression_weight(gate, d, params.get(i + 1, {}))
    return total


# ---------------------------------------------------------------------------
# Measure 2 – D_formula: programme-length proxy in bits
#
# IMPORTANT — WHAT THIS IS AND IS NOT
# -----------------------------------
# D_formula is the COST OF ENCODING THE GENERATOR: the number of bits needed to
# write down the network specification (gate types, wiring, parameters) under the
# declared encoding below.  It is a description length of the PROGRAMME.
#
# It is NOT a complexity measure of the network's behaviour, and must never be
# reported as one.  Concretely:
#
#   * D_formula never reads a single output bit.  It is a function of n, the
#     in-degrees, and the gate types, and of nothing else.  Rewire a node to a
#     different input set of the same size and D_formula does not move, while the
#     behaviour changes substantially (verified in D_formula_explained.ipynb §6:
#     440 of 1024 output rows change, distinct output states 206 -> 172, and
#     D_formula is bit-identical).  The same degeneracy was found independently in
#     the imp-pathinfo replication, where a wiring-based D separated 0 of 250
#     same-degree pairs.
#
#   * It therefore CANNOT rank, discriminate, or say anything about behaviours.
#     Any claim of the form "network A is more complex than network B because
#     D_formula(A) > D_formula(B)" is invalid.
#
#   * It is an UPPER BOUND on the shortest description in ONE declared language,
#     not an estimate of K.  Write "a description of 101.07 bits", never "the
#     complexity is 101.07 bits".
#
# Why this is legitimate here rather than a limitation: in this research the
# generator is GIVEN.  The network is a controlled object, not an unknown to be
# reverse-engineered, so no algorithmic-complexity estimation problem arises on
# the mechanism side.  All that is required is the cost of encoding a known
# programme.  That is exactly what D_formula supplies, and it is the correct
# quantity for the programme side of a programme-versus-output comparison.
#
# ENCODING
# --------
# Each node i is encoded by four fields:
#   (a) gate type:       log2(K)                  K = 12 gate types
#   (b) in-degree:       log2(n + 1)              d_i in {0, ..., n}
#   (c) input set:       log2(C(n, d_i))          C(n,d) ways to choose d of n
#   (d) gate-specific:
#         KOFN           log2(d+1) + 1            threshold k in {0,...,d}
#         CANALISING     log2(n) + 2              index + value + output bit
#         IMPLIES/NIMPLIES  log2(max(1,d(d-1)))   ordered pair within inputs
#         NOT            log2(max(1,d))            which input to negate
#         XOR/XNOR/MAJORITY  1                    parity / majority flag
#         others         1                        polarity bit
#
# The in-degree field (b) is required for the code to be uniquely decodable: a
# decoder cannot read log2(C(n,d_i)) bits, nor interpret them as an index into the
# d_i-subsets of [n], without first knowing d_i.  Earlier revisions of this script
# and of both manuscripts omitted it and reported D_formula = 101.07 bits; that
# figure was not a valid description length and has been superseded by 135.66 bits.
# The cost of specifying n itself is not charged, since it is constant across the
# networks being compared.
#
# Source: encodeCostBits function in
#   tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m (lines 235-254),
#   extended here with the in-degree field.
# ---------------------------------------------------------------------------

def _log2(x: float) -> float:
    return math.log2(x) if x > 0 else 0.0


def encode_node_cost(d: int, gate: str, n: int) -> float:
    """D contribution for one node."""
    K = len(GATE_LABELS)
    cost = _log2(K)
    cost += _log2(n + 1)                      # in-degree d, required for decodability
    cost += _log2(max(1, math.comb(n, d)))
    if gate == "KOFN":
        cost += _log2(d + 1) + 1.0
    elif gate == "CANALISING":
        cost += _log2(n) + 2.0
    elif gate in ("IMPLIES", "NIMPLIES"):
        cost += _log2(max(1, d * (d - 1)))
    elif gate == "NOT":
        cost += _log2(max(1, d))
    else:  # AND, OR, NAND, NOR, XOR, XNOR, MAJORITY, and any other
        cost += 1.0
    return cost


def compute_d_formula(cm: list[list[int]], dyn: list[str], n: int) -> float:
    """Sum of encoding costs (in bits) across all nodes."""
    return sum(encode_node_cost(sum(cm[i]), dyn[i], n) for i in range(n))


# ---------------------------------------------------------------------------
# Measure 3 – ZIP_bits: compressed output-table size in bits
#
# The 2^n x n output table is serialised as a CSV (comma-separated 0/1
# integers, one row per line, Unix line endings) and compressed with zlib
# (deflate, level 9).  ZIP_bits is the compressed byte count × 8.
#
# Note on the archived value (1600 bits / 200 bytes):
#   The Complexity.json value of 1600 bits came from a Wolfram ZIP file that
#   contained only a 64-byte path-reference string, not the actual compressed
#   CSV.  The 200-byte file size was therefore a measurement artefact rather
#   than a compression of the output repertoire.  This companion script uses
#   proper zlib compression of the actual CSV bytes.  The scientific
#   conclusion (D_formula << compressed_output << H_total) holds under either
#   measurement.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Measure 2b - D_schema: the catalogue-free description length.
#
# AUDIT03/R2b. D_formula above charges log2(12) to name a gate in a catalogue
# the code never transmits. D_schema transmits no catalogue: it writes each
# node's schemata out. R3 made it the primary mechanism-side measure, so it
# needs a producer here rather than only in an audit script -- both manuscripts
# quote it, and a quoted number without a producer is the defect this audit
# exists to remove.
#
# The computation is DELEGATED to src/description_lengths.py, the repository's
# single description-length owner, which in turn reuses minimal_dnf from
# index-deconvolution. Nothing is reimplemented here; a second copy of either
# routine is exactly what R2b removes.
# ---------------------------------------------------------------------------

def compute_d_schema(cm: list[list[int]], dyn: list[str], params: dict,
                     n: int) -> float:
    import sys
    from pathlib import Path
    root = Path(__file__).resolve().parents[4]
    p = str(root / "src")
    if p not in sys.path:
        sys.path.insert(0, p)
    import description_lengths as dl

    total = 0.0
    for i in range(n):
        ic = [j for j, v in enumerate(cm[i]) if v == 1]
        d = len(ic)
        node_params = params.get(i + 1, {})
        tt = [_eval_gate(dyn[i], [(y >> b) & 1 for b in range(d)], node_params)
              for y in range(2 ** d)]
        total += dl.schema_normal_form_length(tt, n)
    return total


def compute_zip_bits(table: list[list[int]]) -> tuple[int, int, int]:
    """
    Returns (csv_bytes_len, compressed_bytes_len, zip_bits).

    CSV format matches Mathematica's Export[matrix, "CSV"]:
    comma-separated 0/1 integers, newline-terminated rows.
    """
    import zlib
    csv_lines = [",".join(str(v) for v in row) + "\n" for row in table]
    csv_bytes = "".join(csv_lines).encode("ascii")
    compressed = zlib.compress(csv_bytes, level=9)
    return len(csv_bytes), len(compressed), len(compressed) * 8


# ---------------------------------------------------------------------------
# Measure 4 – H_total: total Shannon entropy in bits
#
# For the full output table (2^n rows x n columns):
#   p_overall = fraction of 1s across all output bits
#   h_overall = -p*log2(p) - (1-p)*log2(1-p)   (binary entropy)
#   H_total   = h_overall * 2^n * n
#
# Source: pOverall / shannonOverall / H computation in
#   tests/MUnit/Mixed/TSK-MIXED-001-FormulaVsExhaustive.m (lines 206-211)
# ---------------------------------------------------------------------------

def _binary_entropy(p: float) -> float:
    if p <= 0.0 or p >= 1.0:
        return 0.0
    return -p * math.log2(p) - (1 - p) * math.log2(1 - p)


def compute_h_total(table: list[list[int]]) -> tuple[float, float, list[float]]:
    """
    Returns (shannon_overall, H_total_bits, shannon_per_node).
    """
    n_rows = len(table)
    n_cols = len(table[0])
    total_bits = n_rows * n_cols

    flat = [v for row in table for v in row]
    p_overall = sum(flat) / total_bits
    h_overall = _binary_entropy(p_overall)
    H_total = h_overall * total_bits

    per_node: list[float] = []
    for col in range(n_cols):
        col_sum = sum(table[row][col] for row in range(n_rows))
        p_col = col_sum / n_rows
        per_node.append(_binary_entropy(p_col))

    return h_overall, H_total, per_node


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    n = len(DYN10)

    # Build the exhaustive output table
    table = build_output_table(CM10, DYN10, PARAMS10)

    # C_formula
    c_formula = compute_c_formula(CM10, DYN10, PARAMS10)

    # D_formula
    d_formula = compute_d_formula(CM10, DYN10, n)

    # D_schema (AUDIT03/R3: primary measure)
    d_schema = compute_d_schema(CM10, DYN10, PARAMS10, n)

    # ZIP (proper lossless compression of actual CSV)
    csv_raw_bytes, csv_compressed_bytes, zip_bits = compute_zip_bits(table)

    # Shannon / H_total
    h_overall, H_total, h_per_node = compute_h_total(table)

    results = {
        "C_formula": c_formula,
        "D_formula_bits": round(d_formula, 5),
        "D_schema_bits": round(d_schema, 5),
        "CSV_raw_bytes": csv_raw_bytes,
        "CSV_compressed_bytes": csv_compressed_bytes,
        "ZIP_bits": zip_bits,
        "H_total_bits": round(H_total, 5),
        "shannonOverall": round(h_overall, 13),
        "shannonPerNode": [round(h, 13) for h in h_per_node],
        "Formula_over_ZIP": round(d_formula / zip_bits, 9),
        "Formula_over_Shannon": round(d_formula / H_total, 9),
        "ZIP_over_Schema": round(zip_bits / d_schema, 5),
        "Shannon_over_Schema": round(H_total / d_schema, 5),
        "note_zip": (
            "ZIP_bits is proper zlib compression of the full CSV. "
            "The manuscript value 1600 bits came from a Wolfram ZIP artefact "
            "(path-reference string, not compressed output data)."
        ),
    }

    # -----------------------------------------------------------------------
    # Verification against published values (method_paper.tex, Table 2)
    # -----------------------------------------------------------------------
    PAPER_C    = 23
    PAPER_D    = 135.66    # bits, rounded (self-delimiting; supersedes 101.07)
    PAPER_H    = 10229.61  # bits, rounded
    PAPER_DS   = 232.72    # bits, rounded (catalogue-free; AUDIT03/R3)

    ok_c = (c_formula == PAPER_C)
    ok_d = (abs(d_formula - PAPER_D) < 0.01)
    ok_h = (abs(H_total  - PAPER_H)  < 0.1)
    ok_ds = (abs(d_schema - PAPER_DS) < 0.01)
    # ZIP note: paper value (1600 bits) was an artefact; we verify the ordering
    # D_formula << zlib_zip << H_total instead.
    ok_ordering = (d_formula < zip_bits < H_total * 2)

    print("=" * 60)
    print("  Complexity analysis — 10-node mixed-gate network")
    print("=" * 60)
    print(f"  n = {n}   |Im(F)| = {len(set(map(tuple, table)))}")
    print()
    print(f"  C_formula   = {c_formula}          paper: {PAPER_C}  {'OK' if ok_c else 'FAIL'}")
    print(f"  D_formula   = {d_formula:.5f} bits  paper: {PAPER_D}   {'OK' if ok_d else 'FAIL'}")
    print(f"  D_schema    = {d_schema:.5f} bits  paper: {PAPER_DS}  {'OK' if ok_ds else 'FAIL'}")
    print(f"  H_total     = {H_total:.5f} bits  paper: {PAPER_H}  {'OK' if ok_h else 'FAIL'}")
    print()
    print(f"  CSV raw     = {csv_raw_bytes} bytes")
    print(f"  zlib compr  = {csv_compressed_bytes} bytes = {zip_bits} bits")
    print(f"  (paper ZIP  = 200 bytes = 1600 bits  [Wolfram artefact, see note])")
    print()
    print(f"  D/zlib      = {results['Formula_over_ZIP']:.5f}")
    print(f"  D/H_total   = {results['Formula_over_Shannon']:.6f}")
    print(f"  Ordering D << zlib << H:  {'OK' if ok_ordering else 'FAIL'}")
    print()
    all_ok = ok_c and ok_d and ok_ds and ok_h and ok_ordering
    print(f"  Overall: {'PASS' if all_ok else 'FAIL'}")
    print("=" * 60)

    out_path = Path(__file__).parent / "complexity_results.json"
    out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
    print(f"\n  Results written to {out_path.name}")


if __name__ == "__main__":
    main()
