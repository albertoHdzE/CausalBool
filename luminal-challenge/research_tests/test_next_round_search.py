"""Stage R and Stage D correctness of the successor solver (next round 1.0).

Real boundaries only: the pinned validator checks what is accepted, the frozen
owner ``objective_index_search`` is the parity reference, and the independent
oracle enumerates declared domains. Every test that could pass vacuously
asserts its denominator.

The R1 regression is written once (``interruption_scenario``) and run against
both the frozen owner and the successor: it must fail on the first and pass on
the second. ``FrozenOwnerStillHasTheDefect`` asserts the failure so that the
regression cannot silently lose its power.
"""

from __future__ import annotations

import unittest
from unittest import mock

import machine

import direct_contract as dc

from research import next_round_search as nrs
from research import objective_index_search as ois
from research import objective_index_validation as oiv
from research import structural_encoding as se
from research import structural_oracle as so

from tests_direct import generate_programs as gp


CELLS = (("a4", "heap"), ("a4", "dfs"), ("a3", "heap"), ("a3", "dfs"))


def _bootstrap(program):
    return oiv.bootstrap(program)


def _j(facts, times, addresses):
    return (max(times.values()) + 1) * dc.footprint(facts, addresses)


def _key(times, addresses):
    return (tuple(sorted((int(k), v) for k, v in times.items())),
            tuple(sorted(addresses.items())))


class _Clock:
    """A deterministic clock: ``base`` plus ``step`` per reading, plus jumps."""

    def __init__(self, step: float = 0.0) -> None:
        self.now = 0.0
        self.step = step
        self.readings = 0

    def __call__(self) -> float:
        self.readings += 1
        self.now += self.step
        return self.now


def interruption_scenario(module, *, when: str, jump: float, budget: float = 5.0,
                          query_seconds: float = 0.1, seed: int = 800004,
                          learner_factory=None, max_interruptions=None, **kwargs):
    """Force deadline expiry around candidate validation; count what happens.

    ``when="during"`` advances the clock inside the pinned validator of a
    strict-improvement candidate; ``when="before"`` advances it on entering
    ``consider`` for a strict-improvement candidate, so the pre-validation check
    fires. ``jump`` is how far the clock moves: past the query allowance only
    (query deadline) or past the whole budget (global deadline).
    ``max_interruptions`` stops forcing after that many jumps.
    Returns the internal count (summed over every acceptor) and the record.
    """

    program = gp.additional_program(seed)
    facts, times, addresses = _bootstrap(program)
    # 1e-5 s per reading: a query allowance of 0.1 s is 10^4 readings, so
    # scenarios that continue after a query-level interruption stay fast.
    clock = _Clock(step=1e-5)
    state = {"candidate": False, "internal": 0, "forced": 0, "reports": []}
    real_check = machine.check_compilation
    real_consider = module._Acceptor.consider

    def may_force():
        return max_interruptions is None or state["forced"] < max_interruptions

    def late_check(prog, compiled):
        result = real_check(prog, compiled)
        if state["candidate"] and when == "during" and may_force():
            clock.now += jump
            state["forced"] += 1
        return result

    def consider(self, node_state):
        cycles, scratch, product = se.objective(self.facts, node_state.times,
                                                node_state.addresses)
        strict = self.best is None or product < self.best
        if strict and when == "before" and may_force():
            identity = se.object_digest(se.normalise_compilation(
                self.facts, dc.compilation(self.facts, node_state.times, node_state.addresses)))
            if identity not in self.seen:
                clock.now += jump
                state["forced"] += 1
        before = self.report.interrupted_validations
        state["candidate"] = True
        try:
            return real_consider(self, node_state)
        finally:
            state["candidate"] = False
            state["internal"] += self.report.interrupted_validations - before

    with mock.patch.object(machine, "check_compilation", late_check), \
            mock.patch.object(module._Acceptor, "consider", consider):
        best_t, best_a, record = module.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=budget,
            query_seconds=query_seconds, clock=clock, learner_factory=learner_factory,
            **kwargs)
    return {"program": program, "facts": facts, "bootstrap": (times, addresses),
            "best": (best_t, best_a), "record": record, "internal": state["internal"],
            "forced": state["forced"]}


