"""Standalone direct-index compiler for the Luminal machine.

Assembled from the sources listed below. Do not edit this copy; edit the
sources and export again. Standard library only, beside the supplied
machine module.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import dataclass, asdict
from dataclasses import dataclass, field as _dataclass_field
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple
from typing import Dict, Iterator, Optional, Sequence, Tuple, Union
from typing import Dict, List, Optional, Sequence, Tuple
import hashlib
import json
import machine
import sys
import time

import sys as _sys

# Each module name is bound to this assembled module, so a qualified call
# such as dc.footprint(...) stays an attribute lookup and cannot be
# shadowed by a local variable of the same name.
_self = _sys.modules[__name__]
si = _self
dc = _self
dk = _self
schema_index = _self
direct_contract = _self
direct_constraints = _self
direct_optimizer = _self
direct_compiler = _self

# Source provenance:
# schema_index.py: SHA256 f7bec20681cec044bc0c550b319dddee6acd325e2338a11810209c972e660820
# direct_contract.py: SHA256 3b37ad0e7f5feb8ac464b074ebd8e8c6ab079c79ada3ab1bacc4b2a9f1a83fa8
# direct_constraints.py: SHA256 8743e82f75356de4be8b622a73c0f24e9c58536e2695184b87f5d3470299f376
# direct_optimizer.py: SHA256 a5f71a407418121a39c98e5ccc87036ef7732df2e81c2082fad285869e755d27
# direct_compiler.py: SHA256 523fccd16b6d7dd9d4c9589e3a8ea3caeacc29decce0a470582dd8d7be60fe7a

# ---- schema_index.py -----------------------------------------------
SAT = "SAT"

UNSAT = "UNSAT"

UNKNOWN = "UNKNOWN"

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
                # The cover was charged before it was scanned, so the clock has
                # not been read since. Read it now. Usually the next popped
                # state would, but when this scan leaves no survivor and empties
                # the stack there is no next state, and the loop would fall
                # through to a verdict of UNSAT — a positive claim that the
                # declared domain holds no solution — using time the query did
                # not have. Checking here bounds the overrun to exactly one
                # cover, which is itself capped at ``max_cover`` and validated
                # against that cap before the search starts.
                meter.check_time()
            else:
                raise TypeError(f"expected an expression, got {type(head).__name__}")
        # Defence in depth for the branches that empty the stack without
        # scanning anything, such as a disjunction with no children: no
        # completed verdict is certified on a meter whose deadline has passed.
        meter.check_time()
        return QueryResult(UNSAT, None, None, meter.elapsed, meter.visited, meter.counters())
    except BudgetExhausted as exc:
        return QueryResult(UNKNOWN, None, exc.reason, meter.elapsed, meter.visited, meter.counters())

# ---- direct_contract.py --------------------------------------------
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

# ---- direct_constraints.py -----------------------------------------
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

# ---- direct_optimizer.py -------------------------------------------
WINDOW_SIZE = 4

_RESERVE_SECONDS = 1.0

def _digest(times: Dict[int, int], addresses: Dict[str, int]) -> str:
    payload = repr((sorted(times.items()), sorted(addresses.items()))).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:16]

def targets_for(facts: dc.ProgramFacts, cycles: int, memory: int) -> List[Tuple[int, int]]:
    """The target pairs of section 5.4, in their declared order."""

    product = cycles * memory
    cycle_floor = facts.cycle_lower_bound()
    memory_floor = facts.memory_lower_bound()

    candidates: List[Tuple[int, int]] = [(cycles - 1, memory), (cycles, memory - 1)]
    candidates.append((cycles + 1, (product - 1) // (cycles + 1)))
    if cycles - 1 > 0:
        candidates.append(
            (cycles - 1, min(machine.SCRATCH_WORDS, (product - 1) // (cycles - 1)))
        )

    chosen: List[Tuple[int, int]] = []
    for target_cycles, target_memory in candidates:
        if target_cycles < 1 or target_memory < 1:
            continue
        if target_cycles < cycle_floor or target_memory < memory_floor:
            continue
        if target_cycles > facts.horizon:
            continue
        if target_memory > machine.SCRATCH_WORDS:
            continue
        if target_cycles * target_memory >= product:
            continue
        if (target_cycles, target_memory) in chosen:
            continue
        chosen.append((target_cycles, target_memory))
    return chosen

def windows_for(
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    scratch_first: bool,
) -> List[Tuple[int, ...]]:
    """The candidate windows of section 5.4, deduplicated in order."""

    latest = sorted(range(facts.count), key=lambda op_id: (-times[op_id], op_id))
    time_window = tuple(sorted(latest[:WINDOW_SIZE]))

    highest = sorted(
        facts.value_names,
        key=lambda name: (-(addresses[name] + facts.width[name]), facts.producers[name]),
    )
    scratch_window = tuple(
        sorted({facts.producers[name] for name in highest[:WINDOW_SIZE]})
    )

    # Starts advance by two and each window is truncated at the operation
    # count, which keeps the final nonempty shorter window. Breaking out as
    # soon as a full window reached the end would drop that tail: for six
    # operations it would omit (4, 5).
    source: List[Tuple[int, ...]] = []
    for start in range(0, facts.count, 2):
        candidate = tuple(range(start, min(start + WINDOW_SIZE, facts.count)))
        if candidate:
            source.append(candidate)

    ordered: List[Tuple[int, ...]] = []
    leading = [scratch_window, time_window] if scratch_first else [time_window, scratch_window]
    for window in leading + source:
        if window and window not in ordered:
            ordered.append(window)
    return ordered

def optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    limits,
    deadline,
    counters,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the incumbent through bounded joint queries.

    Returns the best validated schedule and allocation together with a record
    of what was attempted. The incumbent passed in has already been validated
    by the caller, so returning it unchanged is always safe.
    """

    statuses = {
        "SAT": 0,
        "UNSAT": 0,
        "UNKNOWN_CONSTRUCTION": 0,
        "UNKNOWN_SEARCH": 0,
        "INFEASIBLE": 0,
    }
    reasons: Dict[str, int] = {}
    improvements: List[dict] = []
    validation_errors: List[dict] = []
    target_discrepancies: List[dict] = []
    attempted: set = set()
    stopped = "pass_complete"
    started = deadline.elapsed
    # Created here and discarded with this compilation, so nothing is shared
    # between programs and no process-global state accumulates. A hit is
    # charged the visits and records its miss cost, so reuse never buys budget.
    cache = dk.CoverCache()

    allowance = min(
        limits.optimise_seconds, deadline.seconds - started - _RESERVE_SECONDS
    )
    horizon = started + allowance

    best_times = dict(times)
    best_addresses = dict(addresses)

    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = _digest(best_times, best_addresses)

        for target_cycles, target_memory in targets_for(facts, cycles, memory):
            windows = windows_for(
                facts, best_times, best_addresses, scratch_first=target_memory < memory
            )
            for window in windows:
                if len(attempted) >= limits.max_queries:
                    stopped = "query_cap"
                    break
                if deadline.elapsed >= horizon:
                    stopped = "deadline"
                    break
                key = (digest, window, target_cycles, target_memory)
                if key in attempted:
                    continue
                # An attempted query is one whose construction has started.
                attempted.add(key)

                remaining = min(limits.query_seconds, horizon - deadline.elapsed)
                if remaining <= 0:
                    stopped = "deadline"
                    break
                meter = si.Budget(
                    seconds=remaining,
                    max_cover=limits.max_cover,
                    max_visited=limits.max_visited,
                    max_records=limits.max_records,
                ).start()

                try:
                    query = dk.JointQuery(
                        facts,
                        best_times,
                        best_addresses,
                        window,
                        target_cycles,
                        target_memory,
                        meter,
                        cache,
                    )
                    expression = query.expression()
                except dk.Infeasible:
                    statuses["INFEASIBLE"] += 1
                    continue
                except si.BudgetExhausted as exc:
                    # The expression could not even be built within budget.
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    reasons[exc.reason] = reasons.get(exc.reason, 0) + 1
                    continue

                result = si.solve(expression, query.n, meter=meter)
                counters.absorb(meter, 0)
                if result.is_unknown:
                    # Budget exhaustion is not a statement about solutions.
                    statuses["UNKNOWN_SEARCH"] += 1
                    # Which declared limit stopped the search is a diagnostic
                    # worth keeping: a search that now stops on the visited-cube
                    # cap rather than the clock has explored more of its space,
                    # not less, and reached that cap sooner in wall-clock time.
                    if result.reason:
                        reasons[result.reason] = reasons.get(result.reason, 0) + 1
                    continue
                if result.is_unsat:
                    # Only this neighbourhood is excluded, nothing wider.
                    statuses["UNSAT"] += 1
                    continue

                statuses["SAT"] += 1
                try:
                    candidate_times, candidate_addresses = query.decode(result.cube)
                    dc.check_feasible(facts, candidate_times, candidate_addresses)
                    compiled = dc.compilation(facts, candidate_times, candidate_addresses)
                    machine.check_compilation(program, compiled)
                except (ValueError, dc.ContractError, machine.CompileError) as exc:
                    # The query said this witness meets the criteria and the
                    # validator disagrees. That is a defect: record it, keep
                    # the incumbent, and let the release verifier fail.
                    validation_errors.append(
                        {
                            "window": list(window),
                            "target": [target_cycles, target_memory],
                            "error": str(exc),
                        }
                    )
                    continue

                actual_cycles = len(compiled["bundles"])
                actual_memory = dc.footprint(facts, candidate_addresses)
                actual_product = actual_cycles * actual_memory

                # The acceptance expression encodes both target bounds, so a
                # satisfying witness that misses either one is a disagreement
                # between the query and the measurement, not an ordinary
                # unsuccessful optimisation. Record it; the release gate fails
                # on it. Measuring first and rejecting on product alone would
                # hide the defect, because every generated target already
                # requires a strict product improvement.
                if actual_cycles > target_cycles or actual_memory > target_memory:
                    target_discrepancies.append(
                        {
                            "window": list(window),
                            "target": [target_cycles, target_memory],
                            "actual_cycles": actual_cycles,
                            "actual_memory": actual_memory,
                            "reason": (
                                f"witness satisfied the query but measured "
                                f"({actual_cycles}, {actual_memory}) against target "
                                f"({target_cycles}, {target_memory})"
                            ),
                        }
                    )
                    continue

                if actual_product >= product:
                    # Within target, but not a strict improvement of the
                    # measured product. Nothing is accepted, and this is not a
                    # discrepancy.
                    continue

                improvements.append(
                    {
                        "window": list(window),
                        "target": [target_cycles, target_memory],
                        "from": {"cycles": cycles, "footprint": memory, "product": product},
                        "to": {
                            "cycles": actual_cycles,
                            "footprint": actual_memory,
                            "product": actual_product,
                        },
                    }
                )
                best_times = candidate_times
                best_addresses = candidate_addresses
                improved = True
                break
            if improved or stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    record = {
        "enabled": True,
        "attempted_queries": len(attempted),
        "statuses": statuses,
        "unknown_reasons": reasons,
        "accepted": len(improvements),
        "improvements": improvements,
        "validation_errors": validation_errors,
        "target_discrepancies": target_discrepancies,
        "discrepancy_count": len(validation_errors) + len(target_discrepancies),
        "stopped_because": stopped,
        "cover_cache": cache.statistics(),
        "seconds": deadline.elapsed - started,
        "allowance_seconds": allowance,
    }
    return best_times, best_addresses, record

