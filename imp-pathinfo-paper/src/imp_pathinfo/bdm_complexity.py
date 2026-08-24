"""Algorithmic complexity of molecular graphs via the Block Decomposition Method.

Section 2.2 of the paper: the adjacency matrix ``A`` of each molecular graph is
partitioned into non-overlapping ``d x d`` blocks, each block ``r_j`` is scored
with the Coding Theorem Method, and

    K_BDM(G, d) = sum over distinct blocks of  K_CTM(r_j) + log2(n_j),

with ``n_j`` the multiplicity of block ``r_j``.  The authors used the public
``pybdm`` implementation, whose two-dimensional CTM lookup table is built for
``d = 4`` from a very large run of 2-dimensional Turing machines; this module
calls exactly that library.

The dataset-level number reported in Table 4 -- what the paper calls the
*ascending order algorithmic complexity* (AOAC) -- is the mean of
``K_BDM(G, 4)`` over every molecular graph of the (noise-free) dataset.  Because
noise is added only to node and edge features and never to the bonds, all six
members of a dataset family share one AOAC value.
"""

from __future__ import annotations

import numpy as np
from pybdm import BDM

_BDM2D = None


def bdm_engine() -> BDM:
    """The 2-dimensional binary BDM engine (4x4 CTM blocks), created once."""
    global _BDM2D
    if _BDM2D is None:
        _BDM2D = BDM(ndim=2)
    return _BDM2D


def graph_bdm(graph, engine: BDM | None = None) -> float | None:
    """K_BDM of one molecular graph's adjacency matrix.

    Molecules with fewer than four atoms have no complete 4x4 block, so the
    ``PartitionIgnore`` scheme leaves nothing to score and ``pybdm`` refuses to
    return a value.  ``None`` is returned for those graphs; they are left out of
    the dataset average, which is what reproduces the published AOAC numbers.
    """
    engine = engine or bdm_engine()
    adj = graph.adjacency().astype(int)
    try:
        return float(engine.bdm(adj))
    except ValueError:
        return None


def dataset_aoac(dataset, engine: BDM | None = None):
    """Per-graph BDM values, the dataset family's AOAC, and the skipped count."""
    engine = engine or bdm_engine()
    scored = [graph_bdm(g, engine) for g in dataset.graphs]
    values = np.asarray([v for v in scored if v is not None], dtype=np.float64)
    n_skipped = sum(v is None for v in scored)
    return values, float(values.mean()), n_skipped


def graph_entropy(graph) -> float:
    """Shannon block entropy of the adjacency matrix, for contrast with BDM."""
    engine = bdm_engine()
    return float(engine.ent(graph.adjacency().astype(int)))
