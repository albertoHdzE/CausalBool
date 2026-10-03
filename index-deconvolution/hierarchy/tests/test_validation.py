"""Study validation through the real report/verify commands on a tiny frozen run.

One tiny study is frozen and benchmarked once per module with the production code
paths (freeze, isolated workers, merge, report). The design is explicit and small:
confirmation F01, F04 x 64 bits x replicates 1000-1001, transfer F01 x 64 bits x
replicate 2000. Each test copies the run, damages it in one declared way and checks
the exit state of ``report`` and ``verify`` and the gated decisions they write.
"""
from __future__ import annotations

import json
import shutil
import sys

import pytest

from hierarchy import benchmark as B
from hierarchy import cli
from hierarchy import corpus
from hierarchy import report as R
from hierarchy import validation as V
from hierarchy.wire import encode_literal

RID = "confirm-tiny"
TINY = {"confirmation": {"families": ("F01", "F04"), "base_lengths": (64,),
                         "replicates": (1000, 1001)},
        "transfer": {"families": ("F01",), "base_lengths": (64,), "replicates": (2000,)},
        "development": corpus.SPLITS["development"]}
FAKE_DIAG = {"objects": {}, "holm": {}, "claim_status": "inconclusive",
             "claim_detail": {"structured_rejected_after_holm": []}}


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    mp = pytest.MonkeyPatch()
    root = tmp_path_factory.mktemp("tiny_results")
    mp.setattr(corpus, "SPLITS", TINY)
    mp.setattr(B, "RESULTS", root)
    B.write_freeze(RID)
    for split in ("confirmation", "transfer"):
        B.benchmark(RID, split, resume=False, log=lambda m: None)
    d = B.run_dir(RID)
    (d / "diagnostics.json").write_text(json.dumps(FAKE_DIAG))
    assert cli.main(["report", "--run-id", RID]) == cli.EXIT_OK
    yield root
    mp.undo()


@pytest.fixture
def run(built, tmp_path, monkeypatch):
    """A private copy of the tiny run; returns its directory."""
    monkeypatch.setattr(corpus, "SPLITS", TINY)
    monkeypatch.setattr(B, "RESULTS", tmp_path / "results")
    shutil.copytree(built, tmp_path / "results")
    return B.run_dir(RID)


def _rows(d):
    return R.load_rows(d)


def _write(d, rows, jsonl_extra=()):
    """Write rows to both rows/<case>.json and cases.jsonl (extra lines: jsonl only)."""
    by = {}
    for r in rows:
        by.setdefault(r["case_id"], []).append(r)
    for p in (d / "rows").glob("*.json"):
        p.unlink()
    for cid, rr in by.items():
        (d / "rows" / f"{cid}.json").write_text(json.dumps(rr, sort_keys=True))
    lines = [json.dumps(r, sort_keys=True) for r in list(rows) + list(jsonl_extra)]
    (d / "cases.jsonl").write_text("\n".join(lines) + "\n" if lines else "")


def _report_and_verify(d):
    rc = cli.main(["report", "--run-id", RID])
    s = json.loads((d / "summary.json").read_text())
    vc = cli.main(["verify", "--run-id", RID])
    v = json.loads((d / "verification.json").read_text())
    return rc, s, vc, v


def _store(d, data: bytes):
    rel, h = B.store_archive(d, data)
    return rel, h


def test_complete_valid_study_passes_whatever_its_verdict(run):
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_OK, cli.EXIT_OK)
    assert v["engineering_status"] == "valid" and v["completeness"] == "complete"
    p = s["primary"]
    assert p["verdict"] in ("supported", "not_supported", "inconclusive")
    assert p["required_units"] == p["available_units"] == p["units"] == 4
    assert s["study_complete"] and s["engineering_status"] == "valid"
    assert v["validation"]["archives_checked"] == (8 + 2) * len(B.ALL_METHODS)
    assert v["summary_recomputed"]["agrees"]
    assert v["environment_differences"] == {} or all(
        not c["required_for"] for c in v["environment_differences"].values())


