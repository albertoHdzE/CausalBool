"""Stage L instruments and Stage D/E decision arithmetic (next round 1.0).

The ranker must be oracle-free, the timed learner must decide exactly as the
frozen learner, the endpoint and its sensitivity must follow the plan's
arithmetic, and the selection rules must honour their tie-breaks. Synthetic
rows are used only for arithmetic; learner parity uses real domains.
"""

from __future__ import annotations

import ast
import json
import math
import tempfile
import unittest
from pathlib import Path

from research import next_round_acquisition as nra
from research import next_round_analysis as nran
from research import next_round_common as nrc
from research import next_round_learning as nrl
from research import next_round_ranker as nrr
from research import next_round_search as nrs
from research import objective_index_learned as oil
from research import objective_index_validation as oiv
from research import structural_encoding as se


ROOT = Path(__file__).resolve().parents[1]
DEV_FIXTURES = nrl.OLD_RUN / "fixtures" / "development"


class RankerIsOracleFree(unittest.TestCase):
    def test_static_imports(self):
        tree = ast.parse((ROOT / "research" / "next_round_ranker.py").read_text())
        imported = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                imported.update(f"{node.module}.{a.name}" for a in node.names)
            elif isinstance(node, ast.Import):
                imported.update(a.name for a in node.names)
        forbidden = [name for name in imported if any(
            word in name for word in ("oracle", "fixtures", "next_round_learning", "split"))]
        self.assertEqual(forbidden, [])
        self.assertIn("research.schema_ranker", imported)

    def test_orderings_are_permutations_and_deterministic(self):
        indices = list(range(0, 400, 17))[:20]
        products = [30 + (i % 7) for i in range(20)]
        pool = nrr.common_pool(12, indices, products, "d" * 64)
        self.assertTrue(set(pool["pool"]).isdisjoint(indices))
        seen = set()
        for ordering in nrr.ORDERINGS:
            a = nrr.order(ordering, 12, indices, products, pool["pool"], "d" * 64)
            b = nrr.order(ordering, 12, indices, products, pool["pool"], "d" * 64)
            self.assertEqual(a["ordered"], b["ordered"])
            self.assertEqual(sorted(map(int, a["ordered"])), sorted(pool["pool"]))
            seen.add(a["ordering_sha256"])
        self.assertEqual(len(nrr.ORDERINGS), 14)
        self.assertGreaterEqual(len(seen), 12)

    def test_seed_keys_follow_the_protocol(self):
        seeds = nrr.seeds("abc")
        self.assertEqual(seeds["pool"], nrc.stable_seed([2026092604, "abc"]))
        self.assertEqual(seeds["shuffled"], nrc.stable_seed([2026092605, "abc"]))
        self.assertEqual(seeds["random"][2026092610], nrc.stable_seed([2026092610, "abc"]))


