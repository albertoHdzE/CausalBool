"""Engineering fixtures for ``search`` (BENCHMARK section 2). Expectations are written by
hand from the wire annex and the protocol text, not taken from the implementation."""
from __future__ import annotations

import ast
import random
from pathlib import Path

import pytest
from hierarchy.decode import decode_archive
from hierarchy.wire import encode_literal

from hierarchy_multilevel import search as S
from hierarchy_multilevel.search import ARMS, MultilevelConfig, augment, strip_timing
from hierarchy_multilevel.tests import fixtures as F

PKG = Path(S.__file__).resolve().parent


def run(name, arm="A3", cfg=None):
    x = F.bits(name)
    return x, augment(x, cfg or ARMS[arm], encode_literal(x))


def view(res, level, width, origin):
    return next(v for v in res.views if (v["level"], v["width"], v["origin"]) == (level, width, origin))


def test_declared_fixture_bounds():
    vals = [v for _, v in F.INPUTS.values()]
    assert len(set(vals)) == len(vals) <= 32
    assert max(map(len, vals)) <= 4099


def test_empty_input_requests_nothing_and_diagnostics_unavailable():
    a0 = encode_literal("")
    res = augment("", ARMS["A3"], a0)
    assert res.archive == a0 and res.views == [] and res.counters["requests"] == 0
    assert res.counters["diagnostics_unavailable"] == "empty_input"
    assert res.stop_reason == "empty_input"


def test_short_and_width_larger_than_input_are_ineligible():
    x, res = run("short4")
    assert {v["status"] for v in res.views} == {S.INELIGIBLE_SHORT}
    assert res.counters["requests"] == 0 and res.archive == encode_literal(x)
    _, res = run("odd_symbols_59")
    assert view(res, 1, 64, 0)["status"] == S.INELIGIBLE_SHORT          # 64 > 59


def test_single_symbol_branch_stops_after_its_proposals():
    _, res = run("single_symbol_256")
    v1 = view(res, 1, 4, 0)
    assert v1["status"] == S.EVALUATED and v1["k"] == 1 and v1["m"] == 64
    assert all(p["status"] != S.P_CAP for p in v1["proposals"])
    assert view(res, 2, 4, 0)["status"] == S.SINGLE


def test_odd_symbol_counts_move_into_suffix_hand():
    x = F.bits("odd_symbols_59")
    lv = S.path_levels(x, 8, 0, 3)
    assert [L.m for L in lv] == [7, 3, 1]
    _, res = run("odd_symbols_59")
    assert view(res, 1, 8, 0)["k"] == 1                       # seven identical words
    v2 = view(res, 2, 8, 0)
    assert v2["status"] == S.SINGLE                           # path stopped after level 1
    assert v2["prefix_bits"] == 0 and v2["suffix_bits"] == 59 - 3 * 16 == 11
    assert view(res, 3, 8, 0)["status"] == S.SINGLE
    v2o = view(res, 2, 8, 4)                                  # origin 4: m1 = 6, m2 = 3
    assert v2o["m"] == 3 and v2o["prefix_bits"] == 4 and v2o["suffix_bits"] == 59 - 4 - 48


@pytest.mark.parametrize("name", [k for k in F.INPUTS if k != "empty"])
def test_every_admissible_archive_round_trips_and_spans_are_lossless(name):
    x, res = run(name)                    # augment raises DecodeMismatch on any discrepancy
    assert decode_archive(res.archive) == x
    for v in res.views:
        if v["status"] == S.EVALUATED:
            assert v["prefix_bits"] + v["m"] * v["span"] + v["suffix_bits"] == len(x)
            assert v["prefix_bits"] == v["origin"]
            assert len(v["top_stream"]) == v["m"]


def test_hand_cost_of_g0_includes_dictionary_and_envelope():
    # x = W*4, W=01101001. Origin 0: REPEAT(LITERAL W, 4).
    # rules: LITERAL op1 + len1 + 1 byte = 3; REPEAT op1 + child1 + copies1 = 3; q_rules 1
    # payload 7; envelope magic 4 + codec 1 + n 1 + payload length 1 = 7; total 14 bytes.
    _, res = run("hand32", "A1")
    g0 = view(res, 1, 8, 0)["proposals"][0]
    assert g0["proposal"] == "G0" and g0["archive_bits"] == 8 * 14
    # origin 4: CONCAT(LIT 0110, REPEAT(LIT 10010110, 3), LIT 1001): 3+3+3+3 + CONCAT
    # op1 + arity1 + 3 ids = 5 -> 17, q 1 -> payload 18, envelope 7 -> 25 bytes.
    g0o = view(res, 1, 8, 4)["proposals"][0]
    assert g0o["archive_bits"] == 8 * 25
    # the literal A0 is 7 + 4 = 11 bytes, so the 14-byte G0 is offered and loses
    assert len(encode_literal(F.bits("hand32"))) == 11 and res.selected["source"] == "A0"


