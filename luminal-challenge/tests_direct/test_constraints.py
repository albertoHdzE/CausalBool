"""T02: arithmetic covers and complete joint acceptance expressions.

Covers are compared against plain integer predicates at *every* index of the
universe, so soundness and completeness are both checked rather than sampled.
Joint queries are compared against exhaustive enumeration of their declared
domains, judged by the frozen machine plus the explicit target bounds.
"""

from __future__ import annotations

import itertools
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / ".reference") not in sys.path:
    sys.path.insert(0, str(ROOT / ".reference"))

import machine
import direct_compiler as dcmp
import direct_constraints as dk
import direct_contract as dc
import schema_index as si
from tests_direct.test_contract import program


OFFSETS = (0, 1, 2, 3, 4, 8)
EXACT = {
    "le": lambda a, b: a <= b,
    "lt": lambda a, b: a < b,
    "eq": lambda a, b: a == b,
    "ne": lambda a, b: a != b,
}


def fresh_meter(seconds=60.0, **kwargs):
    return si.Budget(seconds=seconds, **kwargs).start()


def accepts(expression, index):
    """Evaluate an expression at one index, independently of the solver."""

    if isinstance(expression, si.Leaf):
        return any(
            (index & (si.universe_mask(cube.n) ^ cube.free_mask)) == cube.anchor
            for cube in expression.cubes
        )
    if isinstance(expression, si.AllOf):
        return all(accepts(child, index) for child in expression.children)
    if isinstance(expression, si.AnyOf):
        return any(accepts(child, index) for child in expression.children)
    raise AssertionError("unknown expression")


class RelationCoverTests(unittest.TestCase):
    """Soundness and completeness at every index, for every declared offset."""

    def check(self, name, lhs, rhs, n):
        cover = dk.relation_cover(name, lhs, rhs, n, fresh_meter())
        exact = EXACT[name]
        for index in range(1 << n):
            left = (
                lhs.offset
                if lhs.field is None
                else lhs.field.decode(index) + lhs.offset
            )
            right = (
                rhs.offset
                if rhs.field is None
                else rhs.field.decode(index) + rhs.offset
            )
            self.assertEqual(
                si.cover_contains(cover, index),
                exact(left, right),
                f"{name} at index {index} with lhs={left} rhs={right}",
            )
        return cover

    def test_two_fields_at_every_width_and_offset(self):
        for width in range(1, 6):
            first = si.Field("a", 0, width)
            second = si.Field("b", width, width)
            n = 2 * width
            for name in EXACT:
                for left_offset in OFFSETS:
                    for right_offset in (0, 1, 8):
                        self.check(
                            name,
                            dk.Term(first, left_offset),
                            dk.Term(second, right_offset),
                            n,
                        )

    def test_negative_constant_offsets(self):
        first = si.Field("a", 0, 4)
        second = si.Field("b", 4, 4)
        for name in EXACT:
            for left_offset in (-1, -3, -8):
                self.check(name, dk.Term(first, left_offset), dk.Term(second, 0), 8)

    def test_constant_operands_on_either_side(self):
        field = si.Field("a", 0, 4)
        for name in EXACT:
            for value in (0, 1, 7, 15, 16, 100, -5):
                self.check(name, dk.Term(field, 0), dk.constant(value), 4)
                self.check(name, dk.constant(value), dk.Term(field, 0), 4)

    def test_carry_beyond_the_field_width_is_not_truncated(self):
        # A three bit field holds 0..7; adding eight gives 8..15, and a naive
        # truncation to three bits would wrap it back to 0..7.
        field = si.Field("a", 0, 3)
        cover = self.check("lt", dk.Term(field, 8), dk.constant(10), 3)
        self.assertEqual(
            sorted(index for index in range(8) if si.cover_contains(cover, index)),
            [0, 1],
        )
        cover = self.check("le", dk.constant(10), dk.Term(field, 8), 3)
        self.assertEqual(
            sorted(index for index in range(8) if si.cover_contains(cover, index)),
            [2, 3, 4, 5, 6, 7],
        )

    def test_both_operands_share_one_field(self):
        field = si.Field("a", 0, 4)
        n = 4
        universe = si.universe(n)
        for left, right, name, expected in (
            (0, 0, "le", True),
            (0, 0, "lt", False),
            (0, 0, "eq", True),
            (0, 0, "ne", False),
            (1, 0, "lt", False),
            (0, 1, "lt", True),
            (3, 3, "eq", True),
            (3, 4, "eq", False),
        ):
            cover = dk.relation_cover(
                name, dk.Term(field, left), dk.Term(field, right), n, fresh_meter()
            )
            self.assertEqual(cover == (universe,), expected, (left, right, name))
            self.assertEqual(cover == (), not expected, (left, right, name))

    def test_boundary_equality_and_disjoint_ranges(self):
        first = si.Field("a", 0, 3)
        second = si.Field("b", 3, 3)
        # Ranges 0..7 and 8..15 are disjoint, so a < b always and a == b never.
        self.assertEqual(
            dk.relation_cover("lt", dk.Term(first), dk.Term(second, 8), 6, fresh_meter()),
            (si.universe(6),),
        )
        self.assertEqual(
            dk.relation_cover("eq", dk.Term(first), dk.Term(second, 8), 6, fresh_meter()),
            (),
        )
        # Touching at exactly one point resolves le but not lt.
        self.assertEqual(
            dk.relation_cover("le", dk.Term(first), dk.Term(second, 7), 6, fresh_meter()),
            (si.universe(6),),
        )

    def test_straddling_extrema_are_split_rather_than_dropped(self):
        first = si.Field("a", 0, 3)
        # Over the whole cube a ranges 0..7, so a < 4 straddles the boundary.
        cover = self.check("lt", dk.Term(first), dk.constant(4), 3)
        self.assertNotEqual(cover, ())
        self.assertNotEqual(cover, (si.universe(3),))
        members = {index for index in range(8) if si.cover_contains(cover, index)}
        self.assertEqual(members, {0, 1, 2, 3})

    def test_coordinates_outside_the_support_stay_free(self):
        field = si.Field("a", 0, 3)
        n = 6  # three further coordinates belong to nobody
        cover = dk.relation_cover("lt", dk.Term(field), dk.constant(4), n, fresh_meter())
        outside = si.universe_mask(n) ^ field.mask
        for cube in cover:
            self.assertEqual(cube.free_mask & outside, outside)

    def test_unknown_relation_is_rejected(self):
        with self.assertRaises(ValueError):
            dk.relation_cover("gte", dk.constant(1), dk.constant(2), 3, fresh_meter())


