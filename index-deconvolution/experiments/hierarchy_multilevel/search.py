"""HID multilevel v1: the single owner of the multi-width, multi-level augmentation.

``augment(bits, config, baseline_archive)`` receives the input bits, an immutable
``MultilevelConfig`` and the completed, verified A0 (search-v2 k=1) archive, nothing
else (SEARCH section 1). It enumerates reversible views by (level, width, origin),
offers the exact proposals G0, G1, G2, G3 of every evaluated view in that order, and
keeps the incumbent unless a complete, independently decoded candidate archive is
strictly shorter. Earlier incumbents win ties, so A0 is retained on equality.

Representation (SEARCH section 2). At width b, origin o, level l the span is
s = b * 2**(l-1) and m = floor((n-o)/s); the view covers x[o:o+m*s] and keeps the exact
literal prefix x[:o] and suffix x[o+m*s:]. Level-1 symbols are the distinct b-bit words
(LITERAL rules); level-l symbols are the distinct ordered pairs of level-(l-1) symbols
(CONCAT rules over the lower dictionary), numbered by first appearance. An odd trailing
lower symbol therefore falls into the higher view's literal suffix; no bit is dropped.

Proposals (SEARCH section 3). Every proposal is a full-input root
CONCAT(prefix?, core, suffix?) built in one ``NodeFactory`` per view, serialized with the
owner writer and decoded by the owner's independent decoder before it may be accepted;
a disagreement raises ``DecodeMismatch`` (fatal INVALID).

  G0  maximal runs of one top symbol become REPEAT (count >= 2), concatenated in order;
  G1  the owner ``candidates.pair_grammar`` on the top stream (first_id = k, max 64 rules),
      its rules rebuilt as CONCAT, then the G0 run construction on its start stream;
  G2/G3  occurrence-gap templates: the first and second gap p of the pooled consecutive
      occurrence differences ranked (count desc, gap asc) with 1 <= p < m; the core is
      REPEAT(T, m // p) followed by the first m % p symbols of T = top[:p], with every
      differing bit PATCHed (more than 64 flips: PATCH_LIMIT_REJECTION, no archive).

Diagnostics (SEARCH section 5) are observational records computed from the input only:
they never feed back into what is proposed or selected. Token coordinates (positions in
the top stream) and bit coordinates (positions in x) are kept in separately named fields.
"""
from __future__ import annotations

import hashlib
import json
import time
from collections import Counter
from dataclasses import asdict, dataclass

from hierarchy.candidates import pair_grammar, shortest_period
from hierarchy.decode import decode_archive
from hierarchy.model import NodeFactory, check_bits, count_reachable, to_model
from hierarchy.segmentation import DecodeMismatch
from hierarchy.wire import serialize_model

WIDTHS = (4, 8, 12, 16, 24, 32, 48, 64)
PROPOSALS = ("G0", "G1", "G2", "G3")

# view status
EVALUATED = "EVALUATED"
INELIGIBLE_SHORT = "INELIGIBLE_SHORT"
SATURATED = "SATURATED_REPETITION_BRANCH"
SINGLE = "SINGLE_SYMBOL_BRANCH"
VIEW_CAP = "NOT_REACHED_VIEW_CAP"
REQUEST_CAP_VIEW = "NOT_REACHED_REQUEST_CAP"
# proposal status
P_NEW = "SERIALIZED_DECODED"
P_DUP = "DUPLICATE_ARCHIVE"
P_GRAPH = "GRAPH_REJECTION"
P_PATCH = "PATCH_LIMIT_REJECTION"
P_NOGAP = "NO_GAP_TEMPLATE"
P_CAP = "NOT_REQUESTED_REQUEST_CAP"
# description-gap status of a view
D_SHORTER = "SHORTER_THAN_A0"
D_NOT_SHORTER = "NO_SHORTER_CANDIDATE_AMONG_EVALUATED"
D_NONE = "NO_ADMISSIBLE_CANDIDATE"


class BaselineUnusable(ValueError):
    """The supplied A0 archive does not decode to the input."""


