"""Engineering fixtures for ``search`` (BENCHMARK section 2). Expectations are the ones
declared in ``fixtures.EXPECTATIONS`` before any execution, derived by hand from the wire
annex and SEARCH.md, not taken from the implementation."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest
from hierarchy import codes as C
from hierarchy.decode import decode_archive
from hierarchy.model import NodeFactory, apply_xform, to_model
from hierarchy.wire import encode_literal, serialize_model
from hierarchy_multilevel import search as ML

from hierarchy_dictionary import search as S
from hierarchy_dictionary.search import ARMS, MODES, DictionaryConfig, augment, strip_timing
from hierarchy_dictionary.tests import fixtures as F

PKG = Path(S.__file__).resolve().parent


def run(name, arm="D2", cfg=None, a0=None):
    x = F.bits(name)
    return x, augment(x, cfg or ARMS[arm], a0 if a0 is not None else encode_literal(x))


def view(res, level, width, origin):
    return next(v for v in res.views if (v["level"], v["width"], v["origin"]) == (level, width, origin))


def mode(v, name):
    return next(m for m in v["modes"] if m["mode"] == name)


def props(v, name):
    m = mode(v, name)
    return v["proposals"][m["proposal_range"][0]:m["proposal_range"][1]]


def rel(v, name="R(O)"):
    return {r["id"]: r for r in mode(v, name)["construction"]["relations"]}


# ---------------------------------------------------------------------------
# declaration, empty/short, tails, branch flags
# ---------------------------------------------------------------------------

def test_declared_fixture_bounds():
    vals = [v for _, v in F.INPUTS.values()]
    assert len(set(vals)) == len(vals) <= 24
    assert max(map(len, vals)) <= 4099


def test_arms_match_contract():
    assert ARMS["D0"].modes == ("O",) and ARMS["D1"].modes == ("O", "P") and ARMS["D2"].modes == MODES
    for c in ARMS.values():
        assert (c.max_views, c.max_requests, c.max_rules, c.max_depth, c.pair_rules_per_view,
                c.patch_flips, c.predecessors, c.relation_flips, c.relation_hops) == \
            (64, 1024, 4096, 64, 64, 64, 8, 8, 8)
        assert c.widths == (4, 8, 12, 16, 24, 32, 48, 64) and c.max_level == 4 and not c.old_branch_mask
        assert len(c.views()) == 64


def test_empty_input_requests_nothing_and_diagnostics_unavailable():
    a0 = encode_literal("")
    res = augment("", ARMS["D2"], a0)
    assert res.archive == a0 and res.views == [] and res.counters["requests"] == 0
    assert res.counters["diagnostics_unavailable"] == "empty_input" and res.stop_reason == "empty_input"


def test_short_input_all_views_skipped_explicitly():
    x, res = run("short4")
    assert len(res.views) == 64 and {v["status"] for v in res.views} == {ML.INELIGIBLE_SHORT}
    assert res.counters["requests"] == 0 and res.archive == encode_literal(x)


def test_odd_tails_at_multiple_levels_and_both_origins():
    x, res = run("odd_tail_59")
    v1, v2, v2o = view(res, 1, 8, 0), view(res, 2, 8, 0), view(res, 2, 8, 4)
    assert v1["k"] == 1 and v1["status"] == ML.EVALUATED
    assert v2["status"] == ML.EVALUATED and v2["m"] == 3 and v2["suffix_bits"] == 59 - 48 == 11
    assert v2["branch_flags"]["old_mask_status"] == ML.SINGLE        # recorded, not a stop rule
    assert v2o["m"] == 3 and v2o["prefix_bits"] == 4 and v2o["suffix_bits"] == 59 - 4 - 48
    assert view(res, 3, 8, 0)["m"] == 1 and view(res, 3, 8, 0)["status"] == ML.INELIGIBLE_SHORT
    for v in res.views:
        if v["status"] == ML.EVALUATED:
            assert v["prefix_bits"] + v["m"] * v["span"] + v["suffix_bits"] == len(x)
            assert v["true_input_span"] == [v["origin"], v["origin"] + v["m"] * v["span"]]


def test_k1_and_km_descendants_still_evaluated():
    _, res = run("single_symbol_256", "D0")
    v1 = view(res, 1, 4, 0)
    assert v1["k"] == 1 and v1["branch_flags"]["k_eq_1"]
    for lv in (2, 3, 4):
        v = view(res, lv, 4, 0)
        assert v["status"] == ML.EVALUATED and v["branch_flags"]["old_mask_status"] == ML.SINGLE
    _, res = run("counter_1024", "D0")
    assert view(res, 1, 8, 0)["branch_flags"]["k_eq_m"]
    v2 = view(res, 2, 8, 0)
    assert v2["status"] == ML.EVALUATED and v2["branch_flags"]["old_mask_status"] == ML.SATURATED
    assert res.counters["views_old_mask_blocked"] > 0


def test_forced_grouping_separate_from_reuse():
    _, res = run("nested_ab_640", "D0")
    for v in res.views:
        if v["status"] == ML.EVALUATED:
            assert v["symbols_reused"] + v["symbols_singleton"] == v["k"]
            assert (v["forced_grouping_entries"] is None) == (v["level"] == 1)


# ---------------------------------------------------------------------------
# P: periods
# ---------------------------------------------------------------------------

def test_period_mode_hand_costs_and_non_dividing_period():
    x, res = run("period_96", "D1")
    v = view(res, 1, 8, 0)
    con = mode(v, "P")["construction"]
    assert con["periods"] == [3, 2, 8] and con["replaced_ids"] == [1]
    assert con["non_dividing_proper_period_ids"] == [0]
    o_g0, p_g0 = props(v, "O")[0], props(v, "P")[0]
    assert o_g0["proposal"] == p_g0["proposal"] == "G0"
    assert o_g0["archive_bits"] == 248 and p_g0["archive_bits"] == 272     # P increases the archive
    assert decode_archive(res.candidates[mode(v, "P")["best_sha256"]]) == x


def test_period_nodes_preserve_words_and_share_factory():
    f = NodeFactory()
    words = ["01010101", "00100100", "11111111"]
    base = [f.literal(w) for w in words]
    nodes, meta = S.periodic_mode(f, words, base)
    assert [f.expand(nd) for nd in nodes] == words
    assert nodes[1] is base[1] and nodes[0].op == C.OP_REPEAT and nodes[2].op == C.OP_REPEAT
    assert meta["replaced_ids"] == [0, 2] and meta["periods"] == [2, 3, 1]


# ---------------------------------------------------------------------------
# R: relations
# ---------------------------------------------------------------------------

def oracle(words, base_hops_cap=8, flips_cap=8, window=8):
    """Independent restatement of SEARCH section 2 R (string comparisons, no ints)."""
    hops, out = [], {}
    for i, w in enumerate(words):
        cands = []
        for j in range(max(0, i - window), i):
            for fl in (0, 1, 2, 3):
                t = apply_xform(words[j], fl, 0)
                d = [q for q in range(len(w)) if t[q] != w[q]]
                if len(d) <= flips_cap and 1 + hops[j] <= base_hops_cap:
                    cands.append((len(d), j, fl, d))
        if cands:
            c = min(cands, key=lambda t: t[:3])
            out[i] = {"j": c[1], "flags": c[2], "flip_positions": c[3], "hops": 1 + hops[c[1]]}
            hops.append(1 + hops[c[1]])
        else:
            hops.append(0)
    return out, hops


def test_relations_exact_transforms_flip_caps_window_and_ties():
    x, res = run("relation_1344")
    v = view(res, 1, 64, 32)
    assert v["m"] == 20 and v["k"] == 10 and v["prefix_bits"] == 32 and v["suffix_bits"] == 32
    r = rel(v)
    assert (r[1]["j"], r[1]["flags"], r[1]["flip_positions"]) == (0, 1, [])
    assert (r[2]["j"], r[2]["flags"], r[2]["flip_positions"]) == (0, 2, [])
    assert (r[3]["j"], r[3]["flags"], r[3]["flip_positions"]) == (0, 3, [])
    assert (r[4]["j"], r[4]["flags"], r[4]["flip_positions"]) == (0, 0, list(range(8)))
    assert 5 not in r and not {6, 7, 8} & set(r)
    con = mode(v, "R(O)")["construction"]
    assert con["comparison_flip_counts"][5][0] == 9                 # (j=0, flags 0)
    assert con["comparisons_first_j"][9] == 1                       # j=0 outside the window
    assert (r[9]["j"], r[9]["flags"], r[9]["flip_positions"], r[9]["hops"]) == (1, 1, [0], 2)
    assert [r[i]["hops"] for i in (1, 2, 3, 4)] == [1, 1, 1, 1]
    exp, hops = oracle(F.relation_words())
    assert {i: {k: r[i][k] for k in ("j", "flags", "flip_positions", "hops")} for i in r} == exp
    assert con["hops"] == hops
    assert all(rr["j"] < rr["id"] for rr in con["relations"])        # no cycles


def test_hop_depth_8_boundary():
    _, res = run("hop_chain_1408", "D2")
    v = view(res, 1, 64, 0)
    r = rel(v)
    for i in range(1, 9):
        assert (r[i]["j"], r[i]["flags"], r[i]["flip_positions"], r[i]["hops"]) == (i - 1, 0, [20 + i - 1], i)
    assert (r[9]["j"], r[9]["flip_positions"], r[9]["hops"]) == (7, [27, 28], 8)
    assert (r[10]["j"], r[10]["flip_positions"], r[10]["hops"]) == (7, [27, 28, 29], 8)
    con = mode(v, "R(O)")["construction"]
    assert con["max_hops"] == 8 and con["eligible_by_flips_rejected_by_hop_cap"] >= 3
    assert oracle(F.chain_words())[1] == con["hops"]


def test_original_versus_rewritten_donor():
    _, res = run("donor_rewritten_128")
    v = view(res, 1, 16, 0)
    ro, rp = rel(v, "R(O)"), rel(v, "R(P)")
    assert (ro[1]["j"], ro[1]["flags"], ro[1]["flip_positions"]) == (0, 1, [15])   # tie f1 < f2
    assert ro[1] == rp[1]
    assert mode(v, "P")["construction"]["replaced_ids"] == [0]
    f = NodeFactory()
    words = [F.D_P, F.D_C]
    o = [f.literal(w) for w in words]
    p, _ = S.periodic_mode(f, words, o)
    ro_nodes, _ = S.relation_mode(f, words, o, ARMS["D2"])
    rp_nodes, _ = S.relation_mode(f, words, p, ARMS["D2"])
    for nodes, donor_op in ((ro_nodes, C.OP_LITERAL), (rp_nodes, C.OP_REPEAT)):
        assert nodes[1].op == C.OP_PATCH and nodes[1].args[1] == (15,)
        xf = nodes[1].children[0]
        assert xf.op == C.OP_XFORM and xf.args[1:] == (1, 0) and xf.children[0] is nodes[0]
        assert nodes[0].op == donor_op and [f.expand(nd) for nd in nodes] == words


def test_shared_donor_graph_retained_when_otherwise_unused():
    f = NodeFactory()
    words = [F.D_P, F.D_C]
    nodes, _ = S.relation_mode(f, words, [f.literal(w) for w in words], ARMS["D2"])
    root = f.concat([nodes[1], nodes[1]])            # the donor id 0 is never used directly
    arc = serialize_model(to_model(root), 32)
    assert decode_archive(arc) == F.D_C * 2
    ops = [r.op for r in to_model(root).rules]
    assert ops.count(C.OP_LITERAL) == 1 and C.OP_XFORM in ops and C.OP_PATCH in ops


def test_shared_word_witness_relation_beats_its_O_proposal_but_not_a0():
    x, res = run("witness_shared_128")
    v = view(res, 1, 64, 0)
    assert props(v, "O")[0]["archive_bits"] == 264
    assert props(v, "R(O)")[0]["archive_bits"] == 216
    assert rel(v)[1] == {"id": 1, "j": 0, "flags": 1, "flip_positions": [], "hops": 1}
    assert 8 * len(encode_literal(x)) == 192 and res.selected["source"] == "A0"
    assert mode(v, "R(O)")["minus_O_bits"] == mode(v, "R(O)")["best_bits"] - mode(v, "O")["best_bits"] < 0


def test_relation_disabled_reproduces_base_mode():
    for name in ("complement_pair_512", "relation_1344"):
        x = F.bits(name)
        cfg = DictionaryConfig("fx_r_off", MODES, predecessors=0)
        res = augment(x, cfg, encode_literal(x))
        for v in res.views:
            if v["status"] == ML.EVALUATED:
                po, pp = props(v, "O"), props(v, "P")
                assert [p["archive_sha256"] for p in props(v, "R(O)")] == [p["archive_sha256"] for p in po]
                assert [p["archive_sha256"] for p in props(v, "R(P)")] == [p["archive_sha256"] for p in pp]
                assert all(p["status"] in (ML.P_DUP, ML.P_NOGAP, ML.P_PATCH) for p in props(v, "R(O)"))


# ---------------------------------------------------------------------------
# every mode preserves expansions and the full input; costs are paid
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("name", [k for k in F.INPUTS if k not in ("empty", "short4")])
def test_every_archive_round_trips_and_every_mode_word_matches(name):
    x, res = run(name)                    # augment raises DecodeMismatch on any discrepancy
    assert decode_archive(res.archive) == x
    for h, arc in res.candidates.items():
        assert decode_archive(arc) == x
    for v in res.views:
        if v["status"] == ML.EVALUATED:
            assert all(m["construction"]["expansions_match_original"] for m in v["modes"])
            assert len(v["modes"]) == 4 and [m["mode"] for m in v["modes"]] == list(MODES)


def test_ledger_sums_exactly_for_relation_candidate():
    from hierarchy.ledger import archive_ledger
    _, res = run("witness_shared_128")
    v = view(res, 1, 64, 0)
    h = mode(v, "R(O)")["best_sha256"]
    led = archive_ledger(res.candidates[h])
    assert sum(f["bytes"] for f in led["fields"]) == len(res.candidates[h]) == 27
    kinds = {C.OP_NAMES[r.op] for r in led["model"].rules}
    assert kinds == {"LITERAL", "XFORM", "CONCAT"}


def test_ties_keep_the_earlier_incumbent():
    inc = S._Inc(b"x" * 10)
    assert not inc.offer(b"y" * 10, {"source": "augmentation"}) and inc.archive == b"x" * 10
    assert inc.offer(b"z" * 9, {"source": "a"}) and not inc.offer(b"w" * 9, {"source": "b"})


def test_duplicate_modes_still_count_requests_and_are_not_redecoded():
    _, res = run("random_1024", "D1")
    v = view(res, 1, 64, 0)                    # no periodic 64-bit words: P == O
    assert mode(v, "P")["construction"]["replaced"] == 0
    assert all(p["status"] in (ML.P_DUP, ML.P_NOGAP) for p in props(v, "P"))
    assert all(p["request_ordinal"] is not None for p in props(v, "P") if p["status"] == ML.P_DUP)
    assert res.counters["decoded"] + res.counters["duplicates"] == res.counters["serialized"]


def test_gap_templates_patch_limit_identical_across_modes():
    _, res = run("gap_flips_80", "D2")
    v = view(res, 1, 8, 0)
    for m in MODES:
        st = [p["status"] for p in props(v, m)][2:]
        assert ML.P_PATCH in st
        assert [p["detail"].get("patch_flips") for p in props(v, m)][2:] == \
            [p["detail"].get("patch_flips") for p in props(v, "O")][2:]


def test_graph_caps_and_request_caps():
    cfg = DictionaryConfig("fx_depth", MODES, widths=(8,), max_level=4, max_depth=3)
    _, res = run("complement_pair_512", cfg=cfg)
    assert res.counters["graph_rejections"] > 0
    rej = [p for v in res.views for p in v["proposals"] if p["status"] == ML.P_GRAPH]
    assert rej and all(p["request_ordinal"] is not None and p["archive_bits"] is None for p in rej)
    cfg = DictionaryConfig("fx_rules", MODES, widths=(4,), max_level=1, max_rules=3)
    _, res = run("nested_ab_640", cfg=cfg)
    assert res.counters["graph_rejections"] > 0
    cfg = DictionaryConfig("fx_views", ("O",), widths=(4, 8), max_level=2, max_views=2)
    _, res = run("complement_pair_512", cfg=cfg)
    assert res.counters["views_evaluated"] == 2 and res.stop_reason == "work_cap_views"
    cfg = DictionaryConfig("fx_req", MODES, widths=(8,), max_level=1, max_requests=5)
    _, res = run("complement_pair_512", cfg=cfg)
    assert res.counters["requests"] == 5 and res.stop_reason == "work_cap_requests"
    v = res.views[0]
    assert [m.get("status") for m in v["modes"]][2:] == [S.M_NOT_BUILT] * 2
    assert [p["status"] for p in props(v, "P")] == [ML.P_DUP, ML.P_DUP, ML.P_CAP, ML.P_NOGAP]


def test_baseline_must_decode_to_input():
    with pytest.raises(S.BaselineUnusable):
        augment("0101", ARMS["D0"], encode_literal("0110"))


def test_unavailable_is_never_zero():
    _, res = run("random_1024", "D2")
    v = view(res, 1, 64, 0)
    assert v["occurrence"]["pooled_modal_gap"] is None
    _, res = run("gap_flips_80", "D2")
    for vv in res.views:
        for m in vv.get("modes", []):
            if m["best_bits"] is None:
                assert m["minus_a0_bits"] is None and m["minus_O_bits"] is None


# ---------------------------------------------------------------------------
# restrictions and the old A3 mask
# ---------------------------------------------------------------------------

def _proj(res):
    return strip_timing(res.views), res.archive, res.selected


def test_nested_mode_restrictions_reproduce():
    for name in ("complement_pair_512", "period_96", "relation_1344", "gap_flips_10"):
        x = F.bits(name)
        a0 = encode_literal(x)
        d0 = augment(x, ARMS["D0"], a0)
        d1o = augment(x, DictionaryConfig("dict_OP_restricted", ("O",)), a0)
        assert _proj(d0) == _proj(d1o) and d0.counters == d1o.counters
        d1 = augment(x, ARMS["D1"], a0)
        d2op = augment(x, DictionaryConfig("dict_OPR_restricted", ("O", "P")), a0)
        assert strip_timing(d1.views) == strip_timing(d2op.views) and d1.archive == d2op.archive
        assert d1.counters == d2op.counters


@pytest.mark.parametrize("name", ["complement_pair_512", "nested_ab_640", "counter_1024",
                                  "gap_flips_10", "odd_tail_59", "single_symbol_256"])
def test_old_mask_reproduces_old_a3_deterministic_proposals(name):
    x = F.bits(name)
    a0 = encode_literal(x)
    old = ML.augment(x, ML.ARMS["A3"], a0)
    cfg = DictionaryConfig("dict_O_oldmask", ("O",), max_requests=256, old_branch_mask=True)
    new = augment(x, cfg, a0)
    assert new.archive == old.archive
    drop = ("mode", "trace")
    assert {k: v for k, v in new.selected.items() if k not in drop} == \
        {k: v for k, v in old.selected.items() if k not in drop}
    assert [{k: v for k, v in t.items() if k != "mode"} for t in new.selected["trace"]] == old.selected["trace"]
    keep = ("proposal", "status", "archive_bits", "archive_sha256", "rule_count", "dag_depth",
            "accepted", "detail")
    assert len(new.views) == len(old.views)
    for a, b in zip(new.views, old.views):
        assert (a["level"], a["width"], a["origin"], a["status"], a["m"], a["k"]) == \
            (b["level"], b["width"], b["origin"], b["status"], b["m"], b["k"])
        assert [{k: p[k] for k in keep} for p in a["proposals"]] == [{k: p[k] for k in keep} for p in b["proposals"]]
        if a["status"] == ML.EVALUATED:
            assert a["dictionary_content"] == b["dictionary_content"] and a["top_stream"] == b["top_stream"]
    for k in ("views_evaluated", "requests", "serialized", "decoded", "duplicates", "patch_rejections",
              "graph_rejections", "no_gap_template", "strict_improvements"):
        assert new.counters[k] == old.counters[k], k


# ---------------------------------------------------------------------------
# Q4 guard: one owner, no copied engine
# ---------------------------------------------------------------------------

OWNER_DEFS = {"pair_grammar", "serialize_model", "decode_archive", "shortest_period", "apply_xform",
              "to_model", "NodeFactory", "infer_v2", "archive_ledger", "encode_literal", "path_levels",
              "ViewBuilder", "ranked_gaps", "view_diagnostics", "canonical", "runs", "occurrences",
              "read_checkpoints", "run_queue", "validate_references", "tree_hash", "_Inc"}
ALGO_DEFS = {"augment", "periodic_mode", "relation_mode", "DictionaryConfig", "dictionary_graph"}


def owner_copies(paths) -> list[str]:
    bad = []
    for p in paths:
        tree = ast.parse(Path(p).read_text())
        for n in ast.walk(tree):
            if isinstance(n, (ast.FunctionDef, ast.ClassDef)):
                if n.name in OWNER_DEFS or (n.name in ALGO_DEFS and Path(p).name != "search.py"):
                    bad.append(f"{Path(p).name}:{n.name}")
    return bad


def test_no_copied_owner_or_second_algorithm_definition(tmp_path):
    files = sorted(PKG.rglob("*.py"))
    assert files and owner_copies(files) == []
    planted = tmp_path / "planted.py"
    planted.write_text("def ViewBuilder(x):\n    return x\ndef relation_mode(x):\n    return x\n")
    assert owner_copies([planted]) == ["planted.py:ViewBuilder", "planted.py:relation_mode"]
