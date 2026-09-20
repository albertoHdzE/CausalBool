"""T03 and T06: machine-boundary cases, derived facts, and the corpus.

The oracle throughout is the unchanged reference: ``machine.check_compilation``
for legality, ``machine.check_case`` and ``machine.run_reference`` for the final
memory image. Every boundary fixture asserts that our own predicates and the
frozen validator reach the *same* verdict, so a divergence in either direction
fails the test.
"""

from __future__ import annotations

import copy
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / ".reference") not in sys.path:
    sys.path.insert(0, str(ROOT / ".reference"))

import machine
import direct_contract as dc
from tests_direct import generate_programs as gp


# --------------------------------------------------------------------------
# Fixtures and oracles
# --------------------------------------------------------------------------


def program(name, buffers, operations, cases):
    built = {
        "name": name,
        "buffers": dict(buffers),
        "operations": [dict(operation, id=index) for index, operation in enumerate(operations)],
        "cases": cases,
    }
    machine.validate_program(built)
    return built


def unique_addresses(facts):
    """Private, vectors-first allocation. No baseline compiler is called."""

    addresses = {}
    cursor = 0
    for name in facts.value_names:
        if facts.width[name] == machine.VLEN:
            cursor = machine.align_up(cursor, machine.VLEN)
            addresses[name] = cursor
            cursor += machine.VLEN
    for name in facts.value_names:
        if facts.width[name] != machine.VLEN:
            addresses[name] = cursor
            cursor += 1
    return addresses


def sequential_times(facts):
    """One operation per cycle, at or after every predecessor's bound."""

    times = {}
    cycle = 0
    for op_id in range(facts.count):
        earliest = cycle
        for predecessor, lag in facts.predecessors[op_id].items():
            earliest = max(earliest, times[predecessor] + lag)
        times[op_id] = earliest
        cycle = earliest + 1
    return times


def peak_live_width(facts, times):
    live = dc.lifetimes(facts, times)
    if not live:
        return 0
    span = max(end for _, end in live.values())
    best = 0
    for cycle in range(span + 1):
        total = sum(
            facts.width[name]
            for name, (start, end) in live.items()
            if start <= cycle <= end
        )
        best = max(best, total)
    return best


class ContractCase(unittest.TestCase):
    def verdicts(self, source, times, addresses):
        """Our checker and the reference validator, on the same candidate."""

        facts = dc.derive(source)
        try:
            dc.check_feasible(facts, times, addresses)
            ours = True
        except dc.ContractError:
            ours = False
        try:
            compiled = dc.compilation(facts, times, addresses)
            machine.check_compilation(source, compiled)
            reference = True
        except (machine.CompileError, dc.ContractError):
            reference = False
        self.assertEqual(
            ours,
            reference,
            f"our checker said {ours} and the reference said {reference}",
        )
        return ours


# --------------------------------------------------------------------------


class LatencyBoundaryTests(ContractCase):
    SOURCE = program(
        "latency_boundary",
        {"out": 1},
        [
            {"op": "const", "dest": "a", "value": 5},
            {"op": "mul", "dest": "b", "args": ["a", "a"]},
            {"op": "store", "args": ["b"], "buffer": "out", "offset": 0},
        ],
        [{"out": [0]}],
    )

    def test_consumer_at_the_ready_cycle_is_legal(self):
        # const has latency one, so a consumer at cycle one is exactly legal.
        addresses = unique_addresses(dc.derive(self.SOURCE))
        self.assertTrue(self.verdicts(self.SOURCE, {0: 0, 1: 1, 2: 3}, addresses))

    def test_one_cycle_earlier_is_illegal(self):
        addresses = unique_addresses(dc.derive(self.SOURCE))
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 0, 2: 3}, addresses))

    def test_multiply_latency_is_counted_exactly_once(self):
        addresses = unique_addresses(dc.derive(self.SOURCE))
        # mul has latency two: its consumer is legal at cycle three, not two.
        self.assertTrue(self.verdicts(self.SOURCE, {0: 0, 1: 1, 2: 3}, addresses))
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 1, 2: 2}, addresses))


