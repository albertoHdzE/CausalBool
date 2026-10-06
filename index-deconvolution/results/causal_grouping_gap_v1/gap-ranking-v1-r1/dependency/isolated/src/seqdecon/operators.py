"""The operator group — declared, versioned and hashed in advance.

`TRANSFERENCE.md` §3 requires that the operator group be fixed *before* an experiment
and that growing it opportunistically mid-experiment invalidates the null. So the group
is a literal declaration in this module, and :func:`operator_group_hash` fingerprints it.
Every result must record that hash; a result whose hash does not match the group in force
is not comparable.

Two families live here.

**Occurrence extractors** map a series to the integer positions of its salient events.
The audit in `TRANSFERENCE.md` §5 found that `directional_change_pivots` cannot be
applied to binary series — it uses a relative reversal threshold guarded on
``ext_val > 0`` — so the positive controls need a different member. That is the whole
argument for an abstraction rather than a single pivot function.

**Digit/mantissa operators** are gated by **G3**: they may only be applied to
quantities declared dimensionless. Raw prices carry currency, base and split history;
their digits are Level-4 trend contamination in a new costume. The gate is enforced by
:func:`digits`, which raises on an undeclared or dimensioned input.
"""

from __future__ import annotations

import hashlib
import json
import math
from collections.abc import Sequence
from dataclasses import dataclass
from typing import NamedTuple

OPERATOR_GROUP_VERSION = "causal-grouping-gap-v1"


# ---------------------------------------------------------------------------
# Occurrence extractors
# ---------------------------------------------------------------------------


class Pivot(NamedTuple):
    index: int
    value: float
    kind: int  # +1 local maximum, -1 local minimum


def directional_change_pivots(series: Sequence[float], theta: float) -> list[Pivot]:
    """Causal, one-pass recovery of the **financial pivots** at reversal scale ``theta``.

    **Definition (GLOSSARY.md §1, settled 2026-08-22).** A *pivot* is a position that a
    **causal** process — one with no look-ahead — reproduces **exactly**; what no such
    process reaches is the **residual**. In finance: a **financial pivot** is an *oracle
    action point* that this construction, run at ``theta = c``, recovers exactly without
    seeing the future. The oracle is God's answer key, computed *with* the future; the
    residual is the part of it that causality cannot reach.

    **What follows is the recovery method, not the definition.** Defining a pivot as
    "whatever this walk returns" was confusion source #1 (`GLOSSARY.md` §2): the walk is
    a procedure that always returns *something*, whereas the definition carries a claim
    that can fail. The two places that made that error — the sibling's
    `notebooks/09_oracle_perfect_trader.ipynb` Step 1 and `level5/pivots.py` — were
    **fixed there on 2026-08-22** (commits `cba2eec`, `4d9a959`, branch `clean`); this
    docstring describes the method with the distinction built in.

    Measured over 12 series x 4 theta with theta matched to c: containment
    56,500/56,509 = 0.9998, exact on 42 of 48 pairs, oracle residual 1.37%.

    Not to be confused with the **decimal anchor** ``P(I_c) = sum_{i in I_c} w(i)`` of the
    Boolean indexing method, which is the decimal *encoding* of a pivot set, not the set.

    **The complement's name does not transfer** (GLOSSARY.md §1c). ``pivot``/``residual``
    is a partition by causal reachability and is **lossy** — the residual is what no causal
    process reaches. ``decimal family``/``sumandos`` is the Boolean method's compressed form
    and is **lossless** — ``Dec(L,S) = {l+s}`` reconstructs the repertoire exactly, so
    sumandos are fully determined, not unreachable. There is no residual in the Boolean
    method and no sumando in finance; pairing *pivot* with *sumandos* is a category error.

    **Positive series only** — the threshold is relative, so the construction is invariant
    to multiplicative rescaling but undefined at or below zero.
    """
    if theta <= 0:
        raise ValueError("theta must be positive")
    if not series:
        return []
    if min(series) <= 0:
        raise ValueError(
            "directional_change_pivots requires a strictly positive series; for binary "
            "or sign-changing input use binary_flip_times or level_crossing_times"
        )
    pivots: list[Pivot] = []
    mode = 0
    ext_val, ext_idx = series[0], 0
    for i in range(1, len(series)):
        x = series[i]
        if mode >= 0 and x > ext_val:
            ext_val, ext_idx, mode = x, i, 1
        elif mode <= 0 and x < ext_val:
            ext_val, ext_idx, mode = x, i, -1
        if mode == 1 and ext_val > 0 and x <= ext_val * (1 - theta):
            pivots.append(Pivot(ext_idx, ext_val, +1))
            mode, ext_val, ext_idx = -1, x, i
        elif mode == -1 and ext_val > 0 and x >= ext_val * (1 + theta):
            pivots.append(Pivot(ext_idx, ext_val, -1))
            mode, ext_val, ext_idx = 1, x, i
    return pivots


