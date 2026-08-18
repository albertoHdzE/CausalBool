"""Regimes to bits, so that the Boolean gate family applies (protocol 1b.1).

Three encodings are implemented and **all three are reported**, whatever they
show. Reporting only the best of three would be selection over encodings, which
is the error Level 4 of the deconvolution programme records and which GWP3
conclusion 2 — *discretisation matters more than model choice* — warns about
from the other direction.

The primary encoding is thermometer, because the three regimes are **ordered**:
they are labelled by the arithmetic mean of the underlying monthly change, so
bear < stagnant < bull is a fact about the fit and not a convention. A
thermometer code preserves that order and gives each bit an economic reading.
Plain binary destroys the order and admits an unrealisable code; one-hot
preserves it but is redundant by construction.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

#: Bits per regime, per encoding.
WIDTH = {"thermometer": 2, "binary": 2, "onehot": 3}

#: Bit names, used to keep the node labels readable in every report.
SUFFIX = {
    "thermometer": ("not_bear", "bull"),
    "binary": ("b0", "b1"),
    "onehot": ("is_bear", "is_stagnant", "is_bull"),
}

_CODES = {
    # regime -> tuple of bits
    "thermometer": {0: (0, 0), 1: (1, 0), 2: (1, 1)},      # 01 is unreachable
    "binary": {0: (0, 0), 1: (1, 0), 2: (0, 1)},           # 11 is unreachable
    "onehot": {0: (1, 0, 0), 1: (0, 1, 0), 2: (0, 0, 1)},
}


def encode_frame(frame: pd.DataFrame, kind: str = "thermometer") -> pd.DataFrame:
    """Expand a frame of ternary regimes into binary node columns.

    Seven series at two bits each gives fourteen binary nodes. Every node is a
    target as well as a candidate parent, so what is built is a network rather
    than a single conditional — which is the correction Phase 1b exists to make.
    """
    if kind not in _CODES:
        raise ValueError(f"unknown encoding {kind!r}")
    codes, suffix = _CODES[kind], SUFFIX[kind]
    out = {}
    for col in frame.columns:
        v = frame[col].to_numpy(np.int64)
        bits = np.asarray([codes[int(x)] for x in v], dtype=np.int64)
        for j, name in enumerate(suffix):
            out[f"{col}.{name}"] = bits[:, j]
    return pd.DataFrame(out, index=frame.index)


def decode_column(bits: np.ndarray, kind: str = "thermometer") -> np.ndarray:
    """Inverse of :func:`encode_frame` for one series, for round-trip checks.

    Unreachable codes are mapped to the nearest reachable regime rather than
    raising, because a *predicted* bit pattern may fall outside the reachable
    set even though an observed one never does. Which codes are unreachable is
    part of what distinguishes the three encodings and is reported.
    """
    bits = np.atleast_2d(bits)
    if kind == "thermometer":
        return bits.sum(axis=1)                     # 00->0, 10->1, 11->2, 01->1
    if kind == "binary":
        val = bits[:, 0] + 2 * bits[:, 1]
        return np.clip(val, 0, 2)
    if kind == "onehot":
        return np.where(bits.sum(axis=1) == 1, bits.argmax(axis=1),
                        bits.argmax(axis=1))
    raise ValueError(kind)


def reachable_codes(kind: str) -> dict:
    """Which bit patterns a regime can produce, and how many are unreachable."""
    codes = _CODES[kind]
    width = WIDTH[kind]
    used = set(codes.values())
    return dict(kind=kind, width=width, n_codes=2 ** width,
                n_used=len(used), n_unreachable=2 ** width - len(used),
                mapping={k: "".join(map(str, v)) for k, v in codes.items()})


def round_trip_ok(frame: pd.DataFrame, kind: str) -> bool:
    """Encoding then decoding must return the original regimes exactly."""
    enc = encode_frame(frame, kind)
    w = WIDTH[kind]
    for i, col in enumerate(frame.columns):
        block = enc.iloc[:, i * w:(i + 1) * w].to_numpy()
        if not np.array_equal(decode_column(block, kind), frame[col].to_numpy()):
            return False
    return True
