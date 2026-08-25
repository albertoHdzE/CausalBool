"""Mirror of the paper's results using the CausalBool index-set calculus.

The replication in the sibling modules is faithful to the paper: it estimates
algorithmic complexity with BDM, a look-up-table approximation built from a very
large run of two-dimensional Turing machines, and reads structure off the
resulting real number.

This module answers the same question with the machinery developed in the root
of the CausalBool project: **deterministic index sets and exact generating
mechanisms**.  Where BDM returns an approximation whose value depends on a
pre-computed empirical distribution, the index-set calculus returns a
closed-form description length, and -- more importantly -- returns it for
*index sets that have been recovered from observed behaviour* rather than
assumed.

Three mirrors are provided.

Causal modelling and deconvolution
    :func:`molecular_network` turns a molecule into a synchronous Boolean
    network whose connectivity matrix is the bond adjacency and whose per-atom
    gate is fixed by that atom's chemistry.  :func:`deconvolve_molecule` then
    throws the network away and recovers, from observed transitions alone, each
    atom's index set and gate.  This certifies that the index sets the
    complexity measures below are computed on are the causally correct ones.

    The full output repertoire of an *n*-atom molecule has 2**n rows, which is
    hopeless for a 136-atom molecule.  The index-set factorisation is what makes
    this tractable: node ``k``'s output column depends only on its connected
    inputs, so the problem decomposes into one local problem per atom, of size
    ``2**(degree + decoys)``.  Chemistry bounds atomic degree at four, so every
    molecule in every one of the six datasets is analysed at a cost of a few
    hundred rows per atom.

Description length as a substitute for BDM
    :func:`graph_description_length` implements the canonical CausalBool
    description length of ``src/Packages/Integration/BioMetrics.m``: per node,
    ``log2(#gates) + log2(C(n, d)) + parameter cost``.  The wiring term
    ``log2 C(n, d)`` is exactly the cost of naming an index set, it is
    order-invariant, and it is exact.

Path information from the index algebra
    :func:`path_index_sets` lifts the same encoding to the *L*-hop index sets --
    the sets of atoms reachable by a simple path of length exactly ``L`` -- and
    :func:`receptive_saturation` measures what fraction of a molecule a
    path-length-bounded model actually sees.  This is the quantity the paper is
    circling around, computed exactly and without training anything.
"""

from __future__ import annotations

import itertools
import math
import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[3]

#: Gate label vocabulary of the canonical CausalBool family (Gates.m).
GATE_LABELS = ('AND', 'OR', 'XOR', 'NAND', 'NOR', 'XNOR',
               'NOT', 'IMPLIES', 'NIMPLIES', 'MAJORITY', 'KOFN', 'CANALISING')

#: Elements treated as heteroatoms when assigning canalising gates.
HETEROATOMS = frozenset({'N', 'O', 'S', 'P', 'F', 'Cl', 'Br', 'I'})


def load_root_modules():
    """Import the root project's index-set forward and deconvolution code.

    Returns ``(causalbool, deconvolution)``.  Those modules use flat intra-package
    imports, so their directory goes on ``sys.path`` rather than being imported
    as a package -- the same arrangement the sibling replications use.
    """
    src = ROOT / 'index-deconvolution' / 'src'
    if not src.is_dir():
        raise FileNotFoundError(f'expected the root index-set sources at {src}')
    if str(src) not in sys.path:
        sys.path.insert(0, str(src))
    import causalbool                                            # noqa: E402
    import deconvolution                                         # noqa: E402
    return causalbool, deconvolution


# ---------------------------------------------------------------------------
# Causal modelling: a molecule as a synchronous Boolean network
# ---------------------------------------------------------------------------

def atom_gate(symbol: str, degree: int, aromatic: bool, neighbour_symbols: list[str]):
    """Assign a canonical gate to one atom from its chemistry.

    The assignment is deterministic and chemically motivated, and it exercises
    four distinct members of the gate family:

    ``NOT``
        a terminal atom, whose state is fixed by its single bonded partner;
    ``XOR``
        an aromatic atom, whose parity-like response models a delocalised ring;
    ``CANALISING``
        an atom bonded to a heteroatom, which dominates the atom's behaviour --
        the canonical form of a dominant regulator;
    ``MAJORITY``
        everything else, a threshold response to its bonded neighbours.

    The particular assignment is a modelling choice.  What matters for the
    mirror is that whatever mechanism is written down must then be *recovered*
    from behaviour alone by the deconvolution, with no knowledge of this rule.
    """
    if degree == 0:
        return 'FALSE', {}
    if degree == 1:
        return 'NOT', {}
    if aromatic:
        return 'XOR', {}
    hetero = [j for j, s in enumerate(neighbour_symbols) if s in HETEROATOMS]
    if hetero:
        return 'CANALISING', {'canalisingIndex': hetero[0],
                              'canalisingValue': 1, 'canalisedOutput': 1}
    return 'MAJORITY', {}


