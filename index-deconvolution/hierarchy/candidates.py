"""Deterministic proposal generators. Each receives only a bit string (or its
own derived symbols) and plain parameters -- never a family name, seed, truth or
file name. Proposals are suggestions: the search verifies every one by
evaluation and selects only by complete serialized archive length.

Complexity notes (also in SEARCH_SPEC.md):
  shortest_period       O(n) prefix function;
  ap_runs               O(n);
  ap_cover              O(n * steps) with steps <= 8;
  schema_pairs          delegates to index-deconvolution/src/deconvolution.py
                        ``minimal_dnf``: Quine-McCluskey (worst case exponential
                        in d) plus a GREEDY set cover -- not a certified minimum;
                        callers restrict it to tables of <= 256 entries;
  pair_grammar          incremental RePair-style substitution, O(n log n);
  noisy_periods         O(n) per period via integer XOR and popcount.
"""
from __future__ import annotations

import heapq
import importlib.util
from pathlib import Path

# ---------------------------------------------------------------------------
# Exact period
# ---------------------------------------------------------------------------


def shortest_period(s: str) -> int:
    """Shortest p with s[i] == s[i+p] for all valid i (finite-prefix period)."""
    n = len(s)
    if n == 0:
        return 0
    pi = [0] * n
    k = 0
    for i in range(1, n):
        ch = s[i]
        while k and s[k] != ch:
            k = pi[k - 1]
        if s[k] == ch:
            k += 1
        pi[i] = k
    return n - pi[-1]


# ---------------------------------------------------------------------------
# Arithmetic progressions
# ---------------------------------------------------------------------------


def positions_of(s: str, fg: str) -> list[int]:
    out = []
    i = s.find(fg)
    while i != -1:
        out.append(i)
        i = s.find(fg, i + 1)
    return out


def ap_runs(positions: list[int]) -> list[tuple[int, int, int]]:
    """Greedy left-to-right partition into maximal consecutive constant-gap runs.

    A final singleton is (p, 1, 1).
    """
    runs = []
    i = 0
    m = len(positions)
    while i < m:
        if i + 1 == m:
            runs.append((positions[i], 1, 1))
            break
        step = positions[i + 1] - positions[i]
        j = i + 1
        while j + 1 < m and positions[j + 1] - positions[j] == step:
            j += 1
        runs.append((positions[i], step, j - i + 1))
        i = j + 1
    return runs


def ap_cover(positions: list[int], n: int, max_steps: int = 8,
             lookahead: int = 4, min_count: int = 3) -> list[tuple[int, int, int]]:
    """Cover a position set by possibly interleaved progressions (union semantics).

    Candidate steps are the ``max_steps`` most frequent differences p[i+j]-p[i],
    1 <= j <= lookahead (ties: smaller step). For each step and residue the
    maximal runs of consecutive members with >= ``min_count`` elements are
    collected; runs are chosen greedily by (-count, start, step) while they add
    at least ``min_count`` uncovered positions; the remainder is partitioned
    with ``ap_runs``. Returned triples are sorted and contained in the set.
    """
    m = len(positions)
    if m < 2 * min_count:
        return ap_runs(positions)
    diff_count: dict[int, int] = {}
    for j in range(1, lookahead + 1):
        for i in range(m - j):
            d = positions[i + j] - positions[i]
            diff_count[d] = diff_count.get(d, 0) + 1
    steps = sorted(diff_count, key=lambda d: (-diff_count[d], d))[:max_steps]
    member = bytearray(n)
    for p in positions:
        member[p] = 1
    runs = []
    for step in steps:
        for r in range(step):
            i = r
            while i < n:
                if member[i]:
                    j = i
                    while j + step < n and member[j + step]:
                        j += step
                    count = (j - i) // step + 1
                    if count >= min_count:
                        runs.append((i, step, count))
                    i = j + step
                else:
                    i += step
    runs.sort(key=lambda t: (-t[2], t[0], t[1]))
    covered = bytearray(n)
    chosen = []
    for start, step, count in runs:
        new = 0
        for k in range(count):
            if not covered[start + k * step]:
                new += 1
        if new >= min_count:
            chosen.append((start, step, count))
            covered[start:start + (count - 1) * step + 1:step] = b"\x01" * count
    rest = [p for p in positions if not covered[p]]
    return sorted(set(chosen) | set(ap_runs(rest)))


