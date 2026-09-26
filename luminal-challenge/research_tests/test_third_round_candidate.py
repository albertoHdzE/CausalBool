"""C1 versus R0: exact decisions and certificates, and planted BS1 defects.

- Exhaustive small-domain parity on the objective-index fixture records: every
  propagated child event (outcome, prefix, surviving time/address domains, LC,
  LS), every collected improving object, the retained certificate LIST and the
  report counters are identical for R0 and C1, at three incumbent thresholds.
  The oracle's improving set is compared as well.
- Fixed-work parity on development programs of every family (decision
  fingerprint: search trace, incumbent, certificate stream, statuses, aggregate,
  stop reason), including a repeated compilation in the same process.
- Tick-clock parity at wall budgets (exact deadline boundaries, late proofs,
  clock-reading counts).
- Mutations of the BS1 kernel (stale domain summary, omitted consumer
  dependency, stale singles, sibling contamination, stale incumbent-sensitive
  value, stale address support) must each break one of these parities.
"""

from __future__ import annotations

import unittest
from unittest import mock

import schema_index as si

from research import efficiency_search as r0
from research import objective_index_validation as oiv
from research import structural_encoding as se
from research import structural_oracle as so
from research import third_round_candidate as c1
from research import third_round_kernel as tk
from research import third_round_resume_dworker as dw
from research_tests import test_third_round_kernel as kt

from tests_direct import generate_programs as gp

BIG = si.Budget(seconds=1e6, max_cover=4096, max_visited=10_000_000, max_records=1_000_000)
FIXED_SEEDS = (800000, 800001, 800002, 800003, 800004, 800007, 800008, 800009, 800010,
               800012, 800018, 800024)


def _records():
    return list(oiv.original_fixtures()) + oiv.recipe_fixtures()


RECORDS = None


def records():
    global RECORDS
    if RECORDS is None:
        RECORDS = _records()
    return RECORDS


def _plain(event):
    return {k: (dict(v) if isinstance(v, dict) else v) for k, v in event.items()}


def event_stream(module, record, threshold):
    domain = se.Domain.from_record(dict(record, target=None))
    stats = module.PropagationStats(keep=True)
    events = []
    result, extras = module.propagated_search(domain, record["incumbent"], BIG, stats=stats,
                                              collect=True, audit=events.append,
                                              threshold=threshold)
    collected = sorted(repr(sorted(x.items())) for x in extras["collected"].values())
    return {"events": [_plain(e) for e in events], "collected": collected,
            "certificates": list(stats.certificates), "counts": dict(stats.counts),
            "report": {k: v for k, v in result.to_row().items()
                       if "second" not in k and "elapsed" not in k}}


def thresholds(record):
    feasible = so.enumerate_feasible(record, oiv.ORACLE_MAX)["feasible"]
    products = sorted({x["product"] for x in feasible})
    if not products:
        return [1], feasible
    return sorted({products[0] + 1, products[len(products) // 2] + 1, products[-1] + 1}), feasible


def fixed_fingerprint(module, seed):
    program = gp.additional_program(seed)
    trace = []
    compiled, record, facts, stats = dw.compile_call(module, program, "work:10000", trace)
    return dw.fingerprint(record, trace, compiled, facts)


class _Clock:
    def __init__(self, step):
        self.now, self.step, self.readings = 0.0, step, 0

    def __call__(self):
        self.readings += 1
        self.now += self.step
        return self.now


def tick_run(module, seed, budget, step):
    program = gp.additional_program(seed)
    facts, times, addresses = oiv.bootstrap(program)
    clock, trace = _Clock(step), []
    t, a, r = module.multiscale_optimise(program, facts, times, addresses, budget_seconds=budget,
                                         clock=clock, trace=trace, catalog="a4",
                                         traversal="dfs")
    keep = ("accepted", "epochs", "catalog_sizes", "stopped_because", "aggregate", "statuses",
            "propagation", "discrepancy_count", "interrupted_validation_total",
            "construction_overrun_count", "construction_interruption_count",
            "queries_not_started")
    return (t, a, trace, clock.readings, {k: r.get(k) for k in keep})


class ExhaustiveParity(unittest.TestCase):
    def test_every_event_certificate_and_improving_object_is_identical(self):
        compared = events = objects = 0
        for record in records():
            ths, feasible = thresholds(record)
            for threshold in ths:
                a = event_stream(r0, record, threshold)
                b = event_stream(c1, record, threshold)
                self.assertEqual(a, b, (record["id"], threshold))
                truth = sum(1 for x in feasible if x["product"] < threshold)
                self.assertEqual(len(b["collected"]), truth, (record["id"], threshold))
                compared += 1
                events += len(a["events"])
                objects += truth
        self.assertGreater(compared, 30)
        self.assertGreater(events, 1000)
        self.assertGreater(objects, 0)


class FixedWorkParity(unittest.TestCase):
    def test_fingerprints_identical_across_families(self):
        families = set()
        for seed in FIXED_SEEDS:
            self.assertEqual(fixed_fingerprint(r0, seed), fixed_fingerprint(c1, seed), seed)
            families.add(seed % 5)
        self.assertEqual(families, {0, 1, 2, 3, 4})

    def test_repeated_independent_compilations(self):
        first = fixed_fingerprint(c1, 800009)
        self.assertEqual(first, fixed_fingerprint(c1, 800009))
        self.assertEqual(first, fixed_fingerprint(r0, 800009))


class TickClockParity(unittest.TestCase):
    def test_deadlines_and_clock_readings(self):
        for seed in (800001, 800004, 800009, 800010):
            for budget, step in ((0.01, 2e-6), (0.1, 2e-6), (0.1, 5e-5)):
                self.assertEqual(tick_run(r0, seed, budget, step),
                                 tick_run(c1, seed, budget, step), (seed, budget, step))


class Mutations(unittest.TestCase):
    """Each planted BS1 defect breaks fixed-work or exhaustive parity."""

    def _caught(self, mutant):
        with mock.patch.object(tk, "SharedPropagation", mutant):
            for seed in FIXED_SEEDS:
                try:
                    if fixed_fingerprint(c1, seed) != fixed_fingerprint(r0, seed):
                        return True
                except Exception:
                    return True
            for record in records()[:12]:
                ths, _ = thresholds(record)
                for threshold in ths:
                    try:
                        if event_stream(c1, record, threshold) != event_stream(r0, record,
                                                                               threshold):
                            return True
                    except Exception:
                        return True
        return False

    def test_mutants_are_caught(self):
        for mutant in (kt.StaleDomainSummary, kt.OmittedConsumerDependency, kt.StaleSingles,
                       kt.SiblingContamination, kt.StaleIncumbent, kt.StaleAddressSupport):
            self.assertTrue(self._caught(mutant), mutant.__name__)

    def test_unmutated_kernel_is_not_flagged(self):
        self.assertFalse(self._caught(tk.SharedPropagation))


class Identity(unittest.TestCase):
    def test_c1_is_r0_plus_the_expander_diff(self):
        import hashlib
        with open(r0.__file__, "rb") as handle:
            self.assertEqual(c1.C1_PARENT_SHA256, hashlib.sha256(handle.read()).hexdigest())
        with open(tk.__file__, "rb") as handle:
            self.assertEqual(c1.BS1_KERNEL_SHA256, hashlib.sha256(handle.read()).hexdigest())
        self.assertEqual(c1.VERSION, "third_round_candidate C1")
        self.assertEqual(r0.VERSION, "efficiency_search R0")


if __name__ == "__main__":
    unittest.main()
