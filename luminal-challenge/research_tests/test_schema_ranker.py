"""Theory regressions and the supervised schema ranker (objective-index protocol 1.0).

Part 1 re-checks the lead's analytic finding on GENERAL exact covers (not only
the one ``exact_cover`` builds), empty/full sets, zero-width codes, training
supersets and the union of expansion depths 1 and 2. A counterexample fails the
test and must be reported, not discarded.

Part 2 tests the ranker: labels, the exact-Gini tree, the partition theorem of
its leaves, the common pool, the orderings, the seeds and the learner's import
boundary.
"""

from __future__ import annotations

import ast
import hashlib
import itertools
import json
import random
import unittest
from fractions import Fraction
from pathlib import Path

import schema_index as si

from research import objective_index_common as oic
from research import run_structural_experiments as rse
from research import schema_ranker as sr
from research import structural_encoding as se
from research import structural_models as sm

ROOT = Path(__file__).resolve().parents[1]


# --------------------------------------------------------------------------
# Part 1: expansion equivalence on general exact covers
# --------------------------------------------------------------------------


def _random_exact_covers(bits, elite, rng, count=3):
    """Exact covers of ``elite``: singletons, merged, and overlapping variants."""

    covers = [[si.Cube(bits, e, 0) for e in sorted(elite)]]
    if elite:
        built = sm.exact_cover(sorted(elite), bits, 65536, 10)
        covers.append(list(built.cubes))
    for _ in range(count):
        cubes = [si.Cube(bits, e, 0) for e in sorted(elite)]
        for _ in range(4 * len(cubes) + 4):
            if len(cubes) < 2:
                break
            a, b = rng.sample(range(len(cubes)), 2)
            x, y = cubes[a], cubes[b]
            if x.free_mask != y.free_mask:
                continue
            diff = x.anchor ^ y.anchor
            if diff.bit_count() != 1:
                continue
            merged = si.Cube(bits, x.anchor & ~diff, x.free_mask | diff)
            cubes = [c for i, c in enumerate(cubes) if i not in (a, b)] + [merged]
        # Overlap on purpose: a redundant sub-cube keeps the union exact.
        if cubes and rng.random() < 0.5:
            host = rng.choice(cubes)
            cubes.append(si.Cube(bits, next(host.members()), 0))
        covers.append(cubes)
    return covers


def _members(cubes):
    return set(sm.ordered_union(cubes))


def _ball(elite, bits, radius):
    return {e ^ sum(1 << c for c in coords) for e in elite
            for r in range(1, radius + 1) for coords in itertools.combinations(range(bits), r)}


