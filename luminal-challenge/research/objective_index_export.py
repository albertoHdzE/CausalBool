"""Standalone export of the frozen selected solver, and its isolated validation.

``assemble`` writes ONE ``compiler.py``: the exact bytes of every measured
module the selected solver imports, embedded as string literals with their
SHA256, installed at start-up as separate module objects (so no top-level name
of one module can shadow another's), each hash re-verified before it runs.
``run_structural_experiments`` is the one exception: the solver needs only
``physical_address_domain`` and ``matched_window_record``, and the whole file
imports the production comparison harness. Those two functions are embedded as
an exact source slice with per-function hashes. Standard library plus the
pinned ``machine`` only; the AST audit refuses any classical/serial reference
and any non-standard import.

``validate`` builds the export in the result directory (never production),
checks deterministic regeneration and component hashes against the freeze,
runs the unchanged pinned public tests and ``score.py`` in a temporary
workspace with import-path assertions, then measures 3 repetitions on every
public and fresh program (624 rows) with the 20 s process limit.

Usage::

    PYTHONPATH=.reference:. python -m research.objective_index_export --run DIR --label nonmodel
"""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import math
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time
from typing import Dict, List, Optional, Tuple

import machine

from research import optimization_common as oc
from research import optimization_export_validation as oev


ROOT = oc.ROOT
WHOLE = (
    ("schema_index", "schema_index.py"),
    ("direct_contract", "direct_contract.py"),
    ("direct_constraints", "direct_constraints.py"),
    ("direct_optimizer", "direct_optimizer.py"),
    ("direct_compiler", "direct_compiler.py"),
    ("research.optimization_common", "research/optimization_common.py"),
    ("research.objective_index_common", "research/objective_index_common.py"),
    ("research.structural_encoding", "research/structural_encoding.py"),
    ("research.structural_search", "research/structural_search.py"),
)
RSE_SLICE = ("physical_address_domain", "matched_window_record")
RSE_HEADER = ("from __future__ import annotations\n"
              "from typing import Dict, List, Sequence\n"
              "import machine\n"
              "import direct_constraints as dk\n"
              "import direct_contract as dc\n")
OM_SLICE = ("elite_threshold",)
OM_HEADER = ("from __future__ import annotations\n"
             "import math\n"
             "from typing import Sequence\n")
SOLVER = (("research.objective_index_search", "research/objective_index_search.py"),)
LEARNED = (("research.schema_ranker", "research/schema_ranker.py"),
           ("research.objective_index_learned", "research/objective_index_learned.py"))
BANNED_CALLS = {"serial_compile", "classical_compile", "repertoire_program"}
BANNED_IMPORTS = {"common", "compilers", "index_query", "compare_direct", "verify_direct"}
OPTIMISATION_SECONDS = 0.1


def _slice(path: Path, names: Tuple[str, ...], header: str) -> Tuple[str, Dict[str, str]]:
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines(keepends=True)
    tree = ast.parse(text)
    chunks, hashes = [], {}
    for node in tree.body:
        if getattr(node, "name", None) in names:
            start = min([node.lineno] + [d.lineno for d in getattr(node, "decorator_list", [])])
            chunk = "".join(lines[start - 1:node.end_lineno])
            chunks.append(chunk)
            hashes[node.name] = hashlib.sha256(chunk.encode("utf-8")).hexdigest()
    if sorted(hashes) != sorted(names):
        raise RuntimeError(f"slice of {path.name} incomplete: {sorted(hashes)}")
    return header + "\n\n" + "\n\n".join(chunks), hashes


