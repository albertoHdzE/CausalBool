"""The direct-index compiler: bootstrap construction through exact queries.

Task L04 of ``plan/INDEX_ONLY_PLAN.md``, section 5.2. Every issue cycle and
every scratch address is chosen as the witness of an exact index query over
cube covers. No classical list scheduler, no first-fit allocator, no binary
decision diagram, and no external solver takes part, and
``machine.serial_compile`` is never called. There is no classical fallback: a
query that cannot complete is a compilation failure, not a reason to hand the
work to another method.

The two existence arguments the plan requires a reviewer to check against this
source are stated at ``_earliest_cycle`` and ``_lowest_address``.
"""

from __future__ import annotations

from dataclasses import dataclass, asdict
import json
from pathlib import Path
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_contract as dc
import schema_index as si


__all__ = [
    "Limits",
    "DEFAULT_LIMITS",
    "CompilationFailure",
    "compile_program",
    "compile_with_report",
    "bootstrap",
    "main",
]


@dataclass(frozen=True)
class Limits:
    """Central definition of every budget, recorded verbatim in reports."""

    total_seconds: float = 15.0
    optimise_seconds: float = 10.0
    query_seconds: float = 0.1
    max_cover: int = 4096
    max_visited: int = 50000
    max_records: int = 20000
    max_queries: int = 32

    def as_dict(self) -> Dict[str, float]:
        return dict(asdict(self))


DEFAULT_LIMITS = Limits()


class CompilationFailure(Exception):
    """Construction could not complete. No partial schedule is emitted."""


class _Deadline:
    """A monotonic soft deadline shared by every query of one compilation."""

    def __init__(self, seconds: float) -> None:
        self.started = time.monotonic()
        self.seconds = seconds

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self.started

    @property
    def remaining(self) -> float:
        return self.seconds - self.elapsed

    def budget(self, limits: Limits) -> si.Budget:
        remaining = self.remaining
        if remaining <= 0:
            raise CompilationFailure("the compilation deadline passed during construction")
        return si.Budget(
            seconds=min(limits.query_seconds, remaining),
            max_cover=limits.max_cover,
            max_visited=limits.max_visited,
            max_records=limits.max_records,
        )


class _Counters:
    """Query bookkeeping carried into the report."""

    def __init__(self) -> None:
        self.queries = 0
        self.cubes = 0
        self.largest_cover = 0
        self.intersections = 0

    def absorb(self, meter: si.Meter, cover_size: int) -> None:
        self.queries += 1
        self.cubes += meter.visited
        self.intersections += meter.intersections
        self.largest_cover = max(self.largest_cover, cover_size)

    def as_dict(self) -> Dict[str, int]:
        return {
            "queries": self.queries,
            "largest_cover": self.largest_cover,
            "intersections": self.intersections,
        }


# --------------------------------------------------------------------------
# Cover arithmetic used by the bootstrap queries
# --------------------------------------------------------------------------


def _intersect_cover(
    cover: Sequence[si.Cube], other: Sequence[si.Cube], meter: si.Meter
) -> Tuple[si.Cube, ...]:
    result: List[si.Cube] = []
    for left in cover:
        for right in other:
            meter.intersection()
            met = si.intersect(left, right)
            if met is not None:
                result.append(met)
    meter.cover(len(result))
    return tuple(result)


def _subtract_cover(
    cover: Sequence[si.Cube], removed: Sequence[si.Cube], meter: si.Meter
) -> Tuple[si.Cube, ...]:
    """Remove every member of ``removed`` from ``cover``.

    Interval covers are disjoint and cube difference preserves disjointness, so
    each removal replaces at most one member of the cover and the cover cannot
    grow without bound.
    """

    current = tuple(cover)
    for cube in removed:
        survivors: List[si.Cube] = []
        for member in current:
            meter.intersection()
            if si.compatible(member, cube):
                survivors.extend(si.difference(member, cube))
            else:
                survivors.append(member)
        meter.cover(len(survivors))
        current = tuple(survivors)
        if not current:
            break
    return current


def _overlap(first: Tuple[int, int], second: Tuple[int, int]) -> bool:
    """Inclusive live intervals touch."""

    return first[0] <= second[1] and second[0] <= first[1]


# --------------------------------------------------------------------------
# Scheduling
# --------------------------------------------------------------------------