# ---------------------------------------------------------------------------
# Schema supports (bridge to the exact deconvolution owner)
# ---------------------------------------------------------------------------

_OWNER = None


def _cover_owner():
    """Load ``minimal_dnf`` from index-deconvolution/src/deconvolution.py by path.

    Resolved relative to this repository and asserted, so a same-named module
    injected by a .pth file from a sibling repository cannot be picked up.
    """
    global _OWNER
    if _OWNER is None:
        import sys
        src = Path(__file__).resolve().parents[1] / "src"
        path = src / "deconvolution.py"
        if str(src) not in sys.path:
            sys.path.insert(0, str(src))          # its own import of causalbool
        spec = importlib.util.spec_from_file_location("_hid_deconvolution_owner", path)
        mod = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = mod
        spec.loader.exec_module(mod)
        fn = mod.minimal_dnf
        got = Path(fn.__code__.co_filename).resolve()
        if got != path.resolve() or got.parts[-3:] != ("index-deconvolution", "src",
                                                       "deconvolution.py"):
            raise ImportError(f"schema cover owner resolved to {got}")
        _OWNER = fn
    return _OWNER


def owner_source_path() -> str:
    fn = _cover_owner()
    return fn.__code__.co_filename


def schema_pairs(s: str, fg: str, pad: int) -> list[tuple[int, int]] | None:
    """Schema cover of the ``fg`` support of ``s``, or None if it fails to verify.

    The membership table is padded to 2^d with ``pad`` (a proposal device only),
    covered by the owner, translated to (mask, value) pairs, clipped to the
    actual domain and verified on the unpadded positions.
    """
    length = len(s)
    d = (length - 1).bit_length()
    table = [1 if ch == fg else 0 for ch in s] + [pad] * ((1 << d) - length)
    clauses = _cover_owner()(table)
    pairs = set()
    for cl in clauses:
        mask = 0
        value = 0
        for j in cl["activators"]:
            mask |= 1 << j
            value |= 1 << j
        for j in cl["inhibitors"]:
            mask |= 1 << j
        if value < length:
            pairs.add((mask, value))
    pairs = sorted(pairs)
    for i, ch in enumerate(s):
        hit = any((i & m) == v for m, v in pairs)
        if hit != (ch == fg):
            return None
    return pairs


# ---------------------------------------------------------------------------
# Noisy periods
# ---------------------------------------------------------------------------

NOISY_PERIODS = tuple(range(1, 33)) + (64, 128, 256)


