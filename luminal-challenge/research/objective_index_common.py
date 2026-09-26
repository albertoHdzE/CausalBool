"""Shared constants and conventions of the objective-index research protocol 1.0.

``plan/CLAUDE_PHASE2_RESEARCH_PROTOCOL.md`` and its ``phase2_research/PROTOCOL.json``
are the authority. This module owns three things only:

- the protocol constants, read from ``PROTOCOL.json`` and checked against the
  literal values below so that a drifted package fails loudly;
- ``stable_seed``, the one semantic/seed key function of protocol section 7
  (sha256 of compact sorted-key JSON, first 16 hex digits as an unsigned
  integer; never Python ``hash()``);
- the result-directory path.

File I/O, journals, source manifests and logged commands are owned by
``optimization_common`` and are imported from there, not restated.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Tuple

from research import optimization_common as oc


ROOT = oc.ROOT
RESULTS = oc.RESULTS
PACKAGE = ROOT / "plan" / "phase2_research"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PROTOCOL_ID = "luminal-objective-index-research-1.0"
RUN_DIR = RESULTS / "objective_index_20260924"

ARMS: Tuple[str, ...] = (
    "A0_frozen_phase2",
    "A1_deadline_control",
    "A2_product_search",
    "A3_propagated_search",
    "A4_multiscale_search",
)
NEW_ARMS: Tuple[str, ...] = ARMS[1:]
BUDGETS: Tuple[float, ...] = (0.01, 0.1, 1.0)
PRIMARY_BUDGET = 0.1
EXTERNAL_SECONDS = 20.0

LIMITS: Dict[str, float] = {
    "aggregate_nodes": 1_000_000,
    "aggregate_validation_attempts": 100_000,
    "query_active_seconds": 0.1,
    "slice_seconds": 0.002,
    "slice_nodes": 2048,
    "frontier_per_query": 4096,
    "resident_queries": 8,
}

SEED_POOL = 2026092501
SEED_SHUFFLED = 2026092502
SEED_SPLIT = 2026092503
SEED_BOOTSTRAP = 2026092504
SEED_ARM_ORDER = 2026092505
RANDOM_ORDER_SEEDS: Tuple[int, ...] = tuple(range(2026092510, 2026092520))

COHORTS = {
    "development": (800000, 800099),
    "compiler_evaluation": (910000, 910199),
    "model_development_pool": (920000, 920199),
    "model_evaluation_pool": (930000, 930399),
}
FIXTURE_QUOTAS = {"development": 3, "evaluation": 6}


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def check_protocol_constants() -> dict:
    """Every literal above must equal the frozen package; the count is printed."""

    protocol = load_protocol()
    checks = {
        "protocol_id": (protocol["protocol_id"], PROTOCOL_ID),
        "arms": (tuple(protocol["arms"]), ARMS),
        "budgets": (tuple(protocol["budgets_seconds"]), BUDGETS),
        "primary": (protocol["primary_budget_seconds"], PRIMARY_BUDGET),
        "external": (float(protocol["external_seconds"]), EXTERNAL_SECONDS),
        "limits": (protocol["limits"], LIMITS),
        "seed_pool": (protocol["seeds"]["pool"], SEED_POOL),
        "seed_shuffled": (protocol["seeds"]["shuffled_labels"], SEED_SHUFFLED),
        "seed_split": (protocol["seeds"]["split"], SEED_SPLIT),
        "seed_bootstrap": (protocol["seeds"]["bootstrap"], SEED_BOOTSTRAP),
        "seed_arm_order": (protocol["seeds"]["arm_order"], SEED_ARM_ORDER),
        "random_order": (tuple(protocol["seeds"]["random_order"]), RANDOM_ORDER_SEEDS),
        "development": ((protocol["cohorts"]["development"]["first"],
                         protocol["cohorts"]["development"]["last"]), COHORTS["development"]),
        "compiler_evaluation": ((protocol["cohorts"]["compiler_evaluation"]["first"],
                                 protocol["cohorts"]["compiler_evaluation"]["last"]),
                                COHORTS["compiler_evaluation"]),
        "model_development_pool": ((protocol["cohorts"]["model_development_pool"]["first"],
                                    protocol["cohorts"]["model_development_pool"]["last"]),
                                   COHORTS["model_development_pool"]),
        "model_evaluation_pool": ((protocol["cohorts"]["model_evaluation_pool"]["first"],
                                   protocol["cohorts"]["model_evaluation_pool"]["last"]),
                                  COHORTS["model_evaluation_pool"]),
    }
    mismatches = {name: {"package": a, "module": b} for name, (a, b) in checks.items()
                  if a != b}
    return {"checked": len(checks), "mismatches": mismatches,
            "status": "PASS" if checks and not mismatches else "FAIL"}


def stable_seed(parts: object) -> int:
    """Protocol section 7: sha256 of compact sorted-key JSON, first 16 hex digits."""

    text = json.dumps(parts, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
                      allow_nan=False)
    return int(hashlib.sha256(text.encode("utf-8")).hexdigest()[:16], 16)
