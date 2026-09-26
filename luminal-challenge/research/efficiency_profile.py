"""Gate P: where the fixed-work time of the frozen baseline R0 goes, below "propagation".

Plan ``CLAUDE_PHASE2_EFFICIENCY_PHASE.md`` section 4. One fresh process per
(program, mode). Programs: the first two development seeds of each family
(800000-800009). Work: the fixed-work definition of the E gate -- the A4
catalog, depth-first traversal, every existing limit, aggregate 10,000 nodes
and 100,000 validations, and a CONSTANT clock, so that no wall expiry fires and
the profiled, counted and timed runs do exactly the same search.

Modes:

- ``time``: unprofiled; the complete compile call (bootstrap, set-up,
  optimisation, final compilation) on a separate real clock. Three fresh
  processes per program give the matched-work reference.
- ``profile``: ``cProfile`` over the same call, with ``SplitPropagation`` and
  ``SplitExpander``: subclasses whose method bodies are the R0 bodies with the
  two rules of ``times_fixpoint`` and the state copies of ``children`` moved
  into named helpers, so exclusive time separates into precedence,
  issue-capacity, address support, bounds, certificates and state copying.
  The run is compared with an uninstrumented run of the same work (trace,
  incumbent, certificate stream): the split changes no decision.
- ``count``: no profiler; counts calls, domain changes, fixpoint sweeps and
  EXACT repeated input signatures (the work a cache keyed by domain identity and
  every input could avoid), and the certificate bytes hashed.
- ``memory``: ``tracemalloc`` peak of the call (separate: it distorts time).

Built-ins and shared helpers are split over their callers' categories, in
proportion to the caller-edge time (the next-round profiler's rule, written
here with a finer category set because that owner is frozen and takes no
classifier argument).

Usage::

    PYTHONPATH=.reference:. python -m research.efficiency_profile --run RUN
"""

from __future__ import annotations

import argparse
import bisect
import collections
import cProfile
import hashlib
import json
import math
import os
import pstats
import statistics
import subprocess
import sys
import time
from pathlib import Path
from typing import Dict, Iterator, Optional, Tuple

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import efficiency_common as ec
from research import efficiency_search as es
from research import optimization_common as oc
from research import structural_encoding as se

from tests_direct import generate_programs as gp

KIND = "efficiency_profile"
SEEDS = tuple(range(800000, 800010))          # two per family: seed % 5 is the family
MODES = ("time", "timers", "profile", "count", "memory", "timers_split", "parity")
# ``timers_split`` (added after the first pass) is ``timers`` with rule 2 split
# into its EO part and its scan; the first-pass ``timers`` rows are retained.
TIME_REPS = 3


class _Constant:
    """The fixed-work clock: always 0.0, so no allowance, slice or deadline expires."""

    def __call__(self) -> float:
        return 0.0


# --------------------------------------------------------------------------
# Split instrumentation (identical bodies, named helpers)
# --------------------------------------------------------------------------


def _count_capacity(prop, counters, engine, limit, values, singles, full) -> None:
    """Count mode only: the scan's work and what a static/dynamic split would leave.

    ``static``: cycles full from FIXED issues alone (base >= limit), a property of
    the domain; ``dynamic``: cycles made full by selected singletons. The scan
    tests every value; only values in ``static | dynamic`` can be removed.
    """

    static = getattr(prop, "_static_full_counted", None)
    if static is None:
        static = {}
        for (e, c), n in prop.base_count.items():
            if n >= es.machine.ENGINE_LIMITS[e]:
                static.setdefault(e, set()).add(c)
        prop._static_full_counted = static
    dynamic = {c for (e, c), ops in singles.items() if e == engine
               and prop.base_count.get((e, c), 0) + len(ops) >= limit}
    stat = static.get(engine, set())
    counters["capacity_ops_scanned"] += 1
    counters["capacity_value_checks"] += len(values)
    counters["capacity_full_hits"] += len(full)
    counters["capacity_static_full_values"] += sum(1 for c in values if c in stat)
    counters["capacity_dynamic_full_values"] += sum(1 for c in values if c in dynamic)
    counters["capacity_ops_without_dynamic_full"] += not dynamic
    counters["capacity_static_cycles_per_engine_sum"] += len(stat)


