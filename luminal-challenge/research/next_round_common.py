"""Constants and ledgers of the Phase 2 next round (protocol 1.0).

``plan/CLAUDE_PHASE2_NEXT_ROUND.md`` and ``plan/phase2_next_round/PROTOCOL.json``
are the authority. This module owns only:

- the protocol constants, read from ``PROTOCOL.json`` and compared with the
  literals below, so a drifted package fails loudly (the count is printed);
- the run directory of this round;
- the measurement wall-time ledger (section 8: at most 24 hours of measurement
  process wall time, checked before each worker launch, failed attempts and
  reruns included).

The seed function is ``objective_index_common.stable_seed``: the definition in
this protocol is word for word the earlier one, so it is imported, not restated.
File I/O, journals and source manifests are ``optimization_common``'s.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Dict, Optional, Tuple

from research import objective_index_common as oic
from research import optimization_common as oc


ROOT = oc.ROOT
RESULTS = oc.RESULTS
PACKAGE = ROOT / "plan" / "phase2_next_round"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PROTOCOL_ID = "luminal-phase2-next-round-1.0"
RUN_NAME = "next_round_20260925"

stable_seed = oic.stable_seed

BUDGETS: Tuple[float, ...] = (0.01, 0.1, 1.0)
PRIMARY_BUDGET = 0.1
EXTERNAL_SECONDS = 20.0
WALL_CAP_HOURS = 24.0

DEVELOPMENT = (800000, 800099)
CONFIRMATION = (960000, 960199)
LEARNING_POOL = (970000, 970399)

SEED_ARM_ORDER = 2026092601
SEED_BOOTSTRAP = 2026092602
SEED_TRAINING_DRAW = 2026092603
SEED_POOL = 2026092604
SEED_SHUFFLED = 2026092605
RANDOM_ORDER_SEEDS: Tuple[int, ...] = tuple(range(2026092610, 2026092620))

RESAMPLES = 10_000
PRIMARY_PERCENTILES = (0.025, 0.975)
CANDIDATE_PERCENTILES = (0.00625, 0.99375)
LEARNING_PERCENTILES = (0.008333333333333333, 0.9916666666666667)

LEARNING = {"training_count": 20, "primary_prefix": 32, "evaluation_fixtures": 30,
            "per_family": 6, "minimum_informative_development": 10,
            "minimum_informative_evaluation": 20,
            "minimum_informative_evaluation_per_family": 3,
            "minimum_acquisition_program_fraction": 0.1, "minimum_yield_difference": 0.05,
            "ordering_count": 14}

TARGETS = {"quality_route": {"upper_J_ratio": 0.98, "upper_compile_ratio": 1.1},
           "efficiency_route": {"upper_compile_ratio": 0.8, "upper_J_ratio": 1.01}}

# The repaired A4 values held fixed across the 2x2 ablation (plan section 4).
A4_LIMITS: Dict[str, float] = {
    "slice_seconds": 0.002, "slice_nodes": 2048, "resident_queries": 8,
    "query_active_seconds": 0.1, "aggregate_nodes": 1_000_000,
    "aggregate_validation_attempts": 100_000, "frontier_per_query": 4096,
}

# The four cells of the ablation plus the earlier optimizer (section 4).
CELLS = {
    "cell_a3cat_dfs": {"catalog": "a3", "traversal": "dfs"},
    "cell_a3cat_heap": {"catalog": "a3", "traversal": "heap"},
    "cell_a4cat_dfs": {"catalog": "a4", "traversal": "dfs"},
    "cell_a4cat_heap": {"catalog": "a4", "traversal": "heap"},
}
REPAIRED_A4 = "cell_a4cat_heap"
EARLIER = "earlier_cap512_wider"
EARLIER_SPEC = {"config": "cap512_wider", "build": "cached", "search_arm": "structural_bound",
                "model_depth": None}
DEVELOPMENT_ARMS: Tuple[str, ...] = tuple(sorted(CELLS)) + (EARLIER,)


def run_dir(suffix: Optional[int] = None) -> Path:
    name = RUN_NAME if suffix is None else f"{RUN_NAME}_{suffix}"
    return RESULTS / name


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def check_protocol_constants() -> dict:
    """Every literal above equals the locked package; mismatches are listed."""

    p = load_protocol()
    learning = p["learning"]
    checks = {
        "protocol_id": (p["protocol_id"], PROTOCOL_ID),
        "budgets": (tuple(p["budgets_seconds"]), BUDGETS),
        "primary": (p["primary_budget_seconds"], PRIMARY_BUDGET),
        "external": (float(p["external_timeout_seconds"]), EXTERNAL_SECONDS),
        "wall_cap": (float(p["measurement_wall_cap_hours"]), WALL_CAP_HOURS),
        "development": (tuple(p["development"]["seeds"]), DEVELOPMENT),
        "confirmation": (tuple(p["confirmation"]["seeds"]), CONFIRMATION),
        "learning_pool": (tuple(learning["fresh_pool_seeds"]), LEARNING_POOL),
        "arm_order": (p["seeds"]["arm_order"], SEED_ARM_ORDER),
        "bootstrap": (p["seeds"]["bootstrap"], SEED_BOOTSTRAP),
        "training_draw": (p["seeds"]["training_draw"], SEED_TRAINING_DRAW),
        "pool": (p["seeds"]["pool"], SEED_POOL),
        "shuffled": (p["seeds"]["shuffled_labels"], SEED_SHUFFLED),
        "random_order": (tuple(p["seeds"]["random_order"]), RANDOM_ORDER_SEEDS),
        "resamples": (p["statistics"]["resamples"], RESAMPLES),
        "primary_percentiles": (tuple(p["statistics"]["primary_head_to_head_percentiles"]),
                                PRIMARY_PERCENTILES),
        "candidate_percentiles": (
            tuple(p["statistics"]["new_candidate_four_endpoints_percentiles"]),
            CANDIDATE_PERCENTILES),
        "learning_percentiles": (tuple(p["statistics"]["learning_three_contrasts_percentiles"]),
                                 LEARNING_PERCENTILES),
        "targets": (p["practical_targets"]["quality_route"], TARGETS["quality_route"]),
        "targets_eff": (p["practical_targets"]["efficiency_route"],
                        TARGETS["efficiency_route"]),
    }
    for name in ("training_count", "primary_prefix", "evaluation_fixtures", "per_family",
                 "minimum_informative_development", "minimum_informative_evaluation",
                 "minimum_informative_evaluation_per_family",
                 "minimum_acquisition_program_fraction", "minimum_yield_difference",
                 "ordering_count"):
        checks[f"learning.{name}"] = (learning[name], LEARNING[name])
    mismatches = {n: {"package": a, "module": b} for n, (a, b) in checks.items() if a != b}
    return {"checked": len(checks), "mismatches": mismatches,
            "status": "PASS" if checks and not mismatches else "FAIL"}


# --------------------------------------------------------------------------
# Measurement wall-time ledger (section 8)
# --------------------------------------------------------------------------


def ledger_path(run: Path) -> Path:
    return Path(run) / "MEASUREMENT_WALL_LEDGER.jsonl"


def measured_hours(run: Path) -> float:
    """Sum of every retained measurement process wall time, failed ones included."""

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