class RelationBudgetTests(unittest.TestCase):
    """Each limit fires independently, and none of them reports UNSAT."""

    def test_cover_budget_fires(self):
        field = si.Field("a", 0, 10)
        other = si.Field("b", 10, 10)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover(
                "lt", dk.Term(field), dk.Term(other), 20, fresh_meter(max_cover=4)
            )
        self.assertIn("cover", caught.exception.reason)

    def test_visited_budget_fires(self):
        field = si.Field("a", 0, 10)
        other = si.Field("b", 10, 10)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover(
                "ne", dk.Term(field), dk.Term(other), 20, fresh_meter(max_visited=4)
            )
        self.assertIn("visited", caught.exception.reason)

    def test_time_budget_fires(self):
        field = si.Field("a", 0, 12)
        other = si.Field("b", 12, 12)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover(
                "ne",
                dk.Term(field),
                dk.Term(other),
                24,
                fresh_meter(seconds=0.005, max_visited=10 ** 9, max_cover=10 ** 9),
            )
        self.assertIn("time", caught.exception.reason)

    def test_an_exhausted_budget_never_yields_a_usable_cover(self):
        field = si.Field("a", 0, 10)
        other = si.Field("b", 10, 10)
        try:
            dk.relation_cover(
                "lt", dk.Term(field), dk.Term(other), 20, fresh_meter(max_cover=4)
            )
        except si.BudgetExhausted:
            pass
        else:  # pragma: no cover - the call above must raise
            self.fail("the cover budget did not fire")


# --------------------------------------------------------------------------
# Joint queries
# --------------------------------------------------------------------------


JOINT_FIXTURES = {}


def _joint(name, buffers, operations, cases):
    JOINT_FIXTURES[name] = program(name, buffers, operations, cases)
    return JOINT_FIXTURES[name]


_joint(
    "two_constants",
    {"out": 2},
    [
        {"op": "const", "dest": "a", "value": 1},
        {"op": "const", "dest": "b", "value": 2},
        {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["b"], "buffer": "out", "offset": 1},
    ],
    [{"out": [0, 0]}],
)

_joint(
    "short_chain",
    {"data": 4, "out": 2},
    [
        {"op": "load", "dest": "x", "buffer": "data", "offset": 0},
        {"op": "add", "dest": "y", "args": ["x", "x"]},
        {"op": "store", "args": ["y"], "buffer": "out", "offset": 0},
    ],
    [{"data": [1, 2, 3, 4], "out": [0, 0]}],
)

_joint(
    "shared_engine",
    {"out": 3},
    [
        {"op": "const", "dest": "a", "value": 1},
        {"op": "const", "dest": "b", "value": 2},
        {"op": "const", "dest": "c", "value": 3},
        {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["b"], "buffer": "out", "offset": 1},
        {"op": "store", "args": ["c"], "buffer": "out", "offset": 2},
    ],
    [{"out": [0, 0, 0]}],
)


_joint(
    "vector_overlap",
    {"data": 16, "out": 16},
    [
        {"op": "vload", "dest": "v0", "buffer": "data", "offset": 0},
        {"op": "vload", "dest": "v1", "buffer": "data", "offset": 8},
        {"op": "vadd", "dest": "v2", "args": ["v0", "v1"]},
        {"op": "vstore", "args": ["v2"], "buffer": "out", "offset": 0},
        {"op": "vstore", "args": ["v0"], "buffer": "out", "offset": 8},
    ],
    [{"data": list(range(16)), "out": [0] * 16}],
)

