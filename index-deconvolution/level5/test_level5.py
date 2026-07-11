"""test_level5.py

Deterministic tests for the representation-free pivot geometry: the directional-
change construction, the fractal-dimension fit, Benford, and the intrinsic-time
memory, each pinned on a synthetic where the answer is known.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from pivots import directional_change_pivots, legs
from occurrence_geometry import (fractal_dimension, benford_distance, leading_digit,
                                 intrinsic_time_memory, BENFORD)
from controls import geometric_random_walk, return_shuffle, log_returns, rebuild_from_returns


def test_directional_change_on_zigzag():
    # a clean zig-zag: 100 -> 110 -> 99 -> 121 -> ...  reversals of >5% each
    s = [100, 110, 99, 121, 100, 130]
    pv = directional_change_pivots(s, 0.05)
    kinds = [p.kind for p in pv]
    # alternating peaks and troughs
    assert all(kinds[i] != kinds[i + 1] for i in range(len(kinds) - 1))
    assert len(pv) >= 3


def test_pivot_scale_invariance():
    rng = random.Random(1)
    s = geometric_random_walk(2000, 0.01, rng)
    a = directional_change_pivots(s, 0.03)
    b = directional_change_pivots([1000 * x for x in s], 0.03)  # rescale
    assert [p.index for p in a] == [p.index for p in b]


def test_legs_shapes():
    s = [100, 110, 99, 121]
    pv = directional_change_pivots(s, 0.05)
    lg = legs(pv)
    assert len(lg) == len(pv) - 1
    for dt, dv in lg:
        assert dt >= 1


def test_monotone_has_no_pivots():
    s = [100 * math.exp(0.001 * t) for t in range(500)]
    assert directional_change_pivots(s, 0.05) == []


def test_fewer_pivots_at_larger_theta():
    rng = random.Random(2)
    s = geometric_random_walk(4000, 0.01, rng)
    n_small = len(directional_change_pivots(s, 0.02))
    n_large = len(directional_change_pivots(s, 0.10))
    assert n_small > n_large > 0


def test_fractal_dimension_positive_and_fits_on_gbm():
    rng = random.Random(3)
    s = geometric_random_walk(12000, 0.01, rng)
    fd = fractal_dimension(s, [0.01 * 1.5 ** k for k in range(9)])
    assert fd["r2"] > 0.9          # a clean power law
    assert 1.0 < fd["D"] < 2.5     # in the expected band for a random walk


def test_leading_digit_and_benford():
    assert leading_digit(0.0034) == 3
    assert leading_digit(920.0) == 9
    assert leading_digit(1.0) == 1
    # a scale-invariant (log-uniform) sample is close to Benford
    rng = random.Random(4)
    xs = [10 ** (3 * rng.random()) for _ in range(20000)]
    assert benford_distance(xs)["tv"] < 0.03
    assert abs(sum(BENFORD) - 1.0) < 1e-9


def test_intrinsic_time_returns_finite_memory():
    rng = random.Random(5)
    s = geometric_random_walk(6000, 0.01, rng)
    r = intrinsic_time_memory(s, 0.03)
    assert r["n_legs"] > 10
    assert -1.0 <= r["driver_ac1"] <= 1.0
    assert -1.0 <= r["clock_ac1"] <= 1.0


def test_return_shuffle_preserves_marginal():
    rng = random.Random(6)
    s = geometric_random_walk(3000, 0.01, rng)
    sh = return_shuffle(s, rng)
    a = sorted(round(x, 9) for x in log_returns(s))
    b = sorted(round(x, 9) for x in log_returns(sh))
    # same multiset of increments, reordered
    assert len(a) == len(b)
    assert all(abs(x - y) < 1e-6 for x, y in zip(a, b))


def test_rebuild_roundtrip():
    r = [0.01, -0.02, 0.03]
    s = rebuild_from_returns(r, 100.0)
    got = log_returns(s)
    assert all(abs(x - y) < 1e-9 for x, y in zip(got, r))
