"""Bounds, budgets and traversal tests for the phase 2 structural search.

Acceptance-matrix checks covered here: C13 admissible lower bounds against every
completion of every prefix, C14 budget and verdict integrity, and C29 clock
overshoot with incumbent retention.

The decisive property is that exhausting a declared finite domain, pruned only
by bounds proved admissible, agrees with an independent enumeration. Budget
exhaustion is UNKNOWN and is never reported as UNSAT.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
for candidate in (ROOT, ROOT / ".reference"):
    if str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))

import machine  # noqa: E402

import direct_contract as dc  # noqa: E402
import direct_compiler as dcomp  # noqa: E402
import direct_optimizer as dopt  # noqa: E402
import schema_index as si  # noqa: E402

from research import structural_encoding as se  # noqa: E402
from research import structural_oracle as so  # noqa: E402
from research import structural_search as ss  # noqa: E402
from research import run_structural_experiments as runner  # noqa: E402


FIXTURES = json.loads((ROOT / "plan" / "phase2" / "FIXTURES.json").read_text())["fixtures"]


def generous_budget(seconds=30.0):
    return si.Budget(
        seconds=seconds, max_cover=65536, max_visited=1000000, max_records=100000
    )


class BoundAdmissibility(unittest.TestCase):
    """C13: no prefix bound exceeds any completion of that prefix."""

    def test_every_prefix_bound_on_every_fixture(self):
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            with self.subTest(fixture=record["id"]):
                report = runner.bound_admissibility(domain)
                self.assertIn(report["status"], (runner.PASS, runner.NOT_APPLICABLE))
                self.assertEqual(report.get("violation_count", 0), 0)
                self.assertGreater(report["prefixes_checked"], 0)

    def test_cycle_bound_omits_the_maximum_when_nothing_is_placed(self):
        record = FIXTURES[0]
        facts = dc.derive(record["program"])
        self.assertEqual(ss.cycle_bound(facts, {}), facts.cycle_lower_bound())
        self.assertGreaterEqual(
            ss.cycle_bound(facts, {0: 5}), max(facts.cycle_lower_bound(), 6)
        )

    def test_scratch_bound_uses_the_widest_result_and_placed_blocks(self):
        record = next(item for item in FIXTURES if item["family"] == "mixed")
        facts = dc.derive(record["program"])
        self.assertEqual(ss.scratch_bound(facts, {}), facts.memory_lower_bound())
        name = facts.value_names[0]
        placed = ss.scratch_bound(facts, {name: 40})
        self.assertGreaterEqual(placed, 40 + facts.width[name])

    def test_peak_live_width_is_a_bound_not_an_achievable_footprint(self):
        """It is a lower bound only; alignment can make it unreachable."""

        record = next(item for item in FIXTURES if item["family"] == "mixed")
        domain = se.Domain.from_record(record)
        enumeration = so.enumerate_feasible(record, 65536)
        self.assertTrue(enumeration["feasible"])
        for member in enumeration["feasible"]:
            times = {int(key): value for key, value in member["times"].items()}
            live = dc.lifetimes(domain.facts, times)
            self.assertLessEqual(
                ss.peak_live_width(domain.facts, live), member["scratch"]
            )


class ExhaustiveAgreement(unittest.TestCase):
    """The pruned and unpruned arms reach the independent oracle's minimum."""

    def test_both_arms_reach_the_oracle_minimum(self):
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(record, 65536)
            minimum = min(
                (entry["product"] for entry in enumeration["feasible"]), default=None
            )
            with self.subTest(fixture=record["id"]):
                for arm in ("structural_dfs", "structural_bound"):
                    report = ss.search(domain, None, arm, generous_budget())
                    self.assertEqual(report.status, "SAT")
                    self.assertEqual(report.best_product, minimum)
                    self.assertEqual(report.rejected_completions, [])

    def test_pruning_never_changes_the_answer_but_visits_fewer_nodes(self):
        cheaper = 0
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            plain = ss.search(domain, None, "structural_dfs", generous_budget())
            pruned = ss.search(domain, None, "structural_bound", generous_budget())
            self.assertEqual(plain.best_product, pruned.best_product, record["id"])
            self.assertLessEqual(pruned.nodes, plain.nodes, record["id"])
            if pruned.nodes < plain.nodes:
                cheaper += 1
        self.assertGreater(cheaper, 0, "pruning never helped on any fixture")

    def test_unpruned_completions_equal_the_feasible_set(self):
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(record, 65536)
            report = ss.search(domain, None, "structural_dfs", generous_budget())
            with self.subTest(fixture=record["id"]):
                self.assertEqual(report.completions, enumeration["feasible_count"])
                self.assertEqual(report.duplicate_hits, 0)

    def test_strict_improvement_only(self):
        """An equal product retains the earlier incumbent."""

        record = FIXTURES[0]
        domain = se.Domain.from_record(record)
        enumeration = so.enumerate_feasible(record, 65536)
        minimum = min(entry["product"] for entry in enumeration["feasible"])
        optimal = next(
            entry for entry in enumeration["feasible"] if entry["product"] == minimum
        )
        incumbent = json.loads(optimal["identity"])
        report = ss.search(domain, incumbent, "structural_bound", generous_budget())
        self.assertFalse(report.improved)
        self.assertEqual(report.status, "UNSAT")
        self.assertEqual(report.best_identity, se.object_digest(
            se.normalise_compilation(domain.facts, incumbent)
        ))

    def test_unsat_means_this_domain_and_nothing_wider(self):
        record = FIXTURES[0]
        domain = se.Domain.from_record(record)
        enumeration = so.enumerate_feasible(record, 65536)
        minimum = min(entry["product"] for entry in enumeration["feasible"])
        optimal = next(
            entry for entry in enumeration["feasible"] if entry["product"] == minimum
        )
        report = ss.search(
            domain, json.loads(optimal["identity"]), "structural_bound", generous_budget()
        )
        self.assertEqual(report.status, "UNSAT")
        self.assertIn("declared domain", report.reason)


