"""HID-search-v2 stage B: bounded input-only boundary discovery (SEARCH.md section 3).

A specified heuristic, not an optimal partition solver. It owns its own candidate
graph (a private ``NodeFactory``), starts from one leaf covering [0, n), and splits
one parent interval at a time, pricing every trial as the COMPLETE serialized
full-input archive of the flat concatenation of its leaves (shared subgraphs and
reference costs included). Intervals are half-open and zero-based.

Leaf builder (shortest-period-only leaf pricing, explicitly a heuristic): the
literal node and, when the existing ``shortest_period`` owner returns p <= 256 with
at least two copies, the periodic node; each priced as a standalone archive of the
slice; the shorter wins, literal on a tie. The shortest period need not minimize
encoded bytes across all periods.

Coarse round: every parent with length >= 64, left to right, at the distinct cuts
{a+1, b-1} U {a + floor(j(b-a)/32) : j = 1..31}; trials ranked by (archive length,
parent start, cut, archive bytes); the best coarse trial is refined (up to five
levels) whether or not it improves; the best coarse/refined trial is committed only
if strictly shorter than the current state. Stops at eight segments, on no strict
improvement, or when a deterministic charge cannot be paid; on exhaustion the best
full-input archive actually serialized so far is offered.

Caps: 512 distinct partition serializations (including the initial state), 2,048
cached leaves, total shortest-period length charge <= 256 n; each leaf is charged
(length + one cache slot, atomically) before its uncached call, each partition one
trial before its serialization. Leaf standalone serializations are counted
separately. Every full-input trial is checked against the rule/depth limits and
decoded by the independent decoder; a disagreement is fatal.

HID-search-v3a (protocols/hierarchy_search_v3a/SEARCH.md) adds an explicit
``BoundaryPolicy`` to the same search: ``refinement_seed_count`` k refines the k best
coarse trials with distinct resulting partitions, level-major then seed-rank-major,
each with its own local pool (its parent's coarse trials plus its own refinements);
caches and charges are shared, the global winner is chosen over every trial, and the
commit stays strict. k = 1 is the search-v2 behaviour byte for byte (same telemetry,
same ``BoundaryConfig`` serialization). An optional ``TraceObserver`` records one event
per trial request in call order; it only appends, adds no charged operation and is
never read by the search.
"""
from __future__ import annotations

import hashlib
import math
from dataclasses import asdict, dataclass

from .candidates import shortest_period
from .consensus import periodic
from .decode import decode_archive
from .model import NodeFactory, count_reachable, to_model
from .wire import serialize_model


@dataclass(frozen=True)
class BoundaryConfig:
    max_segments: int = 8
    parent_min_bits: int = 64
    child_min_bits: int = 1
    coarse_grid_denominator: int = 32
    max_refinement_levels: int = 5
    refinement_grid_denominator: int = 16
    refinement_offset: int = 8
    root_trial_cap: int = 512
    cached_leaf_cap: int = 2048
    length_charge_multiplier: int = 256
    leaf_period_max: int = 256
    max_rules: int = 4096
    max_depth: int = 64

    def as_dict(self) -> dict:
        return asdict(self)


@dataclass(frozen=True)
class BoundaryPolicy:
    """How many ranked coarse trials are refined per round (SEARCH.md section 3)."""

    refinement_seed_count: int = 1
    schedule: str = "level_major_then_fixed_coarse_seed_rank"
    seed_selection: str = "distinct_resulting_partitions_ranked_by_length_parent_start_cut_bytes"
    seed_pool: str = "all_coarse_trials_of_seed_parent_plus_own_refinement_trials"

    def __post_init__(self):
        if self.refinement_seed_count < 1:
            raise ValueError("refinement_seed_count must be >= 1")

    def as_dict(self) -> dict:
        return asdict(self)


K1 = BoundaryPolicy()
TRACE_SCHEMA = "hid-boundary-trace-v1"
TRACE_MAX_EVENTS = 8192
_CHARGES = ("root_trials", "leaf_cache", "leaf_length_charge")


class TraceOverflow(RuntimeError):
    """More trial events than the defensive bound: a trace failure, never truncation."""


class TraceObserver:
    """Direct observational trace of one boundary-search invocation (append only)."""

    def __init__(self, max_events: int = TRACE_MAX_EVENTS) -> None:
        self.max_events = max_events
        self.events: list[dict] = []
        self.summary: list[dict] = []

    def event(self, ev: dict) -> None:
        if len(self.events) >= self.max_events:
            raise TraceOverflow(f"more than {self.max_events} boundary trial events")
        ev["position"] = len(self.events)
        self.events.append(ev)

    def mark(self, item: dict) -> None:
        self.summary.append(item)

    def as_dict(self) -> dict:
        return {"schema": TRACE_SCHEMA, "max_events": self.max_events,
                "event_count": len(self.events), "events": self.events,
                "summary": self.summary}


