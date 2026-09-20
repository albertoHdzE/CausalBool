"""Machine facts derived independently for the direct-index compiler.

This module owns the derived view of a program that the direct compiler needs:
producers, consumers, dependencies, widths, lifetimes, bundle assembly,
footprints, horizons, and lower bounds. It is task L02 of
``plan/INDEX_ONLY_PLAN.md``.

Ownership notes, under the repository's single-owner rule:

* The pinned ``machine`` module remains the owner of every hardware fact:
  ``OP_SPECS``, ``ENGINE_LIMITS``, ``VLEN``, ``SCRATCH_WORDS``,
  ``producer_map``, ``result_kinds``, ``memory_width`` and
  ``memory_predecessors``. Those are imported, never restated.
* ``common.py`` derives some of the same quantities for the frozen classical
  arm. That file is pinned by hash and may not be changed, and plan section 5.1
  bars the production path from importing it. The two owners therefore coexist
  by declared exception rather than by collapse. ``tests_direct/test_contract``
  measures their agreement elementwise, and ``tests_direct/test_independence``
  keeps the import boundary shut.

Nothing here allocates or schedules, and nothing here calls a baseline
compiler. ``machine.serial_compile`` is never invoked.
"""

from __future__ import annotations

from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import machine


__all__ = [
    "ADDRESS_WIDTH",
    "ProgramFacts",
    "derive",
    "lifetimes",
    "assemble_bundles",
    "compilation",
    "footprint",
    "cycle_count",
    "engine_usage",
    "time_width",
    "check_feasible",
    "ContractError",
]


# The scratchpad holds 256 words of 32 bits each, so a word address needs
# eight bits. This is an address width, not a count of bits of scratch.
ADDRESS_WIDTH = 8


class ContractError(ValueError):
    """A derived fact was violated by a candidate schedule or allocation."""


