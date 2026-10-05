"""Owner tests for bdm_anatomy_v1: block_code_parts and certified_eca_code.

Decodability is shown by ROUND TRIP, not asserted by formula: the tests build
the prefix codes the owner's docstrings describe (canonical codes from the
declared lengths, Elias gamma, multiset-permutation rank), encode, decode, and
compare bit for bit; the encoded length must equal the owner's number.
"""
import itertools
import math
import random
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT / "src", ROOT / "index-deconvolution" / "src"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from description_lengths import (bdm_1d, block_code_parts, certified_eca_code,  # noqa: E402
                                 ctm_1d)
from ca_deconvolution import evolve_eca  # noqa: E402


# --- reference codes (test-local; they verify the owner, they define nothing) --

def gamma(x):
    b = format(x, "b")
    return "0" * (len(b) - 1) + b


def read_gamma(s, i):
    z = 0
    while s[i + z] == "0":
        z += 1
    return int(s[i + z:i + 2 * z + 1], 2), i + 2 * z + 1


def canonical_code(lengths):
    """Canonical prefix code from {symbol: length}; refuses a Kraft sum > 1."""
    assert sum(2.0 ** -L for L in lengths.values()) <= 1.0
    code, prev, out = 0, None, {}
    for sym, L in sorted(lengths.items(), key=lambda kv: (kv[1], kv[0])):
        if prev is not None:
            code = (code + 1) << (L - prev)
        out[sym] = format(code, f"0{L}b")
        prev = L
    return out


def multiset_rank(seq):
    """Lexicographic rank of seq among distinct permutations of its multiset."""
    counts = {}
    for x in seq:
        counts[x] = counts.get(x, 0) + 1
    rank = 0
    for x in seq:
        total = sum(counts.values())
        for y in sorted(counts):
            if y == x:
                break
            if counts[y]:
                counts[y] -= 1
                n = math.factorial(total - 1)
                for v in counts.values():
                    n //= math.factorial(v)
                rank += n
                counts[y] += 1
        counts[x] -= 1
    return rank


def multiset_unrank(rank, counts):
    counts, out = dict(counts), []
    while sum(counts.values()):
        total = sum(counts.values())
        for y in sorted(counts):
            if not counts[y]:
                continue
            counts[y] -= 1
            n = math.factorial(total - 1)
            for v in counts.values():
                n //= math.factorial(v)
            if rank < n:
                out.append(y)
                break
            rank -= n
            counts[y] += 1
    return out


WORDS = {format(i, f"0{L}b") for L in range(1, 13) for i in range(2 ** L)}
WORD_CODE = canonical_code({w: math.ceil(ctm_1d(w)) for w in WORDS})


def word_key(w):
    return (len(w), w)


def encode_blocks(s, block, remainder):
    parts = block_code_parts(s, block=block, remainder=remainder)
    from description_lengths import bdm_1d_trace
    seq = [r["block"] for r in bdm_1d_trace(s, block=block, remainder=remainder)["rows"]]
    words = sorted(parts["counts"], key=word_key)
    out = gamma(len(words))
    for w in words:
        out += WORD_CODE[w] + gamma(parts["counts"][w])
    idx = {w: i for i, w in enumerate(words)}
    n_seq = math.factorial(len(seq))
    for v in parts["counts"].values():
        n_seq //= math.factorial(v)
    rb = (n_seq - 1).bit_length()
    r = multiset_rank([idx[w] for w in seq])
    out += format(r, f"0{rb}b") if rb else ""
    return out, parts


def decode_blocks(code):
    inv = {v: k for k, v in WORD_CODE.items()}
    k, i = read_gamma(code, 0)
    words, counts = [], {}
    for j in range(k):
        cur = ""
        while cur not in inv:
            cur += code[i]
            i += 1
        w = inv[cur]
        c, i = read_gamma(code, i)
        words.append(w)
        counts[j] = c
    n_seq = math.factorial(sum(counts.values()))
    for v in counts.values():
        n_seq //= math.factorial(v)
    rb = (n_seq - 1).bit_length()
    r = int(code[i:i + rb], 2) if rb else 0
    assert i + rb == len(code)
    return "".join(words[j] for j in multiset_unrank(r, counts))


# --- block_code_parts ----------------------------------------------------------

def _corpus():
    rng = random.Random(19)
    out = ["1111100000", "0" * 48, "01" * 30, "1" * 8 + "0" + "1" * 15]
    for n in (12, 24, 36, 60, 96):
        out.append("".join(rng.choice("01") for _ in range(n)))
        p = "".join(rng.choice("01") for _ in range(rng.randrange(1, 9)))
        out.append((p * n)[:n])
    return out


CORPUS = _corpus()


