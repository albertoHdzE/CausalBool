"""Baseline codecs (W4-W7): exhaustive round trips, fixtures, the pair grammar."""
from __future__ import annotations

import itertools
import lzma
import random
import zlib

import pytest

from hierarchy.baselines import BASELINE_METHODS, METHOD_CODEC, encode_baseline, select_best
from hierarchy.candidates import pair_grammar, pair_grammar_reference, shortest_period
from hierarchy.decode import decode_archive
from hierarchy.wire import pack_bits, put_u

ALL8 = ["".join(t) for k in range(9) for t in itertools.product("01", repeat=k)]


@pytest.mark.parametrize("method", BASELINE_METHODS)
def test_every_baseline_round_trips_all_511_strings(method):
    assert len(ALL8) == 511
    for s in ALL8:
        a = encode_baseline(s, method)
        assert decode_archive(a) == s
        if s == "":
            assert a == b"ISD1\x00\x00\x00"
        elif method != "raw":
            assert a[4] == METHOD_CODEC[method]


@pytest.mark.parametrize("bits,method,hexs", [
    ("0001111", "rle", "49534431 02 07 04 00 02 03 04"),
    ("0001000", "gaps", "49534431 03 07 03 01 01 03"),
    ("0110110", "period", "49534431 04 07 02 03 60"),
    ("0101", "pair_grammar", "49534431 09 04 06 01 00 01 02 02 02"),
    ("0110", "bernoulli", "49534431 05 04 02 02 02"),
    ("0101", "context", "49534431 06 04 04 00 02 02 00"),
])
def test_hand_derived_baseline_fixtures(bits, method, hexs):
    assert encode_baseline(bits, method) == bytes.fromhex(hexs.replace(" ", ""))


def test_gaps_chooses_the_shorter_foreground():
    a = encode_baseline("1110111", "gaps")
    assert a[7] == 0                       # foreground 0, one position
    assert decode_archive(a) == "1110111"


def test_stdlib_codecs_compress_packed_bits_with_their_headers_counted():
    s = "1" * 80
    z = encode_baseline(s, "zlib")
    body = zlib.compress(pack_bits(s), 9)
    assert z == b"ISD1\x07" + put_u(80) + put_u(len(body)) + body
    x = encode_baseline(s, "lzma")
    xz = lzma.compress(pack_bits(s), format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC64, preset=6)
    assert x[-len(xz):] == xz and xz[:6] == b"\xfd7zXZ\x00"


def test_pair_grammar_equals_the_slow_reference():
    rng = random.Random(9)
    for t in range(400):
        p1 = rng.choice([0.5, 0.1, 0.9])
        seq = [int(rng.random() < p1) for _ in range(rng.randint(0, 150))]
        if t % 5 == 0:
            seq = [rng.randrange(5) for _ in range(rng.randint(0, 60))]
        assert pair_grammar(seq, 10, 4096) == pair_grammar_reference(seq, 10, 4096)


def test_pair_grammar_overlap_rule():
    # "aaa": overlapping count 2, one non-overlapping occurrence -> no rule.
    assert pair_grammar([0, 0, 0], 2, 10) == ([], [0, 0, 0])
    assert pair_grammar([0, 0, 0, 0], 2, 10) == ([(0, 0)], [2, 2])


@pytest.mark.parametrize("s,p", [("", 0), ("1", 1), ("1111", 1), ("0101010", 2),
                                 ("abcabcab".replace("a", "0").replace("b", "1").replace("c", "1"), 3),
                                 ("0" + "1" * 12 + "0" + "1" * 12 + "0" + "1" * 5, 13),
                                 ("10110111011110", 12)])
def test_shortest_period(s, p):
    assert shortest_period(s) == p


def test_exact_period_beyond_twelve_with_phase_and_incomplete_copy():
    rng = random.Random(3)
    for p in (13, 17, 31, 63):
        w = "".join(rng.choice("01") for _ in range(p))
        while any(w == w[:d] * (p // d) for d in range(1, p) if p % d == 0):
            w = "".join(rng.choice("01") for _ in range(p))
        for phase in (0, 5):
            s = ((w * 10)[phase:])[:3 * p + 4]
            assert shortest_period(s) == p


def test_select_best_is_a_decodable_minimum_with_codec_tiebreak():
    s = "0" * 100
    arcs = {m: encode_baseline(s, m) for m in BASELINE_METHODS}
    best = select_best(arcs)
    assert len(arcs[best]) == min(len(a) for a in arcs.values())
    tied = [m for m in arcs if len(arcs[m]) == len(arcs[best])]
    assert arcs[best][4] == min(arcs[m][4] for m in tied)
    with pytest.raises(ValueError):
        select_best({"raw": arcs["raw"]})
