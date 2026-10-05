"""The whole reporting pipeline (rows -> summaries -> flags -> decision) on copies of the
retained a1 job records, complete and with records made unavailable or invalid IN MEMORY.

Nothing on disk is written or altered: the retained records are read once and every
scenario mutates a deep copy. Unavailable evidence (missing, timeout, worker error,
graph-limited translation) must give INCOMPLETE with intended/available denominators,
never a KeyError or a zero gain; invalid evidence (wrong decode, source mismatch, B0
mismatch, reference not reproduced, D1 problem) must give INVALID, even when records
are also missing.
"""
from __future__ import annotations

import copy
import json

import pytest

from search_diagnosis import analysis as A
from search_diagnosis import common as K
from search_diagnosis.report import build

pytestmark = pytest.mark.skipif(not (K.RUN_DIR / "jobs").is_dir(),
                                reason="retained search-diagnosis-v1-r1 records not present")


@pytest.fixture(scope="module")
def saved():
    d2ids = K.section_ids("D2")
    ids = {"targets": d2ids["targets"], "controls": d2ids["controls"],
           "d4": K.section_ids("D4")["targets"]}
    d1 = K.RUN_DIR / "d1"
    return {"rec2": A.load_records("D2", sorted(ids["targets"] + ids["controls"]), ("B0", "B8")),
            "rec3": A.load_records("D3", ids["targets"], ("D3",)),
            "rec4": A.load_records("D4", ids["d4"], ("D4",)),
            "d1": json.loads((d1 / "d1_cases.json").read_text()),
            "d1t": json.loads((d1 / "d1_tables.json").read_text()),
            "refs": K.references(), "ids": ids,
            "a1_numbers": json.loads((K.RUN_DIR / "analysis/key_numbers.json").read_text()),
            "a1_flags": json.loads((K.RUN_DIR / "analysis/flags.json").read_text())}


def run(saved, mutate=None, d1_problems=0):
    rec = {k: copy.deepcopy(saved[k]) for k in ("rec2", "rec3", "rec4")}
    if mutate:
        mutate(rec, saved)
    return build(rec["rec2"], rec["rec3"], rec["rec4"], saved["d1"], saved["d1t"],
                 d1_problems, saved["refs"], saved["ids"])


def first_losing_translated_winner(saved, identical_bytes=True):
    """A D4 string whose portfolio winner is a translated method, HID loses and H == T."""
    for cid in saved["ids"]["d4"]:
        rows = K.saved_rows(cid)
        m = rows["baseline_best"]["selected_method"]
        r = saved["rec4"][(cid, "D4")]
        if m in ("period", "pair_grammar") and \
                rows["hid_full"]["archive_bits"] > rows["baseline_best"]["archive_bits"] and \
                r["info"][m]["translated_bits"] == rows["hid_full"]["archive_bits"] and \
                (r["archives"][m]["sha256"] == rows["hid_full"]["archive_sha256"]) == identical_bytes:
            return cid, m
    raise AssertionError("no such string")


# --------------------------------------------------------------------------- complete


def test_complete_run_keeps_every_a1_number(saved):
    b = run(saved)
    dec, kn, old = b["decision"], b["key_numbers"], saved["a1_numbers"]
    assert dec["recommendation"] == "BOTH_SEPARATELY" and dec["valid"] and dec["complete"]
    renamed = {"d3_B0_cut_location"}
    for k, v in old.items():
        if k not in renamed:
            assert kn[k] == v, k
    prox = kn["d3_returned_B0_cut_proximity"]
    assert (prox["supplied_cut_with_returned_B0_cut_within_8_bits"],
            prox["supplied_cut_without_returned_B0_cut_within_8_bits"], prox["strings"]) == \
        (old["d3_B0_cut_location"]["supplied_cut_with_B0_cut_within_8_bits"],
         old["d3_B0_cut_location"]["supplied_cut_without"], 68)
    # R1: equal length is not equal bytes -- 282 = 261 identical + 21 different
    assert (kn["d4_hid_loses_H_eq_T"], kn["d4_hid_loses_H_eq_T_identical_bytes"],
            kn["d4_hid_loses_H_eq_T_different_bytes"]) == (282, 261, 21)
    assert kn["d4_hid_loses_translation_unavailable"] == 0
    assert b["flags"]["evidence"]["complete"] and not b["flags"]["evidence"]["invalid"]["any"]


