"""Unit tests for src/description_lengths.py — the VALUES, not just the shape.

AUDIT03-C. The existing suite (test_description_length_is_algorithmic.py) proves
the measure is *algorithmic* rather than entropy-derived: additivity under
repetition, independence of the surrounding gate distribution, no ensemble
vocabulary. Those are the right properties and they are well tested.

What nothing tested was the ARITHMETIC. Coverage of the owner was 60%, and the
missing lines were precisely the per-gate cost branches:

    88  include_header      93  KOFN      95  CANALISING
    97  IMPLIES/NIMPLIES   111  empty graph

The mutation harness found the same hole from the other side: mutants that
change the catalogue size, drop the in-degree field, or price the wrong subset
all SURVIVED the Python tier. A measure whose published value is 135.66005 bits
deserves tests that would notice it becoming 134.

Every expected value here is derived from the cost model IN THE TEST, from the
declared field widths, not copied from the implementation's output. A test that
asserts f(x) == f(x) proves nothing.
"""
from __future__ import annotations

import math
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import description_lengths as dl  # noqa: E402

TWELVE = math.log2(12)


def expected_node_cost(n, d, gate, include_header=False, in_degree_field=True):
    """The cost model written out independently of the implementation.

    Fields, in the order a decoder must read them:
      log2(12)            which of the twelve families
      log2(n)             graph header, only when charged
      log2(n+1)           the in-degree d (n+1 values: 0..n)
      log2(C(n,d))        which d-subset of the n coordinates
      + a gate-specific payload
    """
    cost = math.log2(12)
    if include_header:
        cost += math.log2(max(1, n))
    if in_degree_field:
        cost += math.log2(n + 1)
    cost += math.log2(max(1, math.comb(n, d)))
    if gate == "KOFN":
        cost += math.log2(d + 1) + 1          # k in 0..d, plus the strict bit
    elif gate == "CANALISING":
        cost += math.log2(max(1, n)) + 2      # index, value, canalised output
    elif gate in ("IMPLIES", "NIMPLIES"):
        cost += math.log2(max(1, d * (d - 1)))  # the ordered pair
    elif gate == "NOT":
        cost += math.log2(max(1, d))
    else:
        cost += 1
    return cost


# ── every family, every branch, against an independent statement ─────────────

@pytest.mark.parametrize("gate", list(dl.GATE_LABELS))
@pytest.mark.parametrize("n,d", [(4, 1), (4, 2), (6, 3), (10, 2), (10, 5)])
def test_node_cost_matches_the_declared_field_widths(gate, n, d):
    assert dl.node_description_cost(n, d, gate) == pytest.approx(
        expected_node_cost(n, d, gate), abs=1e-12)


def test_the_catalogue_has_exactly_twelve_families():
    # A thirteenth family is a research decision (R4), not an accident. If this
    # fails, log2(12) is no longer the family field and every published D moves.
    assert len(dl.GATE_LABELS) == 12
    assert len(set(dl.GATE_LABELS)) == 12


def test_gate_field_is_log2_twelve():
    # AND at n=1,d=1 pays: family + in-degree + subset(1 of 1) + default 1 bit.
    got = dl.node_description_cost(1, 1, "AND")
    assert got == pytest.approx(TWELVE + math.log2(2) + 0.0 + 1, abs=1e-12)


def test_kofn_pays_for_k_and_the_strict_bit():
    d = 4
    delta = dl.node_description_cost(8, d, "KOFN") - dl.node_description_cost(8, d, "AND")
    assert delta == pytest.approx(math.log2(d + 1) + 1 - 1, abs=1e-12)


def test_canalising_pays_index_value_and_output():
    n, d = 8, 3
    delta = dl.node_description_cost(n, d, "CANALISING") - dl.node_description_cost(n, d, "AND")
    assert delta == pytest.approx(math.log2(n) + 2 - 1, abs=1e-12)


def test_not_pays_which_input_it_negates():
    n, d = 8, 4
    delta = dl.node_description_cost(n, d, "NOT") - dl.node_description_cost(n, d, "AND")
    assert delta == pytest.approx(math.log2(d) - 1, abs=1e-12)