def test_weak_support_spans_in_original_bit_coordinates_hand():
    _, res = run("hand_origin32", "A1")
    v = view(res, 1, 8, 4)                      # tokens W1 W2 W1; W2 singleton at token 1
    assert v["top_stream"] == [0, 1, 0]
    ws = v["weak_support"]
    assert ws["bit_intervals"] == [[0, 4], [12, 20], [28, 32]]
    assert ws["bits"] == 16 and ws["fraction_of_n"] == 0.5
    occ = {r["symbol"]: r for r in v["occurrence"]["per_symbol"]}
    assert occ[0]["token_positions"] == [0, 2] and occ[0]["modal_gap"] == 2
    assert occ[1]["modal_gap"] is None and occ[1]["irregular_fraction"] is None
    assert occ[1]["unavailable_reason"] == "single_occurrence"


def test_unavailable_is_never_zero():
    assert S.modal_gap([]) == (None, None)
    _, res = run("random_1024", "A2")
    v = view(res, 1, 64, 0)                     # 16 distinct 64-bit words: no repeats
    assert v["k"] == v["m"] == 16
    assert v["occurrence"]["pooled_modal_gap"] is None
    assert v["occurrence"]["pooled_irregular_fraction"] is None
    assert v["occurrence"]["unavailable_reason"] == "no_repeated_symbol"


def test_gap_template_exact_and_patch_limits():
    _, res = run("gap_exact_960", "A1")
    v = view(res, 1, 8, 0)
    g2 = v["proposals"][2]
    assert v["ranked_gaps"][0][0] == 3 and g2["detail"]["gap"] == 3 and g2["detail"]["patch_flips"] == 0
    _, res = run("gap_flips_10", "A1")
    g2 = view(res, 1, 8, 0)["proposals"][2]
    assert g2["detail"]["patch_flips"] == 10 and g2["status"] in (S.P_NEW, S.P_DUP)
    _, res = run("gap_flips_80", "A1")
    rej = [p for p in view(res, 1, 8, 0)["proposals"][2:] if p["status"] == S.P_PATCH]
    assert rej and all(p["detail"]["patch_flips"] > 64 and p["archive_bits"] is None for p in rej)


def test_no_gap_template_is_recorded_not_errored():
    _, res = run("single_symbol_256")
    v = view(res, 1, 4, 0)                      # one symbol: one gap value (1) only
    assert [p["status"] for p in v["proposals"]][3] == S.P_NOGAP
    assert v["proposals"][3]["archive_bits"] is None


def test_shorter_tokens_lose_after_dictionary_cost():
    x, res = run("random_1024", "A2")
    lit = 8 * len(encode_literal(x))
    v = view(res, 1, 4, 0)
    assert all(p["archive_bits"] > lit for p in v["proposals"] if p["archive_bits"] is not None)
    assert res.selected["source"] == "A0"


def test_duplicate_proposal_counted():
    _, res = run("random_1024", "A2")
    v = view(res, 1, 64, 0)
    assert v["proposals"][1]["status"] == S.P_DUP            # no pair repeats: G1 == G0


def test_ties_keep_the_earlier_incumbent():
    inc = S._Inc(b"x" * 10)
    assert not inc.offer(b"y" * 10, {"source": "augmentation"}) and inc.archive == b"x" * 10
    assert inc.offer(b"z" * 9, {"source": "a"}) and not inc.offer(b"w" * 9, {"source": "b"})
    assert inc.archive == b"z" * 9


def test_graph_rejection_and_caps():
    cfg = MultilevelConfig("fx_depth", (8,), 4, max_depth=3)
    _, res = run("alternating_512", cfg=cfg)
    assert res.counters["graph_rejections"] > 0
    assert any(p["status"] == S.P_GRAPH for v in res.views for p in v["proposals"])
    cfg = MultilevelConfig("fx_rules", (4,), 1, max_rules=3)
    _, res = run("permutation_1024", cfg=cfg)
    assert res.counters["graph_rejections"] > 0
    cfg = MultilevelConfig("fx_views", (4, 8), 2, max_views=2)
    _, res = run("alternating_512", cfg=cfg)
    assert res.counters["views_evaluated"] == 2 and res.stop_reason == "work_cap_views"
    assert any(v["status"] == S.VIEW_CAP for v in res.views)
    cfg = MultilevelConfig("fx_req", (4, 8), 1, max_requests=2)
    _, res = run("alternating_512", cfg=cfg)
    assert res.counters["requests"] == 2 and res.stop_reason == "work_cap_requests"
    assert [p["status"] for p in res.views[0]["proposals"]][2] == S.P_CAP
    assert [v["status"] for v in res.views[1:]] == [S.REQUEST_CAP_VIEW] * 3


