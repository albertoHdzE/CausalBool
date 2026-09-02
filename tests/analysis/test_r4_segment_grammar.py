"""AC-R4-1 — join/Kraft test for the R4 segmented gate-grammar codec.

PROTOCOL §4: "EVERY component carries a Kraft / prefix-free check
(suite-enforced), and the JOIN protocol gets its own test that must be green
BEFORE any length is quoted anywhere (AC-R4-1)."

Every positive assertion here is paired with a NEGATIVE control that shows the
same check failing on a deliberately broken code. Without that pairing a green
suite is not evidence: it could be green because the check is inert.
"""

from __future__ import annotations

import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, "src", "analysis"))

from r4_segment_grammar import (  # noqa: E402
    BitReader, BitWriter, Components, GrammarCodec, KraftViolation, Segment,
    decode_delta, decode_gamma, elias_delta, elias_gamma, is_prefix_free,
    kraft_sum, load_catalogue,
)

MAXI = 2048


@pytest.fixture(scope="module")
def codec():
    return GrammarCodec()


# ---------------------------------------------------------------------------
# component codes
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("enc", [elias_gamma, elias_delta])
def test_kraft_sum_at_most_one(enc):
    assert kraft_sum([enc(i) for i in range(1, MAXI + 1)]) <= 1.0 + 1e-12


@pytest.mark.parametrize("enc", [elias_gamma, elias_delta])
def test_prefix_free(enc):
    ok, offender = is_prefix_free([enc(i) for i in range(1, MAXI + 1)])
    assert ok, f"prefix violation between codes {offender}"


@pytest.mark.parametrize("enc,dec", [(elias_gamma, decode_gamma),
                                     (elias_delta, decode_delta)])
def test_stream_roundtrip_without_lengths(enc, dec):
    """The real prefix-free proof: decode a concatenated stream with no lengths
    transmitted alongside. Kraft <= 1 is necessary but not sufficient."""
    w = BitWriter()
    for i in range(1, MAXI + 1):
        w.write(enc(i))
    r = BitReader(w.tolist())
    assert [dec(r) for _ in range(1, MAXI + 1)] == list(range(1, MAXI + 1))
    assert r.exhausted()


def test_negative_control_kraft_detects_a_bad_code():
    """A code that assigns every integer 3 bits has Kraft sum 8*2^-3 = 1 for
    eight codewords but blows past 1 for more -- the check must see it."""
    bad = [[0, 0, 0]] * 32
    assert kraft_sum(bad) > 1.0


def test_negative_control_prefix_check_detects_a_violation():
    """'1' is a prefix of '10'. If is_prefix_free cannot see this, every
    positive prefix-free assertion above is worthless."""
    ok, offender = is_prefix_free([[1], [1, 0], [0, 0]])
    assert not ok and offender is not None


def test_negative_control_truncated_code_fails_roundtrip():
    """Chopping the leading zeros off gamma destroys self-delimitation."""
    def broken(n):
        return [int(c) for c in bin(n)[2:]]      # no length prefix
    w = BitWriter()
    for i in range(1, 33):
        w.write(broken(i))
    r = BitReader(w.tolist())
    decoded = []
    try:
        for _ in range(32):
            decoded.append(decode_gamma(r))
    except EOFError:
        pass
    assert decoded != list(range(1, 33))


# ---------------------------------------------------------------------------
# join protocol
# ---------------------------------------------------------------------------

def test_self_check_passes(codec):
    rep = codec.self_check(max_int=MAXI)
    for name in ("elias_gamma", "elias_delta"):
        assert rep[name]["kraft_ok"]
        assert rep[name]["prefix_free"]
        assert rep[name]["stream_roundtrip"]
    assert rep["join"]["all_passed"]


