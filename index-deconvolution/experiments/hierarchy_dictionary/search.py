"""HID dictionary relations v1: the single owner of the dictionary-mode augmentation.

``augment(bits, config, baseline_archive)`` receives the input bits, an immutable
``DictionaryConfig`` and the completed, verified A0 (search-v2 k=1) archive, nothing
else. It enumerates the multilevel-v1 views by (level, width, origin) WITHOUT branch
pruning, and for every eligible view offers, per dictionary mode of the arm (in the
order O, P, R(O), R(P)), the unchanged multilevel-v1 proposals G0, G1, G2, G3. The
incumbent is kept unless a complete, independently decoded candidate archive is
strictly shorter; earlier incumbents win ties, so A0 is retained on equality.

Reused, not copied (PROTOCOL section 2): views, canonical ids and exact
prefix/core/suffix coverage come from ``hierarchy_multilevel.search.path_levels`` and
``ViewBuilder``; proposals are its ``g0``/``g1``/``gap`` methods; diagnostics are its
``view_diagnostics``; the incumbent is its ``_Inc``. A dictionary mode only replaces
the top-level dictionary node list ``ViewBuilder.sym`` (one ``NodeFactory`` per view,
shared by all modes); top ids, streams, gaps, prefix and suffix are unchanged.

Dictionary modes (SEARCH section 2), over the exact top words w[i] (first appearance):

  O     the ViewBuilder nodes (level 1 LITERAL; higher levels CONCAT of lower entries);
  P     REPEAT(LITERAL(w[:p]), |w|/p) when the owner ``shortest_period`` p < |w| divides
        |w|, otherwise O[i]; every eligible replacement at once;
  R(B)  for base B in {O, P}, ids ascending: among predecessors j = max(0, i-8)..i-1 and
        flags 0..3 (owner ``apply_xform``: complement then reversal, rotation 0), the
        first of (flips, j, flags) with flips <= 8 and 1 + hops[j] <= 8; node =
        PATCH(XFORM(resolved node j of this mode, flags), flips) with identity XFORM and
        empty PATCH omitted; otherwise B[i] with zero hops.

Every mode node is expanded by the encoder evaluator and must equal its original word
(``DecodeMismatch`` otherwise). All dictionary, relation, exception, prefix, tail and
header costs are paid by the owner wire serialization of the full-input root; nothing is
priced standalone. Diagnostics never feed back into what is proposed or selected.
"""
from __future__ import annotations

import hashlib
import json
import time
from dataclasses import asdict, dataclass

from hierarchy.candidates import shortest_period
from hierarchy.decode import decode_archive
from hierarchy.model import apply_xform, check_bits, count_reachable, nodes_postorder, to_model
from hierarchy.segmentation import DecodeMismatch
from hierarchy.wire import serialize_model
from hierarchy_multilevel.search import (D_NONE, D_NOT_SHORTER, D_SHORTER, EVALUATED,
                                         INELIGIBLE_SHORT, P_CAP, P_DUP, P_GRAPH, P_NEW,
                                         P_NOGAP, P_PATCH, PROPOSALS, REQUEST_CAP_VIEW,
                                         SATURATED, SINGLE, VIEW_CAP, WIDTHS,
                                         BaselineUnusable, ViewBuilder, _Inc, path_levels,
                                         ranked_gaps, strip_timing, view_diagnostics)

__all__ = ["ARMS", "MODES", "DictionaryConfig", "augment", "strip_timing", "BaselineUnusable"]

MODES = ("O", "P", "R(O)", "R(P)")
M_NOT_BUILT = "NOT_BUILT_REQUEST_CAP"