@dataclass
class MolecularNetwork:
    """A molecule expressed in the CausalBool network formalism."""

    n: int
    neighbours: list           # neighbours[k] = ascending index set I_c of atom k
    gates: list
    params: list
    symbols: list

    def local_column(self, k: int, universe: list) -> list:
        """Output column of atom ``k`` over all states of a local universe.

        ``universe`` is an ascending list of atom indices; the returned column
        has ``2**len(universe)`` entries, enumerated LSB-first, exactly as the
        root ``causalbool.repertoire`` enumerates a full repertoire.  Atoms of
        the universe that do not feed ``k`` are the offset dimension: the column
        is constant along them, which is precisely what the deconvolution's
        essential-variable test detects.
        """
        cb, _ = load_root_modules()
        pos = {a: i for i, a in enumerate(universe)}
        ic_local = [pos[a] for a in self.neighbours[k]]
        m = len(universe)
        col = []
        for x in range(2 ** m):
            v = [(x >> i) & 1 for i in range(m)]
            sub = [v[i] for i in ic_local]
            col.append(cb.apply_gate(self.gates[k], sub, self.params[k]))
        return col


def molecular_network(graph, symbols: list | None = None) -> MolecularNetwork:
    """Build the Boolean network of a molecular graph: connectivity ``C = A``."""
    from rdkit import Chem

    n = graph.n_nodes
    nb = [sorted(set(int(v) for u, v in zip(graph.src, graph.dst) if int(u) == k))
          for k in range(n)]

    if symbols is None:
        mol = Chem.MolFromSmiles(graph.smiles)
        if mol is not None:
            from rdkit.Chem import rdmolfiles, rdmolops
            mol = rdmolops.RenumberAtoms(mol, list(rdmolfiles.CanonicalRankAtoms(mol)))
            symbols = [a.GetSymbol() for a in mol.GetAtoms()]
            aromatic = [a.GetIsAromatic() for a in mol.GetAtoms()]
        else:
            symbols, aromatic = ['C'] * n, [False] * n
    else:
        aromatic = [False] * n

    gates, params = [], []
    for k in range(n):
        g, p = atom_gate(symbols[k], len(nb[k]), aromatic[k],
                         [symbols[j] for j in nb[k]])
        gates.append(g)
        params.append(p)
    return MolecularNetwork(n, nb, gates, params, symbols)


@dataclass
class DeconvolutionReport:
    """Outcome of recovering a molecule's mechanisms from observed behaviour."""

    n_atoms: int
    n_recovered_exactly: int      # index set recovered == true bonded neighbours
    n_index_subset: int           # recovered index set a strict subset (inert input)
    n_gate_matched: int           # a canonical gate reproducing the column was found
    max_local_rows: int           # largest local repertoire actually enumerated
    full_repertoire_rows: float   # 2**n, the cost the factorisation avoids

    @property
    def exact_fraction(self) -> float:
        return self.n_recovered_exactly / self.n_atoms if self.n_atoms else float('nan')


def deconvolve_molecule(graph, n_decoys: int = 3, rng_seed: int = 0) -> DeconvolutionReport:
    """Recover every atom's index set and gate from observed transitions alone.

    For each atom a local universe is formed from its bonded neighbours plus
    ``n_decoys`` non-neighbours drawn deterministically.  The decoys are the
    test: a correct deconvolution must return the neighbours as essential and
    reject the decoys, i.e. separate pivots from the offset dimension.
    """
    _, dc = load_root_modules()
    net = molecular_network(graph)
    rng = np.random.default_rng(rng_seed)

    exact = subset = gate_ok = 0
    max_rows = 0
    for k in range(net.n):
        true_ic = net.neighbours[k]
        if not true_ic:
            continue
        others = [a for a in range(net.n) if a != k and a not in true_ic]
        decoys = list(rng.choice(others, size=min(n_decoys, len(others)), replace=False)) \
            if others else []
        universe = sorted(set(true_ic) | {int(d) for d in decoys})
        col = net.local_column(k, universe)
        max_rows = max(max_rows, len(col))

        rec = dc.deconvolve_column(col, len(universe), k)
        recovered = sorted(universe[i] for i in rec.connected_inputs)
        if recovered == list(true_ic):
            exact += 1
        elif set(recovered) <= set(true_ic):
            subset += 1
        if rec.canonical is not None:
            gate_ok += 1

    n_active = sum(1 for k in range(net.n) if net.neighbours[k])
    return DeconvolutionReport(n_active, exact, subset, gate_ok, max_rows,
                               float(2 ** min(net.n, 1023)))


