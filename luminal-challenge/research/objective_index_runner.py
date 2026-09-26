"""Orchestration of the objective-index protocol 1.0: corpora, matrices, journals.

This module launches workers; it measures nothing itself. Every measured row
comes from a fresh subprocess:

- ``research.objective_index_worker`` for A1-A4 (and the conditional learned
  pair), current research source;
- ``optimization_frozen_worker.py`` inside the frozen-control workspace for A0
  (accepted ``final_source_v2`` ``structural_bound``), the accepted direct arms,
  classical and serial. The workspace and its worker are the earlier release's
  owners (``optimization_runner.setup_frozen_workspace``), reused unchanged;
- ``research.objective_index_ranker_worker`` for fixture ranker rows.

Cell order (section 9): within each (program, repetition) block, arm/budget
cells are sorted by ``stable_seed([2026092505, program digest, repetition, arm,
budget])``, ties broken lexicographically. Rows and commands are appended and
fsynced one at a time; resume re-runs only keys with no row, and only under an
identical stage manifest.

Usage::

    PYTHONPATH=.reference:. python -m research.objective_index_runner --run DIR --stage STAGE
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time
from typing import Dict, List, Optional, Sequence, Tuple

from research import objective_index_common as oic
from research import optimization_common as oc
from research import optimization_runner as orun


WORKER_TIMEOUT = oic.EXTERNAL_SECONDS
BUDGETS = oic.BUDGETS
FROZEN_LABELS = {"A0_frozen_phase2": "frozen_phase2", "accepted_budgeted": "accepted_budgeted",
                 "accepted_default": "accepted_default",
                 "accepted_bootstrap": "accepted_bootstrap", "classical": "classical",
                 "serial": "serial"}
RANKER_ARMS = ("tree", "ascending", "hamming", "shuffled_tree", "empirical_cover") + tuple(
    f"random_{tag}" for tag in oic.RANDOM_ORDER_SEEDS)

# Files imported by NEW compiler workers; a change after a stage starts
# invalidates pooling with that stage's earlier rows.
COMPILER_SOURCES = (
    "research/__init__.py", "research/optimization_common.py",
    "research/objective_index_common.py", "research/objective_index_search.py",
    "research/objective_index_worker.py", "research/optimization_frozen_worker.py",
    "research/run_structural_experiments.py", "research/structural_encoding.py",
    "research/structural_search.py", "research/structural_oracle.py",
    "research/structural_evidence.py", "research/physical_probes.py",
    "research/classical_measurement_worker.py",
)
# The conditional learned pair additionally imports these.
LEARNED_SOURCES = COMPILER_SOURCES + (
    "research/objective_index_learned.py", "research/schema_ranker.py",
    "research/optimization_models.py", "research/optimization_search.py",
    "research/structural_models.py",
)
RANKER_SOURCES = (
    "research/__init__.py", "research/optimization_common.py",
    "research/objective_index_common.py", "research/schema_ranker.py",
    "research/objective_index_ranker_worker.py", "research/optimization_models.py",
    "research/optimization_search.py", "research/structural_models.py",
    "research/run_structural_experiments.py", "research/structural_encoding.py",
    "research/structural_search.py", "research/structural_oracle.py",
    "research/structural_evidence.py", "research/physical_probes.py",
    "research/objective_index_fixtures.py", "research/optimization_fixtures.py",
)


# --------------------------------------------------------------------------
# Arms, keys and cell order
# --------------------------------------------------------------------------


def compiler_arm(label: str, learned: Optional[str] = None, solver: Optional[str] = None) -> dict:
    if label in FROZEN_LABELS:
        return {"label": label, "worker": "frozen", "frozen_label": FROZEN_LABELS[label]}
    return {"label": label, "worker": "objective", "solver_arm": solver or label,
            "learned": learned}


def ranker_arm(label: str) -> dict:
    if label.startswith("random_"):
        return {"label": label, "worker": "ranker", "learner_arm": "random",
                "random_tag": int(label.split("_", 1)[1])}
    return {"label": label, "worker": "ranker", "learner_arm": label, "random_tag": None}


def row_key(entry_id: str, arm: str, budget, repetition: int) -> str:
    return f"{entry_id}|{arm}|{budget}|{repetition}"


def entry_id(entry: dict) -> str:
    return entry.get("fixture_id") or entry["program_sha256"]


def schedule(entries: Sequence[dict], cells: Sequence[Tuple[str, object]], repetitions: int
             ) -> List[Tuple[dict, object, int, str]]:
    """Programs in manifest order, repetitions ascending, cells by stable hash."""

    out = []
    for entry in entries:
        ident = entry_id(entry)
        for repetition in range(repetitions):
            keyed = sorted(
                ((oic.stable_seed([oic.SEED_ARM_ORDER, ident, repetition, arm, budget]),
                  arm, "" if budget is None else str(budget)), arm, budget)
                for arm, budget in cells)
            for _, arm, budget in keyed:
                out.append((entry, budget, repetition, arm))
    return out


def cells_for(unbudgeted: Sequence[str], budgeted: Sequence[str],
              budgets: Sequence[object] = BUDGETS) -> List[Tuple[str, object]]:
    return [(arm, None) for arm in unbudgeted] + [(arm, b) for arm in budgeted for b in budgets]


def stage_manifest(stage: str, extra: dict, sources: Sequence[str]) -> dict:
    missing = [name for name in sources if oc.file_sha256(oc.ROOT / name) is None]
    if missing:
        raise RuntimeError(f"measured sources missing: {missing}")
    payload = {"stage": stage, "protocol_id": oic.PROTOCOL_ID,
               "measured_sources": {name: oc.file_sha256(oc.ROOT / name) for name in sources},
               "production": oc.production_source_hashes(),
               "frozen_snapshot": oc.frozen_snapshot_hashes(),
               "python": sys.version, "executable": oc.PYTHON, "extra": extra}
    payload["manifest_sha256"] = oc.object_sha256(payload)
    return payload


# --------------------------------------------------------------------------
# Commands
# --------------------------------------------------------------------------


def arm_command(run: Path, stage: str, corpus: str, entry: dict, arm: dict, budget,
                repetition: int) -> Tuple[List[str], dict, Path]:
    worker = arm["worker"]
    if worker == "objective":
        spec = {"kind": "objective_index_measurement", "program_path": entry["program_path"],
                "program_sha256": entry["program_sha256"], "arm": arm["label"],
                "solver_arm": arm["solver_arm"], "learned": arm.get("learned"),
                "budget_seconds": budget, "repetition": repetition, "stage": stage,
                "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.objective_index_worker", "--spec", oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker == "frozen":
        inner_arm = {"label": arm["frozen_label"], "worker": "frozen",
                     "inner_arm": {"frozen_phase2": "structural_bound"}.get(
                         arm["frozen_label"], arm["frozen_label"])}
        return orun.arm_command(run, stage, corpus, entry, inner_arm, budget, repetition)
    if worker == "ranker":
        spec = {"kind": "objective_index_ranker_measurement", "fixture_dir": entry["fixture_dir"],
                "fixture_id": entry["fixture_id"], "family": entry["family"],
                "program_sha256": entry["program_sha256"],
                "expected_sha256": entry["expected_sha256"], "arm": arm["label"],
                "learner_arm": arm["learner_arm"], "random_tag": arm.get("random_tag"),
                "budget_seconds": budget, "repetition": repetition, "stage": stage,
                "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.objective_index_ranker_worker", "--spec",
                oc.canonical(spec)]
        return argv, spec, oc.ROOT
    raise ValueError(f"unknown worker {worker!r}")


# --------------------------------------------------------------------------
# Matrix engine
# --------------------------------------------------------------------------


class Matrix:
    """One stage's expected keys, cell order, journal and resume ownership."""

    def __init__(self, run: Path, stage: str, corpus: str, entries: Sequence[dict],
                 arms: Dict[str, dict], cells: Sequence[Tuple[str, object]], repetitions: int,
                 sources: Sequence[str], extra: Optional[dict] = None,
                 freeze_sha256: Optional[str] = None) -> None:
        self.run = Path(run).resolve()
        self.stage = stage
        self.corpus = corpus
        self.entries = list(entries)
        self.arms = arms
        self.cells = list(cells)
        self.repetitions = repetitions
        self.freeze_sha256 = freeze_sha256
        self.dir = self.run / "stages" / stage
        self.dir.mkdir(parents=True, exist_ok=True)
        self.rows_path = self.dir / "rows.jsonl"
        self.commands_path = self.dir / "commands.jsonl"
        self.plan = schedule(self.entries, self.cells, repetitions)
        self.expected = [row_key(entry_id(e), a, b, r) for e, b, r, a in self.plan]
        extra = dict(extra or {}, corpus=corpus, arms=arms,
                     cells=[[a, b] for a, b in self.cells], repetitions=repetitions,
                     programs=[{k: e.get(k) for k in ("seed", "family", "program_sha256",
                                                       "file_sha256", "fixture_id",
                                                       "expected_sha256")}
                               for e in self.entries],
                     freeze_sha256=freeze_sha256, order_seed=oic.SEED_ARM_ORDER)
        self.manifest = stage_manifest(stage, extra, sources)

    def write_expected(self) -> None:
        path = self.dir / "EXPECTED_KEYS.json"
        payload = {"stage": self.stage, "count": len(self.expected), "keys": self.expected,
                   "order_seed": oic.SEED_ARM_ORDER}
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
                    "resume is refused. Preserve these rows as superseded and start afresh.")
            return
        oc.write_immutable_json(path, self.manifest)

    def done_keys(self) -> set:
        return {row["key"] for row in oc.read_rows(self.rows_path)}

    def run_all(self, progress_every: int = 1000) -> dict:
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
        end_sources = {name: oc.file_sha256(oc.ROOT / name)
                       for name in self.manifest["measured_sources"]}
        unchanged = end_sources == self.manifest["measured_sources"]
        rows = oc.read_rows(self.rows_path)
        summary = {"stage": self.stage, "sources_unchanged_during_stage": unchanged,
                   "expected": len(self.expected), "observed": len(done),
                   "missing": len(set(self.expected) - done),
                   "failed": sum(1 for r in rows if r["failed_row"])}
        oc.append_row(self.dir / "resume_log.jsonl", dict(summary, event="end",
                      utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())))
        return summary

    def run_one(self, entry: dict, budget, repetition: int, arm_label: str) -> dict:
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
               "fixture_id": entry.get("fixture_id"), "seed": entry.get("seed"),
               "arm": arm_label, "budget_seconds": budget, "repetition": repetition,
               "exit_code": code, "timed_out": timed_out, "process_seconds": process_seconds,
               "stderr_tail": stderr[-4000:], "stdout_bytes": len(stdout),
               "started_utc": stamp, "manifest_sha256": self.manifest["manifest_sha256"],
               "freeze_sha256": self.freeze_sha256}
        parsed = None
        if not timed_out and code == 0 and stdout.strip():
            try:
                parsed = json.loads(stdout.strip().splitlines()[-1])
            except json.JSONDecodeError as exc:
                row["failure"] = f"stdout was not one JSON object: {exc}"
        if parsed is not None and str(parsed.get("kind", "")).endswith("_result"):
            result = {k: v for k, v in parsed.items() if k != "kind"}
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
            "started_utc": stamp, "stdout_sha256": oc.sha256_bytes(stdout.encode())})
        oc.append_row(self.rows_path, row)
        return row


# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------


def development_entries(run: Path) -> List[dict]:
    return orun.generated_cohort(run, "development", *oic.COHORTS["development"])


def fresh_entries(run: Path) -> List[dict]:
    return orun.generated_cohort(run, "compiler_evaluation", *oic.COHORTS["compiler_evaluation"])


def public_entries(run: Path) -> List[dict]:
    return orun.public_cohort(run)


def fixture_entries(run: Path, cohort: str) -> List[dict]:
    manifest = json.loads((Path(run) / "fixtures" / cohort / "MANIFEST.json").read_text())
    if manifest["status"] != "PASS" or manifest["collision_block"]:
        raise RuntimeError(f"{cohort} fixtures are {manifest['status']}; stage blocked")
    entries = []
    for fixture in manifest["fixtures"]:
        directory = Path(run).resolve() / "fixtures" / cohort / fixture["fixture_id"]
        entries.append({"fixture_id": fixture["fixture_id"], "family": fixture["family"],
                        "seed": fixture["seed"], "program_sha256": fixture["program_sha256"],
                        "fixture_dir": str(directory),
                        "expected_sha256": {"record": fixture["record_sha256"],
                                            "oracle": fixture["oracle_sha256"],
                                            "split": fixture["split_sha256"]}})
    return entries


def load_freeze(run: Path) -> Tuple[dict, str]:
    path = Path(run) / "FROZEN_SELECTION.json"
    return json.loads(path.read_text()), oc.file_sha256(path)


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------

