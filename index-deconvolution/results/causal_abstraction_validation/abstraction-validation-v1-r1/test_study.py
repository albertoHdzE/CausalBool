"""Run-local tests of abstraction-validation-v1-r1 orchestration: status table,
coarse evaluation, fixtures FX-*, ragged partitions, timing, audit list.
STUDY_DIR selects the study module (the mutation runner points it at mutants)."""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.environ.get("STUDY_DIR", HERE))
sys.path.insert(1, os.path.join(HERE, *[".."] * 2, "..", "src"))

import pytest  # noqa: E402
import study as S  # noqa: E402

P, F, U = S.PASS, S.FAIL, S.UNKNOWN
DECL = json.load(open(os.path.join(HERE, "fixtures.json")))


@pytest.fixture(scope="module")
def m1():
    return S.Model("M1")


@pytest.fixture(scope="module")
def m2():
    return S.Model("M2")


def cand(n, **kw):
    return next(c for c in S.candidates(n) if all(c.get(k) == v for k, v in kw.items()))


# ------------------------------------------------------------------ declarations and counts

def test_counts_match_declarations():
    assert len(S.candidates(8)) == 135 and len(S.candidates(10)) == 141
    assert len(S.track_d_q(8)) == 42 and len(S.track_d_q(10)) == 52
    assert DECL["n_rows"] == 2730 and DECL["declared_D_pairs"] == 59312640
    assert sum(len(S.partition(w, o, 8)) for w in S.WIDTHS for o in range(w)) == 30
    assert sum(len(S.partition(w, o, 10)) for w in S.WIDTHS for o in range(w)) == 36
    rows = {S.row_id(m, c["id"], t) for m in S.MODEL_IDS for c in S.candidates(S.MODEL_N[m]) for t in S.TAUS}
    assert rows == set(range(2730))


def test_ragged_partition_kept():
    assert [ln for _, ln in S.partition(3, 1, 8)] == [1, 3, 3, 1]
    assert [ln for _, ln in S.partition(4, 3, 10)] == [3, 4, 3]


def test_audit_list():
    r = S.audit_rows()
    assert len(r) == len(set(r)) == 273 and min(r) == 0 and max(r) <= 2729
    counts = [sum(1 for x in r if x % 5 == k) for k in range(5)]
    assert counts == [55, 55, 55, 54, 54] == DECL["audit_tau_counts"]
    assert r == DECL["audit_rows"]


# ------------------------------------------------------------------ intervention timing

def test_reset_acts_before_the_macro_step(m2):
    q = {"op": "reset", "j": 0, "c": 1}
    assert m2.q_table(q, 1)[0] == 2          # reset 0 -> 1, then +1
    assert m2.q_table({"op": "flip", "j": 1, "c": None}, 2)[0] == 4


def test_knockout_active_throughout(m2):
    q = {"op": "knockout", "j": 0, "c": 0}
    # f_0 := 0 for both steps from x = 0: 0 -> 0 (bit0 forced 0, carry-free) -> 0
    assert m2.q_table(q, 2)[0] == 0
    assert m2.q_table({"op": "tick", "j": None, "c": None}, 1)[5] == 7


# ------------------------------------------------------------------ primary status (addendum 1)

def test_status_all_branches():
    st = lambda e2, e3: S.primary_status(e2, e3)["status"]
    assert st(F, {0: F, 1: P}) == "AUT-FAIL"
    assert st(U, {0: U, 1: F, 2: P}) == "NOT-FULL-INCOMPLETE"       # unknown E2 + failed intervention
    assert st(U, {0: U, 1: P}) == "INCOMPLETE"
    assert st(P, {0: P, 1: P, 2: F}) == "RESTRICTED"
    assert S.primary_status(P, {0: P, 1: P, 2: F, 3: U})["q_prime_lower_bound"] is True
    assert S.primary_status(P, {0: P, 1: P, 2: F})["q_prime_lower_bound"] is False
    assert st(P, {0: P, 1: F, 2: F}) == "AUT-ONLY"
    assert st(P, {0: P, 1: F, 2: U}) == "NOT-FULL-INCOMPLETE"
    assert st(P, {0: P, 1: P, 2: U}) == "INCOMPLETE"
    assert st(P, {0: P, 1: P, 2: P}) == "FULL"


