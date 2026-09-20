"""T01: schema algebra, fields, decoding, and query solving.

Every oracle here is built from Python sets and plain integer arithmetic. The
production predicates in ``schema_index`` are never used to judge themselves.
"""

from __future__ import annotations

import itertools
import time
import unittest

import schema_index as si


# --------------------------------------------------------------------------
# Independent oracles: explicit sets, built without the module under test
# --------------------------------------------------------------------------


def members_of(n: int, anchor: int, free: int) -> frozenset:
    """The set denoted by an anchor and free mask, decided coordinate by coordinate."""

    fixed = [b for b in range(n) if not (free >> b) & 1]
    return frozenset(
        index
        for index in range(1 << n)
        if all(((index >> b) & 1) == ((anchor >> b) & 1) for b in fixed)
    )


def cube_members(cube) -> frozenset:
    return members_of(cube.n, cube.anchor, cube.free_mask)


def cover_members(cover) -> frozenset:
    out = set()
    for cube in cover:
        out |= cube_members(cube)
    return frozenset(out)


def all_cubes(n: int):
    limit = (1 << n) - 1
    return [
        si.Cube(n, anchor, free)
        for free in range(limit + 1)
        for anchor in range(limit + 1)
        if not (anchor & free)
    ]


def accepted_set(expression, n: int) -> frozenset:
    """The acceptance set of an expression, evaluated by explicit set algebra."""

    if isinstance(expression, si.Leaf):
        return cover_members(expression.cubes)
    if isinstance(expression, si.AllOf):
        out = frozenset(range(1 << n))
        for child in expression.children:
            out &= accepted_set(child, n)
        return out
    if isinstance(expression, si.AnyOf):
        out = frozenset()
        for child in expression.children:
            out |= accepted_set(child, n)
        return out
    raise AssertionError("unknown expression")


def leaf_from_set(n: int, indices) -> si.Leaf:
    """A leaf covering exactly ``indices``, as singleton cubes."""

    return si.Leaf(tuple(si.Cube(n, index, 0) for index in sorted(indices)))


# --------------------------------------------------------------------------


class CubeConstructionTests(unittest.TestCase):
    def test_zero_width_universe_holds_the_empty_assignment(self):
        cube = si.universe(0)
        self.assertEqual(cube.anchor, 0)
        self.assertEqual(cube.free_mask, 0)
        self.assertEqual(cube.size, 1)
        self.assertEqual(list(cube.members()), [0])
        self.assertTrue(cube.contains(0))

    def test_booleans_are_rejected_where_integers_are_required(self):
        with self.assertRaises(TypeError):
            si.Cube(True, 0, 0)
        with self.assertRaises(TypeError):
            si.Cube(2, True, 0)
        with self.assertRaises(TypeError):
            si.Cube(2, 0, False)

    def test_invalid_anchors_and_masks_are_rejected(self):
        with self.assertRaises(ValueError):
            si.Cube(3, 8, 0)
        with self.assertRaises(ValueError):
            si.Cube(3, 0, 8)
        with self.assertRaises(ValueError):
            si.Cube(3, 1, 1)
        with self.assertRaises(ValueError):
            si.Cube(-1, 0, 0)

    def test_complement_stays_inside_the_declared_universe(self):
        # An unbounded Python complement would leak bits above the universe.
        for n in range(6):
            cube = si.universe(n)
            self.assertEqual(cube.fixed_mask, 0)
            self.assertLessEqual(cube.free_mask, (1 << n) - 1)
            for member in cube.members():
                self.assertLess(member, 1 << n)

    def test_label_declares_its_lsb_first_convention(self):
        cube = si.Cube(4, 0b0001, 0b1000)
        self.assertEqual(cube.label(), "x0..x3:100*")

    def test_members_are_increasing_and_match_the_oracle(self):
        for n in range(6):
            for cube in all_cubes(n):
                listed = list(cube.members())
                self.assertEqual(listed, sorted(listed))
                self.assertEqual(len(listed), cube.size)
                self.assertEqual(frozenset(listed), cube_members(cube))

    def test_contains_agrees_with_the_oracle_for_every_index(self):
        for n in range(5):
            for cube in all_cubes(n):
                expected = cube_members(cube)
                for index in range(1 << n):
                    self.assertEqual(cube.contains(index), index in expected)
                self.assertFalse(cube.contains(1 << n))