_joint(
    "ordered_aliasing",
    {"data": 8},
    [
        {"op": "load", "dest": "a", "buffer": "data", "offset": 0},
        {"op": "add", "dest": "b", "args": ["a", "a"]},
        {"op": "store", "args": ["b"], "buffer": "data", "offset": 0},
        {"op": "load", "dest": "c", "buffer": "data", "offset": 0},
        {"op": "store", "args": ["c"], "buffer": "data", "offset": 1},
    ],
    [{"data": list(range(8))}, {"data": [7, 6, 5, 4, 3, 2, 1, 0]}],
)


def incumbent(source):
    """The bootstrap result.

    These are unit tests of the joint query, so they are posed against the
    deterministic bootstrap incumbent rather than against whatever the
    optimiser happens to have reached.
    """

    compiled, _ = dcmp.compile_with_report(source, optimise=False)
    times = {
        op_id: cycle
        for cycle, bundle in enumerate(compiled["bundles"])
        for ids in bundle.values()
        for op_id in ids
    }
    return times, dict(compiled["scratch"])


def oracle_feasible(source, facts, query, times, addresses):
    """Judge one complete candidate with the frozen machine and the targets."""

    try:
        compiled = dc.compilation(facts, times, addresses)
        machine.check_compilation(source, compiled)
    except (machine.CompileError, dc.ContractError):
        return False
    if len(compiled["bundles"]) > query.target_cycles:
        return False
    if dc.footprint(facts, addresses) > query.target_memory:
        return False
    return True


def index_for(query, times, addresses, lanes=None):
    """Encode one complete assignment of the query's fields into an index.

    Starting from a full assignment rather than from zero matters: an index
    that leaves unrelated fields at zero can fail a constraint that has nothing
    to do with the one under test.
    """

    lanes = lanes or {}
    index = 0
    for op_id, field in query.time_field.items():
        index |= field.encode(times[op_id])
    for name, field in query.address_field.items():
        index |= field.encode(addresses[name])
    for op_id, field in query.lane_field.items():
        index |= field.encode(lanes.get(op_id, 0))
    return index


def window_for(times):
    """The first two operations, a deterministic small window."""

    return tuple(sorted(times)[:2])


def independent_domains(facts, times, window, target_cycles, target_memory):
    """The declared finite domains, derived from the plan rather than the query.

    Section 5.3: time domains are the incumbent plus or minus two, clipped to
    ``[0, min(H0, T) - 1]``; selected address domains hold every aligned
    address ending at or below ``M``. Taking these from the query object would
    make a query that refuses to exist impossible to contradict.
    """

    labels, axes = [], []
    ceiling = min(facts.horizon, target_cycles) - 1
    for op_id in window:
        low = max(0, times[op_id] - dk.TIME_SLACK)
        high = min(times[op_id] + dk.TIME_SLACK, ceiling)
        labels.append(("time", op_id))
        axes.append(list(range(low, high + 1)))
    for op_id in window:
        name = facts.dest[op_id]
        if name is None:
            continue
        width = facts.width[name]
        step = machine.VLEN if width == machine.VLEN else 1
        labels.append(("address", name))
        axes.append(list(range(0, max(target_memory - width, -1) + 1, step)))
    return labels, axes


def machine_feasible(source, facts, times, addresses, target_cycles, target_memory):
    """The frozen machine plus the explicit target bounds. No query involved."""

    try:
        compiled = dc.compilation(facts, times, addresses)
        machine.check_compilation(source, compiled)
    except (machine.CompileError, dc.ContractError):
        return False
    return (
        len(compiled["bundles"]) <= target_cycles
        and dc.footprint(facts, addresses) <= target_memory
    )


def decode_index(query, index, times, addresses):
    """Read an index back with plain shifts and masks."""

    decoded_times = dict(times)
    decoded_addresses = dict(addresses)
    for op_id, field in query.time_field.items():
        decoded_times[op_id] = (index >> field.offset) & ((1 << field.width) - 1)
    for name, field in query.address_field.items():
        decoded_addresses[name] = (index >> field.offset) & ((1 << field.width) - 1)
    return decoded_times, decoded_addresses


def predicate_accepts(query, expression, times, addresses):
    """Whether the predicate accepts this assignment under *some* lane choice.

    Lanes are auxiliaries of the query with no counterpart in the machine, so
    the comparison against the machine quantifies over them existentially.
    """

    base = 0
    for op_id, field in query.time_field.items():
        base |= times[op_id] << field.offset
    for name, field in query.address_field.items():
        base |= addresses[name] << field.offset
    lanes = sorted(query.lane_field)
    for mask in range(1 << len(lanes)):
        index = base
        for position, op_id in enumerate(lanes):
            if (mask >> position) & 1:
                index |= 1 << query.lane_field[op_id].offset
        if accepts(expression, index):
            return True
    return False


def enumerate_domains(query):
    """Every combination of the declared finite domains, in order."""

    axes = []
    labels = []
    for op_id in query.window:
        low, high = query._time_domain(op_id)
        axes.append(list(range(low, high + 1)))
        labels.append(("time", op_id))
    for name in query.selected_values:
        width = query.facts.width[name]
        step = machine.VLEN if width == machine.VLEN else 1
        axes.append(list(range(0, query.target_memory - width + 1, step)))
        labels.append(("address", name))
    total = 1
    for axis in axes:
        total *= max(len(axis), 1)
    return labels, axes, total