def test_unknown_is_never_pass():
    assert S.primary_status(P, {0: P, 1: U})["status"] == "INCOMPLETE"
    assert S.primary_status(U, {0: U})["status"] == "INCOMPLETE"


def test_invalid_evidence_raises():
    with pytest.raises(ValueError):
        S.primary_status(P, {0: P, 1: None})
    with pytest.raises(ValueError):
        S.primary_status("MISSING", {0: P})


def test_control_flag_never_hides_missing_or_invalid():
    assert S.is_control(None, 256) is None                # missing E1 not inferred
    assert S.is_control(1, 256) is True and S.is_control(256, 256) is True
    assert S.display_label("INCOMPLETE", True) == "INCOMPLETE"
    assert S.display_label("NOT-FULL-INCOMPLETE", True) == "CHECKER-INVALID"
    assert S.display_label("RESTRICTED", True) == "CHECKER-INVALID"
    assert S.display_label("FULL", True) == "CONTROL"
    assert S.display_label("INCOMPLETE", None) == "INCOMPLETE"
    assert S.display_label("FULL", False) == "FULL"


def test_run_status_order():
    assert S.run_status(True, True, True) == "FAILED-RUN"
    assert S.run_status(False, True, True) == "CHECKER-INVALID"
    assert S.run_status(False, False, True) == "INCOMPLETE"
    assert S.run_status(False, False, False) == "COMPLETE"


# ------------------------------------------------------------------ coarse evaluation, missingness

def test_coarse_missing_and_struct_fail():
    sizes = {0: 2, 1: 2}
    maps = {0: {0: 1, 1: 0}, 1: None, 2: {0: 1, 1: 0}, 3: {0: 0, 1: 0}}
    r = S.evaluate_classes([[0, 2, 3], [1, 2]], maps, {0, 1, 2, 3}, sizes, 4)
    assert r["label"] == "COARSE-DISAGREE"
    m = r["classes"][0]["members"]
    assert m[0]["outcome"] == "AGREE" and m[1]["outcome"] == "DISAGREE"
    assert m[1]["macro_disagreements"] == 1 and m[1]["micro_mismatches"] == 2 and m[1]["witness_macro"] == 0
    assert r["classes"][1]["rep_state"] == "REP-NOEXIST"
    assert r["classes"][1]["members"][0]["outcome"] == "NOT-EVALUABLE"
    assert r["pairs_intended"] == 12 and r["pairs_inspected"] == 12 and r["pairs_evaluable"] == 8
    r2 = S.evaluate_classes([[0, 2], [1, 3]], maps, {0, 1, 2}, sizes, 4)   # q3 record absent
    assert r2["label"] == "COARSE-STRUCT-FAIL" and r2["counts"]["MISSING"] == 1
    r3 = S.evaluate_classes([[0, 2]], maps, {0}, sizes, 4)
    assert r3["label"] == "COARSE-INCOMPLETE" and r3["pairs_inspected"] == 0
    assert S.evaluate_classes([[0], [2]], maps, {0, 2}, sizes, 4)["label"] == "COARSE-NO-HOLDOUT"
    assert S.evaluate_classes([[0, 2]], maps, {0, 2}, sizes, 4)["label"] == "COARSE-HOLDS"


def test_missing_representative_is_not_substituted():
    maps = {0: {0: 0}, 1: {0: 0}, 2: {0: 0}}
    r = S.evaluate_classes([[0, 1, 2]], maps, {1, 2}, {0: 1}, 1)
    assert r["classes"][0]["rep"] == 0 and r["classes"][0]["rep_state"] == "MISSING"
    assert all(m["outcome"] == "MISSING" and m["micro_mismatches"] is None for m in r["classes"][0]["members"])


# ------------------------------------------------------------------ fixtures FX-*

def _maps(model, c, tau, qs):
    canon = S.canonical_partition([S.alpha_value(c, x, model.n) for x in range(model.N)])
    Q = S.track_d_q(model.n)
    return canon, {i: S.induced_map(canon, [canon[y] for y in model.q_table(Q[i], tau)])[0] for i in qs}


