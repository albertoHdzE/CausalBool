import json
import os
import sys
import unittest
from pathlib import Path

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from integration.grn_data_pipeline import GRNLoader


class TestGRNDataLoader(unittest.TestCase):
    def setUp(self) -> None:
        self.loader = GRNLoader()

    def test_lambda_phage_published_model(self) -> None:
        models = self.loader.build_published_models()
        self.assertIn("lambda_phage", models)

        net = models["lambda_phage"]
        nodes = net["nodes"]
        cm = net["cm_array"]

        expected_nodes = ["CI", "Cro", "CII", "N"]
        self.assertEqual(len(nodes), 4)
        self.assertEqual(nodes, expected_nodes)
        self.assertEqual(net["n"], 4)

        self.assertEqual(cm.shape, (4, 4))

        edges = set()
        for i in range(cm.shape[0]):
            for j in range(cm.shape[1]):
                if cm[i, j] == 1:
                    edges.add((nodes[j], nodes[i]))

        expected_edges = {
            ("Cro", "CI"),
            ("CI", "Cro"),
            ("N", "CII"),
            ("CII", "CI"),
        }

        self.assertEqual(edges, expected_edges)

        processed_path = Path(net["path"])
        self.assertTrue(processed_path.exists())

        with open(processed_path, "r") as f:
            data = json.load(f)

        self.assertEqual(data["nodes"], expected_nodes)
        self.assertEqual(len(data["cm"]), 4)
        self.assertEqual(len(data["cm"][0]), 4)


if __name__ == "__main__":
    unittest.main()
