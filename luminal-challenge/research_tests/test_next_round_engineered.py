"""Parity of the Stage E engineering variant with its parent (next round 1.0).

``next_round_engineered`` differs from ``next_round_search`` only in how the two
propagation fixpoints are revised. These tests require what the plan requires
of a pure speed change: identical candidate sequences, pruning decisions and
incumbents at equal work, on exhaustive fixtures and on development programs,
and every emitted certificate still sound on replay.
"""

from __future__ import annotations

import unittest

import direct_contract as dc

from research import next_round_engineered as nre
from research import next_round_search as nrs
from research import objective_index_replay as oir
from research import objective_index_validation as oiv
from research import optimization_common as oc
from research import structural_encoding as se

from tests_direct import generate_programs as gp

CELLS = (("a4", "dfs"), ("a4", "heap"), ("a3", "dfs"), ("a3", "heap"))


def _j(facts, times, addresses):
    return (max(times.values()) + 1) * dc.footprint(facts, addresses)


class _Clock:
    def __init__(self, step):
        self.now, self.step = 0.0, step

    def __call__(self):
        self.now += self.step
        return self.now


def _records():
    return [dict(r, target=None) for r in list(oiv.original_fixtures())
            + oiv.recipe_fixtures(920000, 12)]


class SourceIdentity(unittest.TestCase):
    def test_parent_hash_is_the_measured_successor(self):
        self.assertEqual(oc.file_sha256(oc.ROOT / "research" / "next_round_search.py"),
                         nre.PARENT_SOURCE_SHA256)


class ExhaustiveParity(unittest.TestCase):
    """Same pop order (discrepancy, bound, ranks), same collected set, both traversals."""

    def test_enumerations_are_identical(self):
        nodes = 0
        for record in _records():
            facts = dc.derive(record["program"])
            incumbent = record["incumbent"]
            times = se.issue_cycles_of(record["program"], incumbent["bundles"])
            addresses = dict(incumbent["scratch"])
            domain = se.Domain.from_record(record)
            j0 = _j(facts, times, addresses)
            for threshold in (j0, 10 * j0):
                for name in ("dfs_enumerate", "lds_enumerate"):
                    a = getattr(nrs, name)(domain, incumbent, threshold)
                    b = getattr(nre, name)(domain, incumbent, threshold)
                    self.assertEqual(a["status"], b["status"])
                    self.assertEqual(a["pop_order"], b["pop_order"])
                    self.assertEqual(set(a["collected"]), set(b["collected"]))
                    self.assertEqual(a["nodes"], b["nodes"])
                    nodes += a["nodes"]
        self.assertGreater(nodes, 5000)

    def test_every_child_domain_and_bound_is_identical(self):
        events = 0
        for record in _records()[:20]:
            domain = se.Domain.from_record(record)
            threshold = 10 ** 9
            seen = {}
            for module in (nrs, nre):
                report = module._new_report(domain, "parity", record["incumbent"])
                expander = module.Expander(domain, "propagate", module.PropagationStats(),
                                           report)
                trail = []
                expander.audit = lambda e, t=trail: t.append(
                    (e["outcome"], tuple(sorted(e["times"].items())),
                     tuple(sorted(e["addresses"].items())),
                     None if e["D"] is None else tuple(sorted(e["D"].items())),
                     None if e["A"] is None else tuple(sorted(e["A"].items())),
                     e.get("LC"), e.get("LS")))
                stack = [expander.root(threshold)]
                while stack:
                    node = stack.pop()
                    if node is None or expander.is_leaf(node):
                        continue
                    stack.extend(reversed(list(expander.children(node, lambda: threshold))))
                seen[module.__name__] = (trail, report.pruned, report.dead_ends,
                                         expander.filtered)
            self.assertEqual(seen["research.next_round_search"],
                             seen["research.next_round_engineered"])
            events += len(seen["research.next_round_search"][0])
        self.assertGreater(events, 5000)


class ControllerParity(unittest.TestCase):
    def _run(self, module, program, catalog, traversal, **kwargs):
        facts, times, addresses = oiv.bootstrap(program)
        trace = []
        best_t, best_a, record = module.multiscale_optimise(
            program, facts, times, addresses, trace=trace, catalog=catalog,
            traversal=traversal, **kwargs)
        return best_t, best_a, record, trace

    def test_equal_work_runs_are_identical_on_development_programs(self):
        compared = 0
        for seed in range(800000, 800100, 3):
            program = gp.additional_program(seed)
            for catalog, traversal in CELLS:
                kwargs = {"budget_seconds": 1e6, "query_seconds": 1e6, "slice_seconds": 1e6,
                          "node_ceiling": 20_000, "clock": _Clock(1e-6)}
                a = self._run(nrs, program, catalog, traversal, **kwargs)
                kwargs["clock"] = _Clock(1e-6)
                b = self._run(nre, program, catalog, traversal, **kwargs)
                self.assertEqual(a[3], b[3], (seed, catalog, traversal))
                self.assertEqual(a[:2], b[:2])
                for field in ("statuses", "accepted", "epochs", "catalog_sizes",
                              "stopped_because", "aggregate", "queries_not_started",
                              "discrepancy_count", "interrupted_validation_total"):
                    self.assertEqual(a[2][field], b[2][field], field)
                compared += len(a[3])
        self.assertGreater(compared, 50_000)

    def test_tick_clock_budget_runs_are_identical(self):
        # A deterministic clock that advances per reading: the variant makes
        # the same readings because propagation reads no clock.
        for seed in (800001, 800014, 800033, 800047, 800088):
            program = gp.additional_program(seed)
            a = self._run(nrs, program, "a4", "dfs", budget_seconds=0.1, clock=_Clock(2e-6))
            b = self._run(nre, program, "a4", "dfs", budget_seconds=0.1, clock=_Clock(2e-6))
            self.assertEqual(a[3], b[3])
            self.assertEqual(a[:2], b[:2])
            self.assertEqual(a[2]["improvements"], b[2]["improvements"])


class CertificatesStaySound(unittest.TestCase):
    def test_variant_certificate_streams_replay_without_failure(self):
        replayed = 0
        for seed in (800002, 800006, 800011):
            program = gp.additional_program(seed)
            facts, times, addresses = oiv.bootstrap(program)
            stats = nre.PropagationStats(keep=True)
            nre.multiscale_optimise(program, facts, times, addresses, budget_seconds=1e6,
                                    query_seconds=1e6, slice_seconds=1e6, node_ceiling=5_000,
                                    stats=stats, catalog="a4", traversal="dfs")
            result = oir.replay_stream(facts, stats.certificates)
            self.assertEqual(result["failure_count"], 0)
            replayed += len(stats.certificates)
        self.assertGreater(replayed, 1000)


if __name__ == "__main__":
    unittest.main()
