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
    assignment_q7_bits, witness_q7,
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


EXHAUSTIVE_WIDTH = 4  # Q7_WIDTH is 64; enumerating it would be 2**192 triples.


def _check_gate_and_blocks() -> dict:
    full = build_full_adder_dag()
    full_count = 0
    for bits in itertools.product((0, 1), repeat=3):
        got = evaluate_boolean_dag(full, bits)
        expected = sum(bits)
        assert got == [expected & 1, expected >> 1]
        full_count += 1
    multipliers = {}
    # Bounded by EXHAUSTIVE_WIDTH, never by Q7_WIDTH: this loop enumerates
    # (2**width)**2 products, so following the question's width would ask for
    # 2**128 evaluations and never return.
    for width in range(1, EXHAUSTIVE_WIDTH + 1):
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
        "note": "Q7 is now like-for-like: both routes are width 64. Q5 and Q6 are not, "
                "because the recovered route compiles a general bound through Boolean gates "
                "where the legacy systems use a bit count and a field inverse. The recovered "
                "route is larger everywhere and no performance claim is made for it."
    }
    return result


def _check_q7_exhaustive(width: int = EXHAUSTIVE_WIDTH) -> dict:
    """Every triple at a width small enough to enumerate completely."""
    system = build_q7(width).to_dict()
    valid = invalid = 0
    for u, v, n in itertools.product(range(1 << width), repeat=3):
        expected = u >= 2 and v >= 2 and u * v == n
        failures = check_rows(system, assignment_q7_bits(n, u, v, width))
        if expected:
            assert failures == []
            valid += 1
        else:
            assert failures
            invalid += 1
    assert valid + invalid == (1 << width) ** 3
    return {"width": width, "triples": valid + invalid, "valid": valid, "invalid": invalid,
            "oracle": "independent integer predicate u>=2 and v>=2 and u*v==n"}


def _check_full_width_q7() -> dict:
    """The width the question asks for, on genuine and adversarial assignments."""
    system = build_q7().to_dict()
    accepted = [(3, 5), (65537, 65539), (4294967291, 4294967279), (2, 2)]
    for u, v in accepted:
        assert check_rows(system, witness_q7(u * v, u, v)) == []
    big, other = (1 << 33) + 7, (1 << 33) + 13
    attacks = {
        "trivial_factor_u": assignment_q7_bits(7, 1, 7),
        "trivial_factor_v": assignment_q7_bits(7, 7, 1),
        "all_zero": assignment_q7_bits(0, 0, 0),
        "wrong_product": assignment_q7_bits(15, 3, 4),
        "truncated_overflow": assignment_q7_bits((big * other) % (1 << Q7_WIDTH), big, other),
    }
    for name, attack in attacks.items():
        assert check_rows(system, attack), name
    return {"width": Q7_WIDTH, "accepted_factorisations": len(accepted),
            "rejected_attacks": sorted(attacks),
            "largest_accepted_product": max(u * v for u, v in accepted)}


def _check_deconvolution() -> dict:
    """Check the cells actually compiled into Q5, Q6 and Q7 are recovered ones.

    This replaces a six-node replay probe that verified nothing about the
    constraint systems. Every cell below is named by the method from a stated
    integer relation, and every expansion into the DAG gates is discharged by
    root identity rather than assumed.
    """
    from oxparc_challenge.boolean_arithmetic import (
        _comparator_step, _difference_step, full_adder_cell, partial_product_cell,
        verify_expansion)

    cells = {"full_adder": full_adder_cell(), "partial_product": partial_product_cell(),
             "comparator_bound_0": _comparator_step(0), "comparator_bound_1": _comparator_step(1),
             "difference_bit_0": _difference_step(0), "difference_bit_1": _difference_step(1)}
    recovered, expansions = {}, 0
    for name, group in cells.items():
        for gate in group:
            assert verify_expansion(gate), name
            expansions += 1
        recovered[name] = [g.as_dict() for g in group]
    # The classical identities, recovered rather than written down.
    assert [g.gate for g in cells["full_adder"]] == ["XOR", "MAJORITY"]
    assert [g.gate for g in cells["partial_product"]] == ["AND"]
    return {"cells": recovered, "expansions_verified_by_root_identity": expansions,
            "used_by": {"Q5": ["comparator_bound_0", "comparator_bound_1"],
                        "Q6": ["comparator_bound_0", "comparator_bound_1",
                               "difference_bit_0", "difference_bit_1"],
                        "Q7": ["full_adder", "partial_product"]},
            "note": "sum = XOR and carry = MAJORITY are returned by the method from the "
                    "relation a + b + carry_in; neither gate is named in the source"}


# What index deconvolution does for each question. BOUNDS is not a softer
# DERIVES: for Q8 the method supplies a measured limit, and the answer itself is
# the direct limb construction. Detail and denominators in paper_certificates.py.
ROLE_LEDGER = {"Q1": "CERTIFIES", "Q2": "DERIVES", "Q3": "CERTIFIES", "Q4": "CERTIFIES",
               "Q5": "DERIVES", "Q6": "DERIVES", "Q7": "DERIVES", "Q8": "BOUNDS"}


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
    q7_full = _check_full_width_q7()
    deconv = _check_deconvolution()
    systems = {"Q5": build_q5(), "Q6": build_q6(), "Q7": build_q7()}
    compile_status = _compile_if_requested(args.output.with_suffix(".compile.json"), systems) if args.compile else {"status": "UNKNOWN", "reason": "not attempted"}
    report = {"status": "PASS", "role_ledger": ROLE_LEDGER,
              "q7_scope": f"width {Q7_WIDTH} built and attacked; exhaustive enumeration "
                          f"at width {q7['width']}, where it is complete",
              "gate_and_blocks": gate, "rows": rows, "q7_exhaustive": q7,
              "q7_full_width": q7_full, "deconvolution": deconv,
              "compile": compile_status, "elapsed_seconds": time.monotonic() - started}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(json.dumps({"status": report["status"], "output": str(args.output),
                      "q7_triples": q7["triples"], "q7_full_width": q7_full["width"],
                      "elapsed_seconds": report["elapsed_seconds"]}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
