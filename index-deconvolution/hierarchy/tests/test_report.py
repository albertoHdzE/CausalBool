"""Analysis from rows: a hand-checked aggregate, verdict rules, BDM calibration."""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from hierarchy import report as R
from hierarchy import validation as V
from hierarchy.diagnostics import adaptive, holm


def _row(fam, bl, rep, ragged, method, bits, n, status="ok"):
    return {"split": "confirmation", "family": fam, "base_length": bl, "replicate": rep,
            "ragged": ragged, "method": method, "archive_bits": bits, "n_bits": n,
            "status": status, "case_id": V.case_id("confirmation", fam, bl, rep, ragged),
            "decode_ok": True, "archive_path": "x", "selected_method": "raw",
            "input_sha256": f"{fam}{bl}{rep}{ragged}", "encode_wall_ns": 1,
            "worker_wall_ns": 1, "peak_rss_bytes": 1, "stop_reason": "converged"}


def _design(savings):
    """Explicit fixture design: exactly the cells and replicates of ``savings``."""
    fams = sorted({f for f, _ in savings})
    bls = sorted({b for _, b in savings})
    reps = range(max(len(u) for u in savings.values()))
    return V.make_design({"confirmation": {"families": fams, "base_lengths": bls,
                                           "replicates": reps}},
                         ("hid_full", "baseline_best") + R.ABLATION_METHODS, ())


def _table(savings, status_best="ok"):
    """savings[(fam, bl)] = list of (base_saving_bits, ragged_saving_bits) per unit."""
    rows = []
    for (fam, bl), units in savings.items():
        for rep, pair in enumerate(units):
            for ragged, sav in zip((False, True), pair):
                n = bl + (3 if ragged else 0)
                rows.append(_row(fam, bl, rep, ragged, "hid_full", 1000, n))
                rows.append(_row(fam, bl, rep, ragged, "baseline_best", 1000 + sav, n,
                                 status_best if (rep == 0 and not ragged) else "ok"))
                for a in R.ABLATION_METHODS:
                    rows.append(_row(fam, bl, rep, ragged, a, 1000 + 8, n))
    return rows


def _fixture_validation(rows, valid=True):
    """Arithmetic fixture: rows indexed as validate_study would index them, with the
    engineering state given explicitly. Completeness is still decided from the design
    by the report's own population gate. Archive checks are tested in test_validation."""
    index = {}
    for r in rows:
        assert r["method"] not in index.setdefault(r["case_id"], {})
        index[r["case_id"]][r["method"]] = r
    return {"engineering_valid": valid, "complete": True, "_index": index,
            "invalid": [] if valid else ["fixture: invalid"], "incomplete": [],
            "censored": [], "duplicates": [], "unknown": [], "expected_rows": len(rows),
            "present_rows": len(rows), "archives_checked": 0, "distinct_archives_decoded": 0,
            "missing_units": {}, "missing_methods": {}, "status_counts": {}}


def _summ(savings, rows=None, valid=True):
    rows = _table(savings) if rows is None else rows
    return R.summarise(_fixture_validation(rows, valid), _design(savings), "confirmation")


def test_aggregate_matches_a_hand_computation():
    # Two cells. F01/100: units (+10,+10) and (+30,+30) bits -> per-bit unit means
    # 10/100 & 10/103 averaged, etc. Computed here by hand, then compared.
    sav = {("F01", 100): [(10, 10), (30, 30)], ("F02", 100): [(-20, -20), (0, 0)]}
    s = _summ(sav)

    def unit(a, b):
        return (a / 100 + b / 103) / 2
    cell1 = (unit(10, 10) + unit(30, 30)) / 2
    cell2 = (unit(-20, -20) + unit(0, 0)) / 2
    assert s["primary"]["estimate_mean_saving_per_input_bit"] == pytest.approx((cell1 + cell2) / 2)
    lo, hi = s["primary"]["ci95"]
    assert lo <= (cell1 + cell2) / 2 <= hi
    assert s["primary"]["cells"] == 2 and s["primary"]["units"] == 4
    assert s["primary"]["required_units"] == 4
    # ablation increments: +8 bits everywhere
    inc = s["ablations"]["hid_flat"]["incremental_gain_per_input_bit"]
    assert inc == pytest.approx(np.mean([8 / 100, 8 / 103]))
    assert s["ablations"]["hid_flat"]["component_advantage"] == "supported"


def test_verdicts_positive_negative_and_blocked_by_a_censored_baseline():
    pos = {("F01", 100): [(50, 50)] * 5, ("F04", 100): [(40, 41)] * 5}
    assert _summ(pos)["primary"]["verdict"] == "supported"
    neg = {("F01", 100): [(-50, -50)] * 5, ("F04", 100): [(-40, -41)] * 5}
    assert _summ(neg)["primary"]["verdict"] == "not_supported"
    for table in (pos, neg):
        blocked = _summ(table, _table(table, status_best="incomplete_constituents"))
        assert blocked["primary"]["verdict"] == "inconclusive"     # censoring beats either sign
        assert blocked["primary"]["units_missing"] == ["confirmation|F01|100|0",
                                                       "confirmation|F04|100|0"]
        assert "estimate_mean_saving_per_input_bit" not in blocked["primary"]
        assert blocked["primary"]["partial_diagnostic"]["label"].startswith("PARTIAL")


