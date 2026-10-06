"""Tests for the Phase 1 machinery: operators, the G3 gate, MDL, nulls, and the matcher.

The matcher tests use the real corpus index and skip cleanly when it is absent. The
rest run everywhere. No mocked OEIS data anywhere — a planted match is a real OEIS entry.
"""

from __future__ import annotations

import math
import random
from pathlib import Path

import pytest

from seqdecon import nulls as N
from seqdecon.mdl import (
    baseline_bits,
    elias_bits,
    elias_delta_bits,
    histogram_bits,
    score_match,
)
from seqdecon.operators import (
    G3Violation,
    Quantity,
    binary_flip_times,
    digits,
    directional_change_pivots,
    gaps,
    level_crossing_times,
    operator_group_hash,
    pivot_times,
)

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / "indices" / "corpus_k6.npz"
DB = ROOT / "corpus" / "oeis.duckdb"
needs_index = pytest.mark.skipif(not CACHE.exists(), reason="corpus index not built")


# --- operators ------------------------------------------------------------


def test_dc_pivots_are_invariant_to_rescaling():
    """The relative threshold is what makes the construction representation-free."""
    s = [1.0, 1.2, 1.1, 1.4, 0.9, 1.3, 1.0, 1.6, 1.1]
    a = pivot_times(directional_change_pivots(s, 0.1))
    b = pivot_times(directional_change_pivots([7.5 * x for x in s], 0.1))
    assert a == b


def test_dc_pivots_refuse_binary_input():
    """TRANSFERENCE §5: this is the audit finding that forced the operator abstraction."""
    with pytest.raises(ValueError, match="strictly positive"):
        directional_change_pivots([0, 1, 0, 1, 1, 0], 0.1)


def test_dc_pivots_refuse_nonpositive_theta():
    with pytest.raises(ValueError):
        directional_change_pivots([1.0, 2.0, 1.0], 0.0)


def test_binary_flip_times_are_the_change_points():
    assert binary_flip_times([0, 0, 1, 1, 1, 0, 1]) == [2, 5, 6]


def test_binary_flip_times_refuse_nonbinary():
    with pytest.raises(ValueError, match="0/1"):
        binary_flip_times([0, 1, 2])


def test_gaps_are_first_differences():
    assert gaps([2, 5, 6, 10]) == [3, 1, 4]
    assert gaps([7]) == []


def test_level_crossings_catch_both_directions():
    assert level_crossing_times([0.0, 2.0, 0.0], 1.0) == [1, 2]


def test_operator_group_hash_is_stable_and_pinned():
    """If this fails the operator group changed and every recorded null is stale."""
    assert operator_group_hash() == (
        "5d11bddea00fb1f16c5a01694f3fd49c9a3a7ad9ed703a506a6e894937e5ad3e"
    )


# --- G3 -------------------------------------------------------------------


def test_g3_allows_a_declared_dimensionless_quantity():
    n = Quantity(0.69, "hawkes_branching_ratio", dimensionless=True)
    assert digits(n, 4) == [6, 9, 0, 0]


def test_g3_blocks_a_dimensioned_quantity():
    price = Quantity(431.27, "NVDA_close_usd", dimensionless=False)
    with pytest.raises(G3Violation, match="dimensioned"):
        digits(price)


def test_g3_blocks_a_bare_number():
    """A raw float must not be able to reach a digit operator by accident."""
    with pytest.raises(G3Violation, match="declared Quantity"):
        digits(431.27)  # type: ignore[arg-type]


def test_g3_digits_survive_binary_float_representation():
    """0.69 must read 6,9,0,0 — not the 6,8,9,9 its float representation truncates to."""
    assert digits(Quantity(0.69, "n", dimensionless=True), 4) == [6, 9, 0, 0]
    assert digits(Quantity(0.34, "H", dimensionless=True), 3) == [3, 4, 0]
    assert digits(Quantity(1 / 3, "third", dimensionless=True), 5) == [3, 3, 3, 3, 3]


def test_g3_digits_reject_precision_beyond_float64():
    with pytest.raises(ValueError, match="1..17"):
        digits(Quantity(0.69, "n", dimensionless=True), 25)


def test_g3_digits_are_scale_free():
    """Mantissa normalization: the same number in different units gives the same digits."""
    a = Quantity(0.5, "alpha", dimensionless=True)
    b = Quantity(500.0, "alpha_scaled", dimensionless=True)
    assert digits(a, 5) == digits(b, 5)


# --- MDL ------------------------------------------------------------------


