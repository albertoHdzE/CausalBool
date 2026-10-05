"""Instruction scheduling and scratch allocation for the Luminal machine.

Usage:  python3 compiler.py <program.json>   (schedule JSON on stdout only)

1. Facts.        Dependencies, engine capacities, value sizes and lifetimes
                 are derived from the program and the machine contract.
2. Construction. Operations are placed in source order. Each operation is
                 issued at the earliest cycle that its operands and engine
                 capacity allow, and each result takes the lowest aligned
                 address that is free for its whole lifetime.
3. Improvement.  A bounded search re-times small windows of operations,
                 re-assigns their addresses and lanes, and accepts a change
                 only when it is independently validated and strictly lowers
                 cycles x scratch footprint. It stops after 0.1 s and keeps
                 the best validated schedule found.

Standard library only, beside the supplied machine module.
"""

from __future__ import annotations

import bisect
import hashlib
import heapq
import json
import machine
import sys
import time
from collections import deque
from dataclasses import asdict
from dataclasses import dataclass
from dataclasses import field as _dataclass_field
from dataclasses import field as _field
from typing import Callable
from typing import Dict
from typing import Iterator
from typing import List
from typing import Optional
from typing import Sequence
from typing import Tuple
from typing import Union

OPTIMISATION_SECONDS = 0.1


SAT = 'SAT'
UNSAT = 'UNSAT'
UNKNOWN = 'UNKNOWN'

def _idx_plain_int(value: object) -> bool:
    """A genuine integer. Booleans are rejected where integers are required."""
    return isinstance(value, int) and (not isinstance(value, bool))

def _require_index(value: object, name: str, minimum: int=0) -> int:
    if not _idx_plain_int(value):
        raise TypeError(f'{name} must be a plain integer, not {type(value).__name__}')
    if value < minimum:
        raise ValueError(f'{name} must be at least {minimum}, got {value}')
    return int(value)

def universe_mask(n: int) -> int:
    _require_index(n, 'n')
    return (1 << n) - 1

@dataclass(frozen=True)
class Cube:
    """An immutable schema: a decimal anchor and its free-coordinate mask."""
    n: int
    anchor: int
    free_mask: int

    def __post_init__(self) -> None:
        _require_index(self.n, 'n')
        _require_index(self.anchor, 'anchor')
        _require_index(self.free_mask, 'free_mask')
        limit = universe_mask(self.n)
        if self.anchor > limit:
            raise ValueError(f'anchor {self.anchor} exceeds the {self.n} bit universe')
        if self.free_mask > limit:
            raise ValueError(f'free mask {self.free_mask} exceeds the {self.n} bit universe')
        if self.anchor & self.free_mask:
            raise ValueError('anchor and free mask must be disjoint')

    @property
    def universe(self) -> int:
        return universe_mask(self.n)

    @property
    def fixed_mask(self) -> int:
        return universe_mask(self.n) ^ self.free_mask

    @property
    def size(self) -> int:
        return 1 << self.free_mask.bit_count()

    def contains(self, index: int) -> bool:
        _require_index(index, 'index')
        if index > universe_mask(self.n):
            return False
        return index & self.fixed_mask == self.anchor

    def members(self) -> Iterator[int]:
        """Every filling of the free coordinates, in increasing numeric order."""
        positions = [i for i in range(self.n) if self.free_mask >> i & 1]
        for code in range(1 << len(positions)):
            offset = 0
            for j, position in enumerate(positions):
                if code >> j & 1:
                    offset |= 1 << position
            yield (self.anchor + offset)

    def label(self) -> str:
        marks = []
        for i in range(self.n):
            if self.free_mask >> i & 1:
                marks.append('*')
            else:
                marks.append('1' if self.anchor >> i & 1 else '0')
        return 'x0..x{}:{}'.format(max(self.n - 1, 0), ''.join(marks))

def _derived_cube(n: int, anchor: int, free_mask: int) -> Cube:
    """Build a cube whose invariant is already proved by its caller."""
    cube = object.__new__(Cube)
    object.__setattr__(cube, 'n', n)
    object.__setattr__(cube, 'anchor', anchor)
    object.__setattr__(cube, 'free_mask', free_mask)
    return cube

def universe(n: int) -> Cube:
    return Cube(n, 0, universe_mask(n))

def compatible(a: Cube, b: Cube) -> bool:
    """Whether two equal-width cubes intersect."""
    _require_same_width(a, b)
    limit = universe_mask(a.n)
    return (a.anchor ^ b.anchor) & (limit ^ (a.free_mask | b.free_mask)) == 0

def _require_same_width(a: Cube, b: Cube) -> None:
    if not isinstance(a, Cube) or not isinstance(b, Cube):
        raise TypeError('cube operations require Cube operands')
    if a.n != b.n:
        raise ValueError(f'cube widths differ: {a.n} and {b.n}')

def intersect(a: Cube, b: Cube) -> Optional[Cube]:
    if a.__class__ is not Cube or b.__class__ is not Cube or a.n != b.n:
        _require_same_width(a, b)
    if (a.anchor ^ b.anchor) & ~(a.free_mask | b.free_mask):
        return None
    return _derived_cube(a.n, a.anchor | b.anchor, a.free_mask & b.free_mask)

def difference(a: Cube, b: Cube) -> Tuple[Cube, ...]:
    _require_same_width(a, b)
    if not compatible(a, b):
        return (a,)
    split = a.free_mask & b.fixed_mask
    if split == 0:
        return ()
    pieces = []
    anchor = a.anchor
    free = a.free_mask
    for i in range(a.n):
        bit = 1 << i
        if not split & bit:
            continue
        matching = b.anchor >> i & 1
        remaining = free & ~bit
        opposite_anchor = anchor if matching else anchor | bit
        pieces.append(_derived_cube(a.n, opposite_anchor, remaining))
        anchor = anchor | bit if matching else anchor
        free = remaining
    return tuple(pieces)

def split(cube: Cube, coordinate: int) -> Tuple[Cube, Cube]:
    if not isinstance(cube, Cube):
        raise TypeError('split requires a Cube')
    _require_index(coordinate, 'coordinate')
    if coordinate >= cube.n:
        raise ValueError(f'coordinate {coordinate} is outside a {cube.n} bit universe')
    bit = 1 << coordinate
    if not cube.free_mask & bit:
        raise ValueError(f'coordinate {coordinate} is not free in {cube.label()}')
    remaining = cube.free_mask ^ bit
    anchor = cube.anchor
    return (_derived_cube(cube.n, anchor, remaining), _derived_cube(cube.n, anchor | bit, remaining))

def normalise_cover(cubes: Sequence[Cube], meter: Optional['Meter']=None) -> Tuple[Cube, ...]:
    """Deterministic order with exact duplicates removed."""
    ordered = tuple(cubes)
    if len(ordered) > 1:
        previous = None
        canonical = True
        for index, cube in enumerate(ordered):
            if meter is not None and (not index % 256):
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
        if meter is not None and (not index % 256):
            meter.check_time()
        if not isinstance(cube, Cube):
            raise TypeError('a cover holds Cube members')
        key = (cube.n, cube.anchor, cube.free_mask)
        if key in seen:
            continue
        seen.add(key)
        unique.append(cube)
    widths = {cube.n for cube in unique}
    if len(widths) > 1:
        raise ValueError(f'a cover mixes widths {sorted(widths)}')
    unique.sort(key=lambda c: (c.anchor, -c.free_mask.bit_count(), c.free_mask))
    return tuple(unique)

def min_member(cover: Sequence[Cube]) -> Optional[int]:
    best = None
    for cube in cover:
        if not isinstance(cube, Cube):
            raise TypeError('a cover holds Cube members')
        if best is None or cube.anchor < best:
            best = cube.anchor
    return best

@dataclass(frozen=True)
class Field:
    """A contiguous bit range of the index, read LSB-first within the field."""
    name: str
    offset: int
    width: int

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name:
            raise ValueError('a field requires a non-empty name')
        _require_index(self.offset, 'offset')
        _require_index(self.width, 'width', minimum=1)

    @property
    def mask(self) -> int:
        return (1 << self.width) - 1 << self.offset

    @property
    def limit(self) -> int:
        """One past the largest value the field can hold."""
        return 1 << self.width

    def end(self) -> int:
        return self.offset + self.width

    def fits(self, n: int) -> bool:
        _require_index(n, 'n')
        return self.end() <= n

    def decode(self, index: int) -> int:
        _require_index(index, 'index')
        return index >> self.offset & (1 << self.width) - 1

    def encode(self, value: int) -> int:
        _require_index(value, 'value')
        if value >= self.limit:
            raise ValueError(f'value {value} does not fit field {self.name!r} of width {self.width}')
        return value << self.offset

def _require_field_fits(field: Field, n: int) -> None:
    if not isinstance(field, Field):
        raise TypeError('expected a Field')
    if not field.fits(n):
        raise ValueError(f'field {field.name!r} ends at bit {field.end()}, past the {n} bit universe')

def interval(field: Field, lo: int, hi: int, n: int) -> Tuple[Cube, ...]:
    _require_field_fits(field, n)
    _require_index(lo, 'lo')
    _require_index(hi, 'hi')
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
            size = 1 << block + 1
            if value % size != 0 or value + size - 1 > hi:
                break
            block += 1
        free_low = (1 << block) - 1
        anchor = (value & ~free_low) << field.offset
        cubes.append(_derived_cube(n, anchor, outside | free_low << field.offset))
        value += 1 << block
    return tuple(cubes)

@dataclass(frozen=True)
class Leaf:
    cubes: Tuple[Cube, ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'cubes', normalise_cover(tuple(self.cubes)))

    @property
    def width(self) -> Optional[int]:
        return self.cubes[0].n if self.cubes else None

@dataclass(frozen=True)
class AllOf:
    children: Tuple['Expression', ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'children', _checked_children(self.children))

@dataclass(frozen=True)
class AnyOf:
    children: Tuple['Expression', ...] = ()

    def __post_init__(self) -> None:
        object.__setattr__(self, 'children', _checked_children(self.children))
Expression = Union[Leaf, AllOf, AnyOf]

def _checked_children(children) -> Tuple['Expression', ...]:
    children = tuple(children)
    widths = set()
    for child in children:
        if not isinstance(child, (Leaf, AllOf, AnyOf)):
            raise TypeError(f'expected an expression, got {type(child).__name__}')
        width = expression_width(child)
        if width is not None:
            widths.add(width)
    if len(widths) > 1:
        raise ValueError(f'an expression mixes widths {sorted(widths)}')
    return children

def expression_width(expression: 'Expression') -> Optional[int]:
    stack = [expression]
    while stack:
        node = stack.pop()
        if isinstance(node, Leaf):
            if node.cubes:
                return node.cubes[0].n
        elif isinstance(node, (AllOf, AnyOf)):
            stack.extend(reversed(node.children))
        else:
            raise TypeError(f'expected an expression, got {type(node).__name__}')
    return None

def count_records(expression: 'Expression') -> int:
    """Expression records: one per node plus one per cube alternative."""
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
            raise TypeError(f'expected an expression, got {type(node).__name__}')
    return total

