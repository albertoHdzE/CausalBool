"""Tests for Level 3 gate-agnostic behaviour-table analysis.
Run: python -m pytest level3/ -q"""

import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from causalbool import apply_gate
from behaviour_table import behaviour_decomposition, lz76_complexity, run_length_encoding


def _gate_column(n, connected, gate):
    return [apply_gate(gate, [(x >> i) & 1 for i in connected]) for x in range(2 ** n)]


def test_structured_pattern_compresses():
    # AND of 3 of 8 inputs: one schema covers all 2^5 ones; 5 sumando bits.
    col = _gate_column(8, [1, 3, 5], "AND")
    d = behaviour_decomposition(col, 8)
    assert d["num_schemata"] == 1
    assert len(d["sumando_bits"]) == 5
    assert d["ones_per_schema"] == 32.0


def test_random_pattern_does_not_compress():
    import random
    rng = random.Random(0)
    col = [rng.randint(0, 1) for _ in range(256)]
    d = behaviour_decomposition(col, 8)
    # many schemata, few ones each -> incompressible
    assert d["num_schemata"] > 20
    assert d["ones_per_schema"] < 5


def test_lz76_orders_structure_below_randomness():
    periodic = [0, 1] * 200
    import random
    rng = random.Random(3)
    rand = [rng.randint(0, 1) for _ in range(400)]
    assert lz76_complexity(periodic) < lz76_complexity(rand)


def test_run_length_encoding_basic():
    assert run_length_encoding([0, 0, 0, 1, 0]) == [(0, 3), (1, 1), (0, 1)]


def test_local_complexity_profile_detects_clustered_structure():
    # A series with a calm (low-complexity) half and a random (high-complexity)
    # half has a dispersed window profile; a uniform-random series does not.
    import random
    from exp11_pivot_distribution import window_profile
    import statistics
    rng = random.Random(2)
    clustered = [0, 1] * 200 + [rng.randint(0, 1) for _ in range(400)]
    uniform = [rng.randint(0, 1) for _ in range(800)]
    disp_clustered = statistics.pstdev(window_profile(clustered, 30))
    disp_uniform = statistics.pstdev(window_profile(uniform, 30))
    assert disp_clustered > disp_uniform
