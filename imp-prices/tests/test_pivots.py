"""The confirmed-only pivot rule (protocol R1), and proof that it bites.

This is the principal false-positive risk of Phase 2. A directional-change pivot
occurs at one time and becomes knowable at a later one; using the earlier
timestamp in a forecasting feature is look-ahead. It is the same error class GWP3
caught in the source dissertation, and here it is subtler, because the turning
point genuinely is in the past — only the knowledge of it is not.

Two things must therefore be established, and the second matters as much as the
first: that the rule is correct, and that it is **not vacuous**.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from imp_prices.pivots import (Pivot, directional_change, known_pivots,
                               leak_opportunities, leaked_pivots, legs,
                               short_wait_target)


# ---------------------------------------------------------------------------
# The detector itself
# ---------------------------------------------------------------------------

def test_a_clean_zigzag_is_detected_exactly():
    """A triangular wave of known amplitude must give the known turning points."""
    up = np.linspace(100, 130, 31)
    down = np.linspace(130, 100, 31)[1:]
    prices = np.concatenate([up, down, up[1:], down])
    pv = directional_change(prices, theta=0.10)
    assert len(pv) >= 2
    assert pv[0].kind == "peak"
    assert prices[pv[0].extreme_index] == pytest.approx(130.0)
    assert all(q.extreme_price == pytest.approx(prices[q.extreme_index]) for q in pv)


def test_pivots_alternate_between_peaks_and_troughs():
    rng = np.random.default_rng(0)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 2000)))
    pv = directional_change(prices, theta=0.05)
    kinds = [q.kind for q in pv]
    assert len(pv) > 10
    assert all(a != b for a, b in zip(kinds, kinds[1:])), "peaks and troughs must alternate"


def test_threshold_is_relative_so_the_encoding_is_scale_invariant():
    """The same reversal must be the same event at any price level.

    This is what makes the encoding free of the number's magnitude — the property
    Level 5 reached from Benford-like scale invariance — and it is why a
    percentage threshold is used rather than an absolute one.
    """
    rng = np.random.default_rng(1)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 1500)))
    a = directional_change(prices, 0.05)
    b = directional_change(prices * 37.5, 0.05)
    assert [(q.extreme_index, q.confirm_index, q.kind) for q in a] == \
           [(q.extreme_index, q.confirm_index, q.kind) for q in b]


def test_initial_direction_is_not_assumed():
    """A monotone rise must not produce a spurious pivot at the left edge."""
    assert directional_change(np.linspace(100, 200, 100), 0.05) == []
    assert directional_change(np.linspace(200, 100, 100), 0.05) == []


def test_higher_threshold_gives_fewer_pivots():
    rng = np.random.default_rng(2)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 3000)))
    counts = [len(directional_change(prices, t)) for t in (0.02, 0.05, 0.10, 0.20)]
    assert counts == sorted(counts, reverse=True), counts


# ---------------------------------------------------------------------------
# The confirmation lag: correctness
# ---------------------------------------------------------------------------

def test_confirmation_is_always_strictly_after_the_extreme():
    """The defining property. A lag of zero would mean clairvoyance."""
    rng = np.random.default_rng(3)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 3000)))
    pv = directional_change(prices, 0.05)
    assert pv
    assert all(q.confirm_index > q.extreme_index for q in pv)
    assert all(q.lag >= 1 for q in pv)


def test_known_pivots_never_include_the_future():
    rng = np.random.default_rng(4)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 1500)))
    pv = directional_change(prices, 0.05)
    for t in range(0, len(prices), 37):
        assert all(q.confirm_index <= t for q in known_pivots(pv, t))


def test_known_pivots_are_a_strict_subset_of_occurred_pivots():
    """The distinction is real: at some times a pivot has happened unknowably."""
    rng = np.random.default_rng(5)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 1500)))
    pv = directional_change(prices, 0.05)
    strictly_smaller = 0
    for t in range(len(prices)):
        occurred = [q for q in pv if q.extreme_index <= t]
        known = known_pivots(pv, t)
        assert len(known) <= len(occurred)
        strictly_smaller += len(known) < len(occurred)
    assert strictly_smaller > 0, "if this never happens the guard is vacuous"


# ---------------------------------------------------------------------------
# The confirmation lag: the guard is not vacuous
# ---------------------------------------------------------------------------

def test_the_leak_window_is_large_enough_to_matter():
    """Measure the temptation rather than assuming it is small.

    If the naive and correct accessors agreed almost always, the guard would be
    a formality. They do not: the leak window covers a substantial fraction of
    the series.
    """
    rng = np.random.default_rng(6)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 3000)))
    pv = directional_change(prices, 0.05)
    rep = leak_opportunities(pv, len(prices))
    assert rep["n_pivots"] > 20
    assert rep["min_lag"] >= 1
    assert rep["fraction_of_time"] > 0.10, (
        f"only {rep['fraction_of_time']:.3f} of the series is in a leak window; "
        "the guard would barely bite")


def test_the_leak_is_exploitable_which_is_why_it_must_be_guarded():
    """A positive control on the guard: show the bias is real and large.

    A rule that peeks at unconfirmed pivots can 'predict' the sign of the move
    from the current extreme, because knowing an unconfirmed peak exists means
    knowing the price has already turned down from it. The confirmed-only rule
    cannot do this. The gap between the two is the bias the guard removes.
    """
    rng = np.random.default_rng(7)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 4000)))
    pv = directional_change(prices, 0.05)

    leaky_hits = leaky_n = 0
    for t in range(10, len(prices) - 1):
        pending = leaked_pivots(pv, t)
        if not pending:
            continue
        # A pending peak means the price has already turned down from it.
        pred_down = pending[-1].kind == "peak"
        actual_down = prices[t + 1] < prices[t]
        leaky_hits += int(pred_down == actual_down)
        leaky_n += 1

    assert leaky_n > 100
    leaky_acc = leaky_hits / leaky_n
    assert leaky_acc > 0.55, (
        f"peeking gives {leaky_acc:.3f} accuracy on next-step direction, against "
        "0.5 for anything causal; the leak is exploitable and must be guarded")


# ---------------------------------------------------------------------------
# Legs and the target
# ---------------------------------------------------------------------------

def test_legs_are_only_usable_after_their_closing_pivot_is_confirmed():
    rng = np.random.default_rng(8)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 2000)))
    tab = legs(directional_change(prices, 0.05))
    assert len(tab) > 10
    assert (tab["known_at"] > tab["end_index"]).all()
    assert (tab["dt"] > 0).all()


def test_short_wait_target_is_near_balanced_by_construction():
    """The point of the re-target: a median split cannot be defeated by a base rate.

    The monthly regime target is 66 to 73 per cent stagnant (A7, A11), so raw
    accuracy is uninformative there. A running-median split of the waiting times
    sits close to a half.
    """
    rng = np.random.default_rng(9)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 6000)))
    tgt = short_wait_target(legs(directional_change(prices, 0.04)))
    assert len(tgt) > 40
    rate = tgt["short"].mean()
    assert 0.35 < rate < 0.65, f"base rate {rate:.3f} is not near-balanced"


def test_the_running_median_is_causal():
    """The threshold itself must not look ahead — a quieter form of leakage."""
    rng = np.random.default_rng(10)
    prices = 100 * np.exp(np.cumsum(rng.normal(0, 0.02, 4000)))
    tab = legs(directional_change(prices, 0.04))
    tgt = short_wait_target(tab)
    for _, r in tgt.iterrows():
        past = tab["dt"].to_numpy()[:int(r["leg"]) + 1]
        assert r["running_median"] == pytest.approx(float(np.median(past)))
