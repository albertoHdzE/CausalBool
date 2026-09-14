#!/usr/bin/env python3
"""AUDIT04 Phase 2 - does importing a module DO anything?

WHY THIS EXISTS. Phase 3 must import 29 previously-untested modules in order to
test them. Importing a module that performs work at module level would, at best,
make the suite slow and non-deterministic, and at worst write into results/ or
figures/ during a test run -- the stale-artefact class this programme has
already been bitten by twice, once by its own mutation harness.

"It has an `if __name__ == '__main__'` guard" is NOT the same as "it is safe to
import", and that distinction is the whole point of this gate: a guard at the
bottom says nothing about the twenty lines above it.

METHOD, and where it is weak. This is a STATIC check: it walks the module-level
body of each file and classifies statements. It cannot see work hidden inside a
function called at import time, nor dynamic execution. It is therefore a
NECESSARY-not-sufficient screen, and its output says so. What it does catch is
the common shape -- a script whose body runs when touched.

Module-level statements are classified as:

  structural  imports, def, class, docstrings, `if __name__ == "__main__"`,
              plain assignments of literals or comprehensions
  benign      sys.path manipulation, logging config, warnings filters,
              matplotlib.use() -- import-time effects that are conventional and
              confined to the process
  UNSAFE      file I/O, printing, plotting, network, subprocess, directory
              creation, or a call whose result is discarded

Exit codes, three states as everywhere in this programme:
    0  every scanned module is import-safe
    1  at least one module does work at import time
    2  refused: zero modules scanned
"""
from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

# Callables whose appearance at module level means the import DOES something.
UNSAFE_CALLS = {
    "open", "print", "savefig", "show", "dump", "dumps_to_file", "write",
    "makedirs", "mkdir", "remove", "unlink", "rmtree", "copy", "copyfile",
    "run", "call", "check_output", "Popen", "system",
    "get", "post", "urlopen", "urlretrieve",
    "read_csv", "to_csv", "read_json", "connect",
}
# Import-time effects that are conventional, process-local and expected.
BENIGN_ATTRS = {
    "insert", "append",          # sys.path.insert / append
    "basicConfig", "getLogger", "setLevel",
    "filterwarnings", "simplefilter",
    "use",                       # matplotlib.use("Agg")
    "set_option", "set_printoptions", "seterr",
    "register",
}


def call_name(node: ast.AST) -> str | None:
    if not isinstance(node, ast.Call):
        return None
    f = node.func
    if isinstance(f, ast.Name):
        return f.id
    if isinstance(f, ast.Attribute):
        return f.attr
    return None


def is_main_guard(node: ast.AST) -> bool:
    if not isinstance(node, ast.If):
        return False
    t = node.test
    return (isinstance(t, ast.Compare)
            and isinstance(t.left, ast.Name) and t.left.id == "__name__")


def scan(path: Path) -> list[str]:
    """Unsafe module-level statements, as 'line: description'."""
    try:
        tree = ast.parse(path.read_text(errors="replace"))
    except SyntaxError as e:
        return [f"{e.lineno}: does not parse ({e.msg})"]

    findings: list[str] = []
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef, ast.Assign,
                             ast.AnnAssign, ast.AugAssign, ast.Pass)):
            # An assignment is structural UNLESS its value is an unsafe call:
            # `DATA = json.load(open(...))` runs at import.
            for sub in ast.walk(node) if isinstance(
                    node, (ast.Assign, ast.AnnAssign, ast.AugAssign)) else []:
                nm = call_name(sub)
                if nm in UNSAFE_CALLS and nm not in BENIGN_ATTRS:
                    findings.append(f"{node.lineno}: assignment calls {nm}() at import time")
                    break
            continue
        if is_main_guard(node):
            continue
        if isinstance(node, ast.Expr):
            if isinstance(node.value, ast.Constant):     # docstring
                continue
            nm = call_name(node.value)
            if nm is None:
                continue
            if nm in BENIGN_ATTRS:
                continue
            if nm in UNSAFE_CALLS:
                findings.append(f"{node.lineno}: {nm}() runs at import time")
            else:
                findings.append(f"{node.lineno}: bare call {nm}() at module level")
            continue
        if isinstance(node, (ast.If, ast.For, ast.While, ast.With, ast.Try)):
            # Control flow at module level that is not the __main__ guard.
            # `try: import x except ImportError:` is the common benign case.
            if isinstance(node, ast.Try) and all(
                    isinstance(b, (ast.Import, ast.ImportFrom, ast.Assign))
                    for b in node.body):
                continue
            # FALSE POSITIVE FIXED, AUDIT04 Phase 2. The idiom
            #     if str(src_dir) not in sys.path:
            #         sys.path.append(str(src_dir))
            # is how every script in this repo reaches src/, and the bare form
            # was already whitelisted while the guarded form -- the better one --
            # was flagged. A gate that penalises the more careful spelling
            # teaches people to write the careless one.
            if isinstance(node, ast.If) and node.body and all(
                    isinstance(b, ast.Expr) and call_name(b.value) in BENIGN_ATTRS
                    for b in node.body):
                continue
            kind = type(node).__name__
            findings.append(f"{node.lineno}: module-level {kind} executes on import")
    return findings


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--path", default="src", help="directory to scan")
    a = ap.parse_args()

    base = ROOT / a.path
    files = sorted(p for p in base.rglob("*.py")
                   if "external" not in p.parts and "__pycache__" not in p.parts)
    if not files:
        print(f"REFUSED: 0 modules found under {a.path}. "
              "A scan over nothing is not a pass.")
        return 2

    bad: dict[Path, list[str]] = {}
    for f in files:
        found = scan(f)
        if found:
            bad[f] = found

    print(f"IMPORT-SAFETY: {len(files) - len(bad)}/{len(files)} modules under "
          f"{a.path}/ are import-safe by static scan.")
    if bad:
        print("\nThese DO WORK when imported, so a test that imports them runs "
              "that work:")
        for f, items in sorted(bad.items()):
            print(f"\n  {f.relative_to(ROOT)}")
            for it in items:
                print(f"      {it}")
    print("\nStatic screen only: it cannot see work hidden inside a function "
          "that is called at import time.")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