class CubeAlgebraTests(unittest.TestCase):
    """Every cube pair of widths zero through five, against explicit sets."""

    def test_intersection_and_difference_over_every_pair(self):
        for n in range(6):
            cubes = all_cubes(n)
            sets = {cube: cube_members(cube) for cube in cubes}
            self.assertEqual(len(cubes), 3 ** n)
            for a in cubes:
                for b in cubes:
                    expected_meet = sets[a] & sets[b]
                    meet = si.intersect(a, b)
                    self.assertEqual(si.compatible(a, b), bool(expected_meet))
                    if not expected_meet:
                        self.assertIsNone(meet)
                    else:
                        self.assertIsNotNone(meet)
                        self.assertEqual(cube_members(meet), expected_meet)

                    pieces = si.difference(a, b)
                    self.assertEqual(cover_members(pieces), sets[a] - sets[b])
                    # The difference must be disjoint, not merely extensionally right.
                    total = sum(piece.size for piece in pieces)
                    self.assertEqual(total, len(sets[a] - sets[b]))
                    for first, second in itertools.combinations(pieces, 2):
                        self.assertEqual(cube_members(first) & cube_members(second), frozenset())

    def test_containment_and_duplicate_cases(self):
        a = si.Cube(4, 0b0000, 0b1111)
        b = si.Cube(4, 0b0101, 0b0000)
        self.assertEqual(si.difference(a, a), ())
        self.assertEqual(si.intersect(a, a), a)
        self.assertEqual(si.intersect(b, b), b)
        self.assertEqual(si.difference(b, a), ())
        self.assertEqual(cover_members(si.difference(a, b)), cube_members(a) - cube_members(b))

    def test_incompatible_fixed_bits_leave_the_left_operand_whole(self):
        a = si.Cube(3, 0b001, 0b100)
        b = si.Cube(3, 0b010, 0b100)
        self.assertFalse(si.compatible(a, b))
        self.assertIsNone(si.intersect(a, b))
        self.assertEqual(si.difference(a, b), (a,))

    def test_mismatched_widths_are_rejected(self):
        a = si.Cube(3, 0, 0)
        b = si.Cube(4, 0, 0)
        for operation in (si.intersect, si.difference, si.compatible):
            with self.assertRaises(ValueError):
                operation(a, b)

    def test_restrict_over_every_cube_coordinate_and_value(self):
        for n in range(1, 6):
            for cube in all_cubes(n):
                base = cube_members(cube)
                for coordinate in range(n):
                    for value in (0, 1):
                        expected = frozenset(
                            index for index in base if ((index >> coordinate) & 1) == value
                        )
                        got = si.restrict(cube, coordinate, value)
                        if not expected:
                            self.assertIsNone(got)
                        else:
                            self.assertIsNotNone(got)
                            self.assertEqual(got.n, cube.n)
                            self.assertEqual(cube_members(got), expected)

    def test_restrict_rejects_out_of_range_coordinates_and_values(self):
        cube = si.universe(3)
        with self.assertRaises(ValueError):
            si.restrict(cube, 3, 0)
        with self.assertRaises(ValueError):
            si.restrict(cube, 0, 2)
        with self.assertRaises(ValueError):
            si.restrict(cube, 0, True)
        with self.assertRaises(ValueError):
            si.restrict(cube, -1, 0)

    def test_min_member_of_empty_and_nonempty_covers(self):
        self.assertIsNone(si.min_member(()))
        cover = (si.Cube(4, 0b1000, 0b0011), si.Cube(4, 0b0100, 0b0010))
        self.assertEqual(si.min_member(cover), 0b0100)
        for n in range(5):
            for cube in all_cubes(n):
                self.assertEqual(si.min_member((cube,)), min(cube_members(cube)))

    def test_cover_normalisation_orders_and_deduplicates(self):
        first = si.Cube(3, 0b001, 0b010)
        second = si.Cube(3, 0b000, 0b110)
        leaf = si.Leaf((first, second, first))
        self.assertEqual(leaf.cubes, (second, first))
        with self.assertRaises(ValueError):
            si.Leaf((si.Cube(2, 0, 0), si.Cube(3, 0, 0)))

    def test_universal_and_empty_covers(self):
        for n in range(4):
            self.assertEqual(cover_members(si.true_leaf(n).cubes), frozenset(range(1 << n)))
            self.assertEqual(cover_members(si.false_leaf().cubes), frozenset())


