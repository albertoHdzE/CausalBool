"""The acceptance corpus: eight public, 30 regression, 100 additional, four stress.

Task L02 of ``plan/INDEX_ONLY_PLAN.md``, section 7 T06. Generation is a corpus
producer and is deliberately kept outside the production compiler's dependency
path: nothing in ``direct_compiler`` imports this module.

The 30 regression programs are reproduced by calling the existing generator in
``test_comparison``, not by restating it, so their recorded behaviour is
preserved exactly. That module belongs to the historical hybrid pilot and is
imported here only to generate inputs.

Every generated program is validated with the reference, and its starter-fit
property is checked by confirming the frozen serial baseline compiles it. A
program that fails either check is a generator defect to be fixed and logged;
it is never silently discarded, and no case is dropped because the direct
compiler happens to perform badly on it.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import random
import sys
from typing import Dict, List, Optional, Sequence, Tuple

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / ".reference") not in sys.path:
    sys.path.insert(0, str(ROOT / ".reference"))

import machine  # noqa: E402


__all__ = [
    "FAMILIES",
    "SIZES",
    "public_programs",
    "regression_programs",
    "additional_programs",
    "stress_programs",
    "corpus",
    "corpus_manifest",
    "program_digest",
    "EXPECTED_CORPUS_SIZE",
]


FAMILIES = ("scalar", "vector", "mixed", "dependency", "aliasing")
SIZES = (8, 16, 32, 64)
ADDITIONAL_SEEDS = tuple(range(1000, 1100))
EXPECTED_CORPUS_SIZE = 8 + 30 + 100 + 4


SCALAR_ARITHMETIC = ("add", "sub", "mul", "xor", "and", "or", "shl", "shr", "eq", "lt")
VECTOR_ARITHMETIC = ("vadd", "vsub", "vmul", "vxor", "vand", "vor", "vshl", "vshr")

POOLS: Dict[str, Tuple[str, ...]] = {
    "scalar": ("const", "load") + SCALAR_ARITHMETIC + ("select",),
    "vector": ("vload",) + VECTOR_ARITHMETIC + ("splat", "vselect"),
    "mixed": ("const", "load", "vload")
    + SCALAR_ARITHMETIC
    + VECTOR_ARITHMETIC
    + ("splat", "select", "vselect", "store", "vstore"),
    "dependency": ("const", "load", "vload")
    + SCALAR_ARITHMETIC
    + VECTOR_ARITHMETIC
    + ("splat", "select", "vselect"),
    "aliasing": ("const", "load", "vload", "store", "vstore", "add", "xor", "vadd", "vxor"),
}


class _Builder:
    """Assembles a valid straight-line SSA program one operation at a time.

    The builder refuses any operation whose arguments do not yet exist, and any
    result that would push the unique, vectors-first allocation past the 256
    word scratchpad. The second rule is what preserves the starter-fit property
    for the frozen serial baseline, which allocates every value privately.
    """

    def __init__(self, name: str, buffers: Dict[str, int], rng: random.Random,
                 recent: bool = False) -> None:
        self.name = name
        self.buffers = dict(buffers)
        self.rng = rng
        self.recent = recent
        self.operations: List[dict] = []
        self.available: Dict[str, List[str]] = {"scalar": [], "vector": []}
        self.vector_results = 0
        self.scalar_results = 0

    def _fits(self, kind: Optional[str]) -> bool:
        vectors = self.vector_results + (1 if kind == "vector" else 0)
        scalars = self.scalar_results + (1 if kind == "scalar" else 0)
        return vectors * machine.VLEN + scalars <= machine.SCRATCH_WORDS

    def _pick(self, kind: str) -> str:
        pool = self.available[kind]
        if self.recent:
            # Prefer the newest results, which lengthens the critical path.
            window = pool[-3:]
            return self.rng.choice(window)
        return self.rng.choice(pool)

    def emit(self, opcode: str, offset: Optional[int] = None) -> bool:
        spec = machine.OP_SPECS[opcode]
        if any(not self.available[kind] for kind in spec["args"]):
            return False
        if not self._fits(spec["result"]):
            return False

        operation = {"id": len(self.operations), "op": opcode}
        if spec["args"]:
            operation["args"] = [self._pick(kind) for kind in spec["args"]]
        if opcode == "const":
            operation["value"] = self.rng.randrange(-(1 << 32), 1 << 33)
        if opcode in machine.MEMORY_OPS:
            buffer = self.rng.choice(sorted(self.buffers))
            width = machine.VLEN if opcode in ("vload", "vstore") else 1
            span = self.buffers[buffer] - width
            if span < 0:
                return False
            operation["buffer"] = buffer
            operation["offset"] = (
                min(offset, span) if offset is not None else self.rng.randrange(span + 1)
            )
        if spec["result"]:
            operation["dest"] = "v%d" % len(self.operations)
            self.available[spec["result"]].append(operation["dest"])
            if spec["result"] == "vector":
                self.vector_results += 1
            else:
                self.scalar_results += 1
        self.operations.append(operation)
        return True

    def finish(self, cases: int) -> dict:
        """Close the program with terminating stores and random cases."""

        if self.available["scalar"]:
            self.emit("store")
        if self.available["vector"]:
            self.emit("vstore")
        program = {
            "name": self.name,
            "buffers": dict(self.buffers),
            "operations": self.operations,
            "cases": [
                {
                    buffer: [self.rng.getrandbits(32) for _ in range(length)]
                    for buffer, length in sorted(self.buffers.items())
                }
                for _ in range(cases)
            ],
        }
        machine.validate_program(program)
        return program


# --------------------------------------------------------------------------
# Corpus members
# --------------------------------------------------------------------------


def public_programs() -> List[dict]:
    paths = sorted((ROOT / ".reference" / "programs").glob("*.json"))
    if len(paths) != 8:
        raise RuntimeError(f"expected eight public programs, found {len(paths)}")
    return [machine.load_program(path) for path in paths]


def regression_programs() -> List[dict]:
    """The 30 programs of the historical pilot, from their existing generator."""

    from test_comparison import generated_program

    return [generated_program(seed) for seed in range(30)]


def additional_program(seed: int) -> dict:
    """One additional program. Family is ``seed % 5``; size is ``seed % 4``."""

    family = FAMILIES[seed % 5]
    size = SIZES[seed % 4]
    rng = random.Random(seed)
    buffers = {"data": 32, "out": 32}
    builder = _Builder(
        "additional_%d" % seed, buffers, rng, recent=(family == "dependency")
    )
    # Seed both value pools so that every opcode in the family is reachable.
    builder.emit("const")
    if family != "scalar":
        builder.emit("vload")
    pool = POOLS[family]
    window = 4 if family == "aliasing" else None
    while len(builder.operations) < size:
        opcode = pool[rng.randrange(len(pool))]
        offset = rng.randrange(window) if window is not None else None
        if builder.emit(opcode, offset):
            continue
        # The chosen opcode was refused, either for want of an argument or
        # because a further result would not fit the unique allocation. Stores
        # consume a value without producing one, so they always make progress
        # once the scratchpad is full; a const covers the opposite case.
        if any(builder.emit(fallback, offset) for fallback in ("store", "vstore", "const")):
            continue
        raise RuntimeError(
            f"generator stalled on seed {seed} at {len(builder.operations)} operations"
        )
    return builder.finish(cases=2)


def additional_programs() -> List[dict]:
    return [additional_program(seed) for seed in ADDITIONAL_SEEDS]


def _reverse_consumed(name: str, buffers: Dict[str, int], producers: List[dict],
                      stores: List[dict], cases: int = 1) -> dict:
    """A program whose consumers run in reverse creation order.

    The last value created is consumed first, so the earliest consumer cannot
    issue until every producer has issued. Every result is therefore live at
    that cycle, which is what makes these fixtures test the scratch bound.
    """

    operations = []
    for operation in producers + stores:
        operation = dict(operation)
        operation["id"] = len(operations)
        operations.append(operation)
    rng = random.Random(len(operations))
    program = {
        "name": name,
        "buffers": dict(buffers),
        "operations": operations,
        "cases": [
            {
                buffer: [rng.getrandbits(32) for _ in range(length)]
                for buffer, length in sorted(buffers.items())
            }
            for _ in range(cases)
        ],
    }
    machine.validate_program(program)
    return program


def stress_live_scalars() -> dict:
    """256 scalar results live at once: the scratchpad exactly full."""

    producers = [{"op": "const", "dest": "s%d" % i, "value": i * 7 + 1} for i in range(256)]
    stores = [
        {"op": "store", "args": ["s%d" % i], "buffer": "out", "offset": i}
        for i in reversed(range(256))
    ]
    return _reverse_consumed("stress_live_scalars", {"out": 256}, producers, stores)


def stress_live_vectors() -> dict:
    """32 vector results live at once: 32 times eight words."""

    producers = [
        {"op": "vload", "dest": "v%d" % i, "buffer": "data", "offset": 0} for i in range(32)
    ]
    stores = [
        {"op": "vstore", "args": ["v%d" % i], "buffer": "out", "offset": i * machine.VLEN}
        for i in reversed(range(32))
    ]
    return _reverse_consumed(
        "stress_live_vectors", {"data": 8, "out": 256}, producers, stores
    )


def stress_mixed_pressure() -> dict:
    """16 live vectors beside 128 live scalars, filling scratch exactly."""

    producers = [
        {"op": "vload", "dest": "v%d" % i, "buffer": "data", "offset": 0} for i in range(16)
    ]
    producers += [
        {"op": "const", "dest": "s%d" % i, "value": i * 3 + 2} for i in range(128)
    ]
    stores = [
        {"op": "store", "args": ["s%d" % i], "buffer": "out", "offset": i}
        for i in reversed(range(128))
    ]
    stores += [
        {"op": "vstore", "args": ["v%d" % i], "buffer": "wide", "offset": i * machine.VLEN}
        for i in reversed(range(16))
    ]
    return _reverse_consumed(
        "stress_mixed_pressure", {"data": 8, "out": 128, "wide": 128}, producers, stores
    )


def stress_memory_chain() -> dict:
    """64 ordered overlapping load and store pairs over a small live set."""

    operations = []
    for i in range(64):
        operations.append(
            {"op": "load", "dest": "m%d" % i, "buffer": "data", "offset": i % 8}
        )
        operations.append(
            {"op": "store", "args": ["m%d" % i], "buffer": "data", "offset": i % 8}
        )
    return _reverse_consumed("stress_memory_chain", {"data": 8}, operations, [], cases=2)


def stress_programs() -> List[dict]:
    return [
        stress_live_scalars(),
        stress_live_vectors(),
        stress_mixed_pressure(),
        stress_memory_chain(),
    ]


def corpus() -> List[dict]:
    """All 142 acceptance programs, in a fixed order."""

    programs = (
        public_programs() + regression_programs() + additional_programs() + stress_programs()
    )
    if len(programs) != EXPECTED_CORPUS_SIZE:
        raise RuntimeError(
            f"expected {EXPECTED_CORPUS_SIZE} programs, built {len(programs)}"
        )
    return programs


# --------------------------------------------------------------------------
# Manifest
# --------------------------------------------------------------------------


def program_digest(program: dict) -> str:
    payload = json.dumps(program, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _group_of(index: int) -> str:
    if index < 8:
        return "public"
    if index < 38:
        return "regression"
    if index < 138:
        return "additional"
    return "stress"


def corpus_manifest() -> dict:
    """Seeds, families, cases, hashes, and reference validity for every program.

    The starter-fit check runs the frozen serial baseline. This module is a
    corpus producer, so calling it here is not a compilation path.
    """

    entries = []
    for index, program in enumerate(corpus()):
        group = _group_of(index)
        seed = ADDITIONAL_SEEDS[index - 38] if group == "additional" else None
        machine.validate_program(program)
        baseline = machine.serial_compile(program)
        machine.check_compilation(program, baseline)
        for case in program["cases"]:
            machine.check_case(program, baseline, case)
        entries.append(
            {
                "index": index,
                "group": group,
                "name": program["name"],
                "seed": seed,
                "family": FAMILIES[seed % 5] if seed is not None else None,
                "operations": len(program["operations"]),
                "cases": len(program["cases"]),
                "serial_cycles": len(baseline["bundles"]),
                "serial_scratch": machine.scratch_footprint(program, baseline),
                "reference_valid": True,
                "starter_fits": True,
                "sha256": program_digest(program),
            }
        )
    groups: Dict[str, int] = {}
    for entry in entries:
        groups[entry["group"]] = groups.get(entry["group"], 0) + 1
    return {
        "expected_size": EXPECTED_CORPUS_SIZE,
        "size": len(entries),
        "groups": groups,
        "families": list(FAMILIES),
        "sizes": list(SIZES),
        "additional_seeds": [ADDITIONAL_SEEDS[0], ADDITIONAL_SEEDS[-1]],
        "programs": entries,
    }


if __name__ == "__main__":
    manifest = corpus_manifest()
    json.dump(manifest, sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
