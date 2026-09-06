"""Contract test for LogicParser (AUDIT04-P4g)."""

import numpy as np
from src.integration.LogicParser import LogicParser


class TestLogicParserContract:
    def test_valid_logic_expression_contract(self):
        parser = LogicParser()
        # Small inline fixture: standard AND gate with two inputs.
        inputs = ["A", "B"]
        rule = "A AND B"
        result = parser.parse_and_classify(rule, inputs)
        # Contract: valid expression yields stated keys and types.
        assert isinstance(result, dict)
        assert "inputs" in result and isinstance(result["inputs"], list)
        assert "gate" in result and isinstance(result["gate"], str)
        assert "parameters" in result and isinstance(result["parameters"], dict)
        assert "truth_table" in result and isinstance(result["truth_table"], np.ndarray)
        # Shape: (2^k, k+1).
        k = len(inputs)
        expected_shape = (2**k, k + 1)
        assert result["truth_table"].shape == expected_shape
        assert result["gate"] == "AND"

    def test_malformed_logic_expression_refuses(self):
        parser = LogicParser()
        # Malformed: empty expression must not return a fabricated gate.
        try:
            result = parser.parse_and_classify("", ["A"])
            # Contract: empty or invalid expression must refuse or raise,
            # never return a plausible gate label silently.
            assert result is None or result.get("gate") not in (
                "AND", "OR", "XOR", "NOT", "NAND", "NOR", "XNOR",
                "IMPLIES", "NIMPLIES", "KOFN", "CANALISING",
                "IDENTITY", "CONST0", "CONST1",
            )
        except ValueError:
            # Explicit refusal is acceptable.
            pass

    def test_logic_parser_determinism_invariant(self):
        parser = LogicParser()
        inputs = ["X"]
        # A NOT gate definition is deterministic.
        r1 = parser.parse_and_classify("NOT X", inputs)
        r2 = parser.parse_and_classify("NOT X", inputs)
        # Contract: same input yields same output (compare serializable parts).
        assert r1["gate"] == r2["gate"] == "NOT"
        assert r1["inputs"] == r2["inputs"] == ["X"]
        # Truth tables must match elementwise.
        import numpy as np
        assert np.array_equal(r1["truth_table"], r2["truth_table"])

    def test_logic_parser_truth_table_shape_invariant(self):
        parser = LogicParser()
        # Contract: truth_table shape must always be (2^len(inputs), len(inputs)+1).
        # Use expressions appropriate to the input variables.
        rules_for_inputs = {
            1: "NOT A",
            2: "OR(A, B)",
            3: "A AND B",
            5: "W",
        }
        for inputs in (["A"], ["A", "B", "C"], ["W", "X", "Y", "Z", "P"]):
            k = len(inputs)
            rule = rules_for_inputs.get(k, inputs[0] if k > 0 else "A")
            table = parser.truth_table(rule, inputs)
            assert table.shape == (2**len(inputs), len(inputs) + 1)
