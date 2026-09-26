"""The nominated shared-state kernel of the third round (``MECHANISM_SPEC.json``).

ONE query-local representation: an immutable **branch state** per search node,
built when the node's propagation completes and shared, read-only, by all of
its children. It holds the node's domains and the facts derived from them that
R0 re-derives at every child:

- ``TimeState``: time domains ``D``; ``singles`` -- selected singleton issues per
  ``(engine, cycle)`` exactly as R0's last rule-2 snapshot of the node; the
  compulsory-lifetime contribution of every dynamic value and the resulting
  ``(peak, cycle)`` (computed on first use, then reused).
- ``AddressState``: address domains ``A`` and the pair-incidence table of the
  time leaf's ``pairs`` tuple.

A child applies one decision and propagates only what the change can reach. A
single CHANGE RECORD -- which domains lost their minimum or maximum, which became
singletons -- drives every consumer:

- precedence (rule 1): an edge ``(u, v, lag)`` can fire only after ``max(D_v)``
  fell or ``min(D_u)`` rose since it was last satisfied; the kernel evaluates
  exactly those edges, in R0's sweep order (bitmask of edge indices: an edge
  dirtied at a later index is evaluated in the same sweep, an earlier one in the
  next), so every certificate is emitted in R0's order;
- issue capacity (rule 2): only new singletons change the per-cycle counts, so
  only their ``(engine, cycle)`` keys can overflow (EO: first in sorted order)
  and only NEWLY full cycles can be deleted (EF: ops in selected order, values in
  domain order), because every non-singleton domain was already disjoint from
  the older full cycles at the previous rule-2 phase;
- live bounds (rule 4): a value's compulsory interval is recomputed only when
  its producer's bounds or a consumer's minimum changed; if none changed the
  parent's peak is reused;
- address support (rule 3): a pair ``(u, v)`` can fire only after ``min(A_v)``
  rose or ``max(A_v)`` fell; same sweep-order emulation over pair indices.

Roots are computed by R0's own ``times_fixpoint`` (time) or by the emulation
with every pair dirty (address), which is R0's first sweep exactly. Nothing is
kept across siblings except the parent's immutable state; nothing crosses a
``Propagation`` (one query domain) and nothing crosses a compilation.
"""

from __future__ import annotations

import bisect
from typing import Dict, List, Optional, Sequence, Tuple

import machine

from research import efficiency_search as es


class TimeState:
    __slots__ = ("D", "singles", "contrib", "peak", "parent", "changed")

    def __init__(self, D, singles, parent=None, changed=None) -> None:
        self.D = D
        self.singles = singles
        self.contrib = None
        self.peak = None
        self.parent = parent        # held only until the contributions are derived
        self.changed = changed      # ops whose domain differs from the parent's


class AddressState:
    __slots__ = ("A", "info")

    def __init__(self, A, info) -> None:
        self.A = A
        self.info = info


class PairInfo:
    """Pair-incidence of one ``pairs`` tuple: pair indices whose SECOND value is v."""

    __slots__ = ("pairs", "second_mask", "all_mask", "widths")

    def __init__(self, pairs: Sequence[tuple], facts) -> None:
        self.pairs = tuple(pairs)
        second: Dict[str, int] = {}
        for index, (u, v) in enumerate(self.pairs):
            second[v] = second.get(v, 0) | (1 << index)
        self.second_mask = second
        self.all_mask = (1 << len(self.pairs)) - 1
        self.widths = facts.width