class SplitPropagation(es.Propagation):
    """``times_fixpoint`` of R0 with its two rules and its copy in named helpers."""

    counters: Optional[collections.Counter] = None

    def _copy_domains(self, D):
        return dict(D)

    def _precedence(self, D) -> Tuple[Optional[dict], bool]:
        emit = self.stats.emit
        changed = False
        for u, v, lag in self.edges:
            du, dv = self._t(D, u), self._t(D, v)
            high = dv[-1] - lag
            if du[-1] > high:
                kept = du[:bisect.bisect_right(du, high)]
                removed = du[len(kept):]
                if u not in D:
                    emit(("EMPTY", "time", u, ("PU", u, v, lag, dv[-1])))
                    return None, changed
                emit(("PU", u, v, lag, dv[-1], removed), len(removed))
                if not kept:
                    emit(("EMPTY", "time", u))
                    return None, changed
                D[u] = du = kept
                changed = True
            low = du[0] + lag
            if dv[0] < low:
                kept = dv[bisect.bisect_left(dv, low):]
                removed = dv[:len(dv) - len(kept)]
                if v not in D:
                    emit(("EMPTY", "time", v, ("PL", u, v, lag, du[0])))
                    return None, changed
                emit(("PL", u, v, lag, du[0], removed), len(removed))
                if not kept:
                    emit(("EMPTY", "time", v))
                    return None, changed
                D[v] = kept
                changed = True
        return D, changed

    def _capacity(self, D, changed: bool) -> Tuple[Optional[dict], bool]:
        singles = self._capacity_singles(D)
        if singles is None:
            return None, changed
        return self._capacity_scan(D, changed, singles)

    def _capacity_singles(self, D):
        """Rule 2, first part: singleton issues per cycle and the overflow (EO) test."""

        facts = self.facts
        emit = self.stats.emit
        base = self.base_count
        singles: Dict[Tuple[str, int], list] = {}
        for op in self.selected:
            values = D[op]
            if len(values) == 1:
                singles.setdefault((facts.engine[op], values[0]), []).append(op)
        for (engine, cycle), ops in sorted(singles.items()):
            limit = es.machine.ENGINE_LIMITS[engine]
            if base.get((engine, cycle), 0) + len(ops) > limit:
                emit(("EO", engine, cycle,
                      tuple(sorted(self.base_usage.get((engine, cycle), []) + ops)), limit))
                return None
        return singles

    def _capacity_scan(self, D, changed: bool, singles) -> Tuple[Optional[dict], bool]:
        """Rule 2, second part: every value of every non-singleton op tested for a full cycle."""

        facts = self.facts
        emit = self.stats.emit
        base = self.base_count
        counters = SplitPropagation.counters
        for op in self.selected:
            values = D[op]
            if len(values) == 1:
                continue
            engine = facts.engine[op]
            limit = es.machine.ENGINE_LIMITS[engine]
            full = [cycle for cycle in values
                    if base.get((engine, cycle), 0)
                    + len(singles.get((engine, cycle), ())) >= limit]
            if counters is not None:
                _count_capacity(self, counters, engine, limit, values, singles, full)
            if not full:
                continue
            for cycle in full:
                emit(("EF", engine, cycle, op, limit), 1)
            kept = tuple(x for x in values if x not in full)
            if not kept:
                emit(("EMPTY", "time", op))
                return None, changed
            D[op] = kept
            changed = True
        return D, changed

    def times_fixpoint(self, D):
        counters = SplitPropagation.counters
        D = self._copy_domains(D)
        changed = True
        sweeps = 0
        while changed:
            sweeps += 1
            D, changed = self._precedence(D)
            if D is None:
                break
            D, changed = self._capacity(D, changed)
            if D is None:
                break
        if counters is not None:
            counters["times_fixpoint_sweeps"] += sweeps
            counters["times_fixpoint_edge_visits"] += sweeps * len(self.edges)
        return D


