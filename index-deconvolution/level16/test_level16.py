"""test_level16.py

Correctness of the synthetic gate-network constructions and the fractal fit.
Deterministic; standard library + pytest only.
"""

from __future__ import annotations

import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

from synthgate import superpose, branching, nested, alpha_of, fit_nested_alpha  # noqa: E402


def test_superposition_is_flat():
    # a flat OR of independent scales -> Palm-Khinchin -> ~ renewal, Fano exponent ~ 0
    a = [alpha_of(superpose(3000, 8, 2.0, 12000, s), 12000) for s in range(4)]
    assert abs(sum(a) / len(a)) < 0.15


def test_nested_is_self_similar():
    # the fractal nested construction clusters -> Fano exponent clearly positive
    a = [alpha_of(nested(4, 2, 3.0, 400, 12000, s), 12000) for s in range(4)]
    assert sum(a) / len(a) > 0.3


def test_branching_clusters_but_less():
    # a self-exciting cascade clusters, positive but typically below the deep nested one
    ab = sum(alpha_of(branching(200, 0.6, 15, 12000, s), 12000) for s in range(4)) / 4
    an = sum(alpha_of(nested(5, 2, 2.5, 600, 12000, s), 12000) for s in range(4)) / 4
    assert ab > 0.0
    assert an > ab


def test_fit_nested_reaches_target():
    fit = fit_nested_alpha(0.5, n_events=1000, T=12000, seeds=2)
    assert fit["residual"] < 0.2                # a nested construction can match ~0.5
    assert fit["r"] > 1.0 and fit["levels"] >= 3


def test_determinism():
    a = nested(4, 2, 2.5, 500, 8000, 7)
    b = nested(4, 2, 2.5, 500, 8000, 7)
    assert a == b


def test_event_counts_positive():
    assert len(superpose(2000, 6, 2.0, 10000, 1)) > 0
    assert len(nested(4, 2, 2.0, 400, 10000, 1)) > 0
    assert len(branching(100, 0.5, 20, 10000, 1)) > 0
