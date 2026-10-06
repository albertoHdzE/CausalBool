"""Tests of task-preserving state compaction owned by deconvolution.py
(minimal_task_partition, distinguishing_task_word, task_word_path).

Fixtures and expected outcomes were declared, before any execution, in the run file
results/causal_task_compaction_v1/task-compaction-v1-r1/fixtures.json; tests/fixtures/
task_compaction_v1.json is its byte-identical versioned copy (sha256 6f7f7cd5...cbef690),
so these tests do not need the run directory.  The counter and rule-150 tables below are
hand-built from their formulas, not from any model owner."""
from __future__ import annotations

import json
import os
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

from deconvolution import (  # noqa: E402
    distinguishing_task_word, induced_map, minimal_task_partition, task_word_path,
)

FIXTURES = os.path.join(HERE, "fixtures", "task_compaction_v1.json")
DECL = {f["id"]: f for f in json.load(open(FIXTURES))["fixtures"]}


def counter_actions(n: int) -> list[list[int]]:
    """PROTOCOL §2 order on F(x) = x+1 mod 2**n, built from the formula."""
    N = 2 ** n
    F = [(x + 1) % N for x in range(N)]
    acts = [F]
    acts += [[F[(x & ~(1 << j)) | (c << j)] for x in range(N)] for j in range(n) for c in (0, 1)]
    acts += [[F[x ^ (1 << j)] for x in range(N)] for j in range(n)]
    acts += [[(F[x] & ~(1 << j)) | (c << j) for x in range(N)] for j in range(n) for c in (0, 1)]
    acts += [[F[F[x]] for x in range(N)]]
    return acts


def rule150_ring4() -> list[int]:
    def bit(x, i):
        return (x >> (i % 4)) & 1
    return [sum((bit(x, i - 1) ^ bit(x, i) ^ bit(x, i + 1)) << i for i in range(4)) for x in range(16)]


def parity(N: int) -> list[int]:
    return [bin(x).count("1") % 2 for x in range(N)]


@pytest.mark.parametrize("fid", ["FX1_identity", "FX2_one_step", "FX3_two_step",
                                 "FX6_constant_task", "FX6_identity_task", "FX9_relabel_outputs"])
def test_declared_stage_chains(fid):
    f = DECL[fid]
    r = minimal_task_partition(f["outputs"], f["transitions"])
    e = f["expect"]
    if "stages" in e:
        assert r["stages"] == e["stages"]
        assert r["strict_rounds"] == e["strict_rounds"]
    assert r["K"] == e["K"]
    for key in ("alpha", "decoder", "macro", "representatives"):
        if key in e:
            assert r[key] == e[key]
    assert r["stages"][-1] == r["stages"][-2] == r["alpha"]


def test_fx1_identity_grouping_is_valid_but_not_minimal():
    f = DECL["FX1_identity"]
    ident = [0, 1, 2, 3]
    assert induced_map(ident, f["outputs"])[1] is None
    assert all(induced_map(ident, [ident[t[x]] for x in range(4)])[1] is None for t in f["transitions"])
    r = minimal_task_partition(f["outputs"], f["transitions"])
    assert r["K"] < len(set(ident))
    assert r["alpha"] == [0, 0, 1, 1]


@pytest.mark.parametrize("fid", ["FX2_one_step", "FX3_two_step"])
def test_declared_witnesses(fid):
    f = DECL[fid]
    r = minimal_task_partition(f["outputs"], f["transitions"])
    for w in f["expect"]["witness_pairs"]:
        x, y = w["x"], w["y"]
        sep = next(d for d, s in enumerate(r["stages"]) if s[x] != s[y])
        assert sep == w["first_separation_depth"]
        word = distinguishing_task_word(f["outputs"], f["transitions"], r["stages"], x, y)
        assert word == w["word"]
        px = task_word_path(f["transitions"], x, word)
        py = task_word_path(f["transitions"], y, word)
        assert f["outputs"][px[-1]] != f["outputs"][py[-1]]
        for k in range(len(word)):   # no shorter prefix distinguishes, including the empty word
            assert f["outputs"][px[k]] == f["outputs"][py[k]]


