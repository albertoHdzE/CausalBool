"""test_level13.py

Correctness of the scale-free symboliser and the determinism analyser.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from spacetime import logistic_series, symbolise_log, recurrence_and_determinism  # noqa: E402


def test_symbolise_is_scale_free_for_commensurate_rescaling():
    # rescaling by exp(k*h) shifts every symbol by exactly the integer k, so the symbol
    # sequence is identical up to a constant -> transition structure invariant. (For a
    # non-commensurate factor the invariance is only approximate, up to bin-boundary
    # reassignments -- an honest subtlety of a fixed-grid symboliser.)
    h = 0.05
    s = [100.0 * (1.01 ** t) * (1 + 0.1 * math.sin(t)) for t in range(200)]
    a = symbolise_log(s, h)
    factor = math.exp(3 * h)                                  # commensurate: log-factor = 3h
    b = symbolise_log([factor * x for x in s], h)
    assert a == b


def test_coarser_bins_recur_more():
    s = [100.0 * math.exp(0.01 * t + 0.3 * math.sin(t / 5)) for t in range(500)]
    fine = recurrence_and_determinism(symbolise_log(s, 0.005), 2)["recurrence"]
    coarse = recurrence_and_determinism(symbolise_log(s, 0.1), 2)["recurrence"]
    assert coarse > fine


def test_deterministic_sequence_has_zero_contradiction():
    # a strictly periodic symbol stream: every window maps to a unique next symbol
    seq = [0, 1, 2, 3] * 100
    m = recurrence_and_determinism(seq, 2)
    assert m["contradiction"] == 0.0
    assert m["lift"] > 0.0


def test_random_sequence_has_high_contradiction():
    import random
    rng = random.Random(0)
    seq = [rng.randint(0, 3) for _ in range(4000)]
    m = recurrence_and_determinism(seq, 1)
    assert m["contradiction"] > 0.5                    # order-1 windows map to many nexts
    assert abs(m["lift"]) < 0.1                          # no predictive edge


def test_logistic_is_more_deterministic_than_noise():
    import random
    rng = random.Random(1)
    log_m = recurrence_and_determinism(symbolise_log(logistic_series(6000), 0.02), 2)
    noise = [100.0]
    for _ in range(6000):
        noise.append(noise[-1] * math.exp(0.02 * rng.gauss(0, 1)))
    noise_m = recurrence_and_determinism(symbolise_log(noise, 0.02), 2)
    # the deterministic map contradicts itself less than the random walk
    assert log_m["contradiction"] < noise_m["contradiction"]


def test_short_input_is_safe():
    m = recurrence_and_determinism([0, 1], 2)
    assert m["n_windows"] == 0 and math.isnan(m["lift"])
