"""HID-search-v3a: multi-seed boundary schedule, observer trace, runner, gates, primary
arithmetic (protocols/hierarchy_search_v3a/ACCEPTANCE.md section 1).

Schedule fixtures use ``Priced``: the real ``BoundarySearch.run`` over a hand-written
price table (the archive of a partition is its cut list padded to the table's length),
so every ranking, pool and commit is computable by hand. Cap fixtures use the real
leaf builder and serializer. Watchdog fixtures use deliberately tiny limits on the
real ``_Job`` worker and are labelled as such. Only the ``search_v3a_fixture``
namespace is generated.
"""
from __future__ import annotations

import hashlib
import json
import math
import shutil

import numpy as np
import pytest

from hierarchy import benchmark as B
from hierarchy import freeze_v2
from hierarchy import report as R
from hierarchy import report_v3a as R3
from hierarchy import segmentation as SG
from hierarchy import study as S
from hierarchy import study_corpus as SC
from hierarchy import validation as V
from hierarchy.search_v2 import ARMS, infer_v2
from hierarchy.search_v3a import ARMS_V3A, REFINE4, infer_v3a
from hierarchy.segmentation import (BoundaryConfig, BoundaryPolicy, BoundarySearch,
                                    TraceObserver, _Cap)

NS = "search_v3a_fixture"


# ---------------------------------------------------------------------------
# Hand-priced search
# ---------------------------------------------------------------------------

class Priced(BoundarySearch):
    """Real ``run``/``_request``; ``evaluate`` prices a partition from ``table``
    (missing -> ``default``; ``None`` -> graph rejection). Root-trial cap and cache
    semantics are the owner's; leaves are not used."""

    def __init__(self, n, table, k=1, default=1000, observer=None, **cfg):
        super().__init__("0" * n, BoundaryConfig(**cfg), BoundaryPolicy(k), observer)
        self.table, self.default, self.calls = table, default, []

    def evaluate(self, cuts):
        if cuts in self.parts:
            return self.parts[cuts]
        if self.counts["root_trials"] + 1 > self.cfg.root_trial_cap:
            raise _Cap("root_trial_cap")
        self.counts["root_trials"] += 1
        self.calls.append(cuts)
        price = self.table.get(cuts, self.default)
        if price is None:
            self.counts["graph_rejections"] += 1
            self.parts[cuts] = None
            return None
        enc = b"".join(c.to_bytes(4, "big") for c in cuts)
        arc = enc + b"\0" * (price - len(enc))
        self.parts[cuts] = arc
        self.seq += 1
        if self.best_seen is None or len(arc) < self.best_seen[0]:
            self.best_seen = (len(arc), self.seq, arc, cuts)
        return arc


