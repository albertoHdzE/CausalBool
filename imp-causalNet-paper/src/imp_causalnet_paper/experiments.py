"""Replication runners for the numerical experiments of arXiv:1802.09904v8.

Covers Figs. 3C, 3D (twenty replicates each of two graph-mixing regimes) and
Fig. 5A (the robustness sweep, ten replicates per point), together with the
scoring the paper reports: precision at identifying the randomly connecting
links, the false-positive rate, and whether the two generating mechanisms end up
in separate connected components.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Callable, Iterable

import networkx as nx
import numpy as np

from .zenil_algorithms import deconvolve_epsilon
from .graphs import complete_graph, erdos_renyi, join_random, scale_free

__all__ = [
    "SeparationScore",
    "score_separation",
    "run_case",
    "figure3c",
    "figure3d",
    "_sf_er",
    "_complete_er",
    "fixed_size_sweep",
    "growing_size_sweep",
]


@dataclass
class SeparationScore:
    """How well one deconvolution recovered the planted structure."""

    n_flagged: int
    n_planted: int
    n_edges: int
    true_positives: int
    precision: float
    recall: float
    false_positive_rate: float
    n_components: int
    blocks_separated: bool
    largest_component_purity: float

    def as_dict(self) -> dict:
        return asdict(self)


def _canon(e) -> tuple:
    u, v = e
    return (u, v) if u <= v else (v, u)


def score_separation(
    G: nx.Graph,
    result,
    blocks: list[range],
    planted: Iterable[tuple[int, int]],
) -> SeparationScore:
    """Score flagged edges against the ground-truth inter-block links.

    ``false_positive_rate`` is normalised by the total number of edges, matching
    the paper's statement that "the number of false positives is constant at
    about 5%".
    """
    flagged = {_canon(e) for e in result.removed}
    planted_set = {_canon(e) for e in planted}
    tp = len(flagged & planted_set)
    n_edges = G.number_of_edges()

    components = [set(c) for c in nx.connected_components(result.graph)]
    block_sets = [set(b) for b in blocks]
    separated = False
    if len(block_sets) == 2:
        separated = any(
            c & block_sets[0] and not (c & block_sets[1]) for c in components
        ) and any(c & block_sets[1] and not (c & block_sets[0]) for c in components)

    if components:
        largest = max(components, key=len)
        purity = max(len(largest & b) for b in block_sets) / len(largest)
    else:
        purity = float("nan")

    return SeparationScore(
        n_flagged=len(flagged),
        n_planted=len(planted_set),
        n_edges=n_edges,
        true_positives=tp,
        precision=tp / len(flagged) if flagged else float("nan"),
        recall=tp / len(planted_set) if planted_set else float("nan"),
        false_positive_rate=(len(flagged) - tp) / n_edges if n_edges else float("nan"),
        n_components=len(components),
        blocks_separated=separated,
        largest_component_purity=purity,
    )


def run_case(
    left: nx.Graph,
    right: nx.Graph,
    n_links: int = 3,
    seed: int | None = None,
    epsilon: float | None = None,
    complexity: Callable[[np.ndarray], float] | None = None,
) -> tuple[nx.Graph, list[range], list[tuple[int, int]], object, SeparationScore]:
    """Compose two graphs, deconvolve with Algorithm 2, and score the outcome."""
    G, blocks, planted = join_random(left, right, n_links=n_links, seed=seed)
    result = deconvolve_epsilon(G, epsilon=epsilon, complexity=complexity)
    score = score_separation(G, result, blocks, planted)
    return G, blocks, planted, result, score


# ---------------------------------------------------------------------------
# Figure 3C / 3D
# ---------------------------------------------------------------------------


def figure3c(replicates: int = 20, seed0: int = 0, **kwargs) -> list[dict]:
    """Fig. 3C: ``K_20`` joined by 3 random edges to a scale-free graph of size 100.

    "Fig. 3C is a complete graph of size 20 randomly connected by 3 edges to a
     scale-free graph of size 100."
    """
    rows = []
    for r in range(replicates):
        seed = seed0 + r
        _, _, _, _, score = run_case(
            complete_graph(20), scale_free(100, k=2, seed=seed), n_links=3,
            seed=seed, **kwargs
        )
        rows.append({"replicate": r, **score.as_dict()})
    return rows


def figure3d(
    n: int = 60, replicates: int = 20, seed0: int = 100, **kwargs
) -> list[dict]:
    """Fig. 3D: an Erdos-Renyi graph at density 0.5 joined by 3 edges to a S-F graph.

    "instead of a complete graph an Erdos-Renyi (E-R) graph with edge density 0.5
     is produced and connected by 3 random edges to a scale-free network produced
     in the same fashion as in Fig. 3C."
    """
    rows = []
    for r in range(replicates):
        seed = seed0 + r
        _, _, _, _, score = run_case(
            erdos_renyi(n, 0.5, seed=seed), scale_free(n, k=2, seed=seed),
            n_links=3, seed=seed, **kwargs
        )
        rows.append({"replicate": r, **score.as_dict()})
    return rows


# ---------------------------------------------------------------------------
# Figure 5A
# ---------------------------------------------------------------------------


def _sf_er(n: int, seed: int) -> tuple[nx.Graph, nx.Graph]:
    """The paper's Fig. 5 pairing: scale-free structure against Erdos-Renyi noise."""
    return scale_free(n, k=2, seed=seed), erdos_renyi(n, 0.5, seed=seed)


