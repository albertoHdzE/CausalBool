"""R1: construction-exit and model-phase accounting of the efficiency baseline R0.

Plan ``CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` section 3, R1. Every test drives
``research.efficiency_search.multiscale_optimise`` with a deterministic clock
and forces ONE initialization exit of the first query, with the clock moved by
a chosen amount inside that initialization. ``PowerOnParent`` shows the same
lead probe returns zero on the parent ``next_round_search`` (the evidence that
these tests can fail), and ``ParityWithParent`` shows the repair changes no
search decision.
"""

from __future__ import annotations

import unittest
from unittest import mock

import machine

import direct_constraints as dk

from research import efficiency_search as es
from research import next_round_search as nrs
from research import objective_index_learned as oil
from research import objective_index_validation as oiv
from research import structural_encoding as se
from research import structural_oracle as so

from tests_direct import generate_programs as gp

SEED = 800000
DFS = {"catalog": "a4", "traversal": "dfs"}


class _Clock:
    def __init__(self, step: float = 0.0) -> None:
        self.now = 0.0
        self.step = step
        self.readings = 0

    def __call__(self) -> float:
        self.readings += 1
        self.now += self.step
        return self.now


def _bootstrap(seed=SEED):
    program = gp.additional_program(seed)
    facts, times, addresses = oiv.bootstrap(program)
    return program, facts, times, addresses


def first_query_exit(module, exit_kind: str, jump: float, *, budget: float = 5.0,
                     query_seconds: float = 0.1, node_ceiling: int = 3000, seed: int = SEED,
                     step: float = 0.0, which: int = 1, **kwargs):
    """Force ``exit_kind`` in the FIRST query's initialization after moving the clock.

    ``exit_kind``: ``caps`` (NO_STRICT_IMPROVEMENT), ``conflict`` (root schedule
    conflict), ``root`` (root prune/inconsistency), ``infeasible``
    (``dk.Infeasible`` from the capped record), ``domain`` (``se.DomainError``)
    or ``normal`` (initialization succeeds). The clock moves by ``jump`` inside
    ``product_caps`` of that query only. ``which`` selects the initialization
    (1 = the first query initialized); the returned ``query`` is that one.
    """

    program, facts, times, addresses = _bootstrap(seed)
    clock = _Clock(step)
    state = {"calls": 0, "window": None}
    real_caps = module.product_caps
    real_record = module.product_record
    real_from_record = se.Domain.from_record
    real_conflict = se.State.schedule_conflict
    real_root = module.Expander.root

    def first():
        return state["calls"] == which

    def caps(*args, **kw):
        state["calls"] += 1
        result = real_caps(*args, **kw)
        if first():
            state["window"] = list(args[3])
            clock.now += jump
            if exit_kind == "caps":
                result = dict(result, status="NO_STRICT_IMPROVEMENT", reason="forced cap proof")
            elif result["status"] != "OK":
                raise AssertionError("the forced query needs an OK cap to reach its exit")
        return result

    def record(*args, **kw):
        if first() and exit_kind == "infeasible":
            raise dk.Infeasible("forced infeasible window")
        return real_record(*args, **kw)

    def from_record(record_, memo=None):
        if first() and exit_kind == "domain":
            raise se.DomainError("forced domain error")
        return real_from_record(record_, memo=memo)

    def conflict(self):
        if first() and exit_kind == "conflict":
            return "forced conflict"
        return real_conflict(self)

    def root(self, best):
        if first() and exit_kind == "root":
            return None
        return real_root(self, best)

    with mock.patch.object(module, "product_caps", caps), \
            mock.patch.object(module, "product_record", record), \
            mock.patch.object(se.Domain, "from_record", staticmethod(from_record)), \
            mock.patch.object(se.State, "schedule_conflict", conflict), \
            mock.patch.object(module.Expander, "root", root):
        best_t, best_a, report = module.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=budget,
            query_seconds=query_seconds, clock=clock, node_ceiling=node_ceiling, **DFS,
            **kwargs)
    # The parent's log has no ``construction_seconds``; its active time holds
    # the same reading for a query that ended at initialization.
    first_query = next(q for q in report["queries"] if q["window"] == state["window"]
                       and q.get("construction_seconds", q["active_seconds"]) is not None
                       and q.get("construction_seconds", q["active_seconds"]) >= jump - 1e-12)
    return {"report": report, "query": first_query, "best": (best_t, best_a),
            "program": program, "facts": facts}


TERMINAL = {"caps": "NO_STRICT_IMPROVEMENT", "conflict": "UNSAT", "root": "UNSAT",
            "infeasible": "INFEASIBLE", "domain": "UNKNOWN_CONSTRUCTION"}