class SplitExpander(es.Expander):
    """``children`` of R0 (propagate mode only) with the copies in named helpers."""

    @staticmethod
    def _copy_state(state):
        return state.copy()

    @staticmethod
    def _copy_domains(D):
        return dict(D)

    def children(self, node, best_ref) -> Iterator:
        if self.mode != "propagate":
            yield from super().children(node, best_ref)
            return
        domain = self.domain
        state = node.state
        selected = domain.selected_operations
        if node.phase == "time" and node.position == len(selected):
            state.recompute_lifetimes()
            if state.fixed_address_conflict() is not None:
                self.report.dead_ends += 1
                return
            order = state.allocation_order()
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
            yield es._Node(state, node.D, A, pairs, "address", 0, order, node.ranks, node.disc, lb)
            return
        if node.phase == "time":
            op = selected[node.position]
            legal = se.options(domain, state, ("time", op))
            if not legal:
                self.report.dead_ends += 1
                return
            allowed = set(node.D[op])
            for rank, value in enumerate(legal):
                if value not in allowed:
                    self.filtered += 1
                    continue
                nxt = self._copy_state(state)
                nxt.times[op] = value
                ranks = node.ranks + (rank,)
                disc = node.disc + (1 if rank else 0)
                D2 = self._copy_domains(node.D)
                D2[op] = (value,)
                D2 = self.prop.times_fixpoint(D2)
                if D2 is None:
                    self._audit("inconsistent", nxt, None, None)
                    self.report.dead_ends += 1
                    continue
                pruned, lb = self.prop.prune(D2, None, best_ref())
                self._audit("pruned" if pruned else "kept", nxt, D2, None)
                if pruned:
                    self.report.pruned += 1
                    continue
                yield es._Node(nxt, D2, None, None, "time", node.position + 1, None, ranks, disc,
                               lb)
            return
        name = node.order[node.position]
        legal = se.options(domain, state, ("address", name))
        if not legal:
            self.report.dead_ends += 1
            return
        allowed = set(node.A[name])
        for rank, value in enumerate(legal):
            if value not in allowed:
                self.filtered += 1
                continue
            nxt = self._copy_state(state)
            nxt.addresses[name] = value
            ranks = node.ranks + (rank,)
            disc = node.disc + (1 if rank else 0)
            A2 = self._copy_domains(node.A)
            A2[name] = (value,)
            A2 = self.prop.addresses_fixpoint(A2, node.pairs)
            if A2 is None:
                self._audit("inconsistent", nxt, None, None)
                self.report.dead_ends += 1
                continue
            pruned, lb = self.prop.prune(node.D, A2, best_ref())
            self._audit("pruned" if pruned else "kept", nxt, node.D, A2)
            if pruned:
                self.report.pruned += 1
                continue
            yield es._Node(nxt, node.D, A2, node.pairs, "address", node.position + 1, node.order,
                           ranks, disc, lb)


# --------------------------------------------------------------------------
# The fixed-work call
# --------------------------------------------------------------------------


def _bootstrap(program):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, se.issue_cycles_of(program, compiled["bundles"]), dict(compiled["scratch"])


def fixed_work_call(program, trace=None, stats=None):
    """The complete compile call under the fixed-work definition (R0 parameters)."""

    facts, times, addresses = _bootstrap(program)
    best_t, best_a, record = es.multiscale_optimise(
        program, facts, times, addresses, budget_seconds=ec.PRIMARY_BUDGET,
        node_ceiling=ec.FIXED_WORK["aggregate_nodes"],
        validation_ceiling=ec.FIXED_WORK["aggregate_validations"],
        slice_nodes=ec.FIXED_WORK["slice_nodes"], clock=_Constant(), stats=stats, trace=trace,
        **ec.BASELINE_CELL)
    compiled = dc.compilation(facts, best_t, best_a)
    return compiled, record, facts


def _decision_fingerprint(record, trace, compiled, facts) -> dict:
    return {"trace_sha256": hashlib.sha256(repr(trace).encode()).hexdigest(),
            "trace_length": len(trace),
            "incumbent_sha256": se.object_digest(se.normalise_compilation(facts, compiled)),
            "certificates": record["propagation"]["certificate_stream_sha256"],
            "certificate_count": record["propagation"]["certificate_stream_length"],
            "statuses": record["statuses"], "aggregate": record["aggregate"],
            "stopped_because": record["stopped_because"]}


# --------------------------------------------------------------------------
# Attribution
# --------------------------------------------------------------------------

CATEGORIES = ("prop_precedence", "prop_issue_capacity", "prop_address_support", "prop_bounds",
              "prop_certificates", "state_copy", "frontier_options", "frontier_other",
              "domain_construction", "encoding_digest", "validation", "bootstrap",
              "orchestration")
PROPAGATION = ("prop_precedence", "prop_issue_capacity", "prop_address_support", "prop_bounds",
               "prop_certificates")