def test_elias_delta_matches_known_lengths():
    assert elias_delta_bits(1) == 1
    assert elias_delta_bits(2) == 4
    # delta(4) = gamma(3)="011" then the 2 low bits of 4 -> 5 bits
    assert elias_delta_bits(4) == 5
    assert elias_delta_bits(8) == 8


def test_elias_delta_rejects_nonpositive():
    with pytest.raises(ValueError):
        elias_delta_bits(0)


def test_elias_handles_negative_terms():
    """OEIS carries signed sequences; the code must not choke on them."""
    assert elias_bits([-3, 0, 5]) > 0


def test_histogram_code_beats_elias_on_a_repetitive_sequence():
    seq = [1] * 500
    assert histogram_bits(seq) < elias_bits(seq)
    assert baseline_bits(seq) == histogram_bits(seq)


def test_baseline_is_the_stronger_of_the_two_codes():
    for seq in ([1] * 50, [17, 3, 291, 8], list(range(1, 60))):
        assert baseline_bits(seq) == min(elias_bits(seq), histogram_bits(seq))


def test_no_match_cannot_gain_bits():
    """G1: naming an entry and explaining nothing must cost, never save."""
    tgt = [3, 1, 4, 1, 5, 9, 2, 6, 5, 3, 5, 8, 9, 7, 9]
    s = score_match(tgt, "A000796", 398520, target_offset=0, entry_offset=0, match_len=0)
    assert s.gain_bits < 0
    assert not s.counts


def test_full_match_gains_a_lot():
    tgt = list(range(100, 160))
    s = score_match(tgt, "A000027", 398520, 0, 99, len(tgt))
    assert s.residual_bits == 0
    assert s.gain_bits > 0 and s.counts


def test_pointer_cost_is_the_look_elsewhere_correction():
    tgt = [5] * 40
    small = score_match(tgt, "A1", 10, 0, 0, 10)
    large = score_match(tgt, "A1", 400_000, 0, 0, 10)
    assert large.pointer_bits > small.pointer_bits
    assert large.gain_bits < small.gain_bits


def test_score_match_rejects_a_window_outside_the_target():
    with pytest.raises(ValueError):
        score_match([1, 2, 3], "A1", 100, target_offset=2, entry_offset=0, match_len=5)


# --- nulls ----------------------------------------------------------------


def test_return_shuffle_preserves_the_increment_multiset_exactly():
    rng = random.Random(0)
    s = [100.0 * math.exp(0.01 * i % 3) + i for i in range(1, 400)]
    sur = N.return_shuffle(s, rng)
    assert sorted(round(x, 9) for x in N.log_returns(s)) == pytest.approx(
        sorted(round(x, 9) for x in N.log_returns(sur)), abs=1e-6
    )


def test_block_shuffle_preserves_the_increment_multiset():
    rng = random.Random(1)
    s = [100.0 + i + (i % 7) for i in range(300)]
    sur = N.block_shuffle(s, rng, block=20)
    assert sorted(N.log_returns(s)) == pytest.approx(sorted(N.log_returns(sur)), abs=1e-9)


def test_gap_shuffle_on_a_constant_sequence_is_a_point_mass():
    """The degeneracy that forced amendment §5a of the pre-registration."""
    rng = random.Random(0)
    const = [1] * 100
    assert all(N.gap_shuffle(const, rng) == const for _ in range(20))


def test_rank_p_has_the_resolution_the_surrogate_count_buys():
    assert N.rank_p_value(1e9, [0.0] * 200) == pytest.approx(1 / 201)
    assert N.rank_p_value(-1e9, [0.0] * 200) == pytest.approx(1.0)


def test_flip_density_of_an_alternating_series_is_one():
    assert N.flip_density([0, 1] * 50) == 1.0


# --- matcher, against the real corpus -------------------------------------


@needs_index
def test_matcher_finds_a_planted_fibonacci_window():
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    m = idx.best_match([55, 89, 144, 233, 377, 610, 987, 1597, 2584, 4181])
    assert m is not None and m.a_number == "A000045"
    assert m.match_len == 10 and m.entry_offset == 10


@needs_index
def test_matcher_finds_a_planted_prime_window():
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    m = idx.best_match([101, 103, 107, 109, 113, 127, 131, 137])
    assert m is not None and m.a_number == "A000040" and m.entry_offset == 25


