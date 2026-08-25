"""reprogramming.py

Exact network reprogramming, the deterministic counterpart of the
algorithmic-information reprogramming of Zenil and colleagues.

Zenil's team perturbs a network and measures the change in the approximate
algorithmic complexity (BDM) of its adjacency matrix, ranking nodes by that
information value.  Here we perturb a node (a gene knockout) and measure the
exact change in the dynamics of the Boolean network: the size of the image (the
number of reachable next-states) and the number of attractors.  Because the
CausalBool method gives the exact behaviour, the information value is exact, not
an estimate.

A node's information value is measure(full) - measure(knockout).  A positive
value means the node expands the dynamics (its removal makes the system more
convergent, moving it towards order); a negative value means the opposite.  The
relative reprogrammability is the normalised imbalance of positive and negative
nodes, in the spirit of the reprogrammability index Pr.
"""

from __future__ import annotations

from causalbool import Network, step, input_vector


def _next_index(net: Network, x: int) -> int:
    s = input_vector(x, net.n)
    ns = step(net, s)
    y = 0
    for i in range(net.n):
        if ns[i]:
            y |= (1 << i)
    return y


def image_size(net: Network) -> int:
    """Number of distinct reachable next-states (size of the image of F)."""
    return len({_next_index(net, x) for x in range(2 ** net.n)})


def num_attractors(net: Network) -> int:
    """Number of attractors (cycles) of the synchronous update map."""
    n = net.n
    N = 2 ** n
    nxt = [_next_index(net, x) for x in range(N)]
    colour = [0] * N  # 0 unvisited, 1 on current path, 2 finished
    attractors = set()
    for start in range(N):
        if colour[start]:
            continue
        path = []
        x = start
        while colour[x] == 0:
            colour[x] = 1
            path.append(x)
            x = nxt[x]
        if colour[x] == 1:  # a new cycle closes here
            cyc = []
            y = x
            while True:
                cyc.append(y)
                y = nxt[y]
                if y == x:
                    break
            attractors.add(frozenset(cyc))
        for p in path:
            colour[p] = 2
    return len(attractors)


def knockout(net: Network, node: int, value: int = 0) -> Network:
    """Fix ``node`` to a constant value (a knockout at 0 or over-expression at 1)."""
    C = [row[:] for row in net.C]
    gates = list(net.gates)
    params = [dict(p) for p in net.params]
    C[node] = [0] * net.n
    gates[node] = "TRUE" if value == 1 else "FALSE"
    params[node] = {}
    return Network(n=net.n, C=C, gates=gates, params=params)


def spectrum(net: Network, measure=image_size) -> list[float]:
    """Exact information value of every node under knockout."""
    base = measure(net)
    return [base - measure(knockout(net, i)) for i in range(net.n)]


def relative_reprogrammability(info: list[float]) -> float:
    """Normalised imbalance of positive and negative information nodes."""
    pos = sum(1 for v in info if v > 0)
    neg = sum(1 for v in info if v < 0)
    return abs(pos - neg) / len(info) if info else 0.0