@pytest.mark.parametrize("gate", ["IMPLIES", "NIMPLIES"])
def test_implies_ordered_pair_costs_one_bit_at_the_only_reachable_arity(gate):
    # AUDIT03-B measured this: IMPLIES is binary, so d == 2 always and
    # log2(d(d-1)) = log2 2 = 1 -- identical to the default branch. The field
    # prices an ordered pair the engine cannot choose (the caller sorts), and
    # the cost consequence is exactly zero. Pinned so a "simplification" that
    # moves a published number cannot pass silently.
    assert dl.node_description_cost(10, 2, gate) == pytest.approx(
        dl.node_description_cost(10, 2, "AND"), abs=1e-12)


# ── the in-degree field: without it this is not a description length ─────────

@pytest.mark.parametrize("n", [1, 4, 10])
def test_dropping_the_in_degree_field_costs_exactly_log2_n_plus_one(n):
    with_f = dl.node_description_cost(n, 2 if n > 1 else 1, "AND", in_degree_field=True)
    without = dl.node_description_cost(n, 2 if n > 1 else 1, "AND", in_degree_field=False)
    assert with_f - without == pytest.approx(math.log2(n + 1), abs=1e-12)


def test_the_code_is_uniquely_decodable_kraft_sum_at_most_one():
    """Kraft: sum over every EXPRESSIBLE node-code of 2^-L must be <= 1.

    This is the property that makes D a length rather than a number. Without the
    in-degree field the sum is n+1 rather than 1 -- the defect AUDIT03/R2b
    removed -- so both arms are asserted.
    """
    import itertools
    n = 4
    total_with = total_without = 0.0
    for d in range(1, n + 1):
        for _ in itertools.combinations(range(n), d):
            for g in dl.GATE_LABELS:
                if g in ("IMPLIES", "NIMPLIES") and d != 2:
                    continue
                if g == "NOT" and d != 1:
                    continue
                total_with += 2 ** -dl.node_description_cost(n, d, g)
                total_without += 2 ** -dl.node_description_cost(
                    n, d, g, in_degree_field=False)
    assert total_with <= 1.0
    assert total_without > total_with     # the field is doing real work


def test_include_header_charges_log2_n():
    n, d = 8, 3
    delta = (dl.node_description_cost(n, d, "AND", include_header=True)
             - dl.node_description_cost(n, d, "AND", include_header=False))
    assert delta == pytest.approx(math.log2(n), abs=1e-12)


# ── the graph-level wrapper ─────────────────────────────────────────────────

def test_empty_graph_costs_nothing():
    assert dl.graph_gate_index_length({}, {}) == 0.0


def test_graph_length_is_the_header_plus_every_node():
    degs = {0: 2, 1: 1, 2: 3}
    gates = {0: "AND", 1: "NOT", 2: "XOR"}
    n = 3
    expected = math.log2(n) + sum(
        expected_node_cost(n, degs[v], gates[v]) for v in range(n))
    assert dl.graph_gate_index_length(degs, gates) == pytest.approx(expected, abs=1e-12)


def test_the_published_flagship_anchor_does_not_move():
    """D_formula = 135.66005 bits on the 10-node mixed flagship.

    Quoted in BOTH manuscripts. Pinned here so a change to the cost model is a
    deliberate, visible act rather than something noticed later in a diff.
    """
    cm10 = [
        [0, 1, 1, 0, 0, 0, 0, 0, 0, 0], [1, 0, 1, 0, 0, 0, 0, 0, 0, 0],
        [0, 0, 0, 1, 1, 0, 0, 0, 0, 0], [0, 1, 1, 0, 1, 0, 0, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0], [0, 0, 0, 0, 1, 0, 1, 0, 0, 0],
        [0, 0, 0, 0, 0, 1, 0, 0, 0, 0], [1, 0, 0, 0, 0, 0, 0, 0, 1, 0],
        [0, 1, 0, 0, 0, 0, 0, 0, 0, 1], [0, 0, 1, 1, 0, 0, 1, 1, 0, 0]]
    dyn10 = ["AND", "OR", "XOR", "KOFN", "NOR", "XNOR", "NOT",
             "IMPLIES", "NIMPLIES", "MAJORITY"]
    n = 10
    total = sum(dl.node_description_cost(n, sum(cm10[v]), dyn10[v])
                for v in range(n))
    assert total == pytest.approx(135.66005, abs=1e-5)


