"""Census of NON-ALGORITHMIC complexity measures across the whole tree.

AUDIT04-E, author directive 2026-09-07: remove every naive and Shannon-derived
complexity measure, and make the two comparison measures BDM and the index-set
(Kolmogorov-approximation) program length.

WHY A NEW DETECTOR RATHER THAN THE EXISTING GUARD. `tests/analysis/
test_description_length_is_algorithmic.py` matches ENSEMBLE VOCABULARY -- the
words `entropy`, `shannon`, `Counter`, `probabilit`. Measured 2026-09-07, that
regex catches entropy that is LABELLED and misses entropy that is COMPUTED:

    "h = -sum(p * math.log2(p))  # entropy"   -> CAUGHT (by the comment)
    "h = -sum(p * math.log2(p))"              -> MISSED
    D_v2's actual line                        -> MISSED

Its own positive control passes because of a code comment. So this census works
on SHAPE: a probability-like quantity multiplied by its own logarithm, a
normalisation into a probability, a frequency table, or a log of a combinatorial
count used as a description length.

Every hit is CLASSIFIED, never auto-edited. Three kinds exist and they have
different correct outcomes:

  ours        code that produces a number this programme claims -> REPLACE
  replication code that must reproduce another author's published table, where
              using our measure would make the replication unfaithful -> KEEP,
              and declare. imp-pathinfo's mirror is already a declared exception
              of exactly this type.
  archive     doc/ and workspaces/ are frozen provenance -> DO NOT REWRITE
              (plan stop condition)

Refuses on an empty scan and prints its denominator.
"""
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

# ── what counts as non-algorithmic ──────────────────────────────────────────
# SHAPE, not vocabulary. Each pattern is a way of computing a Shannon-like or
# purely combinatorial quantity.
PATTERNS: dict[str, re.Pattern] = {
    # p * log(p), in any spelling, including the two-term binary form
    "shannon_plogp": re.compile(
        r"(\w+)\s*\*\s*(?:math\.|np\.|numpy\.)?log2?\s*\(\s*\1\s*\)"
        r"|log2?\s*\(\s*(\w+)\s*\)\s*\*\s*\2\b"),
    # scipy / numpy entropy helpers
    "entropy_call": re.compile(
        r"\b(?:scipy\.stats\.|stats\.)?entropy\s*\(|shannon_entropy\s*\(", re.I),
    # a count normalised into a probability, the step that precedes plogp
    "count_to_prob": re.compile(
        r"=\s*\w*(?:count|freq|n_\w+|ones|hits)\w*\s*/\s*(?:\w*(?:total|sum|size|n)\w*|len\()", re.I),
    # log of a combinatorial count used as a code length (HierarchyEncoder shape)
    "combinatorial_code": re.compile(
        r"log2?\s*\(\s*(?:math\.)?comb\s*\(|log2?\s*\(\s*(?:math\.)?factorial\s*\("),
    # frequency tables feeding a length
    "frequency_table": re.compile(r"\bCounter\s*\(|\.value_counts\s*\(", re.I),
}

# Where a hit lives decides what to do about it, not whether it is a hit.
ARCHIVE_PARTS = {"doc", "workspaces", "archive", "4ClaudeCode", "reference", "external"}
REPLICATION_ROOTS = {"imp-causal-paper", "imp-causalNet-paper",
                     "imp-pathinfo-paper", "imp-prices"}
SKIP_PARTS = {"venv", ".venv", "__pycache__", "node_modules", ".git",
              "site-packages", "build", "dist"}


def classify(rel: Path) -> str:
    parts = set(rel.parts)
    if parts & ARCHIVE_PARTS:
        return "archive"
    if rel.parts and rel.parts[0] in REPLICATION_ROOTS:
        return "replication"
    if rel.parts and rel.parts[0] == "index-deconvolution":
        return "sibling-pkg"
    return "ours"


def is_complexity_context(text: str) -> bool:
    """Is this file plausibly ABOUT complexity, or merely using a log?

    A log2 in a plotting axis is not a complexity measure. Requiring one of
    these tokens keeps the census on measures rather than on arithmetic.
    """
    return bool(re.search(
        r"\b(complexity|description[_ ]length|\bD_v2\b|dv2|\bD_bio\b|bdm|kolmogorov"
        r"|entropy|encoder|cost|bits|compress|lempel|ziv|\bLZ\b)", text, re.I))


def main() -> int:
    files = [p for p in ROOT.rglob("*.py")
             if not (set(p.relative_to(ROOT).parts) & SKIP_PARTS)]
    if not files:
        print("CENSUS: REFUSED — scanned 0 files.")
        return 2

    findings: list[tuple[str, str, int, str, str]] = []
    scanned = 0
    for p in files:
        try:
            text = p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        scanned += 1
        if not is_complexity_context(text):
            continue
        rel = p.relative_to(ROOT)
        kind = classify(rel)
        # strip docstrings so prose explaining why entropy is NOT used is not a hit
        try:
            tree = ast.parse(text)
            doc_lines: set[int] = set()
            for node in ast.walk(tree):
                if isinstance(node, (ast.Module, ast.ClassDef,
                                     ast.FunctionDef, ast.AsyncFunctionDef)):
                    d = ast.get_docstring(node, clean=False)
                    if d and node.body:
                        first = node.body[0]
                        doc_lines.update(
                            range(first.lineno, (first.end_lineno or first.lineno) + 1))
        except SyntaxError:
            doc_lines = set()
        for i, line in enumerate(text.splitlines(), 1):
            if i in doc_lines:
                continue
            stripped = line.split("#", 1)[0]
            for name, pat in PATTERNS.items():
                if pat.search(stripped):
                    findings.append((kind, str(rel), i, name, line.strip()[:96]))

    print(f"CENSUS: scanned {scanned} python files under {ROOT.name}")
    print(f"        {len(findings)} non-algorithmic measure sites\n")

    by_kind: dict[str, list] = {}
    for f in findings:
        by_kind.setdefault(f[0], []).append(f)

    for kind in ("ours", "sibling-pkg", "replication", "archive"):
        rows = by_kind.get(kind, [])
        files_hit = sorted({r[1] for r in rows})
        print(f"── {kind.upper():12s} {len(rows):4d} sites in {len(files_hit)} files")
        for fn in files_hit:
            hits = [r for r in rows if r[1] == fn]
            kinds = sorted({h[3] for h in hits})
            print(f"     {fn}  ({len(hits)}) {','.join(kinds)}")
        print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
