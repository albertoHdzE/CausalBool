"""Third round: protocol constants, row discipline, kernel exactness and kernel mutations.

The kernel is checked against the CAPTURED R0 workloads of the frozen M0 run
(``WORKLOAD_MANIFEST.json``): every output digest, every per-call emission count
and the whole certificate stream. Each mutation plants one of the defects the
plan names (stale domain summary, stale incumbent-sensitive value, sibling
contamination, omitted consumer dependency) and must be caught.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path

from research import efficiency_search as es
from research import third_round_common as tc
from research import third_round_kernel as tk
from research import third_round_workload as tw

RUN = tc.run_dir()
# Small workloads covering the time phase, the address phase and rule 2.
SEEDS = ("800000", "800002", "800004", "800008", "800010", "800012")


def _prepared():
    manifest = json.loads((RUN / "WORKLOAD_MANIFEST.json").read_text())
    out = {}
    for seed in SEEDS:
        item = manifest["workloads"][seed]
        out[seed] = tw.prepare(tw.load(Path(item["path"])))
    return out


PREPARED = None


def prepared():
    global PREPARED
    if PREPARED is None:
        PREPARED = _prepared()
    return PREPARED


def parity_with(factory) -> dict:
    """Replay every small workload with ``factory`` as the kernel's Propagation."""

    original = tk.SharedPropagation
    tk.SharedPropagation = factory
    try:
        results = {}
        for seed, prep in prepared().items():
            stats = es.PropagationStats()
            try:
                replay = tk.replay_shared(prep, stats)
                results[seed] = tw.compare_to_capture(prep, replay, stats)["parity"]
            except Exception:           # a crash is also a detected defect
                results[seed] = False
        return results
    finally:
        tk.SharedPropagation = original


class ProtocolAndRows(unittest.TestCase):
    def test_protocol_constants(self):
        report = tc.check_protocol_constants()
        self.assertEqual(report["status"], "PASS", report["mismatches"])
        self.assertEqual(report["checked"], 21)

    def test_check_rows_refuses_empty_and_flags_defects(self):
        with self.assertRaises(ValueError):
            tc.check_rows([], [])
        row = {"stage_id": "S", "program_sha256": "p", "repetition": 0, "arm_id": "R0",
               "mode_key": "m"}
        key = tc.row_key(row)
        ok = tc.check_rows([row], [key])
        self.assertTrue(ok["complete"])
        self.assertFalse(tc.check_rows([row, row], [key])["complete"])
        self.assertFalse(tc.check_rows([], [key])["complete"])
        self.assertFalse(tc.check_rows([dict(row, failed=True)], [key])["complete"])
        self.assertFalse(tc.check_rows([dict(row, timed_out=True)], [key])["complete"])
        self.assertFalse(tc.check_rows([dict(row, arm_id="X")], [key])["complete"])


class KernelExactness(unittest.TestCase):
    def test_baseline_replay_reproduces_capture(self):
        for seed, prep in prepared().items():
            stats = es.PropagationStats()
            check = tw.compare_to_capture(prep, tw.replay_baseline(prep, stats), stats)
            self.assertTrue(check["parity"], (seed, check))

    def test_kernel_reproduces_capture(self):
        results = parity_with(tk.SharedPropagation)
        self.assertEqual(len(results), len(SEEDS))
        self.assertTrue(all(results.values()), results)

    def test_kernel_exercises_every_consumer(self):
        kinds = set()
        for prep in prepared().values():
            kinds |= {e[0] for e in prep["events"]}
            if any(e[0] == "T" and e[3] is not None for e in prep["events"]):
                kinds.add("T_child")
            if any(e[0] == "A" and e[3] is not None for e in prep["events"]):
                kinds.add("A_child")
        self.assertTrue({"T", "T_child", "P", "L", "A", "A_child"} <= kinds, kinds)

    def test_states_are_not_mutated_by_children(self):
        """Every parent state is byte-identical before and after all its children."""

        for seed, prep in prepared().items():
            stats = es.PropagationStats()
            props, out, snapshots = {}, {}, {}
            for event in prep["events"]:
                kind, ev, index = event[0], event[1], event[2]
                prop = props.get(index) or props.setdefault(
                    index, tk.SharedPropagation(prep["domains"][index], stats))
                if kind == "T":
                    parent, d_in, op, value = event[3:]
                    result = (prop.time_root(d_in) if parent is None
                              else prop.time_child(out[parent], op, value))
                    if result is not None:
                        snapshots[ev] = (repr(sorted(result.D.items())),
                                         repr(sorted(result.singles.items())))
                    out[ev] = result
                elif kind == "P":
                    d_ev, a_ev, best = event[3:]
                    prop.prune_state(out[d_ev], None if a_ev is None else out[a_ev].A, best)
                elif kind == "L":
                    out[ev] = prop.address_pairs(event[3])
                else:
                    parent, pairs_ev, a_in, name, value = event[3:]
                    out[ev] = (prop.address_root(a_in, out[pairs_ev]) if parent is None
                               else prop.address_child(out[parent], name, value))
            for ev, snap in snapshots.items():
                state = out[ev]
                self.assertEqual(snap, (repr(sorted(state.D.items())),
                                        repr(sorted(state.singles.items()))), (seed, ev))


