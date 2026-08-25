#!/usr/bin/env python3
"""AUDIT01/T0.5 - paper-number snapshot and drift gate.

Modes:
  snapshot  (default)  Extract every number-bearing line/table from both live
                       manuscripts into papers/method/artifact_baseline/paper_numbers.json
  --check              Re-extract and diff against the committed snapshot;
                       exit 1 listing changed/added/removed IDs.

Extraction is purely regex-deterministic: for each .tex line we record all
decimal numbers, percentages, and scientific-notation tokens, plus a flag and
label when the line sits inside a table/table* environment. Volatile metadata
(generation time) lives outside the compared payload.
"""
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
BASE = REPO / "papers" / "method" / "artifact_baseline"
SNAP = BASE / "paper_numbers.json"

MANUSCRIPTS = [
    REPO / "papers/method/manuscript_formal/method_paper.tex",
    REPO / "papers/method/manuscript_computational/comp_paper.tex",
]

NUM_RE = re.compile(
    r"-?\d+\.\d+(?:[eE][+-]?\d+)?"      # decimals / sci-notation
    r"|-\d+[eE][+-]?\d+"                 # integer sci-notation
    r"|\d+(?:\.\d+)?\s*(?:\\?%|\\\\%)"   # percentages
)
TABLE_BEGIN = re.compile(r"\\begin\{table\*?\}")
TABLE_END = re.compile(r"\\end\{table\*?\}")
LABEL_RE = re.compile(r"\\label\{([^}]*)\}")
SECTION_RE = re.compile(r"\\(?:sub)*section\{([^}]*)\}")


def extract_file(path: Path):
    """Return list of entry dicts for one manuscript."""
    entries = []
    if not path.exists():
        return entries
    in_table = False
    current_label = None
    current_section = ""
    pending_table_lines = []
    table_start = None

    def flush_table():
        nonlocal pending_table_lines, table_start, current_label
        if not pending_table_lines:
            return
        nums = []
        for ln in pending_table_lines:
            nums.extend(m.group(0).strip() for m in NUM_RE.finditer(ln))
        if nums:
            entries.append({
                "id": f"{path.name}#tbl@{table_start}",
                "kind": "table",
                "start_line": table_start,
                "label": current_label or "",
                "section": current_section,
                "n_lines": len(pending_table_lines),
                "numbers": nums,
            })
        pending_table_lines = []
        table_start = None
        current_label = None

    with path.open(encoding="utf-8", errors="replace") as fh:
        for lineno, line in enumerate(fh, 1):
            if TABLE_BEGIN.search(line):
                flush_table()
                in_table = True
                table_start = lineno
                m = LABEL_RE.search(line)
                current_label = m.group(1) if m else None
            elif TABLE_END.search(line):
                if in_table:
                    pending_table_lines.append(line)
                    flush_table()
                    in_table = False
                continue
            if in_table:
                if current_label is None:
                    m = LABEL_RE.search(line)
                    if m:
                        current_label = m.group(1)
                pending_table_lines.append(line)
                continue
            sm = SECTION_RE.search(line)
            if sm:
                current_section = sm.group(1)
            nums = [m.group(0).strip() for m in NUM_RE.finditer(line)]
            if nums:
                entries.append({
                    "id": f"{path.name}#L{lineno}",
                    "kind": "inline",
                    "line": lineno,
                    "section": current_section,
                    "numbers": nums,
                })
    flush_table()
    return entries


def build_snapshot():
    payload = {}
    for mp in MANUSCRIPTS:
        for e in extract_file(mp):
            payload[e["id"]] = {k: v for k, v in e.items() if k != "id"}
    return {
        "_meta": {
            "note": "compared payload excludes _meta; regenerate via tools/snapshot_paper_numbers.py",
            "files": [str(p.relative_to(REPO)) for p in MANUSCRIPTS],
        },
        "entries": payload,
    }


def main():
    mode = sys.argv[1] if len(sys.argv) > 1 else "snapshot"
    fresh = build_snapshot()
    if mode == "--check":
        if not SNAP.exists():
            print(f"GATE FAIL: snapshot missing at {SNAP}")
            sys.exit(1)
        old = json.loads(SNAP.read_text())["entries"]
        new = fresh["entries"]
        removed = sorted(set(old) - set(new))
        added = sorted(set(new) - set(old))
        changed = sorted(k for k in set(old) & set(new) if old[k] != new[k])
        if not (removed or added or changed):
            print(f"PAPER-NUMBER GATE PASS: {len(new)} entries identical")
            sys.exit(0)
        print("PAPER-NUMBER GATE FAIL")
        for k in removed:
            print(f"  REMOVED: {k}")
        for k in added:
            print(f"  ADDED:   {k} -> {new[k]['numbers'][:4]}")
        for k in changed:
            print(f"  CHANGED: {k}\n    was: {old[k]['numbers']}\n    now: {new[k]['numbers']}")
        sys.exit(1)
    BASE.mkdir(parents=True, exist_ok=True)
    SNAP.write_text(json.dumps(fresh, indent=1, sort_keys=True) + "\n")
    total = len(fresh["entries"])
    tables = sum(1 for v in fresh["entries"].values() if v["kind"] == "table")
    print(f"snapshot written: {SNAP} ({total} entries, {tables} table blocks)")


if __name__ == "__main__":
    main()
