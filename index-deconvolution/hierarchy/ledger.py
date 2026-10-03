"""Field ledgers and graph explanations read from stored archive BYTES (reporting).

``archive_ledger(data)`` cuts any HID-v1 archive into labelled fields whose
concatenation is asserted to equal the archive, so a ledger can never omit a byte.
For HID archives it also returns the rule records, rebuilt as ``model.Model`` and
evaluated by the encoder-side evaluator; the caller cross-checks that expansion
against the independent decoder. This parser is for reports only; decoding for
verification always uses decode.py.
"""
from __future__ import annotations

from . import codes as C
from .model import (APUnion, Concat, Literal, Model, Patch, Repeat, SchemaUnion, Xform)


class _Cut:
    def __init__(self, data: bytes) -> None:
        self.data, self.pos, self.rows = data, 0, []

    def u(self) -> tuple[int, bytes]:
        start, v, shift = self.pos, 0, 0
        while True:
            b = self.data[self.pos]
            self.pos += 1
            v |= (b & 0x7F) << shift
            shift += 7
            if not b & 0x80:
                return v, self.data[start:self.pos]

    def take(self, k: int) -> bytes:
        out = self.data[self.pos:self.pos + k]
        self.pos += k
        return out

    def add(self, owner, field, raw, value=None):
        self.rows.append({"owner": owner, "field": field, "bytes": len(raw), "hex": raw.hex(),
                          "value": value})

    def fu(self, owner, field):
        v, raw = self.u()
        self.add(owner, field, raw, v)
        return v

    def fb(self, owner, field):
        raw = self.take(1)
        self.add(owner, field, raw, raw[0])
        return raw[0]

    def fraw(self, owner, field, k, value=None):
        raw = self.take(k)
        self.add(owner, field, raw, value)
        return raw


def _bits(raw: bytes, n: int) -> str:
    if n == 0:
        return ""
    return format(int.from_bytes(raw, "big") >> (8 * len(raw) - n), "b").zfill(n)


