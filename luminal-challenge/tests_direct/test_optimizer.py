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