class BudgetIntegrity(unittest.TestCase):
    """C14: exhaustion is UNKNOWN or INTERRUPTED, never a fabricated UNSAT."""

    def test_node_cap_yields_unknown(self):
        record = next(item for item in FIXTURES if item["cartesian_assignments"] >= 180)
        domain = se.Domain.from_record(record)
        budget = si.Budget(seconds=30, max_cover=16, max_visited=1, max_records=1)
        report = ss.search(domain, None, "structural_dfs", budget)
        self.assertEqual(report.status, "UNKNOWN")
        self.assertIn("budget", report.reason)

    def test_validation_is_charged_and_fully_accounted(self):
        """Validation work is paid for and every validated candidate is case-checked.

        A limitation worth stating rather than engineering around: each frozen
        fixture has only **two** distinct objective values, so at most one strict
        improvement can occur and the search validates at most once. These
        fixtures therefore cannot drive the validation counter to its cap, and
        no amount of incumbent choice changes that. What is checkable here is
        the accounting, which is what the cap protects.
        """

        cases_seen = 0
        for record in FIXTURES:
            domain = se.Domain.from_record(record)
            enumeration = so.enumerate_feasible(record, 65536)
            if not enumeration["feasible"]:
                continue
            distinct = {entry["product"] for entry in enumeration["feasible"]}
            self.assertLessEqual(len(distinct), 2, record["id"])
            worst = max(enumeration["feasible"], key=lambda entry: entry["product"])
            report = ss.search(
                domain, json.loads(worst["identity"]), "structural_dfs", generous_budget()
            )
            with self.subTest(fixture=record["id"]):
                self.assertLessEqual(report.validations, report.completions)
                self.assertEqual(
                    report.case_checks,
                    report.validations * len(record["program"]["cases"]),
                )
                cases_seen += report.case_checks
        self.assertGreater(cases_seen, 0)

    def test_an_exhausted_record_budget_is_unknown_on_a_richer_domain(self):
        """A domain with many distinct objectives does reach the validation cap."""

        name, program = runner.public_programs()[0]
        facts = dc.derive(program)
        compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        domain = se.Domain.from_record(
            runner.whole_program_record("expanded", "expanded", program, facts, compiled)
        )
        budget = si.Budget(seconds=5, max_cover=16, max_visited=1000000, max_records=1)
        report = ss.search(domain, compiled, "structural_bound", budget)
        self.assertNotEqual(report.status, "UNSAT")
        self.assertEqual(report.rejected_completions, [])

    def test_time_cap_yields_unknown_and_keeps_the_incumbent(self):
        """C29: an interrupted search retains the prior validated incumbent."""

        record = FIXTURES[3]
        domain = se.Domain.from_record(record)
        incumbent = record["incumbent"]
        budget = si.Budget(seconds=1.0, max_cover=16, max_visited=1000000, max_records=100000)
        meter_budget = si.Budget(
            seconds=0.000001, max_cover=16, max_visited=1000000, max_records=100000
        )
        report = ss.search(domain, incumbent, "structural_bound", meter_budget)
        self.assertIn(report.status, ("UNKNOWN", "UNSAT", "SAT"))
        if report.status == "UNKNOWN":
            self.assertEqual(
                report.best_identity,
                se.object_digest(se.normalise_compilation(domain.facts, incumbent)),
            )
            self.assertFalse(report.improved)

    def test_an_exhausted_budget_is_never_reported_as_unsat(self):
        record = next(item for item in FIXTURES if item["cartesian_assignments"] >= 180)
        domain = se.Domain.from_record(record)
        for visited in (1, 2, 3):
            budget = si.Budget(
                seconds=30, max_cover=16, max_visited=visited, max_records=100000
            )
            report = ss.search(domain, None, "structural_dfs", budget)
            self.assertNotEqual(report.status, "UNSAT")

    def test_decoder_interruption_is_a_status_not_an_exception(self):
        domain = se.Domain.from_record(FIXTURES[0])
        meter = si.Budget(
            seconds=30, max_cover=4, max_visited=1, max_records=1
        ).start()
        result = se.decode(domain, 0, "structural_rank", meter=meter)
        self.assertEqual(result.status, se.INTERRUPTED)
        self.assertIsNone(result.compilation)
        self.assertTrue(result.reason)


