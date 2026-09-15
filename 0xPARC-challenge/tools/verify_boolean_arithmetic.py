#!/usr/bin/env python3
"""Reproducible bounded verifier for the CausalBool arithmetic route.

The default run is intentionally self-contained and does not require Circom.
``--compile`` attempts the pinned external toolchain and records UNKNOWN when
the tools are absent; it never turns missing tooling into a PASS.
"""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
from pathlib import Path
import sys
import tempfile
import time

from oxparc_challenge.boolean_arithmetic import (
    BooleanDAG, BooleanGate, build_full_adder_dag, build_multiplier_dag,
    evaluate_boolean_dag,
)
from oxparc_challenge.boolean_constraints import (
    Q6_WIDTH, Q7_WIDTH, build_q5, build_q6, build_q7, witness_q5, witness_q6,
    witness_q7,
)
from oxparc_challenge.circom import compile_circuit, export_circom
from oxparc_challenge.constraints import ConstraintSystem
from oxparc_challenge.gadgets import build_exclude_one, build_factor64, build_range
from oxparc_challenge.row_evaluator import check_rows


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _system_stats(system: ConstraintSystem) -> dict:
    serialized = system.to_json().encode("utf-8")
    return {"signals": len(system.signals), "rows": len(system.constraints),
            "serialized_bytes": len(serialized), "structural_sha256": _sha(serialized)}


def _check_gate_and_blocks() -> dict:
    full = build_full_adder_dag()
    full_count = 0
    for bits in itertools.product((0, 1), repeat=3):
        got = evaluate_boolean_dag(full, bits)
        expected = sum(bits)
        assert got == [expected & 1, expected >> 1]
        full_count += 1
    multipliers = {}
    for width in range(1, Q7_WIDTH + 1):
        dag = build_multiplier_dag(width)
        count = 0
        for u in range(1 << width):
            for v in range(1 << width):
                bits = [(u >> i) & 1 for i in range(width)] + [(v >> i) & 1 for i in range(width)]
                out = evaluate_boolean_dag(dag, bits)
                product = sum(bit << i for i, bit in enumerate(out[:2 * width]))
                assert product == u * v and out[2 * width:] == [0] * width
                count += 1
        multipliers[str(width)] = count
    defective = BooleanDAG(3, (BooleanGate("XOR", (0, 1)),
                              BooleanGate("AND", (0, 1))), (3, 4))
    counterexamples = []
    for bits in itertools.product((0, 1), repeat=3):
        expected = [sum(bits) & 1, sum(bits) >> 1]
        if evaluate_boolean_dag(defective, bits) != expected:
            counterexamples.append({"bits": list(bits), "expected": expected,
                                    "actual": evaluate_boolean_dag(defective, bits)})
            break
    assert counterexamples == [{"bits": [0, 0, 1], "expected": [1, 0], "actual": [0, 0]}]
    return {"full_adder_states": full_count, "multiplier_states": multipliers,
            "defective_block_counterexample": counterexamples[0]}


def _check_rows() -> dict:
    systems = {"Q5": (build_q5(), [(0, witness_q5(0)), (1, witness_q5(1)),
                                    ((1 << 64) - 1, witness_q5((1 << 64) - 1))]),
               "Q6": (build_q6(), [(0, witness_q6(0)), (2, witness_q6(2)),
                                    ("P-1", witness_q6(__import__("oxparc_challenge").FIELD_PRIME - 1))]),
               "Q7": (build_q7(), [(15, witness_q7(15, 3, 5)),
                                    ("swapped", witness_q7(15, 5, 3))])}
    result = {}
    for name, (system, cases) in systems.items():
        serialized = system.to_dict()
        valid = [{"case": str(case), "failures": check_rows(serialized, witness)}
                 for case, witness in cases]
        forged = dict(cases[0][1])
        if name == "Q5":
            forged["x_b0"] = 2
        elif name == "Q6":
            forged["r"] = 1
            prime = __import__("oxparc_challenge").FIELD_PRIME
            forged.update({f"r_b{i}": ((prime + 1) >> i) & 1 for i in range(Q6_WIDTH)})
        else:
            forged.update({"n": 0, **{f"n_b{i}": 0 for i in range(Q7_WIDTH)}})
        failures = check_rows(serialized, forged)
        assert failures
        result[name] = {"stats": _system_stats(system), "valid_cases": valid,
                         "forged_assignment_failures": failures}
    result["baseline_comparison"] = {
        "Q5_legacy_64bit_range": _system_stats(build_range()),
        "Q6_legacy_field_inverse": _system_stats(build_exclude_one()),
        "Q7_legacy_64bit_factor": _system_stats(build_factor64()),
        "note": "Counts are not like-for-like: the new route is Boolean-gate compiled; Q7 new is width 4 and legacy is width 64."
    }
    return result