def returned_count(record) -> int:
    """The repaired name when present; the frozen owner's only count otherwise."""

    if "interrupted_validation_total" in record:
        return record["interrupted_validation_total"]
    return sum(item.get("count", 0) for item in record["interrupted_attempts"]
               if item.get("phase") == "validation")


def _assert_validated_no_worse(test, result):
    program, facts = result["program"], result["facts"]
    best_t, best_a = result["best"]
    compiled = dc.compilation(facts, best_t, best_a)
    cycles = machine.check_compilation(program, compiled)
    for case in program["cases"]:
        machine.check_case(program, compiled, case)
    test.assertLessEqual(cycles * machine.scratch_footprint(program, compiled),
                         _j(facts, *result["bootstrap"]))


class _Fake:
    """A learner that observes, is never READY, and so never validates."""

    validations = 0
    rejected = []
    continued = None
    reason = "fake"
    validation_budget = 0

    def __init__(self, domain):
        pass

    def observe(self, item):
        pass

    def prepare(self, deadline):
        return "EXPIRED"

    def step(self, *args, **kwargs):
        return ("exhausted",)

    def summary(self):
        return {"status": "fake"}


# --------------------------------------------------------------------------
# R1: interruption accounting
# --------------------------------------------------------------------------


class InterruptionAccounting(unittest.TestCase):
    """Every scenario: returned count equals the internal count; nothing late accepted."""

    def _check(self, result, *, expected_status_prefix=None):
        record = result["record"]
        self.assertGreater(result["internal"], 0, "scenario forced no interruption")
        self.assertEqual(returned_count(record), result["internal"])
        self.assertEqual(record["interrupted_validation_total"], result["internal"])
        per_query = record["interrupted_validations_per_query"]
        self.assertEqual(sum(item["count"] for item in per_query), result["internal"])
        self.assertEqual(record["interrupted_validation_queries"], len(per_query))
        self.assertEqual(len({(i["epoch"], i["query"]) for i in per_query}), len(per_query))
        logged = sum(q["interrupted_validations"] for q in record["queries"])
        self.assertEqual(logged, result["internal"])
        self.assertEqual(record["discrepancy_count"], 0)
        _assert_validated_no_worse(self, result)
        if expected_status_prefix:
            for item in per_query:
                self.assertTrue(item["status"].startswith(expected_status_prefix), item)
        return record

    def test_during_validation_global_deadline_no_learner(self):
        result = interruption_scenario(nrs, when="during", jump=10.0)
        record = self._check(result, expected_status_prefix="UNKNOWN_DEADLINE")
        self.assertEqual(result["internal"], 1)
        self.assertEqual(record["interrupted_validation_queries"], 1)
        self.assertEqual(record["accepted"], 0)
        self.assertEqual(result["best"], result["bootstrap"])

    def test_before_validation_global_deadline_no_learner(self):
        result = interruption_scenario(nrs, when="before", jump=10.0)
        record = self._check(result, expected_status_prefix="UNKNOWN_DEADLINE")
        self.assertEqual(result["internal"], 1)
        self.assertEqual(record["accepted"], 0)
        self.assertEqual(result["best"], result["bootstrap"])

    def test_during_validation_query_deadline_only(self):
        # The jump passes one query's 0.1 s allowance but not the 5 s budget.
        result = interruption_scenario(nrs, when="during", jump=0.2, max_interruptions=1)
        record = self._check(result, expected_status_prefix="UNKNOWN_ALLOWANCE")
        self.assertEqual(result["internal"], 1)
        self.assertNotEqual(record["stopped_because"], "deadline")

    def test_before_validation_query_deadline_only(self):
        result = interruption_scenario(nrs, when="before", jump=0.2, max_interruptions=1)
        self._check(result, expected_status_prefix="UNKNOWN_ALLOWANCE")
        self.assertEqual(result["internal"], 1)

    def test_multiple_interrupted_validations_across_queries(self):
        # Every strict candidate overruns its own query allowance; the global
        # budget absorbs many such queries.
        result = interruption_scenario(nrs, when="during", jump=0.2, budget=100.0)
        record = self._check(result, expected_status_prefix="UNKNOWN_ALLOWANCE")
        self.assertGreaterEqual(record["interrupted_validation_queries"], 2)
        self.assertEqual(record["accepted"], 0)
        self.assertEqual(result["best"], result["bootstrap"])

    def test_learner_path_counts_once(self):
        result = interruption_scenario(nrs, when="during", jump=10.0, learner_factory=_Fake)
        self._check(result)
        self.assertEqual(result["internal"], 1)

    def test_learner_path_query_deadline_only(self):
        result = interruption_scenario(nrs, when="during", jump=0.2, max_interruptions=1,
                                       learner_factory=_Fake)
        self._check(result)
        self.assertEqual(result["internal"], 1)

    def test_zero_interruption_controls(self):
        compared = 0
        for seed in (800000, 800004, 800011):
            for catalog, traversal in CELLS:
                program = gp.additional_program(seed)
                facts, times, addresses = _bootstrap(program)
                _, _, record = nrs.multiscale_optimise(
                    program, facts, times, addresses, budget_seconds=1e6, query_seconds=1e6,
                    slice_seconds=1e6, clock=_Clock(1e-7), catalog=catalog,
                    traversal=traversal, node_ceiling=20_000)
                self.assertEqual(record["interrupted_validation_total"], 0)
                self.assertEqual(record["interrupted_validation_queries"], 0)
                self.assertEqual(record["interrupted_validations_per_query"], [])
                self.assertEqual(record["construction_interruption_count"], 0)
                compared += 1
        self.assertEqual(compared, 12)

    def test_construction_interruptions_are_separate(self):
        # A zero budget: every query is refused before construction; no
        # validation is attempted, so the validation counts stay zero.
        program = gp.additional_program(800004)
        facts, times, addresses = _bootstrap(program)
        clock = _Clock(0.0)
        _, _, record = nrs.multiscale_optimise(program, facts, times, addresses,
                                               budget_seconds=0.0, clock=clock)
        self.assertEqual(record["interrupted_validation_total"], 0)
        # The overall deadline check precedes the first slice: nothing starts.
        self.assertEqual(record["stopped_because"], "deadline")

        # A construction that itself overruns the allowance: the clock jumps
        # inside domain construction, before any node is popped.
        real = se.Domain.from_record
        jumped = {"n": 0}

        def slow(record_, memo=None):
            domain = real(record_, memo=memo)
            if jumped["n"] == 0:
                clock.now += 0.5
                jumped["n"] += 1
            return domain

        clock = _Clock(1e-5)
        with mock.patch.object(se.Domain, "from_record", staticmethod(slow)):
            _, _, record = nrs.multiscale_optimise(program, facts, times, addresses,
                                                   budget_seconds=5.0, clock=clock)
        self.assertEqual(jumped["n"], 1)
        self.assertEqual(record["construction_interruption_count"], 1)
        self.assertEqual(record["interrupted_validation_total"], 0)