def coarse(a, b):
    return sorted(c for c in {a + 1, b - 1} | {a + (j * (b - a)) // 32 for j in range(1, 32)}
                  if a < c < b)


def ref_positions(c, lo, hi, step):
    return sorted(p for p in {lo, hi, c} | {c + j * step for j in range(-8, 9)} if lo <= p <= hi)


def test_coarse_rank_dedup_and_fewer_than_four_seeds():
    # n=64: one parent; coarse cuts 1,2,...,63 (33 distinct incl. ends). Two prices tie.
    t = {(32,): 200, (2,): 200, (40,): 210}
    s = Priced(64, t, k=4, max_segments=2)
    out = s.run()
    seeds = s.rounds[0]["seeds"]
    # ties ranked by (length, parent start, cut): cut 2 before cut 32
    assert [sd["coarse_cut"] for sd in seeds[:3]] == [2, 32, 40]
    assert len(seeds) == 4 and seeds[3]["coarse_bytes"] == 1000
    assert out["stop_reason"] == "max_segments" and out["cuts"] == [2]
    # fewer than four admissible: everything else is a graph rejection
    rej = {(c,): None for c in coarse(0, 64)}
    rej.update({(10,): 300, (20,): 310})
    s2 = Priced(64, rej, k=4, max_segments=2)
    s2.run()
    assert [sd["coarse_cut"] for sd in s2.rounds[0]["seeds"]] == [10, 20]
    # zero admissible: the old outcome
    s3 = Priced(64, {(c,): None for c in coarse(0, 64)}, k=4)
    assert s3.run()["stop_reason"] == "no_admissible_trial"


def test_same_parent_seeds_independent_pools_and_level_major_order():
    n = 1024
    t = {(320,): 500, (640,): 510, (352,): 520, (608,): 530}
    t.update({(332,): 480, (652,): 470})          # on the level-1 grids of seeds 0 and 1
    obs = TraceObserver()
    s = Priced(n, t, k=4, observer=obs, max_segments=2)
    out = s.run()
    seeds = s.rounds[0]["seeds"]
    assert [sd["coarse_cut"] for sd in seeds] == [320, 640, 352, 608]
    assert all(sd["parent"] == [0, 1024] for sd in seeds)      # same parent, no diversity rule
    ref = [e for e in obs.events if e["phase"] == "refine"]
    # level-major then seed-rank-major: every level-1 request precedes every level-2 one,
    # and within a level the seeds appear in rank order, each completing its level
    lv = [(e["level"], e["seed_rank"]) for e in ref]
    assert lv == sorted(lv)
    # level 1 of seed 0 is exactly the hand-computed grid
    r = math.ceil(1024 / 32)
    lo, hi = 320 - r, 320 + r
    step = math.ceil((hi - lo) / 16)
    got = [e["cut"] for e in ref if e["level"] == 1 and e["seed_rank"] == 0]
    assert got == ref_positions(320, lo, hi, step)
    # pools are local: seed 0 centres on 330 (its own refinement), not on 650
    assert seeds[0]["refined_cut"] == 332 and seeds[1]["refined_cut"] == 652
    # seed 2 (352) evaluates 332 as a cache hit and keeps it; 652 is not in its pool
    assert seeds[2]["refined_cut"] == 332
    # global winner over every trial, strict commit
    assert out["cuts"] == [652] and s.rounds[0]["best_bytes"] == 470


def test_converging_seeds_are_not_merged_and_step_one_terminates():
    n = 1024
    t = {(320,): 500, (352,): 505, (336,): 400}    # both seeds converge on 336
    s = Priced(n, t, k=2, max_segments=2)
    s.run()
    sd = s.rounds[0]["seeds"]
    assert sd[0]["refined_cut"] == sd[1]["refined_cut"] == 336
    assert len(sd) == 2 and all(x["resolved_to_one_bit"] for x in sd)
    assert all(x["last_step"] == 1 and x["levels"] <= 5 for x in sd)


def test_boundary_clamping_and_five_level_limit():
    n = 64                                          # parent length 64: r = 2, tiny brackets
    t = {(1,): 100}
    s = Priced(n, t, k=1, max_segments=2)
    s.run()
    rnd = s.rounds[0]
    assert rnd["coarse_cut"] == 1 and rnd["last_bracket"][0] >= 1
    assert rnd["levels"] <= 5
    # five-level limit: max_refinement_levels counts
    s2 = Priced(4096, {(1024,): 100}, k=4, max_segments=2, max_refinement_levels=2)
    s2.run()
    assert all(x["levels"] <= 2 for x in s2.rounds[0]["seeds"])


def test_strict_commit_rejection_and_k4_can_finish_worse():
    n = 1024
    # round 1: k=1 refines only 320 (coarse best 900); k=4 also refines 640 and finds 656
    # (not a coarse cut); round 2 from {320} reaches 518 (= 320 + 22*9, a coarse cut of
    # [320, 1024)) but from {656} only 679 (= 656 + floor(2*368/32))
    t = {(320,): 900, (640,): 950, (656,): 850, (320, 518): 500, (656, 679): 840}
    k1 = Priced(n, t, k=1, max_segments=3).run()
    k4 = Priced(n, t, k=4, max_segments=3).run()
    assert k1["cuts"] == [320, 518] and k1["archive_bits"] == 8 * 500
    assert k4["committed_cuts"] == [656, 679] and k4["archive_bits"] == 8 * 840
    assert k4["archive_bits"] > k1["archive_bits"]          # wider refinement finished worse
    # strict commit: an equal-length best is not committed
    eq = Priced(n, {(): 1000}, k=4, default=1000)
    out = eq.run()
    assert out["stop_reason"] == "no_strict_improvement" and out["cuts"] == []


def test_cap_during_coarse_and_mid_seed_refinement_best_seen_and_unresolved():
    n = 1024
    t = {(160,): 700, (96,): 700, (320,): 600}
    # coarse cap: initial + 9 coarse trials -> the 10th request is blocked
    obs = TraceObserver()
    s = Priced(n, t, k=4, observer=obs, root_trial_cap=10)
    out = s.run()
    assert out["stop_reason"] == "root_trial_cap"
    assert out["unresolved_refinement"] == {"round": 1, "phase": "coarse"}
    # best seen among the 9 coarse cuts 1,32,...,256: 96 and 160 tie at 700 -> earliest (96)
    assert out["cuts"] == [96] and out["archive_bits"] == 8 * 700
    assert obs.events[-1]["outcome"] == "cap_blocked" and obs.events[-1]["cut"] == 288
    # mid-seed cap: allow all 33 coarse + a few refinements of seed 0
    obs2 = TraceObserver()
    s2 = Priced(n, t, k=4, observer=obs2, root_trial_cap=1 + 33 + 5)
    out2 = s2.run()
    u = out2["unresolved_refinement"]
    assert out2["stop_reason"] == "root_trial_cap"
    assert u["round"] == 1 and u["phase"] == "refinement" and u["seed_rank"] == 0
    assert u["current_level"] == 1 and u["levels_done"] == 0 and u["parent"] == [0, 1024]
    assert out2["cuts"] == [320]
    assert obs2.events[-1]["outcome"] == "cap_blocked"


@pytest.mark.parametrize("cap", [dict(cached_leaf_cap=6), dict(length_charge_multiplier=2),
                                 dict(root_trial_cap=40)])
def test_real_leaf_caps_best_seen_matches_trace(cap):
    from hierarchy.study_corpus import generate_unit
    x, _ = generate_unit(NS, "F12", 1024, 0)
    obs = TraceObserver()
    out = BoundarySearch(x, BoundaryConfig(**cap), BoundaryPolicy(4), obs).run()
    assert out["cap_hit"] and out["stop_reason"].endswith("_cap")
    new = [e for e in obs.events if e["outcome"] == "new_admissible"]
    best = min(new, key=lambda e: (e["archive_bytes"], e["position"]))   # earliest of a tie
    marks = [m for m in obs.summary if m["kind"] in ("initial", "commit")]
    cur = marks[-1]
    if best["archive_bytes"] < cur["archive_bytes"]:
        want = (best["archive_bytes"], best["partition"])
    else:
        want = (cur["archive_bytes"], cur["cuts"])
    assert (out["archive_bits"], out["cuts"]) == (8 * want[0], want[1])
    assert obs.events[-1]["outcome"] == "cap_blocked"
    if out["unresolved_refinement"]["phase"] == "refinement":
        assert {"seed_rank", "current_level", "current_bracket"} <= set(out["unresolved_refinement"])
    for a, b in zip(obs.events, obs.events[1:]):
        assert a["post"] == b["pre"]


def test_observer_on_off_identical_and_trace_matches_execution():
    from hierarchy.study_corpus import generate_unit
    x, _ = generate_unit(NS, "S02", 4096, 1)
    for k in (1, 4):
        a = BoundarySearch(x, BoundaryConfig(), BoundaryPolicy(k)).run()
        obs = TraceObserver()
        b = BoundarySearch(x, BoundaryConfig(), BoundaryPolicy(k), obs).run()
        assert a == b
        ev = obs.events
        assert sum(e["outcome"].startswith("new_") for e in ev) == b["counts"]["root_trials"]
        done = [e for e in ev if e["outcome"] != "cap_blocked"]
        assert sum(e["phase"] == "coarse" for e in done) == b["counts"]["coarse_trials"]
        assert sum(e["phase"] == "refine" for e in done) == b["counts"]["refine_trials"]
        assert len(ev) - len(done) == int(b["cap_hit"])
        assert not any(k_ in e for e in ev for k_ in ("family", "case_id", "replicate", "seed"))


def test_v3a_trace_sidecar_passes_trace_checks_and_k1_equals_infer_v2():
    from hierarchy.study_corpus import generate_unit
    x, _ = generate_unit(NS, "F12", 4096, 2)
    r1, side1 = infer_v3a(x, ARMS_V3A["hid_full"], trace=True)
    r0 = infer_v2(x, ARMS["hid_full"])
    assert r1.archive == r0.archive and r1.config_sha256 == r0.config_sha256
    r4, side4 = infer_v3a(x, REFINE4, trace=True)
    for res, side in ((r1, side1), (r4, side4)):
        row = {"config_sha256": res.config_sha256, "status": "ok",
               "archive_sha256": hashlib.sha256(res.archive).hexdigest(),
               "search_counters": res.telemetry}
        assert R3.trace_problems(side, row) == []
    assert side4["refinement_seed_count"] == 4 and r4.config_sha256 == REFINE4.sha256()


def test_hid_full_config_hash_is_the_frozen_search_v2_hash():
    from pathlib import Path
    fr = json.loads((Path(B.ID_ROOT) / "results/hierarchy_search_v2/search-confirm-v2-r1/"
                     "freeze.json").read_text())["method_configs"]["hid_full"]
    assert ARMS_V3A["hid_full"] is ARMS["hid_full"]
    assert ARMS["hid_full"].sha256() == fr["sha256"]
    assert ARMS["hid_full"].as_dict() == fr["config"]["search_config"]
    assert "refinement_seed_count" not in json.dumps(ARMS["hid_full"].as_dict())
    assert REFINE4.sha256() != ARMS["hid_full"].sha256()
    assert REFINE4.as_dict()["boundary_policy"]["refinement_seed_count"] == 4


def test_decode_disagreement_is_fatal(monkeypatch):
    from hierarchy.study_corpus import generate_unit
    x, _ = generate_unit(NS, "F12", 256, 3)
    monkeypatch.setattr(SG, "decode_archive", lambda a: "0")
    with pytest.raises(SG.DecodeMismatch):
        BoundarySearch(x, BoundaryConfig(), BoundaryPolicy(4)).run()


def test_trace_overflow_is_a_failure_not_truncation():
    from hierarchy.study_corpus import generate_unit
    x, _ = generate_unit(NS, "F12", 1024, 4)
    with pytest.raises(SG.TraceOverflow):
        BoundarySearch(x, BoundaryConfig(), BoundaryPolicy(4), TraceObserver(max_events=5)).run()


# ---------------------------------------------------------------------------
# Primary arithmetic on tiny analytical designs
# ---------------------------------------------------------------------------

def _design(units=20):
    roles = {"boundary": ("F12", (4096,)), "boundary_large": ("F12", (16384, 65536, 131072)),
             "boundary_stress": ("S02", (4096, 65536))}
    splits = {r: {"families": (f,), "base_lengths": bl, "replicates": tuple(range(units))}
              for r, (f, bl) in roles.items()}
    return V.make_design(splits, ("hid_full", "hid_refine4"), (),
                         kinds={"hid_full": "hid_v3a", "hid_refine4": "hid_v3a"})


def _index(design, fn):
    """fn(role, base_length, replicate, ragged) -> (full_bits, refine4_bits) or None."""
    idx = {}
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design):
        got = fn(sp, bl, rep, rg)
        if got is None:
            continue
        a, b = got
        idx[cid] = {m: {"status": "ok", "archive_bits": v, "n_bits": n}
                    for m, v in (("hid_full", a), ("hid_refine4", b))}
    return idx


