"""A small, typed Boolean DAG layer for arithmetic experiments.

The historical :class:`BooleanCircuit` API is intentionally MAJ3-only.  This
module is additive: arithmetic circuits use :class:`BooleanDAG` and never
change that API.  Evaluation is deliberately routed through the repository's
``index-deconvolution/src/causalbool.py`` implementation so that Boolean
semantics are not duplicated here.
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import importlib.util
import json
from pathlib import Path
import sys


SUPPORTED_GATES = ("AND", "OR", "XOR", "NOT", "MAJORITY", "TRUE", "FALSE")
_ARITY = {"AND": 2, "OR": 2, "XOR": 2, "NOT": 1, "MAJORITY": 3,
          "TRUE": 0, "FALSE": 0}


@dataclass(frozen=True)
class BooleanGate:
    """One acyclic gate; operands are ordered wire references."""

    kind: str
    operands: tuple[int, ...] = ()

    def validate(self, gate_index: int, n_inputs: int) -> "BooleanGate":
        if type(self.kind) is not str or self.kind not in SUPPORTED_GATES:
            raise ValueError(f"unsupported Boolean gate: {self.kind!r}")
        if type(self.operands) is not tuple or len(self.operands) != _ARITY[self.kind]:
            raise ValueError(f"{self.kind} requires {_ARITY[self.kind]} operands")
        limit = n_inputs + gate_index
        if any(type(ref) is not int or isinstance(ref, bool) or ref < 0 or ref >= limit
               for ref in self.operands):
            raise ValueError("gate operand must reference an earlier wire")
        return self


@dataclass(frozen=True)
class BooleanDAG:
    """A combinational Boolean DAG with stable, integer wire references."""

    n_inputs: int
    gates: tuple[BooleanGate, ...]
    outputs: tuple[int, ...]

    def validate(self) -> "BooleanDAG":
        if type(self.n_inputs) is not int or isinstance(self.n_inputs, bool) or self.n_inputs < 0:
            raise ValueError("n_inputs must be a nonnegative integer")
        if type(self.gates) is not tuple or type(self.outputs) is not tuple:
            raise ValueError("gates and outputs must be tuples")
        for index, gate in enumerate(self.gates):
            if type(gate) is not BooleanGate:
                raise ValueError("gates must be BooleanGate instances")
            gate.validate(index, self.n_inputs)
        limit = self.n_inputs + len(self.gates)
        if any(type(ref) is not int or isinstance(ref, bool) or ref < 0 or ref >= limit
               for ref in self.outputs):
            raise ValueError("output must be a circuit wire")
        return self

    def to_dict(self) -> dict:
        self.validate()
        return {"version": 1, "n_inputs": self.n_inputs,
                "gates": [{"kind": g.kind, "operands": list(g.operands)} for g in self.gates],
                "outputs": list(self.outputs)}

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text: str) -> "BooleanDAG":
        try:
            data = json.loads(text)
            if type(data) is not dict or data.get("version") != 1:
                raise ValueError("unsupported Boolean DAG version")
            gates = tuple(BooleanGate(g["kind"], tuple(g["operands"])) for g in data["gates"])
            return cls(data["n_inputs"], gates, tuple(data["outputs"])).validate()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if str(exc) == "unsupported Boolean DAG version":
                raise
            raise ValueError("invalid Boolean DAG JSON") from exc

    def structural_hash(self) -> str:
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


def _causal_module():
    path = Path(__file__).resolve().parents[3] / "index-deconvolution" / "src" / "causalbool.py"
    name = "_oxparc_causalbool_arithmetic_adapter"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load CausalBool engine: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


def causal_apply_gate(kind: str, inputs: list[int]) -> int:
    """Call the existing CausalBool gate evaluator for one supported gate."""
    if kind not in SUPPORTED_GATES:
        raise ValueError(f"unsupported Boolean gate: {kind!r}")
    result = _causal_module().apply_gate(kind, inputs, {})
    if type(result) is not int or result not in (0, 1):
        raise ValueError("CausalBool returned a non-Boolean result")
    return result


def evaluate_wires(dag: BooleanDAG, bits: list[int] | tuple[int, ...]) -> list[int]:
    """Evaluate every wire in topological order through CausalBool."""
    dag.validate()
    if type(bits) not in (list, tuple) or len(bits) != dag.n_inputs:
        raise ValueError("bits must match n_inputs")
    if any(type(bit) is not int or isinstance(bit, bool) or bit not in (0, 1) for bit in bits):
        raise ValueError("bits must be binary integers")
    wires = list(bits)
    for index, gate in enumerate(dag.gates):
        value = causal_apply_gate(gate.kind, [wires[ref] for ref in gate.operands])
        wires.append(value)
    return wires


def evaluate_boolean_dag(dag: BooleanDAG, bits: list[int] | tuple[int, ...]) -> list[int]:
    wires = evaluate_wires(dag, bits)
    return [wires[ref] for ref in dag.outputs]


class DAGBuilder:
    """Convenience builder that keeps references topological and deterministic."""

    def __init__(self, n_inputs: int):
        if type(n_inputs) is not int or isinstance(n_inputs, bool) or n_inputs < 0:
            raise ValueError("n_inputs must be a nonnegative integer")
        self.n_inputs = n_inputs
        self.gates: list[BooleanGate] = []

    def add(self, kind: str, *operands: int) -> int:
        gate = BooleanGate(kind, tuple(operands))
        gate.validate(len(self.gates), self.n_inputs)
        self.gates.append(gate)
        return self.n_inputs + len(self.gates) - 1

    def finish(self, outputs: tuple[int, ...] | list[int]) -> BooleanDAG:
        return BooleanDAG(self.n_inputs, tuple(self.gates), tuple(outputs)).validate()


# ---------------------------------------------------------------------------
# Recovered cells
#
# The cells below are not written down.  Each is stated as an integer relation,
# its complete finite behaviour is handed to index deconvolution, and the gate
# that comes back is what gets compiled.  For the full adder the method returns
# sum = XOR and carry = MAJORITY without being told either, which is the
# classical identity recovered rather than asserted.
#
# Recovery is cached per cell because it is deterministic: the same behaviour
# always yields the same gates, and the recovery itself is re-checked by the
# tests and by tools/verify_boolean_arithmetic.py.
# ---------------------------------------------------------------------------


def _deconvolution_module():
    path = Path(__file__).resolve().parents[3] / "index-deconvolution" / "src"
    name = "_oxparc_deconvolution_adapter"
    module = sys.modules.get(name)
    if module is None:
        if str(path) not in sys.path:
            sys.path.insert(0, str(path))
        spec = importlib.util.spec_from_file_location(name, path / "deconvolution.py")
        if spec is None or spec.loader is None:
            raise ImportError(f"cannot load the deconvolution engine: {path}")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class RecoveredGate:
    """One output of a cell, as index deconvolution named it."""

    output: int
    connected_inputs: tuple[int, ...]
    gate: str
    params: tuple[tuple[str, object], ...]
    matches: tuple[str, ...]

    def as_dict(self) -> dict:
        return {"output": self.output, "connected_inputs": list(self.connected_inputs),
                "gate": self.gate, "params": dict(self.params),
                "ambiguity_class": list(self.matches)}


_RECOVERY_CACHE: dict[str, tuple[RecoveredGate, ...]] = {}


def recover_cell(label: str, n_inputs: int, outputs) -> tuple[RecoveredGate, ...]:
    """Recover a cell's gates from its behaviour alone.

    ``outputs`` is a sequence of callables mapping an LSB-first input bit list
    to 0 or 1 -- the integer relation the cell is required to satisfy. Nothing
    about gates is supplied. What returns is what the method found.
    """
    if label in _RECOVERY_CACHE:
        return _RECOVERY_CACHE[label]
    engine = _deconvolution_module()
    manager = engine.symbolic_manager(n_inputs)
    recovered = []
    for index, behaviour in enumerate(outputs):
        root = engine.root_from_behaviour(manager, n_inputs, behaviour)
        report = engine.deconvolve_root(manager, root, index)
        recovered.append(RecoveredGate(
            index, tuple(report.connected_inputs), report.canonical.gate,
            tuple(sorted(report.canonical.params.items())),
            tuple(sorted({m.gate for m in report.matches}))))
    result = tuple(recovered)
    _RECOVERY_CACHE[label] = result
    return result


def emit_recovered(builder: "DAGBuilder", recovered: RecoveredGate,
                   input_refs: list[int] | tuple[int, ...]) -> int:
    """Realise one recovered gate using the supported DAG gates.

    A recovered gate names a function of any arity; the DAG layer carries
    binary XOR/AND/OR and ternary MAJORITY. Expansion here is therefore an
    associative fold, and it is verified against the recovered gate by root
    identity in ``tools/verify_boolean_arithmetic.py`` rather than assumed.
    """
    refs = [input_refs[i] for i in recovered.connected_inputs]
    kind = recovered.gate
    if not refs:
        return builder.add("TRUE" if kind == "TRUE" else "FALSE")
    if kind == "MAJORITY" and len(refs) == 3:
        return builder.add("MAJORITY", *refs)
    if kind in ("AND", "OR", "XOR"):
        if len(refs) == 1:
            return refs[0]
        current = refs[0]
        for ref in refs[1:]:
            current = builder.add(kind, current, ref)
        return current
    if kind == "NOT" and len(refs) == 1:
        return builder.add("NOT", refs[0])
    raise ValueError(f"no supported expansion for recovered gate {kind!r} of arity {len(refs)}")


def full_adder_cell() -> tuple[RecoveredGate, ...]:
    """Recover ``(sum, carry)`` from the relation ``a + b + carry_in``."""
    return recover_cell(
        "full_adder", 3,
        (lambda bits: sum(bits) & 1, lambda bits: sum(bits) >> 1))


def partial_product_cell() -> tuple[RecoveredGate, ...]:
    """Recover the one-bit product ``u * v``."""
    return recover_cell("partial_product", 2, (lambda bits: bits[0] * bits[1],))


def build_full_adder_dag() -> BooleanDAG:
    """Return a 3-input full adder with outputs ``(sum, carry)``.

    The two gates are recovered from the integer relation, not written here.
    """
    total_gate, carry_gate = full_adder_cell()
    b = DAGBuilder(3)
    total = emit_recovered(b, total_gate, (0, 1, 2))
    carry = emit_recovered(b, carry_gate, (0, 1, 2))
    return b.finish((total, carry))


def build_multiplier_dag(width: int) -> BooleanDAG:
    """Build an exact ``2*width``-bit shift/add multiplier.

    Inputs are ``u_b0..u_b(width-1), v_b0..v_b(width-1)`` and outputs are the
    complete product, least-significant bit first.  Each addition retains its
    carry wire; no product bit is discarded by construction.
    """
    if type(width) is not int or isinstance(width, bool) or width <= 0:
        raise ValueError("width must be a positive integer")
    total_gate, carry_gate = full_adder_cell()
    product_gate, = partial_product_cell()
    b = DAGBuilder(2 * width)
    zero = b.add("FALSE")
    product = [zero] * (2 * width)
    stage_carries = []
    for j in range(width):
        carry = zero
        for k in range(2 * width):
            addend = (emit_recovered(b, product_gate, (k - j, width + j))
                      if j <= k < j + width else zero)
            # One recovered full adder per column: sum and carry come from the
            # gates deconvolution returned, never from a hand-written pattern.
            operands = (product[k], addend, carry)
            total = emit_recovered(b, total_gate, operands)
            carry = emit_recovered(b, carry_gate, operands)
            product[k] = total
        stage_carries.append(carry)
    # Stage carries are returned as diagnostic outputs after the product.  The
    # arithmetic compiler constrains them to zero in addition to the full
    # product, making the no-truncation boundary explicit.
    return b.finish(tuple(product + stage_carries))


def build_less_than_constant_dag(width: int, bound: int) -> BooleanDAG:
    """Build a little-endian Boolean predicate ``bits < bound``."""
    if type(width) is not int or width <= 0 or type(bound) is not int or not 0 <= bound < (1 << width):
        raise ValueError("invalid width or bound")
    b = DAGBuilder(width)
    false = b.add("FALSE")
    equal = b.add("TRUE")
    less = false
    for bit in reversed(range(width)):
        not_bit = b.add("NOT", bit)
        term = b.add("AND", equal, not_bit) if (bound >> bit) & 1 else false
        less = b.add("OR", less, term)
        equal_bit = bit if (bound >> bit) & 1 else not_bit
        equal = b.add("AND", equal, equal_bit)
    return b.finish((less,))


def build_not_equal_constant_dag(width: int, value: int) -> BooleanDAG:
    """Build the predicate ``little_endian_bits != value``."""
    if type(width) is not int or width <= 0 or type(value) is not int or not 0 <= value < (1 << width):
        raise ValueError("invalid width or value")
    b = DAGBuilder(width)
    different = b.add("FALSE")
    for bit in range(width):
        if (value >> bit) & 1:
            mismatch = b.add("NOT", bit)
        else:
            mismatch = bit
        different = b.add("OR", different, mismatch)
    return b.finish((different,))