class DecodeMismatch(RuntimeError):
    """A full-input candidate decodes to a different string: fatal, never a fallback."""


class _Cap(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class BoundarySearch:
    def __init__(self, x: str, cfg: BoundaryConfig = BoundaryConfig(),
                 policy: BoundaryPolicy = K1, observer: TraceObserver | None = None) -> None:
        self.x, self.n, self.cfg = x, len(x), cfg
        self.policy, self.observer = policy, observer
        self.f = NodeFactory()
        self.leaves: dict[tuple[int, int], tuple] = {}
        self.parts: dict[tuple[int, ...], bytes | None] = {}
        self.charge_length = 0
        self.length_cap = cfg.length_charge_multiplier * self.n
        self.counts = {"root_trials": 0, "leaf_cache": 0, "leaf_length_charge": 0,
                       "leaf_serializations": 0, "leaf_periodic_chosen": 0,
                       "graph_rejections": 0, "decoded": 0, "duplicate_archives": 0,
                       "rounds": 0, "commits": 0, "coarse_trials": 0, "refine_trials": 0}
        self.seen_archives: set[bytes] = set()
        self.best_seen: tuple[int, int, bytes, tuple] | None = None
        self.seq = 0
        self.rounds: list[dict] = []

    # -- deterministic charges ------------------------------------------------

    def leaf(self, a: int, b: int):
        got = self.leaves.get((a, b))
        if got is not None:
            return got[0]
        L = b - a
        if len(self.leaves) + 1 > self.cfg.cached_leaf_cap:
            raise _Cap("cached_leaf_cap")
        if self.charge_length + L > self.length_cap:
            raise _Cap("leaf_length_charge_cap")
        self.charge_length += L                 # both charges together, before the call
        self.counts["leaf_length_charge"] = self.charge_length
        f, s = self.f, self.x[a:b]
        lit = f.literal(s)
        best = (len(serialize_model(to_model(lit), L)), 0, lit)
        self.counts["leaf_serializations"] += 1
        p = shortest_period(s)
        if p <= self.cfg.leaf_period_max and L // p >= 2:
            node = periodic(f, s, p)
            size = len(serialize_model(to_model(node), L))
            self.counts["leaf_serializations"] += 1
            if size < best[0]:
                best = (size, 1, node)
                self.counts["leaf_periodic_chosen"] += 1
        self.leaves[(a, b)] = (best[2], best[0], p)
        self.counts["leaf_cache"] = len(self.leaves)
        return best[2]

    def evaluate(self, cuts: tuple[int, ...]) -> bytes | None:
        """Complete archive of the partition at ``cuts`` (interior cut positions)."""
        if cuts in self.parts:
            return self.parts[cuts]
        bounds = (0,) + cuts + (self.n,)
        kids = [self.leaf(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)]
        if self.counts["root_trials"] + 1 > self.cfg.root_trial_cap:
            raise _Cap("root_trial_cap")
        self.counts["root_trials"] += 1
        root = self.f.concat(kids)
        if root.depth > self.cfg.max_depth or count_reachable(root) > self.cfg.max_rules:
            self.counts["graph_rejections"] += 1
            self.parts[cuts] = None
            return None
        archive = serialize_model(to_model(root), self.n)
        if archive in self.seen_archives:
            self.counts["duplicate_archives"] += 1
        else:
            self.seen_archives.add(archive)
            self.counts["decoded"] += 1
            if decode_archive(archive) != self.x:
                raise DecodeMismatch(f"boundary partition {cuts} does not decode to the input")
        self.parts[cuts] = archive
        self.seq += 1
        if self.best_seen is None or len(archive) < self.best_seen[0]:
            self.best_seen = (len(archive), self.seq, archive, cuts)
        return archive

    # -- search ----------------------------------------------------------------

    def coarse_cuts(self, a: int, b: int) -> list[int]:
        k = self.cfg.coarse_grid_denominator
        cand = {a + 1, b - 1} | {a + (j * (b - a)) // k for j in range(1, k)}
        return sorted(c for c in cand if a < c < b)

    def _charges(self) -> dict:
        return {k: self.counts[k] for k in _CHARGES}

    def _request(self, cuts: tuple[int, ...], info: dict) -> bytes | None:
        """``evaluate`` with one observational trace event (when an observer is set)."""
        obs = self.observer
        if obs is None:
            return self.evaluate(cuts)
        ev = dict(info, partition=list(cuts), pre=self._charges(), cache_hit=cuts in self.parts)
        try:
            arc = self.evaluate(cuts)
        except _Cap as cap:
            ev.update(post=self._charges(), outcome="cap_blocked", cap=cap.reason)
            obs.event(ev)
            raise
        if arc is None:
            ev["outcome"] = "cached_graph_rejection" if ev["cache_hit"] else "new_graph_rejection"
        else:
            ev["outcome"] = "cached_admissible" if ev["cache_hit"] else "new_admissible"
            ev["archive_bytes"] = len(arc)
            ev["archive_sha256"] = hashlib.sha256(arc).hexdigest()
        ev["post"] = self._charges()
        obs.event(ev)
        return arc

    def _mark(self, kind: str, cuts, archive: bytes | None, **extra) -> None:
        if self.observer is not None:
            self.observer.mark(dict(extra, kind=kind, cuts=list(cuts),
                                    archive_bytes=None if archive is None else len(archive),
                                    archive_sha256=None if archive is None
                                    else hashlib.sha256(archive).hexdigest()))

    def run(self, offer=None) -> dict:
        """Run B; ``offer(archive)`` is called on every commit and on the final output."""
        cfg, k = self.cfg, self.policy.refinement_seed_count
        cuts: tuple[int, ...] = ()
        stop, unresolved = None, None
        current = None
        try:
            current = self._request(cuts, {"round": 0, "phase": "initial"})
            if current is None:
                raise RuntimeError("the initial single-leaf partition violates graph limits")
            self._mark("initial", cuts, current)
            while True:
                if len(cuts) + 1 >= cfg.max_segments:
                    stop = "max_segments"
                    break
                bounds = (0,) + cuts + (self.n,)
                parents = [(bounds[i], bounds[i + 1]) for i in range(len(bounds) - 1)
                           if bounds[i + 1] - bounds[i] >= cfg.parent_min_bits]
                if not parents:
                    stop = "no_eligible_parent"
                    break
                self.counts["rounds"] += 1
                rnd = {"round": self.counts["rounds"], "segments_before": len(cuts) + 1}
                self.rounds.append(rnd)
                trials: list[tuple] = []      # (len, parent start, cut, bytes, new cuts)
                per_parent: dict[int, list[tuple]] = {}

                def trial(a, b, c, stage, seed=None):
                    new = tuple(sorted(cuts + (c,)))
                    info = {"round": rnd["round"], "phase": stage, "current": list(cuts),
                            "parent": [a, b], "cut": c}
                    if seed is not None:
                        info.update(seed_rank=seed["rank"], level=seed["levels"] + 1)
                    arc = self._request(new, info)
                    self.counts[f"{stage}_trials"] += 1
                    if arc is None:
                        return
                    t = (len(arc), a, c, arc, new)
                    trials.append(t)
                    if seed is None:
                        per_parent.setdefault(a, []).append(t)
                    else:
                        seed["pool"].append(t)

                unresolved = {"round": rnd["round"], "phase": "coarse"}
                for a, b in parents:
                    for c in self.coarse_cuts(a, b):
                        trial(a, b, c, "coarse")
                if not trials:
                    stop = "no_admissible_trial"
                    unresolved = None
                    break
                seeds, taken = [], set()
                for t in sorted(trials, key=lambda t: t[:4]):
                    if len(seeds) == k:
                        break
                    if t[4] in taken:
                        continue
                    taken.add(t[4])
                    a, c = t[1], t[2]
                    b = next(bb for aa, bb in parents if aa == a)
                    r = math.ceil((b - a) / cfg.coarse_grid_denominator)
                    lo, hi = max(a + 1, c - r), min(b - 1, c + r)
                    state = {"round": rnd["round"], "phase": "refinement", "parent": [a, b],
                             "bracket": [lo, hi], "cut": c, "levels_done": 0}
                    if k > 1:
                        state["seed_rank"] = len(seeds)
                    seeds.append({"rank": len(seeds), "a": a, "b": b, "c": c, "lo": lo,
                                  "hi": hi, "levels": 0, "step": None, "active": True,
                                  "coarse_cut": c, "coarse_bytes": t[0],
                                  "pool": list(per_parent[a]), "unresolved": state})
                top = seeds[0]
                rnd.update(coarse_parent=[top["a"], top["b"]], coarse_cut=top["c"],
                           coarse_bytes=top["coarse_bytes"])
                for _ in range(cfg.max_refinement_levels):
                    for sd in seeds:
                        if not sd["active"]:
                            continue
                        a, b, c, lo, hi = sd["a"], sd["b"], sd["c"], sd["lo"], sd["hi"]
                        unresolved = sd["unresolved"]
                        if k > 1:
                            unresolved.update(current_level=sd["levels"] + 1,
                                              current_bracket=[lo, hi])
                        step = max(1, math.ceil((hi - lo) / cfg.refinement_grid_denominator))
                        pos = {lo, hi, c} | {c + j * step for j in range(-cfg.refinement_offset,
                                                                         cfg.refinement_offset + 1)}
                        for q in sorted(p for p in pos if lo <= p <= hi):
                            trial(a, b, q, "refine", sd)
                        pb = min(sd["pool"], key=lambda t: (t[0], t[2], t[3]))
                        sd["c"] = c = pb[2]
                        sd["levels"] += 1
                        sd["step"] = step
                        unresolved.update(bracket=[lo, hi], cut=c, levels_done=sd["levels"],
                                          step=step)
                        if step == 1:
                            sd["active"] = False
                            continue
                        sd["lo"], sd["hi"] = max(a + 1, c - step), min(b - 1, c + step)
                    if not any(sd["active"] for sd in seeds):
                        break
                rnd.update(refined_cut=top["c"], last_bracket=[top["lo"], top["hi"]],
                           last_step=top["step"], levels=top["levels"],
                           resolved_to_one_bit=top["step"] == 1)
                if k > 1:
                    rnd["seeds"] = [{"rank": sd["rank"], "parent": [sd["a"], sd["b"]],
                                     "coarse_cut": sd["coarse_cut"],
                                     "coarse_bytes": sd["coarse_bytes"], "refined_cut": sd["c"],
                                     "last_bracket": [sd["lo"], sd["hi"]],
                                     "last_step": sd["step"], "levels": sd["levels"],
                                     "resolved_to_one_bit": sd["step"] == 1,
                                     "local_best_bytes": min(t[0] for t in sd["pool"])}
                                    for sd in seeds]
                    rnd["seed_count"] = len(seeds)
                unresolved = None
                win = min(trials, key=lambda t: t[:4])
                rnd.update(best_parent_start=win[1], best_cut=win[2], best_bytes=win[0],
                           current_bytes=len(current))
                if win[0] < len(current):
                    cuts, current = win[4], win[3]
                    self.counts["commits"] += 1
                    rnd["committed"] = True
                    self._mark("commit", cuts, current, round=rnd["round"])
                    if offer is not None:
                        offer(current)
                else:
                    rnd["committed"] = False
                    stop = "no_strict_improvement"
                    break
        except _Cap as cap:
            stop = cap.reason
        output, output_cuts = current, cuts
        source = "current"
        if stop and stop.endswith("_cap") and self.best_seen is not None and \
                (current is None or self.best_seen[0] < len(current)):
            output, output_cuts = self.best_seen[2], self.best_seen[3]
            source = "best_seen"
        self._mark("final", output_cuts, output, stop_reason=stop, source=source,
                   unresolved=unresolved if stop and stop.endswith("_cap") else None)
        if output is not None and offer is not None:
            offer(output)
        return {"archive": output, "cuts": list(output_cuts), "committed_cuts": list(cuts),
                "segments": len(output_cuts) + 1, "stop_reason": stop,
                "cap_hit": bool(stop and stop.endswith("_cap")),
                "unresolved_refinement": unresolved if stop and stop.endswith("_cap") else None,
                "counts": dict(self.counts), "rounds": self.rounds,
                "archive_bits": None if output is None else 8 * len(output)}


def supplied_partition(x: str, cuts, cfg: BoundaryConfig = BoundaryConfig()) -> dict:
    """Evaluation-only feasible reference: partition at supplied cuts with the same leaf
    builder, sharing and serializer, without charges or search. Never used by inference."""
    srch = BoundarySearch(x, cfg)           # one partition: no cap can bind
    arc = srch.evaluate(tuple(sorted(set(cuts))))
    return {"archive": arc, "cuts": sorted(set(cuts)),
            "leaves": [{"interval": [a, b], "choice": "periodic" if leaf[0].op != 0 else "literal",
                        "standalone_bytes": leaf[1], "shortest_period": leaf[2]}
                       for (a, b), leaf in sorted(srch.leaves.items())]}