# ---------------------------------------------------------------------------
# Description length: the canonical CausalBool complexity index
# ---------------------------------------------------------------------------

def _log2_binomial(n: int, d: int) -> float:
    """``log2 C(n, d)`` -- the exact cost of naming an index set of size d."""
    return math.log2(max(1, math.comb(n, d)))


def node_description_cost(n: int, degree: int, gate: str) -> float:
    """Per-node description length, following ``BioMetrics.m``'s ``encodeNodeCost``.

    ``log2(#gate types)`` names the gate, ``log2 C(n, d)`` names the index set,
    and a gate-specific term pays for its parameters.
    """
    cost = math.log2(len(GATE_LABELS))
    cost += _log2_binomial(n, degree)
    if gate == 'KOFN':
        cost += math.log2(degree + 1) + 1
    elif gate == 'CANALISING':
        cost += math.log2(max(1, n)) + 2
    elif gate in ('IMPLIES', 'NIMPLIES'):
        cost += math.log2(max(1, degree * (degree - 1)))
    elif gate == 'NOT':
        cost += math.log2(max(1, degree))
    else:
        cost += 1
    return cost


def graph_description_length(graph, wiring_only: bool = False) -> float:
    """Exact description length ``D`` of a molecular graph's causal structure.

    With ``wiring_only`` the gate and parameter terms are dropped and only the
    index-set cost ``sum_v log2 C(n, deg v)`` remains, which is the purely
    structural quantity directly comparable with BDM: both look at the bonds
    and nothing else.
    """
    n = graph.n_nodes
    if n == 0:
        return 0.0
    if wiring_only:
        # Purely structural: the index-set term needs only the degree sequence,
        # so no chemistry and no gate assignment is consulted.
        degrees = np.bincount(np.asarray(graph.dst, dtype=int), minlength=n)
        return math.log2(max(1, n)) + float(sum(_log2_binomial(n, int(d))
                                                for d in degrees))
    net = molecular_network(graph)
    return math.log2(max(1, n)) + sum(
        node_description_cost(n, len(net.neighbours[k]), net.gates[k])
        for k in range(n))


# ---------------------------------------------------------------------------
# Path information from the index algebra
# ---------------------------------------------------------------------------

def path_index_sets(graph, max_len: int = 3) -> list:
    """``L``-hop index sets: atoms reachable from each atom by a simple path of length L.

    This is the index-set reading of exactly the object T-Hop tensorises and
    Graphormer walks along.  Sets, not counts: the index algebra asks *which*
    atoms a path of a given length can reach, which is what determines how much
    of the molecule a path-bounded model can address.
    """
    n = graph.n_nodes
    nb = graph.neighbours()
    layers = [[set() for _ in range(n)] for _ in range(max_len)]

    for s in range(n):
        visited = [False] * n
        path = []

        def dfs(u):
            visited[u] = True
            path.append(u)
            length = len(path) - 1
            if 1 <= length <= max_len:
                layers[length - 1][s].add(u)
            if length < max_len:
                for w in nb[u]:
                    if not visited[w]:
                        dfs(w)
            path.pop()
            visited[u] = False

        dfs(s)
    return layers


def path_description_length(graph, max_len: int = 3) -> dict:
    """Index-set description length of each path layer, and their sum.

    Layer ``L`` costs ``sum_v log2 C(n, |N_L(v)|)``: the price of naming, for
    every atom, the set of atoms its length-``L`` paths reach.
    """
    n = graph.n_nodes
    layers = path_index_sets(graph, max_len)
    out = {}
    for L, layer in enumerate(layers, start=1):
        out[f'D_hop{L}'] = sum(_log2_binomial(n, len(s)) for s in layer)
    out['D_path_total'] = sum(out.values())
    return out


