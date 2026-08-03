"""Graph generators matching Supplementary Information 4.2 of arXiv:1802.09904v8.

    "The graphs used throughout this paper were generated using the Wolfram
     Language ... using the function RandomGraph[] with uniform distribution
     (UniformGraphDistribution[]) for Erdos-Renyi graphs and a scale-free
     distribution (BarabasiAlbertGraphDistribution[]) for the scale-free
     networks constructed by starting from a cycle graph of size 3 and a vertex
     of k edges added at each step according to the preferential attachment
     algorithm ... All experiments were replicated 20 times."

The Barabasi-Albert construction is written out here rather than delegated to
``networkx.barabasi_albert_graph`` because the paper pins the seed graph to a
3-cycle, which ``networkx`` does not do by default.
"""

from __future__ import annotations

import numpy as np
import networkx as nx

__all__ = [
    "complete_graph",
    "star_graph",
    "erdos_renyi",
    "scale_free",
    "kary_tree",
    "join_random",
    "compose_disjoint",
    "adjacency",
]


def adjacency(G: nx.Graph, nodelist=None) -> np.ndarray:
    """Binary adjacency matrix with a deterministic node ordering."""
    if nodelist is None:
        nodelist = sorted(G.nodes())
    return nx.to_numpy_array(G, nodelist=nodelist, dtype=int).astype(int)


def complete_graph(n: int) -> nx.Graph:
    """``CompleteGraph[n]``.  Program length grows only as ``log n`` (Sec. 3.2)."""
    return nx.complete_graph(n)


def star_graph(n: int) -> nx.Graph:
    """``StarGraph[n]``: one hub and ``n - 1`` leaves."""
    return nx.star_graph(n - 1)


def erdos_renyi(n: int, p: float = 0.5, seed: int | None = None) -> nx.Graph:
    """``RandomGraph[UniformGraphDistribution[...]]`` -- G(n, p)."""
    return nx.gnp_random_graph(n, p, seed=seed)


def scale_free(n: int, k: int = 2, seed: int | None = None) -> nx.Graph:
    """Preferential attachment from a 3-cycle seed, ``k`` new links per node.

    This is ``BarabasiAlbertGraphDistribution[n, k]`` as described in Sup. Inf.
    4.2; Figs. 3C, 3D and 5 all use ``k = 2``.
    """
    if n < 3:
        raise ValueError("scale-free construction starts from a 3-cycle")
    rng = np.random.default_rng(seed)
    G = nx.cycle_graph(3)
    # repeated-node list realises attachment proportional to degree
    targets = [0, 1, 1, 2, 2, 0]
    for new in range(3, n):
        chosen: set[int] = set()
        while len(chosen) < min(k, new):
            chosen.add(int(targets[rng.integers(len(targets))]))
        for t in chosen:
            G.add_edge(new, t)
            targets.extend([new, t])
    return G


def kary_tree(n: int, k: int = 2) -> nx.Graph:
    """``KaryTree[n, k]``: the complete ``k``-ary tree on ``n`` vertices.

    Figs. 3A and 3B use ``n = 6`` and ``n = 10`` with the Wolfram default
    ``k = 2``.
    """
    G = nx.Graph()
    G.add_nodes_from(range(n))
    for child in range(1, n):
        G.add_edge((child - 1) // k, child)
    return G


def compose_disjoint(*graphs: nx.Graph) -> tuple[nx.Graph, list[range]]:
    """Relabel graphs onto disjoint consecutive integer blocks and union them."""
    G = nx.Graph()
    blocks: list[range] = []
    offset = 0
    for g in graphs:
        mapping = {v: i + offset for i, v in enumerate(sorted(g.nodes()))}
        G = nx.union(G, nx.relabel_nodes(g, mapping))
        blocks.append(range(offset, offset + g.number_of_nodes()))
        offset += g.number_of_nodes()
    return G, blocks


def join_random(
    *graphs: nx.Graph,
    n_links: int = 3,
    seed: int | None = None,
) -> tuple[nx.Graph, list[range], list[tuple[int, int]]]:
    """Connect disjoint graphs by ``n_links`` uniformly random inter-block edges.

    Returns the composite graph, the node blocks of each component, and the
    ground-truth list of connecting edges.  Fig. 3C uses ``n_links = 3`` between
    a complete graph of size 20 and a scale-free graph of size 100.
    """
    rng = np.random.default_rng(seed)
    G, blocks = compose_disjoint(*graphs)
    if len(blocks) < 2:
        return G, blocks, []
    added: list[tuple[int, int]] = []
    guard = 0
    while len(added) < n_links and guard < 10_000 * n_links:
        guard += 1
        a, b = rng.choice(len(blocks), size=2, replace=False)
        u = int(rng.choice(list(blocks[a])))
        v = int(rng.choice(list(blocks[b])))
        e = (min(u, v), max(u, v))
        if G.has_edge(*e):
            continue
        G.add_edge(*e)
        added.append(e)
    return G, blocks, added
