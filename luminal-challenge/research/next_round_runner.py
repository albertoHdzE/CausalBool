"""Orchestration of the Phase 2 next round (protocol 1.0): corpora, matrices, journals.

Launches workers; measures nothing itself. Every measured row comes from a
fresh subprocess:

- ``research.next_round_worker`` -- the four ablation cells of the SUCCESSOR
  solver (``next_round_search``), and after Stage E the engineering variant;
- ``research.optimization_worker`` -- the earlier ``cap512_wider`` optimizer,
  unchanged, with its frozen spec (config ``cap512_wider``, build ``cached``,
  search arm ``structural_bound``), through ``optimization_runner.arm_command``;
- ``optimization_frozen_worker.py`` in this run's frozen-control workspace --
  classical, the accepted direct bootstrap and serial (unchanged owners);
- ``research.next_round_profile`` -- separate profiling runs (never timing rows).

Why a Matrix class here rather than the earlier runners' Matrix: those owners
are frozen, hard-code their own protocol's arm-order seed and protocol id, and
cannot charge this round's 24-hour measurement ledger. This one restates their
journal discipline (append + fsync per row, resume only missing keys under an
identical stage manifest) and adds the ledger check before every launch.

Cell order: within each (program, repetition) block, cells are sorted by
``stable_seed([2026092601, program_sha256, repetition, arm_id, budget_or_null])``
(PROTOCOL.json ``seed_keys.arm_order``), ties broken by (arm, budget text).

Usage::

    PYTHONPATH=.reference:. python -m research.next_round_runner --run DIR --stage STAGE
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

from research import next_round_common as nrc
from research import optimization_common as oc
from research import optimization_runner as orun


WORKER_TIMEOUT = nrc.EXTERNAL_SECONDS
WORK_LIMITS = (1_000, 10_000, 50_000)

# Files imported by this round's workers. A change after a stage starts
# refuses resume (stage manifest) and is reported at stage end.
MEASURED_SOURCES = (
    "research/__init__.py", "research/optimization_common.py",
    "research/objective_index_common.py", "research/next_round_common.py",
    "research/next_round_search.py", "research/next_round_worker.py",
    "research/optimization_search.py", "research/optimization_worker.py",
    "research/optimization_frozen_worker.py", "research/run_structural_experiments.py",
    "research/structural_encoding.py", "research/structural_search.py",
    "research/structural_models.py", "research/structural_oracle.py",
    "research/structural_evidence.py", "research/physical_probes.py",
    "research/classical_measurement_worker.py",
)


# --------------------------------------------------------------------------
# Arms, keys and cell order
# --------------------------------------------------------------------------


def cell_arm(label: str, variant: Optional[str] = None) -> dict:
    cell = nrc.CELLS[label] if variant is None else nrc.CELLS[label.split("+", 1)[0]]
    return {"label": label, "worker": "next", "catalog": cell["catalog"],
            "traversal": cell["traversal"], "variant": variant}


def earlier_arm() -> dict:
    return dict(orun.new_arm(nrc.EARLIER, nrc.EARLIER_SPEC["config"], nrc.EARLIER_SPEC["build"],
                             nrc.EARLIER_SPEC["search_arm"], nrc.EARLIER_SPEC["model_depth"]))


def frozen_arm(label: str) -> dict:
    return orun.frozen_arm(label)


def profile_arm(label: str) -> dict:
    return {"label": label, "worker": "profile", "target": label}


def row_key(program_sha256: str, arm: str, budget, repetition: int) -> str:
    return f"{program_sha256}|{arm}|{budget}|{repetition}"


def order_key(program_sha256: str, repetition: int, arm: str, budget) -> tuple:
    return (nrc.stable_seed([nrc.SEED_ARM_ORDER, program_sha256, repetition, arm, budget]),
            arm, "" if budget is None else str(budget))


def schedule(entries: Sequence[dict], cells: Sequence[Tuple[str, object]], repetitions: int
             ) -> List[Tuple[dict, object, int, str]]:
    """Programs in manifest order, repetitions ascending, cells by stable hash."""

    out = []
    for entry in entries:
        for repetition in range(repetitions):
            for arm, budget in sorted(cells, key=lambda c: order_key(
                    entry["program_sha256"], repetition, c[0], c[1])):
                out.append((entry, budget, repetition, arm))
    return out


def cells_for(unbudgeted: Sequence[str], budgeted: Sequence[str],
              budgets: Sequence[object] = nrc.BUDGETS) -> List[Tuple[str, object]]:
    return [(arm, None) for arm in unbudgeted] + [(arm, b) for arm in budgeted for b in budgets]


def stage_manifest(stage: str, extra: dict, sources: Sequence[str]) -> dict:
    missing = [name for name in sources if oc.file_sha256(oc.ROOT / name) is None]
    if missing:
        raise RuntimeError(f"measured sources missing: {missing}")
    payload = {"stage": stage, "protocol_id": nrc.PROTOCOL_ID,
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
    if worker == "next":
        spec = {"kind": "next_round_measurement", "program_path": entry["program_path"],
                "program_sha256": entry["program_sha256"], "arm": arm["label"],
                "catalog": arm["catalog"], "traversal": arm["traversal"],
                "variant": arm.get("variant"), "repetition": repetition, "stage": stage,
                "corpus": corpus}
        if isinstance(budget, str) and budget.startswith("work:"):
            spec.update(budget_seconds=None, work_limit=int(budget[5:]))
        else:
            spec.update(budget_seconds=budget, work_limit=None)
        argv = [oc.PYTHON, "-m", "research.next_round_worker", "--spec", oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker == "profile":
        spec = {"kind": "next_round_profile", "program_path": entry["program_path"],
                "program_sha256": entry["program_sha256"], "arm": arm["label"],
                "target": arm["target"], "budget_seconds": budget, "repetition": repetition,
                "stage": stage, "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.next_round_profile", "--spec", oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker == "ranker":
        spec = {"kind": "next_round_ranker", "program_sha256": entry["program_sha256"],
                "fixture_id": entry["fixture_id"], "ranker_input": entry["ranker_input"],
                "ranker_input_sha256": entry["ranker_input_sha256"], "arm": arm["label"],
                "ordering": arm["ordering"], "repetition": repetition, "stage": stage,
                "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.next_round_ranker", "--spec", oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker == "acquisition":
        spec = {"kind": "next_round_acquisition", "program_path": entry["program_path"],
                "program_sha256": entry["program_sha256"], "arm": arm["label"],
                "budget_seconds": budget, "repetition": repetition, "stage": stage,
                "corpus": corpus}
        argv = [oc.PYTHON, "-m", "research.next_round_acquisition", "--spec",
                oc.canonical(spec)]
        return argv, spec, oc.ROOT
    if worker in ("new", "frozen"):
        return orun.arm_command(run, stage, corpus, entry, arm, budget, repetition)
    raise ValueError(f"unknown worker {worker!r}")


# --------------------------------------------------------------------------
# Matrix engine
# --------------------------------------------------------------------------


class CapReached(RuntimeError):
    """The 24-hour measurement ledger is full; the stage stops cleanly."""


class Matrix:
    """One stage's expected keys, cell order, journal, ledger and resume ownership."""

    def __init__(self, run: Path, stage: str, corpus: str, entries: Sequence[dict],
                 arms: Dict[str, dict], cells: Sequence[Tuple[str, object]], repetitions: int,
                 sources: Sequence[str] = MEASURED_SOURCES, extra: Optional[dict] = None,
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
        self.expected = [row_key(e["program_sha256"], a, b, r) for e, b, r, a in self.plan]
        if len(set(self.expected)) != len(self.expected):
            raise RuntimeError(f"{stage}: duplicate expected keys")
        extra = dict(extra or {}, corpus=corpus, arms=arms,
                     cells=[[a, b] for a, b in self.cells], repetitions=repetitions,
                     programs=[{k: e.get(k) for k in ("seed", "family", "program_sha256",
                                                       "file_sha256", "semantic_sha256")}
                               for e in self.entries],
                     freeze_sha256=freeze_sha256, order_seed=nrc.SEED_ARM_ORDER)
        self.manifest = stage_manifest(stage, extra, sources)

    def write_expected(self) -> None:
        path = self.dir / "EXPECTED_KEYS.json"
        payload = {"stage": self.stage, "count": len(self.expected), "keys": self.expected,
                   "order_seed": nrc.SEED_ARM_ORDER}
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
            "pending": len(pending), "manifest_sha256": self.manifest["manifest_sha256"],
            "measured_hours_before": nrc.measured_hours(self.run)})
        started = time.perf_counter()
        cap = False
        for count, (entry, budget, repetition, arm_label) in enumerate(pending, 1):
            if nrc.cap_reached(self.run):
                cap = True
                break
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
                   "failed": sum(1 for r in rows if r["failed_row"]),
                   "timed_out": sum(1 for r in rows if r["timed_out"]),
                   "stopped_at_wall_cap": cap,
                   "measured_hours_after": nrc.measured_hours(self.run)}
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
        key = row_key(entry["program_sha256"], arm_label, budget, repetition)
        nrc.charge(self.run, self.stage, key, process_seconds)
        row = {"key": key, "stage": self.stage, "corpus": self.corpus,
               "program_sha256": entry["program_sha256"], "family": entry["family"],
               "seed": entry.get("seed"), "arm": arm_label, "budget_seconds": budget,
               "repetition": repetition, "exit_code": code, "timed_out": timed_out,
               "process_seconds": process_seconds, "stderr_tail": stderr[-4000:],
               "stdout_bytes": len(stdout), "started_utc": stamp,
               "manifest_sha256": self.manifest["manifest_sha256"],
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
            "env_pythonpath": env["PYTHONPATH"], "exit_code": code, "timed_out": timed_out,
            "process_seconds": process_seconds, "started_utc": stamp,
            "stdout_sha256": oc.sha256_bytes(stdout.encode()),
            "stderr_sha256": oc.sha256_bytes(stderr.encode())})
        oc.append_row(self.rows_path, row)
        return row