def test_one_f04_pair_out_of_the_declared_design_is_not_assessed(run):
    keep = [r for r in _rows(run) if r["case_id"].startswith("confirmation-F04-64-1000-")]
    _write(run, keep)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INCOMPLETE, cli.EXIT_INCOMPLETE)
    p = s["primary"]
    assert p["verdict"] == "not_assessed" and p["evidence_completeness"] == "incomplete"
    assert p["required_units"] == 4 and p["available_units"] == 1
    assert "ci95" not in p and p["partial_diagnostic"]["label"].startswith("PARTIAL")
    mu = s["validation"]["missing_units"]["confirmation"]
    assert mu == ["confirmation|F01|64|1000", "confirmation|F01|64|1001",
                  "confirmation|F04|64|1001"]
    led = {c["id"]: c for c in json.loads((run / "claim_ledger.json").read_text())}
    assert led["C1"]["decision"] == "not_assessed" and led["C1"]["estimate"] is None
    assert s["status_counts"]["confirmation"]["hid_full"]["absent"] == 6


@pytest.mark.parametrize("drop,unit", [
    (lambda r: r["case_id"].startswith("confirmation-F01-64-1000-"), "whole unit"),
    (lambda r: r["split"] == "confirmation" and r["family"] == "F01", "whole cell"),
    (lambda r: r["case_id"] == "confirmation-F04-64-1001-ragged", "one ragged member"),
])
def test_missing_rows_make_the_primary_incomplete(run, drop, unit):
    _write(run, [r for r in _rows(run) if not drop(r)])
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INCOMPLETE, cli.EXIT_INCOMPLETE), unit
    assert s["primary"]["verdict"] == "not_assessed", unit
    assert v["incomplete_count"] > 0 and v["engineering_status"] == "valid", unit


def test_missing_baseline_method_is_incomplete_and_its_portfolio_unverifiable(run):
    _write(run, [r for r in _rows(run) if r["method"] != "lzma"])
    rc, s, vc, v = _report_and_verify(run)
    # an "ok" portfolio whose constituent row is absent cannot be checked: invalid
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    assert v["completeness"] == "incomplete"
    assert s["validation"]["missing_methods"]["confirmation"] == {"lzma": 8}
    assert any("constituents not ok" in x for x in v["invalid_reasons"])
    assert s["primary"]["verdict"] == "not_assessed"


def test_missing_ablation_method_blocks_components_but_not_the_primary(run):
    _write(run, [r for r in _rows(run) if r["method"] != "hid_no_schema"])
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INCOMPLETE, cli.EXIT_INCOMPLETE)
    assert s["validation"]["missing_methods"]["confirmation"] == {"hid_no_schema": 8}
    assert s["primary"]["verdict"] != "not_assessed"           # its own population is complete
    assert {a["component_advantage"] for a in s["ablations"].values()} == {"not_assessed"}


def test_duplicate_row_key_is_invalid_and_never_overwrites(run):
    rows = _rows(run)
    dup = dict(rows[0], archive_bits=8)
    _write(run, rows, jsonl_extra=[dup])
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    assert s["validation"]["duplicates"] == [f"{rows[0]['case_id']}:{rows[0]['method']}"]
    assert s["primary"]["verdict"] == "not_assessed"


def _censor(d, rows, cid, method="lzma"):
    """Make one constituent a legitimate censored timeout and re-derive the portfolio
    exactly as the runner does; the study stays valid and complete."""
    by = {r["method"]: r for r in rows if r["case_id"] == cid}
    case = next(c for c in corpus.split_cases(cid.split("-")[0])[0] if c.case_id == cid)
    lit = encode_literal(case.bits)
    rel, h = _store(d, lit)
    by[method].update(status="censored_timeout", archive_path=rel, archive_sha256=h,
                      archive_bits=8 * len(lit), selected_codec_id=lit[4],
                      exception_type="timeout", encode_wall_ns=None)
    avail = {m: (d / by[m]["archive_path"]).read_bytes() for m in B.BASELINE_METHODS
             if by[m]["status"] == "ok"}
    best = V.portfolio_choice(avail)
    by["baseline_best"].update(status="incomplete_constituents", selected_method=best,
                               archive_path=by[best]["archive_path"],
                               archive_sha256=by[best]["archive_sha256"],
                               archive_bits=by[best]["archive_bits"],
                               selected_codec_id=by[best]["selected_codec_id"])


