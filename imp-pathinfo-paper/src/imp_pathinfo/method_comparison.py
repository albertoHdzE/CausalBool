"""Experiments adjudicating BDM against the CausalBool index-set calculus.

Every claim made in the methodological discussion around this replication is
turned here into something runnable.  Nothing in this module asserts; each
function returns measurements, and the accompanying notebook
``notebooks/method_comparison.ipynb`` reports them for and against.

The experiments, in the order the notebook uses them:

``random_regime_scan``
    Does BDM still measure randomness once the object is random?  Or does it
    degenerate into a count of blocks?

``relabelling_spread``
    A graph has no canonical node numbering.  How much does BDM move when the
    numbering changes, and does the index-set description length move at all?

``adversarial_triple`` / ``same_degree_pairs`` / ``separation_benchmark``
    The index-set *wiring* term reads only the degree sequence.  Which measures
    can separate non-isomorphic graphs that share a degree sequence, and which
    of those measures are genuine isomorphism invariants?

``landscape_signature`` / ``knockout_profile``
    The repertoire layer: the exhaustive state-transition landscape of the
    Boolean network, and its response to perturbation.

``kraft_sum``
    Does the description length define a prefix code, and therefore induce an
    algorithmic probability ``2**-D`` over the model class?
"""

from __future__ import annotations

import itertools
import math
import sys
from collections import defaultdict
from pathlib import Path

import numpy as np

from .bdm_complexity import bdm_engine
from .causalbool_mirror import (GATE_LABELS, load_root_modules, node_description_cost,
                                path_surplus, receptive_saturation)

ROOT = Path(__file__).resolve().parents[3]


# ---------------------------------------------------------------------------
# small helpers: a bare graph object with the interface the mirror expects
# ---------------------------------------------------------------------------

class PlainGraph:
    """Minimal graph carrying the attributes the rest of the package reads."""

    def __init__(self, A: np.ndarray, smiles: str = 'synthetic'):
        A = np.asarray(A, dtype=np.int16)
        self._A = A
        self.n_nodes = A.shape[0]
        self.src, self.dst = np.nonzero(A)
        self.smiles = smiles

    def adjacency(self):
        return self._A

    def neighbours(self):
        nb = [[] for _ in range(self.n_nodes)]
        for u, v in zip(self.src, self.dst):
            nb[int(u)].append(int(v))
        return nb


def graph_from_edges(n: int, edges) -> PlainGraph:
    A = np.zeros((n, n), dtype=np.int16)
    for u, v in edges:
        A[u, v] = A[v, u] = 1
    return PlainGraph(A)


def degree_sequence(A) -> tuple:
    return tuple(sorted(np.asarray(A).sum(axis=1).tolist()))


def wiring_description_length(A) -> float:
    """``log2 n + sum_v log2 C(n, d_v)`` -- the index-set term, degrees only."""
    A = np.asarray(A)
    n = A.shape[0]
    deg = A.sum(axis=1)
    return math.log2(max(1, n)) + float(sum(math.log2(max(1, math.comb(n, int(d))))
                                            for d in deg))


# ---------------------------------------------------------------------------
# Claim: BDM degenerates to a size counter in the random regime
# ---------------------------------------------------------------------------