class ExpansionEquivalence(unittest.TestCase):
    def _check(self, bits, elite, rng, supersets=2):
        checked = 0
        for cover in _random_exact_covers(bits, elite, rng):
            self.assertEqual(_members(cover), set(elite))
            expanded = sm.expand_cubes(cover, bits)
            twice = sm.expand_cubes(expanded, bits)
            universe = range(1 << bits)
            extras = [set()] + [set(rng.sample(universe, rng.randrange(0, (1 << bits) + 1)))
                                for _ in range(supersets)]
            for extra in extras:
                training = set(elite) | extra
                novel1 = [x for x in sm.ordered_union(expanded) if x not in training]
                neighbours = sorted(_ball(elite, bits, 1) - training)
                self.assertEqual(novel1, neighbours, (bits, sorted(elite), cover))
                novel12 = (_members(expanded) | _members(twice)) - training
                self.assertEqual(novel12, _ball(elite, bits, 2) - training)
                checked += 1
        return checked

    def test_every_elite_set_up_to_three_bits_under_general_covers(self):
        rng = random.Random(2026092401)
        checked = sets = 0
        for bits in range(0, 4):
            for mask in range(1 << (1 << bits)):
                elite = {i for i in range(1 << bits) if mask >> i & 1}
                checked += self._check(bits, elite, rng)
                sets += 1
        self.assertEqual(sets, 2 + 4 + 16 + 256)
        self.assertGreater(checked, 2000)

    def test_random_larger_elite_sets(self):
        rng = random.Random(2026092402)
        checked = 0
        for bits in range(4, 9):
            for _ in range(40):
                elite = set(rng.sample(range(1 << bits), rng.randrange(min(48, 1 << bits) + 1)))
                checked += self._check(bits, elite, rng, supersets=1)
        self.assertGreater(checked, 800)

    def test_zero_width_empty_and_full(self):
        for bits in (0, 1, 3):
            self.assertEqual(sm.expand_cubes([], bits), ())
            full = set(range(1 << bits))
            cover = [si.universe(bits)]
            self.assertEqual(_members(sm.expand_cubes(cover, bits)) - full, set())
        self.assertEqual(_ball({0}, 0, 2), set())

    def test_depth_one_proposal_stream_is_one_bit_mutation(self):
        rng = random.Random(7)
        checked = 0
        for bits in range(1, 8):
            for _ in range(25):
                elite = sorted(set(rng.sample(range(1 << bits), rng.randrange(1, min(20, 1 << bits) + 1))))
                cover = sm.exact_cover(elite, bits, 65536, 10).cubes
                one = [x for x, dup in sm.proposals("model_expand", bits, elite, cover, set(elite), None)
                       if not dup]
                control = [x for x, dup in sm.proposals("one_bit", bits, elite, cover, set(elite), None)
                           if not dup]
                self.assertEqual(one, control)
                checked += 1
        self.assertEqual(checked, 175)


# --------------------------------------------------------------------------
# Part 2: the ranker
# --------------------------------------------------------------------------


