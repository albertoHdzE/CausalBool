"""Run-local tests of the revised audit (audit_r2): the five original label/structure tests,
re-pointed at the revision, plus type-exact summary comparison.  The full pipeline matrix
(PROTOCOL R1 items 1-10) is src/probe_matrix.py on copies of the saved production."""
from __future__ import annotations

import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), "src"))

import audit_r2 as R  # noqa: E402

A = R.A   # the frozen audit's independent checks, identity-verified on import


def test_label_order():
    assert A.label_status(1, 0) == "INVALID"
    assert A.label_status(0, 1) == "INCOMPLETE"
    assert A.label_status(1, 1) == "INVALID"
    assert A.label_status(0, 0) == "VALID_COMPLETE"


def test_determines_least_pair_and_sup1():
    assert A.determines([0, 0, 1, 1], [5, 5, 6, 6]) is None
    assert A.determines([0, 1, 1, 2], [1, 0, 3, 2]) == (1, 2)
    assert A.determines([0, 1, 0, 1], [0, 0, 1, 1]) == (0, 2)


def test_legitimate_negative_candidate_is_not_an_issue():
    L = R.Ledger()
    art = {"outputs": [0, 0, 1, 1], "stages": [[0, 0, 1, 1], [0, 0, 1, 1]], "alpha": [0, 0, 1, 1],
           "K": 2, "decoder": [0, 1], "macro": [[0, 1]], "representatives": [0, 2],
           "strict_rounds": 0, "coarsening": [[0, 1]]}
    assert R.schema_certificate(art, 4, 1) is None
    assert A.certificate(art, [[0, 1, 2, 3]], L, "fx") == {"validity": True, "minimality": True}
    assert L.invalid == [] and L.missing == []


def test_identity_certificate_valid_but_not_minimal():
    L = R.Ledger()
    ident = [0, 1, 2, 3]
    art = {"outputs": [0, 0, 1, 1], "stages": [[0, 0, 1, 1], ident, ident], "alpha": ident, "K": 4,
           "decoder": [0, 0, 1, 1], "macro": [ident], "representatives": ident, "strict_rounds": 1,
           "coarsening": [[0, 0, 1, 1], ident]}
    assert R.schema_certificate(art, 4, 1) is None
    assert A.certificate(art, [ident], L, "fx") == {"validity": True, "minimality": False}


def test_absent_and_malformed_evidence_are_structured(tmp_path):
    assert R.main(str(tmp_path / "nothing"), str(tmp_path / "a1")) == 1
    a1 = json.load(open(tmp_path / "a1" / "audit.json"))
    assert a1["status"] == "INCOMPLETE" and a1["n_invalid"] == 0 and a1["n_missing"] >= 2
    bad = tmp_path / "bad"
    bad.mkdir()
    (bad / "cases.json").write_text("{not json")
    assert R.main(str(bad), str(tmp_path / "a2")) == 1
    a2 = json.load(open(tmp_path / "a2" / "audit.json"))
    assert a2["status"] == "INVALID" and "aggregates" not in a2


def test_nonfinite_and_bool_are_rejected(tmp_path):
    L = R.Ledger()
    (tmp_path / "x.json").write_text('{"a": NaN}')
    assert R.load_json(str(tmp_path / "x.json"), L, "x")[0] == "invalid"
    assert not R.int_vec([0, True]) and not R.int_vec([0, 1.0]) and R.int_vec([0, 1], 2, 0, 2)


def test_summary_comparison_is_type_exact():
    assert R.exact(0) != R.exact(False) and R.exact(1) != R.exact(1.0) and R.exact(None) != R.exact(0)
    assert R.exact({"b": 1, "a": None}) == R.exact({"a": None, "b": 1})