BY_NAME = {
    "prop_precedence": {"_precedence"},
    "prop_issue_capacity": {"_capacity", "_capacity_singles", "_capacity_scan"},
    "prop_address_support": {"addresses_fixpoint", "address_pairs"},
    "prop_bounds": {"product_bound", "compulsory_peak", "_static_max", "prune"},
    "prop_certificates": {"emit", "summary"},
    "state_copy": {"_copy_state", "_copy_domains", "copy"},
    "frontier_options": {"options", "time_options", "address_options"},
    "frontier_other": {"children", "is_leaf", "heap_key", "push", "pop",
                       "recompute_lifetimes", "fixed_address_conflict", "allocation_order",
                       "_collides", "times_fixpoint"},
    "bootstrap": {"_bootstrap"},
    "domain_construction": {
        "product_caps", "neighborhood_record", "capped_record", "product_record",
        "build_catalog", "memory_group", "_k_queue", "initialize", "root", "from_record",
        "_checked_domain", "_plain_int", "_key_to_op", "_check_address", "_incumbent_first",
        "address_order", "cartesian_size", "ordered_domain", "decision_keys",
        "physical_address_domain", "schedule_conflict", "windows_for", "targets_for"},
    "encoding_digest": {
        "canonical_json", "object_digest", "normalise_compilation", "encode", "_field_value",
        "layout", "_rank_width", "field", "read", "write", "digest", "_new_report",
        "objective", "consider", "issue_cycles_of"},
}
HELPERS = ("direct_contract.py", "direct_optimizer.py", "direct_constraints.py",
           "direct_compiler.py", "schema_index.py", "bisect.py", "heapq.py", "hashlib.py",
           "json/__init__.py", "json/encoder.py", "copy.py", "typing.py", "enum.py",
           "functools.py", "dataclasses.py")
ACCESSORS = {"_t", "_a"}          # tiny accessors: split over their callers
NODE_INIT_LINE = es._Node.__init__.__code__.co_firstlineno
CONSTRUCTION_INIT_LINES = {es.Propagation.__init__.__code__.co_firstlineno,
                           es.Expander.__init__.__code__.co_firstlineno,
                           es._Acceptor.__init__.__code__.co_firstlineno}


def own_category(filename: str, name: str, line: int = 0):
    base = filename.replace(os.sep, "/")
    if base.endswith("/machine.py"):
        return "validation"
    if base.endswith("direct_contract.py") and name == "compilation":
        return "encoding_digest"
    if filename == "~" or name in ACCESSORS or any(base.endswith(h) for h in HELPERS):
        return None
    if name == "__init__":
        if base.endswith(("efficiency_search.py", "efficiency_profile.py")):
            if line == NODE_INIT_LINE:
                return "state_copy"
            return ("domain_construction" if line in CONSTRUCTION_INIT_LINES
                    else "orchestration")
        if base.endswith("structural_encoding.py"):
            return "domain_construction"
    for category, names in BY_NAME.items():
        if name in names:
            return category
    return "orchestration"


def attribute(stats: pstats.Stats) -> Tuple[Dict[str, float], Dict[str, list], float]:
    raw = stats.stats
    memo: Dict[tuple, Dict[str, float]] = {}

    def shares(func, depth=0):
        filename, line, name = func
        category = own_category(filename, name, line)
        if category is not None:
            return {category: 1.0}
        if func in memo:
            return memo[func]
        memo[func] = {"orchestration": 1.0}
        weights, total = {}, 0.0
        for caller, edge in raw[func][4].items():
            tt = edge[2] if len(edge) > 2 else 0.0
            if tt <= 0 or depth > 12:
                continue
            total += tt
            for cat, share in shares(caller, depth + 1).items():
                weights[cat] = weights.get(cat, 0.0) + tt * share
        result = ({c: w / total for c, w in weights.items()} if total > 0
                  else {"orchestration": 1.0})
        memo[func] = result
        return result

    seconds = {c: 0.0 for c in CATEGORIES}
    top = {c: [] for c in CATEGORIES}
    grand = 0.0
    for func, (cc, nc, tt, ct, callers) in raw.items():
        grand += tt
        for category, share in shares(func).items():
            seconds[category] += tt * share
            top[category].append((tt * share, f"{os.path.basename(func[0])}:{func[2]}:{nc}"))
    for c in top:
        top[c] = [[n, round(v, 6)] for v, n in sorted(top[c], reverse=True)[:6] if v > 0]
    return seconds, top, grand


# --------------------------------------------------------------------------
# Modes
# --------------------------------------------------------------------------