class FieldTests(unittest.TestCase):
    def test_field_validation(self):
        with self.assertRaises(ValueError):
            si.Field("", 0, 1)
        with self.assertRaises(ValueError):
            si.Field("t", 0, 0)
        with self.assertRaises(ValueError):
            si.Field("t", -1, 1)

    def test_decoding_reads_the_field_lsb_first(self):
        field = si.Field("value", 2, 3)
        # Bit 2 of the index is the field's least significant bit.
        self.assertEqual(field.decode(0b00100), 1)
        self.assertEqual(field.decode(0b01000), 2)
        self.assertEqual(field.decode(0b10000), 4)
        self.assertEqual(field.decode(0b11100), 7)
        self.assertEqual(field.decode(0b00011), 0)
        for value in range(field.limit):
            self.assertEqual(field.decode(field.encode(value)), value)
        with self.assertRaises(ValueError):
            field.encode(field.limit)

    def test_interval_covers_every_inclusive_range(self):
        for width in range(1, 6):
            for offset in (0, 2):
                n = offset + width + 1
                f = si.Field("f", offset, width)
                for lo in range(1 << width):
                    for hi in range(lo, 1 << width):
                        cover = si.interval(f, lo, hi, n)
                        expected = frozenset(
                            index for index in range(1 << n) if lo <= f.decode(index) <= hi
                        )
                        self.assertEqual(cover_members(cover), expected)
                        # Blocks are disjoint, and coordinates outside stay free.
                        self.assertEqual(sum(c.size for c in cover), len(expected))
                        outside = ((1 << n) - 1) ^ f.mask
                        for cube in cover:
                            self.assertEqual(cube.free_mask & outside, outside)

    def test_interval_edge_cases(self):
        f = si.Field("f", 0, 3)
        self.assertEqual(si.interval(f, 5, 4, 3), ())
        self.assertEqual(cover_members(si.interval(f, 0, 99, 3)), frozenset(range(8)))
        with self.assertRaises(ValueError):
            si.interval(si.Field("f", 0, 4), 0, 1, 3)
        with self.assertRaises(ValueError):
            si.interval(f, -1, 2, 3)

    def test_domain_excludes_invalid_non_power_of_two_codes(self):
        f = si.Field("engine", 0, 3)
        cover = si.domain(f, 5, 3)
        self.assertEqual(cover_members(cover), frozenset({0, 1, 2, 3, 4}))
        for invalid in (5, 6, 7):
            self.assertFalse(si.cover_contains(cover, invalid))
        self.assertEqual(cover_members(si.domain(f, 8, 3)), frozenset(range(8)))
        with self.assertRaises(ValueError):
            si.domain(f, 9, 3)
        with self.assertRaises(ValueError):
            si.domain(f, 0, 3)


