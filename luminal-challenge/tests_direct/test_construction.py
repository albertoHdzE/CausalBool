"""T04: independent query and construction checks for the bootstrap.

The oracles are written here from integer arithmetic and the frozen machine.
Where a domain is small enough, the whole domain is exhausted rather than
sampled, so a "minimum" claim is checked against every alternative.
"""

from __future__ import annotations

import copy
import importlib
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
import direct_contract as dc
from tests_direct import generate_programs as gp
from tests_direct.test_contract import program, sequential_times, unique_addresses


FORBIDDEN = ("common", "compilers", "index_query", "repertoire_program", "doppel_challenge")


# --------------------------------------------------------------------------
# Independent oracles
# --------------------------------------------------------------------------


def feasible_cycle(facts, op_id, cycle, times, calendar):
    """Is ``cycle`` legal for ``op_id`` given the already fixed prefix?

    Written from the machine's rules directly: data readiness, ordered memory
    separation, and per-cycle issue capacity.
    """

    operations = facts.program["operations"]
    for arg in operations[op_id].get("args", []):
        producer = facts.producers[arg]
        latency = machine.OP_SPECS[operations[producer]["op"]]["latency"]
        if cycle < times[producer] + latency:
            return False
    for predecessor in machine.memory_predecessors(facts.program, op_id):
        if cycle < times[predecessor] + 1:
            return False
    engine = machine.OP_SPECS[operations[op_id]["op"]]["engine"]
    if calendar.get((engine, cycle), 0) >= machine.ENGINE_LIMITS[engine]:
        return False
    return True


def brute_force_schedule(facts):
    """Source-order earliest feasible placement, found by scanning integers."""

    times = {}
    calendar = {}
    for op_id in range(facts.count):
        cycle = 0
        while not feasible_cycle(facts, op_id, cycle, times, calendar):
            cycle += 1
            if cycle > facts.horizon:
                raise AssertionError("no feasible cycle below the horizon")
        times[op_id] = cycle
        engine = machine.OP_SPECS[facts.program["operations"][op_id]["op"]]["engine"]
        calendar[(engine, cycle)] = calendar.get((engine, cycle), 0) + 1
    return times


def feasible_address(facts, name, address, live, addresses):
    width = facts.width[name]
    if address < 0 or address + width > machine.SCRATCH_WORDS:
        return False
    if width == machine.VLEN and address % machine.VLEN:
        return False
    for other, base in addresses.items():
        other_width = facts.width[other]
        spatial = address < base + other_width and base < address + width
        temporal = live[name][0] <= live[other][1] and live[other][0] <= live[name][1]
        if spatial and temporal:
            return False
    return True


def brute_force_allocation(facts, times, order):
    """Smallest legal address per value, found by scanning every word."""

    live = dc.lifetimes(facts, times)
    addresses = {}
    for name in order:
        for address in range(machine.SCRATCH_WORDS + 1):
            if feasible_address(facts, name, address, live, addresses):
                addresses[name] = address
                break
        else:
            raise AssertionError(f"no legal address for {name!r}")
    return addresses


class _Blocker:
    """A meta path finder that refuses the prohibited modules."""

    def __init__(self, names):
        self.names = tuple(names)

    def find_module(self, fullname, path=None):
        return self.find_spec(fullname, path)

    def find_spec(self, fullname, path=None, target=None):
        root = fullname.split(".")[0]
        if root in self.names or fullname in self.names:
            raise AssertionError(f"the direct path must not import {fullname!r}")
        return None


# --------------------------------------------------------------------------


FIXTURES = {}


def _fixture(name, buffers, operations, cases):
    FIXTURES[name] = program(name, buffers, operations, cases)
    return FIXTURES[name]


_fixture(
    "chain",
    {"data": 8, "out": 1},
    [
        {"op": "load", "dest": "a", "buffer": "data", "offset": 0},
        {"op": "add", "dest": "b", "args": ["a", "a"]},
        {"op": "mul", "dest": "c", "args": ["b", "b"]},
        {"op": "sub", "dest": "d", "args": ["c", "b"]},
        {"op": "store", "args": ["d"], "buffer": "out", "offset": 0},
    ],
    [{"data": list(range(8)), "out": [0]}],
)

