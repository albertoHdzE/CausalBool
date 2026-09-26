"""R4: why the per-query learner cannot reach 20 observations before model preparation.

Two regressions, both deterministic (see ``LEARNER_CLOSURE.md``):

1. ``LeafBoundIsExact`` -- exhaustively, on every leaf of the exhaustible
   fixtures, the propagated product bound equals the leaf's C*S. Hence a leaf
   that survives the prune ``LC*LS >= best`` is a STRICT improvement.
2. ``ObservationsPerQuery`` -- the controller with a recording learner, on
   development programs, under an infinitely fast (constant) clock and under a
   stepping clock that reaches the half-time boundary. It counts, per query,
   the distinct observations at the first model preparation and over the whole
   query, and requires both to be at most 1 plus the query's validator
   rejections. Faster propagation cannot change a bound that holds at every
   clock.
"""

from __future__ import annotations

import unittest

from research import efficiency_search as es
from research import objective_index_learned as oil
from research import objective_index_validation as oiv
from research import structural_encoding as se
from research import schema_ranker as sr

from tests_direct import generate_programs as gp


class _Clock:
    def __init__(self, step: float) -> None:
        self.now, self.step = 0.0, step

    def __call__(self) -> float:
        self.now += self.step
        return self.now


class LeafBoundIsExact(unittest.TestCase):
    def test_every_full_leaf_bound_equals_its_product(self):
        leaves = pruned_leaves = fixtures = exact = 0
        for record in list(oiv.original_fixtures()) + oiv.recipe_fixtures(920000, 10):
            record = dict(record, target=None)
            domain = se.Domain.from_record(record)
            facts = domain.facts
            values = len(facts.value_names)
            incumbent = se.objective(facts, *_incumbent(domain))[2]
            fixtures += 1
            # Exactness is threshold-free: enumerate with no effective prune,
            # then with the incumbent as the prune threshold.
            for threshold in (10**12, incumbent):
                events = []
                report = es._new_report(domain, "closure", None)
                expander = es.Expander(domain, "propagate", es.PropagationStats(), report)
                expander.audit = events.append
                stack = [expander.root(threshold)]
                while stack:
                    node = stack.pop()
                    if node is None or expander.is_leaf(node):
                        continue
                    stack.extend(reversed(list(expander.children(node, lambda: threshold))))
                for event in events:
                    if event["outcome"] == "inconsistent" or len(event["addresses"]) != values:
                        continue
                    product = se.objective(facts, event["times"], event["addresses"])[2]
                    self.assertEqual(event["LC"] * event["LS"], product)
                    if threshold == incumbent and event["outcome"] == "kept":
                        self.assertLess(product, incumbent)
                        leaves += 1
                    elif threshold == incumbent:
                        self.assertGreaterEqual(product, incumbent)
                        pruned_leaves += 1
                    else:
                        exact += 1
        self.assertGreater(fixtures, 10)
        self.assertGreater(exact, 1000)
        print(f"\n[closure] fixtures={fixtures} exact_full_leaves_unpruned={exact} "
              f"surviving_full_leaves_at_incumbent={leaves} pruned_full_leaves={pruned_leaves}")


def _incumbent(domain):
    normalised = se.normalise_compilation(domain.facts, domain.incumbent)
    return se.issue_cycles_of(domain.program, normalised["bundles"]), dict(normalised["scratch"])


class _Recording(oil.QueryLearner):
    LOG: list = []
    EPOCH_J = None

    def __init__(self, domain):
        super().__init__(domain, "tree")
        self.epoch_j = _Recording.EPOCH_J
        self.products = []
        self.at_prepare = None
        _Recording.LOG.append(self)

    def observe(self, item):
        if item["identity"] not in self.observations:
            self.products.append(item["product"])
        super().observe(item)

    def prepare(self, deadline):
        if self.at_prepare is None:
            self.at_prepare = len(self.observations)
        return super().prepare(deadline)


class ObservationsPerQuery(unittest.TestCase):
    def _run(self, step: float, seeds) -> dict:
        _Recording.LOG = []
        rejected = queries = prepared = 0
        maximum_any = maximum_prepare = 0
        for seed in seeds:
            program = gp.additional_program(seed)
            facts, times, addresses = oiv.bootstrap(program)
            _, _, record = es.multiscale_optimise(
                program, facts, times, addresses, budget_seconds=1.0, clock=_Clock(step),
                node_ceiling=10_000, catalog="a4", traversal="dfs",
                learner_factory=_Recording)
            rejected += record["discrepancy_count"]
        for learner in _Recording.LOG:
            queries += 1
            maximum_any = max(maximum_any, len(learner.observations))
            if learner.at_prepare is not None:
                prepared += 1
                maximum_prepare = max(maximum_prepare, learner.at_prepare)
                self.assertNotEqual(learner.status, "READY")
        return {"queries": queries, "prepared": prepared, "max_observations_any_query":
                maximum_any, "max_observations_at_prepare": maximum_prepare,
                "rejected_candidates": rejected}

    def test_infinitely_fast_search_observes_at_most_one_per_query(self):
        out = self._run(0.0, range(800000, 800020))
        print(f"\n[closure] constant clock: {out}")
        self.assertGreater(out["queries"], 100)
        self.assertEqual(out["rejected_candidates"], 0)
        self.assertLessEqual(out["max_observations_any_query"], 1)
        self.assertLessEqual(out["max_observations_at_prepare"], 1)
        self.assertLess(out["max_observations_at_prepare"], sr.MIN_TRAINING)

    def test_half_time_boundary_leaves_at_most_one_at_first_preparation(self):
        prepared = 0
        for step in (1e-5, 1e-4, 1e-3):
            out = self._run(step, range(800000, 800020))
            print(f"\n[closure] stepping clock {step}: {out}")
            prepared += out["prepared"]
            self.assertEqual(out["rejected_candidates"], 0)
            self.assertLessEqual(out["max_observations_at_prepare"], 1)
            self.assertLessEqual(out["max_observations_any_query"], 1)
        self.assertGreater(prepared, 10, "the half-time boundary was rarely reached")

    def test_every_observed_leaf_strictly_improves_its_epoch(self):
        _Recording.LOG = []
        seen = 0
        for seed in range(800000, 800010):
            program = gp.additional_program(seed)
            facts, times, addresses = oiv.bootstrap(program)
            epochs = []
            real = es.build_catalog

            def catalog(facts_, t, a):
                epochs.append((max(t.values()) + 1) * es.dc.footprint(facts_, a))
                _Recording.EPOCH_J = epochs[-1]
                return real(facts_, t, a)

            _Recording.LOG = []
            from unittest import mock
            with mock.patch.object(es, "build_catalog", catalog):
                es.multiscale_optimise(program, facts, times, addresses, budget_seconds=1.0,
                                       clock=_Clock(0.0), node_ceiling=10_000, catalog="a4",
                                       traversal="dfs", learner_factory=_Recording)
            # Queries of epoch k observe only products below that epoch's J.
            for learner in _Recording.LOG:
                for product in learner.products:
                    self.assertLess(product, learner.epoch_j)
                    seen += 1
        self.assertGreater(seen, 0)


if __name__ == "__main__":
    unittest.main()
