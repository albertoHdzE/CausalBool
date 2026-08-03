"""Verified ports of the authors' own published R implementation.

Source: https://github.com/allgebrist/Causal-Deconvolution-of-Networks
(the R Shiny code behind http://www.complexitycalculator.com/deconvolution),
maintained by Allan A. Zea, one of the paper's authors, and cited by the paper
itself.  Files ported here: ``scripts/BDM2D.R``, ``infosignature.R``,
``deconvolve.R`` and ``deconvolveterm.R``.

Consulting this code settles four things the two PDFs leave ambiguous.

1. **The cutoff constant is one bit, not 0.693.**  The paper writes "log(2)"
   throughout, which reads naturally as a natural logarithm.  The R source
   writes ``log2(2)``, that is ``1``.  This matters enormously: the deconvolution
   criterion is a threshold on a quantity measured in bits, and reading it in
   the wrong base makes Algorithm 2 appear self-contradictory when it is not.

2. **The default tolerance is ``epsilon = 1``**, a literal default argument of
   ``deconvolve_with_termination``, not a quantity estimated from the signature.
   With ``log2(2) = 1`` the published test ``|difference - log2(2)| > epsilon``
   reduces to ``difference > 2`` on a descending signature, which is a perfectly
   sensible rule.

3. **The BDM partition takes an ``offset``.**  ``bdm2D(mat, blockSize, offset)``
   supports overlapping decompositions, and the test case shipped in
   ``deconvolve.R`` uses ``offset = 1`` — a fully overlapping, stride-one
   partition — even though the paper's Methods say "no string/array overlapping
   in the decomposition".  Both are provided here.

4. **A cut removes one edge, not a class of edges.**  Algorithm 2's line 13 says
   "remove all candidate edges from G"; the R code deletes the single edge at
   the row just below the gap.

The CTM table shipped in ``data/K-4x4.csv`` was checked entry by entry against
``pybdm``'s ``CTM-B2-D4x4``: all 65 536 blocks agree to within 1e-6, so the two
implementations share an identical numerical backend.
"""

from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass

import networkx as nx
import numpy as np
from pybdm.encoding import normalize_key, string_from_array

from .complexity import _BDM_2D
from .graphs import adjacency

__all__ = [
    "LOG2_BITS",
    "EPSILON_DEFAULT",
    "bdm2d",
    "InfoSignature",
    "get_info_signature",
    "deconvolve",
    "deconvolve_with_termination",
]

#: ``log2(2)`` as written in ``deconvolveterm.R`` -- one bit.
LOG2_BITS = math.log2(2)

#: The default argument of ``deconvolve_with_termination(..., epsilon = 1)``.
EPSILON_DEFAULT = 1.0

_CTM_4x4 = _BDM_2D._ctm[(4, 4)]
_CTM_3x3 = _BDM_2D._ctm.get((3, 3), {})


def _ctm(block: np.ndarray) -> float:
    return _CTM_4x4[normalize_key(string_from_array(block))]


def bdm2d(mat: np.ndarray, block_size: int = 4, offset: int = 4) -> float:
    """Port of ``scripts/BDM2D.R``::

        ind <- function(matDim, blockSize, offset) {
            Map(`:`, seq(1, matDim-blockSize+1, by = offset),
                     seq(blockSize, matDim, by = offset))
        }
        bdm2D <- function(mat, blockSize, offset){
            parts <- myPartition(mat, blockSize, offset)
            squaresTally <- as.data.frame(table(unlist(lapply(parts, stringify))))
            bdm <- sum(fourByFourCTM[rownames(squaresTally), ]) + sum(log2(squaresTally$Freq))
        }

    ``offset == block_size`` gives the non-overlapping partition described in the
    paper's Methods and is numerically identical to
    :func:`~imp_causalnet_paper.complexity.bdm_2d`.  ``offset == 1`` gives the
    fully overlapping partition used by the repository's own test case.
    """
    if block_size != 4:
        raise NotImplementedError("only the 4x4 CTM table is ported here")
    M = np.asarray(mat, dtype=int)
    rows, cols = M.shape
    tally: Counter[str] = Counter()
    values: dict[str, float] = {}
    for r in range(0, rows - block_size + 1, offset):
        for c in range(0, cols - block_size + 1, offset):
            block = M[r : r + block_size, c : c + block_size]
            key = normalize_key(string_from_array(block))
            tally[key] += 1
            values[key] = _CTM_4x4[key]
    return sum(values[k] for k in tally) + sum(math.log2(n) for n in tally.values())


@dataclass
class InfoSignature:
    """Port of ``get_info_signature``: positive-loss edges, sorted descending."""

    edges: list[tuple[int, int]]
    information_loss: np.ndarray
    original_bdm: float

    def differences(self) -> np.ndarray:
        """``information_signature$information_loss[i] - ...[i+1]``."""
        return -np.diff(self.information_loss)


def get_info_signature(
    G: nx.Graph, block_size: int = 4, offset: int = 4
) -> InfoSignature:
    """Port of ``infosignature.R``.

    Note the R code filters to ``information_loss > 0`` and carries the authors'
    own comment on that line: ``# This condition must be revised``.
    """
    nodelist = sorted(G.nodes())
    index = {v: i for i, v in enumerate(nodelist)}
    A = adjacency(G, nodelist)
    base = bdm2d(A, block_size, offset)

    rows: list[tuple[tuple[int, int], float]] = []
    for u, v in G.edges():
        i, j = index[u], index[v]
        A[i, j] = A[j, i] = 0
        rows.append(((u, v), base - bdm2d(A, block_size, offset)))
        A[i, j] = A[j, i] = 1

    rows = [r for r in rows if r[1] > 0]
    rows.sort(key=lambda t: -t[1])
    return InfoSignature([e for e, _ in rows], np.array([v for _, v in rows]), base)


def deconvolve(
    G: nx.Graph,
    block_size: int = 4,
    offset: int = 4,
    desired_components: int = 1,
    max_rounds: int = 1000,
) -> nx.Graph:
    """Port of ``deconvolve.R`` -- Algorithm 1.

    Repeatedly removes every edge attaining the minimal *positive* information
    loss until the graph has at least ``desired_components`` components.
    """
    H = G.copy()
    for _ in range(max_rounds):
        if nx.number_connected_components(H) >= desired_components:
            break
        sig = get_info_signature(H, block_size, offset)
        if sig.information_loss.size == 0:
            break
        minimal = sig.information_loss.min()
        batch = [
            e
            for e, v in zip(sig.edges, sig.information_loss)
            if math.isclose(v, minimal, rel_tol=0, abs_tol=1e-12)
        ]
        H.remove_edges_from(batch)
    return H


def deconvolve_with_termination(
    G: nx.Graph,
    block_size: int = 4,
    offset: int = 4,
    epsilon: float = EPSILON_DEFAULT,
) -> tuple[nx.Graph, list[tuple[int, int]], InfoSignature]:
    """Port of ``deconvolveterm.R`` -- Algorithm 2::

        for(i in 1:length(information_differences)) {
            if(abs(information_differences[i]-log2(2)) > epsilon) {
              cutting_points <- c(cutting_points, i+1)
            }
        }

    Returns the deconvolved graph, the edges cut, and the signature.
    """
    sig = get_info_signature(G, block_size, offset)
    diffs = sig.differences()
    cuts = [i + 1 for i, d in enumerate(diffs) if abs(d - LOG2_BITS) > epsilon]
    removed = [sig.edges[c] for c in cuts]
    H = G.copy()
    H.remove_edges_from([e for e in removed if H.has_edge(*e)])
    return H, removed, sig