def test_censored_baseline_forces_inconclusive_whatever_the_interval(run):
    rows = _rows(run)
    _censor(run, rows, "confirmation-F04-64-1000-base")
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_OK, cli.EXIT_OK)                # valid, complete
    p = s["primary"]
    assert p["verdict"] == "inconclusive" and p["censored_baselines"] == 2
    assert "ci95" not in p and p["partial_diagnostic"]["units"] == 3
    assert v["validation"]["censored"]


def test_error_row_is_invalid_engineering_and_blocks_every_claim(run):
    rows = _rows(run)
    r = next(r for r in rows if r["method"] == "hid_no_schema")
    r.update(status="error", archive_path=None, archive_sha256=None, archive_bits=None,
             decode_ok=None, exception_type="hierarchy.infer.CandidateExpansionMismatch")
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    assert s["primary"]["verdict"] == "not_assessed"
    assert s["primary"]["evidence_validity"] == "invalid"
    assert "estimate_mean_saving_per_input_bit" not in s["primary"]
    led = {c["id"]: c for c in json.loads((run / "claim_ledger.json").read_text())}
    assert led["C2"]["status"] == "not_supported"
    assert all(led[f"C3.{i}"]["decision"] == "not_assessed" for i in range(1, 6))


@pytest.mark.parametrize("damage,needle", [
    (lambda d, r: r.update(archive_path=None), "no archive_path"),
    (lambda d, r: r.update(archive_sha256="0" * 64), "archive hash differs"),
    (lambda d, r: r.update(archive_bits=r["archive_bits"] + 8), "archive_bits"),
    (lambda d, r: r.update(selected_codec_id=(r["selected_codec_id"] + 1) % 10),
     "selected_codec_id"),
    (lambda d, r: r.update(decode_ok=False), "decode_ok"),
])
def test_ok_row_archive_defects_are_invalid(run, damage, needle):
    rows = _rows(run)
    r = next(r for r in rows if r["method"] == "hid_full" and r["split"] == "confirmation")
    damage(run, r)
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    assert any(needle in x for x in v["invalid_reasons"]), v["invalid_reasons"][:5]


