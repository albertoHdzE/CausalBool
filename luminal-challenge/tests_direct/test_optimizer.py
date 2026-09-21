"""T05: optimiser behaviour.

The oracle for feasibility is the frozen machine plus the explicit target
bounds. Where a distinction is claimed — that a joint change achieves what a
schedule-only or address-only change cannot — it is established by exhausting
the alternatives, not by assertion.
"""

from __future__ import annotations

import itertools
import math
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
import direct_optimizer as do
import schema_index as si
from tests_direct import generate_programs as gp
from tests_direct.test_contract import program
from tests_direct.test_constraints import independent_domains, machine_feasible


JOINT_NEEDED = program(
    "joint_needed",
    {"out": 2},
    [
        {"op": "const", "dest": "a", "value": 1},
        {"op": "const", "dest": "b", "value": 2},
        {"op": "store", "args": ["a"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["b"], "buffer": "out", "offset": 1},
    ],
    [{"out": [0, 0]}],
)

# A frozen program for which the optimiser accepts a witness that spends a
# cycle to buy scratch: the bootstrap reaches 6 cycles by 24 words, and the
# accepted joint witness reaches 7 by 16. Cycles worsen, the product improves
# from 144 to 112, and the official score rises. Discovered by scanning
# generated programs, then frozen literally here so that it does not depend on
# the generator. It is deliberately NOT added to the 142-program corpus, whose
# membership is a declared acceptance number. Case values are simple and
# deterministic; they cannot affect compilation, which is itself tested.
CYCLE_FOR_MEMORY_TRADE = program(
    "cycle_for_memory_trade",
    {"data": 32, "out": 32},
    [
        {"op": "const", "dest": "v0", "value": 2130979992},
        {"op": "vload", "dest": "v1", "buffer": "out", "offset": 24},
        {"op": "vshl", "dest": "v2", "args": ["v1", "v1"]},
        {"op": "vmul", "dest": "v3", "args": ["v2", "v2"]},
        {"op": "and", "dest": "v4", "args": ["v0", "v0"]},
        {"op": "or", "dest": "v5", "args": ["v4", "v4"]},
        {"op": "vshl", "dest": "v6", "args": ["v1", "v1"]},
        {"op": "vshl", "dest": "v7", "args": ["v1", "v6"]},
        {"op": "store", "args": ["v5"], "buffer": "out", "offset": 2},
        {"op": "vstore", "args": ["v1"], "buffer": "out", "offset": 21},
    ],
    [
        {"data": [i * 7 + 1 for i in range(32)], "out": [i * 3 + 2 for i in range(32)]},
        {"data": [0xFFFFFFFF - i for i in range(32)], "out": [i for i in range(32)]},
    ],
)

MOVING_CONSUMER = program(
    "moving_consumer",
    {"out": 2},
    [
        {"op": "const", "dest": "x", "value": 1},
        {"op": "add", "dest": "y", "args": ["x", "x"]},
        {"op": "store", "args": ["y"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["x"], "buffer": "out", "offset": 1},
    ],
    [{"out": [0, 0]}],
)


def bootstrap_of(source):
    compiled, report = dcmp.compile_with_report(source, optimise=False)
    times = {
        op_id: cycle
        for cycle, bundle in enumerate(compiled["bundles"])
        for ids in bundle.values()
        for op_id in ids
    }
    return times, dict(compiled["scratch"]), report


def feasible_with(source, facts, times, addresses, target_cycles, target_memory):
    try:
        compiled = dc.compilation(facts, times, addresses)
        machine.check_compilation(source, compiled)
    except (machine.CompileError, dc.ContractError):
        return False
    return (
        len(compiled["bundles"]) <= target_cycles
        and dc.footprint(facts, addresses) <= target_memory
    )


class JointNecessityTests(unittest.TestCase):
    """A joint change reaches a bound that neither change alone can reach."""

    def setUp(self):
        self.source = JOINT_NEEDED
        self.facts = dc.derive(self.source)
        self.times, self.addresses, _ = bootstrap_of(self.source)
        self.cycles = max(self.times.values()) + 1
        self.memory = dc.footprint(self.facts, self.addresses)

    def test_the_incumbent_is_what_we_think_it_is(self):
        self.assertEqual((self.cycles, self.memory), (3, 2))

    def test_address_only_changes_cannot_reach_the_target(self):
        # Times pinned at the incumbent; every address pair is tried.
        found = []
        for first, second in itertools.product(range(4), repeat=2):
            candidate = {"a": first, "b": second}
            if feasible_with(
                self.source, self.facts, self.times, candidate, self.cycles, self.memory - 1
            ):
                found.append(candidate)
        self.assertEqual(found, [], "an address-only change should not suffice")

    def test_schedule_only_changes_cannot_reach_the_target(self):
        # Addresses pinned at the incumbent; every schedule in range is tried.
        found = []
        span = range(0, self.facts.horizon)
        for combination in itertools.product(span, repeat=self.facts.count):
            candidate = dict(zip(range(self.facts.count), combination))
            if feasible_with(
                self.source,
                self.facts,
                candidate,
                self.addresses,
                self.cycles,
                self.memory - 1,
            ):
                found.append(candidate)
        self.assertEqual(found, [], "a schedule-only change should not suffice")

    def test_a_joint_change_does_reach_it_and_the_optimiser_finds_it(self):
        compiled, report = dcmp.compile_with_report(self.source)
        self.assertEqual(report["optimisation"]["accepted"], 1)
        self.assertEqual(report["footprint"], 1)
        self.assertEqual(report["cycles"], 3)
        self.assertLess(report["product"], self.cycles * self.memory)
        # Both values share one word, so their lifetimes must be disjoint.
        self.assertEqual(compiled["scratch"], {"a": 0, "b": 0})
        machine.check_compilation(self.source, compiled)
        for case in self.source["cases"]:
            machine.check_case(self.source, compiled, case)


class ObjectiveTests(unittest.TestCase):
    def test_targets_include_a_cycle_for_memory_trade(self):
        facts = dc.derive(gp.public_programs()[3])
        cycles, memory = 10, 40
        targets = do.targets_for(facts, cycles, memory)
        self.assertIn((cycles - 1, memory), targets)
        traded = [pair for pair in targets if pair[0] > cycles]
        self.assertTrue(traded, "a target spending a cycle to buy memory must exist")
        for target_cycles, target_memory in traded:
            # One metric worsens, and the product still strictly improves.
            self.assertGreater(target_cycles, cycles)
            self.assertLess(target_memory, memory)
            self.assertLess(target_cycles * target_memory, cycles * memory)

    def test_every_target_strictly_improves_the_product(self):
        for seed in (1000, 1013, 1044):
            facts = dc.derive(gp.additional_program(seed))
            for cycles, memory in ((12, 30), (8, 64), (20, 16)):
                for target in do.targets_for(facts, cycles, memory):
                    self.assertLess(target[0] * target[1], cycles * memory)
                    self.assertGreaterEqual(target[0], facts.cycle_lower_bound())
                    self.assertGreaterEqual(target[1], facts.memory_lower_bound())
                    self.assertLessEqual(target[0], facts.horizon)
                    self.assertLessEqual(target[1], machine.SCRATCH_WORDS)

    def test_an_accepted_witness_actually_trades_a_cycle_for_scratch(self):
        """A real compiled result, not target arithmetic.

        The optimiser accepts a witness whose cycle count is worse than the
        incumbent's while the product improves. Both compilations are checked
        with the frozen machine on every case, and the official score is
        recomputed from the actual integer metrics.
        """

        source = CYCLE_FOR_MEMORY_TRADE
        facts = dc.derive(source)
        baseline = machine.serial_compile(source)
        serial_cycles = len(baseline["bundles"])
        serial_memory = machine.scratch_footprint(source, baseline)

        before, before_report = dcmp.compile_with_report(source, optimise=False)
        after, after_report = dcmp.compile_with_report(source)

        for compiled in (before, after):
            machine.check_compilation(source, compiled)
            for case in source["cases"]:
                machine.check_case(source, compiled, case)

        self.assertEqual(after_report["discrepancy_count"], 0)
        self.assertEqual(after_report["optimisation"]["accepted"], 1)
        record = after_report["optimisation"]["improvements"][0]

        # One measured metric genuinely worsens.
        self.assertGreater(after_report["cycles"], before_report["cycles"])
        self.assertLess(after_report["footprint"], before_report["footprint"])
        self.assertLess(after_report["product"], before_report["product"])
        self.assertEqual(
            (record["from"]["cycles"], record["from"]["footprint"]),
            (before_report["cycles"], before_report["footprint"]),
        )
        self.assertEqual(
            (record["to"]["cycles"], record["to"]["footprint"]),
            (after_report["cycles"], after_report["footprint"]),
        )

        # The official score, recomputed from the actual integers.
        def combined(cycles, memory):
            return math.sqrt((serial_cycles / cycles) * (serial_memory / memory))

        score_before = combined(before_report["cycles"], before_report["footprint"])
        score_after = combined(after_report["cycles"], after_report["footprint"])
        self.assertGreater(score_after, score_before)

    def test_the_traded_cycle_was_necessary_for_that_footprint(self):
        """Independently establish the alternatives over the same window.

        Within the accepted window's declared domains, no assignment reaches
        the improved footprint while keeping the incumbent's cycle count, so
        the trade is not an artefact of search order.
        """

        source = CYCLE_FOR_MEMORY_TRADE
        facts = dc.derive(source)
        times, addresses, before_report = bootstrap_of(source)
        _, after_report = dcmp.compile_with_report(source)
        window = tuple(after_report["optimisation"]["improvements"][0]["window"])
        incumbent_cycles = before_report["cycles"]
        improved_memory = after_report["footprint"]

        labels, axes = independent_domains(
            facts, times, window, incumbent_cycles, improved_memory
        )
        total = 1
        for axis in axes:
            total *= max(len(axis), 1)
        self.assertLessEqual(total, 65536)

        reachable = []
        for combination in itertools.product(*axes):
            candidate_times = dict(times)
            candidate_addresses = dict(addresses)
            for (kind, key), value in zip(labels, combination):
                if kind == "time":
                    candidate_times[key] = value
                else:
                    candidate_addresses[key] = value
            if machine_feasible(
                source, facts, candidate_times, candidate_addresses,
                incumbent_cycles, improved_memory,
            ):
                reachable.append((candidate_times, candidate_addresses))

        self.assertEqual(
            reachable,
            [],
            f"footprint {improved_memory} was reachable at {incumbent_cycles} "
            f"cycles, so the accepted trade was avoidable",
        )

    def test_a_worse_metric_with_a_better_product_scores_better(self):
        """The product is the right objective for the official score."""

        serial_cycles, serial_memory = 40, 80
        worse_metric = (11, 20)  # more cycles
        incumbent = (10, 24)
        self.assertGreater(worse_metric[0], incumbent[0])
        self.assertLess(worse_metric[0] * worse_metric[1], incumbent[0] * incumbent[1])

        def combined(pair):
            return math.sqrt(
                (serial_cycles / pair[0]) * (serial_memory / pair[1])
            )

        self.assertGreater(combined(worse_metric), combined(incumbent))


class ExternalEffectTests(unittest.TestCase):
    def test_moving_a_selected_consumer_changes_an_external_lifetime(self):
        source = MOVING_CONSUMER
        facts = dc.derive(source)
        times, addresses, _ = bootstrap_of(source)
        meter = si.Budget(seconds=30.0, max_cover=10 ** 6, max_records=10 ** 6).start()
        # Select only the final store, which consumes x but does not produce it.
        consumer = max(times)
        query = dk.JointQuery(
            facts, times, addresses, (consumer,), max(times.values()) + 3, 64, meter
        )
        self.assertIn(consumer, facts.consumers["x"])
        self.assertNotIn(facts.producers["x"], query.time_field)
        # x is affected even though its producer is fixed, because its last
        # reader can move.
        self.assertIn("x", query.affected_values)
        start, end = query._live_bounds("x")
        self.assertGreaterEqual(end, query._time_domain(consumer)[1])
        self.assertGreater(end, start)

    def test_a_fixed_decision_violating_a_target_is_locally_infeasible(self):
        source = gp.public_programs()[0]
        facts = dc.derive(source)
        times, addresses, _ = bootstrap_of(source)
        meter = si.Budget(seconds=30.0).start()
        with self.assertRaises(dk.Infeasible):
            dk.JointQuery(facts, times, addresses, (0,), 1, 256, meter).expression()
        with self.assertRaises(dk.Infeasible):
            dk.JointQuery(facts, times, addresses, (0,), 256, 1, meter).expression()


class RollbackTests(unittest.TestCase):
    def test_an_optimiser_timeout_returns_the_validated_incumbent(self):
        source = gp.public_programs()[5]
        base, base_report = dcmp.compile_with_report(source, optimise=False)
        limits = dcmp.Limits(optimise_seconds=0.0)
        compiled, report = dcmp.compile_with_report(source, limits)
        self.assertEqual(compiled, base)
        self.assertEqual(report["optimisation"]["accepted"], 0)
        self.assertEqual(report["optimisation"]["stopped_because"], "deadline")
        machine.check_compilation(source, compiled)

    def test_starved_queries_record_unknown_and_keep_the_incumbent(self):
        source = gp.public_programs()[5]
        base, _ = dcmp.compile_with_report(source, optimise=False)
        # Starve the optimiser alone. Shrinking query_seconds would starve the
        # bootstrap too, and that is a compilation failure rather than a
        # rollback, which is a different behaviour tested elsewhere.
        limits = dcmp.Limits(optimise_seconds=0.001)
        compiled, report = dcmp.compile_with_report(source, limits)
        statuses = report["optimisation"]["statuses"]
        unknown = statuses["UNKNOWN_CONSTRUCTION"] + statuses["UNKNOWN_SEARCH"]
        self.assertGreater(unknown, 0, "starved queries must be recorded as UNKNOWN")
        self.assertEqual(statuses["SAT"], 0)
        self.assertEqual(compiled, base)
        machine.check_compilation(source, compiled)

    def test_unknown_is_never_reported_as_unsat(self):
        source = gp.public_programs()[7]
        limits = dcmp.Limits(optimise_seconds=0.001)
        _, report = dcmp.compile_with_report(source, limits)
        self.assertEqual(report["optimisation"]["statuses"]["UNSAT"], 0)

    def test_an_invalid_candidate_is_rejected_and_recorded(self):
        """Inject a bad witness through a seam; the checker must catch it.

        The reference validator is not modified. The optimiser's own
        acceptance check and the frozen validator both run on every candidate,
        and a disagreement is recorded rather than released.
        """

        source = JOINT_NEEDED
        original = dk.JointQuery.decode

        def corrupt(self, cube):
            original(self, cube)
            # Keep the incumbent schedule, where the two values are certainly
            # live together, but stack them on one word. Corrupting only the
            # addresses would not do: at the witness schedule the lifetimes are
            # disjoint, so a shared word there is perfectly legal.
            return dict(self.times), {name: 0 for name in self.facts.value_names}

        dk.JointQuery.decode = corrupt
        try:
            compiled, report = dcmp.compile_with_report(source)
        finally:
            dk.JointQuery.decode = original

        errors = report["optimisation"]["validation_errors"]
        self.assertTrue(errors, "the invalid candidate must be recorded")
        self.assertEqual(report["optimisation"]["accepted"], 0)
        # The released compilation is still the validated incumbent.
        machine.check_compilation(source, compiled)
        for case in source["cases"]:
            machine.check_case(source, compiled, case)


class DeterminismTests(unittest.TestCase):
    def test_windows_are_deduplicated_and_ordered(self):
        source = gp.public_programs()[6]
        facts = dc.derive(source)
        times, addresses, _ = bootstrap_of(source)
        for scratch_first in (False, True):
            windows = do.windows_for(facts, times, addresses, scratch_first)
            self.assertEqual(len(windows), len(set(windows)))
            for window in windows:
                self.assertEqual(list(window), sorted(window))
                self.assertLessEqual(len(window), do.WINDOW_SIZE)
                self.assertTrue(window)

    def test_source_windows_keep_the_final_shorter_tail(self):
        """Starts advance by two and the last, shorter window is retained.

        Stopping as soon as a full window touched the end dropped the tail, so
        the final operations were never selectable together.
        """

        def source_windows(count):
            consts = count // 2
            operations = [
                {"op": "const", "dest": "c%d" % i, "value": i} for i in range(consts)
            ]
            for index in range(count - consts):
                operations.append(
                    {
                        "op": "store",
                        "args": ["c%d" % (index % consts)],
                        "buffer": "out",
                        "offset": index,
                    }
                )
            built = program(
                "windows_%d" % count,
                {"out": count},
                operations,
                [{"out": [0] * count}],
            )
            facts = dc.derive(built)
            times, addresses, _ = bootstrap_of(built)
            return facts, times, addresses

        for count, expected_tail in ((6, (4, 5)), (7, (6,)), (10, (8, 9))):
            facts, times, addresses = source_windows(count)
            windows = do.windows_for(facts, times, addresses, False)
            self.assertIn(
                expected_tail,
                windows,
                f"{count} operations: the final shorter window {expected_tail} is missing",
            )
            # Exactly the specified starts, truncated at the operation count.
            expected_source = []
            for start in range(0, count, 2):
                candidate = tuple(range(start, min(start + do.WINDOW_SIZE, count)))
                if candidate and candidate not in expected_source:
                    expected_source.append(candidate)
            for candidate in expected_source:
                self.assertIn(candidate, windows, f"{count} operations: {candidate}")
            # Stable deduplication: no repeats, first occurrence kept.
            self.assertEqual(len(windows), len(set(windows)))

    def test_source_windows_for_six_operations_are_exact(self):
        source = program(
            "six_ops",
            {"out": 3},
            [{"op": "const", "dest": "c%d" % i, "value": i} for i in range(3)]
            + [
                {"op": "store", "args": ["c%d" % i], "buffer": "out", "offset": i}
                for i in range(3)
            ],
            [{"out": [0, 0, 0]}],
        )
        facts = dc.derive(source)
        times, addresses, _ = bootstrap_of(source)
        windows = do.windows_for(facts, times, addresses, False)
        for expected in ((0, 1, 2, 3), (2, 3, 4, 5), (4, 5)):
            self.assertIn(expected, windows)

    def test_scratch_window_leads_when_the_memory_target_is_tighter(self):
        source = gp.public_programs()[6]
        facts = dc.derive(source)
        times, addresses, _ = bootstrap_of(source)
        memory_first = do.windows_for(facts, times, addresses, True)
        time_first = do.windows_for(facts, times, addresses, False)
        self.assertNotEqual(memory_first[0], time_first[0])

    def test_compilation_is_reproducible(self):
        for source in gp.public_programs()[:4]:
            first, first_report = dcmp.compile_with_report(source)
            second, second_report = dcmp.compile_with_report(source)
            self.assertEqual(first, second)
            self.assertEqual(
                first_report["optimisation"]["improvements"],
                second_report["optimisation"]["improvements"],
            )

    def test_the_query_cap_is_respected(self):
        for source in gp.public_programs()[:4]:
            _, report = dcmp.compile_with_report(source)
            self.assertLessEqual(
                report["optimisation"]["attempted_queries"],
                dcmp.DEFAULT_LIMITS.max_queries,
            )

    def test_accepted_improvements_are_strict_and_validated(self):
        improved = 0
        for seed in (1009, 1024, 1049, 1088):
            source = gp.additional_program(seed)
            compiled, report = dcmp.compile_with_report(source)
            machine.check_compilation(source, compiled)
            for case in source["cases"]:
                machine.check_case(source, compiled, case)
            for record in report["optimisation"]["improvements"]:
                improved += 1
                self.assertLess(record["to"]["product"], record["from"]["product"])
            self.assertEqual(report["optimisation"]["validation_errors"], [])
        self.assertGreater(improved, 0, "these seeds are known to improve")


if __name__ == "__main__":
    unittest.main()
