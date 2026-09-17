"""Lower Boolean DAGs into the frozen quadratic-row representation.

Every signal is explicitly bit-constrained.  The returned systems are ordinary
``ConstraintSystem`` objects and therefore use the existing serializer,
serialized-row evaluator, and generic Circom exporter without a parallel
constraint format.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import re

from . import FIELD_PRIME
from .boolean_arithmetic import (BooleanDAG, DAGBuilder, build_less_than_constant_dag,
                                 build_multiplier_dag, build_not_equal_constant_dag,
                                 evaluate_wires)
from .constraints import ConstraintSystem, LinearExpression, QuadraticConstraint


_P = FIELD_PRIME
Q7_WIDTH = 64  # The question's width. Small widths remain buildable for exhaustive checks.
Q6_WIDTH = _P.bit_length()


def _l(constant: int = 0, terms: dict[str, int] | None = None, **kwargs: int) -> LinearExpression:
    values = dict(terms or {})
    values.update(kwargs)
    return LinearExpression(constant=constant, terms=values)


def _row(a: LinearExpression, b: LinearExpression, c: LinearExpression, label: str) -> QuadraticConstraint:
    return QuadraticConstraint(a, b, c, label)


def _sum_terms(*terms: tuple[str, int]) -> dict[str, int]:
    """Combine repeated signal names instead of overwriting coefficients."""
    result: dict[str, int] = {}
    for name, coefficient in terms:
        result[name] = result.get(name, 0) + coefficient
    return {name: coefficient for name, coefficient in result.items() if coefficient}


def _assert_bit(name: str, label: str) -> QuadraticConstraint:
    return _row(_l(terms={name: 1}), _l(-1, terms={name: 1}), _l(), label)


def _assert_one(name: str, label: str) -> QuadraticConstraint:
    return _row(_l(1), _l(terms={name: 1}), _l(1), label)


def _assert_zero(name: str, label: str) -> QuadraticConstraint:
    return _row(_l(1), _l(terms={name: 1}), _l(), label)


def _equal(left: str, right: str, label: str) -> QuadraticConstraint:
    return _row(_l(1), _l(terms={left: 1, right: -1}), _l(), label)


def _pack(signal: str, bits: list[str], label: str) -> QuadraticConstraint:
    return _row(_l(1), _l(terms={signal: 1}),
                _l(terms={bit: 1 << index for index, bit in enumerate(bits)}), label)


@dataclass(frozen=True)
class BooleanLowering:
    """Rows and names emitted for one DAG, retained for diagnosis."""

    input_signals: tuple[str, ...]
    wire_signals: tuple[str, ...]
    auxiliary_signals: tuple[str, ...]
    constraints: tuple[QuadraticConstraint, ...]
    rows_by_gate: tuple[tuple[str, ...], ...]
    # Rules for the auxiliaries a gate needs beyond its own output wire, paired
    # with the names at the point those names are minted. Witness builders used
    # to re-derive the naming convention themselves, which silently produced
    # incomplete assignments the moment a gate grew an extra auxiliary.
    aux_rules: tuple[tuple[str, object], ...] = ()

    def assignment(self, dag: BooleanDAG, bits: list[int] | tuple[int, ...]) -> dict[str, int]:
        """Value every signal this lowering generated, from the input bits."""
        values = evaluate_wires(dag, bits)
        result = {name: values[index] for index, name in enumerate(self.wire_signals)}
        for name, rule in self.aux_rules:
            result[name] = rule(result)
        return result


@lru_cache(maxsize=None)
def _cached_lowering(dag: BooleanDAG, input_signals: tuple[str, ...], prefix: str) -> BooleanLowering:
    """Lowering of a fixed DAG under fixed names; pure, so it is cached.

    Witness tracing asks for the same lowering once per assignment, and an
    exhaustive sweep asks millions of times.
    """
    return lower_boolean_dag(dag, list(input_signals), prefix=prefix)


def _signal_ok(name: str) -> bool:
    return type(name) is str and re.fullmatch(r"[A-Za-z][A-Za-z0-9_]*", name) is not None


def lower_boolean_dag(dag: BooleanDAG, input_signals: list[str] | tuple[str, ...],
                      *, prefix: str = "bool", constrain_inputs: bool = True) -> BooleanLowering:
    """Lower a DAG, preserving a gate-to-row label map.

    Inputs are existing signal names; every generated gate/internal wire is an
    auxiliary signal.  All gate refs are prior refs, so cycles and malformed
    refs are rejected by ``BooleanDAG.validate`` before rows are emitted.
    """
    dag.validate()
    if type(input_signals) not in (list, tuple) or len(input_signals) != dag.n_inputs:
        raise ValueError("input_signals must match DAG inputs")
    if not _signal_ok(prefix):
        raise ValueError("prefix must be a valid signal-name prefix")
    names = tuple(input_signals)
    if any(not _signal_ok(name) for name in names) or len(set(names)) != len(names):
        raise ValueError("input signals must be unique valid names")

    wire_signals = list(names)
    auxiliary: list[str] = []
    rows: list[QuadraticConstraint] = []
    rows_by_gate: list[list[str]] = []
    aux_rules: list[tuple[str, object]] = []

    def fresh(suffix: str) -> str:
        name = f"{prefix}_{suffix}"
        if name in wire_signals or name in auxiliary:
            raise ValueError(f"generated signal collides with input: {name}")
        auxiliary.append(name)
        return name

    if constrain_inputs:
        for index, name in enumerate(names):
            rows.append(_assert_bit(name, f"input_bit_{index}"))

    def add(row: QuadraticConstraint, gate_rows: list[str]) -> None:
        rows.append(row)
        gate_rows.append(row.label)

    for index, gate in enumerate(dag.gates):
        gate_rows: list[str] = []
        args = [wire_signals[ref] for ref in gate.operands]
        out = fresh(f"g{index}")
        wire_signals.append(out)
        if gate.kind == "AND":
            add(_row(_l(terms={args[0]: 1}), _l(terms={args[1]: 1}), _l(terms={out: 1}),
                     f"gate_{index}_and"), gate_rows)
        elif gate.kind == "OR":
            add(_row(_l(terms={args[0]: 1}), _l(terms={args[1]: 1}),
                     _l(terms=_sum_terms((args[0], 1), (args[1], 1), (out, -1))),
                     f"gate_{index}_or"), gate_rows)
        elif gate.kind == "XOR":
            add(_row(_l(terms={args[0]: 2}), _l(terms={args[1]: 1}),
                     _l(terms=_sum_terms((args[0], 1), (args[1], 1), (out, -1))),
                     f"gate_{index}_xor"), gate_rows)
        elif gate.kind == "NOT":
            add(_row(_l(1), _l(1, terms={args[0]: -1}), _l(terms={out: 1}),
                     f"gate_{index}_not"), gate_rows)
        elif gate.kind == "TRUE":
            add(_row(_l(1), _l(1), _l(terms={out: 1}), f"gate_{index}_true"), gate_rows)
        elif gate.kind == "FALSE":
            add(_row(_l(1), _l(terms={out: 1}), _l(), f"gate_{index}_false"), gate_rows)
        elif gate.kind == "MAJORITY":
            # MAJ(a,b,c) = (a AND b) OR (c AND (a XOR b)); all auxiliaries
            # are explicitly constrained and bit-constrained below.
            ab = fresh(f"g{index}_and")
            axb = fresh(f"g{index}_xor")
            cterm = fresh(f"g{index}_cterm")
            # Value rules beside the names, so a witness can never omit them.
            aux_rules.extend((
                (ab, lambda w, x=args[0], y=args[1]: w[x] & w[y]),
                (axb, lambda w, x=args[0], y=args[1]: w[x] ^ w[y]),
                (cterm, lambda w, z=args[2], t=axb: w[z] & w[t]),
            ))
            add(_row(_l(terms={args[0]: 1}), _l(terms={args[1]: 1}), _l(terms={ab: 1}),
                     f"gate_{index}_and"), gate_rows)
            add(_row(_l(terms={args[0]: 2}), _l(terms={args[1]: 1}),
                     _l(terms={args[0]: 1, args[1]: 1, axb: -1}), f"gate_{index}_xor"), gate_rows)
            add(_row(_l(terms={args[2]: 1}), _l(terms={axb: 1}), _l(terms={cterm: 1}),
                     f"gate_{index}_cterm"), gate_rows)
            add(_row(_l(terms={ab: 1}), _l(terms={cterm: 1}),
                     _l(terms={ab: 1, cterm: 1, out: -1}), f"gate_{index}_or"), gate_rows)
        else:  # defensive; BooleanDAG.validate already rejects this.
            raise ValueError(f"unsupported Boolean gate: {gate.kind!r}")
        for signal in wire_signals[-1:] + ([ab, axb, cterm] if gate.kind == "MAJORITY" else []):
            add(_assert_bit(signal, f"gate_{index}_{signal}_bit"), gate_rows)
        rows_by_gate.append(gate_rows)

    return BooleanLowering(names, tuple(wire_signals), tuple(auxiliary), tuple(rows),
                           tuple(tuple(group) for group in rows_by_gate), tuple(aux_rules))


def _system(public: list[str], private: list[str], auxiliary: list[str],
            rows: list[QuadraticConstraint]) -> ConstraintSystem:
    return ConstraintSystem(prime=_P, public_inputs=public, private_inputs=private,
                            auxiliary_signals=auxiliary, constraints=rows).validate()


def _bits(value: int, width: int, prefix: str) -> dict[str, int]:
    return {f"{prefix}_b{index}": (value >> index) & 1 for index in range(width)}


def _integer(value: int, name: str) -> int:
    if type(value) is not int or isinstance(value, bool):
        raise ValueError(f"{name} must be an integer")
    return value


Q5_BOUND = 1 << 64
# One wider than the bound, so the comparator is doing real work: a decomposition
# of this width can represent values at or above the bound, and only the
# recovered comparator excludes them. A 64-wide decomposition would make the
# predicate vacuously true and prove nothing.
Q5_WIDTH = Q5_BOUND.bit_length()


@lru_cache(maxsize=None)
def _q5_dag() -> BooleanDAG:
    return build_less_than_constant_dag(Q5_WIDTH, Q5_BOUND)


def build_q5() -> ConstraintSystem:
    """Scalar range relation (Q5): ``x`` lies in ``[0, 2**64)``.

    Built from the recovered comparator, so the bound is general rather than a
    power of two that a bit count would settle on its own.
    """
    bits = [f"x_b{i}" for i in range(Q5_WIDTH)]
    dag = _q5_dag()
    lowered = lower_boolean_dag(dag, bits, prefix="q5")
    below = lowered.wire_signals[dag.outputs[0]]
    return _system([], ["x"], bits + list(lowered.auxiliary_signals),
                   list(lowered.constraints) +
                   [_pack("x", bits, "x_pack"), _assert_one(below, "range_below_bound")])


def witness_q5(x: int) -> dict[str, int]:
    x = _integer(x, "x")
    if not 0 <= x < Q5_BOUND:
        raise ValueError("x must be a 64-bit nonnegative integer")
    return assignment_q5_bits(x, [(x >> i) & 1 for i in range(Q5_WIDTH)])


def assignment_q5_bits(scalar: int, bits: list[int] | tuple[int, ...]) -> dict[str, int]:
    """Trace a complete Q5 assignment without asserting the range relation.

    Separate from :func:`witness_q5` so a reviewer can submit an out-of-range
    decomposition straight to the serialized rows and watch them reject it.
    """
    scalar = _integer(scalar, "scalar")
    if type(bits) not in (list, tuple) or len(bits) != Q5_WIDTH:
        raise ValueError("Q5 bit vector is invalid")
    if any(type(bit) is not int or isinstance(bit, bool) or bit not in (0, 1) for bit in bits):
        raise ValueError("Q5 bits must be binary integers")
    dag = _q5_dag()
    lowered = _cached_lowering(dag, tuple(f"x_b{i}" for i in range(Q5_WIDTH)), "q5")
    return {"x": scalar, **lowered.assignment(dag, list(bits))}


def _append_dag(left: DAGBuilder, right: BooleanDAG, input_refs: list[int]) -> list[int]:
    """Append right's gates to left, translating its input refs."""
    right.validate()
    if len(input_refs) != right.n_inputs:
        raise ValueError("DAG input reference mismatch")
    translated = list(input_refs)
    for gate in right.gates:
        translated.append(left.add(gate.kind, *(translated[ref] for ref in gate.operands)))
    return [translated[ref] for ref in right.outputs]


