"""Direct index schemata: cube algebra, fields, expressions, and exact solving.

This module is the single owner of the direct-index representation described in
section 3 of ``plan/INDEX_ONLY_PLAN.md`` (task L01). Nothing else in the direct
path may define a second cube algebra.

A cube is a decimal anchor together with a free-coordinate mask. It denotes the
set ``{anchor + s}`` where ``s`` ranges over every subset of the free-coordinate
weights; those fillings are the cube's sumandos. Coordinates are LSB-first, so
coordinate ``i`` carries weight ``1 << i``. A family of cubes denotes the union
of its members.

An index encodes candidate decisions. Decoding one of its fields may yield a
scratch address, but the index itself is not a physical scratch address.

No binary decision diagram, truth-table inversion over a whole program, or
external solver appears here. Queries are answered by lazy depth-first
intersection over an AND/OR expression whose leaves are exact cube covers.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field as _dataclass_field
from typing import Dict, Iterator, Optional, Sequence, Tuple, Union

__all__ = [
    "SAT",
    "UNSAT",
    "UNKNOWN",
    "Cube",
    "Field",
    "Leaf",
    "AllOf",
    "AnyOf",
    "Budget",
    "Meter",
    "BudgetExhausted",
    "QueryResult",
    "DEFAULT_BUDGET",
    "universe_mask",
    "universe",
    "compatible",
    "intersect",
    "difference",
    "restrict",
    "split",
    "interval",
    "domain",
    "min_member",
    "cover_contains",
    "normalise_cover",
    "true_leaf",
    "false_leaf",
    "expression_width",
    "count_records",
    "solve",
]


SAT = "SAT"
UNSAT = "UNSAT"
UNKNOWN = "UNKNOWN"


# --------------------------------------------------------------------------
# Validation helpers
# --------------------------------------------------------------------------


def _plain_int(value: object) -> bool:
    """A genuine integer. Booleans are rejected where integers are required."""

    return isinstance(value, int) and not isinstance(value, bool)


def _require_index(value: object, name: str, minimum: int = 0) -> int:
    if not _plain_int(value):
        raise TypeError(f"{name} must be a plain integer, not {type(value).__name__}")
    if value < minimum:
        raise ValueError(f"{name} must be at least {minimum}, got {value}")
    return int(value)


def universe_mask(n: int) -> int:
    """The all-coordinates mask ``U`` of an ``n`` bit universe."""

    _require_index(n, "n")
    return (1 << n) - 1


# --------------------------------------------------------------------------
# Cubes
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Cube:
    """An immutable schema: a decimal anchor and its free-coordinate mask."""

    n: int
    anchor: int
    free_mask: int

    def __post_init__(self) -> None:
        _require_index(self.n, "n")
        _require_index(self.anchor, "anchor")
        _require_index(self.free_mask, "free_mask")
        limit = universe_mask(self.n)
        if self.anchor > limit:
            raise ValueError(f"anchor {self.anchor} exceeds the {self.n} bit universe")
        if self.free_mask > limit:
            raise ValueError(f"free mask {self.free_mask} exceeds the {self.n} bit universe")
        if self.anchor & self.free_mask:
            raise ValueError("anchor and free mask must be disjoint")

    @property
    def universe(self) -> int:
        return universe_mask(self.n)

    @property
    def fixed_mask(self) -> int:
        return universe_mask(self.n) ^ self.free_mask

    @property
    def size(self) -> int:
        """The number of sumandos, that is the cardinality of the cube."""

        return 1 << self.free_mask.bit_count()

    def contains(self, index: int) -> bool:
        _require_index(index, "index")
        if index > universe_mask(self.n):
            return False
        return (index & self.fixed_mask) == self.anchor

    def members(self) -> Iterator[int]:
        """Every filling of the free coordinates, in increasing numeric order."""

        positions = [i for i in range(self.n) if (self.free_mask >> i) & 1]
        for code in range(1 << len(positions)):
            offset = 0
            for j, position in enumerate(positions):
                if (code >> j) & 1:
                    offset |= 1 << position
            yield self.anchor + offset

    def label(self) -> str:
        """A printed pattern in the declared ``x0, x1, ...`` LSB-first order."""

        marks = []
        for i in range(self.n):
            if (self.free_mask >> i) & 1:
                marks.append("*")
            else:
                marks.append("1" if (self.anchor >> i) & 1 else "0")
        return "x0..x{}:{}".format(max(self.n - 1, 0), "".join(marks))


def _derived_cube(n: int, anchor: int, free_mask: int) -> Cube:
    """Build a cube whose invariant is already proved by its caller.

    ``Cube.__post_init__`` re-validates three integers on every construction.
    That is the right behaviour at the boundary, where a cube is built from
    values this module did not produce. Inside the algebra it is pure overhead:
    each operation below derives its result from operands that are already
    valid cubes of the same width, and each carries the proof that the
    invariant survives. The profiled search built cubes 142,485 times and asked
    ``universe_mask`` to revalidate a width 49,092,774 times.

    Every use of this constructor states its proof at the call site. The public
    ``Cube`` constructor is unchanged and still rejects a bad anchor, a bad
    free mask, an overlap between them, a boolean, or a negative value.
    """

    cube = object.__new__(Cube)
    object.__setattr__(cube, "n", n)
    object.__setattr__(cube, "anchor", anchor)
    object.__setattr__(cube, "free_mask", free_mask)
    return cube


def universe(n: int) -> Cube:
    """The cube holding every index of an ``n`` bit universe.

    For ``n == 0`` this is the single empty assignment, index zero.
    """

    return Cube(n, 0, universe_mask(n))


def compatible(a: Cube, b: Cube) -> bool:
    """Whether two equal-width cubes intersect."""

    _require_same_width(a, b)
    limit = universe_mask(a.n)
    return ((a.anchor ^ b.anchor) & (limit ^ (a.free_mask | b.free_mask))) == 0


def _require_same_width(a: Cube, b: Cube) -> None:
    if not isinstance(a, Cube) or not isinstance(b, Cube):
        raise TypeError("cube operations require Cube operands")
    if a.n != b.n:
        raise ValueError(f"cube widths differ: {a.n} and {b.n}")


def intersect(a: Cube, b: Cube) -> Optional[Cube]:
    """The exact intersection of two equal-width cubes, or ``None`` if empty.

    This is the innermost operation of the whole method: the profiled search of
    one public query called it 48,950,288 times, and 99.7% of those calls
    return ``None``. Two rewritings make that path cheap without changing what
    it computes.

    The universe mask is not needed. Both anchors are at most ``U``, so their
    exclusive-or is too, and for nonnegative ``x, y <= U`` the identity
    ``x & ~y == x & (U ^ (y & U))`` holds. Masking by ``U`` was therefore
    always redundant here, and removing it removes a revalidation of the width
    from every call.

    The result's invariant is proved rather than rechecked. ``anchor | anchor``
    is at most ``U`` and ``free & free`` is at most ``U``; and since
    ``a.anchor & a.free_mask == 0`` and ``b.anchor & b.free_mask == 0``,
    ``(a.anchor | b.anchor) & (a.free_mask & b.free_mask)`` is zero.
    """

    if a.__class__ is not Cube or b.__class__ is not Cube or a.n != b.n:
        # Preserve the documented type and width errors exactly.
        _require_same_width(a, b)
    if (a.anchor ^ b.anchor) & ~(a.free_mask | b.free_mask):
        return None
    return _derived_cube(a.n, a.anchor | b.anchor, a.free_mask & b.free_mask)


def difference(a: Cube, b: Cube) -> Tuple[Cube, ...]:
    """A disjoint exact cover of ``a`` minus ``b``.

    When the cubes are compatible the coordinates free in ``a`` but fixed by
    ``b`` are split in ascending order. Each split emits the branch opposite
    ``b`` and descends the matching branch; the final portion lies inside ``b``
    and is discarded.
    """

    _require_same_width(a, b)
    if not compatible(a, b):
        return (a,)
    split = a.free_mask & b.fixed_mask
    if split == 0:
        # Every coordinate fixed by b is fixed and agreeing in a, so a is inside b.
        return ()
    pieces = []
    anchor = a.anchor
    free = a.free_mask
    for i in range(a.n):
        bit = 1 << i
        if not (split & bit):
            continue
        matching = (b.anchor >> i) & 1
        remaining = free & ~bit
        opposite_anchor = anchor if matching else anchor | bit
        # ``bit`` is free in ``a`` and is removed from ``remaining``, so the
        # anchor and the free mask stay disjoint and neither leaves the
        # universe; the invariant is proved rather than rechecked.
        pieces.append(_derived_cube(a.n, opposite_anchor, remaining))
        anchor = anchor | bit if matching else anchor
        free = remaining
    return tuple(pieces)


def restrict(cube: Cube, coordinate: int, value: int) -> Optional[Cube]:
    """Fix one coordinate inside the original coordinate space.

    The width is preserved; a contradicting fixed coordinate yields ``None``.
    """

    if not isinstance(cube, Cube):
        raise TypeError("restrict requires a Cube")
    _require_index(coordinate, "coordinate")
    if coordinate >= cube.n:
        raise ValueError(f"coordinate {coordinate} is outside a {cube.n} bit universe")
    if value not in (0, 1) or isinstance(value, bool):
        raise ValueError("value must be the integer 0 or 1")
    bit = 1 << coordinate
    if cube.free_mask & bit:
        # ``bit`` moves from the free mask to the anchor, so the two stay
        # disjoint and neither grows past the universe.
        return _derived_cube(
            cube.n, cube.anchor | (bit if value else 0), cube.free_mask ^ bit
        )
    return cube if ((cube.anchor >> coordinate) & 1) == value else None


def split(cube: Cube, coordinate: int) -> Tuple[Cube, Cube]:
    """Both cofactors of a coordinate that is free in ``cube``.

    This is ``(restrict(cube, coordinate, 0), restrict(cube, coordinate, 1))``
    for a coordinate the caller already knows to be free, which is the only
    case the comparison splitter of ``direct_constraints`` ever needs. It
    exists so that splitter does not restate the cofactor algebra: the owner of
    the cube representation stays the only place that builds a cube. The two
    parts partition ``cube`` exactly, so a cover built from them is unchanged.
    """

    if not isinstance(cube, Cube):
        raise TypeError("split requires a Cube")
    _require_index(coordinate, "coordinate")
    if coordinate >= cube.n:
        raise ValueError(f"coordinate {coordinate} is outside a {cube.n} bit universe")
    bit = 1 << coordinate
    if not (cube.free_mask & bit):
        raise ValueError(f"coordinate {coordinate} is not free in {cube.label()}")
    remaining = cube.free_mask ^ bit
    anchor = cube.anchor
    return (
        _derived_cube(cube.n, anchor, remaining),
        _derived_cube(cube.n, anchor | bit, remaining),
    )


def normalise_cover(
    cubes: Sequence[Cube], meter: Optional["Meter"] = None
) -> Tuple[Cube, ...]:
    """Deterministic order with exact duplicates removed.

    Alternatives may overlap. Their cardinalities are not summed and
    disjointness is not asserted. A meter may be supplied so that a long
    normalisation is interrupted by the deadline rather than running past it.
    """

    # A cover that is already in the canonical order is returned untouched. A
    # relation cover is normalised once when it is built and again when it is
    # handed to ``Leaf``, and without this the second pass repeats the sort and
    # rebuilds the set for nothing. The scan below is one pass and allocates
    # nothing; anything it cannot certify falls through to the full path, which
    # is also what raises the documented type and width errors.
    ordered = tuple(cubes)
    if len(ordered) > 1:
        previous = None
        canonical = True
        for index, cube in enumerate(ordered):
            if meter is not None and not index % 256:
                meter.check_time()
            if cube.__class__ is not Cube or cube.n != ordered[0].n:
                canonical = False
                break
            key = (cube.anchor, -cube.free_mask.bit_count(), cube.free_mask)
            if previous is not None and key <= previous:
                canonical = False
                break
            previous = key
        if canonical:
            return ordered

    seen = set()
    unique = []
    for index, cube in enumerate(ordered):
        if meter is not None and not index % 256:
            meter.check_time()
        if not isinstance(cube, Cube):
            raise TypeError("a cover holds Cube members")
        key = (cube.n, cube.anchor, cube.free_mask)
        if key in seen:
            continue
        seen.add(key)
        unique.append(cube)
    widths = {cube.n for cube in unique}
    if len(widths) > 1:
        raise ValueError(f"a cover mixes widths {sorted(widths)}")
    unique.sort(key=lambda c: (c.anchor, -c.free_mask.bit_count(), c.free_mask))
    return tuple(unique)


def min_member(cover: Sequence[Cube]) -> Optional[int]:
    """The smallest index of a nonempty cover, or ``None`` for the empty set.

    The smallest member of a cube is its anchor, since every free coordinate
    contributes a nonnegative weight.
    """

    best = None
    for cube in cover:
        if not isinstance(cube, Cube):
            raise TypeError("a cover holds Cube members")
        if best is None or cube.anchor < best:
            best = cube.anchor
    return best


def cover_contains(cover: Sequence[Cube], index: int) -> bool:
    return any(cube.contains(index) for cube in cover)


# --------------------------------------------------------------------------
# Fields
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Field:
    """A contiguous bit range of the index, read LSB-first within the field."""

    name: str
    offset: int
    width: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError("a field requires a non-empty name")
        _require_index(self.offset, "offset")
        _require_index(self.width, "width", minimum=1)

    @property
    def mask(self) -> int:
        return ((1 << self.width) - 1) << self.offset

    @property
    def limit(self) -> int:
        """One past the largest value the field can hold."""

        return 1 << self.width

    def end(self) -> int:
        return self.offset + self.width

    def fits(self, n: int) -> bool:
        _require_index(n, "n")
        return self.end() <= n

    def decode(self, index: int) -> int:
        _require_index(index, "index")
        return (index >> self.offset) & ((1 << self.width) - 1)

    def encode(self, value: int) -> int:
        _require_index(value, "value")
        if value >= self.limit:
            raise ValueError(f"value {value} does not fit field {self.name!r} of width {self.width}")
        return value << self.offset


def _require_field_fits(field: Field, n: int) -> None:
    if not isinstance(field, Field):
        raise TypeError("expected a Field")
    if not field.fits(n):
        raise ValueError(
            f"field {field.name!r} ends at bit {field.end()}, past the {n} bit universe"
        )


def interval(field: Field, lo: int, hi: int, n: int) -> Tuple[Cube, ...]:
    """An exact cover of the inclusive unsigned range ``lo <= field <= hi``.

    Every coordinate outside the field stays free. The cover is a disjoint
    decomposition into aligned binary blocks, in increasing value order.
    """

    _require_field_fits(field, n)
    _require_index(lo, "lo")
    _require_index(hi, "hi")
    top = field.limit - 1
    if hi > top:
        hi = top
    if lo > hi:
        return ()
    limit = universe_mask(n)
    outside = limit ^ field.mask
    cubes = []
    value = lo
    while value <= hi:
        block = 0
        while block < field.width:
            size = 1 << (block + 1)
            if value % size != 0 or value + size - 1 > hi:
                break
            block += 1
        free_low = (1 << block) - 1
        anchor = (value & ~free_low) << field.offset
        # The anchor lies inside the field mask above the block's free bits, so
        # it is disjoint from both ``outside`` and the shifted block, and the
        # field was checked to fit the universe.
        cubes.append(_derived_cube(n, anchor, outside | (free_low << field.offset)))
        value += 1 << block
    return tuple(cubes)


def domain(field: Field, size: int, n: int) -> Tuple[Cube, ...]:
    """The cover of the valid codes ``0 <= field < size``.

    A domain whose size is not a power of two leaves unusable high codes. Those
    codes are excluded here and must never appear in a witness.
    """

    _require_index(size, "size", minimum=1)
    if size > field.limit:
        raise ValueError(
            f"domain size {size} exceeds field {field.name!r} of width {field.width}"
        )
    return interval(field, 0, size - 1, n)


# --------------------------------------------------------------------------
# Expressions
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class Leaf:
    """An exact cover of one relation. ``Leaf(())`` is false."""

    cubes: Tuple[Cube, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "cubes", normalise_cover(tuple(self.cubes)))

    @property
    def width(self) -> Optional[int]:
        return self.cubes[0].n if self.cubes else None


@dataclass(frozen=True)
class AllOf:
    """Every child must hold. ``AllOf(())`` is true."""

    children: Tuple["Expression", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "children", _checked_children(self.children))


@dataclass(frozen=True)
class AnyOf:
    """At least one child must hold. ``AnyOf(())`` is false."""

    children: Tuple["Expression", ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, "children", _checked_children(self.children))


Expression = Union[Leaf, AllOf, AnyOf]


def _checked_children(children) -> Tuple["Expression", ...]:
    children = tuple(children)
    widths = set()
    for child in children:
        if not isinstance(child, (Leaf, AllOf, AnyOf)):
            raise TypeError(f"expected an expression, got {type(child).__name__}")
        width = expression_width(child)
        if width is not None:
            widths.add(width)
    if len(widths) > 1:
        raise ValueError(f"an expression mixes widths {sorted(widths)}")
    return children


def expression_width(expression: "Expression") -> Optional[int]:
    """The universe width implied by an expression, or ``None`` if unconstrained.

    The first width found in pre-order, exactly as the recursive definition
    returned the first non-``None`` child. Walked with an explicit stack: this
    runs once per child every time a node is constructed, so a deep conjunction
    used to recurse its whole depth at each level and could exhaust the
    interpreter's recursion limit while merely being built.
    """

    stack = [expression]
    while stack:
        node = stack.pop()
        if isinstance(node, Leaf):
            if node.cubes:
                return node.cubes[0].n
        elif isinstance(node, (AllOf, AnyOf)):
            stack.extend(reversed(node.children))
        else:
            raise TypeError(f"expected an expression, got {type(node).__name__}")
    return None


def count_records(expression: "Expression") -> int:
    """Expression records: one per node plus one per cube alternative.

    Counted with an explicit stack rather than by recursion. The total is
    identical; a deep conjunction no longer pays Python's call overhead per
    node, and the walk cannot exhaust the interpreter's recursion limit.
    """

    total = 0
    stack = [expression]
    while stack:
        node = stack.pop()
        if isinstance(node, Leaf):
            total += 1 + len(node.cubes)
        elif isinstance(node, (AllOf, AnyOf)):
            total += 1
            stack.extend(node.children)
        else:
            raise TypeError(f"expected an expression, got {type(node).__name__}")
    return total


def true_leaf(n: int) -> Leaf:
    return Leaf((universe(n),))


def false_leaf() -> Leaf:
    return Leaf(())


# --------------------------------------------------------------------------
# Budgets
# --------------------------------------------------------------------------


class BudgetExhausted(Exception):
    """A declared limit stopped the work before it completed.

    This is always reported as ``UNKNOWN``. It is never reported as ``UNSAT``.
    """

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


@dataclass(frozen=True)
class Budget:
    """The resource limits of one query, per plan section 5.5."""

    seconds: float = 0.1
    max_cover: int = 4096
    max_visited: int = 50000
    max_records: int = 20000

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, (int, float)) or isinstance(self.seconds, bool):
            raise TypeError("seconds must be a number")
        if self.seconds <= 0:
            raise ValueError("seconds must be positive")
        for name in ("max_cover", "max_visited", "max_records"):
            _require_index(getattr(self, name), name, minimum=1)

    def start(self) -> "Meter":
        return Meter(self)


DEFAULT_BUDGET = Budget()


class Meter:
    """The running cost of one query.

    A meter is shared between construction and solving so that building the
    acceptance expression is guarded by the same budget that guards the search.
    """

    def __init__(self, budget: Budget) -> None:
        if not isinstance(budget, Budget):
            raise TypeError("a meter requires a Budget")
        self.budget = budget
        self.started = time.monotonic()
        self.visited = 0
        self.records = 0
        self.intersections = 0
        # Expressions this meter has already been billed for, keyed by object
        # identity. The value keeps a reference alive so the identity cannot be
        # reused by a later object.
        self._charged: Dict[int, object] = {}

    @property
    def started(self) -> float:
        return self._started

    @started.setter
    def started(self, value: float) -> None:
        """Move the start, and the deadline derived from it, together.

        ``check_time`` compares the clock against a precomputed deadline rather
        than recomputing ``elapsed > budget.seconds``: it is consulted tens of
        millions of times in a single search. The two must never drift apart,
        and tests that age a meter by assigning to ``started`` must keep
        working, so the deadline is maintained here rather than only at
        construction.
        """

        self._started = value
        self._deadline = value + self.budget.seconds

    @property
    def elapsed(self) -> float:
        return time.monotonic() - self._started

    @property
    def remaining(self) -> float:
        return self.budget.seconds - self.elapsed

    def check_time(self) -> None:
        if time.monotonic() > self._deadline:
            raise BudgetExhausted("time budget exhausted")

    def visit(self, count: int = 1) -> None:
        self.visited += count
        if self.visited > self.budget.max_visited:
            raise BudgetExhausted("visited-cube budget exhausted")
        if time.monotonic() > self._deadline:
            raise BudgetExhausted("time budget exhausted")

    def record(self, count: int = 1) -> None:
        self.records += count
        if self.records > self.budget.max_records:
            raise BudgetExhausted("expression-record budget exhausted")
        if time.monotonic() > self._deadline:
            raise BudgetExhausted("time budget exhausted")

    def intersection(self, count: int = 1) -> None:
        self.intersections += count
        if time.monotonic() > self._deadline:
            raise BudgetExhausted("time budget exhausted")

    def node(self, count: int = 1) -> None:
        """Charge expression nodes as they are built.

        A node costs a record just as a cube alternative does, so an expression
        whose node count alone exceeds the cap is stopped while it is being
        assembled rather than after it has been returned.
        """

        self.record(count)

    def charge_expression(self, expression: object) -> None:
        """Bill an expression once, however many times it is handed over.

        Construction and solving share a meter. Charging the whole record count
        again at the start of a search would double-bill everything the builder
        already paid for, and could report exhaustion on an expression that fits.
        """

        key = id(expression)
        # Reusing paid work does not revive a meter exhausted by another
        # expression. Check the record cap as well as the clock on cache hits.
        self.record(0)
        if key in self._charged:
            return
        self.record(count_records(expression))
        # Failed charges must never grant the cached, already-paid status.
        self._charged[key] = expression

    def mark_charged(self, expression: object) -> None:
        """Record that this expression was billed as it was constructed."""

        self._charged[id(expression)] = expression

    def cover_limit(self, size: int) -> None:
        """Validate a cover size against the cap, charging nothing.

        This exists so that a structure still being built can be checked on
        every growth step. Charging records here as well would bill the same
        cover once per member and again at the end.
        """

        if size > self.budget.max_cover:
            raise BudgetExhausted("atomic relation cover budget exhausted")

    def cover(self, size: int) -> None:
        """Check and charge a completed cover."""

        self.cover_limit(size)
        self.record(size)

    def counters(self) -> Dict[str, int]:
        return {
            "visited": self.visited,
            "records": self.records,
            "intersections": self.intersections,
        }


# --------------------------------------------------------------------------
# Queries
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class QueryResult:
    """The outcome of one exact query.

    ``SAT`` carries a cube wholly inside the acceptance set. ``UNSAT`` means
    this query's declared domains and context were completely exhausted.
    Budget exhaustion is ``UNKNOWN`` and must never be read as ``UNSAT``.
    """

    status: str
    cube: Optional[Cube] = None
    reason: Optional[str] = None
    elapsed: float = 0.0
    visited: int = 0
    counters: Dict[str, int] = _dataclass_field(default_factory=dict)

    @property
    def is_sat(self) -> bool:
        return self.status == SAT

    @property
    def is_unsat(self) -> bool:
        return self.status == UNSAT

    @property
    def is_unknown(self) -> bool:
        return self.status == UNKNOWN

    def to_dict(self) -> Dict[str, object]:
        payload: Dict[str, object] = {
            "status": self.status,
            "elapsed": self.elapsed,
            "visited": self.visited,
            "counters": dict(self.counters),
        }
        if self.cube is not None:
            payload["anchor"] = self.cube.anchor
            payload["free_mask"] = self.cube.free_mask
            payload["width"] = self.cube.n
        if self.reason is not None:
            payload["reason"] = self.reason
        return payload


def _check_expression_width(expression: "Expression", n: int) -> None:
    width = expression_width(expression)
    if width is not None and width != n:
        raise ValueError(f"expression width {width} does not match the {n} bit universe")


def _check_incoming_leaves(expression: "Expression", meter: "Meter") -> None:
    """Validate every leaf cover the query was handed.

    A leaf built elsewhere can be arbitrarily large. Without this, a query
    could be answered from a cover that exceeds the declared atomic-relation
    cap, which would report SAT where the budget says the work was never
    licensed. Exhaustion is reported as UNKNOWN by the caller.
    """

    stack = [expression]
    while stack:
        meter.check_time()
        node = stack.pop()
        if isinstance(node, Leaf):
            meter.cover_limit(len(node.cubes))
        elif isinstance(node, (AllOf, AnyOf)):
            stack.extend(node.children)


def solve(
    expression: "Expression",
    n: int,
    budget: Optional[Budget] = None,
    meter: Optional[Meter] = None,
) -> QueryResult:
    """Answer one query by lazy depth-first intersection.

    The search keeps a current cube and an ordered list of pending predicates.
    A conjunction places its children in front of the pending list, so earlier
    predicates narrow the cube before later ones are touched. A disjunction
    branches over its children in order. A leaf intersects the current cube
    with each alternative in turn. An accepting cube is returned only when the
    pending list is empty, that is once every required predicate has been
    satisfied; the cube is therefore wholly inside the acceptance set.

    No Cartesian product of constraint families or candidate assignments is
    ever materialised.

    Two representation choices, neither of which changes the order in which
    states are explored or the answer that is returned:

    * The pending list is a chain of ``(head, tail)`` pairs rather than a
      tuple. Placing a conjunction's children in front used to copy the whole
      remaining list, which made a deep conjunction quadratic in its depth;
      building a chain is one pair per child.
    * A leaf charges the meter once for its whole cover instead of once per
      alternative. The count the meter accumulates is identical. The clock is
      therefore consulted before a cover is scanned rather than inside the
      scan, so a deadline can overshoot by at most one cover — itself capped at
      ``max_cover`` alternatives, and already validated against that cap before
      the search starts. Every popped state still checks the clock through
      ``visit``.
    """

    _require_index(n, "n")
    meter = meter if meter is not None else (budget or DEFAULT_BUDGET).start()
    try:
        _check_expression_width(expression, n)
        _check_incoming_leaves(expression, meter)
        # Idempotent: an expression this meter already paid to build is not
        # billed again, while an externally supplied one still is.
        meter.charge_expression(expression)
        stack = [(universe(n), (expression, None))]
        while stack:
            meter.visit()
            cube, pending = stack.pop()
            if pending is None:
                return QueryResult(SAT, cube, None, meter.elapsed, meter.visited, meter.counters())
            head, rest = pending
            if isinstance(head, AllOf):
                chain = rest
                for child in reversed(head.children):
                    chain = (child, chain)
                stack.append((cube, chain))
            elif isinstance(head, AnyOf):
                for child in reversed(head.children):
                    stack.append((cube, (child, rest)))
            elif isinstance(head, Leaf):
                alternatives = head.cubes
                meter.intersection(len(alternatives))
                anchor = cube.anchor
                free = cube.free_mask
                survivors = []
                for alternative in alternatives:
                    # ``intersect`` inlined over a fixed left operand: the two
                    # cubes are members of the same query, so they share a
                    # width and the type check cannot fail.
                    if (anchor ^ alternative.anchor) & ~(free | alternative.free_mask):
                        continue
                    survivors.append(
                        (
                            _derived_cube(
                                cube.n,
                                anchor | alternative.anchor,
                                free & alternative.free_mask,
                            ),
                            rest,
                        )
                    )
                stack.extend(reversed(survivors))
            else:
                raise TypeError(f"expected an expression, got {type(head).__name__}")
        return QueryResult(UNSAT, None, None, meter.elapsed, meter.visited, meter.counters())
    except BudgetExhausted as exc:
        return QueryResult(UNKNOWN, None, exc.reason, meter.elapsed, meter.visited, meter.counters())
