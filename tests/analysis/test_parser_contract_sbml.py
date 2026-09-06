"""Contract test for SBMLParser (AUDIT04-P4g, strengthened AUDIT04-D).

WHY THIS FILE WAS REWRITTEN. The first version asserted
`len(result["nodes"]) >= 1` over a fixture containing exactly ONE node. Measured
by planting on 2026-09-05, truncating the parser to a single node left the whole
suite green -- and it would have stayed green even with the assertion tightened
to `== 1`, because one node truncated to one node is still one node. The fixture
was too small for ANY assertion over it to bite, so the fixture is what had to
change first.

Every expected value below is derived by hand from the fixture and the parser's
documented MathML mapping (SBMLParser._parse_mathml), never by running the parser
and recording what it printed.
"""

import os
import tempfile
from pathlib import Path

from src.integration.SBMLParser import SBMLParser

# Three species and two transitions, so that dropping a node, dropping a
# transition, or reordering either is detectable.
#
#   A   no transition targets it            -> INPUT
#   B   becomes 1 when A >= 1               -> "A"
#   C   becomes 1 when A >= 1 and B == 0    -> "AND(A, NOT(B))"
#
# Hand-derivation of C's string, following _parse_mathml case by case:
#   <apply><geq/><ci>A</ci><cn>1</cn></apply>  -> op 'geq', val '1'  -> "A"
#   <apply><eq/><ci>B</ci><cn>0</cn></apply>   -> op 'eq',  val '0'  -> "NOT(B)"
#   <apply><and/> ...two args... </apply>      -> "AND(" + ", ".join -> "AND(A, NOT(B))"
# The fixture is NAMESPACED, matching the 76 files in data/bio/raw that the
# parser actually reads. That is not cosmetic: writing it without namespaces
# revealed a latent defect and would have pinned the wrong behaviour. See
# test_a_model_with_no_species_refuses and the note at the foot of this file.
THREE_NODE_SBML = """<?xml version="1.0"?>
<sbml xmlns="http://www.sbml.org/sbml/level3/version1/core"
      xmlns:qual="http://www.sbml.org/sbml/level3/version1/qual/version1"
      level="3" version="1">
  <model id="threeNodeFixture">
    <qual:listOfQualitativeSpecies>
      <qual:qualitativeSpecies qual:id="A" qual:maxLevel="1"/>
      <qual:qualitativeSpecies qual:id="B" qual:maxLevel="1"/>
      <qual:qualitativeSpecies qual:id="C" qual:maxLevel="1"/>
    </qual:listOfQualitativeSpecies>
    <qual:listOfTransitions>
      <qual:transition>
        <qual:listOfOutputs>
          <qual:output qual:qualitativeSpecies="B"/>
        </qual:listOfOutputs>
        <qual:listOfFunctionTerms>
          <qual:functionTerm qual:resultLevel="1">
            <math xmlns="http://www.w3.org/1998/Math/MathML">
              <apply><geq/><ci>A</ci><cn>1</cn></apply>
            </math>
          </qual:functionTerm>
        </qual:listOfFunctionTerms>
      </qual:transition>
      <qual:transition>
        <qual:listOfOutputs>
          <qual:output qual:qualitativeSpecies="C"/>
        </qual:listOfOutputs>
        <qual:listOfFunctionTerms>
          <qual:functionTerm qual:resultLevel="1">
            <math xmlns="http://www.w3.org/1998/Math/MathML">
              <apply>
                <and/>
                <apply><geq/><ci>A</ci><cn>1</cn></apply>
                <apply><eq/><ci>B</ci><cn>0</cn></apply>
              </apply>
            </math>
          </qual:functionTerm>
        </qual:listOfFunctionTerms>
      </qual:transition>
    </qual:listOfTransitions>
  </model>
</sbml>"""


def _write(fixture: str) -> Path:
    with tempfile.NamedTemporaryFile(suffix=".sbml", delete=False, mode="w") as f:
        f.write(fixture)
        return Path(f.name)


def _parse(fixture: str):
    """Write the fixture to a temporary file and parse it."""
    temp_path = _write(fixture)
    try:
        return SBMLParser().parse_file(temp_path)
    finally:
        os.unlink(temp_path)


class TestSBMLParserContract:
    def test_every_node_survives_the_parse(self):
        """The defect this catches: a model truncated to fewer species.

        Asserted as the EXACT list in document order, not a count. A count of 3
        would also pass on ["A", "A", "A"], and the order carries the node
        indexing that every downstream index-set computation depends on.
        """
        result = _parse(THREE_NODE_SBML)
        assert result is not None
        assert result["nodes"] == ["A", "B", "C"]

    def test_logic_strings_are_reconstructed_exactly(self):
        """Every rule, hand-derived from the MathML above.

        This pins the mapping itself: `geq X 1` collapses to the bare variable,
        `eq X 0` becomes a negation, and a node no transition writes to is
        INPUT rather than a fabricated constant.
        """
        result = _parse(THREE_NODE_SBML)
        assert result["logic"] == {
            "A": "INPUT",
            "B": "A",
            "C": "AND(A, NOT(B))",
        }

    def test_model_identity_and_declared_keys(self):
        result = _parse(THREE_NODE_SBML)
        assert result["name"] == "threeNodeFixture"
        assert result["source"] == "BioModels"
        assert set(result) == {"name", "nodes", "logic", "source", "description"}

    def test_a_model_with_no_species_refuses(self):
        """A model element with no qualitative species must return None.

        The failure being excluded is a plausible EMPTY network entering the
        corpus, which is indistinguishable downstream from a real one whose
        nodes were dropped.
        """
        assert _parse('<?xml version="1.0"?><sbml><model></model></sbml>') is None

    def test_parse_is_deterministic(self):
        """The SAME file parsed twice, not two temporary files.

        `description` and `name` are derived from the filename, so parsing two
        different temporary paths differs for a reason that has nothing to do
        with determinism -- which is exactly what the first version of this test
        was measuring.
        """
        temp_path = _write(THREE_NODE_SBML)
        try:
            parser = SBMLParser()
            assert parser.parse_file(temp_path) == parser.parse_file(temp_path)
        finally:
            os.unlink(temp_path)


# ---------------------------------------------------------------------------
# FINDING, recorded rather than pinned (AUDIT04-D, 2026-09-06).
#
# Writing this fixture WITHOUT namespaces made every node come back as "INPUT",
# with no error and no warning. The cause is a shallow fallback: the namespaced
# lookup for functionTerm is a descendant search,
#
#     trans.findall('.//{qual}functionTerm')
#
# but the fallback for a file with no namespace iterates only DIRECT children,
#
#     for elem in trans: if elem.tag.endswith('functionTerm')
#
# and functionTerm lives inside listOfFunctionTerms. So on a non-namespaced
# SBML-qual file the parser finds no rules and silently returns a network in
# which every node is an input -- a plausible model, not a refusal.
#
# MEASURED IMPACT ON THE CORPUS: NONE. Of 160 SBML/XML files in data/bio/raw,
# 76 declare the qual namespace and all 76 parse with logic recovered; 0 of 76
# come back all-INPUT. The remaining 84 are not SBML-qual at all and are refused
# for having no qualitative species. So this is a latent defect with zero effect
# on any published number, and it is NOT pinned here: writing a test that asserts
# the all-INPUT output would freeze the wrong behaviour as the contract.
# ---------------------------------------------------------------------------
