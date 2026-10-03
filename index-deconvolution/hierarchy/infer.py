"""HID-v1 bounded deterministic search: best archive found under a fixed budget.

The search receives a bit string and a frozen SearchConfig, nothing else. It
proposes descriptions from the generators in candidates.py, verifies every one
by evaluation against the input, and selects ONLY by the length of the complete
serialized archive (ties: literal first, then lexicographic archive bytes).
Proposal priorities use local serialized sizes as heuristics; they never pick
the winner. The literal archive is always a candidate, so the result is never
longer than the literal. "Best found under budget", not a minimum.

Enumeration order, site traversal, beam deduplication and counter semantics are
fixed in SEARCH_SPEC.md.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass, field

from . import codes as C
from .candidates import (ap_cover, ap_runs, noisy_periods, pair_grammar,
                         positions_of, schema_pairs, shortest_period)
from .decode import decode_archive
from .model import (Model, Node, NodeFactory, apply_xform, check_bits, count_reachable,
                    nodes_postorder, to_model)
from .wire import encode_literal, model_payload, serialize_model

PRIMITIVE_OPS = (C.OP_LITERAL, C.OP_AP_UNION, C.OP_SCHEMA_UNION)


@dataclass(frozen=True)
class SearchConfig:
    """Every knob of the search. Data-independent; frozen before confirmation."""

    name: str = "full"
    enable_schema: bool = True
    enable_ap: bool = True
    enable_transform: bool = True
    enable_grammar: bool = True
    enable_segmentation: bool = True
    enable_patch: bool = True
    flat: bool = False
    fixed8: bool = False
    restricted: bool = False
    # caps (protocol defaults; any change is recorded in SEARCH_SPEC.md)
    max_candidates: int = 512
    max_rules: int = 4096
    max_ap: int = 256
    max_schema_clauses: int = 64
    max_depth: int = 64
    beam_width: int = 8
    rewrite_rounds: int = 4
    max_sites: int = 16
    site_proposals: int = 1
    schema_max_len: int = 256
    schema_table_budget: int = 4096
    max_relation_reps: int = 64
    max_relation_candidates: int = 8
    patch_max: int = 64
    patch_divisor: int = 16
    ap_single_runs: int = 8
    noisy_keep: int = 3
    dyadic_min: int = 32
    fixed_widths: tuple = (8, 16, 32, 64, 128, 256)
    max_phases: int = 8
    grammar_literal_thresholds: tuple = (0, 16, 64)
    split_min: int = 64
    work_cap: int = 120_000_000
    restricted_max_nodes: int = 3

    def sha256(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode("ascii")
        return hashlib.sha256(blob).hexdigest()


FULL = SearchConfig()
ABLATIONS = {
    "full": FULL,
    "no_schema": SearchConfig(name="no_schema", enable_schema=False),
    "no_arithmetic": SearchConfig(name="no_arithmetic", enable_ap=False),
    "no_transform": SearchConfig(name="no_transform", enable_transform=False),
    "flat": SearchConfig(name="flat", flat=True, enable_transform=False,
                         enable_grammar=False),
    "fixed8": SearchConfig(name="fixed8", fixed8=True),
}
RESTRICTED_ORACLE = SearchConfig(name="restricted_oracle", restricted=True,
                                 enable_schema=False, enable_ap=False,
                                 enable_transform=False, enable_grammar=False,
                                 enable_segmentation=False, enable_patch=False)


@dataclass(frozen=True)
class InferenceResult:
    archive: bytes
    mode: str                       # "literal" or "hid"
    model: Model | None
    archive_bits: int
    literal_bits: int
    candidate_counts: dict
    stop_reason: str
    work: dict
    trace: tuple
    best_source: str
    config_name: str
    config_sha256: str
    rule_count: int | None = None
    dag_depth: int | None = None
    extras: dict = field(default_factory=dict)


class CandidateExpansionMismatch(RuntimeError):
    """A proposal of the right length expands to a different string: an internal
    semantic failure of the search, never a rejected candidate or a fallback."""


class _Stop(Exception):
    def __init__(self, reason: str) -> None:
        self.reason = reason


class _Search:
    def __init__(self, bits: str, cfg: SearchConfig) -> None:
        self.x = bits
        self.n = len(bits)
        self.cfg = cfg
        self.f = NodeFactory()
        self.share = not (cfg.flat or cfg.restricted)
        self.counts = {k: 0 for k in (
            "proposed", "serialized_unique", "duplicate_archive", "rejected_depth",
            "rejected_rules", "rejected_structure", "rejected_verify",
            "skipped_candidate_cap", "schema_calls", "schema_table_entries",
            "schema_budget_skips", "schema_clause_cap", "ap_entry_cap",
            "patch_cap", "local_prop_calls", "rewrite_sites", "relation_found",
            "rounds_completed")}
        self.work = 0
        self.pool: dict[bytes, tuple[str, Node]] = {}
        self.best: tuple[int, bytes] | None = None
        self.trace: list[dict] = []
        self._props: dict[str, list[tuple[str, Node]]] = {}
        self._best_local: dict[tuple[str, bool], Node] = {}
        self._lcost: dict[int, tuple[int, bytes]] = {}
        self.stop_reason = None

    # -- accounting ----------------------------------------------------------

    def charge(self, units: int) -> None:
        self.work += units
        if self.work > self.cfg.work_cap:
            raise _Stop("work_cap")

    def local_cost(self, node: Node) -> tuple[int, bytes]:
        c = self._lcost.get(node.uid)
        if c is None:
            pay = model_payload(to_model(node, self.share))
            c = (len(pay), pay)
            self._lcost[node.uid] = c
        return c

    # -- admissibility -------------------------------------------------------

    def _structure_ok(self, root: Node) -> bool:
        cfg = self.cfg
        allowed = {C.OP_LITERAL, C.OP_CONCAT, C.OP_REPEAT, C.OP_PATCH}
        if cfg.enable_ap:
            allowed.add(C.OP_AP_UNION)
        if cfg.enable_schema:
            allowed.add(C.OP_SCHEMA_UNION)
        if cfg.enable_transform:
            allowed.add(C.OP_XFORM)
        if cfg.restricted:
            allowed = {C.OP_LITERAL, C.OP_CONCAT, C.OP_REPEAT}
        stack, seen = [root], set()
        while stack:
            nd = stack.pop()
            if nd.uid in seen:
                continue
            seen.add(nd.uid)
            if nd.op not in allowed:
                return False
            if cfg.restricted and nd.op == C.OP_CONCAT and len(nd.children) != 2:
                return False
            stack.extend(nd.children)
        if cfg.restricted:
            return count_reachable(root, share=False) <= cfg.restricted_max_nodes
        if cfg.flat:
            r = root.children[0] if root.op == C.OP_PATCH else root
            if r.op in PRIMITIVE_OPS:
                return True
            if r.op == C.OP_REPEAT:
                return r.children[0].op in PRIMITIVE_OPS
            if r.op == C.OP_CONCAT:
                return all(c.op in PRIMITIVE_OPS for c in r.children)
            return False
        return True

    def consider(self, root: Node, source: str) -> None:
        cfg = self.cfg
        self.counts["proposed"] += 1
        if root.length != self.n:
            raise AssertionError(f"proposal {source} has length {root.length} != {self.n}")
        if root.depth > cfg.max_depth:
            self.counts["rejected_depth"] += 1
            return
        if not self._structure_ok(root):
            self.counts["rejected_structure"] += 1
            return
        if count_reachable(root, self.share) > cfg.max_rules:
            self.counts["rejected_rules"] += 1
            return
        if self.counts["serialized_unique"] >= cfg.max_candidates:
            self.counts["skipped_candidate_cap"] += 1
            raise _Stop("candidate_cap")
        archive = serialize_model(to_model(root, self.share), self.n)
        self.charge(len(archive))
        if archive in self.pool:
            self.counts["duplicate_archive"] += 1
            return
        self.counts["serialized_unique"] += 1
        if self.f.expand(root) != self.x:
            self.counts["rejected_verify"] += 1
            raise CandidateExpansionMismatch(
                f"proposal {source!r} has length {self.n} but expands to a different string "
                f"(first difference at bit "
                f"{next(i for i, (a, b) in enumerate(zip(self.f.expand(root), self.x)) if a != b)})")
        self.pool[archive] = (source, root)
        key = (len(archive), archive)
        if self.best is None or key < self.best:
            if self.best is None or len(archive) < self.best[0]:
                self.trace.append({"step": self.counts["serialized_unique"],
                                   "source": source, "archive_bits": 8 * len(archive)})
            self.best = key

    # -- local proposals -----------------------------------------------------

    def periodic(self, w: str, length: int) -> Node:
        f = self.f
        k, r = divmod(length, len(w))
        lit = f.literal(w)
        if self.cfg.flat or self.cfg.restricted:
            if r == 0:
                return f.repeat(lit, k)
            return f.concat([lit] * k + [f.literal(w[:r])])
        body = f.repeat(lit, k)
        return f.concat([body, f.literal(w[:r])]) if r else body

    def local_props(self, s: str, allow_split: bool = True) -> list[tuple[str, Node]]:
        key = s if allow_split else "\x00" + s
        got = self._props.get(key)
        if got is not None:
            return got
        cfg, f = self.cfg, self.f
        self.counts["local_prop_calls"] += 1
        L = len(s)
        self.charge(L)
        out: list[tuple[str, Node]] = [("literal", f.literal(s))]
        p = shortest_period(s)
        self.charge(2 * L)
        if L // p >= 2:
            out.append((f"period[{p}]", self.periodic(s[:p], L)))
        if cfg.enable_ap:
            for fg in "01":
                pos = positions_of(s, fg)
                runs = ap_runs(pos)
                if len(runs) <= cfg.max_ap:
                    out.append((f"ap_runs[fg={fg}]", f.ap_union(L, int(fg), runs)))
                else:
                    self.counts["ap_entry_cap"] += 1
                if len(pos) >= 6:
                    self.charge(8 * L)
                    cov = ap_cover(pos, L)
                    if len(cov) <= cfg.max_ap and cov != runs:
                        out.append((f"ap_cover[fg={fg}]", f.ap_union(L, int(fg), cov)))
                if cfg.enable_patch:
                    cap = min(cfg.patch_max, L // cfg.patch_divisor)
                    longest = sorted(runs, key=lambda t: (-t[2], t[0], t[1]))[:cfg.ap_single_runs]
                    for run in longest:
                        if run[2] < 2:
                            continue
                        start, step, count = run
                        member = set(range(start, start + count * step, step))
                        errs = [q for q in pos if q not in member]
                        if 0 < len(errs) <= cap:
                            out.append((f"ap_run_patch[fg={fg}]",
                                        f.patch(f.ap_union(L, int(fg), [run]), errs)))
                        elif errs:
                            self.counts["patch_cap"] += 1
        if cfg.enable_schema and L <= cfg.schema_max_len:
            d = (L - 1).bit_length()
            for fg in "01":
                for pad in (0, 1):
                    if self.counts["schema_table_entries"] + (1 << d) > cfg.schema_table_budget:
                        self.counts["schema_budget_skips"] += 1
                        continue
                    self.counts["schema_calls"] += 1
                    self.counts["schema_table_entries"] += 1 << d
                    self.charge(64 * (1 << d))
                    pairs = schema_pairs(s, fg, pad)
                    if pairs is None:
                        continue
                    if len(pairs) > cfg.max_schema_clauses:
                        self.counts["schema_clause_cap"] += 1
                        continue
                    out.append((f"schema[fg={fg},pad={pad}]",
                                f.schema_union(L, int(fg), pairs)))
        if cfg.enable_patch:
            cap = min(cfg.patch_max, L // cfg.patch_divisor)
            self.charge(36 * L)
            for err, per, errs in noisy_periods(s, cfg.noisy_keep):
                if 0 < err <= cap:
                    out.append((f"noisy_period[{per},err={err}]",
                                f.patch(self.periodic(s[:per], L), errs)))
                elif err:
                    self.counts["patch_cap"] += 1
        if (allow_split and not cfg.flat and not cfg.fixed8 and not cfg.restricted
                and L >= cfg.split_min):
            h = 1 << ((L - 1).bit_length() - 1)
            out.append((f"split[{h}]", f.concat([self.best_local(s[:h]),
                                                  self.best_local(s[h:])])))
        if cfg.restricted:
            for h in range(1, L):
                out.append((f"split[{h}]", f.concat([f.literal(s[:h]), f.literal(s[h:])])))
        # de-duplicate by node identity, first label wins
        seen: dict[int, None] = {}
        uniq = []
        for lab, nd in out:
            if nd.uid not in seen:
                seen[nd.uid] = None
                uniq.append((lab, nd))
        self._props[key] = uniq
        return uniq

    def best_local(self, s: str, primitives_only: bool = False) -> Node:
        key = (s, primitives_only)
        got = self._best_local.get(key)
        if got is None:
            props = self.local_props(s, allow_split=False)
            if primitives_only:
                props = [p for p in props if p[1].op in PRIMITIVE_OPS]
            got = min(props, key=lambda p: (self.local_cost(p[1]), p[0]))[1]
            self._best_local[key] = got
        return got

    # -- whole-input proposal families --------------------------------------

    def root_from_children(self, kids: list[Node]) -> Node:
        f = self.f
        if self.cfg.flat or self.cfg.restricted:
            return f.concat(kids)
        merged: list[Node] = []
        i = 0
        while i < len(kids):
            j = i
            while j < len(kids) and kids[j] is kids[i]:
                j += 1
            merged.append(f.repeat(kids[i], j - i))
            i = j
        return f.concat(merged)

    def grammar_root(self, terminals: list[Node], rules, start, threshold: int) -> Node:
        f = self.f
        nodes: list[Node] = list(terminals)
        for a, b in rules:
            nodes.append(f.concat([nodes[a], nodes[b]]))
        if threshold:
            for i in range(len(terminals), len(nodes)):
                if nodes[i].length <= threshold:
                    nodes[i] = f.literal(f.expand(nodes[i]))
            # rebuild productions so that literalised children propagate
            rebuilt = list(terminals)
            for i, (a, b) in enumerate(rules):
                rid = len(terminals) + i
                if nodes[rid].op == C.OP_LITERAL:
                    rebuilt.append(nodes[rid])
                else:
                    rebuilt.append(f.concat([rebuilt[a], rebuilt[b]]))
            nodes = rebuilt
        return self.root_from_children([nodes[s] for s in start])

    def grammar_props(self) -> None:
        cfg, f, x = self.cfg, self.f, self.x
        if not cfg.enable_grammar or cfg.flat or cfg.restricted:
            return
        self.charge(16 * self.n)
        if cfg.fixed8:
            full = self.n // 8
            vocab: dict[str, int] = {}
            seq = []
            for i in range(full):
                seq.append(vocab.setdefault(x[8 * i:8 * i + 8], len(vocab)))
            if self.n % 8:
                seq.append(vocab.setdefault(x[8 * full:], len(vocab)))
            terminals = [f.literal(w) for w in vocab]
            rules, start = pair_grammar(seq, len(terminals), C.PAIR_MAX_RULES)
            label = "grammar_fixed8"
        else:
            terminals = [f.literal("0"), f.literal("1")]
            rules, start = pair_grammar([int(c) for c in x], 2, C.PAIR_MAX_RULES)
            label = "grammar"
        for t in cfg.grammar_literal_thresholds:
            self.consider(self.grammar_root(terminals, rules, start, t), f"{label}[lit<={t}]")

    def segmentations(self) -> list[tuple[str, list[str]]]:
        cfg, x, n = self.cfg, self.x, self.n
        out = []
        w = cfg.dyadic_min
        while w < n:
            out.append((f"dyadic[{w}]", [x[i:i + w] for i in range(0, n, w)]))
            w *= 2
        for w in cfg.fixed_widths:
            if w >= n:
                continue
            phases = 1 if cfg.fixed8 else min(cfg.max_phases, w)
            for ph in range(phases):
                chunks = [x[:ph]] if ph else []
                chunks += [x[i:i + w] for i in range(ph, n, w)]
                out.append((f"fixed[{w},phase={ph}]", chunks))
        return out

    def segmentation_props(self) -> None:
        cfg = self.cfg
        if not cfg.enable_segmentation:
            return
        for label, chunks in self.segmentations():
            self.charge(self.n)
            kids = [self.best_local(c, primitives_only=cfg.flat) for c in chunks]
            self.consider(self.root_from_children(kids), f"seg:{label}:local")
            if cfg.flat:
                continue
            # chunk-level grammar: identical chunk descriptions become symbols
            ids: dict[int, int] = {}
            terms: list[Node] = []
            seq = []
            for k in kids:
                if k.uid not in ids:
                    ids[k.uid] = len(terms)
                    terms.append(k)
                seq.append(ids[k.uid])
            rules, start = pair_grammar(seq, len(terms), C.PAIR_MAX_RULES)
            if rules:
                self.consider(self.grammar_root(terms, rules, start, 0),
                              f"seg:{label}:chunk_grammar")

    # -- rewrites ------------------------------------------------------------

    def sites(self, root: Node) -> list[Node]:
        order = nodes_postorder(root, True)
        rid = {nd.uid: i for i, nd in enumerate(order)}
        cand = [nd for nd in order if nd is not root]
        cand.sort(key=lambda nd: (-nd.length, rid[nd.uid]))
        return cand[:self.cfg.max_sites]

    def references(self, root: Node) -> dict[int, int]:
        refs: dict[int, int] = {}
        for nd in nodes_postorder(root, True):
            for c in nd.children:
                refs[c.uid] = refs.get(c.uid, 0) + 1
        return refs

    def rewrite(self, root: Node, source: str) -> None:
        cfg, f = self.cfg, self.f
        refs = self.references(root)
        for site in self.sites(root):
            self.counts["rewrite_sites"] += 1
            s = f.expand(site)
            props = [p for p in self.local_props(s) if p[1] is not site]
            if cfg.flat:
                props = [p for p in props if p[1].op in PRIMITIVE_OPS]
            props.sort(key=lambda p: (self.local_cost(p[1]), p[0]))
            for lab, nd in props[:cfg.site_proposals]:
                new_root = f.rebuild(root, {site.uid: nd})
                self.consider(new_root, f"{source}>site(len={site.length},"
                                        f"refs={refs.get(site.uid, 0)}):{lab}")
        if cfg.enable_transform and not cfg.flat and not cfg.restricted:
            self.relations(root, source, refs)

    def relations(self, root: Node, source: str, refs: dict[int, int]) -> None:
        f, cfg = self.f, self.cfg
        reps = [nd for nd in nodes_postorder(root, True) if nd.op == C.OP_LITERAL]
        if root.op == C.OP_CONCAT:
            reps += [c for c in root.children if c.op != C.OP_LITERAL]
        uniq: dict[int, Node] = {}
        for nd in reps:
            uniq.setdefault(nd.uid, nd)
        reps = sorted(uniq.values(), key=lambda nd: (-refs.get(nd.uid, 0), f.expand(nd)))
        reps = reps[:cfg.max_relation_reps]
        by_exp: dict[str, Node] = {}
        for nd in reps:
            by_exp.setdefault(f.expand(nd), nd)
        found: list[tuple[Node, Node, int, int]] = []
        targets: dict[int, None] = {}
        for src in reps:
            s = f.expand(src)
            L = len(s)
            self.charge(20 * L)
            for flags in (0, 1, 2, 3):
                for r0 in (0, 1, 2, 4, 8):
                    r = r0 % L
                    if (r0 and not r) or (flags == 0 and r == 0):
                        continue           # duplicate of r=0, or the identity
                    t = apply_xform(s, flags, r)
                    tgt = by_exp.get(t)
                    if tgt is None or tgt is src or tgt.uid in targets:
                        continue
                    found.append((tgt, src, flags, r))
                    targets[tgt.uid] = None
        self.counts["relation_found"] += len(found)
        mapping: dict[int, Node] = {}
        used_src: dict[int, None] = {}
        for tgt, src, flags, r in found[:cfg.max_relation_candidates]:
            node = f.xform(src, flags, r)
            self.consider(f.rebuild(root, {tgt.uid: node}),
                          f"{source}>xform(flags={flags},r={r})")
        for tgt, src, flags, r in found:
            if src.uid in mapping or tgt.uid in used_src:
                continue
            mapping[tgt.uid] = f.xform(src, flags, r)
            used_src[src.uid] = None
        if len(mapping) > 1:
            self.consider(f.rebuild(root, mapping), f"{source}>xform(joint={len(mapping)})")

    # -- driver ----------------------------------------------------------------

    def beam(self) -> list[tuple[bytes, str, Node]]:
        ranked = sorted(self.pool, key=lambda a: (len(a), a))[:self.cfg.beam_width]
        return [(a,) + self.pool[a] for a in ranked]

    def run(self) -> None:
        try:
            for lab, nd in self.local_props(self.x):
                self.consider(nd, f"global:{lab}")
            self.grammar_props()
            self.segmentation_props()
            expanded: dict[bytes, None] = {}
            for _ in range(self.cfg.rewrite_rounds):
                before = [a for a, _, _ in self.beam()]
                for archive, source, root in self.beam():
                    if archive in expanded:
                        continue
                    expanded[archive] = None
                    self.rewrite(root, source.split(">")[0])
                self.counts["rounds_completed"] += 1
                if [a for a, _, _ in self.beam()] == before:
                    self.stop_reason = "converged"
                    return
            self.stop_reason = "rounds_exhausted"
        except _Stop as stop:
            self.stop_reason = stop.reason


def infer(bits: str, config: SearchConfig = FULL) -> InferenceResult:
    """Best archive found for ``bits`` under ``config`` (literal fallback included)."""
    check_bits(bits)
    if not isinstance(config, SearchConfig):
        raise TypeError("config must be a SearchConfig")
    literal = encode_literal(bits)
    n = len(bits)
    if n == 0:
        bits_ = 8 * len(literal)
        return InferenceResult(literal, "literal", None, bits_, bits_, {}, "empty_input", {},
                               (), "literal", config.name, config.sha256())
    srch = _Search(bits, config)
    srch.run()
    mode, archive, model, source = "literal", literal, None, "literal"
    if srch.best is not None and srch.best[0] < len(literal):
        archive = srch.best[1]
        source, root = srch.pool[archive]
        model = to_model(root, srch.share)
        mode = "hid"
        if serialize_model(model, n) != archive:
            raise AssertionError("winning model does not reserialize to its archive")
    if decode_archive(archive) != bits:
        raise AssertionError("independent decoder disagrees with the input")
    counts = dict(srch.counts)
    work = {"work_units": srch.work, "work_cap": config.work_cap,
            "nodes_interned": len(srch.f)}
    return InferenceResult(
        archive=archive, mode=mode, model=model, archive_bits=8 * len(archive),
        literal_bits=8 * len(literal), candidate_counts=counts,
        stop_reason=srch.stop_reason or "converged", work=work,
        trace=tuple(srch.trace), best_source=source, config_name=config.name,
        config_sha256=config.sha256(),
        rule_count=len(model.rules) if model else None,
        dag_depth=model.depth() if model else None)
