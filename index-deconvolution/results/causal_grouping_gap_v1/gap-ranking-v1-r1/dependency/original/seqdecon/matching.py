"""The matching vocabulary — normalizations, transforms, and approximate matchers.

**An open, extensible registry.** New members are expected and welcome; that is the whole
point of G4's open-vocabulary stance applied one level down. What is *not* negotiable is
that every member is declared and hashed before a run (`TRANSFERENCE.md` §3), because
each one multiplies the look-elsewhere burden.

Three kinds live here, and the distinction matters:

**Normalizations** — canonicalize a target so accidental encoding choices stop blocking a
match. Dividing by the GCD is the clearest case: `(4, 8, 12)` and `(1, 2, 3)` are the same
sequence wearing different clothes, and OEIS stores only one of them. Modelled on Hugo
Pfoertner's GCD-reduced OEIS search.

**Transforms** — the classical OEIS operator family. The priority order below is not
guessed: it is **measured from our own corpus**, by counting how often each transform is
named in the `%C`, `%F`, `%N` and `%Y` fields of all 398,520 entries. Binomial (4,889
mentions), Euler (2,851), Hankel (1,149), Möbius (~1,700 across spellings), Invert (574),
Bell (347), Stirling (215), Weigh (149), boustrophedon (130), revert (67).
This is the same family `oia-searching/search_engine/advanced/engine1-5.py` scanned for,
and the same one Sloane's **Superseeker** applies before looking a sequence up.

**Approximate matchers** — the oia fuzzy matchers, re-housed. Per `TRANSFERENCE.md` §4
they are **retrieval**, never evidence: they generate candidates, and MDL decides. An
approximate match is a richer *model class* whose cost MDL prices exactly — "entry A,
here, with these k corrections" — which is what a similarity percentage structurally
cannot do.

Nothing in this module returns a verdict. Everything returns candidates or a transformed
sequence.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from math import comb, gcd
from typing import Any

MATCHING_VOCABULARY_VERSION = "0.1.0"


# ---------------------------------------------------------------------------
# Normalizations — same sequence, different clothes
# ---------------------------------------------------------------------------


def normalize_gcd(seq: Sequence[int]) -> list[int]:
    """Divide out the GCD. `(4, 8, 12) -> (1, 2, 3)`; OEIS stores only one of these."""
    g = 0
    for x in seq:
        g = gcd(g, abs(int(x)))
    return [int(x) // g for x in seq] if g > 1 else [int(x) for x in seq]


def normalize_abs(seq: Sequence[int]) -> list[int]:
    """Drop signs. Recovers a sequence stored unsigned in `%S`."""
    return [abs(int(x)) for x in seq]


def normalize_offset(seq: Sequence[int]) -> list[int]:
    """Subtract the minimum, so an additive convention cannot block a match."""
    m = min(seq) if len(seq) else 0
    return [int(x) - int(m) for x in seq]


def normalize_monic(seq: Sequence[int]) -> list[int]:
    """Divide by the first non-zero term, keeping integrality only when exact."""
    lead = next((int(x) for x in seq if x), 0)
    if lead in (0, 1):
        return [int(x) for x in seq]
    if all(int(x) % lead == 0 for x in seq):
        return [int(x) // lead for x in seq]
    return [int(x) for x in seq]


# ---------------------------------------------------------------------------
# Transforms — the classical OEIS operator family
# ---------------------------------------------------------------------------


def t_identity(seq: Sequence[int]) -> list[int]:
    """The identity element. Phase 1 used only this one."""
    return [int(x) for x in seq]


def t_differences(seq: Sequence[int]) -> list[int]:
    return [int(seq[i + 1]) - int(seq[i]) for i in range(len(seq) - 1)]


def t_partial_sums(seq: Sequence[int]) -> list[int]:
    out, run = [], 0
    for x in seq:
        run += int(x)
        out.append(run)
    return out


def t_binomial(seq: Sequence[int]) -> list[int]:
    """`b(n) = sum_k C(n,k) a(k)` — the most-cited transform in the corpus."""
    a = [int(x) for x in seq]
    return [sum(comb(n, k) * a[k] for k in range(n + 1)) for n in range(len(a))]


def t_binomial_inverse(seq: Sequence[int]) -> list[int]:
    """`b(n) = sum_k (-1)^(n-k) C(n,k) a(k)`."""
    a = [int(x) for x in seq]
    return [sum((-1) ** (n - k) * comb(n, k) * a[k] for k in range(n + 1))
            for n in range(len(a))]


def t_invert(seq: Sequence[int]) -> list[int]:
    """INVERT: if `A(x) = 1 + sum a(n)x^n`, return coefficients of `1/(2 - A(x))`."""
    a = [int(x) for x in seq]
    b: list[int] = []
    for n in range(len(a)):
        v = a[n] + sum(a[k] * b[n - 1 - k] for k in range(n))
        b.append(v)
    return b


def t_boustrophedon(seq: Sequence[int]) -> list[int]:
    """The ox-plough (zigzag) transform: build each row alternating direction."""
    a = [int(x) for x in seq]
    out: list[int] = []
    row: list[int] = []
    for n, x in enumerate(a):
        new = [x]
        for k in range(n):
            new.append(new[k] + row[n - 1 - k])
        row = new
        out.append(row[-1])
    return out


def t_run_lengths(seq: Sequence[int]) -> list[int]:
    """Lengths of maximal constant runs — the natural transform for a bursty clock."""
    if not len(seq):
        return []
    out, run = [], 1
    for i in range(1, len(seq)):
        if seq[i] == seq[i - 1]:
            run += 1
        else:
            out.append(run)
            run = 1
    out.append(run)
    return out


def t_moebius(seq: Sequence[int]) -> list[int]:
    """Möbius (Dirichlet) inversion over a 1-indexed sequence."""
    a = [int(x) for x in seq]
    n = len(a)
    b = [0] * n
    for i in range(1, n + 1):
        s = a[i - 1]
        for d in range(1, i):
            if i % d == 0:
                s -= b[d - 1]
        b[i - 1] = s
    return b


# ---------------------------------------------------------------------------
# Approximate matchers — retrieval only, never evidence
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ApproxHit:
    """A candidate alignment. Carries no verdict — MDL decides."""

    target_offset: int
    entry_offset: int
    length: int
    n_mismatch: int
    corrections: tuple[tuple[int, int], ...]  # (position within window, delta)


def approx_window(
    target: Sequence[int],
    entry: Sequence[int],
    t_off: int,
    e_off: int,
    max_mismatch: int,
) -> ApproxHit | None:
    """Extend an alignment allowing at most ``max_mismatch`` substitutions.

    Returns the corrections explicitly, because they are exactly what MDL must charge
    for: the description is "entry A, here, with these deltas".
    """
    corr: list[tuple[int, int]] = []
    i = 0
    while t_off + i < len(target) and e_off + i < len(entry):
        d = int(target[t_off + i]) - int(entry[e_off + i])
        if d:
            if len(corr) >= max_mismatch:
                break
            corr.append((i, d))
        i += 1
    # Never end a window on a correction: paying to correct the final term buys nothing
    # that shortening the window by one would not give for free.
    while corr and corr[-1][0] == i - 1:
        corr.pop()
        i -= 1
    if i == 0:
        return None
    return ApproxHit(t_off, e_off, i, len(corr), tuple(corr))


def fuzzy_drop_terms(a: Sequence[int], b: Sequence[int], max_drop: int) -> int:
    """Longest common subsequence-with-bounded-drops, the oia `fuzzy_match_t1` idea.

    Allows terms to be *skipped* in either sequence — the case that matters when an
    occurrence set has a spurious extra event or a missing one. Returns the number of
    aligned terms; retrieval only.
    """
    n, m = len(a), len(b)
    best = 0
    for start in range(n):
        i, j, drops, hits = start, 0, 0, 0
        while i < n and j < m:
            if int(a[i]) == int(b[j]):
                hits += 1
                i += 1
                j += 1
            elif drops < max_drop:
                drops += 1
                if i + 1 < n and int(a[i + 1]) == int(b[j]):
                    i += 1
                elif j + 1 < m and int(a[i]) == int(b[j + 1]):
                    j += 1
                else:
                    i += 1
                    j += 1
            else:
                break
        best = max(best, hits)
    return best


def ratio_signature(seq: Sequence[int]) -> tuple[float, ...]:
    """Successive ratios — invariant to multiplying the whole sequence by a constant.

    Retrieval aid for "is the target a *multiple* of an OEIS entry", the oia engine-2
    question, without materializing every multiple.
    """
    out = []
    for i in range(len(seq) - 1):
        d = int(seq[i])
        out.append(float(seq[i + 1]) / d if d else float("inf"))
    return tuple(out)


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------

NORMALIZATIONS: dict[str, Callable[[Sequence[int]], list[int]]] = {
    "none": t_identity,
    "gcd": normalize_gcd,
    "abs": normalize_abs,
    "offset": normalize_offset,
    "monic": normalize_monic,
}

TRANSFORMS: dict[str, Callable[[Sequence[int]], list[int]]] = {
    "identity": t_identity,
    "differences": t_differences,
    "partial_sums": t_partial_sums,
    "binomial": t_binomial,
    "binomial_inverse": t_binomial_inverse,
    "invert": t_invert,
    "boustrophedon": t_boustrophedon,
    "run_lengths": t_run_lengths,
    "moebius": t_moebius,
}

#: Corpus-measured citation counts, from the `%C/%F/%N/%Y` fields of all 398,520 entries.
#: Recorded so the priority order is evidence rather than taste.
TRANSFORM_CORPUS_CITATIONS = {
    "binomial": 4889, "euler": 2851, "hankel": 1149, "moebius": 1697,
    "invert": 574, "bell": 347, "stirling": 215, "weigh": 149,
    "boustrophedon": 130, "revert": 67, "partition": 60, "run_lengths": 52,
}

#: Not yet implemented, listed so the gap is explicit rather than invisible.
TRANSFORMS_NOT_YET_IMPLEMENTED = ("euler", "hankel", "bell", "stirling", "weigh", "revert")


def matching_vocabulary() -> dict[str, Any]:
    return {
        "version": MATCHING_VOCABULARY_VERSION,
        "normalizations": sorted(NORMALIZATIONS),
        "transforms": sorted(TRANSFORMS),
        "approximate": ["approx_window", "fuzzy_drop_terms", "ratio_signature"],
        "not_yet_implemented": list(TRANSFORMS_NOT_YET_IMPLEMENTED),
        "role": "RETRIEVAL ONLY — generates candidates; MDL adjudicates, nulls gate",
    }


def matching_vocabulary_hash() -> str:
    blob = json.dumps(matching_vocabulary(), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