class EndpointArithmetic(unittest.TestCase):
    def _evaluator(self, entries, threshold=10, min_train=10, min_heldout=9):
        return {"pool_entries": entries, "elite_threshold": threshold,
                "min_training_J": min_train, "min_heldout_J": min_heldout}

    def test_yield_counts_distinct_useful_and_divides_by_32(self):
        entries = [{"index": "1", "label": "feasible", "heldout": True, "product": 9,
                    "identity_sha256": "a", "useful": True},
                   {"index": "2", "label": "not_feasible"},
                   {"index": "3", "label": "feasible", "heldout": True, "product": 12,
                    "identity_sha256": "b", "useful": False},
                   {"index": "4", "label": "feasible", "heldout": True, "product": 10,
                    "identity_sha256": "a", "useful": True}]
        out = nrl.score(["2", "1", "4", "3"], self._evaluator(entries))
        self.assertEqual(out["useful_distinct"], 1)
        self.assertEqual(out["yield"], 1 / 32)
        self.assertEqual(out["positions"], 4)
        self.assertEqual(out["best_heldout_J_in_prefix"], 9)
        with self.assertRaises(ValueError):
            nrl.score(["1", "2"], self._evaluator(entries))

    def test_prefix_is_thirty_two(self):
        entries = [{"index": str(i), "label": "feasible", "heldout": True, "product": 5,
                    "identity_sha256": str(i), "useful": True} for i in range(40)]
        out = nrl.score([str(i) for i in range(40)], self._evaluator(entries))
        self.assertEqual(out["useful_distinct"], 32)
        self.assertEqual(out["yield"], 1.0)

    def test_sensitivity_range_on_every_dev_fixture(self):
        fixtures = nrl.manifest_fixtures(DEV_FIXTURES / "MANIFEST.json")
        self.assertEqual(len(fixtures), 15)
        with tempfile.TemporaryDirectory() as tmp:
            for fixture in fixtures[:5]:
                d = nrl.design(DEV_FIXTURES / fixture["fixture_id"], fixture, Path(tmp))
                s = d["sensitivity"]
                self.assertEqual(s["k"], min(32, s["N_pool"]))
                self.assertEqual(s["max_count"], min(s["k"], s["M_useful"]))
                self.assertEqual(s["min_count"], max(0, s["k"] - (s["N_pool"] - s["M_useful"])))
                self.assertEqual(s["decode_mismatches"], 0)
                ranker = json.loads(Path(d["ranker_input"]).read_text())
                self.assertEqual(len(ranker["training_indices"]), 20)
                self.assertTrue(set(ranker["pool"]).isdisjoint(ranker["training_indices"]))
                self.assertNotIn("oracle", json.dumps(ranker))
                evaluator = json.loads((Path(tmp) / fixture["fixture_id"]
                                        / "EVALUATOR.json").read_text())
                # Extremes are attainable: sort useful first / last and score.
                useful = [e["index"] for e in evaluator["pool_entries"] if e.get("useful")]
                other = [e["index"] for e in evaluator["pool_entries"] if not e.get("useful")]
                best = nrl.score(useful + other, evaluator)["useful_distinct"]
                worst = nrl.score(other + useful, evaluator)["useful_distinct"]
                self.assertEqual(best, s["max_count"])
                self.assertEqual(worst, s["min_count"])

    def test_training_draw_is_uniform_without_replacement_and_keyed(self):
        identities = [f"id{i:03d}" for i in range(60)]
        a = nrl.training_draw(identities, "f" * 64)
        b = nrl.training_draw(list(reversed(identities)), "f" * 64)
        self.assertEqual(a, b)
        self.assertEqual(len(set(a)), 20)
        self.assertNotEqual(a, nrl.training_draw(identities, "e" * 64))


class ContrastRule(unittest.TestCase):
    def _scores(self, tree, control):
        scores, families = {}, {}
        for i in range(30):
            s = {o: control for o in nrr.ORDERINGS}
            s["tree"] = tree
            scores[f"f{i}"] = s
            families[f"f{i}"] = f"fam{i % 5}"
        return scores, families

    def test_signal_requires_every_lower_bound_positive_and_gain_005(self):
        self.assertEqual(nrl.contrasts(*self._scores(0.5, 0.4))["mechanism_signal"], "PASS")
        self.assertEqual(nrl.contrasts(*self._scores(0.43, 0.4))["mechanism_signal"],
                         "FAIL_OR_INCONCLUSIVE")
        self.assertEqual(nrl.contrasts(*self._scores(0.4, 0.4))["mechanism_signal"],
                         "FAIL_OR_INCONCLUSIVE")


