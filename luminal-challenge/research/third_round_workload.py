"""Captured propagation workloads of M0: loading, baseline replay and the reuse counts.

A workload (``third_round_diagnosis.mode_workload_trace``) is the ordered list
of R0 propagation calls of one fixed-work compile, each linked to the call that
produced its parent node's domains:

- ``["T", ev, prop, parent_ev, D_in, op, value]`` ``times_fixpoint``. A root call
  (``parent_ev`` None) carries its full input ``D_in``; a child call is
  ``dict(parent output)`` with ``op`` fixed to ``value`` (``Expander.children``).
- ``["P", ev, prop, d_ev, a_ev, best]`` ``prune`` on those outputs.
- ``["L", ev, prop, lifetimes]`` ``address_pairs``.
- ``["A", ev, prop, parent_ev, pairs_ev, A_in, name, value]`` ``addresses_fixpoint``
  (root: full ``A_in``; child: ``dict(parent output)`` with ``name`` fixed).

``prepare`` turns the JSON back into the exact Python inputs and rebuilds each
``se.Domain`` once, OUTSIDE any timed region. ``replay_baseline`` re-executes
R0's own methods in the captured order (the child copy of ``Expander.children``
included), frees every output after its last use, and returns per-event emitted
counts and output digests for comparison with the capture.

``reuse_counts`` measures, on the same workload, how much of R0's work re-derives
facts that have not changed since the parent node (M0: "changes and reused
subcomputations, not whole-call inputs").
"""

from __future__ import annotations

import bisect
import collections
import gzip
import json
from pathlib import Path
from typing import Dict, List, Optional

import machine

from research import efficiency_search as es
from research import structural_encoding as se
from research import third_round_diagnosis as td


def load(path: Path) -> dict:
    return json.loads(gzip.decompress(Path(path).read_bytes()))


def prepare(workload: dict) -> dict:
    """Exact Python inputs and rebuilt domains (untimed)."""

    memo: dict = {}
    domains = []
    for record in workload["records"]:
        domains.append(se.Domain.from_record(record, memo=memo))
    events = []
    last_use: Dict[int, int] = {}
    for e in workload["events"]:
        kind = e[0]
        if kind == "T":
            _, ev, prop, parent, d_in, op, value = e
            if d_in is not None:
                d_in = {int(k): tuple(v) for k, v in d_in.items()}
            else:
                last_use[parent] = ev
            events.append(("T", ev, prop, parent, d_in, op, value))
        elif kind == "P":
            _, ev, prop, d_ev, a_ev, best = e
            last_use[d_ev] = ev
            if a_ev is not None:
                last_use[a_ev] = ev
            events.append(("P", ev, prop, d_ev, a_ev, best))
        elif kind == "L":
            _, ev, prop, lifetimes = e
            events.append(("L", ev, prop, {k: tuple(v) for k, v in lifetimes.items()}))
        elif kind == "A":
            _, ev, prop, parent, pairs_ev, a_in, name, value = e
            last_use[pairs_ev] = ev
            if a_in is not None:
                a_in = {k: tuple(v) for k, v in a_in.items()}
            else:
                last_use[parent] = ev
            events.append(("A", ev, prop, parent, pairs_ev, a_in, name, value))
        else:
            raise ValueError(kind)
    # Outputs referenced later are kept until their last use; the rest are freed.
    for ev in range(len(events)):
        last_use.setdefault(ev, -1)
    release: Dict[int, List[int]] = collections.defaultdict(list)
    for ev, last in last_use.items():
        if last >= 0:
            release[last].append(ev)
    return {"domains": domains, "events": events,
            "release": {k: tuple(v) for k, v in release.items()},
            "keep_after": {ev for ev, last in last_use.items() if last >= 0},
            "certificate_stream_sha256": workload["certificate_stream_sha256"],
            "certificate_stream_length": workload["certificate_stream_length"],
            "outputs": workload["outputs"], "emitted": workload["emitted"]}