# --------------------------------------------------------------------------
# Mutations: each must break parity on at least one workload
# --------------------------------------------------------------------------


class StaleDomainSummary(tk.SharedPropagation):
    """Precedence: an op's falling maximum no longer dirties its incoming edges."""

    def __init__(self, domain, stats):
        super().__init__(domain, stats)
        self.in_mask = {}


class OmittedConsumerDependency(tk.SharedPropagation):
    """Live bounds: a consumer's minimum is no longer a dependency of its value."""

    def __init__(self, domain, stats):
        super().__init__(domain, stats)
        producers = {self.dynamic_values.index(n): self.facts.producers[n]
                     for n in self.dynamic_values}
        self.values_of = {op: [i for i in idx if producers[i] == op]
                          for op, idx in self.values_of.items()}


class StaleSingles(tk.SharedPropagation):
    """Rule 2: a child inherits its parent's singleton counts unchanged."""

    def time_child(self, parent, op, value):
        state = super().time_child(parent, op, value)
        if state is not None:
            state.singles = parent.singles
        return state


class SiblingContamination(tk.SharedPropagation):
    """A child writes its new singleton counts into the parent's shared map.

    (Writing the child's decision into ``parent.D`` instead is NOT a defect of
    this kernel: the stale ``old`` domain only enlarges the dirty edge set, so
    that variant keeps parity -- observed while writing this test.)
    """

    def time_child(self, parent, op, value):
        state = super().time_child(parent, op, value)
        if state is not None and state.singles is not parent.singles:
            parent.singles.update(state.singles)
        return state


class StaleIncumbent(tk.SharedPropagation):
    """Prune: the first incumbent bound seen is reused for later calls."""

    def prune_state(self, state, A, best):
        if not hasattr(self, "_first_best"):
            self._first_best = best
        return super().prune_state(state, A, None if best is None else self._first_best + 10**6)


class StaleAddressSupport(tk.SharedPropagation):
    """Address support: a value's changed bounds no longer dirty the pairs reading it."""

    def address_child(self, parent, name, value):
        A = dict(parent.A)
        A[name] = (value,)
        return self._address(A, parent.info, 0)


class KernelMutations(unittest.TestCase):
    def _assert_caught(self, factory):
        results = parity_with(factory)
        self.assertEqual(len(results), len(SEEDS))
        self.assertFalse(all(results.values()), f"{factory.__name__} not caught: {results}")

    def test_stale_domain_summary_caught(self):
        self._assert_caught(StaleDomainSummary)

    def test_omitted_consumer_dependency_caught(self):
        self._assert_caught(OmittedConsumerDependency)

    def test_stale_singles_caught(self):
        self._assert_caught(StaleSingles)

    def test_sibling_contamination_caught(self):
        self._assert_caught(SiblingContamination)

    def test_stale_incumbent_caught(self):
        self._assert_caught(StaleIncumbent)

    def test_stale_address_support_caught(self):
        self._assert_caught(StaleAddressSupport)


if __name__ == "__main__":
    unittest.main()