# --------------------------------------------------------------------------
# Corpora
# --------------------------------------------------------------------------


def development_entries(run: Path) -> List[dict]:
    return orun.generated_cohort(run, "development", *nrc.DEVELOPMENT)


def profiling_entries(run: Path) -> List[dict]:
    """The first two seeds of each family, in family order (plan section 4)."""

    out: Dict[str, List[dict]] = {}
    for entry in development_entries(run):
        out.setdefault(entry["family"], []).append(entry)
    chosen = []
    for family, entries in out.items():
        chosen.extend(sorted(entries, key=lambda e: e["seed"])[:2])
    if len(chosen) != 10:
        raise RuntimeError("expected ten profiling programs")
    return chosen


def public_entries(run: Path) -> List[dict]:
    return orun.public_cohort(run)


def confirmation_entries(run: Path) -> List[dict]:
    return orun.generated_cohort(run, "confirmation", *nrc.CONFIRMATION)


# --------------------------------------------------------------------------
# Stages
# --------------------------------------------------------------------------


def development_arms() -> Dict[str, dict]:
    arms = {label: cell_arm(label) for label in nrc.CELLS}
    arms[nrc.EARLIER] = earlier_arm()
    return arms


def stage_d_factorial(run: Path) -> Matrix:
    arms = development_arms()
    return Matrix(run, "D_factorial", "development", development_entries(run), arms,
                  cells_for([], list(nrc.DEVELOPMENT_ARMS)), 3)


