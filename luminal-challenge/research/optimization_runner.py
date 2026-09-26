"""Orchestration of optimization protocol 1.0: corpora, matrices, journals.

This module launches workers; it measures nothing itself. Every measured row
comes from a fresh subprocess:

- ``research.optimization_worker`` for NEW arms (current research source);
- ``optimization_frozen_worker.py`` inside the frozen-control workspace for the
  accepted Phase 2 control, the original direct arms, classical and serial;
- ``research.optimization_model_worker`` for fixture model rows.

Rows and commands are appended and fsynced one at a time. Resume re-runs only
keys that have no row at all, and only under an identical stage manifest.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_runner --run DIR --stage STAGE
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import random
import shutil
import subprocess
import sys
import time
from typing import Callable, Dict, List, Optional, Sequence, Tuple

import machine

from research import optimization_common as oc


SEED_ARM_ORDER = 2026092401
BUDGETS = (0.01, 0.1, 1.0)
WORKER_TIMEOUT = 20.0

# The inherited worker policy of the accepted run, reused verbatim so that the
# accepted entry point accepts the spec. These are the frozen recovery inputs.
FROZEN_LIMITS = {
    "cover_max_cubes": 65536, "cover_seconds_per_set": 10, "exhaust_bit_width_max": 16,
    "external_process_seconds": 20, "optimisation_seconds": [0.01, 0.1, 1.0],
    "oracle_cartesian_max": 65536, "primary_seconds": 0.1, "query_max_cover": 4096,
    "query_max_records": 20000, "query_max_visited": 50000,
    "search_max_candidate_validations": 100000, "search_max_nodes": 1000000,
}
RECOVERY_FILES = (
    "plan/PHASE2_RECOVERY_AND_COMPARISON_PLAN.md", "plan/phase2_recovery/AMENDMENT.json",
    "plan/phase2_recovery/LUNA_PROMPT.md", "plan/phase2_recovery/verify_package.py",
    "plan/phase2/PACKAGE_LOCK.json", "plan/phase2/BASELINE_LOCK.json", "plan/phase2/PROTOCOL.json",
)

# Files imported by NEW-arm and model workers. A change to any of them after a
# stage starts invalidates pooling with that stage's earlier rows.
COMPILER_SOURCES = (
    "research/__init__.py", "research/optimization_common.py",
    "research/optimization_search.py", "research/optimization_worker.py",
    "research/optimization_frozen_worker.py", "research/run_structural_experiments.py",
    "research/structural_encoding.py", "research/structural_search.py",
    "research/structural_models.py", "research/structural_oracle.py",
    "research/structural_evidence.py", "research/physical_probes.py",
    "research/classical_measurement_worker.py",
)
MODEL_SOURCES = COMPILER_SOURCES + (
    "research/optimization_models.py", "research/optimization_model_worker.py",
    "research/optimization_fixtures.py",
)


# --------------------------------------------------------------------------
# Frozen-control workspace
# --------------------------------------------------------------------------


def frozen_workspace(run: Path) -> Path:
    return Path(run).resolve() / "frozen_control_workspace"


def setup_frozen_workspace(run: Path) -> dict:
    """Copy the verified accepted snapshot and the worker into a workspace."""

    check = oc.verify_frozen_snapshot()
    if check["status"] != "PASS":
        raise RuntimeError(f"accepted snapshot verification failed: {check}")
    workspace = frozen_workspace(run)
    if not workspace.exists():
        (workspace / "research").mkdir(parents=True)
        for path in sorted((oc.FROZEN_SNAPSHOT / "research").iterdir()):
            if path.is_file():
                shutil.copy2(path, workspace / "research" / path.name)
        os.symlink(oc.ROOT / "plan", workspace / "plan")
        shutil.copy2(oc.ROOT / "research" / "optimization_frozen_worker.py",
                     workspace / "optimization_frozen_worker.py")
    hashes = {str(p.relative_to(workspace)): oc.file_sha256(p)
              for p in sorted(workspace.rglob("*.py")) if "__pycache__" not in p.parts
              and not str(p.relative_to(workspace)).startswith("plan")}
    snapshot = oc.frozen_snapshot_hashes()
    mismatched = [name for name, digest in snapshot.items() if hashes.get(name) != digest]
    worker_equal = hashes.get("optimization_frozen_worker.py") == oc.file_sha256(
        oc.ROOT / "research" / "optimization_frozen_worker.py")
    return {"workspace": str(workspace), "snapshot_check": check, "hashes": hashes,
            "snapshot_mismatches": mismatched, "worker_equal_to_source": worker_equal,
            "status": "PASS" if not mismatched and worker_equal else "FAIL"}


def isolation_probe(run: Path) -> dict:
    """Which files each worker kind actually imports, with their hashes."""

    workspace = frozen_workspace(run)
    frozen_code = (
        "import sys, json, hashlib\n"
        f"sys.path[:0] = [{str(workspace)!r}, {str(oc.ROOT / '.reference')!r}, {str(oc.ROOT)!r}]\n"
        "import research.run_structural_experiments, research.classical_measurement_worker\n"
        "import common\n"
        "out = {}\n"
        "for n, m in sorted(sys.modules.items()):\n"
        "    f = getattr(m, '__file__', None)\n"
        "    if f and (n == 'research' or n.startswith('research.') or n in ('machine','common',"
        "'direct_compiler','direct_contract','direct_optimizer','direct_constraints',"
        "'schema_index','compare_direct','verify_direct')):\n"
        "        out[n] = {'path': f, 'sha256': hashlib.sha256(open(f,'rb').read()).hexdigest()}\n"
        "print(json.dumps(out))\n"
    )
    new_code = frozen_code.replace(f"{str(workspace)!r}, ", "").replace(
        "import research.run_structural_experiments, research.classical_measurement_worker",
        "import research.optimization_worker" + (
            ", research.optimization_model_worker"
            if (oc.ROOT / "research" / "optimization_model_worker.py").exists() else ""))
    out = {}
    for label, code, cwd in (("frozen", frozen_code, workspace), ("new", new_code, oc.ROOT)):
        proc = subprocess.run([oc.PYTHON, "-c", code], cwd=str(cwd), capture_output=True,
                              text=True, env={"PATH": os.environ.get("PATH", "")})
        out[label] = {"exit_code": proc.returncode, "stderr": proc.stderr[-2000:],
                      "modules": json.loads(proc.stdout) if proc.returncode == 0 else None}
    frozen_modules = (out["frozen"]["modules"] or {})
    snapshot = oc.frozen_snapshot_hashes()
    research_ok = all(
        entry["path"].startswith(str(workspace)) and
        entry["sha256"] == snapshot.get(str(Path(entry["path"]).relative_to(workspace)))
        for name, entry in frozen_modules.items() if name.startswith("research")
        and name != "research")
    production = oc.production_source_hashes()
    prod_ok = all(entry["sha256"] == production.get(str(Path(entry["path"]).relative_to(oc.ROOT)))
                  for name, entry in frozen_modules.items() if not name.startswith("research")
                  and str(entry["path"]).startswith(str(oc.ROOT)) and
                  str(Path(entry["path"]).relative_to(oc.ROOT)) in production)
    out["frozen_research_from_snapshot"] = research_ok and any(
        n.startswith("research.") for n in frozen_modules)
    out["frozen_production_protected"] = prod_ok
    out["status"] = "PASS" if (out["frozen_research_from_snapshot"] and prod_ok and
                               out["new"]["exit_code"] == 0) else "FAIL"
    return out


# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------


def _pin(run: Path, cohort: str, name: str, program: dict) -> Tuple[Path, str]:
    from tests_direct import generate_programs as gp

    path = Path(run) / "inputs" / cohort / f"{name}.json"
    data = json.dumps(program, sort_keys=True, indent=1) + "\n"
    if path.exists():
        if path.read_text() != data:
            raise RuntimeError(f"pinned program {path} changed")
    else:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data)
    return path, gp.program_digest(program)


def generated_cohort(run: Path, cohort: str, first: int, last: int) -> List[dict]:
    """Programs from the unchanged generator, pinned, in family-then-seed order."""

    from research import structural_encoding as se
    from tests_direct import generate_programs as gp

    entries = []
    for seed in range(first, last + 1):
        program = gp.additional_program(seed)
        machine.validate_program(program)
        serial = machine.serial_compile(program)
        machine.check_compilation(program, serial)
        for case in program["cases"]:
            machine.check_case(program, serial, case)
        path, digest = _pin(run, cohort, f"seed_{seed}", program)
        entries.append({"seed": seed, "family": gp.FAMILIES[seed % 5], "name": program["name"],
                        "program_path": str(path), "program_sha256": digest,
                        "file_sha256": oc.file_sha256(path),
                        "semantic_sha256": se.program_semantic_digest(program),
                        "operations": len(program["operations"])})
    order = {family: i for i, family in enumerate(gp.FAMILIES)}
    entries.sort(key=lambda e: (order[e["family"]], e["seed"]))
    return entries


def public_cohort(run: Path) -> List[dict]:
    from research import structural_encoding as se

    entries = []
    for path in sorted((oc.ROOT / ".reference" / "programs").glob("*.json")):
        program = machine.load_program(path)
        pinned, digest = _pin(run, "public", path.stem, program)
        entries.append({"seed": None, "family": "public", "name": program["name"],
                        "program_path": str(pinned), "program_sha256": digest,
                        "file_sha256": oc.file_sha256(pinned),
                        "semantic_sha256": se.program_semantic_digest(program),
                        "operations": len(program["operations"])})
    if len(entries) != 8:
        raise RuntimeError("expected eight public programs")
    return entries


# --------------------------------------------------------------------------
# Arms
# --------------------------------------------------------------------------


def recovery_identity() -> dict:
    return {"amendment_id": "luminal-phase2-recovery-1.0",
            "amendment_files": {name: oc.file_sha256(oc.ROOT / name) for name in RECOVERY_FILES}}


def arm_command(run: Path, stage: str, corpus: str, entry: dict, arm: dict,
                budget: Optional[float], repetition: int) -> Tuple[List[str], dict, Path]:
    """The exact argv, spec and cwd of one measured row."""

    worker = arm["worker"]
    if worker == "new":
        spec = {"kind": "optimization_new_measurement", "program_path": entry["program_path"],
                "program_sha256": entry["program_sha256"], "arm": arm["label"],
                "config": arm["config"], "build": arm["build"],
                "search_arm": arm.get("search_arm", "structural_bound"),
                "model_depth": arm.get("model_depth"), "budget_seconds": budget,
                "repetition": repetition, "stage": stage, "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.optimization_worker", "--spec", oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker == "frozen":
        workspace = frozen_workspace(run)
        spec = {"kind": "optimization_frozen_measurement", "arm": arm["label"],
                "program_path": entry["program_path"], "program_sha256": entry["program_sha256"],
                "budget_seconds": budget, "repetition": repetition, "stage": stage,
                "corpus": corpus}
        if arm["label"] == "classical":
            spec["inner"] = dict(recovery_identity(), kind="phase2_measurement", arm="classical",
                                 budget_seconds=None, search_seed=None, stage=stage,
                                 corpus=corpus, program_path=entry["program_path"],
                                 program_sha256=entry["program_sha256"], repetition=repetition)
        elif arm["label"] != "serial":
            spec["inner"] = dict(recovery_identity(), kind="phase2_measurement",
                                 arm=arm["inner_arm"], budget_seconds=budget, codec=None,
                                 elite_fraction=0.1, limits=FROZEN_LIMITS, stage=stage,
                                 corpus=corpus, program_path=entry["program_path"],
                                 program_sha256=entry["program_sha256"],
                                 repetition=repetition, search_seed=None)
        argv = [oc.PYTHON, str(workspace / "optimization_frozen_worker.py"), "--workspace",
                str(workspace), "--challenge", str(oc.ROOT), "--spec", oc.canonical(spec)]
        return argv, spec, workspace
    if worker == "model":
        spec = {"kind": "optimization_model_measurement", "fixture_dir": entry["fixture_dir"],
                "fixture_id": entry["fixture_id"], "family": entry["family"],
                "program_sha256": entry["program_sha256"],
                "expected_sha256": entry["expected_sha256"], "arm": arm["label"],
                "learner_arm": arm["learner_arm"], "search_seed": arm.get("search_seed"),
                "budget_seconds": budget, "repetition": repetition, "stage": stage,
                "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.optimization_model_worker", "--spec",
                oc.canonical(spec)]
        return argv, spec, oc.ROOT
    raise ValueError(f"unknown worker {worker!r}")


def frozen_arm(label: str) -> dict:
    inner = {"frozen_phase2": "structural_bound", "accepted_budgeted": "accepted_budgeted",
             "accepted_default": "accepted_default",
             "accepted_bootstrap": "accepted_bootstrap"}.get(label)
    return {"label": label, "worker": "frozen", "inner_arm": inner}


def new_arm(label: str, config: str, build: str = "reference",
            search_arm: str = "structural_bound", model_depth: Optional[int] = None) -> dict:
    return {"label": label, "worker": "new", "config": config, "build": build,
            "search_arm": search_arm, "model_depth": model_depth}


# --------------------------------------------------------------------------
# Matrix engine
# --------------------------------------------------------------------------


def row_key(program_sha256: str, arm: str, budget: Optional[float], repetition: int) -> str:
    return f"{program_sha256}|{arm}|{budget}|{repetition}"


def entry_id(entry: dict) -> str:
    """Programs are keyed by program digest; fixtures by fixture identifier."""

    return entry.get("fixture_id") or entry["program_sha256"]


def schedule(entries: Sequence[dict], unbudgeted: Sequence[str], budgeted: Sequence[str],
             budgets: Sequence[float], repetitions: int, seed: int = SEED_ARM_ORDER
             ) -> List[Tuple[dict, Optional[float], int, str]]:
    """Programs in manifest order; budgets ascending after the unbudgeted block;
    repetitions ascending; within each (program, budget, repetition) block the
    sorted arm list is shuffled by one RNG seeded ``2026092401`` for the stage."""

    rng = random.Random(seed)
    out = []
    for entry in entries:
        for budget in [None] + sorted(budgets):
            arms = sorted(unbudgeted) if budget is None else sorted(budgeted)
            if not arms:
                continue
            for repetition in range(repetitions):
                order = list(arms)
                rng.shuffle(order)
                for arm in order:
                    out.append((entry, budget, repetition, arm))
    return out


def stage_manifest(stage: str, extra: dict, sources: Sequence[str] = COMPILER_SOURCES) -> dict:
    """Everything that must be identical for rows of one stage to be pooled.

    The source list is the set of files imported by that stage's workers, so a
    later addition of an unrelated module does not masquerade as a change."""

    missing = [name for name in sources if oc.file_sha256(oc.ROOT / name) is None]
    if missing:
        raise RuntimeError(f"measured sources missing: {missing}")
    payload = {"stage": stage, "measured_sources": {
        name: oc.file_sha256(oc.ROOT / name) for name in sources},
        "production": oc.production_source_hashes(),
        "frozen_snapshot": oc.frozen_snapshot_hashes(),
        "python": sys.version, "executable": oc.PYTHON, "extra": extra}
    payload["manifest_sha256"] = oc.object_sha256(payload)
    return payload


class Matrix:
    """One stage's expected keys, schedule, journal and resume ownership."""

    def __init__(self, run: Path, stage: str, corpus: str, entries: Sequence[dict],
                 arms: Dict[str, dict], unbudgeted: Sequence[str], budgeted: Sequence[str],
                 budgets: Sequence[float], repetitions: int, extra: Optional[dict] = None,
                 freeze_sha256: Optional[str] = None,
                 sources: Sequence[str] = COMPILER_SOURCES) -> None:
        self.run = Path(run).resolve()
        self.stage = stage
        self.corpus = corpus
        self.entries = list(entries)
        self.arms = arms
        self.unbudgeted = list(unbudgeted)
        self.budgeted = list(budgeted)
        self.budgets = list(budgets)
        self.repetitions = repetitions
        self.freeze_sha256 = freeze_sha256
        self.dir = self.run / "stages" / stage
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rows_path = self.dir / "rows.jsonl"
        self.commands_path = self.dir / "commands.jsonl"
        self.plan = schedule(self.entries, self.unbudgeted, self.budgeted, self.budgets,
                             self.repetitions)
        self.expected = [row_key(entry_id(e), a, b, r) for e, b, r, a in self.plan]
        extra = dict(extra or {}, corpus=corpus, arms=arms, unbudgeted=self.unbudgeted,
                     budgeted=self.budgeted, budgets=self.budgets, repetitions=repetitions,
                     programs=[{k: e.get(k) for k in ("seed", "family", "program_sha256",
                                                       "file_sha256", "fixture_id",
                                                       "expected_sha256")}
                               for e in self.entries],
                     freeze_sha256=freeze_sha256)
        self.manifest = stage_manifest(stage, extra, sources)

    def write_expected(self) -> None:
        path = self.dir / "EXPECTED_KEYS.json"
        payload = {"stage": self.stage, "count": len(self.expected), "keys": self.expected,
                   "order_seed": SEED_ARM_ORDER}
        if path.exists():
            if json.loads(path.read_text())["keys"] != self.expected:
                raise RuntimeError(f"{self.stage}: expected key ledger changed")
            return
        oc.write_immutable_json(path, payload)

    def check_manifest(self) -> None:
        path = self.dir / "STAGE_MANIFEST.json"
        if path.exists():
            previous = json.loads(path.read_text())
            if previous["manifest_sha256"] != self.manifest["manifest_sha256"]:
                raise RuntimeError(
                    f"{self.stage}: source/config/environment differs from the stage manifest; "
                    "resume is refused. Preserve these rows as superseded and start a fresh stage.")
            return
        oc.write_immutable_json(path, self.manifest)

    def done_keys(self) -> set:
        return {row["key"] for row in oc.read_rows(self.rows_path)}

    def run_all(self, progress_every: int = 500) -> dict:
        self.check_manifest()
        self.write_expected()
        done = self.done_keys()
        extra_rows = done - set(self.expected)
        if extra_rows:
            raise RuntimeError(f"{self.stage}: journal holds {len(extra_rows)} unexpected keys")
        pending = [item for item, key in zip(self.plan, self.expected) if key not in done]
        oc.append_row(self.dir / "resume_log.jsonl", {
            "event": "start", "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "pid": os.getpid(), "expected": len(self.expected), "already_done": len(done),
            "pending": len(pending), "manifest_sha256": self.manifest["manifest_sha256"]})
        started = time.perf_counter()
        for count, (entry, budget, repetition, arm_label) in enumerate(pending, 1):
            self.run_one(entry, budget, repetition, arm_label)
            if count % progress_every == 0:
                print(f"{self.stage}: {count}/{len(pending)} rows, "
                      f"{time.perf_counter() - started:.0f}s", flush=True)
        done = self.done_keys()
        # Sources are re-hashed at the end: an edit during the stage would mean
        # rows measured different code under one manifest, which is refused.
        end_sources = {name: oc.file_sha256(oc.ROOT / name)
                       for name in self.manifest["measured_sources"]}
        unchanged = end_sources == self.manifest["measured_sources"]
        summary = {"stage": self.stage, "sources_unchanged_during_stage": unchanged,
                   "expected": len(self.expected), "observed": len(done),
                   "missing": len(set(self.expected) - done),
                   "failed": sum(1 for r in oc.read_rows(self.rows_path) if r["failed_row"])}
        oc.append_row(self.dir / "resume_log.jsonl", dict(summary, event="end",
                      utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        return summary

    def run_one(self, entry: dict, budget: Optional[float], repetition: int,
                arm_label: str) -> dict:
        arm = self.arms[arm_label]
        argv, spec, cwd = arm_command(self.run, self.stage, self.corpus, entry, arm, budget,
                                      repetition)
        env = {"PATH": os.environ.get("PATH", ""),
               "PYTHONPATH": f"{oc.ROOT / '.reference'}{os.pathsep}{oc.ROOT}"}
        if arm["worker"] == "frozen":
            env["PYTHONPATH"] = ""
        stamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        started = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(argv, cwd=str(cwd), capture_output=True, text=True,
                                  timeout=WORKER_TIMEOUT, env=env)
            stdout, stderr, code = proc.stdout, proc.stderr, proc.returncode
        except subprocess.TimeoutExpired as exc:
            timed_out = True
            stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
            stderr = exc.stderr.decode() if isinstance(exc.stderr, bytes) else (exc.stderr or "")
            code = None
        process_seconds = time.perf_counter() - started
        key = row_key(entry_id(entry), arm_label, budget, repetition)
        row = {"key": key, "stage": self.stage, "corpus": self.corpus,
               "program_sha256": entry["program_sha256"], "family": entry["family"],
               "fixture_id": entry.get("fixture_id"),
               "seed": entry["seed"], "arm": arm_label, "budget_seconds": budget,
               "repetition": repetition, "exit_code": code, "timed_out": timed_out,
               "process_seconds": process_seconds, "stderr_tail": stderr[-2000:],
               "started_utc": stamp, "manifest_sha256": self.manifest["manifest_sha256"],
               "freeze_sha256": self.freeze_sha256}
        parsed = None
        if not timed_out and code == 0 and stdout.strip():
            try:
                parsed = json.loads(stdout.strip().splitlines()[-1])
            except json.JSONDecodeError as exc:
                row["failure"] = f"stdout was not one JSON object: {exc}"
        if parsed is not None and str(parsed.get("kind", "")).endswith("_result"):
            result = {k: v for k, v in parsed.items() if k not in ("kind",)}
            for field in ("arm", "budget_seconds", "repetition", "stage", "corpus"):
                result.pop(field, None)
            if result.get("program_sha256") != entry["program_sha256"]:
                row["failure"] = "worker program identity does not match the spec"
            result.pop("program_sha256", None)
            row["result"] = result
            row["cycles"] = result.get("cycles")
            row["scratch"] = result.get("scratch")
            row["product"] = result.get("product")
            row["correctness"] = result.get("correctness", "FAIL")
        else:
            row.setdefault("failure", "worker produced no valid result")
            row["correctness"] = "FAIL"
        row["failed_row"] = bool(row.get("failure")) or row["correctness"] != "PASS"
        oc.append_row(self.commands_path, {
            "key": key, "argv": argv[:-1] + ["<spec>"], "spec": spec, "cwd": str(cwd),
            "exit_code": code, "timed_out": timed_out, "process_seconds": process_seconds,
            "started_utc": stamp})
        oc.append_row(self.rows_path, row)
        return row


# --------------------------------------------------------------------------
# Stage definitions
# --------------------------------------------------------------------------


def development_entries(run: Path) -> List[dict]:
    return generated_cohort(run, "development", 800000, 800099)


def stage_b(run: Path) -> Matrix:
    from research import optimization_search as osr

    arms = {f"new_{config}": new_arm(f"new_{config}", config) for config in osr.CONFIGS}
    arms.update({label: frozen_arm(label) for label in ("frozen_phase2", "accepted_budgeted")})
    arms["classical"] = frozen_arm("classical")
    budgeted = sorted(label for label in arms if label != "classical")
    return Matrix(run, "B_search_development", "development", development_entries(run), arms,
                  ["classical"], budgeted, BUDGETS, 3)


def selected_from(run: Path) -> dict:
    """The development decisions made so far, each written once to its own file."""

    out = {}
    for part in ("search", "engineering", "ablation", "model"):
        path = Path(run) / "selection" / f"{part}.json"
        if path.exists():
            out[part] = json.loads(path.read_text())
    return out


def decide(run: Path, part: str) -> dict:
    """Apply one fixed development rule to complete development rows."""

    from research import optimization_analysis as oa
    from research import optimization_search as osr

    run = Path(run)
    target = run / "selection" / f"{part}.json"
    if part == "search":
        stage = "B_search_development"
        rows = oa.stage_rows(run, stage)
        payload = oa.select_search(rows, oa.expected_keys(run, stage), osr.CONFIGS)
        arm = payload["selected_compiler"]
        payload["minimum_detectable_effect"] = oa.minimum_detectable_effect(
            rows, arm if arm != "frozen_phase2" else "new_cap32_matched")
        payload["runtime_0.1_vs_frozen"] = {
            e["config"]: oa.runtime_ratio(rows, "frozen_phase2", e["arm"], 0.1, 0.1,
                                          "compile_seconds", with_interval=False)
            for e in payload["table"]}
    elif part == "engineering":
        stage = "B_engineering_pair"
        payload = oa.engineering_decision(oa.stage_rows(run, stage),
                                          oa.expected_keys(run, stage))
    elif part == "ablation":
        stage = "B_bound_ablation"
        payload = oa.ablation_description(oa.stage_rows(run, stage),
                                          oa.expected_keys(run, stage))
    elif part == "model":
        stage = "C_model_development"
        payload = oa.select_depth(oa.stage_rows(run, stage), oa.expected_keys(run, stage))
    else:
        raise ValueError(part)
    payload["source_rows_sha256"] = oc.file_sha256(run / "stages" / stage / "rows.jsonl")
    payload["decided_utc"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    oc.write_immutable_json(target, payload)
    return payload


def stage_engineering(run: Path) -> Matrix:
    selection = selected_from(run)["search"]
    config = selection["selected_config"]
    if config is None:
        raise RuntimeError("no NEW configuration was selected; engineering pair not applicable")
    arms = {"selected_reference": new_arm("selected_reference", config, "reference"),
            "selected_cached": new_arm("selected_cached", config, "cached")}
    return Matrix(run, "B_engineering_pair", "development", development_entries(run), arms, [],
                  sorted(arms), BUDGETS, 3, extra={"selected_config": config})


def stage_ablation(run: Path) -> Matrix:
    selection = selected_from(run)
    config = selection["search"]["selected_config"]
    build = selection["engineering"]["adopted_build"]
    arms = {"selected_bound": new_arm("selected_bound", config, build, "structural_bound"),
            "selected_dfs": new_arm("selected_dfs", config, build, "structural_dfs")}
    return Matrix(run, "B_bound_ablation", "development", development_entries(run), arms, [],
                  sorted(arms), BUDGETS, 3, extra={"selected_config": config, "build": build})


def fresh_entries(run: Path) -> List[dict]:
    return generated_cohort(run, "compiler_evaluation", 810000, 810199)


def evaluation_arms(frozen: dict, model: bool) -> Tuple[Dict[str, dict], List[str], List[str]]:
    arms = {label: frozen_arm(label) for label in (
        "accepted_bootstrap", "accepted_default", "classical", "accepted_budgeted",
        "frozen_phase2")}
    selected = frozen["search"]
    arms["selected_nonmodel"] = (
        new_arm("selected_nonmodel", selected["config"], selected["build"])
        if selected["config"] is not None else dict(frozen_arm("frozen_phase2"),
                                                    label="selected_nonmodel"))
    budgeted = ["accepted_budgeted", "frozen_phase2", "selected_nonmodel"]
    if model:
        arms["selected_model_compiler"] = new_arm(
            "selected_model_compiler", selected["config"] or "cap32_matched",
            selected["build"], model_depth=frozen["model"]["selected_depth"])
        budgeted.append("selected_model_compiler")
    return arms, ["accepted_bootstrap", "accepted_default", "classical"], budgeted


def load_freeze(run: Path) -> Tuple[dict, str]:
    path = Path(run) / "FROZEN_SELECTION.json"
    payload = json.loads(path.read_text())
    return payload, oc.file_sha256(path)


def stage_d(run: Path, model: bool = False) -> Matrix:
    frozen, digest = load_freeze(run)
    entries = [e for e in json.loads((Path(run) / "FRESH_COHORT.json").read_text())["programs"]]
    arms, unbudgeted, budgeted = evaluation_arms(frozen, model=False)
    if model:
        all_arms, _, _ = evaluation_arms(frozen, model=True)
        arms = {"selected_model_compiler": all_arms["selected_model_compiler"]}
        return Matrix(run, "D_fresh_model_compiler", "compiler_evaluation", entries, arms, [],
                      ["selected_model_compiler"], BUDGETS, 15, freeze_sha256=digest)
    return Matrix(run, "D_fresh_compiler", "compiler_evaluation", entries, arms, unbudgeted,
                  budgeted, BUDGETS, 15, freeze_sha256=digest)


def stage_public(run: Path, model: bool = False) -> Matrix:
    frozen, digest = load_freeze(run)
    entries = public_cohort(run)
    arms, unbudgeted, budgeted = evaluation_arms(frozen, model=False)
    if model:
        all_arms, _, _ = evaluation_arms(frozen, model=True)
        arms = {"selected_model_compiler": all_arms["selected_model_compiler"]}
        return Matrix(run, "D_public_model_compiler", "public", entries, arms, [],
                      ["selected_model_compiler"], BUDGETS, 15, freeze_sha256=digest)
    arms["serial"] = frozen_arm("serial")
    return Matrix(run, "D_public", "public", entries, arms, unbudgeted + ["serial"], budgeted,
                  BUDGETS, 15, freeze_sha256=digest)


UNIFORM_SEEDS = tuple(range(2026092410, 2026092420))


def fixture_entries(run: Path, cohort: str) -> List[dict]:
    manifest = json.loads((Path(run) / "fixtures" / cohort / "MANIFEST.json").read_text())
    if manifest["status"] != "PASS" or manifest["collision_block"]:
        raise RuntimeError(f"{cohort} fixtures are {manifest['status']}; stage blocked")
    entries = []
    for fixture in manifest["fixtures"]:
        directory = Path(run) / "fixtures" / cohort / fixture["fixture_id"]
        entries.append({"fixture_id": fixture["fixture_id"], "family": fixture["family"],
                        "seed": fixture["seed"], "program_sha256": fixture["program_sha256"],
                        "fixture_dir": str(directory),
                        "expected_sha256": {"record": fixture["record_sha256"],
                                            "oracle": fixture["oracle_sha256"],
                                            "split": fixture["split_sha256"]}})
    return entries


def model_arm(label: str, learner_arm: str, seed: Optional[int] = None) -> dict:
    return {"label": label, "worker": "model", "learner_arm": learner_arm, "search_seed": seed}


def stage_model_development(run: Path) -> Matrix:
    arms = {"model_depth1": model_arm("model_depth1", "model_depth1"),
            "model_depth2": model_arm("model_depth2", "model_depth2")}
    return Matrix(run, "C_model_development", "model_development",
                  fixture_entries(run, "development"), arms, [], sorted(arms), BUDGETS, 3,
                  sources=MODEL_SOURCES)


def stage_model_evaluation(run: Path, descriptive: bool = False) -> Matrix:
    frozen, digest = load_freeze(run)
    depth = frozen["model"]["selected_depth"]
    if descriptive:
        if depth != 2:
            raise RuntimeError("the depth-1 descriptive arm applies only when depth 2 is selected")
        arms = {"model_depth1_descriptive": model_arm("model_depth1_descriptive",
                                                       "model_depth1")}
        return Matrix(run, "C_model_evaluation_depth1_descriptive", "model_evaluation",
                      fixture_entries(run, "evaluation"), arms, [], sorted(arms), BUDGETS, 15,
                      freeze_sha256=digest, sources=MODEL_SOURCES)
    arms = {"empirical_cover": model_arm("empirical_cover", "empirical_cover"),
            "selected_model": model_arm("selected_model", f"model_depth{depth}"),
            "one_bit": model_arm("one_bit", "one_bit")}
    for seed in UNIFORM_SEEDS:
        arms[f"uniform_bits_{seed}"] = model_arm(f"uniform_bits_{seed}", "uniform_bits", seed)
    return Matrix(run, "C_model_evaluation", "model_evaluation",
                  fixture_entries(run, "evaluation"), arms, [], sorted(arms), BUDGETS, 15,
                  freeze_sha256=digest, sources=MODEL_SOURCES)


STAGES: Dict[str, Callable[..., Matrix]] = {
    "C_model_development": stage_model_development,
    "C_model_evaluation": stage_model_evaluation,
    "C_model_evaluation_depth1_descriptive": lambda run: stage_model_evaluation(run, True),
    "B_search_development": stage_b,
    "B_engineering_pair": stage_engineering,
    "B_bound_ablation": stage_ablation,
    "D_fresh_compiler": stage_d,
    "D_public": stage_public,
    "D_fresh_model_compiler": lambda run: stage_d(run, model=True),
    "D_public_model_compiler": lambda run: stage_public(run, model=True),
}


def qualify(run: Path, cohort: str) -> dict:
    """Oracle-only fixture qualification of one pool (Stage C)."""

    from research import optimization_fixtures as of

    others = {"development": of.POOLS["evaluation"], "evaluation": of.POOLS["development"]}
    other_first, other_last, _ = others[cohort]
    index = of.existing_semantics({"old_development": range(800000, 800100),
                                   "compiler_evaluation": range(810000, 810200)})
    started = time.perf_counter()
    manifest = of.qualify_pool(cohort, Path(run) / "fixtures" / cohort, index,
                               range(other_first, other_last + 1))
    manifest_seconds = time.perf_counter() - started
    oc.append_row(Path(run) / "fixtures" / "qualification_runs.jsonl",
                  {"cohort": cohort, "seconds": manifest_seconds, "status": manifest["status"],
                   "filled": manifest["filled"],
                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return manifest


def freeze_fresh_cohort(run: Path) -> dict:
    """Reference-only legality checks and semantic collision detection."""

    from research import optimization_fixtures as of

    run = Path(run)
    entries = fresh_entries(run)
    index = of.existing_semantics({"old_development": range(800000, 800100),
                                   "model_development_pool": range(820000, 820200),
                                   "model_evaluation_pool": range(830000, 830400)})
    collisions = []
    seen: Dict[str, int] = {}
    for entry in entries:
        if entry["semantic_sha256"] in index:
            collisions.append({"seed": entry["seed"], "against": index[entry["semantic_sha256"]]})
        if entry["semantic_sha256"] in seen:
            collisions.append({"seed": entry["seed"], "against": f"fresh:{seen[entry['semantic_sha256']]}"})
        seen[entry["semantic_sha256"]] = entry["seed"]
    # The accepted owner's check: public/regression/additional/stress programs
    # and every retained historical extra-corpus manifest (full digests).
    from research import run_structural_experiments as rse

    for item in rse.heldout_collisions(entries):
        if item["kind"] != "internal":
            collisions.append({"seed": item["seed"], "against": item["against"],
                               "kind": item["kind"]})
    # Seeds used by any earlier retained result directory, by manifest.
    previously_used = []
    for manifest in sorted(oc.RESULTS.glob("*/inputs/heldout/*.json")):
        stem = manifest.stem
        if stem.startswith("seed_") and 810000 <= int(stem[5:]) <= 810199:
            previously_used.append(str(manifest.relative_to(oc.ROOT)))
    counts = oc.family_counts(entries)
    payload = {"cohort": "compiler_evaluation", "seeds": [810000, 810199],
               "family_counts": counts, "programs": entries, "collisions": collisions,
               "previously_used_seed_files": previously_used,
               "status": ("PASS" if not collisions and not previously_used and
                          all(n == 40 for n in counts.values()) and len(counts) == 5
                          else "BLOCKED"),
               "legality": "machine.validate_program + serial reference compile + every case",
               "exposure": "legality and collision checks only; no candidate outcome observed"}
    oc.write_immutable_json(run / "FRESH_COHORT.json", payload)
    return payload


def write_freeze(run: Path) -> dict:
    """FROZEN_SELECTION.json: everything fixed before any NEW evaluation outcome."""

    import tarfile

    run = Path(run)
    target = run / "FROZEN_SELECTION.json"
    if target.exists():
        raise FileExistsError("FROZEN_SELECTION.json is immutable")
    selection = selected_from(run)
    for part in ("search", "engineering", "ablation", "model"):
        if part not in selection:
            raise RuntimeError(f"development decision {part!r} is missing")
    fresh = json.loads((run / "FRESH_COHORT.json").read_text())
    if fresh["status"] != "PASS":
        raise RuntimeError("the fresh compiler cohort is blocked")
    manifests = {}
    for cohort in ("development", "evaluation"):
        path = run / "fixtures" / cohort / "MANIFEST.json"
        manifests[cohort] = {"path": str(path.relative_to(run)), "sha256": oc.file_sha256(path),
                             "status": json.loads(path.read_text())["status"]}
    frozen_dir = run / "SOURCE_MANIFESTS" / "frozen"
    frozen_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(frozen_dir / "research_source.tar", "x") as tar:
        for folder in ("research", "research_tests"):
            for path in sorted((oc.ROOT / folder).glob("*.py")):
                tar.add(path, arcname=f"{folder}/{path.name}")
    search = selection["search"]
    config = search["selected_config"]
    build = selection["engineering"]["adopted_build"] if config else None
    depth = selection["model"]["selected_depth"]
    h4_eligible = (manifests["evaluation"]["status"] == "PASS" and depth is not None)
    payload = {
        "protocol_id": "luminal-phase2-optimization-1.0",
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package_lock_sha256": oc.file_sha256(oc.PACKAGE / "LOCK.json"),
        "search": {"config": config, "build": build, "outcome": search["outcome"],
                   "arm": "selected_nonmodel", "optimisation_query_seconds": 0.1,
                   "aggregate_ceilings": {"nodes": 1_000_000, "validations": 100_000}},
        "model": {"selected_depth": depth, "h4_new_eligible_to_run": h4_eligible,
                  "evaluation_arms": ["empirical_cover", "selected_model", "one_bit",
                                      "uniform_bits x 10 seeds"],
                  "descriptive_depth1": depth == 2},
        "selection_files_sha256": {part: oc.file_sha256(run / "selection" / f"{part}.json")
                                   for part in ("search", "engineering", "ablation", "model")},
        "fixture_recipe_sha256": oc.file_sha256(oc.ROOT / "research" / "optimization_fixtures.py"),
        "fixture_manifests": manifests,
        "fresh_cohort": {"path": "FRESH_COHORT.json",
                         "sha256": oc.file_sha256(run / "FRESH_COHORT.json")},
        "sources": {"research": oc.research_source_hashes(),
                    "production": oc.production_source_hashes(),
                    "frozen_snapshot": oc.frozen_snapshot_hashes(),
                    "frozen_workspace_worker": oc.file_sha256(
                        frozen_workspace(run) / "optimization_frozen_worker.py"),
                    "source_tar_sha256": oc.file_sha256(frozen_dir / "research_source.tar")},
        "seeds": {"arm_order": SEED_ARM_ORDER, "fixture_split": 2026092402,
                  "bootstrap": 2026092403, "uniform_search": list(UNIFORM_SEEDS)},
        "controls": {"frozen_phase2": "accepted final_source_v2 structural_bound via the "
                                      "frozen workspace", "accepted_budgeted": "production v4",
                     "accepted_default": "production v4", "accepted_bootstrap": "production v4",
                     "classical": "common.classical_compile via the accepted isolated worker",
                     "serial": "machine.serial_compile (score denominator)"},
        "inference": {
            "primary": "mean paired log(J_frozen_phase2/J_selected_nonmodel) at 0.1 s on the "
                       "fresh cohort; repetitions within program; equal family weights; "
                       "family-stratified program bootstrap 10000 seed 2026092403; two-sided "
                       "95%; lower>0 improvement, upper<0 degradation, else INCONCLUSIVE",
            "H4_NEW": "selected_model vs one_bit and vs uniform_bits at 0.1 s; best_test_J = "
                      "min(min_training_J, validated new TEST objects); repetitions then "
                      "uniform seeds then fixtures, equal family weights; 97.5% bootstrap "
                      "(.0125/.9875) 10000 seed 2026092403; PASS iff all 30 fixtures accounted, "
                      ">=3 informative families, zero defects, both lower bounds > 0",
            "conditional_model_compiler": "only if H4_NEW passes: selected_model_compiler vs "
                                          "selected_nonmodel at 0.1 s, 95% interval",
            "public": "exact suite score per repetition; strict gain iff every paired ratio > "
                      "1+1e-12; descriptive",
            "runtime": "per-program median over repetitions, log ratio, family-weighted, "
                       "programs resampled within family"},
        "exposure": {"legality_and_oracle_qualification": "done before this freeze",
                     "new_candidate_outcomes_observed_on_evaluation_cohorts": False},
    }
    expected = {}
    arms, unbudgeted, budgeted = evaluation_arms(payload, model=False)
    entries = fresh["programs"]
    plan = schedule(entries, unbudgeted, budgeted, BUDGETS, 15)
    expected["D_fresh_compiler"] = [row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
    public = [{"program_sha256": e["program_sha256"], "family": "public", "seed": None}
              for e in public_cohort(run)]
    plan = schedule(public, unbudgeted + ["serial"], budgeted, BUDGETS, 15)
    expected["D_public"] = [row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
    if h4_eligible:
        fixtures = fixture_entries(run, "evaluation")
        labels = sorted(["empirical_cover", "selected_model", "one_bit"] +
                        [f"uniform_bits_{seed}" for seed in UNIFORM_SEEDS])
        plan = schedule(fixtures, [], labels, BUDGETS, 15)
        expected["C_model_evaluation"] = [row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
        if depth == 2:
            plan = schedule(fixtures, [], ["model_depth1_descriptive"], BUDGETS, 15)
            expected["C_model_evaluation_depth1_descriptive"] = [
                row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
        for stage, entries_c in (("D_fresh_model_compiler", entries), ("D_public_model_compiler",
                                                                        public)):
            plan = schedule(entries_c, [], ["selected_model_compiler"], BUDGETS, 15)
            expected[stage] = [row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
    expected_dir = run / "frozen_expected"
    payload["expected_matrices"] = {}
    for stage, keys in expected.items():
        digest = oc.write_immutable_json(expected_dir / f"{stage}.json",
                                         {"stage": stage, "count": len(keys), "keys": keys})
        payload["expected_matrices"][stage] = {"count": len(keys), "sha256": digest,
                                               "conditional": stage.endswith("model_compiler")}
    payload["expected_matrices"]["export_nonmodel"] = {"count": 624}
    oc.write_immutable_json(target, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", required=True,
                        choices=sorted(STAGES) + ["setup", "probe", "decide", "qualify",
                                                  "fresh_cohort", "freeze"])
    parser.add_argument("--part", choices=["search", "engineering", "ablation", "model",
                                           "development", "evaluation"])
    args = parser.parse_args(argv)
    # Absolute: workers run with the frozen workspace as their working
    # directory, where a relative path would silently resolve elsewhere.
    run = Path(args.run).resolve()
    if args.stage == "setup":
        report = setup_frozen_workspace(run)
        oc.write_json(run / "frozen_control_workspace.json", report)
        print(json.dumps({k: report[k] for k in ("status", "snapshot_mismatches",
                                                  "worker_equal_to_source")}))
        return 0 if report["status"] == "PASS" else 1
    if args.stage == "decide":
        payload = decide(run, args.part)
        brief = {k: payload.get(k) for k in ("outcome", "selected_config", "adopted_build",
                                             "selected_depth", "best_effect_0.1",
                                             "tie_group_at_best")}
        print(json.dumps(brief))
        return 0
    if args.stage == "freeze":
        payload = write_freeze(run)
        print(json.dumps({"search": payload["search"], "model": payload["model"],
                          "expected": payload["expected_matrices"]}))
        return 0
    if args.stage == "qualify":
        manifest = qualify(run, args.part)
        print(json.dumps({k: manifest[k] for k in ("cohort", "status", "filled",
                                                    "collision_block")}))
        return 0 if manifest["status"] == "PASS" else 1
    if args.stage == "fresh_cohort":
        payload = freeze_fresh_cohort(run)
        print(json.dumps({k: payload[k] for k in ("status", "family_counts", "collisions",
                                                   "previously_used_seed_files")}))
        return 0 if payload["status"] == "PASS" else 1
    if args.stage == "probe":
        report = isolation_probe(run)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        oc.write_json(run / "isolation" / f"probe_{stamp}.json", report)
        print(json.dumps({k: report[k] for k in ("status", "frozen_research_from_snapshot",
                                                  "frozen_production_protected")}))
        return 0 if report["status"] == "PASS" else 1
    matrix = STAGES[args.stage](run)
    summary = matrix.run_all()
    print(json.dumps(summary))
    return 0 if summary["missing"] == 0 and summary["sources_unchanged_during_stage"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
