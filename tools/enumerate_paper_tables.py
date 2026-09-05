"""AUDIT03-B — how much of the two active manuscripts does verify-paper cover?

`verify_paper_artefacts.py` prints "7 covered, 1 pending with reasons". That
reads like 7/8. It is not. The single pending entry is a CATCH-ALL --
"remaining appendix/expansion tables" -- with no enumeration and no count,
while the two active manuscripts carry 34 `tabular` environments between them.

The gate is not wrong: every entry it checks, it checks properly, and the
pending entry does carry a reason, which is all it asserts. But its summary
line invites a reader to believe coverage is near-complete, and nobody had
measured what the denominator is.

This enumerates every number-bearing table in both active manuscripts and marks
it COVERED or UNCOVERED, so the honest fraction can be printed instead.

METHOD, and its weakness stated plainly:

  * A table is any `\\begin{tabular}` in the two active manuscripts. Its
    identity is taken from the nearest preceding `\\label{...}`, else the
    nearest `\\caption{...}`, else its ordinal position.
  * A table is COVERED when it lies INSIDE a `%% ARTEFACT-BEGIN/END <block>`
    span that a covered inventory entry declares -- which is exactly the region
    `verify_paper_artefacts.py` checks. Nothing looser counts.
  * This is a DOCUMENT-side measure. It says a producer is wired to that table,
    NOT that the numbers are right -- `verify_paper_artefacts.py` is the only
    member that reconciles a value to its source.
  * Tables carrying no digits are counted separately, so a table of symbols
    cannot inflate the deficit. Measured: there are none -- all 34 carry
    numbers.

MEASURED 2026-09-04: 5 of 34 (15%). The gate's own summary said "7 covered,
1 pending", which reads as 88%.

Usage:  venv/bin/python tools/enumerate_paper_tables.py [--json]
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INVENTORY = ROOT / "papers/method/artifact_baseline/artefacts.json"

MANUSCRIPTS = {
    "formal": ROOT / "papers/method/manuscript_formal/method_paper.tex",
    "computational": ROOT / "papers/method/manuscript_computational/comp_paper.tex",
}

TABULAR = re.compile(r"\\begin\{tabular\}")
LABEL = re.compile(r"\\label\{([^}]*)\}")
CAPTION = re.compile(r"\\caption\{")
DIGIT = re.compile(r"\d")


def table_body(text: str, start: int) -> str:
    end = text.find(r"\end{tabular}", start)
    return text[start:end if end != -1 else len(text)]


def enumerate_tables(name: str, path: Path) -> list[dict]:
    if not path.exists():
        return []
    text = path.read_text(errors="replace")
    out = []
    for i, m in enumerate(TABULAR.finditer(text), start=1):
        body = table_body(text, m.start())
        # nearest preceding label, then nearest following (caption order varies)
        before = text[:m.start()]
        labs = LABEL.findall(before[-1500:])
        after_labs = LABEL.findall(text[m.start():m.start() + 2500])
        label = (after_labs[0] if after_labs else (labs[-1] if labs else f"{name}-tabular-{i}"))
        line = before.count("\n") + 1
        out.append({
            "manuscript": name,
            "label": label,
            "line": line,
            "offset": m.start(),
            "has_numbers": bool(DIGIT.search(body)),
        })
    return out


def covered_spans(inv: dict) -> dict[str, list[tuple[int, int]]]:
    """Character spans of every `%% ARTEFACT-BEGIN/END <block>` a covered
    artefact declares, keyed by manuscript path. A table is COVERED when it
    lies inside one of these spans -- which is exactly what the gate checks."""
    spans: dict[str, list[tuple[int, int]]] = {}
    for art in inv.get("covered", []):
        tex = art.get("tex_file")
        block = art.get("block")
        if not tex or not block:
            continue
        path = ROOT / tex
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        m = re.search(
            rf"%% ARTEFACT-BEGIN {re.escape(block)}.*?%% ARTEFACT-END {re.escape(block)}",
            text, re.DOTALL)
        if m:
            spans.setdefault(tex, []).append((m.start(), m.end()))
    return spans


def main() -> int:
    if not INVENTORY.exists():
        print(f"REFUSED: no inventory at {INVENTORY}")
        return 2
    inv = json.loads(INVENTORY.read_text())
    spans = covered_spans(inv)

    tables = []
    for name, path in MANUSCRIPTS.items():
        if not path.exists():
            print(f"REFUSED: active manuscript missing: {path}")
            return 2
        tables.extend(enumerate_tables(name, path))

    if not tables:
        print("REFUSED: found 0 tabular environments in the active manuscripts. "
              "A coverage report over zero tables is not a report.")
        return 2

    # A table counts as covered when it lies INSIDE a verified artefact block.
    for t in tables:
        key = str(MANUSCRIPTS[t["manuscript"]].relative_to(ROOT))
        t["covered"] = any(a <= t["offset"] < b for a, b in spans.get(key, []))

    numeric = [t for t in tables if t["has_numbers"]]
    symbolic = [t for t in tables if not t["has_numbers"]]
    cov = [t for t in numeric if t["covered"]]
    unc = [t for t in numeric if not t["covered"]]

    print("verify-paper coverage of the ACTIVE manuscripts")
    print(f"  tabular environments        : {len(tables)}")
    print(f"  of which number-bearing     : {len(numeric)}")
    print(f"  of which symbolic (nothing to verify) : {len(symbolic)}")
    print()
    print(f"  COVERED   {len(cov)}/{len(numeric)}"
          f"  ({100 * len(cov) / max(1, len(numeric)):.0f}%)")
    print(f"  UNCOVERED {len(unc)}/{len(numeric)}")
    print()
    print("  This is a DOCUMENT-side measure: it says a producer is wired to the")
    print("  table, not that the numbers are right. verify_paper_artefacts.py is")
    print("  the only member that reconciles a value to its source.")
    print()
    for t in sorted(unc, key=lambda r: (r["manuscript"], r["line"])):
        print(f"    UNCOVERED  {t['manuscript']:14} :{t['line']:<6} {t['label']}")

    out = ROOT / "papers/method/artifact_baseline/table_coverage.json"
    out.write_text(json.dumps({
        "n_tabular": len(tables), "n_numeric": len(numeric),
        "n_symbolic": len(symbolic), "n_covered": len(cov),
        "tables": tables}, indent=2))
    print(f"\nwritten: {out.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
