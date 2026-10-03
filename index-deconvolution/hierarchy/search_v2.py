"""HID-search-v2 orchestrator: six cumulative arms over the unchanged HID-v1 language.

``infer_v2(bits, config)`` receives the bit string and a frozen ``SearchV2Config``,
nothing else. It starts from the complete literal archive, runs every included stage
in order and keeps the smallest COMPLETE archive; on equal length the earlier
incumbent stays (raw, then L, P, C, D, G, B; periods ascending within a stage).

  L  the original ``infer(bits, FULL)``, unchanged and rerun inside every arm;
  P  first-block templates, original grid, local patches;
  C  consensus templates, original grid, local patches;
  D  consensus templates, the remaining dense periods, local patches;
  G  consensus templates, the whole dense grid, one global patch;
  B  bounded input-only boundary discovery (segmentation.py).

Every admissible new full-input candidate is serialized with the existing writer and
decoded by the independent decoder; a disagreement raises ``DecodeMismatch`` (fatal).
Final selection compares complete archive lengths only. Telemetry counts work per
stage (attempts, gate and graph rejections, serializations, decodes, duplicates,
strict improvements, incumbent after the stage, wall time); it never contains
anything but quantities computed from the input.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass, field

from .consensus import (Residual, consensus_word, dense_grid, first_block_word,
                        global_proposal, local_proposal, original_grid)
from .decode import decode_archive
from .infer import FULL, infer
from .model import NodeFactory, check_bits, count_reachable, to_model
from .segmentation import BoundaryConfig, BoundarySearch, DecodeMismatch
from .wire import encode_literal, serialize_model

STAGE_ORDER = ("L", "P", "C", "D", "G", "B")
ORIGINAL_GRID = tuple(range(1, 33)) + (64, 128, 256)


@dataclass(frozen=True)
class SearchV2Config:
    """Every knob of one HID-search-v2 arm (SEARCH.md, study_contract.json)."""

    name: str
    stages: tuple
    legacy_config_sha256: str = FULL.sha256()
    period_max: int = 256
    original_grid: tuple = ORIGINAL_GRID
    consensus_tie_bit: str = "0"
    residual_divisor: int = 16
    local_block_bits: int = 1024
    local_patch_max: int = 64
    max_rules: int = 4096
    max_depth: int = 64
    first_local_candidate_cap: int = 35
    consensus_local_candidate_cap: int = 256
    consensus_global_candidate_cap: int = 256
    boundary: BoundaryConfig = field(default_factory=BoundaryConfig)

    def __post_init__(self):
        if tuple(self.stages) != STAGE_ORDER[:len(self.stages)] or not self.stages:
            raise ValueError(f"stages must be a nonempty prefix of {STAGE_ORDER}")
        if self.legacy_config_sha256 != FULL.sha256():
            raise ValueError("stage L must be the unchanged legacy FULL configuration")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["stages"] = list(self.stages)
        d["original_grid"] = list(self.original_grid)
        return d

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode()).hexdigest()


ARMS = {
    "hid_legacy": SearchV2Config("hid_legacy", ("L",)),
    "hid_first_local": SearchV2Config("hid_first_local", ("L", "P")),
    "hid_consensus_local": SearchV2Config("hid_consensus_local", ("L", "P", "C")),
    "hid_dense_local": SearchV2Config("hid_dense_local", ("L", "P", "C", "D")),
    "hid_global": SearchV2Config("hid_global", ("L", "P", "C", "D", "G")),
    "hid_full": SearchV2Config("hid_full", STAGE_ORDER),
}


@dataclass(frozen=True)
class V2Result:
    archive: bytes
    selected_stage: str
    archive_bits: int
    literal_bits: int
    telemetry: dict
    trace: tuple
    config_name: str
    config_sha256: str


class _Incumbent:
    def __init__(self, raw: bytes) -> None:
        self.archive, self.stage, self.detail = raw, "raw", None
        self.trace: list[dict] = []

    def offer(self, archive: bytes, stage: str, detail=None) -> bool:
        if len(archive) < len(self.archive):
            self.archive, self.stage, self.detail = archive, stage, detail
            self.trace.append({"stage": stage, "detail": detail, "archive_bits": 8 * len(archive)})
            return True
        return False


def _stage_counter() -> dict:
    return {"periods_attempted": 0, "gate_rejections": 0, "graph_rejections": 0,
            "serialized": 0, "decoded": 0, "duplicate_archives": 0,
            "strict_improvements": 0, "best_candidate_bits": None, "best_period": None}


class _Templates:
    """Shared within ONE invocation: consensus words and residuals per period."""

    def __init__(self, x: str, cfg: SearchV2Config) -> None:
        self.x, self.n, self.cfg = x, len(x), cfg
        self.x_int = int(x, 2)
        self.limit = self.n // cfg.residual_divisor
        self.consensus: dict[int, Residual] = {}
        self.first: dict[int, Residual] = {}
        self.seen: set[bytes] = set()

    def residual(self, p: int, kind: str) -> Residual:
        cache = self.consensus if kind == "consensus" else self.first
        got = cache.get(p)
        if got is None:
            word = consensus_word(self.x, p) if kind == "consensus" else first_block_word(self.x, p)
            got = Residual(self.x, self.x_int, word, self.limit)
            cache[p] = got
        return got

    def run_stage(self, periods, kind: str, placement: str, inc: _Incumbent, stage: str,
                  cap: int, counts: dict) -> None:
        cfg = self.cfg
        for p in periods:
            if counts["serialized"] >= cap:
                counts["candidate_cap_hit"] = True
                break
            counts["periods_attempted"] += 1
            res = self.residual(p, kind)
            if res.positions is None:
                counts["gate_rejections"] += 1
                continue
            f = NodeFactory()
            if placement == "local":
                root = local_proposal(f, self.x, res, p, cfg.local_block_bits,
                                      cfg.local_patch_max, cfg.residual_divisor)
            else:
                root = global_proposal(f, res, p)
            if root.depth > cfg.max_depth or count_reachable(root) > cfg.max_rules:
                counts["graph_rejections"] += 1
                continue
            archive = serialize_model(to_model(root), self.n)
            counts["serialized"] += 1
            if archive in self.seen:
                counts["duplicate_archives"] += 1
            else:
                self.seen.add(archive)
                counts["decoded"] += 1
                if decode_archive(archive) != self.x:
                    raise DecodeMismatch(f"stage {stage} period {p} does not decode to the input")
            bits = 8 * len(archive)
            if counts["best_candidate_bits"] is None or bits < counts["best_candidate_bits"]:
                counts["best_candidate_bits"], counts["best_period"] = bits, p
            if inc.offer(archive, stage, {"period": p, "errors": res.count}):
                counts["strict_improvements"] += 1


def infer_v2(bits: str, config: SearchV2Config) -> V2Result:
    """Best complete archive found by the arm ``config`` (literal fallback included)."""
    check_bits(bits)
    if not isinstance(config, SearchV2Config):
        raise TypeError("config must be a SearchV2Config")
    raw = encode_literal(bits)
    inc = _Incumbent(raw)
    n = len(bits)
    tele: dict = {"arm": config.name, "stages_included": list(config.stages), "n_bits": n,
                  "stages": {}}
    t_all = time.perf_counter()
    if n == 0:
        tele["stop"] = "empty_input"
        return V2Result(raw, "raw", 8 * len(raw), 8 * len(raw), tele, (), config.name,
                        config.sha256())
    tpl = _Templates(bits, config)
    for stage in config.stages:
        t0 = time.perf_counter()
        if stage == "L":
            res = infer(bits, FULL)
            improved = inc.offer(res.archive, "L", {"best_source": res.best_source})
            st = {"archive_sha256": hashlib.sha256(res.archive).hexdigest(),
                  "archive_bits": res.archive_bits, "mode": res.mode,
                  "stop_reason": res.stop_reason, "work_units": res.work.get("work_units"),
                  "serialized_unique": res.candidate_counts.get("serialized_unique"),
                  "rule_count": res.rule_count, "dag_depth": res.dag_depth,
                  "best_source": res.best_source, "strict_improvements": int(improved)}
        elif stage == "B":
            srch = BoundarySearch(bits, config.boundary)
            st = {"strict_improvements": 0}

            def offer(arc, st=st):
                if inc.offer(arc, "B", {"cuts": None}):
                    st["strict_improvements"] += 1
            out = srch.run(offer)
            if inc.stage == "B":
                inc.detail = {"cuts": out["cuts"]}
                inc.trace[-1]["detail"] = inc.detail
            st.update({k: out[k] for k in ("cuts", "segments", "stop_reason", "cap_hit",
                                           "unresolved_refinement", "counts", "rounds",
                                           "archive_bits")})
        else:
            st = _stage_counter()
            if stage == "P":
                periods = original_grid(n, config.original_grid, config.period_max)
                tpl.run_stage(periods, "first", "local", inc, "P",
                              config.first_local_candidate_cap, st)
            elif stage == "C":
                periods = original_grid(n, config.original_grid, config.period_max)
                tpl.run_stage(periods, "consensus", "local", inc, "C",
                              config.consensus_local_candidate_cap, st)
            elif stage == "D":
                grid = set(config.original_grid)
                periods = tuple(p for p in dense_grid(n, config.period_max) if p not in grid)
                used = tele["stages"].get("C", {}).get("serialized", 0)
                tpl.run_stage(periods, "consensus", "local", inc, "D",
                              config.consensus_local_candidate_cap - used, st)
            else:
                periods = dense_grid(n, config.period_max)
                tpl.run_stage(periods, "consensus", "global", inc, "G",
                              config.consensus_global_candidate_cap, st)
            st["eligible_periods"] = len(periods)
        st["incumbent_bits_after"] = 8 * len(inc.archive)
        st["incumbent_stage_after"] = inc.stage
        st["wall_s"] = time.perf_counter() - t0
        tele["stages"][stage] = st
    if decode_archive(inc.archive) != bits:
        raise DecodeMismatch("the selected archive does not decode to the input")
    tele["selected_stage"] = inc.stage
    tele["selected_detail"] = inc.detail
    tele["total_wall_s"] = time.perf_counter() - t_all
    return V2Result(inc.archive, inc.stage, 8 * len(inc.archive), 8 * len(raw), tele,
                    tuple(inc.trace), config.name, config.sha256())