def test_complete_run_flag_tables_match_a1(saved):
    f, old = run(saved)["flags"], saved["a1_flags"]
    for k in ("budget_opportunity_observed", "missed_baseline_structure_observed",
              "proposal_representation_penalty_observed"):
        assert f[k]["value"] == old[k]["value"]
    for c, v in old["restricted_path_barrier_observed"]["by_cell"].items():
        new = dict(f["restricted_path_barrier_observed"]["by_cell"][c])
        assert new.pop("available") == v["strings"] and new == v, c
    dec = f["d4_loss_decomposition_where_portfolio_winner_was_translated"]
    for c, v in old["d4_loss_decomposition_where_portfolio_winner_was_translated"]["by_cell"].items():
        assert {k: dec["by_cell"][c][k] for k in v} == v, c


# --------------------------------------------------------------------------- unavailable


def test_missing_d2_control_b8_is_incomplete_not_keyerror(saved):
    cid = saved["ids"]["controls"][0]

    def m(rec, s):
        rec["rec2"][(cid, "B8")] = None
    b = run(saved, m)
    f = b["flags"]["budget_opportunity_observed"]["control_behaviour"]
    assert b["decision"]["recommendation"] == "INCOMPLETE"
    assert b["decision"]["search_signal"] is None and b["decision"]["representation_signal"] is None
    assert (f["comparable_controls"], f["control_strings"], f["B8_differs_from_B0"]) == (31, 32, 0)
    assert b["flags"]["evidence"]["unavailable"]["D2"] == {"missing": 1}


def test_d2_target_timeout_keeps_cell_partial_never_zero(saved):
    cid = "stress-S02-4096-4001-ragged"            # the one B8 witness

    def m(rec, s):
        r = rec["rec2"][(cid, "B8")]
        r.update(status="timeout", info=None, archives={}, exception="worker exceeded 30.0 s")
    b = run(saved, m)
    row = b["d2_rows"][cid]
    assert row["B8_status"] == "timeout" and "opportunity_per_input_bit" not in row
    cellv = b["d2_summary"]["targets"]["opportunity"]["stress|S02|4096"]
    assert cellv["mean"] is None and cellv["complete_units"] == 7 and cellv["units"] == 8
    assert b["d2_summary"]["targets"]["equal_cell_mean_opportunity"] is None
    kn = b["key_numbers"]
    assert kn["d2_completed_B8_targets"] == 175 and kn["d2_B8_witnesses"] == []
    assert kn["d2_partial_cells"] == ["stress|S02|4096"]
    assert b["decision"]["recommendation"] == "INCOMPLETE"


@pytest.mark.parametrize("status", ["timeout", "error", "rss_limit", "not_run"])
def test_d3_unavailable_record_is_partial(saved, status):
    cid = saved["ids"]["targets"][0]

    def m(rec, s):
        rec["rec3"][(cid, "D3")].update(status=status, info=None, archives={},
                                         exception=None if status == "not_run" else status)
    b = run(saved, m)
    f = b["flags"]["restricted_path_barrier_observed"]
    cell = K.parse_case_id(cid)["cell"]
    assert f["denominator"]["strings"] == 176 and f["denominator"]["available_strings"] == 175
    assert f["by_cell"][cell][f"unavailable_{status}"] == 1
    assert f["by_cell"][cell]["strings"] == f["by_cell"][cell]["available"] + 1
    assert b["decision"]["recommendation"] == "INCOMPLETE"
    assert b["key_numbers"]["d3_available_strings"] == 175


def test_d3_missing_record_is_partial(saved):
    cid = saved["ids"]["targets"][-1]

    def m(rec, s):
        rec["rec3"][(cid, "D3")] = None
    b = run(saved, m)
    assert b["flags"]["evidence"]["unavailable"]["D3"] == {"missing": 1}
    assert b["decision"]["recommendation"] == "INCOMPLETE"