def _earliest_cycle(
    facts: dc.ProgramFacts,
    op_id: int,
    lower: int,
    calendar: Dict[Tuple[str, int], int],
    budget: si.Budget,
    counters: _Counters,
) -> int:
    """The smallest legal issue cycle, retrieved as a schema witness.

    Construction argument, per plan section 5.2. Let ``h_i`` be the sum of the
    latencies of the operations before ``i``. By induction every earlier chosen
    time satisfies ``t_j <= h_j``, and ``h_j < h_i`` because every latency is
    positive. So at cycle ``h_i`` no earlier operation issues at all, which
    leaves its engine empty; every data predecessor is ready, and every ordered
    memory predecessor issued strictly earlier. Therefore ``h_i`` is a feasible
    extension and ``lower <= h_i <= horizon - 1``.

    The queried window ends at or beyond ``h_i``, and it also spans more cycles
    than there are blocked ones, so the remaining cover is never empty and a
    single query suffices. The calendar is bookkeeping for the predicates; the
    cycle itself is the minimum member of the queried cover.
    """

    engine = facts.engine[op_id]
    capacity = machine.ENGINE_LIMITS[engine]
    width = dc.time_width(facts.horizon)
    field = si.Field("t", 0, width)

    blocked = sorted(
        cycle
        for (other_engine, cycle), used in calendar.items()
        if other_engine == engine and used >= capacity and cycle >= lower
    )
    hi = min(facts.horizon - 1, max(lower + len(blocked), facts.prefix_horizon(op_id)))
    if lower > hi:
        raise CompilationFailure(
            f"operation {op_id} has no cycle in [{lower}, {hi}] within the horizon"
        )

    meter = budget.start()
    cover = si.interval(field, lower, hi, width)
    meter.cover(len(cover))
    cover = _subtract_cover(
        cover,
        tuple(si.Cube(width, field.encode(cycle), 0) for cycle in blocked if cycle <= hi),
        meter,
    )
    chosen = si.min_member(cover)
    counters.absorb(meter, len(cover))
    if chosen is None:
        raise CompilationFailure(f"no legal issue cycle remained for operation {op_id}")
    return field.decode(chosen)


def _schedule(
    facts: dc.ProgramFacts, limits: Limits, deadline: _Deadline, counters: _Counters
) -> Dict[int, int]:
    times: Dict[int, int] = {}
    calendar: Dict[Tuple[str, int], int] = {}
    for op_id in range(facts.count):
        lower = 0
        for predecessor, lag in facts.predecessors[op_id].items():
            candidate = times[predecessor] + lag
            if candidate > lower:
                lower = candidate
        try:
            cycle = _earliest_cycle(
                facts, op_id, lower, calendar, deadline.budget(limits), counters
            )
        except si.BudgetExhausted as exc:
            raise CompilationFailure(
                f"scheduling query for operation {op_id} exhausted its budget: {exc.reason}"
            ) from exc
        times[op_id] = cycle
        key = (facts.engine[op_id], cycle)
        calendar[key] = calendar.get(key, 0) + 1
    return times


# --------------------------------------------------------------------------
# Allocation
# --------------------------------------------------------------------------


def _lowest_address(
    facts: dc.ProgramFacts,
    name: str,
    live: Dict[str, Tuple[int, int]],
    placed: Sequence[str],
    addresses: Dict[str, int],
    budget: si.Budget,
    counters: _Counters,
) -> int:
    """The smallest legal aligned address, retrieved as a schema witness.

    Allocation argument, per plan section 5.2. Vectors are placed first, so
    while they are being placed a previously unused eight word block always
    lies below the total width of the vectors processed so far, and the
    scratchpad admits it because the unique vectors-first allocation of the
    whole program fits within 256 words. Scalars follow, and therefore need no
    alignment padding of their own. Reuse can only lower the high-water mark.

    The queried window first covers every address up to the total width already
    occupied by overlapping values, which is where a smallest-address answer
    must lie for a scalar, and is then widened to the whole legal domain. The
    widening keeps the query complete when alignment makes the tighter bound
    optimistic for a vector.
    """

    width = facts.width[name]
    field = si.Field("a", 0, dc.ADDRESS_WIDTH)
    universe = dc.ADDRESS_WIDTH
    cap = machine.SCRATCH_WORDS - width

    overlapping = [other for other in placed if _overlap(live[name], live[other])]
    occupied = sum(facts.width[other] for other in overlapping)

    windows = []
    for candidate in (min(cap, occupied), cap):
        if candidate >= 0 and candidate not in windows:
            windows.append(candidate)

    for hi in windows:
        meter = budget.start()
        cover = si.interval(field, 0, hi, universe)
        meter.cover(len(cover))
        if width == machine.VLEN:
            # A vector address has its low three bits clear.
            alignment = si.Cube(universe, 0, si.universe_mask(universe) ^ (machine.VLEN - 1))
            cover = _intersect_cover(cover, (alignment,), meter)
        for other in overlapping:
            base = addresses[other]
            low = max(0, base - width + 1)
            high = min(hi, base + facts.width[other] - 1)
            if low > high:
                continue
            cover = _subtract_cover(cover, si.interval(field, low, high, universe), meter)
            if not cover:
                break
        chosen = si.min_member(cover)
        counters.absorb(meter, len(cover))
        if chosen is not None:
            return field.decode(chosen)

    raise CompilationFailure(f"no legal scratch address remained for value {name!r}")