def mode_time(program) -> dict:
    started = time.perf_counter()
    compiled, record, facts = fixed_work_call(program)
    seconds = time.perf_counter() - started
    return {"compile_call_seconds": seconds, "nodes": record["aggregate"]["nodes"],
            "validations": record["aggregate"]["validations"],
            "certificates": record["propagation"]["certificate_stream_length"],
            "stopped_because": record["stopped_because"]}


def _with_split(fn):
    """Run ``fn`` with R0's module names bound to the split subclasses."""

    originals = es.Expander, es.Propagation
    es.Expander, es.Propagation = SplitExpander, SplitPropagation
    try:
        return fn()
    finally:
        es.Expander, es.Propagation = originals


TIMED = {  # (owner, attribute) -> category; exclusive time by a timer stack
    ("SplitPropagation", "_precedence"): "prop_precedence",
    ("SplitPropagation", "_capacity_singles"): "prop_issue_capacity_singles_eo",
    ("SplitPropagation", "_capacity_scan"): "prop_issue_capacity_scan",
    ("SplitPropagation", "_copy_domains"): "state_copy",
    ("SplitPropagation", "addresses_fixpoint"): "prop_address_support",
    ("SplitPropagation", "address_pairs"): "prop_address_support",
    ("SplitPropagation", "product_bound"): "prop_bounds",
    ("SplitPropagation", "prune"): "prop_bounds",
    ("SplitExpander", "_copy_state"): "state_copy",
    ("SplitExpander", "_copy_domains"): "state_copy",
    ("PropagationStats", "emit"): "prop_certificates",
    ("se", "options"): "frontier_options",
    ("es", "_new_report"): "encoding_digest",
    ("machine", "check_compilation"): "validation",
    ("machine", "check_case"): "validation",
}


def mode_timers(program) -> dict:
    """Unprofiled exclusive seconds of the named helpers (perf_counter timer stack)."""

    owners = {"SplitPropagation": SplitPropagation, "SplitExpander": SplitExpander,
              "PropagationStats": es.PropagationStats, "se": se, "es": es,
              "machine": machine}
    exclusive = collections.Counter()
    calls = collections.Counter()
    stack = [0.0]
    clock = time.perf_counter
    originals = {}

    def wrap(fn, category):
        def timed(*args, **kwargs):
            stack.append(0.0)
            started = clock()
            try:
                return fn(*args, **kwargs)
            finally:
                spent = clock() - started
                inner = stack.pop()
                exclusive[category] += spent - inner
                stack[-1] += spent
                calls[category] += 1
        return timed

    for (owner, name), category in TIMED.items():
        target = owners[owner]
        own = not isinstance(target, type) or name in target.__dict__
        original = (target.__dict__[name] if isinstance(target, type) and own
                    else getattr(target, name))
        originals[(owner, name)] = (original, own)
        if isinstance(original, staticmethod):
            setattr(target, name, staticmethod(wrap(original.__func__, category)))
        else:
            setattr(target, name, wrap(original, category))
    try:
        started = clock()
        compiled, record, facts = _with_split(lambda: fixed_work_call(program))
        wall = clock() - started
    finally:
        for (owner, name), (original, own) in originals.items():
            if own:
                setattr(owners[owner], name, original)
            else:
                delattr(owners[owner], name)
    return {"timed_call_wall_seconds": wall,
            "exclusive_seconds": dict(exclusive), "calls": dict(calls),
            "untimed_remainder_seconds": wall - sum(exclusive.values()),
            "nodes": record["aggregate"]["nodes"]}


def mode_profile(program) -> dict:
    trace_plain = []
    compiled, record, facts = fixed_work_call(program, trace=trace_plain)
    plain = _decision_fingerprint(record, trace_plain, compiled, facts)
    profiler = cProfile.Profile()
    trace = []

    def run():
        profiler.enable()
        started = time.perf_counter()
        out = fixed_work_call(program, trace=trace)
        wall = time.perf_counter() - started
        profiler.disable()
        return out, wall

    (compiled, record, facts), wall = _with_split(run)
    split = _decision_fingerprint(record, trace, compiled, facts)
    seconds, top, grand = attribute(pstats.Stats(profiler))
    return {"profiled_call_wall_seconds": wall, "profiled_tottime_total": grand,
            "reconciliation_ratio": grand / wall if wall else None,
            "category_seconds": seconds, "top_functions": top,
            "split_changes_no_decision": plain == split, "fingerprint": split}


def _signature(*parts) -> str:
    return hashlib.sha256(repr(parts).encode()).hexdigest()


