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


# ── bdm_1d / ctm_1d: the 1-D partition is chosen explicitly ─────────────────

def test_ctm_is_invariant_under_reversal_and_complement():
    # The D(5) machine space is closed under both symmetries, so the table is.
    s = "10111111"
    comp = "".join("1" if c == "0" else "0" for c in s)
    assert dl.ctm_1d(s) == pytest.approx(dl.ctm_1d(s[::-1]))
    assert dl.ctm_1d(s) == pytest.approx(dl.ctm_1d(comp))


def test_aligned_bdm_is_the_sum_of_ctm_plus_log2_multiplicity():
    # Derived from the BDM definition, not copied from pybdm's output.
    blocks = ["01111111", "10111111", "01111111"]
    expected = dl.ctm_1d(blocks[0]) + 1.0 + dl.ctm_1d(blocks[1])
    assert dl.bdm_1d("".join(blocks), block=8) == pytest.approx(expected)


def test_bdm_1d_refuses_a_remainder_unless_asked():
    with pytest.raises(ValueError, match="tiled"):
        dl.bdm_1d("1" * 20, block=12)
    assert dl.bdm_1d("1" * 20, block=12, remainder="drop") == pytest.approx(
        dl.ctm_1d("1" * 12))


def test_ctm_1d_refuses_beyond_the_table():
    with pytest.raises(ValueError, match="1..12"):
        dl.ctm_1d("1" * 13)


# ── HID-v1 / H0: the 1-D interface validates before converting ──────────────

import numpy as _np


@pytest.mark.parametrize("bad", [
    [0.0, 1.0, 1.0], _np.array([0.0, 1.0]), [0, 0.5, 1], _np.array([0.5, 1.0]),
    [0, 2, 1], "01a1", "0 1", [[0, 1], [1, 0]], _np.zeros((2, 2), dtype=int),
    [[0, 1], [1]], [], "", _np.array([], dtype=int), 1, 0, True, _np.int64(1),
    b"0101", [None, 1],
])
def test_bits_refuses_float_nonbinary_ragged_empty_and_scalar(bad):
    with pytest.raises(ValueError):
        dl.ctm_1d(bad)


def test_float_one_half_is_never_cast_to_zero():
    # The historical dtype=int cast scored [0, 0.5, 1] as "001"; it must now refuse.
    with pytest.raises(ValueError, match="int or bool"):
        dl.bdm_1d([0, 0.5, 1, 1], block=4)


def test_int_bool_and_string_inputs_agree():
    s = "0110100110010110"
    as_int = [int(c) for c in s]
    as_bool = [c == "1" for c in s]
    want = dl.bdm_1d(s, block=8)
    assert dl.bdm_1d(as_int, block=8) == want
    assert dl.bdm_1d(as_bool, block=8) == want
    assert dl.bdm_1d(_np.array(as_int, dtype=_np.int8), block=8) == want
    assert dl.bdm_1d(_np.array(as_bool), block=8) == want


@pytest.mark.parametrize("kw", [
    {"block": 0}, {"block": 13}, {"block": True}, {"block": 8.0},
    {"block": 8, "shift": 0}, {"block": 8, "shift": 9}, {"block": 8, "shift": True},
    {"block": 8, "shift": 2.0}, {"block": 8, "remainder": "pad"},
    {"block": 8, "remainder": None},
])
def test_bdm_1d_parameter_validation(kw):
    with pytest.raises(ValueError):
        dl.bdm_1d("01" * 12, **kw)


def test_short_input_is_refused_for_raise_and_drop_not_scored_as_zero():
    for policy in ("raise", "drop"):
        with pytest.raises(ValueError, match="shorter than block"):
            dl.bdm_1d("0101", block=8, remainder=policy)


def test_recursive_short_input_scores_the_shorter_block():
    assert dl.bdm_1d("01101", block=8, remainder="recursive") == pytest.approx(
        dl.ctm_1d("01101"))


def test_recursive_covers_every_bit_and_equals_the_parts_by_definition():
    s = "1011" * 6 + "110"          # 27 bits: 12 + 12 + 3
    d = dl.bdm_1d_partition(s, block=12, remainder="recursive")
    assert d["covered_bits"] == 27 and d["dropped_bits"] == 0
    assert d["parts"] == [(0, 12), (12, 12), (24, 3)]
    # Two identical 12-blocks: CTM once + log2(2); the 3-bit remainder separately.
    expected = dl.ctm_1d(s[:12]) + 1.0 + dl.ctm_1d("110")
    assert d["score"] == pytest.approx(expected)


def test_recursive_is_refused_with_a_sliding_shift():
    with pytest.raises(ValueError, match="shift=None"):
        dl.bdm_1d("01" * 12, block=8, shift=1, remainder="recursive")


def test_sliding_raise_requires_exact_tiling_and_drop_reports_coverage():
    s = "011010011001"                       # 12 bits
    with pytest.raises(ValueError, match="tiled"):
        dl.bdm_1d(s, block=4, shift=3)       # starts 0,3,6 cover 10 bits
    d = dl.bdm_1d_partition(s, block=4, shift=3, remainder="drop")
    assert d["covered_bits"] == 10 and d["dropped_bits"] == 2
    assert [p[0] for p in d["parts"]] == [0, 3, 6]
    full = dl.bdm_1d_partition(s, block=4, shift=1)
    assert full["covered_bits"] == 12 and len(full["parts"]) == 9


def test_historical_scores_from_bitacoras_32_and_33_are_unchanged():
    shifted = ["1" * i + "0" + "1" * (7 - i) for i in range(8)]
    a64 = "".join(shifted)
    a72 = "1" * 8 + a64
    # Recorded before H0 by the unhardened owner (bitacora 32 Finding 3, bitacora 33 3.2).
    assert dl.bdm_1d(a64, block=8) == pytest.approx(159.785, abs=5e-4)
    assert dl.bdm_1d(a72, block=3) == pytest.approx(17.842, abs=5e-4)
    assert dl.bdm_1d(a72, block=9) == pytest.approx(24.615, abs=5e-4)
    assert dl.bdm_1d(a72, block=8) == pytest.approx(178.31, abs=5e-3)


def test_encoded_bit_length_is_eight_times_the_byte_count():
    assert dl.encoded_bit_length(b"") == 0
    assert dl.encoded_bit_length(b"ISD1\x00\x00\x00") == 56
    for bad in ("ISD1", bytearray(b"ab"), memoryview(b"ab"), [1, 2], None):
        with pytest.raises(TypeError):
            dl.encoded_bit_length(bad)
