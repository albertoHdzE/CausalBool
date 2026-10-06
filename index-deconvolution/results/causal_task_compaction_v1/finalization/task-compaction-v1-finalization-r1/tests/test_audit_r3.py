"""Run-local tests of audit_r3: type-exact comparison, the record schema, parity of the
refactored expectation with the frozen audit_cell on every saved cell, source resolution,
and the import boundary. The pipeline matrix is src/probe_matrix_r3.py."""
from __future__ import annotations

import ast
import json
import os
import sys

import pytest

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
SRC = os.path.join(os.path.dirname(HERE), "src")
sys.path.insert(0, SRC)

import audit_r3 as R  # noqa: E402

A, E = R.A, R.E
PROD = os.path.join(R.ORIG_RUN, "production")


def _cases():
    return json.load(open(os.path.join(PROD, "cases.json")))["cells"]


def test_first_diff_is_type_exact_and_recursive():
    assert R.first_diff({"a": [1, {"b": True}]}, {"a": [1, {"b": True}]}, "x") is None
    assert R.first_diff({"a": [1, {"b": 1}]}, {"a": [1, {"b": True}]}, "x") == ("x.a[1].b", "type int != expected bool")
    assert R.first_diff(256.0, 256, "K")[1] == "type float != expected int"
    assert R.first_diff({"num": 1}, {"num": 1, "den": 2}, "r") == ("r.den", "missing required field")
    assert R.first_diff({"num": 1, "x": 0}, {"num": 1}, "r") == ("r.x", "undeclared field")
    assert R.first_diff(None, 0, "v")[1] == "type NoneType != expected int"


def test_schema_record_accepts_saved_rows_and_names_fields():
    c = _cases()[0]
    rows = [json.loads(x) for x in open(os.path.join(PROD, "candidates", "cell_00.jsonl"))]
    assert all(R.schema_record(r, c, c["n_actions"]) == [] for r in rows)
    r = dict(rows[1], decodable=1, decode_conflict=[3, 0], null_reason="")
    got = {f for f, _ in R.schema_record(r, c, c["n_actions"])}
    assert got == {"decodable", "null_reason"}            # conflict rule is skipped once decodable is not bool
    r = dict(rows[1], decode_conflict=[3, 0])
    assert {f for f, _ in R.schema_record(r, c, c["n_actions"])} == {"decode_conflict"}


def test_expected_r3_matches_frozen_audit_cell_on_every_saved_cell():
    """Parity evidence for the refactor: on all 24 saved cells the frozen audit_cell raises no
    issue, and the refactored expectation equals the saved summary and records TYPE-EXACTLY."""
    T = {m: json.load(open(os.path.join(PROD, "tables", f"{m}.json"))) for m in sorted({c["model"] for c in _cases()})}
    L = A.Ledger()
    tabs = A.audit_tables(T, "production", L)
    cal, clos_f, clos_e = {}, {}, {}
    for m, t in T.items():
        decl = A.S.candidates(t["n"])
        cal[m] = (decl, [A.first_appearance([A.S.alpha_value(c, x, t["n"]) for x in range(t["N"])]) for c in decl])
    n_cells = 0
    for c in _cases():
        w = f"cell_{c['cell_id']:02d}"
        art = json.load(open(os.path.join(PROD, "cells", f"{w}.json")))
        recs = [json.loads(x) for x in open(os.path.join(PROD, "candidates", f"{w}.jsonl"))]
        A.audit_cell(c, art, recs, tabs[c["model"]], cal[c["model"]], clos_f, L, w)
        rows = E.expected_candidates(A, c, art["alpha"], tabs[c["model"]], *cal[c["model"]], clos_e)
        assert all(th in (True, None) for _, _, th in rows)
        exp = [{k: v for k, v in e.items()} for e, _, _ in rows]
        saved = [{k: v for k, v in r.items() if k != "null_reason"} for r in recs]
        assert R.first_diff(saved, exp, "records") is None
        s = E.expected_summary(A, c, art["stages"], art["alpha"], tabs[c["model"]], cal[c["model"]][0], rows)
        assert R.first_diff(art["summary"], s, "summary") is None
        n_cells += 1
    assert n_cells == 24 and L.invalid == [] and L.missing == []


def test_scientific_modules_resolve_to_the_original_isolated_copy():
    L = R.Ledger()
    rep = {}
    R.source_resolution(L, rep)
    assert L.invalid == []
    assert set(rep["source_resolution"]) == set(R.SCIENTIFIC_MODULES)
    assert all(v.startswith("isolated/") for v in rep["source_resolution"].values())
    active = os.path.join(R.REPO, "index-deconvolution", "src")
    assert all(not os.path.abspath(sys.modules[m].__file__).startswith(active + os.sep) for m in R.SCIENTIFIC_MODULES)


def test_source_resolution_rejects_a_switched_module(monkeypatch):
    fake = type(sys)("deconvolution")
    fake.__file__ = os.path.join(R.REPO, "index-deconvolution", "src", "deconvolution.py")
    monkeypatch.setitem(sys.modules, "deconvolution", fake)
    L = R.Ledger()
    R.source_resolution(L, {})
    assert [i["where"] for i in L.invalid] == ["source_resolution"]


@pytest.mark.parametrize("name", ["audit_r3.py", "expected_r3.py"])
def test_import_boundary_and_single_expectation(name):
    tree = ast.parse(open(os.path.join(SRC, name)).read())
    mods = {a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    mods |= {n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert mods <= {"__future__", "hashlib", "importlib.util", "json", "os", "sys"}
    names = {n.attr for n in ast.walk(tree) if isinstance(n, ast.Attribute)} | \
        {n.id for n in ast.walk(tree) if isinstance(n, ast.Name)}
    forbidden = {"audit_cell", "minimal_task_partition", "distinguishing_task_word", "task_word_path", "produce"}
    assert not names & forbidden


def test_label_precedence_keeps_both_lists():
    L = R.Ledger()
    L.bad_field("w", "f", "x")
    L.absent("w", "y")
    assert A.label_status(len(L.invalid), len(L.missing)) == "INVALID"
    assert L.invalid == [{"where": "w", "field": "f", "check": "x"}] and L.missing == [{"where": "w", "missing": "y"}]
