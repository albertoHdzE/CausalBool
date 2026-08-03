"""Explicit generating models recovered by the CausalBool index-set calculus.

:mod:`causalbool_mirror` answers the paper's questions with a *decision* per cell.
This module goes the rest of the way and returns the **model**: for each object
the paper analyses, the smallest index set and the exact Boolean function that
regenerates it, verified by running the recovered mechanism forward.

That is the step the paper itself asks for and does not take. It says of Fig. 1
that it recovers "the candidate programs (which for this trivial example are
exactly the original)", but what it actually reports is a real-valued footprint;
the program in Figs. 1C-E is drawn by hand, not inferred. Here the mechanism is
inferred, printed, and checked.

Three object types are covered, matching the paper's own progression:

``deconvolve_string``
    Fig. 1A-B. A string is modelled as a Boolean recurrence: each bit is a
    function of a minimal set of earlier lags. For ``'01'`` repeated, the
    recovered model is ``b[i] = NOT b[i-1]`` -- the generating program itself.
``deconvolve_ca_network``
    Fig. 2 and Sup. Fig. 2. A space-time diagram is deconvolved into a full
    synchronous Boolean network, one gate per cell, then verified against the
    automaton's exhaustive global map.
``segment_string``
    The deconvolution proper: find where along a string the minimal model
    changes, which is the paper's causal partition done exactly.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np

from .causalbool_mirror import load_root_modules

__all__ = [
    "StringModel",
    "deconvolve_string",
    "segment_string",
    "CANetworkModel",
    "deconvolve_ca_network",
]


# ---------------------------------------------------------------------------
# Strings as Boolean recurrences (Fig. 1)
# ---------------------------------------------------------------------------


@dataclass
class StringModel:
    """A recovered generating mechanism for a binary string.

    ``lags`` is the index set: the offsets back from the current position that
    the next bit actually depends on.  ``table`` is the truth table over those
    lags, in LSB-first order.  ``gate`` names it against the canonical family
    where one applies.
    """

    lags: tuple[int, ...] | None
    table: list[int] | None
    gate: str | None
    order_searched: int
    exact: bool
    n_samples: int

    def describe(self) -> str:
        if not self.exact:
            return f"no deterministic model of order <= {self.order_searched}"
        if not self.lags:
            return f"constant {self.table[0] if self.table else '?'}"
        args = ", ".join(f"b[i-{l}]" for l in self.lags)
        return f"b[i] = {self.gate}({args})   index set {set(self.lags)}"

    def regenerate(self, prefix: list[int], n: int) -> list[int]:
        """Run the recovered mechanism forward from ``prefix``."""
        if not self.exact or self.lags is None:
            raise ValueError("no exact model to run")
        out = list(prefix)
        while len(out) < n:
            key = 0
            for k, l in enumerate(self.lags):
                if out[len(out) - l]:
                    key |= 1 << k
            out.append(self.table[key])
        return out[:n]


def _consistent(samples, lags) -> list[int] | None:
    """Truth table over ``lags`` if the samples define a function, else ``None``."""
    table: dict[int, int] = {}
    for hist, out in samples:
        key = 0
        for k, l in enumerate(lags):
            if hist[-l]:
                key |= 1 << k
        if table.setdefault(key, out) != out:
            return None
    return [table.get(k, 0) for k in range(2 ** len(lags))]


def deconvolve_string(bits, max_order: int = 6) -> StringModel:
    """Recover the smallest lag index set and Boolean function generating ``bits``.

    Search is over index sets in order of increasing size, so the answer is the
    *minimal* mechanism rather than merely a sufficient one.  If no index set
    within ``max_order`` explains every transition, the string has no
    deterministic model at that order -- which is the honest answer for an
    algorithmically random segment, and is exactly the signal the paper's
    footprint approximates with a real number.
    """
    b = [int(c) for c in bits] if isinstance(bits, str) else [int(x) for x in bits]
    samples = [(b[:i], b[i]) for i in range(max_order, len(b))]
    if not samples:
        return StringModel(None, None, None, max_order, False, 0)

    for size in range(0, max_order + 1):
        for lags in combinations(range(1, max_order + 1), size):
            table = _consistent(samples, lags)
            if table is not None:
                gate = _name_gate(table)
                return StringModel(lags, table, gate, max_order, True, len(samples))
    return StringModel(None, None, None, max_order, False, len(samples))


def _name_gate(table: list[int]) -> str:
    _, dec_root, _ = load_root_modules()
    try:
        _, canonical = dec_root.identify_gate(table)
        return canonical.gate
    except Exception:  # pragma: no cover - naming is cosmetic
        return "LUT"


def segment_string(bits, max_order: int = 6, window: int = 24) -> list[dict]:
    """Slide a window along the string and record where the minimal model changes.

    This is the paper's causal partition, done by mechanism rather than by
    perturbation magnitude: a boundary is a position where the smallest index
    set that explains the data stops explaining it.
    """
    b = [int(c) for c in bits] if isinstance(bits, str) else [int(x) for x in bits]
    rows = []
    for start in range(0, len(b) - window + 1):
        m = deconvolve_string(b[start : start + window], max_order=max_order)
        rows.append(
            {
                "start": start,
                "exact": m.exact,
                "lags": m.lags,
                "gate": m.gate,
                "model": m.describe(),
            }
        )
    return rows


# ---------------------------------------------------------------------------
# Space-time diagrams as Boolean networks (Fig. 2, Sup. Fig. 2)
# ---------------------------------------------------------------------------


@dataclass
class CANetworkModel:
    """A synchronous Boolean network recovered from observed space-time diagrams."""

    network: object
    reports: list
    verification: dict
    width: int

    @property
    def supports(self) -> list[list[int]]:
        return [r.support for r in self.reports]

    @property
    def gates(self) -> list[str]:
        return [r.canonical.gate for r in self.reports]

    def summary(self) -> dict:
        sizes = [len(s) for s in self.supports]
        return {
            "cells": self.width,
            "mean_index_set_size": float(np.mean(sizes)),
            "max_index_set_size": int(np.max(sizes)),
            "mean_coverage": float(np.mean([r.coverage for r in self.reports])),
            **self.verification,
        }


def deconvolve_ca_network(
    diagrams, max_radius: int = 2, rule: int | None = None
) -> CANetworkModel:
    """Deconvolve one or more space-time diagrams into an explicit Boolean network.

    Delegates to the root project's ``index-deconvolution`` implementation, so
    the mechanism recovered here is the same object the rest of the CausalBool
    programme works with, not a reimplementation.

    ``verification`` reports two things.  ``trajectory_exact`` says the recovered
    network reproduces every observed diagram from its first row.
    ``global_map_exact`` -- available for narrow tapes -- says the network's
    *exhaustive repertoire* over all ``2**w`` states equals the automaton's true
    global map.  The second is the decisive test: it certifies that the
    mechanism was recovered, not merely fitted to the observations.
    """
    _, _, cadec = load_root_modules()
    ds = [np.asarray(d).astype(int).tolist() for d in diagrams]
    net, reports = cadec.deconvolve_ca(ds, max_radius=max_radius)
    verification = cadec.verify_ca(ds, net, rule=rule)
    return CANetworkModel(net, reports, verification, len(ds[0][0]))