def mode_count(program) -> dict:
    counters = collections.Counter()
    seen = collections.defaultdict(set)          # per (Propagation id, kind): signatures
    changes = collections.Counter()
    real = {name: getattr(SplitPropagation, name) for name in
            ("times_fixpoint", "addresses_fixpoint", "compulsory_peak", "product_bound",
             "prune", "address_pairs")}

    def wrap(name, key):
        def wrapper(self, *args):
            counters[f"{name}_calls"] += 1
            signature = key(self, *args)
            bucket = seen[(id(self), name)]
            if signature in bucket:
                counters[f"{name}_repeated_in_domain"] += 1
            else:
                bucket.add(signature)
            result = real[name](self, *args)
            if name == "times_fixpoint":
                if result is None:
                    changes["times_fixpoint_dead"] += 1
                elif result != args[0]:
                    changes["times_fixpoint_changed_domains"] += 1
            if name == "addresses_fixpoint":
                if result is None:
                    changes["addresses_fixpoint_dead"] += 1
                elif result != args[0]:
                    changes["addresses_fixpoint_changed_domains"] += 1
            return result
        return wrapper

    key_D = lambda self, D, *rest: _signature(sorted(D.items()))  # noqa: E731
    patches = {
        "times_fixpoint": key_D,
        "compulsory_peak": key_D,
        "addresses_fixpoint": lambda self, A, pairs: _signature(sorted(A.items()), pairs),
        "product_bound": lambda self, D, A: _signature(sorted(D.items()),
                                                       sorted(A.items()) if A else None),
        "prune": lambda self, D, A, best: _signature(sorted(D.items()),
                                                     sorted(A.items()) if A else None, best),
        "address_pairs": lambda self, lifetimes: _signature(sorted(lifetimes.items())),
    }
    for name, key in patches.items():
        setattr(SplitPropagation, name, wrap(name, key))
    copies = collections.Counter()
    real_copy = se.State.copy
    real_options = se.options
    option_seen = collections.defaultdict(set)

    def copy(self):
        copies["state_copies"] += 1
        return real_copy(self)

    def options(domain, prefix, decision):
        copies["options_calls"] += 1
        signature = _signature(decision, sorted(prefix.times.items()),
                               sorted(prefix.addresses.items()))
        bucket = option_seen[id(domain)]
        if signature in bucket:
            copies["options_repeated_in_domain"] += 1
        else:
            bucket.add(signature)
        return real_options(domain, prefix, decision)

    stats = es.PropagationStats()
    certificate_bytes = [0]
    real_emit = es.PropagationStats.emit

    def emit(self, certificate, removed=0):
        certificate_bytes[0] += len(repr(certificate)) + 1
        return real_emit(self, certificate, removed)

    SplitPropagation.counters = counters
    es.PropagationStats.emit = emit
    se.State.copy = copy
    se.options = options
    try:
        compiled, record, facts = _with_split(lambda: fixed_work_call(program, stats=stats))
    finally:
        for name in patches:
            setattr(SplitPropagation, name, real[name])
        SplitPropagation.counters = None
        es.PropagationStats.emit = real_emit
        se.State.copy = real_copy
        se.options = real_options
    return {"counters": dict(counters), "domain_changes": dict(changes), "copies": dict(copies),
            "certificates": stats.stream_length, "certificate_bytes": certificate_bytes[0],
            "removed_values": dict(stats.removed_values), "rule_counts": dict(stats.counts),
            "nodes": record["aggregate"]["nodes"], "queries": record["queries_finished"],
            "epochs": record["epochs"]}


def mode_parity(program) -> dict:
    """The split subclasses (as finally used by ``timers_split``) change no decision."""

    trace_plain, trace_split = [], []
    compiled, record, facts = fixed_work_call(program, trace=trace_plain)
    plain = _decision_fingerprint(record, trace_plain, compiled, facts)
    compiled, record, facts = _with_split(lambda: fixed_work_call(program, trace=trace_split))
    split = _decision_fingerprint(record, trace_split, compiled, facts)
    return {"split_changes_no_decision": plain == split, "fingerprint": split}


def mode_memory(program) -> dict:
    import tracemalloc
    tracemalloc.start()
    fixed_work_call(program)
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {"tracemalloc_peak_bytes": peak, "tracemalloc_current_bytes": current}


