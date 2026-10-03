"""Generator correctness by independent invariants, never function-vs-itself."""
from __future__ import annotations

import pytest

from hierarchy import corpus


def test_expected_counts_match_the_annex():
    c = corpus.expected_counts()
    assert c["development"]["scored_strings"] == 128
    assert c["confirmation"]["scored_strings"] == 1440
    assert c["transfer"]["scored_strings"] == 192


def test_seed_derivation_is_the_annex_formula():
    import hashlib
    import random
    key = "hid-v1|development|F01|256|0|structure"
    want = random.Random(int.from_bytes(hashlib.sha256(key.encode()).digest(), "big"))
    assert corpus.stream_rng("development", "F01", 256, 0, "structure").random() == want.random()


def test_development_split_and_lengths():
    cases, manifest = corpus.split_cases("development")
    assert len(cases) == 128 and len(manifest) == 64
    for c in cases:
        assert c.family not in corpus.HELD_OUT
        assert len(c.bits) == c.base_length + (3 if c.ragged else 0)


def _unit(fam, split="development", bl=256, rep=0):
    return corpus.generate_unit(split, fam, bl, rep)


def test_f01_is_a_rotated_primitive_tiling():
    bits, m = _unit("F01")
    p = m["period"]
    assert p in (3, 5, 7, 9) and corpus.is_primitive(m["word"])
    assert all(bits[i] == bits[i + p] for i in range(len(bits) - p))
    w = m["word"]
    assert m["tiled_word"] == w[len(w) - m["rotation_right"]:] + w[:len(w) - m["rotation_right"]]


def test_f04_membership_is_an_explicit_union_of_progressions():
    bits, m = _unit("F04", rep=1)
    fg = str(m["foreground"])
    for i, ch in enumerate(bits):
        inside = any(i >= a and (i - a) % s == 0 for s, a in zip(m["steps"], m["starts"]))
        assert (ch == fg) == inside


def test_f05_schema_membership_by_enumerated_fillings():
    bits, m = _unit("F05", bl=1024, rep=2)
    coords = m["coordinates_in_pattern_order"]
    fg = str(m["foreground"])
    d = 11
    members = set()
    for pat in ("01*", "10*", "*10"):
        fixed = {c: int(ch) for ch, c in zip(pat, coords) if ch != "*"}
        free = [j for j in range(d) if j not in fixed]
        for k in range(1 << len(free)):
            i = sum(v << c for c, v in fixed.items())
            i += sum(((k >> t) & 1) << j for t, j in enumerate(free))
            members.add(i)
    assert all((ch == fg) == (i in members) for i, ch in enumerate(bits))


def test_f06_flips_exactly_the_declared_positions():
    bits, m = _unit("F06", bl=1024)
    clean = corpus.tile(m["tiled_word"], len(bits))
    diff = [i for i in range(len(bits)) if bits[i] != clean[i]]
    assert diff == m["flips"] and len(diff) == len(bits) // 64


def test_f08_f09_statistics_are_plausible():
    b8, _ = _unit("F08", bl=1024, rep=0)
    assert 0.07 < b8.count("1") / len(b8) < 0.18
    b8c, _ = _unit("F08", bl=1024, rep=1)
    assert 0.82 < b8c.count("1") / len(b8c) < 0.93
    b9, _ = _unit("F09", bl=1024, rep=1)
    flips = sum(b9[i] != b9[i + 1] for i in range(len(b9) - 1)) / (len(b9) - 1)
    assert 0.18 < flips < 0.32


def test_f10_thue_morse_by_popcount_parity():
    # Generated with confirmation parameters but NO inference is run on it.
    bits, m = corpus.generate_unit("confirmation", "F10", 256, 1000)
    for i in (0, 1, 7, 100, 258):
        assert int(bits[i]) == (bin(i + m["offset"]).count("1") % 2) ^ m["complement"]


def test_f11_rule110_truth_table():
    table = {"111": 0, "110": 1, "101": 1, "100": 0, "011": 1, "010": 1, "001": 1, "000": 0}
    row = [int(c) for c in "0110100111010011" * 4]
    nxt = corpus.rule110_step(row)
    w = len(row)
    for j in range(w):
        key = f"{row[(j - 1) % w]}{row[j]}{row[(j + 1) % w]}"
        assert nxt[j] == table[key]


def test_f12_edit_positions():
    bits, m = corpus.generate_unit("confirmation", "F12", 256, 1000)
    assert len(bits) == 259 and m["region_lengths"] == [86, 86, 87]
    assert m["insert_index"] == 51 and m["delete_index"] == 207


def test_f02_submodes_and_f03_construction():
    _, even = _unit("F02", rep=0)
    _, odd = _unit("F02", rep=1)
    assert even["submode"] == "ordered" and odd["submode"] == "iid_tokens"
    bits, m = corpus.generate_unit("confirmation", "F03", 256, 1000)
    u = m["U"]
    v = corpus.complement(u)
    a = u + u + u + v
    assert bits.startswith(a + u[::-1] + u) and m["macro_length"] == 308


def test_primitive_guard_raises_rather_than_substituting():
    class Const:
        def getrandbits(self, k):
            return 0
    with pytest.raises(corpus.GeneratorError):
        corpus.primitive_word(Const(), 5)
