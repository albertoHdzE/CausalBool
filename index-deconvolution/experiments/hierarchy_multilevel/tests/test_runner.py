"""Real-child fixtures: owner watchdog, checkpoints, failure isolation, status precedence,
deployment-cost attribution. Limits here are FIXTURE limits (tiny wall or RSS), not
observed 30 s / 1 GiB study breaches."""
from __future__ import annotations

import json
import time
from pathlib import Path

import pytest
from hierarchy import benchmark as B
from hierarchy.corpus import Case
from hierarchy.decode import decode_archive
from hierarchy.study import get_study
from hierarchy.wire import encode_literal

from hierarchy_multilevel import report as RP
from hierarchy_multilevel import runner as RN
from hierarchy_multilevel.tests import fixtures as F


def case(name: str) -> Case:
    return Case(f"fixture-{name}", "confirmation", "FX", 0, 0, False, F.bits(name))


def wait(job, wall=30.0):
    t0 = time.time()
    while not job.poll(wall):
        time.sleep(0.02)
        assert time.time() - t0 < 60
    return job


def a0_row(arc: bytes, wall_ns=123_456_789, rss=1000):
    return {"archive_sha256": RN.sha(arc), "archive_bits": 8 * len(arc),
            "worker_wall_ns": wall_ns, "peak_rss_bytes": rss}


@pytest.fixture(scope="module")
def owner_a0(tmp_path_factory):
    """A real A0 from the owner worker (search-v2 hid_full) on alternating_512."""
    d = tmp_path_factory.mktemp("a0")
    c = case("alternating_512")
    job = wait(B._Job(c, "hid_full", d, registry="search-v2"))
    row, arc = B._job_row(job, "fixture", "fixture", 8 * len(encode_literal(c.bits)),
                          get_study("search-v2"), 30.0)
    assert row["status"] == "ok" and decode_archive(arc) == c.bits
    p = d / "a0.isd"
    p.write_bytes(arc)
    return c, arc, p, row


def aug(tmp_path, c, a0: bytes, arm="A3", env=None, wall=None, rss=RN.RSS, lock="-", a0row=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "a0.isd"
    p.write_bytes(a0)
    job = RN.launch_aug(c, arm, tmp_path, p, lock, rss, env, wall)
    wait(job, wall or 30.0)
    return RN.finish_aug(job, tmp_path, "fixture-lock", a0, a0row or a0_row(a0))


def test_completed_job_and_deployment_cost_includes_a0(tmp_path):
    c = case("alternating_512")
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit)
    assert row["status"] == "ok" and row["validity"] == "valid" and row["search_complete"]
    assert row["archive_bits"] < 8 * len(lit) and row["selected"]["source"] == "augmentation"
    assert row["deployment_wall_ns"] == 123_456_789 + row["worker_wall_ns"]
    assert row["deployment_peak_rss_bytes"] >= row["peak_rss_bytes"]
    tr = json.loads((tmp_path / row["trace_path"]).read_text())
    assert RN.sha((tmp_path / row["trace_path"]).read_bytes()) == row["trace_sha256"]
    assert tr["selected"]["proposal"] == row["selected"]["proposal"]
    assert row["checkpoints"]["valid"] and not row["checkpoints"]["corrupt"]


def test_watchdog_timeout_keeps_parent_verified_checkpoint(tmp_path):
    c = case("alternating_512")
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit, env={"HML_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"}, wall=2.0)
    assert row["status"] == "watchdog_timeout_fallback" and row["validity"] == "valid"
    assert not row["search_complete"] and row["timed_out"]
    assert row["selected"]["source"] == "checkpoint" and row["selected"]["seq"] == 1
    assert row["archive_sha256"] == row["checkpoints"]["valid"][0]["archive_sha256"]
    assert row["archive_bits"] < 8 * len(lit) and row["decode_ok"]
    assert row["partial_views_path"]