def bundle(learned: Optional[str]) -> List[dict]:
    items: List[dict] = []
    for name, relative in WHOLE:
        text = (ROOT / relative).read_text(encoding="utf-8")
        items.append({"module": name, "kind": "whole", "file": relative, "source": text,
                      "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "file_sha256": oc.file_sha256(ROOT / relative)})
    source, hashes = _slice(ROOT / "research/run_structural_experiments.py", RSE_SLICE,
                            RSE_HEADER)
    items.append({"module": "research.run_structural_experiments", "kind": "slice",
                  "file": "research/run_structural_experiments.py", "source": source,
                  "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                  "file_sha256": oc.file_sha256(ROOT / "research/run_structural_experiments.py"),
                  "function_sha256": hashes})
    extra = SOLVER
    if learned:
        source, hashes = _slice(ROOT / "research/optimization_models.py", OM_SLICE, OM_HEADER)
        items.append({"module": "research.optimization_models", "kind": "slice",
                      "file": "research/optimization_models.py", "source": source,
                      "sha256": hashlib.sha256(source.encode("utf-8")).hexdigest(),
                      "file_sha256": oc.file_sha256(ROOT / "research/optimization_models.py"),
                      "function_sha256": hashes})
        extra = SOLVER + LEARNED
    for name, relative in extra:
        text = (ROOT / relative).read_text(encoding="utf-8")
        items.append({"module": name, "kind": "whole", "file": relative, "source": text,
                      "sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                      "file_sha256": oc.file_sha256(ROOT / relative)})
    return items


LOADER = '''
def _install():
    """Install every embedded module from its verified bytes, in order."""

    package = types.ModuleType("research")
    package.__path__ = []
    package.__file__ = "<export:research>"
    sys.modules["research"] = package
    for name, digest, source in _BUNDLE:
        if hashlib.sha256(source.encode("utf-8")).hexdigest() != digest:
            raise RuntimeError(f"embedded module {name} does not match its recorded hash")
        module = types.ModuleType(name)
        module.__file__ = f"<export:{name}>"
        sys.modules[name] = module
        exec(compile(source, f"<export:{name}>", "exec"), module.__dict__)
        if name.startswith("research."):
            setattr(package, name.split(".", 1)[1], module)


_install()

import direct_contract  # noqa: E402  (the embedded module)
import direct_compiler  # noqa: E402
import research.objective_index_search as _ois  # noqa: E402
import research.structural_encoding as _se  # noqa: E402


def compile_program(program: dict) -> dict:
    """Direct bootstrap, then the frozen selected solver for 0.1 s."""

    facts = direct_contract.derive(program)
    bootstrap, _ = direct_compiler.compile_with_report(program, direct_compiler.DEFAULT_LIMITS,
                                                       optimise=False)
    times = _se.issue_cycles_of(program, bootstrap["bundles"])
    addresses = dict(bootstrap["scratch"])
    if EXPORT_LEARNED:
        import research.objective_index_learned as _oil

        best_times, best_addresses, record = _oil.optimise(
            program, facts, times, addresses, arm=EXPORT_ARM,
            budget_seconds=EXPORT_OPTIMISATION_SECONDS, labels_mode=EXPORT_LEARNED)
    else:
        best_times, best_addresses, record = _ois.optimise(
            program, facts, times, addresses, arm=EXPORT_ARM,
            budget_seconds=EXPORT_OPTIMISATION_SECONDS)
    if record["discrepancy_count"]:
        print(f"warning: {record['discrepancy_count']} rejected candidates", file=sys.stderr)
    return direct_contract.compilation(facts, best_times, best_addresses)


def main(argv) -> int:
    """Emit only schedule JSON on stdout; diagnostics go to stderr."""

    if len(argv) != 1:
        print("usage: python3 compiler.py <program.json>", file=sys.stderr)
        return 2
    try:
        program = machine.load_program(argv[0])
        compiled = compile_program(program)
    except Exception as exc:  # report and fail; never fall back to another compiler
        print(f"FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    json.dump(compiled, sys.stdout)
    sys.stdout.write("\\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
'''


def assemble(arm: str, learned: Optional[str]) -> Tuple[str, dict]:
    items = bundle(learned)
    header = [
        '"""Standalone objective-index compiler (frozen selected solver, 0.1 s allowance).',
        "",
        "Generated by research/objective_index_export.py from the measured sources, whose",
        "exact bytes are embedded below with their SHA256 and re-verified on start-up.",
        "Do not edit; regenerate. Standard library plus the supplied machine module only.",
        '"""',
        "",
        "import hashlib",
        "import json",
        "import sys",
        "import types",
        "",
        "import machine",
        "",
        f"EXPORT_ARM = {arm!r}",
        f"EXPORT_LEARNED = {learned!r}",
        f"EXPORT_OPTIMISATION_SECONDS = {OPTIMISATION_SECONDS!r}",
        "",
        "_BUNDLE = [",
    ]
    for item in items:
        header.append(f"    ({item['module']!r}, {item['sha256']!r}, {item['source']!r}),")
    header.append("]")
    source = "\n".join(header) + "\n" + LOADER
    ast.parse(source)
    manifest = {"arm": arm, "learned": learned, "optimisation_seconds": OPTIMISATION_SECONDS,
                "components": [{k: v for k, v in item.items() if k != "source"}
                               for item in items],
                "generator_sha256": oc.file_sha256(Path(__file__))}
    return source, manifest


def audit(source: str) -> List[str]:
    """The export and every embedded module: no classical/serial path, stdlib only."""

    problems: List[str] = []
    texts = [("compiler.py", source)]
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and any(isinstance(t, ast.Name) and t.id == "_BUNDLE"
                                                for t in node.targets):
            for element in node.value.elts:
                texts.append((element.elts[0].value, element.elts[2].value))
    for label, text in texts:
        sub = ast.parse(text)
        for node in ast.walk(sub):
            if isinstance(node, ast.Attribute) and node.attr in BANNED_CALLS:
                problems.append(f"{label}: references {node.attr}")
            if isinstance(node, ast.Name) and node.id in BANNED_CALLS:
                problems.append(f"{label}: references {node.id}")
            if isinstance(node, (ast.Import, ast.ImportFrom)):
                names = ([a.name for a in node.names] if isinstance(node, ast.Import)
                         else [node.module or ""])
                for name in names:
                    root = name.split(".")[0]
                    if root in BANNED_IMPORTS:
                        problems.append(f"{label}: imports {name}")
                    embedded = {t[0] for t in texts} | {"research"}
                    if (root not in sys.stdlib_module_names and root != "machine"
                            and name not in embedded and root not in embedded and root):
                        problems.append(f"{label}: imports non-embedded non-stdlib {name}")
    return problems


def write_export(output: Path, arm: str, learned: Optional[str]) -> dict:
    source, manifest = assemble(arm, learned)
    problems = audit(source)
    manifest["audit_problems"] = problems
    if problems:
        raise RuntimeError("export audit failed: " + "; ".join(problems[:5]))
    if output.exists():
        raise FileExistsError(f"refusing to overwrite {output}")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(source, encoding="utf-8")
    manifest["export_sha256"] = oc.file_sha256(output)
    oc.write_json(output.parent / "compiler_MANIFEST.json", manifest)
    return manifest


# --------------------------------------------------------------------------
# Validation
# --------------------------------------------------------------------------


def pinned_checks(tmp: Path, out_dir: Path) -> dict:
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""}
    probe = ("import json, sys, compiler, machine\n"
             "mods = {n: getattr(m, '__file__', None) for n, m in sys.modules.items()\n"
             "        if n == 'research' or n.startswith('research.') or n.startswith('direct_')\n"
             "        or n == 'schema_index'}\n"
             "print(json.dumps({'compiler': compiler.__file__, 'machine': machine.__file__,\n"
             "                  'arm': compiler.EXPORT_ARM, 'learned': compiler.EXPORT_LEARNED,\n"
             "                  'modules': mods}))\n")
    identity = subprocess.run([oc.PYTHON, "-c", probe], cwd=str(tmp), capture_output=True,
                              text=True, env=env)
    tests = oc.run_logged("pinned_public_tests",
                          [oc.PYTHON, "-m", "unittest", "tests.test_public_programs",
                           "tests.test_machine", "-v"], out_dir, env=env, cwd=tmp)
    score = oc.run_logged("pinned_score", [oc.PYTHON, "score.py"], out_dir, env=env, cwd=tmp)
    ident = json.loads(identity.stdout) if identity.returncode == 0 else {}
    modules = ident.get("modules", {})
    return {"identity": ident, "identity_stderr": identity.stderr[-2000:],
            "compiler_is_export": Path(ident.get("compiler", "/")).resolve() ==
            (tmp / "compiler.py").resolve(),
            "machine_is_pinned_copy": Path(ident.get("machine", "/")).resolve() ==
            (tmp / "machine.py").resolve(),
            "embedded_modules_only": bool(modules) and all(
                str(path).startswith("<export:") for path in modules.values()),
            "pinned_tests_exit": tests["exit_code"], "score_exit": score["exit_code"],
            "score_stdout": (out_dir / "pinned_score.stdout").read_text()[-1500:],
            "tests_sha256": {p.name: oc.file_sha256(p)
                             for p in sorted((tmp / "tests").glob("*.py"))},
            "score_sha256": oc.file_sha256(tmp / "score.py"),
            "machine_sha256": oc.file_sha256(tmp / "machine.py"),
            "reference_hashes_equal": {
                "score.py": oc.file_sha256(tmp / "score.py") ==
                oc.file_sha256(ROOT / ".reference" / "score.py"),
                "machine.py": oc.file_sha256(tmp / "machine.py") ==
                oc.file_sha256(ROOT / ".reference" / "machine.py")}}


def measure_rows(run: Path, tmp: Path, label: str, entries: list, reps: int) -> list:
    rows_path = run / "export" / label / "rows.jsonl"
    done = {r["key"] for r in oc.read_rows(rows_path)}
    env = {"PATH": os.environ.get("PATH", ""), "PYTHONPATH": ""}
    for entry in entries:
        program = machine.load_program(entry["program_path"])
        for rep in range(reps):
            key = f"{entry['program_sha256']}|export_{label}|0.1|{rep}"
            if key in done:
                continue
            stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
            started = time.perf_counter()
            timed_out = False
            try:
                proc = subprocess.run([oc.PYTHON, "compiler.py", entry["program_path"]],
                                      cwd=str(tmp), capture_output=True, text=True,
                                      timeout=20.0, env=env)
                stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out, code = True, None
                stdout = exc.stdout if isinstance(exc.stdout, str) else ""
                stderr = exc.stderr if isinstance(exc.stderr, str) else ""
            seconds = time.perf_counter() - started
            row = {"key": key, "program_sha256": entry["program_sha256"],
                   "family": entry["family"], "corpus": entry["corpus"], "repetition": rep,
                   "exit_code": code, "timed_out": timed_out, "process_seconds": seconds,
                   "stderr_tail": stderr[-500:], "started_utc": stamp,
                   "stdout_sha256": oc.sha256_bytes(stdout.encode())}
            try:
                if stdout.count("\n") != 1 or not stdout.endswith("\n"):
                    raise ValueError("stdout is not exactly one JSON line")
                compiled = json.loads(stdout)
                cycles = machine.check_compilation(program, compiled)
                cases = 0
                for case in program["cases"]:
                    machine.check_case(program, compiled, case)
                    cases += 1
                scratch = machine.scratch_footprint(program, compiled)
                row.update(cycles=cycles, scratch=scratch, product=cycles * scratch, cases=cases,
                           program_name=program["name"], correctness="PASS")
            except Exception as exc:  # retained as a failed row
                row.update(correctness="FAIL", failure=f"{type(exc).__name__}: {exc}")
            row["failed_row"] = row["correctness"] != "PASS" or code != 0 or timed_out
            oc.append_row(rows_path, row)
    return oc.read_rows(rows_path)


def validate(run: Path, label: str) -> dict:
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    arm = frozen["selection"]["selected_arm"]
    learned = {"nonmodel": None, "tree": "tree", "shuffled_tree": "shuffled_tree"}[label]
    if arm == "A0_frozen_phase2":
        raise RuntimeError("A0 selected: the accepted Phase 2 control has no new export")
    out_dir = run / "export" / label
    output = out_dir / "compiler.py"
    report: dict = {"label": label, "arm": arm, "learned": learned}
    if not output.exists():
        manifest = write_export(output, arm, learned)
    else:
        manifest = json.loads((out_dir / "compiler_MANIFEST.json").read_text())
    research = frozen["sources"]["research"]
    production = frozen["sources"]["production"]
    mismatched = [c["file"] for c in manifest["components"]
                  if (research.get(c["file"]) or production.get(c["file"])) != c["file_sha256"]]
    report["build"] = {"path": str(output), "sha256": oc.file_sha256(output),
                       "component_file_mismatches_vs_freeze": mismatched,
                       "generator_matches_freeze": manifest["generator_sha256"] ==
                       research.get("research/objective_index_export.py"),
                       "components": manifest["components"]}
    again, _ = assemble(arm, learned)
    report["deterministic_regeneration"] = (hashlib.sha256(again.encode()).hexdigest()
                                            == oc.file_sha256(output))
    report["audit_problems"] = audit(output.read_text())
    tmp = oev.workspace(output)
    report["pinned"] = pinned_checks(tmp, out_dir / "pinned")
    public = [dict(e, corpus="public") for e in json.loads(
        (run / "stages" / "EVAL_public" / "STAGE_MANIFEST.json").read_text())["extra"]["programs"]]
    from tests_direct import generate_programs as gp

    pinned_public = sorted((run / "inputs" / "public").glob("*.json"))
    for entry in public:
        match = [p for p in pinned_public
                 if gp.program_digest(machine.load_program(p)) == entry["program_sha256"]]
        entry["program_path"] = str(match[0])
    fresh = [dict(e, corpus="fresh") for e in
             json.loads((run / "FRESH_COHORT.json").read_text())["programs"]]
    rows = measure_rows(run, tmp, label, public + fresh, 3)
    report["rows"] = len(rows)
    report["expected_rows"] = 624
    report["failed_rows"] = sum(r["failed_row"] for r in rows)
    boot, research_j = {}, {}
    for stage in ("EVAL_compiler", "EVAL_public"):
        for r in oc.read_rows(run / "stages" / stage / "rows.jsonl"):
            if r["arm"] == "accepted_bootstrap" and not r["failed_row"]:
                boot[r["program_sha256"]] = r["product"]
            if r["arm"] == arm and r["budget_seconds"] == OPTIMISATION_SECONDS \
                    and not r["failed_row"]:
                research_j.setdefault(r["program_sha256"], set()).add(r["product"])
    above = [r["key"] for r in rows if not r["failed_row"] and
             r["product"] > boot.get(r["program_sha256"], float("inf"))]
    differs = [r["key"] for r in rows if not r["failed_row"] and
               r["product"] not in research_j.get(r["program_sha256"], set())]
    report["outputs_above_bootstrap"] = above
    report["outputs_outside_research_J_set"] = {
        "count": len(differs), "first": differs[:10],
        "note": "timing-sensitive J variation; reported, not a failure by itself"}
    from research import optimization_stage_a as osa

    serial = osa.frozen_serial()
    scores = []
    for rep in range(3):
        chosen = [r for r in rows if r["corpus"] == "public" and r["repetition"] == rep]
        if len(chosen) == 8 and not any(r["failed_row"] for r in chosen):
            speed = math.exp(sum(math.log(serial[r["program_name"]]["cycles"] / r["cycles"])
                                 for r in chosen) / 8)
            scratch = math.exp(sum(math.log(serial[r["program_name"]]["scratch"] / r["scratch"])
                                   for r in chosen) / 8)
            scores.append(math.sqrt(speed * scratch))
        else:
            scores.append(None)
    report["export_public_scores"] = scores
    times = sorted(r["process_seconds"] for r in rows if not r["failed_row"])
    report["process_seconds"] = {"median": times[len(times) // 2] if times else None,
                                 "p95": times[int(0.95 * (len(times) - 1))] if times else None,
                                 "max": times[-1] if times else None}
    pinned = report["pinned"]
    report["status"] = ("PASS" if report["rows"] == 624 and report["failed_rows"] == 0
                        and not above and pinned["compiler_is_export"]
                        and pinned["machine_is_pinned_copy"] and pinned["embedded_modules_only"]
                        and pinned["pinned_tests_exit"] == 0 and pinned["score_exit"] == 0
                        and report["deterministic_regeneration"] and not mismatched
                        and not report["audit_problems"] else "FAIL")
    oc.write_json(out_dir / "EXPORT_VALIDATION.json", report)
    shutil.rmtree(tmp, ignore_errors=True)
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--label", default="nonmodel",
                        choices=["nonmodel", "tree", "shuffled_tree"])
    args = parser.parse_args(argv)
    report = validate(Path(args.run).resolve(), args.label)
    print(json.dumps({k: report[k] for k in ("status", "rows", "failed_rows",
                                             "export_public_scores")}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
