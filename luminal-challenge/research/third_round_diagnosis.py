"""Stage M0 of the third round: what propagation work is shared between a node and its children.

Plan ``CLAUDE_PHASE2_THIRD_ROUND.md`` section 3, M0. Diagnostic programs are
seeds 800000-800029 (six per family). Every row is one fresh process running
R0 (``research/efficiency_search.py``, imported, never edited) in the fixed-work
mode of ``efficiency_profile.fixed_work_call``: A4 catalog, DFS, aggregate
10,000 nodes / 100,000 validations / 2,048-node slices, CONSTANT clock.

Modes (7 rows per program, 210 in all):

- ``work:10000`` x3: unprofiled complete compile call on a real clock (``T0``).
- ``exclusive_timers``: perf_counter timer stack over named helpers of the
  split subclasses of ``efficiency_profile`` (identical bodies); nested work
  is charged once (exclusive); the untimed remainder closes the reconciliation.
- ``workload_trace``: captures the propagation WORKLOAD with its parent links:
  every ``times_fixpoint``/``prune``/``address_pairs``/``addresses_fixpoint``
  call, the node it expands, the decision it applies and the incumbent bound it
  sees, plus the domain record of every ``Propagation``. The kernel replay of
  M2 consumes exactly this file. Written to ``workloads/<seed>.json.gz``.
- ``peak_memory``: tracemalloc peak of the plain call.
- ``instrumentation_parity``: the plain call, the timer-instrumented call and
  the trace-instrumented call give the same decision fingerprint (search
  trace, incumbent, certificate stream, statuses, aggregate).

Usage::

    python -m research.third_round_diagnosis --run RUN          # all 210 rows
    python -m research.third_round_diagnosis --spec JSON        # one worker
"""

from __future__ import annotations

import argparse
import collections
import gzip
import hashlib
import json
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional

import machine

from research import efficiency_profile as ep
from research import efficiency_search as es
from research import optimization_common as oc
from research import structural_encoding as se
from research import third_round_common as tc

from tests_direct import generate_programs as gp

STAGE = "M_diagnosis"
ARM = "R0"
MODES = ("work:10000",) + tc.OTHER_MODES


# --------------------------------------------------------------------------
# Exclusive timers
# --------------------------------------------------------------------------

# (owner, attribute) -> component. Ownership map: every timed helper is charged
# to exactly one component; a nested call is subtracted from its caller.
TIMED = {
    ("SplitPropagation", "times_fixpoint"): "tfix_shell",
    ("SplitPropagation", "_copy_domains"): "tfix_copy",
    ("SplitPropagation", "_precedence"): "precedence",
    ("SplitPropagation", "_capacity_singles"): "issue_capacity",
    ("SplitPropagation", "_capacity_scan"): "issue_capacity",
    ("SplitPropagation", "prune"): "bounds_product",
    ("SplitPropagation", "product_bound"): "bounds_product",
    ("SplitPropagation", "compulsory_peak"): "bounds_live",
    ("SplitPropagation", "_static_max"): "bounds_live",
    ("SplitPropagation", "addresses_fixpoint"): "address_support",
    ("SplitPropagation", "address_pairs"): "address_pairs",
    ("SplitPropagation", "__init__"): "propagation_setup",
    ("SplitExpander", "_copy_state"): "state_copy",
    ("SplitExpander", "_copy_domains"): "child_domain_copy",
    ("PropagationStats", "emit"): "certificates",
    ("se", "options"): "options",
    ("es", "_new_report"): "encoding",
    ("machine", "check_compilation"): "validation",
    ("machine", "check_case"): "validation",
}


def mode_exclusive_timers(program) -> dict:
    owners = {"SplitPropagation": ep.SplitPropagation, "SplitExpander": ep.SplitExpander,
              "PropagationStats": es.PropagationStats, "se": se, "es": es,
              "machine": machine}
    exclusive = collections.Counter()
    calls = collections.Counter()
    stack = [0.0]
    clock = time.perf_counter
    originals = {}

    def wrap(fn, component):
        def timed(*args, **kwargs):
            stack.append(0.0)
            started = clock()
            try:
                return fn(*args, **kwargs)
            finally:
                spent = clock() - started
                inner = stack.pop()
                exclusive[component] += spent - inner
                stack[-1] += spent
                calls[component] += 1
        return timed

    for (owner, name), component in TIMED.items():
        target = owners[owner]
        own = not isinstance(target, type) or name in target.__dict__
        original = (target.__dict__[name] if isinstance(target, type) and own
                    else getattr(target, name))
        originals[(owner, name)] = (original, own)
        if isinstance(original, staticmethod):
            setattr(target, name, staticmethod(wrap(original.__func__, component)))
        else:
            setattr(target, name, wrap(original, component))
    try:
        trace: list = []
        started = clock()
        compiled, record, facts = ep._with_split(lambda: ep.fixed_work_call(program, trace=trace))
        wall = clock() - started
    finally:
        for (owner, name), (original, own) in originals.items():
            if own:
                setattr(owners[owner], name, original)
            else:
                delattr(owners[owner], name)
    fingerprint = ep._decision_fingerprint(record, trace, compiled, facts)
    return {"timed_call_wall_seconds": wall, "exclusive_seconds": dict(exclusive),
            "calls": dict(calls), "timed_top_level_seconds": stack[0],
            "untimed_remainder_seconds": wall - sum(exclusive.values()),
            "nodes": record["aggregate"]["nodes"], "fingerprint": fingerprint}


