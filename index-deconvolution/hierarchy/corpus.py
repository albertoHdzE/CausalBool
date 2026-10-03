"""Synthetic corpus for HID-v1 (benchmark annex B1-B2). Never imported by inference.

Every base unit (split, family, base_length, replicate) generates N =
base_length + 3 bits from independent named streams; both the first
base_length bits ("base") and all N bits ("ragged") are scored. Realised
parameters go to an evaluation-only manifest that inference never receives.
"""
from __future__ import annotations

import hashlib
import random
from dataclasses import dataclass

STREAMS = ("structure", "content", "noise")

SPLITS = {
    "development": {"families": ("F01", "F02", "F04", "F05", "F06", "F07", "F08", "F09"),
                    "base_lengths": (256, 1024), "replicates": tuple(range(0, 4))},
    "confirmation": {"families": tuple(f"F{i:02d}" for i in range(1, 13)),
                     "base_lengths": (256, 1024, 4096),
                     "replicates": tuple(range(1000, 1020))},
    "transfer": {"families": tuple(f"F{i:02d}" for i in range(1, 13)),
                 "base_lengths": (16384, 65536), "replicates": tuple(range(2000, 2004))},
}
HELD_OUT = ("F03", "F10", "F11", "F12")
STRUCTURED = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")
CONTROLS = ("F07", "F08", "F09")
GUARD = 1000


class GeneratorError(RuntimeError):
    """A sampling guard was hit; never silently replaced by another example."""


def stream_rng(split: str, family: str, base_length: int, replicate: int,
               stream: str) -> random.Random:
    if stream not in STREAMS and not stream.startswith("bdm_null_"):
        raise ValueError(f"unknown stream {stream!r}")
    key = f"hid-v1|{split}|{family}|{base_length}|{replicate}|{stream}"
    seed = int.from_bytes(hashlib.sha256(key.encode("ascii")).digest(), "big")
    return random.Random(seed)


