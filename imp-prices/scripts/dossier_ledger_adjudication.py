#!/usr/bin/env python
"""Adjudication dossier for T5.4 ledger-lint residue (post-lint deep search).

READ-ONLY over protected history: searches the WHOLE artifact corpus
(results/, reference/, notebooks/, bitacora/) for every decimal the full lint
could not verify, instead of only the artifacts cited by each row. Percent-form
aware ("1.55 per cent" vs leaf 0.0155) and rounding-tolerant.

REPORT-FIRST: writes results/ledger_lint_full/adjudication_dossier.md only.
FINDINGS.md is never touched; fixes enter via the T2.1 addendum protocol AFTER
author adjudication. Verdict classes:
  FOUND-ELSEWHERE   value located in an artifact the row did not cite
  FOUND-IN-CITED    located in a cited artifact (lint miss, e.g. unreadable path)
  PROSE-ONLY        no artifact anywhere; candidate dated-addendum annotation
"""
from __future__ import annotations

import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINDINGS = ROOT / "FINDINGS.md"
OUT = ROOT / "results" / "ledger_lint_full" / "adjudication_dossier.md"

ROW_RE = re.compile(r"^\| (C\d+) \|(.*?)\|(.*?)\|(.*?)\|\s*$", re.S | re.M)
DEC_RE = re.compile(r"(?<![\d.])(\d+\.\d+)(?![\d])")
UNVERIFIED = {  # from report.md (T5.4): row -> list of unverified decimals
}

SEARCH_ROOTS = ["results", "reference", "notebooks", "bitacora"]
TEXT_SUFFIXES = {".json", ".csv", ".md", ".ipynb", ".txt"}
SKIP_PARTS = {".venv", "__pycache__", ".git"}


def load_report_unverified() -> dict:
    txt = (ROOT / "results" / "ledger_lint_full" / "report.md").read_text()
    out = {}
    for line in txt.splitlines():
        m = re.match(r"- \*\*(C\d+)\*\*:.*?UNVERIFIED: (\[.*?\])", line)
        if m:
            out[m.group(1)] = eval(m.group(2))  # noqa: S307 - own file, fixed format
    return out


def harvest_corpus():
    """corpus = list of (relpath, text)."""
    items = []
    for root in SEARCH_ROOTS:
        base = ROOT / root
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if any(part in SKIP_PARTS for part in p.parts):
                continue
            if p.is_file() and p.suffix.lower() in TEXT_SUFFIXES:
                try:
                    items.append((str(p.relative_to(ROOT)), p.read_text(errors="replace")))
                except OSError:
                    pass
    return items


def matches(token: str, value_txt: str) -> bool:
    """rounding-tolerant match of printed token against artifact numeric text."""
    t = float(token)
    # direct string or float parse
    try:
        v = float(value_txt)
    except ValueError:
        return False
    nd = len(token.split(".")[1])
    if round(v, nd) == round(t, nd):
        return True
    if round(v * 100, nd) == round(t, nd):  # fraction stored, quoted as per cent
        return True
    return False


NUMTXT = re.compile(r"-?\d+\.\d+(?:[eE][-+]?\d+)?")


def find_token(token: str, corpus):
    """Two-tier: Tier A machine artifacts (json/csv) outrank Tier B prose
    (md/ipynb/txt — bitácoras and notebook narratives QUOTE numbers; an echo
    there is not artifact verification)."""
    hits_a, hits_b = [], []
    for rel, text in corpus:
        tier = "A" if rel.lower().endswith((".json", ".csv")) else "B"
        if tier == "B":
            continue
        for nv in NUMTXT.findall(text):
            if matches(token, nv):
                idx = text.find(nv)
                line = text[max(0, idx - 60): idx + 40].replace("\n", " ")
                hits_a.append((rel, nv, line))
                break
    if hits_a:
        return "A", hits_a
    for rel, text in corpus:
        if rel.lower().endswith((".json", ".csv")) or rel.endswith("FINDINGS.md"):
            continue
        for nv in NUMTXT.findall(text):
            if matches(token, nv):
                idx = text.find(nv)
                line = text[max(0, idx - 60): idx + 40].replace("\n", " ")
                hits_b.append((rel, nv, line))
                break
    return ("B", hits_b) if hits_b else ("-", [])


def main():
    unv = load_report_unverified()
    corpus = harvest_corpus()
    print(f"rows with unverified decimals: {len(unv)}; corpus files: {len(corpus)}")

    lines = [
        "# Adjudication dossier — T5.4 residue (deep search)",
        "",
        f"Deep search over {len(corpus)} artifact files (whole results/reference/",
        "notebooks/bitacora corpus, not only row-cited artifacts). Percent-form",
        "and rounding tolerant. READ-ONLY w.r.t. FINDINGS.md: adjudicate per row,",
        "fixes land via the T2.1 dated-addendum protocol only.",
        "'PROSE-ONLY' is NOT an assertion of error (same semantics as report.md",
        "header): it means no machine-reachable source exists in this repo.",
        "",
    ]
    total = resolved = 0
    for cid in sorted(unv, key=lambda c: int(c[1:])):
        toks = unv[cid]
        m = ROW_RE.search(FINDINGS.read_text())
        lines.append(f"## {cid} — {len(toks)} decimal(s)")
        for tok in toks:
            total += 1
            tier, hits = find_token(tok, corpus)
            if tier == "A":
                resolved += 1
                rel, nv, ctx = hits[0]
                extra = f" (+{len(hits)-1} more files)" if len(hits) > 1 else ""
                lines.append(
                    f"- `{tok}` → **FOUND-IN-ARTIFACT** `{rel}` (value `{nv}`, "
                    f"context: …{ctx}…){extra}"
                )
            elif tier == "B":
                rel, nv, ctx = hits[0]
                extra = f" (+{len(hits)-1} more)" if len(hits) > 1 else ""
                lines.append(
                    f"- `{tok}` → **PROSE-ECHO ONLY** (no machine artifact; quoted "
                    f"in `{rel}`: …{ctx}…){extra} — needs dated-addendum annotation "
                    "or a re-executed producer"
                )
            else:
                lines.append(
                    f"- `{tok}` → **UNRESOLVED** — no artifact or prose source in "
                    "corpus; options: annotate as unrecoverable draw (DEV-2.2 "
                    "precedent) or correct if author knows the intended source"
                )
        lines.append("")
    lines.append("---")
    lines.append(f"Summary: {resolved}/{total} decimals located in artifacts; "
                 f"{total-resolved} PROSE-ONLY candidates for annotation.")
    OUT.write_text("\n".join(lines) + "\n")
    print(f"summary: {resolved}/{total} located -> {OUT}")


if __name__ == "__main__":
    main()
