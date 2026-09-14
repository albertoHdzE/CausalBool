#!/usr/bin/env python3
"""AUDIT03 — programme-wide duplicated-code census.

The audit has been collapsing one concept at a time as it tripped over them:
the engine (AUDIT02/P4e), the offset family (R2a.2), the description length
(R2b). That is reactive. This asks the question once, over the WHOLE research
programme -- the root repository and every subproject -- and answers it with a
list rather than an impression.

METHOD, and its limits, stated up front because a duplication metric is easy to
report dishonestly.

  Python: functions are compared by their NORMALISED ABSTRACT SYNTAX TREE.
  Docstrings and comments are stripped, so a copy that was re-commented does
  not hide; formatting is irrelevant for the same reason. Names ARE kept, so
  two functions differing only in a variable name are NOT reported -- that
  keeps the false-positive rate low at the cost of missing renamed copies.

  Wolfram: no parser available, so definitions are compared on normalised TEXT
  (whitespace collapsed, comments stripped). This is weaker and is labelled as
  such; it is why the offset-family parity at R2a.2 had to be settled in the
  kernel rather than by hashing.

WHAT IS NOT A DEFECT, and is excluded with its reason:

  * `archive/` -- kept deliberately, by the repository's own archive policy.
  * `venv/`, `.venv/`, `node_modules/`, `site-packages/` -- not our code.
  * `src/external/ccapi/` -- vendored third party, a dependency boundary.
  * `imp-prices/vendor/` -- a deliberate vendored copy under the two-copies
    rule, byte-identical to its source by design and pinned as such.
  * trivial bodies (fewer than MIN_STMTS statements) -- `return self.x`
    collides constantly and means nothing.

A subproject reimplementing a routine that the root already owns IS reported,
because that is precisely the failure this audit exists to remove: one concept
with many homes, drifting apart silently.

Run:
    venv/bin/python audit/AUDIT03_R2_collapse/duplication_census.py
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
import warnings
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
LINE = "-" * 78

EXCLUDE_PARTS = ("venv", ".venv", "node_modules", "site-packages", "__pycache__",
                 "archive", ".git", "build", "dist", ".ipynb_checkpoints")
# Each replication package vendors the ORIGINAL AUTHORS' code under
# <project>/reference/ so the replication can be checked against it. That is a
# dependency boundary, exactly like src/external/ccapi: duplication inside
# somebody else's codebase is not our defect and we must not "fix" it. Their
# internal repetition dominated the first run of this census -- 13 copies of one
# helper in kaust_path_project alone -- and would have buried our own.
EXCLUDE_PREFIX = ("src/external/ccapi", "imp-prices/vendor",
                  "imp-causal-paper/reference", "imp-causalNet-paper/reference",
                  "imp-pathinfo-paper/reference", "imp-prices/reference")
MIN_STMTS = 4          # below this, collisions are noise
MIN_WL_CHARS = 120     # same idea for the text-compared Wolfram side


def excluded(p: Path) -> bool:
    rel = p.relative_to(ROOT).as_posix()
    if any(rel.startswith(x) for x in EXCLUDE_PREFIX):
        return True
    return any(part in EXCLUDE_PARTS for part in p.parts)


def strip_docstring(node) -> list:
    body = list(node.body)
    if (body and isinstance(body[0], ast.Expr)
            and isinstance(body[0].value, ast.Constant)
            and isinstance(body[0].value.value, str)):
        body = body[1:]
    return body


def norm_python(fn: ast.AST) -> tuple[str, int]:
    """Structural digest of a function body, docstring removed."""
    body = strip_docstring(fn)
    if len(body) < MIN_STMTS:
        return "", len(body)
    mod = ast.Module(body=body, type_ignores=[])
    try:
        dump = ast.dump(mod, annotate_fields=False, include_attributes=False)
    except Exception:
        return "", len(body)
    return hashlib.sha1(dump.encode()).hexdigest()[:16], len(body)


WL_COMMENT = re.compile(r"\(\*.*?\*\)", re.S)
# A body whose FIRST statement delegates to a package symbol is a forwarder,
# whatever follows it in the extraction window.
FORWARDER = re.compile(r"^\s*Integration`[A-Za-z]+`[A-Za-z][A-Za-z0-9]*\[")
WL_DEF = re.compile(
    r"^\s*([A-Za-z][A-Za-z0-9`]*)\s*\[[^\]]*\]\s*:=", re.M)


def scan_python():
    """{digest: [(path, funcname, nstmts)]}"""
    table = defaultdict(list)
    for p in ROOT.rglob("*.py"):
        if excluded(p):
            continue
        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore")
                tree = ast.parse(p.read_text(encoding="utf-8", errors="replace"))
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                dig, n = norm_python(node)
                if dig:
                    table[dig].append(
                        (p.relative_to(ROOT).as_posix(), node.name, n))
    return table


def scan_wolfram():
    """Definition bodies compared on normalised text. Weaker; labelled so."""
    table = defaultdict(list)
    for ext in ("*.m", "*.wl"):
        for p in ROOT.rglob(ext):
            if excluded(p):
                continue
            txt = WL_COMMENT.sub(" ", p.read_text(encoding="utf-8",
                                                  errors="replace"))
            for m in WL_DEF.finditer(txt):
                start = m.end()
                # A body ends at "\n];" OR at the start of the NEXT definition,
                # whichever comes first. Assuming the former alone made a
                # one-line definition swallow everything up to the next block,
                # which is how the post-collapse forwarders kept being reported
                # as duplicated logic.
                e1 = txt.find("\n];", start)
                e1 = e1 + 3 if e1 != -1 else len(txt)
                nxt = WL_DEF.search(txt, start)
                e2 = nxt.start() if nxt else len(txt)
                end = min(e1, e2, start + 1500)
                body = " ".join(txt[start:end].split())
                # A pure FORWARDER is not duplicated logic. After a collapse the
                # delegating stubs are identical by construction, and reporting
                # them would make this census cry wolf about work already done
                # -- the same failure R6.4 fixed in the paper-number gate.
                if FORWARDER.match(body):
                    continue
                if len(body) < MIN_WL_CHARS:
                    continue
                dig = hashlib.sha1(body.encode()).hexdigest()[:16]
                table[dig].append(
                    (p.relative_to(ROOT).as_posix(), m.group(1), len(body)))
    return table


def project_of(path: str) -> str:
    top = path.split("/")[0]
    return top if top.startswith(("imp-", "index-")) else "ROOT"


def report(name: str, table: dict, unit: str):
    dups = {k: v for k, v in table.items() if len(v) > 1}
    # Same file twice is an overload or a redefinition inside one module; it is
    # a different problem from one concept living in two files.
    cross = {k: v for k, v in dups.items()
             if len({x[0] for x in v}) > 1}
    print(f"\n  {name}: {len(table)} distinct bodies, "
          f"{len(dups)} with more than one definition, "
          f"{len(cross)} spanning MORE THAN ONE FILE")
    rows = []
    for k, v in sorted(cross.items(), key=lambda x: -len(x[1])):
        projects = sorted({project_of(f) for f, _, _ in v})
        rows.append({"digest": k, "copies": len(v),
                     "projects": projects,
                     "cross_project": len(projects) > 1,
                     "sites": [{"file": f, "name": nm, unit: n}
                               for f, nm, n in sorted(v)]})
    return rows


def main() -> int:
    print("AUDIT03 — programme-wide duplicated-code census")
    print("\n  Excluded, each for a stated reason: archive/ (deliberate policy),")
    print("  venv and site-packages (not ours), src/external/ccapi (vendored),")
    print("  imp-prices/vendor (two-copies rule, pinned byte-identical).")

    py = scan_python()
    wl = scan_wolfram()

    print(f"\n{LINE}\nPYTHON — normalised AST, docstrings and comments stripped\n{LINE}")
    py_rows = report("python", py, "stmts")
    xproj = [r for r in py_rows if r["cross_project"]]
    print(f"    of which CROSS-PROJECT: {len(xproj)}")
    print(f"\n  {'copies':>7}  {'projects':<28} first two sites")
    for r in py_rows[:25]:
        s = r["sites"]
        mark = "  <-- CROSS-PROJECT" if r["cross_project"] else ""
        print(f"  {r['copies']:>7}  {','.join(r['projects']):<28}"
              f"{s[0]['file']}::{s[0]['name']}{mark}")
        print(f"  {'':>7}  {'':<28}{s[1]['file']}::{s[1]['name']}")

    print(f"\n{LINE}\nWOLFRAM — normalised TEXT (weaker; see the header)\n{LINE}")
    wl_rows = report("wolfram", wl, "chars")
    print(f"\n  {'copies':>7}  symbol / sites")
    for r in wl_rows[:15]:
        s = r["sites"]
        print(f"  {r['copies']:>7}  {s[0]['name']}")
        for x in s:
            print(f"  {'':>7}    {x['file']}")

    out = {"python_cross_file": py_rows, "wolfram_cross_file": wl_rows,
           "python_cross_project": len(xproj),
           "excluded_prefixes": list(EXCLUDE_PREFIX),
           "excluded_parts": list(EXCLUDE_PARTS),
           "min_stmts": MIN_STMTS, "min_wl_chars": MIN_WL_CHARS}
    (HERE / "duplication_census.json").write_text(json.dumps(out, indent=1))
    print(f"\nwritten: {HERE / 'duplication_census.json'}")
    print("\n  A digest collision is a CANDIDATE, not a verdict. Each is")
    print("  adjudicated in DUPLICATION.md: some are genuine one-concept-many-")
    print("  homes defects, some are independent code that happens to have the")
    print("  same shape, and the two must not be confused.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