SOLVER_ARMS = oic.ARMS  # A0..A4


def stage_dev_compiler(run: Path) -> Matrix:
    arms = {label: compiler_arm(label) for label in SOLVER_ARMS + ("accepted_budgeted",
                                                                    "classical")}
    cells = cells_for(["classical"], list(SOLVER_ARMS) + ["accepted_budgeted"])
    return Matrix(run, "DEV_compiler", "development", development_entries(run), arms, cells, 3,
                  COMPILER_SOURCES)


def stage_dev_model(run: Path) -> Matrix:
    arms = {label: ranker_arm(label) for label in RANKER_ARMS}
    return Matrix(run, "DEV_model", "model_development", fixture_entries(run, "development"),
                  arms, cells_for([], RANKER_ARMS), 3, RANKER_SOURCES)


def stage_eval_model(run: Path) -> Matrix:
    _, digest = load_freeze(run)
    arms = {label: ranker_arm(label) for label in RANKER_ARMS}
    return Matrix(run, "EVAL_model_wall", "model_evaluation", fixture_entries(run, "evaluation"),
                  arms, cells_for([], RANKER_ARMS), 15, RANKER_SOURCES, freeze_sha256=digest)


def stage_eval_model_work(run: Path) -> Matrix:
    _, digest = load_freeze(run)
    arms = {label: ranker_arm(label) for label in RANKER_ARMS}
    return Matrix(run, "EVAL_model_work", "model_evaluation", fixture_entries(run, "evaluation"),
                  arms, cells_for([], RANKER_ARMS, ["fixed_work"]), 1, RANKER_SOURCES,
                  freeze_sha256=digest)