@lru_cache(maxsize=None)
def _q6_dag() -> BooleanDAG:
    b = DAGBuilder(Q6_WIDTH)
    lt = _append_dag(b, build_less_than_constant_dag(Q6_WIDTH, _P), list(range(Q6_WIDTH)))[0]
    neq = _append_dag(b, build_not_equal_constant_dag(Q6_WIDTH, 1), list(range(Q6_WIDTH)))[0]
    return b.finish((lt, neq))


def build_q6() -> ConstraintSystem:
    """Canonical field-element exclusion relation (Q6), compiled from gates."""
    bits = [f"r_b{i}" for i in range(Q6_WIDTH)]
    dag = _q6_dag()
    lowered = lower_boolean_dag(dag, bits, prefix="q6")
    lt, neq = (lowered.wire_signals[ref] for ref in dag.outputs)
    rows = list(lowered.constraints)
    rows.extend([_pack("r", bits, "r_pack"), _assert_one(lt, "canonical_lt_prime"),
                 _assert_one(neq, "exclude_one_boolean")])
    return _system([], ["r"], bits + list(lowered.auxiliary_signals), rows)


def witness_q6(r: int) -> dict[str, int]:
    r = _integer(r, "r")
    if not 0 <= r < _P or r == 1:
        raise ValueError("r must be canonical, below the field prime, and different from one")
    return assignment_q6_bits(r, [(r >> i) & 1 for i in range(Q6_WIDTH)])