def sumando_bits(graph, order: int = 2) -> float:
    """Size of the compressed ``(DecimalRepertoire, Sumandos)`` answer, in bits.

    When ``onPossibleBehaviour`` answers a query about ``order`` nodes it
    enumerates ``joinedNames`` -- the union of their index sets -- and folds
    every remaining coordinate into the sumandos.  The offset family therefore
    has :math:`2^{\\,n - |joinedNames|}` members, so

        log2 |Omega| = n - |joinedNames|

    is the number of bits the compressed answer devotes to the free part.
    Averaged over all ``order``-node queries this is a purely **structural**
    quantity: it needs no gates, so unlike the description length ``D`` it does
    not depend on any dynamics we impose on a molecule.

    **This mean is itself degree-determined, and therefore separates nothing.**
    Summing over pairs,
    ``sum |N(i) u N(j)| = sum (d_i + d_j) - sum |N(i) n N(j)|`` and
    ``sum |N(i) n N(j)| = sum_v C(d_v, 2)``, so both terms depend only on the
    degree sequence.  Measured: 0 of 250 same-degree pairs separated, exactly
    like ``D_wiring``.  It is kept because the failure is instructive -- the
    obvious repair is not a repair.

    Use :func:`sumando_spread`, or the full sorted profile
    (``method_comparison.query_overlap_profile``), which read the *distribution*
    of overlaps rather than its mean and do carry topology.
    """
    A = np.asarray(graph.adjacency())
    n = A.shape[0]
    if n < order:
        return float('nan')
    nb = [set(np.nonzero(A[i])[0].tolist()) for i in range(n)]
    return float(np.mean([n - len(set().union(*[nb[i] for i in combo]))
                          for combo in itertools.combinations(range(n), order)]))


def sumando_spread(graph, order: int = 2) -> float:
    """Standard deviation of the sumando-bit profile over all ``order``-node queries.

    The mean of that profile is degree-determined (see :func:`sumando_bits`), but
    its *shape* is not: two graphs with identical degrees can spread their
    neighbourhood overlaps very differently.  Measured on the same 250
    same-degree molecule pairs: 84.4% separated at ``order=2`` and 95.2% at
    ``order=3``, against 0% for the mean and for ``D_wiring``.
    """
    A = np.asarray(graph.adjacency())
    n = A.shape[0]
    if n < order:
        return float('nan')
    nb = [set(np.nonzero(A[i])[0].tolist()) for i in range(n)]
    vals = [n - len(set().union(*[nb[i] for i in combo]))
            for combo in itertools.combinations(range(n), order)]
    return float(np.std(vals))


def receptive_saturation(graph, max_len: int = 3) -> float:
    """Fraction of the molecule a path-length-bounded model can actually address.

    For each atom, the union of its 1..``max_len``-hop index sets divided by the
    number of other atoms; averaged over atoms.  A value of 1 means a model with
    that path budget sees the whole molecule from every atom; a small value
    means it sees a local neighbourhood and the rest of the molecule is
    invisible to it.
    """
    n = graph.n_nodes
    if n <= 1:
        return float('nan')
    layers = path_index_sets(graph, max_len)
    fracs = []
    for v in range(n):
        reach = set()
        for layer in layers:
            reach |= layer[v]
        reach.discard(v)
        fracs.append(len(reach) / (n - 1))
    return float(np.mean(fracs))


def path_surplus(graph, max_len: int = 3) -> float:
    """Description length of the path layers relative to the bonds alone.

    ``(D_hop2 + ... + D_hopL) / D_hop1``.  Large values mean the path structure
    is expensive to state given the bonds -- it carries a lot that the adjacency
    does not -- and small values mean it is nearly implied by the bonds.
    """
    d = path_description_length(graph, max_len)
    base = d['D_hop1']
    if base <= 0:
        return float('nan')
    return (d['D_path_total'] - base) / base


# ---------------------------------------------------------------------------
# Dataset-level aggregation, mirroring the paper's AOAC
# ---------------------------------------------------------------------------

def dataset_index_measures(dataset, max_len: int = 3, limit: int | None = None) -> dict:
    """Average every index-set observable over a dataset's molecular graphs.

    The direct analogue of the paper's AOAC: one number per dataset family,
    computed from bonds alone and therefore shared by all six noise variants of
    the family.
    """
    graphs = dataset.graphs if limit is None else dataset.graphs[:limit]
    rows = []
    for g in graphs:
        if g.n_nodes < 2:
            continue
        d = path_description_length(g, max_len)
        rows.append(dict(
            n_atoms=g.n_nodes,
            D=graph_description_length(g),
            D_wiring=graph_description_length(g, wiring_only=True),
            saturation=receptive_saturation(g, max_len),
            sumando_bits_k2=sumando_bits(g, 2),
            sumando_bits_k3=sumando_bits(g, 3),
            sumando_spread_k2=sumando_spread(g, 2),
            sumando_spread_k3=sumando_spread(g, 3),
            path_surplus=path_surplus(g, max_len),
            **d))
    arr = {k: float(np.nanmean([r[k] for r in rows])) for k in rows[0]}
    arr['n_graphs'] = len(rows)
    arr['D_per_atom'] = float(np.mean([r['D'] / r['n_atoms'] for r in rows]))
    return arr
