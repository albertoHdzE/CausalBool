"""Worker-side computations: thin calls into the frozen owners, nothing re-implemented.

  boundary(bits, name)            D2: ``BoundarySearch(bits, cfg).run()`` with B0 or B8;
                                  receives only the bits and the declared config name.
  supplied_subsets(bits, cuts)    D3 (truth-assisted, a separate job kind): every subset of
                                  the retained supplied cuts priced by
                                  ``BoundarySearch.evaluate`` on ONE B0 instance.
  translate(bits, period, pair)   D4: the saved period and pair-grammar archives rewritten
                                  as HID graphs with ``NodeFactory``, ``consensus.periodic``,
                                  ``to_model`` and ``serialize_model``.

Every produced archive is decoded by the independent decoder; a disagreement raises.
"""
from __future__ import annotations

import hashlib
from dataclasses import replace
from itertools import combinations

from hierarchy import codes as C
from hierarchy.consensus import periodic, tile
from hierarchy.decode import decode_archive
from hierarchy.ledger import archive_ledger, field_buckets
from hierarchy.model import NodeFactory, count_reachable, nodes_postorder, to_model
from hierarchy.segmentation import BoundaryConfig, BoundarySearch, DecodeMismatch
from hierarchy.wire import encode_literal, serialize_model

B0 = BoundaryConfig()
CONFIGS = {"B0": B0,
           "B8": replace(B0, root_trial_cap=4096, cached_leaf_cap=16384,
                         length_charge_multiplier=2048)}
DETERMINISTIC_B = ("archive_bits", "cuts", "segments", "counts", "rounds", "stop_reason",
                   "cap_hit", "unresolved_refinement")
MAX_RULES, MAX_DEPTH = 4096, 64


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


# ---------------------------------------------------------------------------
# D2
# ---------------------------------------------------------------------------

def boundary(bits: str, name: str) -> tuple[dict, dict[str, bytes]]:
    out = BoundarySearch(bits, CONFIGS[name]).run()
    arc = out["archive"]
    info = {k: out[k] for k in DETERMINISTIC_B}
    info["committed_cuts"] = out["committed_cuts"]
    info["config"] = name
    info["config_fields"] = CONFIGS[name].as_dict()
    archives = {}
    if arc is not None:
        if decode_archive(arc) != bits:
            raise DecodeMismatch("boundary output does not decode to the input")
        info["archive_sha256"] = _sha(arc)
        archives["output"] = arc
    return info, archives


# ---------------------------------------------------------------------------
# D3
# ---------------------------------------------------------------------------

def subsets_in_order(cuts) -> list[tuple[int, ...]]:
    """All subsets: increasing cardinality, then ascending cut tuple."""
    cuts = sorted(cuts)
    return [s for k in range(len(cuts) + 1) for s in combinations(cuts, k)]


def supplied_subsets(bits: str, cuts) -> tuple[dict, dict[str, bytes]]:
    if len(set(cuts)) != len(cuts) or any(not 0 < c < len(bits) for c in cuts):
        raise ValueError("supplied cuts must be distinct interior positions")
    srch = BoundarySearch(bits, B0)                 # one cache for the whole string
    recs, archives = [], {}
    for s in subsets_in_order(cuts):
        arc = srch.evaluate(s)
        rec = {"subset": list(s), "status": "graph_limit" if arc is None else "ok"}
        if arc is not None:
            if decode_archive(arc) != bits:          # evaluate() already decoded unseen bytes
                raise DecodeMismatch(f"subset {s} does not decode")
            h = _sha(arc)
            rec.update(archive_bits=8 * len(arc), archive_sha256=h)
            archives[h] = arc
        recs.append(rec)
    leaves = [{"interval": [a, b], "choice": "periodic" if lf[0].op != C.OP_LITERAL
               else "literal", "standalone_bytes": lf[1], "shortest_period": lf[2]}
              for (a, b), lf in sorted(srch.leaves.items())]
    return {"cuts": sorted(cuts), "subsets": recs, "leaves": leaves,
            "charges": dict(srch.counts)}, archives


# ---------------------------------------------------------------------------
# D4
# ---------------------------------------------------------------------------

def _field_values(led: dict, owner: str) -> dict[str, int]:
    return {r["field"]: r["value"] for r in led["fields"] if r["owner"] == owner}


def _admit(root, n: int) -> tuple[dict, bytes | None]:
    rules, depth = count_reachable(root), root.depth
    info = {"rule_count": rules, "dag_depth": depth}
    if rules > MAX_RULES or depth > MAX_DEPTH:
        info["status"] = "unavailable_graph_limit"
        return info, None
    arc = serialize_model(to_model(root), n)
    info["status"] = "ok"
    return info, arc


def translate_period(bits: str, arc: bytes) -> tuple[dict, bytes | None]:
    led = archive_ledger(arc)
    if led["codec_id"] != C.CODEC_PERIOD:
        raise ValueError("not a period archive")
    p = _field_values(led, "period")["period_length"]
    n = len(bits)
    if decode_archive(arc) != bits or tile(bits[:p], n) != bits:
        raise DecodeMismatch("period archive is not the repeated first p bits of the input")
    root = periodic(NodeFactory(), bits, p)
    q, t = divmod(n, p)
    info, out = _admit(root, n)
    info.update(period=p, copies=q, tail_bits=t,
                shape="literal (fewer than two copies)" if q < 2
                else ("repeat + tail literal" if t else "repeat"))
    return info, out


def translate_pair(bits: str, arc: bytes) -> tuple[dict, bytes | None]:
    led = archive_ledger(arc)
    if led["codec_id"] != C.CODEC_PAIR:
        raise ValueError("not a pair-grammar archive")
    v = _field_values(led, "pair")
    q, m = v["q_rules"], v["m_start"]
    f = NodeFactory()
    sym = [f.literal("0"), f.literal("1")]          # terminal ids 0 and 1
    for j in range(q):
        sym.append(f.concat([sym[v[f"rule{j + 2}.left"]], sym[v[f"rule{j + 2}.right"]]]))
    start = [v[f"start[{j}]"] for j in range(m)]
    root = f.concat([sym[s] for s in start])
    info, out = _admit(root, len(bits))
    if out is not None:
        order = {nd.uid: i for i, nd in enumerate(nodes_postorder(root))}
        info["symbol_to_rule"] = [order.get(nd.uid) for nd in sym]
        info["unreachable_symbols"] = sum(1 for nd in sym if nd.uid not in order)
    info.update(q_rules=q, m_start=m)
    return info, out


def translate(bits: str, period_arc: bytes, pair_arc: bytes) -> tuple[dict, dict[str, bytes]]:
    n = len(bits)
    raw_bits = 8 * len(encode_literal(bits))
    out, archives = {}, {}
    for name, fn, src in (("period", translate_period, period_arc),
                          ("pair_grammar", translate_pair, pair_arc)):
        info, arc = fn(bits, src)
        info["baseline_bits"] = 8 * len(src)
        info["baseline_buckets"] = field_buckets(src)
        info["raw_bits"] = raw_bits
        if arc is not None:
            if decode_archive(arc) != bits:
                raise DecodeMismatch(f"translated {name} archive does not decode")
            info.update(translated_bits=8 * len(arc), translated_sha256=_sha(arc),
                        translated_buckets=field_buckets(arc),
                        raw_clipped_bits=min(8 * len(arc), raw_bits))
            archives[name] = arc
        info["n_bits"] = n
        out[name] = info
    return out, archives
