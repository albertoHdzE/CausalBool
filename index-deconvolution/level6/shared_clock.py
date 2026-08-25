"""shared_clock.py  (Level 6)

Is the activity clock shared across instruments?  If the timing of salient events
is driven by one common, market-wide activity, then each instrument's clock is
largely explained by the others', and the others' recent activity should forecast
an instrument's future activity beyond its own past.

The instruments are aligned on their common trading days so their activity signals
are contemporaneous.  The common signal for a target is the leave-one-out mean of
the others' activity, so nothing of the target leaks into its own predictor.
"""

from __future__ import annotations

import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import load_yahoo_close  # noqa: E402
from point_process import activity_signal  # noqa: E402

LONG_DIR = os.path.join(ROOT, "finance", "data_long")


def aligned_prices() -> tuple[list[str], list[list[float]]]:
    """Return (names, matrix) with matrix[name_index] the price series on the
    common trading days of all instruments."""
    names = sorted(f[:-5] for f in os.listdir(LONG_DIR) if f.endswith(".json"))
    series = {nm: load_yahoo_close(os.path.join(LONG_DIR, nm + ".json")) for nm in names}
    common = sorted(set.intersection(*(set(s) for s in series.values())))
    matrix = [[series[nm][d] for d in common] for nm in names]
    return names, matrix


def activity_matrix(theta: float, window: int) -> tuple[list[str], list[list[int]]]:
    names, matrix = aligned_prices()
    acts = [activity_signal(px, theta, window) for px in matrix]
    L = min(len(a) for a in acts)
    return names, [a[:L] for a in acts]


def pearson(x: list[float], y: list[float]) -> float:
    mx, my = statistics.mean(x), statistics.mean(y)
    sx = math.sqrt(sum((a - mx) ** 2 for a in x))
    sy = math.sqrt(sum((b - my) ** 2 for b in y))
    return sum((a - mx) * (b - my) for a, b in zip(x, y)) / (sx * sy) if sx * sy else 0.0


def leave_one_out_common(acts: list[list[int]], j: int) -> list[float]:
    others = [acts[k] for k in range(len(acts)) if k != j]
    return [statistics.mean(vals) for vals in zip(*others)]
