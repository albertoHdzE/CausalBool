"""Build the emailed ``compiler.py`` from the accepted C1 export.

The accepted export (``EXPORT`` below) embeds thirteen modules as strings and
executes them at start-up. That is faithful but reads as obfuscation, so this
builder flattens the same bytes into one plain module:

* the embedded sources are taken from the accepted export itself and checked
  against their recorded SHA256, so nothing is re-read from the working tree;
* only top-level definitions reachable from ``compile_program`` are kept;
* qualified references (``dc.derive``) become bare names, and a name defined
  in two modules is prefixed with a neutral tag, the last module keeping the
  bare name; a rename that a local binding would capture is refused;
* docstrings keep their first line when it is free of project vocabulary,
  and comments are dropped (``ast.unparse``).

The result is only accepted by ``check_parity.py``, which compares its output
with the accepted export under a deterministic clock. Nothing here is emailed.
"""

from __future__ import annotations

import ast
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Set, Tuple

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
EXPORT = ROOT / "results/phase2_structural_encoding/third_round_20260925_resume/exports/C1/compiler.py"
MANIFEST = EXPORT.with_name("compiler_MANIFEST.json")
OUTPUT = HERE / "compiler.py"

TAGS = {
    "schema_index": "idx", "direct_contract": "contract", "direct_constraints": "cover",
    "direct_optimizer": "local", "direct_compiler": "build",
    "research.optimization_common": "common", "research.objective_index_common": "limits",
    "research.structural_encoding": "enc", "research.structural_search": "search",
    "research.run_structural_experiments": "exp", "research.efficiency_search": "base",
    "research.third_round_kernel": "kernel", "research.third_round_candidate": "",
}

# The call sequence of the accepted loader's compile_program (EXPORT_LEARNED is None).
ROOTS = [
    ("direct_contract", "derive"), ("direct_contract", "compilation"),
    ("direct_compiler", "compile_with_report"), ("direct_compiler", "DEFAULT_LIMITS"),
    ("research.structural_encoding", "issue_cycles_of"),
    ("research.third_round_candidate", "multiscale_optimise"),
]

BANNED = re.compile(
    r"\b(R\d|C\d|A\d|BS\d|L\d\d|rounds?|frozen|protocol|plan|task|stage|arms?|research|audit|"
    r"codex|claude|paper|deconvol\w*|sumando\w*|phase|wave|owners?|ablation|successor|learn\w*|"
    r"export\w*|candidate|release|baseline|pinned|manifest|section|economics|diagnostic)\b|§|``",
    re.IGNORECASE)

# Labels carried in the search's run record; none of them reaches the schedule.
RELABEL = {
    "third_round_candidate C1": "1.0",
    "efficiency_search.multiscale_optimise": "multiscale_optimise",
    "A4_multiscale_search": "multiscale_search",
    "a3_product_window": "product_window",
    "frozen_source_sha256": "source_sha256",
    "8cda157f465b1d23bb3894d8b3226437210d537f03cffd6ed8db523b12c4c7f5": "",
}

HEADER = '''"""Instruction scheduling and scratch allocation for the Luminal machine.

Usage:  python3 compiler.py <program.json>   (schedule JSON on stdout only)

1. Facts.        Dependencies, engine capacities, value sizes and lifetimes
                 are derived from the program and the machine contract.
2. Construction. Operations are placed in source order. Each operation is
                 issued at the earliest cycle that its operands and engine
                 capacity allow, and each result takes the lowest aligned
                 address that is free for its whole lifetime.
3. Improvement.  A bounded search re-times small windows of operations,
                 re-assigns their addresses and lanes, and accepts a change
                 only when it is independently validated and strictly lowers
                 cycles x scratch footprint. It stops after 0.1 s and keeps
                 the best validated schedule found.

Standard library only, beside the supplied machine module.
"""
'''