def replay_baseline(prepared: dict, stats: es.PropagationStats, record: bool = True) -> dict:
    """R0's own methods on the captured calls, in order; the timed body of a baseline row."""

    domains = prepared["domains"]
    release = prepared["release"]
    keep = prepared["keep_after"]
    props: Dict[int, es.Propagation] = {}
    out: Dict[int, object] = {}
    emitted: List[int] = []
    digests: List[Optional[str]] = []
    for event in prepared["events"]:
        kind, ev, index = event[0], event[1], event[2]
        before = stats.stream_length
        prop = props.get(index)
        if prop is None:
            prop = props[index] = es.Propagation(domains[index], stats)
        if kind == "T":
            parent, d_in, op, value = event[3:]
            if parent is None:
                result = prop.times_fixpoint(d_in)
            else:
                D2 = dict(out[parent])
                D2[op] = (value,)
                result = prop.times_fixpoint(D2)
        elif kind == "P":
            d_ev, a_ev, best = event[3:]
            result = prop.prune(out[d_ev], None if a_ev is None else out[a_ev], best)
        elif kind == "L":
            result = prop.address_pairs(event[3])
        else:
            parent, pairs_ev, a_in, name, value = event[3:]
            if parent is None:
                result = prop.addresses_fixpoint(a_in, out[pairs_ev])
            else:
                A2 = dict(out[parent])
                A2[name] = (value,)
                result = prop.addresses_fixpoint(A2, out[pairs_ev])
        if ev in keep:
            out[ev] = result
        for dead in release.get(ev, ()):
            out.pop(dead, None)
        if record:
            emitted.append(stats.stream_length - before)
            digests.append(td._out_digest(result))
    return {"emitted": emitted, "outputs": digests}


def compare_to_capture(prepared: dict, replay: dict, stats: es.PropagationStats) -> dict:
    n = len(prepared["events"])
    if n == 0:
        raise ValueError("refusing to compare an empty workload")
    out_bad = sum(1 for a, b in zip(replay["outputs"], prepared["outputs"]) if a != b)
    em_bad = sum(1 for a, b in zip(replay["emitted"], prepared["emitted"]) if a != b)
    return {"events": n, "output_mismatches": out_bad, "emitted_mismatches": em_bad,
            "length_equal": len(replay["outputs"]) == n,
            "certificate_stream_equal": (stats.digest() == prepared["certificate_stream_sha256"]
                                         and stats.stream_length
                                         == prepared["certificate_stream_length"]),
            "parity": (out_bad == 0 and em_bad == 0 and len(replay["outputs"]) == n
                       and stats.digest() == prepared["certificate_stream_sha256"])}


# --------------------------------------------------------------------------
# Reuse counts (M0): R0's bodies with counters and lineage-aware input memory
# --------------------------------------------------------------------------


