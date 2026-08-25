"""Complexity estimators used by Zenil, Kiani, Zea and Tegner (2018),
"Algorithmic Causal Deconvolution of Intertwined Data and Networks by
Generating Mechanism", arXiv:1802.09904v8.

The paper fixes its estimator parameters explicitly (Section 2.4):

    "The only parameter used for the application of BDM ... is to set the
     overlapping of the decomposition to the maximum 12 bits for strings and
     4 square bits for arrays, given the current best CTM approximations from
     an empirical distribution based on all Turing machines with up to 5
     states, with no string/array overlapping in the decomposition."

``pybdm`` ships exactly those two CTM tables (``CTM-B2-D12`` and
``CTM-B2-D4x4``), so the numerical backend here is the same empirical
approximation to the Universal Distribution that the authors used.

The remaining estimators (Shannon entropy, mutual information, normalised
compression distance) reproduce the Wolfram Language definitions given
verbatim in Supplementary Information Section 4.4.
"""

from __future__ import annotations

import math
import zlib
from collections import Counter
from functools import lru_cache
from typing import Iterable, Sequence

import numpy as np
from pybdm import BDM

__all__ = [
    "bdm_1d",
    "bdm_2d",
    "string_bdm",
    "entropy",
    "mutual_information",
    "ncd",
    "compress_length",
    "block_entropy_2d",
]

# ---------------------------------------------------------------------------
# Block Decomposition Method
# ---------------------------------------------------------------------------

_BDM_1D = BDM(ndim=1, warn_if_missing_ctm=False)
_BDM_2D = BDM(ndim=2, warn_if_missing_ctm=False)


def _as_binary(array: np.ndarray, ndim: int) -> np.ndarray:
    arr = np.asarray(array, dtype=int)
    if arr.ndim != ndim:
        raise ValueError(f"expected a {ndim}D array, received shape {arr.shape}")
    bad = np.setdiff1d(np.unique(arr), np.array([0, 1]))
    if bad.size:
        raise ValueError(f"BDM tables are binary; received symbols {bad.tolist()}")
    return arr


def bdm_1d(sequence: Sequence[int]) -> float:
    """BDM of a binary string with 12-bit non-overlapping blocks (paper: strings)."""
    arr = _as_binary(np.asarray(sequence), 1)
    if arr.size < 12:
        # Below one block pybdm has no CTM entry; fall back to the padded block.
        arr = np.concatenate([arr, np.zeros(12 - arr.size, dtype=int)])
    return float(_BDM_1D.bdm(arr))


def bdm_2d(array: np.ndarray) -> float:
    """BDM of a binary array with 4x4 non-overlapping blocks (paper: arrays/graphs)."""
    arr = _as_binary(array, 2)
    if arr.shape[0] < 4 or arr.shape[1] < 4:
        pad_r = max(0, 4 - arr.shape[0])
        pad_c = max(0, 4 - arr.shape[1])
        arr = np.pad(arr, ((0, pad_r), (0, pad_c)))
    return float(_BDM_2D.bdm(arr))


@lru_cache(maxsize=1 << 20)
def _string_bdm_cached(bits: str) -> float:
    return bdm_1d([int(c) for c in bits])


def string_bdm(bits: Iterable[int] | str) -> float:
    """``StringBDM`` of the Supplementary Information, memoised.

    The sliding-window row analyses evaluate the same short words millions of
    times, so caching on the bit-string key is what makes them tractable.
    """
    if not isinstance(bits, str):
        bits = "".join(str(int(b)) for b in bits)
    return _string_bdm_cached(bits)


def block_entropy_2d(array: np.ndarray) -> float:
    """Shannon entropy over the same 4x4 block partition BDM uses.

    Used for the Supplementary Fig. 8B comparison, where the paper reports that
    "all values collapse into a single value for entropy".
    """
    arr = _as_binary(array, 2)
    rows = (arr.shape[0] // 4) * 4
    cols = (arr.shape[1] // 4) * 4
    blocks = [
        arr[i : i + 4, j : j + 4].tobytes()
        for i in range(0, rows, 4)
        for j in range(0, cols, 4)
    ]
    if not blocks:
        return 0.0
    counts = Counter(blocks)
    total = len(blocks)
    return -sum((c / total) * math.log2(c / total) for c in counts.values())


# ---------------------------------------------------------------------------
# Classical information theory (Sup. Inf. 4.4)
# ---------------------------------------------------------------------------


def _elements(x) -> list:
    """Mathematica's ``Entropy`` treats its argument as a flat list of elements.

    For a 2D array (a list of rows) the elements are therefore the *rows*, which
    is what ``MutualInformation[#, array]`` in the Sup. Inf. compares.
    """
    arr = np.asarray(x)
    if arr.ndim <= 1:
        return arr.tolist()
    return [tuple(row) for row in arr.reshape(arr.shape[0], -1).tolist()]


def entropy(x, base: float = math.e) -> float:
    """``Entropy[x]``: Shannon entropy of the empirical distribution of elements.

    Mathematica's default base is ``e``; the paper's ``MutualInformation`` uses
    that default, so it is kept here.
    """
    elems = _elements(x)
    if not elems:
        return 0.0
    counts = Counter(elems)
    n = len(elems)
    return -sum((c / n) * math.log(c / n, base) for c in counts.values())


def _conditional_entropy(x, y, base: float = math.e) -> float:
    """``Statistics`Library`NConditionalEntropy[x, y]`` = H(x | y).

    Estimated from the paired empirical distribution of corresponding elements.
    """
    ex, ey = _elements(x), _elements(y)
    if len(ex) != len(ey):
        raise ValueError("conditional entropy needs element lists of equal length")
    n = len(ex)
    if n == 0:
        return 0.0
    joint = Counter(zip(ex, ey))
    marginal_y = Counter(ey)
    total = 0.0
    for (a, b), c in joint.items():
        p_joint = c / n
        p_cond = c / marginal_y[b]
        total -= p_joint * math.log(p_cond, base)
    return total


def mutual_information(x, y) -> float:
    """Verbatim Sup. Inf. 4.4::

        MutualInformation[x_, y_] :=
         N[Entropy[x] + Entropy[y] - Statistics`Library`NConditionalEntropy[x, y]]

    Note this is the paper's own definition and is *not* the textbook mutual
    information ``H(x) + H(y) - H(x, y)``; it is reproduced as written.
    """
    return entropy(x) + entropy(y) - _conditional_entropy(x, y)


def compress_length(x) -> int:
    """Byte count of a losslessly compressed object.

    The Sup. Inf. uses ``ByteCount[Compress[x]]``. Wolfram's ``Compress`` is a
    zlib deflate of the internal expression followed by a base-64 encoding; the
    closest faithful substitute available outside Mathematica is a raw zlib
    deflate of the canonical byte serialisation, which is what is used here.
    """
    arr = np.asarray(x, dtype=np.int8)
    return len(zlib.compress(arr.tobytes(), level=9))


def ncd(x, y) -> float:
    """Verbatim Sup. Inf. 4.4::

        NCD[x_, y_] := N@Block[{cx = ByteCount[Compress[x]],
                                cy = ByteCount[Compress[y]],
                                cxy = ByteCount[Compress[Join[x, y]]]},
                               (cxy - Min[cx, cy]) / Max[cx, cy]]
    """
    ax, ay = np.asarray(x), np.asarray(y)
    joined = np.concatenate([ax, ay], axis=0)
    cx, cy, cxy = compress_length(ax), compress_length(ay), compress_length(joined)
    return (cxy - min(cx, cy)) / max(cx, cy)
