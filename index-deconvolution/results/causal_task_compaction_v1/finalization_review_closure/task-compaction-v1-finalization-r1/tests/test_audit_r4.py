"""Run-local tests of audit_r4: the seal authority, the authority-based seal check and the FX1
fixture check, in-process on small copies. The pipeline matrix is src/probe_matrix_r4.py."""
from __future__ import annotations

import copy
import json
import os
import shutil
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import audit_r4 as R  # noqa: E402

PROD = os.path.join(R.ORIG_RUN, "production")
FX = json.load(open(os.path.join(PROD, "fixtures", "FX1_identity.json")))
SEAL = json.load(open(os.path.join(PROD, "seal.json")))


def _seal(tmp_path, seal=None, bypass=False, drop=None):
    prod = tmp_path / "production"
    shutil.copytree(PROD, prod)
    if seal is not None:
        (prod / "seal.json").write_text(json.dumps(seal))
    if drop:
        os.remove(prod / drop)
    L, rep = R.R3.Ledger(), {}
    R.check_seal_r4(str(prod), L, bypass, rep)
    return L, rep["integrity"]


def _fixture(tmp_path, fx):
    d = tmp_path / "production" / "fixtures"
    d.mkdir(parents=True)
    if fx is not None:
        (d / "FX1_identity.json").write_text(json.dumps(fx))
    L, rep = R.R3.Ledger(), {}
    R.check_fixture_r4(str(tmp_path / "production"), L, rep)
    return L, rep["fixture_FX1"]


def test_authority_is_the_pinned_original_seal_not_a_candidate():
    assert len(R.AUTH) == 60 and R.AUTH == SEAL["sha256"]
    assert R.AUTHORITY_LOG["sha256"] == R.sha(os.path.join(PROD, "seal.json"))


def test_wiring_rebinds_exactly_the_two_entry_points():
    assert R.R3.R2.check_seal is R.check_seal_r4 and R.R3.check_fixture is R.check_fixture_r4
    assert R.R3.R2.schema_cell is R.R2.schema_cell        # everything else is r2/r3's


def test_pristine_seal_counts(tmp_path):
    L, i = _seal(tmp_path)
    assert (L.invalid, L.missing) == ([], [])
    assert (i["intended_entries"], i["candidate_entries_agreeing"], i["hashes_compared"]) == (60, 60, 60)


def test_empty_seal_is_incomplete_in_both_modes(tmp_path):
    for bypass in (False, True):
        s = copy.deepcopy(SEAL)
        s["sha256"] = {}
        L, i = _seal(tmp_path / str(bypass), s, bypass)
        assert L.invalid == [] and len(L.missing) == 60 and i["candidate_entries_agreeing"] == 0


def test_absent_data_and_absent_entry_are_both_missing(tmp_path):
    s = copy.deepcopy(SEAL)
    s["sha256"].pop("imports.json")
    L, i = _seal(tmp_path, s, False, drop="imports.json")
    assert {m["missing"] for m in L.missing} == {"seal entry imports.json", "sealed artifact imports.json"}
    assert i["hashes_compared"] == 59


def test_contradicting_hash_is_invalid_even_in_bypass(tmp_path):
    s = copy.deepcopy(SEAL)
    s["sha256"]["cases.json"] = "f" * 64
    L, _ = _seal(tmp_path, s, True)
    assert [x["field"] for x in L.invalid] == ["sha256[cases.json]"]


def test_pristine_fixture_runs_both_certificate_checks(tmp_path):
    L, r = _fixture(tmp_path, FX)
    assert L.invalid == [] and (r["validity"], r["minimality"], r["certificate_checks_completed"]) == (True, True, 2)


def test_absent_fixture_is_incomplete(tmp_path):
    L, r = _fixture(tmp_path, None)
    assert L.invalid == [] and len(L.missing) == 1 and r["file_available"] is False
    assert r["certificate_checks_completed"] == 0


def test_every_rejected_fixture_branch_names_its_field(tmp_path):
    cases = {"fixture_id": 123, "K": True, "coarsening": None, "strict_rounds": -1, "macro": [],
             "transitions": [[0, 1, 3, 2]], "representatives": "x", "decoder": [0.0, 1]}
    for k, v in cases.items():
        fx = dict(FX, **{k: v})
        L, r = _fixture(tmp_path / k, fx)
        assert any(x.get("field", "").startswith(f"fixture.{k}") for x in L.invalid), k
        assert r["certificate_checks_completed"] == 0 and r["schema_valid"] is False, k
