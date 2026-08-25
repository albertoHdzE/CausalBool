"""test_level4.py

Deterministic tests for the Level 4 multi-bit behaviour-table discovery.  They pin
the controls (a random unit must not survive or compress; a clustered synthetic
unit must), the algebra of the process columns, and the calibration of the
structure statistics, so the pipeline cannot silently start manufacturing order.
"""

from __future__ import annotations

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from binarise import (binarisations, sign_bit, top_magnitude_bit,
                      relative_difference, trend_contamination)
from unit_survival import survival_report, lag1_autocorr, longest_run_of_ones
from occurrence_arithmetic import (behaviour_table, transition_probs, gaps,
                                   description_length_gain, hurst_aggregated_variance,
                                   run_length_encoding)


def _clustered_bits(n, seed=0):
    """A two-state (persistent) synthetic: p11 and p00 both high -> clustering."""
    rng = random.Random(seed)
    bits = [0]
    for _ in range(n - 1):
        stay = 0.85
        bits.append(bits[-1] if rng.random() < stay else 1 - bits[-1])
    return bits


# --- binarisation ----------------------------------------------------------

def test_binarisation_shapes():
    vals = [float(x) for x in [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5]]
    bn = binarisations(vals, nbits=3)
    assert len(bn["raw"]) == 3 and len(bn["raw"][0]) == len(vals)
    assert len(bn["diff_sign"]) == 1 and len(bn["diff_sign"][0]) == len(vals) - 1
    assert len(bn["diff_mag"]) == 3
    # every bit is 0/1
    for cols in bn.values():
        for col in cols:
            assert set(col) <= {0, 1}


def test_rank_bits_are_scale_free():
    vals = [1.0, 2.0, 3.0, 4.0]
    a = binarisations(vals, 2)["raw"]
    b = binarisations([10 * v + 7 for v in vals], 2)["raw"]  # monotone rescaling
    assert a == b


def test_top_magnitude_and_sign_lengths():
    vals = [float(x) for x in range(20)]
    assert len(top_magnitude_bit(vals)) == 19
    assert len(sign_bit(vals)) == 19


def test_relative_difference_is_scale_free():
    vals = [1.0, 2.0, 4.0, 8.0]        # multiplicative
    r = relative_difference(vals)
    assert all(abs(x - 1.0) < 1e-9 for x in r)  # each step doubles: +100%
    # invariant to multiplicative rescaling of the whole sequence
    r2 = relative_difference([100 * v for v in vals])
    assert all(abs(a - b) < 1e-12 for a, b in zip(r, r2))


def test_trend_contamination_flags_exponential_growth():
    # an exponential ramp: additive |diff| grows with level, so the additive
    # magnitude unit is a step function -> large contamination.  A stationary
    # multiplicative series -> near zero.
    ramp = [1.02 ** t for t in range(400)]
    assert trend_contamination(ramp) > 0.3
    import random as _r
    rng = _r.Random(0)
    stat = [1.0]
    for _ in range(400):
        stat.append(stat[-1] * (1 + 0.02 * (rng.random() - 0.5)))
    assert abs(trend_contamination(stat)) < 0.2
    # the scale-free unit removes the ramp contamination
    a = top_magnitude_bit(ramp)                 # additive: almost all late ones
    b = top_magnitude_bit(ramp, scale_free=True)  # relative: balanced
    h = len(a) // 2
    assert sum(a[h:]) / h > 0.9
    assert 0.3 < sum(b[h:]) / h < 0.7


# --- process-column algebra ------------------------------------------------

def test_transition_probs_known():
    bits = [1, 1, 0, 0, 1, 1, 0, 0]  # deterministic period-4
    p, p11, p00 = transition_probs(bits)
    assert abs(p - 0.5) < 1e-9
    # after a 1: sequence of nexts is 1,0,-,0,1,0,- -> among positions with a 1 at t
    assert 0.0 <= p11 <= 1.0 and 0.0 <= p00 <= 1.0


def test_gaps_and_runs():
    bits = [1, 0, 0, 1, 0, 1]
    assert gaps(bits) == [3, 2]              # occurrences at 0,3,5
    assert run_length_encoding(bits) == [(1, 1), (0, 2), (1, 1), (0, 1), (1, 1)]


def test_geometric_run_length_law_matches_observed_on_markov():
    # For a two-state chain the mean run of ones is exactly 1/(1-p11); the closed
    # form must track the observed mean on a long clustered sample.
    bits = _clustered_bits(20000, seed=1)
    bt = behaviour_table(bits)
    obs = bt["run_length"]["mean_run_of_ones"]
    pred = bt["run_length"]["geometric_mean_run_pred"]
    assert abs(obs - pred) / obs < 0.05


# --- calibration: controls -------------------------------------------------

def test_random_unit_does_not_survive_or_compress():
    rng = random.Random(2)
    bits = [rng.randint(0, 1) for _ in range(1000)]
    rep = survival_report(bits, n_shuffle=100, seed=0)
    assert not rep["survives"]
    assert description_length_gain(bits)["gain_bits"] < 0  # no compression beyond model cost


def test_clustered_unit_survives_and_is_persistent():
    bits = _clustered_bits(1000, seed=3)
    rep = survival_report(bits, n_shuffle=100, seed=0)
    assert rep["survives"]
    assert rep["z"]["autocorr1"] > 2.0
    bt = behaviour_table(bits)
    assert bt["persistence_excess"] > 0.05
    assert bt["columns"]["memory_hurst"] > 0.5


def test_hurst_independent_near_half():
    rng = random.Random(4)
    bits = [rng.randint(0, 1) for _ in range(4096)]
    assert abs(hurst_aggregated_variance(bits) - 0.5) < 0.08


def test_autocorr_and_run_helpers():
    assert lag1_autocorr([0, 1, 0, 1, 0, 1]) < 0        # anti-persistent
    assert lag1_autocorr([1, 1, 1, 0, 0, 0]) > 0        # persistent
    assert longest_run_of_ones([0, 1, 1, 1, 0, 1]) == 3