class ConstructionExits(unittest.TestCase):
    """Every exit x {no overrun, exact equality, query expiry, global expiry}."""

    def test_every_terminal_exit_without_overrun_is_in_budget(self):
        for kind, status in TERMINAL.items():
            with self.subTest(kind=kind):
                q = first_query_exit(es, kind, 0.05)["query"]
                r = first_query_exit(es, kind, 0.05)["report"]
                self.assertEqual(q["status"], status)
                self.assertEqual(q["terminal_reason"], status)
                self.assertFalse(q["construction_deadline_exceeded"])
                self.assertFalse(q["interrupted_before_search"])
                self.assertIsNone(q["late_terminal_reason"])
                self.assertAlmostEqual(q["construction_seconds"], 0.05, places=12)
                self.assertEqual(r["construction_overrun_count"], 0)
                self.assertEqual(r["construction_interruption_count"], 0)

    def test_every_terminal_exit_at_exact_deadline_is_late(self):
        # clock 0 -> 0.1 inside initialization; the hard deadline is 0 + 0.1.
        for kind, status in TERMINAL.items():
            with self.subTest(kind=kind):
                result = first_query_exit(es, kind, 0.1)
                q, r = result["query"], result["report"]
                self.assertEqual(q["status"], "UNKNOWN_ALLOWANCE")
                self.assertEqual(q["terminal_reason"], status)
                self.assertTrue(q["late_terminal_reason"].startswith(status))
                self.assertTrue(q["construction_deadline_exceeded"])
                self.assertTrue(q["interrupted_before_search"])
                self.assertEqual(q["construction_past_deadline_seconds"], 0.0)
                self.assertEqual(r["construction_overrun_count"], 1)
                self.assertEqual(r["construction_interruption_count"], 1)
                self.assertEqual(r["late_terminal_reasons"], {status: 1})

    def test_query_expiry_versus_global_expiry(self):
        for kind in TERMINAL:
            with self.subTest(kind=kind):
                query_only = first_query_exit(es, kind, 0.5, budget=5.0)
                self.assertEqual(query_only["query"]["status"], "UNKNOWN_ALLOWANCE")
                global_ = first_query_exit(es, kind, 0.5, budget=0.3)
                self.assertEqual(global_["query"]["status"], "UNKNOWN_DEADLINE")
                for result in (query_only, global_):
                    self.assertEqual(result["report"]["construction_overrun_count"], 1)
                    # Measured from the query's hard deadline min(overall, 0 + 0.1).
                    self.assertAlmostEqual(result["query"]["construction_past_deadline_seconds"],
                                           0.4, places=12)
                self.assertNotEqual(query_only["query"]["status"], global_["query"]["status"])

    def test_nonterminal_overrun_counted_once_and_no_proof(self):
        # Seed 800001: the third initialization is nonterminal (its query
        # expands nodes when nothing is forced); checked, not assumed.
        probe = first_query_exit(es, "normal", 0.0, seed=800001, which=3)["query"]
        self.assertIsNone(probe["terminal_reason"])
        self.assertGreater(probe["nodes"], 0)
        result = first_query_exit(es, "normal", 0.25, seed=800001, which=3)
        q, r = result["query"], result["report"]
        self.assertEqual(q["status"], "UNKNOWN_ALLOWANCE")
        self.assertIsNone(q["terminal_reason"])
        self.assertIsNone(q["late_terminal_reason"])
        self.assertEqual(q["nodes"], 0)
        self.assertTrue(q["construction_deadline_exceeded"])
        self.assertEqual(r["construction_overrun_count"], 1)
        self.assertEqual(r["construction_interruption_count"], 1)
        self.assertEqual(len(r["construction_interruptions"]), 1)
        self.assertEqual(r["late_terminal_reasons"], {})

    def test_normal_initialization_is_not_an_interruption(self):
        result = first_query_exit(es, "normal", 0.01)
        q, r = result["query"], result["report"]
        self.assertFalse(q["construction_deadline_exceeded"])
        self.assertFalse(q["interrupted_before_search"])
        self.assertAlmostEqual(q["construction_seconds"], 0.01, places=12)
        self.assertEqual(r["construction_overrun_count"], 0)

    def test_lead_probe_counts_the_overrun_and_accepts_nothing(self):
        result = first_query_exit(es, "caps", 1.0, budget=0.1)
        q, r = result["query"], result["report"]
        self.assertEqual(r["construction_overrun_count"], 1)
        self.assertEqual(r["construction_interruption_count"], 1)
        self.assertEqual(q["status"], "UNKNOWN_DEADLINE")
        self.assertEqual(q["construction_seconds"], 1.0)
        self.assertEqual(r["accepted"], 0)
        self.assertNotIn("NO_STRICT_IMPROVEMENT", r["statuses"])

    def test_repeated_resumes_are_not_construction_interruptions(self):
        # Tiny slices: every query resumes many times; a stepping clock ends
        # allowances mid-search, after nodes were expanded.
        program, facts, times, addresses = _bootstrap(800004)
        _, _, r = es.multiscale_optimise(program, facts, times, addresses, budget_seconds=5.0,
                                         clock=_Clock(1e-3), slice_nodes=3, **DFS)
        resumed = [q for q in r["queries"] if q["slices"] > 2]
        self.assertTrue(resumed)
        self.assertTrue(any(q["status"] == "UNKNOWN_ALLOWANCE" for q in resumed))
        for q in resumed:
            self.assertFalse(q["construction_deadline_exceeded"])
            self.assertFalse(q["interrupted_before_search"])
        self.assertEqual(r["construction_overrun_count"],
                         sum(q["construction_deadline_exceeded"] for q in r["queries"]))
        self.assertEqual(r["construction_interruption_count"],
                         sum(q["interrupted_before_search"] for q in r["queries"]))