def test_archive_of_another_input_is_invalid(run):
    rows = _rows(run)
    r = next(r for r in rows if r["method"] == "raw" and r["split"] == "confirmation")
    other = encode_literal("01" * (r["n_bits"] // 2) + "0" * (r["n_bits"] % 2))
    rel, h = _store(run, other)
    r.update(archive_path=rel, archive_sha256=h, archive_bits=8 * len(other))
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert vc == cli.EXIT_INVALID
    assert any("decodes to a different input" in x for x in v["invalid_reasons"])


def test_wrong_input_hash_on_a_case_is_invalid(run):
    rows = _rows(run)
    cid = "confirmation-F01-64-1000-base"
    for r in rows:
        if r["case_id"] == cid:
            r["input_sha256"] = "f" * 64
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert vc == cli.EXIT_INVALID
    assert any("regenerated input" in x for x in v["invalid_reasons"])


def test_portfolio_identity_is_checked_beyond_its_size(run):
    rows = _rows(run)
    cid = "confirmation-F04-64-1000-base"
    by = {r["method"]: r for r in rows if r["case_id"] == cid}
    best = by["baseline_best"]
    other = next(m for m in B.BASELINE_METHODS if m != best["selected_method"])
    best["selected_method"] = other            # size, bytes and hash still the minimum's
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert vc == cli.EXIT_INVALID
    assert any("deterministic minimum" in x for x in v["invalid_reasons"])


def test_unknown_case_or_method_is_invalid(run):
    rows = _rows(run)
    extra = dict(rows[0], method="hid_mystery")
    _write(run, rows + [extra])
    rc, s, vc, v = _report_and_verify(run)
    assert vc == cli.EXIT_INVALID and s["validation"]["unknown"]


def test_rows_file_disagreeing_with_cases_jsonl_is_invalid(run):
    rows = _rows(run)
    cid = rows[0]["case_id"]
    on_disk = json.loads((run / "rows" / f"{cid}.json").read_text())
    on_disk[0]["stop_reason"] = "edited"
    (run / "rows" / f"{cid}.json").write_text(json.dumps(on_disk))
    assert cli.main(["verify", "--run-id", RID]) == cli.EXIT_INVALID


def test_not_run_rows_are_incomplete_not_invalid(run):
    rows = _rows(run)
    cid = "confirmation-F01-64-1001-ragged"
    case = next(c for c in corpus.split_cases("confirmation")[0] if c.case_id == cid)
    fsha = rows[0]["freeze_sha256"]
    rows = [r for r in rows if r["case_id"] != cid] + B.not_run_rows(case, RID, fsha, "budget")
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INCOMPLETE, cli.EXIT_INCOMPLETE)
    assert s["primary"]["verdict"] == "not_assessed"


def test_stale_summary_is_detected_by_verify(run):
    s = json.loads((run / "summary.json").read_text())
    s["primary"]["verdict"] = "supported" if s["primary"]["verdict"] != "supported" else "inconclusive"
    (run / "summary.json").write_text(json.dumps(s))
    assert cli.main(["verify", "--run-id", RID]) == cli.EXIT_INVALID


def test_report_and_verify_share_one_validation_path(run, monkeypatch):
    calls = []
    real = V.validate_run

    def spy(*a, **k):
        calls.append(a[0])
        return real(*a, **k)
    monkeypatch.setattr(V, "validate_run", spy)
    cli.main(["report", "--run-id", RID])
    cli.main(["verify", "--run-id", RID])
    assert calls == [RID, RID]


# ---------------------------------------------------------------------------
# R2: a semantic mismatch inside a worker is an error row, never a fallback
# ---------------------------------------------------------------------------

FAULT = """
import sys
import hierarchy.infer as I
orig = I._Search.consider
def bad(self, root, source):
    if not getattr(self, "_fault", False):
        self._fault = True
        flip = "1" if self.x[0] == "0" else "0"
        root = self.f.literal(flip + self.x[1:])
    return orig(self, root, source)
I._Search.consider = bad
import hierarchy.benchmark as B
sys.exit(B.worker_main(sys.argv[1], sys.argv[2]))
"""


class FaultJob(B._Job):
    def worker_argv(self, method):
        if method.startswith("hid_"):
            return [sys.executable, "-S", "-c", FAULT, method, str(self.tmp)]
        return super().worker_argv(method)


def test_worker_semantic_mismatch_becomes_an_invalid_error_row(tmp_path, monkeypatch):
    monkeypatch.setattr(B, "_Job", FaultJob)
    bits, _ = corpus.generate_unit("development", "F01", 256, 0)
    cases = [corpus.Case(corpus.case_id("development", "F01", 256, 0, rg), "development",
                         "F01", 256, 0, rg, bits if rg else bits[:256]) for rg in (False, True)]
    B.run_cases(cases, tmp_path, "dev-fault", "h", False, lambda m: None)
    rows = [r for c in cases for r in json.loads(B.case_rows_path(tmp_path, c).read_text())]
    hid = [r for r in rows if r["method"].startswith("hid_")]
    assert hid and all(r["status"] == "error" for r in hid)
    assert all("CandidateExpansionMismatch" in r["exception_type"] for r in hid)
    assert all(r["archive_path"] is None and r["archive_bits"] is None for r in hid)
    design = V.make_design({"development": {"families": ("F01",), "base_lengths": (256,),
                                            "replicates": (0,)}},
                           B.ALL_METHODS, B.BASELINE_METHODS)
    v = V.validate_study(rows, design, run_dir=tmp_path, freeze_sha="h",
                         inputs={c.case_id: c.bits for c in cases})
    assert not v["engineering_valid"] and v["complete"]
    assert sum("error row" in x for x in v["invalid"]) == 2 * len(B.HID_METHODS)


# ---------------------------------------------------------------------------
# R5: the frozen environment is enforced before results are written
# ---------------------------------------------------------------------------

def test_benchmark_resume_refuses_a_different_codec_library(run, monkeypatch):
    real = B.environment()
    before = sorted(p.name for p in (run / "rows").iterdir())
    monkeypatch.setattr(B, "environment",
                        lambda: dict(real, lzma_liblzma="probe-sha256:" + "0" * 64))
    with pytest.raises(RuntimeError, match=r"environment\[lzma_liblzma\]"):
        B.benchmark(RID, "confirmation", resume=True, log=lambda m: None)
    assert sorted(p.name for p in (run / "rows").iterdir()) == before


def test_report_and_diagnostics_refuse_and_verify_reports_a_different_numpy(run, monkeypatch):
    real = B.environment()
    freeze = (run / "freeze.json").read_bytes()
    summary = (run / "summary.json").read_bytes()
    monkeypatch.setattr(B, "environment", lambda: dict(real, numpy_version="0.0", cpu="elsewhere"))
    with pytest.raises(SystemExit, match="numpy_version"):
        cli.main(["report", "--run-id", RID])
    with pytest.raises(SystemExit, match="numpy_version"):
        cli.main(["diagnostics", "--run-id", RID])
    assert (run / "summary.json").read_bytes() == summary
    assert cli.main(["verify", "--run-id", RID]) == cli.EXIT_OK      # offline check still possible
    v = json.loads((run / "verification.json").read_text())
    assert v["environment_differences"]["numpy_version"]["required_for"] == ["diagnostics", "report"]
    assert v["environment_differences"]["cpu"]["required_for"] == []
    assert v["verification_environment"]["numpy_version"] == "0.0"
    assert v["summary_recomputed"].startswith("skipped")
    assert (run / "freeze.json").read_bytes() == freeze                # provenance untouched


# ---------------------------------------------------------------------------
# Validator closure (bitacora 37 §4): R1a missing/malformed archives reach the
# structured invalid record; R1b rows files are checked before they are keyed;
# R1c undeclared rows are validated, never filtered out
# ---------------------------------------------------------------------------

FIRST = "confirmation-F01-64-1000-base"       # first sample stratum and representative ledger


def _ledger_item(d, cid, method):
    for e in json.loads((d / "ledgers.json").read_text()):
        if e.get(method, {}).get("case_id") == cid:
            return e[method]
    raise KeyError(cid)


def _assert_nothing_claims_success(d, s, v):
    assert s["engineering_status"] == "invalid" and s["primary"]["verdict"] == "not_assessed"
    led = {c["id"]: c for c in json.loads((d / "claim_ledger.json").read_text())}
    assert led["C1"]["decision"] == "not_assessed" and led["C2"]["status"] == "not_supported"
    assert v["engineering_status"] == "invalid" and v["exit_code"] == cli.EXIT_INVALID


def test_valid_run_presents_every_archive_and_samples_without_gaps(run):
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_OK, cli.EXIT_OK)
    assert not any("unavailable" in e.get(m, {}) for e in json.loads((run / "ledgers.json").read_text())
                   for m in ("hid_full", "baseline_best"))
    sp = v["separate_process_decode"]
    assert sp["all_ok"] and sp["sampled"] > 0 and "unavailable" not in sp and "failed" not in sp


