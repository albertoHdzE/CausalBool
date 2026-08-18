"""The index-set encoding and its description length (ledger B4).

A description-length comparison is trivially riggable by choice of encoding, so
the tests here are mostly about the *code* rather than about the data: that each
term is a valid self-delimiting code length, that the encoding recovers a
deterministic system, and that it does not manufacture structure in noise.

The panel result itself is a negative, and it is asserted too — a negative that
is not pinned by a test can quietly become a positive after a refactor.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
import pytest

from imp_prices.controls import random_frame, rule110_frame
from imp_prices.index_set import (best_by_total, bootstrap_parent_sets, cpt_code,
                                  elias_gamma_bits, index_set_code, log2_binom,
                                  marginal_code, prequential_bits, residual_bits,
                                  scan_codes, structure_bits)
from imp_prices.feasibility import build_design


# ---------------------------------------------------------------------------
# The codes themselves
# ---------------------------------------------------------------------------

def test_elias_gamma_is_a_valid_prefix_code():
    """Kraft's inequality: a prefix code's lengths must satisfy sum 2^-L <= 1."""
    total = sum(2.0 ** -elias_gamma_bits(n) for n in range(0, 4096))
    assert total <= 1.0 + 1e-9, f"Kraft sum {total} exceeds 1"
    assert elias_gamma_bits(0) == 1
    assert all(elias_gamma_bits(n + 1) >= elias_gamma_bits(n) for n in range(500))


def test_structure_code_is_a_valid_prefix_code():
    """Over all parent sets up to the in-degree limit, Kraft must hold."""
    n, kmax = 7, 3
    total = sum(math.comb(n, k) * 2.0 ** -structure_bits(n, k, kmax)
                for k in range(kmax + 1))
    assert total <= 1.0 + 1e-9, f"Kraft sum {total} exceeds 1"


def test_residual_code_is_monotone_and_cheapest_when_exact():
    """More errors must never cost fewer bits, and zero errors must be cheapest."""
    n, a = 137, 3
    costs = [residual_bits(n, e, a) for e in range(0, n // 2)]
    assert costs[0] == min(costs)
    assert costs[0] < 3, "an exact map should pay almost nothing"
    assert all(b >= a_ for a_, b in zip(costs, costs[1:]))


def test_code_lengths_are_positive_and_decompose():
    rng = np.random.default_rng(0)
    df = pd.DataFrame(rng.integers(0, 3, size=(150, 4)),
                      columns=[f"c{i}" for i in range(4)])
    X, y = build_design(df, "c0", ["c1", "c2"])
    for fn in (index_set_code, cpt_code):
        c = fn(X, y, ("c1", "c2"), 4, 3)
        assert c.structure > 0 and c.parameters > 0 and c.data > 0
        assert c.total == pytest.approx(c.structure + c.parameters + c.data)
        assert c.model_bits == pytest.approx(c.structure + c.parameters)


# ---------------------------------------------------------------------------
# Positive control: the encoding must express what it was designed for
# ---------------------------------------------------------------------------

def test_rule110_is_compressed_by_the_index_set_encoding():
    """A deterministic system: an exact map, and a decisive win over the CPT."""
    ca = rule110_frame(width=7, steps=200)
    tab = scan_codes(ca, "c0", list(ca.columns), 3, alphabet=2)
    marg = tab[tab["k"] == 0].iloc[0]["total_bits"]
    isb = best_by_total(tab[tab["k"] > 0], "index-set")
    cpt = best_by_total(tab[tab["k"] > 0], "cpt")

    assert set(isb["parents"].split("+")) == {"c6", "c0", "c1"}
    assert isb["n_errors"] == 0
    assert isb["data_bits"] < 2, "an exact map pays essentially nothing for data"
    assert isb["total_bits"] < 0.15 * marg, "must compress the deterministic system"
    assert isb["total_bits"] < cpt["total_bits"] / 2, "must beat the CPT decisively"


def test_a_planted_ternary_map_is_recovered_and_compressed():
    """The same, on three symbols, so the win is not an artefact of binary data."""
    rng = np.random.default_rng(3)
    df = pd.DataFrame(rng.integers(0, 3, size=(300, 5)),
                      columns=[f"c{i}" for i in range(5)])
    df["y"] = np.roll((df["c1"] + 2 * df["c2"]) % 3, 1)
    tab = scan_codes(df, "y", [f"c{i}" for i in range(5)], 3)
    isb = best_by_total(tab[tab["k"] > 0], "index-set")
    assert set(isb["parents"].split("+")) == {"c1", "c2"}
    assert isb["n_errors"] == 0
    assert isb["total_bits"] < tab[tab["k"] == 0].iloc[0]["total_bits"] / 5


# ---------------------------------------------------------------------------
# Negative control: the accounting must not be biased
# ---------------------------------------------------------------------------

def test_neither_encoding_beats_the_marginal_on_noise():
    """Falsifiability of the *comparison*, not of the model.

    If the index-set encoding beat the marginal baseline on independent uniform
    symbols, the bit accounting would be biased in its favour and every panel
    result would be void.
    """
    rnd = random_frame(width=7, steps=200, n_values=3)
    tab = scan_codes(rnd, "c0", list(rnd.columns), 3)
    marg = tab[tab["k"] == 0].iloc[0]["total_bits"]
    for model in ("index-set", "cpt"):
        best = best_by_total(tab[tab["k"] > 0], model)
        assert best["total_bits"] > marg, f"{model} manufactured structure in noise"


def test_marginal_code_is_near_the_entropy_bound_on_uniform_noise():
    rnd = random_frame(width=7, steps=400, n_values=3)
    c = marginal_code(rnd["c0"].to_numpy()[1:], 7, 3)
    per_obs = c.data / c.n
    assert per_obs == pytest.approx(math.log2(3), abs=0.05)


# ---------------------------------------------------------------------------
# The panel: a negative, pinned so that it cannot drift into a positive
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def panel_train():
    from imp_prices import RegimeDiscretiser, load_and_split
    split = load_and_split()
    fr = RegimeDiscretiser("gaussian").fit(split.train).transform(split.full)
    return fr.reindex(split.train.index).dropna().astype(int)


def test_b4_fails_the_cpt_describes_the_panel_in_fewer_bits(panel_train):
    """Ledger C15. The pre-registered expectation was the opposite."""
    from imp_prices import SERIES, TARGET
    tab = scan_codes(panel_train, TARGET, SERIES, 3)
    marg = tab[tab["k"] == 0].iloc[0]["total_bits"]
    isb = best_by_total(tab[tab["k"] > 0], "index-set")
    cpt = best_by_total(tab[tab["k"] > 0], "cpt")

    # Both find signal: the panel is not noise, and persistence is compressible.
    assert isb["total_bits"] < marg and cpt["total_bits"] < marg
    # But the probabilistic encoding wins, by a clear margin.
    assert cpt["total_bits"] < isb["total_bits"]
    assert isb["total_bits"] - cpt["total_bits"] > 10, "margin should be substantial"
    # And both select the target's proxy, exactly as Gate 1.0 predicted.
    assert isb["parents"] == cpt["parents"] == "WTI_CL"


def test_prequential_agrees_so_the_verdict_is_not_a_precision_convention(panel_train):
    """The two-part codes need a parameter-precision convention; this does not."""
    from imp_prices import TARGET
    a = prequential_bits(panel_train, TARGET, ["WTI_CL"], "index-set")
    b = prequential_bits(panel_train, TARGET, ["WTI_CL"], "cpt")
    assert b["prequential_bits"] < a["prequential_bits"]
    assert a["n_scored"] == b["n_scored"]


def test_index_set_selection_is_less_stable_than_the_cpt_selection(panel_train):
    """Ledger C16, and a correction to an argument made in bitacora 03.

    Identical moving-block resamples, identical candidate space; only the
    encoding differs. The index-set code length selects a far less stable parent
    set than the conditional probability table does. The reason is visible in the
    accounting: a lookup table costs log2(3) bits per pattern against the table's
    (a-1)/2 * log2(N), so the index-set code under-penalises in-degree and
    over-selects.
    """
    from imp_prices import SERIES, TARGET
    kw = dict(max_indegree=3, alphabet=3, n_boot=120, seed=42, block=12)
    a = bootstrap_parent_sets(panel_train, TARGET, SERIES, scorer="index-set", **kw)
    b = bootstrap_parent_sets(panel_train, TARGET, SERIES, scorer="cpt", **kw)
    assert a["n_distinct_winners"] > 3 * b["n_distinct_winners"]
    assert a["modal_frequency"] < b["modal_frequency"]


def test_bootstrap_is_deterministic(panel_train):
    from imp_prices import SERIES, TARGET
    kw = dict(max_indegree=3, alphabet=3, n_boot=40, seed=7, block=12)
    a = bootstrap_parent_sets(panel_train, TARGET, SERIES, **kw)
    b = bootstrap_parent_sets(panel_train, TARGET, SERIES, **kw)
    assert a == b
