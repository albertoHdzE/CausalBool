"""ca_deconvolution.py

Deconvolve a cellular-automaton space-time diagram into a Boolean network.

An elementary cellular automaton is already a synchronous Boolean network: each
cell is a node connected to its neighbourhood, and the rule is the shared local
gate.  A space-time diagram, however, gives only a trajectory (each row is the
input to the next), not the exhaustive repertoire.  So this is the per-node
deconvolution of :mod:`deconvolution` applied to trajectory samples instead of
the full repertoire.

For every cell the method (following Zenil et al., Supplement p.33) infers the
smallest local support consistent with the observations, drops any provably
irrelevant neighbour, builds the local truth table from the samples, and names
the gate against the canonical family (falling back to an explicit look-up
table for rules with no canonical name, which is most of them).  The recovered
network is then run forward and checked against the diagram; when the trajectory
covers every local neighbourhood the recovered rule is exact and the network's
exhaustive repertoire equals the automaton's global map.

Conventions match :mod:`causalbool`: LSB-first, 0-based indices, connectivity as
ascending absolute cell indices.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from causalbool import Network, evolve_network, repertoire
from deconvolution import identify_gate, GateMatch


# ---------------------------------------------------------------------------
# Elementary cellular automaton forward dynamics
# ---------------------------------------------------------------------------

def eca_next_cell(left: int, centre: int, right: int, rule: int) -> int:
    """Next value of a cell from its neighbourhood under an ECA rule."""
    idx = (left << 2) | (centre << 1) | right
    return (rule >> idx) & 1


def evolve_eca(rule: int, initial: list[int], steps: int) -> list[list[int]]:
    """Space-time diagram of an ECA with periodic boundary conditions."""
    w = len(initial)
    rows = [list(initial)]
    for _ in range(steps - 1):
        cur = rows[-1]
        nxt = [eca_next_cell(cur[(i - 1) % w], cur[i], cur[(i + 1) % w], rule)
               for i in range(w)]
        rows.append(nxt)
    return rows


# ---------------------------------------------------------------------------
# Deconvolution
# ---------------------------------------------------------------------------

@dataclass
class CANodeReconstruction:
    cell: int
    support: list[int]           # absolute cell indices, ascending
    reduced_truth_table: list[int]
    coverage: float              # fraction of local neighbourhoods observed
    canonical: GateMatch
    num_matches: int

    def as_dict(self) -> dict:
        return {
            "cell": self.cell,
            "support": list(self.support),
            "reduced_truth_table": list(self.reduced_truth_table),
            "coverage": self.coverage,
            "canonical": self.canonical.as_dict(),
            "num_matches": self.num_matches,
        }


def _window(i: int, r: int, w: int) -> list[int]:
    """Ascending absolute cell indices within radius r of cell i (periodic)."""
    return sorted({(i + d) % w for d in range(-r, r + 1)})


def _key(state: list[int], support: list[int]) -> int:
    y = 0
    for j, c in enumerate(support):
        if state[c]:
            y |= (1 << j)
    return y


def _consistent(samples: list[tuple[list[int], int]], support: list[int]) -> bool:
    """True if the samples define a well-formed function of ``support``."""
    seen: dict[int, int] = {}
    for state, out in samples:
        k = _key(state, support)
        if k in seen:
            if seen[k] != out:
                return False
        else:
            seen[k] = out
    return True


def _essential_cells(samples: list[tuple[list[int], int]], window: list[int]) -> list[int]:
    """Cells in ``window`` proven to influence the output over the samples."""
    essential = []
    for j in window:
        rest = [c for c in window if c != j]
        groups: dict[int, set[int]] = {}
        for state, out in samples:
            k = _key(state, rest)
            groups.setdefault(k, set()).add(out)
        # j is essential if fixing the other cells still leaves output ambiguous,
        # which (given determinism over the full window) must be due to j.
        if any(len(outs) > 1 for outs in groups.values()):
            essential.append(j)
    return essential


def _collect_samples(diagrams: list[list[list[int]]], cell: int) -> list[tuple[list[int], int]]:
    """Pool (state -> next value at ``cell``) samples across an observation ensemble."""
    samples = []
    for diagram in diagrams:
        for t in range(len(diagram) - 1):
            samples.append((diagram[t], diagram[t + 1][cell]))
    return samples


def deconvolve_ca_cell(
    diagrams: list[list[list[int]]], cell: int, max_radius: int
) -> CANodeReconstruction:
    w = len(diagrams[0][0])
    samples = _collect_samples(diagrams, cell)

    # smallest radius whose window explains the samples deterministically
    support = None
    for r in range(0, max_radius + 1):
        win = _window(cell, r, w)
        if _consistent(samples, win):
            support = win
            break
    if support is None:
        support = _window(cell, max_radius, w)

    # drop provably irrelevant neighbours, keeping consistency
    ess = _essential_cells(samples, support)
    if ess and _consistent(samples, ess):
        support = ess
    elif not ess and _consistent(samples, []):
        support = []  # constant cell

    # build the local truth table from the samples
    m = len(support)
    table: list[int | None] = [None] * (2 ** m)
    for state, out in samples:
        table[_key(state, support)] = out
    observed = sum(1 for v in table if v is not None)
    coverage = observed / (2 ** m) if m >= 0 else 1.0
    reduced = [0 if v is None else v for v in table]

    matches, canonical = identify_gate(reduced)
    return CANodeReconstruction(
        cell=cell, support=support, reduced_truth_table=reduced,
        coverage=coverage, canonical=canonical, num_matches=len(matches),
    )


def deconvolve_ca(
    diagrams: list[list[list[int]]], max_radius: int = 3
) -> tuple[Network, list[CANodeReconstruction]]:
    """Deconvolve an observation ensemble of space-time diagrams into a network.

    ``diagrams`` is a list of diagrams (each a list of rows), pooled as
    observations of the same automaton.  A single diagram may be passed wrapped
    in a one-element list.  Returns the reconstructed network and per-cell
    reports.  The gate of each cell is applied to its recovered support in
    ascending order, so it is directly runnable by
    :func:`causalbool.evolve_network`.
    """
    w = len(diagrams[0][0])
    reports = [deconvolve_ca_cell(diagrams, i, max_radius) for i in range(w)]

    C = [[0] * w for _ in range(w)]
    gates: list[str] = ["FALSE"] * w
    params: list[dict] = [dict() for _ in range(w)]
    for i, rec in enumerate(reports):
        for c in rec.support:
            C[i][c] = 1
        gates[i] = rec.canonical.gate
        if rec.canonical.gate == "LUT":
            params[i] = {"table": rec.reduced_truth_table}
        else:
            params[i] = dict(rec.canonical.params)

    net = Network(n=w, C=C, gates=gates, params=params)
    return net, reports


# ---------------------------------------------------------------------------
# Verification
# ---------------------------------------------------------------------------

def ca_global_map(rule: int, w: int) -> list[list[int]]:
    """The automaton's global map: next state for every one of the 2**w states,
    enumerated LSB-first (same ordering as :func:`causalbool.repertoire`)."""
    out = []
    for x in range(2 ** w):
        v = [(x >> i) & 1 for i in range(w)]
        out.append([eca_next_cell(v[(i - 1) % w], v[i], v[(i + 1) % w], rule)
                    for i in range(w)])
    return out


def verify_ca(diagrams: list[list[list[int]]], net: Network,
              rule: int | None = None) -> dict:
    """Verify the recovered network against the observations and, optionally,
    against the automaton's exact global map.

    - trajectory_exact: the network reproduces every observed diagram from its
      first row.
    - global_map_exact: when ``rule`` is given and the width is small enough,
      the network's exhaustive repertoire equals the automaton's global map on
      all 2**w states.  This is the decisive test of exact rule recovery, not
      merely trajectory reproduction.
    """
    w = net.n
    trajectory_exact = all(
        evolve_network(net, d[0], len(d)) == d for d in diagrams)
    result = {"trajectory_exact": trajectory_exact, "width": w,
              "n_diagrams": len(diagrams)}
    if rule is not None and w <= 20:
        result["global_map_exact"] = (repertoire(net) == ca_global_map(rule, w))
    return result
