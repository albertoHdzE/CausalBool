"""Deterministic standalone export of the frozen selected compiler (Stage E).

Assembles ONE file, ``compiler.py``, from the measured sources: the production
bootstrap modules, the research codec/search/model owners, the three functions
the NEW controller reaches in ``run_structural_experiments`` and the NEW
controller itself. The frozen configuration is written as constants; the
optimisation allowance is 0.1 seconds. Standard library plus the pinned
``machine`` only. No classical or serial path exists in the file and the audit
refuses one.

This follows ``export_direct.py`` (production exporter, which may not be edited
and whose splitter is hard-wired to its own allowlist): every module name is
bound to the assembled module so qualified calls stay attribute lookups. Two
top-level names collide across the bundle and are resolved explicitly:

- ``_plain_int`` exists in ``schema_index`` and ``structural_encoding`` with the
  same body (``isinstance(value, int) and not isinstance(value, bool)``); the
  second definition is omitted;
- ``optimise`` exists in ``direct_optimizer`` and ``optimization_search``; the
  latter is emitted as ``optimization_search_optimise``. Nothing in the bundle
  refers to it by its bare name.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_export --config CONFIG \
        --build BUILD [--model-depth D] --output PATH
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
from pathlib import Path
import sys
from typing import List, Optional, Tuple

ROOT = Path(__file__).resolve().parents[1]

MODULES = (
    ("schema_index.py", "si", ("schema_index",)),
    ("direct_contract.py", "dc", ("direct_contract",)),
    ("direct_constraints.py", "dk", ("direct_constraints",)),
    ("direct_optimizer.py", "dopt", ("direct_optimizer",)),
    ("direct_compiler.py", "dcomp", ("direct_compiler",)),
    ("research/structural_encoding.py", "se", ()),
    ("research/structural_search.py", "ss", ()),
    ("research/structural_models.py", "sm", ()),
    ("research/run_structural_experiments.py", "rse", ()),
    ("research/optimization_search.py", "osr", ()),
)
RSE_SLICE = ("physical_address_domain", "matched_window_record", "_elite_threshold")
INTERNAL_ROOTS = {"schema_index", "direct_contract", "direct_constraints", "direct_optimizer",
                  "direct_compiler", "research"}
BANNED = ("serial_compile", "classical_compile", "repertoire_program", "_Manager",
          "index_query", "compilers", "common.", "import common")


def _internal(node: ast.stmt) -> bool:
    if isinstance(node, ast.Import):
        return any(a.name.split(".")[0] in INTERNAL_ROOTS for a in node.names)
    if isinstance(node, ast.ImportFrom):
        return node.module is not None and node.module.split(".")[0] in INTERNAL_ROOTS
    return False


def _split(path: Path, only: Optional[Tuple[str, ...]] = None,
           omit: Tuple[str, ...] = (), rename: Optional[dict] = None) -> Tuple[List[str], List[str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)) and _internal(node) and \
                node not in tree.body:
            indent = " " * node.col_offset
            for number in range(node.lineno, node.end_lineno + 1):
                lines[number - 1] = f"{indent}pass  # (export) module bound at the top.\n"
    imports: List[str] = []
    body: List[str] = []
    for node in tree.body:
        start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])]) - 1
        chunk = "".join(lines[start:node.end_lineno])
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom) and node.module == "__future__":
                continue
            if _internal(node):
                continue
            if only is None:
                imports.append(chunk.strip())
            continue
        name = getattr(node, "name", None)
        if only is not None:
            if name in only:
                body.append(chunk)
            continue
        if isinstance(node, ast.Assign) and any(
                isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            continue
        if isinstance(node, ast.If) and isinstance(node.test, ast.Compare) and \
                isinstance(node.test.left, ast.Name) and node.test.left.id == "__name__":
            continue
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant) and \
                node is tree.body[0]:
            continue
        if name in omit:
            continue
        if rename and name in rename:
            chunk = chunk.replace(f"def {name}(", f"def {rename[name]}(", 1)
        body.append(chunk)
    return imports, body


def assemble(config: str, build: str, model_depth: Optional[int]) -> Tuple[str, dict]:
    imports: List[str] = ["import json", "import sys", "import time", "import math"]
    bodies: List[str] = []
    components = {}
    aliases: List[str] = []
    for relative, alias, extra in MODULES:
        path = ROOT / relative
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        components[relative] = digest
        if relative.endswith("run_structural_experiments.py"):
            module_imports, module_body = _split(path, only=RSE_SLICE)
            found = [n for n in RSE_SLICE if any(f"def {n}(" in c for c in module_body)]
            if found != list(RSE_SLICE):
                raise RuntimeError(f"export slice incomplete: {found}")
        elif relative.endswith("structural_encoding.py"):
            module_imports, module_body = _split(path, omit=("_plain_int",))
        elif relative == "direct_compiler.py":
            # Its own entry points are replaced by the export's below.
            module_imports, module_body = _split(path, omit=("main", "compile_program"))
        elif relative.endswith("optimization_search.py"):
            module_imports, module_body = _split(
                path, rename={"optimise": "optimization_search_optimise"})
        else:
            module_imports, module_body = _split(path)
        for statement in module_imports:
            if statement not in imports:
                imports.append(statement)
        bodies.append(f"# ---- {relative} (SHA256 {digest}) " + "-" * 8)
        bodies.extend(module_body)
        aliases.extend([alias, *extra])
    aliases = sorted(set(aliases))
    header = [
        '"""Standalone Phase 2 optimization compiler (frozen selected configuration).',
        "",
        "Generated by research/optimization_export.py from measured sources. Do not edit;",
        "regenerate. Standard library plus the supplied machine module only.",
        '"""',
        "",
        "from __future__ import annotations",
        "",
    ] + sorted(imports) + [
        "",
        "_self = sys.modules[__name__]",
    ] + [f"{alias} = _self" for alias in aliases] + [
        "",
        f"EXPORT_CONFIG = {config!r}",
        f"EXPORT_BUILD = {build!r}",
        f"EXPORT_MODEL_DEPTH = {model_depth!r}",
        "EXPORT_OPTIMISATION_SECONDS = 0.1",
        "",
    ]
    footer = '''

def compile_program(program: dict) -> dict:
    """Direct bootstrap, then the frozen NEW structural controller for 0.1 s."""

    facts = direct_contract.derive(program)
    bootstrap_compiled, _ = direct_compiler.compile_with_report(
        program, direct_compiler.DEFAULT_LIMITS, optimise=False)
    times = structural_encoding_issue_cycles(program, bootstrap_compiled)
    addresses = dict(bootstrap_compiled["scratch"])
    best_times, best_addresses, record = optimization_search_optimise(
        program, facts, times, addresses, config=EXPORT_CONFIG,
        budget_seconds=EXPORT_OPTIMISATION_SECONDS, build=EXPORT_BUILD,
        model_depth=EXPORT_MODEL_DEPTH)
    if record["discrepancy_count"]:
        print(f"warning: {record['discrepancy_count']} rejected candidates", file=sys.stderr)
    return direct_contract.compilation(facts, best_times, best_addresses)


def structural_encoding_issue_cycles(program: dict, compiled: dict) -> dict:
    return issue_cycles_of(program, compiled["bundles"])


def main(argv) -> int:
    """Emit only schedule JSON on stdout; diagnostics go to stderr."""

    if len(argv) != 1:
        print("usage: python3 compiler.py <program.json>", file=sys.stderr)
        return 2
    try:
        program = machine.load_program(argv[0])
        compiled = compile_program(program)
    except (OSError, json.JSONDecodeError, machine.ProgramError, machine.CompileError,
            direct_contract.ContractError, direct_compiler.CompilationFailure,
            DomainError) as exc:
        print(f"FAILED: {exc}", file=sys.stderr)
        return 1
    json.dump(compiled, sys.stdout)
    sys.stdout.write("\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''
    source = "\n".join(header) + "\n" + "\n".join(bodies) + footer
    ast.parse(source)
    manifest = {"config": config, "build": build, "model_depth": model_depth,
                "optimisation_seconds": 0.1, "components_sha256": components,
                "collisions_resolved": {"_plain_int": "second identical definition omitted",
                                        "optimise": "optimization_search -> "
                                                    "optimization_search_optimise"},
                "generator_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}
    return source, manifest


def audit(source: str) -> List[str]:
    problems = [f"mentions {b!r}" for b in BANNED if b in source]
    tree = ast.parse(source)
    defined = {}
    for node in tree.body:
        name = getattr(node, "name", None)
        if name:
            defined[name] = defined.get(name, 0) + 1
    problems += [f"top-level {n!r} defined {c} times" for n, c in defined.items() if c > 1]
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and \
                node.func.id in ("exec", "eval", "compile"):
            problems.append(f"calls {node.func.id}")
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                     else [node.module or ""])
            for name in names:
                root = name.split(".")[0]
                if root in INTERNAL_ROOTS or root in ("common", "compilers", "index_query"):
                    problems.append(f"imports {name}")
                if root not in sys.stdlib_module_names and root != "machine" and root:
                    problems.append(f"imports non-stdlib {name}")
    return problems


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--build", required=True)
    parser.add_argument("--model-depth", type=int, default=None)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    source, manifest = assemble(args.config, args.build, args.model_depth)
    problems = audit(source)
    manifest["audit_problems"] = problems
    output = Path(args.output)
    if output.exists():
        print(f"refusing to overwrite {output}", file=sys.stderr)
        return 1
    output.parent.mkdir(parents=True, exist_ok=True)
    if problems:
        print("EXPORT FAILED: " + "; ".join(problems), file=sys.stderr)
        return 1
    output.write_text(source, encoding="utf-8")
    manifest["export_sha256"] = hashlib.sha256(source.encode("utf-8")).hexdigest()
    (output.parent / (output.stem + "_MANIFEST.json")).write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"output": str(output), "sha256": manifest["export_sha256"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
