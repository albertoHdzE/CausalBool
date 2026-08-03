"""Exact incremental BDM for single-bit perturbations of a 2D binary array.

The deconvolution algorithms evaluate ``C(G) - C(G \\ e)`` for *every* edge, and
the robustness study of Fig. 5 repeats that over hundreds of graphs.  Recomputing
the whole Block Decomposition Method each time is wasteful: flipping one entry
touches exactly one 4x4 block of the non-overlapping partition.

Because BDM is

.. math:: C(X) = \\sum_{(r_u, n_u)} \\mathrm{CTM}(r_u) + \\log_2 n_u

over the *distinct* blocks ``r_u`` with multiplicities ``n_u`` (Eq. 2 of the
paper), a single flip changes the block multiset in a completely local way, and
the resulting value can be updated in constant time.

This class returns values that are bit-for-bit identical to
:func:`~imp_causalnet_paper.complexity.bdm_2d`; :mod:`tests.test_fastbdm` asserts
that equivalence.
"""

from __future__ import annotations

from collections import Counter
from math import log2

import numpy as np

from .complexity import _BDM_2D

__all__ = ["IncrementalBDM2D"]


class IncrementalBDM2D:
    """BDM of a binary array under cheap, exactly-computed single-bit edits."""

    def __init__(self, array: np.ndarray):
        self.array = np.asarray(array, dtype=int).copy()
        rows, cols = self.array.shape
        # pybdm's default partition ignores the remainder beyond whole blocks.
        self.nbr, self.nbc = rows // 4, cols // 4
        self._keys: dict[tuple[int, int], str] = {}
        self._ctm: dict[str, float] = {}
        counts: Counter[str] = Counter()
        for br in range(self.nbr):
            for bc in range(self.nbc):
                key, ctm = self._block(br, bc)
                self._keys[(br, bc)] = key
                self._ctm[key] = ctm
                counts[key] += 1
        self._counts = counts
        self._value = sum(self._ctm[k] + log2(n) for k, n in counts.items())

    # -- internals ---------------------------------------------------------
    def _block(self, br: int, bc: int) -> tuple[str, float]:
        block = self.array[4 * br : 4 * br + 4, 4 * bc : 4 * bc + 4]
        key, ctm = next(iter(_BDM_2D.lookup([block])))
        return key, ctm

    def _block_of(self, i: int, j: int) -> tuple[int, int] | None:
        br, bc = i // 4, j // 4
        if br >= self.nbr or bc >= self.nbc:
            return None  # inside the ignored margin: no contribution at all
        return br, bc

    @staticmethod
    def _term(ctm: float, n: int) -> float:
        return ctm + log2(n) if n > 0 else 0.0

    # -- public API --------------------------------------------------------
    @property
    def value(self) -> float:
        """BDM of the current array."""
        return self._value

    def value_after_flips(self, coords) -> float:
        """BDM of the array with the given ``(i, j)`` entries flipped, without mutating."""
        blocks = {b for b in (self._block_of(i, j) for i, j in coords) if b is not None}
        if not blocks:
            return self._value

        for i, j in coords:
            self.array[i, j] ^= 1
        try:
            delta_counts: Counter[str] = Counter()
            new_ctm: dict[str, float] = {}
            for b in blocks:
                old_key = self._keys[b]
                new_key, ctm = self._block(*b)
                new_ctm[new_key] = ctm
                delta_counts[old_key] -= 1
                delta_counts[new_key] += 1
        finally:
            for i, j in coords:
                self.array[i, j] ^= 1

        delta = 0.0
        for key, dn in delta_counts.items():
            if dn == 0:
                continue
            old_n = self._counts.get(key, 0)
            ctm = self._ctm.get(key, new_ctm.get(key))
            delta += self._term(ctm, old_n + dn) - self._term(ctm, old_n)
        return self._value + delta

    def apply_flips(self, coords) -> float:
        """Permanently flip the given entries and return the new BDM."""
        for i, j in coords:
            self.array[i, j] ^= 1
        blocks = {b for b in (self._block_of(i, j) for i, j in coords) if b is not None}
        for b in blocks:
            old_key = self._keys[b]
            new_key, ctm = self._block(*b)
            self._ctm[new_key] = ctm
            self._counts[old_key] -= 1
            if self._counts[old_key] == 0:
                del self._counts[old_key]
            self._counts[new_key] += 1
            self._keys[b] = new_key
        self._value = sum(self._ctm[k] + log2(n) for k, n in self._counts.items())
        return self._value
