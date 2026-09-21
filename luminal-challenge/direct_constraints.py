"""Arithmetic covers and the complete joint acceptance expression.

Task L03 of ``plan/INDEX_ONLY_PLAN.md``, sections 3.3 and 5.3.

A term is a field plus an integer offset, or a plain constant. All time and
address arithmetic here is **nonwrapping**: an offset is added with ordinary
Python integers and a carry is never truncated because the underlying field has
a fixed width. Comparisons are built as exact cube covers by min and max
interval reasoning on each partial cube; when the extrema straddle the boundary
the cube is unresolved and is split, never dropped.

The joint query of section 5.3 varies the issue times of a small window of
operations, the addresses of the results they produce, and their engine lanes.
Every other decision stays fixed, and constraints involving fixed decisions are
still built, including constraints on values whose producers lie outside the
window.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import machine

import direct_contract as dc
import schema_index as si


__all__ = [
    "Term",
    "constant",
    "le",
    "lt",
    "ge",
    "gt",
    "eq",
    "ne",
    "relation_cover",
    "CoverCache",
    "JointQuery",
    "Infeasible",
]


# --------------------------------------------------------------------------
# Cover reuse
# --------------------------------------------------------------------------


class CoverCache:
    """Relation covers already built during one compilation.

    A relation cover is a pure function of the relation name, the two terms and
    the universe width: no clock, no incumbent and no target enters it. Terms
    and fields are frozen, cubes are immutable and a cover is a tuple of them,
    so a stored cover can be handed to a second query unchanged. The optimiser
    poses the same window against several targets in turn, and the precedence,
    capacity and scratch-safety relations of a window do not depend on the
    target, so the same covers are otherwise rebuilt from scratch each time.

    Three properties make this safe to use inside a budgeted search.

    * **The key carries every semantic input.** Relation name, each term's
      field — itself keyed by name, offset and width — each term's integer
      offset, and the universe width.
    * **A hit costs exactly what the miss cost.** The visits and records the
      original construction paid are stored beside the cover and charged again
      on every hit, so a query that could not have afforded to build the cover
      still cannot afford to use it. The cache buys time, never budget.
    * **A partial cover is never stored.** An entry is written only after
      ``relation_cover`` returns, so a construction stopped by exhaustion
      leaves nothing behind.

    The cache is created per compilation and thrown away with it. It is never
    process-global, it holds no mutable state, and it is bounded in both
    entries and retained cubes; past either bound it simply stops storing.
    """

    __slots__ = ("_entries", "max_entries", "max_cubes", "cubes", "hits", "misses", "refused")

    def __init__(self, max_entries: int = 4096, max_cubes: int = 200000) -> None:
        self._entries: Dict[tuple, Tuple[Tuple[si.Cube, ...], int, int]] = {}
        self.max_entries = max_entries
        self.max_cubes = max_cubes
        self.cubes = 0
        self.hits = 0
        self.misses = 0
        self.refused = 0

    @staticmethod
    def key(name: str, lhs: "Term", rhs: "Term", n: int) -> tuple:
        return (
            name,
            lhs.field,
            lhs.offset,
            rhs.field,
            rhs.offset,
            n,
        )

    def get(self, key: tuple):
        found = self._entries.get(key)
        if found is None:
            self.misses += 1
            return None
        self.hits += 1
        return found

    def put(self, key: tuple, cover: Tuple[si.Cube, ...], visits: int, records: int) -> None:
        if key in self._entries:
            return
        if len(self._entries) >= self.max_entries or self.cubes + len(cover) > self.max_cubes:
            self.refused += 1
            return
        self._entries[key] = (cover, visits, records)
        self.cubes += len(cover)

    def statistics(self) -> Dict[str, int]:
        return {
            "entries": len(self._entries),
            "cubes_retained": self.cubes,
            "hits": self.hits,
            "misses": self.misses,
            "refused": self.refused,
            "max_entries": self.max_entries,
            "max_cubes": self.max_cubes,
        }


class Infeasible(Exception):
    """A fixed decision already violates the requested target.

    This does not authorise widening the window; the query is simply
    infeasible as posed.
    """


# --------------------------------------------------------------------------
# Terms
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Term:
    """``field + offset``, or a bare constant when ``field`` is ``None``.

    The offset may be negative. Addition never wraps.
    """

    field: Optional[si.Field] = None
    offset: int = 0

    def __post_init__(self) -> None:
        if self.field is not None and not isinstance(self.field, si.Field):
            raise TypeError("a term holds a Field or None")
        if not isinstance(self.offset, int) or isinstance(self.offset, bool):
            raise TypeError("a term offset must be a plain integer")

    @property
    def mask(self) -> int:
        return 0 if self.field is None else self.field.mask

    @property
    def is_constant(self) -> bool:
        return self.field is None

    def bounds(self, cube: si.Cube) -> Tuple[int, int]:
        """The smallest and largest value this term takes inside ``cube``."""

        if self.field is None:
            return self.offset, self.offset
        field = self.field
        low = (cube.anchor & field.mask) >> field.offset
        high = ((cube.anchor | cube.free_mask) & field.mask) >> field.offset
        return low + self.offset, high + self.offset

    def shifted(self, amount: int) -> "Term":
        return Term(self.field, self.offset + amount)


def constant(value: int) -> Term:
    return Term(None, value)


# --------------------------------------------------------------------------
# Relations
# --------------------------------------------------------------------------


def _decide_le(low_l, high_l, low_r, high_r):
    if high_l <= low_r:
        return True
    if low_l > high_r:
        return False
    return None


def _decide_lt(low_l, high_l, low_r, high_r):
    if high_l < low_r:
        return True
    if low_l >= high_r:
        return False
    return None


def _decide_eq(low_l, high_l, low_r, high_r):
    if low_l == high_l == low_r == high_r:
        return True
    if high_l < low_r or high_r < low_l:
        return False
    return None


def _decide_ne(low_l, high_l, low_r, high_r):
    if high_l < low_r or high_r < low_l:
        return True
    if low_l == high_l == low_r == high_r:
        return False
    return None


_RELATIONS = {
    "le": (_decide_le, lambda a, b: a <= b),
    "lt": (_decide_lt, lambda a, b: a < b),
    "eq": (_decide_eq, lambda a, b: a == b),
    "ne": (_decide_ne, lambda a, b: a != b),
}


def _significance(coordinate: int, lhs: "Term", rhs: "Term") -> int:
    """Place value of a coordinate within whichever term's field holds it."""

    best = -1
    for term in (lhs, rhs):
        if term.field is None:
            continue
        if term.field.offset <= coordinate < term.field.end():
            best = max(best, coordinate - term.field.offset)
    return best


