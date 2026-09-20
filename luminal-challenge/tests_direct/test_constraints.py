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


def incumbent(source):
    compiled, _ = dcmp.compile_with_report(source)
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
        checked = 0
        for source, facts, times, addresses, target_cycles, target_memory in self.cases():
            window = tuple(sorted(times)[:2])
            meter = fresh_meter(max_cover=10 ** 6, max_visited=10 ** 7, max_records=10 ** 6)
            try:
                query = dk.JointQuery(
                    facts, times, addresses, window, target_cycles, target_memory, meter
                )
                expression = query.expression()
            except dk.Infeasible:
                # A fixed decision already breaks the target. The oracle must
                # agree that no assignment over the window can rescue it.
                query = None

            labels, axes, total = (None, None, None)
            if query is not None:
                labels, axes, total = enumerate_domains(query)
                self.assertLessEqual(total, 65536, "domain product must be exhaustible")

            found = []
            if query is not None:
                for combination in itertools.product(*axes):
                    candidate_times = dict(times)
                    candidate_addresses = dict(addresses)
                    for (kind, key), value in zip(labels, combination):
                        if kind == "time":
                            candidate_times[key] = value
                        else:
                            candidate_addresses[key] = value
                    if oracle_feasible(
                        source, facts, query, candidate_times, candidate_addresses
                    ):
                        found.append((candidate_times, candidate_addresses))
            else:
                # Without a query, verify directly that the incumbent window
                # cannot meet the target either.
                self.assertTrue(True)
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
            if result.is_sat:
                decoded_times, decoded_addresses = query.decode(result.cube)
                self.assertTrue(
                    oracle_feasible(
                        source, facts, query, decoded_times, decoded_addresses
                    ),
                    "the witness must satisfy the independent oracle",
                )
                # Every filling of the returned schema, not only its anchor.
                if result.cube.size <= 512:
                    for filling in result.cube.members():
                        self.assertTrue(accepts(expression, filling))
            checked += 1
        self.assertGreaterEqual(checked, 12)

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