def _allocate(
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    limits: Limits,
    deadline: _Deadline,
    counters: _Counters,
) -> Dict[str, int]:
    live = dc.lifetimes(facts, times)
    vectors = [name for name in facts.value_names if facts.width[name] == machine.VLEN]
    scalars = [name for name in facts.value_names if facts.width[name] != machine.VLEN]

    def ordering(name: str) -> Tuple[int, int]:
        return (live[name][0], facts.producers[name])

    order = sorted(vectors, key=ordering) + sorted(scalars, key=ordering)

    addresses: Dict[str, int] = {}
    placed: List[str] = []
    for name in order:
        try:
            addresses[name] = _lowest_address(
                facts, name, live, placed, addresses, deadline.budget(limits), counters
            )
        except si.BudgetExhausted as exc:
            raise CompilationFailure(
                f"allocation query for {name!r} exhausted its budget: {exc.reason}"
            ) from exc
        placed.append(name)
    return addresses


# --------------------------------------------------------------------------
# Entry points
# --------------------------------------------------------------------------


def bootstrap(
    facts: dc.ProgramFacts, limits: Limits, deadline: _Deadline, counters: _Counters
) -> Tuple[Dict[int, int], Dict[str, int]]:
    """A complete first solution, built only from exact index queries."""

    times = _schedule(facts, limits, deadline, counters)
    addresses = _allocate(facts, times, limits, deadline, counters)
    return times, addresses


def compile_with_report(
    program: dict, limits: Optional[Limits] = None, optimise: bool = True
) -> Tuple[dict, dict]:
    """Compile, and return diagnostics beside the official result.

    The input dictionary is read and never modified. ``optimise`` is a
    diagnostic switch used to measure the bootstrap on its own; the official
    ``compile_program`` entry point never sets it.
    """

    limits = limits or DEFAULT_LIMITS
    deadline = _Deadline(limits.total_seconds)
    counters = _Counters()

    facts = dc.derive(program)
    times, addresses = bootstrap(facts, limits, deadline, counters)

    compiled = dc.compilation(facts, times, addresses)
    # Validate the incumbent before anything is allowed to build on it. Our own
    # predicates and the frozen validator must both accept it; a disagreement
    # is a defect, never something to route around.
    dc.check_feasible(facts, times, addresses)
    machine.check_compilation(program, compiled)

    cycles = len(compiled["bundles"])
    footprint = dc.footprint(facts, addresses)
    report = {
        "method": "direct_index",
        "stage": "bootstrap",
        "limits": limits.as_dict(),
        "operations": facts.count,
        "values": len(facts.value_names),
        "horizon": facts.horizon,
        "cycle_lower_bound": facts.cycle_lower_bound(),
        "memory_lower_bound": facts.memory_lower_bound(),
        "bootstrap": {
            "cycles": cycles,
            "footprint": footprint,
            "product": cycles * footprint,
            "queries": counters.as_dict(),
            "seconds": deadline.elapsed,
        },
        # A runner should not have to know how diagnostics are nested to find
        # out whether this compilation disagreed with its own queries.
        "optimisation": {"enabled": False, "discrepancy_count": 0},
        "discrepancy_count": 0,
        "cycles": cycles,
        "footprint": footprint,
        "product": cycles * footprint,
        "seconds": deadline.elapsed,
    }

    if optimise:
        # Imported inside the function so that the two modules do not form an
        # import cycle. This is the integration point of plan section 6, where
        # the lead wires L05 in behind L04's frozen interface.
        import direct_optimizer

        times, addresses, record = direct_optimizer.optimise(
            program, facts, times, addresses, limits, deadline, counters
        )
        report["optimisation"] = record
        report["discrepancy_count"] = record["discrepancy_count"]
        report["stage"] = "optimised" if record["accepted"] else "bootstrap"
        # Whatever survives is validated again before it is returned.
        dc.check_feasible(facts, times, addresses)
        compiled = dc.compilation(facts, times, addresses)
        machine.check_compilation(program, compiled)
        cycles = len(compiled["bundles"])
        footprint = dc.footprint(facts, addresses)
        report["cycles"] = cycles
        report["footprint"] = footprint
        report["product"] = cycles * footprint
        report["queries"] = counters.as_dict()
        report["seconds"] = deadline.elapsed

    return compiled, report


def compile_program(program: dict) -> dict:
    """The official contract: ``{'scratch': {...}, 'bundles': [...]}``."""

    compiled, _ = compile_with_report(program)
    return compiled


def main(argv: Sequence[str]) -> int:
    """Emit only schedule JSON on stdout; diagnostics go to stderr."""

    if len(argv) != 1:
        print("usage: python3 direct_compiler.py <program.json>", file=sys.stderr)
        return 2
    try:
        program = machine.load_program(argv[0])
        compiled, report = compile_with_report(program)
    except (OSError, json.JSONDecodeError, machine.ProgramError, machine.CompileError,
            dc.ContractError, CompilationFailure) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    print(
        "cycles={cycles} footprint={footprint} seconds={seconds:.3f}".format(**report),
        file=sys.stderr,
    )
    json.dump(compiled, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