EVAL_UNBUDGETED = ("accepted_bootstrap", "accepted_default", "classical")
EVAL_BUDGETED = ("accepted_budgeted",) + SOLVER_ARMS


def stage_eval_compiler(run: Path) -> Matrix:
    frozen, digest = load_freeze(run)
    entries = json.loads((Path(run) / "FRESH_COHORT.json").read_text())["programs"]
    arms = {label: compiler_arm(label) for label in EVAL_UNBUDGETED + EVAL_BUDGETED}
    return Matrix(run, "EVAL_compiler", "compiler_evaluation", entries, arms,
                  cells_for(EVAL_UNBUDGETED, EVAL_BUDGETED), 15, COMPILER_SOURCES,
                  freeze_sha256=digest)


def stage_eval_public(run: Path) -> Matrix:
    frozen, digest = load_freeze(run)
    arms = {label: compiler_arm(label) for label in EVAL_UNBUDGETED + EVAL_BUDGETED}
    return Matrix(run, "EVAL_public", "public", public_entries(run), arms,
                  cells_for(EVAL_UNBUDGETED, EVAL_BUDGETED), 15, COMPILER_SOURCES,
                  freeze_sha256=digest)


def stage_eval_public_serial(run: Path) -> Matrix:
    frozen, digest = load_freeze(run)
    arms = {"serial": compiler_arm("serial")}
    return Matrix(run, "EVAL_public_serial", "public", public_entries(run), arms,
                  cells_for(["serial"], []), 15, COMPILER_SOURCES, freeze_sha256=digest)


