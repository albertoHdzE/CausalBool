"""test_level7.py

Deterministic tests for the recursion (clock of the clock) and the joint (dt, dv)
law.  The key calibration: a random walk's legs must be Brownian (within-leg
diffusion exponent near 1/2), so a departure on real data is meaningful; and the
absolute directional-change construction must find reversals and preserve ordering.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))

from recursion import absolute_dc_pivots, meta_clock_exponent
from joint_law import within_leg_diffusion_exponent, cross_leg_couplings
from pivots import directional_change_pivots, legs
from controls import geometric_random_walk


def test_absolute_dc_on_zigzag():
    x = [0.0, 5.0, 0.0, 6.0, 0.0, 7.0]     # reversals of 5-7 absolute
    piv = absolute_dc_pivots(x, 3.0)
    assert piv == sorted(piv)
    assert len(piv) >= 3
    assert absolute_dc_pivots(x, 0.0) == []   # non-positive threshold -> none


def test_absolute_dc_monotone_none():
    x = [float(t) for t in range(200)]
    assert absolute_dc_pivots(x, 5.0) == []   # never reverses


def test_meta_clock_exponent_finite_on_bursty():
    # a bursty non-negative signal should yield meta-pivots and a finite exponent
    rng = random.Random(1)
    sig = []
    on = False
    for _ in range(4000):
        on = (rng.random() < 0.97) if on else (rng.random() < 0.02)
        sig.append(rng.randint(2, 6) if on else rng.randint(0, 1))
    r = meta_clock_exponent([float(x) for x in sig], [4, 8, 16, 32, 64])
    assert r["n_meta_pivots"] > 10
    assert r["alpha"] == r["alpha"]           # not NaN


def test_within_leg_exponent_brownian_on_random_walk():
    rng = random.Random(2)
    s = geometric_random_walk(12000, 0.01, rng)
    lg = legs(directional_change_pivots(s, 0.02))
    H = within_leg_diffusion_exponent(lg)
    assert 0.4 < H < 0.6                       # a random walk's legs are Brownian


def test_cross_leg_couplings_keys_and_bounds():
    rng = random.Random(3)
    s = geometric_random_walk(6000, 0.01, rng)
    lg = legs(directional_change_pivots(s, 0.02))
    cc = cross_leg_couplings(lg)
    for k in ("within_dt_dv", "calm_then_move", "move_then_rest"):
        assert -1.0 <= cc[k] <= 1.0
    # positive within-leg coupling: longer legs travel further
    assert cc["within_dt_dv"] > 0.0


def test_within_leg_exponent_nan_when_too_few():
    assert math.isnan(within_leg_diffusion_exponent([(1, 0.1), (2, 0.2)]))