def test_corpus_is_not_empty():
    assert len(CORPUS) == 14 and len(set(CORPUS)) == 14


@pytest.mark.parametrize("block", [3, 4, 5, 8, 12])
def test_dictionary_plus_counts_is_bdm(block):
    checked = 0
    for s in CORPUS:
        p = block_code_parts(s, block=block, remainder="recursive")
        assert abs(p["dictionary_bits"] + p["count_bits"] - bdm_1d(s, block=block, remainder="recursive")) < 1e-9
        checked += 1
    assert checked == len(CORPUS)


@pytest.mark.parametrize("block", [3, 4, 8, 12])
def test_round_trip_and_length(block):
    checked = 0
    for s in CORPUS:
        code, parts = encode_blocks(s, block, "recursive")
        assert decode_blocks(code) == s
        assert len(code) == parts["decodable_bits"]
        checked += 1
    assert checked == len(CORPUS)


def test_permutation_invariance_and_arrangement():
    rng = random.Random(7)
    s = "".join(rng.choice("01") for _ in range(96))
    blocks = [s[i:i + 8] for i in range(0, 96, 8)]
    base = block_code_parts(s, block=8)
    for _ in range(200):
        rng.shuffle(blocks)
        p = block_code_parts("".join(blocks), block=8)
        assert abs(p["bdm"] - base["bdm"]) < 1e-9   # equal up to float summation order
        assert abs(p["arrangement_bits"] - base["arrangement_bits"]) < 1e-9


def test_log_bound():
    c8 = sum(ctm_1d(format(i, "08b")) for i in range(256))
    rng = random.Random(3)
    for m in (4, 64, 1024):
        s = "".join(rng.choice("01") for _ in range(8 * m))
        assert bdm_1d(s, block=8) <= c8 + 256 * math.log2(m) + 1e-9


def test_decodable_refused_for_lossy_partitions():
    assert block_code_parts("1111100000", block=5, shift=1)["decodable_bits"] is None
    assert block_code_parts("1111100000", block=4, remainder="drop")["decodable_bits"] is None


def test_word_code_kraft():
    total = sum(2.0 ** -math.ceil(ctm_1d(w)) for w in WORDS)
    assert len(WORDS) == 8190 and 0.67 < total < 0.671


# --- certified_eca_code --------------------------------------------------------

RULE_CODE = canonical_code({r: certified_eca_code(r, [0], 1)["rule_bits"]
                            for r in range(256)})


def test_rule_code_kraft():
    total = sum(2.0 ** -len(c) for c in RULE_CODE.values())
    assert len(RULE_CODE) == 256 and total <= 1.0


@pytest.mark.parametrize("rule", list(range(256)))
def test_certified_eca_round_trip(rule):
    rng = random.Random(rule)
    w, steps = 16 + rule % 17, 3 + rule % 29
    seed = [rng.randrange(2) for _ in range(w)]
    cert = certified_eca_code(rule, seed, steps)
    code = RULE_CODE[rule] + gamma(w) + "".join(map(str, seed)) + gamma(steps)
    assert len(code) == cert["certified_bits"]
    inv = {v: k for k, v in RULE_CODE.items()}
    cur, i = "", 0
    while cur not in inv:
        cur += code[i]
        i += 1
    r = inv[cur]
    w2, i = read_gamma(code, i)
    seed2 = [int(c) for c in code[i:i + w2]]
    steps2, i = read_gamma(code, i + w2)
    assert i == len(code)
    assert evolve_eca(r, seed2, steps2) == evolve_eca(rule, seed, steps)


def test_certified_refuses_bad_input():
    with pytest.raises(ValueError):
        certified_eca_code(256, [0, 1], 3)
    with pytest.raises(ValueError):
        certified_eca_code(30, [0, 1], 0)
    with pytest.raises(ValueError):
        certified_eca_code(30, [], 3)


def test_multiset_rank_reference_is_correct():
    # the test-local rank/unrank agree with brute force on a small multiset
    seq = [0, 0, 1, 2, 2]
    perms = sorted(set(itertools.permutations(seq)))
    for k, p in enumerate(perms):
        assert multiset_rank(list(p)) == k
        assert multiset_unrank(k, {0: 2, 1: 1, 2: 2}) == list(p)


# --- heterogeneous ECA (index-deconvolution/src/ca_deconvolution.py) -----------

def test_heterogeneous_eca_equals_evolve_eca_for_one_rule():
    from ca_deconvolution import heterogeneous_eca_network
    from causalbool import evolve_network
    checked = 0
    for rule in range(256):
        rng = random.Random(rule)
        init = [rng.randrange(2) for _ in range(17)]
        assert evolve_network(heterogeneous_eca_network([rule] * 17), init, 12) == evolve_eca(rule, init, 12)
        checked += 1
    assert checked == 256