def worker(spec: dict) -> dict:
    program = gp.additional_program(spec["seed"])
    fn = {"time": mode_time, "timers": mode_timers, "profile": mode_profile,
          "count": mode_count, "memory": mode_memory, "timers_split": mode_timers,
          "parity": mode_parity}[spec["mode"]]
    return {"kind": KIND + "_result", "seed": spec["seed"], "family": ec.FAMILIES[
        spec["seed"] % 5], "mode": spec["mode"], "rep": spec.get("rep", 0), **fn(program)}


# --------------------------------------------------------------------------
# Driver and aggregation
# --------------------------------------------------------------------------


def run(run_dir: Path) -> dict:
    out = Path(run_dir) / "profile"
    out.mkdir(parents=True, exist_ok=True)
    rows_path = out / "rows.jsonl"
    done = {(r["seed"], r["mode"], r["rep"]) for r in oc.read_rows(rows_path)}
    plan = [(seed, mode, rep) for seed in SEEDS for mode in MODES
            for rep in range(TIME_REPS if mode == "time" else 1)]
    for seed, mode, rep in plan:
        if (seed, mode, rep) in done:
            continue
        if ec.cap_reached(run_dir):
            raise RuntimeError("measurement cap reached")
        spec = {"seed": seed, "mode": mode, "rep": rep}
        started = time.perf_counter()
        proc = subprocess.run([oc.PYTHON, "-m", "research.efficiency_profile", "--spec",
                               json.dumps(spec)], cwd=str(ec.ROOT), capture_output=True,
                              text=True, timeout=600,
                              env={"PYTHONPATH": f"{ec.ROOT / '.reference'}:{ec.ROOT}",
                                   "PATH": "/usr/bin:/bin", "HOME": str(Path.home())})
        seconds = time.perf_counter() - started
        ec.charge(run_dir, "P_profile", f"{seed}|{mode}|{rep}", seconds)
        if proc.returncode != 0:
            oc.append_row(rows_path, {"seed": seed, "mode": mode, "rep": rep, "failed": True,
                                      "stderr": proc.stderr[-2000:]})
            continue
        row = json.loads(proc.stdout)
        row["process_seconds"] = seconds
        oc.append_row(rows_path, row)
    return aggregate(out)


def aggregate(out: Path) -> dict:
    rows = oc.read_rows(out / "rows.jsonl")
    failed = [r for r in rows if r.get("failed")]
    by = collections.defaultdict(list)
    for r in rows:
        if not r.get("failed"):
            by[(r["seed"], r["mode"])].append(r)
    programs = {}
    totals = collections.Counter()
    unprofiled_total = profiled_total = 0.0
    for seed in SEEDS:
        times = [r["compile_call_seconds"] for r in by[(seed, "time")]]
        profile = by[(seed, "profile")][0]
        count = by[(seed, "count")][0]
        memory = by[(seed, "memory")][0]
        median = statistics.median(times)
        unprofiled_total += median
        profiled_total += profile["profiled_call_wall_seconds"]
        for c, v in profile["category_seconds"].items():
            totals[c] += v
        programs[str(seed)] = {
            "family": profile["family"], "unprofiled_compile_seconds": times,
            "unprofiled_median": median,
            "profiled_wall": profile["profiled_call_wall_seconds"],
            "distortion": profile["profiled_call_wall_seconds"] / median,
            "reconciliation_ratio": profile["reconciliation_ratio"],
            "split_changes_no_decision": profile["split_changes_no_decision"],
            "nodes": count["nodes"], "certificates": count["certificates"],
            "counters": count["counters"], "copies": count["copies"],
            "domain_changes": count["domain_changes"],
            "tracemalloc_peak_bytes": memory["tracemalloc_peak_bytes"],
            "category_shares": {c: v / profile["profiled_tottime_total"]
                                for c, v in profile["category_seconds"].items()}}
    grand = sum(totals.values())
    summary = {
        "programs": len(programs), "failed_rows": len(failed),
        "unprofiled_matched_work_seconds_total": unprofiled_total,
        "profiled_wall_seconds_total": profiled_total,
        "distortion_total": profiled_total / unprofiled_total,
        "category_shares_pooled": {c: totals[c] / grand for c in CATEGORIES},
        "propagation_share_pooled": sum(totals[c] for c in PROPAGATION) / grand,
        "split_changes_no_decision_all": all(p["split_changes_no_decision"]
                                             for p in programs.values()),
        "final_split_changes_no_decision_all": all(
            by[(seed, "parity")][0]["split_changes_no_decision"] for seed in SEEDS
            if by.get((seed, "parity"))) and all(by.get((seed, "parity")) for seed in SEEDS),
        "counts_pooled": {}}
    pooled = collections.Counter()
    for p in programs.values():
        for block in ("counters", "copies", "domain_changes"):
            for k, v in p[block].items():
                pooled[k] += v
        pooled["certificates"] += p["certificates"]
        pooled["nodes"] += p["nodes"]
    summary["counts_pooled"] = dict(sorted(pooled.items()))
    summary.update(ceilings(by, programs))
    summary["repeat_work"] = {
        name: {"calls": pooled.get(f"{name}_calls", 0),
               "exact_repeats_in_domain": pooled.get(f"{name}_repeated_in_domain", 0),
               "fraction": (pooled.get(f"{name}_repeated_in_domain", 0)
                            / pooled[f"{name}_calls"]) if pooled.get(f"{name}_calls") else None}
        for name in ("times_fixpoint", "compulsory_peak", "product_bound", "prune",
                     "addresses_fixpoint")}
    summary["rule2_scan"] = {
        "value_checks": pooled.get("capacity_value_checks", 0),
        "op_scans": pooled.get("capacity_ops_scanned", 0),
        "full_hits": pooled.get("capacity_full_hits", 0),
        "futile_check_fraction": 1 - pooled.get("capacity_full_hits", 0)
        / max(1, pooled.get("capacity_value_checks", 0)),
        "op_scans_without_dynamic_full_cycle": pooled.get("capacity_ops_without_dynamic_full", 0)}
    summary["fixpoint_sweeps"] = {
        "calls": pooled.get("times_fixpoint_calls", 0),
        "sweeps": pooled.get("times_fixpoint_sweeps", 0),
        "confirmation_sweeps_at_least": pooled.get("times_fixpoint_calls", 0)
        - pooled.get("times_fixpoint_dead", 0),
        "edge_visits": pooled.get("times_fixpoint_edge_visits", 0)}
    report = {"summary": summary, "programs": programs,
              "definition": "fixed work: A4 catalog, DFS, aggregate 10,000 nodes, 100,000 "
                            "validations, constant clock; complete compile call"}
    oc.write_json(out / "PROFILE.json", report)
    return report