def pivot_times(pivots: Sequence[Pivot]) -> list[int]:
    return [p.index for p in pivots]


def binary_flip_times(series: Sequence[int]) -> list[int]:
    """Indices at which a binary series changes value.

    The occurrence-set extractor for the CA and biological positive controls. A
    financial pivot is the time at which a price series reverses; a flip is the
    time at which a binary series reverses. Same object, domain-appropriate member.
    """
    vals = set(series)
    if not vals <= {0, 1}:
        raise ValueError(f"binary_flip_times requires a 0/1 series; saw {sorted(vals)[:5]}")
    return [i for i in range(1, len(series)) if series[i] != series[i - 1]]


def level_crossing_times(series: Sequence[float], level: float) -> list[int]:
    """Indices at which a series crosses ``level`` — the general-purpose fallback."""
    return [
        i
        for i in range(1, len(series))
        if (series[i - 1] < level <= series[i]) or (series[i - 1] >= level > series[i])
    ]


def token_occurrence_frames(tokens: Sequence[int], value: int) -> list[int]:
    """Every zero-based frame at which a token sequence equals ``value``.

    The occurrence-set extractor for finite symbolic sequences: block tokens of a
    sampled Boolean-network trajectory, or any other sequence of nonnegative integer
    symbols. It is occurrence extraction, not change detection — consecutive equal
    frames are all returned, so a constant sequence yields every frame. Feed the result
    to :func:`gaps`.

    The whole input is validated before any result is returned: ``tokens`` and ``value``
    must be nonnegative built-in integers, and ``bool`` is refused. An empty sequence or
    an absent value yields ``[]``.
    """
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(f"token_occurrence_frames requires a nonnegative int value; saw {value!r}")
    if isinstance(tokens, (str, bytes)):
        raise ValueError("token_occurrence_frames requires a sequence of ints, not a string")
    try:
        seq = list(tokens)
    except TypeError as exc:
        raise ValueError("token_occurrence_frames requires a finite sequence of ints") from exc
    for i, t in enumerate(seq):
        if isinstance(t, bool) or not isinstance(t, int) or t < 0:
            raise ValueError(
                f"token_occurrence_frames requires nonnegative int tokens; saw {t!r} at {i}"
            )
    return [i for i, t in enumerate(seq) if t == value]


def gaps(occurrences: Sequence[int]) -> list[int]:
    """First differences of an occurrence set — the integer target OEIS can match."""
    return [occurrences[i + 1] - occurrences[i] for i in range(len(occurrences) - 1)]


# ---------------------------------------------------------------------------
# G3 — digit operators, dimensionless only
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Quantity:
    """A number with an explicit dimensionality declaration.

    ``dimensionless=True`` asserts that the value is invariant to the unit, currency,
    base and corporate-action conventions of its source — i.e. that it is the same
    number for every observer. Hawkes branching ratio, a Hurst exponent, a Fano
    exponent, an R^2 and a Benford-normalized mantissa qualify. A price does not.
    """

    value: float
    name: str
    dimensionless: bool
    provenance: str = ""


