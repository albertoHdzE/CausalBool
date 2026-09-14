import copy
import hashlib
import json
from pathlib import Path

import pytest

from doppel_challenge import joint_study as joint
from doppel_challenge.io import atomic_write_json, read_json
from doppel_challenge.records import seal, scientific_digest


@pytest.fixture
def manifest():
    return joint.make_manifest("pilot", sizes=(6,), families=("ring",), seeds=(100,), include_stress=False)


@pytest.fixture
def valid_record(manifest):
    key, case, family = next(joint.tasks(manifest))
    row = joint.joint_worker(case)
    row.update(record_kind="joint_study_network", manifest_sha256=manifest["sha256"],
               network_sha256=key, network=joint.network_payload(case), family=family,
               wolfram_reference={"status": "completed", "output_sha256": row["compression"]["checked_output_sha256"]})
    return seal(row), case


@pytest.mark.parametrize("n", (8, 10, 12))
@pytest.mark.parametrize("family", joint.FAMILIES)
def test_bounded_construction_is_deterministic(n, family):
    first, audit = joint.bounded_network(family, n, 102)
    assert (first, audit) == joint.bounded_network(family, n, 102)
    assert all(1 <= sum(row) <= 5 for row in first["cm"])
    assert all(first["cm"][i][i] == 0 for i in range(n))
    original = [row[:] for row in audit["original_cm"]]
    for change in audit["construction_changes"]:
        assert change["operation"] == "remove"
        original[change["target"]][change["source"]] = 0
    assert original == first["cm"]
    for old, new in zip(audit["original_cm"], first["cm"]):
        if sum(old) <= 5:
            assert old == new


def test_frozen_resume_rejects_configuration_and_sources(tmp_path, monkeypatch):
    args = dict(sizes=(6,), families=("ring",), seeds=(100,), include_stress=False)
    m = joint.frozen_manifest(tmp_path, "pilot", **args)
    assert joint.frozen_manifest(tmp_path, "pilot", **args) == m
    with pytest.raises(ValueError, match="mismatch"):
        joint.frozen_manifest(tmp_path, "pilot", **{**args, "seeds": (101,)})
    monkeypatch.setattr(joint, "study_provenance", lambda: {"changed": True})
    with pytest.raises(ValueError, match="mismatch"):
        joint.frozen_manifest(tmp_path, "pilot", **args)


def test_manifest_denominator_and_identity(manifest):
    base = manifest["bases"][0]
    for kind, entries in base["catalogues"].items():
        assert entries[0]["perturbation_id"] == f"{kind}:identity"
        assert entries[0]["admissible"]
        assert len(entries) == len(joint.ball(base["network"]["cm"], 1, kind))
        assert len({e["perturbation_id"] for e in entries}) == len(entries)
    keys = [key for key, _, _ in joint.tasks(manifest)]
    assert len(set(keys)) == len(keys)
    assert keys.count(base["network_sha256"]) == 1


def test_integration_roundtrip_and_digest(manifest, valid_record):
    row, case = valid_record
    assert joint.validate_joint_record(row, case, manifest, replay=True)["valid"]
    altered = copy.deepcopy(row)
    altered["elapsed_seconds"] += 10
    altered["dynamics_seconds"] += 10
    altered["compression"]["compile_seconds"] += 10
    assert scientific_digest(row) == scientific_digest(altered)


@pytest.mark.parametrize("corruption", ("output", "network", "reference", "bdm", "missing_bits", "acceptance", "manifest", "basin", "cycles"))
def test_corrupt_joint_evidence_rejected(manifest, valid_record, corruption):
    row, case = copy.deepcopy(valid_record)
    if corruption == "output":
        row["dynamics"]["repertoire"]["transition_map"][0] ^= 1
    elif corruption == "network":
        case["dyn"][0] = "XNOR"
    elif corruption == "reference":
        row["wolfram_reference"]["output_sha256"] = "bad"
    elif corruption == "bdm":
        row["compression"]["bdm_original_output"]["value"] = None
    elif corruption == "missing_bits":
        row["compression"]["checked_output_bits"] -= 1
    elif corruption == "acceptance":
        row["dynamics"]["accepted_validation"] = False
    elif corruption == "manifest":
        row["manifest_sha256"] = "stale"
    elif corruption == "basin":
        row["dynamics"]["repertoire"]["basin_sizes"][0] += 1
    else:
        row["dynamics"]["repertoire"]["attractor_cycles"][0].append(63)
    assert not joint.validate_joint_record(row, case, manifest, replay=True)["valid"]


