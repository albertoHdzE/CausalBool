from __future__ import annotations

import math

import numpy as np
import pandas as pd


def median_absolute_deviation(values: np.ndarray) -> float:
    median = np.median(values)
    return float(np.median(np.abs(values - median)))


def relative_reprogrammability(signature: pd.DataFrame) -> float:
    values = signature["delta"].to_numpy(dtype=float)
    if values.size == 0:
        return 0.0
    maximum = float(np.max(values))
    if maximum == 0.0:
        return 0.0
    return median_absolute_deviation(values) / maximum


def absolute_reprogrammability(signature: pd.DataFrame) -> float:
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
    rel = relative_reprogrammability(signature)
    abs_val = absolute_reprogrammability(signature)
    return math.sqrt(rel * rel + abs_val * abs_val)
