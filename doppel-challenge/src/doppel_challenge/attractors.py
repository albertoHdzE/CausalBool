"""attractors -- attractor enumeration for synchronous Boolean networks.

The number of attractors and the attractor sizes are computed by the
``reprogramming`` module in the root.  This module wraps the call and
returns a JSON-friendly dict.
"""
from __future__ import annotations

from typing import Any

from .adapters import Network, step, input_vector
from .repertoire import transition_map


def _next_index(net: Network, x: int) -> int:
    """Decimal index of the next state of ``x`` under ``net``."""
    s = input_vector(x, net.n)
    ns = step(net, s)
    y = 0
    for i, b in enumerate(ns):
        if b:
            y |= 1 << i
    return y


def enumerate_attractors(net: Network) -> dict[str, Any]:
    """Return attractor count, attractor sizes, and the support.

    The support is the set of states on any attractor; this is the same
    as the support in ``compute_repertoire`` and is verified to match.
    """
    n = net.n
    N = 1 << n
    nxt = transition_map(net)
    colour = [0] * N  # 0 unvisited, 1 on current path, 2 finished
    attractors: list[list[int]] = []
    for start in range(N):
        if colour[start]:
            continue
        path: list[int] = []
        x = start
        while colour[x] == 0:
            colour[x] = 1
            path.append(x)
            x = nxt[x]
        if colour[x] == 1:  # new cycle closes here
            cyc: list[int] = []
            y = x
            while True:
                cyc.append(y)
                y = nxt[y]
                if y == x:
                    break
            attractors.append(sorted(cyc))
        for p in path:
            colour[p] = 2
    sizes = sorted(len(a) for a in attractors)
    # Independent callers can use this record without reconstructing the map.
    return {
        "n_attractors": len(attractors),
        "attractor_sizes": sizes,
        "support": sorted({s for a in attractors for s in a}),
        "attractor_cycles": attractors,
        "transition_map": nxt,
    }
