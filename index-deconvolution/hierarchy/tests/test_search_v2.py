"""HID-search-v2 proposals, arms and boundary search (ACCEPTANCE.md section 2, items 1-5).

Every input is constructed here; generator truth (true word, period, flip positions,
cuts) appears only in assertions, never as an argument to inference.
"""
from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

from hierarchy import consensus as K
from hierarchy import search_v2 as S
from hierarchy.candidates import shortest_period
from hierarchy.decode import decode_archive
from hierarchy.infer import FULL, infer
from hierarchy.ledger import BUCKETS, archive_ledger, field_buckets
from hierarchy.model import NodeFactory, Patch, Repeat, count_reachable, to_model
from hierarchy.segmentation import BoundaryConfig, BoundarySearch, supplied_partition
from hierarchy.wire import encode_literal, serialize_model

ARMS = S.ARMS


def primitive(rng, p):
    while True:
        w = "".join(rng.choice("01") for _ in range(p))
        if all(w != w[:d] * (p // d) for d in range(1, p) if p % d == 0):
            return w


def noisy(word, n, flips):
    y = bytearray(K.tile(word, n).encode())
    for q in flips:
        y[q] ^= 1
    return y.decode()


# ---------------------------------------------------------------------------
# 1. Consensus templates and corrections
# ---------------------------------------------------------------------------

def test_consensus_majority_tie_and_ragged_phases():
    assert K.consensus_word("01", 1) == "0"                   # one 0, one 1: tie -> 0
    assert K.consensus_word("0111", 1) == "1"
    # n = 10, p = 3: phase 0 has four members, phases 1-2 have three
    x = "1" + "10" + "0" + "11" + "1" + "01" + "0"            # x[0::3] = 1,0,1,0 (tie)
    assert [x[j::3] for j in range(3)] == ["1010", "110", "011"]
    assert K.consensus_word(x, 3) == "011"


def test_consensus_corrects_a_noisy_first_block_where_the_first_block_template_fails():
    word = "10110010"
    flips = [1, 4, 33, 70, 101]                              # two errors in the first block
    x = noisy(word, 128, flips)
    lim = 128 // 16
    c = K.Residual(x, int(x, 2), K.consensus_word(x, 8), lim)
    f = K.Residual(x, int(x, 2), K.first_block_word(x, 8), lim)
    assert c.word == word and c.positions == flips
    assert f.word != word and f.count > lim and f.positions is None


def test_residual_gate_boundary_is_floor_n_over_16():
    word = "0" * 31 + "1"
    n = 1024
    rng = random.Random(3)
    ok = sorted(rng.sample(range(32, n), n // 16))
    bad = sorted(rng.sample(range(32, n), n // 16 + 1))
    for flips, admitted in ((ok, True), (bad, False)):
        x = noisy(word, n, flips)
        r = K.Residual(x, int(x, 2), word, n // 16)
        assert r.count == len(flips) and (r.positions is not None) is admitted


def test_period_63_outside_the_old_grid_is_found_with_all_corrections_by_the_global_arm():
    rng = random.Random(63)
    word = primitive(rng, 63)
    n = 4096
    flips = sorted(rng.sample(range(n), 200))                # > 64 corrections, <= n/16
    x = noisy(word, n, flips)
    assert 63 not in S.ORIGINAL_GRID
    res = S.infer_v2(x, ARMS["hid_global"])
    assert decode_archive(res.archive) == x
    led = archive_ledger(res.archive)
    patches = [r for r in led["model"].rules if isinstance(r, Patch)]
    assert res.selected_stage == "G" and res.telemetry["selected_detail"]["period"] == 63
    assert len(patches) == 1 and list(patches[0].positions) == flips
    reps = [r for r in led["model"].rules if isinstance(r, Repeat)]
    assert reps and led["model"].lengths()[reps[0].child] == 63
    assert res.telemetry["stages"]["G"]["best_period"] == 63


def test_zero_error_template_collapses_patch_and_global_holds_more_than_64_corrections():
    f = NodeFactory()
    x = K.tile("110", 300)
    r = K.Residual(x, int(x, 2), "110", 300 // 16)
    assert r.positions == [] and K.global_proposal(f, r, 3).op != Patch.op
    n = 2048
    rng = random.Random(9)
    flips = sorted(rng.sample(range(n), 100))
    x = noisy("1101", n, flips)
    r = K.Residual(x, int(x, 2), "1101", n // 16)
    root = K.global_proposal(NodeFactory(), r, 4)
    m = to_model(root)
    assert decode_archive(serialize_model(m, n)) == x
    assert [len(p.positions) for p in m.rules if isinstance(p, Patch)] == [100]


# ---------------------------------------------------------------------------
# 2. Local blocks
# ---------------------------------------------------------------------------

def test_local_blocks_carry_phase_short_final_block_and_eligibility_boundaries():
    word = "1011001"                                          # 1024 mod 7 = 2: block 2 phase 2
    n = 2 * 1024 + 40                                         # short final block of 40 bits
    y = K.tile(word, n)
    exact = list(range(5, 5 + 64 * 7, 7))[:64]                # block 0: exactly min(64, 64)
    over = list(range(1024 + 3, 1024 + 3 + 65 * 9, 9))[:65]   # block 1: 65 > 64 -> literal
    tail = [2048 + 1, 2048 + 10, 2048 + 20]                   # block 2: 3 > floor(40/16) = 2
    flips = exact + over + tail
    x = noisy(word, n, flips)
    r = K.Residual(x, int(x, 2), word, 10 ** 9)
    f = NodeFactory()
    root = K.local_proposal(f, x, r, 7, 1024, 64, 16)
    kids = root.children
    assert len(kids) == 3
    assert kids[0].op == Patch.op and len(kids[0].args[1]) == 64
    assert kids[1].op == 0 and f.expand(kids[1]) == x[1024:2048]          # literal
    assert kids[2].op == 0 and f.expand(kids[2]) == x[2048:]
    assert f.expand(root) == x
    assert decode_archive(serialize_model(to_model(root), n)) == x
    # phase: block 1's builder word (were it eligible) is the rotated slice, not the word
    b1 = K.periodic(NodeFactory(), y[1024:2048], 7)
    assert b1.children[0].children[0].args[0] == y[1024:1031] != word


def test_local_block_with_zero_local_errors_is_a_shared_periodic_node():
    x = noisy("01", 3072, [5])
    r = K.Residual(x, int(x, 2), "01", 3072 // 16)
    f = NodeFactory()
    root = K.local_proposal(f, x, r, 2, 1024, 64, 16)
    assert root.children[1] is root.children[2]                # identical blocks interned
    assert root.children[0].op == Patch.op
    m = to_model(root)
    assert len(m.rules) < count_reachable(root, share=False)


# ---------------------------------------------------------------------------
# 3. Arms: cumulative preservation, ties, independent legacy, determinism
# ---------------------------------------------------------------------------

def _f06_like(seed=6, n=4096, p=63):
    rng = random.Random(seed)
    word = primitive(rng, p)
    return noisy(word, n, sorted(rng.sample(range(n), n // 32)))


def test_arms_are_nested_and_every_arm_reruns_the_unchanged_legacy_search():
    x = _f06_like()
    legacy = infer(x, FULL).archive
    prev = None
    for name, cfg in ARMS.items():
        r = S.infer_v2(x, cfg)
        assert decode_archive(r.archive) == x
        assert r.telemetry["stages"]["L"]["archive_sha256"] == \
            __import__("hashlib").sha256(legacy).hexdigest()
        assert list(r.telemetry["stages"]) == list(cfg.stages)
        assert prev is None or r.archive_bits <= prev
        prev = r.archive_bits
    assert S.infer_v2(x, ARMS["hid_legacy"]).archive == legacy


def test_an_added_proposal_strictly_wins_and_raw_is_kept_on_random_input():
    x = _f06_like()
    d = S.infer_v2(x, ARMS["hid_dense_local"])
    g = S.infer_v2(x, ARMS["hid_global"])
    assert g.archive_bits < d.archive_bits and g.selected_stage == "G"
    assert g.telemetry["stages"]["G"]["strict_improvements"] >= 1
    from hierarchy import corpus
    rnd, _ = corpus.generate_unit("search_v2_fixture", "F07", 1024, 0)
    assert infer(rnd, FULL).mode == "literal"               # precondition, checked
    r = S.infer_v2(rnd + "011", ARMS["hid_full"])
    rnd += "011"
    assert r.selected_stage == "raw" and r.archive == encode_literal(rnd)


def test_equal_length_keeps_the_earlier_incumbent():
    inc = S._Incumbent(b"x" * 10)
    assert not inc.offer(b"y" * 10, "L") and inc.stage == "raw"
    assert inc.offer(b"z" * 9, "P") and not inc.offer(b"w" * 9, "C") and inc.stage == "P"
    x = K.tile("1100101", 700)                               # legacy already optimal here
    r = S.infer_v2(x, ARMS["hid_full"])
    assert r.selected_stage in ("L", "raw")
    assert all(st.get("strict_improvements", 0) == 0 for s, st in r.telemetry["stages"].items()
               if s != "L")


def test_repeated_runs_give_identical_archives_and_deterministic_telemetry():
    x = _f06_like(seed=11, n=3000, p=45)

    def strip(t):
        if isinstance(t, dict):
            return {k: strip(v) for k, v in t.items() if not k.endswith("wall_s")}
        return [strip(v) for v in t] if isinstance(t, list) else t
    a, b = S.infer_v2(x, ARMS["hid_full"]), S.infer_v2(x, ARMS["hid_full"])
    assert a.archive == b.archive and strip(a.telemetry) == strip(b.telemetry)
    assert a.trace == b.trace


def test_config_refuses_non_prefix_stages_and_changed_legacy():
    with pytest.raises(ValueError):
        S.SearchV2Config("x", ("L", "C"))
    with pytest.raises(ValueError):
        S.SearchV2Config("x", ("L",), legacy_config_sha256="0" * 64)
    assert len({c.sha256() for c in ARMS.values()}) == 6


def test_inference_modules_import_no_corpus_or_evaluation_layer():
    import ast
    pkg = Path(S.__file__).parent
    for mod in ("search_v2.py", "consensus.py", "segmentation.py"):
        tree = ast.parse((pkg / mod).read_text())
        names = {a.name for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)
                 for a in n.names} | {n.module for n in ast.walk(tree)
                                      if isinstance(n, ast.ImportFrom) and n.module}
        assert not names & {"corpus", "study_corpus", "benchmark", "report", "report_v2",
                            "diagnostics_v2", "study"}, mod


def test_search_v2_reuses_the_existing_owners():
    import hierarchy.candidates as Cd
    import hierarchy.consensus as Kc
    import hierarchy.decode as Dm
    import hierarchy.segmentation as Sg
    import hierarchy.wire as W
    assert Sg.shortest_period is Cd.shortest_period and Kc.positions_of is Cd.positions_of
    assert S.serialize_model is W.serialize_model and Sg.serialize_model is W.serialize_model
    assert S.decode_archive is Dm.decode_archive and Sg.decode_archive is Dm.decode_archive
    assert S.infer is infer and S.FULL is FULL


# ---------------------------------------------------------------------------
# 4. Boundary search
# ---------------------------------------------------------------------------

def test_coarse_cut_set_parent_eligibility_and_one_bit_children():
    b = BoundarySearch("0" * 100)
    want = sorted({1, 99} | {(j * 100) // 32 for j in range(1, 32)})
    assert b.coarse_cuts(0, 100) == want and 1 in want and 99 in want
    assert b.coarse_cuts(10, 74) == sorted({11, 73} | {10 + (j * 64) // 32 for j in range(1, 32)})
    short = BoundarySearch("01" * 31 + "1")                  # 63 bits: no eligible parent
    out = short.run()
    assert out["stop_reason"] == "no_eligible_parent" and out["segments"] == 1


def test_two_regime_input_is_split_and_strict_improvement_terminates():
    rng = random.Random(5)
    x = K.tile("0011", 1500) + "".join(rng.choice("01") for _ in range(500)) + K.tile("10", 1000)
    b = BoundarySearch(x)
    offered = []
    out = b.run(offered.append)
    assert decode_archive(out["archive"]) == x
    assert out["segments"] >= 2 and out["stop_reason"] in ("no_strict_improvement", "max_segments")
    assert out["counts"]["commits"] == out["segments"] - 1
    sizes = [len(a) for a in offered]
    assert sizes == sorted(sizes, reverse=True) and offered[-1] == out["archive"]
    assert all(r["levels"] <= 5 for r in out["rounds"] if "levels" in r)
    # the heuristic is not claimed optimal: a tiny exhaustive single-cut table is diagnostic
    best_single = min(len(BoundarySearch(x).evaluate((c,))) for c in range(1, len(x), 50))
    assert best_single > 0


def test_refinement_tie_rule_prefers_shorter_then_smaller_cut():
    x = "0" * 200 + "1" * 200
    out = BoundarySearch(x).run()
    assert out["cuts"] == [200] and out["rounds"][0]["resolved_to_one_bit"]


@pytest.mark.parametrize("cfg,reason", [
    (BoundaryConfig(root_trial_cap=5), "root_trial_cap"),
    (BoundaryConfig(cached_leaf_cap=4), "cached_leaf_cap"),
    (BoundaryConfig(length_charge_multiplier=3), "leaf_length_charge_cap"),
])
def test_budget_exhaustion_stops_and_offers_the_best_serialized_trial(cfg, reason):
    x = K.tile("0011", 800) + K.tile("011", 800)
    b = BoundarySearch(x, cfg)
    out = b.run()
    assert out["stop_reason"] == reason and out["cap_hit"]
    assert out["archive"] == b.best_seen[2] or len(out["archive"]) <= b.best_seen[0]
    assert decode_archive(out["archive"]) == x
    assert b.counts["root_trials"] <= cfg.root_trial_cap
    assert len(b.leaves) <= cfg.cached_leaf_cap
    assert b.charge_length <= cfg.length_charge_multiplier * len(x)
    assert out["unresolved_refinement"] is not None


def test_leaf_builder_is_shortest_period_only_with_literal_on_ties():
    b = BoundarySearch("01" * 50)
    node = b.leaf(0, 100)
    assert shortest_period("01" * 50) == 2 and node.op != 0
    lit = BoundarySearch("0110")
    assert lit.leaf(0, 4).op == 0                             # period 3 > 4 // 2: literal
    assert b.counts["leaf_serializations"] == 2 and b.counts["leaf_length_charge"] == 100


def test_partition_shares_identical_leaves():
    x = "01" * 40 + "1" * 20 + "01" * 40
    ref = supplied_partition(x, [80, 100])
    m = archive_ledger(ref["archive"])["model"]
    assert decode_archive(ref["archive"]) == x
    assert len(m.rules) < 2 * 3                              # the two "01"*40 leaves are one node


def test_boundary_stage_offers_to_the_full_incumbent():
    rng = random.Random(12)
    x = K.tile(primitive(rng, 17), 1365) + "".join(rng.choice("01") for _ in range(1366)) + \
        K.tile(primitive(rng, 13), 1365)
    g = S.infer_v2(x, ARMS["hid_global"])
    full = S.infer_v2(x, ARMS["hid_full"])
    assert full.archive_bits <= g.archive_bits
    st = full.telemetry["stages"]["B"]
    assert st["counts"]["root_trials"] <= 512 and st["segments"] <= 8
    if full.selected_stage == "B":
        assert full.telemetry["selected_detail"]["cuts"] == st["cuts"]


# ---------------------------------------------------------------------------
# 5. Independent decoding, bounds and ledgers
# ---------------------------------------------------------------------------

def test_isolated_stdlib_decoder_reads_long_and_ragged_v2_archives(tmp_path):
    from hierarchy import decode as dmod
    rng = random.Random(21)
    xs = [_f06_like(seed=1, n=65539, p=63), K.tile("101", 4099) + "1",
          K.tile(primitive(rng, 19), 3000) + K.tile("10", 1099)]
    shutil.copy(dmod.__file__, tmp_path / "decode.py")
    names = []
    for i, x in enumerate(xs):
        arc = S.infer_v2(x, ARMS["hid_full" if i else "hid_global"]).archive
        (tmp_path / f"a{i}.bin").write_bytes(arc)
        names.append(f"a{i}.bin")
    out = subprocess.run([sys.executable, "-I", "-S", "decode.py", *names], cwd=tmp_path,
                         env={"PATH": os.environ.get("PATH", "")}, capture_output=True, text=True)
    got = json.loads(out.stdout)
    assert out.returncode == 0 and [g["bits"] for g in got] == xs


def test_graph_limits_reject_candidates_with_telemetry_and_never_truncate():
    x = _f06_like(seed=4, n=8192, p=63)
    tight = S.SearchV2Config("tight", ("L", "P", "C", "D", "G"), max_rules=3)
    r = S.infer_v2(x, tight)
    assert r.telemetry["stages"]["D"]["graph_rejections"] > 0
    assert r.telemetry["stages"]["G"]["graph_rejections"] > 0
    assert r.selected_stage in ("raw", "L") and decode_archive(r.archive) == x


def test_field_buckets_sum_exactly_for_every_codec_and_arm():
    from hierarchy.baselines import BASELINE_METHODS, encode_baseline
    rng = random.Random(2)
    xs = ["1", "01" * 300, _f06_like(seed=3, n=2048, p=21),
          "".join(rng.choice("01") for _ in range(999))]
    for x in xs:
        arcs = [encode_baseline(x, m) for m in BASELINE_METHODS]
        arcs += [S.infer_v2(x, c).archive for c in ARMS.values()]
        for a in arcs:
            b = field_buckets(a)
            assert set(b) == set(BUCKETS) and sum(b.values()) == 8 * len(a)
    lit = field_buckets(encode_literal("101"))
    assert lit["literal_payload_bits"] == 3 and lit["literal_padding_bits"] == 5
