"""Contract test for LogicParser (AUDIT04-P4g, strengthened AUDIT04-D).

WHY THIS FILE WAS REWRITTEN. The first version asserted gate LABELS and table
SHAPE. Measured by planting on 2026-09-05, reversing the input bit ordering
(`bits[::-1]` in `truth_table`) left the whole suite green.

The reason is worth stating, because it also refutes the fix recorded in commit
551edb6, which said an ASYMMETRIC gate was needed. Reversal keeps every row
internally consistent and only permutes the row ORDER, and
`classify_truth_table` recomputes the expected column from the input columns of
the table it is handed. So the label is invariant under the defect:

    'A AND B'      good=AND         planted=AND
    'A AND NOT B'  good=CANALISING  planted=CANALISING

Asymmetry is irrelevant. What catches it is an ELEMENTWISE assertion on the
input enumeration itself, which is what this file now makes. That enumeration is
load-bearing: the whole project is ordering-aware through the Phi bit-reversal
mapping, so the row order is part of the contract and not an implementation
detail.

Every expected array below is written out by hand from the gate definition.
"""

import numpy as np

from src.integration.LogicParser import LogicParser


class TestLogicParserContract:
    def test_input_enumeration_is_msb_first_and_exact(self):
        """The row ordering convention, pinned independently of any gate.

        `format(idx, "03b")` is MSB-first, so row 1 must be [0, 0, 1] and row 4
        must be [1, 0, 0]. Under a reversed enumeration row 1 becomes [1, 0, 0]
        and this fails, whatever rule is being evaluated.
        """
        table = LogicParser().truth_table("A AND B AND C", ["A", "B", "C"])
        expected_inputs = np.array([
            [0, 0, 0],
            [0, 0, 1],
            [0, 1, 0],
            [0, 1, 1],
            [1, 0, 0],
            [1, 0, 1],
            [1, 1, 0],
            [1, 1, 1],
        ])
        assert np.array_equal(table[:, :3], expected_inputs)

    def test_asymmetric_rule_truth_table_elementwise(self):
        """`A AND NOT B`, every cell derived by hand.

        Rows are (A, B, out): 00 -> 0, 01 -> 0, 10 -> 1, 11 -> 0.
        """
        table = LogicParser().truth_table("A AND NOT B", ["A", "B"])
        expected = np.array([
            [0, 0, 0],
            [0, 1, 0],
            [1, 0, 1],
            [1, 1, 0],
        ])
        assert np.array_equal(table, expected)

    def test_functional_mode_negation_is_exercised(self):
        """`AND(NOT(A), B)` -- the only route that reaches the functional NOT.

        `_uses_functional_syntax` looks for "AND(", "OR(", "XOR(" and so on, but
        NOT "NOT(". So a rule written as `NOT(X)` alone is dispatched to the
        INFIX evaluator, where NOT is rewritten to Python's `not` and happens to
        give the right answer. The functional-mode negation is therefore only
        reachable when nested inside another functional call, and until this test
        existed nothing in the suite reached it at all.

        Rows are (A, B, out): 00 -> 0, 01 -> 1, 10 -> 0, 11 -> 0.
        """
        parser = LogicParser()
        rule = "AND(NOT(A), B)"
        assert parser._uses_functional_syntax(rule) is True
        expected = np.array([
            [0, 0, 0],
            [0, 1, 1],
            [1, 0, 0],
            [1, 1, 0],
        ])
        assert np.array_equal(parser.truth_table(rule, ["A", "B"]), expected)

    def test_single_input_gates_elementwise(self):
        parser = LogicParser()
        assert np.array_equal(
            parser.truth_table("NOT A", ["A"]), np.array([[0, 1], [1, 0]])
        )
        assert np.array_equal(
            parser.truth_table("A", ["A"]), np.array([[0, 0], [1, 1]])
        )

    def test_classification_labels_the_hand_written_tables(self):
        parser = LogicParser()
        for rule, inputs, gate in [
            ("A AND B", ["A", "B"], "AND"),
            ("A OR B", ["A", "B"], "OR"),
            ("A XOR B", ["A", "B"], "XOR"),
            ("NOT A", ["A"], "NOT"),
            ("A AND NOT B", ["A", "B"], "CANALISING"),
        ]:
            assert parser.parse_and_classify(rule, inputs)["gate"] == gate

    def test_malformed_expression_refuses(self):
        parser = LogicParser()
        try:
            result = parser.parse_and_classify("", ["A"])
        except ValueError:
            return
        assert result is None or result.get("gate") in ("CUSTOM",)

    def test_parse_is_deterministic(self):
        parser = LogicParser()
        r1 = parser.parse_and_classify("A AND NOT B", ["A", "B"])
        r2 = parser.parse_and_classify("A AND NOT B", ["A", "B"])
        assert r1["gate"] == r2["gate"]
        assert np.array_equal(r1["truth_table"], r2["truth_table"])
