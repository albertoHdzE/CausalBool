#!/usr/bin/env python3
"""Fail if any notebook figure is defined outside ``viz.py``, or twice.

``viz.py`` is the declared single owner of every picture the Luminal notebooks
draw. The failure this guard exists to stop is the cheap one: a notebook that
pastes its own ``show_timeline`` into a cell, so that a later fix to the owner
silently leaves one figure stale while the prose claims both agree.

Both languages of the notebook directory are scanned -- ``.py`` modules and the
code cells inside ``.ipynb`` JSON -- because the whole point is that a cell is a
hiding place an ordinary import check never looks in.

The guard refuses to pass on nothing: if it scans zero files, or finds zero
owned renders to check, it exits 2 rather than printing a green line over an
empty denominator.

Exit codes: 0 all renders single and owned, 1 a violation, 2 nothing scanned.
"""

from __future__ import annotations

import ast
import json
from pathlib import Path
import sys
from typing import Dict, List, Tuple


HERE = Path(__file__).resolve().parent
OWNER = "viz.py"

# Only these are owned. A notebook remains free to define a one-off helper that
# is not a figure; this guard makes no claim about those.
OWNED_PREFIXES = ("show_", "narrate")


def _definitions(source: str, origin: str) -> List[Tuple[str, str]]:
    """Every top-level function definition in one chunk of source."""

    try:
        tree = ast.parse(source)
    except SyntaxError:
        # A cell with a magic or shell escape is not Python and defines nothing
        # this guard can own. It is counted as scanned and skipped.
        return []
    found = []
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.name.startswith(OWNED_PREFIXES):
                found.append((node.name, origin))
    return found


def collect() -> Tuple[Dict[str, List[str]], int]:
    """Map each owned render name to every place it is defined."""

    where: Dict[str, List[str]] = {}
    scanned = 0

    for path in sorted(HERE.glob("*.py")):
        if path.name == Path(__file__).name:
            continue
        scanned += 1
        for name, origin in _definitions(path.read_text(encoding="utf-8"), path.name):
            where.setdefault(name, []).append(origin)

    for path in sorted(HERE.glob("*.ipynb")):
        scanned += 1
        notebook = json.loads(path.read_text(encoding="utf-8"))
        for index, cell in enumerate(notebook.get("cells", [])):
            if cell.get("cell_type") != "code":
                continue
            source = "".join(cell.get("source", []))
            for name, _ in _definitions(source, ""):
                where.setdefault(name, []).append(f"{path.name} cell {index}")

    return where, scanned


def main() -> int:
    where, scanned = collect()

    if scanned == 0:
        print("REFUSED: scanned 0 files under", HERE, file=sys.stderr)
        return 2
    if not where:
        print(
            f"REFUSED: scanned {scanned} files and found 0 owned renders; "
            f"expected at least one definition in {OWNER}",
            file=sys.stderr,
        )
        return 2

    violations = []
    for name, origins in sorted(where.items()):
        if len(origins) > 1:
            violations.append(f"{name} defined {len(origins)} times: {', '.join(origins)}")
        elif origins[0] != OWNER:
            violations.append(f"{name} defined in {origins[0]}, not in {OWNER}")

    print(f"scanned {scanned} files under {HERE.name}/")
    print(f"owned renders checked: {len(where)} ({', '.join(sorted(where))})")

    if violations:
        print(f"FAIL: {len(violations)} violation(s)", file=sys.stderr)
        for line in violations:
            print(f"  - {line}", file=sys.stderr)
        return 1

    print(f"PASS: all {len(where)} renders defined exactly once, in {OWNER}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
