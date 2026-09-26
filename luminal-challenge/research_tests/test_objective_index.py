"""Correctness tests of the A1-A4 solver ladder (objective-index protocol 1.0).

Real boundaries only: the independent oracle enumerates declared domains, the
pinned validator checks every accepted object, and the parity tests compare
against the accepted owners (``structural_search.search`` and
``optimization_search.optimise``) rather than against mocks of our own code.
Every test that could pass vacuously asserts its denominator.
"""

from __future__ import annotations

import json
import time
import unittest
from pathlib import Path
from unittest import mock

import machine

import direct_compiler as dcomp
import direct_contract as dc
import direct_constraints as dk
import schema_index as si

from research import objective_index_replay as oir
from research import objective_index_search as ois
from research import objective_index_validation as oiv
from research import optimization_search as osr
from research import run_structural_experiments as rse
from research import structural_encoding as se
from research import structural_oracle as so
from research import structural_search as ss

from tests_direct import generate_programs as gp

ROOT = Path(__file__).resolve().parents[1]


def _bootstrap(program):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, se.issue_cycles_of(program, compiled["bundles"]), dict(compiled["scratch"])


def _development(count=100):
    return [gp.additional_program(seed) for seed in range(800000, 800000 + count)]


def _public():
    root = ROOT / ".reference" / "programs"
    return [machine.load_program(path) for path in sorted(root.glob("*.json"))]


def _original_fixtures():
    return oiv.original_fixtures()


def _recipe_fixtures(first=920000, count=30, cartesian_max=12_000):
    return oiv.recipe_fixtures(first, count, cartesian_max)


def _all_fixture_records():
    return list(_original_fixtures()) + _recipe_fixtures()


def _key(times, addresses):
    return (tuple(sorted((int(k), v) for k, v in times.items())),
            tuple(sorted(addresses.items())))


BIG = si.Budget(seconds=1e6, max_cover=4096, max_visited=10_000_000, max_records=1_000_000)


# --------------------------------------------------------------------------
# Section 4: the integer-cap lemma
# --------------------------------------------------------------------------


class IntegerCapLemma(unittest.TestCase):
    def test_arithmetic_every_small_case(self):
        checked = 0
        for j0 in range(1, 61):
            for lc in range(1, j0 + 1):
                for ls in range(1, j0 + 1):
                    ccap, scap = (j0 - 1) // ls, (j0 - 1) // lc
                    for c in range(lc, j0 + 1):
                        for s in range(ls, j0 + 1):
                            if c * s <= j0 - 1:
                                checked += 1
                                self.assertLessEqual(c, ccap)
                                self.assertLessEqual(s, scap)
        self.assertGreater(checked, 10_000)

    def test_zero_objective_and_caps_below_bounds(self):
        program = gp.additional_program(800000)
        facts, times, addresses = _bootstrap(program)
        window = tuple(range(min(4, facts.count)))
        caps = ois.product_caps(facts, times, addresses, window, objective=0)
        self.assertEqual(caps["status"], "ZERO_OBJECTIVE")
        caps = ois.product_caps(facts, times, addresses, window, objective=1)
        self.assertEqual(caps["status"], "NO_STRICT_IMPROVEMENT")
        with self.assertRaises(ValueError):
            ois.capped_record({}, facts, caps)

    def test_capped_domain_keeps_every_strict_improvement_at_every_threshold(self):
        """Oracle of the UNCAPPED neighborhood versus the capped domain.

        ``objective_index_validation.cap_lemma``: at every threshold the strict
        improvements of each exhaustible fixture's uncapped declared domain
        equal those of the capped domain by oracle, by the A2-order DFS, by
        A3's propagated DFS and by A4's discrepancy heap run to exhaustion.
        """

        result = oiv.cap_lemma(_all_fixture_records())
        self.assertEqual(result["status"], "PASS", result["violations"][:5])
        self.assertGreaterEqual(result["fixtures"], 40)
        self.assertGreater(result["thresholds"], 100)
        self.assertGreater(result["thresholds_with_improvements"], 20)
        self.assertGreater(result["improving_objects_compared"], 200)

    def test_product_record_is_the_capped_neighborhood(self):
        checked = 0
        for program in _development(20):
            facts, times, addresses = _bootstrap(program)
            for window in ois.product_window_plan(facts, times, addresses)[:3]:
                caps = ois.product_caps(facts, times, addresses, window)
                if caps["status"] != "OK":
                    continue
                try:
                    record = ois.product_record("x", program, facts, times, addresses, window,
                                                2, caps)
                except dk.Infeasible:
                    continue
                checked += 1
                self.assertIsNone(record["target"])
                for key, values in record["time_domains"].items():
                    t = times[int(key)]
                    self.assertEqual(values, list(range(max(0, t - 2),
                                                        min(t + 2, caps["Ccap"] - 1) + 1)))
                for name, values in record["address_domains"].items():
                    self.assertEqual(values, rse.physical_address_domain(facts, name,
                                                                         caps["Scap"]))
                se.Domain.from_record(record)
        self.assertGreater(checked, 20)


