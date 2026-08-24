"""Phase 1b — the method as it actually is (protocol section 1b).

Phase 1 compared an arbitrary lookup table against a conditional probability
table and called it the index-set method. These tests pin the corrected version:
the real gate family from the validated forward model, a whole network, and BDM
as the model term.
"""

from __future__ import annotations

try:
    import hmmlearn  # noqa: F401
except ImportError:
    import pytest
    pytest.importorskip('hmmlearn', reason='AUDIT01/T2.0: HMM-dependent module; core pivot/clock suite stays runnable')
import numpy as np
import pandas as pd
import pytest

from imp_prices.algorithmic import bdm_bits, resolution_check, structure_axis
from imp_prices.binarise import WIDTH, encode_frame, reachable_codes, round_trip_ok
from imp_prices.gate_network import (connectivity_matrix, dnf_candidate,
                                     fit_network, fit_node_gate, gate_catalogue,
                                     parameter_array, truth_table_array)


# ---------------------------------------------------------------------------
# Binarisation
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["thermometer", "binary", "onehot"])
def test_every_encoding_round_trips(kind):
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.integers(0, 3, size=(200, 7)),
                      columns=[f"s{i}" for i in range(7)])
    assert round_trip_ok(df, kind)
    assert encode_frame(df, kind).shape == (200, 7 * WIDTH[kind])


def test_thermometer_preserves_the_regime_order():
    """The regimes are labelled by mean log return, so their order is a fact."""
    m = reachable_codes("thermometer")["mapping"]
    assert m == {0: "00", 1: "10", 2: "11"}
    # Monotone: each successive regime turns a bit on and never off.
    bits = [tuple(int(c) for c in m[k]) for k in (0, 1, 2)]
    assert all(b <= a for lo, hi in zip(bits, bits[1:]) for a, b in zip(lo, hi)) or \
           all(a <= b for lo, hi in zip(bits, bits[1:]) for a, b in zip(lo, hi))


def test_unreachable_codes_are_declared_not_hidden():
    assert reachable_codes("thermometer")["n_unreachable"] == 1
    assert reachable_codes("binary")["n_unreachable"] == 1
    assert reachable_codes("onehot")["n_unreachable"] == 5


# ---------------------------------------------------------------------------
# The gate family comes from the validated forward model
# ---------------------------------------------------------------------------

def test_catalogue_is_generated_from_the_vendored_forward_model():
    """AND, OR and XOR must have exactly the truth tables the method defines."""
    tables = {(n, t) for n, _, t in gate_catalogue(2)}
    assert ("AND", (0, 0, 0, 1)) in tables
    assert ("OR", (0, 1, 1, 1)) in tables
    assert ("XOR", (0, 1, 1, 0)) in tables
    assert ("NAND", (1, 1, 1, 0)) in tables


def test_the_gate_class_does_not_fit_anything():
    """Rule R4. The family must cover a small fraction of Boolean functions."""
    distinct = {t for _, _, t in gate_catalogue(3)}
    assert len(distinct) < 30, f"{len(distinct)} of 256 is too permissive"
    rng = np.random.default_rng(7)
    draws = [tuple(rng.integers(0, 2, 8)) for _ in range(2000)]
    hit = sum(1 for d in draws if d in distinct)
    # The observed match rate must track the class's coverage, not exceed it.
    assert abs(hit / len(draws) - len(distinct) / 256) < 0.02


def test_regulatory_dnf_is_admitted_only_when_it_compresses():
    assert dnf_candidate([0, 0, 0, 0]) is None            # empty
    assert dnf_candidate([1, 1, 1, 1, 1, 1, 1, 1]) is not None
    rng = np.random.default_rng(1)
    rejected = sum(1 for _ in range(200)
                   if dnf_candidate(list(rng.integers(0, 2, 8))) is None)
    assert rejected > 0, "random functions must sometimes fail to compress"


# ---------------------------------------------------------------------------
# BDM as an instrument
# ---------------------------------------------------------------------------

def test_bdm_resolution_is_checked_not_assumed():
    """imp-pathinfo found BDM can track size; the object must be big enough."""
    assert resolution_check((14, 14))["usable"]
    assert not resolution_check((4, 4))["usable"], (
        "a 4x4 object is below BDM's resolution and must be reported as such")


