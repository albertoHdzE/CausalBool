"""BDM — algorithmic complexity as a code length, via `pybdm`.

**G1b**: BDM complements MDL, it does not replace it and is not excluded from it.
[Zenil et al., *Entropy* 20(8):605 (2018)](https://www.mdpi.com/1099-4300/20/8/605)
Proposition 1 gives `K(X) <= BDM(X) + O(log2|A|) + eps`, so BDM is an upper bound on K
and therefore a genuine achievable description length. CTM is `-log` of an empirical
output distribution over small Turing machines, Kraft-valid over its support.

Two things this module must get right, both of which are traps.

**1. Binarization must be lossless.** BDM's CTM tables are binary. Thresholding an
integer sequence to bits would *choose the result* — the `trend_contamination` trap the
sibling project already paid for. So we binarize **bijectively**, through the Elias-delta
code: no threshold, no tuning, nothing discarded, and the original sequence is
recoverable from the bitstring. The only choice is the code, which is declared.

**2. RAW BDM IS NOT ON A CODE-LENGTH SCALE — do not put it in a `min()`.**
*Corrected 2026-08-21 after I got this wrong.* Measured: `BDM(random binary string)` is
about **2.7x the string's length**, stably across lengths 120-3840. The paper itself says
"no string can have an algorithmic complexity greater than its length", so raw BDM is an
unnormalized CTM sum, not an estimate on the K scale. Proposition 1 still holds — BDM is a
valid upper bound, so it can never manufacture hypercompression — but it is a *loose* one,
and comparing it in raw bits against a practical code such as Elias or LZMA compares two
different coordinates. An earlier version of this project reported "BDM is 3x worse than
Elias" on gap sequences; that ratio (3.03) was almost entirely the 2.70 scale factor, and
the claim was withdrawn.

Use one of the two comparisons the authors actually recommend (their §8 and Fig. 11,
which use rank correlation rather than absolute values):

- :func:`nbdm` — normalized BDM in [0, 1], for comparing objects of different sizes;
- :func:`bdm_vs_matched_null` — BDM against controls randomized at the **sequence** level
  and re-binarized through the **same** Elias-delta code, so every nuisance dimension the
  measure responds to is held fixed and only the data's temporal arrangement varies.

**3. BDM is invariant to block permutation** — the authors' own §4.2 and Fig. 4, and
measured here in `tests/test_bdm.py`: permuting whole blocks leaves BDM identical, while
shuffling symbols changes it. So BDM sees order *within* a block and is blind *across*
blocks. In a programme whose thesis is that the information lives in the **order**, that
disqualifies raw BDM from adjudicating. :func:`bdm_star_bits` adds the arrangement term
BDM omits, which restores order-sensitivity and preserves Proposition 1 because it only
enlarges the bound.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from functools import lru_cache

import numpy as np

from seqdecon.mdl import elias_delta_bits

BDM_BLOCK_SIZE = 12  # pybdm's 1-D CTM table width


@lru_cache(maxsize=2)
def _engine(ndim: int):
    # pybdm 0.1.0 imports `pkg_resources`, which setuptools deprecated. The warning is
    # about pybdm's internals, not our use of it, and it would otherwise print on every
    # call; silence it once, here, at the source rather than tolerating the noise.
    import warnings

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="pybdm.*")
        warnings.filterwarnings("ignore", category=DeprecationWarning)
        warnings.filterwarnings("ignore", category=SyntaxWarning)
        from pybdm import BDM as _BDM  # lazy: optional dependency

        return _BDM(ndim=ndim)


def _shift(x: int) -> int:
    return 2 * x + 1 if x >= 0 else -2 * x


def elias_delta_code(x: int) -> str:
    """The Elias-delta codeword for a positive integer, as a bit string."""
    if x < 1:
        raise ValueError(f"Elias delta codes positive integers only, got {x}")
    n = x.bit_length() - 1  # floor(log2 x)
    ln = n + 1
    prefix = "0" * (ln.bit_length() - 1) + bin(ln)[2:]  # Elias gamma of n+1
    suffix = bin(x)[3:] if n else ""  # low bits of x, leading 1 implied
    return prefix + suffix


def binarize(seq: Sequence[int]) -> np.ndarray:
    """Lossless, threshold-free bit representation of an integer sequence.

    Bijective by construction — Elias-delta is a prefix code, so the bitstring can be
    decoded back to the sequence. Nothing is chosen, so nothing can be chosen wrongly.
    """
    bits = "".join(elias_delta_code(_shift(int(x))) for x in seq)
    return np.array([int(b) for b in bits], dtype=int)


def bdm_bits(seq: Sequence[int]) -> float:
    """Raw BDM of the sequence's lossless bit representation, in bits."""
    b = binarize(seq)
    if len(b) < BDM_BLOCK_SIZE:
        return float(elias_delta_bits(max(len(b), 1)))
    return float(_engine(1).bdm(b))