def stage_d_fixed_work(run: Path) -> Matrix:
    arms = {label: cell_arm(label) for label in nrc.CELLS}
    return Matrix(run, "D_fixed_work", "development_profiling", profiling_entries(run), arms,
                  cells_for([], sorted(nrc.CELLS), [f"work:{n}" for n in WORK_LIMITS]), 1,
                  extra={"work_limits": list(WORK_LIMITS),
                         "wall": "no allowance except the 20 s external safety limit"})


def stage_d_profile(run: Path) -> Matrix:
    arms = {label: profile_arm(label) for label in nrc.DEVELOPMENT_ARMS}
    sources = MEASURED_SOURCES + ("research/next_round_profile.py",)
    return Matrix(run, "D_profile", "development_profiling", profiling_entries(run), arms,
                  cells_for([], list(nrc.DEVELOPMENT_ARMS)), 1, sources=sources,
                  extra={"note": "separate cProfile runs; never used as timing rows"})


ENGINEERED = "cell_a4cat_dfs+engineered"
ENGINEERED_SOURCES = MEASURED_SOURCES + ("research/next_round_engineered.py",)


def stage_e_engineering(run: Path) -> Matrix:
    selection = json.loads((Path(run) / "SELECTION.json").read_text())
    parent = selection["selection"]["selected_arm"]
    label = f"{parent}+engineered"
    if label != ENGINEERED:
        raise RuntimeError(f"the engineering plan names {ENGINEERED}, selection gives {label}")
    arms = {label: cell_arm(label, variant="engineered")}
    return Matrix(run, "E_engineering", "development", development_entries(run), arms,
                  cells_for([], [label]), 3, sources=ENGINEERED_SOURCES,
                  extra={"parent": parent, "engineering_plan_sha256": oc.file_sha256(
                      Path(run) / "ENGINEERING_PLAN.json")})