def test_witness_none_and_empty():
    f = DECL["FX2_one_step"]
    r = minimal_task_partition(f["outputs"], f["transitions"])
    assert distinguishing_task_word(f["outputs"], f["transitions"], r["stages"], 2, 3) is None
    assert distinguishing_task_word(f["outputs"], f["transitions"], r["stages"], 0, 2) == []


def test_witness_rejects_bad_certificate():
    f = DECL["FX2_one_step"]
    r = minimal_task_partition(f["outputs"], f["transitions"])
    with pytest.raises(ValueError):
        distinguishing_task_word(f["outputs"], f["transitions"], r["stages"][:-1], 0, 1)
    with pytest.raises(ValueError):
        distinguishing_task_word(f["outputs"], f["transitions"], r["stages"], 0, 4)
    with pytest.raises(ValueError):
        distinguishing_task_word(f["outputs"], f["transitions"], [[0, 0, 1, 1], [0, 1, 1]], 0, 1)


def test_fx4_adding_a_nonfirst_action_refines():
    f = DECL["FX4_added_action"]
    for reg in ("a_only", "a_and_b"):
        e = f["regimes"][reg]
        r = minimal_task_partition(f["outputs"], e["transitions"])
        assert (r["alpha"], r["K"]) == (e["alpha"], e["K"])
    assert len(minimal_task_partition(f["outputs"], f["regimes"]["a_and_b"]["transitions"])["macro"]) == 2


def test_fx5_replay_composes_in_written_order():
    f = DECL["FX5_action_order"]
    for rp in f["replays"]:
        path = task_word_path(f["transitions"], rp["x"], rp["word"])
        assert path == rp["path"]
        assert f["outputs"][path[-1]] == rp["final_output"]


def test_fx7_counter():
    F = [[(x + 1) % 8 for x in range(8)]]
    r0 = minimal_task_partition([x & 1 for x in range(8)], F)
    assert (r0["K"], r0["alpha"]) == (DECL["FX7_counter3_bit0_auto"]["expect"]["K"],
                                      DECL["FX7_counter3_bit0_auto"]["expect"]["alpha"])
    r2 = minimal_task_partition([(x >> 2) & 1 for x in range(8)], F)
    assert r2["K"] == DECL["FX7_counter3_bit2_auto"]["expect"]["K"]
    seq = [(x >> 2) & 1 for x in range(8)]
    assert len({tuple(seq[i:] + seq[:i]) for i in range(8)}) == 8
    acts = counter_actions(3)
    e = DECL["FX7_counter3_bit0_intervention"]["expect"]
    assert len(acts) == e["n_actions"]
    ri = minimal_task_partition([x & 1 for x in range(8)], acts)
    assert (ri["K"], ri["alpha"]) == (e["K"], e["alpha"])


def test_fx8_rule150_parity_and_reset():
    T = rule150_ring4()
    h = parity(16)
    assert all(h[T[x]] == h[x] for x in range(16))
    assert minimal_task_partition(h, [T])["K"] == DECL["FX8_rule150_ring4_auto"]["expect"]["K"]
    reset0 = [T[x & ~1] for x in range(16)]
    e = DECL["FX8_rule150_ring4_reset0"]["expect"]
    r = minimal_task_partition(h, [T, reset0])
    assert r["K"] > e["K_greater_than"]
    p = e["pair"]
    word = distinguishing_task_word(h, [T, reset0], r["stages"], p["x"], p["y"])
    assert word == p["word"]
    assert [h[task_word_path([T, reset0], s, word)[-1]] for s in (p["x"], p["y"])] == p["outputs_after"]