# --------------------------------------------------------------------------
# Workload capture
# --------------------------------------------------------------------------


class _Capture:
    """Process-wide capture state (the trace mode runs one compile per process)."""

    def __init__(self) -> None:
        self.records: List[dict] = []
        self.events: List[list] = []
        self.outputs: List[Optional[str]] = []
        self.emitted: List[int] = []
        self.registry: Dict[int, int] = {}
        self.keep: List[object] = []          # keeps registered objects alive (ids stay unique)
        self.stats: Optional[es.PropagationStats] = None

    def register(self, obj, event: int) -> None:
        if obj is not None:
            self.registry[id(obj)] = event
            self.keep.append(obj)

    def ref(self, obj) -> Optional[int]:
        if obj is None:
            return None
        return self.registry[id(obj)]

    def start(self) -> tuple:
        return len(self.events), self.stats.stream_length

    def finish(self, event: list, before: int, result) -> None:
        self.events.append(event)
        self.emitted.append(self.stats.stream_length - before)
        self.outputs.append(_out_digest(result))


CAPTURE: Optional[_Capture] = None


def _plain(value):
    if isinstance(value, dict):
        return {str(k): _plain(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(v) for v in value]
    return value


def _out_digest(result) -> Optional[str]:
    if result is None:
        return None
    if isinstance(result, dict):
        return hashlib.sha256(repr(sorted(result.items())).encode()).hexdigest()[:24]
    return hashlib.sha256(repr(result).encode()).hexdigest()[:24]


class TracePropagation(es.Propagation):
    """R0's propagation; each public call is delegated unchanged and recorded."""

    def __init__(self, domain, stats) -> None:
        super().__init__(domain, stats)
        cap = CAPTURE
        cap.stats = stats
        self._index = len(cap.records)
        cap.records.append(_plain(domain.record))
        self._ctx = None

    def times_fixpoint(self, D):
        cap = CAPTURE
        ev, before = cap.start()
        ctx = self._ctx
        if ctx == "root":
            event = ["T", ev, self._index, None, {str(k): list(v) for k, v in D.items()},
                     None, None]
        else:
            op = self.domain.selected_operations[ctx.position]
            event = ["T", ev, self._index, cap.ref(ctx.D), None, op, D[op][0]]
        result = super().times_fixpoint(D)
        cap.register(result, ev)
        cap.finish(event, before, result)
        return result

    def prune(self, D, A, best):
        cap = CAPTURE
        ev, before = cap.start()
        event = ["P", ev, self._index, cap.ref(D), cap.ref(A), best]
        result = super().prune(D, A, best)
        cap.finish(event, before, result)
        return result

    def address_pairs(self, lifetimes):
        cap = CAPTURE
        ev, before = cap.start()
        event = ["L", ev, self._index, {k: list(v) for k, v in lifetimes.items()}]
        result = super().address_pairs(lifetimes)
        cap.register(result, ev)
        cap.finish(event, before, result)
        return result

    def addresses_fixpoint(self, A, pairs):
        cap = CAPTURE
        ev, before = cap.start()
        ctx = self._ctx
        if ctx.phase == "time":
            event = ["A", ev, self._index, None, cap.ref(pairs),
                     {k: list(v) for k, v in A.items()}, None, None]
        else:
            name = ctx.order[ctx.position]
            event = ["A", ev, self._index, cap.ref(ctx.A), cap.ref(pairs), None, name,
                     A[name][0]]
        result = super().addresses_fixpoint(A, pairs)
        cap.register(result, ev)
        cap.finish(event, before, result)
        return result


class TraceExpander(es.Expander):
    """R0's expander; only sets the propagation's context before each resumption."""

    def root(self, best):
        if self.prop is not None:
            self.prop._ctx = "root"
        return super().root(best)

    def children(self, node, best_ref):
        gen = super().children(node, best_ref)
        while True:
            if self.prop is not None:
                self.prop._ctx = node
            try:
                child = next(gen)
            except StopIteration:
                return
            yield child


def _with_trace(fn):
    originals = es.Expander, es.Propagation
    es.Expander, es.Propagation = TraceExpander, TracePropagation
    try:
        return fn()
    finally:
        es.Expander, es.Propagation = originals


def traced_call(program):
    global CAPTURE
    CAPTURE = _Capture()
    trace: list = []
    compiled, record, facts = _with_trace(lambda: ep.fixed_work_call(program, trace=trace))
    cap, CAPTURE = CAPTURE, None
    return cap, ep._decision_fingerprint(record, trace, compiled, facts), record


def mode_workload_trace(program, path: str) -> dict:
    cap, fingerprint, record = traced_call(program)
    kinds = collections.Counter(e[0] for e in cap.events)
    roots = collections.Counter(e[0] for e in cap.events
                                if e[0] in ("T", "A") and e[3] is None)
    payload = {"seed_program_sha256": gp.program_digest(program), "records": cap.records,
               "events": cap.events, "outputs": cap.outputs, "emitted": cap.emitted,
               "certificate_stream_sha256": record["propagation"]["certificate_stream_sha256"],
               "certificate_stream_length": record["propagation"]["certificate_stream_length"]}
    data = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "wb") as handle:
        handle.write(gzip.compress(data, mtime=0))
    shown = Path(path).resolve()
    shown = shown.relative_to(tc.ROOT) if shown.is_relative_to(tc.ROOT) else shown
    return {"workload_path": str(shown),
            "workload_sha256": oc.sha256_bytes(data), "events": len(cap.events),
            "event_kinds": dict(kinds), "root_calls": dict(roots),
            "propagations": len(cap.records), "fingerprint": fingerprint}