def test_invalid_engineering_blocks_every_claim_whatever_the_sign():
    for table in ({("F01", 100): [(50, 50)] * 5}, {("F01", 100): [(-50, -50)] * 5}):
        s = _summ(table, valid=False)
        assert s["primary"]["verdict"] == "not_assessed"
        assert s["primary"]["evidence_validity"] == "invalid"
        assert "ci95" not in s["primary"]
        assert {v["component_advantage"] for v in s["ablations"].values()} == {"not_assessed"}
        led = {c["id"]: c for c in R.claim_ledger(s, None, "x")}
        assert led["C1"]["status"] == "inconclusive" and led["C1"]["decision"] == "not_assessed"
        assert led["C2"]["status"] == "not_supported"


def test_verdict_function_applies_gates_before_the_interval():
    ok = {"engineering_valid": True, "complete": True, "censored_count": 0, "assessable": True}
    for ci in ((-.2, -.1), (.1, .2)):
        assert R.verdict(ci, dict(ok, engineering_valid=False, assessable=False)) == "not_assessed"
        assert R.verdict(ci, dict(ok, complete=False, assessable=False)) == "not_assessed"
        assert R.verdict(ci, dict(ok, censored_count=1)) == "inconclusive"
    assert R.verdict((-.2, -.1), ok) == "not_supported"
    assert R.verdict((.1, .2), ok) == "supported"
    assert R.verdict((-.1, .1), ok) == "inconclusive"


def test_population_is_the_declared_design_not_the_present_rows():
    # The design declares 2 cells x 5 units; keep ONE unit of F04 with all its methods.
    table = {("F01", 100): [(-50, -50)] * 5, ("F04", 100): [(40, 41)] * 5}
    rows = [r for r in _table(table) if r["family"] == "F04" and r["replicate"] == 0]
    s = _summ(table, rows)
    p = s["primary"]
    assert p["verdict"] == "not_assessed" and p["evidence_completeness"] == "incomplete"
    assert p["required_units"] == 10 and p["available_units"] == 1
    assert p["gate"]["missing_count"] == (20 - 2) * 2       # strings x (hid_full, baseline_best)
    assert p["partial_diagnostic"]["units"] == 1
    assert "estimate_mean_saving_per_input_bit" not in p
    assert s["status_counts"]  # computed from the design even with rows absent


def test_an_empty_population_is_never_complete():
    # a design with no structured family: the primary population is empty, not vacuously complete
    table = {("F07", 100): [(0, 0)] * 2}
    s = _summ(table)
    assert s["primary"]["verdict"] == "not_assessed"
    assert s["primary"]["gate"]["missing"][0].startswith("empty population")
    v = V.validate_study([], V.make_design({}, ("hid_full",), ()), run_dir=Path("."))
    assert not v["engineering_valid"] and not v["complete"]


def test_bootstrap_keeps_pairs_and_is_seeded():
    cells = {("F01", 1): np.array([[1.0], [3.0]]), ("F02", 1): np.array([[0.0], [0.0]])}
    a = R.stratified_bootstrap(cells, 2000, 33001)
    b = R.stratified_bootstrap(cells, 2000, 33001)
    assert np.array_equal(a, b)
    assert set(np.round(a[:, 0], 9)) <= {0.5, 1.0, 1.5}     # (mean of cell1)/2 only


def test_adaptive_p_is_symmetric_inclusive_and_never_zero():
    # Observed row 0 is the lowest in every configuration.
    m = [[0.0, 0.0]] + [[float(i), float(200 - i)] for i in range(1, 200)]
    a = adaptive(m)
    assert a["adaptive_p"] >= 1 / 200
    # all ties: p = 1
    t = adaptive([[1.0, 2.0]] * 200)
    assert t["adaptive_p"] == 1.0
    # a null row that is extreme in ONE configuration is also selected for: symmetric
    m2 = [[5.0, 5.0]] + [[0.0, 9.0]] + [[9.0, 9.0]] * 198
    assert adaptive(m2)["r_null_at_or_below"] >= 1


def test_holm_step_down():
    # thresholds .05/3, .05/2, .05/1: a rejects, b (0.03 > 0.025) stops the procedure
    h = holm({"a": 0.001, "b": 0.03, "c": 0.04})
    assert h["a"]["reject_at_0.05"] and not h["b"]["reject_at_0.05"]
    assert not h["c"]["reject_at_0.05"]
    assert h["b"]["holm_adjusted"] == pytest.approx(0.06)
    assert all(v["reject_at_0.05"] for v in holm({"a": 0.001, "b": 0.02, "c": 0.04}).values())