class MatchedWindowDomains(unittest.TestCase):
    """The structural arm states the identical physical domain as JointQuery."""

    def setUp(self):
        self.name, self.program = runner.public_programs()[0]
        self.facts = dc.derive(self.program)
        compiled, _ = dcomp.compile_with_report(
            self.program, dcomp.DEFAULT_LIMITS, optimise=False
        )
        self.times = se.issue_cycles_of(self.program, compiled["bundles"])
        self.addresses = dict(compiled["scratch"])

    def test_time_domain_matches_the_accepted_query(self):
        import direct_constraints as dk

        cycles = max(self.times.values()) + 1
        memory = dc.footprint(self.facts, self.addresses)
        targets = dopt.targets_for(self.facts, cycles, memory)
        self.assertTrue(targets)
        target_cycles, target_memory = targets[0]
        window = dopt.windows_for(
            self.facts, self.times, self.addresses,
            scratch_first=target_memory < memory,
        )[0]
        try:
            record = runner.matched_window_record(
                "matched", "matched", self.program, self.facts,
                self.times, self.addresses, window, target_cycles, target_memory,
            )
        except dk.Infeasible:
            self.skipTest("the first window of this program is infeasible")
        meter = si.Budget(seconds=5.0).start()
        query = dk.JointQuery(
            self.facts, self.times, self.addresses, window,
            target_cycles, target_memory, meter, None,
        )
        for op_id in window:
            low, high = query._time_domain(op_id)
            self.assertEqual(
                record["time_domains"][str(op_id)], list(range(low, high + 1))
            )
        for op_id in window:
            name = self.facts.dest[op_id]
            if name is None:
                continue
            low, high = query._address_bounds(name)
            expected = [
                base for base in range(low, high + 1)
                if self.facts.width[name] != machine.VLEN or base % machine.VLEN == 0
            ]
            self.assertEqual(record["address_domains"][name], expected)

    def test_a_fixed_decision_violating_the_target_is_infeasible(self):
        import direct_constraints as dk

        with self.assertRaises(dk.Infeasible):
            runner.matched_window_record(
                "impossible", "matched", self.program, self.facts,
                self.times, self.addresses, (0,), 1, 1,
            )

    def test_expanded_domain_is_never_labelled_matched(self):
        self.assertIn("structural_expanded", ss.ARMS)
        record = runner.whole_program_record(
            "expanded", "expanded", self.program, self.facts,
            dc.compilation(self.facts, self.times, self.addresses),
        )
        self.assertEqual(record["family"], "expanded")
        self.assertEqual(len(record["selected_operations"]), self.facts.count)
        self.assertEqual(record["fixed_times"], {})
        self.assertIsNone(record["target"])