class _Counted(es.Propagation):
    """R0 bodies, unchanged in effect, counting evaluations whose inputs are unchanged.

    "Unchanged" for a precedence edge: the four bounds it reads equal those of
    its previous evaluation on the same branch (within the call, else at the end
    of the parent's call). For the capacity scan of an op: its domain and the
    full-cycle set of its engine equal those of its previous scan on the branch.
    For a compulsory-peak value: its producer bounds and consumer minima equal
    those at the parent's prune. For an address pair: the bounds of ``A_v``.
    """

    def __init__(self, domain, stats, counter) -> None:
        super().__init__(domain, stats)
        self.c = counter

    # memory objects travel with outputs: dicts keyed by edge / op / value / pair
    def tf(self, D, memo_in):
        c = self.c
        facts = self.facts
        emit = self.stats.emit
        memo = dict(memo_in) if memo_in is not None else {}
        D = dict(D)
        changed = True
        c["tf_calls"] += 1
        c["tf_root_calls" if memo_in is None else "tf_child_calls"] += 1
        while changed:
            changed = False
            c["tf_sweeps"] += 1
            for index, (u, v, lag) in enumerate(self.edges):
                du, dv = self._t(D, u), self._t(D, v)
                key = (du[0], du[-1], dv[0], dv[-1])
                c["edge_evals"] += 1
                prev = memo.get(("e", index))
                if prev is None:
                    c["edge_evals_cold"] += 1
                elif prev == key:
                    c["edge_evals_unchanged"] += 1
                fired = False
                high = dv[-1] - lag
                if du[-1] > high:
                    kept = du[:bisect.bisect_right(du, high)]
                    removed = du[len(kept):]
                    if u not in D:
                        emit(("EMPTY", "time", u, ("PU", u, v, lag, dv[-1])))
                        return None, None
                    emit(("PU", u, v, lag, dv[-1], removed), len(removed))
                    if not kept:
                        emit(("EMPTY", "time", u))
                        return None, None
                    D[u] = du = kept
                    changed = fired = True
                low = du[0] + lag
                if dv[0] < low:
                    kept = dv[bisect.bisect_left(dv, low):]
                    removed = dv[:len(dv) - len(kept)]
                    if v not in D:
                        emit(("EMPTY", "time", v, ("PL", u, v, lag, du[0])))
                        return None, None
                    emit(("PL", u, v, lag, du[0], removed), len(removed))
                    if not kept:
                        emit(("EMPTY", "time", v))
                        return None, None
                    D[v] = kept
                    changed = fired = True
                c["edge_fires"] += fired
                dv2 = self._t(D, v)
                memo[("e", index)] = (du[0], du[-1], dv2[0], dv2[-1])
            base = self.base_count
            singles: Dict[tuple, List[int]] = {}
            c["rule2_phases"] += 1
            for op in self.selected:
                c["singles_ops_visited"] += 1
                values = D[op]
                if len(values) == 1:
                    singles.setdefault((facts.engine[op], values[0]), []).append(op)
            snap = tuple(sorted((k, len(v)) for k, v in singles.items()))
            prev_snap = memo.get(("s",))
            c["rule2_phases_singles_unchanged"] += prev_snap == snap
            memo[("s",)] = snap
            for (engine, cycle), ops in sorted(singles.items()):
                limit = machine.ENGINE_LIMITS[engine]
                if base.get((engine, cycle), 0) + len(ops) > limit:
                    emit(("EO", engine, cycle,
                          tuple(sorted(self.base_usage.get((engine, cycle), []) + ops)), limit))
                    return None, None
            for op in self.selected:
                values = D[op]
                if len(values) == 1:
                    continue
                engine = facts.engine[op]
                limit = machine.ENGINE_LIMITS[engine]
                fullset = frozenset(c2 for (e2, c2), ops in singles.items() if e2 == engine
                                    and base.get((e2, c2), 0) + len(ops) >= limit)
                c["op_scans"] += 1
                c["value_checks"] += len(values)
                prev = memo.get(("o", op))
                if prev is not None and prev[0] == values and prev[1] == fullset:
                    c["op_scans_unchanged"] += 1
                full = [cycle for cycle in values
                        if base.get((engine, cycle), 0)
                        + len(singles.get((engine, cycle), ())) >= limit]
                if full:
                    c["op_scans_fired"] += 1
                if not full:
                    memo[("o", op)] = (values, fullset)
                    continue
                for cycle in full:
                    emit(("EF", engine, cycle, op, limit), 1)
                kept = tuple(x for x in values if x not in full)
                if not kept:
                    emit(("EMPTY", "time", op))
                    return None, None
                D[op] = kept
                memo[("o", op)] = (kept, fullset)
                changed = True
        return D, memo

    def peak_inputs(self, D):
        facts = self.facts
        out = {}
        for name in self.dynamic_values:
            p = facts.producers[name]
            dp = self._t(D, p)
            out[name] = (dp[0], dp[-1]) + tuple(self._t(D, c)[0] for c in facts.consumers[name])
        return out

    def af(self, A, pairs, memo_in):
        c = self.c
        facts = self.facts
        emit = self.stats.emit
        memo = dict(memo_in) if memo_in is not None else {}
        A = dict(A)
        changed = True
        c["af_calls"] += 1
        c["af_root_calls" if memo_in is None else "af_child_calls"] += 1
        while changed:
            changed = False
            c["af_sweeps"] += 1
            for index, (u, v) in enumerate(pairs):
                au, av = self._a(A, u), self._a(A, v)
                c["pair_evals"] += 1
                key = (av[0], av[-1])
                prev = memo.get(index)
                if prev is None:
                    c["pair_evals_cold"] += 1
                elif prev == key:
                    c["pair_evals_unchanged"] += 1
                memo[index] = key
                lo = av[-1] - facts.width[u] + 1
                hi = av[0] + facts.width[v] - 1
                if lo > hi:
                    continue
                left = bisect.bisect_left(au, lo)
                right = bisect.bisect_right(au, hi)
                if left >= right:
                    continue
                c["pair_fires"] += 1
                removed = au[left:right]
                inputs = (u, v, av[-1], av[0], facts.width[u], facts.width[v])
                if u not in A:
                    emit(("EMPTY", "address", u, ("AL",) + inputs))
                    return None, None
                kept = au[:left] + au[right:]
                emit(("AL",) + inputs + (removed,), len(removed))
                if not kept:
                    emit(("EMPTY", "address", u))
                    return None, None
                A[u] = kept
                changed = True
        return A, memo