def tile(w: str, n: int) -> str:
    if not w:
        raise ValueError("tile needs a nonempty word")
    return (w * (n // len(w) + 1))[:n]


def is_primitive(w: str) -> bool:
    p = len(w)
    return all(w != w[:d] * (p // d) for d in range(1, p) if p % d == 0)


def rand_word(rng: random.Random, p: int) -> str:
    return format(rng.getrandbits(p), "b").zfill(p)


def primitive_word(rng: random.Random, p: int) -> str:
    for _ in range(GUARD):
        w = rand_word(rng, p)
        if is_primitive(w):
            return w
    raise GeneratorError(f"no primitive {p}-bit word in {GUARD} draws")


def complement(w: str) -> str:
    return w.translate(str.maketrans("01", "10"))


def rotate_right(w: str, r: int) -> str:
    return w[-r:] + w[:-r] if r else w


def _choice(rng: random.Random, seq):
    return seq[rng.randrange(len(seq))]


# ---------------------------------------------------------------------------
# Families. Each returns (bits of length N, realised parameters).
# ---------------------------------------------------------------------------

def is_development(split: str) -> bool:
    """Development parameter ranges; also used by development resource probes."""
    return split.startswith("development")


def _periods(split: str):
    return (3, 5, 7, 9) if is_development(split) else (13, 17, 31, 63)


def f01(split, N, rs, rc, rn, rep):
    p = _choice(rs, _periods(split))
    w = primitive_word(rc, p)
    r = rs.randrange(p)
    word = rotate_right(w, r)
    return tile(word, N), {"period": p, "word": w, "rotation_right": r, "tiled_word": word}


def f02(split, N, rs, rc, rn, rep):
    w = _choice(rs, (8, 12) if is_development(split) else (13, 17, 31))
    words: list[str] = []
    for _ in range(GUARD):
        cand = primitive_word(rc, w)
        if cand not in words:
            words.append(cand)
            if len(words) == 4:
                break
    else:
        raise GeneratorError("no four distinct primitive words")
    if len(words) < 4:
        raise GeneratorError("no four distinct primitive words")
    need = N // w + 1
    if rep % 2 == 0:
        sub, base = "ordered", [0, 1, 0, 2, 0, 1, 0, 3]
        tokens = [base[i % 8] for i in range(need)]
    else:
        sub = "iid_tokens"
        tokens = [rs.randrange(4) for _ in range(need)]
    bits = "".join(words[t] for t in tokens)[:N]
    return bits, {"width": w, "words": words, "submode": sub, "tokens": tokens}


def f03(split, N, rs, rc, rn, rep):
    u = primitive_word(rc, 11)
    v, w = complement(u), u[::-1]
    a = u * 3 + v
    b = (w + u) * 2
    macro = (a + b) * 2 + a * 3
    return tile(macro, N), {"U": u, "macro_length": len(macro)}


def f04(split, N, rs, rc, rn, rep):
    steps = rs.sample(list(_periods(split)), 2)
    starts = [rs.randrange(s) for s in steps]
    fg = rs.randrange(2)
    support = set()
    for s, a in zip(steps, starts):
        support.update(range(a, N, s))
    bits = "".join(str(fg) if i in support else str(1 - fg) for i in range(N))
    return bits, {"steps": steps, "starts": starts, "foreground": fg}


SCHEMA_F05 = ("01*", "10*", "*10")


def f05_member(i: int, coords, patterns=SCHEMA_F05) -> bool:
    for pat in patterns:
        if all(ch == "*" or ((i >> c) & 1) == int(ch) for ch, c in zip(pat, coords)):
            return True
    return False


def f05(split, N, rs, rc, rn, rep, base_length=None):
    d0 = base_length.bit_length() - 1
    if 1 << d0 != base_length:
        raise GeneratorError("F05 needs a power-of-two base length")
    coords = rs.sample(range(d0), 3)        # ordered: pattern char k -> coords[k]
    fg = rs.randrange(2)
    bits = "".join(str(fg) if f05_member(i, coords) else str(1 - fg) for i in range(N))
    return bits, {"coordinates_in_pattern_order": coords, "patterns": list(SCHEMA_F05),
                  "foreground": fg, "d0": d0}


def f06(split, N, rs, rc, rn, rep):
    clean, meta = f01(split, N, rs, rc, rn, rep)
    k = N // 64 if is_development(split) else N // 32
    flips = sorted(rn.sample(range(N), k))
    out = bytearray(clean.encode("ascii"))
    for q in flips:
        out[q] ^= 1
    meta = dict(meta, flips=flips, n_flips=k)
    return out.decode("ascii"), meta


def f07(split, N, rs, rc, rn, rep):
    return rand_word(rc, N), {}


def f08(split, N, rs, rc, rn, rep):
    bits = "".join("1" if rc.randrange(8) == 0 else "0" for _ in range(N))
    if rep % 2:
        bits = complement(bits)
    return bits, {"p_one": 7 / 8 if rep % 2 else 1 / 8}


def f09(split, N, rs, rc, rn, rep):
    flip_mod = 16 if rep % 2 == 0 else 4
    b = rc.getrandbits(1)
    out = [b]
    for _ in range(N - 1):
        if rc.randrange(flip_mod) == 0:
            b ^= 1
        out.append(b)
    return "".join(map(str, out)), {"flip_probability": 1 / flip_mod}


def thue_morse_bit(i: int, offset: int, flag: int) -> int:
    return ((i + offset).bit_count() & 1) ^ flag


def f10(split, N, rs, rc, rn, rep):
    offset = rs.randrange(1 << 20)
    flag = rs.randrange(2)
    return "".join(str(thue_morse_bit(i, offset, flag)) for i in range(N)), {
        "offset": offset, "complement": flag}


def rule110_step(row: list[int]) -> list[int]:
    w = len(row)
    return [(110 >> (4 * row[(j - 1) % w] + 2 * row[j] + row[(j + 1) % w])) & 1
            for j in range(w)]


def f11(split, N, rs, rc, rn, rep):
    width = 64
    row = [int(c) for c in rand_word(rc, width)]
    start = rs.randrange(64)
    rows = [row]
    while len(rows) * width < start + N:
        rows.append(rule110_step(rows[-1]))
    flat = "".join("".join(map(str, r)) for r in rows)
    return flat[start:start + N], {"start_offset": start, "initial_row": "".join(map(str, row)),
                                   "rows": len(rows)}


def f12(split, N, rs, rc, rn, rep):
    l1 = N // 3
    l2 = 2 * N // 3 - N // 3
    l3 = N - 2 * N // 3
    w17 = primitive_word(rc, 17)
    r2 = rand_word(rc, l2)
    u = primitive_word(rc, 13)
    region3 = tile(u + complement(u) + u[::-1], l3)
    base = tile(w17, l1) + r2 + region3
    ins_at, ins_bit = N // 5, str(rn.getrandbits(1))
    inserted = base[:ins_at] + ins_bit + base[ins_at:]
    del_at = 4 * N // 5
    out = inserted[:del_at] + inserted[del_at + 1:]
    return out, {"region_lengths": [l1, l2, l3], "word17": w17, "U13": u,
                 "insert_index": ins_at, "insert_bit": ins_bit, "delete_index": del_at}


FAMILIES = {"F01": f01, "F02": f02, "F03": f03, "F04": f04, "F05": f05, "F06": f06,
            "F07": f07, "F08": f08, "F09": f09, "F10": f10, "F11": f11, "F12": f12}
FAMILY_NAMES = {"F01": "periodic", "F02": "macro order", "F03": "nested relations",
                "F04": "arithmetic support", "F05": "schema support",
                "F06": "noisy period", "F07": "fair IID", "F08": "biased IID",
                "F09": "Markov", "F10": "Thue-Morse", "F11": "rule-110 trace",
                "F12": "mixed regimes and edits"}


@dataclass(frozen=True)
class Case:
    case_id: str
    split: str
    family: str
    base_length: int
    replicate: int
    ragged: bool
    bits: str

    @property
    def input_sha256(self) -> str:
        return hashlib.sha256(self.bits.encode("ascii")).hexdigest()


def generate_unit(split: str, family: str, base_length: int, replicate: int
                  ) -> tuple[str, dict]:
    N = base_length + 3
    rs, rc, rn = (stream_rng(split, family, base_length, replicate, s) for s in STREAMS)
    fn = FAMILIES[family]
    if family == "F05":
        bits, meta = fn(split, N, rs, rc, rn, replicate, base_length=base_length)
    else:
        bits, meta = fn(split, N, rs, rc, rn, replicate)
    if len(bits) != N or bits.strip("01"):
        raise GeneratorError(f"{family} produced an invalid string")
    return bits, meta


def unit_id(split, family, base_length, replicate) -> str:
    return f"{split}|{family}|{base_length}|{replicate}"


def case_id(split, family, base_length, replicate, ragged) -> str:
    return f"{split}-{family}-{base_length}-{replicate:04d}-{'ragged' if ragged else 'base'}"


def split_cases(split: str) -> tuple[list[Case], list[dict]]:
    spec = SPLITS[split]
    cases, manifest = [], []
    for family in spec["families"]:
        for bl in spec["base_lengths"]:
            for rep in spec["replicates"]:
                bits, meta = generate_unit(split, family, bl, rep)
                for ragged in (False, True):
                    s = bits if ragged else bits[:bl]
                    cases.append(Case(case_id(split, family, bl, rep, ragged), split,
                                      family, bl, rep, ragged, s))
                manifest.append({
                    "unit_id": unit_id(split, family, bl, rep), "split": split,
                    "family": family, "base_length": bl, "replicate": rep,
                    "N": bl + 3,
                    "full_sha256": hashlib.sha256(bits.encode("ascii")).hexdigest(),
                    "base_sha256": hashlib.sha256(bits[:bl].encode("ascii")).hexdigest(),
                    "params": meta})
    return cases, manifest


def expected_counts() -> dict:
    out = {}
    for split, spec in SPLITS.items():
        units = len(spec["families"]) * len(spec["base_lengths"]) * len(spec["replicates"])
        out[split] = {"units": units, "scored_strings": 2 * units}
    return out
