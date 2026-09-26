"""R3: the oracle-free ranker boundary is the owners' algorithm, extracted.

Every definition in ``efficiency_ranker.PROVENANCE`` is compared with its owner
by AST after replacing the qualified owner references listed in ``RENAMES``;
docstrings count. The per-function hashes of both source segments are
returned by ``provenance_hashes`` and stored with the replay evidence.
"""

from __future__ import annotations

import ast
import hashlib
import unittest
from pathlib import Path

from research import efficiency_ranker as er

ROOT = Path(__file__).resolve().parents[1]


def _definitions(path: Path) -> dict:
    text = path.read_text()
    tree = ast.parse(text)
    out = {}
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
            out[node.name] = (node, ast.get_source_segment(text, node, padded=False))
    return out


class _Rename(ast.NodeTransformer):
    def visit_Attribute(self, node):
        self.generic_visit(node)
        if isinstance(node.value, ast.Name):
            qualified = f"{node.value.id}.{node.attr}"
            if qualified in er.RENAMES:
                return ast.copy_location(ast.Name(id=er.RENAMES[qualified], ctx=node.ctx), node)
        return node


def _normalised(node) -> str:
    return ast.dump(_Rename().visit(ast.parse(ast.unparse(node))), include_attributes=False)


def provenance_hashes() -> dict:
    mine = _definitions(ROOT / "research" / "efficiency_ranker.py")
    out = {}
    for name, (owner_file, owner_name) in sorted(er.PROVENANCE.items()):
        owner = _definitions(ROOT / owner_file)[owner_name]
        out[name] = {"owner": f"{owner_file}::{owner_name}",
                     "owner_segment_sha256": hashlib.sha256(owner[1].encode()).hexdigest(),
                     "extracted_segment_sha256": hashlib.sha256(mine[name][1].encode()).hexdigest(),
                     "normalised_ast_sha256": hashlib.sha256(_normalised(owner[0]).encode())
                     .hexdigest(),
                     "ast_identical_after_renames": _normalised(owner[0]) == _normalised(
                         mine[name][0])}
    return out


class ExtractionIsTheOwnersAlgorithm(unittest.TestCase):
    def test_every_extracted_definition_is_ast_identical(self):
        hashes = provenance_hashes()
        self.assertEqual(len(hashes), 13)
        for name, entry in hashes.items():
            self.assertTrue(entry["ast_identical_after_renames"], name)

    def test_a_planted_change_is_detected(self):
        owner = _definitions(ROOT / "research/schema_ranker.py")["order_pool"][0]
        planted = ast.parse(ast.unparse(owner).replace("-tree.predict(index), index",
                                                       "tree.predict(index), index"))
        self.assertNotEqual(_normalised(owner), _normalised(planted.body[0]))

    def test_constants_equal_their_owners(self):
        from research import next_round_common as nrc
        from research import next_round_ranker as nrr
        from research import schema_ranker as sr
        self.assertEqual((er.MAX_DEPTH, er.MIN_CHILD, er.ELITE_FRACTION),
                         (sr.MAX_DEPTH, sr.MIN_CHILD, sr.ELITE_FRACTION))
        self.assertEqual((er.SEED_POOL, er.SEED_SHUFFLED, er.RANDOM_ORDER_SEEDS),
                         (nrc.SEED_POOL, nrc.SEED_SHUFFLED, nrc.RANDOM_ORDER_SEEDS))
        self.assertEqual(er.ORDERINGS, nrr.ORDERINGS)

    def test_imports_are_stdlib_and_schema_index_only(self):
        import sys
        tree = ast.parse((ROOT / "research" / "efficiency_ranker.py").read_text())
        names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names |= {a.name.split(".")[0] for a in node.names}
            elif isinstance(node, ast.ImportFrom):
                names.add((node.module or "").split(".")[0])
        self.assertTrue(names)
        self.assertEqual(names - set(sys.stdlib_module_names), {"schema_index"})
        schema = ast.parse((ROOT / "schema_index.py").read_text())
        for node in ast.walk(schema):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                module = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
                self.assertIn((module or "").split(".")[0], sys.stdlib_module_names)

    def test_orderings_equal_the_owner_on_every_retained_input(self):
        import json
        from research import next_round_ranker as nrr
        from research import efficiency_common as ec
        evaluation = json.loads((ec.NEXT_ROUND_RUN / "learning" / "DESIGN_EVALUATION.json")
                                .read_text())
        compared = 0
        for design in evaluation["designs"]:
            data = json.loads(Path(design["ranker_input"]).read_text())
            args = (data["bits"], [int(i) for i in data["training_indices"]],
                    data["training_products"], [int(i) for i in data["pool"]],
                    data["domain_sha256"])
            for ordering in er.ORDERINGS:
                a, b = nrr.order(ordering, *args), er.order(ordering, *args)
                self.assertEqual((a["ordered"], a["ordering_sha256"], a["info"]),
                                 (b["ordered"], b["ordering_sha256"], b["info"]))
                compared += 1
        self.assertEqual(compared, 420)


if __name__ == "__main__":
    unittest.main()
