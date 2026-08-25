"""test_level6.py

Deterministic tests for the clock point-process analysis: the Fano exponent must
read near zero on an independent (renewal) process and clearly positive on a
clustered one; the generalised Hurst must read near 1/2 on white noise; the shared-
clock helpers must align and reduce correctly.
"""

from __future__ import annotations

import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from point_process import (fano_exponent, activity_signal, generalised_hurst,
                           pivot_indices)
from shared_clock import pearson, leave_one_out_common

WINDOWS = [10, 20, 40, 80, 160, 320]


def _poisson_times(n, p, seed):
    rng = random.Random(seed)
    return [t for t in range(n) if rng.random() < p]


def _clustered_times(n, seed):
    """A bursty point process: an on/off latent state; events dense when 'on'."""
    rng = random.Random(seed)
    on = False
    times = []
    for t in range(n):
        on = (rng.random() < 0.98) if on else (rng.random() < 0.01)
        if on and rng.random() < 0.7:
            times.append(t)
    return times


def test_fano_flat_for_poisson():
    times = _poisson_times(12000, 0.1, 1)
    fx = fano_exponent(times, 12000, WINDOWS)
    assert abs(fx["alpha"]) < 0.15          # renewal: flat Fano factor


def test_fano_positive_for_clustered():
    times = _clustered_times(12000, 2)
    fx = fano_exponent(times, 12000, WINDOWS)
    assert fx["alpha"] > 0.3                # clustering grows the Fano factor
    assert fx["r2"] > 0.8


def test_activity_signal_shape():
    rng = random.Random(3)
    s = [100.0]
    for _ in range(2000):
        s.append(s[-1] * (1 + 0.01 * (rng.random() - 0.5)))
    a = activity_signal(s, 0.02, 40)
    assert len(a) == (len(s) - 40) // 40 + 1
    assert all(x >= 0 for x in a)


def test_generalised_hurst_white_noise_near_half():
    rng = random.Random(4)
    sig = [rng.gauss(0, 1) for _ in range(4096)]
    h = generalised_hurst(sig, [2.0], [8, 16, 32, 64, 128, 256])
    assert abs(h[2.0] - 0.5) < 0.12


def test_pearson_bounds_and_perfect():
    assert abs(pearson([1, 2, 3, 4], [2, 4, 6, 8]) - 1.0) < 1e-9
    assert abs(pearson([1, 2, 3, 4], [4, 3, 2, 1]) + 1.0) < 1e-9


def test_leave_one_out_excludes_self():
    acts = [[1, 1, 1], [2, 2, 2], [3, 3, 3]]
    # leave out index 0 -> mean of [2,2,2] and [3,3,3] = 2.5
    assert leave_one_out_common(acts, 0) == [2.5, 2.5, 2.5]


def test_pivot_indices_monotone():
    rng = random.Random(5)
    s = [100.0]
    for _ in range(3000):
        s.append(s[-1] * (1 + 0.01 * (rng.random() - 0.5)))
    idx = pivot_indices(s, 0.02)
    assert idx == sorted(idx)
    assert all(0 <= i < len(s) for i in idx)
