import copy
import hashlib
import json
import time

import pytest

from doppel_challenge import joint_study as joint
from doppel_challenge import joint_parallel as parallel
from doppel_challenge.io import read_json
from doppel_challenge.records import seal


@pytest.fixture
def manifest():
    return joint.make_manifest("pilot", sizes=(6,), families=("ring",), seeds=(100,), include_stress=False)


def reference(case):
    net = joint.Network(case["network_size"], case["cm"], case["dyn"], case["params"])
    rows = list(joint.iter_output_rows(joint.compile_repertoire_program(net)))
    return {"status": "completed", "owner": "Wolfram", "process_status": "normal_exit",
            "output_sha256": hashlib.sha256(bytes(b for row in rows for b in row)).hexdigest()}, rows


@pytest.mark.parametrize("fault", (None, "ids", "duplicate", "binary", "shape", "json", "timeout", "process"))
def test_batch_transport_is_exact_or_explicit_failure(manifest, monkeypatch, fault):
    cases = [task[1] for task in list(joint.tasks(manifest))[:2]]
    def run(*args, **kwargs):
        if fault == "timeout":
            raise parallel.subprocess.TimeoutExpired("kernel", 1)
        items = [{"id": joint.network_hash(c), "status": "completed", "rows": reference(c)[1]} for c in cases]
        if fault == "ids":
            items[0]["id"] = "unknown"
        if fault == "duplicate":
            items[1]["id"] = items[0]["id"]
        if fault == "binary":
            items[0]["rows"][0][0] = True  # bool is not an integer bit in the wire contract
        if fault == "shape":
            items[0]["rows"].pop()
        return parallel.subprocess.CompletedProcess([], 1 if fault == "process" else 0,
                    stdout="malformed" if fault == "json" else json.dumps(list(reversed(items))), stderr="failure")
    monkeypatch.setattr(parallel.subprocess, "run", run)
    result = parallel.wolfram_batch(cases)
    if fault is None:
        assert all(result[joint.network_hash(c)]["output_sha256"] == reference(c)[0]["output_sha256"] for c in cases)
    else:
        expected = {"timeout": "timeout", "process": "process_failure"}.get(fault, "malformed_payload")
        assert all(r["status"] == expected for r in result.values())


def test_real_batched_wolfram_equals_individual_reference():
    cases = [joint.bounded_network(f, n, 100)[0] for f, n in (("ring", 8), ("hub", 10))]
    result = parallel.wolfram_batch(cases, timeout_seconds=60)
    for case in cases:
        individual = joint.wolfram_reference(case, timeout_seconds=60)
        assert individual["status"] == "completed"
        assert result[joint.network_hash(case)]["output_sha256"] == individual["output_sha256"]


def test_pipeline_serial_parallel_digests_and_order(manifest, monkeypatch):
    jobs = list(joint.tasks(manifest))[:7]
    monkeypatch.setattr(joint, "run_worker", lambda c, t, m: joint.joint_worker(c))
    monkeypatch.setattr(parallel, "wolfram_batch", lambda cases, **kw: {joint.network_hash(c): reference(c)[0] for c in cases})
    serial = [parallel.finish_record(t, joint.joint_worker(t[1]), reference(t[1])[0], manifest) for t in jobs]
    rows, batches = parallel.pipeline(jobs, manifest, workers=3, batch_size=3, deadline=time.monotonic()+60)
    assert [r["scientific_digest"] for r in rows] == [r["scientific_digest"] for r in serial]
    assert [b["n_networks"] for b in batches] == [3, 3, 1]


def test_expired_pipeline_launches_nothing(manifest, monkeypatch):
    monkeypatch.setattr(joint, "run_worker", lambda *a: pytest.fail("expired worker launched"))
    rows, batches = parallel.pipeline(list(joint.tasks(manifest)), manifest, workers=2, batch_size=4, deadline=time.monotonic()-1)
    assert rows == [] and batches == []


def test_failed_batch_never_accepts_prefix(manifest, monkeypatch):
    jobs = list(joint.tasks(manifest))[:4]
    monkeypatch.setattr(joint, "run_worker", lambda c, t, m: joint.joint_worker(c))
    monkeypatch.setattr(parallel, "wolfram_batch", lambda cases, **kw: {joint.network_hash(c): {"status": "timeout"} for c in cases})
    rows, _ = parallel.pipeline(jobs, manifest, workers=2, batch_size=2, deadline=time.monotonic()+10)
    assert len(rows) == 2 and all(not r["accepted_validation"] for r in rows)


def test_selection_leaves_cpu_and_memory_headroom():
    trials = [{"workers": w, "elapsed_seconds": t, "peak_worker_rss_bytes": 100*1024**2, "passed": True}
              for w, t in ((8, 10.3), (16, 10), (24, 9.9))]
    assert parallel.choose_workers(trials, memory_budget_bytes=64*1024**3, cpu_count=28)["workers"] == 8
    trials[0]["passed"] = False
    assert parallel.choose_workers(trials, memory_budget_bytes=64*1024**3, cpu_count=28)["workers"] == 16
    with pytest.raises(ValueError):
        parallel.choose_workers(trials, memory_budget_bytes=1024, cpu_count=28)


def test_parallel_resume_preserves_records_and_profile(tmp_path, manifest, monkeypatch):
    monkeypatch.setattr(joint, "run_worker", lambda c, t, m: joint.joint_worker(c))
    monkeypatch.setattr(parallel, "wolfram_batch", lambda cases, **kw: {joint.network_hash(c): reference(c)[0] for c in cases})
    execution = seal({"provenance": manifest["provenance"], "workers": 2, "batch_size": 4})
    result = joint.run_stage(tmp_path, manifest, execution=execution)
    assert result["release_ready"]
    saved = {p.name: p.read_bytes() for p in (tmp_path / "pilot/networks").glob("*.json")}
    monkeypatch.setattr(joint, "run_worker", lambda *a: pytest.fail("resume recomputed accepted record"))
    assert joint.run_stage(tmp_path, manifest, execution=execution)["release_ready"]
    assert saved == {p.name: p.read_bytes() for p in (tmp_path / "pilot/networks").glob("*.json")}
    altered = seal({**execution, "workers": 3})
    with pytest.raises(ValueError, match="execution mismatch"):
        joint.run_stage(tmp_path, manifest, execution=altered)