_fixture(
    "many_ready",
    {"out": 6},
    [{"op": "const", "dest": "c%d" % i, "value": i} for i in range(6)]
    + [
        {"op": "store", "args": ["c%d" % i], "buffer": "out", "offset": i}
        for i in range(6)
    ],
    [{"out": [0] * 6}],
)

_fixture(
    "memory_bottleneck",
    {"data": 4},
    [
        {"op": "load", "dest": "l%d" % i, "buffer": "data", "offset": 0} for i in range(3)
    ]
    + [
        {"op": "store", "args": ["l0"], "buffer": "data", "offset": 0},
        {"op": "load", "dest": "l3", "buffer": "data", "offset": 0},
        {"op": "store", "args": ["l3"], "buffer": "data", "offset": 0},
    ],
    [{"data": [1, 2, 3, 4]}],
)

_fixture(
    "sparse",
    {"data": 8, "out": 4},
    [
        {"op": "const", "dest": "k", "value": 3},
        {"op": "load", "dest": "x", "buffer": "data", "offset": 0},
        {"op": "load", "dest": "y", "buffer": "data", "offset": 4},
        {"op": "add", "dest": "s", "args": ["x", "y"]},
        {"op": "xor", "dest": "t", "args": ["k", "k"]},
        {"op": "store", "args": ["s"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["t"], "buffer": "out", "offset": 1},
    ],
    [{"data": list(range(8)), "out": [0] * 4}],
)

_fixture(
    "mixed_lifetimes",
    {"data": 16, "out": 16},
    [
        {"op": "vload", "dest": "v0", "buffer": "data", "offset": 0},
        {"op": "const", "dest": "k", "value": 7},
        {"op": "splat", "dest": "vs", "args": ["k"]},
        {"op": "vmul", "dest": "vm", "args": ["v0", "vs"]},
        {"op": "vload", "dest": "v1", "buffer": "data", "offset": 8},
        {"op": "vadd", "dest": "va", "args": ["vm", "v1"]},
        {"op": "vstore", "args": ["va"], "buffer": "out", "offset": 0},
        {"op": "vstore", "args": ["v0"], "buffer": "out", "offset": 8},
    ],
    [{"data": list(range(16)), "out": [0] * 16}],
)

_fixture(
    "unused_and_shared",
    {"out": 2},
    [
        {"op": "const", "dest": "a", "value": 1},
        {"op": "const", "dest": "unused", "value": 2},
        {"op": "add", "dest": "b", "args": ["a", "a"]},
        {"op": "add", "dest": "c", "args": ["a", "b"]},
        {"op": "store", "args": ["b"], "buffer": "out", "offset": 0},
        {"op": "store", "args": ["c"], "buffer": "out", "offset": 1},
    ],
    [{"out": [0, 0]}],
)


def small_programs():
    """At least twelve small fixtures with exhaustively checkable domains."""

    programs = list(FIXTURES.values())
    programs += [gp.additional_program(seed) for seed in range(1000, 1008)]
    return programs


class WitnessTests(unittest.TestCase):
    """Every retrieved witness is the true minimum, checked against a scan."""

    def test_at_least_twelve_small_fixtures_are_covered(self):
        self.assertGreaterEqual(len(small_programs()), 12)

    def test_every_chosen_cycle_is_the_smallest_feasible_one(self):
        for source in small_programs():
            facts = dc.derive(source)
            compiled, _ = dcmp.compile_with_report(source)
            times = {
                op_id: cycle
                for cycle, bundle in enumerate(compiled["bundles"])
                for ids in bundle.values()
                for op_id in ids
            }
            self.assertEqual(times, brute_force_schedule(facts), source["name"])

    def test_every_chosen_address_is_the_smallest_legal_one(self):
        for source in small_programs():
            facts = dc.derive(source)
            compiled, _ = dcmp.compile_with_report(source)
            times = {
                op_id: cycle
                for cycle, bundle in enumerate(compiled["bundles"])
                for ids in bundle.values()
                for op_id in ids
            }
            live = dc.lifetimes(facts, times)
            vectors = [n for n in facts.value_names if facts.width[n] == machine.VLEN]
            scalars = [n for n in facts.value_names if facts.width[n] != machine.VLEN]
            key = lambda name: (live[name][0], facts.producers[name])
            order = sorted(vectors, key=key) + sorted(scalars, key=key)
            self.assertEqual(
                compiled["scratch"],
                brute_force_allocation(facts, times, order),
                source["name"],
            )

    def test_every_alternative_cycle_below_the_choice_is_infeasible(self):
        """Exhaust the domain below each witness, rather than trusting it."""

        for source in small_programs()[:8]:
            facts = dc.derive(source)
            times = brute_force_schedule(facts)
            calendar = {}
            for op_id in range(facts.count):
                for cycle in range(times[op_id]):
                    self.assertFalse(
                        feasible_cycle(facts, op_id, cycle, times, calendar),
                        f"{source['name']}: cycle {cycle} was free for {op_id}",
                    )
                engine = facts.engine[op_id]
                calendar[(engine, times[op_id])] = calendar.get((engine, times[op_id]), 0) + 1

    def test_every_address_below_the_choice_is_illegal(self):
        for source in small_programs()[:8]:
            facts = dc.derive(source)
            compiled, _ = dcmp.compile_with_report(source)
            times = {
                op_id: cycle
                for cycle, bundle in enumerate(compiled["bundles"])
                for ids in bundle.values()
                for op_id in ids
            }
            live = dc.lifetimes(facts, times)
            placed = {}
            vectors = [n for n in facts.value_names if facts.width[n] == machine.VLEN]
            scalars = [n for n in facts.value_names if facts.width[n] != machine.VLEN]
            key = lambda name: (live[name][0], facts.producers[name])
            for name in sorted(vectors, key=key) + sorted(scalars, key=key):
                chosen = compiled["scratch"][name]
                for address in range(chosen):
                    self.assertFalse(
                        feasible_address(facts, name, address, live, placed),
                        f"{source['name']}: address {address} was free for {name}",
                    )
                placed[name] = chosen


class StructureTests(unittest.TestCase):
    def test_structural_fixtures_all_compile_and_validate(self):
        for name, source in FIXTURES.items():
            compiled = dcmp.compile_program(source)
            machine.check_compilation(source, compiled)
            for case in source["cases"]:
                machine.check_case(source, compiled, case)

    def test_chain_cannot_beat_its_dependency_lower_bound(self):
        source = FIXTURES["chain"]
        facts = dc.derive(source)
        compiled = dcmp.compile_program(source)
        self.assertEqual(len(compiled["bundles"]), facts.cycle_lower_bound())

    def test_many_ready_operations_fill_engine_slots(self):
        source = FIXTURES["many_ready"]
        compiled = dcmp.compile_program(source)
        # Six consts on a two-slot load engine need three cycles.
        self.assertEqual(len(compiled["bundles"][0].get("load", [])), 2)
        self.assertEqual(len(compiled["bundles"][1].get("load", [])), 2)

    def test_memory_bottleneck_separates_ordered_operations(self):
        source = FIXTURES["memory_bottleneck"]
        compiled = dcmp.compile_program(source)
        machine.check_compilation(source, compiled)
        times = {
            op_id: cycle
            for cycle, bundle in enumerate(compiled["bundles"])
            for ids in bundle.values()
            for op_id in ids
        }
        for op_id in range(len(source["operations"])):
            for predecessor in machine.memory_predecessors(source, op_id):
                self.assertGreater(times[op_id], times[predecessor])

    def test_operations_appear_exactly_once_and_unchanged(self):
        for source in small_programs():
            before = copy.deepcopy(source)
            compiled = dcmp.compile_program(source)
            placed = [
                op_id
                for bundle in compiled["bundles"]
                for ids in bundle.values()
                for op_id in ids
            ]
            self.assertEqual(sorted(placed), list(range(len(source["operations"]))))
            self.assertEqual(len(placed), len(set(placed)))
            # No insertion, removal, or rewriting of the source program.
            self.assertEqual(source, before)

    def test_result_shape_matches_the_official_contract(self):
        source = FIXTURES["mixed_lifetimes"]
        compiled = dcmp.compile_program(source)
        self.assertEqual(set(compiled), {"scratch", "bundles"})
        self.assertEqual(set(compiled["scratch"]), set(machine.result_kinds(source)))
        for bundle in compiled["bundles"]:
            self.assertIsInstance(bundle, dict)
            for engine in bundle:
                self.assertIn(engine, machine.ENGINE_LIMITS)


class IndependenceBehaviourTests(unittest.TestCase):
    """The bootstrap must work with every prohibited route closed."""

    def test_compiles_with_serial_compile_patched_to_raise(self):
        def refuse(*args, **kwargs):
            raise AssertionError("the direct compiler must not call serial_compile")

        original = machine.serial_compile
        machine.serial_compile = refuse
        try:
            for source in gp.public_programs():
                compiled = dcmp.compile_program(source)
                machine.check_compilation(source, compiled)
        finally:
            machine.serial_compile = original

    def test_compiles_with_the_prohibited_modules_unimportable(self):
        blocker = _Blocker(FORBIDDEN)
        removed = {name: sys.modules.pop(name) for name in FORBIDDEN if name in sys.modules}
        sys.meta_path.insert(0, blocker)
        try:
            importlib.reload(dcmp)
            for source in gp.public_programs()[:4]:
                compiled = dcmp.compile_program(source)
                machine.check_compilation(source, compiled)
        finally:
            sys.meta_path.remove(blocker)
            sys.modules.update(removed)
            importlib.reload(dcmp)

    def test_no_prohibited_module_is_reachable_from_the_direct_path(self):
        for name in FORBIDDEN:
            sys.modules.pop(name, None)
        importlib.reload(dcmp)
        for source in gp.public_programs()[:2]:
            dcmp.compile_program(source)
        for name in FORBIDDEN:
            self.assertNotIn(name, sys.modules, f"{name} was imported during compilation")


class FailureTests(unittest.TestCase):
    def test_an_exhausted_deadline_fails_rather_than_emitting_a_partial_schedule(self):
        source = gp.stress_programs()[0]
        limits = dcmp.Limits(total_seconds=1e-6)
        with self.assertRaises(dcmp.CompilationFailure):
            dcmp.compile_with_report(source, limits)

    def test_a_starved_query_budget_fails_rather_than_falling_back(self):
        source = gp.stress_programs()[0]
        limits = dcmp.Limits(max_cover=1)
        with self.assertRaises(dcmp.CompilationFailure):
            dcmp.compile_with_report(source, limits)

    def test_report_records_the_limits_and_query_counters(self):
        source = gp.public_programs()[0]
        compiled, report = dcmp.compile_with_report(source)
        self.assertEqual(report["method"], "direct_index")
        self.assertEqual(report["limits"], dcmp.DEFAULT_LIMITS.as_dict())
        self.assertGreater(report["bootstrap"]["queries"]["queries"], 0)
        self.assertEqual(report["cycles"], len(compiled["bundles"]))
        self.assertGreaterEqual(report["cycles"], report["cycle_lower_bound"])
        self.assertGreaterEqual(report["footprint"], report["memory_lower_bound"])


class CorpusConstructionTests(unittest.TestCase):
    def test_stress_fixtures_compile_within_the_deadline(self):
        for source in gp.stress_programs():
            compiled, report = dcmp.compile_with_report(source)
            machine.check_compilation(source, compiled)
            for case in source["cases"]:
                machine.check_case(source, compiled, case)
            self.assertLess(report["seconds"], dcmp.DEFAULT_LIMITS.total_seconds)

    def test_public_programs_improve_on_the_serial_baseline(self):
        for source in gp.public_programs():
            compiled = dcmp.compile_program(source)
            baseline = machine.serial_compile(source)
            product = len(compiled["bundles"]) * machine.scratch_footprint(source, compiled)
            reference = len(baseline["bundles"]) * machine.scratch_footprint(source, baseline)
            self.assertLess(product, reference, source["name"])


if __name__ == "__main__":
    unittest.main()