TAIL = '''

def compile_program(program: dict) -> dict:
    facts = derive(program)
    initial, _ = compile_with_report(program, DEFAULT_LIMITS, optimise=False)
    times = issue_cycles_of(program, initial["bundles"])
    addresses = dict(initial["scratch"])
    best_times, best_addresses, record = multiscale_optimise(
        program, facts, times, addresses,
        budget_seconds=OPTIMISATION_SECONDS, catalog="a4", traversal="dfs")
    if record["discrepancy_count"]:
        print(f"warning: {record['discrepancy_count']} rejected candidates", file=sys.stderr)
    return compilation(facts, best_times, best_addresses)


def main(argv) -> int:
    if len(argv) != 1:
        print("usage: python3 compiler.py <program.json>", file=sys.stderr)
        return 2
    try:
        program = machine.load_program(argv[0])
        compiled = compile_program(program)
    except Exception as exc:
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    json.dump(compiled, sys.stdout)
    sys.stdout.write("\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


class BuildError(RuntimeError):
    pass


def load_bundle() -> List[Tuple[str, str]]:
    manifest = json.loads(MANIFEST.read_text())
    if hashlib.sha256(EXPORT.read_bytes()).hexdigest() != manifest["export_sha256"]:
        raise BuildError("accepted export does not match its manifest")
    tree = ast.parse(EXPORT.read_text(encoding="utf-8"))
    bundle = next(ast.literal_eval(n.value) for n in tree.body
                  if isinstance(n, ast.Assign) and getattr(n.targets[0], "id", "") == "_BUNDLE")
    seconds = next(ast.literal_eval(n.value) for n in tree.body
                   if isinstance(n, ast.Assign)
                   and getattr(n.targets[0], "id", "") == "EXPORT_OPTIMISATION_SECONDS")
    out = []
    for name, digest, source in bundle:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise BuildError(f"{name}: embedded bytes do not match their hash")
        out.append((name, source))
    if [n for n, _ in out] != list(TAGS):
        raise BuildError(f"unexpected module list {[n for n, _ in out]}")
    return out, seconds


def bundled_target(node: ast.stmt, alias: ast.alias, modules: Set[str]):
    """Module named by an import alias, or None when it is not bundled."""

    if isinstance(node, ast.Import):
        return alias.name if alias.name in modules else None
    full = f"{node.module}.{alias.name}" if node.module else alias.name
    if full in modules:
        return full
    if node.module in modules:
        raise BuildError(f"from-import of a name from bundled module {node.module}")
    return None


class Module:
    def __init__(self, name: str, source: str, modules: Set[str]):
        self.name = name
        self.tree = ast.parse(source)
        self.aliases: Dict[str, str] = {}
        self.external: List[ast.stmt] = []
        self.symbols: Dict[str, List[ast.stmt]] = {}
        self.order: List[ast.stmt] = []
        for node in ast.walk(self.tree):
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    target = bundled_target(node, alias, modules)
                    if target is None:
                        continue
                    local = alias.asname or alias.name.split(".")[0]
                    if self.aliases.get(local, target) != target:
                        raise BuildError(f"{name}: alias {local} names two modules")
                    self.aliases[local] = target
        for stmt in self.tree.body:
            if isinstance(stmt, (ast.Import, ast.ImportFrom)):
                if not any(bundled_target(stmt, a, modules) for a in stmt.names):
                    if not (isinstance(stmt, ast.ImportFrom) and stmt.module == "__future__"):
                        self.external.append(stmt)
                continue
            names = defined_names(stmt)
            if not names:
                continue
            self.order.append(stmt)
            for n in names:
                self.symbols.setdefault(n, []).append(stmt)


def defined_names(stmt: ast.stmt) -> List[str]:
    if isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
        return [stmt.name]
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        return [n.id for t in targets for n in ast.walk(t) if isinstance(n, ast.Name)]
    return []


def references(mod: Module, stmt: ast.stmt) -> Set[Tuple[str, str]]:
    """Over-approximate the symbols a statement may reach."""

    found = set()
    for node in ast.walk(stmt):
        if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
                and node.value.id in mod.aliases:
            found.add((mod.aliases[node.value.id], node.attr))
        elif isinstance(node, ast.Name) and node.id in mod.symbols:
            found.add((mod.name, node.id))
    return found


def reachable(mods: Dict[str, Module]) -> Set[Tuple[str, str]]:
    keep, todo = set(), list(ROOTS)
    while todo:
        key = todo.pop()
        if key in keep:
            continue
        mod = mods[key[0]]
        if key[1] not in mod.symbols:
            raise BuildError(f"unresolved reference {key[0]}.{key[1]}")
        keep.add(key)
        for stmt in mod.symbols[key[1]]:
            todo.extend(references(mod, stmt))
    return keep


def scope_bindings(node) -> Set[str]:
    """Names bound in a function, lambda or comprehension scope, minus globals."""

    bound, declared_global = set(), set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for arg in a.posonlyargs + a.args + a.kwonlyargs + [a.vararg, a.kwarg]:
            if arg is not None:
                bound.add(arg.arg)
        body = node.body if isinstance(node.body, list) else [node.body]
    else:  # comprehension
        body = []
        for gen in node.generators:
            bound |= {n.id for n in ast.walk(gen.target) if isinstance(n, ast.Name)}
        return bound

    def visit(n):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            bound.add(n.name)
            for d in n.decorator_list:
                visit(d)
            return
        if isinstance(n, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)):
            return
        if isinstance(n, ast.Global):
            declared_global.update(n.names)
        elif isinstance(n, ast.Nonlocal):
            bound.update(n.names)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            bound.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for alias in n.names:
                bound.add(alias.asname or alias.name.split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            bound.add(n.name)
        elif isinstance(n, ast.NamedExpr):
            bound.add(n.target.id)
        for child in ast.iter_child_nodes(n):
            visit(child)

    for stmt in body:
        visit(stmt)
    return bound - declared_global


SCOPES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
          ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


class Rewriter(ast.NodeTransformer):
    """Unqualify bundled references and apply the rename map, scope-aware."""

    def __init__(self, mod: Module, final: Dict[Tuple[str, str], str], mods: Set[str]):
        self.mod, self.final, self.modules = mod, final, mods
        self.stack: List[Set[str]] = []
        self.depth = 0
        self.conflicts: Set[Tuple[str, str]] = set()

    def local(self, name: str) -> bool:
        return any(name in s for s in self.stack)

    def resolve(self, key: Tuple[str, str], node: ast.AST) -> ast.Name:
        if key not in self.final:
            raise BuildError(f"{self.mod.name}: reference to unkept {key}")
        new = self.final[key]
        if self.local(new):
            self.conflicts.add(key)
        return ast.copy_location(ast.Name(id=new, ctx=node.ctx), node)

    def visit_Attribute(self, node):
        if isinstance(node.value, ast.Name) and node.value.id in self.mod.aliases \
                and not self.local(node.value.id):
            return self.resolve((self.mod.aliases[node.value.id], node.attr), node)
        return self.generic_visit(node)

    def visit_Name(self, node):
        if node.id in self.mod.aliases and not self.local(node.id):
            raise BuildError(f"{self.mod.name}: module alias {node.id} used as a value")
        if node.id in self.mod.symbols and not self.local(node.id):
            return self.resolve((self.mod.name, node.id), node)
        return node

    def visit_Global(self, node):
        node.names = [self.final.get((self.mod.name, n), n) for n in node.names]
        return node

    def _drop_bundled_imports(self, node):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            keep = [a for a in node.names if bundled_target(node, a, self.modules) is None]
            if not keep:
                return ast.copy_location(ast.Pass(), node)
            node.names = keep
        return node

    def visit_Import(self, node):
        return self._drop_bundled_imports(node)

    visit_ImportFrom = visit_Import

    def _rename_definition(self, node):
        if self.depth == 0:
            node.name = self.final[(self.mod.name, node.name)]

    def _scoped(self, node):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            self._rename_definition(node)
            node.decorator_list = [self.visit(d) for d in node.decorator_list]
            node.args.defaults = [self.visit(d) for d in node.args.defaults]
            node.args.kw_defaults = [self.visit(d) if d else d for d in node.args.kw_defaults]
            if node.returns:
                node.returns = self.visit(node.returns)
            for a in node.args.posonlyargs + node.args.args + node.args.kwonlyargs \
                    + [node.args.vararg, node.args.kwarg]:
                if a is not None and a.annotation is not None:
                    a.annotation = self.visit(a.annotation)
            self.stack.append(scope_bindings(node))
            self.depth += 1
            node.body = [x for s in node.body for x in _as_list(self.visit(s))]
            self.depth -= 1
            self.stack.pop()
            return node
        if isinstance(node, ast.Lambda):
            node.args.defaults = [self.visit(d) for d in node.args.defaults]
            self.stack.append(scope_bindings(node))
            node.body = self.visit(node.body)
            self.stack.pop()
            return node
        # comprehension: the first iterable is evaluated in the enclosing scope
        gens = node.generators
        gens[0].iter = self.visit(gens[0].iter)
        self.stack.append(scope_bindings(node))
        for i, g in enumerate(gens):
            g.target = self.visit(g.target)
            if i:
                g.iter = self.visit(g.iter)
            g.ifs = [self.visit(c) for c in g.ifs]
        for field in ("elt", "key", "value"):
            if hasattr(node, field):
                setattr(node, field, self.visit(getattr(node, field)))
        self.stack.pop()
        return node

    visit_FunctionDef = visit_AsyncFunctionDef = visit_Lambda = _scoped
    visit_ListComp = visit_SetComp = visit_DictComp = visit_GeneratorExp = _scoped

    def visit_ClassDef(self, node):
        self._rename_definition(node)
        node.bases = [self.visit(b) for b in node.bases]
        node.keywords = [self.visit(k) for k in node.keywords]
        node.decorator_list = [self.visit(d) for d in node.decorator_list]
        # Class-body names are local to the class body only; methods skip them.
        bound = {n.id for s in node.body for n in ast.walk(s)
                 if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store)
                 and not isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef))}
        bound |= {s.name for s in node.body
                  if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))}
        body = []
        self.depth += 1
        for s in node.body:
            if isinstance(s, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                body.extend(_as_list(self.visit(s)))
            else:
                self.stack.append(bound)
                body.extend(_as_list(self.visit(s)))
                self.stack.pop()
        self.depth -= 1
        node.body = body
        return node


def _as_list(x):
    return x if isinstance(x, list) else [x]


def trim_docstrings(tree: ast.AST) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            continue
        body = node.body
        if body and isinstance(body[0], ast.Expr) and isinstance(body[0].value, ast.Constant) \
                and isinstance(body[0].value.value, str):
            first = body[0].value.value.strip().split("\n\n")[0].replace("\n", " ")
            first = " ".join(first.split())
            if first and not BANNED.search(first) and len(first) <= 100:
                body[0].value.value = first
            else:
                body.pop(0)
                if not body:
                    body.append(ast.Pass())


def build() -> str:
    bundle, seconds = load_bundle()
    names = {n for n, _ in bundle}
    mods = {n: Module(n, s, names) for n, s in bundle}
    keep = reachable(mods)

    # Final names: the last module defining a colliding name keeps it bare.
    final: Dict[Tuple[str, str], str] = {}
    by_name: Dict[str, List[str]] = {}
    for mod, name in keep:
        by_name.setdefault(name, []).append(mod)
    order = list(TAGS)
    forced: Set[Tuple[str, str]] = set()
    reserved = {"compile_program", "main", "OPTIMISATION_SECONDS", "machine", "json", "sys"}

    for _ in range(10):
        final.clear()
        for name, owners in by_name.items():
            owners.sort(key=order.index)
            for i, mod in enumerate(owners):
                bare = i == len(owners) - 1 and (mod, name) not in forced \
                    and not (name in reserved and TAGS[mod] != "")
                tag = TAGS[mod] or "c"
                final[(mod, name)] = name if bare else f"_{tag}_{name.lstrip('_')}"
        if len(set(final.values())) != len(final):
            raise BuildError("rename map is not injective")
        bodies: List[Tuple[str, List[ast.stmt]]] = []
        conflicts: Set[Tuple[str, str]] = set()
        external: Dict[str, str] = {}
        for mod_name in order:
            mod = mods[mod_name]
            kept = [s for s in mod.order if any((mod_name, n) in keep for n in defined_names(s))]
            if not kept:
                continue
            # Parse afresh so repeated passes start from the embedded bytes.
            fresh = Module(mod_name, dict(bundle)[mod_name], names)
            fresh_kept = [fresh.order[mod.order.index(s)] for s in kept]
            rw = Rewriter(fresh, final, names)
            out = [x for s in fresh_kept for x in _as_list(rw.visit(s))]
            conflicts |= rw.conflicts
            bodies.append((mod_name, out))
            for stmt in fresh.external:
                for alias in stmt.names:
                    bound = alias.asname or alias.name.split(".")[0]
                    text = ast.unparse(ast.ImportFrom(module=stmt.module, names=[alias], level=0)
                                       if isinstance(stmt, ast.ImportFrom)
                                       else ast.Import(names=[alias]))
                    if external.setdefault(bound, text) != text:
                        raise BuildError(f"import name {bound} bound two ways")
        if not conflicts:
            break
        forced |= conflicts
    else:
        raise BuildError("rename conflicts did not settle")

    globals_emitted = set(final.values())
    clash = globals_emitted & set(external)
    if clash:
        raise BuildError(f"definitions shadow imports: {sorted(clash)}")

    code_parts = []
    for mod_name, stmts in bodies:
        section = ast.Module(body=stmts, type_ignores=[])
        trim_docstrings(section)
        for node in ast.walk(section):
            if isinstance(node, ast.Constant) and node.value in RELABEL:
                node.value = RELABEL[node.value]
        ast.fix_missing_locations(section)
        code_parts.append(ast.unparse(section))
    code = "\n\n\n".join(code_parts)

    used = {n.id for n in ast.walk(ast.parse(code + TAIL)) if isinstance(n, ast.Name)}
    used |= {"machine", "json", "sys"}
    imports = sorted({text for bound, text in external.items() if bound in used},
                     key=lambda t: (not t.startswith("import "), t))

    source = (HEADER + "\nfrom __future__ import annotations\n\n" + "\n".join(imports)
              + f"\n\nOPTIMISATION_SECONDS = {seconds!r}\n\n\n" + code + "\n" + TAIL)
    ast.parse(source, feature_version=(3, 10))
    leaks = sorted({m.group(0) for m in BANNED.finditer(
        "\n".join(ast.get_docstring(n) or "" for n in ast.walk(ast.parse(source))
                  if isinstance(n, (ast.FunctionDef, ast.ClassDef))))})
    if leaks:
        raise BuildError(f"project vocabulary left in docstrings: {leaks}")
    return source


def main() -> int:
    source = build()
    OUTPUT.write_text(source, encoding="utf-8")
    print(f"wrote {OUTPUT.relative_to(ROOT)}: {len(source.splitlines())} lines, "
          f"sha256 {hashlib.sha256(source.encode()).hexdigest()[:16]}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