class FrozenOwnerStillHasTheDefect(unittest.TestCase):
    """The same regression fails on the frozen owner (the evidence of power)."""

    def test_frozen_non_learner_returns_zero_for_one_internal_interruption(self):
        result = interruption_scenario(ois, when="during", jump=10.0)
        self.assertEqual(result["internal"], 1)
        self.assertEqual(returned_count(result["record"]), 0)
        self.assertNotIn("interrupted_validation_total", result["record"])

    def test_frozen_learner_path_counted(self):
        result = interruption_scenario(ois, when="during", jump=10.0, learner_factory=_Fake)
        self.assertEqual(returned_count(result["record"]), result["internal"])


class DecisionParityWithFrozenOwner(unittest.TestCase):
    """The repair changes reporting only: same decisions under a deterministic clock."""

    def _run(self, module, program, clock_step, **kwargs):
        facts, times, addresses = _bootstrap(program)
        trace = []
        best_t, best_a, record = module.multiscale_optimise(
            program, facts, times, addresses, clock=_Clock(clock_step), trace=trace, **kwargs)
        return best_t, best_a, record, trace

    def test_default_cell_equals_frozen_owner(self):
        compared = 0
        for seed in list(range(800000, 800010)) + [800014, 800021, 800033]:
            program = gp.additional_program(seed)
            for kwargs, step in (({"budget_seconds": 0.1}, 2e-6),
                                 ({"budget_seconds": 1e6, "query_seconds": 1e6,
                                   "slice_seconds": 1e6, "node_ceiling": 30_000}, 1e-7)):
                t0, a0, r0, tr0 = self._run(ois, program, step, **kwargs)
                t1, a1, r1, tr1 = self._run(nrs, program, step, **kwargs)
                self.assertEqual((t0, a0), (t1, a1))
                self.assertEqual(tr0, tr1)
                for field in ("statuses", "accepted", "epochs", "catalog_sizes",
                              "stopped_because", "aggregate", "queries_not_started",
                              "discrepancy_count"):
                    self.assertEqual(r0[field], r1[field], field)
                self.assertEqual([{k: v for k, v in i.items()
                                   if k not in ("elapsed_seconds", "epoch", "query")}
                                  for i in r1["improvements"]], r0["improvements"])
                self.assertEqual(r0["propagation"], r1["propagation"])
                compared += len(tr0)
        self.assertGreater(compared, 10_000)

    def test_interrupted_scenarios_keep_frozen_decisions(self):
        for kwargs in ({"when": "during", "jump": 10.0}, {"when": "before", "jump": 10.0},
                       {"when": "during", "jump": 0.2, "budget": 100.0}):
            old = interruption_scenario(ois, **kwargs)
            new = interruption_scenario(nrs, **kwargs)
            self.assertEqual(old["best"], new["best"])
            self.assertEqual(old["internal"], new["internal"])
            for field in ("statuses", "accepted", "stopped_because", "aggregate"):
                self.assertEqual(old["record"][field], new["record"][field], field)


