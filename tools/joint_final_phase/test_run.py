"""Admission and persistence checks for the final replication controller."""
import importlib.util
from pathlib import Path
import sys

import pytest

SPEC = importlib.util.spec_from_file_location("final_phase_run", Path(__file__).with_name("run.py"))
r = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = r
SPEC.loader.exec_module(r)


def test_new_seeds_are_disjoint_and_sample_is_fivefold():
    assert len(r.MAIN_SEEDS)*3*4 == 1200
    assert len(r.PILOT_SEEDS)*3*4 == 36
    assert not set(r.MAIN_SEEDS) & set(r.PILOT_SEEDS)
    assert not (set(r.MAIN_SEEDS) | set(r.PILOT_SEEDS)) & (set(range(20)) | set(range(100, 103)))


@pytest.mark.parametrize("path", [r.PREVIOUS, r.PREVIOUS/"nested", r.PREVIOUS_FINAL, r.ROOT, r.ROOT/"doppel-challenge/results"])
def test_existing_results_and_broad_roots_are_protected(path):
    with pytest.raises(ValueError):
        r.assert_namespace(path)


def test_frozen_manifest_cannot_be_silently_replaced(tmp_path):
    path = tmp_path/"protocol.json"
    original = r.seal({"sample": 1200})
    r.freeze(path, original)
    r.freeze(path, original)
    with pytest.raises(ValueError, match="frozen"):
        r.freeze(path, r.seal({"sample": 1199}))
    assert r.checked(path) == original


@pytest.mark.parametrize("mutation", ["missing", "not_ready", "errors", "manifest", "count"])
def test_incomplete_or_failed_stages_cannot_open_next_gate(monkeypatch, mutation):
    manifest = {"stage": "pilot", "sha256": "expected"}
    monkeypatch.setattr(r.joint, "tasks", lambda _: iter([("one", {}, "ring")]))
    audit = {"release_ready": True, "errors": [], "manifest_sha256": "expected",
             "n_missing": 0, "n_accepted": 1, "n_expected": 1}
    if mutation == "missing":
        audit["n_missing"] = 1
    elif mutation == "not_ready":
        audit["release_ready"] = False
    elif mutation == "errors":
        audit["errors"] = ["owner_failure"]
    elif mutation == "manifest":
        audit["manifest_sha256"] = "other"
    else:
        audit["n_expected"] = 0
        audit["n_accepted"] = 0
    with pytest.raises(ValueError):
        r.assert_stage(audit, manifest)


def test_complete_matching_stage_passes(monkeypatch):
    monkeypatch.setattr(r.joint, "tasks", lambda _: iter([("one", {}, "ring")]))
    r.assert_stage({"release_ready": True, "errors": [], "manifest_sha256": "expected",
                    "n_missing": 0, "n_accepted": 1, "n_expected": 1}, {"stage": "pilot", "sha256": "expected"})


def test_changed_artifact_is_rejected(tmp_path):
    path = tmp_path/"evidence.txt"
    path.write_text("original")
    hashes = {path.name: r.sha(path)}
    path.write_text("changed")
    with pytest.raises(ValueError):
        r.verify_files(tmp_path, hashes)