class BudgetExhausted(Exception):
    """A declared limit stopped the work before it completed."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason

@dataclass(frozen=True)
class Budget:
    seconds: float = 0.1
    max_cover: int = 4096
    max_visited: int = 50000
    max_records: int = 20000

    def __post_init__(self) -> None:
        if not isinstance(self.seconds, (int, float)) or isinstance(self.seconds, bool):
            raise TypeError('seconds must be a number')
        if self.seconds <= 0:
            raise ValueError('seconds must be positive')
        for name in ('max_cover', 'max_visited', 'max_records'):
            _require_index(getattr(self, name), name, minimum=1)

    def start(self) -> 'Meter':
        return Meter(self)
DEFAULT_BUDGET = Budget()

class Meter:
    """The running cost of one query."""

    def __init__(self, budget: Budget) -> None:
        if not isinstance(budget, Budget):
            raise TypeError('a meter requires a Budget')
        self.budget = budget
        self.started = time.monotonic()
        self.visited = 0
        self.records = 0
        self.intersections = 0
        self._charged: Dict[int, object] = {}

    @property
    def started(self) -> float:
        return self._started

    @started.setter
    def started(self, value: float) -> None:
        """Move the start, and the deadline derived from it, together."""
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
            raise BudgetExhausted('time budget exhausted')

    def visit(self, count: int=1) -> None:
        self.visited += count
        if self.visited > self.budget.max_visited:
            raise BudgetExhausted('visited-cube budget exhausted')
        if time.monotonic() > self._deadline:
            raise BudgetExhausted('time budget exhausted')

    def record(self, count: int=1) -> None:
        self.records += count
        if self.records > self.budget.max_records:
            raise BudgetExhausted('expression-record budget exhausted')
        if time.monotonic() > self._deadline:
            raise BudgetExhausted('time budget exhausted')

    def intersection(self, count: int=1) -> None:
        self.intersections += count
        if time.monotonic() > self._deadline:
            raise BudgetExhausted('time budget exhausted')

    def node(self, count: int=1) -> None:
        """Charge expression nodes as they are built."""
        self.record(count)

    def charge_expression(self, expression: object) -> None:
        """Bill an expression once, however many times it is handed over."""
        key = id(expression)
        self.record(0)
        if key in self._charged:
            return
        self.record(count_records(expression))
        self._charged[key] = expression

    def mark_charged(self, expression: object) -> None:
        """Record that this expression was billed as it was constructed."""
        self._charged[id(expression)] = expression

    def cover_limit(self, size: int) -> None:
        """Validate a cover size against the cap, charging nothing."""
        if size > self.budget.max_cover:
            raise BudgetExhausted('atomic relation cover budget exhausted')

    def cover(self, size: int) -> None:
        """Check and charge a completed cover."""
        self.cover_limit(size)
        self.record(size)

    def counters(self) -> Dict[str, int]:
        return {'visited': self.visited, 'records': self.records, 'intersections': self.intersections}

@dataclass(frozen=True)
class QueryResult:
    """The outcome of one exact query."""
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
        payload: Dict[str, object] = {'status': self.status, 'elapsed': self.elapsed, 'visited': self.visited, 'counters': dict(self.counters)}
        if self.cube is not None:
            payload['anchor'] = self.cube.anchor
            payload['free_mask'] = self.cube.free_mask
            payload['width'] = self.cube.n
        if self.reason is not None:
            payload['reason'] = self.reason
        return payload

def _check_expression_width(expression: 'Expression', n: int) -> None:
    width = expression_width(expression)
    if width is not None and width != n:
        raise ValueError(f'expression width {width} does not match the {n} bit universe')

def _check_incoming_leaves(expression: 'Expression', meter: 'Meter') -> None:
    """Validate every leaf cover the query was handed."""
    stack = [expression]
    while stack:
        meter.check_time()
        node = stack.pop()
        if isinstance(node, Leaf):
            meter.cover_limit(len(node.cubes))
        elif isinstance(node, (AllOf, AnyOf)):
            stack.extend(node.children)

def solve(expression: 'Expression', n: int, budget: Optional[Budget]=None, meter: Optional[Meter]=None) -> QueryResult:
    """Answer one query by lazy depth-first intersection."""
    _require_index(n, 'n')
    meter = meter if meter is not None else (budget or DEFAULT_BUDGET).start()
    try:
        _check_expression_width(expression, n)
        _check_incoming_leaves(expression, meter)
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
                    if (anchor ^ alternative.anchor) & ~(free | alternative.free_mask):
                        continue
                    survivors.append((_derived_cube(cube.n, anchor | alternative.anchor, free & alternative.free_mask), rest))
                stack.extend(reversed(survivors))
                meter.check_time()
            else:
                raise TypeError(f'expected an expression, got {type(head).__name__}')
        meter.check_time()
        return QueryResult(UNSAT, None, None, meter.elapsed, meter.visited, meter.counters())
    except BudgetExhausted as exc:
        return QueryResult(UNKNOWN, None, exc.reason, meter.elapsed, meter.visited, meter.counters())


ADDRESS_WIDTH = 8

class ContractError(ValueError):
    pass

class ProgramFacts:
    """An immutable derived view of one program."""
    __slots__ = ('program', 'operations', 'count', 'opcode', 'engine', 'latency', 'dest', 'kind', 'producers', 'consumers', 'value_names', 'width', 'data_predecessors', 'memory_predecessors', 'predecessors', 'successors', 'horizon', '_heights')

    def __init__(self, program: dict) -> None:
        machine.validate_program(program)
        operations = program['operations']
        count = len(operations)
        self.program = program
        self.operations = tuple(operations)
        self.count = count
        self.opcode = tuple((op['op'] for op in operations))
        self.engine = tuple((machine.OP_SPECS[code]['engine'] for code in self.opcode))
        self.latency = tuple((machine.OP_SPECS[code]['latency'] for code in self.opcode))
        self.dest = tuple((op.get('dest') for op in operations))
        self.kind = tuple((machine.OP_SPECS[code]['result'] for code in self.opcode))
        self.producers = dict(machine.producer_map(program))
        kinds = machine.result_kinds(program)
        self.value_names = tuple((op['dest'] for op in operations if machine.OP_SPECS[op['op']]['result']))
        self.width = {name: machine.VLEN if kinds[name] == 'vector' else 1 for name in self.value_names}
        consumers: Dict[str, List[int]] = {name: [] for name in self.value_names}
        for op in operations:
            for arg in dict.fromkeys(op.get('args', [])):
                consumers[arg].append(op['id'])
        self.consumers = {name: tuple(ids) for name, ids in consumers.items()}
        data: List[Tuple[Tuple[int, int], ...]] = []
        memory: List[Tuple[int, ...]] = []
        combined: List[Dict[int, int]] = []
        for op in operations:
            incoming: Dict[int, int] = {}
            pairs = []
            for arg in op.get('args', []):
                producer = self.producers[arg]
                lag = self.latency[producer]
                pairs.append((producer, lag))
                incoming[producer] = max(incoming.get(producer, 0), lag)
            ordered = tuple(sorted(set(pairs)))
            data.append(ordered)
            earlier = tuple(machine.memory_predecessors(program, op['id']))
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
        self.successors = tuple((tuple(sorted(items)) for items in successors))
        self.horizon = sum(self.latency)
        heights = [0] * count
        for op_id in reversed(range(count)):
            heights[op_id] = max((lag + heights[successor] for successor, lag in self.successors[op_id]), default=0)
        self._heights = tuple(heights)

    @property
    def heights(self) -> Tuple[int, ...]:
        """Longest remaining dependency lag from each operation."""
        return self._heights

    def prefix_horizon(self, op_id: int) -> int:
        return sum(self.latency[:op_id])

    def dependency_lower_bound(self) -> int:
        """Fewest bundles the dependency graph alone permits."""
        return max(self._heights, default=0) + 1 if self.count else 0

    def engine_lower_bound(self) -> int:
        """Fewest bundles the per-cycle issue capacity alone permits."""
        counts: Dict[str, int] = {}
        for engine in self.engine:
            counts[engine] = counts.get(engine, 0) + 1
        return max((-(-total // machine.ENGINE_LIMITS[engine]) for engine, total in counts.items()), default=0)

    def cycle_lower_bound(self) -> int:
        return max(self.dependency_lower_bound(), self.engine_lower_bound())

    def memory_lower_bound(self) -> int:
        """A basic footprint bound: the widest single result must fit."""
        return max(self.width.values(), default=0)

    def unique_allocation_width(self) -> int:
        """Words used when every value is given private, aligned space."""
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
    if horizon < 1:
        raise ContractError('a horizon must be positive')
    return max(1, (horizon - 1).bit_length())

def lifetimes(facts: ProgramFacts, times: Dict[int, int]) -> Dict[str, Tuple[int, int]]:
    """Inclusive live interval of every value."""
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
    """Emit bundles up to the last issue cycle."""
    if not times:
        raise ContractError('a schedule must place at least one operation')
    span = max(times.values()) + 1
    bundles: List[Dict[str, List[int]]] = [{} for _ in range(span)]
    for op_id in range(facts.count):
        engine = facts.engine[op_id]
        bundles[times[op_id]].setdefault(engine, []).append(op_id)
    return bundles

def _contract_footprint(facts: ProgramFacts, addresses: Dict[str, int]) -> int:
    """Highest allocated end address, in words, including alignment holes."""
    return max((addresses[name] + facts.width[name] for name in facts.value_names), default=0)

def engine_usage(facts: ProgramFacts, times: Dict[int, int]) -> Dict[Tuple[str, int], int]:
    usage: Dict[Tuple[str, int], int] = {}
    for op_id in range(facts.count):
        key = (facts.engine[op_id], times[op_id])
        usage[key] = usage.get(key, 0) + 1
    return usage

def compilation(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]) -> dict:
    return {'scratch': {name: addresses[name] for name in facts.value_names}, 'bundles': assemble_bundles(facts, times)}

def check_feasible(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]) -> None:
    """Our own acceptance check, independent of the reference validator."""
    if set(times) != set(range(facts.count)):
        raise ContractError('every operation must be placed exactly once')
    for op_id, cycle in times.items():
        if not isinstance(cycle, int) or isinstance(cycle, bool) or cycle < 0:
            raise ContractError(f'operation {op_id} has a non-integer issue cycle')
    for op_id in range(facts.count):
        cycle = times[op_id]
        for predecessor, lag in facts.predecessors[op_id].items():
            if cycle < times[predecessor] + lag:
                raise ContractError(f'operation {op_id} issues at {cycle}, before operation {predecessor} is ready at {times[predecessor] + lag}')
    for (engine, cycle), used in engine_usage(facts, times).items():
        if used > machine.ENGINE_LIMITS[engine]:
            raise ContractError(f'cycle {cycle} issues {used} {engine} operations, limit is {machine.ENGINE_LIMITS[engine]}')
    if set(addresses) != set(facts.value_names):
        raise ContractError('every value requires exactly one scratch address')
    live = lifetimes(facts, times)
    for name in facts.value_names:
        base = addresses[name]
        width = facts.width[name]
        if not isinstance(base, int) or isinstance(base, bool) or base < 0:
            raise ContractError(f'value {name!r} has a non-integer address')
        if width == machine.VLEN and base % machine.VLEN != 0:
            raise ContractError(f'vector {name!r} is not aligned to {machine.VLEN} words')
        if base + width > machine.SCRATCH_WORDS:
            raise ContractError(f'value {name!r} ends at {base + width}, past {machine.SCRATCH_WORDS}')
    ordered = list(facts.value_names)
    for i, first in enumerate(ordered):
        for second in ordered[i + 1:]:
            spatial = addresses[first] < addresses[second] + facts.width[second] and addresses[second] < addresses[first] + facts.width[first]
            if not spatial:
                continue
            first_live, second_live = (live[first], live[second])
            temporal = first_live[0] <= second_live[1] and second_live[0] <= first_live[1]
            if temporal:
                raise ContractError(f'values {first!r} and {second!r} share scratch while both are live')


class CoverCache:
    """Relation covers already built during one compilation."""
    __slots__ = ('_entries', 'max_entries', 'max_cubes', 'cubes', 'hits', 'misses', 'refused')

    def __init__(self, max_entries: int=4096, max_cubes: int=200000) -> None:
        self._entries: Dict[tuple, Tuple[Tuple[Cube, ...], int, int]] = {}
        self.max_entries = max_entries
        self.max_cubes = max_cubes
        self.cubes = 0
        self.hits = 0
        self.misses = 0
        self.refused = 0

    @staticmethod
    def key(name: str, lhs: 'Term', rhs: 'Term', n: int) -> tuple:
        return (name, lhs.field, lhs.offset, rhs.field, rhs.offset, n)

    def get(self, key: tuple):
        found = self._entries.get(key)
        if found is None:
            self.misses += 1
            return None
        self.hits += 1
        return found

    def put(self, key: tuple, cover: Tuple[Cube, ...], visits: int, records: int) -> None:
        if key in self._entries:
            return
        if len(self._entries) >= self.max_entries or self.cubes + len(cover) > self.max_cubes:
            self.refused += 1
            return
        self._entries[key] = (cover, visits, records)
        self.cubes += len(cover)

    def statistics(self) -> Dict[str, int]:
        return {'entries': len(self._entries), 'cubes_retained': self.cubes, 'hits': self.hits, 'misses': self.misses, 'refused': self.refused, 'max_entries': self.max_entries, 'max_cubes': self.max_cubes}

class Infeasible(Exception):
    """A fixed decision already violates the requested target."""

@dataclass(frozen=True)
class Term:
    field: Optional[Field] = None
    offset: int = 0

    def __post_init__(self) -> None:
        if self.field is not None and (not isinstance(self.field, Field)):
            raise TypeError('a term holds a Field or None')
        if not isinstance(self.offset, int) or isinstance(self.offset, bool):
            raise TypeError('a term offset must be a plain integer')

    @property
    def mask(self) -> int:
        return 0 if self.field is None else self.field.mask

    @property
    def is_constant(self) -> bool:
        return self.field is None

    def bounds(self, cube: Cube) -> Tuple[int, int]:
        if self.field is None:
            return (self.offset, self.offset)
        field = self.field
        low = (cube.anchor & field.mask) >> field.offset
        high = ((cube.anchor | cube.free_mask) & field.mask) >> field.offset
        return (low + self.offset, high + self.offset)

    def shifted(self, amount: int) -> 'Term':
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
_RELATIONS = {'le': (_decide_le, lambda a, b: a <= b), 'lt': (_decide_lt, lambda a, b: a < b), 'eq': (_decide_eq, lambda a, b: a == b), 'ne': (_decide_ne, lambda a, b: a != b)}

def _significance(coordinate: int, lhs: 'Term', rhs: 'Term') -> int:
    """Place value of a coordinate within whichever term's field holds it."""
    best = -1
    for term in (lhs, rhs):
        if term.field is None:
            continue
        if term.field.offset <= coordinate < term.field.end():
            best = max(best, coordinate - term.field.offset)
    return best

def relation_cover(name: str, lhs: Term, rhs: Term, n: int, meter: Meter, cache: Optional[CoverCache]=None) -> Tuple[Cube, ...]:
    if name not in _RELATIONS:
        raise ValueError(f'unknown relation {name!r}')
    decide, exact = _RELATIONS[name]
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

    def store(cover: Tuple[Cube, ...]) -> Tuple[Cube, ...]:
        """Keep a completed cover, with what it cost, for the next query."""
        if cache is not None and key is not None:
            cache.put(key, cover, meter.visited - visits_before, meter.records - records_before)
        return cover
    if lhs.is_constant and rhs.is_constant or (lhs.field is not None and rhs.field is not None and (lhs.field == rhs.field)):
        meter.check_time()
        if not exact(lhs.offset, rhs.offset):
            return store(())
        meter.record(1)
        return store((universe(n),))
    support = lhs.mask | rhs.mask
    limit = universe_mask(n)
    if support & ~limit:
        raise ValueError('a term reaches outside the declared universe')
    order: List[int] = []
    for coordinate in range(n):
        if not support >> coordinate & 1:
            continue
        order.append(coordinate)
    order.sort(key=lambda c: (_significance(c, lhs, rhs), c), reverse=True)
    order_bits = [(1 << coordinate, coordinate) for coordinate in order]
    l_mask = lhs.field.mask if lhs.field is not None else 0
    l_shift = lhs.field.offset if lhs.field is not None else 0
    l_offset = lhs.offset
    r_mask = rhs.field.mask if rhs.field is not None else 0
    r_shift = rhs.field.offset if rhs.field is not None else 0
    r_offset = rhs.offset
    accepted: List[Cube] = []
    stack = [universe(n)]
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
            cover_limit(len(accepted))
            record(1)
            continue
        if verdict is False:
            continue
        free = support & cube.free_mask
        if free == 0:
            if exact(low_l, low_r):
                accepted.append(cube)
                cover_limit(len(accepted))
                record(1)
            continue
        for bit, coordinate in order_bits:
            if free & bit:
                break
        zero, one = split(cube, coordinate)
        stack.append(one)
        stack.append(zero)
    cover = normalise_cover(accepted, meter)
    meter.cover_limit(len(cover))
    meter.check_time()
    return store(cover)

def _leaf(name: str, lhs: Term, rhs: Term, n: int, meter: Meter, cache: Optional[CoverCache]=None) -> Leaf:
    cover = relation_cover(name, lhs, rhs, n, meter, cache)
    meter.node()
    return Leaf(cover)

def le(lhs, rhs, n, meter, cache=None) -> Leaf:
    return _leaf('le', lhs, rhs, n, meter, cache)

def lt(lhs, rhs, n, meter, cache=None) -> Leaf:
    return _leaf('lt', lhs, rhs, n, meter, cache)

def ge(lhs, rhs, n, meter, cache=None) -> Leaf:
    return _leaf('le', rhs, lhs, n, meter, cache)

def ne(lhs, rhs, n, meter, cache=None) -> Leaf:
    return _leaf('ne', lhs, rhs, n, meter, cache)
TIME_SLACK = 2

class JointQuery:
    """One joint scheduling, allocation and lane query over a small window."""

    def __init__(self, facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int], target_cycles: int, target_memory: int, meter: Meter, cache: Optional[CoverCache]=None) -> None:
        self.facts = facts
        self.times = dict(times)
        self.addresses = dict(addresses)
        self.window = tuple(sorted(set(window)))
        self.target_cycles = target_cycles
        self.target_memory = target_memory
        self.meter = meter
        self.cache = cache
        if not self.window:
            raise ValueError('a joint query needs at least one selected operation')
        if target_cycles < 1 or target_memory < 1:
            raise Infeasible('a target must be positive')
        self.time_bits = time_width(facts.horizon)
        self.time_field: Dict[int, Field] = {}
        self.address_field: Dict[str, Field] = {}
        self.lane_field: Dict[int, Field] = {}
        offset = 0
        for op_id in self.window:
            self.time_field[op_id] = Field('t%d' % op_id, offset, self.time_bits)
            offset += self.time_bits
            name = facts.dest[op_id]
            if name is not None:
                self.address_field[name] = Field('a_' + name, offset, ADDRESS_WIDTH)
                offset += ADDRESS_WIDTH
            if machine.ENGINE_LIMITS[facts.engine[op_id]] > 1:
                self.lane_field[op_id] = Field('l%d' % op_id, offset, 1)
                offset += 1
        self.n = offset
        self.selected_values = tuple((facts.dest[op_id] for op_id in self.window if facts.dest[op_id] is not None))
        affected = set(self.selected_values)
        for name in facts.value_names:
            if any((consumer in self.time_field for consumer in facts.consumers[name])):
                affected.add(name)
        self.affected_values = tuple((name for name in facts.value_names if name in affected))
        self._live_cache: Dict[str, Tuple[int, int]] = {}

    def _leaf_node(self, cover) -> Leaf:
        """A leaf built here, charged as a node plus its alternatives."""
        self.meter.cover_limit(len(cover))
        self.meter.record(len(cover))
        self.meter.node()
        return Leaf(cover)

    def _all(self, children) -> AllOf:
        children = tuple(children)
        self.meter.node()
        return AllOf(children)

    def _any(self, children) -> AnyOf:
        children = tuple(children)
        self.meter.node()
        return AnyOf(children)

    def time_term(self, op_id: int, offset: int=0) -> Term:
        field = self.time_field.get(op_id)
        if field is None:
            return constant(self.times[op_id] + offset)
        return Term(field, offset)

    def address_term(self, name: str, offset: int=0) -> Term:
        field = self.address_field.get(name)
        if field is None:
            return constant(self.addresses[name] + offset)
        return Term(field, offset)

    def lane_term(self, op_id: int) -> Term:
        field = self.lane_field.get(op_id)
        if field is None:
            return constant(self._fixed_lane(op_id))
        return Term(field, 0)

    def write_term(self, name: str, offset: int=0) -> Term:
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

    def _time_bounds(self, op_id: int) -> Tuple[int, int]:
        if op_id not in self.time_field:
            fixed = self.times[op_id]
            return (fixed, fixed)
        low, high = self._time_domain(op_id)
        return (low, high)

    def _time_domain(self, op_id: int) -> Tuple[int, int]:
        ceiling = min(self.facts.horizon, self.target_cycles) - 1
        incumbent = self.times[op_id]
        return (max(0, incumbent - TIME_SLACK), min(incumbent + TIME_SLACK, ceiling))

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
        start, end = (low + latency, high + latency)
        for consumer in self.facts.consumers[name]:
            end = max(end, self._time_bounds(consumer)[1])
        return (start, end)

    def _address_bounds(self, name: str) -> Tuple[int, int]:
        if name not in self.address_field:
            base = self.addresses[name]
            return (base, base)
        return (0, self.target_memory - self.facts.width[name])

    def _domains(self) -> List[Leaf]:
        parts: List[Leaf] = []
        for op_id in self.window:
            field = self.time_field[op_id]
            low, high = self._time_domain(op_id)
            if low > high:
                raise Infeasible(f'operation {op_id} has no cycle below the target of {self.target_cycles}')
            if high >= field.limit:
                raise Infeasible('a time domain does not fit its field')
            parts.append(self._leaf_node(interval(field, low, high, self.n)))
        for name in self.selected_values:
            field = self.address_field[name]
            width = self.facts.width[name]
            high = self.target_memory - width
            if high < 0:
                raise Infeasible(f'value {name!r} cannot fit a target of {self.target_memory}')
            cover = interval(field, 0, high, self.n)
            if width == machine.VLEN:
                alignment = Cube(self.n, 0, universe_mask(self.n) ^ field.encode(machine.VLEN - 1))
                cover = tuple((met for met in (intersect(cube, alignment) for cube in cover) if met is not None))
            if not cover:
                raise Infeasible(f'value {name!r} has an empty address domain')
            parts.append(self._leaf_node(cover))
        return parts

    def _fixed_targets(self) -> None:
        """A fixed decision violating a target makes the query infeasible."""
        for op_id in range(self.facts.count):
            if op_id in self.time_field:
                continue
            if self.times[op_id] >= self.target_cycles:
                raise Infeasible(f'external operation {op_id} issues at {self.times[op_id]}, at or past the target of {self.target_cycles}')
        for name in self.facts.value_names:
            if name in self.address_field:
                continue
            if self.addresses[name] + self.facts.width[name] > self.target_memory:
                raise Infeasible(f'external value {name!r} ends past the target of {self.target_memory}')

    def _data_precedence(self) -> List[Leaf]:
        parts = []
        for op_id in range(self.facts.count):
            for predecessor, lag in sorted(self.facts.predecessors[op_id].items()):
                if op_id not in self.time_field and predecessor not in self.time_field:
                    continue
                clause = ge(self.time_term(op_id), self.time_term(predecessor, lag), self.n, self.meter, self.cache)
                if not clause.cubes:
                    raise Infeasible(f'operation {op_id} cannot follow operation {predecessor}')
                if len(clause.cubes) == 1 and clause.cubes[0] == universe(self.n):
                    continue
                parts.append(clause)
        return parts

    def _engine_capacity(self) -> List[Expression]:
        parts: List[Expression] = []
        for op_id in self.window:
            engine = self.facts.engine[op_id]
            low, high = self._time_domain(op_id)
            for other in range(self.facts.count):
                if other == op_id or self.facts.engine[other] != engine:
                    continue
                if other in self.time_field and other < op_id:
                    continue
                other_low, other_high = self._time_bounds(other)
                if other_high < low or high < other_low:
                    continue
                different_time = ne(self.time_term(op_id), self.time_term(other), self.n, self.meter, self.cache)
                if machine.ENGINE_LIMITS[engine] == 1:
                    if not different_time.cubes:
                        raise Infeasible(f'operations {op_id} and {other} must share a single slot')
                    parts.append(different_time)
                    continue
                different_lane = ne(self.lane_term(op_id), self.lane_term(other), self.n, self.meter, self.cache)
                if different_lane.cubes and universe(self.n) in different_lane.cubes:
                    continue
                if not different_time.cubes and (not different_lane.cubes):
                    raise Infeasible(f'operations {op_id} and {other} cannot share engine {engine}')
                parts.append(self._any((different_time, different_lane)))
        return parts

    def _scratch_safety(self) -> List[Expression]:
        """Spatial separation OR temporal separation, never both required."""
        parts: List[Expression] = []
        names = list(self.facts.value_names)
        position = {name: index for index, name in enumerate(names)}
        pairs = set()
        for first in self.affected_values:
            for second in names:
                if second == first:
                    continue
                pairs.add((first, second) if position[first] < position[second] else (second, first))
        for first, second in sorted(pairs, key=lambda pair: (position[pair[0]], position[pair[1]])):
            first_live = self._live_bounds(first)
            second_live = self._live_bounds(second)
            if first_live[1] < second_live[0] or second_live[1] < first_live[0]:
                continue
            first_span = self._address_bounds(first)
            second_span = self._address_bounds(second)
            first_width = self.facts.width[first]
            second_width = self.facts.width[second]
            if first_span[1] + first_width <= second_span[0] or second_span[1] + second_width <= first_span[0]:
                continue
            clause = self._any((le(self.address_term(first, first_width), self.address_term(second), self.n, self.meter, self.cache), le(self.address_term(second, second_width), self.address_term(first), self.n, self.meter, self.cache), self._ends_before(first, second), self._ends_before(second, first)))
            parts.append(clause)
        return parts

    def _ends_before(self, first: str, second: str) -> Expression:
        write_second = self.write_term(second)
        children: List[Expression] = [lt(self.write_term(first), write_second, self.n, self.meter, self.cache)]
        for consumer in self.facts.consumers[first]:
            children.append(lt(self.time_term(consumer), write_second, self.n, self.meter, self.cache))
        return self._all(children)

    def expression(self) -> Expression:
        self._fixed_targets()
        children: List[Expression] = []
        children.extend(self._domains())
        children.extend(self._data_precedence())
        children.extend(self._engine_capacity())
        children.extend(self._scratch_safety())
        built = self._all(children)
        total = count_records(built)
        if total > self.meter.budget.max_records:
            raise BudgetExhausted('expression-record budget exhausted')
        self.meter.mark_charged(built)
        return built

    def decode(self, cube: Cube) -> Tuple[Dict[int, int], Dict[str, int]]:
        """Read a witness back into a complete schedule and allocation."""
        if cube.n != self.n:
            raise ValueError('the witness has the wrong width')
        times = dict(self.times)
        addresses = dict(self.addresses)
        anchor = cube.anchor
        for op_id, field in self.time_field.items():
            value = field.decode(anchor)
            low, high = self._time_domain(op_id)
            if not low <= value <= high:
                raise ValueError(f'decoded cycle {value} for operation {op_id} is outside its domain')
            times[op_id] = value
        for name, field in self.address_field.items():
            value = field.decode(anchor)
            width = self.facts.width[name]
            if value + width > self.target_memory:
                raise ValueError(f'decoded address {value} for {name!r} exceeds the target')
            if width == machine.VLEN and value % machine.VLEN:
                raise ValueError(f'decoded address {value} for {name!r} is misaligned')
            addresses[name] = value
        return (times, addresses)


