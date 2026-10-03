"""Independent tiny semantic interpreter for HID rules, written from the annex text.

It evaluates hand-written rule tuples position by position, deliberately in the
slowest obvious way, and shares no code with model.py (encoder evaluator) or
decode.py (wire decoder). Rules:

  ("lit", "0110")                    ("cat", i, j, ...)
  ("rep", i, copies)                 ("ap", length, fg, [(start, step, count), ...])
  ("sch", length, fg, [(mask, value), ...])
  ("patch", i, [positions])          ("xf", i, flags, r)
"""
from __future__ import annotations


def evaluate(rules: list[tuple]) -> str:
    vals: list[str] = []
    for r in rules:
        kind = r[0]
        if kind == "lit":
            vals.append(r[1])
        elif kind == "cat":
            out = ""
            for i in r[1:]:
                out = out + vals[i]
            vals.append(out)
        elif kind == "rep":
            out = ""
            for _ in range(r[2]):
                out = out + vals[r[1]]
            vals.append(out)
        elif kind == "ap":
            _, length, fg, aps = r
            out = ""
            for i in range(length):
                hit = False
                for start, step, count in aps:
                    if i >= start and (i - start) % step == 0 and (i - start) // step < count:
                        hit = True
                out += str(fg) if hit else str(1 - fg)
            vals.append(out)
        elif kind == "sch":
            _, length, fg, pairs = r
            d = (length - 1).bit_length()
            out = ""
            for i in range(length):
                bits_i = [(i >> j) & 1 for j in range(d)]
                hit = False
                for mask, value in pairs:
                    ok = True
                    for j in range(d):
                        if (mask >> j) & 1 and bits_i[j] != (value >> j) & 1:
                            ok = False
                    if ok:
                        hit = True
                out += str(fg) if hit else str(1 - fg)
            vals.append(out)
        elif kind == "patch":
            s = list(vals[r[1]])
            for p in r[2]:
                s[p] = "1" if s[p] == "0" else "0"
            vals.append("".join(s))
        elif kind == "xf":
            s = vals[r[1]]
            flags, rot = r[2], r[3]
            if flags & 1:
                s = "".join("1" if c == "0" else "0" for c in s)
            if flags & 2:
                s = "".join(reversed(s))
            for _ in range(rot):                     # one right step at a time
                s = s[-1] + s[:-1]
            vals.append(s)
        else:
            raise ValueError(kind)
    return vals[-1]