def assignment_q6_bits(scalar: int, bits: list[int] | tuple[int, ...]) -> dict[str, int]:
    """Trace a complete Q6 assignment without asserting its relation.

    This is intentionally separate from :func:`witness_q6` and exists so
    reviewers can submit internally consistent forged decompositions directly
    to serialized rows (for example the ``P+1``/scalar-1 alias).
    """
    scalar = _integer(scalar, "scalar")
    if not 0 <= scalar < _P or type(bits) not in (list, tuple) or len(bits) != Q6_WIDTH:
        raise ValueError("scalar or Q6 bit vector is invalid")
    if any(type(bit) is not int or isinstance(bit, bool) or bit not in (0, 1) for bit in bits):
        raise ValueError("Q6 bits must be binary integers")
    dag = _q6_dag()
    lowered = _cached_lowering(dag, tuple(f"r_b{i}" for i in range(Q6_WIDTH)), "q6")
    return {"r": scalar, **lowered.assignment(dag, list(bits))}


def _width(width: int) -> int:
    """A Q7 width must be a positive integer; the question asks for 64."""
    if type(width) is not int or isinstance(width, bool) or width < 2:
        raise ValueError("Q7 width must be an integer of at least two")
    return width


@lru_cache(maxsize=None)
def _q7_lower_dag(width: int) -> BooleanDAG:
    """OR of bits 1..width-1: the Boolean predicate ``value >= 2``."""
    builder = DAGBuilder(width)
    nontrivial = builder.add("FALSE")
    for bit in range(1, width):
        nontrivial = builder.add("OR", nontrivial, bit)
    return builder.finish((nontrivial,))


