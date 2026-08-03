"""Mirror of the paper's results using the CausalBool index-set calculus.

The replication in the sibling modules is faithful to Zenil, Kiani, Zea and
Tegner: it estimates algorithmic complexity with BDM and reads causality off the
*magnitude* of a perturbation's effect on that estimate.  That is an
approximation-first, statistics-free but still numerical answer.

This module answers the same questions with the machinery developed in the root
of the CausalBool project: deterministic index sets and exact generating
mechanisms.  Where the paper's algorithm returns a real-valued footprint that
*suggests* a partition, the index-set method returns, for every cell, the
smallest set of inputs and the exact Boolean gate that reproduces the
observations -- or a proof that no such mechanism exists, which is itself the
boundary signal.

Two mirrors are provided.

Cellular automata
    :func:`local_mechanism_map` and :func:`column_mechanisms`.  For each cell of
    an interacting space-time diagram, recover the local rule from the observed
    transitions alone.  A cell whose observations are consistent with exactly
    one elementary rule is attributed to that generating mechanism; a cell whose
    observations are consistent with neither is on the interaction boundary.
    This yields a hard, exact segmentation to compare against the paper's soft
    BDM footprint, scored against the ground-truth ownership mask.

Graphs
    :func:`index_set_description_length`.  A deterministic, closed-form
    substitute for BDM as the complexity index ``C`` inside Algorithms 1 and 2.
    It reproduces the paper's own stated ordering of graph complexities
    (Section 3.2: a complete graph costs ``~log N``, a scale-free graph
    ``log N + c``, a dense random graph much more) without any empirical
    distribution, look-up table or approximation.
"""

from __future__ import annotations

import math
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

__all__ = [
    "ROOT",
    "load_root_modules",
    "eca_local_table",
    "consistent_rules",
    "local_mechanism_map",
    "column_mechanisms",
    "index_set_description_length",
    "index_set_complexity",
]

#: Root of the CausalBool project, whose ``index-deconvolution`` package holds
#: the reference index-set deconvolution implementation.
ROOT = Path(__file__).resolve().parents[3]


def load_root_modules():
    """Import the root project's index-set deconvolution code.

    Returns ``(causalbool, deconvolution, ca_deconvolution)``.  These modules use
    flat intra-package imports, so their directory is placed on ``sys.path``
    rather than being imported as a package.
    """
    src = ROOT / "index-deconvolution" / "src"
    if not src.is_dir():
        raise FileNotFoundError(
            f"expected the root index-deconvolution sources at {src}"
        )
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import causalbool  # type: ignore
    import deconvolution  # type: ignore
    import ca_deconvolution  # type: ignore

    return causalbool, deconvolution, ca_deconvolution


# ---------------------------------------------------------------------------
# Cellular automata: exact local mechanism recovery
# ---------------------------------------------------------------------------


@lru_cache(maxsize=None)
def eca_local_table(rule: int) -> tuple[int, ...]:
    """Truth table of an elementary rule indexed by ``4*l + 2*c + r``."""
    return tuple((rule >> i) & 1 for i in range(8))


def consistent_rules(samples: list[tuple[int, int]]) -> frozenset[int]:
    """All elementary rules consistent with ``(neighbourhood_index, output)`` samples.

    This is the index-set consistency test at radius one: a rule survives iff it
    reproduces every observed transition exactly.  No tolerance, no threshold.
    """
    constraints: dict[int, int] = {}
    for idx, out in samples:
        if constraints.setdefault(idx, out) != out:
            return frozenset()  # the cell is not a function of its 3-neighbourhood
    survivors = []
    for rule in range(256):
        table = eca_local_table(rule)
        if all(table[i] == o for i, o in constraints.items()):
            survivors.append(rule)
    return frozenset(survivors)


@dataclass
class MechanismMap:
    """Exact per-cell attribution of an interacting space-time diagram.

    ``labels`` uses ``-1`` for the left rule, ``+1`` for the right rule, ``0``
    when the observations are consistent with both (undetermined, typically a
    quiescent region) and ``2`` when they are consistent with neither, which
    identifies the interaction boundary.
    """

    labels: np.ndarray
    survivors: list[frozenset[int]]
    rule_left: int
    rule_right: int

    @property
    def boundary(self) -> np.ndarray:
        return self.labels == 2

    def accuracy_against(self, owner: np.ndarray) -> dict:
        """Score the attributed cells against the ground-truth ownership mask.

        ``owner`` must be broadcastable to ``labels``: a full ownership array for
        the per-pixel map, or a single row for the per-column map.
        """
        truth = np.sign(np.asarray(owner))
        if truth.shape != self.labels.shape:
            if truth.ndim == 2 and self.labels.ndim == 2:
                truth = truth[: self.labels.shape[0], : self.labels.shape[1]]
            elif truth.ndim == 2 and self.labels.ndim == 1:
                truth = truth[-1]
            truth = np.broadcast_to(truth, self.labels.shape)
        decided = np.isin(self.labels, (-1, 1))
        agree = int(np.sum(self.labels[decided] == truth[decided]))
        total = int(np.sum(decided))
        return {
            "cells_decided": total,
            "cells_total": int(self.labels.size),
            "accuracy_on_decided": agree / total if total else float("nan"),
            "boundary_cells": int(np.sum(self.boundary)),
            "undetermined_cells": int(np.sum(self.labels == 0)),
        }