@pytest.mark.parametrize("segs,n", [
    ([Segment(0, 8, 0)], 8),
    ([Segment(0, 8, None, [1, 0, 1, 1, 0, 0, 1, 0])], 8),
    ([Segment(0, 8, 0), Segment(8, 8, 1)], 16),
    ([Segment(0, 8, 0), Segment(8, 8, 0)], 16),
    ([Segment(0, 8, 0), Segment(8, 8, None, [0] * 8), Segment(16, 8, 1)], 24),
])
def test_join_roundtrip_elementwise(codec, segs, n):
    bits, comp = codec.encode(n, segs)
    n2, segs2 = codec.decode(bits)
    assert n2 == n
    assert len(segs2) == len(segs)
    for a, b in zip(segs, segs2):          # elementwise, per U8
        assert (a.start, a.length, a.mech) == (b.start, b.length, b.mech)
        assert list(a.residual_bits) == list(b.residual_bits)


def test_accounting_equals_emitted_bits(codec):
    """Components must sum to the stream exactly. If they do not, some field is
    either uncounted (free lunch) or double-counted."""
    segs = [Segment(0, 8, 0), Segment(8, 8, None, [1] * 8), Segment(16, 8, 1)]
    bits, comp = codec.encode(24, segs)
    assert comp.total() == len(bits)


def test_nothing_is_free_repetition_is_charged(codec):
    """§4.6: the repetition pointer is realised as component 3, not assumed
    free. Two segments must cost strictly more than one."""
    _, c1 = codec.encode(16, [Segment(0, 16, 0)])
    _, c2 = codec.encode(16, [Segment(0, 8, 0), Segment(8, 8, 0)])
    assert c2.total() > c1.total()
    assert c2.cuts > c1.cuts


def test_fallback_is_charged_one_bit_per_symbol(codec):
    """§4.5: the honest fallback is a raw copy. Its residual field must be
    exactly the segment length, so a fallback can never look like compression."""
    _, c = codec.encode(32, [Segment(0, 32, None, [0] * 32)])
    assert c.residuals == 32


def test_fallback_is_not_a_recovered_mechanism():
    """§4.5: 'A fallback is NEVER reported as a recovered mechanism.'"""
    assert Segment(0, 8, None, [0] * 8).is_fallback
    assert not Segment(0, 8, 0).is_fallback


# ---------------------------------------------------------------------------
# the AC-R4-1 guard itself
# ---------------------------------------------------------------------------

def test_codelength_refuses_before_self_check():
    """The heart of AC-R4-1: no length may be quoted before the gate is green."""
    fresh = GrammarCodec()
    with pytest.raises(KraftViolation, match="AC-R4-1"):
        fresh.codelength(8, [Segment(0, 8, 0)])


def test_codelength_allowed_after_self_check():
    fresh = GrammarCodec()
    fresh.self_check(max_int=256)
    length, comp = fresh.codelength(8, [Segment(0, 8, 0)])
    assert length == comp.total() > 0


def test_self_check_raises_on_a_broken_component(monkeypatch):
    """Negative control for the gate: break a component and the gate must
    refuse, not pass. Otherwise self_check is decoration."""
    import r4_segment_grammar as mod
    fresh = GrammarCodec()
    monkeypatch.setattr(mod, "kraft_sum", lambda codes: 2.0)
    with pytest.raises(KraftViolation):
        fresh.self_check(max_int=64)


# ---------------------------------------------------------------------------
# catalogue authority chain
# ---------------------------------------------------------------------------

def test_catalogue_is_the_mirror_tested_one():
    """SUCCESSOR_PLAN v0.2: W1.3/W1.4 must consume catalogue_from_gates.json
    only -- the mirror test is the authority chain."""
    cat = load_catalogue()
    assert cat["generated_by"] == "tools/r4_catalogue_from_gates.wl"
    assert cat["n_mechanisms"] == 220
    tts = {tuple(m["tt"]) for m in cat["mechanisms"]}
    nonconst = {t for t in tts if len(set(t)) > 1}
    assert len(nonconst) == 46, "A3.1 pins frame expressivity at 46 of 256"