def _learned_stage(run: Path, labels_mode: str) -> Matrix:
    frozen, digest = load_freeze(run)
    if not frozen.get("learning", {}).get("conditional_compiler_authorised_by_gate"):
        gate = json.loads((Path(run) / "LEARNING.json").read_text())
        if gate.get("H_LEARN", {}).get("verdict") != "PASS":
            raise RuntimeError("H_LEARN did not pass: the learned compiler pair is BLOCKED")
    selected = frozen["selection"]["selected_arm"]
    label = f"learned_{labels_mode}"
    arms = {label: compiler_arm(label, learned=labels_mode, solver=selected)}
    entries = (json.loads((Path(run) / "FRESH_COHORT.json").read_text())["programs"]
               + public_entries(run))
    return Matrix(run, f"EVAL_learned_{labels_mode}", "compiler_evaluation_and_public",
                  entries, arms, cells_for([], [label]), 15, LEARNED_SOURCES,
                  freeze_sha256=digest)


STAGES = {
    "DEV_compiler": stage_dev_compiler,
    "DEV_model": stage_dev_model,
    "EVAL_model_wall": stage_eval_model,
    "EVAL_model_work": stage_eval_model_work,
    "EVAL_compiler": stage_eval_compiler,
    "EVAL_public": stage_eval_public,
    "EVAL_public_serial": stage_eval_public_serial,
    "EVAL_learned_tree": lambda run: _learned_stage(run, "tree"),
    "EVAL_learned_shuffled_tree": lambda run: _learned_stage(run, "shuffled_tree"),
}


# --------------------------------------------------------------------------
# Setup, isolation, fresh cohort
# --------------------------------------------------------------------------


def isolation_probe(run: Path) -> dict:
    """Frozen-worker isolation (owner's probe) plus our workers' actual imports."""

    report = orun.isolation_probe(run)
    code = (
        "import sys, json, hashlib\n"
        f"sys.path[:0] = [{str(oc.ROOT / '.reference')!r}, {str(oc.ROOT)!r}]\n"
        "import research.objective_index_worker, research.objective_index_ranker_worker\n"
        "out = {}\n"
        "for n, m in sorted(sys.modules.items()):\n"
        "    f = getattr(m, '__file__', None)\n"
        "    if f and (n == 'research' or n.startswith('research.') or n in ('machine',"
        "'direct_compiler','direct_contract','direct_optimizer','direct_constraints',"
        "'schema_index','compare_direct')):\n"
        "        out[n] = {'path': f, 'sha256': hashlib.sha256(open(f,'rb').read()).hexdigest()}\n"
        "print(json.dumps(out))\n")
    proc = subprocess.run([oc.PYTHON, "-c", code], cwd=str(oc.ROOT), capture_output=True,
                          text=True, env={"PATH": os.environ.get("PATH", "")})
    modules = json.loads(proc.stdout) if proc.returncode == 0 else None
    report["objective_workers"] = {"exit_code": proc.returncode, "stderr": proc.stderr[-2000:],
                                   "modules": modules}
    workspace = str(orun.frozen_workspace(run))
    ok = modules is not None and not any(entry["path"].startswith(workspace)
                                         for entry in modules.values())
    report["objective_workers_use_current_source"] = ok
    report["status"] = "PASS" if report["status"] == "PASS" and ok else "FAIL"
    return report