@lru_cache(maxsize=None)
def _q7_dag(width: int) -> BooleanDAG:
    multiplier = build_multiplier_dag(width)
    b = DAGBuilder(2 * width)
    refs = _append_dag(b, multiplier, list(range(2 * width)))
    # Product bits are first; stage carries follow and are all required zero.
    return b.finish(refs)


def build_q7(width: int = Q7_WIDTH) -> ConstraintSystem:
    """Factor-verification relation at ``width`` bits, from the recovered cells."""
    width = _width(width)
    product_width = 2 * width
    nbits = [f"n_b{i}" for i in range(width)]
    ubits = [f"u_b{i}" for i in range(width)]
    vbits = [f"v_b{i}" for i in range(width)]
    inputs = ubits + vbits
    dag = _q7_dag(width)
    lowered = lower_boolean_dag(dag, inputs, prefix="q7")
    rows = list(lowered.constraints)
    product = [lowered.wire_signals[ref] for ref in dag.outputs[:product_width]]
    stage_carries = [lowered.wire_signals[ref] for ref in dag.outputs[product_width:]]
    rows.extend(_equal(product[i], nbits[i], f"product_low_{i}") for i in range(width))
    rows.extend(_assert_zero(product[i], f"product_high_{i}") for i in range(width, product_width))
    rows.extend(_assert_zero(carry, f"stage_carry_zero_{i}") for i, carry in enumerate(stage_carries))
    rows.extend(_assert_bit(bit, f"public_n_bit_{i}") for i, bit in enumerate(nbits))
    lower_dag = _q7_lower_dag(width)
    lower = lower_boolean_dag(lower_dag, ubits, prefix="q7_u")
    lower_v = lower_boolean_dag(lower_dag, vbits, prefix="q7_v")
    rows.extend(lower.constraints)
    rows.extend(lower_v.constraints)
    rows.extend([_assert_one(lower.wire_signals[-1], "factor_u_ge_two"),
                 _assert_one(lower_v.wire_signals[-1], "factor_v_ge_two")])
    auxiliary = (nbits + ubits + vbits + list(lowered.auxiliary_signals) +
                 list(lower.auxiliary_signals) + list(lower_v.auxiliary_signals))
    return _system(["n"], ["u", "v"], auxiliary, rows +
                   [_pack("u", ubits, "u_pack"), _pack("v", vbits, "v_pack"),
                    _pack("n", nbits, "n_pack")])


