"""Exact shared programs for an ordered synchronous output repertoire.

The fixed interpreter knows N and LSB-first row addresses. Decision paths are
disjoint decimal-anchor/free-mask schemata; skipped coordinates generate
Sumandos. Neither compilation nor serialization expands those families.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import time
from typing import Iterable

CODEC = "shared_repertoire_program_v1"


class ResourceLimitError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProgramLimits:
    max_nodes: int = 1_000_000
    timeout_seconds: float = 300.0


@dataclass(frozen=True)
class RepertoireProgram:
    n: int
    nodes: tuple[tuple[int, int, int], ...]
    outputs: tuple[int, ...]
    allocated_nodes: int = 0


def _integer(value, name, minimum=0):
    if type(value) is not int or value < minimum:
        raise ValueError(f"{name} must be an integer >= {minimum}")
    return value


class _Manager:
    def __init__(self, n, limits):
        self.n = _integer(n, "n", 1)
        self.limits = limits or ProgramLimits()
        _integer(self.limits.max_nodes, "max_nodes")
        if self.limits.timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be positive")
        self.deadline = time.monotonic() + self.limits.timeout_seconds
        self.nodes = []
        self.unique = {}
        self.memo = {}

    def check(self):
        if time.monotonic() > self.deadline:
            raise TimeoutError("symbolic compilation deadline exceeded")

    def mk(self, coordinate, low, high):
        self.check()
        if low == high:
            return low
        key = (coordinate, low, high)
        if key not in self.unique:
            if len(self.nodes) >= self.limits.max_nodes:
                raise ResourceLimitError("decision-node allocation limit exceeded")
            self.unique[key] = len(self.nodes) + 2
            self.nodes.append(key)
        return self.unique[key]

    def apply(self, operation, a, b):
        """Iterative Boolean apply; memoization and unique nodes are global."""
        def key(x, y):
            return (operation, min(x, y), max(x, y))
        root = key(a, b)
        stack = [(root, False)]
        while stack:
            self.check()
            current, ready = stack.pop()
            if current in self.memo:
                continue
            _, x, y = current
            if y < 2:
                self.memo[current] = {"and": x & y, "or": x | y,
                                      "xor": x ^ y}[operation]
                continue
            if x == y:
                self.memo[current] = 0 if operation == "xor" else x
                continue
            if x == 0:
                self.memo[current] = 0 if operation == "and" else y
                continue
            if x == 1 and operation in ("and", "or"):
                self.memo[current] = y if operation == "and" else 1
                continue
            v = min(self.nodes[x-2][0] if x >= 2 else self.n,
                    self.nodes[y-2][0] if y >= 2 else self.n)
            xl, xh = self.nodes[x-2][1:] if x >= 2 and self.nodes[x-2][0] == v else (x, x)
            yl, yh = self.nodes[y-2][1:] if y >= 2 and self.nodes[y-2][0] == v else (y, y)
            left, right = key(xl, yl), key(xh, yh)
            if ready:
                self.memo[current] = self.mk(v, self.memo[left], self.memo[right])
            else:
                stack.extend(((current, True), (right, False), (left, False)))
        return self.memo[root]

    def negate(self, root):
        return self.apply("xor", root, 1)

    def restrict(self, root, coordinate, value):
        """Cofactor of ``root`` with ``coordinate`` fixed to ``value``.

        Coordinates are ordered increasing, so a node labelled above
        ``coordinate`` cannot mention it and is returned unchanged. Because the
        unique table is canonical, the two cofactors are equal as node
        references exactly when the coordinate does not influence the function:
        that identity is the non-exhaustive essential-variable test, costing
        one pass over the diagram rather than 2**n evaluations.
        """
        _integer(coordinate, "coordinate")
        if coordinate >= self.n:
            raise ValueError("coordinate is outside the program")
        if value not in (0, 1):
            raise ValueError("value must be 0 or 1")
        memo = {}
        stack = [(root, False)]
        while stack:
            self.check()
            current, ready = stack.pop()
            if current < 2 or current in memo:
                continue
            v, low, high = self.nodes[current-2]
            if v > coordinate:
                memo[current] = current
            elif v == coordinate:
                memo[current] = high if value else low
            elif ready:
                memo[current] = self.mk(v, memo.get(low, low), memo.get(high, high))
            else:
                stack.extend(((current, True), (high, False), (low, False)))
        return memo.get(root, root)

    def threshold(self, coordinates, threshold):
        if threshold <= 0:
            return 1
        if threshold > len(coordinates):
            return 0
        previous = {}
        for remaining, coordinate in enumerate(reversed(coordinates), 1):
            current = {}
            for k in range(1, min(threshold, remaining) + 1):
                current[k] = self.mk(coordinate, previous.get(k, 0),
                                     1 if k == 1 else previous.get(k-1, 0))
            previous = current
        return previous[threshold]

    def gate(self, gate, coordinates, params):
        d = len(coordinates)
        common = {"noiseFlipProb"}
        allowed = {
            "AND": set(), "OR": set(), "XOR": set(), "NAND": set(),
            "NOR": set(), "XNOR": set(), "NOT": set(), "IMPLIES": set(),
            "NIMPLIES": set(), "MAJORITY": {"tiePolicy"},
            "KOFN": {"k", "strict"},
            "CANALISING": {"canalisingIndex", "canalisingValue", "canalisedOutput"},
        }
        if gate not in allowed:
            raise ValueError(f"unsupported gate: {gate}")
        if not isinstance(params, dict) or set(params) - allowed[gate] - common:
            raise ValueError(f"unsupported parameters for {gate}")
        if params.get("noiseFlipProb", 0) != 0:
            raise ValueError("stochastic gate parameters are not supported")
        if (gate in ("NOT", "CANALISING") and d < 1) or (
                gate in ("IMPLIES", "NIMPLIES") and d < 2):
            raise ValueError(f"invalid arity for {gate}")
        if gate in ("AND", "NAND", "OR", "NOR"):
            root = self.threshold(coordinates, d if gate in ("AND", "NAND") else 1)
            return self.negate(root) if gate in ("NAND", "NOR") else root
        if gate in ("XOR", "XNOR"):
            even, odd = 0, 1
            for v in reversed(coordinates):
                even, odd = self.mk(v, even, odd), self.mk(v, odd, even)
            return odd if gate == "XNOR" else even
        if gate == "MAJORITY":
            policy = params.get("tiePolicy", "strict")
            if policy not in ("strict", "atOrAbove"):
                raise ValueError("invalid majority tiePolicy")
            return self.threshold(coordinates, (d+1)//2 if policy == "atOrAbove" else d//2+1)
        if gate == "KOFN":
            k, strict = params.get("k", 1), params.get("strict", False)
            if type(k) is not int or type(strict) is not bool:
                raise ValueError("KOFN requires integer k and Boolean strict")
            return self.threshold(coordinates, k + int(strict))
        if gate == "NOT":
            return self.mk(coordinates[0], 1, 0)
        if gate in ("IMPLIES", "NIMPLIES"):
            a, b = coordinates[:2]
            return (self.mk(a, 1, self.mk(b, 0, 1)) if gate == "IMPLIES"
                    else self.mk(a, 0, self.mk(b, 1, 0)))
        ci = _integer(params.get("canalisingIndex", 0), "canalisingIndex")
        value, out = params.get("canalisingValue", 1), params.get("canalisedOutput", 0)
        if ci >= d or type(value) is not int or value not in (0, 1) or type(out) is not int or out not in (0, 1):
            raise ValueError("invalid canalising parameters")
        condition = self.mk(coordinates[ci], 1-value, value)
        rest = self.threshold(coordinates, 1)
        return self.apply("or", self.apply("and", condition, out),
                          self.apply("and", self.negate(condition), rest))

    def finish(self, outputs):
        self.check()
        return _canonical(RepertoireProgram(self.n, tuple(self.nodes), tuple(outputs), len(self.nodes)))


def _canonical(program):
    n = _integer(program.n, "n", 1)
    nodes, outputs = program.nodes, program.outputs
    if len(outputs) != n:
        raise ValueError("one ordered output reference per node is required")
    for index, node in enumerate(nodes, 2):
        if len(node) != 3:
            raise ValueError("invalid decision record")
        v, low, high = node
        if _integer(v, "coordinate") >= n or low == high:
            raise ValueError("invalid or redundant decision")
        for child in (low, high):
            if _integer(child, "child") >= index:
                raise ValueError("child must precede parent")
            if child >= 2 and nodes[child-2][0] <= v:
                raise ValueError("inconsistent variable order")
    if len(set(nodes)) != len(nodes):
        raise ValueError("duplicate decision record")
    remap = {0: 0, 1: 1}
    ordered = []
    for root in outputs:
        if _integer(root, "output reference") >= len(nodes) + 2:
            raise ValueError("invalid output reference")
        stack = [(root, False)]
        while stack:
            ref, ready = stack.pop()
            if ref in remap:
                continue
            v, low, high = nodes[ref-2]
            if ready:
                remap[ref] = len(ordered) + 2
                ordered.append((v, remap[low], remap[high]))
            else:
                stack.extend(((ref, True), (high, False), (low, False)))
    return RepertoireProgram(n, tuple(ordered), tuple(remap[r] for r in outputs),
                             program.allocated_nodes)


def compile_repertoire_program(network, *, division_size=2, limits=None):
    """Compile the twelve deterministic gate families without enumerating states."""
    manager = _Manager(network.n, limits)
    _integer(division_size, "division_size", 1)
    if len(network.C) != network.n or len(network.gates) != network.n or len(network.params) != network.n:
        raise ValueError("network dimensions disagree")
    outputs = []
    for start in range(0, network.n, division_size):
        for j in range(start, min(start + division_size, network.n)):
            row = network.C[j]
            if len(row) != network.n or any(type(v) is not int or v not in (0, 1) for v in row):
                raise ValueError("connectivity must be a square binary matrix")
            coordinates = [i for i, bit in enumerate(row) if bit]
            outputs.append(manager.gate(network.gates[j], coordinates, network.params[j]))
    return manager.finish(outputs)


def compile_schema_program(n, output_schemata: Iterable, *, limits=None):
    """Compile per-output unions of (anchor, free_mask), including overlapping cubes."""
    manager = _Manager(n, limits)
    outputs = []
    for schemata in output_schemata:
        root = 0
        for anchor, free in schemata:
            _integer(anchor, "anchor")
            _integer(free, "free_mask")
            if anchor >= 1 << n or free >= 1 << n or anchor & free:
                raise ValueError("anchor and free mask must be disjoint N-bit integers")
            cube = 1
            for v in range(n-1, -1, -1):
                if not (free >> v & 1):
                    cube = manager.mk(v, 0, cube) if anchor >> v & 1 else manager.mk(v, cube, 0)
            root = manager.apply("or", root, cube)
        outputs.append(root)
        if len(outputs) > n:
            raise ValueError("too many output columns")
    return manager.finish(outputs)


def evaluate_program(program, row_index):
    _integer(row_index, "row_index")
    if row_index >= 1 << program.n:
        raise ValueError("row outside repertoire")
    result = []
    for root in program.outputs:
        while root >= 2:
            v, low, high = program.nodes[root-2]
            root = high if row_index >> v & 1 else low
        result.append(root)
    return result


def iter_output_rows(program, start=0, stop=None):
    stop = (1 << program.n) if stop is None else stop
    _integer(start, "start")
    _integer(stop, "stop")
    if not start <= stop <= 1 << program.n:
        raise ValueError("invalid output range")
    for row in range(start, stop):
        yield evaluate_program(program, row)


def export_output_schemata(program, output_index, *, max_schemata=10000):
    _integer(output_index, "output_index")
    _integer(max_schemata, "max_schemata")
    if output_index >= program.n:
        raise ValueError("invalid output index")
    result = []
    stack = [(program.outputs[output_index], 0, 0)]
    while stack:
        ref, anchor, fixed = stack.pop()
        if ref == 0:
            continue
        if ref == 1:
            if len(result) >= max_schemata:
                raise ResourceLimitError("schema export limit exceeded; no complete export returned")
            free = ((1 << program.n)-1) ^ fixed
            result.append((anchor, free))
        else:
            v, low, high = program.nodes[ref-2]
            stack.extend(((high, anchor | 1 << v, fixed | 1 << v),
                          (low, anchor, fixed | 1 << v)))
    return result


def _program_bits(program):
    p = _canonical(program)
    m = len(p.nodes)
    vw, rw = (p.n-1).bit_length(), (m+1).bit_length()
    gamma = bin(m+1)[2:]
    fields = ["0"*(len(gamma)-1) + gamma]
    def field(value, width):
        return format(value, f"0{width}b")[::-1] if width else ""
    for v, low, high in p.nodes:
        fields.extend((field(v, vw), field(low, rw), field(high, rw)))
    fields.extend(field(ref, rw) for ref in p.outputs)
    return "".join(fields)


def serialize_program(program):
    bits = _program_bits(program)
    padded = bits + "0"*(-len(bits) % 8)
    return bytes(int(padded[i:i+8], 2) for i in range(0, len(padded), 8))


def deserialize_program(payload, *, n):
    _integer(n, "n", 1)
    if not isinstance(payload, bytes) or not payload:
        raise ValueError("payload must be nonempty bytes")
    bits = "".join(format(b, "08b") for b in payload)
    z = len(bits) - len(bits.lstrip("0"))
    if 2*z+1 > len(bits):
        raise ValueError("truncated gamma count")
    m = int(bits[z:2*z+1], 2)-1
    pos = 2*z+1
    vw, rw = (n-1).bit_length(), (m+1).bit_length()
    logical = pos + m*(vw+2*rw) + n*rw
    if logical > len(bits) or len(bits)-logical >= 8 or any(b != "0" for b in bits[logical:]):
        raise ValueError("truncated payload or invalid trailing padding")
    def read(width):
        nonlocal pos
        value = int(bits[pos:pos+width][::-1], 2) if width else 0
        pos += width
        return value
    nodes = tuple((read(vw), read(rw), read(rw)) for _ in range(m))
    outputs = tuple(read(rw) for _ in range(n))
    program = RepertoireProgram(n, nodes, outputs, m)
    canonical = _canonical(program)
    if canonical.nodes != nodes or canonical.outputs != outputs:
        raise ValueError("unreachable nodes or noncanonical ordering")
    return program


def program_metadata(program):
    p = _canonical(program)
    bits, payload = _program_bits(p), serialize_program(p)
    m, n = len(p.nodes), p.n
    rw = (m+1).bit_length()
    envelope = {"codec": CODEC, "n": n, "logical_bit_length": len(bits), "payload_hex": payload.hex()}
    digest = hashlib.sha256(json.dumps(envelope, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return {
        "codec": CODEC, "network_size": n, "raw_bit_length": n*(1 << n),
        "program_bit_length": len(bits), "decision_count_bits": 2*(m+1).bit_length()-1,
        "decision_record_bits": m*((n-1).bit_length()+2*rw), "output_reference_bits": n*rw,
        "padding_bits": -len(bits) % 8, "stored_bytes": len(payload),
        "stored_bit_length": 8*len(payload), "reachable_nodes": m,
        "allocated_nodes": p.allocated_nodes, "canonical_program_sha256": digest,
        "input_repertoire_implicit": True, "compiler_materializes_positions": False,
        "compiler_enumerates_states": False, "fixed_decoder_overhead_bits": None,
        "total_declared_program_length_bits": None,
    }
