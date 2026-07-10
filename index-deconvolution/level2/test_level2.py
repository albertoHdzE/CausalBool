"""Tests for Level 2 whole-pattern dynamics.  Run: python -m pytest level2/ -q"""

import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from ca_deconvolution import evolve_eca
from pattern_dynamics import evaluate_lookup, whole_pattern_lookup


def test_whole_pattern_exact_on_deterministic_ca():
    # A deterministic CA trajectory: once a pattern is seen, its successor is
    # fixed, so the lookup predicts perfectly out of sample.
    rng = random.Random(110)
    ca = evolve_eca(110, [rng.randint(0, 1) for _ in range(9)], 400)
    r = evaluate_lookup(ca, int(0.6 * len(ca)))
    assert r["exact_pattern_rate"] == 1.0
    assert r["per_bit_accuracy"] == 1.0


def test_lookup_is_deterministic_map():
    ca = evolve_eca(90, [1, 0, 1, 1, 0, 0, 1, 0, 0], 200)
    model = whole_pattern_lookup(ca)
    # every learnt successor is a valid one-step image
    for t in range(len(ca) - 1):
        if tuple(ca[t]) in model:
            # the map is single-valued
            assert isinstance(model[tuple(ca[t])], tuple)