def test_d4_graph_limit_of_portfolio_winner_is_unavailable_not_H_eq_T(saved):
    cid, meth = first_losing_translated_winner(saved)

    def m(rec, s):
        info = rec["rec4"][(cid, "D4")]["info"][meth]
        for k in ("translated_bits", "raw_clipped_bits", "translated_buckets"):
            info.pop(k, None)
        info["status"] = "unavailable_graph_limit"
    b = run(saved, m)
    kn = b["key_numbers"]
    assert kn["d4_hid_loses"] == 367 and kn["d4_hid_loses_translation_unavailable"] == 1
    assert kn["d4_hid_loses_H_eq_T"] == 281 and kn["d4_hid_loses_H_eq_T_identical_bytes"] == 260
    assert kn["d4_admissible"][meth] == 575 and kn["d4_unavailable"][meth] == 1
    assert b["flags"]["evidence"]["unavailable"]["D4_conversions"] == {"unavailable_graph_limit": 1}
    assert b["decision"]["recommendation"] == "INCOMPLETE"


def test_d4_missing_job_removes_both_conversions(saved):
    cid = saved["ids"]["d4"][0]

    def m(rec, s):
        rec["rec4"][(cid, "D4")] = None
    b = run(saved, m)
    assert b["key_numbers"]["d4_unavailable"] == {"period": 1, "pair_grammar": 1}
    assert b["flags"]["evidence"]["unavailable"]["D4_conversions"] == {"missing": 2}
    assert b["decision"]["recommendation"] == "INCOMPLETE"


# --------------------------------------------------------------------------- invalid


def test_b0_deterministic_mismatch_is_invalid(saved):
    cid = saved["ids"]["targets"][0]

    def m(rec, s):
        rec["rec2"][(cid, "B0")]["info"]["archive_bits"] += 8
    b = run(saved, m)
    assert b["decision"]["recommendation"] == "INVALID"
    assert b["decision"]["gates"]["B0_deterministic_mismatches"] == 1


def test_reference_not_reproduced_is_invalid(saved):
    cid = saved["ids"]["targets"][0]

    def m(rec, s):
        full = sorted(s["refs"][cid]["cuts"])
        sub = next(x for x in rec["rec3"][(cid, "D3")]["info"]["subsets"] if x["subset"] == full)
        sub["archive_sha256"] = "0" * 64
    b = run(saved, m)
    assert b["decision"]["recommendation"] == "INVALID"
    assert b["decision"]["gates"]["references_not_reproduced"] == [cid]


def test_wrong_decode_is_invalid_not_unavailable(saved):
    cid = saved["ids"]["d4"][0]

    def m(rec, s):
        rec["rec4"][(cid, "D4")].update(status="error", exception="wrong_decode:period")
    b = run(saved, m)
    ev = b["flags"]["evidence"]
    assert ev["invalid"]["records"]["D4"] == [f"{cid}:invalid_decode"]
    assert ev["unavailable"]["D4_jobs"] == {}
    assert b["decision"]["recommendation"] == "INVALID"


def test_source_mismatch_is_invalid(saved):
    cid = saved["ids"]["controls"][0]

    def m(rec, s):
        rec["rec2"][(cid, "B8")]["input_sha256"] = "f" * 64
    b = run(saved, m)
    assert b["flags"]["evidence"]["invalid"]["records"]["D2"] == [f"{cid}.B8:invalid_source"]
    assert b["decision"]["recommendation"] == "INVALID"


def test_invalid_takes_precedence_over_missing(saved):
    t = saved["ids"]["targets"]

    def m(rec, s):
        rec["rec3"][(t[0], "D3")] = None
        rec["rec2"][(t[1], "B0")]["info"]["archive_bits"] += 8
    b = run(saved, m)
    assert b["decision"]["recommendation"] == "INVALID"
    assert b["flags"]["evidence"]["unavailable"]["D3"] == {"missing": 1}


def test_d1_problem_is_invalid(saved):
    assert run(saved, d1_problems=1)["decision"]["recommendation"] == "INVALID"