def test_bdm_rejects_non_binary_input():
    with pytest.raises(ValueError):
        bdm_bits(np.array([[0, 1, 2], [1, 0, 1]]))


def test_bdm_separates_structure_from_noise_at_the_network_shape():
    rng = np.random.default_rng(0)
    structured = np.zeros((14, 14), dtype=int)
    structured[np.arange(14), (np.arange(14) + 1) % 14] = 1
    noisy = rng.integers(0, 2, size=(14, 14))
    assert bdm_bits(structured) < bdm_bits(noisy) / 2


def test_structure_axis_requires_identical_shapes():
    with pytest.raises(ValueError):
        structure_axis(np.zeros((4, 4), int), np.zeros((5, 5), int), "a", "b")


# ---------------------------------------------------------------------------
# Positive and negative controls on the whole pipeline
# ---------------------------------------------------------------------------

def test_a_deterministic_network_is_fitted_exactly_and_wins():
    """Rule 110 as a 14-node network: zero errors, and a decisive win."""
    from imp_prices.controls import rule110_frame
    ca = rule110_frame(width=14, steps=400)
    cols = list(ca.columns)
    gate_fits = fit_network(ca, cols, "gate", 3)
    cpt_fits = fit_network(ca, cols, "cpt", 3)
    assert sum(f.n_errors for f in gate_fits) == 0
    gate_total = (bdm_bits(connectivity_matrix(gate_fits, cols))
                  + bdm_bits(truth_table_array(gate_fits, 3))
                  + sum(f.data_bits for f in gate_fits))
    cpt_total = (bdm_bits(connectivity_matrix(cpt_fits, cols))
                 + bdm_bits(parameter_array(cpt_fits, 3))
                 + sum(f.data_bits for f in cpt_fits))
    assert gate_total < cpt_total / 2, "must win decisively on a deterministic system"


def test_the_gate_network_does_not_compress_noise():
    """Falsifiability of the comparison: on noise the gate side must lose."""
    rng = np.random.default_rng(42)
    rnd = pd.DataFrame(rng.integers(0, 2, size=(400, 14)),
                       columns=[f"c{i}" for i in range(14)])
    cols = list(rnd.columns)
    gate_fits = fit_network(rnd, cols, "gate", 3)
    err = sum(f.n_errors for f in gate_fits) / sum(f.n for f in gate_fits)
    assert 0.40 < err < 0.50, f"error rate {err} should sit near chance"


# ---------------------------------------------------------------------------
# The panel: B4 refuted again, with the method properly applied
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def panel_bits():
    from imp_prices import RegimeDiscretiser, load_and_split
    split = load_and_split()
    fr = RegimeDiscretiser("gaussian").fit(split.train).transform(split.full)
    train = fr.reindex(split.train.index).dropna().astype(int)
    return encode_frame(train, "thermometer")


def test_b4b_the_cpt_still_wins_with_the_real_gate_family(panel_bits):
    """Ledger C19. The correction was made and the verdict did not change."""
    cols = list(panel_bits.columns)
    gate_fits = fit_network(panel_bits, cols, "gate", 3)
    cpt_fits = fit_network(panel_bits, cols, "cpt", 3)
    gate_total = (bdm_bits(connectivity_matrix(gate_fits, cols))
                  + bdm_bits(truth_table_array(gate_fits, 3))
                  + sum(f.data_bits for f in gate_fits))
    cpt_total = (bdm_bits(connectivity_matrix(cpt_fits, cols))
                 + bdm_bits(parameter_array(cpt_fits, 3))
                 + sum(f.data_bits for f in cpt_fits))
    assert cpt_total < gate_total
    # Counting agrees, so the verdict is not an artefact of the instrument.
    assert sum(f.total for f in cpt_fits) < sum(f.total for f in gate_fits)


def test_almost_no_panel_node_is_describable_by_a_named_gate(panel_bits):
    """Ledger C20, and the deepest finding of Phase 1b.

    If the panel's conditionals were gate-like, the family would name them. It
    names essentially none: every node falls back to a general lookup table.
    """
    cols = list(panel_bits.columns)
    fits = fit_network(panel_bits, cols, "gate", 3)
    named = [f for f in fits if f.gate != "LUT"]
    assert len(named) <= 2, f"expected almost none named, got {len(named)}"
