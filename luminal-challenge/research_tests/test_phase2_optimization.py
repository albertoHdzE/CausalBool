"""Regression tests for the NEW controller of optimization protocol 1.0.

These exercise real boundaries -- a real clock crossing a real query allowance,
real aggregate ceilings, a validator that really rejects -- rather than mocks of
the controller's own internals.
"""

from __future__ import annotations

import time
import unittest
from unittest import mock

import machine

import direct_compiler as dcomp
import direct_contract as dc
import direct_optimizer as dopt

from research import optimization_search as osr
from research import run_structural_experiments as rse
from research import structural_encoding as se
from research import structural_models as sm
import schema_index as si

from tests_direct import generate_programs as gp


def _bootstrap(program):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, se.issue_cycles_of(program, compiled["bundles"]), dict(compiled["scratch"])


def _development(count=100):
    return [gp.additional_program(seed) for seed in range(800000, 800000 + count)]


def _public():
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / ".reference" / "programs"
    return [machine.load_program(path) for path in sorted(root.glob("*.json"))]


class WindowParity(unittest.TestCase):
    def test_size_four_equals_production_owner_on_every_development_program(self):
        checked = 0
        for program in _development() + _public():
            facts, times, addresses = _bootstrap(program)
            for scratch_first in (False, True):
                self.assertEqual(
                    osr.windows_of_size(facts, times, addresses, scratch_first, 4),
                    dopt.windows_for(facts, times, addresses, scratch_first=scratch_first))
                checked += 1
        self.assertEqual(checked, 216)

    def test_matched_plan_is_the_accepted_window_list_at_slack_two(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        plan = osr.query_plan(facts, times, addresses, False, "matched")
        self.assertEqual([w for w, _ in plan], dopt.windows_for(facts, times, addresses, False))
        self.assertEqual({s for _, s in plan}, {2})

    def test_wider_plan_appends_new_eight_windows_after_the_originals(self):
        seen_wider = 0
        for program in _development(20):
            facts, times, addresses = _bootstrap(program)
            base = dopt.windows_for(facts, times, addresses, False)
            plan = osr.query_plan(facts, times, addresses, False, "wider")
            self.assertEqual(plan[:len(base)], [(tuple(w), 2) for w in base])
            extra = plan[len(base):]
            self.assertTrue(all(s == 4 for _, s in extra))
            self.assertFalse(set(w for w, _ in extra) & set(map(tuple, base)))
            self.assertEqual(len({w for w, _ in plan}), len(plan))
            self.assertTrue(all(len(w) <= 8 for w, _ in extra))
            seen_wider += len(extra)
        self.assertGreater(seen_wider, 0)

    def test_slack_parameter_defaults_to_the_accepted_query(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        cycles = max(times.values()) + 1
        memory = dc.footprint(facts, addresses)
        import direct_constraints as dk

        found = None
        for tc, tm in dopt.targets_for(facts, cycles, memory):
            for window in dopt.windows_for(facts, times, addresses, tm < memory):
                try:
                    default = rse.matched_window_record("x", "m", program, facts, times,
                                                        addresses, window, tc, tm)
                except dk.Infeasible:
                    continue
                found = (tc, tm, window)
                break
            if found:
                break
        self.assertIsNotNone(found)
        tc, tm, window = found
        explicit = rse.matched_window_record("x", "m", program, facts, times, addresses, window,
                                             tc, tm, time_slack=2)
        wide = rse.matched_window_record("x", "m", program, facts, times, addresses, window,
                                         tc, tm, time_slack=4)
        self.assertEqual(default, explicit)
        for op in window:
            self.assertLessEqual(len(default["time_domains"][str(op)]),
                                 len(wide["time_domains"][str(op)]))


class CapAndDeadline(unittest.TestCase):
    def setUp(self):
        self.program = gp.additional_program(800007)
        self.facts, self.times, self.addresses = _bootstrap(self.program)

    def run_config(self, config, budget=1.0, **kwargs):
        return osr.optimise(self.program, self.facts, self.times, self.addresses,
                            config=config, budget_seconds=budget, **kwargs)[2]

    def test_cap_accounting_counts_every_attempted_query(self):
        capped = self.run_config("cap32_matched")
        self.assertEqual(capped["attempted_queries"], 32)
        self.assertEqual(capped["stopped_because"], "query_cap")
        uncapped = self.run_config("capnull_matched")
        self.assertGreater(uncapped["attempted_queries"], 32)
        self.assertNotEqual(uncapped["stopped_because"], "query_cap")
        self.assertEqual(sum(uncapped["statuses"].values()), uncapped["recorded_queries"])

    def _slow_construction(self, first_only_seconds):
        original = rse.matched_window_record
        calls = {"n": 0}

        def slow(*args, **kwargs):
            calls["n"] += 1
            record = original(*args, **kwargs)
            if calls["n"] == 1:
                time.sleep(first_only_seconds)
            return record

        return slow, calls

    def test_query_expiry_during_construction_continues_the_traversal(self):
        slow, calls = self._slow_construction(0.12)
        with mock.patch.object(rse, "matched_window_record", slow):
            record = self.run_config("capnull_matched", budget=1.0)
        self.assertEqual(record["statuses"]["QUERY_EXPIRED"], 1)
        self.assertGreater(record["attempted_queries"], 1)
        self.assertNotEqual(record["stopped_because"], "deadline")

    def test_counterexample_frozen_controller_stops_the_whole_pass(self):
        slow, calls = self._slow_construction(0.12)
        # The first window may be INFEASIBLE before construction; find a program
        # position where construction happens by patching Domain construction.
        original = se.Domain.from_record
        state = {"n": 0}

        def slow_domain(record, *args, **kwargs):
            state["n"] += 1
            domain = original(record, *args, **kwargs)
            if state["n"] == 1:
                time.sleep(0.12)
            return domain

        limits = {"query_max_cover": 4096, "search_max_nodes": 10 ** 6,
                  "search_max_candidate_validations": 10 ** 5}
        with mock.patch.object(se.Domain, "from_record", staticmethod(slow_domain)):
            _, _, frozen = rse.structural_optimise(self.program, self.facts, self.times,
                                                   self.addresses, "structural_bound", 1.0,
                                                   0.1, 32, limits)
        state["n"] = 0
        with mock.patch.object(se.Domain, "from_record", staticmethod(slow_domain)):
            new = self.run_config("cap32_matched", budget=1.0)
        self.assertEqual(frozen["stopped_because"], "deadline")
        self.assertEqual(new["statuses"]["QUERY_EXPIRED"], 1)
        self.assertEqual(new["stopped_because"], "query_cap")
        self.assertGreater(new["attempted_queries"], frozen["attempted_queries"])

    def test_genuine_overall_expiry_stops_with_deadline(self):
        original = se.Domain.from_record

        def slow_domain(record, *args, **kwargs):
            time.sleep(0.03)
            return original(record, *args, **kwargs)

        with mock.patch.object(se.Domain, "from_record", staticmethod(slow_domain)):
            record = self.run_config("capnull_wider", budget=0.05)
        self.assertEqual(record["stopped_because"], "deadline")
        self.assertLess(record["seconds"], 0.05 + 0.2)

    def test_aggregate_node_ceiling_counts_all_queries(self):
        record = self.run_config("capnull_wider", node_ceiling=40)
        self.assertEqual(record["stopped_because"], "aggregate_nodes")
        self.assertLessEqual(record["aggregate"]["nodes"], 40)

    def test_aggregate_validation_ceiling(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        record = osr.optimise(program, facts, times, addresses, config="capnull_wider",
                              budget_seconds=5.0, validation_ceiling=1)[2]
        self.assertLessEqual(record["aggregate"]["validations"], 1)
        free = osr.optimise(program, facts, times, addresses, config="capnull_wider",
                            budget_seconds=5.0)[2]
        if free["aggregate"]["validations"] > 1:
            self.assertEqual(record["stopped_because"], "aggregate_validations")


class Discrepancies(unittest.TestCase):
    def test_rejected_candidate_is_retained_as_a_discrepancy(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        real = machine.check_case
        bootstrap = dc.compilation(facts, times, addresses)
        normal = se.normalise_compilation(facts, bootstrap)

        def lying(prog, compilation, case):
            if se.normalise_compilation(facts, compilation) != normal:
                raise machine.ProgramError("planted late discrepancy")
            return real(prog, compilation, case)

        with mock.patch.object(machine, "check_case", lying):
            best_t, best_a, record = osr.optimise(program, facts, times, addresses,
                                                  config="capnull_wider", budget_seconds=2.0)
        self.assertGreater(record["discrepancy_count"], 0)
        self.assertEqual(best_t, times)
        self.assertEqual(best_a, addresses)


class EngineeringEquality(unittest.TestCase):
    def test_cached_build_reproduces_reference_under_deterministic_limits(self):
        compared = 0
        for seed in (800000, 800001, 800003, 800007, 800012, 800019):
            program = gp.additional_program(seed)
            facts, times, addresses = _bootstrap(program)
            for config in ("cap32_matched", "capnull_wider"):
                outputs = []
                for build in osr.BUILDS:
                    t, a, r = osr.optimise(program, facts, times, addresses, config=config,
                                           budget_seconds=1e6, query_seconds=1e6, build=build,
                                           node_ceiling=20000)
                    strip = {k: v for k, v in r.items() if k not in (
                        "seconds", "overshoot_seconds", "build", "queries")}
                    queries = [{k: v for k, v in q.items() if "seconds" not in k}
                               for q in r["queries"]]
                    outputs.append((t, a, strip, queries))
                self.assertEqual(outputs[0], outputs[1])
                compared += 1
        self.assertEqual(compared, 12)

    def test_memo_never_crosses_a_program(self):
        memo = {}
        first = gp.additional_program(800001)
        second = gp.additional_program(800002)
        for program in (first, second):
            facts, times, addresses = _bootstrap(program)
            record = rse.whole_program_record("x", "f", program, facts,
                                              dc.compilation(facts, times, addresses))
            domain = se.Domain.from_record(record, memo=memo)
            self.assertIs(domain.program, program)
            self.assertEqual(domain.facts.count, len(program["operations"]))


class DepthTwoProposals(unittest.TestCase):
    def test_depth_one_equals_the_historical_model_expand_stream(self):
        cover = (si.Cube(8, 0b00010010, 0b00000001), si.Cube(8, 0b10000000, 0))
        historical = list(sm.proposals("model_expand", 8, [], cover, set(), None))
        ours = list(osr.model_proposals(1, 8, cover, set()))
        self.assertEqual(historical, ours)

    def test_depth_two_suppresses_depth_one_indices_and_repeats_nothing(self):
        cover = (si.Cube(6, 0b000110, 0), si.Cube(6, 0b100000, 0b000001))
        accounting = {}
        stream = [i for i, _ in osr.model_proposals(2, 6, cover, set(), None, accounting)]
        self.assertEqual(len(stream), len(set(stream)))
        depth1 = [i for i, _ in osr.model_proposals(1, 6, cover, set())]
        self.assertEqual(stream[:len(depth1)], depth1)
        self.assertGreater(accounting["suppressed_indices"], 0)
        first = sm.expand_cubes(cover, 6)
        second = sm.expand_cubes(first, 6)
        union = set()
        for cube in list(first) + list(second):
            union.update(cube.members())
        self.assertEqual(set(stream), union)


if __name__ == "__main__":
    unittest.main()


class LearnerIsolation(unittest.TestCase):
    def test_learner_module_imports_no_oracle_fixture_or_evaluator(self):
        import ast
        from pathlib import Path

        path = Path(__file__).resolve().parents[1] / "research" / "optimization_models.py"
        tree = ast.parse(path.read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imported.update(f"{node.module}.{alias.name}" for alias in node.names)
        for banned in ("structural_oracle", "optimization_fixtures", "optimization_model_worker",
                       "optimization_runner"):
            self.assertFalse(any(banned in name for name in imported), banned)

    def test_worker_hands_the_learner_only_training_labels(self):
        import json
        import tempfile
        from pathlib import Path

        from research import optimization_fixtures as of
        from research import optimization_model_worker as mw
        from research import structural_oracle as so

        program = gp.additional_program(820000)
        facts, times, addresses, incumbent = of.bootstrap(program)
        orders = of.producing_orders(facts, times, addresses)
        record = of.domain_record("t", "scalar", program, facts, times, addresses, incumbent,
                                  orders["latest_issue"][:2], 2)
        enumeration = so.enumerate_feasible(record, of.CARTESIAN_MAX)
        trips = of.round_trips(se.Domain.from_record(record), enumeration["feasible"])
        self.assertEqual(trips["failures"], [])
        parts = of.split([e["identity"] for e in enumeration["feasible"]])
        with tempfile.TemporaryDirectory() as tmp:
            tmp = Path(tmp)
            (tmp / "record.json").write_text(json.dumps(record))
            (tmp / "oracle.json").write_text(json.dumps(
                {"feasible": enumeration["feasible"], "oracle_seconds": 0.0}))
            (tmp / "split.json").write_text(json.dumps(parts))
            import hashlib

            digests = {k: hashlib.sha256((tmp / f"{k}.json").read_bytes()).hexdigest()
                       for k in ("record", "oracle", "split")}
            seen = {}

            def spy(domain, training, arm, budget, seed=None, clock=time.perf_counter):
                seen["training"] = [se.canonical_json(c) for c, _ in training]
                seen["args"] = (arm, budget, seed)
                return {"status": "PASS", "reason": "", "counts": {}, "phases": {},
                        "found": [], "discrepancies": [], "seconds": 0.0, "bits": 0,
                        "min_training_J": 0, "elite_threshold": 0, "elite_size": 0,
                        "accounting": {}}

            spec = {"kind": mw.KIND, "fixture_dir": str(tmp), "fixture_id": "t",
                    "family": "scalar", "program_sha256": "x", "expected_sha256": digests,
                    "arm": "one_bit", "learner_arm": "one_bit", "search_seed": None,
                    "budget_seconds": 0.1, "repetition": 0}
            with mock.patch.object(mw.om, "learn_and_propose", spy):
                mw.measure(spec)
        self.assertEqual(sorted(seen["training"]), sorted(parts["train"]))
        self.assertFalse(set(seen["training"]) & set(parts["test"] + parts["validation"]))

    def test_split_is_the_canonical_sort_then_seeded_permutation(self):
        from research import optimization_fixtures as of

        identities = [f"id{i:03d}" for i in range(41)]
        parts = of.split(list(reversed(identities)))
        self.assertEqual((len(parts["train"]), len(parts["validation"]), len(parts["test"])),
                         (20, 10, 11))
        again = of.split(identities)
        self.assertEqual(parts, again)

    def test_elite_threshold_includes_ties_at_the_order_statistic(self):
        from research import optimization_models as om

        self.assertEqual(om.elite_threshold([5, 1, 1, 1, 9, 9, 9, 9, 9, 9, 9]), 1)
        self.assertEqual(om.elite_threshold(list(range(20, 0, -1))), 2)


class ExportAudit(unittest.TestCase):
    def test_audit_refuses_planted_serial_fallback_and_exec(self):
        from research import optimization_export as ox

        source, _ = ox.assemble("cap512_wider", "cached", None)
        self.assertEqual(ox.audit(source), [])
        self.assertTrue(ox.audit(source + "\nmachine.serial_compile({})\n"))
        self.assertTrue(ox.audit(source + "\nexec('1')\n"))
        self.assertTrue(ox.audit(source + "\ndef compile_program(p):\n    return p\n"))
