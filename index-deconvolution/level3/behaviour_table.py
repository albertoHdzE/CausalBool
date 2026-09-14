"""behaviour_table.py  (Level 3)

Gate-agnostic behaviour-table analysis: given a binary output pattern, describe
HOW its information is distributed, without assuming any generating gate.  This is
the computational form of the behaviour-table method of the UNAM thesis
(doc/Tesis-UNAM, chapter 4): find the ESSENTIAL VARIABLES (the invariant
place-value structure), the FREE COORDINATES (the offset dimension), and the
schema (clause) structure that tiles the one-set, and measure how much the
pattern compresses.

TWO NOTES, both author rulings, both previously violated by this file.

GLOSSARY sec.1e (2026-09-07): the essential variables are NOT what the retired
word named. That word is a finance term and denotes nothing in this method. This
module used it in its own dict key, ``pivots_essential_bits`` -- and a wrong
identifier is a definition that cannot be argued with, which is why the ruling
had to be made three times before it took.

GLOSSARY sec.1d (2026-09-03): the free coordinates are NOT "the sumandos".
The sumandos of a schema are the fillings of its own don't-care positions,
wherever they fall -- including don't-cares on CONNECTED inputs, which is where
all of Rule 110's live. See free_coordinates() below.

The naming of a gate is deliberately not attempted here.  The object recovered is
the information-distribution structure itself.  A structured pattern (however
generated) compresses; a random pattern does not.  This module is the foundation
for expressing patterns with no gate name, and eventually for synthesising more
general rules than Boolean gates.

Reuses only the essential-variable and schema primitives of Level 1; it does not
modify them.
"""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from deconvolution import essential_variables, reduce_column, minimal_dnf


def decimal_repertoire(column):
    """Decimal indices where the pattern is 1 (the thesis DecimalRepertoire)."""
    return [i for i, v in enumerate(column) if v == 1]


def free_coordinates(column, n):
    """Bit positions that never change the output: the FREE COORDINATES.

    These are the complement of the essential variables; flipping one leaves the
    pattern invariant, so the one-set is a union of translates of the subcube
    they span.

    THIS FUNCTION WAS CALLED ``sumando_bits`` AND THAT NAME WAS THE ERROR
    (GLOSSARY sec.1d, author ruling 2026-09-03). It computes the complement of
    the essential variables, which is the free coordinates -- not the sumandos.

      Definition. The sumandos of a schema are the fillings of ITS OWN
      DON'T-CARE positions, wherever those positions fall.

    The two coincide only in the special case where a schema's don't-cares are
    exactly the disconnected inputs. Rule 110 is the standing counterexample:
    all three inputs are connected, so this function returns [] -- yet the
    correct reading gives three schemata (01*, 10*, *10) whose don't-cares all
    sit on CONNECTED inputs. Naming this ``sumando_bits`` is precisely how the
    implementation detail became the definition, five times over.
    """
    ess = set(essential_variables(column, n))
    return [i for i in range(n) if i not in ess]


def sumando_bits(column, n):
    """DEPRECATED name for :func:`free_coordinates`. Do not use in new code.

    Kept as a forwarder rather than deleted so stored artefacts and the Level-3
    experiments keep resolving; the name is wrong for the reason given above.
    """
    return free_coordinates(column, n)


def behaviour_decomposition(column, n):
    """Full gate-agnostic behaviour table for a 2**n pattern.

    Returns the ESSENTIAL VARIABLES (the sensitive bits), the FREE COORDINATES
    (the insensitive bits), the schema clauses that tile the reduced one-set,
    and a compression
    figure: how many of the pattern's ones each schema accounts for.  A
    structured pattern has few schemata each covering many ones; a random
    pattern needs about one schema per one.

    The second item is NOT "the sumandos" -- see :func:`free_coordinates`.
    """
    ess = essential_variables(column, n)
    reduced = reduce_column(column, n, ess)
    ones_reduced = sum(reduced)
    clauses = minimal_dnf(reduced) if 0 < ones_reduced < len(reduced) else (
        [] if ones_reduced == 0 else [{"activators": ess_i, "inhibitors": []}
                                      for ess_i in [[]]])
    n_clauses = max(1, len(clauses)) if ones_reduced else 0
    one_set_full = ones_reduced * (2 ** len(free_coordinates(column, n)))
    return {
        "n": n,
        "one_set_size": sum(column),
        "essential_variables": ess,
        # deprecated key, kept so Level-3 experiments and stored artefacts
        # resolve; the name is wrong for the reason in this module's docstring
        # (GLOSSARY sec.1e -- *pivot* is a finance term)
        "pivots_essential_bits": ess,
        "free_coordinates": free_coordinates(column, n),
        # deprecated key, kept so Level-3 experiments and stored artefacts resolve
        "sumando_bits": free_coordinates(column, n),
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