def ceilings(by, programs) -> dict:
    """Zero-cost ceilings from the light ``timers_split`` rows.

    For a component with exclusive seconds ``x_p`` on program ``p`` whose
    unprofiled matched-work time is ``T_p``, the ceiling is the equal-family
    geometric mean of ``1 - x_p/T_p``: the fixed-work compile ratio if that
    component cost NOTHING. It bounds any mechanism confined to the component
    (timer overhead makes it, if anything, optimistic).
    """

    shares = collections.defaultdict(dict)
    for seed in SEEDS:
        rows = by.get((seed, "timers_split"))
        if not rows:
            return {"ceilings": "timers_split rows absent"}
        T = programs[str(seed)]["unprofiled_median"]
        e = rows[0]["exclusive_seconds"]
        for k, v in e.items():
            shares[k][seed] = v / T
        shares["times_fixpoint_all_rules"][seed] = sum(
            e.get(k, 0.0) for k in ("prop_precedence", "prop_issue_capacity_scan",
                                    "prop_issue_capacity_singles_eo")) / T
        programs[str(seed)]["timers_split_share_of_unprofiled"] = {
            k: v / T for k, v in sorted(e.items())}
        programs[str(seed)]["timers_split_wall_over_unprofiled"] = (
            rows[0]["timed_call_wall_seconds"] / T)
    out = {}
    for name, per in sorted(shares.items()):
        families = collections.defaultdict(list)
        for seed, share in per.items():
            families[seed % 5].append(math.log(max(1e-9, 1 - min(share, 0.999999))))
        out[name] = {"zero_cost_ceiling_equal_family": math.exp(statistics.mean(
            statistics.mean(v) for v in families.values())),
            "mean_share": statistics.mean(per.values()), "max_share": max(per.values()),
            "min_share": min(per.values())}
    return {"zero_cost_ceilings": out}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec")
    parser.add_argument("--run")
    parser.add_argument("--aggregate-only", action="store_true")
    args = parser.parse_args(argv)
    if args.spec:
        result = worker(json.loads(args.spec))
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0
    if args.aggregate_only:
        report = aggregate(Path(args.run) / "profile")
    else:
        report = run(Path(args.run))
    print(json.dumps(report["summary"], indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
