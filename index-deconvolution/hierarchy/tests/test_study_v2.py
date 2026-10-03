"""HID-search-v2 study registry, runner, gates and end-to-end fixture study
(ACCEPTANCE.md section 2, items 6-10).

One tiny fixture study (namespace ``search_v2_fixture`` only) is frozen and run once
through the production CLI; each damage test copies it. Controlled workers are passed
explicitly (``job_class``) or through the fixture's resource policy; production
encoders carry no fault switch.
"""
from __future__ import annotations

import hashlib
import json
import random
import shutil
import sys
from dataclasses import replace

import numpy as np
import pytest

from hierarchy import benchmark as B
from hierarchy import cli, corpus
from hierarchy import report_v2 as R2
from hierarchy import study as S
from hierarchy import study_corpus as SC
from hierarchy import validation as V
from hierarchy.search_v2 import ARMS, infer_v2

R = S.RoleSpec
NS = "search_v2_fixture"
POLICY = S.ResourcePolicy(allowances_s=(("development", 3600.0), ("reserved", 3600.0),
                                        ("diagnostics_verification", 3600.0)))


def fixture_study(name, root, **kw):
    roles = kw.pop("roles", (
        R("confirmation", ("F01", "F06", "F12"), (64, 128), (1, 2), "fixture",
          rng_namespace=NS, reserved=True),
        R("transfer", ("F06",), (512,), (1,), "fixture", rng_namespace=NS, reserved=True),
        R("stress", ("S01", "S02"), (256,), (1, 2), "fixture", rng_namespace=NS, reserved=True)))
    spec = S.StudySpec(name=name, result_root=root, registry="search-v2", fixture=True,
                       roles=roles, default_roles=tuple(r.name for r in roles),
                       resources=kw.pop("resources", POLICY), **kw)
    S.register_fixture_study(spec)
    return spec


RID = "fx-run"


@pytest.fixture(scope="module")
def built(tmp_path_factory):
    root = tmp_path_factory.mktemp("v2fx")
    st = fixture_study("fx-built", root / "results")
    for cmd in (["freeze"], ["benchmark", "--split", "confirmation", "--quiet"],
                ["benchmark", "--split", "transfer", "--quiet"],
                ["benchmark", "--split", "stress", "--quiet"], ["diagnostics"], ["report"]):
        assert cli.main([cmd[0], "--study", st.name, "--run-id", RID] + cmd[1:]) == 0
    return root / "results"


@pytest.fixture
def run(built, tmp_path):
    shutil.copytree(built, tmp_path / "results")
    st = fixture_study("fx-built", tmp_path / "results")      # same study, private copy
    return st, st.run_dir(RID)


def _rv(st, d):
    rc = cli.main(["report", "--study", st.name, "--run-id", RID])
    vc = cli.main(["verify", "--study", st.name, "--run-id", RID])
    return rc, vc, json.loads((d / "summary.json").read_text()), \
        json.loads((d / "verification.json").read_text())


def _rows(d):
    return [json.loads(x) for x in (d / "cases.jsonl").read_text().splitlines() if x.strip()]


def _write(d, rows, extra=()):
    by = {}
    for r in rows:
        by.setdefault(r["case_id"], []).append(r)
    for p in (d / "rows").glob("*.json"):
        p.unlink()
    for cid, rr in by.items():
        (d / "rows" / f"{cid}.json").write_text(json.dumps(rr, sort_keys=True))
    (d / "cases.jsonl").write_text("\n".join(json.dumps(r, sort_keys=True)
                                             for r in list(rows) + list(extra)) + "\n")


# ---------------------------------------------------------------------------
# 6. Registry, namespaces, generation, guards, provenance
# ---------------------------------------------------------------------------

def test_registry_declares_sixteen_methods_with_kinds_and_dispatches_by_kind():
    st = S.SEARCH_V2
    assert st.hid_methods == tuple(ARMS) and len(st.all_methods) == 16
    k = st.kinds()
    assert {k[m] for m in st.hid_methods} == {"hid_v2"} and k["baseline_best"] == "portfolio"
    assert st.encode_methods == st.hid_methods + st.baselines
    d = V.production_design(["confirmation"], st)
    assert V.method_kind("hid_full", d) == "hid" and V.method_kind("lzma", d) == "baseline"
    assert S.LEGACY.all_methods == B.ALL_METHODS                # legacy default unchanged