def arrangement_bits(seq: Sequence[int]) -> float:
    """`log2(N! / prod n_i!)` over the block multiset — the term raw BDM omits.

    This is exactly the information BDM throws away by being permutation-invariant: how
    the blocks are *arranged*, as opposed to which blocks are present and how often.
    """
    b = binarize(seq)
    blocks = [tuple(b[i : i + BDM_BLOCK_SIZE]) for i in range(0, len(b), BDM_BLOCK_SIZE)]
    if len(blocks) < 2:
        return 0.0
    counts: dict[tuple, int] = {}
    for blk in blocks:
        counts[blk] = counts.get(blk, 0) + 1
    total = math.lgamma(len(blocks) + 1) - sum(math.lgamma(c + 1) for c in counts.values())
    return total / math.log(2)


def bdm_star_bits(seq: Sequence[int]) -> float:
    """**BDM\\*** = BDM + arrangement cost — order-repaired, still an upper bound on K.

    Adding a non-negative term to an upper bound leaves it an upper bound, so
    Proposition 1 survives. Unlike raw BDM this distinguishes a sequence from a
    block-permutation of itself, which is the distinction this programme is *about*.
    """
    return bdm_bits(seq) + arrangement_bits(seq)


def nbdm(seq: Sequence[int]) -> float:
    """Normalized BDM in [0, 1] — the paper's §8 measure for cross-size comparison.

    0 is maximally regular, 1 maximally algorithmically random. Use this, or
    :func:`bdm_vs_matched_null`, instead of raw BDM whenever two objects are compared.
    """
    b = binarize(seq)
    return float(_engine(1).nbdm(b))


def bdm_vs_matched_null(
    seq: Sequence[int],
    n_null: int = 32,
    seed: int = 0,
    mode: str = "permute",
) -> dict[str, float]:
    """BDM of ``seq`` against controls matched on **every nuisance dimension**.

    *Corrected 2026-08-23 (`bitacora/03` Addendum 4; `bitacora/05` B1). The previous
    null permuted the **bits of the Elias-delta codeword stream**. That destroys the
    structure the CODE imposes, not the structure the DATA has — a valid codeword
    stream is more regular than an i.i.d. bitstream by construction — so ``z < 0`` was
    guaranteed for any integer sequence whatsoever (a constant scored z ≈ −24). The
    real data was the *least* extreme thing tested. Density was matched; codeword
    syntax, the dominant nuisance, was not.*

    The corrected null randomizes the **sequence** and re-binarizes through the same
    code, so both sides carry identical codeword syntax:

    - ``mode="permute"`` — a permutation of the observed values. Matches the term
      count and the value multiset exactly; since a permutation reuses the same
      codewords, the bitstream's length **and** density are held *identically*, not
      merely in distribution.
    - ``mode="iid"`` — i.i.d. draws from the observed values. Same in expectation;
      kept because it is the form named in the review.

    What remains for z to measure is the one thing left standing: whether the
    *arrangement* of the sequence is more structured than its own marginal shuffled.

    A constant (or otherwise permutation-invariant) sequence makes every surrogate
    equal the observation, so ``null_sd`` is 0 and ``z`` is 0 with ``degenerate=1``:
    such a target is untestable by this instrument, not "perfectly structured".

    Returns the observed value, the null mean and sd, a z-score (negative means more
    structured than its own shuffled marginal), and the matched nuisance parameters.
    """
    if mode not in ("permute", "iid"):
        raise ValueError(f"mode must be 'permute' or 'iid', got {mode!r}")
    x = [int(v) for v in seq]
    obs = bdm_bits(x)
    rng = np.random.default_rng(seed)
    vals = []
    for _ in range(n_null):
        if mode == "permute":
            order = rng.permutation(len(x))
            sur = [x[i] for i in order]
        else:
            sur = [int(x[i]) for i in rng.integers(0, len(x), len(x))]
        vals.append(bdm_bits(sur))
    mu = float(np.mean(vals))
    sd = float(np.std(vals, ddof=1)) if len(vals) > 1 else 0.0
    spread = float(np.max(vals) - np.min(vals)) if vals else 0.0
    degenerate = spread <= 1e-9 * max(1.0, abs(mu))
    b = binarize(x)
    n, ones = len(b), int(b.sum())
    return {
        "bdm": obs,
        "null_mean": mu,
        "null_sd": 0.0 if degenerate else sd,
        "z": (obs - mu) / sd if (sd and not degenerate) else 0.0,
        "ratio_to_null": obs / mu if mu else float("nan"),
        "n_bits": float(n),
        "density": ones / n if n else 0.0,
        "n_terms": float(len(x)),
        "degenerate": 1.0 if degenerate else 0.0,
        "mode": mode,
    }


def bdm_2d_bits(grid: np.ndarray) -> float:
    """BDM of a 2-D binary array — the CA space-time diagram case, BDM's home turf."""
    a = np.asarray(grid, dtype=int)
    if a.ndim != 2:
        raise ValueError(f"expected a 2-D array, got shape {a.shape}")
    if set(np.unique(a).tolist()) - {0, 1}:
        raise ValueError("bdm_2d_bits requires a binary array")
    return float(_engine(2).bdm(a))


def available() -> bool:
    """Whether `pybdm` can be imported — it is an optional dependency."""
    try:
        _engine(1)
    except Exception:
        return False
    return True
