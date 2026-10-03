"""Runner: freeze refusal, resume refusal on mismatched hashes, worker isolation."""
from __future__ import annotations

import json

import pytest

from hierarchy import benchmark as B
from hierarchy.corpus import Case


def _case(bits="0110" * 10):
    return Case("development-F01-256-0000-base", "development", "F01", 256, 0, False, bits)


def test_worker_runs_isolated_and_rows_are_complete(tmp_path):
    c = _case()
    stats = B.run_cases([c], tmp_path, "dev-test", "development-unfrozen", False, lambda m: None)
    assert stats["done"] == 1
    rows = json.loads(B.case_rows_path(tmp_path, c).read_text())
    assert [r["method"] for r in rows] == list(B.ALL_METHODS)
    assert all(r["status"] == "ok" and r["decode_ok"] for r in rows)
    best = rows[-1]
    cons = [r["archive_bits"] for r in rows if r["method"] in B.BASELINE_METHODS]
    assert best["archive_bits"] == min(cons)
    for r in rows:
        assert (tmp_path / r["archive_path"]).read_bytes()
        assert r["peak_rss_bytes"] > 0 and r["worker_wall_ns"] > 0
    assert B.case_is_complete(tmp_path, c, "development-unfrozen")


def test_resume_refuses_mismatched_hashes_and_skips_intact_cases(tmp_path):
    c = _case()
    B.run_cases([c], tmp_path, "dev-test", "h1", False, lambda m: None)
    s = B.run_cases([c], tmp_path, "dev-test", "h1", True, lambda m: None)
    assert s["skipped"] == 1 and s["done"] == 0
    with pytest.raises(RuntimeError, match="different freeze or input hash"):
        B.run_cases([c], tmp_path, "dev-test", "h2", True, lambda m: None)
    other = _case("1111" * 10)
    with pytest.raises(RuntimeError):
        B.case_is_complete(tmp_path, other, "h1")
    with pytest.raises(RuntimeError, match="use --resume"):
        B.run_cases([c], tmp_path, "dev-test", "h1", False, lambda m: None)


def test_corrupted_archive_makes_a_case_incomplete(tmp_path):
    c = _case()
    B.run_cases([c], tmp_path, "dev-test", "h1", False, lambda m: None)
    rows = json.loads(B.case_rows_path(tmp_path, c).read_text())
    p = tmp_path / rows[0]["archive_path"]
    p.write_bytes(p.read_bytes() + b"\x00")
    assert not B.case_is_complete(tmp_path, c, "h1")


def test_timeout_becomes_an_explicit_fallback_row(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "WALL_LIMIT_S", 0.0)
    monkeypatch.setattr(B, "ENCODE_METHODS", ("hid_full", "raw"))
    c = _case()
    job = B._Job(c, "hid_full", tmp_path)
    while not job.poll(0.0):
        pass
    row, archive = B._job_row(job, "dev-test", "h", 120)
    assert row["status"] == "timeout_raw" and row["decode_ok"] is True
    assert archive[4] == 0                       # raw fallback archive, labelled
    job = B._Job(c, "lzma", tmp_path)
    while not job.poll(0.0):
        pass
    row, _ = B._job_row(job, "dev-test", "h", 120)
    assert row["status"] == "censored_timeout"


def test_freeze_refuses_after_rows_exist(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "run_dir", lambda rid: tmp_path / rid)
    (tmp_path / "x" / "rows").mkdir(parents=True)
    with pytest.raises(RuntimeError, match="refusing to freeze"):
        B.write_freeze("x")


def test_environment_check_compares_only_scientific_fields_and_never_matches_missing():
    fr = B.environment()
    assert B.check_environment(fr, "benchmark", dict(fr)) == []
    informational = dict(fr, cpu="x", platform="y", ram_bytes=1, pytest_version="0",
                         matplotlib_version="0", cpu_count=1, machine="z")
    for purpose in B.ENVIRONMENT_REQUIRED:
        assert B.check_environment(fr, purpose, informational) == []
    p = B.check_environment(fr, "benchmark", dict(fr, zlib_runtime_version="9.9.9"))
    assert len(p) == 1 and "zlib_runtime_version" in p[0] and "re-freeze" in p[0]
    no_field = {k: v for k, v in fr.items() if k != "lzma_liblzma"}
    assert "records no value" in B.check_environment(no_field, "benchmark", fr)[0]
    assert "records no value" in B.check_environment(dict(fr, lzma_liblzma=None), "benchmark", fr)[0]
    assert "provides none" in B.check_environment(fr, "diagnostics", dict(fr, pybdm_version=None))[0]
    assert "numpy_version" in B.check_environment(fr, "report", dict(fr, numpy_version="0"))[0]
    assert B.check_environment(fr, "benchmark", dict(fr, numpy_version="0")) == []
