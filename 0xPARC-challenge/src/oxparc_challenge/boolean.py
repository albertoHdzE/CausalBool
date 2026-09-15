"""Sparse majority circuits with a narrow adapter to the CausalBool engine."""

from dataclasses import dataclass
import importlib.util
import json
import math
from pathlib import Path
import sys
import time


class ResourceLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class MAJ3Gate:
    operands: tuple[int, int, int]

    def __post_init__(self):
        if type(self.operands) is not tuple or len(self.operands) != 3:
            raise ValueError("MAJ3Gate requires exactly three operands")


@dataclass(frozen=True)
class BooleanCircuit:
    n_inputs: int
    gates: tuple[MAJ3Gate, ...]
    outputs: tuple[int, ...]

    def validate(self):
        if type(self.n_inputs) is not int or self.n_inputs <= 0:
            raise ValueError("n_inputs must be positive")
        if type(self.gates) is not tuple or type(self.outputs) is not tuple:
            raise ValueError("gates and outputs must be tuples")
        for i, gate in enumerate(self.gates):
            if type(gate) is not MAJ3Gate:
                raise ValueError("gates must be MAJ3Gate instances")
            if any(type(ref) is not int or ref < 0 or ref >= self.n_inputs + i
                   for ref in gate.operands):
                raise ValueError("gate operand is not a prior wire")
        for ref in self.outputs:
            if type(ref) is not int or ref < 0 or ref >= self.n_inputs + len(self.gates):
                raise ValueError("output is not a circuit wire")
        return self

    def to_json(self):
        self.validate()
        payload = {
            "version": 1,
            "n_inputs": self.n_inputs,
            "gates": [{"operands": list(g.operands)} for g in self.gates],
            "outputs": list(self.outputs),
        }
        return json.dumps(payload, sort_keys=True, separators=(",", ":"))

    @classmethod
    def from_json(cls, text):
        try:
            data = json.loads(text)
            if type(data) is not dict:
                raise ValueError("circuit JSON must be an object")
            if type(data.get("version")) is not int or data.get("version") != 1:
                raise ValueError("unsupported circuit version")
            circuit = cls(data["n_inputs"],
                          tuple(MAJ3Gate(tuple(g["operands"])) for g in data["gates"]),
                          tuple(data["outputs"]))
            return circuit.validate()
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            if isinstance(exc, ValueError) and str(exc) == "unsupported circuit version":
                raise
            raise ValueError("invalid circuit JSON") from exc

    def structural_hash(self):
        import hashlib
        return hashlib.sha256(self.to_json().encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class BuildLimits:
    max_gates: int = 1_000_000
    max_subproblems: int = 1_000_000
    timeout_seconds: float = 300

    def validate(self):
        if (type(self.max_gates) is not int or self.max_gates < 0 or
                type(self.max_subproblems) is not int or self.max_subproblems < 0 or
                type(self.timeout_seconds) not in (int, float) or not math.isfinite(self.timeout_seconds) or self.timeout_seconds < 0):
            raise ValueError("invalid build limits")
        return self


def _causal_apply_gate(inputs):
    path = Path(__file__).resolve().parents[3] / "index-deconvolution" / "src" / "causalbool.py"
    name = "_oxparc_causalbool_adapter"
    module = sys.modules.get(name)
    if module is None:
        spec = importlib.util.spec_from_file_location(name, path)
        if spec is None or spec.loader is None:
            raise ImportError("cannot load CausalBool adapter")
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
    return module.apply_gate("MAJORITY", list(inputs), {})


def evaluate_boolean(circuit, bits):
    circuit.validate()
    if type(bits) not in (list, tuple) or len(bits) != circuit.n_inputs:
        raise ValueError("bits must match n_inputs")
    if any(type(bit) is not int or bit not in (0, 1) for bit in bits):
        raise ValueError("bits must be binary integers")
    wires = list(bits)
    for gate in circuit.gates:
        wires.append(_causal_apply_gate([wires[r] for r in gate.operands]))
    return [wires[r] for r in circuit.outputs]


def build_majority(n, limits=None):
    if type(n) is not int or n <= 0 or n % 2 == 0:
        raise ValueError("n must be a positive odd integer")
    if limits is None:
        limits = BuildLimits()
    if type(limits) is not BuildLimits:
        raise ValueError("limits must be BuildLimits")
    limits.validate()
    started = time.monotonic()
    gates = []
    subproblems = 0
    memo = {}

    def solve(weights, refs):
        nonlocal subproblems
        if time.monotonic() - started > limits.timeout_seconds:
            raise ResourceLimitError('build timeout exceeded')
        key = weights
        if key in memo:
            return memo[key]
        subproblems += 1
        if subproblems > limits.max_subproblems:
            raise ResourceLimitError("build resource limit exceeded")
        active = [i for i, weight in enumerate(weights) if weight]
        total = sum(weights)
        if len(active) <= 2:
            result = max(active, key=lambda i: weights[i])
            memo[key] = refs[result]
            return refs[result]
        for i in active:
            if weights[i] * 2 > total:
                memo[key] = refs[i]
                return refs[i]
        a, b, c = active[:3]
        children = []
        for keep, drop in ((a, b), (b, c), (c, a)):
            child_weights = list(weights)
            child_refs = list(refs)
            child_weights[keep] += child_weights[drop]
            child_weights[drop] = 0
            children.append(solve(tuple(child_weights), tuple(child_refs)))
        if len(gates) >= limits.max_gates:
            raise ResourceLimitError("build resource limit exceeded")
        if time.monotonic() - started > limits.timeout_seconds:
            raise ResourceLimitError("build timeout exceeded")
        gates.append(MAJ3Gate(tuple(children)))
        result = n + len(gates) - 1
        memo[key] = result
        return result

    try:
        output = solve((1,) * n, tuple(range(n)))
    except RecursionError as exc:
        raise ResourceLimitError('Python recursion budget exceeded; no circuit returned') from exc
    return BooleanCircuit(n, tuple(gates), (output,)).validate()


def verify_majority(circuit, limits=None):
    from .symbolic import verify_majority as _verify_majority
    return _verify_majority(circuit, limits)