def _val(idx, valid=True, complete=True):
    return {"_index": idx, "engineering_valid": valid, "complete": complete}


def test_six_cell_equal_weighting_ragged_n_and_fixed_bootstrap():
    d = _design()
    cell_val = {("boundary", 4096): 1, ("boundary_large", 16384): 2,
                ("boundary_large", 65536): 3, ("boundary_large", 131072): 4,
                ("boundary_stress", 4096): 5, ("boundary_stress", 65536): 6}

    def fn(sp, bl, rep, rg):
        n = bl + 3 if rg else bl
        return 10 * n, 10 * n - cell_val[(sp, bl)] * n * (1 + rep % 2)   # saving = v(1+rep%2)
    out = R3.decision(_val(_index(d, fn)), d)
    want = np.mean([v * 1.5 for v in cell_val.values()])                # equal cells, not strings
    assert out["estimate_bits_per_input_bit"] == pytest.approx(want, abs=1e-12)
    assert out["verdict"] == "SUPPORTED"
    # the bootstrap is the owner's, in lexicographic cell order, seed 55001
    cells = {k: np.asarray([[cell_val[(k[0], k[2])] * (1 + r % 2)] for r in range(20)], float)
             for k in sorted((r, "F12" if r != "boundary_stress" else "S02", b)
                             for r, b in cell_val)}
    draws = R.stratified_bootstrap(cells, 10000, 55001)
    lo, hi = np.quantile(draws[:, 0], 0.005), np.quantile(draws[:, 0], 0.995)
    assert out["ci99"] == [pytest.approx(lo, abs=0), pytest.approx(hi, abs=0)]
    assert out["bootstrap"]["cell_order"] == ["boundary|F12|4096", "boundary_large|F12|16384",
                                              "boundary_large|F12|65536",
                                              "boundary_large|F12|131072",
                                              "boundary_stress|S02|4096",
                                              "boundary_stress|S02|65536"]
    assert R3.decision(_val(_index(d, fn)), d) == out                   # fixed RNG and order


