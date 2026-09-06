"""Contract test for GINMLParser (AUDIT04-P4g)."""

import pytest
from pathlib import Path
from src.integration.GINMLParser import GINMLParser


class TestGINMLParserContract:
    def test_valid_ginml_string_contract(self):
        parser = GINMLParser()
        # Minimal inline GINML-like XML fixture.
        fixture = """<?xml version="1.0"?>
<gxl>
  <graph>
    <node id="A" maxvalue="1"/>
    <node id="B" maxvalue="1"/>
  </graph>
</gxl>"""
        # We write to a temporary file because parse_file takes a Path.
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".ginml", delete=False, mode="w") as f:
            f.write(fixture)
            temp_path = Path(f.name)
        try:
            result = parser.parse_file(temp_path)
            # Contract: valid fixture yields stated structure.
            assert result is not None
            assert "name" in result and isinstance(result["name"], str)
            assert "nodes" in result and isinstance(result["nodes"], list)
            assert "edges" in result and isinstance(result["edges"], list)
            assert "logic" in result and isinstance(result["logic"], dict)
            # Nodes present.
            assert len(result["nodes"]) == 2
        finally:
            os.unlink(temp_path)

    def test_malformed_ginml_string_refuses(self):
        parser = GINMLParser()
        import tempfile, os
        # Malformed: XML without <graph>.
        fixture = "<?xml version=\"1.0\"?><gxl></gxl>"
        with tempfile.NamedTemporaryFile(suffix=".ginml", delete=False, mode="w") as f:
            f.write(fixture)
            temp_path = Path(f.name)
        try:
            result = parser.parse_file(temp_path)
            # Contract: malformed file must refuse (None or exception),
            # never return a plausible partial result.
            assert result is None
        finally:
            os.unlink(temp_path)

    def test_ginml_parse_determinism_invariant(self):
        parser = GINMLParser()
        fixture = "<?xml version=\"1.0\"?><gxl><graph>" \
                  "<node id=\"N1\" maxvalue=\"1\"/>" \
                  "</graph></gxl>"
        import tempfile, os
        with tempfile.NamedTemporaryFile(suffix=".ginml", delete=False, mode="w") as f:
            f.write(fixture)
            temp_path = Path(f.name)
        try:
            r1 = parser.parse_file(temp_path)
            r2 = parser.parse_file(temp_path)
            assert r1 is not None
            assert r1 == r2
            assert r1["nodes"] == ["N1"]
        finally:
            os.unlink(temp_path)