class TimedLearnerParity(unittest.TestCase):
    def test_timed_learner_decides_exactly_as_the_frozen_learner(self):
        compared = ready = 0
        for record in list(oiv.original_fixtures()) + oiv.recipe_fixtures(920000, 8):
            record = dict(record, target=None)
            domain = se.Domain.from_record(record)
            from research import structural_oracle as so
            feasible = so.enumerate_feasible(record, 70_000)["feasible"]
            if len(feasible) < 20:
                continue
            learners = [oil.QueryLearner(domain, "tree"), nra.TimedLearner(domain, "tree", 1e18)]
            for learner in learners:
                for item in feasible[:60]:
                    compilation = json.loads(item["identity"])
                    learner.observe({"identity": se.object_digest(compilation),
                                     "compilation": compilation, "product": item["product"]})
            statuses = [learner.prepare(1e18) for learner in learners]
            self.assertEqual(statuses[0], statuses[1])
            self.assertEqual(learners[0].info, learners[1].info)
            self.assertEqual(learners[0].queue, learners[1].queue)
            self.assertEqual(learners[0].validations, learners[1].validations)
            compared += 1
            ready += statuses[0] == "READY"
        self.assertGreater(compared, 5)
        self.assertGreater(ready, 3)

    def test_acquisition_worker_runs_the_repaired_controller(self):
        program_path = nrl.OLD_RUN / "inputs" / "development" / "seed_800021.json"
        result = nra.measure({"kind": nra.KIND, "program_path": str(program_path),
                              "program_sha256": "x", "budget_seconds": 0.1})
        self.assertEqual(result["correctness"], "PASS")
        self.assertIn("interrupted_validation_total", result)
        self.assertGreater(result["queries_with_learner"], 0)
        self.assertIs(nra.nrs, nrs)


def _row(program, family, arm, budget, rep, product, compile_seconds=0.1):
    return {"key": f"{program}|{arm}|{budget}|{rep}", "program_sha256": program,
            "family": family, "arm": arm, "budget_seconds": budget, "repetition": rep,
            "product": product, "failed_row": False, "timed_out": False,
            "process_seconds": compile_seconds + 0.05,
            "result": {"compile_seconds": compile_seconds}}


class SelectionArithmetic(unittest.TestCase):
    def test_minimum_log_j_then_compile_time_then_arm_id(self):
        rows = []
        for p in range(10):
            fam = f"fam{p % 5}"
            for rep in range(3):
                rows.append(_row(f"p{p}", fam, "b_arm", 0.1, rep, 90, 0.2))
                rows.append(_row(f"p{p}", fam, "a_arm", 0.1, rep, 90, 0.3))
                rows.append(_row(f"p{p}", fam, "c_arm", 0.1, rep, 100, 0.01))
        out = nran.select(rows, arms=("a_arm", "b_arm", "c_arm"))
        self.assertEqual(out["tie_group"], ["a_arm", "b_arm"])
        self.assertEqual(out["selected_arm"], "b_arm")
        rows = [dict(r, result={"compile_seconds": 0.2}) for r in rows]
        self.assertEqual(nran.select(rows, arms=("a_arm", "b_arm", "c_arm"))["selected_arm"],
                         "a_arm")

    def test_factorial_signs(self):
        rows = []
        values = {"cell_a4cat_heap": 80, "cell_a4cat_dfs": 90, "cell_a3cat_heap": 95,
                  "cell_a3cat_dfs": 100}
        for p in range(10):
            for arm, j in values.items():
                for rep in range(3):
                    rows.append(_row(f"p{p}", f"fam{p % 5}", arm, 0.1, rep, j))
        out = nran.factorial(rows, 0.1)
        cat = 0.5 * (math.log(80 / 95) + math.log(90 / 100))
        trav = 0.5 * (math.log(80 / 90) + math.log(95 / 100))
        inter = math.log(80 / 90) - math.log(95 / 100)
        self.assertAlmostEqual(out["catalog_effect_a4_minus_a3"]["estimate"], cat)
        self.assertAlmostEqual(out["traversal_effect_heap_minus_dfs"]["estimate"], trav)
        self.assertAlmostEqual(out["interaction"]["estimate"], inter)

    def test_target_is_floor(self):
        self.assertEqual(nran.target_of(119, 0.01), 117)
        self.assertEqual(nran.target_of(119, 0.05), 113)
        self.assertEqual(nran.target_of(100, 0.01), 99)


if __name__ == "__main__":
    unittest.main()
