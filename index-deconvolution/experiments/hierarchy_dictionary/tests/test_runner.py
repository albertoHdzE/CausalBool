"""Real-child fixtures: owner watchdog, checkpoints, failure isolation, status precedence,
deployment-cost attribution, resume identity, old-A3 import. Limits here are FIXTURE
limits (tiny wall or RSS), not observed 30 s / 1 GiB study breaches."""
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

from hierarchy_dictionary import report as RP
from hierarchy_dictionary import runner as RN
from hierarchy_dictionary.tests import fixtures as F


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
    """A real A0 from the owner worker (search-v2 hid_full) on complement_pair_512."""
    d = tmp_path_factory.mktemp("a0")
    c = case("complement_pair_512")
    job = wait(B._Job(c, "hid_full", d, registry="search-v2"))
    row, arc = B._job_row(job, "fixture", "fixture", 8 * len(encode_literal(c.bits)),
                          get_study("search-v2"), 30.0)
    assert row["status"] == "ok" and decode_archive(arc) == c.bits
    p = d / "a0.isd"
    p.write_bytes(arc)
    return c, arc, p, row


def aug(tmp_path, c, a0: bytes, arm="D2", env=None, wall=None, rss=RN.RSS, lock="-", a0row=None):
    tmp_path.mkdir(parents=True, exist_ok=True)
    p = tmp_path / "a0.isd"
    p.write_bytes(a0)
    job = RN.launch_aug(c, arm, tmp_path, p, lock, rss, env, wall)
    wait(job, wall or 30.0)
    return RN.finish_aug(job, tmp_path, "fixture-lock", a0, a0row or a0_row(a0))


def test_completed_job_and_deployment_cost_includes_a0(tmp_path):
    c = case("complement_pair_512")
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
    assert row["archive_sha256"] in row["candidate_archives"]
    for h in row["candidate_archives"]:                       # retained, content-addressed
        assert decode_archive((tmp_path / "archives" / h[:2] / f"{h}.isd").read_bytes()) == c.bits
    best = {m["best_sha256"] for v in tr["views"] for m in v.get("modes", []) if m["best_sha256"]}
    assert best <= set(row["candidate_archives"])


def test_watchdog_timeout_keeps_parent_verified_checkpoint(tmp_path):
    c = case("complement_pair_512")
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit, env={"HDD_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"}, wall=2.0)
    assert row["status"] == "watchdog_timeout_fallback" and row["validity"] == "valid"
    assert not row["search_complete"] and row["timed_out"]
    assert row["selected"]["source"] == "checkpoint" and row["selected"]["seq"] == 1
    assert row["archive_sha256"] == row["checkpoints"]["valid"][0]["archive_sha256"]
    assert row["archive_bits"] < 8 * len(lit) and row["decode_ok"]
    assert row["partial_views_path"]


def test_rss_watchdog_retains_real_owner_baseline(tmp_path, owner_a0):
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
    row = aug(tmp_path, c, lit, env={"HDD_FIXTURE_CRASH_AFTER_CHECKPOINTS": "1"})
    assert row["status"] == "invalid_crash" and row["validity"] == "invalid"
    assert row["archive_sha256"] == RN.sha(lit)


def test_corrupt_checkpoint_is_invalid(tmp_path):
    c = case("complement_pair_512")
    lit = encode_literal(c.bits)
    row = aug(tmp_path, c, lit, env={"HDD_FIXTURE_CORRUPT_CHECKPOINT": "1",
                                     "HDD_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"}, wall=2.0)
    assert row["status"] == "invalid_checkpoint_corrupt" and row["validity"] == "invalid"
    assert row["checkpoints"]["corrupt"][0]["reason"] == "bytes_disagree_with_record"


def test_unusable_baseline_is_invalid_not_success(tmp_path):
    c = case("complement_pair_512")
    row = aug(tmp_path, c, encode_literal(F.bits("random_1024")))
    # the worker refuses (exit 5); the parent's deployed fallback is that same unusable A0,
    # so the row also fails the parent decode check: INVALID either way, never a success
    assert "BaselineUnusable" in row["exception"] and row["exit"] == 5
    assert row["status"] == "invalid_decode_mismatch" and row["validity"] == "invalid"