def reuse_counts(prepared: dict) -> dict:
    """Replay with counters; also verifies the counted bodies reproduce the capture."""

    counter: collections.Counter = collections.Counter()
    stats = es.PropagationStats()
    domains = prepared["domains"]
    props: Dict[int, _Counted] = {}
    out: Dict[int, tuple] = {}
    peak_memo: Dict[int, dict] = {}
    digests: List[Optional[str]] = []
    for event in prepared["events"]:
        kind, ev, index = event[0], event[1], event[2]
        prop = props.get(index)
        if prop is None:
            prop = props[index] = _Counted(domains[index], stats, counter)
        if kind == "T":
            parent, d_in, op, value = event[3:]
            if parent is None:
                D, memo = prop.tf(d_in, None)
            else:
                pD, pmemo = out[parent]
                counter["child_copy_entries"] += len(pD)
                D2 = dict(pD)
                D2[op] = (value,)
                D, memo = prop.tf(D2, pmemo)
            out[ev] = (D, memo)
            if D is not None:
                peak_memo[ev] = prop.peak_inputs(D)
                if parent is not None and parent in peak_memo:
                    old = peak_memo[parent]
                    new = peak_memo[ev]
                    same = sum(1 for k in new if old.get(k) == new[k])
                    counter["peak_values_after_child"] += len(new)
                    counter["peak_values_unchanged_after_child"] += same
                    counter["peak_children_all_unchanged"] += same == len(new)
                    counter["peak_children"] += 1
            digests.append(td._out_digest(D))
        elif kind == "P":
            d_ev, a_ev, best = event[3:]
            counter["prune_calls"] += 1
            counter["prune_calls_address_phase"] += a_ev is not None
            counter["peak_value_evals"] += len(prop.dynamic_values)
            result = prop.prune(out[d_ev][0], None if a_ev is None else out[a_ev][0], best)
            digests.append(td._out_digest(result))
        elif kind == "L":
            result = prop.address_pairs(event[3])
            counter["pairs_total"] += len(result)
            out[ev] = (result, None)
            digests.append(td._out_digest(result))
        else:
            parent, pairs_ev, a_in, name, value = event[3:]
            pairs = out[pairs_ev][0]
            if parent is None:
                A, memo = prop.af(a_in, pairs, None)
            else:
                pA, pmemo = out[parent]
                A2 = dict(pA)
                A2[name] = (value,)
                A, memo = prop.af(A2, pairs, pmemo)
            out[ev] = (A, memo)
            digests.append(td._out_digest(A))
    bad = sum(1 for a, b in zip(digests, prepared["outputs"]) if a != b)
    counter["counted_output_mismatches"] = bad
    counter["counted_certificate_stream_equal"] = int(
        stats.digest() == prepared["certificate_stream_sha256"])
    return dict(counter)