def _flip_idx(j, n=8):
    return 1 + 2 * n + j


def test_fx_r1a_beta_fine_singletons(m2):
    c = cand(8, family="F3", w=4, o=0, block=0)
    row = S.evaluate_row(m2, c, 1)
    assert row["beta_fine_all_singletons"] is True
    for j in range(4):
        assert row["E3"][_flip_idx(j)][1] == P
    fine = S.classes(S.track_d_q(8), S.coordinates(c, 8), S.beta_fine)
    assert all(len(k) == 1 for k in fine)


def test_fx_r1b_wrong_beta_disagrees_at_zero(m2):
    c = cand(8, family="F3", w=4, o=0, block=0)
    idx = [_flip_idx(j) for j in range(4)]
    canon, maps = _maps(m2, c, 1, idx)
    r = S.evaluate_classes([idx], maps, set(idx), S.fibre_sizes(canon), 256)
    assert r["label"] == "COARSE-DISAGREE"
    flip1 = r["classes"][0]["members"][0]
    assert flip1["outcome"] == "DISAGREE" and flip1["witness_macro"] == canon[0]
    assert maps[idx[0]][canon[0]] == canon[2] and maps[idx[1]][canon[0]] == canon[3]


def test_fx_r1c_not_masked_by_control(m2):
    c = cand(8, family="F1", w=4, o=0, g="val")
    idx = [_flip_idx(j) for j in range(4)]
    canon, maps = _maps(m2, c, 1, idx)
    r = S.evaluate_classes([idx], maps, set(idx), S.fibre_sizes(canon), 256)
    assert r["label"] == "COARSE-DISAGREE" and r["classes"][0]["members"][0]["witness_macro"] == canon[0]
    row = S.evaluate_row(m2, c, 1)
    assert row["display"] == "CONTROL" and row["coarse"] == {}     # val maps scored only under beta_fine
    assert S.alpha_value(c, 2, 8) == (2, 0) and S.alpha_value(c, 3, 8) == (3, 0)


def test_fx_rep_representative_failure(m1):
    c = cand(8, family="F1", w=2, o=0, g="par")
    row = S.evaluate_row(m1, c, 2)
    cls = row["coarse"]["H-COARSE"]["classes"]
    r00 = 1 + 2 * 0 + 0      # reset0_0
    r10 = 1 + 2 * 1 + 0      # reset1_0
    k = next(k for k in cls if k["rep"] == r00)
    assert k["rep_state"] == "REP-NOEXIST"
    mem = next(m for m in k["members"] if m["q"] == r10)
    assert mem["outcome"] == "NOT-EVALUABLE" and mem["reason"] == "representative has no induced map"
    assert mem["micro_mismatches"] is None and mem["own_e3"] == F
    assert row["E3"][r10][1] == F
    assert row["coarse"]["H-COARSE"]["label"] in ("COARSE-DISAGREE", "COARSE-STRUCT-FAIL")


def test_h_out_merges_only_out_of_block(m2):
    c = cand(8, family="F3", w=4, o=0, block=0)
    cls = S.classes(S.track_d_q(8), S.coordinates(c, 8), S.beta_out)
    Q = S.track_d_q(8)
    zero = cls[0]
    assert zero[0] == 0
    assert all(Q[i]["op"] != "tick" and (Q[i]["op"] == "id" or Q[i]["j"] >= 4) for i in zero)
    assert len(zero) == 1 + 8 + 4 + 8
    assert all(len(k) == 1 for k in cls[1:])


def test_h_coarse_f4_uses_level2(m1):
    c = cand(8, family="F4", w=2, o=0, g="par", o2=0)
    co = S.coordinates(c, 8)
    assert co[0][:2] == (0, 0) and co[3][:2] == (1, 1) and co[3][2] == 0 and co[4][2] == 1
    assert S.beta_fine({"op": "flip", "j": 2, "c": None}, co) != S.beta_fine({"op": "flip", "j": 3, "c": None}, co)