def test_lock_mismatch_and_hooks_refused_under_lock(tmp_path):
    c = case("complement_pair_512")
    lit = encode_literal(c.bits)
    bad = tmp_path / "lock_bad.json"
    bad.write_text(json.dumps({"closure": {"index-deconvolution/hierarchy/model.py": "0" * 64}}))
    row = aug(tmp_path / "a", c, lit, lock=str(bad))
    assert row["status"] == "invalid_lock" and "LockMismatch" in row["exception"]
    bad2 = tmp_path / "lock_cfg.json"            # a non-Python configuration dependency
    bad2.write_text(json.dumps({"closure": {
        "index-deconvolution/protocols/hierarchy_dictionary_v1/contract.json": "1" * 64}}))
    row = aug(tmp_path / "a2", c, lit, lock=str(bad2))
    assert row["status"] == "invalid_lock"
    good = tmp_path / "lock_empty.json"
    good.write_text(json.dumps({"closure": {}}))
    row = aug(tmp_path / "b", c, lit, lock=str(good), env={"HDD_FIXTURE_STALL_AFTER_CHECKPOINTS": "1"})
    assert row["status"] == "invalid_lock" and "fixture hook" in row["exception"]
    row = aug(tmp_path / "c", c, lit, lock=str(good))
    assert row["status"] == "ok"


def test_partial_writes_ignored_and_reported(tmp_path):
    x = F.bits("complement_pair_512")
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


def test_resume_rejects_corrupt_missing_or_foreign_rows(tmp_path):
    spec = {"case_id": "c1"}
    p = RN.aug_row_path(tmp_path, "c1", "D1")
    p.parent.mkdir(parents=True)
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "D1", "L")       # missing
    p.write_text("{not json")
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "D1", "L")
    p.write_text(json.dumps({"lock_sha256": "other", "status": "ok"}))
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "D1", "L")
    p.write_text(json.dumps({"lock_sha256": "L", "status": "ok", "archive_path": "archives/xx.isd",
                             "archive_sha256": "0" * 64}))
    assert not RN.aug_row_valid_for_resume(tmp_path, spec, "D1", "L")       # archive missing
    a0p = RN.a0_row_path(tmp_path, "c1")
    a0p.write_text(json.dumps({"lock_sha256": "other"}))
    assert RN.a0_verified(tmp_path, spec, "0101", "L")[2] == "a0_row_other_lock"


def test_old_a3_import_detects_tampering(tmp_path):
    rec = next(iter(RN.old_a3_records().values()))
    x = decode_archive((RN.REPO / rec["archive_path"]).read_bytes())  # archive bytes only, no encoder
    good = RN.import_old_a3(rec, x)
    assert good["problems"] == [] and good["evaluated_view_proposals"]
    bad = RN.import_old_a3(dict(rec, trace_sha256="0" * 64), x)
    assert bad["problems"] == ["trace hash"]


# ---------------------------------------------------------------------------
# status precedence and absent values through the reporting path
# ---------------------------------------------------------------------------

def _specs():
    return [{"case_id": f"c{f}{bl}{r}{v}", "family": f"F{f}", "base_length": bl, "replicate": r,
             "ragged": v, "n_bits": 100} for f in (1, 2) for bl in (10,) for r in (1, 2)
            for v in (False, True)]


def _rows(specs, bits=(80, 80, 80, 80)):
    rows = {}
    for s in specs:
        rows[(s["case_id"], "A0")] = {"status": "ok", "decode_ok": True, "archive_bits": bits[0],
                                      "reproduction": {"reproduced": True}}
        for arm, b in zip(RN.AUG_ARMS, bits[1:]):
            rows[(s["case_id"], arm)] = {"status": "ok", "validity": "valid", "archive_bits": b}
    return rows


def _refs(specs):
    return {s["case_id"]: {"problems": [], "methods": {"pair_grammar": {"archive_bits": 90}},
                           "portfolio": {"archive_bits": 60}} for s in specs}