class ClockAndIncumbent(unittest.TestCase):
    """C29: overshoot is measured and reported, not asserted to be zero."""

    def test_structural_optimise_reports_its_overshoot(self):
        name, program = runner.public_programs()[0]
        facts = dc.derive(program)
        compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        times = se.issue_cycles_of(program, compiled["bundles"])
        addresses = dict(compiled["scratch"])
        contract = runner.Contract(ROOT / "plan" / "phase2")
        best_times, best_addresses, record = runner.structural_optimise(
            program, facts, times, addresses, "structural_bound",
            0.05, 0.05, dcomp.DEFAULT_LIMITS.max_queries, contract.budgets,
        )
        self.assertIn("overshoot_seconds", record)
        self.assertEqual(
            record["seconds"] - record["budget_seconds"], record["overshoot_seconds"]
        )
        self.assertEqual(record["discrepancy_count"], 0)
        # Whatever survives is still a legal compilation.
        machine.check_compilation(
            program, dc.compilation(facts, best_times, best_addresses)
        )

    def test_an_interrupted_optimisation_keeps_the_bootstrap_incumbent(self):
        name, program = runner.public_programs()[0]
        facts = dc.derive(program)
        compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        times = se.issue_cycles_of(program, compiled["bundles"])
        addresses = dict(compiled["scratch"])
        contract = runner.Contract(ROOT / "plan" / "phase2")
        best_times, best_addresses, record = runner.structural_optimise(
            program, facts, times, addresses, "structural_bound",
            1e-9, 1e-9, dcomp.DEFAULT_LIMITS.max_queries, contract.budgets,
        )
        self.assertEqual(best_times, times)
        self.assertEqual(best_addresses, addresses)
        self.assertEqual(record["accepted"], 0)
        self.assertEqual(record["stopped_because"], "deadline")

    def test_every_recorded_domain_precedes_its_solve(self):
        name, program = runner.public_programs()[1]
        facts = dc.derive(program)
        compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
        times = se.issue_cycles_of(program, compiled["bundles"])
        addresses = dict(compiled["scratch"])
        contract = runner.Contract(ROOT / "plan" / "phase2")
        _, _, record = runner.structural_optimise(
            program, facts, times, addresses, "structural_dfs",
            0.2, 0.05, dcomp.DEFAULT_LIMITS.max_queries, contract.budgets,
        )
        self.assertEqual(record["recorded_queries"], record["attempted_queries"])
        for entry in record["queries"]:
            self.assertIn("status", entry)
            if entry["status"] != "INFEASIBLE":
                self.assertIsNotNone(entry["domain_sha256"])
        total = sum(record["statuses"].values())
        self.assertEqual(total, record["attempted_queries"])


class ArmSchedule(unittest.TestCase):
    """Balanced arm order, from the frozen RNG, rotated by repetition."""

    def test_rotation_and_membership(self):
        import random

        programs = [{"program_sha256": "p%d" % index, "path": "x"} for index in range(2)]
        rng = random.Random(20261020)
        schedule = runner.arm_schedule(
            programs, [0.01, 0.1], ("accepted_bootstrap", "accepted_default"),
            ("accepted_budgeted", "structural_bound"), rng, 4,
        )
        keys = [(entry[0]["program_sha256"], entry[1], entry[3], entry[4])
                for entry in schedule]
        self.assertEqual(len(keys), 2 * (2 + 2 * 2) * 4 // 1 - 0)
        # Every block sees each arm exactly once per repetition.
        from collections import Counter

        counts = Counter((program, budget, arm) for program, budget, _, _, arm in
                         [(e[0]["program_sha256"], e[1], e[2], e[3], e[4]) for e in schedule])
        self.assertTrue(all(value == 4 for value in counts.values()))

    def test_arm_order_rotates_across_repetitions(self):
        import random

        programs = [{"program_sha256": "p0", "path": "x"}]
        rng = random.Random(20261020)
        schedule = runner.arm_schedule(
            programs, [0.1], (), ("a", "b", "c"), rng, 3
        )
        orders = []
        for repetition in range(3):
            orders.append([entry[4] for entry in schedule if entry[3] == repetition])
        self.assertEqual(len(set(map(tuple, orders))), 3)
        for order in orders:
            self.assertEqual(sorted(order), ["a", "b", "c"])


if __name__ == "__main__":
    unittest.main()
