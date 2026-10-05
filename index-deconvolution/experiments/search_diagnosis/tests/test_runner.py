"""The diagnostic runner through real worker processes: status propagation, resume
identity and explicit not_run records. Writes only below pytest's tmp_path."""
from __future__ import annotations

import hashlib
import json
import sys

import pytest

from search_diagnosis import runner as R
from search_diagnosis.common import Case


def case(bits: str, cid: str = "confirmation-F12-256-3000-base") -> Case:
    return Case(cid, bits, hashlib.sha256(bits.encode()).hexdigest())


class SleepJob(R.DiagJob):
    def worker_argv(self, method):
        return [sys.executable, "-S", "-c", "import time; time.sleep(30)"]


class Expired:
    def expired(self):
        return True

    def save(self):
        pass


def rec(d, section, cid, kind):
    return json.loads(R.record_path(d, section, cid, kind).read_text())


def test_ok_record_with_archive_and_decode(tmp_path):
    c = case("0" * 100 + "1" * 100)
    stats = R.run_jobs([(c, "B0", {})], "D2", "id-1", "a1", d=tmp_path, log=lambda s: None)
    r = rec(tmp_path, "D2", c.case_id, "B0")
    assert stats["done"] == 1 and r["status"] == "ok"
    a = r["archives"]["output"]
    assert a["decode_ok"] and (tmp_path / a["path"]).exists()
    assert r["identity_sha256"] == "id-1" and r["input_sha256"] == c.input_sha256
    assert r["peak_rss_bytes"] > 0 and r["worker_wall_ns"] > 0


def test_timeout_is_an_explicit_record(tmp_path):
    c = case("01" * 50)
    R.run_jobs([(c, "B0", {})], "D2", "id-1", "a1", d=tmp_path, job_class=SleepJob,
               wall_limit=0.5, log=lambda s: None)
    r = rec(tmp_path, "D2", c.case_id, "B0")
    assert r["status"] == "timeout" and r["archives"] == {} and r["info"] is None


def test_rss_breach_uses_the_real_watchdog(tmp_path):
    c = case("01" * 50)
    R.run_jobs([(c, "B8", {})], "D2", "id-1", "a1", d=tmp_path, rss_limit=1 << 20,
               log=lambda s: None)
    r = rec(tmp_path, "D2", c.case_id, "B8")
    assert r["status"] == "rss_limit" and r["exit"] == R.RSS_EXIT


def test_worker_exception_is_an_error_record(tmp_path):
    c = case("01" * 50)
    R.run_jobs([(c, "D3", {"cuts": [0, 10]})], "D3", "id-1", "a1", d=tmp_path,
               log=lambda s: None)
    r = rec(tmp_path, "D3", c.case_id, "D3")
    assert r["status"] == "error" and "ValueError" in r["exception"]
    assert (tmp_path / r["stderr_log"]).exists()


def test_boundary_job_refuses_parameters(tmp_path):
    c = case("01" * 50)
    R.run_jobs([(c, "B0", {"cuts": [10]})], "D2", "id-1", "a1", d=tmp_path,
               log=lambda s: None)
    assert rec(tmp_path, "D2", c.case_id, "B0")["status"] == "error"


def test_resume_skips_identical_and_refuses_changed_identity(tmp_path):
    c = case("0" * 64 + "1" * 64)
    job = [(c, "B0", {})]
    R.run_jobs(job, "D2", "id-1", "a1", d=tmp_path, log=lambda s: None)
    before = R.record_path(tmp_path, "D2", c.case_id, "B0").read_bytes()
    stats = R.run_jobs(job, "D2", "id-1", "a1", d=tmp_path, log=lambda s: None)
    assert stats == {"done": 0, "skipped": 1, "not_run": 0, "non_ok": 0}
    assert R.record_path(tmp_path, "D2", c.case_id, "B0").read_bytes() == before
    with pytest.raises(RuntimeError, match="different identity"):
        R.run_jobs(job, "D2", "id-2", "a2", d=tmp_path, log=lambda s: None)
    changed = [(case("1" * 128), "B0", {})]                  # same id, different input
    with pytest.raises(RuntimeError):
        R.run_jobs(changed, "D2", "id-1", "a1", d=tmp_path, log=lambda s: None)


def test_exhausted_budget_writes_not_run_and_resume_completes(tmp_path):
    cs = [case("01" * 40, "confirmation-F12-256-3000-base"),
          case("10" * 40, "confirmation-F12-256-3000-ragged")]
    jobs = [(c, "B0", {}) for c in cs]
    stats = R.run_jobs(jobs, "D2", "id-1", "a1", d=tmp_path, budget=Expired(),
                       log=lambda s: None)
    assert stats["not_run"] == 2 and stats["done"] == 0
    assert {rec(tmp_path, "D2", c.case_id, "B0")["status"] for c in cs} == {"not_run"}
    stats = R.run_jobs(jobs, "D2", "id-1", "a1", d=tmp_path, log=lambda s: None)
    assert stats["done"] == 2


def test_category_budget_is_durable_in_the_phase_ledger(tmp_path):
    R.charge("fixtures_development", "dev", 12.5, root=tmp_path)
    R.charge("diagnostic_jobs", "x", 1.0, root=tmp_path)
    assert R.used("fixtures_development", root=tmp_path) == 12.5
    assert R.used(root=tmp_path) == 13.5