class JointQueryTests(unittest.TestCase):
    """Differential bounded queries against exhaustive enumeration."""

    def cases(self):
        """At least twelve joint fixtures with exhaustible domains."""

        found = []
        for source in JOINT_FIXTURES.values():
            times, addresses = incumbent(source)
            facts = dc.derive(source)
            cycles = max(times.values()) + 1
            memory = dc.footprint(facts, addresses)
            for target_cycles, target_memory in (
                (cycles, memory),
                (cycles, memory + 2),
                (cycles + 1, memory),
                (cycles - 1, memory + 4),
            ):
                if target_cycles < 1 or target_memory < 1:
                    continue
                found.append((source, facts, times, addresses, target_cycles, target_memory))
        return found

    def test_at_least_twelve_joint_fixtures(self):
        self.assertGreaterEqual(len(self.cases()), 12)

    def test_solver_agrees_with_exhaustive_enumeration(self):
        """Enumerate independently first, then see what construction says.

        The domains come from the plan text, not from the query object, so a
        construction that refuses to build an expression is still held to the
        oracle's verdict. Deriving them from the query would make an
        unconditionally infeasible implementation untestable.
        """

        checked = 0
        satisfiable_cases = 0
        for source, facts, times, addresses, target_cycles, target_memory in self.cases():
            window = window_for(times)
            labels, axes = independent_domains(
                facts, times, window, target_cycles, target_memory
            )
            total = 1
            for axis in axes:
                total *= max(len(axis), 1)
            self.assertLessEqual(total, 65536, "domain product must be exhaustible")

            # The independent answer, computed before construction is consulted.
            found = []
            assignments = []
            for combination in itertools.product(*axes):
                candidate_times = dict(times)
                candidate_addresses = dict(addresses)
                for (kind, key), value in zip(labels, combination):
                    if kind == "time":
                        candidate_times[key] = value
                    else:
                        candidate_addresses[key] = value
                feasible = machine_feasible(
                    source, facts, candidate_times, candidate_addresses,
                    target_cycles, target_memory,
                )
                assignments.append((candidate_times, candidate_addresses, feasible))
                if feasible:
                    found.append((candidate_times, candidate_addresses))
            if found:
                satisfiable_cases += 1

            meter = fresh_meter(max_cover=10 ** 6, max_visited=10 ** 7, max_records=10 ** 6)
            try:
                query = dk.JointQuery(
                    facts, times, addresses, window, target_cycles, target_memory, meter
                )
                expression = query.expression()
            except dk.Infeasible:
                self.assertEqual(
                    found,
                    [],
                    f"{source['name']} target=({target_cycles},{target_memory}): "
                    f"construction declared the query infeasible, but independent "
                    f"enumeration found {len(found)} valid assignments",
                )
                checked += 1
                continue

            result = si.solve(expression, query.n, meter=meter)
            self.assertFalse(result.is_unknown, result.reason)
            self.assertEqual(
                result.is_sat,
                bool(found),
                f"{source['name']} target=({target_cycles},{target_memory}) "
                f"solver={result.status} oracle={len(found)} feasible",
            )

            # Pointwise: the predicate accepts an assignment for some lane
            # exactly when the machine and the targets accept it.
            if len(assignments) <= 512:
                for candidate_times, candidate_addresses, feasible in assignments:
                    accepted = predicate_accepts(
                        query, expression, candidate_times, candidate_addresses
                    )
                    self.assertEqual(
                        accepted,
                        feasible,
                        f"{source['name']}: predicate {accepted} against machine "
                        f"{feasible} for {sorted(candidate_times.items())}",
                    )

            if result.is_sat:
                # Every filling, decoded by plain shifts and masks and checked
                # against the machine, not against the expression that produced it.
                if result.cube.size <= 512:
                    for filling in result.cube.members():
                        filled_times, filled_addresses = decode_index(
                            query, filling, times, addresses
                        )
                        self.assertTrue(
                            machine_feasible(
                                source, facts, filled_times, filled_addresses,
                                target_cycles, target_memory,
                            ),
                            f"{source['name']}: filling {filling} of the returned "
                            f"schema is not independently valid",
                        )
            checked += 1

        self.assertGreaterEqual(checked, 12)
        self.assertGreater(
            satisfiable_cases,
            0,
            "at least one case must be genuinely satisfiable, or an "
            "unconditionally infeasible implementation would pass",
        )

    def test_excluded_domain_encodings_are_rejected(self):
        source = JOINT_FIXTURES["shared_engine"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        meter = fresh_meter(max_cover=10 ** 6, max_records=10 ** 6)
        query = dk.JointQuery(
            facts, times, addresses, tuple(sorted(times)[:2]), 8, 8, meter
        )
        expression = query.expression()
        for op_id in query.window:
            field = query.time_field[op_id]
            low, high = query._time_domain(op_id)
            for code in range(field.limit):
                if low <= code <= high:
                    continue
                # Build an index carrying an excluded code for this field.
                index = field.encode(code)
                for other in query.window:
                    if other == op_id:
                        continue
                    other_low, _ = query._time_domain(other)
                    index |= query.time_field[other].encode(other_low)
                self.assertFalse(
                    accepts(expression, index),
                    f"code {code} outside [{low}, {high}] was accepted",
                )

    def test_a_fixed_decision_violating_a_target_is_infeasible(self):
        source = JOINT_FIXTURES["shared_engine"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        meter = fresh_meter()
        # The window holds only the first operation, so the later fixed ones
        # cannot possibly meet a target of one cycle.
        with self.assertRaises(dk.Infeasible):
            dk.JointQuery(facts, times, addresses, (0,), 1, 64, meter).expression()

    def test_the_incumbent_assignment_is_always_accepted(self):
        for source in JOINT_FIXTURES.values():
            times, addresses = incumbent(source)
            facts = dc.derive(source)
            cycles = max(times.values()) + 1
            memory = dc.footprint(facts, addresses)
            meter = fresh_meter(max_cover=10 ** 6, max_records=10 ** 6)
            window = tuple(sorted(times)[:2])
            query = dk.JointQuery(
                facts, times, addresses, window, cycles, memory, meter
            )
            expression = query.expression()
            lanes = self.consistent_lanes(query, times)
            self.assertTrue(
                accepts(expression, index_for(query, times, addresses, lanes)),
                f"{source['name']}: its own incumbent was rejected",
            )

    @staticmethod
    def consistent_lanes(query, times):
        """Give selected operations distinct lanes when they share a cycle."""

        lanes = {}
        used = {}
        for op_id in sorted(query.lane_field):
            key = (query.facts.engine[op_id], times[op_id])
            lanes[op_id] = used.get(key, 0)
            used[key] = lanes[op_id] + 1
        return lanes

    def test_lanes_enforce_issue_capacity_not_latency(self):
        source = JOINT_FIXTURES["shared_engine"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        cycles = max(times.values()) + 1
        memory = dc.footprint(facts, addresses)
        meter = fresh_meter(max_cover=10 ** 6, max_records=10 ** 6)
        query = dk.JointQuery(facts, times, addresses, (0, 1), cycles, memory, meter)
        # Both consts sit on the two-slot load engine, so each has a lane bit.
        self.assertIn(0, query.lane_field)
        self.assertIn(1, query.lane_field)
        self.assertEqual(times[0], times[1], "the incumbent should pack both consts")
        expression = query.expression()
        # Two selected operations may share a cycle on a two-slot engine,
        # provided they take different lanes.
        for first, second in ((0, 1), (1, 0)):
            self.assertTrue(
                accepts(expression, index_for(query, times, addresses, {0: first, 1: second}))
            )
        # The same lane in the same cycle is a capacity violation.
        for lane in (0, 1):
            self.assertFalse(
                accepts(expression, index_for(query, times, addresses, {0: lane, 1: lane}))
            )

    def test_store_engine_has_a_single_slot_and_no_lane(self):
        source = JOINT_FIXTURES["shared_engine"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        meter = fresh_meter(max_cover=10 ** 6, max_records=10 ** 6)
        stores = tuple(op_id for op_id in range(facts.count) if facts.engine[op_id] == "store")
        query = dk.JointQuery(
            facts, times, addresses, stores[:2], 16, 16, meter
        )
        self.assertEqual(query.lane_field, {})
        expression = query.expression()
        same = query.time_field[stores[0]].encode(times[stores[0]])
        same |= query.time_field[stores[1]].encode(times[stores[0]])
        self.assertFalse(accepts(expression, same))

    def test_field_layout_follows_increasing_operation_identifier(self):
        source = JOINT_FIXTURES["two_constants"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        query = dk.JointQuery(facts, times, addresses, (0, 1), 8, 8, fresh_meter())
        layout = []
        for op_id in query.window:
            layout.append(query.time_field[op_id].offset)
            name = facts.dest[op_id]
            if name is not None:
                layout.append(query.address_field[name].offset)
            if op_id in query.lane_field:
                layout.append(query.lane_field[op_id].offset)
        self.assertEqual(layout, sorted(layout))
        self.assertEqual(layout[0], 0)
        self.assertEqual(query.n, max(layout) + 1 if layout else 0)

    def test_scratch_safety_is_spatial_or_temporal(self):
        source = JOINT_FIXTURES["two_constants"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        meter = fresh_meter(max_cover=10 ** 6, max_records=10 ** 6)
        cycles = max(times.values()) + 1
        memory = dc.footprint(facts, addresses)
        query = dk.JointQuery(facts, times, addresses, (0, 1), cycles, memory, meter)
        expression = query.expression()
        lanes = self.consistent_lanes(query, times)
        # Two values whose intervals overlap may not share a word, but may sit
        # at distinct words; the constraint is a disjunction, not a conjunction.
        apart = dict(addresses)
        apart["a"], apart["b"] = 0, 1
        together = dict(addresses)
        together["a"] = together["b"] = 0
        self.assertTrue(accepts(expression, index_for(query, times, apart, lanes)))
        self.assertFalse(accepts(expression, index_for(query, times, together, lanes)))


if __name__ == "__main__":
    unittest.main()


class ConstructionBudgetTests(unittest.TestCase):
    """F3: accounting must be consistent, and must stop work early.

    `RelationBudgetTests` above only assert that an exception eventually
    arrives. These assert *when* it arrives and what the accounting says, which
    is what distinguishes a budget that is enforced from one that is merely
    reported after the work is done.
    """

    def joint(self, max_records, seconds=30.0):
        source = JOINT_FIXTURES["two_constants"]
        times, addresses = incumbent(source)
        facts = dc.derive(source)
        meter = si.Budget(seconds=seconds, max_records=max_records).start()
        query = dk.JointQuery(
            facts,
            times,
            addresses,
            (0, 1),
            max(times.values()) + 1,
            dc.footprint(facts, addresses),
            meter,
        )
        return query, meter

    def test_construction_never_returns_an_expression_over_its_record_cap(self):
        """The reviewed build returned 554 records under a cap of 533."""

        query, meter = self.joint(max_records=533)
        with self.assertRaises(si.BudgetExhausted) as caught:
            query.expression()
        self.assertIn("record", caught.exception.reason)
        # It stopped as the cap was crossed, not after building everything.
        self.assertLessEqual(meter.records, 534)

    def test_a_generous_cap_charges_exactly_what_the_expression_holds(self):
        query, meter = self.joint(max_records=100000)
        expression = query.expression()
        charged = meter.records
        actual = si.count_records(expression)
        self.assertEqual(charged, actual, "every node and alternative must be billed once")

    def test_solving_does_not_bill_construction_a_second_time(self):
        """The reviewed pair charged 533 then 1,087 for the same expression."""

        query, meter = self.joint(max_records=100000)
        expression = query.expression()
        before = meter.records
        result = si.solve(expression, query.n, meter=meter)
        self.assertEqual(meter.records, before, "solve re-billed the construction")
        self.assertFalse(result.is_unknown, result.reason)

    def test_an_externally_supplied_expression_is_still_billed(self):
        meter = si.Budget(seconds=30.0, max_records=3).start()
        # Never seen by this meter, so it must be charged and must exhaust it.
        outside = si.AllOf(tuple(si.Leaf((si.Cube(4, i, 0),)) for i in range(8)))
        result = si.solve(outside, 4, meter=meter)
        self.assertTrue(result.is_unknown)
        self.assertIn("record", result.reason)

    def test_an_expired_meter_stops_the_simplified_constant_path(self):
        expired = si.Budget(seconds=0.1, max_records=100).start()
        expired.started -= 1
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("le", dk.constant(0), dk.constant(1), 4, expired)
        self.assertIn("time", caught.exception.reason)

    def test_an_expired_meter_stops_the_identical_field_path(self):
        expired = si.Budget(seconds=0.1, max_records=100).start()
        expired.started -= 1
        field = si.Field("a", 0, 4)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("le", dk.Term(field, 0), dk.Term(field, 0), 4, expired)
        self.assertIn("time", caught.exception.reason)

    def test_the_simplified_paths_are_charged_when_they_succeed(self):
        meter = si.Budget(seconds=30.0, max_records=100).start()
        cover = dk.relation_cover("le", dk.constant(0), dk.constant(1), 4, meter)
        self.assertEqual(cover, (si.universe(4),))
        self.assertEqual(meter.records, 1, "an accepted simplification costs a record")
        # A refused simplification yields nothing and so costs nothing.
        before = meter.records
        self.assertEqual(
            dk.relation_cover("lt", dk.constant(5), dk.constant(1), 4, meter), ()
        )
        self.assertEqual(meter.records, before)

    def test_the_cover_cap_stops_a_comparison_early(self):
        """Early stopping, measured: the reviewed build visited 5,115 cubes."""

        first = si.Field("a", 0, 10)
        second = si.Field("b", 10, 10)
        meter = si.Budget(seconds=30.0, max_cover=4).start()
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("lt", dk.Term(first), dk.Term(second), 20, meter)
        self.assertIn("cover", caught.exception.reason)
        self.assertLess(meter.visited, 100, "the search should stop almost at once")

    def test_the_record_cap_stops_a_comparison_early(self):
        first = si.Field("a", 0, 10)
        second = si.Field("b", 10, 10)
        meter = si.Budget(seconds=30.0, max_records=1).start()
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("lt", dk.Term(first), dk.Term(second), 20, meter)
        self.assertIn("record", caught.exception.reason)
        self.assertLess(meter.visited, 100)
        self.assertLessEqual(meter.records, 2)

    def test_exhaustion_during_a_query_is_unknown_not_unsat(self):
        query, meter = self.joint(max_records=533)
        try:
            expression = query.expression()
        except si.BudgetExhausted:
            expression = None
        self.assertIsNone(expression, "construction should have stopped")
        # And when the same starvation happens inside solve, the verdict is
        # UNKNOWN; never UNSAT.
        leaf = si.Leaf(tuple(si.Cube(4, i, 0) for i in range(16)))
        starved = si.solve(leaf, 4, si.Budget(seconds=10.0, max_cover=1))
        self.assertTrue(starved.is_unknown)
        self.assertFalse(starved.is_unsat)


# --------------------------------------------------------------------------
# Cover reuse (plan/OPTIMIZATION_PHASE_PLAN.md, stage B)
# --------------------------------------------------------------------------


class CoverCacheTests(unittest.TestCase):
    """A cached cover must be the cover, and must cost what building it cost.

    The cache exists to save time. It must never save budget, never answer a
    query whose meter is exhausted, never carry a partial cover out of a
    stopped construction, and never let one relation's cover stand in for
    another's.
    """

    RELATIONS = ("le", "lt", "eq", "ne")

    def terms(self, n=6):
        left = si.Field("l", 0, 3)
        right = si.Field("r", 3, 3)
        return [
            (dk.Term(left, 0), dk.Term(right, 0)),
            (dk.Term(left, 1), dk.Term(right, 0)),
            (dk.Term(left, 0), dk.Term(right, 2)),
            (dk.Term(left, 0), dk.constant(3)),
            (dk.constant(2), dk.Term(right, 0)),
            (dk.Term(left, -1), dk.Term(right, 0)),
        ]

    def test_a_hit_returns_exactly_the_cover_a_fresh_build_returns(self):
        cache = dk.CoverCache()
        checked = 0
        for name in self.RELATIONS:
            for lhs, rhs in self.terms():
                fresh = dk.relation_cover(name, lhs, rhs, 6, fresh_meter())
                first = dk.relation_cover(name, lhs, rhs, 6, fresh_meter(), cache)
                second = dk.relation_cover(name, lhs, rhs, 6, fresh_meter(), cache)
                self.assertEqual(fresh, first)
                self.assertEqual(fresh, second)
                # And the same set of indices, judged without the module.
                expected = {
                    index
                    for index in range(1 << 6)
                    if EXACT[name](
                        ((index >> 0) & 7) + lhs.offset if lhs.field else lhs.offset,
                        ((index >> 3) & 7) + rhs.offset if rhs.field else rhs.offset,
                    )
                }
                got = {
                    index
                    for index in range(1 << 6)
                    if any(cube.contains(index) for cube in second)
                }
                self.assertEqual(got, expected, f"{name} {lhs} {rhs}")
                checked += 1
        self.assertEqual(checked, len(self.RELATIONS) * len(self.terms()))
        self.assertGreater(cache.statistics()["hits"], 0, "nothing was reused")

    def test_the_key_separates_every_semantic_input(self):
        """Change one input at a time; the cover must change with it."""

        cache = dk.CoverCache()
        base_left = si.Field("l", 0, 3)
        base_right = si.Field("r", 3, 3)
        base = ("le", dk.Term(base_left, 0), dk.Term(base_right, 0), 6)

        variants = [
            ("lt", base[1], base[2], 6),                                   # relation
            ("le", dk.Term(base_left, 2), base[2], 6),                     # left offset
            ("le", base[1], dk.Term(base_right, 2), 6),                    # right offset
            ("le", dk.Term(si.Field("l", 0, 2), 0), base[2], 6),           # left width
            ("le", base[1], dk.Term(si.Field("r", 2, 3), 0), 6),           # right offset bits
            ("le", base[1], base[2], 7),                                   # universe width
        ]
        reference = dk.relation_cover(*base, fresh_meter(), cache)
        for variant in variants:
            through_cache = dk.relation_cover(*variant, fresh_meter(), cache)
            without_cache = dk.relation_cover(*variant, fresh_meter())
            self.assertEqual(
                through_cache, without_cache, f"{variant} was answered from a wrong entry"
            )
        # The base entry itself is still intact after all those neighbours.
        self.assertEqual(dk.relation_cover(*base, fresh_meter(), cache), reference)

    def test_a_hit_is_charged_what_the_miss_was_charged(self):
        cache = dk.CoverCache()
        lhs, rhs = self.terms()[0]

        miss = fresh_meter()
        dk.relation_cover("le", lhs, rhs, 6, miss, cache)
        hit = fresh_meter()
        dk.relation_cover("le", lhs, rhs, 6, hit, cache)

        self.assertEqual(hit.visited, miss.visited, "a hit skipped the visit charge")
        self.assertEqual(hit.records, miss.records, "a hit skipped the record charge")
        self.assertGreater(miss.records, 0)

    def test_a_hit_cannot_answer_past_an_exhausted_record_budget(self):
        """Reuse must not buy a cover the query could not afford to build."""

        cache = dk.CoverCache()
        lhs, rhs = self.terms()[0]
        paid = fresh_meter()
        cover = dk.relation_cover("le", lhs, rhs, 6, paid, cache)
        self.assertGreater(len(cover), 1)

        starved = fresh_meter(max_records=len(cover) - 1)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("le", lhs, rhs, 6, starved, cache)
        self.assertIn("record", caught.exception.reason)

    def test_a_hit_cannot_answer_past_an_exhausted_visit_budget(self):
        cache = dk.CoverCache()
        lhs, rhs = self.terms()[0]
        paid = fresh_meter()
        dk.relation_cover("le", lhs, rhs, 6, paid, cache)
        self.assertGreater(paid.visited, 1)

        starved = fresh_meter(max_visited=paid.visited - 1)
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("le", lhs, rhs, 6, starved, cache)
        self.assertIn("visited", caught.exception.reason)

    def test_a_hit_cannot_answer_past_an_expired_clock(self):
        cache = dk.CoverCache()
        lhs, rhs = self.terms()[0]
        dk.relation_cover("le", lhs, rhs, 6, fresh_meter(), cache)

        expired = fresh_meter(seconds=0.1)
        expired.started -= 10
        with self.assertRaises(si.BudgetExhausted) as caught:
            dk.relation_cover("le", lhs, rhs, 6, expired, cache)
        self.assertIn("time", caught.exception.reason)

    def test_a_construction_stopped_by_exhaustion_stores_nothing(self):
        cache = dk.CoverCache()
        lhs = dk.Term(si.Field("l", 0, 4), 0)
        rhs = dk.Term(si.Field("r", 4, 4), 0)
        starved = fresh_meter(max_records=3)
        with self.assertRaises(si.BudgetExhausted):
            dk.relation_cover("le", lhs, rhs, 8, starved, cache)
        self.assertEqual(cache.statistics()["entries"], 0, "a partial cover was stored")
        # And a later well-funded query still gets the complete cover.
        complete = dk.relation_cover("le", lhs, rhs, 8, fresh_meter(), cache)
        self.assertEqual(complete, dk.relation_cover("le", lhs, rhs, 8, fresh_meter()))

    def test_the_cache_is_bounded_in_entries_and_in_retained_cubes(self):
        tiny = dk.CoverCache(max_entries=2, max_cubes=10 ** 9)
        for offset in range(6):
            dk.relation_cover(
                "le", dk.Term(si.Field("l", 0, 3), offset),
                dk.Term(si.Field("r", 3, 3), 0), 6, fresh_meter(), tiny,
            )
        statistics = tiny.statistics()
        self.assertLessEqual(statistics["entries"], 2)
        self.assertGreater(statistics["refused"], 0)

        narrow = dk.CoverCache(max_entries=10 ** 9, max_cubes=1)
        for offset in range(4):
            dk.relation_cover(
                "lt", dk.Term(si.Field("l", 0, 3), offset),
                dk.Term(si.Field("r", 3, 3), 0), 6, fresh_meter(), narrow,
            )
        self.assertLessEqual(narrow.statistics()["cubes_retained"], 1)

    def test_the_simplified_paths_are_cached_without_changing_their_charge(self):
        cache = dk.CoverCache()
        field = si.Field("a", 0, 4)
        for name, lhs, rhs, expected in (
            ("le", dk.constant(0), dk.constant(1), (si.universe(4),)),
            ("lt", dk.constant(5), dk.constant(1), ()),
            ("le", dk.Term(field, 0), dk.Term(field, 0), (si.universe(4),)),
        ):
            miss = fresh_meter()
            self.assertEqual(dk.relation_cover(name, lhs, rhs, 4, miss, cache), expected)
            hit = fresh_meter()
            self.assertEqual(dk.relation_cover(name, lhs, rhs, 4, hit, cache), expected)
            self.assertEqual(hit.records, miss.records)
            self.assertEqual(hit.visited, miss.visited)


class CacheFreeJointQueryEquivalenceTests(unittest.TestCase):
    """A shared cache must not change any acceptance expression."""

    def test_expressions_are_identical_with_and_without_a_shared_cache(self):
        source = JOINT_FIXTURES["two_constants"]
        facts = dc.derive(source)
        times, addresses = incumbent(source)
        cycles = max(times.values()) + 1
        memory = dc.footprint(facts, addresses)

        shared = dk.CoverCache()
        checked = 0
        # The same cache is used across different windows and different
        # targets, which is exactly how the optimiser uses it.
        for target in ((cycles, memory), (cycles + 1, memory), (cycles, memory + 1)):
            for window in ((0,), (0, 1), (1, 2), (0, 1, 2)):
                if max(window) >= facts.count:
                    continue
                try:
                    plain = dk.JointQuery(
                        facts, times, addresses, window, target[0], target[1],
                        fresh_meter(),
                    ).expression()
                except dk.Infeasible:
                    with self.assertRaises(dk.Infeasible):
                        dk.JointQuery(
                            facts, times, addresses, window, target[0], target[1],
                            fresh_meter(), shared,
                        ).expression()
                    continue
                cached = dk.JointQuery(
                    facts, times, addresses, window, target[0], target[1],
                    fresh_meter(), shared,
                ).expression()
                self.assertEqual(
                    si.count_records(plain), si.count_records(cached),
                    f"window {window} target {target} changed size",
                )
                width = si.expression_width(plain)
                if width is not None and width <= 16:
                    for index in range(1 << width):
                        self.assertEqual(
                            accepts(plain, index), accepts(cached, index),
                            f"window {window} target {target} index {index}",
                        )
                checked += 1
        self.assertGreater(checked, 0, "no joint query was compared")

    def test_a_cache_does_not_survive_between_compilations(self):
        """Each compilation builds its own cache; none is process-global."""

        import direct_optimizer

        source = JOINT_FIXTURES["two_constants"]
        first, report_one = dcmp.compile_with_report(source)
        second, report_two = dcmp.compile_with_report(source)
        self.assertEqual(first, second)
        one = report_one["optimisation"]["cover_cache"]
        two = report_two["optimisation"]["cover_cache"]
        # A cache carried over would show no misses the second time round.
        self.assertEqual(one["misses"], two["misses"])
        self.assertEqual(one["entries"], two["entries"])
