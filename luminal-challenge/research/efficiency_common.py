"""Constants and ledger of the Phase 2 efficiency phase (protocol 1.0).

``plan/CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` and
``plan/phase2_efficiency/PROTOCOL.json`` are the authority. This module owns:

- the protocol constants, read from ``PROTOCOL.json`` and compared with the
  literals below (``check_protocol_constants`` prints its denominator);
- the run directory ``efficiency_20260925[_N]``, never an occupied one;
- the measurement wall-time ledger: at most 24 hours of measurement process
  wall time, failed attempts and verification replays included, checked
  before every launch.

The seed function is ``objective_index_common.stable_seed`` (the same words in
this protocol). File I/O is ``optimization_common``'s.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Tuple

from research import objective_index_common as oic
from research import optimization_common as oc


ROOT = oc.ROOT
RESULTS = oc.RESULTS
PACKAGE = ROOT / "plan" / "phase2_efficiency"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PROTOCOL_ID = "luminal-phase2-assurance-efficiency-1.0"
RUN_NAME = "efficiency_20260925"
NEXT_ROUND_RUN = RESULTS / "next_round_20260925"

stable_seed = oic.stable_seed

DEVELOPMENT = (800000, 800099)
CONFIRMATION = (980000, 980199)
FAMILIES = ("scalar", "vector", "mixed", "dependency", "aliasing")
BUDGETS: Tuple[float, ...] = (0.01, 0.1, 1.0)
PRIMARY_BUDGET = 0.1
EXTERNAL_SECONDS = 20.0
WALL_CAP_HOURS = 24.0
SEED_ARM_ORDER = 2026092701
SEED_BOOTSTRAP = 2026092702
RESAMPLES = 10_000
PERCENTILES = (0.0125, 0.9875)

FIXED_WORK = {"aggregate_nodes": 10_000, "aggregate_validations": 100_000,
              "slice_nodes": 2048}
MODE_KEYS = ("work:10000", "wall:0.01", "wall:0.1", "wall:1.0", "serial")

# The frozen next-round candidate: A4 catalog, depth-first traversal.
BASELINE_CELL = {"catalog": "a4", "traversal": "dfs"}

EXPECTED_ROWS = {"ranker_isolation_replay": 420, "development_fixed_work": 600,
                 "development_wall_primary": 600, "confirmation_fixed_work": 2000,
                 "confirmation_wall": 6000, "public": 280, "export": 624}

DEVELOPMENT_GATE = {"fixed_work_compile_ratio_max": 0.9,
                    "wall_primary_mean_log_J_ratio_max": 0.0}
CONFIRMATION_GATE = {"fixed_work_compile_ratio_upper_max": 0.8,
                     "wall_primary_J_ratio_upper_max": 1.01}


def run_dir(suffix=None) -> Path:
    return RESULTS / (RUN_NAME if suffix is None else f"{RUN_NAME}_{suffix}")


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def check_protocol_constants() -> dict:
    p = load_protocol()
    checks = {
        "protocol_id": (p["protocol_id"], PROTOCOL_ID),
        "development": ((p["development"]["first_seed"], p["development"]["last_seed"]),
                        DEVELOPMENT),
        "confirmation": ((p["confirmation"]["first_seed"], p["confirmation"]["last_seed"]),
                         CONFIRMATION),
        "budgets": (tuple(p["wall_budgets_seconds"]), BUDGETS),
        "primary": (p["primary_wall_budget_seconds"], PRIMARY_BUDGET),
        "external": (float(p["external_timeout_seconds"]), EXTERNAL_SECONDS),
        "wall_cap": (float(p["measurement_wall_cap_hours"]), WALL_CAP_HOURS),
        "arm_order": (p["seeds"]["arm_order"], SEED_ARM_ORDER),
        "bootstrap": (p["seeds"]["bootstrap"], SEED_BOOTSTRAP),
        "resamples": (p["statistics"]["resamples"], RESAMPLES),
        "percentiles": (tuple(p["statistics"]["two_endpoint_percentiles"]), PERCENTILES),
        "fixed_nodes": (p["fixed_work"]["aggregate_nodes"], FIXED_WORK["aggregate_nodes"]),
        "fixed_validations": (p["fixed_work"]["aggregate_validations"],
                              FIXED_WORK["aggregate_validations"]),
        "slice_nodes": (p["fixed_work"]["slice_nodes"], FIXED_WORK["slice_nodes"]),
        "mode_keys": (tuple(p["mode_keys"]), MODE_KEYS),
        "expected_rows": (p["expected_rows"], EXPECTED_ROWS),
        "development_gate": ({k: p["development_gate"][k] for k in DEVELOPMENT_GATE},
                             DEVELOPMENT_GATE),
        "confirmation_gate": ({k: p["confirmation_gate"][k] for k in CONFIRMATION_GATE},
                              CONFIRMATION_GATE),
        "repetitions": ((p["development"]["repetitions"], p["confirmation"]["repetitions"]),
                        (3, 5)),
    }
    mismatches = {n: {"package": a, "module": b} for n, (a, b) in checks.items() if a != b}
    return {"checked": len(checks), "mismatches": mismatches,
            "status": "PASS" if checks and not mismatches else "FAIL"}


# --------------------------------------------------------------------------
# Measurement wall-time ledger
# --------------------------------------------------------------------------


def ledger_path(run: Path) -> Path:
    return Path(run) / "MEASUREMENT_WALL_LEDGER.jsonl"


def measured_hours(run: Path) -> float:
    total = 0.0
    for row in oc.read_rows(ledger_path(run)):
        total += float(row["process_seconds"])
    return total / 3600.0


def charge(run: Path, stage: str, key: str, process_seconds: float) -> None:
    oc.append_row(ledger_path(run), {"stage": stage, "key": key,
                                     "process_seconds": process_seconds,
                                     "utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})


def cap_reached(run: Path) -> bool:
    return measured_hours(run) >= WALL_CAP_HOURS


def source_hashes(names) -> Dict[str, str]:
    return {name: oc.file_sha256(ROOT / name) for name in names}