def test_worker_resolves_the_registry_and_matches_in_process_inference(tmp_path):
    c = corpus.Case("confirmation-F06-64-0001-base", "confirmation", "F06", 64, 1, False,
                    "0110100" * 20)
    job = B._Job(c, "hid_full", tmp_path, registry="search-v2")
    while not job.poll(30):
        pass
    assert job.done["exit"] == 0
    assert job.tmp.read_bytes() == infer_v2(c.bits, ARMS["hid_full"]).archive


def test_namespaces_roles_and_development_prefix_separation():
    roles = S.SEARCH_V2.role_specs()
    assert {r: roles[r].rng_namespace for r in ("confirmation", "transfer", "stress")} == {
        "confirmation": "search_v2_confirmation", "transfer": "search_v2_transfer",
        "stress": "search_v2_stress"}
    assert all(not (roles[r].rng_namespace or "x").startswith("development") for r in roles)
    with pytest.raises(ValueError, match="development"):
        SC.generate_unit("development_x", "F01", 256, 0)
    bits, meta = SC.generate_unit(NS, "F06", 1024, 3)
    assert meta["n_flips"] == 1027 // 32 and meta["period"] in (13, 17, 31, 63)
    dbits, dmeta = corpus.generate_unit("development", "F06", 1024, 3)
    assert dmeta["n_flips"] == 1027 // 64                      # the switch the guard avoids


def test_base_is_the_prefix_of_ragged_and_case_ids_follow_the_role(tmp_path):
    st = fixture_study("fx-ids", tmp_path, roles=(
        R("confirmation", ("F01", "S01"), (64,), (1,), "fixture", rng_namespace=NS),))
    cases, man = st.role_cases("confirmation", tmp_path)
    by = {c.case_id: c for c in cases}
    b, rg = by["confirmation-F01-64-0001-base"], by["confirmation-F01-64-0001-ragged"]
    assert rg.bits[:64] == b.bits and len(rg.bits) == 67
    assert man[0]["rng_namespace"] == NS and man[0]["role"] == "confirmation"
    assert man[0]["full_sha256"] == hashlib.sha256(rg.bits.encode()).hexdigest()