def test_missing_and_duplicate_catalogues_block_release(tmp_path, manifest):
    audit = joint.audit_stage(tmp_path, manifest)
    assert audit["n_missing"] > 0 and not audit["release_ready"]
    manifest["bases"][0]["catalogues"]["EDGE_ADD"].append(manifest["bases"][0]["catalogues"]["EDGE_ADD"][0])
    audit = joint.audit_stage(tmp_path, manifest)
    assert any("catalogue_ids_mismatch" in e for e in audit["errors"])
    with pytest.raises(ValueError, match="incomplete"):
        joint.summarize_stage(tmp_path, manifest)


def test_run_resume_checkpoint_and_reference_failure(tmp_path, manifest, monkeypatch):
    calls = []
    def worker(case, timeout, nodes):
        calls.append(joint.network_hash(case))
        return joint.joint_worker(case)
    monkeypatch.setattr(joint, "run_worker", worker)
    monkeypatch.setattr(joint, "wolfram_reference", lambda *a, **kw: {"status": "timeout"})
    audit = joint.run_stage(tmp_path, manifest)
    assert not audit["release_ready"] and len(calls) == 1
    key = calls[0]
    row = read_json(tmp_path / f"pilot/networks/{key}.json")
    assert row["status"] == "reference_owner_failure"
    joint.run_stage(tmp_path, manifest)
    assert len(calls) == 1  # failed checkpoint is retained, not silently retried


def test_budget_exhausted_does_not_launch(tmp_path, manifest, monkeypatch):
    manifest["limits"]["stage_seconds"] = 0
    seal(manifest)
    monkeypatch.setattr(joint, "run_worker", lambda *a: pytest.fail("must not launch"))
    result = joint.run_stage(tmp_path, manifest)
    assert not result["release_ready"] and result["stop_reason"] == "stage_budget_exhausted"


def test_crash_reservation_survives(tmp_path, manifest, monkeypatch):
    def crash(*args):
        raise KeyboardInterrupt()
    monkeypatch.setattr(joint, "run_worker", crash)
    with pytest.raises(KeyboardInterrupt):
        joint.run_stage(tmp_path, manifest)
    progress = read_json(tmp_path / "pilot/progress.json")
    assert 600 <= progress["used_seconds"] < 601 and progress["active_network"]


def test_all_catalogues_verified_before_summary(tmp_path, manifest, monkeypatch):
    monkeypatch.setattr(joint, "run_worker", lambda c, t, m: joint.joint_worker(c))
    def reference(case, **kwargs):
        program = joint.compile_repertoire_program(joint.Network(case["network_size"], case["cm"], case["dyn"], case["params"]))
        digest = hashlib.sha256(bytes(b for row in joint.iter_output_rows(program) for b in row)).hexdigest()
        return {"status": "completed", "output_sha256": digest}
    monkeypatch.setattr(joint, "wolfram_reference", reference)
    audit = joint.run_stage(tmp_path, manifest)
    assert audit["release_ready"]
    summary = read_json(tmp_path / "pilot/summary.json")
    assert summary["replication_unit"] == "base_network"
    assert len(summary["catalogues"]) == 2
    assert all(g["n_bases"] == 1 for g in summary["groups"])
    monkeypatch.setattr(joint, "run_worker", lambda *a: pytest.fail("accepted record must not rerun"))
    assert joint.run_stage(tmp_path, manifest)["release_ready"]
    main = copy.deepcopy(manifest)
    main["stage"] = "main"
    main["limits"]["stage_seconds"] = 86400
    assert joint.forecast_main(tmp_path, manifest, main)["admitted"]


@pytest.mark.parametrize("outcome", ("timeout", "process", "json"))
def test_worker_process_taxonomy(monkeypatch, outcome):
    def run(*args, **kwargs):
        if outcome == "timeout":
            raise joint.subprocess.TimeoutExpired("test", 1)
        return joint.subprocess.CompletedProcess([], 1 if outcome == "process" else 0, stdout="bad", stderr="test")
    monkeypatch.setattr(joint.subprocess, "run", run)
    result = joint.run_worker({}, 1, 10)
    assert result["status"] == {"timeout": "timeout", "process": "process_failure", "json": "malformed_payload"}[outcome]


def test_preflight_missing_and_stale(tmp_path, monkeypatch):
    from doppel_challenge import joint_preflight as pre
    assert not pre.validate_preflight(tmp_path)["valid"]
    atomic_write_json(tmp_path / "preflight/report.json", seal({"passed": True, "errors": [],
                      "provenance": {}, "artifact_hashes": {}}))
    assert not pre.validate_preflight(tmp_path)["valid"]


def test_notebook_import_cell_is_executable():
    notebook = json.loads((joint.ROOT / "doppel-challenge/notebooks/01_exact_n8_walkthrough.ipynb").read_text())
    imports = [c for c in notebook["cells"] if "from doppel_challenge.pilot_runner import make_mixed_ring_network" in "".join(c["source"])]
    assert len(imports) == 1 and imports[0]["cell_type"] == "code"
