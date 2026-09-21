import itertools

import pytest

from oxparc_challenge.boolean_arithmetic import (
    BooleanDAG,
    BooleanGate,
    build_full_adder_dag,
    build_less_than_constant_dag,
    build_multiplier_dag,
    evaluate_boolean_dag,
    evaluate_wires,
)


def test_dag_contract_and_round_trip():
    dag = BooleanDAG(2, (BooleanGate("XOR", (0, 1)),), (2,))
    assert BooleanDAG.from_json(dag.to_json()) == dag
    assert len(dag.structural_hash()) == 64
    assert evaluate_boolean_dag(dag, [0, 1]) == [1]
    assert evaluate_boolean_dag(dag, [1, 1]) == [0]


@pytest.mark.parametrize("bad", [
    BooleanDAG(2, (BooleanGate("NOPE", (0, 1)),), (2,)),
    BooleanDAG(2, (BooleanGate("AND", (0, 2)),), (2,)),
    BooleanDAG(2, (BooleanGate("NOT", (0, 1)),), (2,)),
])
def test_malformed_or_unsupported_dag_rejected(bad):
    with pytest.raises(ValueError):
        bad.validate()


def test_constants_repeated_operands_and_fanout():
    dag = BooleanDAG(2, (
        BooleanGate("TRUE"),
        BooleanGate("FALSE"),
        BooleanGate("AND", (0, 0)),
        BooleanGate("OR", (2, 3)),
        BooleanGate("XOR", (4, 4)),
    ), (2, 3, 4, 5, 6))
    assert evaluate_boolean_dag(dag, [1, 0]) == [1, 0, 1, 1, 0]


def test_full_adder_exhaustive():
    dag = build_full_adder_dag()
    for a, b, c in itertools.product((0, 1), repeat=3):
        assert evaluate_boolean_dag(dag, [a, b, c]) == [(a + b + c) & 1, (a + b + c) >> 1]


@pytest.mark.parametrize("width", [1, 2, 3, 4])
def test_multiplier_is_full_width_and_exact(width):
    dag = build_multiplier_dag(width)
    for u in range(1 << width):
        for v in range(1 << width):
            bits = [(u >> i) & 1 for i in range(width)] + [(v >> i) & 1 for i in range(width)]
            outputs = evaluate_boolean_dag(dag, bits)
            product = sum(bit << i for i, bit in enumerate(outputs[:2 * width]))
            assert product == u * v
            assert outputs[2 * width:] == [0] * width


def test_bounded_comparison_exhaustive_and_input_validation():
    dag = build_less_than_constant_dag(4, 11)
    for value in range(16):
        assert evaluate_boolean_dag(dag, [(value >> i) & 1 for i in range(4)]) == [int(value < 11)]
    with pytest.raises(ValueError):
        evaluate_wires(dag, [0, 0, 2, 0])
    with pytest.raises(ValueError):
        evaluate_wires(dag, [0, 0, 0])
