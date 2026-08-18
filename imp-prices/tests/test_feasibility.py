"""The feasibility analyser must be shown to work before its verdict counts.

Protocol rules R3 and R4. Every test here is a control on the instrument, not a
measurement of the market. The market measurement is in
``scripts/gate10_feasibility.py`` and its verdict is void if any of these fail.
"""

from __future__ import annotations

import numpy as np
import pytest

from imp_prices.controls import (persistent_random_frame, random_frame,
                                 rule110_frame)
from imp_prices.feasibility import (circular_shift_null, covariate_shift_null,
                                    coverage, pattern_stats, scan, shuffle_null)


# ---------------------------------------------------------------------------
# Positive control: a deterministic system must be recovered exactly
# ---------------------------------------------------------------------------

def test_rule110_is_recovered_exactly():
    """A cellular automaton is a Boolean network; the analyser must find it.

    The successor of cell 0 on a periodic lattice depends on cells 6, 0 and 1,
    so the true parent set is recoverable at in-degree three, with contradiction
    zero and a lookup table that reproduces the rule.
    """
    ca = rule110_frame(width=7, steps=200)
    tab = scan(ca, "c0", list(ca.columns), max_indegree=3, n_values=2)
    best = tab.loc[tab["contradiction"].idxmin()]
    assert best["contradiction"] == 0.0
    assert best["lookup_accuracy"] == 1.0
    assert set(best["parents"].split("+")) == {"c6", "c0", "c1"}
    # The true parent set is the only exact one at this in-degree.
    assert int((tab["contradiction"] == 0).sum()) == 1


def test_deterministic_recovery_is_not_an_artefact_of_binary_alphabet():
    """The same must hold for a three-symbol deterministic map."""
    rng = np.random.default_rng(0)
    import pandas as pd
    a = rng.integers(0, 3, 300)
    b = rng.integers(0, 3, 300)
    df = pd.DataFrame({"c0": a, "c1": b, "c2": rng.integers(0, 3, 300)})
    # y[t] = f(x[t-1]), so that the successor y[t+1] is a function of the
    # evidence row x[t] that build_design pairs it with.
    df["y"] = np.roll((df["c0"] + 2 * df["c1"]) % 3, 1)
    from imp_prices.feasibility import build_design
    X, y = build_design(df, "y", ["c0", "c1"])
    st = pattern_stats(X, y, ("c0", "c1"))
    assert st.contradiction == 0.0
    assert st.lookup_accuracy == 1.0


# ---------------------------------------------------------------------------
# Negative controls: the analyser must not fit what is not there
# ---------------------------------------------------------------------------

def test_random_data_shows_no_structure():
    """Falsifiability (rule R4): independent symbols must not pass."""
    rnd = random_frame(width=7, steps=200, n_values=3)
    res = circular_shift_null(rnd, "c0", list(rnd.columns), max_indegree=3)
    assert res["p_lookup_accuracy"] > 0.05
    assert res["excess_lookup_accuracy"] < 0.05


def test_persistent_but_causally_empty_data_shows_no_cross_structure():
    """The control that condemned the permutation null.

    Independent Markov chains contain persistence and nothing else. A test for
    *cross-variable* structure must return null on them. The circular-shift null
    does; the permutation null does not, and its failure here is the reason the
    primary null was changed. Both behaviours are asserted so that a regression
    to the weaker null cannot pass silently.
    """
    per = persistent_random_frame(width=7, steps=200, n_values=3, stay=0.75)
    others = [c for c in per.columns if c != "c0"]

    good = circular_shift_null(per, "c0", others, max_indegree=3)
    assert good["p_lookup_accuracy"] > 0.05, "circular-shift null must reject"
    assert abs(good["excess_lookup_accuracy"]) < 0.05

    bad = shuffle_null(per, "c0", others, max_indegree=3, n_shuffles=200, seed=42)
    assert bad["p_lookup_accuracy"] < 0.05, (
        "the permutation null is retained precisely because it fails here; "
        "if it has stopped failing, this documentation is now wrong")


def test_persistence_itself_is_detected():
    """The same control, with the self-parent allowed, must be positive.

    Persistence is real structure. A null that rejected it would be too strong,
    and the pair of assertions pins the discrimination the analyser must make:
    persistence yes, cross-variable no, on the same data.
    """
    per = persistent_random_frame(width=7, steps=200, n_values=3, stay=0.75)
    res = circular_shift_null(per, "c0", list(per.columns), max_indegree=3)
    assert res["p_lookup_accuracy"] < 0.05
    assert res["excess_lookup_accuracy"] > 0.05


# ---------------------------------------------------------------------------
# The increment statistic
# ---------------------------------------------------------------------------

def test_increment_test_detects_a_true_leading_indicator():
    """Power check: the covariate-shift null must find a real covariate."""
    per = persistent_random_frame(width=7, steps=200, n_values=3, stay=0.75)
    per = per.copy()
    per["lead"] = per["c0"].shift(-1).ffill().bfill().astype(int)
    res = covariate_shift_null(per, "c0", ["c0"], ["lead"], max_indegree=2)
    assert res["p_increment"] < 0.05
    assert res["excess_increment"] > 0.10


def test_increment_test_rejects_a_useless_covariate():
    """Size check: an unrelated covariate must not register.

    Adding any parent raises the in-sample accuracy of a lookup table, so the
    raw increment is positive here by construction. The test must nevertheless
    return null, which is the whole purpose of comparing against a surrogate
    increment rather than against zero.
    """
    per = persistent_random_frame(width=7, steps=200, n_values=3, stay=0.75)
    res = covariate_shift_null(per, "c0", ["c0"], ["c1", "c2", "c3"],
                               max_indegree=3)
    assert res["observed_increment"] > 0, "raw increment is positive by construction"
    assert res["p_increment"] > 0.05, "yet it must not be significant"


# ---------------------------------------------------------------------------
# Guards against vacuous determinism
# ---------------------------------------------------------------------------

def test_contradiction_is_undefined_without_recurrence():
    """No recurring pattern means no evidence, not perfect determinism."""
    import pandas as pd
    rng = np.random.default_rng(1)
    df = pd.DataFrame(rng.integers(0, 3, size=(20, 7)),
                      columns=[f"c{i}" for i in range(7)])
    st = pattern_stats(df.to_numpy()[:-1], df["c0"].to_numpy()[1:],
                       tuple(df.columns))
    assert st.n_recurring == 0
    assert np.isnan(st.contradiction), "must be undefined, never zero"


def test_coverage_reports_the_sparsity_honestly():
    rnd = random_frame(width=7, steps=138, n_values=3)
    cov = coverage(rnd, list(rnd.columns))
    assert cov["state_space"] == 3 ** 7 == 2187
    assert cov["distinct_states"] <= cov["n_observations"]
    assert 0 < cov["coverage"] < 0.1


def test_nulls_are_deterministic():
    """Rule R6. The circular-shift null enumerates surrogates and carries no seed."""
    rnd = random_frame(width=7, steps=150, n_values=3)
    a = circular_shift_null(rnd, "c0", list(rnd.columns), max_indegree=2)
    b = circular_shift_null(rnd, "c0", list(rnd.columns), max_indegree=2)
    assert a == b


def test_p_value_floor_is_reported():
    """A p-value can never be zero; the floor must be visible in the output."""
    ca = rule110_frame(width=7, steps=200)
    res = circular_shift_null(ca, "c0", list(ca.columns), max_indegree=3,
                              n_values=2)
    assert res["p_lookup_accuracy"] >= 1 / (res["n_surrogates"] + 1)
    assert res["n_surrogates"] > 100