def relation_cover(
    name: str,
    lhs: Term,
    rhs: Term,
    n: int,
    meter: si.Meter,
    cache: Optional[CoverCache] = None,
) -> Tuple[si.Cube, ...]:
    """An exact, sound and complete cover of ``lhs <name> rhs``.

    Coordinates outside the two terms' fields are left free. The next
    coordinate to split is chosen by descending bit significance within either
    operand field, ties broken by descending absolute coordinate, and the zero
    branch is visited first, so the result is deterministic. This is the
    version 1.1 order approved by the lead; each split still partitions the
    current cube into disjoint exhaustive children, so denotation and exactness
    are unchanged and only the cover's size and cost differ.
    """

    if name not in _RELATIONS:
        raise ValueError(f"unknown relation {name!r}")
    decide, exact = _RELATIONS[name]

    # A cover already built in this compilation is handed back, but only after
    # the meter has been charged the visits and records the original build
    # cost. The cache therefore saves time and never budget: a query that could
    # not have afforded to construct this cover still cannot afford to use it,
    # and it still stops with UNKNOWN rather than receiving a free answer.
    key = None
    if cache is not None:
        key = cache.key(name, lhs, rhs, n)
        found = cache.get(key)
        if found is not None:
            cover, visits, records = found
            meter.visit(visits)
            meter.record(records)
            meter.cover_limit(len(cover))
            return cover
    visits_before = meter.visited
    records_before = meter.records

    # Simplify before splitting: two constants, or the same field on both
    # sides, reduce to a constant comparison. These paths still answer a query
    # and still cost a cube, so they are charged and the clock is checked; an
    # early return that skipped both would hand back an answer under an
    # already-expired budget.
    def store(cover: Tuple[si.Cube, ...]) -> Tuple[si.Cube, ...]:
        """Keep a completed cover, with what it cost, for the next query.

        Only reached on a normal return, so a cover abandoned part-way through
        by an exhausted budget is never stored.
        """

        if cache is not None and key is not None:
            cache.put(
                key, cover, meter.visited - visits_before, meter.records - records_before
            )
        return cover

    if (lhs.is_constant and rhs.is_constant) or (
        lhs.field is not None and rhs.field is not None and lhs.field == rhs.field
    ):
        meter.check_time()
        if not exact(lhs.offset, rhs.offset):
            return store(())
        meter.record(1)
        return store((si.universe(n),))

    support = lhs.mask | rhs.mask
    limit = si.universe_mask(n)
    if support & ~limit:
        raise ValueError("a term reaches outside the declared universe")

    # Split order: the most significant bit *within its own field* first, and
    # the higher coordinate to break a tie. Comparing two fields held at
    # different offsets, a plain highest-coordinate rule would exhaust every
    # value of whichever field sits higher in the index before it ever looked
    # at the other operand, which produces an enormous though still exact
    # cover. Ordering by place value is the usual comparator structure. Any
    # split order gives the same set, since each split partitions the cube;
    # only the size and the cost of the cover change.
    order: List[int] = []
    for coordinate in range(n):
        if not (support >> coordinate) & 1:
            continue
        order.append(coordinate)
    order.sort(key=lambda c: (_significance(c, lhs, rhs), c), reverse=True)
    # The split order is fixed for the whole construction, so its weights are
    # computed once instead of rebuilding a generator at every node.
    order_bits = [(1 << coordinate, coordinate) for coordinate in order]

    # A term's bounds are ``((anchor & mask) >> shift) + offset`` and
    # ``(((anchor | free) & mask) >> shift) + offset``. Hoisting the mask, the
    # shift and the offset out of the loop turns two method calls per node into
    # local arithmetic; a constant term has mask zero, for which the same
    # expression yields its offset twice, so no separate case is needed.
    l_mask = lhs.field.mask if lhs.field is not None else 0
    l_shift = lhs.field.offset if lhs.field is not None else 0
    l_offset = lhs.offset
    r_mask = rhs.field.mask if rhs.field is not None else 0
    r_shift = rhs.field.offset if rhs.field is not None else 0
    r_offset = rhs.offset

    accepted: List[si.Cube] = []
    stack = [si.universe(n)]
    visit = meter.visit
    record = meter.record
    cover_limit = meter.cover_limit
    while stack:
        visit()
        cube = stack.pop()
        anchor = cube.anchor
        span = anchor | cube.free_mask
        low_l = ((anchor & l_mask) >> l_shift) + l_offset
        high_l = ((span & l_mask) >> l_shift) + l_offset
        low_r = ((anchor & r_mask) >> r_shift) + r_offset
        high_r = ((span & r_mask) >> r_shift) + r_offset
        verdict = decide(low_l, high_l, low_r, high_r)
        if verdict is True:
            accepted.append(cube)
            # Charged and checked as the cover grows, not once it is finished:
            # otherwise an over-cap cover is fully built before anyone objects.
            cover_limit(len(accepted))
            record(1)
            continue
        if verdict is False:
            continue
        free = support & cube.free_mask
        if free == 0:
            # Fully fixed on the support: evaluate the predicate exactly.
            if exact(low_l, low_r):
                accepted.append(cube)
                cover_limit(len(accepted))
                record(1)
            continue
        for bit, coordinate in order_bits:
            if free & bit:
                break
        # Both cofactors at once, from the owner of the cube representation.
        # The coordinate is free here, so neither part can be empty. Pushed
        # one first so that the zero branch is explored first.
        zero, one = si.split(cube, coordinate)
        stack.append(one)
        stack.append(zero)
    cover = si.normalise_cover(accepted, meter)
    # The members were charged as they were accepted, so this validates the
    # final size without billing the same cover a second time.
    meter.cover_limit(len(cover))
    # Normalisation reads the clock only every 256 members and ``cover_limit``
    # reads it not at all, so a cover finished after the deadline would
    # otherwise be handed back as a completed relation. Same rule as the
    # solver's terminal verdict: observe the deadline before certifying.
    meter.check_time()
    return store(cover)