# --------------------------------------------------------------------------
# Other modes
# --------------------------------------------------------------------------


def mode_time(program) -> dict:
    return ep.mode_time(program)


def mode_peak_memory(program) -> dict:
    return ep.mode_memory(program)


def mode_instrumentation_parity(program) -> dict:
    trace: list = []
    compiled, record, facts = ep.fixed_work_call(program, trace=trace)
    plain = ep._decision_fingerprint(record, trace, compiled, facts)
    timers = mode_exclusive_timers(program)["fingerprint"]
    _, traced, _ = traced_call(program)
    return {"plain": plain, "timers_equal_plain": timers == plain,
            "trace_equal_plain": traced == plain,
            "parity": timers == plain and traced == plain}


def worker(spec: dict) -> dict:
    program = gp.additional_program(spec["seed"])
    if gp.program_digest(program) != spec["program_sha256"]:
        raise RuntimeError("program digest differs from the frozen key")
    mode = spec["mode_key"]
    if mode == "work:10000":
        body = mode_time(program)
    elif mode == "exclusive_timers":
        body = mode_exclusive_timers(program)
    elif mode == "workload_trace":
        body = mode_workload_trace(program, spec["workload_path"])
    elif mode == "peak_memory":
        body = mode_peak_memory(program)
    elif mode == "instrumentation_parity":
        body = mode_instrumentation_parity(program)
    else:
        raise ValueError(mode)
    return {"family": tc.family_of(spec["seed"]), **body}


# --------------------------------------------------------------------------
# Driver
# --------------------------------------------------------------------------


def specs(run: Path) -> List[dict]:
    out = []
    for seed in tc.diagnostic_seeds():
        digest = gp.program_digest(gp.additional_program(seed))
        for mode in MODES:
            for rep in range(tc.TIME_REPS if mode == "work:10000" else 1):
                spec = {"stage_id": STAGE, "program_sha256": digest, "seed": seed,
                        "repetition": rep, "arm_id": ARM, "mode_key": mode}
                if mode == "workload_trace":
                    spec["workload_path"] = str(Path(run) / "stages" / STAGE / "workloads"
                                                / f"{seed}.json.gz")
                out.append(spec)
    # Deterministic randomized order (protocol order key), repetitions 0-based.
    return sorted(out, key=lambda s: (tc.stable_seed([tc.SEED_ARM_ORDER, s["stage_id"],
                                                      s["program_sha256"], s["repetition"],
                                                      s["arm_id"], s["mode_key"]]),
                                      s["arm_id"], s["mode_key"]))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec")
    parser.add_argument("--run")
    args = parser.parse_args(argv)
    if args.spec:
        result = worker(json.loads(args.spec))
        sys.stdout.write(json.dumps(result, sort_keys=True) + "\n")
        return 0
    all_specs = specs(Path(args.run))
    if len(all_specs) != tc.EXPECTED_ROWS[STAGE]:
        raise RuntimeError(f"{len(all_specs)} specs, expected {tc.EXPECTED_ROWS[STAGE]}")
    report = tc.run_stage(Path(args.run), STAGE, all_specs, "research.third_round_diagnosis",
                          timeout=tc.EXTERNAL_SECONDS)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in report.items()}))
    return 0 if report["complete"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