# --------------------------------------------------------------------------
# D: the 2x2 ablation
# --------------------------------------------------------------------------


class TraversalExhaustiveAgreement(unittest.TestCase):
    """DFS stack and discrepancy heap enumerate the same improving set."""

    def test_object_sets_and_minima_agree_with_the_oracle(self):
        thresholds = objects = 0
        for record in list(oiv.original_fixtures()) + oiv.recipe_fixtures(920000, 10):
            record = dict(record, target=None)
            facts = dc.derive(record["program"])
            incumbent = record["incumbent"]
            times = se.issue_cycles_of(record["program"], incumbent["bundles"])
            addresses = dict(incumbent["scratch"])
            window = tuple(record["selected_operations"])
            uncapped = so.enumerate_feasible(record, oiv.ORACLE_MAX)["feasible"]
            products = sorted({x["product"] for x in uncapped})
            j0 = _j(facts, times, addresses)
            for threshold in sorted(set([j0] + [p + 1 for p in products])):
                caps = nrs.product_caps(facts, times, addresses, window, objective=threshold)
                if caps["status"] != "OK":
                    continue
                try:
                    capped = nrs.capped_record(record, facts, caps)
                except nrs.dk.Infeasible:
                    continue
                improving = {_key(x["times"], x["addresses"]): x["product"]
                             for x in uncapped if x["product"] < threshold}
                domain = se.Domain.from_record(capped)
                found = {}
                for name, runner in (("dfs", nrs.dfs_enumerate), ("heap", nrs.lds_enumerate)):
                    out = runner(domain, incumbent, threshold)
                    self.assertEqual(out["status"], "EXHAUSTED")
                    found[name] = {_key({str(k): v for k, v in x["times"].items()},
                                        x["addresses"]): x["product"]
                                   for x in out["collected"].values()}
                self.assertEqual(found["dfs"], improving)
                self.assertEqual(found["heap"], improving)
                if improving:
                    self.assertEqual(min(found["dfs"].values()), min(improving.values()))
                thresholds += 1
                objects += len(improving)
        self.assertGreater(thresholds, 50)
        self.assertGreater(objects, 500)

    def test_stack_order_is_recursive_depth_first_low_rank_first(self):
        compared = 0
        for record in list(oiv.original_fixtures()) + oiv.recipe_fixtures(920000, 10):
            record = dict(record, target=None)
            facts = dc.derive(record["program"])
            incumbent = record["incumbent"]
            times = se.issue_cycles_of(record["program"], incumbent["bundles"])
            addresses = dict(incumbent["scratch"])
            # The uncapped declared domain and a loose bound: order is the object.
            domain = se.Domain.from_record(record)
            threshold = 10 * _j(facts, times, addresses)
            report = nrs._new_report(domain, "ref", incumbent)
            expander = nrs.Expander(domain, "propagate", nrs.PropagationStats(), report)
            reference = []

            def visit(node):
                reference.append((node.disc, node.lb, node.ranks))
                if expander.is_leaf(node):
                    return
                for child in list(expander.children(node, lambda: threshold)):
                    visit(child)

            root = expander.root(threshold)
            if root is not None:
                visit(root)
            out = nrs.dfs_enumerate(domain, incumbent, threshold)
            self.assertEqual(out["pop_order"], reference)
            compared += len(reference)
        self.assertGreater(compared, 1000)


