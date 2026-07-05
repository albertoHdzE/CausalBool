from __future__ import annotations

import math

import numpy as np
import pandas as pd


def median_absolute_deviation(values: np.ndarray) -> float:
    median = np.median(values)
    return float(np.median(np.abs(values - median)))


def _relative_reprogrammability(values: np.ndarray, *, use_absolute_normalizer: bool) -> float:
    if values.size == 0:
        return 0.0
    maximum = float(np.max(np.abs(values))) if use_absolute_normalizer else float(np.max(values))
    if maximum == 0.0:
        return 0.0
    return median_absolute_deviation(values) / maximum


def relative_reprogrammability(signature: pd.DataFrame) -> float:
    values = signature["delta"].to_numpy(dtype=float)
    # Matches the recovered supplement text from arXiv v7 / biorxiv full manuscript.
    return _relative_reprogrammability(values, use_absolute_normalizer=True)


def relative_reprogrammability_algodyn_reference(signature: pd.DataFrame) -> float:
    values = signature["delta"].to_numpy(dtype=float)
    # Mirrors the recovered local algodyn implementation.
    return _relative_reprogrammability(values, use_absolute_normalizer=False)


def absolute_reprogrammability(signature: pd.DataFrame) -> float:
    """PA(G) := |S(σP) − S(σN)| / max(S(σP), S(σN)).

    The paper (arXiv 1709.05429 §2.4, p.14; Supplement §1, p.25) defines S as
    "an interpolation function" over the positive and negative segments of σ(G).
    Trapezoidal integration is the natural discrete interpolation — it computes
    the area under the piecewise-linear curve through the sorted delta values,
    which is exactly what "interpolation function" means operationally.

    The algodyn R package never implemented this (only stubs), but the
    mathematical definition is unambiguous.
    """
    values = signature["delta"].to_numpy(dtype=float)
    positive = np.sort(values[values > 0])
    negative = np.sort(np.abs(values[values < 0]))
    area_positive = float(np.trapezoid(positive)) if positive.size > 0 else 0.0
    area_negative = float(np.trapezoid(negative)) if negative.size > 0 else 0.0
    normalizer = max(area_positive, area_negative)
    if normalizer == 0.0:
        return 0.0
    return abs(area_positive - area_negative) / normalizer


def combined_reprogrammability(signature: pd.DataFrame) -> float:
    """||VR(G)|| = sqrt(Pr²(G) + PA²(G)).

    Combined reprogrammability is the Euclidean norm on the programmability
    space Pr(G) × PA(G) (arXiv 1709.05429 §2.4, p.14; Supplement §1, p.25).
    """
    rel = relative_reprogrammability(signature)
    abs_val = absolute_reprogrammability(signature)
    return math.sqrt(rel * rel + abs_val * abs_val)


# Backward-compatible aliases (used by experiments.py and tests)
absolute_reprogrammability_trapezoid_proxy = absolute_reprogrammability
combined_reprogrammability_trapezoid_proxy = combined_reprogrammability