def _old(specs, problems=()):
    return {s["case_id"]: {"problems": list(problems), "archive_bits": 80} for s in specs}


def test_invalid_precedes_incomplete_and_disables_recommendation():
    specs = _specs()
    rows, refs, old = _rows(specs), _refs(specs), _old(specs)
    assert RP.evidence_state(specs, rows, refs, old)["state"] == "VALID_COMPLETE"
    rows[(specs[0]["case_id"], "D2")] = None                                 # missing
    st = RP.evidence_state(specs, rows, refs, old)
    assert st["state"] == "INCOMPLETE"
    assert RP.recommendation(st["state"], RP.bits_table(specs, rows, refs, old))["label"] is None
    rows[(specs[1]["case_id"], "D1")] = {"status": "invalid_crash", "validity": "invalid", "archive_bits": 80}
    st = RP.evidence_state(specs, rows, refs, old)
    assert st["state"] == "INVALID" and st["incomplete"]
    rows[(specs[2]["case_id"], "D0")] = {"status": "unavailable_baseline", "validity": "unavailable"}
    assert RP.evidence_state(specs, rows, refs, old)["state"] == "INVALID"
    rows = _rows(specs)
    assert RP.evidence_state(specs, rows, refs, _old(specs, ["trace hash"]))["state"] == "INVALID"
    del old[specs[3]["case_id"]]
    assert RP.evidence_state(specs, rows, refs, old)["state"] == "INCOMPLETE"


def test_missing_values_are_unavailable_not_zero():
    specs = _specs()
    rows, refs, old = _rows(specs, (80, 76, 76, 72)), _refs(specs), _old(specs)
    rows[(specs[0]["case_id"], "D2")] = None
    bits = RP.bits_table(specs, rows, refs, old)
    assert bits[specs[0]["case_id"]]["D2"] is None
    con = RP.contrasts(specs, bits)["D2_vs_A0"]
    assert con["per_string"][specs[0]["case_id"]] is None
    assert con["aggregate"] is None                 # no reduced-population aggregate
    assert con["strings"]["unavailable"] == 1 and con["strings"]["available"] == len(specs) - 1
    full = RP.contrasts(specs, RP.bits_table(specs, _rows(specs, (80, 76, 76, 72)), refs, old))
    assert full["D2_vs_A0"]["aggregate"] == pytest.approx(8 / 100)
    assert full["D2_vs_D1"]["aggregate"] == pytest.approx(4 / 100)
    assert full["D0_vs_oldA3"]["aggregate"] == pytest.approx(4 / 100)
    assert full["D2_vs_A0"]["denominators"] == {"strings": 8, "pairs": 4, "cells": 2}


def test_recommendation_labels_in_order():
    b = {"x": {"A0": 10, "D0": 10, "D1": 10, "D2": 10}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "NO_RETAINED_GAIN"
    b = {"x": {"A0": 10, "D0": 9, "D1": 9, "D2": 9}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "CONTROL_ONLY_GAIN"
    b = {"x": {"A0": 10, "D0": 10, "D1": 9, "D2": 9}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "PERIOD_GAIN_OBSERVED"
    b = {"x": {"A0": 10, "D0": 10, "D1": 9, "D2": 9}, "y": {"A0": 10, "D0": 10, "D1": 10, "D2": 9}}
    assert RP.recommendation("VALID_COMPLETE", b)["label"] == "RELATION_GAIN_OBSERVED"
    assert RP.recommendation("INVALID", b)["label"] is None
    assert RP.recommendation("INCOMPLETE", b)["label"] is None


def test_unavailable_baseline_row(tmp_path):
    spec = {"case_id": "c1", "family": "F", "base_length": 1, "replicate": 1, "ragged": False,
            "n_bits": 4, "input_sha256": "0"}
    row = RN.unavailable_row(tmp_path, spec, "D2", "L", "a0_decode_mismatch")
    assert row["validity"] == "unavailable" and row["archive_bits"] is None
    assert json.loads(Path(RN.aug_row_path(tmp_path, "c1", "D2")).read_text())["status"] == "unavailable_baseline"
