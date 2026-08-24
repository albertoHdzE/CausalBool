"""Algorithms 1 and 2 of arXiv:1802.09904v8, transcribed from the pseudocode.

Definitions (Section 2.5).  For a graph ``G`` with edge set ``E(G)``, the
information contribution of an edge is

.. math:: I(G, e) := C(G) - C(G \\setminus e)

with ``C`` an estimator of algorithmic complexity -- BDM on the adjacency matrix
in the paper.  A positive contribution is an *information loss* on removal, a
negative contribution an *information gain*.

Algorithm 1 takes a target number of components ``N``.  Algorithm 2 replaces
``N`` by a cutoff ``epsilon`` around the theoretical value ``log(2)`` and is
therefore parameter-free in the paper's sense.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Callable, Sequence

import networkx as nx
import numpy as np

from .fastbdm import IncrementalBDM2D
from .graphs import adjacency

__all__ = [
    "LOG2",
    "EPSILON_DEFAULT",
    "EdgeInformation",
    "edge_information",
    "information_signature",
    "estimate_epsilon",
    "deconvolve_n",
    "deconvolve_epsilon",
    "breaking_points",
]

#: The theoretical cutoff of Section 2.5.1.  The paper writes ``log(2)``, which
#: reads naturally as a natural logarithm; the authors' own R implementation
#: (``deconvoLveterm.R``) writes ``log2(2)``, that is **1 bit**.  Since ``I(G,e)``
#: is a difference of BDM values and BDM is measured in bits, base 2 is the
#: correct reading, and it is the one used here.  See :mod:`official`.
LOG2 = 1.0

#: Default tolerance, taken from the R signature ``deconvolve_with_termination(
#: original_graph, block_size, offset, epsilon = 1)``.  With ``LOG2 = 1`` the
#: published test ``|difference - log2(2)| > epsilon`` reduces to
#: ``difference > 2`` on a descending signature.
EPSILON_DEFAULT = 1.0


@dataclass
class EdgeInformation:
    """``I(G, e)`` for every edge, plus the baseline complexity of ``G``."""

    edges: list[tuple[int, int]]
    values: np.ndarray
    base: float

    @property
    def sorted_desc(self) -> list[tuple[tuple[int, int], float]]:
        order = np.argsort(self.values, kind="stable")[::-1]
        return [(self.edges[i], float(self.values[i])) for i in order]

    @property
    def signature(self) -> np.ndarray:
        """The *information signature*: values sorted by maximum contribution."""
        return np.sort(self.values)[::-1]

    def as_dict(self) -> dict[tuple[int, int], float]:
        return {e: float(v) for e, v in zip(self.edges, self.values)}


def edge_information(
    G: nx.Graph,
    nodelist: Sequence | None = None,
    complexity: Callable[[np.ndarray], float] | None = None,
) -> EdgeInformation:
    """Compute ``I(G, e) = C(G) - C(G \\ e)`` for every edge of ``G``.

    With the default (BDM) estimator this uses the exact incremental update of
    :class:`~imp_causalnet_paper.fastbdm.IncrementalBDM2D`.  Any other callable
    accepting an adjacency matrix -- for instance the index-set description
    length of :mod:`imp_causalnet_paper.causalbool_mirror` -- can be substituted,
    which is how the "same algorithm, different index" comparisons are run.
    """
    if nodelist is None:
        nodelist = sorted(G.nodes())
    index = {v: i for i, v in enumerate(nodelist)}
    A = adjacency(G, nodelist)
    edges = [(u, v) for u, v in G.edges()]

    if complexity is None:
        inc = IncrementalBDM2D(A)
        base = inc.value
        values = np.array(
            [
                base - inc.value_after_flips(
                    [(index[u], index[v]), (index[v], index[u])]
                )
                for u, v in edges
            ]
        )
        return EdgeInformation(edges, values, base)

    base = complexity(A)
    values = np.empty(len(edges))
    for n, (u, v) in enumerate(edges):
        i, j = index[u], index[v]
        A[i, j] ^= 1
        A[j, i] ^= 1
        values[n] = base - complexity(A)
        A[i, j] ^= 1
        A[j, i] ^= 1
    return EdgeInformation(edges, values, base)


def information_signature(G: nx.Graph, **kwargs) -> np.ndarray:
    """Convenience wrapper returning only the descending list of values."""
    return edge_information(G, **kwargs).signature


# ---------------------------------------------------------------------------
# Algorithm 1
# ---------------------------------------------------------------------------


def deconvolve_n(
    G: nx.Graph,
    N: int,
    complexity: Callable[[np.ndarray], float] | None = None,
    max_rounds: int = 1000,
) -> tuple[nx.Graph, list[tuple[int, int]]]:
    """Algorithm 1: break ``G`` into at least ``N`` connected components.

    Transcribed from the published pseudocode::

        function Deconvolve(G, N), 1 <= k(G) <= N <= |V(G)|
            while k(G) < N do
                informationLoss <- {I(G, e) : e in E(G), I(G, e) > 0}
                minLoss <- min(informationLoss)
                G <- G \\ {e in E(G) : I(G, e) = minLoss}
            return G

    Note the algorithm removes *all* edges attaining the minimal positive
    contribution simultaneously; the paper is explicit that this is the only
    difference from the brute-force variant, and that both are ``O(M^2)``.
    """
    if not 1 <= nx.number_connected_components(G) <= N <= G.number_of_nodes():
        raise ValueError("Algorithm 1 requires 1 <= k(G) <= N <= |V(G)|")

    H = G.copy()
    removed: list[tuple[int, int]] = []
    for _ in range(max_rounds):
        if nx.number_connected_components(H) >= N:
            break
        if H.number_of_edges() == 0:
            break
        info = edge_information(H, complexity=complexity)
        positive = [(e, v) for e, v in zip(info.edges, info.values) if v > 0]
        if not positive:
            break
        min_loss = min(v for _, v in positive)
        batch = [e for e, v in positive if math.isclose(v, min_loss, rel_tol=0, abs_tol=1e-12)]
        H.remove_edges_from(batch)
        removed.extend(batch)
    return H, removed


# ---------------------------------------------------------------------------
# Algorithm 2
# ---------------------------------------------------------------------------


@dataclass
class EpsilonResult:
    graph: nx.Graph
    removed: list[tuple[int, int]] = field(default_factory=list)
    signature: np.ndarray = field(default_factory=lambda: np.array([]))
    gaps: np.ndarray = field(default_factory=lambda: np.array([]))
    cutoff: float = 0.0
    epsilon: float = 0.0

    @property
    def components(self) -> list[set]:
        return [set(c) for c in nx.connected_components(self.graph)]

    @property
    def n_components(self) -> int:
        return nx.number_connected_components(self.graph)


def estimate_epsilon(signature: np.ndarray) -> float:
    """Estimate ``epsilon`` from the information signature, per Section 2.5.1.

    "epsilon can be estimated from the sequential information differences
     calculated from the absolute distances between the differences of
     consecutive values in the information signature ... and its deviation from
     log(2)."

    Read literally: take the consecutive differences of the descending
    signature, measure how far each sits from ``log(2)``, and let ``epsilon`` be
    the typical (median absolute) such deviation.  The median is used rather
    than the mean so that the handful of large breaking peaks -- exactly the
    signal the criterion is meant to detect -- do not inflate their own
    tolerance.
    """
    sig = np.asarray(signature, dtype=float)
    if sig.size < 3:
        return 0.0
    gaps = -np.diff(sig)  # descending signature, so gaps are non-negative
    return float(np.median(np.abs(gaps - LOG2)))


def breaking_points(
    signature: np.ndarray,
    epsilon: float | None = None,
) -> tuple[np.ndarray, np.ndarray, float]:
    """Fig. 4C: the signature, the negated consecutive differences, and the cutoff.

    Returns ``(gaps, peak_indices, cutoff)`` where ``gaps[i] = signature[i] -
    signature[i+1]`` (the blue "line of the differences of consecutive values of
    the signature multiplied by -1") and ``peak_indices`` are the positions where
    a gap stands out above ``log(2) + epsilon`` (the orange rhombus line).
    """
    sig = np.asarray(signature, dtype=float)
    if epsilon is None:
        epsilon = EPSILON_DEFAULT
    gaps = -np.diff(sig)
    cutoff = LOG2 + epsilon
    peaks = np.flatnonzero(gaps > cutoff)
    return gaps, peaks, cutoff


def deconvolve_epsilon(
    G: nx.Graph,
    epsilon: float | None = None,
    complexity: Callable[[np.ndarray], float] | None = None,
    verbatim: bool = True,
) -> EpsilonResult:
    """Algorithm 2: parameter-free deconvolution with the ``log(2)`` criterion.

    Published pseudocode::

        function Deconvolve(G, eps)
            informationLoss <- {I(G, e) : e in E(G), I(G, e) > 0}
            for loss in informationLoss do
                difference <- 0
                if |informationLoss| > 1 then
                    maxLoss <- max(informationLoss)
                    informationLoss <- informationLoss \\ {maxLoss}
                    difference <- maxLoss - max(informationLoss)
                    if |difference - log(2)| > eps then
                        G <- G \\ {e in E(G) : I(G, e) = max(informationLoss)}
            return G

    The loop walks down the descending information signature one value at a
    time and cuts wherever the gap to the next value departs from ``log(2)``.
    All contributions are evaluated once against the original ``G``, which is
    what makes the algorithm ``O(M)`` as claimed in Section 2.5.2.

    Two readings of line 12 are provided.  Both are sensible **once the base of
    the logarithm is fixed correctly at 2** (see :data:`LOG2`); an earlier
    version of this replication read ``log(2)`` as a natural logarithm and
    concluded, wrongly, that the printed criterion was self-contradictory.

    ``verbatim=True`` (default)
        the printed test ``|difference - log2(2)| > epsilon``, which is exactly
        what the authors' R code implements.  With the default ``epsilon = 1``
        it reduces to ``difference > 2`` on a descending signature.
    ``verbatim=False``
        the criterion the running text states, "no cut is made for an edge with
        information difference below ``log(2) + epsilon``", i.e.
        ``difference > log2(2) + epsilon``.  With ``epsilon = 1`` this is the
        same threshold; the two readings only diverge for ``epsilon != 1``.

    For a literal port of the published R -- including its single-edge cut
    semantics -- use :func:`imp_causalnet_paper.official.deconvolve_with_termination`.
    """
    info = edge_information(G, complexity=complexity)
    positive = [(e, v) for e, v in zip(info.edges, info.values) if v > 0]
    positive.sort(key=lambda t: t[1], reverse=True)
    sig = np.array([v for _, v in positive])

    if epsilon is None:
        epsilon = EPSILON_DEFAULT
    cutoff = LOG2 + epsilon

    H = G.copy()
    removed: list[tuple[int, int]] = []
    for i in range(len(positive) - 1):
        difference = positive[i][1] - positive[i + 1][1]
        fires = (
            abs(difference - LOG2) > epsilon if verbatim else difference > cutoff
        )
        if fires:
            # "remove all candidate edges from G": every edge whose information
            # value equals the new maximum, i.e. the value just below the gap.
            target = positive[i + 1][1]
            batch = [
                e
                for e, v in positive
                if math.isclose(v, target, rel_tol=0, abs_tol=1e-12)
            ]
            H.remove_edges_from([e for e in batch if H.has_edge(*e)])
            removed.extend(batch)

    gaps, _, _ = breaking_points(sig, epsilon)
    return EpsilonResult(
        graph=H,
        removed=list(dict.fromkeys(removed)),
        signature=sig,
        gaps=gaps,
        cutoff=cutoff,
        epsilon=epsilon,
    )
