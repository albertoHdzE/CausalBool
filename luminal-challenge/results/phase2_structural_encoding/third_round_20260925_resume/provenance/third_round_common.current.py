"""Constants, run directory, row ledger and fresh-process runner of the third round.

``plan/CLAUDE_PHASE2_THIRD_ROUND.md`` v1.0 and
``plan/phase2_third_round/PROTOCOL.json`` are the authority. PROTOCOL.json is the
one source of protocol constants; ``check_protocol_constants`` compares it with
the literals below and prints its denominator, so a silent edit of either side
is caught.

Owners reused rather than re-created:

- file I/O, hashes, environment and git state: ``optimization_common``;
- the measurement wall-time ledger (``charge``/``measured_hours``) and the
  fixed-work constants of the E gate: ``efficiency_common``;
- the complete fixed-work compile call and its decision fingerprint:
  ``efficiency_profile.fixed_work_call`` / ``_decision_fingerprint``;
- the stable seed: ``objective_index_common.stable_seed``;
- program generation and digests: ``tests_direct.generate_programs``.

Row discipline (plan section 6): expected keys are frozen before a stage; every
attempt is appended to ``ATTEMPTS.jsonl``; exactly one authoritative row per key
lives in the stage's ``rows.jsonl``; a failed or timed-out key is recorded as a
failed row and never retried.
"""

from __future__ import annotations

import json
import os
import subprocess
import time
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from research import efficiency_common as ec
from research import objective_index_common as oic
from research import optimization_common as oc


ROOT = oc.ROOT
RESULTS = oc.RESULTS
PACKAGE = ROOT / "plan" / "phase2_third_round"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PROTOCOL_ID = "luminal-phase2-third-improvement-1.0"
RUN_NAME = "third_round_20260925"

R0_SOURCE = "research/efficiency_search.py"
R0_SHA256 = "d0fcd441886cc5c3d34a6e1df7b2828ea219b6575ffd2049913b4d4901b92fbf"
R0_EXPORT = "results/phase2_structural_encoding/efficiency_20260925/r0_export/compiler.py"
R0_EXPORT_SHA256 = "74c87b69e63063595d3283bb66986162297519bb1a8a2a87f2853fd7134d9ea9"

FAMILIES = ("scalar", "vector", "mixed", "dependency", "aliasing")
DIAGNOSTIC = (800000, 800029)
DEVELOPMENT = (800000, 800099)
CONFIRMATION = (980000, 980199)
TIME_REPS = 3
KERNEL_REPS = 3
KERNEL_VERSIONS = ("baseline_kernel", "shared_state_kernel")
OTHER_MODES = ("exclusive_timers", "workload_trace", "peak_memory", "instrumentation_parity")
EXTERNAL_SECONDS = 20.0
WALL_CAP_HOURS = 24.0
DEV_CAP_HOURS = 16.0
MECHANISM_GATE = {"conservative_predicted_compile_ratio_max": 0.8,
                  "replacement_and_extra_overhead_multiplier": 1.5}
DEVELOPMENT_GATE = {"fixed_work_compile_ratio_max": 0.9,
                    "wall_primary_mean_log_J_ratio_max": 0}
CONFIRMATION_GATE = {"fixed_work_compile_ratio_upper_max": 0.8,
                     "wall_primary_J_ratio_upper_max": 1.01}
SEED_ARM_ORDER = 2026092801
SEED_BOOTSTRAP = 2026092802
EXPECTED_ROWS = {"M_diagnosis": 210, "M_kernel": 180, "D_fixed_work": 600, "D_wall": 600,
                 "D_memory": 60, "C_acceptance": 284, "C_fixed_work": 2000, "C_wall": 6000,
                 "C_public": 280, "C_export": 1248}

KEY_FIELDS = ("stage_id", "program_sha256", "repetition", "arm_id", "mode_key")

stable_seed = oic.stable_seed
charge = ec.charge
measured_hours = ec.measured_hours