@dataclass(frozen=True)
class DictionaryConfig:
    """Every knob of one augmentation arm (contract.json ``arms`` and ``limits``)."""

    name: str
    modes: tuple
    widths: tuple = WIDTHS
    max_level: int = 4
    max_views: int = 64
    max_requests: int = 1024
    pair_rules_per_view: int = 64
    max_rules: int = 4096
    max_depth: int = 64
    patch_flips: int = 64
    gap_templates: int = 2
    predecessors: int = 8
    relation_flips: int = 8
    relation_hops: int = 8
    relation_flags: tuple = (0, 1, 2, 3)
    old_branch_mask: bool = False            # fixtures only: multilevel-v1 descendant blocking

    def __post_init__(self):
        if tuple(sorted(set(self.widths))) != tuple(self.widths) or not self.widths:
            raise ValueError("widths must be a nonempty strictly ascending tuple")
        if min(self.widths) < 1 or self.max_level < 1:
            raise ValueError("widths and max_level must be positive")
        if not self.modes or any(m not in MODES for m in self.modes) or \
                list(self.modes) != sorted(self.modes, key=MODES.index) or len(set(self.modes)) != len(self.modes):
            raise ValueError(f"modes must be a nonempty ordered subset of {MODES}")

    def as_dict(self) -> dict:
        d = asdict(self)
        d["widths"], d["modes"], d["relation_flags"] = list(self.widths), list(self.modes), list(self.relation_flags)
        return d

    def sha256(self) -> str:
        return hashlib.sha256(json.dumps(self.as_dict(), sort_keys=True).encode()).hexdigest()

    def views(self) -> list[tuple[int, int, int]]:
        """(level, width, origin) in the fixed enumeration order."""
        return [(lv, b, o) for lv in range(1, self.max_level + 1) for b in self.widths
                for o in (0, b // 2)]


ARMS = {
    "D0": DictionaryConfig("dict_O", ("O",)),
    "D1": DictionaryConfig("dict_OP", ("O", "P")),
    "D2": DictionaryConfig("dict_OPR", MODES),
}


# ---------------------------------------------------------------------------
# Dictionary modes (nodes built in the view's own NodeFactory)
# ---------------------------------------------------------------------------

def periodic_mode(f, words: list[str], base: list) -> tuple[list, dict]:
    nodes, replaced, periods = [], [], []
    for i, w in enumerate(words):
        p = shortest_period(w)
        periods.append(p)
        if p < len(w) and len(w) % p == 0:
            nodes.append(f.repeat(f.literal(w[:p]), len(w) // p))
            replaced.append(i)
        else:
            nodes.append(base[i])
    return nodes, {"periods": periods, "replaced_ids": replaced, "replaced": len(replaced),
                   "non_dividing_proper_period_ids": [i for i, w in enumerate(words)
                                                      if periods[i] < len(w) and len(w) % periods[i]]}


def relation_mode(f, words: list[str], base: list, cfg: DictionaryConfig) -> tuple[list, dict]:
    """R(base): the first eligible (flips, j, flags) relation per id, ids ascending."""
    ints = [int(w, 2) for w in words]
    tints = [[int(apply_xform(w, fl, 0), 2) if fl else ints[j] for fl in cfg.relation_flags]
             for j, w in enumerate(words)]
    nodes, hops, selected, comparisons, first_j = [], [], [], [], []
    hop_rejected = 0
    for i, w in enumerate(words):
        lo = max(0, i - cfg.predecessors)
        first_j.append(lo)
        counts, best = [], None
        for j in range(lo, i):
            for fi, fl in enumerate(cfg.relation_flags):
                c = (tints[j][fi] ^ ints[i]).bit_count()
                counts.append(c)
                if c <= cfg.relation_flips:
                    if 1 + hops[j] > cfg.relation_hops:
                        hop_rejected += 1
                    elif best is None or (c, j, fl) < best:
                        best = (c, j, fl)
        comparisons.append(counts)
        if best is None:
            nodes.append(base[i])
            hops.append(0)
            continue
        c, j, fl = best
        t = apply_xform(words[j], fl, 0)
        flips = [q for q, (a, b) in enumerate(zip(t, w)) if a != b]
        node = nodes[j]
        if fl:
            node = f.xform(node, fl, 0)
        node = f.patch(node, flips)
        nodes.append(node)
        hops.append(1 + hops[j])
        selected.append({"id": i, "j": j, "flags": fl, "flip_positions": flips, "hops": hops[-1]})
    return nodes, {"relations": selected, "relations_selected": len(selected), "hops": hops,
                   "max_hops": max(hops, default=0), "comparisons_first_j": first_j,
                   "comparison_flip_counts": comparisons,
                   "comparisons": sum(len(c) for c in comparisons),
                   "eligible_by_flips_rejected_by_hop_cap": hop_rejected}


def dictionary_graph(nodes: list) -> dict:
    seen: dict[int, object] = {}
    for nd in nodes:
        for x in nodes_postorder(nd, True):
            seen.setdefault(x.uid, x)
    return {"dictionary_reachable_rules": len(seen),
            "dictionary_max_depth": max((nd.depth for nd in nodes), default=0)}


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
    candidates: dict          # sha256 -> bytes: shortest serialized archive per view and mode


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def augment(bits: str, config: DictionaryConfig, baseline_archive: bytes,
            on_improve=None, on_view=None) -> AugmentResult:
    """Best complete archive among A0 and this arm's proposals (strictly shorter wins).

    ``on_improve(archive, record)`` is called at every strict improvement (checkpoint);
    ``on_view(record)`` after every view record is final. Neither may alter the search.
    """
    check_bits(bits)
    if not isinstance(config, DictionaryConfig) or type(baseline_archive) is not bytes:
        raise TypeError("config must be a DictionaryConfig and the baseline bytes")
    if decode_archive(baseline_archive) != bits:
        raise BaselineUnusable("the A0 archive does not decode to the input")
    n = len(bits)
    inc = _Inc(baseline_archive)
    a0_bits = 8 * len(baseline_archive)
    cnt = {"views_listed": 0, "views_evaluated": 0, "requests": 0, "serialized": 0,
           "decoded": 0, "duplicates": 0, "graph_rejections": 0, "patch_rejections": 0,
           "no_gap_template": 0, "strict_improvements": 0, "pair_grammar_rules_built": 0,
           "modes_built": 0, "period_replacements": 0, "relation_comparisons": 0,
           "relations_selected": 0, "relation_hop_rejections": 0, "expansion_checks": 0,
           "views_k_eq_m": 0, "views_k_eq_1": 0, "views_old_mask_blocked": 0}
    views: list[dict] = []
    candidates: dict[str, bytes] = {}
    if n == 0:
        return AugmentResult(baseline_archive, dict(inc.source, trace=inc.trace), views,
                             dict(cnt, diagnostics_unavailable="empty_input"),
                             "empty_input", config.name, config.sha256(), candidates)
    seen = {baseline_archive}
    paths = {(b, o): path_levels(bits, b, o, config.max_level)
             for b in config.widths for o in (0, b // 2)}
    old_mask: dict[tuple[int, int], str] = {}        # what multilevel-v1 would have blocked
    stop = "completed"
    for vi, (lv, b, o) in enumerate(config.views()):
        cnt["views_listed"] += 1
        L = paths[(b, o)][lv - 1]
        k = len(L.entries)
        rec = {"view_index": vi, "level": lv, "width": b, "origin": o, "span": L.span,
               "m": L.m, "k": k if L.m else 0, "k_over_m": (k / L.m) if L.m else None,
               "prefix_bits": o if L.m else None,
               "suffix_bits": (n - o - L.m * L.span) if L.m else None,
               "status": None, "proposals": [], "description_gap": None, "wall_s": None,
               "branch_flags": {"old_mask_status": old_mask.get((b, o)),
                                "k_eq_m": None, "k_eq_1": None}}
        if (b, o) in old_mask:
            cnt["views_old_mask_blocked"] += 1
            if config.old_branch_mask:
                rec["status"] = old_mask[(b, o)]
        if rec["status"] is not None:
            pass
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
        rec["branch_flags"].update(k_eq_m=L.m == k, k_eq_1=k == 1)
        cnt["views_k_eq_m"] += L.m == k
        cnt["views_k_eq_1"] += k == 1
        levels = paths[(b, o)][:lv]
        rec.update(view_diagnostics(bits, levels, b, o))
        vb = ViewBuilder(bits, levels, o)
        rec["true_input_span"] = [vb.core_start, vb.core_end]
        words = list(L.expansions)
        rec["dictionary_expansions_sha256"] = _sha("\n".join(words).encode())
        gaps = ranked_gaps(L.stream, L.m)
        rec["ranked_gaps"] = [[g, c] for g, c in gaps[:config.gap_templates]]
        built = {"O": vb.sym}
        best_view = None
        rec["modes"] = []
        for mode in config.modes:
            mrec = {"mode": mode, "built": False, "construction": None, "proposal_range": None,
                    "best_bits": None, "best_sha256": None, "best_proposal": None,
                    "minus_a0_bits": None, "minus_O_bits": None, "wall_s": None}
            rec["modes"].append(mrec)
            if cnt["requests"] >= config.max_requests:
                mrec["status"] = M_NOT_BUILT
                mrec["proposal_range"] = [len(rec["proposals"]), len(rec["proposals"]) + len(PROPOSALS)]
                for pid in PROPOSALS:
                    rec["proposals"].append({"proposal": pid, "mode": mode, "status": P_CAP,
                                              "archive_bits": None, "archive_sha256": None})
                stop = "work_cap_requests"
                continue
            tm = time.perf_counter()
            if mode == "P":
                nodes, meta = periodic_mode(vb.f, words, built["O"])
                cnt["period_replacements"] += meta["replaced"]
            elif mode.startswith("R("):
                nodes, meta = relation_mode(vb.f, words, built.get(mode[2]) or
                                            periodic_mode(vb.f, words, built["O"])[0], config)
                cnt["relation_comparisons"] += meta["comparisons"]
                cnt["relations_selected"] += meta["relations_selected"]
                cnt["relation_hop_rejections"] += meta["eligible_by_flips_rejected_by_hop_cap"]
            else:
                nodes, meta = built["O"], {}
            built[mode] = nodes
            cnt["modes_built"] += 1
            for i, nd in enumerate(nodes):
                cnt["expansion_checks"] += 1
                if vb.f.expand(nd) != words[i]:
                    raise DecodeMismatch(f"view {vi} mode {mode} entry {i} does not expand to its word")
            mrec["built"] = True
            mrec["status"] = "BUILT"
            mrec["construction"] = dict(meta, **dictionary_graph(nodes), expansions_match_original=True)
            if mode == "R(P)" and "R(O)" in built:
                prev = next(m for m in rec["modes"] if m["mode"] == "R(O)")["construction"]
                if prev["comparison_flip_counts"] == meta["comparison_flip_counts"]:
                    mrec["construction"]["comparison_flip_counts"] = "same_as_R(O)"
            vb.sym = nodes
            first = len(rec["proposals"])
            try:
                best_mode = None
                for pid in PROPOSALS:
                    prec = {"proposal": pid, "mode": mode, "status": None, "archive_bits": None,
                            "archive_sha256": None, "rule_count": None, "dag_depth": None,
                            "accepted": False, "request_ordinal": None, "detail": {}}
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
                    prec["request_ordinal"] = cnt["requests"]
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
                    prec["archive_sha256"] = _sha(arc)
                    if arc in seen:
                        prec["status"] = P_DUP
                        cnt["duplicates"] += 1
                    else:
                        seen.add(arc)
                        cnt["decoded"] += 1
                        if decode_archive(arc) != bits:
                            raise DecodeMismatch(f"view {vi} {mode} {pid} does not decode to the input")
                        prec["status"] = P_NEW
                        src = {"source": "augmentation", "view_index": vi, "level": lv, "width": b,
                               "origin": o, "mode": mode, "proposal": pid}
                        if inc.offer(arc, src):
                            prec["accepted"] = True
                            cnt["strict_improvements"] += 1
                            candidates[prec["archive_sha256"]] = arc
                            if on_improve:
                                on_improve(arc, dict(src, archive_bits=8 * len(arc),
                                                     archive_sha256=prec["archive_sha256"]))
                    if best_mode is None or len(arc) < len(best_mode[0]):
                        best_mode = (arc, pid)
            finally:
                vb.sym = built["O"]
                mrec["proposal_range"] = [first, len(rec["proposals"])]
            if best_mode is not None:
                arc, pid = best_mode
                h = _sha(arc)
                candidates[h] = arc
                mrec.update(best_bits=8 * len(arc), best_sha256=h, best_proposal=pid,
                            minus_a0_bits=8 * len(arc) - a0_bits)
                if best_view is None or len(arc) < best_view:
                    best_view = len(arc)
            mrec["wall_s"] = time.perf_counter() - tm
        o_best = next((m["best_bits"] for m in rec["modes"] if m["mode"] == "O"), None)
        for m in rec["modes"]:
            m["minus_O_bits"] = (None if m["best_bits"] is None or o_best is None
                                 else m["best_bits"] - o_best)
        best = None if best_view is None else 8 * best_view
        rec["description_gap"] = {
            "status": D_NONE if best is None else (D_SHORTER if best < a0_bits else D_NOT_SHORTER),
            "best_bits": best, "minus_a0_bits": None if best is None else best - a0_bits}
        if (b, o) not in old_mask:
            if L.m == k:
                old_mask[(b, o)] = SATURATED
            elif k == 1:
                old_mask[(b, o)] = SINGLE
        rec["wall_s"] = time.perf_counter() - t0
        views.append(rec)
        if on_view:
            on_view(rec)
    if decode_archive(inc.archive) != bits:
        raise DecodeMismatch("the selected archive does not decode to the input")
    candidates[_sha(inc.archive)] = inc.archive
    return AugmentResult(inc.archive, dict(inc.source, trace=inc.trace), views, cnt, stop,
                         config.name, config.sha256(), candidates)