def test_actual_n_for_ragged_strings():
    d = _design()

    def fn(sp, bl, rep, rg):
        return (bl + 3 if rg else bl) * 2, (bl + 3 if rg else bl) * 2 - 3   # 3 bits saved
    out = R3.decision(_val(_index(d, fn)), d)
    want = np.mean([np.mean([3 / bl, 3 / (bl + 3)]) for bl in
                    (4096, 16384, 65536, 131072, 4096, 65536)])
    assert out["estimate_bits_per_input_bit"] == pytest.approx(want, rel=1e-12)


@pytest.mark.parametrize("delta,verdict", [(5, "SUPPORTED"), (-5, "HARMFUL"), (0, "INCONCLUSIVE")])
def test_verdict_branches(delta, verdict):
    d = _design()
    out = R3.decision(_val(_index(d, lambda sp, bl, rep, rg: (1000, 1000 - delta))), d)
    assert out["verdict"] == verdict
    if delta == 0:
        assert out["ci99"] == [0.0, 0.0]                              # equality at zero


def test_mixed_signs_inconclusive_and_precedence_invalid_then_incomplete():
    d = _design()
    out = R3.decision(_val(_index(d, lambda sp, bl, rep, rg: (1000, 1000 + (5 if rep % 2 else -5)))), d)
    assert out["verdict"] == "INCONCLUSIVE"
    missing = _index(d, lambda sp, bl, rep, rg: None if (rep == 3 and rg) else (1000, 990))
    inc = R3.decision(_val(missing, complete=False), d)
    assert inc["verdict"] == "INCOMPLETE" and "ci99" not in inc
    assert inc["available_units"] == 120 - 6                           # missing is never zero
    assert R3.decision(_val(missing, valid=False, complete=False), d)["verdict"] == "INVALID"


