"""Codec, domain and property tests for the phase 2 structural encoding.

These cover the acceptance-matrix checks that belong to the codec: C04 fixed
offsets against a schedule-dependent traversal, C05 rank cardinality and zero
width, C06 external predecessors and successors, C07 inclusive endpoints and
pending writes, C08 lifetimes that move because a selected reader moved, C09
vector geometry, C10 exact domain equivalence, C12 a fully decoded illegal
compilation, and C30 the canonical object.

Every fixture is built here or read from the frozen delegation inputs. No
protected source is edited to produce a failure.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import machine  # noqa: E402

import direct_contract as dc  # noqa: E402
import schema_index as si  # noqa: E402

from research import structural_encoding as se  # noqa: E402
from research import structural_oracle as so  # noqa: E402


FIXTURES = json.loads((ROOT / "plan" / "phase2" / "FIXTURES.json").read_text())["fixtures"]


def case_for(buffers):
    return {name: [0] * length for name, length in sorted(buffers.items())}


def program_of(name, buffers, operations, cases=1):
    program = {
        "name": name,
        "buffers": dict(buffers),
        "operations": operations,
        "cases": [case_for(buffers) for _ in range(cases)],
    }
    machine.validate_program(program)
    return program


def record_of(program, selected, time_domains, address_domains,
              fixed_times, fixed_addresses, incumbent=None, target=None, identifier="t"):
    return {
        "id": identifier,
        "family": "unit",
        "program": program,
        "selected_operations": list(selected),
        "time_domains": {str(key): list(value) for key, value in time_domains.items()},
        "address_domains": {key: list(value) for key, value in address_domains.items()},
        "fixed_times": {str(key): value for key, value in fixed_times.items()},
        "fixed_addresses": dict(fixed_addresses),
        "incumbent": incumbent,
        "target": target,
    }


def compile_from(program, times, addresses):
    facts = dc.derive(program)
    return dc.compilation(facts, times, addresses)


# Two loads, a multiply and a store. Latencies 3 + 3 + 2 + 1 give a horizon of
# nine, which leaves room for the fixed decisions these tests need. Every
# declared and fixed cycle must lie below the horizon, so a smaller program
# built only from unit-latency operations cannot express them.
def small_program():
    return program_of(
        "small",
        {"data": 8, "out": 1},
        [
            {"id": 0, "op": "load", "dest": "a", "buffer": "data", "offset": 0},
            {"id": 1, "op": "load", "dest": "b", "buffer": "data", "offset": 1},
            {"id": 2, "op": "mul", "dest": "c", "args": ["a", "b"]},
            {"id": 3, "op": "store", "args": ["c"], "buffer": "out", "offset": 0},
        ],
    )


# The same shape without a consumer for the multiply, so a selected operation
# has predecessors but no fixed successor bounding it from above.
def open_ended_program():
    return program_of(
        "open_ended",
        {"data": 8},
        [
            {"id": 0, "op": "load", "dest": "a", "buffer": "data", "offset": 0},
            {"id": 1, "op": "load", "dest": "b", "buffer": "data", "offset": 1},
            {"id": 2, "op": "mul", "dest": "c", "args": ["a", "b"]},
        ],
    )


class DomainValidation(unittest.TestCase):
    """A malformed domain is refused; an empty feasible set is not malformed."""

    def setUp(self):
        self.program = small_program()

    def base(self, **overrides):
        record = record_of(
            self.program,
            selected=[0],
            time_domains={0: [0, 1]},
            address_domains={"a": [0, 1]},
            fixed_times={1: 0, 2: 6, 3: 8},
            fixed_addresses={"b": 2, "c": 3},
        )
        record.update(overrides)
        return record

    def test_accepts_a_well_formed_record(self):
        domain = se.Domain.from_record(self.base())
        self.assertEqual(domain.selected_operations, (0,))
        self.assertEqual(domain.cartesian_size(), 4)

    def test_rejects_unsorted_domain(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(time_domains={"0": [1, 0]}))

    def test_rejects_duplicate_domain_values(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(time_domains={"0": [0, 0, 1]}))

    def test_rejects_empty_declared_domain(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(time_domains={"0": []}))

    def test_rejects_boolean_domain_values(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(time_domains={"0": [False, True]}))

    def test_rejects_negative_and_out_of_range(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(fixed_times={"1": -1, "2": 6, "3": 8}))
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(time_domains={"0": [0, 9999]}))

    def test_rejects_operation_covered_twice(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(fixed_times={"0": 0, "1": 0, "2": 6, "3": 8}))

    def test_rejects_operation_covered_never(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(fixed_times={"1": 0, "2": 6}))

    def test_rejects_selected_values_that_are_not_selected_results(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(
                self.base(address_domains={"b": [0, 1]}, fixed_addresses={"a": 2, "c": 3})
            )

    def test_rejects_malformed_incumbent(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(incumbent={"bundles": []}))
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(incumbent={"bundles": [{}], "scratch": {}}))

    def test_rejects_misaligned_vector_address(self):
        program = program_of(
            "vec",
            {"data": 8, "out": 8},
            [
                {"id": 0, "op": "vload", "dest": "v", "buffer": "data", "offset": 0},
                {"id": 1, "op": "vstore", "args": ["v"], "buffer": "out", "offset": 0},
            ],
        )
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(
                record_of(program, [0], {0: [0]}, {"v": [1]}, {1: 4}, {})
            )

    def test_rejects_address_past_the_scratchpad(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.base(address_domains={"a": [255, 256]}))

    def test_empty_feasible_set_is_legal(self):
        """A contradiction is expressed through fixed constraints, not malformation."""

        # Operation 2 multiplies a and b, so it cannot issue before operation 1
        # has produced b three cycles later. Fixing both at cycle 0 is a
        # contradiction among the fixed decisions alone.
        record = record_of(
            self.program,
            selected=[0],
            time_domains={0: [5]},
            address_domains={"a": [0]},
            fixed_times={1: 0, 2: 0, 3: 2},
            fixed_addresses={"b": 1, "c": 2},
        )
        domain = se.Domain.from_record(record)
        result = se.decode(domain, 0, "structural_rank")
        self.assertEqual(result.status, se.DEAD_END)
        self.assertIn("contradict", result.reason)


class LayoutAndOffsets(unittest.TestCase):
    """C04: field offsets are fixed and never follow the decoded traversal."""

    def setUp(self):
        # Two vectors and one scalar, so the allocation traversal is vectors
        # first ordered by write cycle, which the schedule can reorder.
        self.program = program_of(
            "reorder",
            {"data": 8, "out": 16},
            [
                {"id": 0, "op": "vload", "dest": "u", "buffer": "data", "offset": 0},
                {"id": 1, "op": "vload", "dest": "w", "buffer": "data", "offset": 0},
                {"id": 2, "op": "vadd", "dest": "z", "args": ["u", "w"]},
                {"id": 3, "op": "vstore", "args": ["z"], "buffer": "out", "offset": 0},
            ],
        )
        self.facts = dc.derive(self.program)

    def record(self):
        return record_of(
            self.program,
            selected=[0, 1],
            time_domains={0: [0, 1, 2], 1: [0, 1, 2]},
            address_domains={"u": [0, 8, 16], "w": [0, 8, 16]},
            fixed_times={2: 7, 3: 8},
            fixed_addresses={"z": 24},
            identifier="reorder",
        )

    def test_offsets_are_by_producer_id_not_by_write_cycle(self):
        domain = se.Domain.from_record(self.record())
        for codec in se.CODECS:
            plan = se.layout(domain, codec)
            keys = [field.key for field in plan.fields]
            self.assertEqual(
                keys,
                [("time", 0), ("time", 1), ("address", "u"), ("address", "w")],
                codec,
            )
            offsets = [field.offset for field in plan.fields]
            self.assertEqual(offsets, sorted(offsets))

    def test_traversal_order_changes_but_offsets_do_not(self):
        domain = se.Domain.from_record(self.record())
        plan = se.layout(domain, "structural_rank")
        before = {field.key: field.offset for field in plan.fields}

        # u before w, then w before u: the allocation traversal must swap.
        early = se.State(domain)
        early.times.update({0: 0, 1: 2})
        early.recompute_lifetimes()
        late = se.State(domain)
        late.times.update({0: 2, 1: 0})
        late.recompute_lifetimes()
        self.assertEqual(early.allocation_order(), ("u", "w"))
        self.assertEqual(late.allocation_order(), ("w", "u"))

        after = {field.key: field.offset for field in se.layout(domain, "structural_rank").fields}
        self.assertEqual(before, after)

    def test_round_trip_holds_under_both_traversal_orders(self):
        record = self.record()
        domain = se.Domain.from_record(record)
        enumeration = so.enumerate_feasible(record, 65536)
        self.assertGreater(enumeration["feasible_count"], 0)
        for member in enumeration["feasible"]:
            compilation = json.loads(member["identity"])
            for codec in se.CODECS:
                index = se.encode(domain, compilation, codec)
                back = se.decode(domain, index, codec)
                self.assertEqual(back.status, se.COMPLETE)
                self.assertEqual(se.canonical_json(back.compilation), member["identity"])


class RankCardinality(unittest.TestCase):
    """C05: three and five choices, excess ranks, and zero-width constants."""

    def setUp(self):
        self.program = small_program()

    def domain_with(self, values):
        return se.Domain.from_record(
            record_of(
                self.program,
                selected=[0],
                time_domains={0: list(values)},
                address_domains={"a": [0]},
                fixed_times={1: 0, 2: 6, 3: 8},
                fixed_addresses={"b": 1, "c": 2},
                identifier="ranks",
            )
        )

    def test_three_choices_take_two_bits_and_leave_rank_three_invalid(self):
        domain = self.domain_with([0, 1, 2])
        plan = se.layout(domain, "structural_rank")
        self.assertEqual(plan.width, 2)
        self.assertEqual(se.decode(domain, 3, "structural_rank").status, se.INVALID_CODE)
        for index in range(3):
            self.assertEqual(se.decode(domain, index, "structural_rank").status, se.COMPLETE)

    def test_five_choices_take_three_bits(self):
        # The multiply has no consumer here, so nothing bounds operation 0 from
        # above and all five declared cycles are legal.
        domain = se.Domain.from_record(
            record_of(
                open_ended_program(),
                selected=[0],
                time_domains={0: [0, 1, 2, 3, 4]},
                address_domains={"a": [0]},
                fixed_times={1: 0, 2: 7},
                fixed_addresses={"b": 1, "c": 2},
                identifier="five",
            )
        )
        plan = se.layout(domain, "structural_rank")
        self.assertEqual(plan.width, 3)
        statuses = [se.decode(domain, index, "structural_rank").status for index in range(8)]
        self.assertEqual(statuses.count(se.COMPLETE), 5)
        self.assertEqual(statuses.count(se.INVALID_CODE), 3)

    def test_field_width_follows_the_declared_domain_not_the_option_count(self):
        """Contract section 4: the width is fixed, state dependence is not.

        Five declared cycles reserve three bits even when the prefix state
        leaves only four of them legal. The unreachable rank is INVALID_CODE and
        is counted; it is never padded away by duplicating an option, because
        that would destroy injectivity and bias uniform-bit sampling.
        """

        domain = self.domain_with([0, 1, 2, 3, 4])
        self.assertEqual(se.layout(domain, "structural_rank").width, 3)
        self.assertEqual(len(domain.ordered_domain(("time", 0))), 5)
        self.assertEqual(len(se.State(domain).time_options(0)), 4)
        statuses = [se.decode(domain, index, "structural_rank").status for index in range(8)]
        self.assertEqual(statuses.count(se.COMPLETE), 4)
        self.assertEqual(statuses.count(se.INVALID_CODE), 4)

    def test_single_choice_is_a_zero_width_constant(self):
        domain = self.domain_with([0])
        plan = se.layout(domain, "structural_rank")
        self.assertEqual(plan.width, 0)
        self.assertEqual(plan.fields[0].width, 0)
        self.assertEqual(se.decode(domain, 0, "structural_rank").status, se.COMPLETE)
        with self.assertRaises(se.DomainError):
            se.decode(domain, 1, "structural_rank")

    def test_zero_width_options_are_still_checked(self):
        """A constant field occupies no bits, and an empty local list is DEAD_END."""

        # The fixed decisions are consistent with each other: b is loaded at 0
        # and ready at 3, the multiply issues at 3 and the store at 5. They
        # leave operation 0 needing a cycle at or before 0, and its only
        # declared cycle is 1, so a zero-width field has an empty option list.
        domain = se.Domain.from_record(
            record_of(
                self.program,
                selected=[0],
                time_domains={0: [1]},
                address_domains={"a": [0]},
                fixed_times={1: 0, 2: 3, 3: 5},
                fixed_addresses={"b": 1, "c": 2},
                identifier="zerowidth",
            )
        )
        self.assertEqual(se.layout(domain, "structural_rank").width, 0)
        result = se.decode(domain, 0, "structural_rank")
        self.assertEqual(result.status, se.DEAD_END)

    def test_index_must_be_a_plain_integer_in_range(self):
        domain = self.domain_with([0, 1, 2])
        for bad in (-1, 4, True, 1.0, "0", None):
            with self.assertRaises(se.DomainError):
                se.decode(domain, bad, "structural_rank")

    def test_dead_end_is_checked_before_rank_validity(self):
        """The precedence that makes the two statuses disjoint."""

        domain = se.Domain.from_record(
            record_of(
                self.program,
                selected=[0],
                time_domains={0: [6, 7, 8]},
                address_domains={"a": [0]},
                fixed_times={1: 0, 2: 3, 3: 5},
                fixed_addresses={"b": 1, "c": 2},
                identifier="precedence",
            )
        )
        # Rank 3 is out of range *and* the option list is empty. The contract
        # fixes DEAD_END as the answer.
        self.assertEqual(se.decode(domain, 3, "structural_rank").status, se.DEAD_END)
        self.assertEqual(se.decode(domain, 0, "structural_rank").status, se.DEAD_END)


class ExternalConstraints(unittest.TestCase):
    """C06: predecessors, successors with larger IDs, and capacity."""

    def setUp(self):
        self.program = small_program()

    def test_selected_operation_cannot_precede_its_producer(self):
        # The multiply reads a and b. a is loaded at 3 and ready at 6, so no
        # cycle below 6 is offered. Nothing consumes the multiply, so this
        # isolates the predecessor constraint from any successor bound.
        program = open_ended_program()
        domain = se.Domain.from_record(
            record_of(
                program,
                selected=[2],
                time_domains={2: list(range(8))},
                address_domains={"c": [0]},
                fixed_times={0: 3, 1: 0},
                fixed_addresses={"a": 1, "b": 2},
                identifier="pred",
            )
        )
        state = se.State(domain)
        self.assertEqual(state.time_options(2), (6, 7))

    def test_external_successor_with_a_larger_id_bounds_the_choice(self):
        # Operation 3 stores c and is fixed at cycle 7. The multiply has
        # latency two, so it must issue at 5 or earlier even though its
        # consumer carries the larger identifier. Both loads are ready at 3.
        domain = se.Domain.from_record(
            record_of(
                self.program,
                selected=[2],
                time_domains={2: [1, 2, 3, 4, 5, 6, 7]},
                address_domains={"c": [0]},
                fixed_times={0: 0, 1: 0, 3: 7},
                fixed_addresses={"a": 1, "b": 2},
                identifier="succ",
            )
        )
        state = se.State(domain)
        self.assertEqual(state.time_options(2), (3, 4, 5))

    def test_engine_capacity_counts_fixed_operations(self):
        # Both consts use the load engine, whose limit is two. Place two fixed
        # loads in one cycle and the selected one may not join them.
        program = program_of(
            "cap",
            {"out": 1},
            [
                {"id": 0, "op": "const", "dest": "a", "value": 1},
                {"id": 1, "op": "const", "dest": "b", "value": 2},
                {"id": 2, "op": "const", "dest": "d", "value": 3},
                {"id": 3, "op": "add", "dest": "c", "args": ["a", "b"]},
                {"id": 4, "op": "store", "args": ["c"], "buffer": "out", "offset": 0},
            ],
        )
        domain = se.Domain.from_record(
            record_of(
                program,
                selected=[2],
                time_domains={2: [0, 1]},
                address_domains={"d": [0]},
                fixed_times={0: 0, 1: 0, 3: 2, 4: 3},
                fixed_addresses={"a": 1, "b": 2, "c": 3},
                identifier="capacity",
            )
        )
        state = se.State(domain)
        self.assertEqual(state.time_options(2), (1,))
        self.assertEqual(machine.ENGINE_LIMITS["load"], 2)


class InclusiveLifetimes(unittest.TestCase):
    """C07 and C08: inclusive endpoints, pending writes and moving readers."""

    def setUp(self):
        self.program = small_program()

    def test_equal_last_read_and_new_write_conflict(self):
        facts = dc.derive(self.program)
        # a and b are both written at 3 and both last read at 6.
        times = {0: 0, 1: 0, 2: 6, 3: 8}
        live = dc.lifetimes(facts, times)
        self.assertEqual(live["a"], (3, 6))
        self.assertEqual(live["b"], (3, 6))
        # Sharing one word while both are live is refused by our own predicate
        # and by the pinned validator alike.
        with self.assertRaises(dc.ContractError):
            dc.check_feasible(facts, times, {"a": 0, "b": 0, "c": 1})
        with self.assertRaises(machine.CompileError):
            machine.check_compilation(
                self.program, dc.compilation(facts, times, {"a": 0, "b": 0, "c": 1})
            )
        # c is written at 8, one cycle after a and b die at 6, so reusing a's
        # word for c is the adjacent non-overlap that must be accepted.
        dc.check_feasible(facts, times, {"a": 0, "b": 1, "c": 0})

    def test_adjacent_non_overlap_is_accepted(self):
        facts = dc.derive(self.program)
        times = {0: 0, 1: 0, 2: 6, 3: 8}
        # c is written at 8 and a dies at 6, so reuse of a's word is legal.
        dc.check_feasible(facts, times, {"a": 0, "b": 1, "c": 0})
        machine.check_compilation(
            self.program, dc.compilation(facts, times, {"a": 0, "b": 1, "c": 0})
        )

    def test_a_selected_reader_can_push_two_fixed_values_into_conflict(self):
        """C08: the fixed/fixed check runs after lifetimes are recomputed."""

        # a and b have separate consumers, so their live intervals can be made
        # disjoint and they can legally share one word. Operation 4 is a second
        # reader of a; moving it late stretches a's interval across b's.
        program = program_of(
            "extend",
            {"data": 8, "out": 4},
            [
                {"id": 0, "op": "load", "dest": "a", "buffer": "data", "offset": 0},
                {"id": 1, "op": "load", "dest": "b", "buffer": "data", "offset": 1},
                {"id": 2, "op": "store", "args": ["a"], "buffer": "out", "offset": 0},
                {"id": 3, "op": "store", "args": ["b"], "buffer": "out", "offset": 1},
                {"id": 4, "op": "store", "args": ["a"], "buffer": "out", "offset": 2},
            ],
        )
        # a is written at 3 and read at 4; b is written at 6 and read at 7.
        record = record_of(
            program,
            selected=[4],
            time_domains={4: [4, 8]},
            address_domains={},
            fixed_times={0: 0, 1: 3, 2: 4, 3: 7},
            fixed_addresses={"a": 0, "b": 0},
            identifier="extend",
        )
        domain = se.Domain.from_record(record)
        state = se.State(domain)
        state.times[4] = 4
        state.recompute_lifetimes()
        self.assertEqual(state.lifetimes["a"], (3, 4))
        self.assertEqual(state.lifetimes["b"], (6, 7))
        self.assertIsNone(state.fixed_address_conflict())

        state = se.State(domain)
        state.times[4] = 8
        state.recompute_lifetimes()
        self.assertEqual(state.lifetimes["a"], (3, 8))
        self.assertIsNotNone(state.fixed_address_conflict())

        # The decoder reports that as DEAD_END, before any COMPLETE result.
        plan = se.layout(domain, "structural_rank")
        statuses = {
            se.decode(domain, index, "structural_rank").status
            for index in range(1 << plan.width)
        }
        self.assertIn(se.DEAD_END, statuses)
        for index in range(1 << plan.width):
            result = se.decode(domain, index, "structural_rank")
            if result.status == se.COMPLETE:
                machine.check_compilation(program, result.compilation)


class VectorGeometry(unittest.TestCase):
    """C09: alignment, the 255 ceiling, overlap, holes and footprint."""

    def setUp(self):
        self.program = program_of(
            "geometry",
            {"data": 8, "out": 8},
            [
                {"id": 0, "op": "vload", "dest": "v", "buffer": "data", "offset": 0},
                {"id": 1, "op": "const", "dest": "s", "value": 3},
                {"id": 2, "op": "vstore", "args": ["v"], "buffer": "out", "offset": 0},
                {"id": 3, "op": "store", "args": ["s"], "buffer": "out", "offset": 0},
            ],
        )

    def record(self, vector_bases, scalar_bases):
        return record_of(
            self.program,
            selected=[0, 1],
            time_domains={0: [0], 1: [0]},
            address_domains={"v": vector_bases, "s": scalar_bases},
            fixed_times={2: 4, 3: 5},
            fixed_addresses={},
            identifier="geometry",
        )

    def test_vector_block_scaling_is_exact(self):
        domain = se.Domain.from_record(self.record([0, 8, 248], [16, 17]))
        plan = se.layout(domain, "vector_block")
        self.assertEqual(plan.field(("address", "v")).width, se.VECTOR_BLOCK_WIDTH)
        self.assertEqual(plan.field(("address", "s")).width, dc.ADDRESS_WIDTH)
        for base in (0, 8, 248):
            compilation = compile_from(self.program, {0: 0, 1: 0, 2: 4, 3: 5},
                                       {"v": base, "s": 16})
            index = se.encode(domain, compilation, "vector_block")
            block = plan.field(("address", "v")).read(index)
            self.assertEqual(block * machine.VLEN, base)

    def test_address_past_255_is_refused_by_the_domain(self):
        with self.assertRaises(se.DomainError):
            se.Domain.from_record(self.record([248, 256], [0]))

    def test_scalar_and_vector_overlap_is_never_complete(self):
        domain = se.Domain.from_record(self.record([0, 8], [0, 1, 8, 9]))
        plan = se.layout(domain, "structural_rank")
        for index in range(1 << plan.width):
            result = se.decode(domain, index, "structural_rank")
            if result.status != se.COMPLETE:
                continue
            # Agreement with the validator, footprint included.
            machine.check_compilation(self.program, result.compilation)
            self.assertEqual(
                result.scratch,
                machine.scratch_footprint(self.program, result.compilation),
            )

    def test_alignment_holes_count_towards_the_footprint(self):
        domain = se.Domain.from_record(self.record([8], [0]))
        result = se.decode(domain, 0, "structural_rank")
        self.assertEqual(result.status, se.COMPLETE)
        # The vector sits at 8..15 and the scalar at 0, so the footprint is 16
        # including the seven-word hole the scalar does not fill.
        self.assertEqual(result.scratch, 16)
        self.assertEqual(
            result.scratch, machine.scratch_footprint(self.program, result.compilation)
        )


class DomainEquivalence(unittest.TestCase):
    """C10: independent enumeration agrees with every codec on all fixtures."""

    def test_exhaustive_set_equality_and_inverse_on_every_fixture(self):
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(record, 65536)
            oracle = {entry["identity"] for entry in enumeration["feasible"]}
            with self.subTest(fixture=record["id"]):
                for codec in se.CODECS:
                    bits = se.layout(domain, codec).width
                    if bits <= 16:
                        found = {}
                        for index in range(1 << bits):
                            result = se.decode(domain, index, codec)
                            if result.status == se.COMPLETE:
                                identity = se.canonical_json(result.compilation)
                                self.assertNotIn(identity, found, "codec is not injective")
                                found[identity] = index
                        self.assertEqual(set(found), oracle, f"{record['id']}/{codec}")
                    for entry in enumeration["feasible"]:
                        compilation = json.loads(entry["identity"])
                        index = se.encode(domain, compilation, codec)
                        back = se.decode(domain, index, codec)
                        self.assertEqual(back.status, se.COMPLETE)
                        self.assertEqual(
                            se.canonical_json(back.compilation), entry["identity"]
                        )
                        self.assertEqual(
                            se.encode(domain, back.compilation, codec), index
                        )

    def test_origin_decodes_to_the_incumbent_under_rank_codecs(self):
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            expected = se.canonical_json(
                se.normalise_compilation(domain.facts, record["incumbent"])
            )
            with self.subTest(fixture=record["id"]):
                for codec in ("static_rank", "structural_rank"):
                    result = se.decode(domain, 0, codec)
                    self.assertEqual(result.status, se.COMPLETE)
                    self.assertEqual(se.canonical_json(result.compilation), expected)

    def test_a_target_excluding_the_incumbent_is_a_dead_end_not_a_discrepancy(self):
        record = dict(FIXTURES[0])
        record["target"] = [1, 1]
        record["id"] = "impossible_target"
        domain = se.Domain.from_record(record)
        result = se.decode(domain, 0, "structural_rank")
        self.assertEqual(result.status, se.DEAD_END)
        self.assertIn("target", result.reason)


class CanonicalObject(unittest.TestCase):
    """C30 and C12: normalisation, exact operation sets, and defects."""

    def setUp(self):
        self.program = small_program()
        self.facts = dc.derive(self.program)

    def test_trailing_empty_bundles_are_removed_and_internal_ones_kept(self):
        compiled = compile_from(self.program, {0: 0, 1: 0, 2: 6, 3: 8}, {"a": 0, "b": 1, "c": 2})
        compiled["bundles"].append({})
        compiled["bundles"].append({"scalar": []})
        normalised = se.normalise_compilation(self.facts, compiled)
        self.assertEqual(len(normalised["bundles"]), 9)
        self.assertEqual(normalised["bundles"][1], {})
        self.assertEqual(normalised["bundles"][-1], {"store": [3]})

    def test_duplicate_or_missing_operations_are_errors(self):
        compiled = compile_from(self.program, {0: 0, 1: 0, 2: 6, 3: 8}, {"a": 0, "b": 1, "c": 2})
        duplicated = json.loads(json.dumps(compiled))
        duplicated["bundles"][0]["load"].append(0)
        with self.assertRaises(se.DomainError):
            se.normalise_compilation(self.facts, duplicated)
        missing = json.loads(json.dumps(compiled))
        missing["bundles"][0]["load"] = [0]
        with self.assertRaises(se.DomainError):
            se.normalise_compilation(self.facts, missing)

    def test_operations_are_sorted_within_an_engine(self):
        compiled = compile_from(self.program, {0: 0, 1: 0, 2: 6, 3: 8}, {"a": 0, "b": 1, "c": 2})
        compiled["bundles"][0]["load"] = [1, 0]
        normalised = se.normalise_compilation(self.facts, compiled)
        self.assertEqual(normalised["bundles"][0]["load"], [0, 1])

    def test_unknown_engine_is_refused(self):
        compiled = compile_from(self.program, {0: 0, 1: 0, 2: 6, 3: 8}, {"a": 0, "b": 1, "c": 2})
        compiled["bundles"][0]["lane"] = []
        with self.assertRaises(se.DomainError):
            se.normalise_compilation(self.facts, compiled)

    def test_encode_refuses_a_compilation_outside_the_domain(self):
        domain = se.Domain.from_record(
            record_of(
                self.program,
                selected=[0],
                time_domains={0: [0, 1]},
                address_domains={"a": [0, 1]},
                fixed_times={1: 0, 2: 6, 3: 8},
                fixed_addresses={"b": 2, "c": 3},
                identifier="outside",
            )
        )
        outside = compile_from(self.program, {0: 3, 1: 0, 2: 6, 3: 8},
                               {"a": 0, "b": 2, "c": 3})
        with self.assertRaises(se.DomainError):
            se.encode(domain, outside, "structural_rank")

    def test_a_fully_decoded_illegal_compilation_raises_a_defect(self):
        """C12: it is retained and it fails; it is never a DEAD_END."""

        domain = se.Domain.from_record(
            record_of(
                self.program,
                selected=[0],
                time_domains={0: [0, 1]},
                address_domains={"a": [0, 1]},
                fixed_times={1: 0, 2: 6, 3: 8},
                fixed_addresses={"b": 2, "c": 3},
                identifier="defect",
            )
        )
        original = se.State.address_options

        def blind(self, name):
            # A deliberately broken option list that offers an address the
            # validator will reject, standing in for a codec regression.
            return tuple(self.domain.ordered_domain(("address", name)))

        se.State.address_options = blind
        try:
            # b is fixed at word 2 and is live across a's whole life, so
            # offering a that same word produces a complete but illegal object.
            broken = se.Domain.from_record(
                record_of(
                    self.program,
                    selected=[0],
                    time_domains={0: [0]},
                    address_domains={"a": [2]},
                    fixed_times={1: 0, 2: 6, 3: 8},
                    fixed_addresses={"b": 2, "c": 3},
                    identifier="defect",
                )
            )
            with self.assertRaises(se.CodecDefect) as caught:
                se.decode(broken, 0, "structural_rank")
            self.assertIn("domain_id", caught.exception.evidence)
            self.assertIn("validator_message", caught.exception.evidence)
        finally:
            se.State.address_options = original

        # The unmutated control decodes cleanly.
        self.assertEqual(se.decode(domain, 0, "structural_rank").status, se.COMPLETE)


class DecodeResultShape(unittest.TestCase):
    """Every result carries decisions, counters, a reason and a trace reference."""

    def test_every_status_carries_its_accounting(self):
        record = FIXTURES[0]
        domain = se.Domain.from_record(record)
        bits = se.layout(domain, "structural_rank").width
        seen = set()
        for index in range(1 << bits):
            result = se.decode(domain, index, "structural_rank")
            seen.add(result.status)
            row = result.to_row()
            self.assertEqual(row["index"], str(index))
            self.assertTrue(row["reason"])
            self.assertTrue(row["trace_reference"])
            self.assertIn("option_constructions", row["counters"])
            if result.status == se.COMPLETE:
                self.assertIsNotNone(row["compilation_sha256"])
                self.assertEqual(row["canonical_index"], str(index))
            else:
                self.assertIsNone(row["compilation_sha256"])
                self.assertIsNone(row["cycles"])
        self.assertIn(se.COMPLETE, seen)

    def test_interruption_is_an_execution_status(self):
        domain = se.Domain.from_record(FIXTURES[1])
        budget = si.Budget(seconds=1.0, max_cover=4, max_visited=1, max_records=1)
        meter = budget.start()
        result = se.decode(domain, 0, "structural_rank", meter=meter)
        self.assertEqual(result.status, se.INTERRUPTED)
        self.assertIsNone(result.compilation)


if __name__ == "__main__":
    unittest.main()
