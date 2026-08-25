"""recursion.py  (Level 7)

One recursion deeper: the clock of the clock.

The base clock is the pivot point process of the sequence.  Its activity signal
(the windowed pivot count) is itself a series; its salient turns mark the onset and
end of high- and low-activity regimes.  Finding the pivots of the activity signal
gives a meta-clock, and asking whether the meta-clock clusters the way the base
clock does tests self-similarity across recursion depth -- bursts of bursts.

The activity signal is a non-negative integer count with zeros, so a relative
reversal threshold is ill-defined; the meta-pivots use an absolute directional-
change threshold in units of the signal's own dispersion.  Everything else (the
Fano exponent) is shared with Level 6.
"""

from __future__ import annotations

import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "level6"))

from point_process import fano_exponent  # noqa: E402


def absolute_dc_pivots(x: list[float], thr: float) -> list[int]:
    """Directional-change pivot indices of ``x`` at an absolute reversal ``thr``."""
    if not x or thr <= 0:
        return []
    piv = []
    mode = 0
    ext_val, ext_idx = x[0], 0
    for i in range(1, len(x)):
        v = x[i]
        if mode >= 0 and v > ext_val:
            ext_val, ext_idx, mode = v, i, 1
        elif mode <= 0 and v < ext_val:
            ext_val, ext_idx, mode = v, i, -1
        if mode == 1 and v <= ext_val - thr:
            piv.append(ext_idx)
            mode, ext_val, ext_idx = -1, v, i
        elif mode == -1 and v >= ext_val + thr:
            piv.append(ext_idx)
            mode, ext_val, ext_idx = 1, v, i
    return piv


def meta_clock_exponent(activity: list[float], window_sizes: list[int],
                        thr_sigmas: float = 1.0) -> dict:
    """Fano exponent of the meta-clock: the pivots of the activity signal.

    The reversal threshold is ``thr_sigmas`` standard deviations of the activity.
    Returns the exponent and the number of meta-pivots found.
    """
    if len(activity) < 8:
        return {"alpha": float("nan"), "n_meta_pivots": 0}
    thr = thr_sigmas * statistics.pstdev(activity)
    mp = absolute_dc_pivots(activity, thr)
    fx = fano_exponent(mp, len(activity), window_sizes)
    fx["n_meta_pivots"] = len(mp)
    return fx