def test_raw_fallback_is_a_valid_cost_but_errors_are_not():
    d = _design()
    idx = _index(d, lambda sp, bl, rep, rg: (1000, 990))
    first = next(iter(idx))
    idx[first]["hid_refine4"]["status"] = "timeout_raw"
    assert R3.decision(_val(idx), d)["verdict"] == "SUPPORTED"
    idx[first]["hid_refine4"]["status"] = "error"
    assert R3.decision(_val(idx), d)["verdict"] == "INCOMPLETE"


# ---------------------------------------------------------------------------
# Registry, job order, reserved access
# ---------------------------------------------------------------------------

def test_registry_kinds_order_and_job_parity():
    st = S.get_study("search-v3a")
    assert st.all_methods == ("hid_full", "hid_refine4", "raw", "rle", "gaps", "period",
                              "bernoulli", "context", "zlib", "lzma", "pair_grammar",
                              "baseline_best")
    assert st.kinds()["hid_full"] == "hid_v3a" and st.method("hid_full").is_hid
    case = lambda rep: type("C", (), {"replicate": rep})()           # noqa: E731
    assert st.job_methods(case(6000))[:2] == ("hid_full", "hid_refine4")
    assert st.job_methods(case(7001))[:2] == ("hid_refine4", "hid_full")
    assert st.job_methods(case(6001))[2:] == st.baselines
    assert B.method_config_sha("hid_full", st) == ARMS["hid_full"].sha256()
    d = freeze_v2.design(st, "search-confirm-v3a-r1")
    assert d["expected_total_strings"] == 256 and d["expected_total_rows"] == 3072


