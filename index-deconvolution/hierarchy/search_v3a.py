"""HID-search-v3a policy/config adapter (protocols/hierarchy_search_v3a/SEARCH.md).

Two full-method arms over the one orchestrator ``search_v2.run_arm``:

  hid_full     the accepted search-v2 arm, unchanged object and configuration hash
               (boundary refinement seed count k = 1);
  hid_refine4  the same stages, caps and grammar with k = 4 ranked coarse seeds,
               level-major then seed-rank-major (``segmentation.BoundaryPolicy``).

``SearchV3aConfig`` binds the k = 4 policy, the schedule and the trace schema into
its own hash; ``hid_full`` keeps the search-v2 serialization (no default-valued key
is added). ``infer_v3a`` receives the bit string and a frozen configuration only and
optionally returns the direct stage-B trace; the observer never influences the search.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field

from .search_v2 import ARMS, STAGE_ORDER, SearchV2Config, V2Result, run_arm
from .segmentation import K1, TRACE_MAX_EVENTS, TRACE_SCHEMA, BoundaryPolicy, TraceObserver


@dataclass(frozen=True)
class SearchV3aConfig:
    """A search-v2 full arm plus an explicit boundary policy and trace schema."""

    base: SearchV2Config
    policy: BoundaryPolicy = field(default_factory=BoundaryPolicy)
    trace_schema: str = TRACE_SCHEMA
    trace_max_events: int = TRACE_MAX_EVENTS

    @property
    def name(self) -> str:
        return self.base.name

    def as_dict(self) -> dict:
        return {"base": self.base.as_dict(), "boundary_policy": self.policy.as_dict(),
                "trace_schema": self.trace_schema, "trace_max_events": self.trace_max_events}

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode()).hexdigest()


REFINE4 = SearchV3aConfig(SearchV2Config("hid_refine4", STAGE_ORDER),
                          BoundaryPolicy(refinement_seed_count=4))
ARMS_V3A = {"hid_full": ARMS["hid_full"], "hid_refine4": REFINE4}


def infer_v3a(bits: str, config, trace: bool = False) -> tuple[V2Result, dict | None]:
    """(result, trace sidecar or None) for a search-v2 arm (k = 1) or a v3a arm."""
    if isinstance(config, SearchV3aConfig):
        base, policy, identity = config.base, config.policy, (config.name, config.sha256())
        max_events = config.trace_max_events
    elif isinstance(config, SearchV2Config):
        base, policy, identity, max_events = config, K1, None, TRACE_MAX_EVENTS
    else:
        raise TypeError("config must be a SearchV2Config or a SearchV3aConfig")
    obs = TraceObserver(max_events) if trace else None
    res = run_arm(bits, base, policy, obs, identity)
    if obs is None:
        return res, None
    side = {"config_name": res.config_name, "config_sha256": res.config_sha256,
            "refinement_seed_count": policy.refinement_seed_count,
            "boundary_invocations": [obs.as_dict()] if "B" in base.stages else [],
            "selected_stage": res.selected_stage, "archive_bits": res.archive_bits,
            "archive_sha256": hashlib.sha256(res.archive).hexdigest()}
    return res, side
