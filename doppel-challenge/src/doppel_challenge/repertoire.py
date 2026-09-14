"""repertoire -- exact attractor repertoire and probability distribution.

The repertoire used by the doppel-challenge is the empirical
distribution over the attractor states of a synchronous Boolean network
under a uniform draw of initial states.  For each initial state x_0:

  1. follow the deterministic dynamics until the trajectory enters a
     cycle A(x_0),
  2. distribute mass 1 / |A(x_0)| equally over the states of that cycle.

Summing over all 2**N initial states yields an exact rational
probability distribution on the union of all attractors.

This is *not* the one-step image of the update map.  The distinction is
essential: the laboratory is defined on attractor repertoires, not on
the immediate next-state map.
"""
from __future__ import annotations

from fractions import Fraction
from typing import Any

from .adapters import Network, input_vector, step


def transition_map(net: Network) -> list[int]:
    """Return the deterministic one-step map on the full N-bit state space."""
    out: list[int] = []
    for x in range(1 << net.n):
        y = 0
        for i, bit in enumerate(step(net, input_vector(x, net.n))):
            if bit:
                y |= 1 << i
        out.append(y)
    return out


def one_step_output_distribution(net: Network, nxt: list[int] | None = None) -> dict[str, Any]:
    """Histogram of ``F(x)`` for a uniform initial state x.

    This is deliberately separate from the long-run basin-weighted
    attractor repertoire returned by :func:`compute_repertoire`.
    """
    nxt = transition_map(net) if nxt is None else nxt
    counts: dict[int, int] = {}
    for state in nxt:
        counts[state] = counts.get(state, 0) + 1
    support = sorted(counts)
    denominator = 1 << net.n
    return {
        "rows": denominator,
        "cols": net.n,
        "matrix_lsb_first": True,
        "support": support,
        "counts": [counts[s] for s in support],
        "probability_denominator": denominator,
        "probs": [counts[s] / denominator for s in support],
    }


def make_network(n: int, C: list[list[int]], gates: list[str],
                 params: list[dict] | None = None) -> Network:
    return Network(n=n, C=C, gates=gates, params=params)


def compute_repertoire(net: Network) -> dict[str, Any]:
    """Compute the exact attractor repertoire of ``net``.

    Returns a dict with keys:

      rows        -- 2**N
      cols        -- N
      support     -- sorted list of decimal states that lie on an attractor
      counts      -- integer numerators on a common denominator
      probability_denominator -- common denominator of the exact probabilities
      probs       -- floating-point probabilities derived from the exact rationals
    """
    n = net.n
    N_rows = 1 << n
    # Compute this once and reuse it for both observables and basin analysis.
    nxt = transition_map(net)

    # Cache the attractor cycle reached from each state.
    cycle_of: dict[int, tuple[int, ...]] = {}
    state_mass: dict[int, Fraction] = {}
    for start in range(N_rows):
        seen: dict[int, int] = {}
        path: list[int] = []
        x = start
        while x not in seen and x not in cycle_of:
            seen[x] = len(path)
            path.append(x)
            x = nxt[x]

        if x in cycle_of:
            cycle = cycle_of[x]
        else:
            cycle = tuple(path[seen[x]:])
            for s in cycle:
                cycle_of[s] = cycle

        for s in path:
            cycle_of[s] = cycle

        contrib = Fraction(1, len(cycle))
        for s in cycle:
            state_mass[s] = state_mass.get(s, Fraction(0, 1)) + contrib

    exact_probs = {s: m / N_rows for s, m in state_mass.items() if m > 0}
    support = sorted(exact_probs)
    denominators = [fr.denominator for fr in exact_probs.values()] or [1]
    common_denominator = 1
    for d in denominators:
        # lcm(common_denominator, d)
        a = common_denominator
        b = d
        while b:
            a, b = b, a % b
        gcd = a
        common_denominator = common_denominator * d // gcd
    counts = [
        exact_probs[s].numerator * (common_denominator // exact_probs[s].denominator)
        for s in support
    ]
    probs = [float(exact_probs[s]) for s in support]

    one_step = one_step_output_distribution(net, nxt)
    # Keep cycles and basin sizes as explicit audit fields.  cycle_of contains
    # transient states as well, so retain only canonical cycles here.
    # Canonicalise cycles by their state set.  The production walk may first
    # encounter a cycle at any phase; scientific records must not depend on
    # that incidental rotation.
    cycles = sorted({tuple(sorted(cycle)) for cycle in cycle_of.values()})
    basin_sizes = [sum(1 for reached in cycle_of.values()
                       if tuple(sorted(reached)) == cycle)
                   for cycle in cycles]
    phase_weights = [
        {"numerator": basin_size, "denominator": N_rows * len(cycle)}
        for cycle, basin_size in zip(cycles, basin_sizes)
    ]
    probability_fractions = [
        {"numerator": exact_probs[state].numerator,
         "denominator": exact_probs[state].denominator}
        for state in support
    ]
    return {
        "rows": N_rows,
        "cols": n,
        "matrix_lsb_first": True,
        "support": support,
        "counts": counts,
        "probability_denominator": common_denominator,
        "probs": probs,
        "probability_fractions": probability_fractions,
        "transition_map": nxt,
        "one_step_output_distribution": one_step,
        "attractor_cycles": [list(cycle) for cycle in cycles],
        "basin_sizes": basin_sizes,
        "phase_weights": phase_weights,
        "observable": "basin_weighted_attractor_repertoire",
    }


def estimate_repertoire(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Lazy compatibility export for the Step 3.5 approximate estimator.

    The implementation lives in :mod:`doppel_challenge.estimator` so the
    exact and approximate algorithms remain visibly separate.
    """
    from .estimator import estimate_repertoire as _estimate_repertoire
    return _estimate_repertoire(*args, **kwargs)