class ProgramFacts:
    """An immutable derived view of one program.

    The input dictionary is read and never modified. Operation identifiers are
    used only for deterministic ordering, never to recognise a particular
    program.
    """

    __slots__ = (
        "program",
        "operations",
        "count",
        "opcode",
        "engine",
        "latency",
        "dest",
        "kind",
        "producers",
        "consumers",
        "value_names",
        "width",
        "data_predecessors",
        "memory_predecessors",
        "predecessors",
        "successors",
        "horizon",
        "_heights",
    )

    def __init__(self, program: dict) -> None:
        machine.validate_program(program)
        operations = program["operations"]
        count = len(operations)

        self.program = program
        self.operations = tuple(operations)
        self.count = count
        self.opcode = tuple(op["op"] for op in operations)
        self.engine = tuple(machine.OP_SPECS[code]["engine"] for code in self.opcode)
        self.latency = tuple(machine.OP_SPECS[code]["latency"] for code in self.opcode)
        self.dest = tuple(op.get("dest") for op in operations)
        self.kind = tuple(machine.OP_SPECS[code]["result"] for code in self.opcode)

        self.producers = dict(machine.producer_map(program))
        kinds = machine.result_kinds(program)
        self.value_names = tuple(
            op["dest"] for op in operations if machine.OP_SPECS[op["op"]]["result"]
        )
        self.width = {
            name: machine.VLEN if kinds[name] == "vector" else 1 for name in self.value_names
        }

        # An operation that reads a value for two arguments is one consumer,
        # not two: this is the set of consuming operations, in issue-id order.
        consumers: Dict[str, List[int]] = {name: [] for name in self.value_names}
        for op in operations:
            for arg in dict.fromkeys(op.get("args", [])):
                consumers[arg].append(op["id"])
        self.consumers = {name: tuple(ids) for name, ids in consumers.items()}

        data: List[Tuple[Tuple[int, int], ...]] = []
        memory: List[Tuple[int, ...]] = []
        combined: List[Dict[int, int]] = []
        for op in operations:
            incoming: Dict[int, int] = {}
            pairs = []
            for arg in op.get("args", []):
                producer = self.producers[arg]
                lag = self.latency[producer]
                pairs.append((producer, lag))
                # A producer feeding two arguments contributes its latency once.
                incoming[producer] = max(incoming.get(producer, 0), lag)
            ordered = tuple(sorted(set(pairs)))
            data.append(ordered)

            earlier = tuple(machine.memory_predecessors(program, op["id"]))
            memory.append(earlier)
            for predecessor in earlier:
                incoming[predecessor] = max(incoming.get(predecessor, 0), 1)
            combined.append(dict(sorted(incoming.items())))
        self.data_predecessors = tuple(data)
        self.memory_predecessors = tuple(memory)
        self.predecessors = tuple(combined)

        successors: List[List[Tuple[int, int]]] = [[] for _ in range(count)]
        for op_id, incoming in enumerate(combined):
            for predecessor, lag in incoming.items():
                successors[predecessor].append((op_id, lag))
        self.successors = tuple(tuple(sorted(items)) for items in successors)

        # A safe issue-time horizon: every latency is at least one, so placing
        # each operation after the sum of all earlier latencies is always legal.
        self.horizon = sum(self.latency)

        heights = [0] * count
        for op_id in reversed(range(count)):
            heights[op_id] = max(
                (lag + heights[successor] for successor, lag in self.successors[op_id]),
                default=0,
            )
        self._heights = tuple(heights)

    # -- derived quantities -------------------------------------------------

    @property
    def heights(self) -> Tuple[int, ...]:
        """Longest remaining dependency lag from each operation."""

        return self._heights

    def prefix_horizon(self, op_id: int) -> int:
        """``h_i``: the sum of latencies of the operations preceding ``op_id``.

        Section 5.2's construction argument uses this value. Every earlier
        chosen time is at most its own ``h_j``, and ``h_j < h_i`` because every
        latency is positive, so ``h_i`` is always a feasible extension.
        """

        return sum(self.latency[:op_id])

    def dependency_lower_bound(self) -> int:
        """Fewest bundles the dependency graph alone permits."""

        return max(self._heights, default=0) + 1 if self.count else 0

    def engine_lower_bound(self) -> int:
        """Fewest bundles the per-cycle issue capacity alone permits."""

        counts: Dict[str, int] = {}
        for engine in self.engine:
            counts[engine] = counts.get(engine, 0) + 1
        return max(
            (-(-total // machine.ENGINE_LIMITS[engine]) for engine, total in counts.items()),
            default=0,
        )

    def cycle_lower_bound(self) -> int:
        return max(self.dependency_lower_bound(), self.engine_lower_bound())

    def memory_lower_bound(self) -> int:
        """A basic footprint bound: the widest single result must fit."""

        return max(self.width.values(), default=0)

    def unique_allocation_width(self) -> int:
        """Words used when every value is given private, aligned space.

        Vectors are placed first so that no scalar introduces alignment
        padding. Reuse can only lower the high-water mark, so this is an upper
        bound on what the bootstrap allocation needs.
        """

        cursor = 0
        for name in self.value_names:
            if self.width[name] == machine.VLEN:
                cursor = machine.align_up(cursor, machine.VLEN)
                cursor += machine.VLEN
        for name in self.value_names:
            if self.width[name] != machine.VLEN:
                cursor += 1
        return cursor


def derive(program: dict) -> ProgramFacts:
    return ProgramFacts(program)


def time_width(horizon: int) -> int:
    """Bits needed to encode an issue time below ``horizon``."""

    if horizon < 1:
        raise ContractError("a horizon must be positive")
    return max(1, (horizon - 1).bit_length())


def lifetimes(facts: ProgramFacts, times: Dict[int, int]) -> Dict[str, Tuple[int, int]]:
    """Inclusive live interval of every value.

    The interval starts when the result writes scratch, at issue cycle plus
    latency, and ends at the last consumer's issue cycle. A result with no
    consumer still occupies its words for its write cycle.
    """

    live: Dict[str, List[int]] = {}
    for op_id in range(facts.count):
        name = facts.dest[op_id]
        if name is None:
            continue
        ready = times[op_id] + facts.latency[op_id]
        live[name] = [ready, ready]
    for name, consumers in facts.consumers.items():
        for consumer in consumers:
            if times[consumer] > live[name][1]:
                live[name][1] = times[consumer]
    return {name: (start, end) for name, (start, end) in live.items()}


def assemble_bundles(facts: ProgramFacts, times: Dict[int, int]) -> List[Dict[str, List[int]]]:
    """Emit bundles up to the last issue cycle.

    The score counts emitted bundles, so no trailing bundle is added for a
    result that is still in flight when the last operation issues.
    """

    if not times:
        raise ContractError("a schedule must place at least one operation")
    span = max(times.values()) + 1
    bundles: List[Dict[str, List[int]]] = [{} for _ in range(span)]
    for op_id in range(facts.count):
        engine = facts.engine[op_id]
        bundles[times[op_id]].setdefault(engine, []).append(op_id)
    return bundles


def cycle_count(compiled: dict) -> int:
    return len(compiled["bundles"])


def footprint(facts: ProgramFacts, addresses: Dict[str, int]) -> int:
    """Highest allocated end address, in words, including alignment holes."""

    return max(
        (addresses[name] + facts.width[name] for name in facts.value_names),
        default=0,
    )


def engine_usage(facts: ProgramFacts, times: Dict[int, int]) -> Dict[Tuple[str, int], int]:
    usage: Dict[Tuple[str, int], int] = {}
    for op_id in range(facts.count):
        key = (facts.engine[op_id], times[op_id])
        usage[key] = usage.get(key, 0) + 1
    return usage


def compilation(
    facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]
) -> dict:
    """The official ``{'scratch': ..., 'bundles': ...}`` contract."""

    return {
        "scratch": {name: addresses[name] for name in facts.value_names},
        "bundles": assemble_bundles(facts, times),
    }


def check_feasible(
    facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]
) -> None:
    """Our own acceptance check, independent of the reference validator.

    The release path additionally runs ``machine.check_compilation`` and
    ``machine.check_case``. Any disagreement between the two is a defect that
    blocks release; it is never resolved by trusting this function.
    """

    if set(times) != set(range(facts.count)):
        raise ContractError("every operation must be placed exactly once")
    for op_id, cycle in times.items():
        if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
            raise ContractError(f"operation {op_id} has a non-integer issue cycle")

    for op_id in range(facts.count):
        cycle = times[op_id]
        for predecessor, lag in facts.predecessors[op_id].items():
            if cycle < times[predecessor] + lag:
                raise ContractError(
                    f"operation {op_id} issues at {cycle}, before operation "
                    f"{predecessor} is ready at {times[predecessor] + lag}"
                )

    for (engine, cycle), used in engine_usage(facts, times).items():
        if used > machine.ENGINE_LIMITS[engine]:
            raise ContractError(
                f"cycle {cycle} issues {used} {engine} operations, limit is "
                f"{machine.ENGINE_LIMITS[engine]}"
            )

    if set(addresses) != set(facts.value_names):
        raise ContractError("every value requires exactly one scratch address")
    live = lifetimes(facts, times)
    for name in facts.value_names:
        base = addresses[name]
        width = facts.width[name]
        if not isinstance(base, int) or isinstance(base, bool) or base < 0:
            raise ContractError(f"value {name!r} has a non-integer address")
        if width == machine.VLEN and base % machine.VLEN != 0:
            raise ContractError(f"vector {name!r} is not aligned to {machine.VLEN} words")
        if base + width > machine.SCRATCH_WORDS:
            raise ContractError(
                f"value {name!r} ends at {base + width}, past {machine.SCRATCH_WORDS}"
            )

    ordered = list(facts.value_names)
    for i, first in enumerate(ordered):
        for second in ordered[i + 1 :]:
            spatial = (
                addresses[first] < addresses[second] + facts.width[second]
                and addresses[second] < addresses[first] + facts.width[first]
            )
            if not spatial:
                continue
            first_live, second_live = live[first], live[second]
            # Inclusive endpoints: an equal final read and new write conflict.
            temporal = first_live[0] <= second_live[1] and second_live[0] <= first_live[1]
            if temporal:
                raise ContractError(
                    f"values {first!r} and {second!r} share scratch while both are live"
                )
