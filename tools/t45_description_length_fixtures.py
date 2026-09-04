#!/usr/bin/env python3
"""AUDIT01/T4.5 - toy-fixture tabulation of the four description-length variants.

Executes all four cost models on ONE shared toy network (the V5 stamp's setting:
n=4, node 0 takes nodes {1,2} under AND; remaining wiring fixed below) and writes
results/description_lengths/toy_fixture.json. The committed JSON is the parity
fixture consumed by tools/test_description_length_parity.py.

Variants (GOVERNANCE/DESCRIPTION_LENGTHS.md is the authority):
  A row_run_index_set   : imp-causalNet-paper causalbool_mirror.index_set_description_length
  B gate_plus_index_set : imp-pathinfo-paper causalbool_mirror.graph_description_length
                          (structurally identical to BioMetrics encodeNodeCost + log2(n)
                          header; the WL side is pinned by the same fixture values in
                          DESCRIPTION_LENGTHS.md, executed via tools/t45_biometrics_toy.m)
  C model_dnf           : imp-causalNet-paper measure.model_description_length on the
                          AND node's truth table
Deterministic; no seeds needed (no stochastic component).
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "imp-causalNet-paper" / "src"))
sys.path.insert(0, str(ROOT / "imp-pathinfo-paper" / "src"))
sys.path.insert(0, str(ROOT / "src"))

OUT = ROOT / "results" / "description_lengths" / "toy_fixture.json"


def toy_graph():
    """n=4 ring-plus-chord wiring: 0<-{1,2} AND, 1<-{2} OR, 2<-{3} XOR, 3<-{0} NOT."""
    n = 4
    edges = {0: [1, 2], 1: [2], 2: [3], 3: [0]}
    gates = {0: "AND", 1: "OR", 2: "XOR", 3: "NOT"}
    A = [[0] * n for _ in range(n)]
    for v, srcs in edges.items():
        for s in srcs:
            A[v][s] = 1  # row v = feeder index set of v (matches variant A's reading)
    return n, edges, gates, A


def variant_a_row_run(A) -> float:
    from imp_causalnet_paper.causalbool_mirror import index_set_description_length
    import numpy as np
    return float(index_set_description_length(np.asarray(A)))


def variant_b_gate_index(n: int, edges, gates) -> float:
    """Variant B from the OWNER, src/description_lengths.py.

    AUDIT03/R2b moved this off the imp-pathinfo mirror. The fixture is the
    root repository's pin, so it must be produced by the root repository's
    owner; sourcing it from a subproject mirror meant the value the gate
    defended and the value the owner computed were free to differ.
    """
    import description_lengths as dl
    degrees = [len(edges[v]) for v in range(n)]
    gl = [gates[v] if v in gates else gates[str(v)] for v in range(n)]
    return float(dl.graph_gate_index_length(degrees, gl, include_header=True))


def variant_b_legacy_pathinfo(n: int, edges, gates) -> float:
    """The SAME variant as computed by imp-pathinfo's mirror, which does not
    charge the in-degree field and so is not a decodable code (Kraft sum n+1).

    It is pinned rather than fixed because imp-pathinfo's published tables were
    computed with it, and silently changing them would corrupt a replication.
    Pinning both makes the gap a measured, guarded quantity instead of a
    difference nobody is looking at: the parity test asserts it is exactly
    n*log2(n+1).
    """
    from imp_pathinfo.causalbool_mirror import node_description_cost
    total = math.log2(max(1, n))  # graph_description_length header
    for v in range(n):
        total += node_description_cost(n, len(edges[v]), gates[v])
    return float(total)


def variant_e_schema(n: int, edges, gates) -> float:
    """Variant E: the catalogue-free schema-normal-form length, summed over the
    toy network. Primary measure since AUDIT03/R3."""
    import description_lengths as dl
    sys.path.insert(0, str(ROOT / "papers" / "method" / "code" / "complexity_analysis"))
    from complexity_analysis import _eval_gate
    total = 0.0
    for v in range(n):
        d = len(edges[v])
        tt = [_eval_gate(gates[v], [(y >> i) & 1 for i in range(d)], {})
              for y in range(2 ** d)]
        total += dl.schema_normal_form_length(tt, n)
    return float(total)


def variant_c_model_dnf() -> float:
    from imp_causalnet_paper.measure import model_description_length
    # AND over two inputs, truth table in the convention measure.py expects
    # (rule-table order for d inputs): AND = 0001 -> bits (t>>i)&1 style.
    table = [(8 >> i) & 1 for i in range(4)]  # idx = c*2+r? fixed below by test
    mc = model_description_length(table, 2)
    return float(mc.bits)


def wl_variant_d() -> float:
    script = ROOT / "tools" / "t45_biometrics_toy.m"
    out = subprocess.run(
        ["/Applications/Wolfram.app/Contents/MacOS/WolframKernel", "-script", str(script)],
        capture_output=True, text=True, check=True).stdout.strip().splitlines()
    return float(out[-1])


def main() -> int:
    n, edges, gates, A = toy_graph()
    fixture = {
        "toy": {"n": n, "edges": {str(k): v for k, v in edges.items()},
                 "gates": gates, "adjacency": A,
                 "note": "C[k][i]=1 iff i feeds k; AND node 0 <- {1,2}; "
                         "AND truth table order: idx = l*2 + r"},
        "pybdm_version": "0.1.0",
        "variants": {
            "A_row_run_index_set_bits": variant_a_row_run(A),
            "B_gate_plus_index_set_bits": variant_b_gate_index(n, edges, gates),
            "B_legacy_pathinfo_no_indegree_bits":
                variant_b_legacy_pathinfo(n, edges, gates),
            "C_model_dnf_and_node_bits": variant_c_model_dnf(),
            "D_biometrics_D_bits_wl": wl_variant_d(),
            "E_schema_normal_form_bits": variant_e_schema(n, edges, gates),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(fixture, indent=1))
    print(json.dumps(fixture["variants"], indent=1))
    print("written:", OUT)

    # Nonidentity control (V5): at least three distinct values among variants.
    vals = sorted(set(round(v, 4) for v in fixture["variants"].values()))
    if len(vals) < 3:
        print("UNEXPECTED: variants collapsed to identical values", vals)
        return 1
    print("T45 FIXTURE OK - distinct values:", vals)
    return 0


if __name__ == "__main__":
    sys.exit(main())
