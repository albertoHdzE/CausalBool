"""Code lengths in bits — **G1**: MDL is the judge, not similarity.

A candidate counts only if it is *strictly shorter* than the best naive description of
the target. Nothing here returns a similarity, a percentage or a distance; an embedding
distance has no units and must never be summed into one of these budgets (**G2**).

The baseline is deliberately the *stronger* of two parameter-free-ish naive codes, so
the burden is on the OEIS explanation to beat the better competitor rather than a
strawman:

  L0  Elias-delta, i.i.d., no parameters at all.
  L1  two-part empirical code: the histogram, then the sequence under it.

`baseline_bits` returns ``min(L0, L1)``. This is conservative in the direction that
matters — it makes a reported gain harder to obtain, not easier.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import asdict, dataclass


def elias_delta_bits(x: int) -> float:
    """Length of the Elias delta codeword for a positive integer ``x``.

    delta(x) = gamma(floor(log2 x) + 1) followed by the low bits of x, giving
    floor(log2 x) + 2*floor(log2(floor(log2 x) + 1)) + 1 bits.
    """
    if x < 1:
        raise ValueError(f"Elias delta codes positive integers only, got {x}")
    n = int(math.floor(math.log2(x)))
    return n + 2 * int(math.floor(math.log2(n + 1))) + 1


def _shift(x: int) -> int:
    """Map any integer into the positive integers so a universal code applies."""
    return 2 * x + 1 if x >= 0 else -2 * x


def elias_bits(seq: Sequence[int]) -> float:
    """L0 — i.i.d. Elias-delta code over a sequence of arbitrary integers."""
    return sum(elias_delta_bits(_shift(int(x))) for x in seq)


def histogram_bits(seq: Sequence[int]) -> float:
    """L1 — two-part code: pay for the empirical histogram, then code under it.

    Model cost is the alphabet (each distinct symbol, Elias-delta coded) plus its
    counts; data cost is the empirical entropy times the length. Both parts are
    counted, so this is a genuine description length and not a plug-in entropy.
    """
    n = len(seq)
    if n == 0:
        return 0.0
    counts: dict[int, int] = {}
    for x in seq:
        counts[int(x)] = counts.get(int(x), 0) + 1
    k = len(counts)
    model = elias_delta_bits(k) + sum(
        elias_delta_bits(_shift(s)) + elias_delta_bits(c) for s, c in counts.items()
    )
    data = -sum(c * math.log2(c / n) for c in counts.values())
    return model + data


def baseline_bits(seq: Sequence[int]) -> float:
    """The naive description length a candidate must strictly beat (G1)."""
    if not len(seq):
        return 0.0
    return min(elias_bits(seq), histogram_bits(seq))


@dataclass(frozen=True)
class MatchScore:
    """The MDL adjudication of one candidate OEIS explanation of a target."""

    a_number: str
    corpus_size: int
    target_len: int
    match_len: int  # terms of the target covered by the OEIS window
    target_offset: int  # where in the target the window starts
    entry_offset: int  # where in the OEIS entry the window starts
    baseline_bits: float
    pointer_bits: float
    address_bits: float
    residual_bits: float

    @property
    def model_bits(self) -> float:
        return self.pointer_bits + self.address_bits + self.residual_bits

    @property
    def gain_bits(self) -> float:
        """Bits saved. **Strictly positive is the only thing that counts (G1).**"""
        return self.baseline_bits - self.model_bits

    @property
    def counts(self) -> bool:
        return self.gain_bits > 0

    def to_dict(self) -> dict:
        d = asdict(self)
        d.update(model_bits=self.model_bits, gain_bits=self.gain_bits, counts=self.counts)
        return d


def score_match(
    target: Sequence[int],
    a_number: str,
    corpus_size: int,
    target_offset: int,
    entry_offset: int,
    match_len: int,
) -> MatchScore:
    """Score `target` explained as "a window of OEIS entry `a_number`, plus a residual".

    The description is: name the entry, say where the shared window sits in each
    sequence, say how long it is, then spell out the target terms the window does not
    cover. ``log2(corpus_size)`` is the pointer cost, and it is exactly the
    look-elsewhere correction for having chosen this entry out of the whole corpus —
    which is why MDL, not a similarity score, is the right adjudicator here (G2).
    """
    n = len(target)
    if not 0 <= target_offset <= n or not 0 <= match_len <= n - target_offset:
        raise ValueError("match window falls outside the target")
    pointer = math.log2(corpus_size)
    address = (
        elias_delta_bits(target_offset + 1)
        + elias_delta_bits(entry_offset + 1)
        + elias_delta_bits(match_len + 1)
    )
    # The residual must be coded by the *same model class* as the baseline. Coding it
    # with a strictly weaker code (plain Elias, while the baseline may use the histogram)
    # would rig every comparison against the match and manufacture negative gains that
    # are an artefact of the scorer, not of the data.
    residual = list(target[:target_offset]) + list(target[target_offset + match_len :])
    return MatchScore(
        a_number=a_number,
        corpus_size=corpus_size,
        target_len=n,
        match_len=match_len,
        target_offset=target_offset,
        entry_offset=entry_offset,
        baseline_bits=baseline_bits(target),
        pointer_bits=pointer,
        address_bits=address,
        residual_bits=baseline_bits(residual),
    )

# ---------------------------------------------------------------------------
# G1b gate — a code length must actually be a code length
# ---------------------------------------------------------------------------


class NotACodeLength(ValueError):
    """Raised when a quantity is used as an `L(·)` term but cannot be one."""


def validate_code_length(
    fn,
    name: str,
    n_trials: int = 5,
    seed: int = 0,
    kraft_k: int = 64,
    floor_m: int = 32,
    floor_slack: float = 0.95,
) -> None:
    """**Hard gate, two-sided since 2026-08-23.** Refuse anything not on a code-length
    scale — from either direction.

    **Upper bound (the original check).** You can always transmit an object by copying
    it, so `L(x) <= |x| + O(log|x|)`. Any quantity exceeding its object's own real code
    length on random data is not a code length, whatever its units are labelled. This
    caught raw BDM (~2.7x the length of a random string) on 2026-08-21; BDM still fails
    here **by design** — it is a valid upper bound on K (Zenil et al. Prop. 1) and can
    never manufacture hypercompression, but it is far too loose to compare in raw bits
    against a practical code. Use `seqdecon.bdm.nbdm` or
    `seqdecon.bdm.bdm_vs_matched_null` instead.

    **Lower bounds (added after `bitacora/05` B2, which showed `lambda seq: 0.0` passed
    the one-sided gate — unbounded hypercompression admitted).** A code length must also
    be *achievable*:

    - **Sampled Kraft.** `kraft_k` distinct objects of one fixed length must satisfy
      `Σ 2^-L(x) <= 1`. A sampled sum above 1 proves infeasibility, since the domain-wide
      sum is at least the sampled one. This catches constant short lengths (`L = 0`,
      `L = 1`); it is structurally blind when each term is already long, and it sits
      exactly at 1.0 for `L = log2(n)` — so it is necessary, not sufficient.
    - **Entropy floor.** On a source of known entropy (uniform over `{1..64}`, so
      `H = 6` bits/term), the mean of `L` over `floor_m` objects must reach
      `floor_slack · n·H`. Shannon's bound says a genuinely decodable code has
      expectation `>= n·H`; genuine two-part codes clear it with room to spare. This
      catches what Kraft cannot see: `0.5 × elias` (Kraft-invisible at ~320 bits/object)
      and plug-in empirical entropy with no model cost, both of which under-price the
      object.

    **What this gate is still not:** a proof of Kraft validity over the whole domain.
    A code tailored to the probe sources — near-zero exactly on uniform 64-term draws,
    truthful elsewhere — would pass. The gate is a tripwire against the two failure
    modes that have actually occurred here (units-scale looseness; hypercompression),
    enforced at import for every declared `L(·)`.
    """
    import random as _random

    rng = _random.Random(seed)

    for _ in range(n_trials):
        n = rng.choice([64, 128, 256])
        seq = [rng.randint(1, 64) for _ in range(n)]
        raw = elias_bits(seq)  # a genuine code length for this object
        got = fn(seq)
        if got > 2.0 * raw:
            raise NotACodeLength(
                f"{name!r} returns {got:.0f} where a real code needs {raw:.0f} bits for "
                f"the same {n}-term object. A code length cannot exceed the cost of "
                f"copying the object. This is not admissible as an L(.) term in an MDL "
                f"budget (G1b); normalize it or compare it against a matched null."
            )

    seen: set[tuple[int, ...]] = set()
    kraft_sum = 0.0
    while len(seen) < kraft_k:
        seq = tuple(rng.randint(1, 64) for _ in range(64))
        if seq in seen:
            continue
        seen.add(seq)
        kraft_sum += 2.0 ** (-float(fn(list(seq))))
    if kraft_sum > 1.0 + 1e-9:
        raise NotACodeLength(
            f"{name!r} fails the sampled Kraft check: Σ 2^-L = {kraft_sum:.4g} > 1 over "
            f"{kraft_k} distinct 64-term objects. No decodable code can assign lengths "
            f"this short to this many distinct objects (G1b, lower bound)."
        )

    n_terms, alphabet = 64, 64
    floor = floor_slack * n_terms * math.log2(alphabet)
    vals = [
        fn([rng.randint(1, alphabet) for _ in range(n_terms)]) for _ in range(floor_m)
    ]
    mean = sum(vals) / len(vals)
    if mean < floor:
        raise NotACodeLength(
            f"{name!r} fails the entropy floor: mean L = {mean:.1f} bits over "
            f"{floor_m} draws from a uniform source needing {n_terms * math.log2(alphabet):.0f} "
            f"bits (floor {floor:.0f}). A decodable code cannot systematically under-price "
            f"its objects — this would manufacture hypercompression (G1b, lower bound)."
        )


#: Codes admissible as `L(·)` terms, each validated by :func:`validate_code_length` at
#: import. Adding a member here without it passing the gate is a hard error, by design.
ADMISSIBLE_CODES: dict[str, object] = {
    "elias": elias_bits,
    "histogram": histogram_bits,
}

for _nm, _fn in ADMISSIBLE_CODES.items():
    validate_code_length(_fn, _nm)
