#!/usr/bin/env python
"""Full ledger lint for imp-prices FINDINGS.md (AUDIT01/T5.4).

Extends scripts/lint_ledger_c18.py from one entry to EVERY C-section row.
For each row: collect the artifacts it cites (backticked paths that exist),
harvest every numeric leaf from those JSONs, then check that every DECIMAL
statistics token quoted in the row text is present among those values
(exact string match, or match after rounding to the printed precision).
Integers are deliberately NOT verified (years, sizes, seeds, sample counts are
structural context); decimals are the statistics proper.

REPORT-FIRST policy (T5.4): default mode only reports. --strict exits non-zero
on any unverified decimal. Fixes enter by the T2.1 addendum protocol AFTER
author review - never silent edits.

Output: results/ledger_lint_full/report.md + console summary.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
FINDINGS = ROOT / "FINDINGS.md"
RESULTS_DIR = ROOT / "results"
OUT = RESULTS_DIR / "ledger_lint_full" / "report.md"

ROW_RE = re.compile(r"^\| (C\d+) \|(.*?)\|(.*?)\|(.*?)\|\s*$", re.S | re.M)
DECIMAL_RE = re.compile(r"(?<![\d.])(\d+\.\d+)(?![\d])")
BACKTICK_RE = re.compile(r"`([^`]+\.(?:json|csv))`")


def harvest_numbers(node, out: set):
    if isinstance(node, dict):
        for v in node.values():
            harvest_numbers(v, out)
    elif isinstance(node, list):
        for v in node:
            harvest_numbers(v, out)
    elif isinstance(node, bool):
        pass
    elif isinstance(node, (int, float)):
        out.add(float(node))
        out.add(round(float(node) * 100, 1))       # percentage renderings
        out.add(round(float(node), 1))
        out.add(round(float(node), 2))
        out.add(round(float(node), 3))


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--strict", action="store_true")
    args = ap.parse_args()

    text = FINDINGS.read_text()
    lines = text.splitlines()
    # locate table-row lines for windowed citation resolution
    row_line_idx: dict[str, int] = {}
    for i, ln in enumerate(lines):
        m = re.match(r"^\| (C\d+) \|", ln)
        if m:
            row_line_idx.setdefault(m.group(1), i)

    def cited_for(cid: str, claim: str) -> tuple[list[str], list[str]]:
        """Row backticks UNION nearest-preceding-prose backticks (30 lines)."""
        cited = [p for p in BACKTICK_RE.findall(claim)]
        start = row_line_idx.get(cid, 0)
        window = "\n".join(lines[max(0, start - 30):start])
        cited += [p for p in BACKTICK_RE.findall(window)]
        seen, ordered = set(), []
        for p in cited:
            p2 = p.replace("\\_", "_")
            if p2 not in seen:
                seen.add(p2)
                ordered.append(p2)
        return ordered, []

    def harvest_csv(path: Path, out: set):
        try:
            for tok in re.findall(r"-?\d+\.\d+", path.read_text()):
                v = float(tok)
                out.update({v, round(v * 100, 1), round(v, 1), round(v, 2), round(v, 3)})
        except Exception:
            pass

    rows = []
    for m in ROW_RE.finditer(text):
        cid, claim = m.group(1), m.group(2)
        if cid.startswith("C") and cid[1:].isdigit():
            rows.append((cid, claim))

    report: list[str] = ["# Ledger lint — full sweep (AUDIT01/T5.4)", "",
                         "Report-first: unverified decimals listed for author review.",
                         "'Unverified' means: no machine-readable value equal to the printed",
                         "decimal was reachable from the row's own or nearby citations — it is",
                         "NOT an assertion of error. Author review adjudicates each.", ""]
    total_quoted = total_unverified = 0
    per_row_lines: list[str] = []

    for cid, claim in rows:
        cited, _ = cited_for(cid, claim)
        values: set[float] = set()
        missing_files = []
        for rel in cited:
            path = ROOT / rel
            if not path.exists() and not rel.startswith("reference"):
                path = RESULTS_DIR / Path(rel).name
            if path.suffix == ".csv" and path.exists():
                harvest_csv(path, values)
                continue
            if not path.exists():
                missing_files.append(rel)
                continue
            try:
                harvest_numbers(json.loads(path.read_text()), values)
            except Exception as exc:  # noqa: BLE001
                missing_files.append(f"{rel} ({type(exc).__name__})")

        quoted = [t for t in DECIMAL_RE.findall(claim.replace("\\_", "_"))]
        unverified = []
        for tok in quoted:
            total_quoted += 1
            v = float(tok)
            if not any(abs(v - c) < 10 ** -(len(tok.split(".")[1])) for c in values):
                unverified.append(tok)
        total_unverified += len(unverified)

        verified = len(quoted) - len(unverified)
        line = f"- **{cid}**: {verified}/{len(quoted)} quoted decimals verified"
        if unverified:
            line += f"; UNVERIFIED: {unverified}"
        if missing_files:
            line += f"; unreadable citations: {missing_files}"
        if unverified or missing_files:
            per_row_lines.append(line)

    report.append(f"- rows parsed: {len(rows)}")
    report.append(f"- decimal statistics quoted: {total_quoted}")
    report.append(f"- unverified against reachable artifacts: {total_unverified}")
    report.append("")
    report.extend(per_row_lines if per_row_lines else ["- none — every quoted decimal traces to its cited artifact."])
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text("\n".join(report) + "\n")
    print("\n".join(report[:4]))
    print(f"full report: {OUT}")
    if args.strict and total_unverified:
        print("STRICT: unverified decimals present -> exit 1")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