def test_reserved_generation_requires_a_validated_freeze(tmp_path):
    st = S.get_study("search-v3a")
    with pytest.raises(SC.ReservedAccessError):
        st.role_cases("boundary", st.run_dir("search-confirm-v3a-r1"))     # no freeze yet
    fake = tmp_path / "search-confirm-v3a-r1"
    fake.mkdir()
    (fake / "freeze.json").write_text(json.dumps({"study": "search-v3a", "design": {
        "roles": {"boundary": {}}}}))
    with pytest.raises(SC.ReservedAccessError):
        st.role_cases("boundary", fake)                    # an existing file is not enough


# ---------------------------------------------------------------------------
# Real watchdog and the record-to-report pipeline (tiny fixture study)
# ---------------------------------------------------------------------------

FX_POLICY = S.ResourcePolicy(allowances_s=S.V3A_ALLOWANCES, total_budget_s=28800.0)


def fx_study(name, root, resources=FX_POLICY, reps=(0,)):
    roles = (S.RoleSpec("boundary", ("F12",), (256,), reps, "fixture", rng_namespace=NS,
                        reserved=True),)
    spec = S.V3aStudy(name=name, result_root=root, registry="search-v3a", roles=roles,
                      default_roles=("boundary",), resources=resources, fixture=True,
                      trace_sidecars=True)
    S.register_fixture_study(spec)
    return spec


def _run(st, rid="fx-v3a"):
    freeze_v2.write(st, rid, None)
    d = st.run_dir(rid)
    fr, fsha, problems = B.load_and_validate_freeze(rid, "benchmark", st)
    assert not problems
    cases, manifest = st.role_cases("boundary", d)
    B.atomic_write(d / "corpus_manifest.boundary.jsonl",
                   ("\n".join(json.dumps(m, sort_keys=True) for m in manifest) + "\n").encode())
    B.run_cases(cases, d, rid, fsha, False, lambda m: None, None, study=st)
    B._merge_outputs(d, st, rid)
    return d, cases, fsha


@pytest.fixture(scope="module")
def fx_built(tmp_path_factory):
    root = tmp_path_factory.mktemp("v3afx") / "results"
    st = fx_study("fx-v3a-built", root)
    d, cases, fsha = _run(st)
    return root


@pytest.fixture
def fx(fx_built, tmp_path):
    shutil.copytree(fx_built, tmp_path / "results")
    st = fx_study("fx-v3a-built", tmp_path / "results")
    return st, st.run_dir("fx-v3a")


def _validate(st):
    val, ctx = V.validate_run("fx-v3a", ["boundary"], frozen=True, study=st)
    return val, ctx


def test_fixture_pipeline_valid_with_traces(fx):
    st, d = fx
    val, ctx = _validate(st)
    assert val["engineering_valid"] and val["complete"], val["invalid"][:5]
    assert val["trace_checks"]["trace_status_counts"] == {"complete": 4}
    rows = [json.loads(x) for x in (d / "cases.jsonl").read_text().splitlines()]
    assert {r["trace_status"] for r in rows if r["method"].startswith("hid")} == {"complete"}
    assert all("trace_status" not in r for r in rows if not r["method"].startswith("hid"))
    s, strings, units = R3.summarise(val, ctx["design"], d)
    assert s["primary"]["verdict"] == "INCOMPLETE"       # a 1-cell fixture is not the design