# ── variant E: the catalogue-free schema normal form ────────────────────────

def test_schema_length_of_a_constant_function_is_minimal():
    # A constant-0 function needs no schema at all; a constant-1 needs the
    # all-don't-care schema. Neither may cost more than a two-input AND.
    n = 2
    const0 = dl.schema_normal_form_length([0, 0, 0, 0], n)
    and2 = dl.schema_normal_form_length([0, 0, 0, 1], n)
    assert const0 <= and2


def test_schema_length_is_invariant_under_input_relabelling():
    """D_schema sits in BDM's invariance class -- that is why AUDIT03/R3 could
    compare the two at all. Relabelling the coordinates of a symmetric function
    must not change its schema length."""
    n = 3
    xor3 = [bin(i).count("1") % 2 for i in range(8)]
    base = dl.schema_normal_form_length(xor3, n)
    for perm in [(0, 2, 1), (1, 0, 2), (2, 1, 0)]:
        relabelled = [0] * 8
        for i in range(8):
            bits = [(i >> k) & 1 for k in range(n)]
            j = sum(bits[perm[k]] << k for k in range(n))
            relabelled[j] = xor3[i]
        assert dl.schema_normal_form_length(relabelled, n) == pytest.approx(base)


def test_a_more_structured_function_is_not_longer_than_a_random_one():
    n = 3
    and3 = [1 if i == 7 else 0 for i in range(8)]
    scattered = [1, 0, 1, 1, 0, 1, 0, 0]
    assert (dl.schema_normal_form_length(and3, n)
            <= dl.schema_normal_form_length(scattered, n))


# ── the pinned dependency ───────────────────────────────────────────────────

def test_pybdm_pin_is_declared_and_enforced():
    assert dl.PYBDM_PIN == "0.1.0"
    # _check_pybdm must RAISE on a mismatch, not warn: the published BDM values
    # depend on this version's edge semantics.
    import types
    fake = types.SimpleNamespace(__version__="9.9.9")
    real = sys.modules.get("pybdm")
    sys.modules["pybdm"] = fake
    try:
        with pytest.raises(RuntimeError, match="pinned"):
            dl._check_pybdm()
    finally:
        if real is not None:
            sys.modules["pybdm"] = real
        else:
            sys.modules.pop("pybdm", None)


# ── the cross-project delegations, which are DECLARED EXCEPTIONS ────────────
#
# Variant A and variant C both delegate outside this repository's root package,
# to imp-causalNet-paper. GOVERNANCE/CORE.md records that as deliberate, not an
# accident. A declared exception still needs a test: "documented" is not
# "working", and this audit has already found a documented owner that had been
# reimplemented by the wrapper that declared it canonical.

def test_variant_a_delegates_and_returns_a_length():
    """Variant A must reach the canonical implementation and price a real graph.

    src/description_lengths.py used to REIMPLEMENT this variant while its own
    governance document named imp-causalNet-paper as canonical. It now
    delegates; this asserts the delegation is live, not just intended.
    """
    adjacency = [[0, 1, 0], [1, 0, 1], [0, 1, 0]]
    bits = dl.row_run_index_set_length(adjacency)
    assert isinstance(bits, float)
    assert bits > 0


