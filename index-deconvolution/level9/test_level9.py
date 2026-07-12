"""test_level9.py

Deterministic tests for the Hawkes generative program: the log-likelihood must
reduce to Poisson when there is no excitation, the fit must recover a near-zero
branching ratio on a simulated Poisson process and a clearly positive one on a
simulated self-exciting process, and the simulator must respect its window.
"""

from __future__ import annotations

import math
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from hawkes import loglik, poisson_loglik, fit_hawkes, simulate, oos_loglik


def test_loglik_reduces_to_poisson_when_no_excitation():
    times = [1.0, 3.5, 7.2, 9.9, 15.0]
    T = 20.0
    for mu in (0.1, 0.3, 0.7):
        assert abs(loglik(times, T, mu, 0.0, 1.0) - poisson_loglik(times, T, mu)) < 1e-9


def test_fit_poisson_recovers_low_branching():
    rng = random.Random(1)
    # homogeneous Poisson stream: rate 0.2 on [0, 3000]
    T, t, cur = 3000.0, [], 0.0
    while True:
        cur += rng.expovariate(0.2)
        if cur >= T:
            break
        t.append(cur)
    fit = fit_hawkes(t, T)
    assert fit["branching_ratio"] < 0.3          # memoryless -> low n


def test_fit_recovers_self_excitation():
    # a genuinely self-exciting simulated process must fit with n well above 0
    t = simulate(mu=0.05, alpha=0.09, beta=0.15, T=6000.0, seed=3)  # true n = 0.6
    assert len(t) > 50
    fit = fit_hawkes(t, T=6000.0)
    assert fit["branching_ratio"] > 0.3
    # and it should beat the Poisson likelihood in sample
    mu_p = len(t) / 6000.0
    assert fit["loglik"] > poisson_loglik(t, 6000.0, mu_p)


def test_simulate_within_window_and_ordered():
    t = simulate(mu=0.1, alpha=0.05, beta=0.2, T=1000.0, seed=0)
    assert all(0 <= x < 1000.0 for x in t)
    assert t == sorted(t)


def test_oos_loglik_additivity():
    times = [1.0, 2.0, 5.0, 6.0, 9.0, 12.0, 15.0, 18.0]
    T, Ttr = 20.0, 10.0
    mu, alpha, beta = 0.2, 0.1, 0.3
    test_ll, n_test = oos_loglik(times, T, Ttr, mu, alpha, beta)
    train = [x for x in times if x <= Ttr]
    assert n_test == len(times) - len(train)
    # test window LL = full LL - train LL (by construction)
    assert abs(test_ll - (loglik(times, T, mu, alpha, beta)
                          - loglik(train, Ttr, mu, alpha, beta))) < 1e-9


def test_loglik_finite_on_reasonable_params():
    t = simulate(mu=0.1, alpha=0.06, beta=0.2, T=2000.0, seed=5)
    v = loglik(t, 2000.0, 0.1, 0.06, 0.2)
    assert math.isfinite(v)