def family_of(seed: int) -> str:
    return FAMILIES[seed % 5]


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def check_protocol_constants() -> dict:
    p = load_protocol()
    checks = {
        "protocol_id": (p["protocol_id"], PROTOCOL_ID),
        "r0": ((p["baseline"]["solver"], p["baseline"]["sha256"]), (R0_SOURCE, R0_SHA256)),
        "r0_export": ((p["baseline"]["export"], p["baseline"]["export_sha256"]),
                      (R0_EXPORT, R0_EXPORT_SHA256)),
        "families": (tuple(p["families"]), FAMILIES),
        "diagnostic": ((p["diagnostic"]["first_seed"], p["diagnostic"]["last_seed"]), DIAGNOSTIC),
        "development": ((p["development"]["first_seed"], p["development"]["last_seed"]),
                        DEVELOPMENT),
        "confirmation": ((p["confirmation"]["first_seed"], p["confirmation"]["last_seed"]),
                         CONFIRMATION),
        "time_reps": (p["diagnostic"]["time_repetitions"], TIME_REPS),
        "kernel_reps": (p["diagnostic"]["kernel_repetitions"], KERNEL_REPS),
        "kernel_versions": (tuple(p["diagnostic"]["kernel_versions"]), KERNEL_VERSIONS),
        "other_modes": (tuple(p["diagnostic"]["other_modes"]), OTHER_MODES),
        "external": (float(p["external_timeout_seconds"]), EXTERNAL_SECONDS),
        "wall_cap": (float(p["measurement_wall_cap_hours"]), WALL_CAP_HOURS),
        "dev_cap": (float(p["active_development_cap_hours"]), DEV_CAP_HOURS),
        "mechanism_gate": ({k: p["mechanism_gate"][k] for k in MECHANISM_GATE},
                           MECHANISM_GATE),
        "development_gate": ({k: p["development_gate"][k] for k in DEVELOPMENT_GATE},
                             DEVELOPMENT_GATE),
        "confirmation_gate": ({k: p["confirmation_gate"][k] for k in CONFIRMATION_GATE},
                              CONFIRMATION_GATE),
        "arm_order": (p["seeds"]["arm_order"], SEED_ARM_ORDER),
        "bootstrap": (p["seeds"]["bootstrap"], SEED_BOOTSTRAP),
        "expected_rows": (p["expected_rows"], EXPECTED_ROWS),
        "fixed_work": ((p["fixed_work"]["aggregate_nodes"],
                        p["fixed_work"]["aggregate_validations"],
                        p["fixed_work"]["slice_nodes"]),
                       (ec.FIXED_WORK["aggregate_nodes"], ec.FIXED_WORK["aggregate_validations"],
                        ec.FIXED_WORK["slice_nodes"])),
    }
    mismatches = {n: {"package": a, "module": b} for n, (a, b) in checks.items() if a != b}
    return {"checked": len(checks), "mismatches": mismatches,
            "status": "PASS" if checks and not mismatches else "FAIL"}


def diagnostic_seeds() -> Tuple[int, ...]:
    return tuple(range(DIAGNOSTIC[0], DIAGNOSTIC[1] + 1))


def run_dir(suffix: Optional[str] = None) -> Path:
    return RESULTS / (RUN_NAME if suffix is None else f"{RUN_NAME}_{suffix}")


def fresh_run_dir() -> Path:
    """The first unoccupied ``third_round_20260925[_N]``; never an occupied one."""

    candidate = run_dir()
    n = 1
    while candidate.exists():
        n += 1
        candidate = run_dir(str(n))
    candidate.mkdir(parents=True)
    return candidate


def cap_reached(run: Path) -> bool:
    return measured_hours(run) >= WALL_CAP_HOURS


# --------------------------------------------------------------------------
# Row keys and the fresh-process runner
# --------------------------------------------------------------------------


def row_key(row: dict) -> str:
    return "|".join(str(row[k]) for k in KEY_FIELDS)