class SharedPropagation(es.Propagation):
    """R0's ``Propagation`` plus the branch-state consumers. R0 methods are untouched."""

    def __init__(self, domain, stats) -> None:
        super().__init__(domain, stats)
        facts = self.facts
        in_mask: Dict[int, int] = {}
        out_mask: Dict[int, int] = {}
        for index, (u, v, lag) in enumerate(self.edges):
            out_mask[u] = out_mask.get(u, 0) | (1 << index)
            in_mask[v] = in_mask.get(v, 0) | (1 << index)
        self.in_mask = in_mask        # edges (w, op): dirty when max(D_op) falls
        self.out_mask = out_mask      # edges (op, w): dirty when min(D_op) rises
        self.engine_of = {op: facts.engine[op] for op in self.selected}
        self.selected_index = {op: i for i, op in enumerate(self.selected)}
        values_of: Dict[int, List[int]] = {}
        for index, name in enumerate(self.dynamic_values):
            for op in (facts.producers[name],) + tuple(facts.consumers[name]):
                bucket = values_of.setdefault(op, [])
                if index not in bucket:
                    bucket.append(index)
        self.values_of = values_of    # dynamic value indices read by an op's bounds

    # -- time phase -----------------------------------------------------------

    def _singles_of(self, D) -> Dict[Tuple[str, int], tuple]:
        singles: Dict[Tuple[str, int], tuple] = {}
        engine = self.engine_of
        for op in self.selected:
            values = D[op]
            if len(values) == 1:
                key = (engine[op], values[0])
                singles[key] = singles.get(key, ()) + (op,)
        return singles

    def time_root(self, D) -> Optional[TimeState]:
        out = self.times_fixpoint(D)
        if out is None:
            return None
        return TimeState(out, self._singles_of(out))

    def time_child(self, parent: TimeState, op: int, value: int) -> Optional[TimeState]:
        """R0's ``times_fixpoint(dict(parent.D) with op=(value,))``, emulated exactly."""

        emit = self.stats.emit
        edges = self.edges
        in_mask, out_mask = self.in_mask, self.out_mask
        fixed = self.fixed_times
        base = self.base_count
        engine_of = self.engine_of
        limits = machine.ENGINE_LIMITS
        Dp = parent.D
        old = Dp[op]
        D = dict(Dp)
        D[op] = (value,)
        changed = set()
        pending: List[int] = []
        cur = 0
        if old != (value,):
            changed.add(op)
            if old[-1] != value:
                cur |= in_mask.get(op, 0)
            if old[0] != value:
                cur |= out_mask.get(op, 0)
            pending.append(op)
        singles = parent.singles
        while True:
            nxt = 0
            while cur:
                low = cur & -cur
                i = low.bit_length() - 1
                cur ^= low
                u, v, lag = edges[i]
                du = D.get(u)
                if du is None:
                    du = (fixed[u],)
                dv = D.get(v)
                if dv is None:
                    dv = (fixed[v],)
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
                    changed.add(u)
                    if len(kept) == 1:
                        pending.append(u)
                    m = in_mask.get(u, 0)
                    if m:
                        above = m >> (i + 1) << (i + 1)
                        cur |= above
                        nxt |= m ^ above
                low_bound = du[0] + lag
                if dv[0] < low_bound:
                    kept = dv[bisect.bisect_left(dv, low_bound):]
                    removed = dv[:len(dv) - len(kept)]
                    if v not in D:
                        emit(("EMPTY", "time", v, ("PL", u, v, lag, du[0])))
                        return None
                    emit(("PL", u, v, lag, du[0], removed), len(removed))
                    if not kept:
                        emit(("EMPTY", "time", v))
                        return None
                    D[v] = kept
                    changed.add(v)
                    if len(kept) == 1:
                        pending.append(v)
                    m = out_mask.get(v, 0)
                    if m:
                        above = m >> (i + 1) << (i + 1)
                        cur |= above
                        nxt |= m ^ above
            if pending:
                # Rule 2 with the new singletons of this sweep's snapshot.
                grown = dict(singles)
                touched = []
                for s in pending:
                    key = (engine_of[s], D[s][0])
                    grown[key] = grown.get(key, ()) + (s,)
                    if key not in touched:
                        touched.append(key)
                pending = []
                for key in sorted(touched):
                    engine, cycle = key
                    limit = limits[engine]
                    if base.get(key, 0) + len(grown[key]) > limit:
                        emit(("EO", engine, cycle,
                              tuple(sorted(self.base_usage.get(key, []) + list(grown[key]))),
                              limit))
                        return None
                newly: Dict[str, set] = {}
                for key in touched:
                    engine, cycle = key
                    limit = limits[engine]
                    count = base.get(key, 0)
                    if count + len(singles.get(key, ())) < limit <= count + len(grown[key]):
                        newly.setdefault(engine, set()).add(cycle)
                singles = grown
                if newly:
                    for s in self.selected:
                        full_cycles = newly.get(engine_of[s])
                        if full_cycles is None:
                            continue
                        values = D[s]
                        if len(values) == 1:
                            continue
                        full = [cycle for cycle in values if cycle in full_cycles]
                        if not full:
                            continue
                        engine = engine_of[s]
                        limit = limits[engine]
                        for cycle in full:
                            emit(("EF", engine, cycle, s, limit), 1)
                        kept = tuple(x for x in values if x not in full)
                        if not kept:
                            emit(("EMPTY", "time", s))
                            return None
                        D[s] = kept
                        changed.add(s)
                        if len(kept) == 1:
                            pending.append(s)
                        if kept[-1] != values[-1]:
                            nxt |= in_mask.get(s, 0)
                        if kept[0] != values[0]:
                            nxt |= out_mask.get(s, 0)
            if not nxt and not pending:
                break
            cur = nxt
        return TimeState(D, singles, parent, changed)

    # -- live bounds ----------------------------------------------------------

    def _contribution(self, D, name):
        facts = self.facts
        p = facts.producers[name]
        dp = D.get(p)
        if dp is None:
            dp = (self.fixed_times[p],)
        start_hi = dp[-1] + facts.latency[p]
        end_lo = dp[0] + facts.latency[p]
        fixed = self.fixed_times
        for c in facts.consumers[name]:
            dc_ = D.get(c)
            first = fixed[c] if dc_ is None else dc_[0]
            if first > end_lo:
                end_lo = first
        if start_hi <= end_lo:
            return (start_hi, end_lo, facts.width[name])
        return None

    def live_peak(self, state: TimeState) -> Tuple[int, int]:
        """R0's ``compulsory_peak(state.D)``, reusing the parent's contributions."""

        if state.peak is not None:
            return state.peak
        parent = state.parent
        names = self.dynamic_values
        D = state.D
        if parent is None or parent.contrib is None:
            contrib = [self._contribution(D, name) for name in names]
        else:
            contrib = list(parent.contrib)
            touched = set()
            values_of = self.values_of
            for op in state.changed:
                for index in values_of.get(op, ()):
                    touched.add(index)
            if not touched and parent.peak is not None:
                state.contrib = parent.contrib
                state.peak = parent.peak
                state.parent = state.changed = None
                return state.peak
            for index in touched:
                contrib[index] = self._contribution(D, names[index])
        delta: Dict[int, int] = {}
        for item in contrib:
            if item is not None:
                start_hi, end_lo, w = item
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
        state.contrib = contrib
        state.peak = (best[0], -best[1])
        state.parent = state.changed = None
        return state.peak

    def prune_state(self, state: TimeState, A, best: Optional[int]) -> Tuple[bool, int]:
        """R0's ``prune(state.D, A, best)`` with the live peak taken from the state."""

        facts = self.facts
        D = state.D
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
        live, cycle = self.live_peak(state)
        if live > ls:
            ls, ls_w = live, ("live", cycle)
        if best is not None and lc * ls >= best:
            self.stats.emit(("PB", lc, ls, best, lc_w, ls_w))
            return True, lc * ls
        return False, lc * ls

    # -- address phase --------------------------------------------------------

    def address_root(self, A, pairs) -> Optional[AddressState]:
        info = PairInfo(pairs, self.facts)
        return self._address(dict(A), info, info.all_mask)

    def address_child(self, parent: AddressState, name: str, value: int
                      ) -> Optional[AddressState]:
        old = parent.A[name]
        A = dict(parent.A)
        A[name] = (value,)
        cur = 0
        if old[0] != value or old[-1] != value:
            cur = parent.info.second_mask.get(name, 0)
        return self._address(A, parent.info, cur)

    def _address(self, A, info: PairInfo, cur: int) -> Optional[AddressState]:
        """R0's ``addresses_fixpoint`` sweeps, evaluating only pairs that can fire."""

        width = info.widths
        emit = self.stats.emit
        pairs = info.pairs
        second = info.second_mask
        fixed = self.fixed_addresses
        while cur:
            nxt = 0
            while cur:
                low = cur & -cur
                i = low.bit_length() - 1
                cur ^= low
                u, v = pairs[i]
                au = A.get(u)
                if au is None:
                    au = (fixed[u],)
                av = A.get(v)
                if av is None:
                    av = (fixed[v],)
                lo = av[-1] - width[u] + 1
                hi = av[0] + width[v] - 1
                if lo > hi:
                    continue
                left = bisect.bisect_left(au, lo)
                right = bisect.bisect_right(au, hi)
                if left >= right:
                    continue
                removed = au[left:right]
                inputs = (u, v, av[-1], av[0], width[u], width[v])
                if u not in A:
                    emit(("EMPTY", "address", u, ("AL",) + inputs))
                    return None
                kept = au[:left] + au[right:]
                emit(("AL",) + inputs + (removed,), len(removed))
                if not kept:
                    emit(("EMPTY", "address", u))
                    return None
                A[u] = kept
                if kept[0] != au[0] or kept[-1] != au[-1]:
                    m = second.get(u, 0)
                    if m:
                        above = m >> (i + 1) << (i + 1)
                        cur |= above
                        nxt |= m ^ above
            cur = nxt
        return AddressState(A, info)