@needs_index
def test_matcher_reports_only_exact_windows():
    """Verify the claimed window really is elementwise equal in the corpus."""
    import duckdb

    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    target = [1, 1, 2, 3, 5, 8, 13, 21, 34, 55, 89]
    m = idx.best_match(target)
    assert m is not None
    con = duckdb.connect(str(DB), read_only=True)
    raw = con.execute(
        "SELECT terms_raw FROM sequences WHERE a_number = ?", [m.a_number]
    ).fetchone()[0]
    con.close()
    terms = [int(t) for t in raw.split(",")]
    window = terms[m.entry_offset : m.entry_offset + m.match_len]
    assert window == target[m.target_offset : m.target_offset + m.match_len]


@needs_index
def test_matcher_finds_nothing_in_random_bignums():
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    rng = random.Random(0)
    assert idx.best_match([rng.randint(10**12, 10**13) for _ in range(40)]) is None


@needs_index
def test_matcher_is_deterministic():
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    rng = random.Random(7)
    tgt = [rng.choice([1, 1, 2, 3, 5]) for _ in range(80)]
    assert idx.best_match(tgt) == idx.best_match(tgt)


@needs_index
def test_matcher_returns_none_below_seed_length():
    from seqdecon.index import SEED_K, CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    assert idx.best_match([1, 2, 3][: SEED_K - 1]) is None


# --- G1b: the code-length gate (formalizing Addendum 3) --------------------


def test_admissible_codes_pass_the_gate_at_import():
    from seqdecon.mdl import ADMISSIBLE_CODES, validate_code_length

    assert set(ADMISSIBLE_CODES) == {"elias", "histogram"}
    for nm, fn in ADMISSIBLE_CODES.items():
        validate_code_length(fn, nm)


def test_gate_refuses_a_quantity_that_is_not_a_code_length():
    from seqdecon.mdl import NotACodeLength, elias_bits, validate_code_length

    with pytest.raises(NotACodeLength, match="cannot exceed"):
        validate_code_length(lambda s: 5.0 * elias_bits(s), "inflated")


# --- G1b lower bounds (bitacora/05 B2: the one-sided gate admitted these) ----


def test_gate_refuses_a_zero_bit_code():
    """The unbounded-hypercompression case: L(x) = 0 for everything."""
    from seqdecon.mdl import NotACodeLength, validate_code_length

    with pytest.raises(NotACodeLength, match="Kraft"):
        validate_code_length(lambda s: 0.0, "zero")


def test_gate_refuses_a_one_bit_code():
    from seqdecon.mdl import NotACodeLength, validate_code_length

    with pytest.raises(NotACodeLength, match="Kraft"):
        validate_code_length(lambda s: 1.0, "one")


def test_gate_refuses_log_of_length():
    """Kraft sits exactly at 1.0 for this one; the entropy floor is what kills it."""
    import math

    from seqdecon.mdl import NotACodeLength, validate_code_length

    with pytest.raises(NotACodeLength, match="entropy floor"):
        validate_code_length(lambda s: math.log2(len(s)), "log2len")


def test_gate_refuses_half_of_a_real_code():
    """Kraft-invisible (each length still long); the entropy floor catches it."""
    from seqdecon.mdl import NotACodeLength, elias_bits, validate_code_length

    with pytest.raises(NotACodeLength, match="entropy floor"):
        validate_code_length(lambda s: 0.5 * elias_bits(s), "half_elias")


def test_gate_refuses_plug_in_entropy_without_model_cost():
    """Empirical entropy alone under-prices: the decoder needs the histogram too."""
    import math
    from collections import Counter

    from seqdecon.mdl import NotACodeLength, validate_code_length

    def plugin_entropy(s):
        c = Counter(s)
        return -sum(v * math.log2(v / len(s)) for v in c.values())

    with pytest.raises(NotACodeLength, match="entropy floor"):
        validate_code_length(plugin_entropy, "plugin_entropy")


# --- the arm test applies G1 (bitacora/03 Addendum 5; bitacora/05 B3) --------


def _fake_target(p_value: float, g1: bool) -> dict:
    return {
        "constant_gaps": False,
        "counts_under_G1": g1,
        "nulls": {
            "gap_shuffle": {"n_valid": 200, "p_value": p_value, "excess_bits": -1.0}
        },
    }


def test_arm_test_counts_a_hit_only_under_G1():
    """p < alpha with negative gain is not a hit: bitacora 02 §3, applied to §4."""
    from experiments.phase1_gonogo import _arm_stats

    rs = (
        [_fake_target(0.005, True) for _ in range(3)]
        + [_fake_target(0.01, False) for _ in range(3)]  # significant, gain <= 0
        + [_fake_target(0.5, True) for _ in range(6)]
    )
    a = _arm_stats(rs, "ca", alpha=0.05, policy="A")
    assert a["n_tested"] == 12
    assert a["n_significant"] == 3
    assert a["n_significant_ignoring_G1"] == 6
    assert a["binomial_p"] == pytest.approx(0.01957, abs=1e-4)
    assert a["passes"]