class EngineCapacityTests(ContractCase):
    def build(self, count):
        operations = [{"op": "const", "dest": "c%d" % i, "value": i} for i in range(count)]
        operations.append({"op": "store", "args": ["c0"], "buffer": "out", "offset": 0})
        return program("capacity_%d" % count, {"out": 1}, operations, [{"out": [0]}])

    def test_two_slot_engine_permits_two_issues_but_not_three(self):
        source = self.build(3)
        facts = dc.derive(source)
        addresses = unique_addresses(facts)
        # The load engine has two slots per cycle.
        self.assertTrue(self.verdicts(source, {0: 0, 1: 0, 2: 1, 3: 2}, addresses))
        self.assertFalse(self.verdicts(source, {0: 0, 1: 0, 2: 0, 3: 2}, addresses))

    def test_capacity_limits_issues_not_in_flight_duration(self):
        # A vmul occupies the vector engine for three cycles of latency, but it
        # reserves only its issue slot. Independent vector work may issue next.
        source = program(
            "in_flight",
            {"data": 8, "out": 8},
            [
                {"op": "vload", "dest": "x", "buffer": "data", "offset": 0},
                {"op": "vmul", "dest": "y", "args": ["x", "x"]},
                {"op": "vadd", "dest": "z", "args": ["x", "x"]},
                {"op": "vstore", "args": ["y"], "buffer": "out", "offset": 0},
                {"op": "vstore", "args": ["z"], "buffer": "out", "offset": 0},
            ],
            [{"data": [1, 2, 3, 4, 5, 6, 7, 8], "out": [0] * 8}],
        )
        facts = dc.derive(source)
        addresses = unique_addresses(facts)
        # vmul issues at cycle four and is in flight until seven; vadd issues at
        # five regardless. The two stores overlap, so they need distinct cycles.
        self.assertTrue(self.verdicts(source, {0: 0, 1: 4, 2: 5, 3: 7, 4: 8}, addresses))


class MemoryOrderTests(ContractCase):
    SOURCE = program(
        "memory_order",
        {"data": 16},
        [
            {"op": "load", "dest": "a", "buffer": "data", "offset": 0},
            {"op": "store", "args": ["a"], "buffer": "data", "offset": 0},
            {"op": "load", "dest": "b", "buffer": "data", "offset": 0},
            {"op": "load", "dest": "c", "buffer": "data", "offset": 8},
            {"op": "store", "args": ["c"], "buffer": "data", "offset": 8},
        ],
        [{"data": list(range(16))}],
    )

    def test_overlapping_store_must_issue_in_a_later_cycle(self):
        facts = dc.derive(self.SOURCE)
        addresses = unique_addresses(facts)
        # The store engine has a single slot, so the two stores take cycles
        # three and four; both loads may share cycle zero.
        self.assertTrue(self.verdicts(self.SOURCE, {0: 0, 1: 3, 2: 4, 3: 0, 4: 4}, addresses))
        # Two stores in one cycle exceed that single slot.
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 3, 2: 4, 3: 0, 4: 3}, addresses))
        # The dependent store in the same cycle as its load is illegal.
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 0, 2: 4, 3: 0, 4: 4}, addresses))
        # The later load may not share the overlapping store's cycle either.
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 3, 2: 3, 3: 0, 4: 4}, addresses))

    def test_disjoint_ranges_and_two_loads_may_share_a_cycle(self):
        facts = dc.derive(self.SOURCE)
        # Loads at data[0] and data[8] are disjoint and unordered.
        self.assertEqual(facts.memory_predecessors[3], ())
        # Two loads of the same word may reorder; only a store orders them.
        source = program(
            "two_loads",
            {"data": 8},
            [
                {"op": "load", "dest": "a", "buffer": "data", "offset": 0},
                {"op": "load", "dest": "b", "buffer": "data", "offset": 0},
                {"op": "store", "args": ["a"], "buffer": "data", "offset": 4},
            ],
            [{"data": list(range(8))}],
        )
        facts = dc.derive(source)
        self.assertEqual(facts.memory_predecessors[1], ())
        self.assertTrue(
            self.verdicts(source, {0: 0, 1: 0, 2: 3}, unique_addresses(facts))
        )

    def test_partial_vector_overlap_is_ordered(self):
        source = program(
            "partial_overlap",
            {"data": 16},
            [
                {"op": "vload", "dest": "v", "buffer": "data", "offset": 0},
                {"op": "store", "args": ["s"], "buffer": "data", "offset": 4}
                if False
                else {"op": "const", "dest": "s", "value": 1},
                {"op": "store", "args": ["s"], "buffer": "data", "offset": 4},
                {"op": "vstore", "args": ["v"], "buffer": "data", "offset": 8},
            ],
            [{"data": list(range(16))}],
        )
        facts = dc.derive(source)
        # The scalar store at word four lies inside the vector load's range.
        self.assertIn(0, facts.memory_predecessors[2])
        # The vector store at words eight to fifteen is disjoint from it.
        self.assertNotIn(2, facts.memory_predecessors[3])