def test_missing_archive_writes_invalid_records_and_replaces_a_stale_success(run):
    assert cli.main(["verify", "--run-id", RID]) == cli.EXIT_OK
    stale = json.loads((run / "verification.json").read_text())
    assert stale["engineering_status"] == "valid"
    row = next(r for r in _rows(run) if r["case_id"] == FIRST and r["method"] == "hid_full")
    (run / row["archive_path"]).unlink()
    val, _ = V.validate_run(RID, ["confirmation", "transfer"])
    assert not val["engineering_valid"]
    assert any(f"{FIRST}:hid_full archive file missing" == x for x in val["invalid"])
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    _assert_nothing_claims_success(run, s, v)
    assert _ledger_item(run, FIRST, "hid_full")["unavailable"] == "archive file missing"
    assert f"{FIRST}:hid_full archive file missing" in v["invalid_reasons"]
    sp = v["separate_process_decode"]
    assert not sp["all_ok"] and f"{FIRST}:hid_full archive file missing" in sp["unavailable"]
    assert v["started_utc"] >= stale["started_utc"] and v != stale


def test_malformed_archive_claimed_by_its_row_is_invalid_everywhere(run):
    rows = _rows(run)
    r = next(r for r in rows if r["case_id"] == FIRST and r["method"] == "hid_full")
    bad = (run / r["archive_path"]).read_bytes()[:-1]          # truncated payload
    rel, h = _store(run, bad)
    r.update(archive_path=rel, archive_sha256=h, archive_bits=8 * len(bad))
    _write(run, rows)
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    _assert_nothing_claims_success(run, s, v)
    assert f"{FIRST}:hid_full decoder raised ArchiveError" in v["invalid_reasons"]
    assert _ledger_item(run, FIRST, "hid_full")["unavailable"].startswith(
        "archive does not decode: ArchiveError")
    sp = v["separate_process_decode"]
    assert not sp["all_ok"] and any(x.startswith(f"{FIRST}:hid_full ArchiveError")
                                    for x in sp["failed"])