# --------------------------------------------------------------------------
# Stage C: confirmation cohort, freeze, matrices
# --------------------------------------------------------------------------

PRIOR_COHORTS = {
    "development_800000": range(800000, 800100),
    "optimization_fresh_810000": range(810000, 810200),
    "optimization_fixture_dev_820000": range(820000, 820200),
    "optimization_fixture_eval_830000": range(830000, 830400),
    "objective_fresh_910000": range(910000, 910200),
    "objective_fixture_dev_920000": range(920000, 920200),
    "objective_fixture_eval_930000": range(930000, 930400),
    "this_round_learning_pool_970000": range(970000, 970400),
}
UNBUDGETED_CONTROLS = ("classical", "accepted_bootstrap")


def freeze_confirmation_cohort(run: Path) -> dict:
    """Seeds 960000-960199: legality, semantic disjointness, no prior exposure.

    A collision or a prior exposure makes the confirmation DESIGN_INVALID; no
    seed is ever replaced.
    """

    from research import objective_index_fixtures as oif
    from research import run_structural_experiments as rse

    run = Path(run)
    entries = confirmation_entries(run)
    index = oif.collision_index(PRIOR_COHORTS)
    collisions = []
    seen: Dict[str, int] = {}
    for entry in entries:
        if entry["semantic_sha256"] in index:
            collisions.append({"seed": entry["seed"], "against": index[entry["semantic_sha256"]]})
        if entry["semantic_sha256"] in seen:
            collisions.append({"seed": entry["seed"],
                               "against": f"confirmation:{seen[entry['semantic_sha256']]}"})
        seen[entry["semantic_sha256"]] = entry["seed"]
    for item in rse.heldout_collisions(entries):
        if item["kind"] != "internal":
            collisions.append({"seed": item["seed"], "against": item["against"],
                               "kind": item["kind"]})
    first, last = nrc.CONFIRMATION
    previously_used = []
    for manifest in sorted(oc.RESULTS.glob("*/inputs/*/*.json")):
        if manifest.is_relative_to(run.resolve()):
            continue
        stem = manifest.stem
        if stem.startswith("seed_") and stem[5:].isdigit() and first <= int(stem[5:]) <= last:
            previously_used.append(str(manifest.relative_to(oc.ROOT)))
    counts = oc.family_counts(entries)
    public = public_entries(run)
    ok = (not collisions and not previously_used and len(counts) == 5
          and all(n == 40 for n in counts.values()))
    payload = {"cohort": "confirmation", "seeds": [first, last], "family_counts": counts,
               "programs": entries, "public_programs": public, "collisions": collisions,
               "prior_cohorts_checked": {k: [v.start, v.stop - 1] for k, v in
                                         PRIOR_COHORTS.items()},
               "previously_used_seed_files": previously_used,
               "status": "PASS" if ok else "DESIGN_INVALID",
               "legality": "machine.validate_program + serial reference compile + every case",
               "exposure": "legality and collision checks only; no candidate outcome observed"}
    oc.write_immutable_json(run / "CONFIRMATION_COHORT.json", payload)
    return payload


def confirmation_arms(run: Path) -> Tuple[Dict[str, dict], List[str]]:
    frozen = json.loads((Path(run) / "FROZEN_SELECTION.json").read_text())
    budgeted = list(frozen["confirmation"]["budgeted_arms"])
    arms = {}
    for label in budgeted:
        if label == nrc.EARLIER:
            arms[label] = earlier_arm()
        elif label.endswith("+engineered"):
            arms[label] = cell_arm(label, variant="engineered")
        else:
            arms[label] = cell_arm(label)
    for label in UNBUDGETED_CONTROLS + ("serial",):
        arms[label] = frozen_arm(label)
    return arms, budgeted


def load_freeze(run: Path) -> Tuple[dict, str]:
    path = Path(run) / "FROZEN_SELECTION.json"
    return json.loads(path.read_text()), oc.file_sha256(path)


def stage_c_confirmation(run: Path) -> Matrix:
    frozen, digest = load_freeze(run)
    cohort = json.loads((Path(run) / "CONFIRMATION_COHORT.json").read_text())
    if cohort["status"] != "PASS":
        raise RuntimeError("the confirmation cohort is DESIGN_INVALID; confirmation stops")
    arms, budgeted = confirmation_arms(run)
    arms = {k: v for k, v in arms.items() if k != "serial"}
    return Matrix(run, "C_confirmation", "confirmation", cohort["programs"], arms,
                  cells_for(UNBUDGETED_CONTROLS, budgeted), 5,
                  sources=tuple(frozen["confirmation"]["measured_sources"]),
                  freeze_sha256=digest)