def test_rss_watchdog_retains_real_baseline(tmp_path, owner_a0):
    c, arc, _, r0 = owner_a0
    row = aug(tmp_path, c, arc, rss=1 << 20,
              a0row=a0_row(arc, r0["worker_wall_ns"], r0["peak_rss_bytes"]))
    assert row["status"] == "watchdog_rss_fallback" and row["exit"] == B.RSS_EXIT
    assert row["selected"] == {"source": "A0"} and row["archive_sha256"] == RN.sha(arc)
    assert row["validity"] == "valid" and row["decode_ok"]
    assert row["deployment_wall_ns"] == r0["worker_wall_ns"] + row["worker_wall_ns"]


def test_crash_is_invalid_but_a0_preserved(tmp_path, owner_a0):
    c, arc, _, _ = owner_a0
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit, env={"HML_FIXTURE_CRASH_AFTER_CHECKPOINTS": "1"})
    assert row["status"] == "invalid_crash" and row["validity"] == "invalid"
    assert row["archive_sha256"] == RN.sha(lit)          # deployed output is the A0 given


def test_corrupt_checkpoint_is_invalid(tmp_path):
    c = case("alternating_512")
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit, env={"HML_FIXTURE_CORRUPT_CHECKPOINT": "1",
                                     "HML_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"}, wall=2.0)
    assert row["status"] == "invalid_checkpoint_corrupt" and row["validity"] == "invalid"
    assert row["checkpoints"]["corrupt"][0]["reason"] == "bytes_disagree_with_record"


def test_lock_mismatch_and_hooks_refused_under_lock(tmp_path):
    c = case("alternating_512")
    lit = encode_literal(c.bits)
    bad = tmp_path / "lock_bad.json"
    bad.write_text(json.dumps({"closure": {"index-deconvolution/hierarchy/model.py": "0" * 64}}))
    row = aug(tmp_path / "a", c, lit, lock=str(bad))
    assert row["status"] == "invalid_lock" and "LockMismatch" in row["exception"]
    good = tmp_path / "lock_empty.json"
    good.write_text(json.dumps({"closure": {}}))
    row = aug(tmp_path / "b", c, lit, lock=str(good), env={"HML_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"})
    assert row["status"] == "invalid_lock" and "fixture hook" in row["exception"]
    row = aug(tmp_path / "c", c, lit, lock=str(good))
    assert row["status"] == "ok"


def test_partial_writes_ignored_and_reported(tmp_path):
    x = F.bits("alternating_512")
    lit = encode_literal(x)
    ck = tmp_path / "ck"
    ck.mkdir()
    (ck / "ckpt_0001.json").write_text(json.dumps({"seq": 1, "archive_sha256": "0" * 64, "archive_bits": 8}))
    (ck / ".ckpt_0002.isd.tmp123").write_bytes(b"partial")
    (ck / "ckpt_0003.isd").write_bytes(lit)
    out = RN.read_checkpoints(ck, x, lit)
    assert out["best"] is None and out["valid"] == [] and out["corrupt"] == []
    assert out["partial"][0]["reason"] == "archive_missing"
    assert out["partial_tmp_files"] == [".ckpt_0002.isd.tmp123"]
    assert out["orphan_archives"] == ["ckpt_0003.isd"]


def test_resume_rejects_corrupt_or_foreign_rows(tmp_path):
    spec = {"case_id": "c1"}
    p = RN.aug_row_path(tmp_path, "c1", "A1")
    p.parent.mkdir(parents=True)
    p.write_text("{not json")
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "A1", "L")
    p.write_text(json.dumps({"lock_sha256": "other", "status": "ok"}))
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "A1", "L")


# ---------------------------------------------------------------------------
# status precedence through the reporting path
# ---------------------------------------------------------------------------

def _specs():
    return [{"case_id": f"c{f}{bl}{r}{v}", "family": f"F{f}", "base_length": bl, "replicate": r,
             "ragged": v, "n_bits": 100} for f in (1, 2) for bl in (10,) for r in (1, 2)
            for v in (False, True)]