def test_saturated_branch_keeps_structured_dictionary():
    _, res = run("counter_1024", "A3")
    v = view(res, 1, 8, 0)
    assert v["k"] == v["m"] == 128
    assert view(res, 2, 8, 0)["status"] == S.SATURATED
    # words 00000000 (period 1) and 01010101 (period 2) are complete proper repeats
    assert sum(c["proper_repeat"] for c in v["dictionary_content"]) >= 2
    p0 = next(c for c in v["dictionary_content"] if c["symbol"] == 0)
    assert p0["shortest_period"] == 1 and p0["proper_repeat"]


def test_forced_grouping_separate_from_reuse():
    _, res = run("thue_morse_1024", "A3")
    for v in res.views:
        if v["status"] == S.EVALUATED:
            assert v["symbols_reused"] + v["symbols_singleton"] == v["k"]
            if v["level"] > 1:
                assert v["forced_grouping_entries"] == v["symbols_singleton"]
            else:
                assert v["forced_grouping_entries"] is None


def test_dictionary_depth_and_pair_rule_depth_reported_separately():
    _, res = run("nested_ab_640", "A3")
    v = view(res, 1, 8, 0)
    g1 = v["proposals"][1]
    assert v["dictionary_depth"] == 1 and g1["detail"]["pair_rules"] >= 1
    assert g1["detail"]["pair_rule_depth"] >= 1
    assert view(res, 2, 8, 0)["dictionary_depth"] == 2


def test_canonical_relabel_invariance():
    rng = random.Random(62001)
    stream = [rng.randrange(5) for _ in range(200)]
    perm = list(range(5))
    rng.shuffle(perm)
    assert S.canonical([perm[t] for t in stream])[0] == S.canonical(stream)[0]
    words = ["0011", "0101", "1100"]
    x = "".join(words[t % 3] for t in stream)
    y = "".join(words[(t + 1) % 3] for t in stream)     # same pattern, labels shifted
    a = S.path_levels(x, 4, 0, 2)
    b = S.path_levels(y, 4, 0, 2)
    assert [L.stream for L in a] == [L.stream for L in b]


def test_nested_ablation_restrictions_equal():
    for name in ("alternating_512", "nested_ab_640", "gap_flips_10"):
        x = F.bits(name)
        a0 = encode_literal(x)
        a2 = augment(x, ARMS["A2"], a0)
        a3l1 = augment(x, MultilevelConfig("multi_l4_restricted", S.WIDTHS, 1), a0)
        assert strip_timing(a2.views) == strip_timing(a3l1.views)
        assert a2.archive == a3l1.archive and a2.counters == a3l1.counters
        a1 = augment(x, ARMS["A1"], a0)
        a2w8 = augment(x, MultilevelConfig("multi_l1_restricted", (8,), 1), a0)
        assert strip_timing(a1.views) == strip_timing(a2w8.views)
        assert a1.archive == a2w8.archive and a1.selected == a2w8.selected


def test_ragged_tails_each_level():
    x, res = run("ragged_4099", "A3")
    for v in res.views:
        if v["m"]:
            assert v["suffix_bits"] == len(x) - v["origin"] - v["m"] * v["span"]
    ms = [view(res, lv, 8, 4)["m"] for lv in (1, 2, 3, 4)]
    assert ms == [(4099 - 4) // 8, (4099 - 4) // 16, (4099 - 4) // 32, (4099 - 4) // 64]


def test_baseline_must_decode_to_input():
    with pytest.raises(S.BaselineUnusable):
        augment("0101", ARMS["A1"], encode_literal("0110"))


# ---------------------------------------------------------------------------
# Q4 guard: one owner, no copied engine
# ---------------------------------------------------------------------------

OWNER_DEFS = {"pair_grammar", "serialize_model", "decode_archive", "shortest_period",
              "to_model", "NodeFactory", "infer_v2", "run_arm", "archive_ledger", "encode_literal"}
ALGO_DEFS = {"augment", "path_levels", "ViewBuilder", "ranked_gaps", "view_diagnostics"}


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
    planted.write_text("def pair_grammar(seq, first_id, max_rules):\n    return [], seq\n"
                       "def augment(x):\n    return x\n")
    assert owner_copies([planted]) == ["planted.py:pair_grammar", "planted.py:augment"]
