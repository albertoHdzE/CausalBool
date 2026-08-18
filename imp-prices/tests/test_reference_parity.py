"""Reference parity: this package must reproduce GWP3 before it may extend it.

Every comparison this package intends to make is against numbers produced by
``reference/gwp3/gwp3_pipeline.py``. If the ported loader, splitter or
discretiser deviates from that pipeline by so much as a rounding, the comparison
measures the port and not the method. These tests are therefore a gate: they run
first and nothing downstream is believable until they pass.

The parity target is ``reference/gwp3/results.json``, written by the GWP3 run of
2026-08-15 and held read-only.
"""

from __future__ import annotations

import json

import numpy as np
import pytest

from imp_prices import (LABELS, SERIES, TARGET, RegimeDiscretiser,
                        load_and_split, load_panel, regime_economics,
                        split_summary)
from imp_prices.config import GWP3_RESULTS


@pytest.fixture(scope="module")
def reference():
    with open(GWP3_RESULTS) as fh:
        return json.load(fh)


@pytest.fixture(scope="module")
def split():
    return load_and_split()


@pytest.fixture(scope="module")
def discretisers(split):
    """Fit both emission schemes once; each fit is ten Baum-Welch restarts."""
    return {kind: RegimeDiscretiser(kind).fit(split.train)
            for kind in ("parity", "gaussian")}


# ---------------------------------------------------------------------------
# The panel and its allocation (ledger anchors A1, A2)
# ---------------------------------------------------------------------------

def test_panel_shape_and_range():
    df = load_panel()
    assert df.shape == (199, 7)
    assert list(df.columns) == SERIES
    assert str(df.index[0].date()) == "2010-01-31"
    assert str(df.index[-1].date()) == "2026-07-31"
    assert not df.isna().any().any()


def test_split_sizes_and_boundaries(split):
    assert split.sizes == (139, 30, 30)
    assert str(split.train.index[0].date()) == "2010-01-31"
    assert str(split.train.index[-1].date()) == "2021-07-31"
    assert str(split.val.index[0].date()) == "2021-08-31"
    assert str(split.val.index[-1].date()) == "2024-01-31"
    assert str(split.test.index[0].date()) == "2024-02-29"
    assert str(split.test.index[-1].date()) == "2026-07-31"


def test_split_is_chronological_and_exhaustive(split):
    assert split.train.index[-1] < split.val.index[0] < split.val.index[-1] < split.test.index[0]
    assert len(split.train) + len(split.val) + len(split.test) == len(split.full)


def test_split_summary_matches_reference(split, reference):
    ours = split_summary(split).to_dict("records")
    theirs = reference["split"]
    assert len(ours) == len(theirs)
    for a, b in zip(ours, theirs):
        assert a == b, f"split summary row differs for {a['Set']}"


# ---------------------------------------------------------------------------
# Hidden Markov models, both emission schemes (ledger anchors A4, A5)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["parity", "gaussian"])
def test_hmm_parameters_match_reference(kind, discretisers, reference):
    """Every fitted parameter of all seven models, to the recorded precision.

    This is the strongest available statement of port fidelity: it covers the
    restart policy, the sticky prior, the state ordering and the emission
    scheme simultaneously.
    """
    ours = discretisers[kind].params
    theirs = reference[f"hmm_{kind}"]
    assert set(ours) == set(theirs) == set(SERIES)
    for s in SERIES:
        a, b = ours[s], theirs[s]
        assert set(a) == set(b), f"{kind}/{s}: parameter keys differ"
        for key in a:
            if key == "state_means_raw":
                # JSON keys are strings; ours are integers.
                assert {str(k): v for k, v in a[key].items()} == b[key], f"{kind}/{s}/{key}"
            elif isinstance(a[key], float):
                assert a[key] == pytest.approx(b[key], abs=1e-3), f"{kind}/{s}/{key}"
            else:
                np.testing.assert_allclose(
                    np.asarray(a[key], dtype=float), np.asarray(b[key], dtype=float),
                    atol=1e-4, err_msg=f"{kind}/{s}/{key}")


def test_parity_scheme_is_degenerate(discretisers):
    """Anchor A4: the source dissertation's scheme yields no persistence."""
    p = discretisers["parity"].params[TARGET]
    assert p["persistence"] == 0.0
    assert p["log_likelihood"] == pytest.approx(-92.367, abs=1e-3)


def test_gaussian_scheme_is_persistent(discretisers):
    """Anchor A5: the modified scheme yields regimes that last."""
    g = discretisers["gaussian"].params[TARGET]
    assert g["persistence"] == pytest.approx(0.742, abs=5e-3)
    assert g["log_likelihood"] == pytest.approx(138.53, abs=1e-2)
    assert g["persistence"] > 20 * (discretisers["parity"].params[TARGET]["persistence"] + 0.01)