def archive_ledger(data: bytes) -> dict:
    c = _Cut(data)
    c.fraw("envelope", "magic", 4, "ISD1")
    codec = c.fb("envelope", "codec_id")
    n = c.fu("envelope", "output_n_bits")
    plen = c.fu("envelope", "payload_n_bytes")
    out = {"codec_id": codec, "codec": C.CODEC_NAMES.get(codec), "n_bits": n,
           "payload_bytes": plen, "model": None}
    if codec == C.CODEC_HID:
        rules = []
        q = c.fu("dag", "q_rules")
        for i in range(q):
            own = f"rule{i}"
            op = c.fb(own, "opcode")
            if op == C.OP_LITERAL:
                L = c.fu(own, "length")
                raw = c.fraw(own, f"P(bits) [{L} bits + {8 * ((L + 7) // 8) - L} pad]",
                             (L + 7) // 8)
                rules.append(Literal(_bits(raw, L)))
            elif op == C.OP_CONCAT:
                k = c.fu(own, "arity")
                rules.append(Concat(tuple(c.fu(own, f"child_id[{j}]") for j in range(k))))
            elif op == C.OP_REPEAT:
                rules.append(Repeat(c.fu(own, "child_id"), c.fu(own, "copies")))
            elif op == C.OP_AP_UNION:
                L, fg, qa = c.fu(own, "length"), c.fb(own, "foreground"), c.fu(own, "q_ap")
                aps = tuple((c.fu(own, f"ap[{j}].start"), c.fu(own, f"ap[{j}].step"),
                             c.fu(own, f"ap[{j}].count")) for j in range(qa))
                rules.append(APUnion(L, fg, aps))
            elif op == C.OP_SCHEMA_UNION:
                L, fg, qs = c.fu(own, "length"), c.fb(own, "foreground"), c.fu(own, "q_schema")
                prs = tuple((c.fu(own, f"pair[{j}].mask"), c.fu(own, f"pair[{j}].value"))
                            for j in range(qs))
                rules.append(SchemaUnion(L, fg, prs))
            elif op == C.OP_PATCH:
                ch, qf = c.fu(own, "child_id"), c.fu(own, "q_flip")
                pos = []
                for j in range(qf):
                    d = c.fu(own, f"delta[{j}]")
                    pos.append(d if j == 0 else pos[-1] + d + 1)
                rules.append(Patch(ch, tuple(pos)))
            else:
                ch, fl, r = c.fu(own, "child_id"), c.fb(own, "flags"), c.fu(own, "right_rotation")
                rules.append(Xform(ch, fl, r))
        out["model"] = Model(tuple(rules))
    elif codec == C.CODEC_LITERAL:
        c.fraw("literal", f"P(bits) [{n} bits]", plen)
    elif codec == C.CODEC_RLE:
        c.fb("rle", "first_bit")
        q = c.fu("rle", "q_runs")
        for j in range(q):
            c.fu("rle", f"run[{j}]")
    elif codec == C.CODEC_GAPS:
        c.fb("gaps", "foreground")
        q = c.fu("gaps", "q_positions")
        for j in range(q):
            c.fu("gaps", f"delta[{j}]")
    elif codec == C.CODEC_PERIOD:
        p = c.fu("period", "period_length")
        c.fraw("period", f"P(first_period) [{p} bits]", (p + 7) // 8)
    elif codec in (C.CODEC_BERNOULLI, C.CODEC_CONTEXT, C.CODEC_ZLIB, C.CODEC_LZMA):
        name = C.CODEC_NAMES[codec]
        if codec == C.CODEC_CONTEXT:
            c.fb(name, "first_bit")
            for f in ("m0", "k0", "k1"):
                c.fu(name, f)
        elif codec == C.CODEC_BERNOULLI:
            c.fu(name, "ones")
        rest = len(data) - c.pos
        c.fraw(name, "rank fields" if codec in (C.CODEC_BERNOULLI, C.CODEC_CONTEXT)
               else "compressed stream incl. library headers/checksums", rest)
    elif codec == C.CODEC_PAIR:
        q = c.fu("pair", "q_rules")
        for j in range(q):
            c.fu("pair", f"rule{j + 2}.left")
            c.fu("pair", f"rule{j + 2}.right")
        m = c.fu("pair", "m_start")
        for j in range(m):
            c.fu("pair", f"start[{j}]")
    if b"".join(bytes.fromhex(r["hex"]) for r in c.rows) != data or c.pos != len(data):
        raise AssertionError("ledger does not reassemble the archive")
    out["fields"] = c.rows
    out["archive_bits"] = 8 * len(data)
    by_owner: dict[str, int] = {}
    for r in c.rows:
        key = r["owner"].split("[")[0]
        by_owner[key] = by_owner.get(key, 0) + r["bytes"]
    out["bytes_by_owner"] = by_owner
    return out


def explain_model(model: Model) -> list[dict]:
    """Human description of every rule, including schema anchors and sumandos."""
    lens = model.lengths()
    exps = model.expansions()
    refs: dict[int, int] = {}
    for r in model.rules:
        for ch in r.refs():
            refs[ch] = refs.get(ch, 0) + 1
    rows = []
    for i, r in enumerate(model.rules):
        d = {"id": i, "op": C.OP_NAMES[r.op], "length": lens[i], "referenced_by": refs.get(i, 0),
             "expansion_prefix": exps[i][:64] + ("..." if lens[i] > 64 else "")}
        if isinstance(r, Literal):
            d["bits"] = r.bits if len(r.bits) <= 128 else r.bits[:128] + "..."
        elif isinstance(r, Concat):
            d["children"] = list(r.children)
        elif isinstance(r, (Repeat,)):
            d.update(child=r.child, copies=r.copies)
        elif isinstance(r, APUnion):
            d.update(foreground=r.foreground, progressions=[list(t) for t in r.aps])
        elif isinstance(r, SchemaUnion):
            dd = (r.length - 1).bit_length()
            schemata = []
            for mask, value in r.pairs:
                free = [j for j in range(dd) if not (mask >> j) & 1]
                fill = sorted({value + sum(((k >> t) & 1) << j for t, j in enumerate(free))
                               for k in range(1 << len(free))})
                clipped = [a for a in fill if a < r.length]
                direct = [a for a in range(r.length) if (a & mask) == value]
                if clipped != direct:
                    raise AssertionError("anchor + sumandos disagree with the mask test")
                pattern = "".join("*" if j in free else str((value >> j) & 1)
                                  for j in reversed(range(dd)))
                schemata.append({"mask": mask, "value": value,
                                 "pattern_msb_to_lsb": pattern, "free_coordinates": free,
                                 "decimal_anchor": value,
                                 "sumandos": "sum(e_j * 2**j for j in free), e_j in {0,1}",
                                 "addresses_after_clipping": len(clipped)})
            d.update(foreground=r.foreground, d=dd, schemata=schemata)
        elif isinstance(r, Patch):
            d.update(child=r.child, flips=len(r.positions), positions=list(r.positions[:32]))
        else:
            d.update(child=r.child, complement=bool(r.flags & 1), reverse=bool(r.flags & 2),
                     right_rotation=r.rotation)
        rows.append(d)
    return rows


# ---------------------------------------------------------------------------
# Exhaustive, mutually exclusive cost buckets (HID-search-v2, SEARCH.md section 4)
# ---------------------------------------------------------------------------

BUCKETS = ("envelope", "dag_count_opcodes", "references", "parameters",
           "literal_payload_bits", "literal_padding_bits", "correction_deltas",
           "other_payload")
BUCKET_RULES = {
    "envelope": "envelope magic, codec_id, output_n_bits, payload_n_bytes",
    "dag_count_opcodes": "HID q_rules and every rule opcode byte",
    "references": "HID child_id fields (REPEAT/PATCH/XFORM child, CONCAT child_id[j])",
    "parameters": "HID length, arity, copies, foreground, q_ap, q_schema, q_flip, flags, "
                  "right_rotation, AP start/step/count and schema mask/value fields",
    "literal_payload_bits": "meaningful bits of HID LITERAL payloads and of the raw codec",
    "literal_padding_bits": "zero padding bits of those payloads (to whole bytes)",
    "correction_deltas": "HID PATCH position deltas",
    "other_payload": "every field of the non-HID, non-raw baseline codecs after the envelope",
}
_PARAMETER_FIELDS = ("length", "arity", "copies", "foreground", "q_ap", "q_schema", "q_flip",
                     "flags", "right_rotation")


def _bucket_of(owner: str, fld: str) -> str | None:
    if owner == "envelope":
        return "envelope"
    if owner == "dag" or fld == "opcode":
        return "dag_count_opcodes"
    if owner.startswith("rule"):
        if fld.startswith("child_id"):
            return "references"
        if fld.startswith("delta["):
            return "correction_deltas"
        if fld.startswith("P(bits)"):
            return None                       # split into payload and padding bits
        if fld in _PARAMETER_FIELDS or fld.startswith(("ap[", "pair[")):
            return "parameters"
        raise ValueError(f"unmapped HID field {owner}.{fld}")
    if owner == "literal":
        return None
    return "other_payload"


def field_buckets(data: bytes) -> dict:
    """Bits of ``data`` per bucket; the buckets sum exactly to 8 * len(data)."""
    led = archive_ledger(data)
    out = dict.fromkeys(BUCKETS, 0)
    for r in led["fields"]:
        b = _bucket_of(r["owner"], r["field"])
        if b is not None:
            out[b] += 8 * r["bytes"]
            continue
        if r["owner"] == "literal":
            meaningful = led["n_bits"]
        else:
            meaningful = int(r["field"].split("[")[1].split(" bits")[0])
        out["literal_payload_bits"] += meaningful
        out["literal_padding_bits"] += 8 * r["bytes"] - meaningful
    if sum(out.values()) != 8 * len(data):
        raise AssertionError("cost buckets do not sum to the archive length")
    return out
