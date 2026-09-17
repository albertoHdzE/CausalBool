"""Adversarial checks for release links, corruption, weighting and execution."""
import importlib.util
import json
from pathlib import Path
import sys

import pandas as pd
import pytest

SPEC = importlib.util.spec_from_file_location("joint_finalization", Path(__file__).with_name("finalize.py"))
f = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = f
SPEC.loader.exec_module(f)


def test_canonical_parent_link_is_independent_of_json_whitespace(tmp_path):
    parent = f.seal({"record_kind": "parent", "release_ready": True})
    summary = f.seal({"record_kind": "summary", "value": 7})
    path = tmp_path / "parent.json"
    path.write_text(json.dumps(parent, indent=4))
    analysis = {"release_sha256": parent["sha256"], "main_summary_sha256": summary["sha256"]}
    assert f.raw_hash(path) != parent["sha256"]
    f.check_parent_link(analysis, f.strict_read(path), summary)
    first = f.raw_hash(path)
    path.write_text(json.dumps(parent, separators=(",", ":")))
    assert f.raw_hash(path) != first
    f.check_parent_link(analysis, f.strict_read(path), summary)


@pytest.mark.parametrize("field", ["release_sha256", "main_summary_sha256"])
def test_wrong_canonical_reference_is_rejected(field):
    analysis = {"release_sha256": "parent", "main_summary_sha256": "summary"}
    analysis[field] = "wrong"
    with pytest.raises(ValueError, match="canonical"):
        f.check_parent_link(analysis, {"sha256": "parent"}, {"sha256": "summary"})


@pytest.mark.parametrize("mutation", ["content", "seal", "scientific_seal", "forged_success"])
def test_modified_record_is_rejected(tmp_path, mutation):
    record = f.seal({"value": 4, "release_ready": False})
    if mutation == "content":
        record["value"] = 5
    elif mutation == "seal":
        record["sha256"] = "bad"
    elif mutation == "scientific_seal":
        record["scientific_digest"] = "bad"
        record["sha256"] = f.compute_sha256(record)
    else:
        record["release_ready"] = True
    path = tmp_path / "record.json"
    path.write_text(json.dumps(record))
    with pytest.raises(ValueError):
        f.strict_read(path)


@pytest.mark.parametrize("mutation", ["changed", "missing", "outside", "empty"])
def test_bad_artifact_manifest_is_rejected(tmp_path, mutation):
    path = tmp_path / "table.csv"
    path.write_text("a,b\n1,2\n")
    hashes = {path.name: f.raw_hash(path)}
    if mutation == "changed":
        path.write_text("a,b\n1,999\n")
    elif mutation == "missing":
        hashes = {"missing.csv": f.raw_hash(path)}
    elif mutation == "outside":
        hashes = {"../outside.csv": "any"}
    else:
        hashes = {}
    with pytest.raises((ValueError, OSError)):
        f.check_artifacts(tmp_path, hashes)


def test_base_means_do_not_weight_larger_catalogues_more():
    rows = [{"family": "ring", "n": 8, "kind": "EDGE_ADD", "base_id": name,
             **{metric: value for metric in f.METRICS}}
            for name, value in [("a", 0), ("a", 0), ("a", 0), ("b", 8)]]
    effects = pd.DataFrame(rows)
    bases = f.base_statistics(effects)
    assert effects.program_bits.mean() == 2
    assert bases.program_bits.mean() == 4
    assert len(bases) == 2


@pytest.mark.parametrize("count,outputs,expected", [(None, [], False), (1, [], True),
                        (1, [{"output_type": "error", "ename": "ValueError"}], False)])
def test_notebook_requires_completed_code_and_no_error(tmp_path, count, outputs, expected):
    path = tmp_path / "notebook.ipynb"
    path.write_text(json.dumps({"cells": [{"cell_type": "code", "source": ["1+1"],
                                          "execution_count": count, "outputs": outputs}]}))
    assert f.notebook_complete(path) is expected


def test_none_is_not_silently_zero_and_nan_does_not_pass():
    assert not f.close(None, 0)
    assert not f.close(float("nan"), float("nan"))
    assert f.close(516.767321359471, 516.7673213594709)
