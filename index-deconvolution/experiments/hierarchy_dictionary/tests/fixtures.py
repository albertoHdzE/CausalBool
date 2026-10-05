"""Declared engineering fixture inputs (BENCHMARK section 2): at most 24 distinct strings,
at most 4,099 bits, exact constructions, pseudorandom ones from local seed 63001 only.
Expectations are derived by hand from the wire annex and SEARCH.md and written into the
declaration BEFORE any fixture is executed. Fixtures are engineering witnesses, never
part of the 96-case endpoint, and were not searched for favourable behaviour."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 63001
VERSION = 1
A8, B8, C8 = "11010010", "00101101", "01110001"


def _rng() -> random.Random:
    return random.Random(SEED)


def _random(n: int) -> str:
    r = _rng()
    return "".join(str(r.getrandbits(1)) for _ in range(n))


def _flip(s: str, positions) -> str:
    b = bytearray(s.encode())
    for p in positions:
        b[p] ^= 1
    return b.decode()


def _comp(s: str) -> str:
    return s.translate(str.maketrans("01", "10"))


def _nested() -> str:
    a, b = "00110101", "11001010"
    p = a + a + b + a
    q = p + p + b + b
    return q * 8


# 64-bit base word for the relation fixtures: 48 zeros then 16 ones. Its reversal is at
# Hamming distance 32 from it and its complement at 64, so for the flip sets used below
# (at most 21 positions in total) every reversal-based comparison has > 8 flips and the
# plain comparison (flags 0) decides, except where an exact transform is planted.
A64 = "0" * 48 + "1" * 16


def _fillers() -> list[str]:
    r = random.Random(SEED + 1)          # documented local stream: seed 63001 + 1
    return ["".join(str(r.getrandbits(1)) for _ in range(64)) for _ in range(3)]


def relation_words() -> list[str]:
    """w0 = A; w1 = comp A; w2 = rev A; w3 = rev(comp A); w4 = A + 8 flips (0..7);
    w5 = A + 9 flips (10..18); w6..w8 random fillers; w9 = A + 1 flip (0)."""
    a = A64
    return [a, _comp(a), a[::-1], _comp(a)[::-1], _flip(a, range(8)), _flip(a, range(10, 19)),
            *_fillers(), _flip(a, [0])]


def relation_input() -> str:
    return "01" * 16 + "".join(relation_words()) * 2 + "0011" * 8


def chain_words() -> list[str]:
    """w_i = A with positions 20..20+i-1 flipped, i = 0..10."""
    return [_flip(A64, range(20, 20 + i)) for i in range(11)]


W0_HEX = "0123456789ABCDEF"
W0 = format(int(W0_HEX, 16), "064b")
D_P = "01" * 8                                  # donor with period 2
D_C = _flip(_comp(D_P), [15])                   # comp(donor) with bit 15 flipped

INPUTS = {
    "empty": ("empty string", ""),
    "short4": ("'0110'", "0110"),
    "odd_tail_59": ("'10110010' * 7 + '101'", "10110010" * 7 + "101"),
    "single_symbol_256": ("'0110' * 64", "0110" * 64),
    "counter_1024": ("8-bit counter 0..127", "".join(format(i, "08b") for i in range(128))),
    "complement_pair_512": ("('00011011' + '11100100') * 32", ("00011011" + "11100100") * 32),
    "nested_ab_640": ("A=00110101 B=11001010, P=AABA, Q=PPBB, Q*8", _nested()),
    "random_1024": ("random.Random(63001).getrandbits(1) for each of 1024 bits", _random(1024)),
    "gap_exact_960": ("(A B C) * 40, A=11010010 B=00101101 C=01110001", (A8 + B8 + C8) * 40),
    "gap_flips_10": ("gap_exact_960 with bits 50 + 90 i flipped, i < 10",
                     _flip((A8 + B8 + C8) * 40, [50 + 90 * i for i in range(10)])),
    "gap_flips_80": ("gap_exact_960 with bits 30 + 11 i flipped, i < 80",
                     _flip((A8 + B8 + C8) * 40, [30 + 11 * i for i in range(80)])),
    "ragged_4099": ("('00011011' + '11100100') * 256 + '101'", ("00011011" + "11100100") * 256 + "101"),
    "witness_shared_128": ("W0 + comp(W0), W0 = 64 bits of 0x0123456789ABCDEF", W0 + _comp(W0)),
    "period_96": ("('00100100' + '01010101' + '11010010') * 4",
                  ("00100100" + "01010101" + "11010010") * 4),
    "relation_1344": ("'01'*16 + (w0..w9 of relation_words) * 2 + '0011'*8; 64-bit words at origin 32",
                      relation_input()),
    "hop_chain_1408": ("(w0..w10 of chain_words) * 2, width 64 origin 0", "".join(chain_words()) * 2),
    "donor_rewritten_128": ("(D + C) * 4, D = '01'*8, C = comp(D) with bit 15 flipped", (D_P + D_C) * 4),
}

EXPECTATIONS = {
    "witness_shared_128": (
        "view (1,64,0): O G0 = CONCAT(LIT W0, LIT W1) = rules 10+10+4, q 1, payload 25, "
        "envelope 4+1+2+1 = 8 -> 33 bytes = 264 bits; R(O) G0 = CONCAT(LIT W0, XFORM(LIT W0, "
        "flags 1)) = 10+4+4, q 1, payload 19 -> 27 bytes = 216 bits (< O); relation of id 1: "
        "j=0, flags 1, 0 flips, hops 1; A0 (literal) = 8 + 16 = 24 bytes = 192 bits is retained"),
    "period_96": (
        "view (1,8,0): words 00100100 (p=3, non-dividing, kept O), 01010101 (p=2 -> REPEAT("
        "LIT 01, 4)), 11010010 (p=8, kept). O G0 = 3 LIT (9) + CONCAT arity 12 (14), q 1, "
        "payload 24, envelope 7 -> 31 bytes = 248 bits; P G0 = 9 - 3 + 3 + 3 + 14 + 1 = 27 "
        "payload -> 34 bytes = 272 bits > O: replacement increases the full archive"),
    "relation_1344": (
        "view (1,64,32) ids 0..9 are w0..w9: w1 j0 f1 0 flips; w2 j0 f2 0 flips; w3 j0 f3 0 "
        "flips (composition); w4 j0 f0 flips [0..7] (8 = cap, eligible); w5 none (9 flips "
        "from w0, comparison (0,0) records 9); w6..w8 none (random); w9: j=0 outside window "
        "(predecessors 1..8); ties (1 flip) at (j1,f1), (j2,f2), (j3,f3) -> j1 f1 flips [0]; "
        "hops: w1..w4 = 1, w9 = 2, others 0"),
    "hop_chain_1408": (
        "view (1,64,0): w1..w8 relate to j=i-1, flags 0, 1 flip, hops i; w9: j=8 excluded "
        "(hops 9) -> j=7, 2 flips [27,28], hops 8; w10: j=9 and j=8 excluded -> j=7, 3 flips "
        "[27,28,29], hops 8"),
    "donor_rewritten_128": (
        "view (1,16,0): D -> P REPEAT(LIT 01, 8); C: no complete period; R(O) C = PATCH(XFORM("
        "LIT D, 1), [15]); R(P) C = PATCH(XFORM(REPEAT(LIT 01, 8), 1), [15]); tie (1, j0, f1) "
        "< (1, j0, f2)"),
    "complement_pair_512": "view (1,8,0): id 1 = comp(id 0): R j0 f1 0 flips",
    "single_symbol_256": "k = 1 at (1,4,0); descendants (2..4,4,0) still EVALUATED with k_eq_1 flags",
    "counter_1024": "k = m at (1,8,0); descendants still EVALUATED; old mask reproduces old A3",
}


def bits(name: str) -> str:
    return INPUTS[name][1]


def declare(path: Path, benchmark_hashes: set | None = None) -> dict:
    vals = {k: v[1] for k, v in INPUTS.items()}
    hashes = {k: hashlib.sha256(v.encode()).hexdigest() for k, v in vals.items()}
    out = {"version": VERSION, "seed": SEED, "max_bits": max(len(v) for v in vals.values()),
           "distinct_inputs": len(set(vals.values())),
           "inputs": {k: {"construction": INPUTS[k][0], "n_bits": len(v), "sha256": hashes[k],
                          "bits_hex_msb_first": (format(int(v, 2), "x").zfill((len(v) + 3) // 4)
                                                 if v else "")}
                      for k, v in vals.items()},
           "expectations": EXPECTATIONS,
           "benchmark_overlap": (None if benchmark_hashes is None
                                 else sorted(k for k, h in hashes.items() if h in benchmark_hashes))}
    assert out["distinct_inputs"] == len(vals) <= 24 and out["max_bits"] <= 4099
    assert not out["benchmark_overlap"]
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() and json.loads(path.read_text()) != out:
        raise SystemExit(f"{path} exists with a different declaration; write a versioned amendment")
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out