WINDOW_SIZE = 4
_RESERVE_SECONDS = 1.0

def _digest(times: Dict[int, int], addresses: Dict[str, int]) -> str:
    payload = repr((sorted(times.items()), sorted(addresses.items()))).encode('utf-8')
    return hashlib.sha256(payload).hexdigest()[:16]

def targets_for(facts: ProgramFacts, cycles: int, memory: int) -> List[Tuple[int, int]]:
    product = cycles * memory
    cycle_floor = facts.cycle_lower_bound()
    memory_floor = facts.memory_lower_bound()
    candidates: List[Tuple[int, int]] = [(cycles - 1, memory), (cycles, memory - 1)]
    candidates.append((cycles + 1, (product - 1) // (cycles + 1)))
    if cycles - 1 > 0:
        candidates.append((cycles - 1, min(machine.SCRATCH_WORDS, (product - 1) // (cycles - 1))))
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

def windows_for(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], scratch_first: bool) -> List[Tuple[int, ...]]:
    latest = sorted(range(facts.count), key=lambda op_id: (-times[op_id], op_id))
    time_window = tuple(sorted(latest[:WINDOW_SIZE]))
    highest = sorted(facts.value_names, key=lambda name: (-(addresses[name] + facts.width[name]), facts.producers[name]))
    scratch_window = tuple(sorted({facts.producers[name] for name in highest[:WINDOW_SIZE]}))
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

def optimise(program: dict, facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], limits, deadline, counters) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the incumbent through bounded joint queries."""
    statuses = {'SAT': 0, 'UNSAT': 0, 'UNKNOWN_CONSTRUCTION': 0, 'UNKNOWN_SEARCH': 0, 'INFEASIBLE': 0}
    reasons: Dict[str, int] = {}
    improvements: List[dict] = []
    validation_errors: List[dict] = []
    target_discrepancies: List[dict] = []
    attempted: set = set()
    stopped = 'pass_complete'
    started = deadline.elapsed
    cache = CoverCache()
    allowance = min(limits.optimise_seconds, deadline.seconds - started - _RESERVE_SECONDS)
    horizon = started + allowance
    best_times = dict(times)
    best_addresses = dict(addresses)
    improved = True
    while improved:
        improved = False
        cycles = max(best_times.values()) + 1
        memory = _contract_footprint(facts, best_addresses)
        product = cycles * memory
        digest = _digest(best_times, best_addresses)
        for target_cycles, target_memory in targets_for(facts, cycles, memory):
            windows = windows_for(facts, best_times, best_addresses, scratch_first=target_memory < memory)
            for window in windows:
                if len(attempted) >= limits.max_queries:
                    stopped = 'query_cap'
                    break
                if deadline.elapsed >= horizon:
                    stopped = 'deadline'
                    break
                key = (digest, window, target_cycles, target_memory)
                if key in attempted:
                    continue
                attempted.add(key)
                remaining = min(limits.query_seconds, horizon - deadline.elapsed)
                if remaining <= 0:
                    stopped = 'deadline'
                    break
                meter = Budget(seconds=remaining, max_cover=limits.max_cover, max_visited=limits.max_visited, max_records=limits.max_records).start()
                try:
                    query = JointQuery(facts, best_times, best_addresses, window, target_cycles, target_memory, meter, cache)
                    expression = query.expression()
                except Infeasible:
                    statuses['INFEASIBLE'] += 1
                    continue
                except BudgetExhausted as exc:
                    statuses['UNKNOWN_CONSTRUCTION'] += 1
                    reasons[exc.reason] = reasons.get(exc.reason, 0) + 1
                    continue
                result = solve(expression, query.n, meter=meter)
                counters.absorb(meter, 0)
                if result.is_unknown:
                    statuses['UNKNOWN_SEARCH'] += 1
                    if result.reason:
                        reasons[result.reason] = reasons.get(result.reason, 0) + 1
                    continue
                if result.is_unsat:
                    statuses['UNSAT'] += 1
                    continue
                statuses['SAT'] += 1
                try:
                    candidate_times, candidate_addresses = query.decode(result.cube)
                    check_feasible(facts, candidate_times, candidate_addresses)
                    compiled = compilation(facts, candidate_times, candidate_addresses)
                    machine.check_compilation(program, compiled)
                except (ValueError, ContractError, machine.CompileError) as exc:
                    validation_errors.append({'window': list(window), 'target': [target_cycles, target_memory], 'error': str(exc)})
                    continue
                actual_cycles = len(compiled['bundles'])
                actual_memory = _contract_footprint(facts, candidate_addresses)
                actual_product = actual_cycles * actual_memory
                if actual_cycles > target_cycles or actual_memory > target_memory:
                    target_discrepancies.append({'window': list(window), 'target': [target_cycles, target_memory], 'actual_cycles': actual_cycles, 'actual_memory': actual_memory, 'reason': f'witness satisfied the query but measured ({actual_cycles}, {actual_memory}) against target ({target_cycles}, {target_memory})'})
                    continue
                if actual_product >= product:
                    continue
                improvements.append({'window': list(window), 'target': [target_cycles, target_memory], 'from': {'cycles': cycles, 'footprint': memory, 'product': product}, 'to': {'cycles': actual_cycles, 'footprint': actual_memory, 'product': actual_product}})
                best_times = candidate_times
                best_addresses = candidate_addresses
                improved = True
                break
            if improved or stopped != 'pass_complete':
                break
        if stopped != 'pass_complete':
            break
    record = {'enabled': True, 'attempted_queries': len(attempted), 'statuses': statuses, 'unknown_reasons': reasons, 'accepted': len(improvements), 'improvements': improvements, 'validation_errors': validation_errors, 'target_discrepancies': target_discrepancies, 'discrepancy_count': len(validation_errors) + len(target_discrepancies), 'stopped_because': stopped, 'cover_cache': cache.statistics(), 'seconds': deadline.elapsed - started, 'allowance_seconds': allowance}
    return (best_times, best_addresses, record)


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

    def budget(self, limits: Limits) -> Budget:
        remaining = self.remaining
        if remaining <= 0:
            raise CompilationFailure('the compilation deadline passed during construction')
        return Budget(seconds=min(limits.query_seconds, remaining), max_cover=limits.max_cover, max_visited=limits.max_visited, max_records=limits.max_records)

class _Counters:
    """Query bookkeeping carried into the report."""

    def __init__(self) -> None:
        self.queries = 0
        self.cubes = 0
        self.largest_cover = 0
        self.intersections = 0

    def absorb(self, meter: Meter, cover_size: int) -> None:
        self.queries += 1
        self.cubes += meter.visited
        self.intersections += meter.intersections
        self.largest_cover = max(self.largest_cover, cover_size)

    def as_dict(self) -> Dict[str, int]:
        return {'queries': self.queries, 'largest_cover': self.largest_cover, 'intersections': self.intersections}

def _intersect_cover(cover: Sequence[Cube], other: Sequence[Cube], meter: Meter) -> Tuple[Cube, ...]:
    result: List[Cube] = []
    for left in cover:
        for right in other:
            meter.intersection()
            met = intersect(left, right)
            if met is not None:
                result.append(met)
    meter.cover(len(result))
    return tuple(result)

def _subtract_cover(cover: Sequence[Cube], removed: Sequence[Cube], meter: Meter) -> Tuple[Cube, ...]:
    current = tuple(cover)
    for cube in removed:
        survivors: List[Cube] = []
        for member in current:
            meter.intersection()
            survivors.extend(difference(member, cube))
        meter.cover(len(survivors))
        current = tuple(survivors)
        if not current:
            break
    return current

def _earliest_cycle(facts: ProgramFacts, op_id: int, lower: int, full_cycles: Dict[str, List[int]], field: Field, width: int, budget: Budget, counters: _Counters) -> int:
    """The smallest legal issue cycle, retrieved as a schema witness."""
    engine = facts.engine[op_id]
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
        raise CompilationFailure(f'operation {op_id} has no cycle in [{lower}, {hi}] within the horizon')
    meter = budget.start()
    cover = interval(field, lower, hi, width)
    meter.cover(len(cover))
    cover = _subtract_cover(cover, tuple((Cube(width, field.encode(cycle), 0) for cycle in blocked if cycle <= hi)), meter)
    chosen = min_member(cover)
    counters.absorb(meter, len(cover))
    if chosen is None:
        raise CompilationFailure(f'no legal issue cycle remained for operation {op_id}')
    return field.decode(chosen)

def _schedule(facts: ProgramFacts, limits: Limits, deadline: _Deadline, counters: _Counters) -> Dict[int, int]:
    times: Dict[int, int] = {}
    calendar: Dict[Tuple[str, int], int] = {}
    full_cycles: Dict[str, List[int]] = {}
    width = time_width(facts.horizon)
    field = Field('t', 0, width)
    for op_id in range(facts.count):
        lower = 0
        for predecessor, lag in facts.predecessors[op_id].items():
            candidate = times[predecessor] + lag
            if candidate > lower:
                lower = candidate
        try:
            cycle = _earliest_cycle(facts, op_id, lower, full_cycles, field, width, deadline.budget(limits), counters)
        except BudgetExhausted as exc:
            raise CompilationFailure(f'scheduling query for operation {op_id} exhausted its budget: {exc.reason}') from exc
        times[op_id] = cycle
        engine = facts.engine[op_id]
        key = (engine, cycle)
        used = calendar.get(key, 0) + 1
        calendar[key] = used
        if used == machine.ENGINE_LIMITS[engine]:
            occupied = full_cycles.setdefault(engine, [])
            position = len(occupied)
            while position and occupied[position - 1] > cycle:
                position -= 1
            occupied.insert(position, cycle)
    return times

def _lowest_address(facts: ProgramFacts, name: str, live: Dict[str, Tuple[int, int]], placed: Sequence[str], addresses: Dict[str, int], field: Field, budget: Budget, counters: _Counters) -> int:
    """The smallest legal aligned address, retrieved as a schema witness."""
    width = facts.width[name]
    universe = ADDRESS_WIDTH
    cap = machine.SCRATCH_WORDS - width
    own_start, own_end = live[name]
    overlapping = [other for other in placed if own_start <= live[other][1] and live[other][0] <= own_end]
    occupied = sum((facts.width[other] for other in overlapping))
    windows = []
    for candidate in (min(cap, occupied), cap):
        if candidate >= 0 and candidate not in windows:
            windows.append(candidate)
    for hi in windows:
        meter = budget.start()
        cover = interval(field, 0, hi, universe)
        meter.cover(len(cover))
        if width == machine.VLEN:
            alignment = Cube(universe, 0, universe_mask(universe) ^ machine.VLEN - 1)
            cover = _intersect_cover(cover, (alignment,), meter)
        for other in overlapping:
            base = addresses[other]
            low = max(0, base - width + 1)
            high = min(hi, base + facts.width[other] - 1)
            if low > high:
                continue
            cover = _subtract_cover(cover, interval(field, low, high, universe), meter)
            if not cover:
                break
        chosen = min_member(cover)
        counters.absorb(meter, len(cover))
        if chosen is not None:
            return field.decode(chosen)
    raise CompilationFailure(f'no legal scratch address remained for value {name!r}')

def _allocate(facts: ProgramFacts, times: Dict[int, int], limits: Limits, deadline: _Deadline, counters: _Counters) -> Dict[str, int]:
    live = lifetimes(facts, times)
    vectors = [name for name in facts.value_names if facts.width[name] == machine.VLEN]
    scalars = [name for name in facts.value_names if facts.width[name] != machine.VLEN]

    def ordering(name: str) -> Tuple[int, int]:
        return (live[name][0], facts.producers[name])
    order = sorted(vectors, key=ordering) + sorted(scalars, key=ordering)
    addresses: Dict[str, int] = {}
    placed: List[str] = []
    field = Field('a', 0, ADDRESS_WIDTH)
    for name in order:
        try:
            addresses[name] = _lowest_address(facts, name, live, placed, addresses, field, deadline.budget(limits), counters)
        except BudgetExhausted as exc:
            raise CompilationFailure(f'allocation query for {name!r} exhausted its budget: {exc.reason}') from exc
        placed.append(name)
    return addresses

def bootstrap(facts: ProgramFacts, limits: Limits, deadline: _Deadline, counters: _Counters) -> Tuple[Dict[int, int], Dict[str, int]]:
    """A complete first solution, built only from exact index queries."""
    times = _schedule(facts, limits, deadline, counters)
    addresses = _allocate(facts, times, limits, deadline, counters)
    return (times, addresses)

def compile_with_report(program: dict, limits: Optional[Limits]=None, optimise: bool=True) -> Tuple[dict, dict]:
    """Compile, and return diagnostics beside the official result."""
    limits = limits or DEFAULT_LIMITS
    deadline = _Deadline(limits.total_seconds)
    counters = _Counters()
    facts = derive(program)
    times, addresses = bootstrap(facts, limits, deadline, counters)
    compiled = compilation(facts, times, addresses)
    check_feasible(facts, times, addresses)
    machine.check_compilation(program, compiled)
    cycles = len(compiled['bundles'])
    footprint = _contract_footprint(facts, addresses)
    report = {'method': 'direct_index', 'stage': 'bootstrap', 'limits': limits.as_dict(), 'operations': facts.count, 'values': len(facts.value_names), 'horizon': facts.horizon, 'cycle_lower_bound': facts.cycle_lower_bound(), 'memory_lower_bound': facts.memory_lower_bound(), 'bootstrap': {'cycles': cycles, 'footprint': footprint, 'product': cycles * footprint, 'queries': counters.as_dict(), 'seconds': deadline.elapsed}, 'optimisation': {'enabled': False, 'discrepancy_count': 0}, 'discrepancy_count': 0, 'cycles': cycles, 'footprint': footprint, 'product': cycles * footprint, 'seconds': deadline.elapsed}
    if optimise:
        pass
        times, addresses, record = direct_optimizer.optimise(program, facts, times, addresses, limits, deadline, counters)
        report['optimisation'] = record
        report['discrepancy_count'] = record['discrepancy_count']
        report['stage'] = 'optimised' if record['accepted'] else 'bootstrap'
        check_feasible(facts, times, addresses)
        compiled = compilation(facts, times, addresses)
        machine.check_compilation(program, compiled)
        cycles = len(compiled['bundles'])
        footprint = _contract_footprint(facts, addresses)
        report['cycles'] = cycles
        report['footprint'] = footprint
        report['product'] = cycles * footprint
        report['queries'] = counters.as_dict()
        report['seconds'] = deadline.elapsed
    return (compiled, report)


LIMITS: Dict[str, float] = {'aggregate_nodes': 1000000, 'aggregate_validation_attempts': 100000, 'query_active_seconds': 0.1, 'slice_seconds': 0.002, 'slice_nodes': 2048, 'frontier_per_query': 4096, 'resident_queries': 8}


CODECS = ('absolute', 'static_rank', 'vector_block', 'structural_rank')
VECTOR_BLOCK_WIDTH = 5

class DomainError(ValueError):
    """An input domain, index or compilation was malformed or out of range."""

def canonical_json(value: object) -> str:
    """UTF-8 canonical form, without a trailing newline."""
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False)

def object_digest(value: object) -> str:
    """SHA256 of the canonical bytes of an object."""
    return hashlib.sha256(canonical_json(value).encode('utf-8')).hexdigest()

def normalise_compilation(facts: ProgramFacts, compiled: dict) -> dict:
    """Bundles by increasing operation ID within each engine, trailing empties cut."""
    if not isinstance(compiled, dict):
        raise DomainError('a compilation must be an object')
    bundles = compiled.get('bundles')
    scratch = compiled.get('scratch')
    if not isinstance(bundles, list) or not isinstance(scratch, dict):
        raise DomainError('a compilation requires a bundles list and a scratch mapping')
    cleaned: List[Dict[str, List[int]]] = []
    for cycle, bundle in enumerate(bundles):
        if not isinstance(bundle, dict):
            raise DomainError(f'bundle {cycle} must be an object')
        engines: Dict[str, List[int]] = {}
        for engine, op_ids in bundle.items():
            if engine not in machine.ENGINE_LIMITS:
                raise DomainError(f'bundle {cycle} names unknown engine {engine!r}')
            if not isinstance(op_ids, list):
                raise DomainError(f'bundle {cycle} engine {engine} must hold a list')
            ordered = sorted(op_ids)
            if len(set(ordered)) != len(ordered):
                raise DomainError(f'bundle {cycle} repeats an operation')
            if ordered:
                engines[engine] = ordered
        cleaned.append(engines)
    while cleaned and (not cleaned[-1]):
        cleaned.pop()
    if not cleaned:
        raise DomainError('a compilation must emit at least one bundle')
    placed = [op_id for bundle in cleaned for ids in bundle.values() for op_id in ids]
    if sorted(placed) != list(range(facts.count)):
        raise DomainError('every operation must appear exactly once in the bundles')
    if set(scratch) != set(facts.value_names):
        raise DomainError('every produced value requires exactly one scratch address')
    return {'bundles': cleaned, 'scratch': {name: scratch[name] for name in sorted(scratch)}}

def issue_cycles_of(program: dict, bundles: Sequence[dict]) -> Dict[int, int]:
    return machine._collect_issue_cycles(program, list(bundles))

def objective(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]):
    cycles = max(times.values()) + 1
    scratch = _contract_footprint(facts, addresses)
    return (cycles, scratch, cycles * scratch)

def _plain_int(value: object) -> bool:
    return isinstance(value, int) and (not isinstance(value, bool))

def _checked_domain(values: object, label: str) -> Tuple[int, ...]:
    if not isinstance(values, (list, tuple)):
        raise DomainError(f'{label}: a domain must be a list of integers')
    items = list(values)
    if not items:
        raise DomainError(f'{label}: a declared domain must be nonempty')
    for item in items:
        if not _plain_int(item):
            raise DomainError(f'{label}: domains hold plain integers, not {item!r}')
        if item < 0:
            raise DomainError(f'{label}: negative domain value {item}')
    if items != sorted(set(items)):
        raise DomainError(f'{label}: domains must be sorted, unique and explicit')
    return tuple(items)

@dataclass(frozen=True)
class Domain:
    identifier: str
    family: str
    program: dict
    facts: ProgramFacts
    selected_operations: Tuple[int, ...]
    selected_values: Tuple[str, ...]
    time_domains: Dict[int, Tuple[int, ...]]
    address_domains: Dict[str, Tuple[int, ...]]
    fixed_times: Dict[int, int]
    fixed_addresses: Dict[str, int]
    incumbent: Optional[dict]
    incumbent_times: Optional[Dict[int, int]]
    incumbent_addresses: Optional[Dict[str, int]]
    target: Optional[Tuple[int, int]]
    record: dict

    @staticmethod
    def from_record(record: dict, memo: Optional[dict]=None) -> 'Domain':
        """Build and check one declared domain."""
        if not isinstance(record, dict):
            raise DomainError('a domain record must be an object')
        for key in ('id', 'program', 'selected_operations', 'time_domains', 'address_domains', 'fixed_times', 'fixed_addresses'):
            if key not in record:
                raise DomainError(f'domain record is missing {key!r}')
        program = record['program']
        if memo is not None and memo.get('program') is program:
            facts = memo['facts']
        else:
            machine.validate_program(program)
            facts = derive(program)
            if memo is not None:
                memo.clear()
                memo.update(program=program, facts=facts, incumbents={})
        selected = record['selected_operations']
        if not isinstance(selected, (list, tuple)):
            raise DomainError('selected_operations must be a list')
        selected_ops = tuple(selected)
        for op_id in selected_ops:
            if not _plain_int(op_id) or not 0 <= op_id < facts.count:
                raise DomainError(f'unknown selected operation {op_id!r}')
        if selected_ops != tuple(sorted(set(selected_ops))):
            raise DomainError('selected_operations must be sorted and unique')
        time_domains: Dict[int, Tuple[int, ...]] = {}
        for key, values in record['time_domains'].items():
            op_id = _key_to_op(key, facts.count)
            time_domains[op_id] = _checked_domain(values, f'time domain {op_id}')
            for value in time_domains[op_id]:
                if value >= facts.horizon:
                    raise DomainError(f'time domain {op_id}: {value} is at or past horizon {facts.horizon}')
        fixed_times: Dict[int, int] = {}
        for key, value in record['fixed_times'].items():
            op_id = _key_to_op(key, facts.count)
            if not _plain_int(value) or not 0 <= value < facts.horizon:
                raise DomainError(f'fixed time for operation {op_id} is out of range')
            fixed_times[op_id] = value
        if set(time_domains) != set(selected_ops):
            raise DomainError('a time domain is required for exactly the selected operations')
        if set(time_domains) & set(fixed_times):
            raise DomainError('an operation cannot be both selected and fixed in time')
        if set(time_domains) | set(fixed_times) != set(range(facts.count)):
            raise DomainError('every operation needs exactly one variable or fixed time')
        expected_values = tuple((facts.dest[op_id] for op_id in selected_ops if facts.dest[op_id] is not None))
        address_domains: Dict[str, Tuple[int, ...]] = {}
        for name, values in record['address_domains'].items():
            if name not in facts.value_names:
                raise DomainError(f'address domain names unknown value {name!r}')
            width = facts.width[name]
            address_domains[name] = _checked_domain(values, f'address domain {name}')
            for value in address_domains[name]:
                _check_address(name, value, width)
        if tuple(sorted(address_domains)) != tuple(sorted(expected_values)):
            raise DomainError('selected values must be exactly the results of the selected operations')
        fixed_addresses: Dict[str, int] = {}
        for name, value in record['fixed_addresses'].items():
            if name not in facts.value_names:
                raise DomainError(f'fixed address names unknown value {name!r}')
            if not _plain_int(value):
                raise DomainError(f'fixed address for {name!r} must be an integer')
            _check_address(name, value, facts.width[name])
            fixed_addresses[name] = value
        if set(address_domains) & set(fixed_addresses):
            raise DomainError('a value cannot be both selected and fixed in address')
        if set(address_domains) | set(fixed_addresses) != set(facts.value_names):
            raise DomainError('every value needs exactly one variable or fixed address')
        incumbent = record.get('incumbent')
        incumbent_times: Optional[Dict[int, int]] = None
        incumbent_addresses: Optional[Dict[str, int]] = None
        if incumbent is not None:
            if not isinstance(incumbent, dict) or 'bundles' not in incumbent or 'scratch' not in incumbent:
                raise DomainError('a malformed incumbent is not a legal domain input')
            known = None
            if memo is not None:
                incumbent_key = canonical_json(incumbent)
                known = memo['incumbents'].get(incumbent_key)
            if known is None:
                try:
                    machine.check_compilation(program, incumbent)
                except (machine.CompileError, machine.ProgramError) as exc:
                    raise DomainError(f'the incumbent is not a legal compilation: {exc}') from exc
                known = issue_cycles_of(program, incumbent['bundles'])
                if memo is not None:
                    memo['incumbents'][incumbent_key] = known
            incumbent_times = dict(known)
            incumbent_addresses = dict(incumbent['scratch'])
            for op_id, fixed in fixed_times.items():
                if incumbent_times[op_id] != fixed:
                    raise DomainError(f'the incumbent contradicts the fixed time of operation {op_id}')
            for name, fixed in fixed_addresses.items():
                if incumbent_addresses[name] != fixed:
                    raise DomainError(f'the incumbent contradicts the fixed address of value {name!r}')
        target = record.get('target')
        if target is not None:
            if not isinstance(target, (list, tuple)) or len(target) != 2 or (not all((_plain_int(value) and value >= 1 for value in target))):
                raise DomainError('a target must be a pair of positive integers')
            target = (int(target[0]), int(target[1]))
        return Domain(identifier=str(record['id']), family=str(record.get('family', 'unspecified')), program=program, facts=facts, selected_operations=selected_ops, selected_values=tuple(sorted(address_domains)), time_domains=time_domains, address_domains=address_domains, fixed_times=fixed_times, fixed_addresses=fixed_addresses, incumbent=incumbent, incumbent_times=incumbent_times, incumbent_addresses=incumbent_addresses, target=target, record=record)

    @property
    def address_order(self) -> Tuple[str, ...]:
        """Selected address fields in producer-ID order: the offset order."""
        return tuple(sorted(self.address_domains, key=lambda name: self.facts.producers[name]))

    def cartesian_size(self) -> int:
        size = 1
        for values in self.time_domains.values():
            size *= len(values)
        for values in self.address_domains.values():
            size *= len(values)
        return size

    def digest(self) -> str:
        """The canonical digest of the declared domain, program included."""
        return object_digest({'id': self.identifier, 'family': self.family, 'program': self.program, 'selected_operations': list(self.selected_operations), 'time_domains': {str(k): list(v) for k, v in sorted(self.time_domains.items())}, 'address_domains': {k: list(v) for k, v in sorted(self.address_domains.items())}, 'fixed_times': {str(k): v for k, v in sorted(self.fixed_times.items())}, 'fixed_addresses': dict(sorted(self.fixed_addresses.items())), 'incumbent': self.incumbent, 'target': list(self.target) if self.target else None})

    def ordered_domain(self, key: Tuple[str, object]) -> Tuple[int, ...]:
        """The declared domain of one decision, incumbent choice first."""
        kind, which = key
        if kind == 'time':
            values = self.time_domains[which]
            preferred = self.incumbent_times.get(which) if self.incumbent_times else None
        else:
            values = self.address_domains[which]
            preferred = self.incumbent_addresses.get(which) if self.incumbent_addresses else None
        return _incumbent_first(values, preferred)

    def decision_keys(self) -> Tuple[Tuple[str, object], ...]:
        """Every decision, in **offset** order: times by op ID, then addresses."""
        return tuple((('time', op_id) for op_id in self.selected_operations)) + tuple((('address', name) for name in self.address_order))

def _key_to_op(key: object, count: int) -> int:
    if _plain_int(key):
        op_id = key
    elif isinstance(key, str):
        try:
            op_id = int(key)
        except ValueError as exc:
            raise DomainError(f'operation key {key!r} is not an integer') from exc
    else:
        raise DomainError(f'operation key {key!r} is not an integer')
    if not 0 <= op_id < count:
        raise DomainError(f'operation key {key!r} is out of range')
    return op_id

def _check_address(name: str, value: int, width: int) -> None:
    if value < 0:
        raise DomainError(f'value {name!r}: negative address {value}')
    if width == machine.VLEN and value % machine.VLEN != 0:
        raise DomainError(f'vector {name!r}: address {value} is not aligned')
    if value + width > machine.SCRATCH_WORDS:
        raise DomainError(f'value {name!r}: address {value} ends past {machine.SCRATCH_WORDS}')

def _incumbent_first(values: Sequence[int], preferred: Optional[int]) -> Tuple[int, ...]:
    ordered = sorted(values)
    if preferred is not None and preferred in ordered:
        return (preferred,) + tuple((value for value in ordered if value != preferred))
    return tuple(ordered)

@dataclass(frozen=True)
class FieldSpec:
    """One field of the fixed layout."""
    key: Tuple[str, object]
    offset: int
    width: int

    def read(self, index: int) -> int:
        if self.width == 0:
            return 0
        return index >> self.offset & (1 << self.width) - 1

    def write(self, value: int) -> int:
        if self.width == 0:
            if value != 0:
                raise DomainError(f'{self.key}: a zero-width field only admits 0')
            return 0
        if not 0 <= value < 1 << self.width:
            raise DomainError(f'{self.key}: field value {value} does not fit {self.width} bits')
        return value << self.offset

@dataclass(frozen=True)
class Layout:
    """The fixed field layout of one domain under one codec."""
    codec: str
    width: int
    fields: Tuple[FieldSpec, ...]
    by_key: Dict[Tuple[str, object], FieldSpec]

    def field(self, key: Tuple[str, object]) -> FieldSpec:
        return self.by_key[key]

def _rank_width(size: int) -> int:
    if size < 1:
        raise DomainError('a rank field requires a nonempty declared domain')
    return (size - 1).bit_length()

def layout(domain: Domain, codec: str) -> Layout:
    if codec not in CODECS:
        raise DomainError(f'unknown codec {codec!r}')
    fields: List[FieldSpec] = []
    offset = 0
    for key in domain.decision_keys():
        kind, which = key
        if codec in ('static_rank', 'structural_rank'):
            width = _rank_width(len(domain.ordered_domain(key)))
        elif kind == 'time':
            width = time_width(domain.facts.horizon)
        elif codec == 'vector_block' and domain.facts.width[which] == machine.VLEN:
            width = VECTOR_BLOCK_WIDTH
        else:
            width = ADDRESS_WIDTH
        fields.append(FieldSpec(key=key, offset=offset, width=width))
        offset += width
    return Layout(codec=codec, width=offset, fields=tuple(fields), by_key={spec.key: spec for spec in fields})

class State:
    """The prefix state of one decode."""
    __slots__ = ('domain', 'times', 'addresses', 'lifetimes', 'counters')

    def __init__(self, domain: Domain) -> None:
        self.domain = domain
        self.times: Dict[int, int] = dict(domain.fixed_times)
        self.addresses: Dict[str, int] = dict(domain.fixed_addresses)
        self.lifetimes: Optional[Dict[str, Tuple[int, int]]] = None
        self.counters: Dict[str, int] = {'option_constructions': 0, 'options_considered': 0, 'legality_checks': 0}

    def copy(self) -> 'State':
        """A branch of the same traversal."""
        clone = State.__new__(State)
        clone.domain = self.domain
        clone.times = dict(self.times)
        clone.addresses = dict(self.addresses)
        clone.lifetimes = self.lifetimes
        clone.counters = self.counters
        return clone

    def schedule_conflict(self) -> Optional[str]:
        """A contradiction among the decisions already in place, if any."""
        facts = self.domain.facts
        for op_id, cycle in sorted(self.times.items()):
            for predecessor, lag in facts.predecessors[op_id].items():
                if predecessor in self.times and cycle < self.times[predecessor] + lag:
                    return f'operation {op_id} issues at {cycle}, before operation {predecessor} is ready at {self.times[predecessor] + lag}'
        usage: Dict[Tuple[str, int], int] = {}
        for op_id, cycle in self.times.items():
            key = (facts.engine[op_id], cycle)
            usage[key] = usage.get(key, 0) + 1
            if usage[key] > machine.ENGINE_LIMITS[key[0]]:
                return f'cycle {cycle} exceeds the {key[0]} issue limit'
        return None

    def time_options(self, op_id: int) -> Tuple[int, ...]:
        facts = self.domain.facts
        declared = self.domain.ordered_domain(('time', op_id))
        self.counters['option_constructions'] += 1
        usage: Dict[Tuple[str, int], int] = {}
        for other, cycle in self.times.items():
            key = (facts.engine[other], cycle)
            usage[key] = usage.get(key, 0) + 1
        legal: List[int] = []
        engine = facts.engine[op_id]
        limit = machine.ENGINE_LIMITS[engine]
        for candidate in declared:
            self.counters['options_considered'] += 1
            self.counters['legality_checks'] += 1
            ok = True
            for predecessor, lag in facts.predecessors[op_id].items():
                if predecessor in self.times and candidate < self.times[predecessor] + lag:
                    ok = False
                    break
            if ok:
                for successor, lag in facts.successors[op_id]:
                    if successor in self.times and candidate + lag > self.times[successor]:
                        ok = False
                        break
            if ok and usage.get((engine, candidate), 0) >= limit:
                ok = False
            if ok:
                legal.append(candidate)
        return tuple(legal)

    def recompute_lifetimes(self) -> None:
        """Complete lifetimes once every issue time is known."""
        self.lifetimes = lifetimes(self.domain.facts, self.times)

    def fixed_address_conflict(self) -> Optional[str]:
        facts = self.domain.facts
        fixed = sorted(self.domain.fixed_addresses)
        for i, first in enumerate(fixed):
            for second in fixed[i + 1:]:
                self.counters['legality_checks'] += 1
                if self._collides(first, self.addresses[first], second):
                    return f'fixed values {first!r} and {second!r} share scratch while both are live, after the selected reads moved'
        return None

    def _collides(self, name: str, base: int, other: str) -> bool:
        facts = self.domain.facts
        other_base = self.addresses[other]
        width = facts.width[name]
        other_width = facts.width[other]
        if not (base < other_base + other_width and other_base < base + width):
            return False
        start, end = self.lifetimes[name]
        other_start, other_end = self.lifetimes[other]
        return start <= other_end and other_start <= end

    def allocation_order(self) -> Tuple[str, ...]:
        facts = self.domain.facts
        selected = list(self.domain.address_domains)
        vectors = [name for name in selected if facts.width[name] == machine.VLEN]
        scalars = [name for name in selected if facts.width[name] != machine.VLEN]

        def ordering(name: str) -> Tuple[int, int]:
            return (self.lifetimes[name][0], facts.producers[name])
        return tuple(sorted(vectors, key=ordering) + sorted(scalars, key=ordering))

    def address_options(self, name: str) -> Tuple[int, ...]:
        declared = self.domain.ordered_domain(('address', name))
        self.counters['option_constructions'] += 1
        placed = sorted(self.addresses)
        legal: List[int] = []
        for candidate in declared:
            self.counters['options_considered'] += 1
            ok = True
            for other in placed:
                self.counters['legality_checks'] += 1
                if self._collides(name, candidate, other):
                    ok = False
                    break
            if ok:
                legal.append(candidate)
        return tuple(legal)

def options(domain: Domain, prefix: State, decision: Tuple[str, object]) -> Tuple[int, ...]:
    if prefix.domain is not domain:
        raise DomainError('the prefix state belongs to a different domain')
    kind, which = decision
    if kind == 'time':
        return prefix.time_options(which)
    if kind == 'address':
        if prefix.lifetimes is None:
            raise DomainError('address options require a completed schedule')
        return prefix.address_options(which)
    raise DomainError(f'unknown decision kind {kind!r}')

def encode(domain: Domain, compiled: dict, codec: str) -> int:
    plan = layout(domain, codec)
    facts = domain.facts
    normalised = normalise_compilation(facts, compiled)
    times = issue_cycles_of(domain.program, normalised['bundles'])
    addresses = dict(normalised['scratch'])
    for op_id, fixed in domain.fixed_times.items():
        if times[op_id] != fixed:
            raise DomainError(f'operation {op_id} contradicts its fixed time')
    for name, fixed in domain.fixed_addresses.items():
        if addresses[name] != fixed:
            raise DomainError(f'value {name!r} contradicts its fixed address')
    state = State(domain)
    if state.schedule_conflict() is not None:
        raise DomainError('the fixed decisions of this domain are contradictory')
    index = 0
    for op_id in domain.selected_operations:
        key = ('time', op_id)
        value = times[op_id]
        declared = domain.ordered_domain(key)
        legal = state.time_options(op_id)
        index |= plan.field(key).write(_field_value(codec, key, value, declared, legal, False))
        state.times[op_id] = value
    state.recompute_lifetimes()
    if state.fixed_address_conflict() is not None:
        raise DomainError('this schedule puts two fixed allocations in conflict')
    for name in state.allocation_order():
        key = ('address', name)
        value = addresses[name]
        declared = domain.ordered_domain(key)
        legal = state.address_options(name)
        is_vector = facts.width[name] == machine.VLEN
        index |= plan.field(key).write(_field_value(codec, key, value, declared, legal, is_vector))
        state.addresses[name] = value
    if domain.target is not None:
        cycles, scratch, _ = objective(facts, state.times, state.addresses)
        if cycles > domain.target[0] or scratch > domain.target[1]:
            raise DomainError("this compilation misses the domain's target")
    return index

def _field_value(codec: str, key: Tuple[str, object], value: int, declared: Tuple[int, ...], legal: Tuple[int, ...], is_vector: bool) -> int:
    if value not in legal:
        raise DomainError(f'{key}: {value} is not a legal choice, so this object is outside F_d')
    if codec == 'structural_rank':
        return legal.index(value)
    if codec == 'static_rank':
        return declared.index(value)
    if codec == 'vector_block' and is_vector:
        if value % machine.VLEN != 0:
            raise DomainError(f'{key}: {value} is not an aligned vector block')
        return value // machine.VLEN
    return value


def cycle_bound(facts: ProgramFacts, times: Dict[int, int]) -> int:
    bound = facts.cycle_lower_bound()
    if times:
        bound = max(bound, 1 + max(times.values()))
    return bound

def scratch_bound(facts: ProgramFacts, addresses: Dict[str, int], live_width: Optional[int]=None) -> int:
    bound = facts.memory_lower_bound()
    for name, base in addresses.items():
        bound = max(bound, base + facts.width[name])
    if live_width is not None:
        bound = max(bound, live_width)
    return bound

def peak_live_width(facts: ProgramFacts, live: Dict[str, Tuple[int, int]]) -> int:
    """The largest total width of values live in one cycle."""
    if not live:
        return 0
    last = max((end for _, end in live.values()))
    first = min((start for start, _ in live.values()))
    peak = 0
    for cycle in range(first, last + 1):
        total = 0
        for name, (start, end) in live.items():
            if start <= cycle <= end:
                total += facts.width[name]
        peak = max(peak, total)
    return peak

@dataclass
class SearchReport:
    """Everything one search consumed and everything it concluded."""
    arm: str
    domain_id: str
    domain_sha256: str
    status: str = 'UNKNOWN'
    reason: str = ''
    incumbent_product: Optional[int] = None
    best_product: Optional[int] = None
    best_cycles: Optional[int] = None
    best_scratch: Optional[int] = None
    best_times: Optional[Dict[int, int]] = None
    best_addresses: Optional[Dict[str, int]] = None
    best_compilation: Optional[dict] = None
    best_identity: Optional[str] = None
    best_index: Optional[str] = None
    improved: bool = False
    nodes: int = 0
    pruned: int = 0
    completions: int = 0
    validations: int = 0
    case_checks: int = 0
    duplicate_lookups: int = 0
    duplicate_hits: int = 0
    option_constructions: int = 0
    options_considered: int = 0
    legality_checks: int = 0
    dead_ends: int = 0
    interrupted_validations: int = 0
    deadline_expired: bool = False
    rejected_completions: List[dict] = _dataclass_field(default_factory=list)
    seconds: float = 0.0

    def to_row(self) -> dict:
        row = dict(self.__dict__)
        row['best_times'] = None if self.best_times is None else {str(key): value for key, value in sorted(self.best_times.items())}
        row['best_addresses'] = None if self.best_addresses is None else dict(sorted(self.best_addresses.items()))
        return row


def physical_address_domain(facts: ProgramFacts, name: str, ceiling: int) -> List[int]:
    width = facts.width[name]
    if width == machine.VLEN:
        return [base for base in range(0, ceiling - width + 1, machine.VLEN)]
    return list(range(0, ceiling - width + 1))


@dataclass
class _base_PropagationStats:
    """Counts by rule, affected domains and the incremental certificate digest."""
    keep: bool = False
    counts: Dict[str, int] = _field(default_factory=dict)
    removed_values: Dict[str, int] = _field(default_factory=dict)
    certificates: List[tuple] = _field(default_factory=list)
    affected_domains: List[str] = _field(default_factory=list)
    _affected_seen: set = _field(default_factory=set)
    _digest: object = _field(default_factory=hashlib.sha256)
    stream_length: int = 0
    current_domain: Optional[str] = None

    def emit(self, certificate: tuple, removed: int=0) -> None:
        rule = certificate[0]
        self.counts[rule] = self.counts.get(rule, 0) + 1
        if removed:
            self.removed_values[rule] = self.removed_values.get(rule, 0) + removed
        self._digest.update(repr(certificate).encode('utf-8'))
        self._digest.update(b'\n')
        self.stream_length += 1
        if self.current_domain is not None and self.current_domain not in self._affected_seen:
            self._affected_seen.add(self.current_domain)
            self.affected_domains.append(self.current_domain)
        if self.keep:
            self.certificates.append(certificate)

    def digest(self) -> str:
        return self._digest.hexdigest()

    def summary(self) -> dict:
        joined = '\n'.join(self.affected_domains)
        return {'counts': dict(sorted(self.counts.items())), 'removed_values': dict(sorted(self.removed_values.items())), 'certificate_stream_sha256': self.digest(), 'certificate_stream_length': self.stream_length, 'affected_domain_count': len(self.affected_domains), 'affected_domain_list_sha256': hashlib.sha256(joined.encode()).hexdigest(), 'affected_domains_first64': [d[:16] for d in self.affected_domains[:64]]}

class Propagation:

    def __init__(self, domain: Domain, stats: _base_PropagationStats) -> None:
        facts = domain.facts
        self.domain = domain
        self.facts = facts
        self.stats = stats
        self.selected = tuple(domain.selected_operations)
        selected = set(self.selected)
        edges = []
        for v in range(facts.count):
            for u, lag in facts.predecessors[v].items():
                if u in selected or v in selected:
                    edges.append((u, v, lag))
        self.edges = tuple(sorted(edges))
        self.fixed_times = dict(domain.fixed_times)
        base_usage: Dict[Tuple[str, int], List[int]] = {}
        for op, cycle in sorted(self.fixed_times.items()):
            base_usage.setdefault((facts.engine[op], cycle), []).append(op)
        self.base_usage = base_usage
        self.base_count = {key: len(ops) for key, ops in base_usage.items()}
        self.fixed_time_max = max(self.fixed_times.values(), default=-1)
        self.cycle_floor = facts.cycle_lower_bound()
        self.widest = facts.memory_lower_bound()
        self.selected_values = tuple(domain.address_order)
        selected_values = set(self.selected_values)
        self.fixed_addresses = dict(domain.fixed_addresses)
        self.fixed_end_max = max((a + facts.width[n] for n, a in self.fixed_addresses.items()), default=0)
        self.static_values = []
        self.dynamic_values = []
        for name in facts.value_names:
            ops = (facts.producers[name],) + tuple(facts.consumers[name])
            if any((op in selected for op in ops)):
                self.dynamic_values.append(name)
            else:
                self.static_values.append(name)
        self.span = facts.horizon + max(facts.latency, default=0) + 2
        static = [0] * (self.span + 1)
        for name in self.static_values:
            p = facts.producers[name]
            start = self.fixed_times[p] + facts.latency[p]
            end = max([start] + [self.fixed_times[c] for c in facts.consumers[name]])
            static[start] += facts.width[name]
            static[end + 1] -= facts.width[name]
        running, levels = (0, [])
        for delta in static:
            running += delta
            levels.append(running)
        self.static_levels = levels
        table = [[(level, -cycle) for cycle, level in enumerate(levels)]]
        width = 1
        while 2 * width <= len(levels):
            previous = table[-1]
            table.append([max(previous[i], previous[i + width]) for i in range(len(levels) - 2 * width + 1)])
            width *= 2
        self._table = table
        self.static_peak = max(table[0]) if table[0] else (0, 0)
        self.selected_value_set = selected_values

    def _t(self, D: Dict[int, Tuple[int, ...]], op: int) -> Tuple[int, ...]:
        values = D.get(op)
        if values is None:
            return (self.fixed_times[op],)
        return values

    def times_fixpoint(self, D: Dict[int, Tuple[int, ...]]) -> Optional[Dict[int, Tuple[int, ...]]]:
        facts = self.facts
        emit = self.stats.emit
        D = dict(D)
        changed = True
        while changed:
            changed = False
            for u, v, lag in self.edges:
                du, dv = (self._t(D, u), self._t(D, v))
                high = dv[-1] - lag
                if du[-1] > high:
                    kept = du[:bisect.bisect_right(du, high)]
                    removed = du[len(kept):]
                    if u not in D:
                        emit(('EMPTY', 'time', u, ('PU', u, v, lag, dv[-1])))
                        return None
                    emit(('PU', u, v, lag, dv[-1], removed), len(removed))
                    if not kept:
                        emit(('EMPTY', 'time', u))
                        return None
                    D[u] = du = kept
                    changed = True
                low = du[0] + lag
                if dv[0] < low:
                    kept = dv[bisect.bisect_left(dv, low):]
                    removed = dv[:len(dv) - len(kept)]
                    if v not in D:
                        emit(('EMPTY', 'time', v, ('PL', u, v, lag, du[0])))
                        return None
                    emit(('PL', u, v, lag, du[0], removed), len(removed))
                    if not kept:
                        emit(('EMPTY', 'time', v))
                        return None
                    D[v] = kept
                    changed = True
            base = self.base_count
            singles: Dict[Tuple[str, int], List[int]] = {}
            for op in self.selected:
                values = D[op]
                if len(values) == 1:
                    singles.setdefault((facts.engine[op], values[0]), []).append(op)
            for (engine, cycle), ops in sorted(singles.items()):
                limit = machine.ENGINE_LIMITS[engine]
                if base.get((engine, cycle), 0) + len(ops) > limit:
                    emit(('EO', engine, cycle, tuple(sorted(self.base_usage.get((engine, cycle), []) + ops)), limit))
                    return None
            for op in self.selected:
                values = D[op]
                if len(values) == 1:
                    continue
                engine = facts.engine[op]
                limit = machine.ENGINE_LIMITS[engine]
                full = [cycle for cycle in values if base.get((engine, cycle), 0) + len(singles.get((engine, cycle), ())) >= limit]
                if not full:
                    continue
                for cycle in full:
                    emit(('EF', engine, cycle, op, limit), 1)
                kept = tuple((x for x in values if x not in full))
                if not kept:
                    emit(('EMPTY', 'time', op))
                    return None
                D[op] = kept
                changed = True
        return D

    def product_bound(self, D: Dict[int, Tuple[int, ...]], A: Optional[Dict[str, Tuple[int, ...]]]) -> Tuple[int, tuple, int, tuple]:
        facts = self.facts
        lc, lc_w = (self.cycle_floor, ('floor',))
        if self.fixed_time_max + 1 > lc:
            lc, lc_w = (self.fixed_time_max + 1, ('fixed',))
        for op in self.selected:
            candidate = D[op][0] + 1
            if candidate > lc:
                lc, lc_w = (candidate, ('min_time', op, D[op][0]))
        ls, ls_w = (self.widest, ('widest',))
        if self.fixed_end_max > ls:
            ls, ls_w = (self.fixed_end_max, ('fixed_end',))
        if A is not None:
            for name in self.selected_values:
                candidate = A[name][0] + facts.width[name]
                if candidate > ls:
                    ls, ls_w = (candidate, ('min_address', name, A[name][0]))
        live, cycle = self.compulsory_peak(D)
        if live > ls:
            ls, ls_w = (live, ('live', cycle))
        return (lc, lc_w, ls, ls_w)

    def _static_max(self, low: int, high: int) -> Tuple[int, int]:
        levels = self.static_levels
        if low >= len(levels):
            return (0, -low)
        high = min(high, len(levels) - 1)
        k = (high - low + 1).bit_length() - 1
        row = self._table[k]
        return max(row[low], row[high - (1 << k) + 1])

    def compulsory_peak(self, D: Dict[int, Tuple[int, ...]]) -> Tuple[int, int]:
        """Peak width of guaranteed-live intervals and its earliest cycle."""
        facts = self.facts
        delta: Dict[int, int] = {}
        for name in self.dynamic_values:
            p = facts.producers[name]
            dp = self._t(D, p)
            start_hi = dp[-1] + facts.latency[p]
            end_lo = dp[0] + facts.latency[p]
            for c in facts.consumers[name]:
                first = self._t(D, c)[0]
                if first > end_lo:
                    end_lo = first
            if start_hi <= end_lo:
                w = facts.width[name]
                delta[start_hi] = delta.get(start_hi, 0) + w
                delta[end_lo + 1] = delta.get(end_lo + 1, 0) - w
        best = self.static_peak
        if delta:
            points = sorted(delta)
            running = 0
            for i, point in enumerate(points[:-1]):
                running += delta[point]
                if running <= 0:
                    continue
                value, negative_cycle = self._static_max(point, points[i + 1] - 1)
                candidate = (value + running, negative_cycle)
                if candidate > best:
                    best = candidate
        return (best[0], -best[1])

    def prune(self, D, A, best: Optional[int]) -> Tuple[bool, int]:
        lc, lc_w, ls, ls_w = self.product_bound(D, A)
        if best is not None and lc * ls >= best:
            self.stats.emit(('PB', lc, ls, best, lc_w, ls_w))
            return (True, lc * ls)
        return (False, lc * ls)

    def address_pairs(self, lifetimes: Dict[str, Tuple[int, int]]) -> Tuple[tuple, ...]:
        """Live-overlapping pairs with at least one selected value, by producer IDs."""
        facts = self.facts
        names = sorted(facts.value_names, key=lambda n: facts.producers[n])
        pairs = []
        for i, first in enumerate(names):
            s1, e1 = lifetimes[first]
            for second in names[i + 1:]:
                if first not in self.selected_value_set and second not in self.selected_value_set:
                    continue
                s2, e2 = lifetimes[second]
                if s1 <= e2 and s2 <= e1:
                    pairs.append((first, second))
                    pairs.append((second, first))
        return tuple(pairs)

    def _a(self, A: Dict[str, Tuple[int, ...]], name: str) -> Tuple[int, ...]:
        values = A.get(name)
        if values is None:
            return (self.fixed_addresses[name],)
        return values

    def addresses_fixpoint(self, A: Dict[str, Tuple[int, ...]], pairs: Sequence[tuple]) -> Optional[Dict[str, Tuple[int, ...]]]:
        """Rule 3 (all times fixed): a_u needs a disjoint block in A_v."""
        facts = self.facts
        emit = self.stats.emit
        A = dict(A)
        changed = True
        while changed:
            changed = False
            for u, v in pairs:
                au, av = (self._a(A, u), self._a(A, v))
                lo = av[-1] - facts.width[u] + 1
                hi = av[0] + facts.width[v] - 1
                if lo > hi:
                    continue
                left = bisect.bisect_left(au, lo)
                right = bisect.bisect_right(au, hi)
                if left >= right:
                    continue
                removed = au[left:right]
                inputs = (u, v, av[-1], av[0], facts.width[u], facts.width[v])
                if u not in A:
                    emit(('EMPTY', 'address', u, ('AL',) + inputs))
                    return None
                kept = au[:left] + au[right:]
                emit(('AL',) + inputs + (removed,), len(removed))
                if not kept:
                    emit(('EMPTY', 'address', u))
                    return None
                A[u] = kept
                changed = True
        return A


class TimeState:
    __slots__ = ('D', 'singles', 'contrib', 'peak', 'parent', 'changed')

    def __init__(self, D, singles, parent=None, changed=None) -> None:
        self.D = D
        self.singles = singles
        self.contrib = None
        self.peak = None
        self.parent = parent
        self.changed = changed

class AddressState:
    __slots__ = ('A', 'info')

    def __init__(self, A, info) -> None:
        self.A = A
        self.info = info

class PairInfo:
    __slots__ = ('pairs', 'second_mask', 'all_mask', 'widths')

    def __init__(self, pairs: Sequence[tuple], facts) -> None:
        self.pairs = tuple(pairs)
        second: Dict[str, int] = {}
        for index, (u, v) in enumerate(self.pairs):
            second[v] = second.get(v, 0) | 1 << index
        self.second_mask = second
        self.all_mask = (1 << len(self.pairs)) - 1
        self.widths = facts.width

class SharedPropagation(Propagation):

    def __init__(self, domain, stats) -> None:
        super().__init__(domain, stats)
        facts = self.facts
        in_mask: Dict[int, int] = {}
        out_mask: Dict[int, int] = {}
        for index, (u, v, lag) in enumerate(self.edges):
            out_mask[u] = out_mask.get(u, 0) | 1 << index
            in_mask[v] = in_mask.get(v, 0) | 1 << index
        self.in_mask = in_mask
        self.out_mask = out_mask
        self.engine_of = {op: facts.engine[op] for op in self.selected}
        self.selected_index = {op: i for i, op in enumerate(self.selected)}
        values_of: Dict[int, List[int]] = {}
        for index, name in enumerate(self.dynamic_values):
            for op in (facts.producers[name],) + tuple(facts.consumers[name]):
                bucket = values_of.setdefault(op, [])
                if index not in bucket:
                    bucket.append(index)
        self.values_of = values_of

    def _singles_of(self, D) -> Dict[Tuple[str, int], tuple]:
        singles: Dict[Tuple[str, int], tuple] = {}
        engine = self.engine_of
        for op in self.selected:
            values = D[op]
            if len(values) == 1:
                key = (engine[op], values[0])
                singles[key] = singles.get(key, ()) + (op,)
        return singles

    def time_root(self, D) -> Optional[TimeState]:
        out = self.times_fixpoint(D)
        if out is None:
            return None
        return TimeState(out, self._singles_of(out))

    def time_child(self, parent: TimeState, op: int, value: int) -> Optional[TimeState]:
        emit = self.stats.emit
        edges = self.edges
        in_mask, out_mask = (self.in_mask, self.out_mask)
        fixed = self.fixed_times
        base = self.base_count
        engine_of = self.engine_of
        limits = machine.ENGINE_LIMITS
        Dp = parent.D
        old = Dp[op]
        D = dict(Dp)
        D[op] = (value,)
        changed = set()
        pending: List[int] = []
        cur = 0
        if old != (value,):
            changed.add(op)
            if old[-1] != value:
                cur |= in_mask.get(op, 0)
            if old[0] != value:
                cur |= out_mask.get(op, 0)
            pending.append(op)
        singles = parent.singles
        while True:
            nxt = 0
            while cur:
                low = cur & -cur
                i = low.bit_length() - 1
                cur ^= low
                u, v, lag = edges[i]
                du = D.get(u)
                if du is None:
                    du = (fixed[u],)
                dv = D.get(v)
                if dv is None:
                    dv = (fixed[v],)
                high = dv[-1] - lag
                if du[-1] > high:
                    kept = du[:bisect.bisect_right(du, high)]
                    removed = du[len(kept):]
                    if u not in D:
                        emit(('EMPTY', 'time', u, ('PU', u, v, lag, dv[-1])))
                        return None
                    emit(('PU', u, v, lag, dv[-1], removed), len(removed))
                    if not kept:
                        emit(('EMPTY', 'time', u))
                        return None
                    D[u] = du = kept
                    changed.add(u)
                    if len(kept) == 1:
                        pending.append(u)
                    m = in_mask.get(u, 0)
                    if m:
                        above = m >> i + 1 << i + 1
                        cur |= above
                        nxt |= m ^ above
                low_bound = du[0] + lag
                if dv[0] < low_bound:
                    kept = dv[bisect.bisect_left(dv, low_bound):]
                    removed = dv[:len(dv) - len(kept)]
                    if v not in D:
                        emit(('EMPTY', 'time', v, ('PL', u, v, lag, du[0])))
                        return None
                    emit(('PL', u, v, lag, du[0], removed), len(removed))
                    if not kept:
                        emit(('EMPTY', 'time', v))
                        return None
                    D[v] = kept
                    changed.add(v)
                    if len(kept) == 1:
                        pending.append(v)
                    m = out_mask.get(v, 0)
                    if m:
                        above = m >> i + 1 << i + 1
                        cur |= above
                        nxt |= m ^ above
            if pending:
                grown = dict(singles)
                touched = []
                for s in pending:
                    key = (engine_of[s], D[s][0])
                    grown[key] = grown.get(key, ()) + (s,)
                    if key not in touched:
                        touched.append(key)
                pending = []
                for key in sorted(touched):
                    engine, cycle = key
                    limit = limits[engine]
                    if base.get(key, 0) + len(grown[key]) > limit:
                        emit(('EO', engine, cycle, tuple(sorted(self.base_usage.get(key, []) + list(grown[key]))), limit))
                        return None
                newly: Dict[str, set] = {}
                for key in touched:
                    engine, cycle = key
                    limit = limits[engine]
                    count = base.get(key, 0)
                    if count + len(singles.get(key, ())) < limit <= count + len(grown[key]):
                        newly.setdefault(engine, set()).add(cycle)
                singles = grown
                if newly:
                    for s in self.selected:
                        full_cycles = newly.get(engine_of[s])
                        if full_cycles is None:
                            continue
                        values = D[s]
                        if len(values) == 1:
                            continue
                        full = [cycle for cycle in values if cycle in full_cycles]
                        if not full:
                            continue
                        engine = engine_of[s]
                        limit = limits[engine]
                        for cycle in full:
                            emit(('EF', engine, cycle, s, limit), 1)
                        kept = tuple((x for x in values if x not in full))
                        if not kept:
                            emit(('EMPTY', 'time', s))
                            return None
                        D[s] = kept
                        changed.add(s)
                        if len(kept) == 1:
                            pending.append(s)
                        if kept[-1] != values[-1]:
                            nxt |= in_mask.get(s, 0)
                        if kept[0] != values[0]:
                            nxt |= out_mask.get(s, 0)
            if not nxt and (not pending):
                break
            cur = nxt
        return TimeState(D, singles, parent, changed)

    def _contribution(self, D, name):
        facts = self.facts
        p = facts.producers[name]
        dp = D.get(p)
        if dp is None:
            dp = (self.fixed_times[p],)
        start_hi = dp[-1] + facts.latency[p]
        end_lo = dp[0] + facts.latency[p]
        fixed = self.fixed_times
        for c in facts.consumers[name]:
            dc_ = D.get(c)
            first = fixed[c] if dc_ is None else dc_[0]
            if first > end_lo:
                end_lo = first
        if start_hi <= end_lo:
            return (start_hi, end_lo, facts.width[name])
        return None

    def live_peak(self, state: TimeState) -> Tuple[int, int]:
        if state.peak is not None:
            return state.peak
        parent = state.parent
        names = self.dynamic_values
        D = state.D
        if parent is None or parent.contrib is None:
            contrib = [self._contribution(D, name) for name in names]
        else:
            contrib = list(parent.contrib)
            touched = set()
            values_of = self.values_of
            for op in state.changed:
                for index in values_of.get(op, ()):
                    touched.add(index)
            if not touched and parent.peak is not None:
                state.contrib = parent.contrib
                state.peak = parent.peak
                state.parent = state.changed = None
                return state.peak
            for index in touched:
                contrib[index] = self._contribution(D, names[index])
        delta: Dict[int, int] = {}
        for item in contrib:
            if item is not None:
                start_hi, end_lo, w = item
                delta[start_hi] = delta.get(start_hi, 0) + w
                delta[end_lo + 1] = delta.get(end_lo + 1, 0) - w
        best = self.static_peak
        if delta:
            points = sorted(delta)
            running = 0
            for i, point in enumerate(points[:-1]):
                running += delta[point]
                if running <= 0:
                    continue
                value, negative_cycle = self._static_max(point, points[i + 1] - 1)
                candidate = (value + running, negative_cycle)
                if candidate > best:
                    best = candidate
        state.contrib = contrib
        state.peak = (best[0], -best[1])
        state.parent = state.changed = None
        return state.peak

    def prune_state(self, state: TimeState, A, best: Optional[int]) -> Tuple[bool, int]:
        facts = self.facts
        D = state.D
        lc, lc_w = (self.cycle_floor, ('floor',))
        if self.fixed_time_max + 1 > lc:
            lc, lc_w = (self.fixed_time_max + 1, ('fixed',))
        for op in self.selected:
            candidate = D[op][0] + 1
            if candidate > lc:
                lc, lc_w = (candidate, ('min_time', op, D[op][0]))
        ls, ls_w = (self.widest, ('widest',))
        if self.fixed_end_max > ls:
            ls, ls_w = (self.fixed_end_max, ('fixed_end',))
        if A is not None:
            for name in self.selected_values:
                candidate = A[name][0] + facts.width[name]
                if candidate > ls:
                    ls, ls_w = (candidate, ('min_address', name, A[name][0]))
        live, cycle = self.live_peak(state)
        if live > ls:
            ls, ls_w = (live, ('live', cycle))
        if best is not None and lc * ls >= best:
            self.stats.emit(('PB', lc, ls, best, lc_w, ls_w))
            return (True, lc * ls)
        return (False, lc * ls)

    def address_root(self, A, pairs) -> Optional[AddressState]:
        info = PairInfo(pairs, self.facts)
        return self._address(dict(A), info, info.all_mask)

    def address_child(self, parent: AddressState, name: str, value: int) -> Optional[AddressState]:
        old = parent.A[name]
        A = dict(parent.A)
        A[name] = (value,)
        cur = 0
        if old[0] != value or old[-1] != value:
            cur = parent.info.second_mask.get(name, 0)
        return self._address(A, parent.info, cur)

    def _address(self, A, info: PairInfo, cur: int) -> Optional[AddressState]:
        width = info.widths
        emit = self.stats.emit
        pairs = info.pairs
        second = info.second_mask
        fixed = self.fixed_addresses
        while cur:
            nxt = 0
            while cur:
                low = cur & -cur
                i = low.bit_length() - 1
                cur ^= low
                u, v = pairs[i]
                au = A.get(u)
                if au is None:
                    au = (fixed[u],)
                av = A.get(v)
                if av is None:
                    av = (fixed[v],)
                lo = av[-1] - width[u] + 1
                hi = av[0] + width[v] - 1
                if lo > hi:
                    continue
                left = bisect.bisect_left(au, lo)
                right = bisect.bisect_right(au, hi)
                if left >= right:
                    continue
                removed = au[left:right]
                inputs = (u, v, av[-1], av[0], width[u], width[v])
                if u not in A:
                    emit(('EMPTY', 'address', u, ('AL',) + inputs))
                    return None
                kept = au[:left] + au[right:]
                emit(('AL',) + inputs + (removed,), len(removed))
                if not kept:
                    emit(('EMPTY', 'address', u))
                    return None
                A[u] = kept
                if kept[0] != au[0] or kept[-1] != au[-1]:
                    m = second.get(u, 0)
                    if m:
                        above = m >> i + 1 << i + 1
                        cur |= above
                        nxt |= m ^ above
            cur = nxt
        return AddressState(A, info)


VERSION = '1.0'
FROZEN_SOURCE_SHA256 = ''
CATALOGS = ('a4', 'a3')
TRAVERSALS = ('heap', 'dfs')
CODEC = 'structural_rank'
BASE_RADIUS = TIME_SLACK
FULL_RANGE = 'full'
PER_QUERY_LIMITS = {'query_max_cover': 4096, 'search_max_nodes': 1000000, 'search_max_candidate_validations': 100000, 'query_max_visited': 50000}

def product_caps(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int], objective: Optional[int]=None) -> dict:
    selected = set(window)
    cycles = max(times.values()) + 1
    scratch = _contract_footprint(facts, addresses)
    j0 = cycles * scratch if objective is None else objective
    fixed_times = [times[op] for op in range(facts.count) if op not in selected]
    fixed_ends = [addresses[name] + facts.width[name] for name in facts.value_names if facts.producers[name] not in selected]
    lc = max(facts.cycle_lower_bound(), 1 + max(fixed_times) if fixed_times else 0)
    ls = max(facts.memory_lower_bound(), max(fixed_ends) if fixed_ends else 0)
    out = {'J0': j0, 'C0': cycles, 'S0': scratch, 'LC': lc, 'LS': ls, 'fixed_time_max': max(fixed_times) if fixed_times else None, 'fixed_end_max': max(fixed_ends) if fixed_ends else None}
    if j0 <= 0:
        out.update(status='ZERO_OBJECTIVE', Ccap=None, Scap=None, reason='no strictly smaller nonnegative product than zero')
        return out
    lc, ls = (max(lc, 1), max(ls, 1))
    ccap = min(facts.horizon, (j0 - 1) // ls)
    scap = min(machine.SCRATCH_WORDS, (j0 - 1) // lc)
    out.update(LC=lc, LS=ls, Ccap=ccap, Scap=scap)
    if ccap < lc or scap < ls:
        out.update(status='NO_STRICT_IMPROVEMENT', reason=f'caps ({ccap}, {scap}) fall below lower bounds ({lc}, {ls})')
    else:
        out.update(status='OK', reason='')
    return out

def neighborhood_record(identifier: str, program: dict, facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int], radius) -> dict:
    """The UNCAPPED neighborhood of one window: the object the lemma speaks about."""
    window = tuple(sorted(set(window)))
    time_domains: Dict[str, List[int]] = {}
    for op in window:
        if radius == FULL_RANGE:
            low, high = (0, facts.horizon - 1)
        else:
            low, high = (max(0, times[op] - radius), min(times[op] + radius, facts.horizon - 1))
        time_domains[str(op)] = list(range(low, high + 1))
    address_domains = {facts.dest[op]: physical_address_domain(facts, facts.dest[op], machine.SCRATCH_WORDS) for op in window if facts.dest[op] is not None}
    return {'id': identifier, 'family': 'product', 'program': program, 'selected_operations': list(window), 'time_domains': time_domains, 'address_domains': address_domains, 'fixed_times': {str(op): times[op] for op in range(facts.count) if op not in window}, 'fixed_addresses': {name: addresses[name] for name in facts.value_names if name not in address_domains}, 'incumbent': compilation(facts, times, addresses), 'target': None}

def capped_record(record: dict, facts: ProgramFacts, caps: dict) -> dict:
    if caps['status'] != 'OK':
        raise ValueError('a capped record requires caps with status OK')
    ccap, scap = (caps['Ccap'], caps['Scap'])
    for key, value in record['fixed_times'].items():
        if value > ccap - 1:
            raise Infeasible(f'fixed operation {key} issues at {value}, past Ccap-1={ccap - 1}')
    for name, value in record['fixed_addresses'].items():
        if value + facts.width[name] > scap:
            raise Infeasible(f'fixed value {name!r} ends past Scap={scap}')
    time_domains = {}
    for key, values in record['time_domains'].items():
        kept = [value for value in values if value <= ccap - 1]
        if not kept:
            raise Infeasible(f'operation {key} has no cycle below Ccap={ccap}')
        time_domains[key] = kept
    address_domains = {}
    for name, values in record['address_domains'].items():
        kept = [value for value in values if value + facts.width[name] <= scap]
        if not kept:
            raise Infeasible(f'value {name!r} cannot fit Scap={scap}')
        address_domains[name] = kept
    return dict(record, time_domains=time_domains, address_domains=address_domains, target=None)

def product_record(identifier: str, program: dict, facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int], radius, caps: dict) -> dict:
    return capped_record(neighborhood_record(identifier, program, facts, times, addresses, window, radius), facts, caps)

def product_window_plan(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]) -> List[Tuple[int, ...]]:
    cycles = max(times.values()) + 1
    memory = _contract_footprint(facts, addresses)
    targets = targets_for(facts, cycles, memory)
    firsts = [target_memory < memory for _, target_memory in targets] or [True]
    seen = set()
    plan: List[Tuple[int, ...]] = []
    for scratch_first in firsts:
        for window in windows_for(facts, times, addresses, scratch_first=scratch_first):
            window = tuple(window)
            if window not in seen:
                seen.add(window)
                plan.append(window)
    return plan

@dataclass
class PropagationStats:
    """Counts by rule, affected domains and the incremental certificate digest."""
    keep: bool = False
    counts: Dict[str, int] = _field(default_factory=dict)
    removed_values: Dict[str, int] = _field(default_factory=dict)
    certificates: List[tuple] = _field(default_factory=list)
    affected_domains: List[str] = _field(default_factory=list)
    _affected_seen: set = _field(default_factory=set)
    _digest: object = _field(default_factory=hashlib.sha256)
    stream_length: int = 0
    current_domain: Optional[str] = None

    def emit(self, certificate: tuple, removed: int=0) -> None:
        rule = certificate[0]
        self.counts[rule] = self.counts.get(rule, 0) + 1
        if removed:
            self.removed_values[rule] = self.removed_values.get(rule, 0) + removed
        self._digest.update(repr(certificate).encode('utf-8'))
        self._digest.update(b'\n')
        self.stream_length += 1
        if self.current_domain is not None and self.current_domain not in self._affected_seen:
            self._affected_seen.add(self.current_domain)
            self.affected_domains.append(self.current_domain)
        if self.keep:
            self.certificates.append(certificate)

    def digest(self) -> str:
        return self._digest.hexdigest()

    def summary(self) -> dict:
        joined = '\n'.join(self.affected_domains)
        return {'counts': dict(sorted(self.counts.items())), 'removed_values': dict(sorted(self.removed_values.items())), 'certificate_stream_sha256': self.digest(), 'certificate_stream_length': self.stream_length, 'affected_domain_count': len(self.affected_domains), 'affected_domain_list_sha256': hashlib.sha256(joined.encode()).hexdigest(), 'affected_domains_first64': [d[:16] for d in self.affected_domains[:64]]}

class _Node:
    __slots__ = ('state', 'D', 'A', 'pairs', 'phase', 'position', 'order', 'ranks', 'disc', 'lb')

    def __init__(self, state, D, A, pairs, phase, position, order, ranks, disc, lb):
        self.state = state
        self.D = D
        self.A = A
        self.pairs = pairs
        self.phase = phase
        self.position = position
        self.order = order
        self.ranks = ranks
        self.disc = disc
        self.lb = lb

class _Stop(Exception):

    def __init__(self, reason: str, status: str='UNKNOWN') -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status

class _Improved(Exception):
    pass

class Expander:
    """Lazy children of a search node."""

    def __init__(self, domain: Domain, mode: str, stats: PropagationStats, report: SearchReport) -> None:
        if mode not in ('ss_bound', 'propagate'):
            raise ValueError(mode)
        self.domain = domain
        self.facts = domain.facts
        self.mode = mode
        self.stats = stats
        self.report = report
        self.prop = SharedPropagation(domain, stats) if mode == 'propagate' else None
        self.filtered = 0
        self.root_state: Optional[State] = None
        self.audit: Optional[Callable[[dict], None]] = None

    def _audit(self, outcome: str, state: State, D, A) -> None:
        if self.audit is None:
            return
        event = {'outcome': outcome, 'times': dict(state.times), 'addresses': dict(state.addresses), 'D': D, 'A': A}
        if D is not None:
            lc, _, ls, _ = self.prop.product_bound(D, A)
            event.update(LC=lc, LS=ls)
        self.audit(event)

    def _ss_prunes(self, state: State, live_width: Optional[int], best: Optional[int]) -> bool:
        if best is None:
            return False
        lower = cycle_bound(self.facts, state.times) * scratch_bound(self.facts, {name: state.addresses[name] for name in state.addresses}, live_width)
        if lower >= best:
            self.report.pruned += 1
            return True
        return False

    def root(self, best: Optional[int]) -> Optional[_Node]:
        state = State(self.domain)
        self.root_state = state
        if self.mode == 'ss_bound':
            return _Node(state, None, None, None, 'time', 0, None, (), 0, 0)
        D = {op: tuple(self.domain.time_domains[op]) for op in self.domain.selected_operations}
        S = self.prop.time_root(D)
        if S is None:
            self._audit('inconsistent', state, None, None)
            self.report.dead_ends += 1
            return None
        pruned, lb = self.prop.prune_state(S, None, best)
        self._audit('pruned' if pruned else 'kept', state, S.D, None)
        if pruned:
            self.report.pruned += 1
            return None
        self.root_state = state
        return _Node(state, S, None, None, 'time', 0, None, (), 0, lb)

    def is_leaf(self, node: _Node) -> bool:
        return node.phase == 'address' and node.position == len(node.order)

    def children(self, node: _Node, best_ref: Callable[[], Optional[int]]) -> Iterator[_Node]:
        """Children in canonical rank order, generated lazily."""
        domain = self.domain
        facts = self.facts
        state = node.state
        selected = domain.selected_operations
        if node.phase == 'time' and node.position == len(selected):
            state.recompute_lifetimes()
            if state.fixed_address_conflict() is not None:
                self.report.dead_ends += 1
                return
            order = state.allocation_order()
            if self.mode == 'ss_bound':
                if self._ss_prunes(state, peak_live_width(facts, state.lifetimes), best_ref()):
                    return
                yield _Node(state, None, None, None, 'address', 0, order, node.ranks, node.disc, node.lb)
                return
            pairs = self.prop.address_pairs(state.lifetimes)
            A = {name: tuple(domain.address_domains[name]) for name in self.prop.selected_values}
            AS = self.prop.address_root(A, pairs)
            if AS is None:
                self._audit('inconsistent', state, None, None)
                self.report.dead_ends += 1
                return
            pruned, lb = self.prop.prune_state(node.D, AS.A, best_ref())
            self._audit('pruned' if pruned else 'kept', state, node.D.D, AS.A)
            if pruned:
                self.report.pruned += 1
                return
            yield _Node(state, node.D, AS, pairs, 'address', 0, order, node.ranks, node.disc, lb)
            return
        if node.phase == 'time':
            op = selected[node.position]
            legal = options(domain, state, ('time', op))
            if not legal:
                self.report.dead_ends += 1
                return
            allowed = None if self.mode == 'ss_bound' else set(node.D.D[op])
            for rank, value in enumerate(legal):
                if allowed is not None and value not in allowed:
                    self.filtered += 1
                    continue
                nxt = state.copy()
                nxt.times[op] = value
                ranks = node.ranks + (rank,)
                disc = node.disc + (1 if rank else 0)
                if self.mode == 'ss_bound':
                    if self._ss_prunes(nxt, None, best_ref()):
                        continue
                    yield _Node(nxt, None, None, None, 'time', node.position + 1, None, ranks, disc, 0)
                    continue
                S2 = self.prop.time_child(node.D, op, value)
                if S2 is None:
                    self._audit('inconsistent', nxt, None, None)
                    self.report.dead_ends += 1
                    continue
                pruned, lb = self.prop.prune_state(S2, None, best_ref())
                self._audit('pruned' if pruned else 'kept', nxt, S2.D, None)
                if pruned:
                    self.report.pruned += 1
                    continue
                yield _Node(nxt, S2, None, None, 'time', node.position + 1, None, ranks, disc, lb)
            return
        name = node.order[node.position]
        legal = options(domain, state, ('address', name))
        if not legal:
            self.report.dead_ends += 1
            return
        if self.mode == 'ss_bound':
            live_width = peak_live_width(facts, state.lifetimes)
            allowed = None
        else:
            allowed = set(node.A.A[name])
        for rank, value in enumerate(legal):
            if allowed is not None and value not in allowed:
                self.filtered += 1
                continue
            nxt = state.copy()
            nxt.addresses[name] = value
            ranks = node.ranks + (rank,)
            disc = node.disc + (1 if rank else 0)
            if self.mode == 'ss_bound':
                if self._ss_prunes(nxt, live_width, best_ref()):
                    continue
                yield _Node(nxt, None, None, None, 'address', node.position + 1, node.order, ranks, disc, 0)
                continue
            AS2 = self.prop.address_child(node.A, name, value)
            if AS2 is None:
                self._audit('inconsistent', nxt, None, None)
                self.report.dead_ends += 1
                continue
            pruned, lb = self.prop.prune_state(node.D, AS2.A, best_ref())
            self._audit('pruned' if pruned else 'kept', nxt, node.D.D, AS2.A)
            if pruned:
                self.report.pruned += 1
                continue
            yield _Node(nxt, node.D, AS2, node.pairs, 'address', node.position + 1, node.order, ranks, disc, lb)

class _Acceptor:

    def __init__(self, domain: Domain, report: SearchReport, meter: Meter, deadline: Callable[[], Optional[float]], clock: Callable[[], float], observe: Optional[Callable[[dict], None]]=None, collect: bool=False, stop_on_improvement: bool=False) -> None:
        self.domain = domain
        self.facts = domain.facts
        self.report = report
        self.meter = meter
        self.deadline = deadline
        self.clock = clock
        self.observe = observe
        self.collect = collect
        self.collected: Dict[str, dict] = {}
        self.stop_on_improvement = stop_on_improvement
        self.best: Optional[int] = report.best_product
        self.threshold: Optional[int] = report.incumbent_product
        self.seen: Dict[str, int] = {}

    def expired(self) -> bool:
        limit = self.deadline()
        return limit is not None and self.clock() >= limit

    def consider(self, state: State) -> None:
        report = self.report
        facts = self.facts
        report.completions += 1
        cycles, scratch, product = objective(facts, state.times, state.addresses)
        if self.domain.target is not None and (cycles > self.domain.target[0] or scratch > self.domain.target[1]):
            return
        compiled = compilation(facts, state.times, state.addresses)
        normalised = normalise_compilation(facts, compiled)
        identity = object_digest(normalised)
        report.duplicate_lookups += 1
        if identity in self.seen:
            report.duplicate_hits += 1
            return
        self.seen[identity] = product
        if self.observe is not None:
            self.observe({'identity': identity, 'product': product, 'cycles': cycles, 'scratch': scratch, 'compilation': normalised, 'times': dict(state.times), 'addresses': dict(state.addresses)})
        if self.collect:
            if self.threshold is None or product < self.threshold:
                self.collected[identity] = {'product': product, 'times': dict(state.times), 'addresses': dict(state.addresses)}
            return
        if self.best is not None and product >= self.best:
            return
        if self.expired():
            report.interrupted_validations += 1
            report.deadline_expired = True
            raise _Stop('the shared deadline expired before candidate validation')
        try:
            self.meter.record()
        except BudgetExhausted as exc:
            raise _Stop(exc.reason) from exc
        report.validations += 1
        try:
            machine.check_compilation(self.domain.program, normalised)
            for case in self.domain.program['cases']:
                machine.check_case(self.domain.program, normalised, case)
                report.case_checks += 1
        except (machine.CompileError, machine.ProgramError) as exc:
            report.rejected_completions.append({'identity': identity, 'times': {str(k): v for k, v in sorted(state.times.items())}, 'addresses': dict(sorted(state.addresses.items())), 'error': str(exc)})
            return
        if self.expired():
            report.interrupted_validations += 1
            report.deadline_expired = True
            raise _Stop('the shared deadline expired during candidate validation')
        self.best = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = dict(state.times)
        report.best_addresses = dict(state.addresses)
        report.best_compilation = normalised
        report.best_identity = identity
        report.improved = True
        try:
            report.best_index = str(encode(self.domain, normalised, CODEC))
        except DomainError:
            report.best_index = None
        if self.stop_on_improvement:
            raise _Improved()

def _new_report(domain: Domain, arm: str, incumbent: Optional[dict], digest: Optional[str]=None) -> SearchReport:
    report = SearchReport(arm=arm, domain_id=domain.identifier, domain_sha256=digest or domain.digest())
    if incumbent is not None:
        facts = domain.facts
        normalised = normalise_compilation(facts, incumbent)
        times = issue_cycles_of(domain.program, normalised['bundles'])
        addresses = dict(normalised['scratch'])
        cycles, scratch, product = objective(facts, times, addresses)
        report.incumbent_product = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = times
        report.best_addresses = addresses
        report.best_compilation = normalised
        report.best_identity = object_digest(normalised)
    return report

class _Aggregate:

    def __init__(self, node_ceiling: int, validation_ceiling: int) -> None:
        self.node_ceiling = node_ceiling
        self.validation_ceiling = validation_ceiling
        self.totals = {'nodes': 0, 'validations': 0, 'case_checks': 0, 'pruned': 0, 'completions': 0, 'dead_ends': 0, 'filtered': 0}

    def exhausted(self) -> Optional[str]:
        if self.node_ceiling - self.totals['nodes'] < 2:
            return 'aggregate_nodes'
        if self.validation_ceiling - self.totals['validations'] < 1:
            return 'aggregate_validations'
        return None

    def budget(self, remaining: float, limits: dict) -> Optional[Budget]:
        nodes_left = self.node_ceiling - self.totals['nodes']
        validations_left = self.validation_ceiling - self.totals['validations']
        if nodes_left < 2 or validations_left < 1:
            return None
        return Budget(seconds=max(remaining, 1e-09), max_cover=limits['query_max_cover'], max_visited=min(limits['search_max_nodes'], nodes_left - 1), max_records=min(limits['search_max_candidate_validations'], validations_left))

    def add(self, report: SearchReport, filtered: int=0) -> None:
        self.totals['nodes'] += report.nodes
        self.totals['validations'] += report.validations
        self.totals['case_checks'] += report.case_checks
        self.totals['pruned'] += report.pruned
        self.totals['completions'] += report.completions
        self.totals['dead_ends'] += report.dead_ends
        self.totals['filtered'] += filtered

def _count_by(labels: List[str]) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for label in labels:
        out[label] = out.get(label, 0) + 1
    return dict(sorted(out.items()))

def memory_group(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], k: int) -> Tuple[int, ...]:
    live = lifetimes(facts, times)
    if not live:
        return tuple(range(min(k, facts.count)))
    first = min((start for start, _ in live.values()))
    last = max((end for _, end in live.values()))
    peak, peak_cycle = (-1, first)
    for cycle in range(first, last + 1):
        total = sum((facts.width[n] for n, (s, e) in live.items() if s <= cycle <= e))
        if total > peak:
            peak, peak_cycle = (total, cycle)
    at_peak = [n for n, (s, e) in live.items() if s <= peak_cycle <= e]
    at_peak.sort(key=lambda n: (-facts.width[n], -(addresses[n] + facts.width[n]), facts.producers[n]))
    ordered: List[int] = [facts.producers[n] for n in at_peak]
    consumers = sorted({c for n in at_peak for c in facts.consumers[n]})
    ordered.extend(consumers)
    ordered.extend(range(facts.count))
    chosen: List[int] = []
    seen = set()
    for op in ordered:
        if op not in seen:
            seen.add(op)
            chosen.append(op)
        if len(chosen) == k:
            break
    return tuple(sorted(chosen))

def _k_queue(facts, times, addresses, k: int) -> List[Tuple[Tuple[int, ...], object, str]]:
    radius = 4 if k <= 8 else 8
    latest = sorted(range(facts.count), key=lambda op: (-times[op], op))[:k]
    queue = [(tuple(sorted(latest)), radius, f'k{k}_latest'), (memory_group(facts, times, addresses, k), radius, f'k{k}_memory')]
    for start in range(0, facts.count, k):
        window = tuple(range(start, min(start + k, facts.count)))
        if window:
            queue.append((window, radius, f'k{k}_contiguous_{start}'))
    return queue

def build_catalog(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]) -> List[dict]:
    queues: List[List[Tuple[Tuple[int, ...], object, str]]] = []
    queues.append([(tuple(w), BASE_RADIUS, 'windows_for') for w in windows_for(facts, times, addresses, scratch_first=True)])
    for k in (4, 8, 16):
        queues.append(_k_queue(facts, times, addresses, k))
    whole = []
    if facts.count <= 16:
        whole.append((tuple(range(facts.count)), FULL_RANGE, 'whole_program'))
    queues.append(whole)
    catalog: List[dict] = []
    seen = set()
    position = 0
    while any((position < len(queue) for queue in queues)):
        for queue_index, queue in enumerate(queues):
            if position >= len(queue):
                continue
            window, radius, tag = queue[position]
            key = (window, radius)
            if not window or key in seen:
                continue
            seen.add(key)
            catalog.append({'window': window, 'radius': radius, 'policy': tag, 'queue': queue_index})
        position += 1
    return catalog

def a3_catalog(facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int]) -> List[dict]:
    return [{'window': tuple(window), 'radius': BASE_RADIUS, 'policy': 'product_window', 'queue': 0} for window in product_window_plan(facts, times, addresses)]

def heap_key(node: _Node) -> tuple:
    return (node.disc, node.lb, -len(node.ranks), node.ranks)

class _Query:

    def __init__(self, entry: dict, index: int) -> None:
        self.entry = entry
        self.index = index
        self.initialized = False
        self.allowance: Optional[float] = None
        self.used = 0.0
        self.status: Optional[str] = None
        self.reason = ''
        self.heap: List[tuple] = []
        self.domain: Optional[Domain] = None
        self.expander: Optional[Expander] = None
        self.acceptor: Optional[_Acceptor] = None
        self.report: Optional[SearchReport] = None
        self.meter: Optional[Meter] = None
        self.caps: Optional[dict] = None
        self.slices = 0
        self.frontier_peak = 0
        self.hard_deadline: Optional[float] = None
        self.learner = None
        self.digest: Optional[str] = None
        self.phase = 'search'
        self.frontier_limited = False
        self.model_pair = None
        self.construction_interrupted = False
        self.construction_seconds: Optional[float] = None
        self.construction_deadline: Optional[float] = None
        self.construction_overrun = False
        self.construction_late_by = 0.0
        self.terminal_reason: Optional[str] = None
        self.late_terminal_reason: Optional[str] = None

    def summary(self) -> dict:
        report = self.report
        return {'window': list(self.entry['window']), 'radius': self.entry['radius'], 'phase': self.phase, 'model': self.learner.summary() if self.learner is not None else None, 'policy': self.entry['policy'], 'status': self.status, 'reason': self.reason, 'active_seconds': self.used, 'allowance_seconds': self.allowance, 'slices': self.slices, 'frontier_peak': self.frontier_peak, 'frontier_left': len(self.heap), 'caps': [self.caps.get('LC'), self.caps.get('LS'), self.caps.get('Ccap'), self.caps.get('Scap')] if self.caps else None, 'nodes': report.nodes if report else 0, 'validations': report.validations if report else 0, 'interrupted_validations': report.interrupted_validations if report else 0, 'construction_interrupted': self.construction_interrupted, 'interrupted_before_search': self.construction_interrupted, 'construction_seconds': self.construction_seconds, 'construction_deadline_exceeded': self.construction_overrun, 'construction_past_deadline_seconds': self.construction_late_by, 'terminal_reason': self.terminal_reason, 'late_terminal_reason': self.late_terminal_reason, 'pruned': report.pruned if report else 0, 'completions': report.completions if report else 0, 'domain_sha256': self.digest}

def multiscale_optimise(program: dict, facts: ProgramFacts, times: Dict[int, int], addresses: Dict[str, int], *, budget_seconds: float, query_seconds: float=LIMITS['query_active_seconds'], node_ceiling: int=int(LIMITS['aggregate_nodes']), validation_ceiling: int=int(LIMITS['aggregate_validation_attempts']), slice_seconds: float=LIMITS['slice_seconds'], slice_nodes: int=int(LIMITS['slice_nodes']), frontier_limit: int=int(LIMITS['frontier_per_query']), resident_limit: int=int(LIMITS['resident_queries']), limits: Optional[dict]=None, clock: Callable[[], float]=time.perf_counter, stats: Optional[PropagationStats]=None, memo: bool=True, trace: Optional[List[tuple]]=None, learner_factory: Optional[Callable[[Domain], object]]=None, catalog: str='a4', traversal: str='heap', timers: Optional[Dict[str, float]]=None) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    if catalog not in CATALOGS or traversal not in TRAVERSALS:
        raise ValueError(f'unknown ablation cell {catalog!r}/{traversal!r}')
    raw_clock = clock
    last_read = [0.0]

    def clock() -> float:
        last_read[0] = raw_clock()
        return last_read[0]
    limits = dict(PER_QUERY_LIMITS if limits is None else limits)
    stats = stats if stats is not None else PropagationStats()
    cache: Optional[dict] = {} if memo else None
    started = clock()
    deadline = started + budget_seconds
    aggregate = _Aggregate(node_ceiling, validation_ceiling)
    best_times, best_addresses = (dict(times), dict(addresses))
    status_counts: Dict[str, int] = {}
    interrupted_by_query: List[dict] = []
    construction_interruptions: List[dict] = []
    construction_overruns: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    interrupted: List[dict] = []
    query_log: List[dict] = []
    stopped = 'pass_complete'
    epochs = 0
    catalog_sizes: List[int] = []
    not_started = 0

    def finish(query: _Query, status: str, reason: str) -> None:
        query.status = status
        query.reason = reason
        status_counts[status] = status_counts.get(status, 0) + 1
        if query.report is not None:
            aggregate.add(query.report, query.expander.filtered if query.expander else 0)
            rejected.extend(query.report.rejected_completions)
        if query.learner is not None:
            aggregate.totals['validations'] += query.learner.validations
            rejected.extend(query.learner.rejected)
        if query.report is not None and query.report.interrupted_validations:
            item = {'phase': 'validation', 'window': list(query.entry['window']), 'count': query.report.interrupted_validations}
            interrupted.append(item)
            interrupted_by_query.append(dict(item, query=query.index, epoch=epochs, policy=query.entry['policy'], status=status))
        late_model = (getattr(query.learner, 'info', None) or {}).get('late_validations', 0) if query.learner is not None else 0
        if late_model:
            item = {'phase': 'model_validation', 'window': list(query.entry['window']), 'count': late_model}
            interrupted.append(item)
            interrupted_by_query.append(dict(item, query=query.index, epoch=epochs, policy=query.entry['policy'], status=status))
        if query.construction_interrupted:
            construction_interruptions.append({'query': query.index, 'epoch': epochs, 'window': list(query.entry['window']), 'status': status, 'overrun': query.construction_overrun, 'late_terminal_reason': query.late_terminal_reason})
        if query.construction_overrun:
            construction_overruns.append({'query': query.index, 'epoch': epochs, 'window': list(query.entry['window']), 'status': status, 'construction_seconds': query.construction_seconds, 'past_deadline_seconds': query.construction_late_by, 'late_terminal_reason': query.late_terminal_reason})
        if len(query_log) < 4096:
            query_log.append(query.summary())
    running: List[_Query] = []
    sequence = [0]

    def live_nodes() -> int:
        return aggregate.totals['nodes'] + sum((q.report.nodes for q in list(resident) + running if q.report is not None))

    def live_validations() -> int:
        return aggregate.totals['validations'] + sum(((q.report.validations if q.report is not None else 0) + (q.learner.validations if q.learner is not None else 0) for q in list(resident) + running))

    def push(heap: list, node: _Node) -> None:
        sequence[0] += 1
        if traversal == 'heap':
            heapq.heappush(heap, (heap_key(node), sequence[0], node))
        else:
            heap.append(node)

    def pop(heap: list) -> _Node:
        if traversal == 'heap':
            return heapq.heappop(heap)[2]
        return heap.pop()

    def initialize(query: _Query, epoch_times, epoch_addresses, product: int) -> Optional[str]:
        """Build caps, domain and root inside the query's allowance."""
        window = query.entry['window']
        caps = product_caps(facts, epoch_times, epoch_addresses, window)
        query.caps = caps
        if caps['status'] != 'OK':
            return caps['status']
        record = product_record(f"{program['name']}::{'-'.join(map(str, window))}::{query.entry['policy']}::r{query.entry['radius']}", program, facts, epoch_times, epoch_addresses, window, query.entry['radius'], caps)
        domain = Domain.from_record(record, memo=cache)
        query.domain = domain
        query.digest = domain.digest()
        report = _new_report(domain, 'multiscale_search', record['incumbent'], query.digest)
        query.report = report
        nodes_left = node_ceiling - live_nodes()
        validations_left = validation_ceiling - live_validations()
        budget = Budget(seconds=1000000000.0, max_cover=limits['query_max_cover'], max_visited=max(1, min(limits['search_max_nodes'], nodes_left - 1)), max_records=max(1, min(limits['search_max_candidate_validations'], validations_left)))
        query.meter = budget.start()
        if learner_factory is not None:
            query.learner = learner_factory(domain)
        query.acceptor = _Acceptor(domain, report, query.meter, lambda: query.hard_deadline, clock, stop_on_improvement=True, observe=query.learner.observe if query.learner is not None else None)
        stats.current_domain = query.digest
        state = State(domain)
        conflict = state.schedule_conflict()
        if conflict is not None:
            return 'UNSAT_CONFLICT'
        query.expander = Expander(domain, 'propagate', stats, report)
        root = query.expander.root(product)
        if root is None:
            return 'UNSAT_ROOT'
        push(query.heap, root)
        return None

    def model_slice(query: _Query, slice_started: float, full_deadline: float, product: int) -> str:
        learner = query.learner
        query.hard_deadline = full_deadline
        if clock() >= full_deadline:
            query.used += clock() - slice_started
            finish(query, 'UNKNOWN_DEADLINE' if clock() >= deadline else 'UNKNOWN_ALLOWANCE', 'the allowance ended before the model phase')
            return 'finished'
        if query.phase == 'model_prepare':
            learner.validation_budget = validation_ceiling - live_validations()
            prepared = learner.prepare(full_deadline)
            query.used += clock() - slice_started
            if prepared == 'READY':
                query.phase = 'model'
                return 'paused'
            if prepared == 'MODEL_UNAVAILABLE' and query.heap and (not query.frontier_limited):
                query.phase = 'search_continued'
                return 'paused'
            finish(query, f'UNKNOWN_MODEL_{prepared}', learner.reason)
            return 'finished'
        outcome = learner.step(product, min(full_deadline, slice_started + slice_seconds), full_deadline)
        query.used += clock() - slice_started
        if outcome[0] == 'improved':
            report = query.report
            report.best_times, report.best_addresses = (dict(outcome[1]), dict(outcome[2]))
            report.best_product = outcome[3]
            report.improved = True
            finish(query, 'SAT', 'the model phase found a strictly better validated compilation')
            return 'improved'
        if outcome[0] == 'exhausted':
            if query.heap and (not query.frontier_limited):
                query.phase = 'search_continued'
                return 'paused'
            finish(query, 'UNKNOWN_MODEL_EXHAUSTED', 'the ordered pool was exhausted')
            return 'finished'
        if clock() >= full_deadline:
            finish(query, 'UNKNOWN_DEADLINE' if clock() >= deadline else 'UNKNOWN_ALLOWANCE', 'the allowance ended in the model phase')
            return 'finished'
        return 'paused'

    class _Switch(Exception):
        pass

    def run_slice(query: _Query, epoch_times, epoch_addresses, product: int) -> str:
        """One slice. Returns 'paused', 'finished' or 'improved'."""
        slice_started = clock()
        query.slices += 1
        just_initialized = False
        first_now: Optional[float] = None
        if not query.initialized:
            query.initialized = True
            just_initialized = True
            query.allowance = min(query_seconds, deadline - slice_started)
            if query.allowance <= 0:
                query.construction_interrupted = True
                finish(query, 'NOT_STARTED_DEADLINE', 'no overall time at initialization')
                return 'finished'
            query.hard_deadline = min(deadline, slice_started + query.allowance)
            try:
                if timers is None:
                    outcome = initialize(query, epoch_times, epoch_addresses, product)
                else:
                    built = raw_clock()
                    try:
                        outcome = initialize(query, epoch_times, epoch_addresses, product)
                    finally:
                        timers['construction'] = timers.get('construction', 0.0) + raw_clock() - built
                        timers['constructions'] = timers.get('constructions', 0) + 1
            except Infeasible as exc:
                terminal = ('INFEASIBLE', str(exc))
            except DomainError as exc:
                terminal = ('UNKNOWN_CONSTRUCTION', str(exc))
            else:
                if outcome is None:
                    terminal = None
                elif outcome == 'NO_STRICT_IMPROVEMENT':
                    terminal = ('NO_STRICT_IMPROVEMENT', query.caps['reason'])
                elif outcome in ('UNSAT_CONFLICT', 'UNSAT_ROOT'):
                    terminal = ('UNSAT', outcome.lower())
                else:
                    terminal = (outcome, '')
            ended = clock()
            query.construction_seconds = ended - slice_started
            query.construction_deadline = query.hard_deadline
            if ended >= query.hard_deadline:
                query.construction_overrun = True
                query.construction_late_by = ended - query.hard_deadline
                query.construction_interrupted = True
            if terminal is not None:
                query.used += ended - slice_started
                query.terminal_reason = terminal[0]
                if query.construction_overrun:
                    query.late_terminal_reason = f'{terminal[0]}: {terminal[1]}'
                    late = 'UNKNOWN_DEADLINE' if ended >= deadline else 'UNKNOWN_ALLOWANCE'
                    finish(query, late, 'initialization ended at or after the deadline')
                else:
                    finish(query, terminal[0], terminal[1])
                return 'finished'
            first_now = ended
        stats.current_domain = query.digest
        remaining_allowance = query.allowance - query.used
        full_deadline = min(deadline, slice_started + remaining_allowance)
        learner = query.learner
        if learner is not None and query.phase in ('model_prepare', 'model'):
            return model_slice(query, slice_started, full_deadline, product)
        learned_search = learner is not None and query.phase == 'search'
        if learned_search:
            query.hard_deadline = min(deadline, slice_started + query.allowance / 2 - query.used)
        else:
            query.hard_deadline = full_deadline
        report = query.report
        expander = query.expander
        acceptor = query.acceptor
        nodes_at_start = report.nodes
        outcome = 'paused'
        try:
            while True:
                if first_now is not None:
                    now, first_now = (first_now, None)
                else:
                    now = clock()
                if now >= query.hard_deadline:
                    if just_initialized and report.nodes == nodes_at_start:
                        query.construction_interrupted = True
                    if now >= deadline:
                        raise _Stop('the overall deadline expired', 'UNKNOWN_DEADLINE')
                    if learned_search:
                        raise _Switch()
                    raise _Stop('the query active-time allowance is spent', 'UNKNOWN_ALLOWANCE')
                if report.nodes - nodes_at_start >= slice_nodes or now - slice_started >= slice_seconds:
                    break
                if not query.heap:
                    raise _Stop('the declared domain holds no strict improvement', 'UNSAT')
                if aggregate.node_ceiling - live_nodes() < 2:
                    raise _Stop('aggregate node ceiling', 'UNKNOWN_AGGREGATE_NODES')
                node = pop(query.heap)
                report.nodes += 1
                try:
                    query.meter.visit()
                except BudgetExhausted as exc:
                    raise _Stop(exc.reason, 'UNKNOWN_QUERY_LIMIT') from exc
                if trace is not None:
                    trace.append((query.index, node.ranks))
                if expander.is_leaf(node):
                    acceptor.consider(node.state)
                    continue
                pending_children: List[_Node] = []
                for child in expander.children(node, lambda: product):
                    if traversal == 'heap':
                        push(query.heap, child)
                        queued = len(query.heap)
                    else:
                        pending_children.append(child)
                        queued = len(query.heap) + len(pending_children)
                    if queued > frontier_limit:
                        if traversal == 'dfs':
                            query.heap.extend(reversed(pending_children))
                        if learned_search:
                            query.frontier_limited = True
                            raise _Switch()
                        raise _Stop('more than the permitted queued prefixes', 'UNKNOWN_FRONTIER_LIMIT')
                if pending_children:
                    for child in reversed(pending_children):
                        push(query.heap, child)
                query.frontier_peak = max(query.frontier_peak, len(query.heap))
        except _Improved:
            outcome = 'improved'
        except _Switch:
            query.used += clock() - slice_started
            query.phase = 'model_prepare'
            return 'paused'
        except _Stop as stop:
            query.used += clock() - slice_started
            status = stop.status
            if status == 'UNKNOWN':
                now = clock()
                if learned_search and now < deadline and (now < full_deadline):
                    query.phase = 'model_prepare'
                    return 'paused'
                status = 'UNKNOWN_DEADLINE' if now >= deadline else 'UNKNOWN_ALLOWANCE' if now >= query.hard_deadline else 'UNKNOWN_QUERY_LIMIT'
            finish(query, status, stop.reason)
            return 'finished'
        query.used += clock() - slice_started
        if outcome == 'improved':
            finish(query, 'SAT', 'a strictly better validated compilation was found')
            return 'improved'
        return 'paused'
    resident: deque = deque()
    while True:
        epochs += 1
        cycles = max(best_times.values()) + 1
        memory = _contract_footprint(facts, best_addresses)
        product = cycles * memory
        epoch_times, epoch_addresses = (dict(best_times), dict(best_addresses))
        if catalog == 'a4':
            entries = build_catalog(facts, epoch_times, epoch_addresses)
        else:
            entries = a3_catalog(facts, epoch_times, epoch_addresses)
        catalog_sizes.append(len(entries))
        pending = deque((_Query(entry, i) for i, entry in enumerate(entries)))
        resident = deque()
        while pending and len(resident) < resident_limit:
            resident.append(pending.popleft())
        improved = False
        while resident:
            if clock() >= deadline:
                stopped = 'deadline'
                break
            exhausted = aggregate.exhausted()
            if exhausted:
                stopped = exhausted
                break
            query = resident.popleft()
            running[:] = [query]
            outcome = run_slice(query, epoch_times, epoch_addresses, product)
            running[:] = []
            if outcome == 'paused':
                resident.append(query)
                continue
            if outcome == 'improved':
                report = query.report
                best_times = dict(report.best_times)
                best_addresses = dict(report.best_addresses)
                improvements.append({'window': list(query.entry['window']), 'radius': query.entry['radius'], 'policy': query.entry['policy'], 'from': product, 'to': report.best_product, 'source': 'model' if query.phase == 'model' else 'search', 'from_CS': [cycles, memory], 'to_CS': [max(best_times.values()) + 1, _contract_footprint(facts, best_addresses)], 'elapsed_seconds': last_read[0] - started, 'epoch': epochs, 'query': query.index})
                improved = True
                break
            if pending:
                resident.append(pending.popleft())
        for query in resident:
            if query.status is None:
                finish(query, 'SUPERSEDED' if improved else 'UNKNOWN_DEADLINE' if stopped == 'deadline' else f'UNKNOWN_{stopped.upper()}', 'left resident')
        for _ in pending:
            not_started += 1
        if not improved:
            break
        resident = deque()
    elapsed = clock() - started
    unknown = sum((n for s, n in status_counts.items() if s.startswith('UNKNOWN')))
    record = {'controller': 'multiscale_optimise', 'version': VERSION, 'source_sha256': FROZEN_SOURCE_SHA256, 'arm': 'multiscale_search', 'catalog': catalog, 'traversal': traversal, 'budget_seconds': budget_seconds, 'query_seconds': query_seconds, 'epochs': epochs, 'catalog_sizes': catalog_sizes[:64], 'statuses': dict(sorted(status_counts.items())), 'queries_finished': sum(status_counts.values()), 'queries_unknown': unknown, 'queries_not_started': not_started, 'accepted': len(improvements), 'improvements': improvements, 'rejected_completions': rejected, 'discrepancy_count': len(rejected), 'stopped_because': stopped, 'seconds': elapsed, 'overshoot_seconds': elapsed - budget_seconds, 'interrupted_attempts': interrupted, 'interrupted_attempt_count': len(interrupted), 'interrupted_validation_total': sum((i['count'] for i in interrupted_by_query)), 'interrupted_validation_search_total': sum((i['count'] for i in interrupted_by_query if i['phase'] == 'validation')), 'interrupted_validation_model_total': sum((i['count'] for i in interrupted_by_query if i['phase'] == 'model_validation')), 'interrupted_validation_queries': len({(i['epoch'], i['query']) for i in interrupted_by_query}), 'interrupted_validations_per_query': interrupted_by_query[:4096], 'construction_interruption_count': len(construction_interruptions), 'construction_interruptions': construction_interruptions[:4096], 'construction_overrun_count': len(construction_overruns), 'construction_overrun_past_deadline_seconds': sum((o['past_deadline_seconds'] for o in construction_overruns)), 'construction_overruns': construction_overruns[:4096], 'late_terminal_reasons': _count_by([o['late_terminal_reason'].split(':')[0] for o in construction_overruns if o['late_terminal_reason']]), 'aggregate': dict(aggregate.totals), 'ceilings': {'nodes': node_ceiling, 'validations': validation_ceiling}, 'limits': {'slice_seconds': slice_seconds, 'slice_nodes': slice_nodes, 'frontier': frontier_limit, 'resident': resident_limit}, 'budget_renewals': 0, 'propagation': stats.summary(), 'queries': query_log}
    return (best_times, best_addresses, record)


def compile_program(program: dict) -> dict:
    facts = derive(program)
    initial, _ = compile_with_report(program, DEFAULT_LIMITS, optimise=False)
    times = issue_cycles_of(program, initial["bundles"])
    addresses = dict(initial["scratch"])
    best_times, best_addresses, record = multiscale_optimise(
        program, facts, times, addresses,
        budget_seconds=OPTIMISATION_SECONDS, catalog="a4", traversal="dfs")
    if record["discrepancy_count"]:
        print(f"warning: {record['discrepancy_count']} rejected candidates", file=sys.stderr)
    return compilation(facts, best_times, best_addresses)


def main(argv) -> int:
    if len(argv) != 1:
        print("usage: python3 compiler.py <program.json>", file=sys.stderr)
        return 2
    try:
        program = machine.load_program(argv[0])
        compiled = compile_program(program)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    json.dump(compiled, sys.stdout)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