class G3Violation(ValueError):
    """Raised when a digit-level operator is aimed at a dimensioned quantity."""


def digits(q: Quantity, n: int = 12, base: int = 10) -> list[int]:
    """The first ``n`` digits of a dimensionless quantity's expansion. **G3 gate.**

    This is the hard gate `TRANSFERENCE.md` §3 asks for, the analogue of the sibling
    project's ``trend_contamination`` guard. It refuses anything not explicitly declared
    dimensionless, so a raw price cannot reach a digit operator by accident.
    """
    if not isinstance(q, Quantity):
        raise G3Violation(
            "G3: digit operators accept only a declared Quantity, not a bare number. "
            "Wrap the value and state whether it is dimensionless."
        )
    if not q.dimensionless:
        raise G3Violation(
            f"G3: {q.name!r} is declared dimensioned. Digits of a dimensioned quantity "
            "are an artefact of its units, not of its generating structure."
        )
    x = abs(q.value)
    if x == 0 or not math.isfinite(x):
        raise G3Violation(f"G3: {q.name!r} has no digit expansion (value {q.value})")
    if base != 10:
        # repeated multiply-and-truncate, valid for bases where no decimal rounding
        # convention applies; still bounded by float precision
        x /= base ** math.floor(math.log(x, base))
        out = []
        for _ in range(n):
            d = int(x)
            out.append(d)
            x = (x - d) * base
        return out

    # Base 10: extract via correctly-rounded decimal formatting. Truncating the binary
    # float directly reads its representation error as digits -- 0.69 comes out
    # 6,8,9,9 rather than 6,9,0,0, which would defeat the inverse-symbolic lookup this
    # channel exists for. A float64 carries at most 17 significant decimal digits.
    if not 1 <= n <= 17:
        raise ValueError(f"base-10 digits: n must be in 1..17 (float64 precision), got {n}")
    mantissa = f"{x:.{n - 1}e}".split("e")[0].replace(".", "").replace("-", "")
    return [int(c) for c in mantissa[:n]]


# ---------------------------------------------------------------------------
# The declaration
# ---------------------------------------------------------------------------

#: Every operator in force for Phase 1, with the parameters it is swept over.
#: Phase 1 is deliberately the *identity* element applied to an occurrence-gap
#: channel: no transform closure, no decomposition, no digit channel. Those are
#: Phase 2 and later, and adding one here would invalidate every null below.
OPERATOR_GROUP: dict[str, object] = {
    "version": OPERATOR_GROUP_VERSION,
    "occurrence_extractors": {
        "directional_change_pivots": {
            "domain": "strictly positive real series",
            "params": {"theta": [0.01, 0.02, 0.04, 0.08]},
            "source": "index-deconvolution level5/pivots.py, behaviour preserved",
        },
        "binary_flip_times": {
            "domain": "binary 0/1 series",
            "params": {},
            "source": "new; the CA/bio member the §5 audit showed was missing",
        },
    },
    "occurrence_frame_extractors": {
        "token_occurrence_frames": {
            "domain": "finite sequence of nonnegative integer tokens",
            "params": {"value": "nonnegative integer target token"},
            "source": "causal-grouping-gap-v1 (CausalBool gap-ranking-v1-r1, ticket U2)",
        },
    },
    "target_channel": {
        "gaps": "first differences of the occurrence set; the integer sequence matched"
    },
    "sequence_operators": {
        "identity": "the target is matched as given — the identity element of the group"
    },
    "digit_channel": {
        "status": "declared but NOT exercised in Phase 1",
        "gate": "G3 — Quantity.dimensionless must be True",
    },
}


def operator_group_hash() -> str:
    """SHA-256 of the canonical JSON of :data:`OPERATOR_GROUP`.

    Record this with every result. If it differs, the operator group changed and the
    nulls are not comparable.
    """
    blob = json.dumps(OPERATOR_GROUP, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()