def random_regime_scan(sizes=(16, 32, 64, 128, 256), density=0.5, repeats=5, seed=0):
    """BDM of Erdos-Renyi graphs, reported per 4x4 block.

    If BDM were tracking randomness rather than extent, the per-block figure
    would vary with the object.  If it is constant, BDM is counting blocks.
    """
    engine = bdm_engine()
    rng = np.random.default_rng(seed)
    rows = []
    for n in sizes:
        vals = []
        for _ in range(repeats):
            A = (rng.random((n, n)) < density).astype(int)
            A = np.triu(A, 1)
            A = A + A.T
            vals.append(engine.bdm(A))
        blocks = (n // 4) ** 2
        rows.append(dict(n=n, blocks=blocks, bdm=float(np.mean(vals)),
                         bdm_std=float(np.std(vals)),
                         bdm_per_block=float(np.mean(vals)) / blocks,
                         wiring_D=wiring_description_length(A)))
    return rows


def structure_ladder(n=64, seed=0):
    """BDM and index-set cost along a ladder from perfect order to noise."""
    engine = bdm_engine()
    rng = np.random.default_rng(seed)
    out = []
    for p in [0.0, 0.02, 0.05, 0.1, 0.2, 0.3, 0.5]:
        # start from a clean band (a chain) and rewire a fraction of the entries
        A = np.zeros((n, n), dtype=int)
        for i in range(n - 1):
            A[i, i + 1] = A[i + 1, i] = 1
        mask = rng.random((n, n)) < p
        mask = np.triu(mask, 1)
        mask = mask + mask.T
        A = np.where(mask.astype(bool), 1 - A, A)
        np.fill_diagonal(A, 0)
        out.append(dict(noise=p, bdm=engine.bdm(A),
                        bdm_per_block=engine.bdm(A) / ((n // 4) ** 2),
                        wiring_D=wiring_description_length(A),
                        edges=int(A.sum() // 2)))
    return out


# ---------------------------------------------------------------------------
# Claim: BDM is not invariant to node labelling
# ---------------------------------------------------------------------------

def relabelling_spread(A, n_perm=500, seed=0):
    """Distribution of BDM over random relabellings of one graph."""
    engine = bdm_engine()
    A = np.asarray(A, dtype=int)
    n = A.shape[0]
    rng = np.random.default_rng(seed)
    vals = np.array([engine.bdm(A[np.ix_(p, p)])
                     for p in (rng.permutation(n) for _ in range(n_perm))])
    return dict(canonical=float(engine.bdm(A)), mean=float(vals.mean()),
                std=float(vals.std()), min=float(vals.min()), max=float(vals.max()),
                relative_spread=float((vals.max() - vals.min()) / vals.mean()),
                wiring_D=wiring_description_length(A), values=vals)


# ---------------------------------------------------------------------------
# The repertoire layer: exhaustive landscape and perturbation response
# ---------------------------------------------------------------------------

def transition_map(A, gate='XOR', knockout=None) -> np.ndarray:
    """The full state-transition function F over all 2**n states.

    Node ``k``'s next state is ``gate`` applied to its bonded neighbours, which
    is the CausalBool forward method with the connectivity matrix set to the
    graph's adjacency.  ``knockout`` clamps one node to zero, which is the
    perturbation used by :func:`knockout_profile`.
    """
    cb, _ = load_root_modules()
    A = np.asarray(A)
    n = A.shape[0]
    nb = [np.nonzero(A[k])[0].tolist() for k in range(n)]
    F = np.empty(2 ** n, dtype=np.int64)
    for x in range(2 ** n):
        v = [(x >> i) & 1 for i in range(n)]
        y = 0
        for k in range(n):
            if k == knockout:
                continue
            if cb.apply_gate(gate, [v[i] for i in nb[k]], {}):
                y |= (1 << k)
        F[x] = y
    return F


def landscape_signature(A, gate='XOR') -> tuple:
    """``(|Im F|, #attractors, attractor periods, basin sizes)``.

    Every component is an isomorphism invariant: relabelling the nodes permutes
    the state space but leaves image size, attractor count, period multiset and
    basin-size multiset untouched.
    """
    F = transition_map(A, gate)
    total = F.shape[0]
    colour = np.full(total, -1, dtype=np.int64)
    periods = []
    for s in range(total):
        path, x = [], s
        while colour[x] == -1 and x not in path:
            path.append(x)
            x = F[x]
        if colour[x] != -1:
            for p in path:
                colour[p] = colour[x]
        else:
            cycle = path[path.index(x):]
            aid = len(periods)
            periods.append(len(cycle))
            for p in path:
                colour[p] = aid
    basins = np.bincount(colour, minlength=len(periods))
    return (int(np.unique(F).size), len(periods), tuple(sorted(periods)),
            tuple(sorted(basins.tolist())))


def knockout_profile(A, gate='XOR') -> tuple:
    """Change in reachable-state count when each node in turn is clamped off.

    This is the index-set analogue of the perturbation step in algorithmic
    information dynamics: instead of measuring how an approximated complexity
    moves, it measures how the *exact* reachable behaviour of the system moves.
    Sorting makes the profile an invariant; the unsorted vector is the per-atom
    causal read-out.
    """
    base = int(np.unique(transition_map(A, gate)).size)
    n = np.asarray(A).shape[0]
    return tuple(sorted(base - int(np.unique(transition_map(A, gate, knockout=k)).size)
                        for k in range(n)))


def knockout_vector(A, gate='XOR') -> list:
    """Unsorted knockout deltas, node by node -- the interpretable version."""
    base = int(np.unique(transition_map(A, gate)).size)
    n = np.asarray(A).shape[0]
    return [base - int(np.unique(transition_map(A, gate, knockout=k)).size)
            for k in range(n)]


# ---------------------------------------------------------------------------
# The adjudicating experiment: graphs with identical degree sequences
# ---------------------------------------------------------------------------

def adversarial_triple(n=12):
    """Three non-isomorphic 2-regular graphs on ``n`` nodes.

    A single cycle, and two ways of splitting the same node budget into shorter
    disjoint cycles.  All have the same degree sequence, so the index-set wiring
    term is identical for all three by construction.
    """
    assert n % 12 == 0 or n == 12
    cycle = graph_from_edges(n, [(i, (i + 1) % n) for i in range(n)])
    squares = graph_from_edges(n, [(0, 1), (1, 2), (2, 3), (3, 0),
                                   (4, 5), (5, 6), (6, 7), (7, 4),
                                   (8, 9), (9, 10), (10, 11), (11, 8)])
    hexagons = graph_from_edges(n, [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 0),
                                    (6, 7), (7, 8), (8, 9), (9, 10), (10, 11), (11, 6)])
    return {'cycle C12': cycle, 'three squares': squares, 'two hexagons': hexagons}


def same_degree_pairs(datasets, min_atoms=6, max_atoms=13, max_pairs=250, seed=0):
    """Non-isomorphic pairs of real molecular graphs sharing a degree sequence.

    Molecules are bucketed by ``(n, sorted degrees)``; within a bucket, pairs are
    kept only when a full isomorphism test says the graphs genuinely differ.
    The size window keeps the exhaustive 2**n repertoire computable.
    """
    import networkx as nx

    buckets = defaultdict(list)
    seen = set()
    for dataset in datasets:
        for g in dataset.graphs:
            n = g.n_nodes
            if not (min_atoms <= n <= max_atoms):
                continue
            A = g.adjacency().astype(int)
            if A.sum() == 0:
                continue
            key = (n, degree_sequence(A))
            G = nx.from_numpy_array(A)
            cert = nx.weisfeiler_lehman_graph_hash(G, iterations=4)
            if (key, cert) in seen:
                continue
            seen.add((key, cert))
            buckets[key].append((g.smiles, A, G))

    pairs = []
    for _, members in buckets.items():
        for a, b in itertools.combinations(members, 2):
            if not nx.is_isomorphic(a[2], b[2]):
                pairs.append((a, b))
    rng = np.random.default_rng(seed)
    rng.shuffle(pairs)
    return pairs[:max_pairs]


# ---------------------------------------------------------------------------
# The query layer: shared inputs of a multi-node query
# ---------------------------------------------------------------------------

def query_overlap_profile(A, order: int = 2) -> tuple:
    """Multiset of ``|N(i_1) u ... u N(i_k)|`` over all ``k``-node queries.

    This is the method's own ``joinedNames`` quantity.  ``onPossibleBehaviour``
    answers a query about ``k`` nodes by enumerating the *union* of their index
    sets; everything outside that union is free and is folded into the sumandos.
    The size of that union therefore sets the entire cost and shape of the
    answer -- it is what the formal paper calls the shared-input reduction.

    At ``order = 1`` the union is just a neighbourhood, so the profile is the
    degree sequence and nothing more.  At ``order >= 2`` it measures how much
    neighbourhoods *overlap*, which is genuine topology: two graphs can share a
    degree sequence yet differ in how their neighbourhoods intersect.

    Sorting makes the profile an isomorphism invariant.  Cost is
    ``O(n^order * d)``.
    """
    A = np.asarray(A)
    n = A.shape[0]
    nb = [set(np.nonzero(A[i])[0].tolist()) for i in range(n)]
    return tuple(sorted(len(set().union(*[nb[i] for i in combo]))
                        for combo in itertools.combinations(range(n), order)))


def node_compressed_size(A) -> tuple:
    """Per-node compressed size: index-set width and one-set size.

    The naive reading of "the size of the compressed representation".  Included
    because it is instructive that it *fails*: for a fixed gate family it is a
    function of the degree sequence alone, so it separates nothing that the
    wiring term does not.
    """
    A = np.asarray(A)
    deg = A.sum(axis=1)
    return tuple(sorted((int(d), 2 ** int(d)) for d in deg))


#: Which measures the benchmark evaluates, and whether each is a graph invariant.
MEASURES = [
    ('index-set wiring D', True, 'degrees only'),
    ('node compressed size', True, 'degrees only, by another route'),
    ('BDM, canonical layout', False, 'reads the matrix as given'),
    ('BDM, mean over relabellings', True, 'averaged over the symmetric group'),
    ('path index sets', True, 'saturation and path surplus'),
    ('query overlap, order 2', True, 'shared inputs of 2-node queries'),
    ('query overlap, order 3', True, 'shared inputs of 3-node queries'),
    ('repertoire landscape, XOR', True, 'image, attractors, periods, basins'),
    ('repertoire landscape, AND', True, 'image, attractors, periods, basins'),
    ('knockout profile, XOR', True, 'perturbation response'),
    ('all index-set invariants', True, 'union of the invariant rows above'),
]


def separation_benchmark(pairs, n_perm=30, seed=0, max_len=3, progress=None):
    """For each measure, the fraction of same-degree pairs it tells apart."""
    engine = bdm_engine()
    rng = np.random.default_rng(seed)
    counts = {name: 0 for name, _, _ in MEASURES}

    for i, ((_, A1, _), (_, A2, _)) in enumerate(pairs):
        if progress and i % progress == 0:
            print(f'  pair {i}/{len(pairs)}', flush=True)
        n = A1.shape[0]

        wiring = abs(wiring_description_length(A1) - wiring_description_length(A2)) > 1e-9
        bdm_can = abs(engine.bdm(A1) - engine.bdm(A2)) > 1e-9
        m1 = np.mean([engine.bdm(A1[np.ix_(p, p)])
                      for p in (rng.permutation(n) for _ in range(n_perm))])
        m2 = np.mean([engine.bdm(A2[np.ix_(p, p)])
                      for p in (rng.permutation(n) for _ in range(n_perm))])
        bdm_avg = abs(m1 - m2) > 0.5

        g1, g2 = PlainGraph(A1), PlainGraph(A2)
        p1 = (round(receptive_saturation(g1, max_len), 9), round(path_surplus(g1, max_len), 9))
        p2 = (round(receptive_saturation(g2, max_len), 9), round(path_surplus(g2, max_len), 9))
        paths = p1 != p2

        ncs = node_compressed_size(A1) != node_compressed_size(A2)
        q2 = query_overlap_profile(A1, 2) != query_overlap_profile(A2, 2)
        q3 = query_overlap_profile(A1, 3) != query_overlap_profile(A2, 3)
        lx = landscape_signature(A1, 'XOR') != landscape_signature(A2, 'XOR')
        la = landscape_signature(A1, 'AND') != landscape_signature(A2, 'AND')
        ko = knockout_profile(A1, 'XOR') != knockout_profile(A2, 'XOR')

        for name, hit in [('index-set wiring D', wiring),
                          ('node compressed size', ncs),
                          ('BDM, canonical layout', bdm_can),
                          ('BDM, mean over relabellings', bdm_avg),
                          ('path index sets', paths),
                          ('query overlap, order 2', q2),
                          ('query overlap, order 3', q3),
                          ('repertoire landscape, XOR', lx),
                          ('repertoire landscape, AND', la),
                          ('knockout profile, XOR', ko),
                          ('all index-set invariants',
                           wiring or paths or q2 or q3 or lx or la or ko)]:
            counts[name] += bool(hit)

    return [dict(measure=name, invariant=inv, reads=reads,
                 separated=counts[name], pairs=len(pairs),
                 percent=100.0 * counts[name] / len(pairs))
            for name, inv, reads in MEASURES]


# ---------------------------------------------------------------------------
# Program length: the description length of a *recovered generating mechanism*
# ---------------------------------------------------------------------------

def program_description_length(net, arity_term: bool = True) -> dict:
    """Bits needed to write down a network, under two rival encodings.

    ``mechanism`` encoding
        name the index set and the gate: ``log2 C(n, d) + log2|G| + params``,
        which is the description length of ``BioMetrics.m`` (plus the arity term
        that Section 10 showed is needed for it to be a prefix code).

    ``set`` encoding
        name the index set, then list the one-set of the gate over it -- the
        ``(DecimalRepertoire, Sumandos)`` form.  ``Omega`` costs nothing beyond
        naming the free coordinates, because it is *generated* by them.

    The honest program length is the **minimum** of the two, node by node: a
    mechanism in the canonical family is cheap to name, and one outside it is
    cheaper to list.  The comparison against the raw repertoire, ``2**n * n``
    bits, is what makes this an algorithmic-complexity statement rather than a
    score.
    """
    cb, _ = load_root_modules()
    n = net.n
    per_node = []
    for k in range(n):
        ic = net.connected_inputs(k)
        d = len(ic)
        mech = node_description_cost(n, d, net.gates[k])
        if arity_term:
            mech += math.log2(n + 1)

        # the (L, Omega) form: name the index set, then list the satisfying
        # assignments of it; the free coordinates generate Omega for free.
        one_set = [x for x in range(2 ** d)
                   if cb.apply_gate(net.gates[k], [(x >> j) & 1 for j in range(d)],
                                    net.params[k])]
        as_set = (math.log2(max(1, math.comb(n, d)))       # which inputs
                  + math.log2(n + 1)                        # how many inputs
                  + math.log2(2 ** d + 1)                   # how many satisfy
                  + len(one_set) * d)                       # list them
        per_node.append(dict(node=k, degree=d, gate=net.gates[k],
                             mechanism_bits=mech, set_bits=as_set,
                             best=min(mech, as_set)))

    total = math.log2(max(1, n)) + sum(p['best'] for p in per_node)
    raw = (2 ** min(n, 60)) * n
    return dict(per_node=per_node, D_program=total, raw_repertoire_bits=float(raw),
                compression=float(raw) / total if total else float('nan'))


# ---------------------------------------------------------------------------
# Applying the calculus outside graphs: the space-time reading
# ---------------------------------------------------------------------------

def local_rule_explains(image, radius: int):
    """Is a binary array consistent with *some* deterministic local rule?

    The array is read as a space-time diagram on a ring: row ``t+1`` is produced
    from row ``t`` by a rule of the given radius.  Consistency is the exact
    index-set test -- the observed (neighbourhood, output) relation must be a
    function.  Returns ``(explains, n_distinct_neighbourhoods)``.
    """
    img = np.asarray(image, dtype=int)
    T, W = img.shape
    seen = {}
    for t in range(T - 1):
        for i in range(W):
            key = tuple(int(img[t, (i + d) % W]) for d in range(-radius, radius + 1))
            out = int(img[t + 1, i])
            if seen.setdefault(key, out) != out:
                return False, len(seen)
    return True, len(seen)


def is_trajectory(image) -> dict:
    """Could this array be produced by *any* deterministic synchronous network?

    A network is a function of the whole state, so the same row must always be
    followed by the same row.  If one row appears twice with different
    successors, no network -- of any connectivity, any gate family, any radius --
    can generate the array.  This is a proof about the object, not a failure of
    a search.

    The converse is weak and must be read carefully: if every row is distinct the
    condition holds vacuously, since any map on distinct inputs is a function.
    Such a "fit" is memorisation, and MDL rejects it.
    """
    img = np.asarray(image, dtype=int)
    seen = {}
    for t in range(len(img) - 1):
        key = tuple(img[t])
        if key in seen and seen[key] != tuple(img[t + 1]):
            return dict(possible=False, distinct_rows=len({tuple(r) for r in img}),
                        rows=len(img), reason=f'row repeats at t={t} with a different successor')
        seen[key] = tuple(img[t + 1])
    distinct = len({tuple(r) for r in img})
    vacuous = distinct == len(img)
    return dict(possible=True, distinct_rows=distinct, rows=len(img),
                reason=('vacuous: every row distinct, so any map is a function'
                        if vacuous else 'the row map is a genuine function'))


def eca_spacetime(rule: int, width: int = 41, steps: int = 21) -> np.ndarray:
    """Space-time diagram of an elementary cellular automaton, single-cell seed."""
    row = np.zeros(width, dtype=int)
    row[width // 2] = 1
    table = [(rule >> i) & 1 for i in range(8)]
    out = [row.copy()]
    for _ in range(steps - 1):
        row = np.array([table[4 * row[(i - 1) % width] + 2 * row[i] + row[(i + 1) % width]]
                        for i in range(width)])
        out.append(row)
    return np.array(out)


def recover_eca_rule(image) -> set:
    """Which elementary rules are consistent with every observed transition?

    The exact index-set consistency test at radius one: a rule survives only if
    it reproduces every transition in the diagram.  An empty result means the
    array is not a radius-1 evolution at all.
    """
    img = np.asarray(image, dtype=int)
    T, W = img.shape
    seen = {}
    for t in range(T - 1):
        for i in range(W):
            idx = 4 * img[t, (i - 1) % W] + 2 * img[t, i] + img[t, (i + 1) % W]
            if seen.setdefault(idx, img[t + 1, i]) != img[t + 1, i]:
                return set()
    return {r for r in range(256)
            if all(((r >> i) & 1) == o for i, o in seen.items())}


def mdl_local_program(image, max_radius: int = 5) -> dict:
    """Smallest local rule that generates the array, with an MDL stopping rule.

    A rule of radius ``r`` costs ``2**(2r+1)`` bits for its table plus ``W`` bits
    for the seed row.  If no radius up to ``max_radius`` explains the array, or
    if the cheapest one costs more than writing the array out verbatim, the
    method **refuses** -- which is the honest answer, and one BDM cannot give.
    """
    img = np.asarray(image, dtype=int)
    T, W = img.shape
    raw = T * W
    for r in range(1, max_radius + 1):
        ok, distinct = local_rule_explains(img, r)
        if ok:
            bits = 2 ** (2 * r + 1) + W
            return dict(radius=r, distinct_neighbourhoods=distinct, program_bits=bits,
                        raw_bits=raw, accepted=bits < raw,
                        verdict=('accepted' if bits < raw else 'refused: program exceeds the data'))
    return dict(radius=None, distinct_neighbourhoods=None, program_bits=None,
                raw_bits=raw, accepted=False,
                verdict=f'refused: no local rule up to radius {max_radius}')


# ---------------------------------------------------------------------------
# Does the description length define a code?
# ---------------------------------------------------------------------------

def kraft_sum(n: int, with_arity_term: bool) -> float:
    """Sum of ``2**-D`` over every single-node mechanism on ``n`` inputs.

    Kraft's inequality says a set of codeword lengths is realisable by a prefix
    code exactly when this sum is at most one, in which case ``2**-D`` is a
    genuine probability distribution over mechanisms -- an algorithmic
    probability defined by construction rather than estimated by sampling
    machines.  ``with_arity_term`` adds ``log2(n + 1)`` for stating the arity,
    which is the term the description length of ``BioMetrics.m`` leaves implicit.
    """
    total = 0.0
    for d in range(n + 1):
        n_index_sets = math.comb(n, d)
        for gate in GATE_LABELS:
            cost = node_description_cost(n, d, gate)
            if with_arity_term:
                cost += math.log2(n + 1)
            total += n_index_sets * 2 ** (-cost)
    return total


# ---------------------------------------------------------------------------
# Where BDM applies and the index-set calculus cannot be posed
# ---------------------------------------------------------------------------

def non_graph_objects(seed=0):
    """Binary objects that are not networks, to test domain generality."""
    rng = np.random.default_rng(seed)
    objects = {}

    bitmap = np.zeros((16, 16), dtype=int)
    bitmap[4:12, 4:12] = 1
    bitmap[6:10, 6:10] = 0
    objects['a bitmap (square annulus)'] = bitmap

    objects['a periodic texture'] = np.indices((16, 16)).sum(axis=0) % 2

    t = np.linspace(0, 8 * np.pi, 256)
    series = (np.sin(t) > 0).astype(int)
    objects['a binarised sine wave'] = series.reshape(16, 16)

    walk = np.cumsum(rng.normal(size=256))
    objects['a binarised random walk'] = (np.diff(walk, prepend=walk[0]) > 0).astype(int).reshape(16, 16)

    objects['uniform noise'] = rng.integers(0, 2, (16, 16))
    return objects