# ---------------------------------------------------------------------------
# Decoded frames (ledger anchors A6, A7)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("kind", ["parity", "gaussian"])
def test_decoded_frame_matches_reference_csv(kind, discretisers, split):
    """The decoded regimes themselves, month by month, for all three windows."""
    import os

    import pandas as pd

    from imp_prices.config import REFERENCE

    frame = discretisers[kind].transform(split.full)
    for window, part in [("train", split.train), ("validation", split.val),
                         ("test", split.test)]:
        path = os.path.join(REFERENCE, "gwp3", f"discrete_{kind}_{window}.csv")
        theirs = pd.read_csv(path, parse_dates=["Date"], index_col="Date")[SERIES]
        ours = frame.reindex(part.index).dropna().astype(int)
        assert list(ours.index) == list(theirs.index), f"{kind}/{window}: index differs"
        pd.testing.assert_frame_equal(ours, theirs.astype(int),
                                      check_dtype=False, obj=f"{kind}/{window}")


def test_switch_counts(discretisers, split):
    """Anchors A4 and A5 read off the decoded target series, not the transition matrix."""
    counts = {}
    for kind in ("parity", "gaussian"):
        col = discretisers[kind].transform(split.full)[TARGET].values
        counts[kind] = int((np.diff(col) != 0).sum())
    assert counts["parity"] == 189
    assert counts["gaussian"] == 52


def test_regime_economics_matches_table_9(discretisers, split):
    """Anchor A6: the economic meaning of the three states on the training window."""
    frame = discretisers["gaussian"].transform(split.full)
    train_regimes = frame.reindex(split.train.index).dropna()[TARGET].astype(int)
    econ = regime_economics(split.full[TARGET], train_regimes).set_index("State")

    expected = {0: (30, -0.1289, 0.1463, 21.7),
                1: (91, +0.0143, 0.0532, 65.9),
                2: (17, +0.1518, 0.1350, 12.3)}
    for state, (months, mean, vol, share) in expected.items():
        row = econ.loc[state]
        assert int(row["Months"]) == months, f"{LABELS[state]}: month count"
        assert row["Mean_log_return"] == pytest.approx(mean, abs=1e-4)
        assert row["Volatility"] == pytest.approx(vol, abs=1e-4)
        assert row["Share"] == pytest.approx(share, abs=0.1)

    # The states are ordered by mean change, so the means must increase.
    assert (econ["Mean_log_return"].diff().dropna() > 0).all()


def test_window_composition_matches_table_5(discretisers, split):
    """Anchor A7: per cent bear / stagnant / bull in each window."""
    frame = discretisers["gaussian"].transform(split.full)
    expected = {"train": (21.7, 65.9, 12.3),
                "val": (23.3, 63.3, 13.3),
                "test": (13.3, 73.3, 13.3)}
    for name, part in [("train", split.train), ("val", split.val), ("test", split.test)]:
        col = frame.reindex(part.index).dropna()[TARGET].astype(int)
        share = tuple(round(100 * float((col == k).mean()), 1) for k in range(3))
        assert share == pytest.approx(expected[name], abs=0.1), name


# ---------------------------------------------------------------------------
# Strict causality (protocol rule R1)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("cut", [60, 90, 120, 150, 180])
def test_decoding_is_filtered_not_smoothed(cut, discretisers, split):
    """No decoded label may depend on an observation that postdates it.

    Truncating the sample must leave every earlier label untouched. This is
    swept over several truncation points rather than tested at one, because a
    single cut can land where a smoothed decoder happens to agree: at cut = 120
    a whole-window Viterbi changes only 1 of 833 labels, which one test would
    catch and another would not.

    The leakage this guards against is what gave the source protocol a nominal
    one-month-ahead accuracy of 100 per cent (GWP3 section 4).
    """
    d = discretisers["gaussian"]
    full = d.transform(split.full)
    truncated = d.transform(split.full.iloc[:cut])
    assert len(truncated) == cut - 1
    np.testing.assert_array_equal(full.loc[truncated.index].values, truncated.values)


def test_the_causality_test_has_teeth(discretisers, split):
    """A smoothed decoder must fail the test above. A control on the control.

    Protocol rule R3 requires that any analyser be shown to detect the thing it
    is meant to detect. Here the analyser is the truncation invariance check and
    the positive control is a deliberately leaky decoder.
    """
    d = discretisers["gaussian"]

    def smoothed(df):
        out = {}
        for s in SERIES:
            x, _ = d._emit(df[s], d.clip[s])
            _, seq = d.models[s].decode(x, algorithm="viterbi")
            out[s] = [d.relabel[s][int(k)] for k in seq]
        return np.asarray([out[s] for s in SERIES]).T

    full = smoothed(split.full)
    changed = 0
    for cut in (60, 90, 120, 150, 180):
        trunc = smoothed(split.full.iloc[:cut])
        changed += int((full[:len(trunc)] != trunc).sum())
    assert changed > 0, "smoothed decoding must violate truncation invariance"