def _leaf(
    name: str,
    lhs: Term,
    rhs: Term,
    n: int,
    meter: si.Meter,
    cache: Optional[CoverCache] = None,
) -> si.Leaf:
    cover = relation_cover(name, lhs, rhs, n, meter, cache)
    meter.node()
    return si.Leaf(cover)


def le(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("le", lhs, rhs, n, meter, cache)


def lt(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("lt", lhs, rhs, n, meter, cache)


def ge(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("le", rhs, lhs, n, meter, cache)


def gt(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("lt", rhs, lhs, n, meter, cache)


def eq(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("eq", lhs, rhs, n, meter, cache)


def ne(lhs, rhs, n, meter, cache=None) -> si.Leaf:
    return _leaf("ne", lhs, rhs, n, meter, cache)


# --------------------------------------------------------------------------
# The joint query
# --------------------------------------------------------------------------


TIME_SLACK = 2


class JointQuery:
    """One joint scheduling, allocation and lane query over a small window.

    Fields are allocated by increasing operation identifier: issue time, then
    the result address if the operation produces one, then a lane bit if its
    engine has two slots. Bits within every field are LSB-first.
    """

    def __init__(
        self,
        facts: dc.ProgramFacts,
        times: Dict[int, int],
        addresses: Dict[str, int],
        window: Sequence[int],
        target_cycles: int,
        target_memory: int,
        meter: si.Meter,
        cache: Optional[CoverCache] = None,
    ) -> None:
        self.facts = facts
        self.times = dict(times)
        self.addresses = dict(addresses)
        self.window = tuple(sorted(set(window)))
        self.target_cycles = target_cycles
        self.target_memory = target_memory
        self.meter = meter
        # Compilation-local, supplied by the optimiser; ``None`` means no reuse.
        self.cache = cache

        if not self.window:
            raise ValueError("a joint query needs at least one selected operation")
        if target_cycles < 1 or target_memory < 1:
            raise Infeasible("a target must be positive")

        self.time_bits = dc.time_width(facts.horizon)
        self.time_field: Dict[int, si.Field] = {}
        self.address_field: Dict[str, si.Field] = {}
        self.lane_field: Dict[int, si.Field] = {}

        offset = 0
        for op_id in self.window:
            self.time_field[op_id] = si.Field("t%d" % op_id, offset, self.time_bits)
            offset += self.time_bits
            name = facts.dest[op_id]
            if name is not None:
                self.address_field[name] = si.Field("a_" + name, offset, dc.ADDRESS_WIDTH)
                offset += dc.ADDRESS_WIDTH
            if machine.ENGINE_LIMITS[facts.engine[op_id]] > 1:
                self.lane_field[op_id] = si.Field("l%d" % op_id, offset, 1)
                offset += 1
        self.n = offset

        self.selected_values = tuple(
            facts.dest[op_id] for op_id in self.window if facts.dest[op_id] is not None
        )
        # A value is affected when its producer moves, or when any consumer
        # moves and so may extend or shorten its live interval.
        affected = set(self.selected_values)
        for name in facts.value_names:
            if any(consumer in self.time_field for consumer in facts.consumers[name]):
                affected.add(name)
        self.affected_values = tuple(
            name for name in facts.value_names if name in affected
        )
        self._live_cache: Dict[str, Tuple[int, int]] = {}

    def _leaf_node(self, cover) -> si.Leaf:
        """A leaf built here, charged as a node plus its alternatives."""

        self.meter.cover_limit(len(cover))
        self.meter.record(len(cover))
        self.meter.node()
        return si.Leaf(cover)

    def _all(self, children) -> si.AllOf:
        children = tuple(children)
        self.meter.node()
        return si.AllOf(children)

    def _any(self, children) -> si.AnyOf:
        children = tuple(children)
        self.meter.node()
        return si.AnyOf(children)

    # -- terms --------------------------------------------------------------

    def time_term(self, op_id: int, offset: int = 0) -> Term:
        field = self.time_field.get(op_id)
        if field is None:
            return constant(self.times[op_id] + offset)
        return Term(field, offset)

    def address_term(self, name: str, offset: int = 0) -> Term:
        field = self.address_field.get(name)
        if field is None:
            return constant(self.addresses[name] + offset)
        return Term(field, offset)

    def lane_term(self, op_id: int) -> Term:
        field = self.lane_field.get(op_id)
        if field is None:
            return constant(self._fixed_lane(op_id))
        return Term(field, 0)

    def write_term(self, name: str, offset: int = 0) -> Term:
        producer = self.facts.producers[name]
        return self.time_term(producer, self.facts.latency[producer] + offset)

    def _fixed_lane(self, op_id: int) -> int:
        """External operations are numbered within their engine and cycle."""

        engine = self.facts.engine[op_id]
        cycle = self.times[op_id]
        lane = 0
        for other in range(self.facts.count):
            if other == op_id:
                break
            if other in self.time_field:
                continue
            if self.facts.engine[other] == engine and self.times[other] == cycle:
                lane += 1
        return lane

    # -- possible extents, used only for exact simplification ---------------

    def _time_bounds(self, op_id: int) -> Tuple[int, int]:
        if op_id not in self.time_field:
            fixed = self.times[op_id]
            return fixed, fixed
        low, high = self._time_domain(op_id)
        return low, high

    def _time_domain(self, op_id: int) -> Tuple[int, int]:
        ceiling = min(self.facts.horizon, self.target_cycles) - 1
        incumbent = self.times[op_id]
        return max(0, incumbent - TIME_SLACK), min(incumbent + TIME_SLACK, ceiling)

    def _live_bounds(self, name: str) -> Tuple[int, int]:
        """The widest live interval this value can take over the domains."""

        cached = self._live_cache.get(name)
        if cached is not None:
            return cached
        result = self._compute_live_bounds(name)
        self._live_cache[name] = result
        return result

    def _compute_live_bounds(self, name: str) -> Tuple[int, int]:
        producer = self.facts.producers[name]
        low, high = self._time_bounds(producer)
        latency = self.facts.latency[producer]
        start, end = low + latency, high + latency
        for consumer in self.facts.consumers[name]:
            end = max(end, self._time_bounds(consumer)[1])
        return start, end

    def _address_bounds(self, name: str) -> Tuple[int, int]:
        if name not in self.address_field:
            base = self.addresses[name]
            return base, base
        return 0, self.target_memory - self.facts.width[name]

    # -- constraint groups --------------------------------------------------

    def _domains(self) -> List[si.Leaf]:
        parts: List[si.Leaf] = []
        for op_id in self.window:
            field = self.time_field[op_id]
            low, high = self._time_domain(op_id)
            if low > high:
                raise Infeasible(
                    f"operation {op_id} has no cycle below the target of {self.target_cycles}"
                )
            if high >= field.limit:
                raise Infeasible("a time domain does not fit its field")
            parts.append(self._leaf_node(si.interval(field, low, high, self.n)))
        for name in self.selected_values:
            field = self.address_field[name]
            width = self.facts.width[name]
            high = self.target_memory - width
            if high < 0:
                raise Infeasible(f"value {name!r} cannot fit a target of {self.target_memory}")
            cover = si.interval(field, 0, high, self.n)
            if width == machine.VLEN:
                alignment = si.Cube(
                    self.n, 0, si.universe_mask(self.n) ^ (field.encode(machine.VLEN - 1))
                )
                cover = tuple(
                    met
                    for met in (si.intersect(cube, alignment) for cube in cover)
                    if met is not None
                )
            if not cover:
                raise Infeasible(f"value {name!r} has an empty address domain")
            parts.append(self._leaf_node(cover))
        return parts

    def _fixed_targets(self) -> None:
        """A fixed decision violating a target makes the query infeasible."""

        for op_id in range(self.facts.count):
            if op_id in self.time_field:
                continue
            if self.times[op_id] >= self.target_cycles:
                raise Infeasible(
                    f"external operation {op_id} issues at {self.times[op_id]}, "
                    f"at or past the target of {self.target_cycles}"
                )
        for name in self.facts.value_names:
            if name in self.address_field:
                continue
            if self.addresses[name] + self.facts.width[name] > self.target_memory:
                raise Infeasible(
                    f"external value {name!r} ends past the target of {self.target_memory}"
                )

    def _data_precedence(self) -> List[si.Leaf]:
        parts = []
        for op_id in range(self.facts.count):
            for predecessor, lag in sorted(self.facts.predecessors[op_id].items()):
                if op_id not in self.time_field and predecessor not in self.time_field:
                    continue
                clause = ge(
                    self.time_term(op_id), self.time_term(predecessor, lag), self.n, self.meter, self.cache
                )
                if not clause.cubes:
                    raise Infeasible(
                        f"operation {op_id} cannot follow operation {predecessor}"
                    )
                if len(clause.cubes) == 1 and clause.cubes[0] == si.universe(self.n):
                    continue
                parts.append(clause)
        return parts

    def _engine_capacity(self) -> List[si.Expression]:
        parts: List[si.Expression] = []
        for op_id in self.window:
            engine = self.facts.engine[op_id]
            low, high = self._time_domain(op_id)
            for other in range(self.facts.count):
                if other == op_id or self.facts.engine[other] != engine:
                    continue
                if other in self.time_field and other < op_id:
                    continue  # the pair was already stated once
                other_low, other_high = self._time_bounds(other)
                if other_high < low or high < other_low:
                    continue  # the two can never share a cycle
                different_time = ne(
                    self.time_term(op_id), self.time_term(other), self.n, self.meter, self.cache
                )
                if machine.ENGINE_LIMITS[engine] == 1:
                    if not different_time.cubes:
                        raise Infeasible(
                            f"operations {op_id} and {other} must share a single slot"
                        )
                    parts.append(different_time)
                    continue
                different_lane = ne(
                    self.lane_term(op_id), self.lane_term(other), self.n, self.meter, self.cache
                )
                if different_lane.cubes and si.universe(self.n) in different_lane.cubes:
                    continue
                if not different_time.cubes and not different_lane.cubes:
                    raise Infeasible(
                        f"operations {op_id} and {other} cannot share engine {engine}"
                    )
                parts.append(self._any((different_time, different_lane)))
        return parts

    def _scratch_safety(self) -> List[si.Expression]:
        """Spatial separation OR temporal separation, never both required."""

        parts: List[si.Expression] = []
        names = list(self.facts.value_names)
        position = {name: index for index, name in enumerate(names)}

        # Only a pair holding an affected value can be anything but constant,
        # so the scan runs over affected values against all values rather than
        # over all pairs. The pairs are then ordered by increasing value
        # identifier, which is the order the plan declares.
        pairs = set()
        for first in self.affected_values:
            for second in names:
                if second == first:
                    continue
                pairs.add(
                    (first, second) if position[first] < position[second] else (second, first)
                )

        for first, second in sorted(pairs, key=lambda pair: (position[pair[0]], position[pair[1]])):
                first_live = self._live_bounds(first)
                second_live = self._live_bounds(second)
                if first_live[1] < second_live[0] or second_live[1] < first_live[0]:
                    continue  # they can never be live together
                first_span = self._address_bounds(first)
                second_span = self._address_bounds(second)
                first_width = self.facts.width[first]
                second_width = self.facts.width[second]
                if (
                    first_span[1] + first_width <= second_span[0]
                    or second_span[1] + second_width <= first_span[0]
                ):
                    continue  # they can never share a word
                clause = self._any(
                    (
                        le(
                            self.address_term(first, first_width),
                            self.address_term(second),
                            self.n,
                            self.meter,
                            self.cache,
                        ),
                        le(
                            self.address_term(second, second_width),
                            self.address_term(first),
                            self.n,
                            self.meter,
                            self.cache,
                        ),
                        self._ends_before(first, second),
                        self._ends_before(second, first),
                    )
                )
                parts.append(clause)
        return parts

    def _ends_before(self, first: str, second: str) -> si.Expression:
        """``end(first) < start(second)``, expanded over every consumer.

        The maximum in ``end`` is not approximated by a selected consumer: the
        write and *every* consumer of ``first`` must precede the write of
        ``second``.
        """

        write_second = self.write_term(second)
        children: List[si.Expression] = [
            lt(self.write_term(first), write_second, self.n, self.meter, self.cache)
        ]
        for consumer in self.facts.consumers[first]:
            children.append(
                lt(self.time_term(consumer), write_second, self.n, self.meter, self.cache)
            )
        return self._all(children)

    # -- assembly -----------------------------------------------------------

    def expression(self) -> si.Expression:
        """The acceptance expression, built in the plan's declared order."""

        self._fixed_targets()
        children: List[si.Expression] = []
        children.extend(self._domains())
        children.extend(self._data_precedence())
        children.extend(self._engine_capacity())
        children.extend(self._scratch_safety())
        built = self._all(children)

        # Every node and alternative was charged as it was assembled, so this
        # can only hold; it is asserted anyway, because the property that
        # matters to a caller is that what comes back fits the declared cap.
        total = si.count_records(built)
        if total > self.meter.budget.max_records:
            raise si.BudgetExhausted("expression-record budget exhausted")
        # Construction paid for this expression; solving must not bill it twice.
        self.meter.mark_charged(built)
        return built

    def decode(self, cube: si.Cube) -> Tuple[Dict[int, int], Dict[str, int]]:
        """Read a witness back into a complete schedule and allocation."""

        if cube.n != self.n:
            raise ValueError("the witness has the wrong width")
        times = dict(self.times)
        addresses = dict(self.addresses)
        anchor = cube.anchor
        for op_id, field in self.time_field.items():
            value = field.decode(anchor)
            low, high = self._time_domain(op_id)
            if not low <= value <= high:
                raise ValueError(
                    f"decoded cycle {value} for operation {op_id} is outside its domain"
                )
            times[op_id] = value
        for name, field in self.address_field.items():
            value = field.decode(anchor)
            width = self.facts.width[name]
            if value + width > self.target_memory:
                raise ValueError(f"decoded address {value} for {name!r} exceeds the target")
            if width == machine.VLEN and value % machine.VLEN:
                raise ValueError(f"decoded address {value} for {name!r} is misaligned")
            addresses[name] = value
        return times, addresses