def freeze_fresh_cohort(run: Path) -> dict:
    """Reference-only legality and semantic disjointness of seeds 910000-910199."""

    from research import objective_index_fixtures as oif
    from research import run_structural_experiments as rse

    run = Path(run)
    entries = fresh_entries(run)
    index = oif.collision_index({
        "old_development": range(800000, 800100),
        "old_fresh_compiler": range(810000, 810200),
        "old_fixture_development_pool": range(820000, 820200),
        "old_fixture_evaluation_pool": range(830000, 830400),
        "fixture_development_pool": range(920000, 920200),
        "fixture_evaluation_pool": range(930000, 930400)})
    collisions = []
    seen: Dict[str, int] = {}
    for entry in entries:
        if entry["semantic_sha256"] in index:
            collisions.append({"seed": entry["seed"], "against": index[entry["semantic_sha256"]]})
        if entry["semantic_sha256"] in seen:
            collisions.append({"seed": entry["seed"],
                               "against": f"fresh:{seen[entry['semantic_sha256']]}"})
        seen[entry["semantic_sha256"]] = entry["seed"]
    for item in rse.heldout_collisions(entries):
        if item["kind"] != "internal":
            collisions.append({"seed": item["seed"], "against": item["against"],
                               "kind": item["kind"]})
    previously_used = []
    first, last = oic.COHORTS["compiler_evaluation"]
    for manifest in sorted(oc.RESULTS.glob("*/inputs/*/*.json")):
        if manifest.is_relative_to(run.resolve()):
            continue
        stem = manifest.stem
        if stem.startswith("seed_") and first <= int(stem[5:]) <= last:
            previously_used.append(str(manifest.relative_to(oc.ROOT)))
    counts = oc.family_counts(entries)
    payload = {"cohort": "compiler_evaluation", "seeds": [first, last], "family_counts": counts,
               "programs": entries, "collisions": collisions,
               "previously_used_seed_files": previously_used,
               "status": ("PASS" if not collisions and not previously_used and
                          all(n == 40 for n in counts.values()) and len(counts) == 5
                          else "BLOCKED"),
               "legality": "machine.validate_program + serial reference compile + every case",
               "exposure": "legality and collision checks only; no candidate outcome observed"}
    oc.write_immutable_json(run / "FRESH_COHORT.json", payload)
    return payload