class SolverTests(unittest.TestCase):
    def assert_sat_cube_is_wholly_accepted(self, result, expression, n):
        """Every filling of the returned schema must satisfy the whole query."""

        self.assertTrue(result.is_sat)
        expected = accepted_set(expression, n)
        fillings = list(result.cube.members())
        self.assertEqual(len(fillings), result.cube.size)
        self.assertTrue(fillings)
        for filling in fillings:
            self.assertIn(filling, expected)

    def test_satisfiable_and_exhausted_queries_over_small_universes(self):
        n = 4
        cubes = all_cubes(n)
        # A deterministic spread of conjunctions and disjunctions.
        for a, b, c in itertools.islice(itertools.product(cubes, repeat=3), 0, None, 37):
            expression = si.AllOf((
                si.AnyOf((si.Leaf((a,)), si.Leaf((b,)))),
                si.Leaf((c,)),
            ))
            expected = accepted_set(expression, n)
            result = si.solve(expression, n, si.Budget(seconds=5.0))
            if expected:
                self.assert_sat_cube_is_wholly_accepted(result, expression, n)
            else:
                self.assertTrue(result.is_unsat, result.reason)

    def test_every_filling_of_every_witness_over_random_free_covers(self):
        n = 5
        universe = frozenset(range(1 << n))
        for seed in range(64):
            picks = [
                frozenset(i for i in universe if (i * (seed + k + 1) + k) % 3)
                for k in range(3)
            ]
            expression = si.AllOf(tuple(leaf_from_set(n, p) for p in picks))
            expected = accepted_set(expression, n)
            result = si.solve(expression, n, si.Budget(seconds=5.0))
            if expected:
                self.assert_sat_cube_is_wholly_accepted(result, expression, n)
            else:
                self.assertTrue(result.is_unsat, result.reason)

    def test_empty_and_vacuous_expressions(self):
        self.assertTrue(si.solve(si.Leaf(()), 3, si.Budget(seconds=5.0)).is_unsat)
        self.assertTrue(si.solve(si.AnyOf(()), 3, si.Budget(seconds=5.0)).is_unsat)
        vacuous = si.solve(si.AllOf(()), 3, si.Budget(seconds=5.0))
        self.assertTrue(vacuous.is_sat)
        self.assertEqual(vacuous.cube, si.universe(3))

    def test_free_coordinate_of_one_schema_is_a_connected_input_of_another(self):
        # Coordinate 2 is free in the first schema and constrained by the second.
        n = 4
        loose = si.Leaf((si.Cube(n, 0b0001, 0b1100),))
        connected = si.Leaf((si.Cube(n, 0b0100, 0b1011),))
        expression = si.AllOf((loose, connected))
        result = si.solve(expression, n, si.Budget(seconds=5.0))
        self.assert_sat_cube_is_wholly_accepted(result, expression, n)
        self.assertEqual(result.cube.free_mask & 0b0100, 0)
        for filling in result.cube.members():
            self.assertEqual((filling >> 2) & 1, 1)

    def test_width_mismatch_between_expression_and_universe(self):
        with self.assertRaises(ValueError):
            si.solve(si.Leaf((si.Cube(3, 0, 0),)), 4, si.Budget(seconds=5.0))

    def test_branch_order_is_deterministic(self):
        n = 4
        expression = si.AnyOf((
            si.Leaf((si.Cube(n, 0b0110, 0b1000),)),
            si.Leaf((si.Cube(n, 0b0001, 0b0000),)),
        ))
        first = si.solve(expression, n, si.Budget(seconds=5.0))
        for _ in range(4):
            again = si.solve(expression, n, si.Budget(seconds=5.0))
            self.assertEqual(again.cube, first.cube)
        self.assertEqual(first.cube.anchor, 0b0110)


class BudgetTests(unittest.TestCase):
    """Exhaustion is UNKNOWN. It is never UNSAT, and never a complete cover."""

    def _hard_unsatisfiable(self, n=20, depth=16):
        """Cheap to build, expensive to search, and certainly unsatisfiable.

        Each child splits one coordinate two ways, so the search must walk
        ``2 ** depth`` branches, while the whole expression holds only a few
        dozen records. The closing empty leaf makes every branch fail, which
        separates a time or visit limit from an honest exhaustion.
        """

        children = []
        for k in range(depth):
            free = ((1 << n) - 1) ^ (1 << k)
            children.append(si.AnyOf((
                si.Leaf((si.Cube(n, 0, free),)),
                si.Leaf((si.Cube(n, 1 << k, free),)),
            )))
        children.append(si.Leaf(()))
        return si.AllOf(tuple(children))

    def test_visited_budget_returns_unknown(self):
        expression = self._hard_unsatisfiable()
        result = si.solve(expression, 20, si.Budget(seconds=60.0, max_visited=5))
        self.assertTrue(result.is_unknown)
        self.assertIn("visited", result.reason)
        self.assertIsNone(result.cube)

    def test_record_budget_returns_unknown(self):
        expression = self._hard_unsatisfiable()
        result = si.solve(expression, 20, si.Budget(seconds=60.0, max_records=10))
        self.assertTrue(result.is_unknown)
        self.assertIn("record", result.reason)

    def test_time_budget_returns_unknown(self):
        expression = self._hard_unsatisfiable()
        started = time.monotonic()
        result = si.solve(expression, 20, si.Budget(seconds=0.02, max_visited=10 ** 9))
        self.assertTrue(result.is_unknown)
        self.assertIn("time", result.reason)
        self.assertLess(time.monotonic() - started, 5.0)

    def test_cover_budget_is_reported_through_the_meter(self):
        meter = si.Budget(seconds=60.0, max_cover=8).start()
        meter.cover(8)
        with self.assertRaises(si.BudgetExhausted):
            meter.cover(9)

    def test_a_completed_unsatisfiable_query_is_unsat_not_unknown(self):
        n = 4
        expression = si.AllOf((
            si.Leaf((si.Cube(n, 0b0000, 0b0110),)),
            si.Leaf((si.Cube(n, 0b0001, 0b0110),)),
        ))
        self.assertEqual(accepted_set(expression, n), frozenset())
        result = si.solve(expression, n, si.Budget(seconds=5.0))
        self.assertTrue(result.is_unsat)
        self.assertIsNone(result.reason)

    def test_budget_validation(self):
        with self.assertRaises(ValueError):
            si.Budget(seconds=0)
        with self.assertRaises(ValueError):
            si.Budget(max_visited=0)
        with self.assertRaises(TypeError):
            si.Budget(seconds="fast")

    def test_result_payload_records_counters(self):
        result = si.solve(si.true_leaf(3), 3, si.Budget(seconds=5.0))
        payload = result.to_dict()
        self.assertEqual(payload["status"], si.SAT)
        self.assertEqual(payload["width"], 3)
        self.assertIn("visited", payload["counters"])
        self.assertGreaterEqual(payload["visited"], 1)


