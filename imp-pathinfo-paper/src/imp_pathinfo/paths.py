"""Path information: the T-Hop tensors, powered adjacencies and shortest paths.

Three kinds of path information are needed, one per model:

* **T-Hop** needs the tensor family :math:`T^L_{i,j,k} = B^L_{i,j,k}/(L+1)`,
  where :math:`B^L_{i,j,k}` counts the simple paths of length ``L`` from ``i``
  to ``j`` that pass through ``k`` (Equation 3 of the paper).  This is a direct
  port of the authors' DFS enumerator
  (``reference/.../t_hop/codes/build_beta_mat_3d.py``): a depth-first search
  from every source node that never revisits a node, incrementing
  ``beta[L-2][i, j, k] += 1/(L+1)`` for every node ``k`` on every enumerated
  path of length ``L >= 2``.
* **Mix-Hop** needs the symmetrically normalised adjacency of Equation 2.
* **Graphormer** needs, for every ordered pair of nodes, the shortest-path
  distance and the sequence of edges along one shortest path.

Sparse storage is used for the T tensors because they are extremely sparse
(a 136-atom molecule would otherwise need 2.5M entries per path length).
"""

from __future__ import annotations

from collections import deque

import numpy as np


def t_tensor_sparse(graph, pow_dim: int):
    """Simple-path tensors :math:`T^2, \\dots, T^{pow\\_dim+1}` for one graph.

    Returns ``(idx, val)`` where ``idx`` is an ``(nnz, 4)`` int32 array of
    ``(i, j, k, p)`` coordinates -- ``p = L - 2`` is the power index -- and
    ``val`` is the corresponding ``(nnz,)`` float32 array of accumulated
    ``1/(L+1)`` contributions.  ``pow_dim == 0`` gives an empty result, which is
    exactly how the authors switch path information off.
    """
    n = graph.n_nodes
    if pow_dim <= 0:
        return (np.zeros((0, 4), dtype=np.int32), np.zeros((0,), dtype=np.float32))

    nb = graph.neighbours()
    max_edges = pow_dim + 1          # authors' max_path_len = pow_dim + 1
    acc = {}
    visited = [False] * n
    path = []

    def dfs(u):
        visited[u] = True
        path.append(u)
        n_nodes_on_path = len(path)
        if n_nodes_on_path > 2:
            length = n_nodes_on_path - 1          # path length in edges
            p = length - 2                        # power index
            contrib = 1.0 / n_nodes_on_path       # 1/(L+1)
            i, j = path[0], path[-1]
            for k in path:
                key = (i, j, k, p)
                acc[key] = acc.get(key, 0.0) + contrib
        if n_nodes_on_path - 1 < max_edges:
            for w in nb[u]:
                if not visited[w]:
                    dfs(w)
        path.pop()
        visited[u] = False

    for s in range(n):
        dfs(s)

    if not acc:
        return (np.zeros((0, 4), dtype=np.int32), np.zeros((0,), dtype=np.float32))
    idx = np.asarray(list(acc.keys()), dtype=np.int32)
    val = np.asarray(list(acc.values()), dtype=np.float32)
    return idx, val


def densify_t(idx, val, n_pad: int, pow_dim: int) -> np.ndarray:
    """Expand a sparse T tensor onto a zero-padded ``(n_pad, n_pad, n_pad, pow_dim)`` grid."""
    out = np.zeros((n_pad, n_pad, n_pad, pow_dim), dtype=np.float32)
    if len(val):
        out[idx[:, 0], idx[:, 1], idx[:, 2], idx[:, 3]] = val
    return out


def simple_path_counts(graph, max_len: int) -> np.ndarray:
    """``A^L_{ij}`` counted over *simple* paths, for L = 1..max_len (Definition 1)."""
    n = graph.n_nodes
    nb = graph.neighbours()
    out = np.zeros((max_len, n, n), dtype=np.float64)
    visited = [False] * n
    path = []

    def dfs(u):
        visited[u] = True
        path.append(u)
        length = len(path) - 1
        if length >= 1:
            out[length - 1, path[0], path[-1]] += 1
        if length < max_len:
            for w in nb[u]:
                if not visited[w]:
                    dfs(w)
        path.pop()
        visited[u] = False

    for s in range(n):
        dfs(s)
    return out


def normalized_adjacency(graph, n_pad: int) -> np.ndarray:
    """Symmetric normalisation :math:`D^{-1/2}(A + I)D^{-1/2}` used by Mix-Hop.

    Port of the authors' ``utils.normalize_adj``: the identity is added on the
    full padded grid and degrees are the in-degrees of the unpadded graph plus
    one, so the padded rows contribute a unit diagonal.
    """
    a = np.zeros((n_pad, n_pad), dtype=np.float32)
    if len(graph.src):
        a[graph.src, graph.dst] = 1.0
    a = np.eye(n_pad, dtype=np.float32) + a

    deg = np.zeros((n_pad, 1), dtype=np.float32)
    if len(graph.dst):
        np.add.at(deg[:, 0], graph.dst, 1.0)
    deg = deg + 1.0
    deg = 1.0 / np.sqrt(deg)
    d = deg @ deg.T
    return d * a


def shortest_paths(graph):
    """BFS shortest-path distances and edge sequences, as ``dgl.shortest_dist``.

    Returns ``(dist, paths)``: ``dist`` is ``(n, n)`` with ``-1`` for
    unreachable pairs and ``0`` on the diagonal; ``paths`` is
    ``(n, n, max_len)`` holding the edge ids along one shortest path, padded
    with ``-1``.
    """
    n = graph.n_nodes
    edge_id = {}
    for e, (u, v) in enumerate(zip(graph.src, graph.dst)):
        edge_id[(int(u), int(v))] = e
    nb = graph.neighbours()

    dist = -np.ones((n, n), dtype=np.int64)
    pred = [[-1] * n for _ in range(n)]
    for s in range(n):
        dist[s, s] = 0
        q = deque([s])
        while q:
            u = q.popleft()
            for w in nb[u]:
                if dist[s, w] == -1:
                    dist[s, w] = dist[s, u] + 1
                    pred[s][w] = u
                    q.append(w)

    max_len = max(1, int(dist.max()))
    paths = -np.ones((n, n, max_len), dtype=np.int64)
    for s in range(n):
        for t in range(n):
            if s == t or dist[s, t] <= 0:
                continue
            seq, cur = [], t
            while cur != s:
                p = pred[s][cur]
                seq.append(edge_id[(p, cur)])
                cur = p
            seq.reverse()
            paths[s, t, :len(seq)] = seq
    return dist, paths