def _candidate_checks(state):
    """Wrap ``_Acceptor.consider`` so only CANDIDATE validations are marked.

    ``Domain.from_record`` also calls the pinned validator (on the incumbent);
    those calls are not candidate validations and are passed through.
    """

    real = es._Acceptor.consider

    def consider(self, node_state):
        state["candidate"] = True
        try:
            return real(self, node_state)
        finally:
            state["candidate"] = False

    return mock.patch.object(es._Acceptor, "consider", consider)


class ValidationEventsWithDeadlines(unittest.TestCase):
    def test_rejection_is_retained_when_a_deadline_also_expires(self):
        program, facts, times, addresses = _bootstrap(800004)
        clock = _Clock(1e-5)
        state = {"n": 0, "candidate": False}
        real = machine.check_compilation

        def reject_then_jump(prog, compiled):
            if state["candidate"]:
                state["n"] += 1
                if state["n"] == 1:
                    clock.now += 10.0
                    raise machine.CompileError("forced rejection")
            return real(prog, compiled)

        with mock.patch.object(machine, "check_compilation", reject_then_jump), \
                _candidate_checks(state):
            _, _, r = es.multiscale_optimise(program, facts, times, addresses,
                                             budget_seconds=5.0, clock=clock, **DFS)
        self.assertEqual(state["n"], 1)
        self.assertEqual(r["discrepancy_count"], 1)
        self.assertEqual(r["rejected_completions"][0]["error"], "forced rejection")
        self.assertEqual(r["accepted"], 0)
        self.assertEqual(r["stopped_because"], "deadline")

    def test_interrupted_validation_and_overrun_are_separate_counts(self):
        program, facts, times, addresses = _bootstrap(800004)
        clock = _Clock(1e-5)
        state = {"checked": 0, "caps": 0, "candidate": False}
        real_check = machine.check_compilation
        real_caps = es.product_caps

        def late_check(prog, compiled):
            result = real_check(prog, compiled)
            if state["candidate"]:
                state["checked"] += 1
                if state["checked"] == 1:
                    clock.now += 0.2      # past the query allowance only
            return result

        def caps(*args, **kw):
            state["caps"] += 1
            result = real_caps(*args, **kw)
            if state["caps"] == 3:
                clock.now += 0.2          # an overrun in a later query
            return result

        with mock.patch.object(machine, "check_compilation", late_check), \
                mock.patch.object(es, "product_caps", caps), _candidate_checks(state):
            _, _, r = es.multiscale_optimise(program, facts, times, addresses,
                                             budget_seconds=100.0, clock=clock, **DFS)
        self.assertGreaterEqual(state["checked"], 1)
        self.assertEqual(r["interrupted_validation_search_total"], 1)
        self.assertEqual(r["interrupted_validation_model_total"], 0)
        self.assertEqual(r["interrupted_validation_total"], 1)
        self.assertEqual(r["construction_overrun_count"], 1)


class _ReadyLearner:
    """A test double that reaches the model phase and validates one candidate late."""

    def __init__(self, domain):
        self.validations = 0
        self.rejected = []
        self.reason = ""
        self.validation_budget = 10**9
        self.info = {}

    def observe(self, item):
        pass

    def prepare(self, deadline):
        return "READY"

    def step(self, best_product, until, hard_deadline=None, first_only=True):
        self.validations += 1
        self.info["late_validations"] = self.info.get("late_validations", 0) + 1
        return ("deadline",)

    def summary(self):
        return {"status": "ready_double", **self.info}