class ScratchReuseTests(ContractCase):
    SOURCE = program(
        "reuse",
        {"out": 2},
        [
            {"op": "const", "dest": "a", "value": 1},
            {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
            {"op": "const", "dest": "b", "value": 2},
            {"op": "store", "args": ["b"], "buffer": "out", "offset": 1},
        ],
        [{"out": [0, 0]}],
    )

    def test_equal_final_read_and_new_write_forbids_reuse(self):
        # a is read at cycle two; b writing at cycle two may not take its word.
        shared = {"a": 0, "b": 0}
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 2, 2: 1, 3: 3}, shared))

    def test_a_write_one_cycle_later_permits_reuse(self):
        shared = {"a": 0, "b": 0}
        self.assertTrue(self.verdicts(self.SOURCE, {0: 0, 1: 2, 2: 2, 3: 4}, shared))

    def test_two_writes_in_the_same_cycle_may_not_overlap(self):
        shared = {"a": 0, "b": 0}
        # Both consts write at cycle one; their words must differ.
        self.assertFalse(self.verdicts(self.SOURCE, {0: 0, 1: 2, 2: 0, 3: 3}, shared))
        self.assertTrue(self.verdicts(self.SOURCE, {0: 0, 1: 2, 2: 0, 3: 3}, {"a": 0, "b": 1}))

    def test_unused_result_still_occupies_its_write_cycle(self):
        source = program(
            "unused",
            {"out": 1},
            [
                {"op": "const", "dest": "a", "value": 1},
                {"op": "const", "dest": "dead", "value": 2},
                {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
            ],
            [{"out": [0]}],
        )
        facts = dc.derive(source)
        self.assertEqual(facts.consumers["dead"], ())
        live = dc.lifetimes(facts, {0: 0, 1: 0, 2: 1})
        self.assertEqual(live["dead"], (1, 1))
        # Sharing a word with a value that is live at cycle one is illegal.
        self.assertFalse(self.verdicts(source, {0: 0, 1: 0, 2: 1}, {"a": 0, "dead": 0}))
        self.assertTrue(self.verdicts(source, {0: 0, 1: 0, 2: 1}, {"a": 0, "dead": 1}))

    def test_value_written_after_the_last_emitted_bundle(self):
        source = program(
            "late_write",
            {"data": 8, "out": 8},
            [
                {"op": "vload", "dest": "x", "buffer": "data", "offset": 0},
                {"op": "vmul", "dest": "d1", "args": ["x", "x"]},
                {"op": "vmul", "dest": "d2", "args": ["x", "x"]},
                {"op": "vstore", "args": ["x"], "buffer": "out", "offset": 0},
            ],
            [{"data": [1] * 8, "out": [0] * 8}],
        )
        facts = dc.derive(source)
        times = {0: 0, 1: 4, 2: 4, 3: 4}
        live = dc.lifetimes(facts, times)
        compiled = dc.compilation(facts, times, {"x": 0, "d1": 8, "d2": 16})
        # The last emitted bundle is cycle four, yet both unused multiplies
        # write at cycle seven, past the end of the schedule.
        self.assertEqual(len(compiled["bundles"]), 5)
        self.assertEqual(live["d1"], (7, 7))
        self.assertEqual(live["d2"], (7, 7))
        self.assertEqual(live["x"], (4, 4))
        self.assertTrue(self.verdicts(source, times, {"x": 0, "d1": 8, "d2": 16}))
        # Those words are reserved even though no bundle ever commits them,
        # so two results writing at cycle seven may not share an address.
        self.assertFalse(self.verdicts(source, times, {"x": 0, "d1": 8, "d2": 8}))
        # A value whose interval has already closed may be overwritten.
        self.assertTrue(self.verdicts(source, times, {"x": 0, "d1": 0, "d2": 8}))

    def test_several_consumers_extend_the_interval_to_the_last(self):
        source = program(
            "many_consumers",
            {"out": 3},
            [
                {"op": "const", "dest": "a", "value": 1},
                {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
                {"op": "store", "args": ["a"], "buffer": "out", "offset": 1},
                {"op": "store", "args": ["a"], "buffer": "out", "offset": 2},
            ],
            [{"out": [0, 0, 0]}],
        )
        facts = dc.derive(source)
        self.assertEqual(facts.consumers["a"], (1, 2, 3))
        self.assertEqual(dc.lifetimes(facts, {0: 0, 1: 1, 2: 5, 3: 3})["a"], (1, 5))

    def test_moving_a_consumer_changes_an_external_lifetime(self):
        source = program(
            "external_lifetime",
            {"out": 2},
            [
                {"op": "const", "dest": "a", "value": 1},
                {"op": "const", "dest": "b", "value": 2},
                {"op": "add", "dest": "c", "args": ["a", "b"]},
                {"op": "store", "args": ["c"], "buffer": "out", "offset": 0},
            ],
            [{"out": [0, 0]}],
        )
        facts = dc.derive(source)
        near = dc.lifetimes(facts, {0: 0, 1: 0, 2: 1, 3: 2})
        far = dc.lifetimes(facts, {0: 0, 1: 0, 2: 6, 3: 7})
        self.assertEqual(near["a"], (1, 1))
        self.assertEqual(far["a"], (1, 6))


class AddressBoundaryTests(ContractCase):
    def test_vector_alignment_exact_end_address_and_holes(self):
        source = program(
            "addresses",
            {"data": 8, "out": 8},
            [
                {"op": "vload", "dest": "v", "buffer": "data", "offset": 0},
                {"op": "vstore", "args": ["v"], "buffer": "out", "offset": 0},
            ],
            [{"data": [1] * 8, "out": [0] * 8}],
        )
        facts = dc.derive(source)
        times = {0: 0, 1: 4}
        # A vector ending exactly at word 256 is legal.
        self.assertTrue(self.verdicts(source, times, {"v": 248}))
        # One word further is past the scratchpad.
        self.assertFalse(self.verdicts(source, times, {"v": 249}))
        # Misalignment is rejected even when the range fits.
        self.assertFalse(self.verdicts(source, times, {"v": 4}))
        # A hole below the vector still counts towards the footprint.
        self.assertEqual(dc.footprint(facts, {"v": 8}), 16)
        self.assertEqual(dc.footprint(facts, {"v": 248}), 256)

    def test_scalar_at_the_last_word(self):
        source = program(
            "last_word",
            {"out": 1},
            [
                {"op": "const", "dest": "a", "value": 1},
                {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
            ],
            [{"out": [0]}],
        )
        self.assertTrue(self.verdicts(source, {0: 0, 1: 1}, {"a": 255}))
        self.assertFalse(self.verdicts(source, {0: 0, 1: 1}, {"a": 256}))

    def test_partial_overlap_of_a_scalar_inside_a_vector_range(self):
        source = program(
            "partial_range",
            {"data": 8, "out": 8},
            [
                {"op": "vload", "dest": "v", "buffer": "data", "offset": 0},
                {"op": "const", "dest": "s", "value": 3},
                {"op": "vstore", "args": ["v"], "buffer": "out", "offset": 0},
                {"op": "store", "args": ["s"], "buffer": "out", "offset": 0},
            ],
            [{"data": [1] * 8, "out": [0] * 8}],
        )
        times = {0: 0, 1: 0, 2: 4, 3: 5}
        # The scalar sits inside the vector's eight words while both are live.
        self.assertFalse(self.verdicts(source, times, {"v": 0, "s": 5}))
        self.assertTrue(self.verdicts(source, times, {"v": 0, "s": 8}))


class SemanticsTests(unittest.TestCase):
    """Every opcode, against the reference interpreter and final memory image."""

    def build_every_opcode(self):
        operations = [
            {"op": "const", "dest": "one", "value": 1},
            {"op": "const", "dest": "big", "value": 0xFFFFFFFF},
            {"op": "const", "dest": "shift", "value": 33},
            {"op": "load", "dest": "l0", "buffer": "data", "offset": 0},
            {"op": "vload", "dest": "vx", "buffer": "data", "offset": 0},
            {"op": "vload", "dest": "vy", "buffer": "data", "offset": 8},
            {"op": "add", "dest": "a_add", "args": ["big", "one"]},
            {"op": "sub", "dest": "a_sub", "args": ["one", "big"]},
            {"op": "mul", "dest": "a_mul", "args": ["big", "big"]},
            {"op": "xor", "dest": "a_xor", "args": ["big", "l0"]},
            {"op": "and", "dest": "a_and", "args": ["big", "l0"]},
            {"op": "or", "dest": "a_or", "args": ["one", "l0"]},
            {"op": "shl", "dest": "a_shl", "args": ["one", "shift"]},
            {"op": "shr", "dest": "a_shr", "args": ["big", "shift"]},
            {"op": "eq", "dest": "a_eq", "args": ["big", "l0"]},
            {"op": "lt", "dest": "a_lt", "args": ["big", "l0"]},
            {"op": "select", "dest": "a_sel", "args": ["a_lt", "one", "big"]},
            {"op": "splat", "dest": "vs", "args": ["a_sel"]},
            {"op": "vadd", "dest": "v_add", "args": ["vx", "vy"]},
            {"op": "vsub", "dest": "v_sub", "args": ["vx", "vy"]},
            {"op": "vmul", "dest": "v_mul", "args": ["vx", "vy"]},
            {"op": "vxor", "dest": "v_xor", "args": ["vx", "vs"]},
            {"op": "vand", "dest": "v_and", "args": ["vx", "vs"]},
            {"op": "vor", "dest": "v_or", "args": ["vx", "vs"]},
            {"op": "vshl", "dest": "v_shl", "args": ["vx", "vs"]},
            {"op": "vshr", "dest": "v_shr", "args": ["vx", "vs"]},
            {"op": "vselect", "dest": "v_sel", "args": ["v_xor", "v_add", "v_sub"]},
            {"op": "store", "args": ["a_add"], "buffer": "out", "offset": 0},
            {"op": "store", "args": ["a_sub"], "buffer": "out", "offset": 1},
            {"op": "store", "args": ["a_mul"], "buffer": "out", "offset": 2},
            {"op": "store", "args": ["a_shl"], "buffer": "out", "offset": 3},
            {"op": "store", "args": ["a_shr"], "buffer": "out", "offset": 4},
            {"op": "store", "args": ["a_eq"], "buffer": "out", "offset": 5},
            {"op": "store", "args": ["a_lt"], "buffer": "out", "offset": 6},
            {"op": "store", "args": ["a_and"], "buffer": "out", "offset": 7},
            {"op": "store", "args": ["a_or"], "buffer": "out", "offset": 8},
            {"op": "vstore", "args": ["v_sel"], "buffer": "wide", "offset": 0},
            {"op": "vstore", "args": ["v_mul"], "buffer": "wide", "offset": 8},
            {"op": "vstore", "args": ["v_and"], "buffer": "wide", "offset": 16},
            {"op": "vstore", "args": ["v_or"], "buffer": "wide", "offset": 24},
            {"op": "vstore", "args": ["v_shl"], "buffer": "wide", "offset": 32},
            {"op": "vstore", "args": ["v_shr"], "buffer": "wide", "offset": 40},
        ]
        cases = [
            {
                "data": [0xFFFFFFFF, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16],
                "out": [0] * 9,
                "wide": [0] * 48,
            },
            {
                "data": [0, 1, 0x80000000, 0x7FFFFFFF, 31, 32, 33, 1, 2, 3, 4, 5, 6, 7, 8, 9],
                "out": [0] * 9,
                "wide": [0] * 48,
            },
        ]
        return program("every_opcode", {"data": 16, "out": 9, "wide": 48}, operations, cases)

    def test_every_opcode_reproduces_the_whole_final_memory_image(self):
        source = self.build_every_opcode()
        covered = {operation["op"] for operation in source["operations"]}
        self.assertEqual(covered, set(machine.OP_SPECS), "every opcode must appear")

        facts = dc.derive(source)
        times = sequential_times(facts)
        compiled = dc.compilation(facts, times, unique_addresses(facts))
        machine.check_compilation(source, compiled)
        for case in source["cases"]:
            expected = machine.run_reference(source, case)
            actual = machine.run_compilation(source, compiled, case)
            # The entire image, not one chosen output buffer.
            self.assertEqual(actual, expected)

    def test_unsigned_comparison_shift_masking_and_wraparound(self):
        source = self.build_every_opcode()
        case = source["cases"][0]
        memory = machine.run_reference(source, case)
        # 0xFFFFFFFF + 1 wraps to zero.
        self.assertEqual(memory["out"][0], 0)
        # 1 - 0xFFFFFFFF wraps to 2.
        self.assertEqual(memory["out"][1], 2)
        # Shift counts use their low five bits, so 33 shifts by one.
        self.assertEqual(memory["out"][3], 2)
        self.assertEqual(memory["out"][4], 0x7FFFFFFF)
        # lt is unsigned: 0xFFFFFFFF is not below itself.
        self.assertEqual(memory["out"][5], 1)
        self.assertEqual(memory["out"][6], 0)


class DerivedFactsTests(unittest.TestCase):
    def test_facts_do_not_modify_the_input_program(self):
        source = gp.additional_program(1000)
        before = copy.deepcopy(source)
        facts = dc.derive(source)
        dc.lifetimes(facts, sequential_times(facts))
        dc.compilation(facts, sequential_times(facts), unique_addresses(facts))
        self.assertEqual(source, before)

    def test_producers_consumers_and_predecessors_against_explicit_scans(self):
        source = gp.additional_program(1003)
        facts = dc.derive(source)
        operations = source["operations"]
        for operation in operations:
            if "dest" in operation:
                self.assertEqual(facts.producers[operation["dest"]], operation["id"])
                expected = tuple(
                    other["id"]
                    for other in operations
                    if operation["dest"] in other.get("args", [])
                )
                self.assertEqual(facts.consumers[operation["dest"]], expected)
        for operation in operations:
            expected = {}
            for arg in operation.get("args", []):
                producer = facts.producers[arg]
                lag = machine.OP_SPECS[operations[producer]["op"]]["latency"]
                expected[producer] = max(expected.get(producer, 0), lag)
            for predecessor in machine.memory_predecessors(source, operation["id"]):
                expected[predecessor] = max(expected.get(predecessor, 0), 1)
            self.assertEqual(facts.predecessors[operation["id"]], expected)

    def test_horizon_is_the_sum_of_latencies_and_dominates_every_prefix(self):
        for seed in (1000, 1017, 1042):
            facts = dc.derive(gp.additional_program(seed))
            self.assertEqual(
                facts.horizon,
                sum(machine.OP_SPECS[op["op"]]["latency"] for op in facts.operations),
            )
            previous = -1
            for op_id in range(facts.count):
                current = facts.prefix_horizon(op_id)
                # Every latency is positive, so the prefix horizon is strictly
                # increasing; this is what section 5.2's argument relies on.
                self.assertGreater(current, previous)
                previous = current
                self.assertLess(current, facts.horizon)

    def test_lower_bounds_never_exceed_an_achievable_schedule(self):
        for seed in (1000, 1005, 1023, 1064):
            source = gp.additional_program(seed)
            facts = dc.derive(source)
            times = sequential_times(facts)
            compiled = dc.compilation(facts, times, unique_addresses(facts))
            machine.check_compilation(source, compiled)
            self.assertLessEqual(facts.cycle_lower_bound(), len(compiled["bundles"]))
            self.assertLessEqual(
                facts.memory_lower_bound(),
                machine.scratch_footprint(source, compiled),
            )
            self.assertLessEqual(facts.unique_allocation_width(), machine.SCRATCH_WORDS)

    def test_time_width_encodes_the_horizon(self):
        self.assertEqual(dc.time_width(1), 1)
        self.assertEqual(dc.time_width(2), 1)
        self.assertEqual(dc.time_width(3), 2)
        self.assertEqual(dc.time_width(256), 8)
        self.assertEqual(dc.time_width(257), 9)
        with self.assertRaises(dc.ContractError):
            dc.time_width(0)

    def test_derived_facts_agree_elementwise_with_the_frozen_classical_helpers(self):
        """Measured drift between the two declared owners of these quantities.

        ``common.py`` is pinned by hash and barred from the production path, so
        the duplication cannot be collapsed. It can be measured, and it must be
        zero.
        """

        import common

        for seed in (1000, 1011, 1029, 1077):
            source = gp.additional_program(seed)
            facts = dc.derive(source)
            times = sequential_times(facts)
            self.assertEqual(
                [dict(entry) for entry in facts.predecessors], common.dependencies(source)
            )
            self.assertEqual(facts.width, common.widths(source))
            expected = {
                name: list(interval)
                for name, interval in dc.lifetimes(facts, times).items()
            }
            self.assertEqual(expected, common.lifetimes(source, times))
            self.assertEqual(
                dc.assemble_bundles(facts, times), common.bundles_for(source, times)
            )


class CorpusTests(unittest.TestCase):
    """T06: the acceptance corpus, its size, validity, and stated properties."""

    @classmethod
    def setUpClass(cls):
        cls.manifest = gp.corpus_manifest()

    def test_corpus_holds_the_expected_one_hundred_and_forty_two_programs(self):
        self.assertEqual(self.manifest["size"], 142)
        self.assertEqual(
            self.manifest["groups"],
            {"public": 8, "regression": 30, "additional": 100, "stress": 4},
        )

    def test_every_program_is_valid_and_fits_the_starter_allocation(self):
        for entry in self.manifest["programs"]:
            self.assertTrue(entry["reference_valid"], entry["name"])
            self.assertTrue(entry["starter_fits"], entry["name"])
            self.assertGreaterEqual(entry["cases"], 1)
            self.assertLessEqual(entry["serial_scratch"], machine.SCRATCH_WORDS)

    def test_additional_programs_cover_every_family_and_size(self):
        additional = [e for e in self.manifest["programs"] if e["group"] == "additional"]
        self.assertEqual(len(additional), 100)
        for entry in additional:
            seed = entry["seed"]
            self.assertEqual(entry["family"], gp.FAMILIES[seed % 5])
            self.assertGreaterEqual(entry["operations"], gp.SIZES[seed % 4])
            self.assertEqual(entry["cases"], 2)
        self.assertEqual(
            sorted({entry["family"] for entry in additional}), sorted(gp.FAMILIES)
        )

    def test_generation_is_deterministic(self):
        self.assertEqual(
            gp.program_digest(gp.additional_program(1042)),
            gp.program_digest(gp.additional_program(1042)),
        )
        self.assertNotEqual(
            gp.program_digest(gp.additional_program(1042)),
            gp.program_digest(gp.additional_program(1043)),
        )

    def test_stress_fixtures_reach_their_intended_pressure(self):
        expected = {
            "stress_live_scalars": 256,
            "stress_live_vectors": 256,
            "stress_mixed_pressure": 256,
        }
        for source in gp.stress_programs():
            facts = dc.derive(source)
            times = sequential_times(facts)
            if source["name"] in expected:
                # Consumers run in reverse creation order, so every result is
                # still live when the first consumer issues.
                self.assertEqual(
                    peak_live_width(facts, times), expected[source["name"]], source["name"]
                )
            if source["name"] == "stress_memory_chain":
                ordered = sum(1 for preds in facts.memory_predecessors if preds)
                self.assertGreaterEqual(ordered, 64)
                self.assertLessEqual(peak_live_width(facts, times), 8)


if __name__ == "__main__":
    unittest.main()