def test_variant_a_is_symmetric_under_neighbourhood_complement():
    """MEASURED, after a wrong guess of mine: variant A gives the IDENTICAL
    length for the emptiest and the densest graph, at every n from 2 to 6
    (n=2: 4.7549 vs 4.7549 ... n=6: 19.6515 vs 19.6515).

    That is not a defect. The row-run code names a SUBSET, and naming costs
    log2 C(n,d); since C(n,0) = C(n,n) = 1, the empty neighbourhood and the full
    one are equally cheap to name. Length is therefore symmetric about d = n/2
    and MAXIMAL in the middle, not at the top.

    Pinned because "longer graph = more edges" is the intuition a reader brings,
    and it is false here.
    """
    for n in range(2, 7):
        empty = dl.row_run_index_set_length([[0] * n for _ in range(n)])
        full = dl.row_run_index_set_length([[1] * n for _ in range(n)])
        assert empty == pytest.approx(full), f"asymmetry appeared at n={n}"


def test_variant_a_is_maximal_at_mid_degree():
    """The corollary: a half-full neighbourhood is the expensive one."""
    n = 6
    lengths = []
    for d in range(0, n + 1):
        row = [1] * d + [0] * (n - d)
        lengths.append(dl.row_run_index_set_length([row[:] for _ in range(n)]))
    assert max(lengths) == lengths[n // 2]
    assert lengths[0] == pytest.approx(lengths[n])


def test_elias_gamma_lengths_are_odd_and_correct():
    # gamma(1)=1, gamma(2)=gamma(3)=3, gamma(4..7)=5 -- the standard code.
    assert dl._gamma_len(1) == 1
    assert dl._gamma_len(2) == dl._gamma_len(3) == 3
    assert all(dl._gamma_len(x) == 5 for x in (4, 5, 6, 7))
    assert all(dl._gamma_len(x) % 2 == 1 for x in range(1, 64))


# ── bdm_2d: the edge semantics differ per consumer, so they are pinned ──────

def test_bdm_is_a_positive_number_for_a_normal_block():
    a = [[0, 1, 0, 1], [1, 0, 1, 0], [0, 0, 1, 1], [1, 1, 0, 0]]
    assert dl.bdm_2d(a) > 0


def test_bdm_below_floor_semantics_are_selected_explicitly_never_silently():
    """Three consumers wanted three different things below 4 atoms. Choosing
    silently is how a None reached a caller expecting a float."""
    small = [[0, 1], [1, 0]]
    assert dl.bdm_2d(small, below_floor="pathinfo") is None
    with pytest.raises(ValueError, match="floor"):
        dl.bdm_2d(small, below_floor="raise")
    # "none" does NOT mean "always returns a number". pybdm itself refuses a
    # block smaller than its 4x4 partition ("Computed BDM is 0, dataset may
    # have incorrect dimensions"). The docstring claimed otherwise and has been
    # corrected; the behaviour is pinned here so the two cannot drift apart.
    with pytest.raises(ValueError):
        dl.bdm_2d(small, below_floor="none")
    big = [[0, 1, 0, 1], [1, 0, 1, 0], [0, 0, 1, 1], [1, 1, 0, 0]]
    assert isinstance(dl.bdm_2d(big, below_floor="none"), float)


def test_bdm_is_invariant_under_transposition_of_a_symmetric_block():
    import numpy as np
    a = np.array([[0, 1, 1, 0], [1, 0, 0, 1], [1, 0, 0, 1], [0, 1, 1, 0]])
    assert dl.bdm_2d(a) == pytest.approx(dl.bdm_2d(a.T))


def test_variant_c_delegates_to_the_causalnet_measure():
    """Variant C prices a mechanism DNF via imp-causalNet-paper.

    A second declared cross-project exception. Asserted live rather than assumed:
    the module must import, return a real cost, and price a two-input AND at
    strictly fewer bits than a scattered function of the same arity.
    """
    import sys as _s
    _s.path.insert(0, str(ROOT / "imp-causalNet-paper" / "src"))
    and2 = dl.model_dnf_bits([0, 0, 0, 1], 2)
    assert isinstance(and2, float) and and2 > 0
    xor3 = dl.model_dnf_bits([0, 1, 1, 0, 1, 0, 0, 1], 3)
    and3 = dl.model_dnf_bits([0, 0, 0, 0, 0, 0, 0, 1], 3)
    # XOR needs four product terms in DNF; AND needs one.
    assert xor3 > and3