def check_rows(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    """Completeness of one stage: exactly one row per expected key, none failed.

    Refuses an empty expectation (a pass over zero keys is not a pass).
    """

    if not expected:
        raise ValueError("refusing to check a stage with zero expected keys")
    counts: Dict[str, int] = {}
    for row in rows:
        counts[row_key(row)] = counts.get(row_key(row), 0) + 1
    expected_set = set(expected)
    missing = sorted(k for k in expected_set if k not in counts)
    duplicates = sorted(k for k, n in counts.items() if n > 1)
    unexpected = sorted(k for k in counts if k not in expected_set)
    failed = sorted(row_key(r) for r in rows if r.get("failed") or r.get("timed_out"))
    return {"expected": len(expected_set), "observed": len(rows), "missing": missing,
            "duplicates": duplicates, "unexpected": unexpected, "failed": failed,
            "complete": not (missing or duplicates or unexpected or failed)}


def worker_env() -> dict:
    """Pinned machine first, no inherited PYTHONPATH additions, no user site."""

    return {"PYTHONPATH": f"{ROOT / '.reference'}:{ROOT}", "PATH": "/usr/bin:/bin",
            "HOME": str(Path.home()), "PYTHONNOUSERSITE": "1", "PYTHONHASHSEED": "0"}


def run_stage(run: Path, stage: str, specs: Sequence[dict], module: str,
              timeout: float = EXTERNAL_SECONDS) -> dict:
    """Run every missing key of ``stage`` in one fresh process each, sequentially.

    ``specs`` carry the key fields. Existing authoritative rows are kept;
    failed/timed-out keys are never retried (their failed row is authoritative).
    """

    out = Path(run) / "stages" / stage
    out.mkdir(parents=True, exist_ok=True)
    rows_path, attempts_path = out / "rows.jsonl", out / "ATTEMPTS.jsonl"
    keys = [row_key(s) for s in specs]
    frozen = out / "EXPECTED_KEYS.json"
    if frozen.exists():
        if json.loads(frozen.read_text())["keys"] != keys:
            raise RuntimeError(f"{stage}: expected keys differ from the frozen list")
    else:
        oc.write_immutable_json(frozen, {"stage": stage, "count": len(keys), "keys": keys,
                                         "sha256": oc.object_sha256(keys)})
    done = {row_key(r) for r in oc.read_rows(rows_path)}
    tried = {r["key"] for r in oc.read_rows(attempts_path)}
    for spec in specs:
        key = row_key(spec)
        if key in done:
            continue
        if key in tried:
            raise RuntimeError(f"{stage}: key {key} has an attempt but no row; lead review")
        if cap_reached(run):
            raise RuntimeError("measurement cap reached")
        argv = [oc.PYTHON, "-s", "-m", module, "--spec", json.dumps(spec, sort_keys=True)]
        oc.append_row(attempts_path, {"key": key, "argv": argv, "started_utc": _utc()})
        started = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(argv, cwd=str(ROOT), capture_output=True, text=True,
                                  timeout=timeout, env=worker_env())
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out, code = True, None
            stdout = (exc.stdout or b"").decode() if isinstance(exc.stdout, bytes) else (
                exc.stdout or "")
            stderr = (exc.stderr or b"").decode() if isinstance(exc.stderr, bytes) else (
                exc.stderr or "")
        seconds = time.perf_counter() - started
        charge(run, stage, key, seconds)
        base = {k: spec[k] for k in KEY_FIELDS + ("seed",)}
        base.update(process_seconds=seconds, exit_code=code, timed_out=timed_out)
        oc.append_row(attempts_path, {"key": key, "finished_utc": _utc(), "exit_code": code,
                                      "timed_out": timed_out, "process_seconds": seconds,
                                      "stderr_tail": stderr[-4000:],
                                      "stdout_sha256": oc.sha256_bytes(stdout.encode())})
        if timed_out or code != 0:
            oc.append_row(rows_path, dict(base, failed=True, stderr_tail=stderr[-4000:]))
            continue
        try:
            result = json.loads(stdout)
        except json.JSONDecodeError:
            oc.append_row(rows_path, dict(base, failed=True, stdout_not_json=True,
                                          stdout_tail=stdout[-2000:]))
            continue
        oc.append_row(rows_path, dict(base, **result))
    rows = oc.read_rows(rows_path)
    return check_rows(rows, keys)


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def write_manifest(path: Path, extra: Optional[dict] = None) -> str:
    """Environment, git state and hashes of every research/production source."""

    payload = {"environment": oc.environment(), "git": oc.git_state(),
               "research_sources": oc.research_source_hashes(),
               "production_sources": oc.production_source_hashes(),
               "r0": {"source": R0_SOURCE, "sha256": oc.file_sha256(ROOT / R0_SOURCE),
                      "expected": R0_SHA256},
               "r0_export": {"path": R0_EXPORT, "sha256": oc.file_sha256(ROOT / R0_EXPORT),
                             "expected": R0_EXPORT_SHA256},
               "protocol_constants": check_protocol_constants(),
               "load": os.getloadavg()}
    if extra:
        payload.update(extra)
    return oc.write_immutable_json(path, payload)