# ---- direct_compiler.py --------------------------------------------
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
            # ``difference`` performs the compatibility test itself and returns
            # the member untouched when the two cannot meet, which is exactly
            # what the separate test used to arrange. Asking twice computed the
            # same predicate twice for every member of every cover.
            survivors.extend(si.difference(member, cube))
        meter.cover(len(survivors))
        current = tuple(survivors)
        if not current:
            break
    return current

def _overlap(first: Tuple[int, int], second: Tuple[int, int]) -> bool:
    """Inclusive live intervals touch."""

    return first[0] <= second[1] and second[0] <= first[1]

def _earliest_cycle(
    facts: dc.ProgramFacts,
    op_id: int,
    lower: int,
    full_cycles: Dict[str, List[int]],
    field: si.Field,
    width: int,
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

    # The cycles on which this engine is already at capacity, kept sorted by
    # the caller as they fill. Rescanning the whole calendar and sorting it
    # once per operation made the schedule quadratic in the program's length
    # for no gain: the same set is available by slicing from ``lower``.
    occupied = full_cycles.get(engine)
    if occupied:
        start = 0
        for start, cycle in enumerate(occupied):
            if cycle >= lower:
                break
        else:
            start = len(occupied)
        blocked = occupied[start:]
    else:
        blocked = []
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
    # Per engine, the cycles already at capacity, held sorted. This is the same
    # information the calendar carries, indexed the way the scheduling query
    # asks for it.
    full_cycles: Dict[str, List[int]] = {}
    # The time field does not change between operations, so it is built once
    # rather than revalidated for every query.
    width = dc.time_width(facts.horizon)
    field = si.Field("t", 0, width)
    for op_id in range(facts.count):
        lower = 0
        for predecessor, lag in facts.predecessors[op_id].items():
            candidate = times[predecessor] + lag
            if candidate > lower:
                lower = candidate
        try:
            cycle = _earliest_cycle(
                facts, op_id, lower, full_cycles, field, width,
                deadline.budget(limits), counters,
            )
        except si.BudgetExhausted as exc:
            raise CompilationFailure(
                f"scheduling query for operation {op_id} exhausted its budget: {exc.reason}"
            ) from exc
        times[op_id] = cycle
        engine = facts.engine[op_id]
        key = (engine, cycle)
        used = calendar.get(key, 0) + 1
        calendar[key] = used
        if used == machine.ENGINE_LIMITS[engine]:
            # Kept in increasing order, which is the order the query wants and
            # the order the old whole-calendar sort produced. A cycle reaches
            # capacity exactly once, so this inserts each cycle once.
            occupied = full_cycles.setdefault(engine, [])
            position = len(occupied)
            while position and occupied[position - 1] > cycle:
                position -= 1
            occupied.insert(position, cycle)
    return times

def _lowest_address(
    facts: dc.ProgramFacts,
    name: str,
    live: Dict[str, Tuple[int, int]],
    placed: Sequence[str],
    addresses: Dict[str, int],
    field: si.Field,
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
    universe = dc.ADDRESS_WIDTH
    cap = machine.SCRATCH_WORDS - width

    own_start, own_end = live[name]
    overlapping = [
        other
        for other in placed
        if own_start <= live[other][1] and live[other][0] <= own_end
    ]
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
    # One address field for every allocation query; it never varies.
    field = si.Field("a", 0, dc.ADDRESS_WIDTH)
    for name in order:
        try:
            addresses[name] = _lowest_address(
                facts, name, live, placed, addresses, field,
                deadline.budget(limits), counters,
            )
        except si.BudgetExhausted as exc:
            raise CompilationFailure(
                f"allocation query for {name!r} exhausted its budget: {exc.reason}"
            ) from exc
        placed.append(name)
    return addresses

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
        # (export) the module is bound to this file at the top.

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
    raise SystemExit(main(_sys.argv[1:]))