def witness_q7(n: int, u: int, v: int, width: int = Q7_WIDTH) -> dict[str, int]:
    width = _width(width)
    n, u, v = (_integer(n, "n"), _integer(u, "u"), _integer(v, "v"))
    limit = 1 << width
    if not (0 <= n < limit and 2 <= u < limit and 2 <= v < limit and u * v == n):
        raise ValueError("n, u, and v must be valid bounded factorization values")
    return assignment_q7_bits(n, u, v, width)


def assignment_q7_bits(n: int, u: int, v: int, width: int = Q7_WIDTH) -> dict[str, int]:
    """Trace a complete bounded Q7 assignment without relation assertions."""
    width = _width(width)
    n, u, v = (_integer(n, "n"), _integer(u, "u"), _integer(v, "v"))
    limit = 1 << width
    if not (0 <= n < limit and 0 <= u < limit and 0 <= v < limit):
        raise ValueError("Q7 scalar values must fit the bounded width")
    ubits = [f"u_b{i}" for i in range(width)]
    vbits = [f"v_b{i}" for i in range(width)]
    uvec = [(u >> i) & 1 for i in range(width)]
    vvec = [(v >> i) & 1 for i in range(width)]
    dag = _q7_dag(width)
    lowered = _cached_lowering(dag, tuple(ubits + vbits), "q7")
    result = {"n": n, "u": u, "v": v}
    result.update(_bits(n, width, "n"))
    result.update(lowered.assignment(dag, uvec + vvec))
    # The two lower-bound DAGs have their own generated signals; each is
    # assigned through the lowering that minted those names.
    lower_dag = _q7_lower_dag(width)
    result.update(_cached_lowering(lower_dag, tuple(ubits), "q7_u").assignment(lower_dag, uvec))
    result.update(_cached_lowering(lower_dag, tuple(vbits), "q7_v").assignment(lower_dag, vvec))
    return result


# Explicit names make the Q-number mapping discoverable without disturbing the
# historical gadgets.py API.
build_boolean_range = build_q5
witness_boolean_range = witness_q5
build_boolean_exclude_one = build_q6
witness_boolean_exclude_one = witness_q6
build_boolean_factor = build_q7
witness_boolean_factor = witness_q7