def _column_samples(observed: np.ndarray, cell: int) -> list[tuple[int, int]]:
    steps, w = observed.shape
    out = []
    for t in range(steps - 1):
        l = observed[t, (cell - 1) % w]
        c = observed[t, cell]
        r = observed[t, (cell + 1) % w]
        out.append((int(4 * l + 2 * c + r), int(observed[t + 1, cell])))
    return out


def column_mechanisms(
    observed: np.ndarray | list[np.ndarray],
    rule_left: int,
    rule_right: int,
) -> MechanismMap:
    """Recover, per column, which elementary rule generated it.

    ``observed`` is the binary space-time diagram (or an ensemble of diagrams
    from independent initial conditions, pooled).  Nothing but the binary image
    is consumed: the colours that distinguish the two automata are not visible
    to this function, exactly as in the paper's Fig. 2C observer view.
    """
    diagrams = [np.asarray(observed)] if np.ndim(observed) == 2 else [
        np.asarray(d) for d in observed
    ]
    w = diagrams[0].shape[1]
    labels = np.zeros(w, dtype=int)
    survivors: list[frozenset[int]] = []
    for cell in range(w):
        samples: list[tuple[int, int]] = []
        for d in diagrams:
            samples.extend(_column_samples(d, cell))
        surv = consistent_rules(samples)
        survivors.append(surv)
        left_ok, right_ok = rule_left in surv, rule_right in surv
        if left_ok and not right_ok:
            labels[cell] = -1
        elif right_ok and not left_ok:
            labels[cell] = 1
        elif left_ok and right_ok:
            labels[cell] = 0
        else:
            labels[cell] = 2
    return MechanismMap(labels, survivors, rule_left, rule_right)


def local_mechanism_map(
    observed: np.ndarray,
    rule_left: int,
    rule_right: int,
) -> MechanismMap:
    """Per-*pixel* mechanism attribution of a single space-time diagram.

    For every cell and every time step, check the single observed transition
    against both candidate rules.  The result is directly comparable, pixel for
    pixel, with the paper's BDM footprint of Figs. 2D-E -- but it is a decision
    rather than a score, and it is exact.
    """
    obs = np.asarray(observed, dtype=int)
    steps, w = obs.shape
    tl, tr = eca_local_table(rule_left), eca_local_table(rule_right)
    labels = np.zeros((steps - 1, w), dtype=int)
    for t in range(steps - 1):
        for i in range(w):
            idx = 4 * obs[t, (i - 1) % w] + 2 * obs[t, i] + obs[t, (i + 1) % w]
            nxt = obs[t + 1, i]
            left_ok, right_ok = tl[idx] == nxt, tr[idx] == nxt
            if left_ok and not right_ok:
                labels[t, i] = -1
            elif right_ok and not left_ok:
                labels[t, i] = 1
            elif left_ok and right_ok:
                labels[t, i] = 0
            else:
                labels[t, i] = 2
    return MechanismMap(labels, [], rule_left, rule_right)


# ---------------------------------------------------------------------------
# Graphs: index-set description length as a drop-in for BDM
# ---------------------------------------------------------------------------


def _runs(bits: np.ndarray) -> int:
    """Number of maximal constant runs in a binary vector."""
    if bits.size == 0:
        return 0
    return 1 + int(np.count_nonzero(bits[1:] != bits[:-1]))


def _row_cost(bits: np.ndarray, unit: float) -> float:
    """Exact index-set description length of one neighbourhood indicator vector.

    The index algebra of the CausalBool core gives a small family of closed
    forms for a set ``C`` over ``n`` positions.  Each costs ``unit = log2(n + 1)``
    bits per stated boundary:

    ``full`` / ``empty``
        one symbol.  A node joined to everything, or to nothing.
    ``band`` / ``complement of a band``
        two boundaries.  A contiguous index range, the form the complete graph
        and the star graph both take.
    ``general``
        one boundary per run of the indicator vector -- the run-length encoding
        that the index algebra falls back on when no closed form applies.

    The cost of a set is the minimum over the family, which is what makes this a
    genuine description length rather than a heuristic score.
    """
    r = _runs(bits)
    if r <= 1:
        return unit  # constant row: full or empty
    if r <= 3:
        # a single contiguous band, or the complement of one
        return 2 * unit
    return r * unit


def index_set_description_length(A: np.ndarray) -> float:
    """Deterministic description length of a graph from its index sets.

    Each node ``v`` is described by the index set of its neighbours; the graph is
    described by the concatenation of those descriptions plus ``log2 n`` for the
    node count itself.  No empirical distribution and no approximation is
    involved: for a given adjacency matrix the value is exact and closed-form.

    Sanity against the paper's own claims (Section 3.2): a complete graph
    ``K_n`` has every row a band-complement, giving ``O(n log n)`` total and the
    smallest per-node cost; an Erdos-Renyi graph at density 0.5 has ``~n/2`` runs
    per row and is the most expensive; a scale-free graph sits between the two.
    """
    M = np.asarray(A, dtype=int)
    n = M.shape[0]
    if n == 0:
        return 0.0
    unit = math.log2(n + 1)
    return math.log2(n + 1) + float(sum(_row_cost(M[v], unit) for v in range(n)))


def index_set_complexity(A: np.ndarray) -> float:
    """Alias with the signature Algorithms 1 and 2 expect for ``complexity``."""
    return index_set_description_length(A)