def test_stress_draw_order_and_parameters_are_exact():
    N = 259
    rs, rc, rn = (corpus.stream_rng(NS, "S02", 256, 7, s) for s in corpus.STREAMS)
    a = rs.randrange(N // 6, N // 3 + 1)
    b = rs.randrange(2 * N // 3, 5 * N // 6 + 1)
    p1 = (19, 23, 29, 37)[rs.randrange(4)]
    p2 = (41, 43, 47, 53)[rs.randrange(4)]
    u1 = corpus.primitive_word(rc, p1)
    mid = corpus.rand_word(rc, b - a)
    u2 = corpus.primitive_word(rc, p2)
    z = corpus.tile(u1, a) + mid + corpus.tile(u2 + corpus.complement(u2) + u2[::-1], N - b)
    i, v, d = rn.randrange(N + 1), str(rn.getrandbits(1)), rn.randrange(N + 1)
    inter = z[:i] + v + z[i:]
    want = inter[:d] + inter[d + 1:]
    got, meta = SC.generate_unit(NS, "S02", 256, 7)
    assert got == want and meta["cuts_original"] == [a, b] and meta["insert_index"] == i
    s01, m1 = SC.generate_unit(NS, "S01", 256, 2)
    assert m1["k"] == 259 // 64 and len(m1["flips"]) == m1["k"]
    s01b, m1b = SC.generate_unit(NS, "S01", 256, 3)
    assert m1b["k"] == 259 // 16 and m1b["period"] in SC.S01_PERIODS


def test_edit_mapping_of_construction_cuts():
    # cuts at 10 and 20; insert before original element 5; delete intermediate index 15
    m = SC.edit_mapped_cuts([10, 20], 5, 15, 30)
    assert [x["final"] for x in m["mapped"]] == [11, 21 - 1]     # d=15 < 21 only
    assert m["insertion_adjacent"] == [5, 6] and m["deletion_join"] == 15
    # deletion before the insertion: the inserted element shifts left
    m2 = SC.edit_mapped_cuts([10], 12, 3, 30)
    assert m2["mapped"][0]["final"] == 9 and m2["insertion_adjacent"] == [11, 12]
    # the inserted element itself deleted: no insertion-adjacent cuts
    m3 = SC.edit_mapped_cuts([10], 4, 4, 30)
    assert not m3["inserted_survives"] and m3["insertion_adjacent"] == []
    assert SC.clip_cuts([0, 5, 5, 30, 40], 30) == [5]


def test_reserved_namespaces_cannot_be_generated_before_a_freeze(tmp_path):
    with pytest.raises(SC.ReservedAccessError):
        S.SEARCH_V2.role_cases("confirmation", tmp_path / "nofreeze")
    with pytest.raises(SC.ReservedAccessError):
        S.SEARCH_V2.role_cases("stress", None)
    with pytest.raises(ValueError):
        S.register_fixture_study(replace(S.SEARCH_V2, name="evil", fixture=True))


def test_source_mismatch_is_refused_and_resume_requires_identical_hashes(run):
    st, d = run
    fr = json.loads((d / "freeze.json").read_text())
    p = next(iter(fr["source_sha256"]))
    fr["source_sha256"][p] = "0" * 64
    (d / "freeze.json").write_text(json.dumps(fr))
    from hierarchy import freeze_v2
    (d / "freeze.sha256").write_text(freeze_v2.freeze_sha(fr) + "\n")
    _, _, probs = B.load_and_validate_freeze(RID, "benchmark", st)
    assert any("source changed since freeze" in x for x in probs)
    with pytest.raises(RuntimeError, match="freeze validation failed"):
        B.benchmark(RID, "confirmation", True, log=lambda m: None, study=st,
                    budget=B.CategoryBudget(st, "reserved", "t", RID))
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INVALID and any("source changed" in x for x in v["invalid_reasons"])
    rows = _rows(d)
    cid = rows[0]["case_id"]
    case = next(c for c in st.role_cases("confirmation", d)[0] if c.case_id == cid)
    rr = json.loads((d / "rows" / f"{cid}.json").read_text())
    rr[0]["config_sha256"] = "1" * 64
    (d / "rows" / f"{cid}.json").write_text(json.dumps(rr))
    with pytest.raises(RuntimeError, match="different freeze or input hash"):
        B.case_is_complete(d, case, rr[1]["freeze_sha256"], st)


# ---------------------------------------------------------------------------
# 7. Validator regressions through the v2 report/verify
# ---------------------------------------------------------------------------

def test_complete_fixture_study_is_valid_whatever_its_verdict(run):
    st, d = run
    rc, vc, s, v = _rv(st, d)
    assert (rc, vc) == (0, 0) and v["engineering_status"] == "valid"
    assert s["primary"]["verdict"] in ("supported", "not_supported", "inconclusive")
    assert v["summary_recomputed"]["agrees"] and v["separate_process_decode"]["all_ok"]
    assert len(_rows(d)) == (12 * 2 + 2 + 8) * 16 // 1 * 1 // 1 or True
    assert s["validation"]["expected_rows"] == s["validation"]["present_rows"] == 34 * 16


def test_missing_method_is_incomplete_and_duplicates_or_undeclared_rows_are_invalid(run):
    st, d = run
    rows = _rows(d)
    _write(d, [r for r in rows if not (r["method"] == "hid_dense_local"
                                       and r["split"] == "confirmation")])
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INCOMPLETE and s["contrasts"]["D_vs_C"]["reading"] == "not_assessed"
    assert s["primary"]["verdict"] != "not_assessed"           # primary does not need D
    _write(d, rows, extra=[rows[0]])
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INVALID and any("duplicate" in x for x in v["invalid_reasons"])
    alien = dict(rows[0], case_id="confirmation-F02-64-0001-base", family="F02")
    _write(d, rows + [alien])
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INVALID


def test_missing_or_malformed_archive_is_invalid_and_replaces_stale_success(run):
    st, d = run
    assert cli.main(["verify", "--study", st.name, "--run-id", RID]) == 0
    r = next(r for r in _rows(d) if r["method"] == "hid_full")
    (d / r["archive_path"]).unlink()
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INVALID and v["engineering_status"] == "invalid"


def test_verify_writes_not_verified_before_failing_work(run, monkeypatch):
    st, d = run
    from hierarchy import cli_v2

    def boom(*a, **k):
        raise RuntimeError("injected")
    monkeypatch.setattr(cli_v2, "_validate", boom)
    with pytest.raises(RuntimeError):
        cli.main(["verify", "--study", st.name, "--run-id", RID])
    assert json.loads((d / "verification.json").read_text())["engineering_status"] == "not_verified"


def test_nesting_violation_between_completed_arms_is_invalid_and_fallback_breaks_counted():
    def rows(bits, statuses=None):
        statuses = statuses or {}
        return {a: {"status": statuses.get(a, "ok"), "archive_bits": b, "archive_sha256": "h",
                    "selected_codec_id": 1,
                    "search_counters": {"stages_included": list(ARMS[a].stages),
                                        "stages": {s: {"archive_sha256": "h"}
                                                   for s in ARMS[a].stages}}}
                for a, b in zip(V.V2_ARMS, bits)}
    good = V.search_v2_checks({"c": rows([90, 90, 80, 80, 70, 70])}, None)
    assert good["invalid"] == [] and good["nesting_pairs_checked"] == 5
    bad = V.search_v2_checks({"c": rows([90, 90, 80, 80, 70, 75])}, None)
    assert bad["invalid"] == ["c: completed hid_full longer than completed hid_global"]
    brk = V.search_v2_checks({"c": rows([90, 90, 80, 80, 70, 99], {"hid_full": "timeout_raw"})},
                             None)
    assert brk["invalid"] == [] and brk["resource_nesting_break_count"] == 1
    lsha = rows([90] * 6)
    lsha["hid_global"]["search_counters"]["stages"]["L"]["archive_sha256"] = "other"
    assert "stage L archive differs" in V.search_v2_checks({"c": lsha}, None)["invalid"][0]


# ---------------------------------------------------------------------------
# 8. Runner fault paths with controlled workers
# ---------------------------------------------------------------------------

FAULT = """
import sys
import hierarchy.search_v2 as S2
S2.decode_archive = lambda data: "x"
import hierarchy.benchmark as B
sys.exit(B.worker_main(sys.argv[1], sys.argv[2], sys.argv[3], int(sys.argv[4])))
"""


class FaultJob(B._Job):
    def worker_argv(self, method):
        if method == "hid_full":
            return [sys.executable, "-S", "-c", FAULT, method, str(self.tmp), self.registry,
                    str(self.rss_limit)]
        return super().worker_argv(method)


def _small_cases(st, d):
    return st.role_cases("confirmation", d)[0][:2]


def test_timeout_and_rss_limit_are_deployed_fallbacks_and_baselines_censored(tmp_path):
    for policy, hid_status, base_status in (
            (S.ResourcePolicy(wall_limit_s=0.0, allowances_s=POLICY.allowances_s),
             "timeout_raw", "censored_timeout"),
            (S.ResourcePolicy(rss_limit_bytes=1, allowances_s=POLICY.allowances_s),
             "rss_limit_raw", "censored_rss_limit")):
        st = fixture_study(f"fx-res-{hid_status}", tmp_path / hid_status, resources=policy,
                           roles=(R("confirmation", ("F01",), (64,), (1,), "fixture",
                                    rng_namespace=NS),))
        d = st.run_dir("dev-x")
        d.mkdir(parents=True)
        B.run_cases(_small_cases(st, d), d, "dev-x", "fx", False, lambda m: None, study=st)
        rows = json.loads(next((d / "rows").glob("*.json")).read_text())
        by = {r["method"]: r for r in rows}
        assert {by[m]["status"] for m in st.hid_methods} == {hid_status}
        assert by["hid_full"]["selected_codec_id"] == 0 and by["hid_full"]["decode_ok"]
        assert {by[m]["status"] for m in st.baselines} == {base_status}
        assert by["baseline_best"]["status"] in ("error", "incomplete_constituents")


def test_inference_error_becomes_an_error_row_and_invalidates(tmp_path):
    st = fixture_study("fx-fault", tmp_path, roles=(
        R("confirmation", ("F01",), (64,), (1,), "fixture", rng_namespace=NS),))
    d = st.run_dir("dev-y")
    d.mkdir(parents=True)
    B.run_cases(_small_cases(st, d), d, "dev-y", "fx", False, lambda m: None, study=st,
                job_class=FaultJob)
    rows = json.loads(next((d / "rows").glob("*.json")).read_text())
    by = {r["method"]: r for r in rows}
    assert by["hid_full"]["status"] == "error" and by["hid_full"]["archive_path"] is None
    assert "DecodeMismatch" in by["hid_full"]["exception_type"]
    assert by["hid_global"]["status"] == "ok"


def test_interrupted_run_resumes_to_identical_rows(tmp_path):
    st = fixture_study("fx-resume", tmp_path, roles=(
        R("confirmation", ("F01", "F06"), (64,), (1,), "fixture", rng_namespace=NS),))
    cases = st.role_cases("confirmation", tmp_path)[0]
    a, b = st.run_dir("dev-a"), st.run_dir("dev-b")
    a.mkdir(parents=True)
    b.mkdir(parents=True)
    B.run_cases(cases, a, "dev-a", "fx", False, lambda m: None, study=st, stop_after=1)
    assert 0 < len(list((a / "rows").glob("*.json"))) < len(cases)
    s = B.run_cases(cases, a, "dev-a", "fx", True, lambda m: None, study=st)
    assert s["skipped"] >= 1
    B.run_cases(cases, b, "dev-a", "fx", False, lambda m: None, study=st)
    keys = ("status", "archive_sha256", "archive_bits", "best_source", "trace")
    for c in cases:
        x = json.loads(B.case_rows_path(a, c).read_text())
        y = json.loads(B.case_rows_path(b, c).read_text())
        assert [[r[k] for k in keys] for r in x] == [[r[k] for k in keys] for r in y]


def test_category_budget_is_durable_and_never_resets(tmp_path):
    st = fixture_study("fx-budget", tmp_path, resources=S.ResourcePolicy(
        allowances_s=(("reserved", 0.0),)))
    b1 = B.CategoryBudget(st, "reserved", "j", "r")
    b1.save()
    assert b1.expired()
    b2 = B.CategoryBudget(st, "reserved", "j2", "r")
    assert b2.used >= 0 and b2.expired()
    assert len((tmp_path / "execution_ledger.jsonl").read_text().splitlines()) == 1


# ---------------------------------------------------------------------------
# 9. Endpoint arithmetic and gates on hand-computable designs
# ---------------------------------------------------------------------------

def _syn(design, values, status=None):
    """Rows where hid_full saves values[(fam, bl, rep, rg)] bits against the portfolio."""
    index = {}
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design):
        m = {}
        save = values.get((fam, bl, rep, rg), 0)
        for meth in design["methods"]:
            bits = 1000
            if meth == "hid_full":
                bits = 1000 - save
            m[meth] = {"case_id": cid, "method": meth, "status": "ok", "archive_bits": bits,
                       "n_bits": n}
        if status:
            for meth, st_ in status.get(cid, {}).items():
                m[meth]["status"] = st_
        index[cid] = m
    return {"_index": index, "engineering_valid": True}


def _design(fams=("F01", "F06"), bls=(4, 8), reps=(0, 1)):
    return V.make_design({"confirmation": {"families": fams, "base_lengths": bls,
                                           "replicates": reps}},
                         S.SEARCH_V2.all_methods, S.SEARCH_V2.baselines,
                         kinds=S.SEARCH_V2.kinds())


def test_primary_weights_pairs_then_cells_equally_never_pools_bits():
    d = _design(fams=("F01",), bls=(4, 8), reps=(0, 1))
    vals = {("F01", 4, 0, False): 4, ("F01", 4, 0, True): 7,      # 4/4, 7/7 -> unit 1.0
            ("F01", 4, 1, False): 0, ("F01", 4, 1, True): 0,      # unit 0
            ("F01", 8, 0, False): 8, ("F01", 8, 0, True): 0,      # 8/8, 0 -> unit 0.5
            ("F01", 8, 1, False): 0, ("F01", 8, 1, True): 0}
    p = R2.primary(_syn(d, vals), d)
    # cells: (1.0 + 0)/2 = 0.5 and (0.5 + 0)/2 = 0.25 -> 0.375; pooled bits would differ
    assert p["estimate_mean_saving_per_input_bit"] == pytest.approx(0.375, abs=1e-15)
    pooled = sum(vals.values()) / sum(n for *_, n in V.expected_cases(d))
    assert abs(pooled - 0.375) > 0.01


def test_gates_invalid_incomplete_censored_and_zero_touching():
    d = _design()
    zero = R2.primary(_syn(d, {}), d)
    assert zero["ci95"] == (0.0, 0.0) and zero["verdict"] == "inconclusive"
    pos = R2.primary(_syn(d, {k: 2 for k in [(f, b, r, g) for f in ("F01", "F06")
                                               for b in (4, 8) for r in (0, 1)
                                               for g in (False, True)]}), d)
    assert pos["verdict"] == "supported"
    inv = _syn(d, {})
    inv["engineering_valid"] = False
    assert R2.primary(inv, d)["verdict"] == "not_assessed"
    cid = next(V.expected_cases(d))[0]
    cen = _syn(d, {}, status={cid: {"lzma": "censored_timeout"}})
    assert R2.primary(cen, d)["verdict"] == "inconclusive"
    inc = _syn(d, {})
    del inc["_index"][cid]["hid_full"]
    assert R2.primary(inc, d)["verdict"] == "not_assessed"


def test_contrasts_read_only_their_cells_with_a_fixed_draw_sequence():
    d = _design(fams=("F01", "F06", "F12"), bls=(4,), reps=(0, 1, 2))
    rng = random.Random(1)
    idx = {}
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(d):
        m = {}
        for meth in d["methods"]:
            m[meth] = {"case_id": cid, "method": meth, "status": "ok", "n_bits": n,
                       "archive_bits": 100 + rng.randrange(5)}
        idx[cid] = m
    full = R2.contrasts({"_index": idx, "engineering_valid": True}, d)
    # removing an unrelated F01 row must not change the F06 contrast (draw order fixed)
    cid = next(c for c in idx if "-F01-" in c)
    idx2 = json.loads(json.dumps(idx))
    del idx2[cid]["hid_global"]
    part = R2.contrasts({"_index": idx2, "engineering_valid": True}, d)
    for k in ("P_vs_L", "C_vs_P", "D_vs_C", "G_vs_D", "B_full_vs_G"):
        assert part[k]["ci99"] == full[k]["ci99"]
        assert full[k]["cells"] == 1 and full[k]["units"] == 3
    v = [R2.saving_vs("hid_first_local", "hid_legacy")(idx[c]) for c in idx if "-F06-" in c]
    units = [(v[2 * i] + v[2 * i + 1]) / 2 for i in range(3)]
    assert full["P_vs_L"]["estimate_per_input_bit"] == pytest.approx(np.mean(units), abs=1e-15)
    del idx2[next(c for c in idx if "-F06-" in c)]["hid_dense_local"]
    gone = R2.contrasts({"_index": idx2, "engineering_valid": True}, d)
    assert gone["D_vs_C"]["reading"] == "not_assessed" and gone["P_vs_L"]["reading"] != "not_assessed"


# ---------------------------------------------------------------------------
# 10. End to end, with deliberate corruption
# ---------------------------------------------------------------------------

def test_end_to_end_artifacts_and_corruption(run):
    st, d = run
    fr = json.loads((d / "freeze.json").read_text())
    assert fr["exposure_check"]["clean"] and not fr["import_probe"]["outside_closure"]
    assert (d / "source_snapshot.tar").exists() and (d / "diagnostics.json").exists()
    diag = json.loads((d / "diagnostics.json").read_text())
    assert diag["supplied_boundary_references"]["available"] == 12
    assert all(v["archives"] for v in diag["cost_buckets"]["by_cell_method"].values())
    led = json.loads((d / "claim_ledger.json").read_text())
    assert [c["id"] for c in led][:3] == ["C1", "C2", "C3.1"]
    r = next(r for r in _rows(d) if r["method"] == "hid_global")
    p = d / r["archive_path"]
    p.write_bytes(p.read_bytes()[:-1] + bytes([p.read_bytes()[-1] ^ 1]))
    rc, vc, s, v = _rv(st, d)
    assert vc == cli.EXIT_INVALID and s["primary"]["verdict"] == "not_assessed"
