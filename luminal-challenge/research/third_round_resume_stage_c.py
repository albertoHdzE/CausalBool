"""Stage C of the third round (parent plan section 5): fresh confirmation, R0 vs C1.

Only a Stage D PASS permits this module to launch rows. Matrices (unchanged):

| stage | rows |
|---|---:|
| ``C_acceptance`` 142 corpus programs x {R0, C1} exports, rep 0 | 284 |
| ``C_fixed_work`` 200 x 5 x {R0, C1}, ``work:10000`` | 2,000 |
| ``C_wall`` 200 x 5 x {R0, C1} x {.01, .1, 1 s} | 6,000 |
| ``C_public`` 8 x 5 x ({R0, C1} x 3 allowances + serial) | 280 |
| ``C_export`` (200 + 8) x 3 x {R0, C1} exports | 1,248 |

Order: programs by (family index, seed), public programs by pinned filename;
repetitions 0-based; within each program/repetition the cells are sorted by the
protocol's stable seed of (arm-order seed, stage, program sha, repetition, arm,
mode) with a lexicographic (arm, mode) tie-break.

``comparison`` (REPORTER) computes the two confirmatory endpoints and their
family-stratified, program-paired percentile bootstrap:

1. cost: per program median of five fixed-work complete compile-call times per
   arm; log(C1/R0); equal-family mean; exponentiated;
2. quality at .1 s: per program mean over repetitions of paired log(J_C1/J_R0);
   equal-family mean; exponentiated.

10,000 draws with ``random.Random(2026092802)``: per draw, per family in protocol
order, 40 indices ``randrange(40)`` into that family's programs sorted by
program sha; the SAME indices serve both endpoints. Percentiles .0125/.9875 by
linear interpolation at (N-1)p on the sorted draws. Success requires cost upper
<= 0.80 AND quality upper <= 1.01, complete evidence and exact fixed-work parity.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import random
import statistics
import sys
from pathlib import Path
from typing import Dict, List

from research import third_round_common as tc
from research import third_round_resume_common as rc

WORKER = "research.third_round_resume_cworker"
ARMS = ("R0", "C1")
WALL_MODES = ("wall:0.01", "wall:0.1", "wall:1.0")
REPS = 5
EXPORT_REPS = 3


def cohort(run: Path) -> dict:
    return json.loads((Path(run) / "cohort" / "COHORT_CHECKED.json").read_text())


def fresh_programs(run: Path) -> List[dict]:
    progs = cohort(run)["programs"]
    items = [dict(p, seed=int(s)) for s, p in progs.items()]
    return sorted(items, key=lambda p: (tc.FAMILIES.index(p["family"]), p["seed"]))


def public_programs() -> List[dict]:
    from tests_direct import generate_programs as gp
    import machine
    out = []
    for path in sorted((rc.ROOT / ".reference" / "programs").glob("*.json")):
        program = machine.load_program(str(path))
        out.append({"seed": None, "path": str(path), "name": path.name,
                    "program_sha256": gp.program_digest(program), "family": "public"})
    return out


def _cells(stage, program, rep, cells):
    specs = [{"stage_id": stage, "program_sha256": program["program_sha256"],
              "seed": program["seed"], "repetition": rep, "arm_id": arm, "mode_key": mode,
              "program_path": program["path"], "corpus": program.get("corpus")}
             for arm, mode in cells]
    return sorted(specs, key=lambda s: (tc.stable_seed([tc.SEED_ARM_ORDER, s["stage_id"],
                                                        s["program_sha256"], s["repetition"],
                                                        s["arm_id"], s["mode_key"]]),
                                        s["arm_id"], s["mode_key"]))


def specs(run: Path, stage: str) -> List[dict]:
    out: List[dict] = []
    if stage == "C_fixed_work":
        for p in fresh_programs(run):
            for rep in range(REPS):
                out += _cells(stage, p, rep, [(a, "work:10000") for a in ARMS])
    elif stage == "C_wall":
        for p in fresh_programs(run):
            for rep in range(REPS):
                out += _cells(stage, p, rep, [(a, m) for a in ARMS for m in WALL_MODES])
    elif stage == "C_public":
        for p in public_programs():
            for rep in range(REPS):
                out += _cells(stage, p, rep, [(a, m) for a in ARMS for m in WALL_MODES]
                              + [("serial", "serial")])
    elif stage == "C_export":
        for p in fresh_programs(run) + public_programs():
            for rep in range(EXPORT_REPS):
                out += _cells(stage, p, rep, [(a, "wall:0.1") for a in ARMS])
    elif stage == "C_acceptance":
        for p in cohort(run)["corpus"]:
            out += _cells(stage, dict(p, seed=None), 0, [(a, "wall:0.1") for a in ARMS])
    else:
        raise ValueError(stage)
    return out


# --------------------------------------------------------------------------
# Reporter
# --------------------------------------------------------------------------


def _pct(sorted_values: List[float], p: float) -> float:
    pos = (len(sorted_values) - 1) * p
    lo = math.floor(pos)
    hi = min(lo + 1, len(sorted_values) - 1)
    return sorted_values[lo] + (sorted_values[hi] - sorted_values[lo]) * (pos - lo)


def paired_bootstrap(cost: Dict[str, float], quality: Dict[str, float],
                     family_of: Dict[str, str]) -> dict:
    """Program-paired, family-stratified bootstrap of both log endpoints."""

    groups = {f: sorted(p for p in cost if family_of[p] == f) for f in tc.FAMILIES}
    if any(len(g) == 0 for g in groups.values()):
        raise ValueError("a family has no programs")
    rng = random.Random(tc.SEED_BOOTSTRAP)
    draws_c, draws_q = [], []
    for _ in range(10_000):
        fc, fq = [], []
        for f in tc.FAMILIES:
            g = groups[f]
            idx = [rng.randrange(len(g)) for _ in range(len(g))]
            fc.append(statistics.fmean(cost[g[i]] for i in idx))
            fq.append(statistics.fmean(quality[g[i]] for i in idx))
        draws_c.append(statistics.fmean(fc))
        draws_q.append(statistics.fmean(fq))
    draws_c.sort()
    draws_q.sort()
    lo, hi = tc.load_protocol()["statistics"]["percentiles"]
    return {"cost": [math.exp(_pct(draws_c, lo)), math.exp(_pct(draws_c, hi))],
            "quality": [math.exp(_pct(draws_q, lo)), math.exp(_pct(draws_q, hi))],
            "resamples": 10_000, "percentiles": [lo, hi], "seed": tc.SEED_BOOTSTRAP}


def comparison(rows: Dict[str, List[dict]], keys: Dict[str, List[str]]) -> dict:
    out: dict = {"stages": {}}
    for stage, stage_rows in rows.items():
        check = tc.check_rows(stage_rows, keys[stage])
        bad = sorted(tc.row_key(r) for r in stage_rows if not r.get("failed")
                     and r.get("correctness", "PASS") != "PASS")
        check["complete"] = check["complete"] and not bad
        out["stages"][stage] = {k: (len(v) if isinstance(v, list) else v)
                                for k, v in check.items()}
        out["stages"][stage]["incorrect"] = len(bad)
    out["complete"] = all(s["complete"] for s in out["stages"].values())
    if not out["complete"]:
        out.update(verdict="INCOMPLETE_WITH_EVIDENCE", success=False)
        return out
    fixed, wall = rows["C_fixed_work"], rows["C_wall"]
    family_of = {r["program_sha256"]: tc.family_of(r["seed"]) for r in fixed}
    pairs = collections.defaultdict(dict)
    for r in fixed:
        pairs[(r["program_sha256"], r["repetition"])][r["arm_id"]] = r
    mism = sorted([p, k] for (p, k), v in pairs.items()
                  if v["R0"]["fingerprint"] != v["C1"]["fingerprint"] or v["R0"]["J"] != v["C1"]["J"])
    out["fixed_work_parity"] = {"pairs": len(pairs), "mismatches": mism[:50],
                                "mismatch_count": len(mism), "exact": not mism}
    t = collections.defaultdict(lambda: collections.defaultdict(list))
    for r in fixed:
        t[r["program_sha256"]][r["arm_id"]].append(r["compile_call_seconds"])
    cost = {p: math.log(statistics.median(a["C1"]) / statistics.median(a["R0"]))
            for p, a in t.items()}
    qual_by = collections.defaultdict(dict)
    for r in wall:
        if r["mode_key"] == "wall:0.1":
            qual_by[(r["program_sha256"], r["repetition"])][r["arm_id"]] = r["J"]
    ql = collections.defaultdict(list)
    for (p, _), v in qual_by.items():
        ql[p].append(math.log(v["C1"] / v["R0"]))
    quality = {p: statistics.fmean(v) for p, v in ql.items()}

    def fam_mean(d):
        return statistics.fmean(statistics.fmean(d[p] for p in d if family_of[p] == f)
                                for f in tc.FAMILIES)

    boot = paired_bootstrap(cost, quality, family_of)
    gate = tc.CONFIRMATION_GATE
    success = (out["fixed_work_parity"]["exact"]
               and boot["cost"][1] <= gate["fixed_work_compile_ratio_upper_max"]
               and boot["quality"][1] <= gate["wall_primary_J_ratio_upper_max"])
    out.update({
        "cost_ratio": math.exp(fam_mean(cost)), "quality_ratio": math.exp(fam_mean(quality)),
        "intervals_97_5": boot, "gate": gate, "success": success,
        "verdict": "SUCCESS" if success else "TARGET_NOT_REACHED",
        "family": {f: {"cost_ratio": math.exp(statistics.fmean(
            cost[p] for p in cost if family_of[p] == f)),
            "quality_ratio": math.exp(statistics.fmean(
                quality[p] for p in quality if family_of[p] == f))} for f in tc.FAMILIES},
        "descriptive": _descriptive(rows), "programs": len(cost)})
    return out


def _descriptive(rows) -> dict:
    d = {}
    for arm in ARMS:
        xs = sorted(r["compile_call_seconds"] for r in rows["C_fixed_work"] if r["arm_id"] == arm)
        d[f"fixed_work_{arm}"] = {"median": statistics.median(xs), "p95": _pct(xs, 0.95),
                                  "max": xs[-1]}
        for mode in WALL_MODES:
            sel = [r for r in rows["C_wall"] if r["arm_id"] == arm and r["mode_key"] == mode]
            xs = sorted(r["compile_call_seconds"] for r in sel)
            d[f"{mode}_{arm}"] = {
                "median": statistics.median(xs), "p95": _pct(xs, 0.95), "max": xs[-1],
                "geo_J": math.exp(statistics.fmean(math.log(r["J"]) for r in sel)),
                "overshoot_max": max(r["overshoot_seconds"] for r in sel),
                "unknown_queries": sum(r["unknown_queries"] for r in sel),
                "construction_overruns": sum(r["construction_overrun_count"] or 0 for r in sel),
                "validations": sum(r["validations"] for r in sel)}
    for mode in WALL_MODES:
        pairs = collections.defaultdict(dict)
        for r in rows["C_wall"]:
            if r["mode_key"] == mode:
                pairs[(r["program_sha256"], r["repetition"])][r["arm_id"]] = r["J"]
        d[f"{mode}_J_ratio_geo"] = math.exp(statistics.fmean(
            math.log(v["C1"] / v["R0"]) for v in pairs.values()))
        d[f"{mode}_W_T_L_C1"] = [sum(v["C1"] < v["R0"] for v in pairs.values()),
                                 sum(v["C1"] == v["R0"] for v in pairs.values()),
                                 sum(v["C1"] > v["R0"] for v in pairs.values())]
    d["public_scores"] = public_scores(rows["C_public"])
    d["export_J_geo"] = {arm: math.exp(statistics.fmean(
        math.log(r["J"]) for r in rows["C_export"] if r["arm_id"] == arm)) for arm in ARMS}
    return d


def public_scores(rows: List[dict]) -> dict:
    """S = sqrt(GM(C_serial/C) * GM(S_serial/S)) over the eight programs, per repetition."""

    serial = {(r["program_sha256"], r["repetition"]): r for r in rows if r["arm_id"] == "serial"}
    out = {}
    for arm in ARMS:
        for mode in WALL_MODES:
            per_rep = []
            for rep in range(REPS):
                sel = [r for r in rows if r["arm_id"] == arm and r["mode_key"] == mode
                       and r["repetition"] == rep]
                if len(sel) != 8:
                    raise ValueError("public denominator is not 8")
                gc = statistics.fmean(math.log(serial[(r["program_sha256"], rep)]["cycles"]
                                               / r["cycles"]) for r in sel)
                gs = statistics.fmean(math.log(serial[(r["program_sha256"], rep)]["scratch"]
                                               / r["scratch"]) for r in sel)
                per_rep.append(math.exp((gc + gs) / 2))
            out[f"{arm}@{mode}"] = per_rep
    return out


def load(run: Path) -> Dict[str, List[dict]]:
    return {s: rc.strict_rows(Path(run) / "stages" / s / "rows.jsonl")
            for s in ("C_fixed_work", "C_wall", "C_public", "C_export", "C_acceptance")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", required=True,
                        choices=("C_fixed_work", "C_wall", "C_public"))
    args = parser.parse_args(argv)
    run = Path(args.run)
    states = json.loads((run / "STAGE_STATES.json").read_text())
    if states["gates"].get("D") != "PASS":
        raise RuntimeError("Stage C requires a Stage D PASS")
    if not (run / "CONFIRMATION_FREEZE.json").exists():
        raise RuntimeError("Stage C requires the confirmation freeze")
    plan = specs(run, args.stage)
    if len(plan) != tc.EXPECTED_ROWS[args.stage]:
        raise RuntimeError(f"{len(plan)} specs, expected {tc.EXPECTED_ROWS[args.stage]}")
    result = rc.run_stage(run, args.stage, plan, WORKER)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in result.items()}))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