class Labels(unittest.TestCase):
    def test_threshold_is_the_ceil_tenth_order_statistic_with_ties(self):
        rng = random.Random(3)
        for _ in range(300):
            products = [rng.randrange(1, 30) for _ in range(rng.randrange(1, 80))]
            threshold, y = sr.labels(products)
            self.assertEqual(threshold, rse._elite_threshold(products, 0.1))
            self.assertEqual(y, [1 if p <= threshold else 0 for p in products])
            self.assertGreaterEqual(sum(y), -(-len(products) // 10))

    def test_shuffled_labels_preserve_class_count_and_are_deterministic(self):
        y = [1] * 7 + [0] * 33
        a = sr.shuffled_labels(y, 11)
        self.assertEqual(sorted(a), sorted(y))
        self.assertEqual(a, sr.shuffled_labels(y, 11))
        self.assertNotEqual(a, y)


class Tree(unittest.TestCase):
    def test_leaves_partition_the_universe(self):
        rng = random.Random(5)
        checked = 0
        for bits in (0, 1, 3, 6, 10, 20):
            for _ in range(20):
                n = rng.randrange(0, 80)
                indices = [rng.randrange(1 << bits) for _ in range(n)]
                y = [rng.randrange(2) for _ in range(n)]
                tree = sr.fit_tree(bits, indices, y)
                leaves = [leaf.cube for leaf in tree.leaves]
                self.assertEqual(sum(c.size for c in leaves), 1 << bits)
                for a, b in itertools.combinations(leaves, 2):
                    self.assertIsNone(si.intersect(a, b))
                if bits <= 10:
                    for index in range(1 << bits):
                        self.assertEqual(sum(c.contains(index) for c in leaves), 1)
                self.assertLessEqual(max(leaf.depth for leaf in tree.leaves), sr.MAX_DEPTH)
                self.assertEqual(sum(leaf.count for leaf in tree.leaves), n)
                checked += 1
        self.assertEqual(checked, 120)

    def test_best_exact_gini_split_lowest_coordinate_on_ties_and_minimum_child(self):
        # Coordinates 1 and 2 separate the labels identically: coordinate 1 wins.
        indices = [0b000, 0b001, 0b110, 0b111] * 3
        y = [0, 0, 1, 1] * 3
        tree = sr.fit_tree(3, indices, y)
        self.assertEqual(tree.splits[0]["coordinate"], 1)
        self.assertEqual(len(tree.leaves), 2)
        self.assertEqual(sorted(leaf.score for leaf in tree.leaves),
                         [Fraction(1, 8), Fraction(7, 8)])
        # A perfect split with a three-object child is inadmissible.
        indices = [0, 0, 0, 1, 1, 1, 1, 1, 1, 1]
        y = [1, 1, 1, 0, 0, 0, 0, 0, 0, 0]
        tree = sr.fit_tree(1, indices, y)
        self.assertEqual(tree.splits, ())
        self.assertEqual(len(tree.leaves), 1)
        self.assertEqual(tree.leaves[0].score, Fraction(4, 12))

    def test_pure_nodes_and_zero_gain_stop(self):
        tree = sr.fit_tree(4, list(range(16)), [0] * 16)
        self.assertEqual(len(tree.leaves), 1)
        # Labels independent of every bit in exact balance: zero gain everywhere.
        indices = [0, 1, 2, 3] * 4
        y = [0, 0, 0, 0, 1, 1, 1, 1, 0, 0, 0, 0, 1, 1, 1, 1]
        tree = sr.fit_tree(2, indices, y)
        self.assertEqual(tree.splits, ())


class Pool(unittest.TestCase):
    def test_hamming_part_order_training_exclusion_and_random_part(self):
        bits = 6
        training = [0, 1, 2, 5, 9, 17]
        elite = [0, 9]
        pool = sr.candidate_pool(bits, training, elite, 123)
        expected = []
        for distance in (1, 2):
            for e in elite:
                for coords in itertools.combinations(range(bits), distance):
                    x = e ^ sum(1 << c for c in coords)
                    if x not in training and x not in expected:
                        expected.append(x)
        hamming = expected[:256]
        self.assertEqual(pool["hamming"], len(hamming))
        self.assertTrue(set(hamming) <= set(pool["pool"]))
        self.assertEqual(pool["pool"], sorted(set(pool["pool"])))
        self.assertFalse(set(pool["pool"]) & set(training))
        self.assertEqual(pool["size"], 64 - len(training))
        self.assertTrue(pool["universe_exhausted"])
        again = sr.candidate_pool(bits, training, elite, 123)
        self.assertEqual(again, pool)

    def test_draw_cap_and_wide_universe(self):
        pool = sr.candidate_pool(20, [0], [0], 99)
        self.assertEqual(pool["hamming"], 20 + 190 if 210 < 256 else 256)
        self.assertEqual(pool["random"], 256)
        self.assertLessEqual(pool["draws"], 8192)
        self.assertEqual(pool["size"], 210 + 256)

    def test_zero_bit_universe(self):
        pool = sr.candidate_pool(0, [0], [0], 1)
        self.assertEqual(pool["pool"], [])
        self.assertTrue(pool["universe_exhausted"])

    def test_orderings_are_permutations_of_one_pool(self):
        rng = random.Random(9)
        bits = 8
        training = rng.sample(range(256), 40)
        products = [rng.randrange(10, 40) for _ in training]
        threshold, y = sr.labels(products)
        elite = sorted({i for i, label in zip(training, y) if label})
        pool = sr.candidate_pool(bits, training, elite, 5)["pool"]
        tree = sr.fit_tree(bits, training, y)
        orders = {"tree": sr.order_pool(pool, "tree", tree=tree),
                  "ascending": sr.order_pool(pool, "ascending"),
                  "hamming": sr.order_pool(pool, "hamming", elite=elite),
                  "random": sr.order_pool(pool, "random", random_seed=4)}
        for name, order in orders.items():
            self.assertEqual(sorted(order), pool, name)
        scores = [(-tree.predict(i), i) for i in orders["tree"]]
        self.assertEqual(scores, sorted(scores))
        distances = [(min((i ^ e).bit_count() for e in elite), i) for i in orders["hamming"]]
        self.assertEqual(distances, sorted(distances))


class Seeds(unittest.TestCase):
    def test_stable_seed_is_sha256_of_compact_sorted_json(self):
        parts = [oic.PROTOCOL_ID, "abc", 2026092501]
        text = json.dumps(parts, sort_keys=True, separators=(",", ":"))
        expected = int(hashlib.sha256(text.encode()).hexdigest()[:16], 16)
        self.assertEqual(oic.stable_seed(parts), expected)
        seeds = sr.arm_seeds("abc")
        self.assertEqual(seeds["pool"], expected)
        self.assertEqual(sorted(seeds["random"]), list(oic.RANDOM_ORDER_SEEDS))
        self.assertEqual(len(set(seeds["random"].values())), 10)

    def test_protocol_constants_match_the_frozen_package(self):
        report = oic.check_protocol_constants()
        self.assertEqual(report["status"], "PASS", report)
        self.assertGreater(report["checked"], 10)


class ImportBoundary(unittest.TestCase):
    def test_the_learner_imports_no_oracle_fixture_or_split_owner(self):
        forbidden = {"research.structural_oracle", "research.optimization_fixtures",
                     "research.objective_index_fixtures", "structural_oracle",
                     "optimization_fixtures", "objective_index_fixtures"}
        tree = ast.parse((ROOT / "research" / "schema_ranker.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imported |= {alias.name for alias in node.names}
            elif isinstance(node, ast.ImportFrom):
                imported |= {f"{node.module}.{alias.name}" for alias in node.names}
                imported.add(node.module or "")
        self.assertEqual(imported & forbidden, set())
        self.assertGreater(len(imported), 5)


class LearnerRun(unittest.TestCase):
    def _fixture(self):
        from research import optimization_fixtures as ofx
        from research import structural_oracle as so
        from tests_direct import generate_programs as gp

        for seed in range(920000, 920040):
            program = gp.additional_program(seed)
            facts, times, addresses, incumbent = ofx.bootstrap(program)
            orders = ofx.producing_orders(facts, times, addresses)
            for order, size, selected in ofx.candidate_tuples(orders):
                record = ofx.domain_record("f", "f", program, facts, times, addresses,
                                           incumbent, selected, 2)
                if ofx.cartesian(record) > 20_000:
                    continue
                feasible = so.enumerate_feasible(record, 70_000)["feasible"]
                if 60 <= len(feasible) <= 512 and len({x["product"] for x in feasible}) > 2:
                    return record, feasible
        self.fail("no test fixture")

    def test_arms_share_the_pool_and_report_only_validated_better_objects(self):
        record, feasible = self._fixture()
        domain = se.Domain.from_record(record)
        rng = random.Random(1)
        train = rng.sample(feasible, len(feasible) // 2)
        training = [(json.loads(x["identity"]), x["product"]) for x in train]
        min_train = min(x["product"] for x in train)
        pools = set()
        for arm in sr.ARMS:
            tag = oic.RANDOM_ORDER_SEEDS[0] if arm == "random" else None
            report = sr.rank_and_propose(domain, training, arm, None, tag, fixed_work=True)
            self.assertEqual(report["status"], "PASS", report["reason"])
            if arm == "empirical_cover":
                self.assertEqual(report["counts"]["novel"], 0)
                self.assertEqual(report["found"], [])
                continue
            pools.add(report["info"]["pool_sha256"])
            self.assertEqual(len(report["trace"]), report["counts"]["novel"])
            for item in report["found"]:
                self.assertLess(item["product"], min_train)
        self.assertEqual(len(pools), 1)

    def test_wall_time_mode_respects_its_deadline(self):
        record, feasible = self._fixture()
        domain = se.Domain.from_record(record)
        training = [(json.loads(x["identity"]), x["product"]) for x in feasible[: len(feasible) // 2]]
        ticks = iter(range(10**6))
        report = sr.rank_and_propose(domain, training, "ascending", 50, clock=lambda: next(ticks))
        self.assertEqual(report["reason"], "the budget expired")
        self.assertLess(report["counts"]["proposed"], 60)


if __name__ == "__main__":
    unittest.main()