def _rows(specs, a3_status="ok"):
    rows = {}
    for s in specs:
        rows[(s["case_id"], "A0")] = {"status": "ok", "decode_ok": True, "archive_bits": 80,
                                      "reproduction": {"reproduced": True}}
        for arm in RN.AUG_ARMS:
            rows[(s["case_id"], arm)] = {"status": "ok", "validity": "valid", "archive_bits": 72}
    return rows


def _refs(specs):
    return {s["case_id"]: {"problems": [], "methods": {"pair_grammar": {"archive_bits": 90}},
                           "portfolio": {"archive_bits": 60}} for s in specs}


def test_invalid_precedes_incomplete_and_disables_recommendation():
    specs = _specs()
    rows, refs = _rows(specs), _refs(specs)
    assert RP.evidence_state(specs, rows, refs)["state"] == "VALID_COMPLETE"
    rows[(specs[0]["case_id"], "A2")] = None                                 # missing
    st = RP.evidence_state(specs, rows, refs)
    assert st["state"] == "INCOMPLETE"
    assert RP.recommendation(st["state"], RP.bits_table(specs, rows, refs))["label"] is None
    rows[(specs[1]["case_id"], "A3")] = {"status": "invalid_crash", "validity": "invalid", "archive_bits": 80}
    st = RP.evidence_state(specs, rows, refs)
    assert st["state"] == "INVALID" and st["incomplete"]
    rows[(specs[2]["case_id"], "A1")] = {"status": "unavailable_baseline", "validity": "unavailable"}
    assert RP.evidence_state(specs, rows, refs)["state"] == "INVALID"


def test_missing_values_are_unavailable_not_zero():
    specs = _specs()
    rows, refs = _rows(specs), _refs(specs)
    rows[(specs[0]["case_id"], "A2")] = None
    bits = RP.bits_table(specs, rows, refs)
    assert bits[specs[0]["case_id"]]["A2"] is None
    con = RP.contrasts(specs, bits)["A2_vs_A0"]
    assert con["per_string"][specs[0]["case_id"]] is None
    assert con["aggregate"] is None                 # no reduced-population aggregate
    assert con["strings"]["unavailable"] == 1 and con["strings"]["available"] == len(specs) - 1
    full = RP.contrasts(specs, RP.bits_table(specs, _rows(specs), refs))["A2_vs_A0"]
    assert full["aggregate"] == pytest.approx(8 / 100) and full["denominators"]["cells"] == 2


def test_weighting_base_ragged_then_replicate_then_cells():
    specs = _specs()
    per = {s["case_id"]: 0.0 for s in specs}
    # one cell: replicate 1 base 1.0 ragged 0.0 -> 0.5; replicate 2 both 0 -> cell 0.25
    first = [s for s in specs if s["family"] == "F1"]
    per[first[0]["case_id"]] = 1.0
    ag = RP.aggregate(specs, per)
    assert ag["cells"]["F1-10"] == 0.25 and ag["cells"]["F2-10"] == 0.0
    assert ag["aggregate"] == 0.125


def test_recommendation_labels():
    b = {"x": {"A0": 10, "A2": 10, "A3": 10}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "NO_RETAINED_GAIN"
    b = {"x": {"A0": 10, "A2": 8, "A3": 8}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "NO_ADDED_LEVEL_GAIN"
    b = {"x": {"A0": 10, "A2": 9, "A3": 8}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "LEVEL_GAIN_OBSERVED"
    assert RP.recommendation("INVALID", b)["label"] is None


def test_unavailable_baseline_row(tmp_path):
    spec = {"case_id": "c1", "family": "F", "base_length": 1, "replicate": 1, "ragged": False,
            "n_bits": 4, "input_sha256": "0"}
    row = RN.unavailable_row(tmp_path, spec, "A2", "L", "a0_decode_mismatch")
    assert row["validity"] == "unavailable" and row["archive_bits"] is None
    assert json.loads(Path(RN.aug_row_path(tmp_path, "c1", "A2")).read_text())["status"] == "unavailable_baseline"
