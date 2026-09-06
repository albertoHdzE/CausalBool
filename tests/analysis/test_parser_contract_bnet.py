"""Contract test for BNetParser (AUDIT04-P4g)."""

from src.integration.BNetParser import BNetParser


class TestBNetParserContract:
    def test_valid_bnet_string_contract(self):
        parser = BNetParser()
        fixture = "targets, factors\nA, TRUE\nB, A AND NOT C\n"
        result = parser.parse_string(fixture, "test_model")
        # Contract: a valid fixture yields the stated structure.
        assert result is not None
        assert "name" in result
        assert result["name"] == "test_model"
        assert "nodes" in result and isinstance(result["nodes"], list)
        assert "edges" in result and isinstance(result["edges"], list)
        assert "rules" in result and isinstance(result["rules"], dict)
        assert result["nodes"] == ["A", "B"]
        # Each edge has the required keys.
        for edge in result["edges"]:
            assert "source" in edge
            assert "target" in edge
            assert "type" in edge

    def test_malformed_bnet_string_refuses(self):
        parser = BNetParser()
        # Malformed: line with no comma separator, which the parser skips,
        # resulting in zero nodes and a refusal (None).
        malformed = "A TRUE\n"
        result = parser.parse_string(malformed, "bad_model")
        # Contract: malformed input must refuse (None or exception),
        # never return a plausible-looking partial result.
        assert result is None

    def test_bnet_string_determinism_invariant(self):
        parser = BNetParser()
        fixture = "targets, factors\nGene1, TRUE\nGene2, Gene1 AND NOT Gene1\n"
        result1 = parser.parse_string(fixture, "inv_model")
        result2 = parser.parse_string(fixture, "inv_model")
        # Contract: parsing is deterministic on the same input.
        assert result1 == result2
        assert result1["name"] == "inv_model"

    def test_empty_string_refuses(self):
        parser = BNetParser()
        # Contract: empty input must not return a fabricated result.
        assert parser.parse_string("", "empty") is None
