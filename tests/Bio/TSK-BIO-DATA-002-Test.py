import os
import sys
import unittest

import numpy as np

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../src")))

from integration.LogicParser import LogicParser
from integration.grn_data_pipeline import GRNLoader


class TestLogicParser(unittest.TestCase):
    def setUp(self) -> None:
        self.parser = LogicParser()

    def test_truth_table_A_AND_NOT_B(self) -> None:
        inputs = ["A", "B"]
        table = self.parser.truth_table("A AND NOT B", inputs)

        self.assertEqual(table.shape, (4, 3))

        expected_inputs = np.array([[0, 0], [0, 1], [1, 0], [1, 1]], dtype=int)
        expected_outputs = np.array([0, 0, 1, 0], dtype=int)

        np.testing.assert_array_equal(table[:, :2], expected_inputs)
        np.testing.assert_array_equal(table[:, 2], expected_outputs)

    def test_classification_canalising(self) -> None:
        inputs = ["A", "B"]
        result = self.parser.parse_and_classify("A AND NOT B", inputs)

        self.assertEqual(result["gate"], "CANALISING")
        table = result["truth_table"]
        self.assertEqual(table.shape, (4, 3))

        params = result["parameters"]
        self.assertIn("canalisingIndex", params)
        self.assertIn("canalisingValue", params)
        self.assertIn("canalisedOutput", params)

    def test_simple_and_gate_classification(self) -> None:
        inputs = ["A", "B"]
        result = self.parser.parse_and_classify("A AND B", inputs)
        self.assertEqual(result["gate"], "AND")

    def test_lambda_phage_gate_histogram(self) -> None:
        loader = GRNLoader()
        models = loader.build_published_models()
        net = models["lambda_phage"]

        self.assertIn("gates", net)
        self.assertIn("gate_histogram", net)

        hist = net["gate_histogram"]
        self.assertGreaterEqual(hist.get("CANALISING", 0), 1)
        self.assertGreaterEqual(hist.get("NOT", 0), 1)


if __name__ == "__main__":
    unittest.main()
