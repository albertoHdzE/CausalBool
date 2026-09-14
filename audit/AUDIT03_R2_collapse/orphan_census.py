"""AUDIT03 — which defined functions are never called?

The duplication census asked "is this concept defined more than once". This asks
the complementary question the user raised: "is this concept called at all".
Dead code is the other half of the monolithic-code law — a function nobody calls
is a function nobody maintains, and it drifts exactly as a duplicate does. This
audit already found two of them the hard way (a TSK-MIXED-001 copy of the
description length that turned out never to be invoked, and a `pair` unpack in
complexity_analysis.py that could only ever have raised).

METHOD, and where it is weak -- stated plainly, because the weakness decides how
the output must be read.

  * Python: a name-based reachability sweep. Every `def` in the tree is a
    candidate; a candidate is CALLED if its name appears anywhere outside its
    own definition, in any Python file, as a call, a reference, an export, a
    decorator target, or a string (entry points and CLI tables use strings).
  * This OVER-counts calls, so it UNDER-reports orphans. That is the safe
    direction: nothing here is a false accusation, but the true orphan set is
    larger than what is printed.
  * Dunder methods, `main`, `test_*` and pytest fixtures are excluded by role,
    not by evidence -- their caller is a framework.
  * A hit inside the SAME file still counts as called, so private helpers used
    once locally are not reported.

So: every name printed is genuinely unreferenced anywhere in the tree. The list
is a floor, not a ceiling.

Usage:  venv/bin/python audit/AUDIT03_R2_collapse/orphan_census.py [--all]
"""
from __future__ import annotations

import ast
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

SKIP_DIRS = {"archive", "venv", ".venv", "node_modules", ".git", "__pycache__",
             "site-packages", "reference", "vendor", "build", "dist",
             "egg-info", ".pytest_cache", ".ipynb_checkpoints"}
SKIP_PATH_PARTS = ("src/external/ccapi", "imp-prices/vendor")

# Excluded by ROLE: their caller is a framework, not our code.
FRAMEWORK = re.compile(r"^(__\w+__|main|test_\w*|setUp\w*|tearDown\w*|conftest)$")


def is_ours(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    if any(part in SKIP_DIRS for part in p.parts):
        return False
    return not any(s in rel for s in SKIP_PATH_PARTS)


def main() -> int:
    show_all = "--all" in sys.argv
    files = [p for p in ROOT.rglob("*.py") if is_ours(p)]
    if not files:
        print("REFUSED: found no Python files. A census over zero files is not a result.")
        return 2

    # 1. every definition
    defs: dict[str, list[str]] = defaultdict(list)
    for p in files:
        try:
            tree = ast.parse(p.read_text(errors="replace"))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                defs[node.name].append(f"{p.relative_to(ROOT)}:{node.lineno}")

    # 2. every referenced name, anywhere, by any means
    referenced: dict[str, int] = defaultdict(int)
    for p in files:
        text = p.read_text(errors="replace")
        try:
            tree = ast.parse(text)
        except SyntaxError:
            for name in defs:
                referenced[name] += text.count(name)
            continue
        own_defs = {n.lineno for n in ast.walk(tree)
                    if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        for node in ast.walk(tree):
            if isinstance(node, ast.Name):
                referenced[node.id] += 1
            elif isinstance(node, ast.Attribute):
                referenced[node.attr] += 1
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.lineno not in own_defs:
                    referenced[node.name] += 1
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                # entry points, CLI dispatch tables, getattr by name
                for name in defs:
                    if name in node.value:
                        referenced[name] += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    referenced[a.name.split(".")[-1]] += 1
                    if a.asname:
                        referenced[a.asname] += 1

    orphans = {}
    for name, sites in defs.items():
        if FRAMEWORK.match(name):
            continue
        if referenced.get(name, 0) > 0:
            continue
        orphans[name] = sites

    by_project: dict[str, list[str]] = defaultdict(list)
    for name, sites in orphans.items():
        proj = sites[0].split("/")[0]
        if proj.endswith(".py"):
            proj = "ROOT"
        by_project[proj].append(f"{name}  ({sites[0]})")

    print(f"Python files scanned : {len(files)}")
    print(f"functions defined    : {sum(len(v) for v in defs.values())}")
    print(f"distinct names       : {len(defs)}")
    print(f"NEVER REFERENCED     : {len(orphans)}  "
          f"({100 * len(orphans) / max(1, len(defs)):.1f}% of distinct names)\n")
    print("Read as a FLOOR: the sweep over-counts references, so the true orphan")
    print("set is larger. Nothing listed is a false accusation.\n")

    for proj in sorted(by_project, key=lambda k: -len(by_project[k])):
        entries = sorted(by_project[proj])
        print(f"  {proj}: {len(entries)}")
        for e in (entries if show_all else entries[:8]):
            print(f"      {e}")
        if not show_all and len(entries) > 8:
            print(f"      ... {len(entries) - 8} more (--all to list)")

    out = ROOT / "audit" / "AUDIT03_R2_collapse" / "orphan_census.json"
    out.write_text(json.dumps(
        {"n_files": len(files), "n_names": len(defs),
         "orphans": {k: v for k, v in sorted(orphans.items())}}, indent=2))
    print(f"\nwritten: {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
