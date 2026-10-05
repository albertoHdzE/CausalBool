"""Declared engineering fixture inputs (BENCHMARK section 2): at most 32 distinct strings,
at most 4,099 bits, exact constructions, pseudorandom ones from local seed 62001 only.
Fixtures are engineering witnesses, never part of the 96-case endpoint."""
from __future__ import annotations

import hashlib
import json
import random
from pathlib import Path

SEED = 62001
A, B_, C_ = "11010010", "00101101", "01110001"


def _random(n: int) -> str:
    r = random.Random(SEED)
    return "".join(str(r.getrandbits(1)) for _ in range(n))


def _thue_morse(n: int) -> str:
    s = "0"
    while len(s) < n:
        s = "".join("01" if c == "0" else "10" for c in s)
    return s[:n]


def _flip(s: str, positions) -> str:
    b = bytearray(s.encode())
    for p in positions:
        b[p] ^= 1
    return b.decode()


def _perm1024() -> str:
    w = ["00110101", "11001010", "01011100", "10100011"]
    blocks = [(0, 1, 2, 3), (1, 3, 0, 2), (2, 0, 3, 1), (3, 2, 1, 0)]
    return "".join(w[i] for _ in range(8) for blk in blocks for i in blk)


def _nested() -> str:
    a, b = "00110101", "11001010"
    p = a + a + b + a
    q = p + p + b + b
    return q * 8


GAP = (A + B_ + C_) * 40
INPUTS = {
    "empty": ("empty string", ""),
    "short4": ("'0110'", "0110"),
    "single_symbol_256": ("'0110' * 64", "0110" * 64),
    "odd_symbols_59": ("'10110010' * 7 + '101'", "10110010" * 7 + "101"),
    "alternating_512": ("('00011011' + '11100100') * 32", ("00011011" + "11100100") * 32),
    "permutation_1024": ("four 8-bit words, blocks (0123)(1302)(2031)(3210) repeated 8 times", _perm1024()),
    "nested_ab_640": ("A=00110101 B=11001010, P=AABA, Q=PPBB, Q*8", _nested()),
    "thue_morse_1024": ("0->01, 1->10 from '0', first 1024 bits", _thue_morse(1024)),
    "random_1024": ("random.Random(62001).getrandbits(1) for each of 1024 bits", _random(1024)),
    "counter_1024": ("8-bit counter 0..127", "".join(format(i, "08b") for i in range(128))),
    "gap_exact_960": ("(A B C) * 40 with A=11010010 B=00101101 C=01110001", GAP),
    "gap_flips_10": ("gap_exact_960 with bits 50 + 90 i flipped, i < 10", _flip(GAP, [50 + 90 * i for i in range(10)])),
    "gap_flips_80": ("gap_exact_960 with bits 30 + 11 i flipped, i < 80", _flip(GAP, [30 + 11 * i for i in range(80)])),
    "hand32": ("'01101001' * 4", "01101001" * 4),
    "hand_origin32": ("'0110' + W1 + W2 + W1 + '1001', W1=00001111 W2=11110000",
                      "0110" + "00001111" + "11110000" + "00001111" + "1001"),
    "ragged_4099": ("('00011011' + '11100100') * 256 + '101'", ("00011011" + "11100100") * 256 + "101"),
}


def bits(name: str) -> str:
    return INPUTS[name][1]


def declare(path: Path) -> dict:
    vals = {k: v[1] for k, v in INPUTS.items()}
    out = {"seed": SEED, "max_bits": max(len(v) for v in vals.values()),
           "distinct_inputs": len(set(vals.values())),
           "inputs": {k: {"construction": INPUTS[k][0], "n_bits": len(v),
                          "sha256": hashlib.sha256(v.encode()).hexdigest()} for k, v in vals.items()},
           "random_1024_bits": vals["random_1024"]}
    assert out["distinct_inputs"] <= 32 and out["max_bits"] <= 4099
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    return out