def test_fixture_corruption_and_missing_rows_invalid_precedes_incomplete(fx):
    st, d = fx
    rows = [json.loads(x) for x in (d / "cases.jsonl").read_text().splitlines()]
    hid = next(r for r in rows if r["method"] == "hid_refine4")
    t = d / hid["trace_path"]
    t.write_bytes(t.read_bytes().replace(b'"cache_hit": false', b'"cache_hit": true ', 1))
    val, ctx = _validate(st)
    assert not val["engineering_valid"]
    assert any("trace hash_mismatch" in x for x in val["invalid"])
    (d / "rows" / f"{rows[0]['case_id']}.json").unlink()
    val, ctx = _validate(st)
    assert R3.decision(val, ctx["design"])["verdict"] == "INVALID"


def test_fixture_missing_and_duplicate_rows(fx):
    st, d = fx
    lines = (d / "cases.jsonl").read_text().splitlines()
    rows = [json.loads(x) for x in lines]
    cid = rows[0]["case_id"]
    keep = [x for x, r in zip(lines, rows) if r["case_id"] != cid]
    (d / "cases.jsonl").write_text("\n".join(keep) + "\n")
    (d / "rows" / f"{cid}.json").unlink()
    val, ctx = _validate(st)
    assert val["engineering_valid"] and not val["complete"]
    assert R3.decision(val, ctx["design"])["verdict"] == "INCOMPLETE"
    (d / "cases.jsonl").write_text("\n".join(keep + keep[:1]) + "\n")
    val, _ = _validate(st)
    assert not val["engineering_valid"] and val["duplicates"]


def test_fixture_resume_changed_identity_fails(fx):
    st, d = fx
    p = next((d / "rows").iterdir())
    rows = json.loads(p.read_text())
    rows[0]["freeze_sha256"] = "0" * 64
    p.write_text(json.dumps(rows))
    cases, _ = st.role_cases("boundary", d)
    fr, fsha, _ = B.load_and_validate_freeze("fx-v3a", "benchmark", st)
    with pytest.raises(RuntimeError, match="different freeze"):
        B.run_cases(cases, d, "fx-v3a", fsha, True, lambda m: None, None, study=st)


def test_fixture_source_change_invalidates_freeze(fx, monkeypatch):
    st, d = fx
    real = freeze_v2.sha_file
    target = str(B.ID_ROOT / "hierarchy" / "segmentation.py")
    monkeypatch.setattr(freeze_v2, "sha_file", lambda p: "0" * 64 if str(p) == target else real(p))
    _, _, problems = freeze_v2.load_and_validate(st, "fx-v3a")
    assert any("segmentation.py" in p for p in problems)
    with pytest.raises(SC.ReservedAccessError):
        st.role_cases("boundary", d)


@pytest.mark.parametrize("limits,hid_status,base_status", [
    (dict(wall_limit_s=0.01), "timeout_raw", "censored_timeout"),
    (dict(rss_limit_bytes=1 << 20), "rss_limit_raw", "censored_rss_limit")])
def test_real_watchdog_tiny_limits_fallback_and_censoring(tmp_path, limits, hid_status, base_status):
    """DELIBERATELY TINY FIXTURE LIMITS (0.01 s wall / 1 MiB RSS): every worker breaches."""
    import dataclasses
    pol = dataclasses.replace(FX_POLICY, **limits)
    st = fx_study(f"fx-v3a-tiny-{hid_status}", tmp_path / "results", resources=pol)
    d, cases, fsha = _run(st)
    val, ctx = V.validate_run("fx-v3a", ["boundary"], frozen=True, study=st)
    rows = [json.loads(x) for x in (d / "cases.jsonl").read_text().splitlines()]
    by = {}
    for r in rows:
        by.setdefault(r["method"], set()).add(r["status"])
    assert by["hid_full"] == by["hid_refine4"] == {hid_status}
    assert by["raw"] == {base_status}
    assert {r["trace_status"] for r in rows if r["method"].startswith("hid")} == \
        {"unavailable_watchdog"}
    assert val["trace_checks"]["trace_status_counts"] == {"unavailable_watchdog": 4}
    assert len(val["censored"]) == 2 * 9
    # owner semantics: a portfolio with NO available constituent is an error row, which
    # validation reports; it is never replaced by raw
    assert by["baseline_best"] == {"error"}
    assert val["invalid"] and all("baseline_best error row" in x for x in val["invalid"])