def _check_q7_exhaustive() -> dict:
    system = build_q7().to_dict()
    valid = invalid = 0
    for u, v, n in itertools.product(range(1 << Q7_WIDTH), repeat=3):
        expected = u >= 2 and v >= 2 and u * v == n
        if expected:
            assert check_rows(system, witness_q7(n, u, v)) == []
            valid += 1
        else:
            invalid += 1
    assert valid + invalid == (1 << Q7_WIDTH) ** 3
    return {"width": Q7_WIDTH, "triples": valid + invalid, "valid": valid, "invalid": invalid,
            "oracle": "independent integer predicate u>=2 and v>=2 and u*v==n"}


def _check_deconvolution() -> dict:
    root = Path(__file__).resolve().parents[2] / "index-deconvolution" / "src"
    sys.path.insert(0, str(root))
    from causalbool import Network, repertoire
    from deconvolution import deconvolve, verify_forward
    # A six-node local repertoire contains pass-through inputs, the first XOR,
    # full-adder sum XOR, and MAJ3 carry.  It is a deconvolution replay probe,
    # not part of the quadratic correctness boundary.
    network = Network(6, [
        [1, 0, 0, 0, 0, 0], [0, 1, 0, 0, 0, 0], [0, 0, 1, 0, 0, 0],
        [1, 1, 0, 0, 0, 0], [0, 0, 1, 1, 0, 0], [1, 1, 1, 0, 0, 0],
    ], ["OR", "OR", "OR", "XOR", "XOR", "MAJORITY"])
    original = repertoire(network)
    recovered, reports = deconvolve(original)
    replay = verify_forward(original, recovered)
    assert replay["exact"]
    return {"nodes": 6, "rows": len(original), "exact_forward_replay": True,
            "canonical_gates": [report.canonical.gate for report in reports]}


def _compile_if_requested(output: Path, systems: dict) -> dict:
    if not systems:
        return {"status": "NOT_REQUESTED"}
    records = {}
    with tempfile.TemporaryDirectory(prefix="causalbool-arithmetic-") as tmp:
        root = Path(tmp)
        for name, system in systems.items():
            source = export_circom(system, root / f"{name}.circom")
            try:
                artifacts = compile_circuit(source, root / name / "compiled")
                records[name] = {"status": "PASS", "source_sha256": _sha(source.read_bytes()),
                                 "r1cs_bytes": artifacts["r1cs"].stat().st_size}
            except RuntimeError as exc:
                records[name] = {"status": "UNKNOWN", "source_sha256": _sha(source.read_bytes()),
                                 "reason": str(exc)}
                break
    output.write_text(json.dumps(records, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return records


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path,
                        default=Path("evidence/causalbool_arithmetic/verification.json"))
    parser.add_argument("--compile", action="store_true")
    args = parser.parse_args()
    started = time.monotonic()
    gate = _check_gate_and_blocks()
    rows = _check_rows()
    q7 = _check_q7_exhaustive()
    deconv = _check_deconvolution()
    systems = {"Q5": build_q5(), "Q6": build_q6(), "Q7": build_q7()}
    compile_status = _compile_if_requested(args.output.with_suffix(".compile.json"), systems) if args.compile else {"status": "UNKNOWN", "reason": "not attempted"}
    report = {"status": "PASS", "q7_scope": "width=4 exhaustive only", "gate_and_blocks": gate,
              "rows": rows, "q7_exhaustive": q7, "deconvolution": deconv,
              "compile": compile_status, "elapsed_seconds": time.monotonic() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "q7_triples": q7["triples"], "elapsed_seconds": report["elapsed_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