def noisy_periods(s: str, keep: int = 3) -> list[tuple[int, int, list[int]]]:
    """(errors, period, error positions) for the ``keep`` best periods.

    Periods 1..32, 64, 128, 256 up to floor(n/2); the base repeats the observed
    first period. Ordered by (errors, period).
    """
    n = len(s)
    if n < 2:
        return []
    x = int(s, 2)
    scored = []
    for p in NOISY_PERIODS:
        if p > n // 2:
            break
        base = (s[:p] * (n // p + 1))[:n]
        scored.append(((x ^ int(base, 2)).bit_count(), p))
    scored.sort()
    out = []
    for err, p in scored[:keep]:
        base = (s[:p] * (n // p + 1))[:n]
        diff = format(x ^ int(base, 2), "b").zfill(n) if err else ""
        out.append((err, p, positions_of(diff, "1") if err else []))
    return out


# ---------------------------------------------------------------------------
# Deterministic pair grammar (wire annex W7)
# ---------------------------------------------------------------------------


def pair_grammar(seq: list[int], first_id: int, max_rules: int
                 ) -> tuple[list[tuple[int, int]], list[int]]:
    """RePair-style substitution, exactly as fixed in W7.

    Repeatedly: rank adjacent pairs of the current stream by overlapping
    frequency (descending), ties by (left, right); select the first pair with at
    least two non-overlapping occurrences under left-to-right greedy
    replacement; give it the next id; replace those occurrences. Stops when no
    pair qualifies or ``max_rules`` rules exist. Returns (rules, start stream).

    Incremental: a doubly linked list over positions, per-pair occurrence sets
    and a lazy max-heap keyed (-count, left, right).
    """
    n = len(seq)
    if n < 2:
        return [], list(seq)
    sym: list[int | None] = list(seq)
    nxt = list(range(1, n + 1))
    nxt[-1] = -1
    prv = list(range(-1, n - 1))
    occ: dict[tuple[int, int], set[int]] = {}
    for i in range(n - 1):
        occ.setdefault((seq[i], seq[i + 1]), set()).add(i)
    heap = [(-len(v), a, b) for (a, b), v in occ.items() if len(v) >= 2]
    heapq.heapify(heap)
    rules: list[tuple[int, int]] = []

    def nonoverlap_at_least_two(pair, pos_set) -> bool:
        if pair[0] != pair[1] or len(pos_set) >= 3:
            return len(pos_set) >= 2
        a, b = sorted(pos_set)              # exactly two: overlapping iff adjacent
        return nxt[a] != b

    while len(rules) < max_rules:
        skipped = []
        chosen = None
        while heap:
            negc, a, b = heapq.heappop(heap)
            cur = occ.get((a, b))
            cnt = len(cur) if cur else 0
            if cnt != -negc or cnt < 2:
                continue
            if not nonoverlap_at_least_two((a, b), cur):
                skipped.append((negc, a, b))
                continue
            chosen = (a, b)
            break
        for e in skipped:
            heapq.heappush(heap, e)
        if chosen is None:
            break
        a, b = chosen
        new = first_id + len(rules)
        rules.append(chosen)
        touched: dict[tuple[int, int], None] = {}

        def dec(pair, pos):
            st = occ.get(pair)
            if st is not None:
                st.discard(pos)
                touched[pair] = None

        def inc(pair, pos):
            occ.setdefault(pair, set()).add(pos)
            touched[pair] = None

        for i in sorted(occ.pop(chosen)):
            if sym[i] != a:
                continue
            j = nxt[i]
            if j == -1 or sym[j] != b:
                continue
            p = prv[i]
            k = nxt[j]
            if p != -1:
                dec((sym[p], a), p)
            if k != -1:
                dec((b, sym[k]), j)
            sym[i] = new
            sym[j] = None
            nxt[i] = k
            if k != -1:
                prv[k] = i
            if p != -1:
                inc((sym[p], new), p)
            if k != -1:
                inc((new, sym[k]), i)
        for pair in touched:
            st = occ.get(pair)
            if st is not None and pair != chosen:
                if not st:
                    del occ[pair]
                elif len(st) >= 2:
                    heapq.heappush(heap, (-len(st), pair[0], pair[1]))
    start = []
    i = 0
    while i != -1:
        start.append(sym[i])
        i = nxt[i]
    return rules, start


def pair_grammar_reference(seq: list[int], first_id: int, max_rules: int
                           ) -> tuple[list[tuple[int, int]], list[int]]:
    """Slow, obviously-correct W7 reference used only by tests."""
    stream = list(seq)
    rules: list[tuple[int, int]] = []
    while len(rules) < max_rules:
        freq: dict[tuple[int, int], int] = {}
        for x, y in zip(stream, stream[1:]):
            freq[(x, y)] = freq.get((x, y), 0) + 1
        chosen = None
        for pair in sorted(freq, key=lambda q: (-freq[q], q)):
            if freq[pair] < 2:
                break
            k, i = 0, 0
            while i < len(stream) - 1:
                if (stream[i], stream[i + 1]) == pair:
                    k += 1
                    i += 2
                else:
                    i += 1
            if k >= 2:
                chosen = pair
                break
        if chosen is None:
            break
        new = first_id + len(rules)
        rules.append(chosen)
        out, i = [], 0
        while i < len(stream):
            if i + 1 < len(stream) and (stream[i], stream[i + 1]) == chosen:
                out.append(new)
                i += 2
            else:
                out.append(stream[i])
                i += 1
        stream = out
    return rules, stream
