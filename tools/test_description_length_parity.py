#!/usr/bin/env python3
"""AUDIT01/T4.5 AC-4.5b parity gate: the shared wrapper must reproduce the
committed toy fixture elementwise AND the V5-stamped single-node values.

Run: source venv/bin/activate && python tools/test_description_length_parity.py
Exit non-zero on any drift. Deterministic.
"""
from __future__ import annotations

import json
import math
import subprocess
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

    # A stale fixture must say so, not raise a KeyError three checks later.
    required = ("A_row_run_index_set_bits", "B_gate_plus_index_set_bits",
                "B_legacy_pathinfo_no_indegree_bits",
                "C_model_dnf_and_node_bits", "D_biometrics_D_bits_wl",
                "E_schema_normal_form_bits")
    missing = [k for k in required if k not in fx["variants"]]
    if missing:
        print("T45 PARITY FAIL: fixture is stale, missing", missing)
        print("  regenerate: venv/bin/python tools/t45_description_length_fixtures.py")
        return 1

    got_a = dl.row_run_index_set_length(A)
    if not close(got_a, fx["variants"]["A_row_run_index_set_bits"]):
        failures.append(f"A wrapper {got_a} != fixture")

    gate_list = [gates[str(v)] if str(v) in gates else gates[v] for v in range(n)]
    degrees = [len(edges[v]) for v in range(n)]
    got_b = dl.graph_gate_index_length(degrees, gate_list)
    if not close(got_b, fx["variants"]["B_gate_plus_index_set_bits"]):
        failures.append(f"B wrapper {got_b} != fixture")

    got_c = dl.model_dnf_bits([0, 0, 0, 1], 2)
    if not close(got_c, fx["variants"]["C_model_dnf_and_node_bits"]):
        failures.append(f"C wrapper {got_c} != fixture")

    # AUDIT03/R2b — variant E, the catalogue-free schema normal form, primary
    # since R3. Recomputed through the owner, not read back from the fixture.
    sys.path.insert(0, str(ROOT / "papers/method/code/complexity_analysis"))
    from complexity_analysis import _eval_gate  # noqa: E402
    got_e = 0.0
    for v in range(n):
        d = len(edges[v])
        tt = [_eval_gate(gate_list[v], [(y >> i) & 1 for i in range(d)], {})
              for y in range(2 ** d)]
        got_e += dl.schema_normal_form_length(tt, n)
    if not close(got_e, fx["variants"]["E_schema_normal_form_bits"]):
        failures.append(f"E wrapper {got_e} != fixture")

    # V5-stamped single-node value (n=4 space, one AND node of degree 2),
    # reproduced elementwise (U8): BioMetrics-family node cost has NO header.
    # AUDIT03/R2b moved this stamp by exactly log2(n+1) = log2 5, the in-degree
    # field, without which the per-node code is not uniquely decodable. The old
    # stamp was 7.169925001442312.
    v5_node = dl.node_description_cost(4, 2, "AND", include_header=False)
    if not close(v5_node, 7.169925001442312 + math.log2(5)):
        failures.append(f"V5 node cost {v5_node} != 7.169925001442312 + log2 5")

    # AUDIT03/R2b — the legacy gap is PINNED rather than removed. imp-pathinfo's
    # mirror does not charge the in-degree field and its published tables depend
    # on that; the difference must therefore be exactly n*log2(n+1) and must be
    # measured, not assumed.
    legacy_gap = (fx["variants"]["B_gate_plus_index_set_bits"]
                  - fx["variants"]["B_legacy_pathinfo_no_indegree_bits"])
    if not close(legacy_gap, n * math.log2(n + 1)):
        failures.append(f"legacy in-degree gap {legacy_gap} != {n} * log2({n+1})")
    got_legacy = dl.graph_gate_index_length(degrees, gate_list,
                                            in_degree_field=False)
    if not close(got_legacy, fx["variants"]["B_legacy_pathinfo_no_indegree_bits"]):
        failures.append(f"legacy switch {got_legacy} != pathinfo mirror value")

    # AUDIT03/R2b — THE WOLFRAM ARM, RE-RUN.
    # This check previously compared two STORED numbers (fixture B minus fixture
    # D) and so could not see the Wolfram side move at all. It did move: R3.1
    # added the in-degree field to BioMetrics.m and the producer went from
    # 25.9248 to 35.2125 bits while this gate kept reporting OK. The producer is
    # now executed and compared.
    wl = subprocess.run(
        ["/Applications/Wolfram.app/Contents/MacOS/WolframKernel", "-script",
         str(ROOT / "tools" / "t45_biometrics_toy.m")],
        capture_output=True, text=True, cwd=ROOT)
    if wl.returncode != 0:
        failures.append(f"WL producer failed: {wl.stderr.strip()[:200]}")
    else:
        got_d = float(wl.stdout.strip().splitlines()[-1])
        if not close(got_d, fx["variants"]["D_biometrics_D_bits_wl"], 1e-6):
            failures.append(
                f"WOLFRAM DRIFT: BioMetrics.m produces {got_d}, fixture pins "
                f"{fx['variants']['D_biometrics_D_bits_wl']}")
        header_delta = fx["variants"]["B_gate_plus_index_set_bits"] - got_d
        if not close(header_delta, 2.0, 1e-6):
            failures.append(
                f"header asymmetry {header_delta} != log2(4); Python and "
                f"Wolfram no longer differ by the header alone")

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
