"""H1: the wire format, its golden fixtures and the independent decoder."""
from __future__ import annotations

import itertools
import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hierarchy import codes, decode
from hierarchy.decode import ArchiveError, ResourceLimitError, decode_archive
from hierarchy.model import (APUnion, Concat, Literal, Model, ModelError, Patch, Repeat,
                             SchemaUnion, Xform)
from hierarchy.tests.interp import evaluate
from hierarchy.wire import (encode_literal, lex_rank, model_ledger, pack_bits, put_rank,
                            put_u, serialize_model)


def H(s: str) -> bytes:
    return bytes.fromhex(s.replace(" ", ""))


def all_strings(max_len: int):
    for k in range(max_len + 1):
        for t in itertools.product("01", repeat=k):
            yield "".join(t)


# --- primitive fields --------------------------------------------------------

@pytest.mark.parametrize("v,hexs", [(0, "00"), (1, "01"), (127, "7f"), (128, "8001"),
                                    (300, "ac02"), (16384, "808001"),
                                    (2 ** 63 - 1, "ffffffffffffffff7f")])
def test_leb128_hand_values(v, hexs):
    assert put_u(v).hex() == hexs


@pytest.mark.parametrize("bad", [-1, 2 ** 63, True, 1.0])
def test_leb128_refuses(bad):
    with pytest.raises((TypeError, ValueError)):
        put_u(bad)


def test_pack_is_msb_first_with_zero_low_padding():
    assert pack_bits("") == b""
    assert pack_bits("1") == b"\x80"
    assert pack_bits("0110") == b"\x60"
    assert pack_bits("101100111") == b"\xb3\x80"


def test_lsb_coordinates_versus_msb_packing_are_distinct_conventions():
    # Position i has address coordinate j weight 2**j (LSB indexing); packing puts
    # position 0 in the MOST significant bit of byte 0. A schema on coordinate 0
    # (odd addresses) therefore lands on packed bit values 0x40, 0x10, 0x04, 0x01.
    s = evaluate([("sch", 8, 1, [(1, 1)])])
    assert s == "01010101"
    assert pack_bits(s) == bytes([0x40 | 0x10 | 0x04 | 0x01])


def test_rank_is_lexicographic_and_exhaustive():
    for m in range(0, 9):
        for k in range(m + 1):
            strings = sorted(s for s in ("".join(t) for t in itertools.product("01", repeat=m))
                             if s.count("1") == k)
            for r, s in enumerate(strings):
                assert lex_rank(s) == r
                raw = put_rank(s)
                assert decode._unrank(m, k, raw) == s


# --- golden fixtures (wire annex W8, hand derived) ---------------------------

GOLDEN = [
    ("literal empty", encode_literal(""), "49 53 44 31 00 00 00", ""),
    ("literal 1", encode_literal("1"), "49 53 44 31 00 01 01 80", "1"),
    ("literal 0110", encode_literal("0110"), "49 53 44 31 00 04 01 60", "0110"),
    ("HID 1 repeat 8", serialize_model(Model((Literal("1"), Repeat(0, 8))), 8),
     "49 53 44 31 01 08 07 02 00 01 80 02 00 08", "11111111"),
    # AP overlap: (0,3,4) -> 0,3,6,9 and (1,4,3) -> 1,5,9 share position 9.
    ("AP overlap", serialize_model(Model((APUnion(10, 1, ((0, 3, 4), (1, 4, 3))),)), 10),
     "49 53 44 31 01 0a 0b 01 03 0a 01 02 00 03 04 01 04 03", "1101011001"),
    # Schema on a ragged domain of 6 (d=3): odd addresses, and bits(2,1)=01 -> {2,3};
    # overlap at 3; the fillings 7 is clipped away.
    ("schema overlap ragged", serialize_model(Model((SchemaUnion(6, 1, ((1, 1), (6, 2))),)), 6),
     "49 53 44 31 01 06 09 01 04 06 01 02 01 01 06 02", "011101"),
    ("ordered concat", serialize_model(Model((Literal("10"), Literal("0111"),
                                              Concat((1, 0, 1)))), 10),
     "49 53 44 31 01 0a 0c 03 00 02 80 00 04 70 01 03 01 00 01", "0111100111"),
    # Patch positions 2, 3, 10 -> deltas 2, 0, 6.
    ("patch deltas", serialize_model(Model((Literal("0" * 11), Patch(0, (2, 3, 10)))), 11),
     "49 53 44 31 01 0b 0b 02 00 0b 00 00 05 00 03 02 00 06", "00110000001"),
    # complement 0011010 -> 1100101, reverse -> 1010011, right-rotate 2 -> 1110100.
    ("transform order", serialize_model(Model((Literal("0011010"), Xform(0, 3, 2))), 7),
     "49 53 44 31 01 07 08 02 00 07 34 06 00 03 02", "1110100"),
    # Multi-byte U: n = 300 and copies = 300 are both written ac 02; payload is
    # q(1) + literal(3) + repeat(4) = 8 bytes.
    ("multi-byte U", serialize_model(Model((Literal("0"), Repeat(0, 300))), 300),
     "49 53 44 31 01 ac 02 08 02 00 01 00 02 00 ac 02", "0" * 300),
]