def stage_c_public(run: Path) -> Matrix:
    frozen, digest = load_freeze(run)
    cohort = json.loads((Path(run) / "CONFIRMATION_COHORT.json").read_text())
    arms, budgeted = confirmation_arms(run)
    return Matrix(run, "C_public", "public", cohort["public_programs"], arms,
                  cells_for(UNBUDGETED_CONTROLS + ("serial",), budgeted), 5,
                  sources=tuple(frozen["confirmation"]["measured_sources"]),
                  freeze_sha256=digest)


def write_freeze(run: Path) -> dict:
    """FROZEN_SELECTION.json: everything fixed before any confirmation outcome."""

    import tarfile

    run = Path(run)
    target = run / "FROZEN_SELECTION.json"
    if target.exists():
        raise FileExistsError("FROZEN_SELECTION.json is immutable")
    selection = json.loads((run / "SELECTION.json").read_text())
    decision = json.loads((run / "ENGINEERING_DECISION.json").read_text())
    cohort = json.loads((run / "CONFIRMATION_COHORT.json").read_text())
    if cohort["status"] != "PASS":
        raise RuntimeError("confirmation cohort DESIGN_INVALID")
    candidate = decision["frozen_candidate"]
    budgeted = []
    for label in (nrc.EARLIER, nrc.REPAIRED_A4, candidate):
        if label not in budgeted:  # exact source/config aliases are measured once
            budgeted.append(label)
    sources = ENGINEERED_SOURCES if candidate.endswith("+engineered") else MEASURED_SOURCES
    frozen_dir = run / "SOURCE_MANIFESTS" / "frozen"
    frozen_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(frozen_dir / "research_source.tar", "x") as tar:
        for folder in ("research", "research_tests"):
            for path in sorted((oc.ROOT / folder).glob("*.py")):
                tar.add(path, arcname=f"{folder}/{path.name}")
    inputs = {}
    for label, relative in (("selection", "SELECTION.json"),
                            ("engineering_plan", "ENGINEERING_PLAN.json"),
                            ("engineering_decision", "ENGINEERING_DECISION.json"),
                            ("confirmation_cohort", "CONFIRMATION_COHORT.json"),
                            ("preflight_estimate", "PREFLIGHT_ESTIMATE.json"),
                            ("d_factorial_rows", "stages/D_factorial/rows.jsonl"),
                            ("e_engineering_rows", "stages/E_engineering/rows.jsonl")):
        inputs[label] = {"path": relative, "sha256": oc.file_sha256(run / relative)}
    payload = {
        "protocol_id": nrc.PROTOCOL_ID,
        "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "package_lock_sha256": oc.file_sha256(nrc.PACKAGE / "LOCK.json"),
        "candidate": {"selected_development_arm": selection["selection"]["selected_arm"],
                      "engineering_variant_frozen": candidate.endswith("+engineered"),
                      "frozen_candidate": candidate,
                      "candidate_is_distinct_new": candidate not in (nrc.EARLIER,
                                                                      nrc.REPAIRED_A4)},
        "references": {nrc.EARLIER: {"worker": "research.optimization_worker (unchanged)",
                                     **nrc.EARLIER_SPEC, "optimisation_query_seconds": 0.1},
                       nrc.REPAIRED_A4: {"worker": "research.next_round_worker",
                                         "solver": "research/next_round_search.py",
                                         "catalog": "a4", "traversal": "heap"}},
        "confirmation": {"budgeted_arms": budgeted, "K": len(budgeted),
                         "unbudgeted_controls": list(UNBUDGETED_CONTROLS),
                         "public_extra_control": "serial", "repetitions": 5,
                         "measured_sources": list(sources)},
        "sources": {"research": oc.research_source_hashes(),
                    "production": oc.production_source_hashes(),
                    "frozen_snapshot": oc.frozen_snapshot_hashes(),
                    "frozen_workspace_worker": oc.file_sha256(
                        orun.frozen_workspace(run) / "optimization_frozen_worker.py"),
                    "source_tar_sha256": oc.file_sha256(frozen_dir / "research_source.tar")},
        "inputs": inputs,
        "seeds": {"arm_order": nrc.SEED_ARM_ORDER, "bootstrap": nrc.SEED_BOOTSTRAP,
                  "training_draw": nrc.SEED_TRAINING_DRAW, "pool": nrc.SEED_POOL,
                  "shuffled_labels": nrc.SEED_SHUFFLED,
                  "random_order": list(nrc.RANDOM_ORDER_SEEDS)},
        "inference": {
            "primary": "mean paired log(J_earlier_cap512_wider / J_cell_a4cat_heap) at 0.1 s on "
                       "the 200 confirmation programs; five repetition logs averaged per program; "
                       "equal-family means; 10,000 program-within-family resamples, seed "
                       "2026092602; two-sided 95% (0.025, 0.975); lower > 0 favours A4, upper < 0 "
                       "favours the earlier optimizer, otherwise INCONCLUSIVE",
            "candidate_endpoints": "only if the candidate is distinct: J ratio (paired "
                                   "repetition logs) and compile-time ratio (ratio of per-program "
                                   "median compile_seconds) against EACH reference; two-sided "
                                   "98.75% (0.00625, 0.99375)",
            "practical_routes": nrc.TARGETS,
            "descriptive": "other budgets, fixed targets, classical and bootstrap comparisons",
            "public": "S = sqrt(GM(C_serial/C) * GM(S_serial/S)) per repetition over eight public "
                      "programs; reconciled with exp(mean(log(J_serial/J))/2)"},
        "learning_track": {
            "rule": "separate fixture/pool manifest freeze (LEARNING_FREEZE.json) before any "
                    "ordering is evaluated; learning source frozen here with the compiler",
            "sources": {name: oc.file_sha256(oc.ROOT / "research" / name) for name in (
                "next_round_learning.py", "next_round_ranker.py", "next_round_acquisition.py",
                "schema_ranker.py", "objective_index_learned.py", "objective_index_fixtures.py",
                "optimization_fixtures.py")}},
        "reporting": {name: oc.file_sha256(oc.ROOT / "research" / name) for name in (
            "next_round_analysis.py", "next_round_report.py", "next_round_checker.py",
            "next_round_audit.py", "next_round_export.py", "next_round_runner.py")},
        "exposure": {"confirmation_candidate_outcomes_observed": False},
    }
    expected = {}
    arms_c = [a for a in budgeted]
    expected["C_confirmation"] = schedule(cohort["programs"],
                                          cells_for(UNBUDGETED_CONTROLS, arms_c), 5)
    expected["C_public"] = schedule(cohort["public_programs"],
                                    cells_for(UNBUDGETED_CONTROLS + ("serial",), arms_c), 5)
    payload["expected_matrices"] = {}
    for stage, plan in expected.items():
        keys = [row_key(e["program_sha256"], a, b, r) for e, b, r, a in plan]
        digest = oc.write_immutable_json(run / "frozen_expected" / f"{stage}.json",
                                         {"stage": stage, "count": len(keys), "keys": keys})
        payload["expected_matrices"][stage] = {"count": len(keys), "sha256": digest}
    payload["expected_matrices"]["export_candidate"] = {"count": 624}
    oc.write_immutable_json(target, payload)
    return payload


