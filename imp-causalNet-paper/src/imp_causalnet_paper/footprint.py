"""The paper's algorithmic information footprint of a 2D object.

Direct transcription of the Wolfram Language functions published in
Supplementary Information 4.4 of arXiv:1802.09904v8.  Each function perturbs
every pixel of a binary array in turn (``Mod[array[[i,j]] + 1, 2]``) and ranks
the pixels by the effect the perturbation has on a chosen index:

* ``CausalDeconvolution`` -- ``BDM[array, 4] - BDM[perturbed, 4]``  (the method
  introduced by the paper);
* ``PIDMI``               -- ``MutualInformation[perturbed, array]``;
* ``PIDNCD``              -- ``NCD[perturbed, array]``.

The sign convention of ``CausalDeconvolution`` is worth stating explicitly,
because every colour map in the paper depends on it.  A **positive** value means
flipping the pixel *lowered* the estimated complexity, so the pixel was itself
contributing to the algorithmic randomness of the object (Fig. 1G "red").  A
**negative** value means flipping it moved the object *towards* randomness, so
the pixel was part of the object's structure (Fig. 1G "blue").  Values near zero
are neutral (Fig. 1G "grey").
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .complexity import bdm_2d, mutual_information, ncd, string_bdm
from .fastbdm import IncrementalBDM2D

__all__ = [
    "Footprint",
    "causal_deconvolution",
    "pid_mi",
    "pid_ncd",
    "calculate_information_row_bdm",
    "calculate_information_row_mi",
    "calculate_information_row_ncd",
    "footprint_colours",
]


@dataclass
class Footprint:
    """Per-pixel information values of a 2D object.

    ``ranking`` is the paper's own output format: ``(flat_index, value)`` pairs
    sorted by value in descending order, as produced by
    ``Reverse[SortBy[Thread[{Range[...], values}], Last]]``.
    """

    values: np.ndarray  # same shape as the analysed array
    method: str

    @property
    def ranking(self) -> list[tuple[int, float]]:
        flat = self.values.ravel()
        order = np.argsort(flat, kind="stable")[::-1]
        # 1-based indices, matching Mathematica's Range[Length[...]]
        return [(int(i) + 1, float(flat[i])) for i in order]

    @property
    def signature(self) -> np.ndarray:
        """Values sorted descending -- the paper's *information signature*."""
        return np.sort(self.values.ravel())[::-1]


def _point_mutations(array: np.ndarray):
    """``pointrowmutation`` of the Sup. Inf.: every single-pixel flip, row-major."""
    arr = np.asarray(array, dtype=int)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            mutated = arr.copy()
            mutated[i, j] = (mutated[i, j] + 1) % 2
            yield i, j, mutated


def causal_deconvolution(array: np.ndarray, exact_slow: bool = False) -> Footprint:
    """``CausalDeconvolution[array_]`` -- BDM information value of every pixel.

    ``exact_slow=True`` recomputes the full BDM for each of the ``rows * cols``
    perturbations, literally as the Wolfram one-liner does.  The default routes
    the same arithmetic through :class:`~imp_causalnet_paper.fastbdm.IncrementalBDM2D`,
    which is bit-for-bit identical (see ``tests/test_replication.py``) but many
    orders of magnitude faster on the image sizes the paper uses.
    """
    arr = np.asarray(array, dtype=int)
    if exact_slow:
        base = bdm_2d(arr)
        values = np.empty(arr.shape, dtype=float)
        for i, j, mutated in _point_mutations(arr):
            values[i, j] = base - bdm_2d(mutated)
        return Footprint(values, "BDM")

    inc = IncrementalBDM2D(arr)
    base = inc.value
    values = np.empty(arr.shape, dtype=float)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            values[i, j] = base - inc.value_after_flips([(i, j)])
    return Footprint(values, "BDM")


def pid_mi(array: np.ndarray) -> Footprint:
    """``PIDMI[array_]`` -- the mutual-information control of the Sup. Inf."""
    arr = np.asarray(array, dtype=int)
    values = np.empty(arr.shape, dtype=float)
    for i, j, mutated in _point_mutations(arr):
        values[i, j] = mutual_information(mutated, arr)
    return Footprint(values, "PID-MI")


def pid_ncd(array: np.ndarray) -> Footprint:
    """``PIDNCD[array_]`` -- the normalised-compression-distance control."""
    arr = np.asarray(array, dtype=int)
    values = np.empty(arr.shape, dtype=float)
    for i, j, mutated in _point_mutations(arr):
        values[i, j] = ncd(mutated, arr)
    return Footprint(values, "PID-NCD")


# ---------------------------------------------------------------------------
# Sliding-window row analyses (Sup. Inf. 4.4, second group of functions)
# ---------------------------------------------------------------------------
#
# ``Take[array[[i]], {m, m + 6}]``   -> 7 cells
# ``Take[array[[i]], {m + 7, m + 12}]`` -> 6 cells
# so each window spans 13 cells split 7 | 6, sliding one cell at a time.


def _row_windows(row: np.ndarray):
    n = len(row)
    for m in range(n - 12):
        yield row[m : m + 7], row[m + 7 : m + 13]


def calculate_information_row_bdm(array: np.ndarray) -> np.ndarray:
    """``CalculateInformationRowBDM`` -- ``|StringBDM(left) - StringBDM(right)|``."""
    arr = np.asarray(array, dtype=int)
    return np.array(
        [
            [abs(string_bdm(a) - string_bdm(b)) for a, b in _row_windows(row)]
            for row in arr
        ]
    )


def calculate_information_row_mi(array: np.ndarray) -> np.ndarray:
    """``CalculateInformationRowMI``."""
    arr = np.asarray(array, dtype=int)
    return np.array(
        [[mutual_information(a, b) for a, b in _row_windows(row)] for row in arr]
    )


def calculate_information_row_ncd(array: np.ndarray) -> np.ndarray:
    """``CalculateInformationRowNCD``."""
    arr = np.asarray(array, dtype=int)
    return np.array([[ncd(a, b) for a, b in _row_windows(row)] for row in arr])


# ---------------------------------------------------------------------------
# Colouring
# ---------------------------------------------------------------------------


def footprint_colours(values: np.ndarray, neutral_tol: float | None = None) -> np.ndarray:
    """Ternary map matching the Fig. 1G legend: -1 blue, 0 grey, +1 red.

    ``neutral_tol`` defaults to a tenth of the robust scale of the values, which
    reproduces the paper's "absolute neutral values are those closest to 0".
    """
    v = np.asarray(values, dtype=float)
    if neutral_tol is None:
        scale = np.median(np.abs(v - np.median(v)))
        neutral_tol = 0.1 * scale if scale > 0 else 1e-9
    out = np.zeros_like(v, dtype=int)
    out[v > neutral_tol] = 1
    out[v < -neutral_tol] = -1
    return out