class ModelPhaseLateValidations(unittest.TestCase):
    def test_the_inherited_learner_counts_a_late_validation(self):
        """The seam itself: QueryLearner.step credits nothing and counts one late."""

        record = dict(oiv.original_fixtures()[0], target=None)
        domain = se.Domain.from_record(record)
        feasible = so.enumerate_feasible(record, 70_000)["feasible"]
        self.assertTrue(feasible)
        import json
        index = se.encode(domain, json.loads(feasible[0]["identity"]), "structural_rank")
        clock = _Clock(0.0)
        learner = oil.QueryLearner(domain, "tree", clock=clock)
        learner.queue = [int(index)]
        real_validate = learner._validate

        def slow_validate(compilation):
            ok = real_validate(compilation)
            clock.now += 5.0
            return ok

        learner._validate = slow_validate
        outcome = learner.step(10**12, until=100.0, hard_deadline=1.0)
        self.assertEqual(outcome, ("deadline",))
        self.assertEqual(learner.info["late_validations"], 1)

    def test_the_controller_total_includes_model_phase_late_validations(self):
        program, facts, times, addresses = _bootstrap(800004)
        _, _, r = es.multiscale_optimise(program, facts, times, addresses,
                                         budget_seconds=5.0, clock=_Clock(1e-3),
                                         learner_factory=_ReadyLearner, **DFS)
        model = r["interrupted_validation_model_total"]
        self.assertGreater(model, 0)
        self.assertEqual(r["interrupted_validation_total"],
                         r["interrupted_validation_search_total"] + model)
        per_query = sum(i["count"] for i in r["interrupted_validations_per_query"]
                        if i["phase"] == "model_validation")
        self.assertEqual(per_query, model)

    def test_the_parent_omits_them(self):
        program, facts, times, addresses = _bootstrap(800004)
        _, _, r = nrs.multiscale_optimise(program, facts, times, addresses,
                                          budget_seconds=5.0, clock=_Clock(1e-3),
                                          learner_factory=_ReadyLearner, **DFS)
        self.assertEqual(r["interrupted_validation_total"], 0)


class PowerOnParent(unittest.TestCase):
    def test_parent_reports_zero_for_the_lead_probe(self):
        result = first_query_exit(nrs, "caps", 1.0, budget=0.1)
        self.assertEqual(result["report"]["construction_interruption_count"], 0)
        self.assertEqual(result["query"]["status"], "NO_STRICT_IMPROVEMENT")
        self.assertNotIn("construction_overrun_count", result["report"])


def _canonical_statuses(report) -> dict:
    """Map each late relabel back to its terminal status (parent vocabulary)."""

    out = dict(report["statuses"])
    for q in report["queries"]:
        if q.get("late_terminal_reason"):
            out[q["status"]] -= 1
            out[q["terminal_reason"]] = out.get(q["terminal_reason"], 0) + 1
    return {k: v for k, v in out.items() if v}


class ParityWithParent(unittest.TestCase):
    """Same decisions, clock readings, certificates and incumbents as the parent."""

    def test_decisions_identical_for_both_traversals_and_modes(self):
        compared = 0
        for seed in list(range(800000, 800010)) + [800014, 800021, 800033]:
            program, facts, times, addresses = _bootstrap(seed)
            for cell in ({"catalog": "a4", "traversal": "dfs"},
                         {"catalog": "a4", "traversal": "heap"}):
                for kwargs, step in (({"budget_seconds": 0.1}, 2e-6),
                                     ({"budget_seconds": 1.0}, 0.0)):
                    outs = []
                    for module in (nrs, es):
                        clock, trace = _Clock(step), []
                        t, a, r = module.multiscale_optimise(
                            program, facts, times, addresses, clock=clock, trace=trace,
                            node_ceiling=10_000, **cell, **kwargs)
                        outs.append((t, a, r, trace, clock.readings))
                    (t0, a0, r0, tr0, n0), (t1, a1, r1, tr1, n1) = outs
                    self.assertEqual((t0, a0), (t1, a1))
                    self.assertEqual(tr0, tr1)
                    self.assertEqual(n0, n1, "clock readings")
                    self.assertEqual(r0["propagation"], r1["propagation"])
                    self.assertEqual(r0["statuses"], _canonical_statuses(r1))
                    for field in ("accepted", "epochs", "catalog_sizes", "stopped_because",
                                  "aggregate", "queries_not_started", "discrepancy_count",
                                  "interrupted_validation_total"):
                        self.assertEqual(r0[field], r1[field], field)
                    compared += len(tr0)
        self.assertGreater(compared, 10_000)


if __name__ == "__main__":
    unittest.main()