# --------------------------------------------------------------------------
# Stage L: learning mechanism and economics pilot
# --------------------------------------------------------------------------

LEARNING_SOURCES = MEASURED_SOURCES + (
    "research/next_round_ranker.py", "research/next_round_acquisition.py",
    "research/schema_ranker.py", "research/objective_index_learned.py",
    "research/objective_index_search.py", "research/optimization_models.py",
)
LEARNING_POOL_OTHER = range(920000, 920200)  # the development fixtures' pool


def _learning_dir(run: Path) -> Path:
    return Path(run) / "learning"


def learning_design(run: Path, cohort: str) -> dict:
    """Training draw, common pool and sensitivity gate for one fixture cohort."""

    from research import next_round_learning as nrl
    from tests_direct import generate_programs as gp

    run = Path(run)
    if cohort == "development":
        manifest_path = nrl.OLD_RUN / "fixtures" / "development" / "MANIFEST.json"
        minimum, per_family = nrc.LEARNING["minimum_informative_development"], 1
    else:
        manifest_path = _learning_dir(run) / "fixtures" / "evaluation" / "MANIFEST.json"
        minimum = nrc.LEARNING["minimum_informative_evaluation"]
        per_family = nrc.LEARNING["minimum_informative_evaluation_per_family"]
    target = _learning_dir(run) / f"DESIGN_{cohort.upper()}.json"
    if target.exists():
        raise FileExistsError(f"{target} is written once")
    fixtures = nrl.manifest_fixtures(manifest_path)
    designs = [nrl.design(manifest_path.parent / f["fixture_id"], f,
                          _learning_dir(run) / "design" / cohort) for f in fixtures]
    gate = nrl.design_gate(designs, minimum, per_family, gp.FAMILIES)
    payload = {"cohort": cohort, "manifest": str(manifest_path.relative_to(oc.ROOT)),
               "manifest_sha256": oc.file_sha256(manifest_path), "designs": designs,
               "gate": gate, "orderings_evaluated_before_this_file": False,
               "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    oc.write_immutable_json(target, payload)
    return payload


def learning_qualify(run: Path) -> dict:
    """Fresh fixtures: the previous recipe unchanged on pool 970000-970399, six per family."""

    from research import objective_index_fixtures as oif

    run = Path(run)
    development = json.loads((_learning_dir(run) / "DESIGN_DEVELOPMENT.json").read_text())
    if development["gate"]["status"] != "PASS":
        raise RuntimeError("development sensitivity failed: the learning track stops")
    index = oif.collision_index({k: v for k, v in PRIOR_COHORTS.items()
                                 if not k.startswith("this_round_learning")}
                                | {"confirmation_960000": range(960000, 960200)})
    first, last = nrc.LEARNING_POOL
    started = time.perf_counter()
    manifest = oif.qualify_pool("evaluation", _learning_dir(run) / "fixtures" / "evaluation",
                                index, LEARNING_POOL_OTHER, first, last,
                                nrc.LEARNING["per_family"], oif.SPLIT_SEED)
    oc.append_row(_learning_dir(run) / "qualification_runs.jsonl",
                  {"seconds": time.perf_counter() - started, "status": manifest["status"],
                   "filled": manifest["filled"], "collisions": len(manifest["collisions"]),
                   "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
    return manifest


def learning_freeze(run: Path) -> dict:
    """LEARNING_FREEZE.json: fixtures, pools and orderings fixed before any evaluation."""

    from research import next_round_ranker as nrr

    run = Path(run)
    target = run / "LEARNING_FREEZE.json"
    if target.exists():
        raise FileExistsError("LEARNING_FREEZE.json is immutable")
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    evaluation = json.loads((_learning_dir(run) / "DESIGN_EVALUATION.json").read_text())
    if evaluation["gate"]["status"] != "PASS":
        raise RuntimeError("evaluation sensitivity failed: orderings are not evaluated")
    drift = {name: digest for name, digest in frozen["learning_track"]["sources"].items()
             if oc.file_sha256(oc.ROOT / "research" / name) != digest}
    if drift:
        raise RuntimeError(f"learning sources changed after the compiler freeze: {drift}")
    payload = {"protocol_id": nrc.PROTOCOL_ID,
               "frozen_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
               "compiler_freeze_sha256": oc.file_sha256(run / "FROZEN_SELECTION.json"),
               "design_development_sha256": oc.file_sha256(
                   _learning_dir(run) / "DESIGN_DEVELOPMENT.json"),
               "design_evaluation_sha256": oc.file_sha256(
                   _learning_dir(run) / "DESIGN_EVALUATION.json"),
               "fixture_manifest_sha256": evaluation["manifest_sha256"],
               "orderings": list(nrr.ORDERINGS),
               "fixtures": [{k: d[k] for k in ("fixture_id", "family", "program_sha256",
                                                "ranker_input_sha256", "evaluator_sha256")}
                            for d in evaluation["designs"]],
               "ranker_sources": {n: oc.file_sha256(oc.ROOT / "research" / n)
                                  for n in ("next_round_ranker.py", "schema_ranker.py",
                                            "next_round_common.py", "optimization_models.py")},
               "evaluation_outcomes_observed": False}
    oc.write_immutable_json(target, payload)
    return payload


def stage_l_orderings(run: Path) -> Matrix:
    from research import next_round_ranker as nrr

    run = Path(run)
    freeze = json.loads((run / "LEARNING_FREEZE.json").read_text())
    evaluation = json.loads((_learning_dir(run) / "DESIGN_EVALUATION.json").read_text())
    entries = [dict(d, seed=d["seed"]) for d in evaluation["designs"]]
    arms = {o: {"label": o, "worker": "ranker", "ordering": o} for o in nrr.ORDERINGS}
    return Matrix(run, "L_orderings", "learning_evaluation", entries, arms,
                  cells_for(list(nrr.ORDERINGS), []), 1,
                  sources=MEASURED_SOURCES + ("research/next_round_ranker.py",
                                              "research/schema_ranker.py",
                                              "research/optimization_models.py"),
                  freeze_sha256=oc.file_sha256(run / "LEARNING_FREEZE.json"),
                  extra={"learning_freeze": freeze["frozen_utc"]})


def stage_l_acquisition(run: Path) -> Matrix:
    arms = {"acquisition_tree": {"label": "acquisition_tree", "worker": "acquisition"}}
    return Matrix(run, "L_acquisition", "development", development_entries(run), arms,
                  cells_for([], ["acquisition_tree"], [nrc.PRIMARY_BUDGET]), 1,
                  sources=LEARNING_SOURCES,
                  extra={"learner": "objective_index_learned.QueryLearner (tree), timed "
                                    "subclass; controller next_round_search repaired A4"})


STAGES = {
    "L_orderings": stage_l_orderings,
    "L_acquisition": stage_l_acquisition,
    "C_confirmation": stage_c_confirmation,
    "C_public": stage_c_public,
    "E_engineering": stage_e_engineering,
    "D_factorial": stage_d_factorial,
    "D_fixed_work": stage_d_fixed_work,
    "D_profile": stage_d_profile,
}


# --------------------------------------------------------------------------
# Setup and isolation
# --------------------------------------------------------------------------


def isolation_probe(run: Path) -> dict:
    """The owner's frozen/new probe plus what the successor worker actually imports."""

    report = orun.isolation_probe(run)
    code = (
        "import sys, json, hashlib\n"
        f"sys.path[:0] = [{str(oc.ROOT / '.reference')!r}, {str(oc.ROOT)!r}]\n"
        "import research.next_round_worker\n"
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
    report["successor_worker"] = {"exit_code": proc.returncode, "stderr": proc.stderr[-2000:],
                                  "modules": modules}
    workspace = str(orun.frozen_workspace(run))
    ok = (modules is not None
          and "research.next_round_search" in modules
          and "research.objective_index_search" not in modules
          and not any(entry["path"].startswith(workspace) for entry in modules.values()))
    report["successor_worker_loads_successor_only"] = ok
    earlier = (report.get("new") or {}).get("modules") or {}
    report["earlier_worker_search_sha256"] = (earlier.get("research.optimization_search")
                                              or {}).get("sha256")
    report["status"] = "PASS" if report["status"] == "PASS" and ok else "FAIL"
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", required=True,
                        choices=sorted(STAGES) + ["setup", "probe", "confirmation_cohort",
                                                  "freeze", "learning_design_development",
                                                  "learning_qualify", "learning_design_evaluation",
                                                  "learning_freeze"])
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
        print(json.dumps({k: report.get(k) for k in (
            "status", "frozen_research_from_snapshot", "frozen_production_protected",
            "successor_worker_loads_successor_only", "earlier_worker_search_sha256")}))
        return 0 if report["status"] == "PASS" else 1
    if args.stage == "confirmation_cohort":
        payload = freeze_confirmation_cohort(run)
        print(json.dumps({k: payload[k] for k in ("status", "family_counts", "collisions",
                                                   "previously_used_seed_files")}))
        return 0 if payload["status"] == "PASS" else 1
    if args.stage in ("learning_design_development", "learning_design_evaluation"):
        payload = learning_design(run, args.stage.rsplit("_", 1)[1])
        print(json.dumps(payload["gate"]))
        return 0 if payload["gate"]["status"] == "PASS" else 1
    if args.stage == "learning_qualify":
        manifest = learning_qualify(run)
        print(json.dumps({k: manifest[k] for k in ("status", "filled", "collisions")}))
        return 0 if manifest["status"] == "PASS" else 1
    if args.stage == "learning_freeze":
        payload = learning_freeze(run)
        print(json.dumps({"fixtures": len(payload["fixtures"]),
                          "orderings": len(payload["orderings"])}))
        return 0
    if args.stage == "freeze":
        payload = write_freeze(run)
        print(json.dumps({"candidate": payload["candidate"],
                          "expected": payload["expected_matrices"]}))
        return 0
    matrix = STAGES[args.stage](run)
    summary = matrix.run_all()
    print(json.dumps(summary))
    return 0 if (summary["missing"] == 0 and summary["sources_unchanged_during_stage"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
