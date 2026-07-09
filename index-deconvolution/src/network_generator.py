"""network_generator.py

Deterministic (seeded) generator of small synchronous Boolean networks for the
deconvolution experiments.  Every generated node carries a gate whose arity is
consistent with its connected set, so the forward repertoire is always well
defined.
"""

from __future__ import annotations

import random

from causalbool import Network

# Gates grouped by the arity constraints they impose.
_ANY_ARITY = ("AND", "OR", "XOR", "NAND", "NOR", "XNOR", "MAJORITY")
_UNARY = ("NOT",)
_BINARY = ("IMPLIES", "NIMPLIES")


def random_network(
    n: int,
    seed: int,
    max_arity: int | None = None,
    gate_pool: str = "all",
) -> Network:
    """Generate a random ``n``-node network.

    Parameters
    ----------
    n : int
        Number of nodes.
    seed : int
        Random seed (pinned for reproducibility).
    max_arity : int | None
        Maximum number of connected inputs per node.  Defaults to
        ``min(n, 5)`` to keep reduced truth tables small.
    gate_pool : str
        ``"all"`` uses the full 12-gate family; ``"symmetric"`` restricts to
        arity-flexible symmetric gates plus KOFN and MAJORITY.
    """
    rng = random.Random(seed)
    if max_arity is None:
        max_arity = min(n, 5)

    if gate_pool == "symmetric":
        pool_any = list(_ANY_ARITY) + ["KOFN"]
        pool_unary: list[str] = []
        pool_binary: list[str] = []
        pool_canalising = False
    elif gate_pool == "core":
        # Gates supported by the canonical Wolfram CausalBoolCore.wl reference
        # (everything except CANALISING).  Used by the equivalence cross-check.
        pool_any = list(_ANY_ARITY) + ["KOFN"]
        pool_unary = list(_UNARY)
        pool_binary = list(_BINARY)
        pool_canalising = False
    else:
        pool_any = list(_ANY_ARITY) + ["KOFN", "CANALISING"]
        pool_unary = list(_UNARY)
        pool_binary = list(_BINARY)
        pool_canalising = True

    C = [[0] * n for _ in range(n)]
    gates: list[str] = []
    params: list[dict] = []

    for k in range(n):
        # Decide a gate class first, then draw a consistent connected set.
        choices: list[str] = list(pool_any)
        if pool_unary:
            choices += pool_unary
        if pool_binary:
            choices += pool_binary
        gate = rng.choice(choices)

        if gate in _UNARY:
            arity = 1
        elif gate in _BINARY:
            arity = 2
        else:
            arity = rng.randint(1, max_arity)

        ic = sorted(rng.sample(range(n), arity))
        for i in ic:
            C[k][i] = 1

        p: dict = {}
        if gate == "KOFN":
            p["k"] = rng.randint(1, arity)
        elif gate == "CANALISING":
            p["canalisingIndex"] = rng.randint(0, arity - 1)
            p["canalisingValue"] = rng.randint(0, 1)
            p["canalisedOutput"] = rng.randint(0, 1)

        gates.append(gate)
        params.append(p)

    return Network(n=n, C=C, gates=gates, params=params)
