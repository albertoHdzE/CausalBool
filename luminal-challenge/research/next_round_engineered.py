"""ENGINEERED VARIANT of ``research/next_round_search.py`` (next round 1.0, Stage E).

Version ``next_round_engineered 1.0``: a byte-for-byte copy of the successor
``research/next_round_search.py`` (sha256 ``PARENT_SOURCE_SHA256`` below) with
ONE engineering change, written in ``ENGINEERING_PLAN.json`` before it was
implemented or measured:

E1. ``Propagation.times_fixpoint`` and ``Propagation.addresses_fixpoint`` revise
    incrementally from a worklist of edges (pairs) incident to operations
    (values) whose domain changed, instead of re-sweeping every edge (pair)
    after any deletion; a child call starts from the assigned decision only,
    because its parent's domains are already a fixpoint. Accessors read one
    merged table. The rules are deletion-only and monotone, so the surviving
    domains -- or the proof of inconsistency -- are the unique greatest
    fixpoint: children, prunes and bounds are unchanged. Only the order and
    grouping of emitted certificates may differ (each certificate is still a
    sound, replayable deletion).

Everything below this paragraph is the parent's text except the two fixpoint
methods, ``Propagation.__init__`` (incidence lists) and the four call sites
that pass ``changed``. The parent's own header follows.

SUCCESSOR VERSION of ``research/objective_index_search.py`` (next round 1.0).

Version ``next_round_search 1.1``. A byte-for-byte copy of the frozen owner
``research/objective_index_search.py`` (sha256 ``FROZEN_SOURCE_SHA256`` below,
authored in the objective-index research protocol 1.0 and measured there),
with only these changes, all listed in ``next_round_20260925/repair/``:

R1 (reporting repair, plan section 3). ``multiscale_optimise.finish`` counted
   a query's interrupted candidate validations only inside the learner branch,
   so the non-model A4 returned zero. They are now accounted for every query:
   ``interrupted_validation_total`` (validations), ``interrupted_validation_
   queries`` (affected queries) and a per-query list, with construction
   interruptions kept separately. Search decisions are unchanged.
R2 (reporting). Each accepted improvement carries its elapsed time, so the
   time-to-target diagnostics of section 4 need no second run.
D  (plan section 4). ``multiscale_optimise`` takes ``catalog`` (``"a4"`` the
   existing ``build_catalog``, or ``"a3"`` ``product_window_plan`` at radius 2)
   and ``traversal`` (``"heap"`` the existing discrepancy heap, or ``"dfs"``
   canonical depth-first, low rank first). Defaults are the repaired A4; the
   default path is the frozen one statement for statement.

The frozen module is untouched and its measured rows keep describing it.

The A1-A4 solver ladder of the objective-index research protocol 1.0.

Protocol sections 3-6. Every arm starts from the same original direct-index
bootstrap, accepts only fully validated strict improvements of J = C*S, and
keeps the codec (``structural_encoding``) as the one owner of index meaning.

What this module owns, and what it takes from elsewhere:

- ``product_caps``/``product_record``: the strict-product domain of section 4.
  Physical address bases come from ``run_structural_experiments.
  physical_address_domain``; targets and four-operation windows from the
  production ``direct_optimizer`` owners; the matched target domain of A1 from
  ``run_structural_experiments.matched_window_record``.
- ``Propagation``: the four sound rules of section 5, each deletion or prune
  emitted as a replayable certificate. Lifetimes are ``direct_contract``'s.
- ``Expander``: one lazy node expansion shared by the A3 depth-first search and
  the A4 discrepancy heap. Ranks are ALWAYS positions in the unfiltered
  ``structural_encoding.options`` list; propagation only skips values, so the
  kth surviving value is never called rank k.
- ``sequential_optimise``: the controller of A1, A2 and A3. A1 and A2 search
  with the unchanged ``structural_search.search``; A3 with the expander.
- ``multiscale_optimise``: A4's five-queue catalog, resumable queries, time
  slices and epoch rebuilds.

The accepted control A0 is not here: it is the accepted ``final_source_v2``
snapshot, measured through ``optimization_frozen_worker`` in its own workspace.

Status vocabulary. ``UNSAT`` is scoped to the exhausted declared domain.
``NO_STRICT_IMPROVEMENT`` is the integer-cap lemma's proof that the window's
caps fall below its lower bounds. Every budget, allowance, frontier or ceiling
stop is an ``UNKNOWN_*`` status and is never reported as ``UNSAT``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass, field as _field
import bisect
import hashlib
import heapq
import time
from typing import Callable, Dict, Iterator, List, Optional, Sequence, Tuple

import machine

import direct_constraints as dk
import direct_contract as dc
import direct_optimizer as dopt
import schema_index as si

from research import objective_index_common as oic
from research import run_structural_experiments as rse
from research import structural_encoding as se
from research import structural_search as ss


__all__ = [
    "ARM_LABELS", "PER_QUERY_LIMITS", "product_caps", "neighborhood_record", "capped_record",
    "product_record",
    "product_window_plan", "Propagation", "Expander", "PropagationStats",
    "propagated_search", "sequential_optimise", "build_catalog", "memory_group",
    "multiscale_optimise", "optimise",
]

VERSION = "next_round_engineered 1.0"
PARENT_SOURCE = "research/next_round_search.py"
PARENT_SOURCE_SHA256 = "b982d4cf62e63d54235237e7032175f893f9f519802f36ff87f7111c5db9c647"
FROZEN_SOURCE = "research/objective_index_search.py"
FROZEN_SOURCE_SHA256 = "8cda157f465b1d23bb3894d8b3226437210d537f03cffd6ed8db523b12c4c7f5"
CATALOGS = ("a4", "a3")
TRAVERSALS = ("heap", "dfs")

ARM_LABELS = oic.NEW_ARMS
CODEC = "structural_rank"
BASE_RADIUS = dk.TIME_SLACK          # 2: the original matched slack
FULL_RANGE = "full"

# The existing per-query safety limits of the accepted research protocol.
PER_QUERY_LIMITS = {
    "query_max_cover": 4096,
    "search_max_nodes": 1_000_000,
    "search_max_candidate_validations": 100_000,
    "query_max_visited": 50_000,
}


# ==========================================================================
# Section 4: strict-product domains
# ==========================================================================


def product_caps(facts: dc.ProgramFacts, times: Dict[int, int], addresses: Dict[str, int],
                 window: Sequence[int], objective: Optional[int] = None) -> dict:
    """``LC``, ``LS``, ``Ccap`` and ``Scap`` of one window at one incumbent.

    ``LC = max(cycle lower bound, 1 + max fixed issue time)`` and
    ``LS = max(memory lower bound, max fixed allocated end)``, empty maxima zero,
    both at least one when ``J0 > 0``. ``objective`` overrides ``J0`` (tests
    check the lemma at every threshold). Every strict improvement satisfies
    ``C >= LC``, ``S >= LS`` and ``C*S <= J0-1``, hence ``C <= (J0-1)//LS`` and
    ``S <= (J0-1)//LC`` (THEORY.md, integer-cap lemma).
    """

    selected = set(window)
    cycles = max(times.values()) + 1
    scratch = dc.footprint(facts, addresses)
    j0 = cycles * scratch if objective is None else objective
    fixed_times = [times[op] for op in range(facts.count) if op not in selected]
    fixed_ends = [addresses[name] + facts.width[name] for name in facts.value_names
                  if facts.producers[name] not in selected]
    lc = max(facts.cycle_lower_bound(), 1 + max(fixed_times) if fixed_times else 0)
    ls = max(facts.memory_lower_bound(), max(fixed_ends) if fixed_ends else 0)
    out = {"J0": j0, "C0": cycles, "S0": scratch, "LC": lc, "LS": ls,
           "fixed_time_max": max(fixed_times) if fixed_times else None,
           "fixed_end_max": max(fixed_ends) if fixed_ends else None}
    if j0 <= 0:
        out.update(status="ZERO_OBJECTIVE", Ccap=None, Scap=None,
                   reason="no strictly smaller nonnegative product than zero")
        return out
    lc, ls = max(lc, 1), max(ls, 1)
    ccap = min(facts.horizon, (j0 - 1) // ls)
    scap = min(machine.SCRATCH_WORDS, (j0 - 1) // lc)
    out.update(LC=lc, LS=ls, Ccap=ccap, Scap=scap)
    if ccap < lc or scap < ls:
        out.update(status="NO_STRICT_IMPROVEMENT",
                   reason=f"caps ({ccap}, {scap}) fall below lower bounds ({lc}, {ls})")
    else:
        out.update(status="OK", reason="")
    return out


def neighborhood_record(identifier: str, program: dict, facts: dc.ProgramFacts,
                        times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int],
                        radius) -> dict:
    """The UNCAPPED neighborhood of one window: the object the lemma speaks about.

    Selected times: incumbent +/- ``radius`` clipped to ``[0, horizon-1]`` (the
    whole horizon for ``radius == "full"``); selected addresses: every legal
    aligned base in the 256-word scratchpad; everything else fixed.
    """

    window = tuple(sorted(set(window)))
    time_domains: Dict[str, List[int]] = {}
    for op in window:
        if radius == FULL_RANGE:
            low, high = 0, facts.horizon - 1
        else:
            low, high = max(0, times[op] - radius), min(times[op] + radius, facts.horizon - 1)
        time_domains[str(op)] = list(range(low, high + 1))
    address_domains = {facts.dest[op]: rse.physical_address_domain(facts, facts.dest[op],
                                                                   machine.SCRATCH_WORDS)
                       for op in window if facts.dest[op] is not None}
    return {
        "id": identifier,
        "family": "product",
        "program": program,
        "selected_operations": list(window),
        "time_domains": time_domains,
        "address_domains": address_domains,
        "fixed_times": {str(op): times[op] for op in range(facts.count) if op not in window},
        "fixed_addresses": {name: addresses[name] for name in facts.value_names
                            if name not in address_domains},
        "incumbent": dc.compilation(facts, times, addresses),
        "target": None,
    }


def capped_record(record: dict, facts: dc.ProgramFacts, caps: dict) -> dict:
    """``record`` restricted by the integer caps: times < Ccap, block ends <= Scap.

    A fixed decision outside either cap, or a selected domain emptied by them,
    makes the window infeasible (``direct_constraints.Infeasible``). No other
    restriction is applied: in particular no target rectangle.
    """

    if caps["status"] != "OK":
        raise ValueError("a capped record requires caps with status OK")
    ccap, scap = caps["Ccap"], caps["Scap"]
    for key, value in record["fixed_times"].items():
        if value > ccap - 1:
            raise dk.Infeasible(f"fixed operation {key} issues at {value}, past Ccap-1={ccap - 1}")
    for name, value in record["fixed_addresses"].items():
        if value + facts.width[name] > scap:
            raise dk.Infeasible(f"fixed value {name!r} ends past Scap={scap}")
    time_domains = {}
    for key, values in record["time_domains"].items():
        kept = [value for value in values if value <= ccap - 1]
        if not kept:
            raise dk.Infeasible(f"operation {key} has no cycle below Ccap={ccap}")
        time_domains[key] = kept
    address_domains = {}
    for name, values in record["address_domains"].items():
        kept = [value for value in values if value + facts.width[name] <= scap]
        if not kept:
            raise dk.Infeasible(f"value {name!r} cannot fit Scap={scap}")
        address_domains[name] = kept
    return dict(record, time_domains=time_domains, address_domains=address_domains, target=None)


def product_record(identifier: str, program: dict, facts: dc.ProgramFacts,
                   times: Dict[int, int], addresses: Dict[str, int], window: Sequence[int],
                   radius, caps: dict) -> dict:
    """The declared strict-product domain of one window (``Domain.target`` absent).

    Exactly ``capped_record(neighborhood_record(...))``: selected times are the
    incumbent +/- ``radius`` (or the full range) clipped to ``[0, Ccap-1]``;
    selected addresses are every legal aligned base ending at or below ``Scap``.
    """

    return capped_record(neighborhood_record(identifier, program, facts, times, addresses,
                                             window, radius), facts, caps)


def product_window_plan(facts: dc.ProgramFacts, times: Dict[int, int],
                        addresses: Dict[str, int]) -> List[Tuple[int, ...]]:
    """A2/A3 windows: A1's target-major window traversal, first occurrences only.

    With no target rectangle, the window list of every target is the same set
    of tuples, so one product query per distinct window in A1's order is the
    whole plan. When ``targets_for`` offers no target the memory-first list is
    used, so a strict improvement the caps still admit is not skipped.
    """

    cycles = max(times.values()) + 1
    memory = dc.footprint(facts, addresses)
    targets = dopt.targets_for(facts, cycles, memory)
    firsts = [target_memory < memory for _, target_memory in targets] or [True]
    seen = set()
    plan: List[Tuple[int, ...]] = []
    for scratch_first in firsts:
        for window in dopt.windows_for(facts, times, addresses, scratch_first=scratch_first):
            window = tuple(window)
            if window not in seen:
                seen.add(window)
                plan.append(window)
    return plan


# ==========================================================================
# Section 5: sound propagation with replayable certificates
# ==========================================================================


@dataclass
class PropagationStats:
    """Counts by rule, affected domains and the incremental certificate digest.

    ``keep`` retains every certificate (exhaustive and mutation tests, replay
    artifacts). Measured runs keep only counts and the stream digest.
    """

    keep: bool = False
    counts: Dict[str, int] = _field(default_factory=dict)
    removed_values: Dict[str, int] = _field(default_factory=dict)
    certificates: List[tuple] = _field(default_factory=list)
    affected_domains: List[str] = _field(default_factory=list)
    _affected_seen: set = _field(default_factory=set)
    _digest: object = _field(default_factory=hashlib.sha256)
    stream_length: int = 0
    current_domain: Optional[str] = None

    def emit(self, certificate: tuple, removed: int = 0) -> None:
        rule = certificate[0]
        self.counts[rule] = self.counts.get(rule, 0) + 1
        if removed:
            self.removed_values[rule] = self.removed_values.get(rule, 0) + removed
        self._digest.update(repr(certificate).encode("utf-8"))
        self._digest.update(b"\n")
        self.stream_length += 1
        if self.current_domain is not None and self.current_domain not in self._affected_seen:
            self._affected_seen.add(self.current_domain)
            self.affected_domains.append(self.current_domain)
        if self.keep:
            self.certificates.append(certificate)

    def digest(self) -> str:
        return self._digest.hexdigest()

    def summary(self) -> dict:
        joined = "\n".join(self.affected_domains)
        return {"counts": dict(sorted(self.counts.items())),
                "removed_values": dict(sorted(self.removed_values.items())),
                "certificate_stream_sha256": self.digest(),
                "certificate_stream_length": self.stream_length,
                "affected_domain_count": len(self.affected_domains),
                "affected_domain_list_sha256": hashlib.sha256(joined.encode()).hexdigest(),
                "affected_domains_first64": [d[:16] for d in self.affected_domains[:64]]}


class Propagation:
    """The four rules of section 5 over a search-only copy of physical domains.

    Time domains are sorted tuples for the selected operations; fixed operations
    are singletons taken from the domain. Address domains are sorted tuples for
    the selected values once every time is fixed. Nothing here touches the
    codec: ranks are computed by the caller from the unfiltered option list.

    Certificates (``repr`` hashed, retained when ``stats.keep``):

    - ``("PU", u, v, lag, maxDv, removed)``  t_u <= max(D_v) - lag
    - ``("PL", u, v, lag, minDu, removed)``  t_v >= min(D_u) + lag
    - ``("EO", engine, cycle, ops, limit)``  singleton issues exceed the limit
    - ``("EF", engine, cycle, op, limit)``   full cycle removed from ``op``
    - ``("AL", u, v, maxAv, minAv, wu, wv, removed)``  removed a_u lie in
      ``[maxAv-wu+1, minAv+wv-1]``: no disjoint a_v exists
    - ``("EMPTY", kind, key)``               a domain emptied: branch impossible
    - ``("PB", LC, LS, best, lc_witness, ls_witness)``  LC*LS >= best: prune
    """

    def __init__(self, domain: se.Domain, stats: PropagationStats) -> None:
        facts = domain.facts
        self.domain = domain
        self.facts = facts
        self.stats = stats
        self.selected = tuple(domain.selected_operations)
        selected = set(self.selected)
        # Edges touching at least one selected operation. A fixed/fixed edge can
        # delete nothing: the root ``schedule_conflict`` already proved it holds.
        edges = []
        for v in range(facts.count):
            for u, lag in facts.predecessors[v].items():
                if u in selected or v in selected:
                    edges.append((u, v, lag))
        self.edges = tuple(sorted(edges))
        # E1: edges incident to each operation, in edge order.
        incident: Dict[int, List[int]] = {}
        for i, (u, v, _) in enumerate(self.edges):
            incident.setdefault(u, []).append(i)
            if v != u:
                incident.setdefault(v, []).append(i)
        self.incident = {op: tuple(ids) for op, ids in incident.items()}
        self.fixed_times = dict(domain.fixed_times)
        base_usage: Dict[Tuple[str, int], List[int]] = {}
        for op, cycle in sorted(self.fixed_times.items()):
            base_usage.setdefault((facts.engine[op], cycle), []).append(op)
        self.base_usage = base_usage
        self.base_count = {key: len(ops) for key, ops in base_usage.items()}
        self.fixed_time_max = max(self.fixed_times.values(), default=-1)
        self.cycle_floor = facts.cycle_lower_bound()
        self.widest = facts.memory_lower_bound()
        self.selected_values = tuple(domain.address_order)
        selected_values = set(self.selected_values)
        self.fixed_addresses = dict(domain.fixed_addresses)
        self.fixed_end_max = max((a + facts.width[n] for n, a in self.fixed_addresses.items()),
                                 default=0)
        # Values whose producer and every consumer are fixed have a fixed
        # lifetime; the rest are recomputed from the domains at every node.
        self.static_values = []
        self.dynamic_values = []
        for name in facts.value_names:
            ops = (facts.producers[name],) + tuple(facts.consumers[name])
            if any(op in selected for op in ops):
                self.dynamic_values.append(name)
            else:
                self.static_values.append(name)
        self.span = facts.horizon + max(facts.latency, default=0) + 2
        static = [0] * (self.span + 1)
        for name in self.static_values:
            p = facts.producers[name]
            start = self.fixed_times[p] + facts.latency[p]
            end = max([start] + [self.fixed_times[c] for c in facts.consumers[name]])
            static[start] += facts.width[name]
            static[end + 1] -= facts.width[name]
        running, levels = 0, []
        for delta in static:
            running += delta
            levels.append(running)
        self.static_levels = levels
        # Range maximum (earliest cycle on ties) over the static profile.
        table = [[(level, -cycle) for cycle, level in enumerate(levels)]]
        width = 1
        while 2 * width <= len(levels):
            previous = table[-1]
            table.append([max(previous[i], previous[i + width])
                          for i in range(len(levels) - 2 * width + 1)])
            width *= 2
        self._table = table
        self.static_peak = max(table[0]) if table[0] else (0, 0)
        self.selected_value_set = selected_values

    # -- time domains -----------------------------------------------------

    def _t(self, D: Dict[int, Tuple[int, ...]], op: int) -> Tuple[int, ...]:
        values = D.get(op)
        if values is None:
            return (self.fixed_times[op],)
        return values

    def times_fixpoint(self, D: Dict[int, Tuple[int, ...]],
                       changed: Optional[Sequence[int]] = None
                       ) -> Optional[Dict[int, Tuple[int, ...]]]:
        """Rules 1 and 2 to a fixed point; ``None`` proves the branch impossible.

        E1: ``changed=None`` revises every edge (root); otherwise only edges
        incident to ``changed`` start in the queue, which is sound because
        the caller's other domains are a fixpoint of the same rules.
        """

        facts = self.facts
        emit = self.stats.emit
        D = dict(D)
        edges = self.edges
        incident = self.incident
        fixed = self.fixed_times
        if changed is None:
            queue = deque(range(len(edges)))
        else:
            queue = deque(sorted({i for op in changed for i in incident.get(op, ())}))
        queued = set(queue)

        def domain_of(op):
            values = D.get(op)
            return (fixed[op],) if values is None else values

        def touch(op):
            for i in incident.get(op, ()):
                if i not in queued:
                    queued.add(i)
                    queue.append(i)

        while True:
            while queue:
                i = queue.popleft()
                queued.discard(i)
                u, v, lag = edges[i]
                du, dv = domain_of(u), domain_of(v)
                high = dv[-1] - lag
                if du[-1] > high:
                    kept = du[:bisect.bisect_right(du, high)]
                    removed = du[len(kept):]
                    if u not in D:
                        emit(("EMPTY", "time", u, ("PU", u, v, lag, dv[-1])))
                        return None
                    emit(("PU", u, v, lag, dv[-1], removed), len(removed))
                    if not kept:
                        emit(("EMPTY", "time", u))
                        return None
                    D[u] = du = kept
                    touch(u)
                low = du[0] + lag
                if dv[0] < low:
                    kept = dv[bisect.bisect_left(dv, low):]
                    removed = dv[:len(dv) - len(kept)]
                    if v not in D:
                        emit(("EMPTY", "time", v, ("PL", u, v, lag, du[0])))
                        return None
                    emit(("PL", u, v, lag, du[0], removed), len(removed))
                    if not kept:
                        emit(("EMPTY", "time", v))
                        return None
                    D[v] = kept
                    touch(v)
            # Rule 2 exactly as the parent applies it after an edge sweep.
            base = self.base_count
            singles: Dict[Tuple[str, int], List[int]] = {}
            for op in self.selected:
                values = D[op]
                if len(values) == 1:
                    singles.setdefault((facts.engine[op], values[0]), []).append(op)
            for (engine, cycle), ops in sorted(singles.items()):
                limit = machine.ENGINE_LIMITS[engine]
                if base.get((engine, cycle), 0) + len(ops) > limit:
                    emit(("EO", engine, cycle,
                          tuple(sorted(self.base_usage.get((engine, cycle), []) + ops)), limit))
                    return None
            changed_here = False
            for op in self.selected:
                values = D[op]
                if len(values) == 1:
                    continue
                engine = facts.engine[op]
                limit = machine.ENGINE_LIMITS[engine]
                full = [cycle for cycle in values
                        if base.get((engine, cycle), 0)
                        + len(singles.get((engine, cycle), ())) >= limit]
                if not full:
                    continue
                for cycle in full:
                    emit(("EF", engine, cycle, op, limit), 1)
                kept = tuple(x for x in values if x not in full)
                if not kept:
                    emit(("EMPTY", "time", op))
                    return None
                D[op] = kept
                touch(op)
                changed_here = True
            if not changed_here and not queue:
                return D

    # -- bounds -----------------------------------------------------------

    def product_bound(self, D: Dict[int, Tuple[int, ...]],
                      A: Optional[Dict[str, Tuple[int, ...]]]) -> Tuple[int, tuple, int, tuple]:
        """Rule 4: ``(LC, lc_witness, LS, ls_witness)``, valid for every completion."""

        facts = self.facts
        lc, lc_w = self.cycle_floor, ("floor",)
        if self.fixed_time_max + 1 > lc:
            lc, lc_w = self.fixed_time_max + 1, ("fixed",)
        for op in self.selected:
            candidate = D[op][0] + 1
            if candidate > lc:
                lc, lc_w = candidate, ("min_time", op, D[op][0])
        ls, ls_w = self.widest, ("widest",)
        if self.fixed_end_max > ls:
            ls, ls_w = self.fixed_end_max, ("fixed_end",)
        if A is not None:
            for name in self.selected_values:
                candidate = A[name][0] + facts.width[name]
                if candidate > ls:
                    ls, ls_w = candidate, ("min_address", name, A[name][0])
        live, cycle = self.compulsory_peak(D)
        if live > ls:
            ls, ls_w = live, ("live", cycle)
        return lc, lc_w, ls, ls_w

    def _static_max(self, low: int, high: int) -> Tuple[int, int]:
        """``(max level, -earliest cycle)`` of the static profile on ``[low, high]``."""

        levels = self.static_levels
        if low >= len(levels):
            return (0, -low)
        high = min(high, len(levels) - 1)
        k = (high - low + 1).bit_length() - 1
        row = self._table[k]
        return max(row[low], row[high - (1 << k) + 1])

    def compulsory_peak(self, D: Dict[int, Tuple[int, ...]]) -> Tuple[int, int]:
        """Peak width of guaranteed-live intervals and its earliest cycle.

        For value ``v`` produced by ``p``: ``start_hi = max(D_p) + latency`` and
        ``end_lo = max(min(D_p) + latency, max over consumers of min(D_c))``.
        Only when ``start_hi <= end_lo`` is ``[start_hi, end_lo]`` live in every
        completion; widths of values live at one cycle need disjoint words.
        """

        facts = self.facts
        delta: Dict[int, int] = {}
        for name in self.dynamic_values:
            p = facts.producers[name]
            dp = self._t(D, p)
            start_hi = dp[-1] + facts.latency[p]
            end_lo = dp[0] + facts.latency[p]
            for c in facts.consumers[name]:
                first = self._t(D, c)[0]
                if first > end_lo:
                    end_lo = first
            if start_hi <= end_lo:
                w = facts.width[name]
                delta[start_hi] = delta.get(start_hi, 0) + w
                delta[end_lo + 1] = delta.get(end_lo + 1, 0) - w
        best = self.static_peak
        if delta:
            points = sorted(delta)
            running = 0
            for i, point in enumerate(points[:-1]):
                running += delta[point]
                if running <= 0:
                    continue
                value, negative_cycle = self._static_max(point, points[i + 1] - 1)
                candidate = (value + running, negative_cycle)
                if candidate > best:
                    best = candidate
        return best[0], -best[1]

    def prune(self, D, A, best: Optional[int]) -> Tuple[bool, int]:
        """``(pruned, LC*LS)``; a prune is certified by its two witnesses."""

        lc, lc_w, ls, ls_w = self.product_bound(D, A)
        if best is not None and lc * ls >= best:
            self.stats.emit(("PB", lc, ls, best, lc_w, ls_w))
            return True, lc * ls
        return False, lc * ls

    # -- address domains --------------------------------------------------

    def address_pairs(self, lifetimes: Dict[str, Tuple[int, int]]) -> Tuple[tuple, ...]:
        """Live-overlapping pairs with at least one selected value, by producer IDs."""

        facts = self.facts
        names = sorted(facts.value_names, key=lambda n: facts.producers[n])
        pairs = []
        for i, first in enumerate(names):
            s1, e1 = lifetimes[first]
            for second in names[i + 1:]:
                if first not in self.selected_value_set and second not in self.selected_value_set:
                    continue
                s2, e2 = lifetimes[second]
                if s1 <= e2 and s2 <= e1:
                    pairs.append((first, second))
                    pairs.append((second, first))
        return tuple(pairs)

    def _a(self, A: Dict[str, Tuple[int, ...]], name: str) -> Tuple[int, ...]:
        values = A.get(name)
        if values is None:
            return (self.fixed_addresses[name],)
        return values

    def addresses_fixpoint(self, A: Dict[str, Tuple[int, ...]], pairs: Sequence[tuple],
                           changed: Optional[Sequence[str]] = None
                           ) -> Optional[Dict[str, Tuple[int, ...]]]:
        """Rule 3 (all times fixed): a_u needs a disjoint block in A_v.

        ``a_u`` has support iff ``min(A_v)+w_v <= a_u`` or ``max(A_v) >= a_u+w_u``;
        the unsupported values are exactly ``[max(A_v)-w_u+1, min(A_v)+w_v-1]``.

        E1: a pair ``(u, v)`` can delete only after ``A_v`` changed, so a
        deletion from ``A_x`` re-queues the pairs whose supporting value is
        ``x``; ``changed=None`` revises every pair, otherwise the pairs that
        mention a changed value in either position start in the queue.
        """

        facts = self.facts
        emit = self.stats.emit
        A = dict(A)
        fixed = self.fixed_addresses
        by_support: Dict[str, List[int]] = {}
        mentions: Dict[str, List[int]] = {}
        for i, (u, v) in enumerate(pairs):
            by_support.setdefault(v, []).append(i)
            mentions.setdefault(u, []).append(i)
            mentions.setdefault(v, []).append(i)
        if changed is None:
            queue = deque(range(len(pairs)))
        else:
            queue = deque(sorted({i for name in changed for i in mentions.get(name, ())}))
        queued = set(queue)
        while queue:
            i = queue.popleft()
            queued.discard(i)
            u, v = pairs[i]
            au = A.get(u)
            if au is None:
                au = (fixed[u],)
            av = A.get(v)
            if av is None:
                av = (fixed[v],)
            lo = av[-1] - facts.width[u] + 1
            hi = av[0] + facts.width[v] - 1
            if lo > hi:
                continue
            left = bisect.bisect_left(au, lo)
            right = bisect.bisect_right(au, hi)
            if left >= right:
                continue
            removed = au[left:right]
            inputs = (u, v, av[-1], av[0], facts.width[u], facts.width[v])
            if u not in A:
                emit(("EMPTY", "address", u, ("AL",) + inputs))
                return None
            kept = au[:left] + au[right:]
            emit(("AL",) + inputs + (removed,), len(removed))
            if not kept:
                emit(("EMPTY", "address", u))
                return None
            A[u] = kept
            for j in by_support.get(u, ()):
                if j not in queued:
                    queued.add(j)
                    queue.append(j)
        return A


# ==========================================================================
# The shared expander (A3 depth-first, A4 discrepancy heap)
# ==========================================================================


class _Node:
    __slots__ = ("state", "D", "A", "pairs", "phase", "position", "order", "ranks", "disc",
                 "lb")

    def __init__(self, state, D, A, pairs, phase, position, order, ranks, disc, lb):
        self.state = state
        self.D = D
        self.A = A
        self.pairs = pairs
        self.phase = phase
        self.position = position
        self.order = order
        self.ranks = ranks
        self.disc = disc
        self.lb = lb


class _Stop(Exception):
    def __init__(self, reason: str, status: str = "UNKNOWN") -> None:
        super().__init__(reason)
        self.reason = reason
        self.status = status


class _Improved(Exception):
    """A validated strict improvement ended an A4 epoch."""


class Expander:
    """Lazy children of a search node.

    ``mode == "ss_bound"`` reproduces ``structural_search.search`` exactly (its
    bounds, its pruning points, its node charging); it exists so that a test can
    prove the shared traversal and acceptance code equal to that owner.
    ``mode == "propagate"`` applies the four section 5 rules instead.
    """

    def __init__(self, domain: se.Domain, mode: str, stats: PropagationStats,
                 report: ss.SearchReport) -> None:
        if mode not in ("ss_bound", "propagate"):
            raise ValueError(mode)
        self.domain = domain
        self.facts = domain.facts
        self.mode = mode
        self.stats = stats
        self.report = report
        self.prop = Propagation(domain, stats) if mode == "propagate" else None
        self.filtered = 0
        self.root_state: Optional[se.State] = None
        # Tests only: ``audit(event)`` sees every propagated child with its
        # prefix, surviving domains, outcome and bound. ``None`` costs nothing.
        self.audit: Optional[Callable[[dict], None]] = None

    def _audit(self, outcome: str, state: se.State, D, A) -> None:
        if self.audit is None:
            return
        event = {"outcome": outcome, "times": dict(state.times),
                 "addresses": dict(state.addresses), "D": D, "A": A}
        if D is not None:
            lc, _, ls, _ = self.prop.product_bound(D, A)
            event.update(LC=lc, LS=ls)
        self.audit(event)

    # -- the ss_bound replica ---------------------------------------------

    def _ss_prunes(self, state: se.State, live_width: Optional[int], best: Optional[int]) -> bool:
        if best is None:
            return False
        lower = ss.cycle_bound(self.facts, state.times) * ss.scratch_bound(
            self.facts, {name: state.addresses[name] for name in state.addresses}, live_width)
        if lower >= best:
            self.report.pruned += 1
            return True
        return False

    # -- root ---------------------------------------------------------------

    def root(self, best: Optional[int]) -> Optional[_Node]:
        state = se.State(self.domain)
        self.root_state = state
        if self.mode == "ss_bound":
            return _Node(state, None, None, None, "time", 0, None, (), 0, 0)
        D = {op: tuple(self.domain.time_domains[op]) for op in self.domain.selected_operations}
        D = self.prop.times_fixpoint(D)
        if D is None:
            self._audit("inconsistent", state, None, None)
            self.report.dead_ends += 1
            return None
        pruned, lb = self.prop.prune(D, None, best)
        self._audit("pruned" if pruned else "kept", state, D, None)
        if pruned:
            self.report.pruned += 1
            return None
        self.root_state = state
        return _Node(state, D, None, None, "time", 0, None, (), 0, lb)

    # -- children -------------------------------------------------------------

    def is_leaf(self, node: _Node) -> bool:
        return node.phase == "address" and node.position == len(node.order)

    def children(self, node: _Node, best_ref: Callable[[], Optional[int]]) -> Iterator[_Node]:
        """Children in canonical rank order, generated lazily.

        ``best_ref`` is read when each child is generated, so a depth-first
        caller that improved the incumbent inside an earlier sibling prunes the
        later siblings with the improved value, exactly as the owner does.
        """

        domain = self.domain
        facts = self.facts
        state = node.state
        selected = domain.selected_operations
        if node.phase == "time" and node.position == len(selected):
            state.recompute_lifetimes()
            if state.fixed_address_conflict() is not None:
                self.report.dead_ends += 1
                return
            order = state.allocation_order()
            if self.mode == "ss_bound":
                if self._ss_prunes(state, ss.peak_live_width(facts, state.lifetimes), best_ref()):
                    return
                yield _Node(state, None, None, None, "address", 0, order, node.ranks, node.disc,
                            node.lb)
                return
            pairs = self.prop.address_pairs(state.lifetimes)
            A = {name: tuple(domain.address_domains[name]) for name in self.prop.selected_values}
            A = self.prop.addresses_fixpoint(A, pairs)
            if A is None:
                self._audit("inconsistent", state, None, None)
                self.report.dead_ends += 1
                return
            pruned, lb = self.prop.prune(node.D, A, best_ref())
            self._audit("pruned" if pruned else "kept", state, node.D, A)
            if pruned:
                self.report.pruned += 1
                return
            yield _Node(state, node.D, A, pairs, "address", 0, order, node.ranks, node.disc, lb)
            return

        if node.phase == "time":
            op = selected[node.position]
            legal = se.options(domain, state, ("time", op))
            if not legal:
                self.report.dead_ends += 1
                return
            allowed = None if self.mode == "ss_bound" else set(node.D[op])
            for rank, value in enumerate(legal):
                if allowed is not None and value not in allowed:
                    self.filtered += 1
                    continue
                nxt = state.copy()
                nxt.times[op] = value
                ranks = node.ranks + (rank,)
                disc = node.disc + (1 if rank else 0)
                if self.mode == "ss_bound":
                    if self._ss_prunes(nxt, None, best_ref()):
                        continue
                    yield _Node(nxt, None, None, None, "time", node.position + 1, None, ranks,
                                disc, 0)
                    continue
                D2 = dict(node.D)
                D2[op] = (value,)
                D2 = self.prop.times_fixpoint(D2, changed=(op,))
                if D2 is None:
                    self._audit("inconsistent", nxt, None, None)
                    self.report.dead_ends += 1
                    continue
                pruned, lb = self.prop.prune(D2, None, best_ref())
                self._audit("pruned" if pruned else "kept", nxt, D2, None)
                if pruned:
                    self.report.pruned += 1
                    continue
                yield _Node(nxt, D2, None, None, "time", node.position + 1, None, ranks, disc, lb)
            return

        # address phase
        name = node.order[node.position]
        legal = se.options(domain, state, ("address", name))
        if not legal:
            self.report.dead_ends += 1
            return
        if self.mode == "ss_bound":
            live_width = ss.peak_live_width(facts, state.lifetimes)
            allowed = None
        else:
            allowed = set(node.A[name])
        for rank, value in enumerate(legal):
            if allowed is not None and value not in allowed:
                self.filtered += 1
                continue
            nxt = state.copy()
            nxt.addresses[name] = value
            ranks = node.ranks + (rank,)
            disc = node.disc + (1 if rank else 0)
            if self.mode == "ss_bound":
                if self._ss_prunes(nxt, live_width, best_ref()):
                    continue
                yield _Node(nxt, None, None, None, "address", node.position + 1, node.order,
                            ranks, disc, 0)
                continue
            A2 = dict(node.A)
            A2[name] = (value,)
            A2 = self.prop.addresses_fixpoint(A2, node.pairs, changed=(name,))
            if A2 is None:
                self._audit("inconsistent", nxt, None, None)
                self.report.dead_ends += 1
                continue
            pruned, lb = self.prop.prune(node.D, A2, best_ref())
            self._audit("pruned" if pruned else "kept", nxt, node.D, A2)
            if pruned:
                self.report.pruned += 1
                continue
            yield _Node(nxt, node.D, A2, node.pairs, "address", node.position + 1, node.order,
                        ranks, disc, lb)


class _Acceptor:
    """Candidate acceptance, identical in policy to ``structural_search.search``.

    ``collect`` (tests only) records every strict improvement on the query's
    starting incumbent without lowering ``best``; the finite-fixture equality
    proofs use it to compare complete improving sets.
    """

    def __init__(self, domain: se.Domain, report: ss.SearchReport, meter: si.Meter,
                 deadline: Callable[[], Optional[float]], clock: Callable[[], float],
                 observe: Optional[Callable[[dict], None]] = None, collect: bool = False,
                 stop_on_improvement: bool = False) -> None:
        self.domain = domain
        self.facts = domain.facts
        self.report = report
        self.meter = meter
        self.deadline = deadline
        self.clock = clock
        self.observe = observe
        self.collect = collect
        self.collected: Dict[str, dict] = {}
        self.stop_on_improvement = stop_on_improvement
        self.best: Optional[int] = report.best_product
        self.threshold: Optional[int] = report.incumbent_product
        self.seen: Dict[str, int] = {}

    def expired(self) -> bool:
        limit = self.deadline()
        return limit is not None and self.clock() >= limit

    def consider(self, state: se.State) -> None:
        report = self.report
        facts = self.facts
        report.completions += 1
        cycles, scratch, product = se.objective(facts, state.times, state.addresses)
        if self.domain.target is not None and (
                cycles > self.domain.target[0] or scratch > self.domain.target[1]):
            return
        compiled = dc.compilation(facts, state.times, state.addresses)
        normalised = se.normalise_compilation(facts, compiled)
        identity = se.object_digest(normalised)
        report.duplicate_lookups += 1
        if identity in self.seen:
            report.duplicate_hits += 1
            return
        self.seen[identity] = product
        if self.observe is not None:
            self.observe({"identity": identity, "product": product, "cycles": cycles,
                          "scratch": scratch, "compilation": normalised,
                          "times": dict(state.times), "addresses": dict(state.addresses)})
        if self.collect:
            if self.threshold is None or product < self.threshold:
                self.collected[identity] = {"product": product, "times": dict(state.times),
                                            "addresses": dict(state.addresses)}
            return
        if self.best is not None and product >= self.best:
            return
        if self.expired():
            report.interrupted_validations += 1
            report.deadline_expired = True
            raise _Stop("the shared deadline expired before candidate validation")
        try:
            self.meter.record()
        except si.BudgetExhausted as exc:
            raise _Stop(exc.reason) from exc
        report.validations += 1
        try:
            machine.check_compilation(self.domain.program, normalised)
            for case in self.domain.program["cases"]:
                machine.check_case(self.domain.program, normalised, case)
                report.case_checks += 1
        except (machine.CompileError, machine.ProgramError) as exc:
            report.rejected_completions.append({
                "identity": identity,
                "times": {str(k): v for k, v in sorted(state.times.items())},
                "addresses": dict(sorted(state.addresses.items())), "error": str(exc)})
            return
        if self.expired():
            report.interrupted_validations += 1
            report.deadline_expired = True
            raise _Stop("the shared deadline expired during candidate validation")
        self.best = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = dict(state.times)
        report.best_addresses = dict(state.addresses)
        report.best_compilation = normalised
        report.best_identity = identity
        report.improved = True
        try:
            report.best_index = str(se.encode(self.domain, normalised, CODEC))
        except se.DomainError:
            report.best_index = None
        if self.stop_on_improvement:
            raise _Improved()


def _new_report(domain: se.Domain, arm: str, incumbent: Optional[dict],
                digest: Optional[str] = None) -> ss.SearchReport:
    # ``digest`` is the caller's already computed ``domain.digest()`` (the
    # same bytes, hashed once per query instead of once per use).
    report = ss.SearchReport(arm=arm, domain_id=domain.identifier,
                             domain_sha256=digest or domain.digest())
    if incumbent is not None:
        facts = domain.facts
        normalised = se.normalise_compilation(facts, incumbent)
        times = se.issue_cycles_of(domain.program, normalised["bundles"])
        addresses = dict(normalised["scratch"])
        cycles, scratch, product = se.objective(facts, times, addresses)
        report.incumbent_product = product
        report.best_product = product
        report.best_cycles = cycles
        report.best_scratch = scratch
        report.best_times = times
        report.best_addresses = addresses
        report.best_compilation = normalised
        report.best_identity = se.object_digest(normalised)
    return report


def propagated_search(
    domain: se.Domain,
    incumbent: Optional[dict],
    budget: si.Budget,
    deadline: Optional[float] = None,
    stats: Optional[PropagationStats] = None,
    mode: str = "propagate",
    observe: Optional[Callable[[dict], None]] = None,
    collect: bool = False,
    clock: Callable[[], float] = time.perf_counter,
    audit: Optional[Callable[[dict], None]] = None,
    threshold: Optional[int] = None,
    domain_digest: Optional[str] = None,
) -> Tuple[ss.SearchReport, dict]:
    """A3's depth-first search: ``structural_search.search`` plus propagation.

    Returns the owner's ``SearchReport`` and an extras dict (filtered option
    count, collected improving set in ``collect`` mode). With
    ``mode="ss_bound"`` the traversal equals the owner's node for node.
    ``collect`` with ``threshold`` (tests only) enumerates every completion
    with ``J < threshold`` (default: the incumbent's J) without lowering it.
    """

    stats = stats if stats is not None else PropagationStats()
    digest = domain_digest or domain.digest()
    stats.current_domain = digest
    report = _new_report(domain, "A3_propagated_search" if mode == "propagate"
                         else "ss_bound_replica", incumbent, digest)
    meter = budget.start()
    acceptor = _Acceptor(domain, report, meter, lambda: deadline, clock, observe, collect)
    if collect and threshold is not None:
        acceptor.threshold = threshold
    extras: dict = {"filtered": 0}

    state = se.State(domain)
    conflict = state.schedule_conflict()
    if conflict is not None:
        report.status = "UNSAT"
        report.reason = f"the fixed decisions contradict each other: {conflict}"
        report.seconds = meter.elapsed
        return report, extras
    if acceptor.expired():
        report.status = "UNKNOWN"
        report.deadline_expired = True
        report.reason = "the shared deadline had already expired before the search began"
        report.seconds = meter.elapsed
        return report, extras

    expander = Expander(domain, mode, stats, report)
    expander.audit = audit

    def charge_node() -> None:
        report.nodes += 1
        if acceptor.expired():
            report.deadline_expired = True
            raise _Stop("the shared optimisation deadline expired")
        try:
            meter.visit()
        except si.BudgetExhausted as exc:
            raise _Stop(exc.reason) from exc

    best_ref = (lambda: acceptor.threshold) if collect else (lambda: acceptor.best)

    def dfs(node: _Node) -> None:
        charge_node()
        if expander.is_leaf(node):
            acceptor.consider(node.state)
            return
        for child in expander.children(node, best_ref):
            dfs(child)

    try:
        root = expander.root(best_ref())
        if root is not None:
            dfs(root)
    except _Stop as stop:
        report.status = "UNKNOWN"
        report.reason = stop.reason
    except RecursionError:
        report.status = "UNKNOWN"
        report.reason = "traversal depth exceeded the interpreter's recursion limit"
    else:
        report.status = "SAT" if report.improved else "UNSAT"
        report.reason = ("a strictly better validated compilation was found" if report.improved
                         else "the declared domain holds no strict improvement")
    counters = (expander.root_state or state).counters
    report.option_constructions = counters["option_constructions"]
    report.options_considered = counters["options_considered"]
    report.legality_checks = counters["legality_checks"]
    report.seconds = meter.elapsed
    if report.rejected_completions:
        report.status = "FAIL"
        report.reason = "a completed candidate was rejected by the pinned validator"
    extras["filtered"] = expander.filtered
    if collect:
        extras["collected"] = acceptor.collected
    return report, extras


# ==========================================================================
# Controller of A1, A2 and A3
# ==========================================================================


class _Aggregate:
    def __init__(self, node_ceiling: int, validation_ceiling: int) -> None:
        self.node_ceiling = node_ceiling
        self.validation_ceiling = validation_ceiling
        self.totals = {"nodes": 0, "validations": 0, "case_checks": 0, "pruned": 0,
                       "completions": 0, "dead_ends": 0, "filtered": 0}

    def exhausted(self) -> Optional[str]:
        if self.node_ceiling - self.totals["nodes"] < 2:
            return "aggregate_nodes"
        if self.validation_ceiling - self.totals["validations"] < 1:
            return "aggregate_validations"
        return None

    def budget(self, remaining: float, limits: dict) -> Optional[si.Budget]:
        nodes_left = self.node_ceiling - self.totals["nodes"]
        validations_left = self.validation_ceiling - self.totals["validations"]
        if nodes_left < 2 or validations_left < 1:
            return None
        # Charged nodes include the one that trips the meter, so the meter gets
        # one fewer than what is left and the aggregate never exceeds its ceiling.
        return si.Budget(seconds=max(remaining, 1e-9), max_cover=limits["query_max_cover"],
                         max_visited=min(limits["search_max_nodes"], nodes_left - 1),
                         max_records=min(limits["search_max_candidate_validations"],
                                         validations_left))

    def add(self, report: ss.SearchReport, filtered: int = 0) -> None:
        self.totals["nodes"] += report.nodes
        self.totals["validations"] += report.validations
        self.totals["case_checks"] += report.case_checks
        self.totals["pruned"] += report.pruned
        self.totals["completions"] += report.completions
        self.totals["dead_ends"] += report.dead_ends
        self.totals["filtered"] += filtered


def _status_key(status: str) -> str:
    return {"SAT": "SAT", "UNSAT": "UNSAT", "UNKNOWN": "UNKNOWN_SEARCH", "FAIL": "FAIL"}[status]


def _digest_of(times: Dict[int, int], addresses: Dict[str, int]) -> str:
    return se.object_digest({"t": {str(k): v for k, v in sorted(times.items())},
                             "a": dict(sorted(addresses.items()))})


def _epoch_queries(arm: str, facts, times, addresses) -> List[dict]:
    """The fixed traversal of one incumbent epoch for A1, A2 or A3."""

    cycles = max(times.values()) + 1
    memory = dc.footprint(facts, addresses)
    if arm == "A1_deadline_control":
        out = []
        for target_cycles, target_memory in dopt.targets_for(facts, cycles, memory):
            for window in dopt.windows_for(facts, times, addresses,
                                           scratch_first=target_memory < memory):
                out.append({"kind": "matched", "window": tuple(window),
                            "target": (target_cycles, target_memory), "radius": BASE_RADIUS})
        return out
    return [{"kind": "product", "window": window, "target": None, "radius": BASE_RADIUS}
            for window in product_window_plan(facts, times, addresses)]


def sequential_optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    *,
    arm: str,
    budget_seconds: float,
    query_seconds: float = oic.LIMITS["query_active_seconds"],
    node_ceiling: int = int(oic.LIMITS["aggregate_nodes"]),
    validation_ceiling: int = int(oic.LIMITS["aggregate_validation_attempts"]),
    limits: Optional[dict] = None,
    clock: Callable[[], float] = time.perf_counter,
    stats: Optional[PropagationStats] = None,
    memo: bool = True,
    learner_factory: Optional[Callable[[se.Domain], object]] = None,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Improve the bootstrap incumbent with A1, A2 or A3.

    One absolute deadline covers construction, propagation, search, decoding
    and validation. Each query's allowance ``min(query_seconds, remaining)`` is
    fixed before its domain is built and never renewed; a query that expires
    while overall time remains is recorded and the fixed traversal advances.

    ``learner_factory`` (the conditional learned compiler only; ``None`` in
    every A1-A3 measurement) splits each query: the first half of its allowance
    searches and records observations, the second half prepares the ranker from
    case-validated observations and walks its proposals. Without enough data it
    spends the remaining allowance on a fresh non-model search of the same
    domain. No deadline is renewed.
    """

    if arm not in ("A1_deadline_control", "A2_product_search", "A3_propagated_search"):
        raise ValueError(f"sequential_optimise does not run {arm!r}")
    limits = dict(PER_QUERY_LIMITS if limits is None else limits)
    stats = stats if stats is not None else PropagationStats()
    cache: Optional[dict] = {} if memo else None
    started = clock()
    deadline = started + budget_seconds
    statuses = {"SAT": 0, "UNSAT": 0, "UNKNOWN_SEARCH": 0, "UNKNOWN_CONSTRUCTION": 0,
                "QUERY_EXPIRED": 0, "INFEASIBLE": 0, "NO_STRICT_IMPROVEMENT": 0, "FAIL": 0}
    queries: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    interrupted: List[dict] = []
    attempted: set = set()
    aggregate = _Aggregate(node_ceiling, validation_ceiling)
    stopped = "pass_complete"
    best_times, best_addresses = dict(times), dict(addresses)
    epochs = 0

    improved = True
    while improved:
        improved = False
        epochs += 1
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        digest = _digest_of(best_times, best_addresses)
        for spec in _epoch_queries(arm, facts, best_times, best_addresses):
            if clock() >= deadline:
                stopped = "deadline"
                break
            exhausted = aggregate.exhausted()
            if exhausted:
                stopped = exhausted
                break
            window = spec["window"]
            key = (digest, spec["kind"], window, spec["target"], spec["radius"])
            if key in attempted:
                continue
            attempted.add(key)
            query_started = clock()
            allowance = min(query_seconds, deadline - query_started)
            if allowance <= 0:
                stopped = "deadline"
                interrupted.append({"phase": "before_construction", "window": list(window)})
                break
            query_deadline = query_started + allowance
            entry = {"window": list(window), "kind": spec["kind"],
                     "target": list(spec["target"]) if spec["target"] else None,
                     "radius": spec["radius"], "allowance_seconds": allowance}
            try:
                if spec["kind"] == "matched":
                    target_cycles, target_memory = spec["target"]
                    record = rse.matched_window_record(
                        f"{program['name']}::{'-'.join(map(str, window))}"
                        f"::{target_cycles}x{target_memory}::s{spec['radius']}",
                        "matched", program, facts, best_times, best_addresses,
                        window, target_cycles, target_memory, time_slack=spec["radius"])
                else:
                    caps = product_caps(facts, best_times, best_addresses, window)
                    entry["caps"] = [caps["LC"], caps["LS"], caps["Ccap"], caps["Scap"]]
                    if caps["status"] != "OK":
                        statuses["NO_STRICT_IMPROVEMENT"] += 1
                        entry.update(status="NO_STRICT_IMPROVEMENT", reason=caps["reason"])
                        queries.append(entry)
                        continue
                    record = product_record(
                        f"{program['name']}::{'-'.join(map(str, window))}::product"
                        f"::r{spec['radius']}", program, facts, best_times, best_addresses,
                        window, spec["radius"], caps)
                domain = se.Domain.from_record(record, memo=cache)
            except dk.Infeasible as exc:
                statuses["INFEASIBLE"] += 1
                entry.update(status="INFEASIBLE", reason=str(exc))
                queries.append(entry)
                continue
            except se.DomainError as exc:
                statuses["UNKNOWN_CONSTRUCTION"] += 1
                entry.update(status="UNKNOWN_CONSTRUCTION", reason=str(exc))
                queries.append(entry)
                continue
            entry["domain_sha256"] = domain.digest()
            entry["bits"] = se.layout(domain, CODEC).width
            remaining = query_deadline - clock()
            entry["remaining_after_construction_seconds"] = remaining
            if remaining <= 0:
                interrupted.append({"phase": "after_construction", "window": list(window),
                                    "domain_sha256": entry["domain_sha256"]})
                if clock() >= deadline:
                    statuses["UNKNOWN_CONSTRUCTION"] += 1
                    entry.update(status="UNKNOWN_CONSTRUCTION",
                                 reason="the overall deadline expired during construction")
                    queries.append(entry)
                    stopped = "deadline"
                    break
                statuses["QUERY_EXPIRED"] += 1
                entry.update(status="QUERY_EXPIRED",
                             reason="the query allowance expired during construction")
                queries.append(entry)
                continue
            budget = aggregate.budget(remaining, limits)
            if budget is None:
                stopped = aggregate.exhausted() or "aggregate_nodes"
                queries.append(dict(entry, status="NOT_RUN", reason=stopped))
                break
            learner = learner_factory(domain) if learner_factory is not None else None
            search_deadline = (query_started + allowance / 2 if learner is not None
                               else query_deadline)

            def run_search(until, meter_budget, watch):
                if arm == "A3_propagated_search":
                    found, extras = propagated_search(domain, record["incumbent"], meter_budget,
                                                      deadline=until, stats=stats, clock=clock,
                                                      observe=watch,
                                                      domain_digest=entry["domain_sha256"])
                    return found, extras["filtered"]
                return ss.search(domain, record["incumbent"], "structural_bound", meter_budget,
                                 deadline=until, observe=watch), 0

            report, filtered = run_search(search_deadline, budget,
                                          learner.observe if learner is not None else None)
            aggregate.add(report, filtered)
            entry.update(status=report.status, reason=report.reason, nodes=report.nodes,
                         validations=report.validations, pruned=report.pruned,
                         completions=report.completions, filtered=filtered)
            statuses[_status_key(report.status)] += 1
            rejected.extend(report.rejected_completions)
            if report.interrupted_validations:
                interrupted.append({"phase": "validation", "window": list(window),
                                    "count": report.interrupted_validations})
            ceiling_hit = (report.status == "UNKNOWN" and "budget exhausted" in report.reason
                           and "time" not in report.reason)
            best_here, pair, source = product, None, None
            if report.improved and report.best_product is not None \
                    and report.best_product < product:
                best_here = report.best_product
                pair = (dict(report.best_times), dict(report.best_addresses))
                source = "search"
            if learner is not None and report.status == "UNKNOWN" and not ceiling_hit:
                learner.validation_budget = validation_ceiling - aggregate.totals["validations"]
                prepared = learner.prepare(query_deadline)
                if prepared == "READY":
                    outcome = learner.step(best_here, query_deadline)
                    if outcome[0] == "improved":
                        pair, best_here, source = (outcome[1], outcome[2]), outcome[3], "model"
                elif prepared == "MODEL_UNAVAILABLE" and clock() < query_deadline:
                    again = aggregate.budget(query_deadline - clock(), limits)
                    if again is not None:
                        second, filtered2 = run_search(query_deadline, again, None)
                        aggregate.add(second, filtered2)
                        rejected.extend(second.rejected_completions)
                        learner.continued = second.status
                        if second.improved and second.best_product is not None \
                                and second.best_product < best_here:
                            best_here = second.best_product
                            pair = (dict(second.best_times), dict(second.best_addresses))
                            source = "continued_search"
                aggregate.totals["validations"] += learner.validations
                rejected.extend(learner.rejected)
            if learner is not None:
                entry["model"] = learner.summary()
            queries.append(entry)
            if ceiling_hit and aggregate.exhausted():
                stopped = aggregate.exhausted()
            if pair is not None:
                best_times, best_addresses = dict(pair[0]), dict(pair[1])
                improvements.append({"window": list(window), "kind": spec["kind"],
                                     "target": entry["target"], "from": product,
                                     "to": best_here, "source": source or "search",
                                     "from_CS": [cycles, memory],
                                     "to_CS": [max(best_times.values()) + 1,
                                               dc.footprint(facts, best_addresses)]})
                improved = True
                break
            if stopped != "pass_complete":
                break
        if stopped != "pass_complete":
            break

    elapsed = clock() - started
    record = {
        "controller": "objective_index_search.sequential_optimise",
        "arm": arm,
        "budget_seconds": budget_seconds,
        "query_seconds": query_seconds,
        "attempted_queries": len(attempted),
        "recorded_queries": len(queries),
        "epochs": epochs,
        "statuses": statuses,
        "accepted": len(improvements),
        "improvements": improvements,
        "rejected_completions": rejected,
        "discrepancy_count": len(rejected),
        "stopped_because": stopped,
        "seconds": elapsed,
        "overshoot_seconds": elapsed - budget_seconds,
        "interrupted_attempts": interrupted,
        "interrupted_attempt_count": len(interrupted),
        "aggregate": dict(aggregate.totals),
        "ceilings": {"nodes": node_ceiling, "validations": validation_ceiling},
        "budget_renewals": 0,
        "propagation": stats.summary() if arm == "A3_propagated_search" else None,
        "queries": queries,
    }
    return best_times, best_addresses, record


# ==========================================================================
# Section 6: A4 catalog, resumable discrepancy search
# ==========================================================================


def memory_group(facts: dc.ProgramFacts, times: Dict[int, int], addresses: Dict[str, int],
                 k: int) -> Tuple[int, ...]:
    """The memory-pressure group of section 6, sorted by operation ID."""

    live = dc.lifetimes(facts, times)
    if not live:
        return tuple(range(min(k, facts.count)))
    first = min(start for start, _ in live.values())
    last = max(end for _, end in live.values())
    peak, peak_cycle = -1, first
    for cycle in range(first, last + 1):
        total = sum(facts.width[n] for n, (s, e) in live.items() if s <= cycle <= e)
        if total > peak:
            peak, peak_cycle = total, cycle
    at_peak = [n for n, (s, e) in live.items() if s <= peak_cycle <= e]
    at_peak.sort(key=lambda n: (-facts.width[n], -(addresses[n] + facts.width[n]),
                                facts.producers[n]))
    ordered: List[int] = [facts.producers[n] for n in at_peak]
    consumers = sorted({c for n in at_peak for c in facts.consumers[n]})
    ordered.extend(consumers)
    ordered.extend(range(facts.count))
    chosen: List[int] = []
    seen = set()
    for op in ordered:
        if op not in seen:
            seen.add(op)
            chosen.append(op)
        if len(chosen) == k:
            break
    return tuple(sorted(chosen))


def _k_queue(facts, times, addresses, k: int) -> List[Tuple[Tuple[int, ...], object, str]]:
    radius = 4 if k <= 8 else 8
    latest = sorted(range(facts.count), key=lambda op: (-times[op], op))[:k]
    queue = [(tuple(sorted(latest)), radius, f"k{k}_latest"),
             (memory_group(facts, times, addresses, k), radius, f"k{k}_memory")]
    for start in range(0, facts.count, k):
        window = tuple(range(start, min(start + k, facts.count)))
        if window:
            queue.append((window, radius, f"k{k}_contiguous_{start}"))
    return queue


def build_catalog(facts: dc.ProgramFacts, times: Dict[int, int],
                  addresses: Dict[str, int]) -> List[dict]:
    """Five queues merged round-robin, deduplicated on (tuple, radius tag)."""

    queues: List[List[Tuple[Tuple[int, ...], object, str]]] = []
    queues.append([(tuple(w), BASE_RADIUS, "windows_for")
                   for w in dopt.windows_for(facts, times, addresses, scratch_first=True)])
    for k in (4, 8, 16):
        queues.append(_k_queue(facts, times, addresses, k))
    whole = []
    if facts.count <= 16:
        whole.append((tuple(range(facts.count)), FULL_RANGE, "whole_program"))
    queues.append(whole)
    catalog: List[dict] = []
    seen = set()
    position = 0
    while any(position < len(queue) for queue in queues):
        for queue_index, queue in enumerate(queues):
            if position >= len(queue):
                continue
            window, radius, tag = queue[position]
            key = (window, radius)
            if not window or key in seen:
                continue
            seen.add(key)
            catalog.append({"window": window, "radius": radius, "policy": tag,
                            "queue": queue_index})
        position += 1
    return catalog


def a3_catalog(facts: dc.ProgramFacts, times: Dict[int, int],
               addresses: Dict[str, int]) -> List[dict]:
    """Ablation catalog level 0: A3's ``product_window_plan`` at radius 2, in order."""

    return [{"window": tuple(window), "radius": BASE_RADIUS, "policy": "a3_product_window",
             "queue": 0} for window in product_window_plan(facts, times, addresses)]


def dfs_enumerate(domain: se.Domain, incumbent: dict, threshold: int,
                  frontier_limit: int = 10**9, max_nodes: int = 10**8) -> dict:
    """Tests only: the ablation's stack traversal run to exhaustion in collect mode.

    Same expander, propagation and child order as ``multiscale_optimise`` with
    ``traversal="dfs"``; no clock. Returns every completion with ``J <
    threshold`` and the pop order (ranks), for comparison with ``lds_enumerate``
    and with a recursive depth-first reference.
    """

    report = _new_report(domain, "dfs_collect", incumbent)
    meter = si.Budget(seconds=1e9, max_visited=max_nodes, max_records=10**9).start()
    acceptor = _Acceptor(domain, report, meter, lambda: None, time.perf_counter, collect=True)
    acceptor.threshold = threshold
    expander = Expander(domain, "propagate", PropagationStats(), report)
    stack: List[_Node] = []
    order: List[tuple] = []
    root = expander.root(threshold)
    if root is not None:
        stack.append(root)
    status = "EXHAUSTED"
    while stack:
        node = stack.pop()
        order.append((node.disc, node.lb, node.ranks))
        report.nodes += 1
        if report.nodes > max_nodes:
            status = "UNKNOWN_NODE_LIMIT"
            break
        if expander.is_leaf(node):
            acceptor.consider(node.state)
            continue
        children = list(expander.children(node, lambda: threshold))
        if len(stack) + len(children) > frontier_limit:
            status = "UNKNOWN_FRONTIER_LIMIT"
            break
        stack.extend(reversed(children))
    return {"status": status, "collected": acceptor.collected, "nodes": report.nodes,
            "pop_order": order}


def heap_key(node: _Node) -> tuple:
    """Section 6 order: (discrepancy, product lower bound, -depth, canonical ranks)."""

    return (node.disc, node.lb, -len(node.ranks), node.ranks)


def lds_enumerate(domain: se.Domain, incumbent: dict, threshold: int,
                  frontier_limit: int = 10**9, max_nodes: int = 10**8) -> dict:
    """Tests only: A4's heap order run to exhaustion in collect mode.

    Same expander, same propagation, same key as ``multiscale_optimise``; no
    clock. Returns every completion with ``J < threshold`` and the pop order.
    """

    report = _new_report(domain, "A4_lds_collect", incumbent)
    meter = si.Budget(seconds=1e9, max_visited=max_nodes, max_records=10**9).start()
    acceptor = _Acceptor(domain, report, meter, lambda: None, time.perf_counter, collect=True)
    acceptor.threshold = threshold
    expander = Expander(domain, "propagate", PropagationStats(), report)
    heap: list = []
    order: List[tuple] = []
    counter = 0
    root = expander.root(threshold)
    if root is not None:
        heapq.heappush(heap, (heap_key(root), counter, root))
    status = "EXHAUSTED"
    while heap:
        _, _, node = heapq.heappop(heap)
        order.append((node.disc, node.lb, node.ranks))
        report.nodes += 1
        if report.nodes > max_nodes:
            status = "UNKNOWN_NODE_LIMIT"
            break
        if expander.is_leaf(node):
            acceptor.consider(node.state)
            continue
        for child in expander.children(node, lambda: threshold):
            counter += 1
            heapq.heappush(heap, (heap_key(child), counter, child))
            if len(heap) > frontier_limit:
                status = "UNKNOWN_FRONTIER_LIMIT"
                break
        if status != "EXHAUSTED":
            break
    return {"status": status, "collected": acceptor.collected, "nodes": report.nodes,
            "pop_order": order}


class _Query:
    """One resumable A4 query with its own active-time allowance."""

    def __init__(self, entry: dict, index: int) -> None:
        self.entry = entry
        self.index = index
        self.initialized = False
        self.allowance: Optional[float] = None
        self.used = 0.0
        self.status: Optional[str] = None
        self.reason = ""
        self.heap: List[tuple] = []
        self.domain: Optional[se.Domain] = None
        self.expander: Optional[Expander] = None
        self.acceptor: Optional[_Acceptor] = None
        self.report: Optional[ss.SearchReport] = None
        self.meter: Optional[si.Meter] = None
        self.caps: Optional[dict] = None
        self.slices = 0
        self.frontier_peak = 0
        self.hard_deadline: Optional[float] = None
        self.learner = None
        self.digest: Optional[str] = None
        self.phase = "search"
        self.frontier_limited = False
        self.model_pair = None
        self.construction_interrupted = False

    def summary(self) -> dict:
        report = self.report
        return {"window": list(self.entry["window"]), "radius": self.entry["radius"],
                "phase": self.phase,
                "model": self.learner.summary() if self.learner is not None else None,
                "policy": self.entry["policy"], "status": self.status, "reason": self.reason,
                "active_seconds": self.used, "allowance_seconds": self.allowance,
                "slices": self.slices, "frontier_peak": self.frontier_peak,
                "frontier_left": len(self.heap),
                "caps": ([self.caps.get("LC"), self.caps.get("LS"), self.caps.get("Ccap"),
                          self.caps.get("Scap")] if self.caps else None),
                "nodes": report.nodes if report else 0,
                "validations": report.validations if report else 0,
                "interrupted_validations": report.interrupted_validations if report else 0,
                "construction_interrupted": self.construction_interrupted,
                "pruned": report.pruned if report else 0,
                "completions": report.completions if report else 0,
                "domain_sha256": self.digest}


def multiscale_optimise(
    program: dict,
    facts: dc.ProgramFacts,
    times: Dict[int, int],
    addresses: Dict[str, int],
    *,
    budget_seconds: float,
    query_seconds: float = oic.LIMITS["query_active_seconds"],
    node_ceiling: int = int(oic.LIMITS["aggregate_nodes"]),
    validation_ceiling: int = int(oic.LIMITS["aggregate_validation_attempts"]),
    slice_seconds: float = oic.LIMITS["slice_seconds"],
    slice_nodes: int = int(oic.LIMITS["slice_nodes"]),
    frontier_limit: int = int(oic.LIMITS["frontier_per_query"]),
    resident_limit: int = int(oic.LIMITS["resident_queries"]),
    limits: Optional[dict] = None,
    clock: Callable[[], float] = time.perf_counter,
    stats: Optional[PropagationStats] = None,
    memo: bool = True,
    trace: Optional[List[tuple]] = None,
    learner_factory: Optional[Callable[[se.Domain], object]] = None,
    catalog: str = "a4",
    traversal: str = "heap",
    timers: Optional[Dict[str, float]] = None,
) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """A4: A3's propagation, the five-queue catalog and resumable LDS queries.

    Successor parameters (plan section 4). ``catalog="a3"`` replaces the
    five-queue catalog by ``product_window_plan`` at radius 2, one query per
    window in that order. ``traversal="dfs"`` replaces the discrepancy heap by
    a stack popped in canonical depth-first order, lowest rank first. Every
    other element -- caps, propagation, variable order, validation, aggregate
    guards, eight resident queries, round-robin slices, epoch restart, the
    per-query frontier limit counted as queued prefixes -- is shared.

    ``timers`` (economics diagnostic only) accumulates query construction
    seconds under ``"construction"`` and counts constructions; ``None`` adds
    no clock reading at all.

    ``learner_factory`` (conditional learned compiler only) gives each query a
    search phase for the first half of its active allowance, observing every
    distinct completion, then a model phase that is itself sliced. Without
    enough validated data, or once the model's pool is exhausted, the query
    resumes its own discrepancy search for whatever allowance remains.
    """

    if catalog not in CATALOGS or traversal not in TRAVERSALS:
        raise ValueError(f"unknown ablation cell {catalog!r}/{traversal!r}")
    # R2: the last clock reading is remembered so an accepted improvement can
    # carry its elapsed time without an extra reading (a deterministic test
    # clock therefore advances exactly as it does for the frozen owner).
    raw_clock = clock
    last_read = [0.0]

    def clock() -> float:
        last_read[0] = raw_clock()
        return last_read[0]

    limits = dict(PER_QUERY_LIMITS if limits is None else limits)
    stats = stats if stats is not None else PropagationStats()
    cache: Optional[dict] = {} if memo else None
    started = clock()
    deadline = started + budget_seconds
    aggregate = _Aggregate(node_ceiling, validation_ceiling)
    best_times, best_addresses = dict(times), dict(addresses)
    status_counts: Dict[str, int] = {}
    interrupted_by_query: List[dict] = []
    construction_interruptions: List[dict] = []
    improvements: List[dict] = []
    rejected: List[dict] = []
    interrupted: List[dict] = []
    query_log: List[dict] = []
    stopped = "pass_complete"
    epochs = 0
    catalog_sizes: List[int] = []
    not_started = 0

    def finish(query: _Query, status: str, reason: str) -> None:
        query.status = status
        query.reason = reason
        status_counts[status] = status_counts.get(status, 0) + 1
        if query.report is not None:
            aggregate.add(query.report, query.expander.filtered if query.expander else 0)
            rejected.extend(query.report.rejected_completions)
        if query.learner is not None:
            aggregate.totals["validations"] += query.learner.validations
            rejected.extend(query.learner.rejected)
        # R1: interrupted candidate validations are counted for every query,
        # with or without a learner (the frozen owner kept them only above).
        if query.report is not None and query.report.interrupted_validations:
            item = {"phase": "validation", "window": list(query.entry["window"]),
                    "count": query.report.interrupted_validations}
            interrupted.append(item)
            interrupted_by_query.append(dict(item, query=query.index, epoch=epochs,
                                             policy=query.entry["policy"], status=status))
        if query.construction_interrupted:
            construction_interruptions.append({"query": query.index, "epoch": epochs,
                                               "window": list(query.entry["window"]),
                                               "status": status})
        if len(query_log) < 4096:
            query_log.append(query.summary())

    running: List[_Query] = []
    sequence = [0]

    def live_nodes() -> int:
        return aggregate.totals["nodes"] + sum(
            q.report.nodes for q in list(resident) + running if q.report is not None)

    def live_validations() -> int:
        return aggregate.totals["validations"] + sum(
            (q.report.validations if q.report is not None else 0)
            + (q.learner.validations if q.learner is not None else 0)
            for q in list(resident) + running)

    def push(heap: list, node: _Node) -> None:
        # The protocol key orders the heap; the counter only makes entries
        # comparable without ever comparing two nodes, and it never reorders
        # distinct keys.
        sequence[0] += 1
        if traversal == "heap":
            heapq.heappush(heap, (heap_key(node), sequence[0], node))
        else:
            heap.append(node)

    def pop(heap: list) -> _Node:
        if traversal == "heap":
            return heapq.heappop(heap)[2]
        return heap.pop()

    def initialize(query: _Query, epoch_times, epoch_addresses, product: int) -> Optional[str]:
        """Build caps, domain and root inside the query's allowance."""

        window = query.entry["window"]
        caps = product_caps(facts, epoch_times, epoch_addresses, window)
        query.caps = caps
        if caps["status"] != "OK":
            return caps["status"]
        record = product_record(
            f"{program['name']}::{'-'.join(map(str, window))}::{query.entry['policy']}"
            f"::r{query.entry['radius']}", program, facts, epoch_times, epoch_addresses,
            window, query.entry["radius"], caps)
        domain = se.Domain.from_record(record, memo=cache)
        query.domain = domain
        query.digest = domain.digest()
        report = _new_report(domain, "A4_multiscale_search", record["incumbent"], query.digest)
        query.report = report
        nodes_left = node_ceiling - live_nodes()
        validations_left = validation_ceiling - live_validations()
        budget = si.Budget(seconds=1e9, max_cover=limits["query_max_cover"],
                           max_visited=max(1, min(limits["search_max_nodes"], nodes_left - 1)),
                           max_records=max(1, min(limits["search_max_candidate_validations"],
                                                  validations_left)))
        query.meter = budget.start()
        if learner_factory is not None:
            query.learner = learner_factory(domain)
        query.acceptor = _Acceptor(domain, report, query.meter, lambda: query.hard_deadline,
                                   clock, stop_on_improvement=True,
                                   observe=(query.learner.observe if query.learner is not None
                                            else None))
        stats.current_domain = query.digest
        state = se.State(domain)
        conflict = state.schedule_conflict()
        if conflict is not None:
            return "UNSAT_CONFLICT"
        query.expander = Expander(domain, "propagate", stats, report)
        root = query.expander.root(product)
        if root is None:
            return "UNSAT_ROOT"
        push(query.heap, root)
        return None

    def model_slice(query: _Query, slice_started: float, full_deadline: float,
                    product: int) -> str:
        """The learned compiler's model phase of one A4 query, one slice at a time."""

        learner = query.learner
        query.hard_deadline = full_deadline
        if clock() >= full_deadline:
            query.used += clock() - slice_started
            finish(query, "UNKNOWN_DEADLINE" if clock() >= deadline else "UNKNOWN_ALLOWANCE",
                   "the allowance ended before the model phase")
            return "finished"
        if query.phase == "model_prepare":
            learner.validation_budget = validation_ceiling - live_validations()
            prepared = learner.prepare(full_deadline)
            query.used += clock() - slice_started
            if prepared == "READY":
                query.phase = "model"
                return "paused"
            if prepared == "MODEL_UNAVAILABLE" and query.heap and not query.frontier_limited:
                query.phase = "search_continued"
                return "paused"
            finish(query, f"UNKNOWN_MODEL_{prepared}", learner.reason)
            return "finished"
        outcome = learner.step(product, min(full_deadline, slice_started + slice_seconds),
                               full_deadline)
        query.used += clock() - slice_started
        if outcome[0] == "improved":
            report = query.report
            report.best_times, report.best_addresses = dict(outcome[1]), dict(outcome[2])
            report.best_product = outcome[3]
            report.improved = True
            finish(query, "SAT", "the model phase found a strictly better validated compilation")
            return "improved"
        if outcome[0] == "exhausted":
            if query.heap and not query.frontier_limited:
                query.phase = "search_continued"
                return "paused"
            finish(query, "UNKNOWN_MODEL_EXHAUSTED", "the ordered pool was exhausted")
            return "finished"
        if clock() >= full_deadline:
            finish(query, "UNKNOWN_DEADLINE" if clock() >= deadline else "UNKNOWN_ALLOWANCE",
                   "the allowance ended in the model phase")
            return "finished"
        return "paused"

    class _Switch(Exception):
        """The learned search phase has spent its half: pause for the model."""

    def run_slice(query: _Query, epoch_times, epoch_addresses, product: int) -> str:
        """One slice. Returns 'paused', 'finished' or 'improved'."""

        slice_started = clock()
        query.slices += 1
        just_initialized = False
        if not query.initialized:
            query.initialized = True
            just_initialized = True
            query.allowance = min(query_seconds, deadline - slice_started)
            if query.allowance <= 0:
                query.construction_interrupted = True
                finish(query, "NOT_STARTED_DEADLINE", "no overall time at initialization")
                return "finished"
            query.hard_deadline = min(deadline, slice_started + query.allowance)
            try:
                if timers is None:
                    outcome = initialize(query, epoch_times, epoch_addresses, product)
                else:
                    built = raw_clock()
                    try:
                        outcome = initialize(query, epoch_times, epoch_addresses, product)
                    finally:
                        timers["construction"] = (timers.get("construction", 0.0)
                                                  + raw_clock() - built)
                        timers["constructions"] = timers.get("constructions", 0) + 1
            except dk.Infeasible as exc:
                query.used += clock() - slice_started
                finish(query, "INFEASIBLE", str(exc))
                return "finished"
            except se.DomainError as exc:
                query.used += clock() - slice_started
                finish(query, "UNKNOWN_CONSTRUCTION", str(exc))
                return "finished"
            if outcome is not None:
                query.used += clock() - slice_started
                if outcome == "NO_STRICT_IMPROVEMENT":
                    finish(query, "NO_STRICT_IMPROVEMENT", query.caps["reason"])
                elif outcome in ("UNSAT_CONFLICT", "UNSAT_ROOT"):
                    finish(query, "UNSAT", outcome.lower())
                else:
                    finish(query, outcome, "")
                return "finished"
        stats.current_domain = query.digest
        remaining_allowance = query.allowance - query.used
        full_deadline = min(deadline, slice_started + remaining_allowance)
        learner = query.learner
        if learner is not None and query.phase in ("model_prepare", "model"):
            return model_slice(query, slice_started, full_deadline, product)
        learned_search = learner is not None and query.phase == "search"
        if learned_search:
            query.hard_deadline = min(deadline, slice_started + query.allowance / 2 - query.used)
        else:
            query.hard_deadline = full_deadline
        report = query.report
        expander = query.expander
        acceptor = query.acceptor
        nodes_at_start = report.nodes
        outcome = "paused"
        try:
            while True:
                now = clock()
                if now >= query.hard_deadline:
                    if just_initialized and report.nodes == nodes_at_start:
                        # Construction consumed the allowance before any node.
                        query.construction_interrupted = True
                    if now >= deadline:
                        raise _Stop("the overall deadline expired", "UNKNOWN_DEADLINE")
                    if learned_search:
                        raise _Switch()
                    raise _Stop("the query active-time allowance is spent", "UNKNOWN_ALLOWANCE")
                if report.nodes - nodes_at_start >= slice_nodes or now - slice_started >= slice_seconds:
                    break
                if not query.heap:
                    raise _Stop("the declared domain holds no strict improvement", "UNSAT")
                if aggregate.node_ceiling - live_nodes() < 2:
                    raise _Stop("aggregate node ceiling", "UNKNOWN_AGGREGATE_NODES")
                node = pop(query.heap)
                report.nodes += 1
                try:
                    query.meter.visit()
                except si.BudgetExhausted as exc:
                    raise _Stop(exc.reason, "UNKNOWN_QUERY_LIMIT") from exc
                if trace is not None:
                    trace.append((query.index, node.ranks))
                if expander.is_leaf(node):
                    acceptor.consider(node.state)
                    continue
                # The stack receives a node's children only once all are
                # generated, reversed so the lowest rank is popped first; the
                # frontier limit counts the generated children as queued.
                pending_children: List[_Node] = []
                for child in expander.children(node, lambda: product):
                    if traversal == "heap":
                        push(query.heap, child)
                        queued = len(query.heap)
                    else:
                        pending_children.append(child)
                        queued = len(query.heap) + len(pending_children)
                    if queued > frontier_limit:
                        if traversal == "dfs":
                            query.heap.extend(reversed(pending_children))
                        if learned_search:
                            query.frontier_limited = True
                            raise _Switch()
                        raise _Stop("more than the permitted queued prefixes",
                                    "UNKNOWN_FRONTIER_LIMIT")
                if pending_children:
                    for child in reversed(pending_children):
                        push(query.heap, child)
                query.frontier_peak = max(query.frontier_peak, len(query.heap))
        except _Improved:
            outcome = "improved"
        except _Switch:
            query.used += clock() - slice_started
            query.phase = "model_prepare"
            return "paused"
        except _Stop as stop:
            query.used += clock() - slice_started
            status = stop.status
            if status == "UNKNOWN":
                now = clock()
                if learned_search and now < deadline and now < full_deadline:
                    # A candidate reached the half-time boundary: it is an
                    # interrupted attempt, and the model phase takes over.
                    query.phase = "model_prepare"
                    return "paused"
                status = ("UNKNOWN_DEADLINE" if now >= deadline else
                          "UNKNOWN_ALLOWANCE" if now >= query.hard_deadline else
                          "UNKNOWN_QUERY_LIMIT")
            finish(query, status, stop.reason)
            return "finished"
        query.used += clock() - slice_started
        if outcome == "improved":
            finish(query, "SAT", "a strictly better validated compilation was found")
            return "improved"
        return "paused"

    resident: deque = deque()
    while True:
        epochs += 1
        cycles = max(best_times.values()) + 1
        memory = dc.footprint(facts, best_addresses)
        product = cycles * memory
        epoch_times, epoch_addresses = dict(best_times), dict(best_addresses)
        if catalog == "a4":
            entries = build_catalog(facts, epoch_times, epoch_addresses)
        else:
            entries = a3_catalog(facts, epoch_times, epoch_addresses)
        catalog_sizes.append(len(entries))
        pending = deque(_Query(entry, i) for i, entry in enumerate(entries))
        resident = deque()
        while pending and len(resident) < resident_limit:
            resident.append(pending.popleft())
        improved = False
        while resident:
            if clock() >= deadline:
                stopped = "deadline"
                break
            exhausted = aggregate.exhausted()
            if exhausted:
                stopped = exhausted
                break
            query = resident.popleft()
            running[:] = [query]
            outcome = run_slice(query, epoch_times, epoch_addresses, product)
            running[:] = []
            if outcome == "paused":
                resident.append(query)
                continue
            if outcome == "improved":
                report = query.report
                best_times = dict(report.best_times)
                best_addresses = dict(report.best_addresses)
                improvements.append({"window": list(query.entry["window"]),
                                     "radius": query.entry["radius"],
                                     "policy": query.entry["policy"], "from": product,
                                     "to": report.best_product,
                                     "source": "model" if query.phase == "model" else "search",
                                     "from_CS": [cycles, memory],
                                     "to_CS": [max(best_times.values()) + 1,
                                               dc.footprint(facts, best_addresses)],
                                     "elapsed_seconds": last_read[0] - started,
                                     "epoch": epochs, "query": query.index})
                improved = True
                break
            if pending:
                resident.append(pending.popleft())
        # Everything still resident or pending is superseded or unreached.
        for query in resident:
            if query.status is None:
                finish(query, "SUPERSEDED" if improved else (
                    "UNKNOWN_DEADLINE" if stopped == "deadline" else f"UNKNOWN_{stopped.upper()}"),
                       "left resident")
        for _ in pending:
            not_started += 1
        if not improved:
            break
        resident = deque()

    elapsed = clock() - started
    unknown = sum(n for s, n in status_counts.items() if s.startswith("UNKNOWN"))
    record = {
        "controller": "next_round_search.multiscale_optimise",
        "version": VERSION,
        "frozen_source_sha256": FROZEN_SOURCE_SHA256,
        "arm": "A4_multiscale_search",
        "catalog": catalog,
        "traversal": traversal,
        "budget_seconds": budget_seconds,
        "query_seconds": query_seconds,
        "epochs": epochs,
        "catalog_sizes": catalog_sizes[:64],
        "statuses": dict(sorted(status_counts.items())),
        "queries_finished": sum(status_counts.values()),
        "queries_unknown": unknown,
        "queries_not_started": not_started,
        "accepted": len(improvements),
        "improvements": improvements,
        "rejected_completions": rejected,
        "discrepancy_count": len(rejected),
        "stopped_because": stopped,
        "seconds": elapsed,
        "overshoot_seconds": elapsed - budget_seconds,
        "interrupted_attempts": interrupted,
        "interrupted_attempt_count": len(interrupted),
        # R1: unambiguous names. Totals count validations; ``_queries`` counts
        # affected queries; construction interruptions are separate and never
        # counted as validations.
        "interrupted_validation_total": sum(i["count"] for i in interrupted_by_query),
        "interrupted_validation_queries": len(interrupted_by_query),
        "interrupted_validations_per_query": interrupted_by_query[:4096],
        "construction_interruption_count": len(construction_interruptions),
        "construction_interruptions": construction_interruptions[:4096],
        "aggregate": dict(aggregate.totals),
        "ceilings": {"nodes": node_ceiling, "validations": validation_ceiling},
        "limits": {"slice_seconds": slice_seconds, "slice_nodes": slice_nodes,
                   "frontier": frontier_limit, "resident": resident_limit},
        "budget_renewals": 0,
        "propagation": stats.summary(),
        "queries": query_log,
    }
    return best_times, best_addresses, record


def optimise(program: dict, facts: dc.ProgramFacts, times: Dict[int, int],
             addresses: Dict[str, int], *, arm: str, budget_seconds: float, **kwargs
             ) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """Dispatch one NEW arm; the frozen A0 is never run here."""

    if arm == "A4_multiscale_search":
        return multiscale_optimise(program, facts, times, addresses,
                                   budget_seconds=budget_seconds, **kwargs)
    return sequential_optimise(program, facts, times, addresses, arm=arm,
                               budget_seconds=budget_seconds, **kwargs)
