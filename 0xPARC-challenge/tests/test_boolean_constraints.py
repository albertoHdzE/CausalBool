import copy
import itertools

import pytest

from oxparc_challenge import FIELD_PRIME as P
from oxparc_challenge.boolean_arithmetic import BooleanDAG, BooleanGate, evaluate_wires
from oxparc_challenge.boolean_constraints import (
    Q6_WIDTH,
    Q7_WIDTH,
    build_q5,
    build_q6,
    build_q7,
    assignment_q7_bits,
    lower_boolean_dag,
    witness_q5,
    witness_q6,
    witness_q7,
)
from oxparc_challenge.circom import export_circom
from oxparc_challenge.constraints import ConstraintSystem
from oxparc_challenge.row_evaluator import check_rows


@pytest.mark.parametrize("kind, arity", [
    ("AND", 2), ("OR", 2), ("XOR", 2), ("NOT", 1),
    ("TRUE", 0), ("FALSE", 0), ("MAJORITY", 3),
])
def test_each_supported_gate_lowers_to_valid_rows(kind, arity):
    dag = BooleanDAG(arity, (BooleanGate(kind, tuple(range(arity))),), (arity,))
    lowered = lower_boolean_dag(dag, [f"input_{i}" for i in range(arity)], prefix="gate")
    system = ConstraintSystem(
        private_inputs=list(lowered.input_signals),
        auxiliary_signals=list(lowered.auxiliary_signals),
        constraints=list(lowered.constraints),
    )
    for bits in itertools.product((0, 1), repeat=arity):
        values = evaluate_wires(dag, bits)
        witness = {name: bit for name, bit in zip(lowered.input_signals, bits)}
        witness["gate_g0"] = values[arity]
        if kind == "MAJORITY":
            a, b, c = bits
            witness.update({
                "gate_g0_and": a & b,
                "gate_g0_xor": a ^ b,
                "gate_g0_cterm": c & (a ^ b),
            })
        assert check_rows(system.to_dict(), witness) == []


@pytest.mark.parametrize("kind, expected", [("OR", None), ("XOR", 0)])
def test_lowering_preserves_repeated_binary_operands(kind, expected):
    dag = BooleanDAG(1, (BooleanGate(kind, (0, 0)),), (1,))
    lowered = lower_boolean_dag(dag, ["input_0"], prefix="repeat")
    system = ConstraintSystem(
        private_inputs=list(lowered.input_signals),
        auxiliary_signals=list(lowered.auxiliary_signals),
        constraints=list(lowered.constraints),
    )
    for bit in (0, 1):
        witness = {"input_0": bit, "repeat_g0": bit if expected is None else expected}
        assert check_rows(system.to_dict(), witness) == []


def test_q5_end_to_end_and_forged_bit():
    system = build_q5()
    for value in (0, 1, (1 << 64) - 1):
        assert check_rows(system.to_dict(), witness_q5(value)) == []
    forged = witness_q5(0)
    forged["x_b0"] = 2
    assert check_rows(system.to_dict(), forged)
    with pytest.raises(ValueError):
        witness_q5(1 << 64)


def test_q6_canonical_bound_exclusion_and_field_alias():
    system = build_q6()
    for value in (0, 2, P - 1):
        assert check_rows(system.to_dict(), witness_q6(value)) == []
    for value in (-1, P, 1, True):
        with pytest.raises(ValueError):
            witness_q6(value)

    # P+1 is representable by 254 bits.  If the scalar is forged as its field
    # alias 1, packing alone would pass; the canonical-less-than-P predicate
    # must still reject the serialized assignment.
    alias = witness_q6(0)
    alias["r"] = 1
    alias.update({f"r_b{i}": ((P + 1) >> i) & 1 for i in range(Q6_WIDTH)})
    assert check_rows(system.to_dict(), alias)

    forged = witness_q6(0)
    forged["r_b0"] = 2
    assert check_rows(system.to_dict(), forged)


def test_q7_exhaustive_width_four_oracle_and_attacks():
    system = build_q7()
    serialized = system.to_dict()
    valid = 0
    for u, v, n in itertools.product(range(1 << Q7_WIDTH), repeat=3):
        expected = u >= 2 and v >= 2 and u * v == n
        failures = check_rows(serialized, assignment_q7_bits(n, u, v))
        if expected:
            valid += 1
            assert failures == []
        else:
            assert failures
    assert valid == 16

    # A full-width product must not be accepted as n=0 by a truncated
    # four-bit product.
    attack = witness_q7(15, 3, 5)
    attack.update({"n": 0, **{f"n_b{i}": 0 for i in range(Q7_WIDTH)}})
    assert check_rows(serialized, attack)

    swapped = witness_q7(15, 5, 3)
    assert check_rows(serialized, swapped) == []
    for name in ("u", "v"):
        forged = witness_q7(15, 3, 5)
        forged[name] = 1
        forged[f"{name}_b0"] = 1
        for bit in range(1, Q7_WIDTH):
            forged[f"{name}_b{bit}"] = 0
        assert check_rows(serialized, forged)

    corrupted = witness_q7(15, 3, 5)
    corrupted["q7_g0"] = 1
    assert check_rows(serialized, corrupted)


def test_q7_width_is_conservatively_bounded():
    assert Q7_WIDTH == 4
    with pytest.raises(ValueError):
        build_q7(5)
    with pytest.raises(ValueError):
        witness_q7(15, 3, 5, 5)


def test_generic_export_reuses_frozen_schema(tmp_path):
    source = export_circom(build_q7(), tmp_path / "q7.circom")
    text = source.read_text(encoding="utf-8")
    assert text.startswith("pragma circom 2.2.3;")
    assert "<--" not in text
    assert "=== " in text
