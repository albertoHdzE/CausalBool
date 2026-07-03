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


def absolute_reprogrammability(signature: pd.DataFrame) -> float | None:
    # The paper supplement leaves S operationally unspecified, and recovered
    # upstream algodyn history contains only stubs for this primitive.
    return None


def absolute_reprogrammability_trapezoid_proxy(signature: pd.DataFrame) -> float:
    values = signature["delta"].to_numpy(dtype=float)
    positive = np.sort(values[values > 0])
    negative = np.sort(np.abs(values[values < 0]))
    area_positive = float(np.trapezoid(positive)) if positive.size > 0 else 0.0
    area_negative = float(np.trapezoid(negative)) if negative.size > 0 else 0.0
    normalizer = max(area_positive, area_negative)
    if normalizer == 0.0:
        return 0.0
    return abs(area_positive - area_negative) / normalizer


def combined_reprogrammability(signature: pd.DataFrame) -> float | None:
    # Combined reprogrammability inherits the unresolved PA(G) dependency.
    return None


def combined_reprogrammability_trapezoid_proxy(signature: pd.DataFrame) -> float:
    rel = relative_reprogrammability(signature)
    abs_val = absolute_reprogrammability_trapezoid_proxy(signature)
    return math.sqrt(rel * rel + abs_val * abs_val)
