"""Assemble the standalone direct-index compiler.

Task L06 of ``plan/INDEX_ONLY_PLAN.md``, section 8.2. The exporter works from
an explicit allowlist of the direct modules, in dependency order. It does not
copy the previous hybrid export, it carries no decision-diagram or classical
code, and it never hides a dependency behind a runtime ``exec``.

Flattening five modules into one file would let a function's local variable
shadow a module-level name: ``compile_with_report`` binds a local called
``footprint`` and also calls ``dc.footprint``. Rather than rename anything, the
assembled file aliases each module name to the assembled module itself, so a
qualified call stays an attribute lookup on the module object and cannot be
captured by a local binding.
"""

from __future__ import annotations

import argparse
import ast
import hashlib
from pathlib import Path
import sys
from typing import List, Tuple

ROOT = Path(__file__).resolve().parent

# Dependency order. Nothing outside this list enters the export.
ALLOWLIST = (
    "schema_index.py",
    "direct_contract.py",
    "direct_constraints.py",
    "direct_optimizer.py",
    "direct_compiler.py",
)

INTERNAL = {path[:-3] for path in ALLOWLIST}

# Names the assembled module binds to itself, so that qualified calls resolve.
ALIASES = (
    "si",
    "dc",
    "dk",
    "schema_index",
    "direct_contract",
    "direct_constraints",
    "direct_optimizer",
    "direct_compiler",
)

BANNED_SUBSTRINGS = (
    "serial_compile",
    "classical_compile",
    "repertoire_program",
    "_Manager",
    "index_query",
    "compilers",
)


def _is_internal_import(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(alias.name.split(".")[0] in INTERNAL for alias in node.names)
    if isinstance(node, ast.ImportFrom):
        if node.module is None:
            return False
        return node.module.split(".")[0] in INTERNAL
    return False


def _split_module(path: Path) -> Tuple[List[str], List[str]]:
    """Return the module's external imports and its definitions."""

    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)

    # Internal imports can be nested inside a function, as the optimiser is
    # imported inside compile_with_report to avoid a module cycle. In the
    # assembled file there is no second module to import, so those lines are
    # replaced wherever they occur. Replacing lines rather than regenerating
    # the source keeps every comment and blank line intact.
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and _is_internal_import(node):
            indent = " " * (node.col_offset)
            for number in range(node.lineno, node.end_lineno + 1):
                lines[number - 1] = (
                    f"{indent}# (export) the module is bound to this file at the top.\n"
                )

    imports: List[str] = []
    body: List[str] = []
    for node in tree.body:
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
        chunk = "".join(lines[start : node.end_lineno])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            if _is_internal_import(node):
                continue
            imports.append(chunk.strip())
            continue
        if isinstance(node, ast.Assign):
            targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
            if "__all__" in targets:
                continue
        if isinstance(node, ast.If):
            # Drop each module's own command line entry point.
            test = node.test
            if (
                isinstance(test, ast.Compare)
                and isinstance(test.left, ast.Name)
                and test.left.id == "__name__"
            ):
                continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
            if node is tree.body[0]:
                continue  # the module docstring
        body.append(chunk)
    return imports, body


def assemble() -> str:
    imports: List[str] = []
    bodies: List[str] = []
    digests: List[str] = []

    for name in ALLOWLIST:
        path = ROOT / name
        digests.append(
            f"# {name}: SHA256 {hashlib.sha256(path.read_bytes()).hexdigest()}"
        )
        module_imports, module_body = _split_module(path)
        for statement in module_imports:
            if statement not in imports:
                imports.append(statement)
        bodies.append(f"# ---- {name} " + "-" * (62 - len(name)))
        bodies.extend(module_body)

    header = [
        '"""Standalone direct-index compiler for the Luminal machine.',
        "",
        "Assembled from the sources listed below. Do not edit this copy; edit the",
        "sources and export again. Standard library only, beside the supplied",
        "machine module.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ]
    header += sorted(imports)
    header += [
        "",
        "import sys as _sys",
        "",
        "# Each module name is bound to this assembled module, so a qualified call",
        "# such as dc.footprint(...) stays an attribute lookup and cannot be",
        "# shadowed by a local variable of the same name.",
        "_self = _sys.modules[__name__]",
    ]
    header += [f"{alias} = _self" for alias in ALIASES]
    header += ["", "# Source provenance:"] + digests + [""]

    footer = [
        "",
        "",
        'if __name__ == "__main__":',
        "    raise SystemExit(main(_sys.argv[1:]))",
        "",
    ]

    result = "\n".join(header) + "\n" + "\n".join(bodies) + "\n".join(footer)
    # A syntax error here is an exporter defect, not something to emit.
    ast.parse(result)
    return result


def audit(source: str) -> List[str]:
    """Refuse an export that carries a prohibited dependency."""

    problems = []
    for banned in BANNED_SUBSTRINGS:
        if banned in source:
            problems.append(f"the export mentions {banned!r}")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in ("exec", "eval", "compile"):
                problems.append(f"the export calls {node.func.id}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = (
                [alias.name for alias in node.names]
                if isinstance(node, ast.Import)
                else [node.module or ""]
            )
            for name in names:
                root = name.split(".")[0]
                if root in INTERNAL or root in ("common", "compilers", "index_query"):
                    problems.append(f"the export imports {name}")
    return problems


def export(output: Path) -> Path:
    source = assemble()
    problems = audit(source)
    if problems:
        raise RuntimeError("; ".join(problems))
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    return output


def main(argv) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output",
        default=str(ROOT / ".build" / "direct_index" / "compiler.py"),
        help="where to write the assembled compiler",
    )
    arguments = parser.parse_args(argv)
    try:
        path = export(Path(arguments.output))
    except (SyntaxError, RuntimeError) as exc:
        print(f"EXPORT FAILED: {exc}", file=sys.stderr)
        return 1
    print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