@pytest.mark.parametrize("name,got,hexs,bits", GOLDEN, ids=[g[0] for g in GOLDEN])
def test_golden_bytes_and_decoding(name, got, hexs, bits):
    assert got == H(hexs)
    assert decode_archive(got) == bits


def test_transform_order_differs_from_rotating_first():
    rotate_first = evaluate([("lit", "0011010"), ("xf", 0, 0, 2)])
    assert evaluate([("lit", rotate_first), ("xf", 0, 3, 0)]) != "1110100"


def test_hid_fixture_loses_to_raw_and_is_not_hidden():
    hid = GOLDEN[3][1]
    assert len(hid) == 14 and len(encode_literal("1" * 8)) == 8


# --- literal path: every string of length 0..10 ------------------------------

def test_literal_round_trips_all_2047_strings():
    count = 0
    for s in all_strings(10):
        a = encode_literal(s)
        assert len(a) == 4 + 1 + len(put_u(len(s))) + len(put_u((len(s) + 7) // 8)) + (len(s) + 7) // 8
        assert decode_archive(a) == s
        count += 1
    assert count == 2047


def test_library_input_types():
    with pytest.raises(TypeError):
        encode_literal(b"0101")
    with pytest.raises(TypeError):
        encode_literal(["0", "1"])
    for bad in ("0102", "01 1", "011\n", "x"):
        with pytest.raises(ValueError):
            encode_literal(bad)


# --- ledger sums to the archive ---------------------------------------------

@pytest.mark.parametrize("name,got,hexs,bits", GOLDEN[3:], ids=[g[0] for g in GOLDEN[3:]])
def test_field_ledger_reassembles_the_archive(name, got, hexs, bits):
    model_bytes = H(hexs)
    led = _ledger_for(name, bits)
    assert b"".join(e[2] for e in led.entries) == model_bytes
    assert sum(len(e[2]) for e in led.entries) == len(model_bytes)


def _ledger_for(name, bits):
    models = {
        "HID 1 repeat 8": Model((Literal("1"), Repeat(0, 8))),
        "AP overlap": Model((APUnion(10, 1, ((0, 3, 4), (1, 4, 3))),)),
        "schema overlap ragged": Model((SchemaUnion(6, 1, ((1, 1), (6, 2))),)),
        "ordered concat": Model((Literal("10"), Literal("0111"), Concat((1, 0, 1)))),
        "patch deltas": Model((Literal("0" * 11), Patch(0, (2, 3, 10)))),
        "transform order": Model((Literal("0011010"), Xform(0, 3, 2))),
        "multi-byte U": Model((Literal("0"), Repeat(0, 300))),
    }
    return model_ledger(models[name], len(bits))


# --- three evaluators agree --------------------------------------------------

def _random_program(rng: random.Random):
    """A random valid composition, as both a Model and interpreter tuples."""
    rules, tuples = [], []
    for _ in range(rng.randint(1, 3)):
        k = rng.randint(1, 9)
        w = "".join(rng.choice("01") for _ in range(k))
        rules.append(Literal(w))
        tuples.append(("lit", w))
    L = rng.randint(1, 23)
    aps = sorted({(s, st, c) for s, st, c in
                  ((rng.randrange(L), rng.randint(1, 5), 1) for _ in range(rng.randint(0, 3)))})
    aps = sorted({(s, st, min(c + rng.randint(0, 3), (L - 1 - s) // st + 1)) for s, st, c in aps})
    rules.append(APUnion(L, rng.randint(0, 1), tuple(aps)))
    tuples.append(("ap",) + (L, rules[-1].foreground, list(aps)))
    L2 = rng.randint(1, 23)
    d = (L2 - 1).bit_length()
    pairs = set()
    for _ in range(rng.randint(0, 3)):
        mask = rng.randrange(1 << d) if d else 0
        value = rng.randrange(1 << d) & mask if d else 0
        if value < L2:
            pairs.add((mask, value))
    pairs = sorted(pairs)
    rules.append(SchemaUnion(L2, rng.randint(0, 1), tuple(pairs)))
    tuples.append(("sch", L2, rules[-1].foreground, list(pairs)))
    while len(rules) < 8:
        lens = _lengths(tuples)
        i = rng.randrange(len(rules))
        kind = rng.choice(["cat", "rep", "patch", "xf"])
        if kind == "cat":
            j = rng.randrange(len(rules))
            rules.append(Concat((i, j)))
            tuples.append(("cat", i, j))
        elif kind == "rep":
            c = rng.randint(2, 3)
            rules.append(Repeat(i, c))
            tuples.append(("rep", i, c))
        elif kind == "patch":
            pos = sorted(rng.sample(range(lens[i]), rng.randint(1, min(3, lens[i]))))
            rules.append(Patch(i, tuple(pos)))
            tuples.append(("patch", i, pos))
        else:
            f = rng.randint(0, 3)
            r = rng.randrange(lens[i])
            if f == 0 and r == 0:
                f = 1
            rules.append(Xform(i, f, r))
            tuples.append(("xf", i, f, r))
    # make everything reachable: concatenate all rules at the root
    rules.append(Concat(tuple(range(len(rules)))))
    tuples.append(("cat",) + tuple(range(len(rules) - 1)))
    return Model(tuple(rules)), tuples


def _lengths(tuples):
    out = []
    for t in tuples:
        k = t[0]
        if k == "lit":
            out.append(len(t[1]))
        elif k == "cat":
            out.append(sum(out[i] for i in t[1:]))
        elif k == "rep":
            out.append(out[t[1]] * t[2])
        elif k in ("ap", "sch"):
            out.append(t[1])
        else:
            out.append(out[t[1]])
    return out


def test_interpreter_encoder_and_decoder_agree_on_random_compositions():
    rng = random.Random(1601)
    for _ in range(300):
        model, tuples = _random_program(rng)
        want = evaluate(tuples)
        assert model.expand() == want
        n = len(want)
        assert decode_archive(serialize_model(model, n)) == want


# --- malformed archives --------------------------------------------------------

def _hid(payload_hex: str, n: int) -> bytes:
    p = H(payload_hex)
    return b"ISD1\x01" + put_u(n) + put_u(len(p)) + p


MALFORMED = {
    "wrong magic": b"ISD2\x00\x01\x01\x80",
    "unknown codec": b"ISD1\x0a\x01\x01\x80",
    "unknown opcode": _hid("01 07 00", 1),
    "forward reference": _hid("02 02 01 02 00 01 80", 2),
    "self reference (cycle attempt)": _hid("01 02 00 02", 2),
    "unreachable rule": _hid("02 00 01 80 00 01 80", 1),
    "malformed U (unterminated)": b"ISD1\x00\x81",
    "non-canonical U": b"ISD1\x00\x01\x00",
    "U overflow": b"ISD1\x00" + b"\xff" * 9 + b"\x01" + b"\x01\x80",
    "zero copies": _hid("02 00 01 80 02 00 01", 1),
    "concat arity one": _hid("02 00 01 80 01 01 00", 1),
    "invalid mask": _hid("01 04 06 01 01 08 00", 6),
    "value outside mask": _hid("01 04 06 01 01 01 02", 6),
    "schema matches nothing": _hid("01 04 06 01 01 06 06", 6),
    "AP out of domain": _hid("01 03 04 01 01 00 02 03", 4),
    "AP unsorted": _hid("01 03 04 01 02 01 01 01 00 01 01", 4),
    "nonzero padding": b"ISD1\x00\x01\x01\x81",
    "trailing data": b"ISD1\x00\x01\x01\x80\x00",
    "truncated payload": b"ISD1\x00\x09\x02\x80",
    "patch out of range": _hid("02 00 01 80 05 00 01 01", 1),
    "patch zero flips": _hid("02 00 01 80 05 00 00", 1),
    "xform identity": _hid("02 00 02 80 06 00 00 00", 2),
    "xform reserved flag": _hid("02 00 02 80 06 00 04 00", 2),
    "root length mismatch": _hid("01 00 02 80", 3),
    "nonliteral empty": b"ISD1\x02\x00\x00",
    "rle runs do not sum": b"ISD1\x02\x04\x03\x00\x01\x03",
    "rle zero run": b"ISD1\x02\x02\x04\x00\x02\x00\x02",
    "rank out of range": b"ISD1\x05\x04\x02\x02\x06",
    "rank wrong width": b"ISD1\x05\x04\x03\x02\x02\x00",
    # n=3, first 0, m0=2, k0=0 (Q0=00), k1=0 (Q1 empty): 0 -> 0 -> 0 consumes Q0 fully;
    # but m1 = 0 so this is valid. Make it impossible: first 1 with m0=2 -> Q1 underflows.
    "impossible Markov queues": b"ISD1\x06\x03\x04\x01\x02\x00\x00",
    "period too long": b"ISD1\x04\x03\x02\x04\x00",
    "pair forward reference": b"ISD1\x09\x04\x05\x01\x02\x01\x01\x02",
    "pair unreachable rule": b"ISD1\x09\x02\x06\x01\x00\x01\x02\x00\x01",
}


@pytest.mark.parametrize("name", sorted(MALFORMED))
def test_malformed_archives_are_rejected(name):
    with pytest.raises(ArchiveError):
        decode_archive(MALFORMED[name])


def test_stdlib_streams_reject_overrun_and_trailing_data():
    import zlib
    good = zlib.compress(b"\xff\xff", 9)
    over = b"ISD1\x07" + put_u(8) + put_u(len(good)) + good      # decompresses to 2 bytes, n=8 wants 1
    with pytest.raises(ArchiveError):
        decode_archive(over)
    trailing = good + b"\x00"
    arc = b"ISD1\x07" + put_u(16) + put_u(len(trailing)) + trailing
    with pytest.raises(ArchiveError):
        decode_archive(arc)
    import lzma
    xz = lzma.compress(b"\xff", format=lzma.FORMAT_XZ, check=lzma.CHECK_CRC32)
    with pytest.raises(ArchiveError):
        decode_archive(b"ISD1\x08" + put_u(8) + put_u(len(xz)) + xz)


def test_resource_limits_raise_a_distinct_exception():
    big = serialize_model(Model((Literal("1"), Repeat(0, 2000))), 2000)
    with pytest.raises(ResourceLimitError):
        decode_archive(big, max_output_bits=1000)
    with pytest.raises(ResourceLimitError):
        decode_archive(big, max_rules=1)
    assert decode_archive(big) == "1" * 2000


def test_mutated_valid_bytes_may_decode_to_another_string():
    # No checksum: a flipped literal data bit is a different valid archive.
    a = bytearray(encode_literal("0110"))
    a[-1] ^= 0x80
    assert decode_archive(bytes(a)) == "1110"


def test_decoder_constants_match_shared_constants():
    assert decode.MAGIC == codes.MAGIC
    assert decode.CODEC_IDS == {v: k for k, v in codes.CODEC_NAMES.items()}
    assert decode.OPCODES == {v: k for k, v in codes.OP_NAMES.items()}


def test_decoder_source_imports_only_the_standard_library():
    src = Path(decode.__file__).read_text()
    imports = [ln.split()[1] for ln in src.splitlines()
               if ln.startswith(("import ", "from ")) and not ln.startswith("from __future__")]
    assert set(imports) <= {"json", "lzma", "math", "sys", "zlib"}, imports


def test_model_validation():
    with pytest.raises(ModelError):
        Model((Literal("1"), Literal("0")))           # unreachable
    with pytest.raises(ModelError):
        Repeat(0, 1)
    with pytest.raises(ModelError):
        SchemaUnion(6, 1, ((6, 6),))
    with pytest.raises(ModelError):
        Xform(0, 0, 0)


def test_separate_process_decoder_without_package_or_originals(tmp_path):
    """Only decode.py and the archives exist in the decoding process."""
    from hierarchy.baselines import BASELINE_METHODS, encode_baseline
    from hierarchy.infer import infer
    rng = random.Random(77)
    originals = {}
    box = tmp_path / "box"
    box.mkdir()
    shutil.copy(decode.__file__, box / "decode.py")
    strings = ["", "1", "0" * 40, ("110" * 30)[:85], "".join(rng.choice("01") for _ in range(200)),
               ("1" * 8 + "0") * 8]
    k = 0
    for s in strings:
        archives = [encode_baseline(s, m) for m in BASELINE_METHODS] + [infer(s).archive]
        for a in archives:
            name = f"a{k:03d}.bin"          # opaque names
            (box / name).write_bytes(a)
            originals[name] = s
            k += 1
    env = {"PATH": os.environ.get("PATH", "")}
    out = subprocess.run([sys.executable, "-I", "-S", "decode.py"] + sorted(originals),
                         cwd=box, env=env, capture_output=True, text=True, check=True)
    rows = json.loads(out.stdout)
    assert len(rows) == len(originals) == k
    for row in rows:
        assert row["ok"], row
        assert row["bits"] == originals[row["path"]]
