"""behaviour_table.py  (Level 3)

Gate-agnostic behaviour-table analysis: given a binary output pattern, describe
HOW its information is distributed, without assuming any generating gate.  This is
the computational form of the behaviour-table method of the UNAM thesis
(doc/Tesis-UNAM, chapter 4): find the pivots (the invariant place-value
structure), the sumandos (the free offset dimension), and the schema (clause)
structure that tiles the one-set, and measure how much the pattern compresses.

The naming of a gate is deliberately not attempted here.  The object recovered is
the information-distribution structure itself.  A structured pattern (however
generated) compresses; a random pattern does not.  This module is the foundation
for expressing patterns with no gate name, and eventually for synthesising more
general rules than Boolean gates.

Reuses only the pivot and schema primitives of Level 1; it does not modify them.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from deconvolution import essential_variables, reduce_column, minimal_dnf


def decimal_repertoire(column):
    """Decimal indices where the pattern is 1 (the thesis DecimalRepertoire)."""
    return [i for i, v in enumerate(column) if v == 1]


def sumando_bits(column, n):
    """Bit positions that never change the output: the free offset dimension.

    These are the complement of the essential variables; flipping a sumando bit
    leaves the pattern invariant, so the one-set is a union of translates of the
    subcube they span.
    """
    ess = set(essential_variables(column, n))
    return [i for i in range(n) if i not in ess]


def behaviour_decomposition(column, n):
    """Full gate-agnostic behaviour table for a 2**n pattern.

    Returns the pivots (essential bits), the sumandos (free bits), the schema
    clauses that tile the reduced one-set, and a compression figure: how many of
    the pattern's ones each schema accounts for.  A structured pattern has few
    schemata each covering many ones; a random pattern needs about one schema per
    one.
    """
    ess = essential_variables(column, n)
    reduced = reduce_column(column, n, ess)
    ones_reduced = sum(reduced)
    clauses = minimal_dnf(reduced) if 0 < ones_reduced < len(reduced) else (
        [] if ones_reduced == 0 else [{"activators": ess_i, "inhibitors": []}
                                      for ess_i in [[]]])
    n_clauses = max(1, len(clauses)) if ones_reduced else 0
    one_set_full = ones_reduced * (2 ** len(sumando_bits(column, n)))
    return {
        "n": n,
        "one_set_size": sum(column),
        "pivots_essential_bits": ess,
        "sumando_bits": sumando_bits(column, n),
        "num_schemata": n_clauses,
        "ones_per_schema": (one_set_full / n_clauses) if n_clauses else 0.0,
        "schemata": clauses,
    }


# ---------------------------------------------------------------------------
# One-dimensional pattern complexity (for a time series read as a binary string)
# ---------------------------------------------------------------------------

def run_length_encoding(bits):
    """Run-length encoding, the thesis's 'k zeros, then 1,0 twice, ...' signature."""
    if not bits:
        return []
    runs = []
    cur = bits[0]
    count = 1
    for b in bits[1:]:
        if b == cur:
            count += 1
        else:
            runs.append((cur, count))
            cur = b
            count = 1
    runs.append((cur, count))
    return runs


def lz76_complexity(bits):
    """Lempel-Ziv (1976) complexity: number of distinct factors in a left-to-right
    parse.  A real algorithmic-complexity measure; low means structured."""
    s = "".join(str(b) for b in bits)
    n = len(s)
    if n == 0:
        return 0
    i, c, u, v, vmax = 0, 1, 1, 1, 1
    while u + v <= n:
        if s[i + v - 1] == s[u + v - 1]:
            v += 1
        else:
            vmax = max(v, vmax)
            i += 1
            if i == u:
                c += 1
                u += vmax
                v = 1
                i = 0
                vmax = 1
            else:
                v = 1
    if v != 1:
        c += 1
    return c