@dataclass(frozen=True)
class MultilevelConfig:
    """Every knob of one augmentation arm (contract.json ``arms`` and ``limits``)."""

    name: str
    widths: tuple
    max_level: int
    max_views: int = 64
    max_requests: int = 256
    pair_rules_per_view: int = 64
    max_rules: int = 4096
    max_depth: int = 64
    patch_flips: int = 64
    gap_templates: int = 2

    def __post_init__(self):
        if tuple(sorted(set(self.widths))) != tuple(self.widths) or not self.widths:
            raise ValueError("widths must be a nonempty strictly ascending tuple")
        if min(self.widths) < 1 or self.max_level < 1:
            raise ValueError("widths and max_level must be positive")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["widths"] = list(self.widths)
        return d

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode()).hexdigest()

    def views(self) -> list[tuple[int, int, int]]:
        """(level, width, origin) in the fixed enumeration order."""
        return [(lv, b, o) for lv in range(1, self.max_level + 1) for b in self.widths
                for o in (0, b // 2)]


ARMS = {
    "A1": MultilevelConfig("word8_l1", (8,), 1),
    "A2": MultilevelConfig("multi_l1", WIDTHS, 1),
    "A3": MultilevelConfig("multi_l4", WIDTHS, 4),
}


# ---------------------------------------------------------------------------
# Reversible abstraction (pure data, no nodes)
# ---------------------------------------------------------------------------

def canonical(stream) -> tuple[list[int], list]:
    """Relabel by first appearance; returns (stream of ids, id -> original label)."""
    ids: dict = {}
    out = []
    for t in stream:
        if t not in ids:
            ids[t] = len(ids)
        out.append(ids[t])
    return out, list(ids)


@dataclass
class Level:
    level: int
    span: int
    m: int
    stream: list          # top token ids, first-appearance canonical
    entries: list         # level 1: words (str); level > 1: (lower id, lower id) pairs
    expansions: list      # exact bit string of every id at this level


def path_levels(x: str, width: int, origin: int, max_level: int) -> list[Level]:
    """Levels 1..max_level of one (width, origin) partition while m >= 1."""
    n = len(x)
    out: list[Level] = []
    m = (n - origin) // width if n > origin else 0
    words = [x[origin + i * width: origin + (i + 1) * width] for i in range(m)]
    stream, entries = canonical(words)
    out.append(Level(1, width, m, stream, entries, list(entries)))
    for lv in range(2, max_level + 1):
        low = out[-1]
        m2 = low.m // 2
        pairs = [(low.stream[2 * i], low.stream[2 * i + 1]) for i in range(m2)]
        stream, entries = canonical(pairs)
        exps = [low.expansions[a] + low.expansions[b] for a, b in entries]
        out.append(Level(lv, low.span * 2, m2, stream, entries, exps))
    return out


def runs(stream) -> list[tuple[int, int]]:
    out: list[list[int]] = []
    for t in stream:
        if out and out[-1][0] == t:
            out[-1][1] += 1
        else:
            out.append([t, 1])
    return [(a, c) for a, c in out]


def occurrences(stream) -> dict[int, list[int]]:
    occ: dict[int, list[int]] = {}
    for i, t in enumerate(stream):
        occ.setdefault(t, []).append(i)
    return occ


def ranked_gaps(stream, m: int) -> list[tuple[int, int]]:
    """Pooled consecutive occurrence differences as (gap, count), ranked
    (count descending, gap ascending), restricted to 1 <= gap < m."""
    pooled: Counter = Counter()
    for js in occurrences(stream).values():
        pooled.update(b - a for a, b in zip(js, js[1:]))
    return sorted(((g, c) for g, c in pooled.items() if 1 <= g < m), key=lambda t: (-t[1], t[0]))


def modal_gap(diffs) -> tuple[int | None, float | None]:
    if not diffs:
        return None, None
    cnt = Counter(diffs)
    mode = min(cnt, key=lambda g: (-cnt[g], g))
    return mode, sum(1 for d in diffs if d != mode) / len(diffs)


def merge_intervals(iv) -> list[list[int]]:
    out: list[list[int]] = []
    for a, b in sorted(iv):
        if a >= b:
            continue
        if out and a <= out[-1][1]:
            out[-1][1] = max(out[-1][1], b)
        else:
            out.append([a, b])
    return out


# ---------------------------------------------------------------------------
# Proposal construction (one NodeFactory per view)
# ---------------------------------------------------------------------------

class ViewBuilder:
    def __init__(self, x: str, levels: list[Level], origin: int) -> None:
        self.x, self.levels, self.origin = x, levels, origin
        self.top = levels[-1]
        self.f = NodeFactory()
        lv1 = levels[0]
        nodes = [self.f.literal(w) for w in lv1.entries]
        for L in levels[1:]:
            nodes = [self.f.concat((nodes[a], nodes[b])) for a, b in L.entries]
        self.sym = nodes                                  # top-level dictionary nodes
        top = self.top
        self.core_start = origin
        self.core_end = origin + top.m * top.span
        self.prefix = x[:origin]
        self.suffix = x[self.core_end:]

    def wrap(self, core):
        pieces = ([self.f.literal(self.prefix)] if self.prefix else []) + [core] + \
                 ([self.f.literal(self.suffix)] if self.suffix else [])
        return self.f.concat(pieces)

    def run_core(self, stream, nodes):
        kids = [self.f.repeat(nodes[s], c) for s, c in runs(stream)]
        return self.f.concat(kids)

    def g0(self):
        return self.wrap(self.run_core(self.top.stream, self.sym)), {}

    def g1(self, max_rules: int):
        k = len(self.sym)
        rules, start = pair_grammar(list(self.top.stream), k, max_rules)
        nodes = dict(enumerate(self.sym))
        rdepth = {i: 0 for i in range(k)}
        for i, (a, b) in enumerate(rules):
            nodes[k + i] = self.f.concat((nodes[a], nodes[b]))
            rdepth[k + i] = 1 + max(rdepth[a], rdepth[b])
        detail = {"pair_rules": len(rules), "start_length": len(start),
                  "pair_rule_depth": max((rdepth[k + i] for i in range(len(rules))), default=0)}
        return self.wrap(self.run_core(start, nodes)), detail

    def gap(self, p: int, flip_cap: int):
        top = self.top
        T = top.stream[:p]
        tnode = self.f.concat([self.sym[s] for s in T])
        q, r = divmod(top.m, p)
        pred = self.f.concat([self.f.repeat(tnode, q)] + [self.sym[s] for s in T[:r]])
        got = self.f.expand(pred)
        actual = self.x[self.core_start:self.core_end]
        flips = [i for i, (a, b) in enumerate(zip(got, actual)) if a != b]
        detail = {"gap": p, "copies": q, "remainder_symbols": r, "patch_flips": len(flips)}
        if len(flips) > flip_cap:
            return None, detail
        return self.wrap(self.f.patch(pred, flips)), detail


# ---------------------------------------------------------------------------
# Observational view diagnostics (never used by selection)
# ---------------------------------------------------------------------------

def view_diagnostics(x: str, levels: list[Level], width: int, origin: int) -> dict:
    n = len(x)
    top = levels[-1]
    occ = occurrences(top.stream)
    per_symbol, pooled = [], Counter()
    for s in range(len(top.entries)):
        js = occ.get(s, [])
        diffs = [b - a for a, b in zip(js, js[1:])]
        pooled.update(diffs)
        mode, irr = modal_gap(diffs)
        per_symbol.append({"symbol": s, "count": len(js), "token_positions": js,
                           "gaps": diffs, "modal_gap": mode, "irregular_fraction": irr,
                           "unavailable_reason": None if diffs else "single_occurrence"})
    core_end = origin + top.m * top.span
    singles = [s for s in range(len(top.entries)) if len(occ.get(s, [])) == 1]
    iv = [[origin + occ[s][0] * top.span, origin + (occ[s][0] + 1) * top.span] for s in singles]
    iv += [[0, origin], [core_end, n]]
    merged = merge_intervals(iv)
    weak_bits = sum(b - a for a, b in merged)
    content = []
    for s, e in enumerate(top.expansions):
        p = shortest_period(e)
        content.append({"symbol": s, "length": len(e), "shortest_period": p,
                        "complete_repeat": len(e) % p == 0, "proper_repeat": len(e) % p == 0 and p < len(e)})
    pooled_mode, pooled_irr = modal_gap(list(pooled.elements()))
    reused = sum(1 for s in occ if len(occ[s]) >= 2)
    return {
        "dictionary": ([{"symbol": s, "word": w} for s, w in enumerate(top.entries)]
                       if top.level == 1 else
                       [{"symbol": s, "lower_pair": list(pr)} for s, pr in enumerate(top.entries)]),
        "dictionary_content": content,
        "top_stream": list(top.stream),
        "token_span_bits": top.span,
        "bit_start_of_token_0": origin,
        "occurrence": {"per_symbol": per_symbol,
                       "pooled_gap_counts": {str(g): c for g, c in sorted(pooled.items())},
                       "pooled_modal_gap": pooled_mode, "pooled_irregular_fraction": pooled_irr,
                       "unavailable_reason": None if pooled else "no_repeated_symbol"},
        "weak_support": {"bits": weak_bits, "fraction_of_n": weak_bits / n if n else None,
                         "bit_intervals": merged, "singleton_symbols": len(singles)},
        "symbols_reused": reused, "symbols_singleton": len(singles),
        "forced_grouping_entries": len(singles) if top.level > 1 else None,
        "dictionary_depth": top.level,
    }


# ---------------------------------------------------------------------------
# The search
# ---------------------------------------------------------------------------

@dataclass
class AugmentResult:
    archive: bytes
    selected: dict
    views: list
    counters: dict
    stop_reason: str
    config_name: str
    config_sha256: str


class _Inc:
    def __init__(self, a0: bytes) -> None:
        self.archive, self.source = a0, {"source": "A0"}
        self.trace: list[dict] = []

    def offer(self, arc: bytes, source: dict) -> bool:
        if len(arc) < len(self.archive):
            self.archive, self.source = arc, source
            self.trace.append(dict(source, archive_bits=8 * len(arc)))
            return True
        return False


def augment(bits: str, config: MultilevelConfig, baseline_archive: bytes,
            on_improve=None, on_view=None) -> AugmentResult:
    """Best complete archive among A0 and this arm's proposals (strictly shorter wins).

    ``on_improve(archive, record)`` is called at every strict improvement (checkpoint);
    ``on_view(record)`` after every view record is final. Neither may alter the search.
    """
    check_bits(bits)
    if not isinstance(config, MultilevelConfig) or type(baseline_archive) is not bytes:
        raise TypeError("config must be a MultilevelConfig and the baseline bytes")
    if decode_archive(baseline_archive) != bits:
        raise BaselineUnusable("the A0 archive does not decode to the input")
    n = len(bits)
    inc = _Inc(baseline_archive)
    a0_bits = 8 * len(baseline_archive)
    cnt = {"views_listed": 0, "views_evaluated": 0, "requests": 0, "serialized": 0,
           "decoded": 0, "duplicates": 0, "graph_rejections": 0, "patch_rejections": 0,
           "no_gap_template": 0, "strict_improvements": 0, "pair_grammar_rules_built": 0}
    views: list[dict] = []
    if n == 0:
        return AugmentResult(baseline_archive, inc.source, views,
                             dict(cnt, diagnostics_unavailable="empty_input"),
                             "empty_input", config.name, config.sha256())
    seen = {baseline_archive}
    paths = {(b, o): path_levels(bits, b, o, config.max_level)
             for b in config.widths for o in (0, b // 2)}
    blocked: dict[tuple[int, int], str] = {}                # path -> branch stop status
    prev_best: dict[tuple[int, int], tuple[int, int] | None] = {}
    stop = "completed"
    for vi, (lv, b, o) in enumerate(config.views()):
        cnt["views_listed"] += 1
        L = paths[(b, o)][lv - 1]
        k = len(L.entries)
        rec = {"view_index": vi, "level": lv, "width": b, "origin": o, "span": L.span,
               "m": L.m, "k": k if L.m else 0, "k_over_m": (k / L.m) if L.m else None,
               "prefix_bits": o if L.m else None,
               "suffix_bits": (n - o - L.m * L.span) if L.m else None,
               "status": None, "proposals": [], "description_gap": None, "wall_s": None}
        if (b, o) in blocked:
            rec["status"] = blocked[(b, o)]
        elif L.m < 2:
            rec["status"] = INELIGIBLE_SHORT
        elif cnt["views_evaluated"] >= config.max_views:
            rec["status"] = VIEW_CAP
            stop = "work_cap_views"
        elif cnt["requests"] >= config.max_requests:
            rec["status"] = REQUEST_CAP_VIEW
            stop = "work_cap_requests"
        if rec["status"] is not None:
            rec["description_gap"] = {"status": rec["status"], "best_bits": None,
                                      "minus_a0_bits": None, "vs_previous_level_bits": None}
            views.append(rec)
            if on_view:
                on_view(rec)
            continue
        t0 = time.perf_counter()
        cnt["views_evaluated"] += 1
        rec["status"] = EVALUATED
        levels = paths[(b, o)][:lv]
        rec.update(view_diagnostics(bits, levels, b, o))
        vb = ViewBuilder(bits, levels, o)
        gaps = ranked_gaps(L.stream, L.m)
        rec["ranked_gaps"] = [[g, c] for g, c in gaps[:config.gap_templates]]
        best = None
        for pid in PROPOSALS:
            prec = {"proposal": pid, "status": None, "archive_bits": None,
                    "archive_sha256": None, "rule_count": None, "dag_depth": None,
                    "accepted": False, "detail": {}}
            rec["proposals"].append(prec)
            gi = PROPOSALS.index(pid) - 2
            if gi >= 0 and gi >= len(gaps):
                prec["status"] = P_NOGAP
                cnt["no_gap_template"] += 1
                continue
            if cnt["requests"] >= config.max_requests:
                prec["status"] = P_CAP
                stop = "work_cap_requests"
                continue
            cnt["requests"] += 1
            if pid == "G0":
                root, detail = vb.g0()
            elif pid == "G1":
                root, detail = vb.g1(config.pair_rules_per_view)
                cnt["pair_grammar_rules_built"] += detail["pair_rules"]
            else:
                root, detail = vb.gap(gaps[gi][0], config.patch_flips)
            prec["detail"] = detail
            if root is None:
                prec["status"] = P_PATCH
                cnt["patch_rejections"] += 1
                continue
            reach = count_reachable(root)
            prec["dag_depth"], prec["rule_count"] = root.depth, reach
            if root.depth > config.max_depth or reach > config.max_rules:
                prec["status"] = P_GRAPH
                cnt["graph_rejections"] += 1
                continue
            arc = serialize_model(to_model(root), n)
            cnt["serialized"] += 1
            prec["archive_bits"] = 8 * len(arc)
            prec["archive_sha256"] = hashlib.sha256(arc).hexdigest()
            if arc in seen:
                prec["status"] = P_DUP
                cnt["duplicates"] += 1
            else:
                seen.add(arc)
                cnt["decoded"] += 1
                if decode_archive(arc) != bits:
                    raise DecodeMismatch(f"view {vi} {pid} does not decode to the input")
                prec["status"] = P_NEW
                src = {"source": "augmentation", "view_index": vi, "level": lv, "width": b,
                       "origin": o, "proposal": pid}
                if inc.offer(arc, src):
                    prec["accepted"] = True
                    cnt["strict_improvements"] += 1
                    if on_improve:
                        on_improve(arc, dict(src, archive_bits=8 * len(arc),
                                             archive_sha256=prec["archive_sha256"]))
            if best is None or prec["archive_bits"] < best:
                best = prec["archive_bits"]
        prev = prev_best.get((b, o))
        rec["description_gap"] = {
            "status": D_NONE if best is None else (D_SHORTER if best < a0_bits else D_NOT_SHORTER),
            "best_bits": best, "minus_a0_bits": None if best is None else best - a0_bits,
            "vs_previous_level_bits": (best - prev[1]) if (best is not None and prev) else None,
            "previous_level": prev[0] if prev else None,
            "vs_previous_unavailable_reason": (None if (best is not None and prev) else
                                               ("level_1" if lv == 1 else
                                                "no_admissible_candidate_here_or_previous"))}
        prev_best[(b, o)] = (lv, best) if best is not None else None
        if L.m == k:
            blocked[(b, o)] = SATURATED
        elif k == 1:
            blocked[(b, o)] = SINGLE
        rec["wall_s"] = time.perf_counter() - t0
        views.append(rec)
        if on_view:
            on_view(rec)
    if decode_archive(inc.archive) != bits:
        raise DecodeMismatch("the selected archive does not decode to the input")
    return AugmentResult(inc.archive, dict(inc.source, trace=inc.trace), views, cnt, stop,
                         config.name, config.sha256())


def strip_timing(obj):
    """Deterministic projection: every key ending in ``wall_s`` or ``_ns`` removed."""
    if isinstance(obj, dict):
        return {k: strip_timing(v) for k, v in obj.items()
                if not (k.endswith("wall_s") or k.endswith("_ns"))}
    if isinstance(obj, list):
        return [strip_timing(v) for v in obj]
    return obj