# --- the matcher never bridges an overflow discontinuity (Phase 2 smoke) -----


@needs_index
def test_best_match_survives_overflow_terms_and_never_bridges_them():
    """Transform products overflow int64; the query side must degrade, not crash."""
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    side = [1, 2, 3, 4, 5, 6]
    target = side + [10**30] + side
    m = idx.best_match(target)
    if m is not None:
        left_side = m.target_offset + m.match_len <= len(side)
        right_side = m.target_offset >= len(side) + 1
        assert left_side or right_side, (
            "a window bridged the overflow position at index 6"
        )


# --- top-k windows (Phase 3's expansion instrument; added additively) --------


@needs_index
def test_best_windows_finds_two_planted_entries_in_one_target():
    """Fibonacci head + primes head in one target: both entries among the top windows."""
    from seqdecon.index import CorpusIndex

    idx = CorpusIndex.open(DB, CACHE, quiet=True)
    fib = [int(x) for x in
           idx_terms(idx, 45)[:12]]  # A000045
    primes = [int(x) for x in idx_terms(idx, 40)[:12]]  # A000040
    target = fib + primes
    wins = idx.best_windows(target, 8)
    assert wins, "no windows found for a target built from two corpus heads"
    assert wins == sorted(wins, key=lambda m: (-m.match_len, m.a_number,
                                               m.target_offset))
    numbers = {w.a_number for w in wins}
    assert "A000045" in numbers and "A000040" in numbers, (
        f"planted entries missing from top-8: {numbers}")
    assert idx.best_match(target) == wins[0]
    assert idx.best_windows(target, 0) == []
    assert idx.best_windows(target, 8) == idx.best_windows(target, 8)


def idx_terms(idx, seq_id):
    import numpy as np

    sel = idx.seq_of == seq_id
    vals = idx.terms[sel][:12]
    return [int(v) for v in vals if v == v and abs(int(v)) < 2**63]


def test_window_two_sequences_offsets_are_exact():
    """Regression: left-extension once produced negative offsets and short lengths."""
    from seqdecon.index import CorpusIndex

    a = [9, 9, 1, 2, 3, 4, 5, 6, 9, 9]
    b = [7, 7, 1, 2, 3, 4, 5, 6, 8, 8]
    assert CorpusIndex.window_two_sequences(a, b) == (2, 2, 6)
    a2 = [1, 2, 3, 4, 5, 6, 0, 0]
    b2 = [5, 5, 1, 2, 3, 4, 5, 6]
    assert CorpusIndex.window_two_sequences(a2, b2) == (0, 2, 6)
    assert CorpusIndex.window_two_sequences([1, 2, 3], [1, 2, 3]) is None


def test_index_cache_round_trips_the_validity_mask():
    import numpy as np

    from seqdecon.index import CorpusIndex

    terms = np.array([1, 2, 3, 0, 5], dtype=np.int64)
    valid = np.array([True, True, True, False, True])
    idx = CorpusIndex(
        terms=terms,
        seq_of=np.array([7, 7, 7, 7, 7], dtype=np.int32),
        pos_in_seq=np.array([0, 1, 2, 3, 4], dtype=np.int32),
        seq_ids=np.array([7], dtype=np.int32),
        seed_hash=np.array([1, 2], dtype=np.uint64),
        seed_pos=np.array([0, 1], dtype=np.int64),
        n_sequences=1,
        valid=valid,
    )
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "cache.npz"
        idx.save(p)
        loaded = CorpusIndex.load(p)
        assert loaded.valid.tolist() == valid.tolist()

        bad = dict(np.load(p))
        bad.pop("valid")
        p2 = Path(d) / "stale.npz"
        np.savez(p2, **bad)
        with pytest.raises(ValueError, match="validity mask"):
            CorpusIndex.load(p2)


@pytest.mark.skipif(
    __import__("seqdecon.bdm", fromlist=["available"]).available() is False,
    reason="pybdm not installed",
)
def test_gate_refuses_raw_bdm_by_design():
    """BDM must fail: valid upper bound on K, but not on a code-length scale."""
    from seqdecon.bdm import bdm_bits, bdm_star_bits
    from seqdecon.mdl import NotACodeLength, validate_code_length

    for nm, fn in (("bdm_bits", bdm_bits), ("bdm_star_bits", bdm_star_bits)):
        with pytest.raises(NotACodeLength):
            validate_code_length(fn, nm)
