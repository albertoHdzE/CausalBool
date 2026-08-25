"""test_level11.py

Correctness of the spectral instrument and the multi-scale Hawkes kernel.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import cmath
import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level9"))

from spectral import _fft, periodogram, loglog_slope  # noqa: E402
from kernels import (geometric_timescales, powerlaw_amplitudes, loglik_multi,  # noqa: E402
                     fit_powerlaw, oos_loglik_multi)
from hawkes import loglik as loglik_single  # noqa: E402


def _dft(x):
    n = len(x)
    return [sum(x[k] * cmath.exp(-2j * math.pi * k * f / n) for k in range(n))
            for f in range(n)]


def test_fft_matches_dft():
    rng = random.Random(0)
    x = [complex(rng.gauss(0, 1), 0) for _ in range(64)]
    fast, slow = _fft(x), _dft(x)
    for a, b in zip(fast, slow):
        assert abs(a - b) < 1e-9


def test_fft_peak_at_known_frequency():
    n = 256
    k0 = 20
    x = [complex(math.cos(2 * math.pi * k0 * i / n), 0) for i in range(n)]
    X = _fft(x)
    mag = [abs(v) for v in X[: n // 2]]
    assert mag.index(max(mag)) == k0


def test_fft_rejects_non_power_of_two():
    try:
        _fft([1 + 0j] * 3)
    except ValueError:
        return
    assert False, "should reject non-power-of-two length"


def test_spectrum_white_is_flat():
    rng = random.Random(1)
    x = [rng.gauss(0, 1) for _ in range(8192)]
    f, p = periodogram(x)
    s = loglog_slope(f, p)["slope"]
    assert abs(s) < 0.3                                  # white: slope ~ 0


def test_spectrum_random_walk_is_red():
    rng = random.Random(2)
    x = [0.0]
    for _ in range(8191):
        x.append(x[-1] + rng.gauss(0, 1))
    f, p = periodogram(x)
    s = loglog_slope(f, p)["slope"]
    assert s < -1.3                                      # random walk: slope ~ -2


def test_powerlaw_branching_ratio_is_exact():
    betas = geometric_timescales(10)
    for n in (0.2, 0.5, 0.8):
        for g in (0.2, 0.7, 1.2):
            a = powerlaw_amplitudes(betas, n, g)
            got = sum(a[p] / betas[p] for p in range(len(betas)))
            assert math.isclose(got, n, rel_tol=1e-9)


def test_multi_reduces_to_single_exponential():
    # one component: multi-exp loglik must equal the Level 9 single-exp loglik
    rng = random.Random(3)
    times = sorted(rng.uniform(0, 1000) for _ in range(200))
    mu, alpha, beta = 0.1, 0.3, 0.5
    a = loglik_multi(times, 1000.0, mu, [alpha], [beta])
    b = loglik_single(times, 1000.0, mu, alpha, beta)
    assert abs(a - b) < 1e-6


def test_fit_powerlaw_runs_and_is_subcritical():
    rng = random.Random(4)
    times = sorted(rng.uniform(0, 5000) for _ in range(400))
    fit = fit_powerlaw(times, 5000.0, k=8)
    assert 0.0 <= fit["branching_ratio"] < 1.0
    assert fit["mu"] > 0
    # held-out log-likelihood is finite
    ll, ntest = oos_loglik_multi(times, 5000.0, 3500.0, fit["mu"], fit["alphas"], fit["betas"])
    assert math.isfinite(ll) and ntest > 0