def decide(run: Path) -> dict:
    """DEVELOPMENT.json: the fixed selection rule, ablations and sensitivity."""

    from research import objective_index_analysis as oia

    run = Path(run)
    target = run / "DEVELOPMENT.json"
    if target.exists():
        raise FileExistsError("DEVELOPMENT.json is written once")
    stage = run / "stages" / "DEV_compiler"
    rows = oc.read_rows(stage / "rows.jsonl")
    expected = json.loads((stage / "EXPECTED_KEYS.json").read_text())["keys"]
    selection = oia.select_arm(rows, expected)
    selected = selection["selected_arm"]
    payload = {
        "protocol_id": oic.PROTOCOL_ID,
        "population": "development seeds 800000-800099 (100 programs), 3 repetitions; public "
                      "programs never enter selection",
        "selection": selection,
        "ablations": oia.ablations(rows, 3),
        "versus_controls_descriptive": {
            f"{control}@{budget}": oia.quality(rows, control, selected, budget,
                                               oic.PRIMARY_BUDGET, 3, oia.DESCRIPTIVE)
            for control, budget in (("A0_frozen_phase2", 0.1), ("accepted_budgeted", 0.1),
                                    ("classical", None))},
        "sensitivity": oia.sensitivity(rows, selected,
                                       [("A0_frozen_phase2", 0.1), ("accepted_budgeted", 0.1),
                                        ("classical", None)]),
        "rows_sha256": oc.file_sha256(stage / "rows.jsonl"),
        "decided_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    oc.write_immutable_json(target, payload)
    return payload


def write_freeze(run: Path) -> dict:
    """FROZEN_SELECTION.json: everything fixed before any evaluation outcome."""

    import tarfile

    run = Path(run)
    target = run / "FROZEN_SELECTION.json"
    if target.exists():
        raise FileExistsError("FROZEN_SELECTION.json is immutable")
    development = json.loads((run / "DEVELOPMENT.json").read_text())
    fresh = json.loads((run / "FRESH_COHORT.json").read_text())
    if fresh["status"] != "PASS":
        raise RuntimeError("the fresh compiler cohort is blocked")
    manifests = {}
    for cohort in ("development", "evaluation"):
        path = run / "fixtures" / cohort / "MANIFEST.json"
        manifests[cohort] = json.loads(path.read_text())
    headroom = [f["fixture_id"] for f in manifests["evaluation"]["fixtures"]
                if f["test_headroom_objects"] > 0]
    frozen_dir = run / "SOURCE_MANIFESTS" / "frozen"
    frozen_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(frozen_dir / "research_source.tar", "x") as tar:
        for folder in ("research", "research_tests"):
            for path in sorted((oc.ROOT / folder).glob("*.py")):
                tar.add(path, arcname=f"{folder}/{path.name}")
    inputs = {}
    for label, relative in (
            ("development", "DEVELOPMENT.json"), ("fresh_cohort", "FRESH_COHORT.json"),
            ("fixtures_development", "fixtures/development/MANIFEST.json"),
            ("fixtures_evaluation", "fixtures/evaluation/MANIFEST.json"),
            ("pruning_validation", "PRUNING_VALIDATION.json"),
            ("dev_compiler_rows", "stages/DEV_compiler/rows.jsonl"),
            ("dev_model_rows", "stages/DEV_model/rows.jsonl")):
        inputs[label] = {"path": relative, "sha256": oc.file_sha256(run / relative)}
    selection = development["selection"]
    payload = {
        "protocol_id": oic.PROTOCOL_ID,
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package_lock_sha256": oc.file_sha256(oic.PACKAGE / "LOCK.json"),
        "selection": {"selected_arm": selection["selected_arm"],
                      "selected_effect_vs_A0_at_0.1": selection["selected_effect"],
                      "tie_group": selection["tie_group"],
                      "selected_non_model_is_alias_of": selection["selected_arm"],
                      "optimisation_query_seconds": 0.1,
                      "aggregate_ceilings": {"nodes": 1_000_000, "validations": 100_000}},
        "learning": {
            "ranker": "depth-3 exact-Gini schema tree over structural_rank bits; min child 4; "
                      "leaf (pos+1)/(n+2); labels at ceil(0.1 n)-th training order statistic",
            "arms": list(RANKER_ARMS),
            "design_diagnostic_from_oracle_only": {
                "evaluation_fixtures_with_a_test_object_below_training_minimum": len(headroom),
                "of": len(manifests["evaluation"]["fixtures"]),
                "consequence": ("best_test_J equals min_training_J for every arm on every "
                                "fixture with no such object; if the count is 0 every H_LEARN "
                                "contrast is identically 0 and H_LEARN cannot pass")},
            "conditional_compiler_authorised_by_gate": False,
            "conditional_compiler_rule": "EVAL_learned_tree and EVAL_learned_shuffled_tree run "
                                         "only if LEARNING.json H_LEARN verdict is PASS"},
        "sources": {"research": oc.research_source_hashes(),
                    "production": oc.production_source_hashes(),
                    "frozen_snapshot": oc.frozen_snapshot_hashes(),
                    "frozen_workspace_worker": oc.file_sha256(
                        orun.frozen_workspace(run) / "optimization_frozen_worker.py"),
                    "source_tar_sha256": oc.file_sha256(frozen_dir / "research_source.tar")},
        "inputs": inputs,
        "seeds": {"arm_order": oic.SEED_ARM_ORDER, "pool": oic.SEED_POOL,
                  "shuffled_labels": oic.SEED_SHUFFLED, "split": oic.SEED_SPLIT,
                  "bootstrap": oic.SEED_BOOTSTRAP, "random_order": list(oic.RANDOM_ORDER_SEEDS)},
        "controls": {"A0_frozen_phase2": "accepted final_source_v2 structural_bound (cap 32) via "
                                         "the frozen workspace",
                     "accepted_budgeted": "production v4 budgeted",
                     "accepted_default": "production v4 default",
                     "accepted_bootstrap": "production v4 bootstrap",
                     "classical": "common.classical_compile via the accepted isolated worker",
                     "serial": "machine.serial_compile (public score denominator)"},
        "inference": {
            "primary": "selected vs A0_frozen_phase2, accepted_budgeted and classical at 0.1 s "
                       "on the 200 fresh programs: paired log(J_control/J_selected), repetitions "
                       "averaged inside program, equal family weights; 10,000 program-within-"
                       "family resamples seed 2026092504; Bonferroni percentiles 1/120 and "
                       "119/120; 'best average output quality among these three controls at "
                       "this budget on this population' iff all three lower bounds > 0",
            "descriptive": "adjacent ladder steps, other budgets, default/bootstrap: unadjusted "
                           "95% intervals",
            "runtime": "per-program median over repetitions, log ratio, family weighted, same "
                       "bootstrap; speed claim only if the interval lies below one",
            "H_LEARN": "tree vs hamming, random (10 seeds) and shuffled_tree at 0.1 s; "
                       "best_test_J; repetitions then seeds inside fixture; equal family weights; "
                       "Bonferroni 1/120, 119/120; PASS iff all three lower bounds > 0 with "
                       "complete 30-fixture membership and zero defects",
            "conditional_learned": "only if H_LEARN passes: learned_tree vs selected and vs "
                                   "learned_shuffled_tree at 0.1 s, percentiles 0.0125/0.9875",
            "public": "sqrt(GM(C_serial/C_arm)*GM(S_serial/S_arm)) per repetition; strict "
                      "fixed-suite gain iff every paired ratio > 1+1e-12"},
        "exposure": {"legality_and_oracle_qualification": "done before this freeze",
                     "evaluation_candidate_outcomes_observed": False},
    }
    expected = {}
    fixtures = fixture_entries(run, "evaluation")
    expected["EVAL_model_wall"] = schedule(fixtures, cells_for([], RANKER_ARMS), 15)
    expected["EVAL_model_work"] = schedule(fixtures, cells_for([], RANKER_ARMS, ["fixed_work"]), 1)
    expected["EVAL_compiler"] = schedule(fresh["programs"],
                                         cells_for(EVAL_UNBUDGETED, EVAL_BUDGETED), 15)
    public = public_entries(run)
    expected["EVAL_public"] = schedule(public, cells_for(EVAL_UNBUDGETED, EVAL_BUDGETED), 15)
    expected["EVAL_public_serial"] = schedule(public, cells_for(["serial"], []), 15)
    for mode in ("tree", "shuffled_tree"):
        expected[f"EVAL_learned_{mode}"] = schedule(fresh["programs"] + public,
                                                    cells_for([], [f"learned_{mode}"]), 15)
    payload["expected_matrices"] = {}
    for stage, plan in expected.items():
        keys = [row_key(entry_id(e), a, b, r) for e, b, r, a in plan]
        digest = oc.write_immutable_json(run / "frozen_expected" / f"{stage}.json",
                                         {"stage": stage, "count": len(keys), "keys": keys})
        payload["expected_matrices"][stage] = {"count": len(keys), "sha256": digest,
                                               "conditional": stage.startswith("EVAL_learned")}
    payload["expected_matrices"]["export_nonmodel"] = {"count": 624}
    oc.write_immutable_json(target, payload)
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", required=True,
                        choices=sorted(STAGES) + ["setup", "probe", "fresh_cohort", "decide",
                                                  "freeze"])
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    if args.stage == "setup":
        report = orun.setup_frozen_workspace(run)
        oc.write_json(run / "frozen_control_workspace.json", report)
        print(json.dumps({k: report[k] for k in ("status", "snapshot_mismatches",
                                                  "worker_equal_to_source")}))
        return 0 if report["status"] == "PASS" else 1
    if args.stage == "probe":
        report = isolation_probe(run)
        stamp = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime())
        oc.write_json(run / "isolation" / f"probe_{stamp}.json", report)
        print(json.dumps({k: report[k] for k in ("status", "frozen_research_from_snapshot",
                                                  "frozen_production_protected",
                                                  "objective_workers_use_current_source")}))
        return 0 if report["status"] == "PASS" else 1
    if args.stage == "decide":
        payload = decide(run)
        print(json.dumps({k: payload["selection"][k] for k in ("selected_arm", "best_effect",
                                                                "tie_group")}))
        return 0
    if args.stage == "freeze":
        payload = write_freeze(run)
        print(json.dumps({"selection": payload["selection"],
                          "expected": payload["expected_matrices"]}))
        return 0
    if args.stage == "fresh_cohort":
        payload = freeze_fresh_cohort(run)
        print(json.dumps({k: payload[k] for k in ("status", "family_counts", "collisions",
                                                   "previously_used_seed_files")}))
        return 0 if payload["status"] == "PASS" else 1
    matrix = STAGES[args.stage](run)
    summary = matrix.run_all()
    print(json.dumps(summary))
    return 0 if summary["missing"] == 0 and summary["sources_unchanged_during_stage"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