class AblationController(unittest.TestCase):
    def _traces(self, program, catalog, traversal, resident, slice_nodes):
        facts, times, addresses = _bootstrap(program)
        trace = []
        best_t, best_a, record = nrs.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=1e6, query_seconds=1e6,
            slice_seconds=1e6, slice_nodes=slice_nodes, resident_limit=resident, trace=trace,
            catalog=catalog, traversal=traversal,
            # A per-query node limit far below the aggregate ceiling makes each
            # query's stopping point independent of the interleaving (the
            # aggregate ceiling, when binding, truncates different queries).
            limits=dict(nrs.PER_QUERY_LIMITS, search_max_nodes=600))
        by_query = {}
        for index, ranks in trace:
            by_query.setdefault(index, []).append(ranks)
        return best_t, best_a, record, by_query

    def test_resumed_prefixes_equal_uninterrupted_for_every_cell(self):
        for catalog, traversal in CELLS:
            compared = 0
            for seed in range(800000, 800100, 2):
                program = gp.additional_program(seed)
                t1, a1, r1, q1 = self._traces(program, catalog, traversal, 1, 10**9)
                t2, a2, r2, q2 = self._traces(program, catalog, traversal, 8, 7)
                if r1["accepted"] or r2["accepted"]:
                    continue
                self.assertEqual(r1["stopped_because"], "pass_complete")
                self.assertEqual(r2["stopped_because"], "pass_complete")
                self.assertEqual(q1, q2, (catalog, traversal, seed))
                self.assertEqual((t1, a1), (t2, a2))
                compared += sum(len(v) for v in q1.values())
            self.assertGreater(compared, 100, (catalog, traversal))

    def test_a3_catalog_is_the_product_window_plan(self):
        program = gp.additional_program(800007)
        facts, times, addresses = _bootstrap(program)
        catalog = nrs.a3_catalog(facts, times, addresses)
        self.assertEqual([c["window"] for c in catalog],
                         ois.product_window_plan(facts, times, addresses))
        self.assertTrue(all(c["radius"] == 2 for c in catalog))
        self.assertGreater(len(catalog), 0)

    def test_frontier_limit_is_unknown_never_unsat_for_the_stack(self):
        program = gp.additional_program(800001)
        facts, times, addresses = _bootstrap(program)
        seen = 0
        for catalog in ("a4", "a3"):
            _, _, record = nrs.multiscale_optimise(program, facts, times, addresses,
                                                   budget_seconds=0.5, frontier_limit=3,
                                                   catalog=catalog, traversal="dfs")
            for query in record["queries"]:
                if query["status"] == "UNSAT":
                    self.assertEqual(query["frontier_left"], 0)
                if query["status"] == "UNKNOWN_FRONTIER_LIMIT":
                    self.assertGreater(query["frontier_left"], 3)
                    seen += 1
        self.assertGreater(seen, 0)

    def test_aggregate_node_ceiling_is_never_exceeded(self):
        program = gp.additional_program(800003)
        facts, times, addresses = _bootstrap(program)
        for catalog, traversal in CELLS:
            for ceiling in (500, 1000, 10_000):
                _, _, record = nrs.multiscale_optimise(
                    program, facts, times, addresses, budget_seconds=1e6, query_seconds=1e6,
                    slice_seconds=1e6, node_ceiling=ceiling, catalog=catalog,
                    traversal=traversal)
                self.assertLessEqual(record["aggregate"]["nodes"], ceiling)

    def test_validator_rejection_is_retained_for_every_cell(self):
        program = gp.additional_program(800004)
        facts, times, addresses = _bootstrap(program)

        def reject(program, compiled, case):
            raise machine.CompileError("planted rejection")

        for catalog, traversal in CELLS:
            with mock.patch.object(machine, "check_case", reject):
                t, a, record = nrs.multiscale_optimise(program, facts, times, addresses,
                                                       budget_seconds=0.2, catalog=catalog,
                                                       traversal=traversal)
            self.assertGreater(record["discrepancy_count"], 0)
            self.assertEqual(record["accepted"], 0)
            self.assertEqual((t, a), (times, addresses))

    def test_every_cell_returns_a_validated_incumbent_no_worse_than_bootstrap(self):
        checked = 0
        public = [machine.load_program(p) for p in sorted(
            (oiv.oc.ROOT / ".reference" / "programs").glob("*.json"))]
        for program in [gp.additional_program(s) for s in range(800000, 800012)] + public:
            facts, times, addresses = _bootstrap(program)
            j0 = _j(facts, times, addresses)
            for catalog, traversal in CELLS:
                t, a, record = nrs.multiscale_optimise(program, facts, times, addresses,
                                                       budget_seconds=0.05, catalog=catalog,
                                                       traversal=traversal)
                compiled = dc.compilation(facts, t, a)
                cycles = machine.check_compilation(program, compiled)
                for case in program["cases"]:
                    machine.check_case(program, compiled, case)
                self.assertLessEqual(cycles * machine.scratch_footprint(program, compiled), j0)
                self.assertEqual(record["discrepancy_count"], 0)
                self.assertEqual(record["budget_renewals"], 0)
                previous = j0
                last = 0.0
                for item in record["improvements"]:
                    self.assertLess(item["to"], previous)
                    self.assertGreaterEqual(item["elapsed_seconds"], last)
                    previous, last = item["to"], item["elapsed_seconds"]
                checked += 1
        self.assertEqual(checked, 80)

    def test_unknown_cell_is_refused(self):
        program = gp.additional_program(800000)
        facts, times, addresses = _bootstrap(program)
        with self.assertRaises(ValueError):
            nrs.multiscale_optimise(program, facts, times, addresses, budget_seconds=0.01,
                                    catalog="a5")


if __name__ == "__main__":
    unittest.main()
