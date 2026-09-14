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
import collections
import hashlib
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
# AUDIT03/R6.4: entries are keyed by CONTENT, not by line number. Keying by
# line meant that inserting a paragraph reported every later entry as
# REMOVED+ADDED -- 91 such entries for zero value changes on one occasion, and
# 37+30 for zero on another during this very audit. A gate that reports dozens
# of findings when nothing has changed teaches the reader to regenerate blindly,
# which is the opposite of what it is for. The key is a digest of the line with
# its numbers MASKED OUT, so a sentence keeps its identity when it moves and
# loses it only when its wording changes.
KEYMASK = re.compile(r"\d")


def content_key(path_name: str, kind: str, text: str, seen: dict) -> str:
    masked = KEYMASK.sub("#", " ".join(text.split()))
    h = hashlib.sha1(masked.encode("utf-8")).hexdigest()[:12]
    base = f"{path_name}#{kind}@{h}"
    seen[base] = seen.get(base, 0) + 1
    return base if seen[base] == 1 else f"{base}~{seen[base]}"


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
    seen: dict = {}

    def flush_table():
        nonlocal pending_table_lines, table_start, current_label
        if not pending_table_lines:
            return
        nums = []
        for ln in pending_table_lines:
            nums.extend(m.group(0).strip() for m in NUM_RE.finditer(ln))
        if nums:
            entries.append({
                "id": content_key(path.name, "tbl",
                                  "".join(pending_table_lines), seen),
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
                    "id": content_key(path.name, "L", line, seen),
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

        # AUDIT03/R6.4: line position is METADATA, not content. Comparing it
        # made every move a "change"; excluding it makes a move visible as a
        # move and reserves failure for what actually matters -- a value.
        POSITION = ("line", "start_line")

        def payload(e):
            return {k: v for k, v in e.items() if k not in POSITION}

        def pos(e):
            return e.get("line", e.get("start_line"))

        removed = sorted(set(old) - set(new))
        added = sorted(set(new) - set(old))
        both = set(old) & set(new)
        changed = sorted(k for k in both if payload(old[k]) != payload(new[k]))
        moved = sorted(k for k in both
                       if payload(old[k]) == payload(new[k])
                       and pos(old[k]) != pos(new[k]))

        # The value multiset is what a reader actually cares about, and it is
        # what I ended up computing by hand every time this gate cried wolf.
        # It is reported here so nobody has to do that again.
        def multiset(entries):
            c = collections.Counter()
            for k, v in entries.items():
                for x in v["numbers"]:
                    c[(k.split("#")[0], x)] += 1
            return c

        gained = multiset(new) - multiset(old)
        lost = multiset(old) - multiset(new)

        if moved and not (removed or added or changed):
            print(f"PAPER-NUMBER GATE PASS: {len(new)} entries, "
                  f"{len(moved)} moved, NO value changed")
            print("  (a move is not a finding; content keys make it visible "
                  "without failing)")
            sys.exit(0)
        if not (removed or added or changed or moved):
            print(f"PAPER-NUMBER GATE PASS: {len(new)} entries identical")
            sys.exit(0)

        print("PAPER-NUMBER GATE FAIL")
        for k in changed:
            print(f"  CHANGED: {k}\n    was: {old[k]['numbers']}"
                  f"\n    now: {new[k]['numbers']}")
        for k in removed:
            print(f"  REMOVED: {k} (was L{pos(old[k])}) -> {old[k]['numbers'][:4]}")
        for k in added:
            print(f"  ADDED:   {k} (now L{pos(new[k])}) -> {new[k]['numbers'][:4]}")
        if moved:
            print(f"  moved without changing: {len(moved)} entries "
                  f"(not a failure on their own)")
        print("\n  VALUE MULTISET — the question a reader actually asks:")
        if not gained and not lost:
            print("    no value gained or lost; every difference above is "
                  "wording or position")
        for k, n in sorted(gained.items()):
            print(f"    GAINED {k[0]} {k[1]} x{n}")
        for k, n in sorted(lost.items()):
            print(f"    LOST   {k[0]} {k[1]} x{n}")
        sys.exit(1)
    BASE.mkdir(parents=True, exist_ok=True)
    SNAP.write_text(json.dumps(fresh, indent=1, sort_keys=True) + "\n")
    total = len(fresh["entries"])
    tables = sum(1 for v in fresh["entries"].values() if v["kind"] == "table")
    print(f"snapshot written: {SNAP} ({total} entries, {tables} table blocks)")


if __name__ == "__main__":
    main()