def _complete_er(n: int, seed: int) -> tuple[nx.Graph, nx.Graph]:
    """The low-complexity pairing Section 3.3 says gives "the same results"."""
    return complete_graph(n), erdos_renyi(n, 0.5, seed=seed)


def fixed_size_sweep(
    n: int = 40,
    link_counts: Iterable[int] = tuple(range(1, 40, 3)),
    replicates: int = 10,
    seed0: int = 1000,
    pairing: Callable[[int, int], tuple[nx.Graph, nx.Graph]] = _sf_er,
    **kwargs,
) -> list[dict]:
    """Fig. 5A, blue circles: fixed-size subgraphs, growing number of random links.

    "increasing the number of random links only for graphs of fixed size (40
     nodes), when successful separation is compromised, noise (E-R) and
     structure (S-F) being indistinguishable ... a maximum precision of about
     0.9 is reached before degradation.  That is, at around 32.5% of the links
     randomly connecting the components."
    """
    rows = []
    for m in link_counts:
        for r in range(replicates):
            seed = seed0 + 1000 * m + r
            left, right = pairing(n, seed)
            G, _, _, _, score = run_case(
                left, right, n_links=int(m), seed=seed, **kwargs
            )
            rows.append(
                {
                    "n_links": int(m),
                    "replicate": r,
                    "link_fraction": m / G.number_of_edges(),
                    **score.as_dict(),
                }
            )
    return rows


def growing_size_sweep(
    sizes: Iterable[int] = (20, 40, 60, 80, 100, 120),
    links_per_node: float = 0.1,
    replicates: int = 10,
    seed0: int = 5000,
    pairing: Callable[[int, int], tuple[nx.Graph, nx.Graph]] = _sf_er,
    **kwargs,
) -> list[dict]:
    """Fig. 5A, red squares: the number of random links grows with subgraph size.

    "When the number of links increases as a function of the subgraph sizes, the
     separability is robust."
    """
    rows = []
    for n in sizes:
        m = max(1, int(round(links_per_node * n)))
        for r in range(replicates):
            seed = seed0 + 1000 * n + r
            left, right = pairing(n, seed)
            G, _, _, _, score = run_case(
                left, right, n_links=m, seed=seed, **kwargs
            )
            rows.append(
                {
                    "n": int(n),
                    "n_links": m,
                    "replicate": r,
                    "link_fraction": m / G.number_of_edges(),
                    **score.as_dict(),
                }
            )
    return rows
