"""Contract test for GINMLParser (AUDIT04-P4g, strengthened AUDIT04-D).

WHY THIS FILE WAS REWRITTEN. The first version asserted that `result["edges"]`
was a list, over a fixture that declared NO edges. Measured by planting on
2026-09-05, dropping every edge in the parser left the whole suite green: an
empty list is a list. A fixture with no edges cannot defend edge parsing, so the
fixture is what had to change first.

Every expected value below is derived by hand from the fixture and the parser's
documented sign mapping, never by running the parser and recording its output.
"""

import os
import tempfile
from pathlib import Path

from src.integration.GINMLParser import GINMLParser

# Three nodes and three edges, one per sign class the parser distinguishes, so
# that dropping edges, dropping one edge, or collapsing the sign mapping are all
# separately detectable. C is multi-valued, which exercises the binarisation the
# parser is required to make visible rather than silent.
THREE_EDGE_GINML = """<?xml version="1.0"?>
<gxl>
  <graph>
    <node id="A" maxvalue="1">
      <value val="1"><exp str="C"/></value>
    </node>
    <node id="B" maxvalue="1"/>
    <node id="C" maxvalue="2">
      <value val="1"><exp str="A AND NOT B"/></value>
      <value val="2"><exp str="A AND B"/></value>
    </node>
    <edge from="A" to="C" sign="positive"/>
    <edge from="B" to="C" sign="negative"/>
    <edge from="C" to="A" sign="dual"/>
  </graph>
</gxl>"""


def _write(fixture: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".ginml", delete=False, mode="w") as f:
        f.write(fixture)
        return Path(f.name)


def _parse(fixture: str):
    temp_path = _write(fixture)
    try:
        return GINMLParser().parse_file(temp_path)
    finally:
        os.unlink(temp_path)


class TestGINMLParserContract:
    def test_every_edge_survives_with_its_sign(self):
        """The defect this catches: edges dropped, or every sign collapsed.

        Asserted as the exact list in document order. The three signs are given
        deliberately different classes, so a mapping that returned "unknown"
        for everything -- which still yields three edges -- fails here too.
        """
        result = _parse(THREE_EDGE_GINML)
        assert result is not None
        assert result["edges"] == [
            {"source": "A", "target": "C", "type": "activation"},
            {"source": "B", "target": "C", "type": "inhibition"},
            {"source": "C", "target": "A", "type": "dual"},
        ]

    def test_every_node_survives_the_parse(self):
        result = _parse(THREE_EDGE_GINML)
        assert result["nodes"] == ["A", "B", "C"]

    def test_binarisation_of_a_multivalued_node_is_declared_not_silent(self):
        """C declares maxvalue 2 and carries a rule for each level.

        The parser keeps the val="1" rule as the Boolean condition, which is an
        approximation it is required to RECORD. Pinning it here is what stops a
        model entering the corpus looking Boolean when it is not -- the failure
        VERIFICATION.md records at 582 of 5882 nodes across the corpus.
        """
        result = _parse(THREE_EDGE_GINML)
        assert result["logic"]["C"] == "A AND NOT B"
        assert result["node_max_values"] == {"A": 1, "B": 1, "C": 2}
        assert result["meta"]["is_multivalued"] is True
        assert result["meta"]["multivalued_nodes"] == ["C"]
        assert result["meta"]["discarded_value_rules"] == {"C": ["2"]}

    def test_a_node_with_no_rule_gets_no_fabricated_logic(self):
        """B declares no value element, so it must be ABSENT from logic.

        A parser that invented "FALSE" here would be indistinguishable from one
        reading a real constant-zero rule.
        """
        result = _parse(THREE_EDGE_GINML)
        assert "B" not in result["logic"]
        assert set(result["logic"]) == {"A", "C"}

    def test_xml_without_a_graph_refuses(self):
        assert _parse('<?xml version="1.0"?><gxl></gxl>') is None

    def test_parse_is_deterministic(self):
        """The SAME file parsed twice.

        `name` and `meta.file_name` are derived from the filename, so two
        temporary paths differ for a reason unrelated to determinism.
        """
        temp_path = _write(THREE_EDGE_GINML)
        try:
            parser = GINMLParser()
            assert parser.parse_file(temp_path) == parser.parse_file(temp_path)
        finally:
            os.unlink(temp_path)
