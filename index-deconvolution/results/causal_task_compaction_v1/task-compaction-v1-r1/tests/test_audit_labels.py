"""Run-local tests of the independent audit's evidence labels and malformed-evidence handling."""
from __future__ import annotations

import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import audit as A  # noqa: E402


def test_label_order():
    assert A.label_status(1, 0) == "INVALID"
    assert A.label_status(0, 1) == "INCOMPLETE"
    assert A.label_status(1, 1) == "INVALID"
    assert A.label_status(0, 0) == "VALID_COMPLETE"


def test_determines_least_pair_and_sup1():
    assert A.determines([0, 0, 1, 1], [5, 5, 6, 6]) is None
    assert A.determines([0, 1, 1, 2], [1, 0, 3, 2]) == (1, 2)   # SUP1 closure witness
    assert A.determines([0, 1, 0, 1], [0, 0, 1, 1]) == (0, 2)


def test_legitimate_negative_candidate_is_not_an_issue():
    L = A.Ledger()
    art = {"outputs": [0, 0, 1, 1], "stages": [[0, 0, 1, 1], [0, 0, 1, 1]], "alpha": [0, 0, 1, 1],
           "K": 2, "decoder": [0, 1], "macro": [[0, 1]], "representatives": [0, 2],
           "strict_rounds": 0, "coarsening": [[0, 1]]}
    assert A.certificate(art, [[0, 1, 2, 3]], L, "fx") == {"validity": True, "minimality": True}
    assert A.determines([0, 0, 0, 0], [0, 0, 1, 1]) == (0, 2)     # constant candidate fails decoding
    assert L.invalid == [] and L.missing == []


def test_identity_certificate_valid_but_not_minimal():
    L = A.Ledger()
    ident = [0, 1, 2, 3]
    art = {"outputs": [0, 0, 1, 1], "stages": [[0, 0, 1, 1], ident, ident], "alpha": ident, "K": 4,
           "decoder": [0, 0, 1, 1], "macro": [ident], "representatives": ident, "strict_rounds": 1,
           "coarsening": [[0, 0, 1, 1], ident]}
    assert A.certificate(art, [ident], L, "fx") == {"validity": True, "minimality": False}


def test_absent_and_malformed_evidence_are_structured(tmp_path):
    assert A.main(str(tmp_path / "nothing"), str(tmp_path / "a1")) == 1
    a1 = json.load(open(tmp_path / "a1" / "audit.json"))
    assert a1["status"] == "INCOMPLETE" and a1["n_missing"] >= 1
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "cases.json").write_text("{not json")
    assert A.main(str(bad), str(tmp_path / "a2")) == 1
    a2 = json.load(open(tmp_path / "a2" / "audit.json"))
    assert a2["status"] == "INVALID"