if __name__ == "__main__":
    unittest.main()


class IncomingExpressionBudgetTests(unittest.TestCase):
    """F3: leaves handed to the solver are validated and billed exactly once."""

    def test_retry_after_failed_charge_stays_unknown(self):
        meter = si.Budget(seconds=10.0, max_records=1).start()
        expression = si.Leaf((si.universe(1),))
        first = si.solve(expression, 1, meter=meter)
        retry = si.solve(expression, 1, meter=meter)
        self.assertTrue(first.is_unknown)
        self.assertTrue(retry.is_unknown, "a failed charge must not authorize a retry")
        self.assertIn("record", retry.reason)
        self.assertIsNone(retry.cube)

    def test_cached_expression_cannot_bypass_later_exhaustion(self):
        meter = si.Budget(seconds=10.0, max_records=2).start()
        first = si.Leaf((si.universe(1),))
        second = si.Leaf((si.Cube(1, 0, 0),))
        self.assertTrue(si.solve(first, 1, meter=meter).is_sat)
        self.assertTrue(si.solve(second, 1, meter=meter).is_unknown)
        retry = si.solve(first, 1, meter=meter)
        self.assertTrue(retry.is_unknown, "cached work cannot revive an exhausted meter")
        self.assertIn("record", retry.reason)
        self.assertIsNone(retry.cube)

    def test_an_oversized_incoming_leaf_is_refused(self):
        leaf = si.Leaf(tuple(si.Cube(4, index, 0) for index in range(16)))
        result = si.solve(leaf, 4, si.Budget(seconds=10.0, max_cover=1))
        self.assertTrue(result.is_unknown)
        self.assertIn("cover", result.reason)
        self.assertIsNone(result.cube)

    def test_a_leaf_within_the_cap_is_accepted(self):
        leaf = si.Leaf(tuple(si.Cube(4, index, 0) for index in range(4)))
        result = si.solve(leaf, 4, si.Budget(seconds=10.0, max_cover=8))
        self.assertTrue(result.is_sat)

    def test_charging_an_expression_twice_bills_it_once(self):
        meter = si.Budget(seconds=10.0, max_records=1000).start()
        expression = si.AllOf((si.Leaf((si.Cube(3, 0, 0),)),))
        meter.charge_expression(expression)
        first = meter.records
        meter.charge_expression(expression)
        self.assertEqual(meter.records, first)
        self.assertEqual(first, si.count_records(expression))

    def test_a_different_expression_is_billed_separately(self):
        meter = si.Budget(seconds=10.0, max_records=1000).start()
        one = si.AllOf((si.Leaf((si.Cube(3, 0, 0),)),))
        two = si.AllOf((si.Leaf((si.Cube(3, 1, 0),)),))
        meter.charge_expression(one)
        first = meter.records
        meter.charge_expression(two)
        self.assertGreater(meter.records, first)

    def test_marking_charged_prevents_a_second_bill(self):
        meter = si.Budget(seconds=10.0, max_records=1000).start()
        expression = si.AllOf((si.Leaf((si.Cube(3, 0, 0),)),))
        meter.mark_charged(expression)
        meter.charge_expression(expression)
        self.assertEqual(meter.records, 0)