def test_corrupted_archive_bytes_are_invalid_and_never_presented(run):
    r = next(r for r in _rows(run) if r["case_id"] == FIRST and r["method"] == "hid_full")
    (run / r["archive_path"]).write_bytes(b"not an archive")
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    _assert_nothing_claims_success(run, s, v)
    assert f"{FIRST}:hid_full archive hash differs from the row" in v["invalid_reasons"]
    assert _ledger_item(run, FIRST, "hid_full")["unavailable"] == \
        "archive hash differs from the row"
    assert not v["separate_process_decode"]["all_ok"]


def test_programmer_error_in_verify_propagates_and_leaves_no_stale_success(run, monkeypatch):
    assert cli.main(["verify", "--run-id", RID]) == cli.EXIT_OK

    def boom(*a, **k):
        raise ZeroDivisionError("planted")
    monkeypatch.setattr(R, "summarise", boom)
    with pytest.raises(ZeroDivisionError, match="planted"):
        cli.main(["verify", "--run-id", RID])
    v = json.loads((run / "verification.json").read_text())
    assert v["engineering_status"] == "not_verified" and v["exit_code"] is None


@pytest.mark.parametrize("damage,needle", [
    (lambda rec: rec + [rec[0]], "appears 2 times"),                          # identical
    (lambda rec: rec + [dict(rec[0], archive_bits=8)], "appears 2 times"),    # conflicting
    (lambda rec: {"rows": rec}, "not a list of rows"),
    (lambda rec: rec + ["row"], "not a row object"),
    (lambda rec: rec + [dict(rec[0], method="hid_mystery")], "not in the declared design"),
    (lambda rec: [dict(rec[0], replicate=1001)] + rec[1:], "field replicate=1001"),
])
def test_malformed_rows_file_is_invalid_before_it_is_keyed(run, damage, needle):
    p = run / "rows" / f"{FIRST}.json"
    p.write_text(json.dumps(damage(json.loads(p.read_text()))))
    val, _ = V.validate_run(RID, ["confirmation", "transfer"])
    assert not val["engineering_valid"]
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    _assert_nothing_claims_success(run, s, v)
    assert any(x.startswith(f"{FIRST}: rows file") and needle in x
               for x in v["invalid_reasons"]), v["invalid_reasons"][:5]


def test_undeclared_split_row_is_validated_not_filtered(run):
    rows = _rows(run)
    extra = dict(rows[0], split="undeclared", case_id="undeclared-F01-64-1000-base")
    with (run / "cases.jsonl").open("a") as stream:
        stream.write(json.dumps(extra) + "\n")
    val, ctx = V.validate_run(RID, ["confirmation", "transfer"])
    assert ctx["scope"] == "whole_run"
    assert not val["engineering_valid"] and val["unknown"] == [
        f"undeclared-F01-64-1000-base:{rows[0]['method']}"]
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    _assert_nothing_claims_success(run, s, v)
    assert v["validation"]["unknown"] == val["unknown"]


def test_undeclared_rows_file_is_invalid(run):
    shutil.copy(run / "rows" / f"{FIRST}.json", run / "rows" / "undeclared-F01-64-1000-base.json")
    rc, s, vc, v = _report_and_verify(run)
    assert (rc, vc) == (cli.EXIT_INVALID, cli.EXIT_INVALID)
    assert any("rows/undeclared-F01-64-1000-base.json is not a declared case" in x
               for x in v["invalid_reasons"])


def test_a_split_subset_is_not_a_partial_acceptance(run):
    val, ctx = V.validate_run(RID, ["confirmation"])
    transfer = [u for u in val["unknown"] if u.startswith("transfer-")]
    assert not val["engineering_valid"] and len(transfer) == 2 * len(B.ALL_METHODS)
    assert sum("is not a declared case of ['confirmation']" in x for x in val["invalid"]) == 2
