#!/usr/bin/env python3
"""AUDIT01/T4.5 AC-4.5b parity gate: the shared wrapper must reproduce the
committed toy fixture elementwise AND the V5-stamped single-node values.

Run: source venv/bin/activate && python tools/test_description_length_parity.py
Exit non-zero on any drift. Deterministic.
"""
from __future__ import annotations

import json
import math
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "imp-causalNet-paper" / "src"))
sys.path.insert(0, str(ROOT / "imp-pathinfo-paper" / "src"))

import description_lengths as dl  # noqa: E402


def close(a, b, tol=1e-9):
    return abs(a - b) <= tol


def main() -> int:
    fx = json.loads((ROOT / "results" / "description_lengths" / "toy_fixture.json").read_text())
    n = fx["toy"]["n"]
    edges = {int(k): v for k, v in fx["toy"]["edges"].items()}
    gates = fx["toy"]["gates"]
    A = fx["toy"]["adjacency"]
    failures = []

    got_a = dl.row_run_index_set_length(A)
    if not close(got_a, fx["variants"]["A_row_run_index_set_bits"]):
        failures.append(f"A wrapper {got_a} != fixture")

    degrees = [len(edges[v]) for v in range(n)]
    got_b = dl.graph_gate_index_length(degrees, [gates[str(v)] if str(v) in gates else gates[v] for v in range(n)])
    if not close(got_b, fx["variants"]["B_gate_plus_index_set_bits"]):
        failures.append(f"B wrapper {got_b} != fixture")

    got_c = dl.model_dnf_bits([0, 0, 0, 1], 2)
    if not close(got_c, fx["variants"]["C_model_dnf_and_node_bits"]):
        failures.append(f"C wrapper {got_c} != fixture")

    # V5-stamped single-node values (n=4 space, one AND node of degree 2),
    # reproduced elementwise (U8): BioMetrics-family node cost has NO header.
    v5_node = dl.node_description_cost(4, 2, "AND", include_header=False)
    if not close(v5_node, 7.169925001442312):
        failures.append(f"V5 node cost {v5_node} != 7.169925001442312")
    # pathinfo graph header asymmetry on the same toy: B - D == log2(4) exactly.
    header_delta = fx["variants"]["B_gate_plus_index_set_bits"] - fx["variants"]["D_biometrics_D_bits_wl"]
    if not close(header_delta, 2.0):
        failures.append(f"pathinfo-vs-BioMetrics header delta {header_delta} != 2.0")

    # BDM edge semantics knob behaves as documented.
    small = [[1, 0], [0, 1]]
    if dl.bdm_2d(small, below_floor="pathinfo") is not None:
        failures.append("bdm_2d below_floor='pathinfo' did not return None below floor")
    try:
        dl.bdm_2d(small, below_floor="raise")
        failures.append("bdm_2d below_floor='raise' did not raise")
    except ValueError:
        pass

    if failures:
        print("T45 PARITY FAIL:")
        for f in failures:
            print(" -", f)
        return 1
    print("T45 PARITY OK (wrapper==fixture; V5 stamps reproduced; BDM knobs behave)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