class TradeOffCoverage(unittest.TestCase):
    def test_product_domain_covers_the_lead_counterexample_pair(self):
        """(12, 8) beats (10, 10) and lies outside every old target rectangle."""

        import direct_optimizer as dopt

        class Facts:
            horizon = 1000

            def cycle_lower_bound(self):
                return 1

            def memory_lower_bound(self):
                return 1

        targets = dopt.targets_for(Facts(), 10, 10)
        self.assertFalse(any(12 <= tc and 8 <= tm for tc, tm in targets))
        lc, ls, j0 = 1, 1, 100
        self.assertLessEqual(12, min(Facts.horizon, (j0 - 1) // ls))
        self.assertLessEqual(8, (j0 - 1) // lc)
        self.assertLess(12 * 8, j0)


# --------------------------------------------------------------------------
# Parity with the accepted owners
# --------------------------------------------------------------------------


def _parity_fields(report):
    return (report.status, report.nodes, report.pruned, report.completions, report.validations,
            report.dead_ends, report.best_product, report.best_identity, report.improved,
            report.interrupted_validations, len(report.rejected_completions))


class OwnerParity(unittest.TestCase):
    def test_ss_bound_replica_equals_structural_search_node_for_node(self):
        checked = 0
        for program in _development(40) + _public():
            facts, times, addresses = _bootstrap(program)
            cycles = max(times.values()) + 1
            memory = dc.footprint(facts, addresses)
            records = []
            for window in ois.product_window_plan(facts, times, addresses)[:2]:
                caps = ois.product_caps(facts, times, addresses, window)
                if caps["status"] == "OK":
                    try:
                        records.append(ois.product_record("p", program, facts, times, addresses,
                                                          window, 2, caps))
                    except dk.Infeasible:
                        pass
            for target in dopt_targets(facts, cycles, memory)[:1]:
                for window in ois.dopt.windows_for(facts, times, addresses, True)[:2]:
                    try:
                        records.append(rse.matched_window_record(
                            "m", "matched", program, facts, times, addresses, window, *target))
                    except dk.Infeasible:
                        pass
            for record in records:
                domain = se.Domain.from_record(record)
                budget = si.Budget(seconds=1e6, max_cover=4096, max_visited=3000,
                                   max_records=100_000)
                owner = ss.search(domain, record["incumbent"], "structural_bound", budget)
                replica, _ = ois.propagated_search(domain, record["incumbent"], budget,
                                                   mode="ss_bound")
                self.assertEqual(_parity_fields(owner), _parity_fields(replica), record["id"])
                checked += 1
        self.assertGreater(checked, 100)

    def test_a1_equals_optimization_search_capnull_matched_under_fixed_work(self):
        limits = dict(ois.PER_QUERY_LIMITS, search_max_nodes=400)
        checked = 0
        for program in _development(25) + _public():
            facts, times, addresses = _bootstrap(program)
            t1, a1, r1 = ois.sequential_optimise(
                program, facts, times, addresses, arm="A1_deadline_control",
                budget_seconds=1e6, query_seconds=1e6, node_ceiling=30_000, limits=limits)
            t2, a2, r2 = osr.optimise(
                program, facts, times, addresses, config="capnull_matched",
                budget_seconds=1e6, build="cached", query_seconds=1e6, node_ceiling=30_000,
                limits=dict(osr.PER_QUERY_LIMITS, search_max_nodes=400))
            self.assertEqual((t1, a1), (t2, a2))
            self.assertEqual([(i["from"], i["to"]) for i in r1["improvements"]],
                             [(i["from"], i["to"]) for i in r2["improvements"]])
            self.assertEqual(r1["attempted_queries"], r2["attempted_queries"])
            self.assertEqual([q["status"] for q in r1["queries"]],
                             [q["status"] for q in r2["queries"]])
            self.assertEqual(r1["stopped_because"], r2["stopped_because"])
            checked += 1
        self.assertEqual(checked, 33)

    def test_propagation_prunes_a_subsequence_and_keeps_the_same_optimum(self):
        checked = fewer = 0
        for program in _development(40):
            facts, times, addresses = _bootstrap(program)
            for window in ois.product_window_plan(facts, times, addresses)[:3]:
                caps = ois.product_caps(facts, times, addresses, window)
                if caps["status"] != "OK":
                    continue
                try:
                    record = ois.product_record("p", program, facts, times, addresses, window,
                                                2, caps)
                except dk.Infeasible:
                    continue
                domain = se.Domain.from_record(record)
                budget = si.Budget(seconds=1e6, max_cover=4096, max_visited=200_000,
                                   max_records=100_000)
                plain = ss.search(domain, record["incumbent"], "structural_bound", budget)
                propagated, _ = ois.propagated_search(domain, record["incumbent"], budget)
                if "UNKNOWN" in (plain.status, propagated.status):
                    continue
                checked += 1
                self.assertEqual(plain.status, propagated.status)
                self.assertEqual(plain.best_product, propagated.best_product)
                self.assertEqual(plain.best_identity, propagated.best_identity)
                self.assertLessEqual(propagated.nodes, plain.nodes)
                fewer += propagated.nodes < plain.nodes
        self.assertGreater(checked, 60)
        self.assertGreater(fewer, 0)


def dopt_targets(facts, cycles, memory):
    return ois.dopt.targets_for(facts, cycles, memory)


# --------------------------------------------------------------------------
# Section 5: exhaustive propagation soundness
# --------------------------------------------------------------------------


class PropagationSoundness(unittest.TestCase):
    def test_every_deletion_prune_and_bound_holds_for_every_feasible_completion(self):
        result = oiv.propagation_soundness(_all_fixture_records())
        self.assertEqual(result["status"], "PASS", result["violations"][:5])
        totals = result["totals"]
        self.assertGreater(totals["events"], 500)
        self.assertGreater(totals["removed_values"], 50)
        self.assertGreater(totals["pruned"], 10)
        self.assertGreater(totals["improving_objects"], 0)
        self.assertGreater(totals["certificates_replayed"], 100)

    def test_planted_unsound_rules_are_detected(self):
        result = oiv.planted_mutations(_all_fixture_records())
        self.assertEqual(result["status"], "PASS", result)

    def test_certificate_replay_rejects_forged_certificates(self):
        program = gp.additional_program(800002)
        facts = dc.derive(program)
        u, v, lag = next((u, v, lag) for v in range(facts.count)
                         for u, lag in facts.predecessors[v].items())
        self.assertEqual(oir.replay(facts, ("PU", u, v, lag, 10, (10 - lag + 1,))), [])
        self.assertTrue(oir.replay(facts, ("PU", u, v, lag, 10, (10 - lag,))))
        self.assertTrue(oir.replay(facts, ("PU", u, v, lag + 5, 10, (99,))))
        self.assertTrue(oir.replay(facts, ("PB", 3, 4, 13, ("fixed",), ("fixed_end",))))
        self.assertEqual(oir.replay_stream(facts, [])["status"], "EMPTY")


# --------------------------------------------------------------------------
# Canonical ranks
# --------------------------------------------------------------------------


class CanonicalRanks(unittest.TestCase):
    def test_every_propagated_leaf_round_trips_through_the_unchanged_codec(self):
        result = oiv.rank_round_trips(_all_fixture_records())
        self.assertEqual(result["status"], "PASS", result)
        self.assertGreater(result["leaves"], 1000)


# --------------------------------------------------------------------------
# Section 6: A4 catalog and resumable queries
# --------------------------------------------------------------------------


class Catalog(unittest.TestCase):
    def test_round_robin_merge_dedup_and_queues(self):
        program = gp.additional_program(800003)
        facts, times, addresses = _bootstrap(program)
        catalog = ois.build_catalog(facts, times, addresses)
        keys = [(tuple(e["window"]), e["radius"]) for e in catalog]
        self.assertEqual(len(keys), len(set(keys)))
        self.assertEqual([e["queue"] for e in catalog[:4]], [0, 1, 2, 3])
        self.assertEqual(catalog[1]["policy"], "k4_latest")
        latest = tuple(sorted(sorted(range(facts.count), key=lambda op: (-times[op], op))[:4]))
        self.assertEqual(tuple(catalog[1]["window"]), latest)
        self.assertFalse(any(e["radius"] == ois.FULL_RANGE for e in catalog))  # 66 ops
        radii = {e["policy"].split("_")[0]: e["radius"] for e in catalog if e["queue"] in (1, 2, 3)}
        self.assertEqual(radii, {"k4": 4, "k8": 4, "k16": 8})
        contiguous = [tuple(e["window"]) for e in catalog if e["policy"].startswith("k16_contig")]
        self.assertEqual(contiguous[-1][-1], facts.count - 1)

    def test_whole_program_queue_only_for_at_most_sixteen_operations(self):
        program = gp.additional_program(800000)
        facts, times, addresses = _bootstrap(program)
        self.assertLessEqual(facts.count, 16)
        catalog = ois.build_catalog(facts, times, addresses)
        whole = [e for e in catalog if e["radius"] == ois.FULL_RANGE]
        self.assertEqual(len(whole), 1)
        self.assertEqual(tuple(whole[0]["window"]), tuple(range(facts.count)))

    def test_memory_group_follows_the_declared_order(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        live = dc.lifetimes(facts, times)
        group = ois.memory_group(facts, times, addresses, 4)
        self.assertEqual(len(group), 4)
        self.assertEqual(list(group), sorted(group))
        widths = {}
        for cycle in range(0, max(e for _, e in live.values()) + 1):
            widths[cycle] = sum(facts.width[n] for n, (s, e) in live.items() if s <= cycle <= e)
        peak = max(widths.values())
        peak_cycle = min(c for c, w in widths.items() if w == peak)
        first = sorted([n for n, (s, e) in live.items() if s <= peak_cycle <= e],
                       key=lambda n: (-facts.width[n], -(addresses[n] + facts.width[n]),
                                      facts.producers[n]))[0]
        self.assertIn(facts.producers[first], group)


class ResumableQueries(unittest.TestCase):
    def _traces(self, program, resident, slice_nodes):
        facts, times, addresses = _bootstrap(program)
        trace = []
        best_t, best_a, record = ois.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=1e6, query_seconds=1e6,
            slice_seconds=1e6, slice_nodes=slice_nodes, resident_limit=resident, trace=trace)
        by_query = {}
        for index, ranks in trace:
            by_query.setdefault(index, []).append(ranks)
        return best_t, best_a, record, by_query

    def test_sliced_interleaved_queries_pop_exactly_the_uninterrupted_sequence(self):
        compared = 0
        for seed in (800000, 800005, 800010, 800015, 800020, 800025, 800030, 800035):
            program = gp.additional_program(seed)
            t1, a1, r1, q1 = self._traces(program, 1, 10**9)
            t2, a2, r2, q2 = self._traces(program, 8, 7)
            if r1["accepted"] or r2["accepted"]:
                # An improvement ends an epoch wherever it is found first; only
                # improvement-free runs have a well-defined per-query sequence.
                continue
            self.assertEqual(q1, q2)
            self.assertEqual((t1, a1), (t2, a2))
            compared += sum(len(v) for v in q1.values())
        self.assertGreater(compared, 100)

    def test_frontier_limit_is_unknown_never_unsat(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        _, _, record = ois.multiscale_optimise(program, facts, times, addresses,
                                               budget_seconds=0.5, frontier_limit=3)
        statuses = record["statuses"]
        self.assertGreater(statuses.get("UNKNOWN_FRONTIER_LIMIT", 0), 0)
        for query in record["queries"]:
            if query["status"] == "UNSAT":
                self.assertEqual(query["frontier_left"], 0)
            if query["status"] == "UNKNOWN_FRONTIER_LIMIT":
                self.assertGreater(query["frontier_left"], 3)


# --------------------------------------------------------------------------
# Acceptance safety
# --------------------------------------------------------------------------


class AcceptanceSafety(unittest.TestCase):
    def _domain(self):
        program = gp.additional_program(800004)
        facts, times, addresses = _bootstrap(program)
        for window in ois.product_window_plan(facts, times, addresses):
            caps = ois.product_caps(facts, times, addresses, window)
            if caps["status"] != "OK":
                continue
            record = ois.product_record("p", program, facts, times, addresses, window, 2, caps)
            domain = se.Domain.from_record(record)
            report, _ = ois.propagated_search(domain, record["incumbent"], BIG)
            if report.improved:
                return domain, record
        self.fail("no improving window on the test program")

    def test_a_candidate_whose_validation_crosses_the_deadline_is_not_accepted(self):
        domain, record = self._domain()
        ticks = iter([0.0] * 100000)
        state = {"after": False}

        def clock():
            return 10.0 if state["after"] else next(ticks)

        real_check = machine.check_compilation

        def slow_check(program, compiled):
            result = real_check(program, compiled)
            state["after"] = True
            return result

        with mock.patch.object(machine, "check_compilation", slow_check):
            report, _ = ois.propagated_search(domain, record["incumbent"], BIG, deadline=5.0,
                                              clock=clock)
        self.assertFalse(report.improved)
        self.assertEqual(report.interrupted_validations, 1)
        self.assertEqual(report.status, "UNKNOWN")

    def test_a_validator_rejection_is_retained_and_fails_the_run(self):
        program = gp.additional_program(800004)
        facts, times, addresses = _bootstrap(program)

        def reject(program, compiled, case):
            raise machine.CompileError("planted rejection")

        for arm in ("A2_product_search", "A3_propagated_search", "A4_multiscale_search"):
            with mock.patch.object(machine, "check_case", reject):
                t, a, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                            budget_seconds=0.2)
            self.assertGreater(record["discrepancy_count"], 0, arm)
            self.assertEqual(record["accepted"], 0, arm)
            self.assertEqual((t, a), (times, addresses), arm)

    def test_aggregate_node_ceiling_is_never_exceeded(self):
        program = gp.additional_program(800003)
        facts, times, addresses = _bootstrap(program)
        for arm in ois.ARM_LABELS:
            _, _, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                        budget_seconds=5.0, node_ceiling=500)
            self.assertLessEqual(record["aggregate"]["nodes"], 500, arm)

    def test_every_arm_returns_a_validated_incumbent_no_worse_than_bootstrap(self):
        checked = 0
        for program in _development(15) + _public():
            facts, times, addresses = _bootstrap(program)
            j0 = (max(times.values()) + 1) * dc.footprint(facts, addresses)
            for arm in ois.ARM_LABELS:
                t, a, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                            budget_seconds=0.05)
                compiled = dc.compilation(facts, t, a)
                cycles = machine.check_compilation(program, compiled)
                for case in program["cases"]:
                    machine.check_case(program, compiled, case)
                self.assertLessEqual(cycles * machine.scratch_footprint(program, compiled), j0)
                self.assertEqual(record["discrepancy_count"], 0)
                self.assertEqual(record["budget_renewals"], 0)
                checked += 1
        self.assertEqual(checked, 92)


def _ticker(step=2e-6):
    state = [0.0]

    def clock():
        state[0] += step
        return state[0]

    return clock


class LearnedCompilerPair(unittest.TestCase):
    """The conditional pair exists and is correct before any fixture evaluation."""

    def test_learned_pair_returns_validated_incumbents_under_every_solver(self):
        from research import objective_index_learned as oil

        checked = 0
        for program in _development(12):
            facts, times, addresses = _bootstrap(program)
            j0 = (max(times.values()) + 1) * dc.footprint(facts, addresses)
            for arm in ois.ARM_LABELS:
                for mode in oil.MODES:
                    t, a, record = oil.optimise(program, facts, times, addresses, arm=arm,
                                                budget_seconds=0.15, labels_mode=mode)
                    compiled = dc.compilation(facts, t, a)
                    cycles = machine.check_compilation(program, compiled)
                    for case in program["cases"]:
                        machine.check_case(program, compiled, case)
                    self.assertLessEqual(cycles * machine.scratch_footprint(program, compiled), j0)
                    self.assertEqual(record["discrepancy_count"], 0)
                    self.assertLess(record["seconds"], 0.15 + 0.25)
                    self.assertEqual(record["learned_mode"], mode)
                    checked += 1
        self.assertEqual(checked, 12 * 4 * 2)

    def _learner_domain(self):
        for record in _recipe_fixtures():
            record = dict(record, target=None)
            feasible = so.enumerate_feasible(record, 70_000)["feasible"]
            if len(feasible) >= 60 and len({x["product"] for x in feasible}) >= 3:
                return se.Domain.from_record(record), feasible
        self.fail("no learner domain")

    def test_query_learner_ready_path_shares_pool_and_differs_only_in_labels(self):
        from research import objective_index_learned as oil

        domain, feasible = self._learner_domain()
        best = min(x["product"] for x in feasible)
        observed = [x for x in feasible if x["product"] > best][:40]
        infos = {}
        for mode in oil.MODES:
            learner = oil.QueryLearner(domain, mode)
            for x in observed:
                compilation = json.loads(x["identity"])
                learner.observe({"identity": se.object_digest(compilation),
                                 "product": x["product"], "compilation": compilation})
            self.assertEqual(learner.prepare(time.perf_counter() + 100), "READY", learner.reason)
            self.assertEqual(learner.validations, len(observed))
            outcome = learner.step(min(x["product"] for x in observed),
                                   time.perf_counter() + 100)
            self.assertIn(outcome[0], ("improved", "exhausted"))
            if outcome[0] == "improved":
                self.assertLess(outcome[3], min(x["product"] for x in observed))
                compiled = dc.compilation(domain.facts, outcome[1], outcome[2])
                machine.check_compilation(domain.program, compiled)
            infos[mode] = learner.summary()
        self.assertEqual(infos["tree"]["pool_sha256"], infos["shuffled_tree"]["pool_sha256"])
        self.assertEqual(infos["tree"]["validated"], infos["shuffled_tree"]["validated"])

    def test_model_unavailable_below_twenty_validated_objects(self):
        from research import objective_index_learned as oil

        domain, feasible = self._learner_domain()
        learner = oil.QueryLearner(domain, "tree")
        for x in feasible[:5]:
            compilation = json.loads(x["identity"])
            learner.observe({"identity": se.object_digest(compilation), "product": x["product"],
                             "compilation": compilation})
        self.assertEqual(learner.prepare(time.perf_counter() + 100), "MODEL_UNAVAILABLE")
        self.assertEqual(learner.validations, 5)

    def test_controllers_accept_a_model_improvement_through_the_hooks(self):
        # 800014 has time-limited A3 queries under this tick clock, so the
        # second (model) half of a query is actually reached.
        program = gp.additional_program(800014)
        facts, times, addresses = _bootstrap(program)
        better_t, better_a, better = ois.optimise(program, facts, times, addresses,
                                                  arm="A4_multiscale_search", budget_seconds=0.5)
        self.assertGreater(better["accepted"], 0)
        target = (max(better_t.values()) + 1) * dc.footprint(facts, better_a)

        class Fake:
            validations = 0
            rejected = []
            continued = None
            reason = ""
            validation_budget = 0

            def __init__(self, domain):
                self.fired = False

            def observe(self, item):
                pass

            def prepare(self, deadline):
                return "READY"

            def step(self, best_product, until, hard_deadline=None, first_only=True):
                if not self.fired and target < best_product:
                    self.fired = True
                    return ("improved", better_t, better_a, target)
                return ("exhausted",)

            def summary(self):
                return {"status": "READY"}

        for arm in ("A3_propagated_search", "A4_multiscale_search"):
            t, a, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                        budget_seconds=0.5, query_seconds=0.0004,
                                        clock=_ticker(2e-5), learner_factory=Fake)
            self.assertTrue(any(i.get("source") == "model" for i in record["improvements"]), arm)
            self.assertLessEqual((max(t.values()) + 1) * dc.footprint(facts, a), target, arm)


class CertificateStream(unittest.TestCase):
    def test_fixed_work_runs_have_identical_certificate_digests(self):
        program = gp.additional_program(800002)
        facts, times, addresses = _bootstrap(program)
        digests = []
        for _ in range(2):
            stats = ois.PropagationStats(keep=True)
            ois.sequential_optimise(program, facts, times, addresses,
                                    arm="A3_propagated_search", budget_seconds=1e6,
                                    query_seconds=1e6, node_ceiling=20_000, stats=stats,
                                    limits=dict(ois.PER_QUERY_LIMITS, search_max_nodes=500))
            digests.append((stats.digest(), stats.stream_length, dict(stats.counts)))
            replayed = oir.replay_stream(facts, stats.certificates)
            self.assertEqual(replayed["failure_count"], 0)
        self.assertEqual(digests[0], digests[1])
        self.assertGreater(digests[0][1], 0)


if __name__ == "__main__":
    unittest.main()
