"""Parser for OEIS internal-format `.seq` files from the `oeisdata` git mirror.

One file per sequence, one field per line:

    %<code> A<number> <content>

Content lines with the same code repeat and are ordinal-ordered; the terms fields
(%S/%T/%U for unsigned display, %V/%W/%X for the signed values when they differ) are
continuation lines of a single comma-separated list.

This module is deliberately dependency-free and lossless: every `%` line in the file
lands in the long `fields` output, and the wide record carries only derived views of it.
"""

from __future__ import annotations

import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

# The full field alphabet of the OEIS internal format. Order is the canonical
# display order used by oeis.org.
FIELD_CODES: tuple[str, ...] = (
    "I",  # ID line: M-number, N-number, revision stamp
    "S",  # terms, first line (unsigned display)
    "T",  # terms, continuation
    "U",  # terms, continuation
    "V",  # signed terms, first line
    "W",  # signed terms, continuation
    "X",  # signed terms, continuation
    "N",  # name
    "C",  # comments
    "D",  # references
    "H",  # links
    "F",  # formulas
    "e",  # examples
    "p",  # Maple program
    "t",  # Mathematica program
    "o",  # other programs (PARI, Python, Magma, ...)
    "Y",  # cross-references
    "K",  # keywords
    "O",  # offset
    "A",  # author
    "E",  # extensions and errors
)

# Codes that carry the term list, in the two variants.
_UNSIGNED_TERM_CODES = ("S", "T", "U")
_SIGNED_TERM_CODES = ("V", "W", "X")

_LINE_RE = re.compile(r"^%(?P<code>[A-Za-z])\s+(?P<anum>A\d{6})(?:\s(?P<content>.*))?$")

_I64_MIN, _I64_MAX = -(2**63), 2**63 - 1


@dataclass
class SeqRecord:
    """One parsed `.seq` file."""

    a_number: str
    seq_id: int
    # long-form: (code, ordinal, line_no, content). `ordinal` counts repeats within a
    # code; `line_no` is the position among the `%` lines of the file, so the source
    # order — including any interleaving of codes — is data, not an artefact of
    # storage order.
    fields: list[tuple[str, int, int, str]] = field(default_factory=list)
    name: str | None = None
    offset: str | None = None
    keywords: list[str] = field(default_factory=list)
    author: str | None = None
    terms_raw: str | None = None
    terms_signed: bool = False
    n_terms: int = 0
    terms_i64: list[int] | None = None
    parse_errors: list[str] = field(default_factory=list)

    def counts(self) -> dict[str, int]:
        """Number of lines present per field code."""
        out: dict[str, int] = {}
        for code, _, _, _ in self.fields:
            out[code] = out.get(code, 0) + 1
        return out


def _join_terms(by_code: dict[str, list[str]], codes: tuple[str, ...]) -> str | None:
    """Concatenate the continuation lines of a term list into one comma-separated string.

    OEIS wraps the term list across %S/%T/%U (or %V/%W/%X); a wrapped line ends with a
    trailing comma. Joining on "," after stripping trailing commas reconstructs the list
    exactly.
    """
    parts: list[str] = []
    for code in codes:
        for line in by_code.get(code, []):
            parts.append(line.strip().rstrip(","))
    if not parts:
        return None
    joined = ",".join(p for p in parts if p)
    return joined or None


def _parse_terms(raw: str) -> tuple[int, list[int] | None, str | None]:
    """Return (n_terms, int64 terms or None, error).

    `terms_i64` is None when any term overflows int64 — OEIS carries bignums freely.
    The raw string is always kept, so nothing is lost.
    """
    toks = [t.strip() for t in raw.split(",")]
    toks = [t for t in toks if t]
    vals: list[int] = []
    overflow = False
    for t in toks:
        try:
            v = int(t)
        except ValueError:
            return len(toks), None, f"non-integer term {t!r}"
        if not (_I64_MIN <= v <= _I64_MAX):
            overflow = True
        vals.append(v)
    return len(toks), (None if overflow else vals), None


def parse_seq_text(text: str, a_number: str) -> SeqRecord:
    """Parse the contents of one `.seq` file."""
    rec = SeqRecord(a_number=a_number, seq_id=int(a_number[1:]))
    by_code: dict[str, list[str]] = {}
    ordinals: dict[str, int] = {}
    line_no = 0

    for line in text.splitlines():
        if not line or not line.startswith("%"):
            if line.strip():
                rec.parse_errors.append(f"non-field line: {line[:60]!r}")
            continue
        m = _LINE_RE.match(line)
        if m is None:
            rec.parse_errors.append(f"unparsed field line: {line[:60]!r}")
            continue
        code = m.group("code")
        if m.group("anum") != a_number:
            rec.parse_errors.append(f"A-number mismatch: {m.group('anum')}")
        content = m.group("content") or ""
        ordinals[code] = ordinals.get(code, -1) + 1
        rec.fields.append((code, ordinals[code], line_no, content))
        by_code.setdefault(code, []).append(content)
        line_no += 1

    signed = _join_terms(by_code, _SIGNED_TERM_CODES)
    unsigned = _join_terms(by_code, _UNSIGNED_TERM_CODES)
    raw = signed if signed is not None else unsigned
    rec.terms_signed = signed is not None
    if raw is not None:
        rec.terms_raw = raw
        rec.n_terms, rec.terms_i64, err = _parse_terms(raw)
        if err:
            rec.parse_errors.append(err)

    if "N" in by_code:
        rec.name = " ".join(by_code["N"]).strip() or None
    if "O" in by_code:
        rec.offset = by_code["O"][0].strip() or None
    if "K" in by_code:
        kw = ",".join(by_code["K"])
        rec.keywords = [k.strip() for k in kw.split(",") if k.strip()]
    if "A" in by_code:
        rec.author = by_code["A"][0].strip() or None

    return rec


def iter_seq_files(seq_root: Path) -> Iterator[Path]:
    """Yield every `.seq` file under `seq_root` in A-number order."""
    for bucket in sorted(p for p in seq_root.iterdir() if p.is_dir()):
        yield from sorted(bucket.glob("*.seq"))


def parse_file(path: Path) -> SeqRecord:
    text = path.read_text(encoding="utf-8", errors="replace")
    return parse_seq_text(text, path.stem)