def test_sup1_refining_is_not_closure():
    f = DECL["SUP1_refines_but_not_closed"]
    r = minimal_task_partition(f["outputs"], f["transitions"])
    assert (r["alpha"], r["K"]) == (f["expect"]["alpha_star"], f["expect"]["K"])
    cand = f["candidate"]
    assert induced_map(cand, r["alpha"])[1] is None
    _, bad = induced_map(cand, [cand[f["transitions"][0][x]] for x in range(4)])
    assert list(bad) == f["expect"]["closure_witness"]


def _malformed(v, n):
    if v == "GENERATOR":
        return (i % 2 for i in range(n))
    if v == "GENERATOR_TABLE":
        return [(i for i in range(n))]
    return v


@pytest.mark.parametrize("case", DECL["FX10_malformed"]["reject_with_ValueError"], ids=lambda c: c["case"])
def test_fx10_malformed_rejected(case):
    outputs = _malformed(case["outputs"], 2)
    transitions = _malformed(case["transitions"], 2)
    with pytest.raises(ValueError):
        minimal_task_partition(outputs, transitions)


def test_fx10_nonbinary_labels_accepted():
    for c in DECL["FX10_malformed"]["accept"]:
        assert minimal_task_partition(c["outputs"], c["transitions"])["K"] == c["K"]


def test_strict_rounds_bound_and_monotone_counts():
    T = rule150_ring4()
    reset0 = [T[x & ~1] for x in range(16)]
    h = parity(16)
    r = minimal_task_partition(h, [T, reset0])
    counts = [max(s) + 1 for s in r["stages"]]
    assert all(a < b for a, b in zip(counts[:-2], counts[1:-1]))
    assert r["strict_rounds"] <= 16 - counts[0]
    for d, up in enumerate(r["coarsening"]):
        assert all(up[r["stages"][d + 1][x]] == r["stages"][d][x] for x in range(16))


# --- task_word_path: the full public replay contract (review R2) ---------------------

SWAP01, SWAP12 = [1, 0, 2], [0, 2, 1]


@pytest.mark.parametrize("transitions, x, word", [
    ([[3, 0]], 0, [0]),                 # review: target 3 outside a two-state domain
    ([[0]], 0, None),                   # review: word is not a container
    ([3], 0, []),                       # review: a table that is not a list or tuple
    ([], 0, []),                        # no tables
    ([[]], 0, []),                      # empty table
    ([[0, 1], [0]], 0, [0]),            # ragged tables
    ([[0, -1]], 0, [0]),                # negative target
    ([[0, 2]], 0, [0]),                 # out-of-range target
    ([[0, 1], [0, 5]], 0, []),          # invalid unused table, empty word
    ([[0, 1], [0, True]], 0, [0]),      # bool target in an unused table
    ([[0, 1]], True, []),               # bool state
    ([[0, 1]], 2, []),                  # state out of range
    ([[0, 1]], 0, [True]),              # bool action
    ([[0, 1]], 0, "0"),                 # string word
    ([[0, 1]], 0, {0}),                 # set word
    ([[0, 1]], 0, iter([0])),           # iterator word
    ([[0, 1]], 0, [0, 0, 0, 1]),        # invalid action late in the word
    ([[0, 1]], 0, [0, 0, 1.0]),         # non-integer action late in the word
    (iter([[0, 1]]), 0, []),            # generator of tables
])
def test_task_word_path_rejects_malformed_calls(transitions, x, word):
    with pytest.raises(ValueError):
        task_word_path(transitions, x, word)


def test_task_word_path_does_not_consume_a_generator_word():
    def gen():
        consumed.append(True)
        yield 0
    consumed = []
    with pytest.raises(ValueError):
        task_word_path([[0, 1]], 0, gen())
    assert consumed == []


def test_task_word_path_valid_calls():
    assert task_word_path([[1, 0]], 1, []) == [1]
    assert task_word_path(([1, 0],), 0, (0, 0, 0)) == [0, 1, 0, 1]
    # noncommuting actions are applied in written order, first letter first
    assert task_word_path([SWAP01, SWAP12], 0, [0, 1]) == [0, 1, 2]
    assert task_word_path([SWAP01, SWAP12], 0, [1, 0]) == [0, 0, 1]
