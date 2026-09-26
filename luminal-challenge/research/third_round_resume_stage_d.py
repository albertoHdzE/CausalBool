"""Stage D of the third round (parent plan section 4), run under the resume.

Matrices (parent protocol, unchanged): development programs 800000-800099,

- ``D_fixed_work``: 100 x 3 reps x {R0, C1}, mode ``work:10000`` (600 rows);
- ``D_wall``: 100 x 3 reps x {R0, C1}, mode ``wall:0.1`` (600 rows);
- ``D_memory``: diagnostic 800000-800029 x {R0, C1}, rep 0, mode ``peak_memory`` (60).

Each row is one fresh process of ``third_round_resume_dworker`` with complete raw
streams (``third_round_resume_common.run_stage``). Cells run sequentially in the
parent's deterministic order; nothing else is measured alongside.

``development(rows...)`` is the REPORTER's gate computation (pure: it takes row
lists, so synthetic complete / negative / incomplete matrices can be dry-run):

- complete: every expected key once, no failed / timed-out / incorrect row;
- exact fixed-work parity: per (program, repetition) the R0 and C1 fingerprints
  are equal (and J equal);
- cost: equal-family geometric mean over programs of median(C1)/median(R0)
  complete compile-call seconds <= 0.90;
- quality: equal-family mean over programs of the within-program mean over
  repetitions of log(J_C1/J_R0) at .1 s <= 0.
"""

from __future__ import annotations

import argparse
import collections
import json
import math
import statistics
import sys
from pathlib import Path
from typing import Dict, List

from research import third_round_common as tc
from research import third_round_resume_common as rc

from tests_direct import generate_programs as gp

ARMS = ("R0", "C1")
STAGES = {"D_fixed_work": "work:10000", "D_wall": "wall:0.1", "D_memory": "peak_memory"}
WORKER = "research.third_round_resume_dworker"


def dev_seeds():
    return range(tc.DEVELOPMENT[0], tc.DEVELOPMENT[1] + 1)


def specs(stage: str) -> List[dict]:
    mode = STAGES[stage]
    seeds = tc.diagnostic_seeds() if stage == "D_memory" else dev_seeds()
    reps = 1 if stage == "D_memory" else 3
    out = []
    for seed in seeds:
        digest = gp.program_digest(gp.additional_program(seed))
        for rep in range(reps):
            for arm in ARMS:
                out.append({"stage_id": stage, "program_sha256": digest, "seed": seed,
                            "repetition": rep, "arm_id": arm, "mode_key": mode})
    return rc.ordered(out)


def expected_keys(stage: str) -> List[str]:
    return [tc.row_key(s) for s in specs(stage)]


# --------------------------------------------------------------------------
# Reporter
# --------------------------------------------------------------------------


def _fam_mean(values: Dict[int, float]) -> float:
    fam = collections.defaultdict(list)
    for seed, v in values.items():
        fam[seed % 5].append(v)
    return statistics.mean(statistics.mean(v) for v in fam.values())


def development(fixed: List[dict], wall: List[dict], memory: List[dict],
                keys: Dict[str, List[str]]) -> dict:
    out: dict = {"stages": {}}
    for name, rows in (("D_fixed_work", fixed), ("D_wall", wall), ("D_memory", memory)):
        check = tc.check_rows(rows, keys[name])
        bad = sorted(tc.row_key(r) for r in rows if not r.get("failed")
                     and (r.get("correctness") != "PASS" or r.get("discrepancy_count") != 0))
        check["incorrect"] = bad
        check["complete"] = check["complete"] and not bad
        out["stages"][name] = {k: (len(v) if isinstance(v, list) else v)
                               for k, v in check.items()}
        out["stages"][name]["failed_keys"] = check["failed"][:20]
        out["stages"][name]["incorrect_keys"] = bad[:20]
    complete = all(s["complete"] for s in out["stages"].values())
    out["complete"] = complete
    if not complete:
        out.update(gate_met=False, verdict="INCOMPLETE_WITH_EVIDENCE",
                   reason="incomplete or failed development matrix")
        return out
    by = collections.defaultdict(dict)
    for r in fixed:
        by[(r["seed"], r["repetition"])][r["arm_id"]] = r
    mismatches = []
    for (seed, rep), pair in sorted(by.items()):
        if pair["R0"]["fingerprint"] != pair["C1"]["fingerprint"] or \
                pair["R0"]["J"] != pair["C1"]["J"]:
            mismatches.append([seed, rep])
    out["fixed_work_parity"] = {"pairs": len(by), "mismatches": mismatches,
                                "exact": not mismatches}
    med = collections.defaultdict(dict)
    for r in fixed:
        med[r["seed"]].setdefault(r["arm_id"], []).append(r["compile_call_seconds"])
    ratios, programs = {}, {}
    for seed, arms in med.items():
        m0, m1 = statistics.median(arms["R0"]), statistics.median(arms["C1"])
        ratios[seed] = math.log(m1 / m0)
        programs[str(seed)] = {"family": tc.family_of(seed), "R0_median": m0, "C1_median": m1,
                               "ratio": m1 / m0}
    cost = math.exp(_fam_mean(ratios))
    wby = collections.defaultdict(dict)
    for r in wall:
        wby[(r["seed"], r["repetition"])][r["arm_id"]] = r
    per_prog = collections.defaultdict(list)
    for (seed, rep), pair in wby.items():
        per_prog[seed].append(math.log(pair["C1"]["J"] / pair["R0"]["J"]))
    qlog = {seed: statistics.mean(v) for seed, v in per_prog.items()}
    quality = _fam_mean(qlog)
    for seed, v in qlog.items():
        programs[str(seed)]["wall_mean_log_J_ratio"] = v
    wmed = collections.defaultdict(dict)
    for r in wall:
        wmed[r["seed"]].setdefault(r["arm_id"], []).append(r["compile_call_seconds"])
    families = collections.defaultdict(lambda: {"cost_log": [], "quality_log": []})
    for seed in ratios:
        families[tc.family_of(seed)]["cost_log"].append(ratios[seed])
        families[tc.family_of(seed)]["quality_log"].append(qlog[seed])
    mem = collections.defaultdict(dict)
    for r in memory:
        mem[r["seed"]][r["arm_id"]] = r
    out.update({
        "programs": programs,
        "fixed_work_compile_ratio_equal_family": cost,
        "wall_primary_mean_log_J_ratio_equal_family": quality,
        "family": {f: {"cost_ratio": math.exp(statistics.mean(v["cost_log"])),
                       "mean_log_J_ratio": statistics.mean(v["quality_log"])}
                   for f, v in families.items()},
        "absolute_fixed_work_seconds": {
            arm: {"median": statistics.median(r["compile_call_seconds"] for r in fixed
                                              if r["arm_id"] == arm),
                  "p95": _q(sorted(r["compile_call_seconds"] for r in fixed
                                   if r["arm_id"] == arm), 0.95),
                  "max": max(r["compile_call_seconds"] for r in fixed if r["arm_id"] == arm)}
            for arm in ARMS},
        "wall_compile_seconds_median": {arm: statistics.median(
            r["compile_call_seconds"] for r in wall if r["arm_id"] == arm) for arm in ARMS},
        "wall_J_wins_ties_losses_C1": [
            sum(1 for p in wby.values() if p["C1"]["J"] < p["R0"]["J"]),
            sum(1 for p in wby.values() if p["C1"]["J"] == p["R0"]["J"]),
            sum(1 for p in wby.values() if p["C1"]["J"] > p["R0"]["J"])],
        "wall_unknown_queries": {arm: sum(r["unknown_queries"] for r in wall
                                          if r["arm_id"] == arm) for arm in ARMS},
        "wall_nodes_median": {arm: statistics.median(r["nodes"] for r in wall
                                                     if r["arm_id"] == arm) for arm in ARMS},
        "memory_peak_ratio_median": statistics.median(
            p["C1"]["tracemalloc_peak_bytes"] / p["R0"]["tracemalloc_peak_bytes"]
            for p in mem.values()),
        "memory_peak_ratio_max": max(
            p["C1"]["tracemalloc_peak_bytes"] / p["R0"]["tracemalloc_peak_bytes"]
            for p in mem.values()),
        "memory_fingerprints_equal": all(
            p["C1"]["fingerprint"] == p["R0"]["fingerprint"] for p in mem.values()),
        "cost_regressions": sorted((s for s, p in programs.items() if p["ratio"] > 1.0)),
    })
    gate = tc.DEVELOPMENT_GATE
    met = (out["fixed_work_parity"]["exact"] and out["memory_fingerprints_equal"]
           and cost <= gate["fixed_work_compile_ratio_max"]
           and quality <= gate["wall_primary_mean_log_J_ratio_max"])
    out.update(gate=gate, gate_met=met,
               verdict="PASS" if met else "DEVELOPMENT_TARGET_NOT_REACHED")
    return out


def _q(xs, p):
    pos = (len(xs) - 1) * p
    lo = math.floor(pos)
    hi = min(lo + 1, len(xs) - 1)
    return xs[lo] + (xs[hi] - xs[lo]) * (pos - lo)


def report(run: Path) -> dict:
    rows = {s: rc.strict_rows(Path(run) / "stages" / s / "rows.jsonl") for s in STAGES}
    return development(rows["D_fixed_work"], rows["D_wall"], rows["D_memory"],
                       {s: expected_keys(s) for s in STAGES})


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--stage", choices=sorted(STAGES), required=True)
    args = parser.parse_args(argv)
    plan = specs(args.stage)
    if len(plan) != tc.EXPECTED_ROWS[args.stage]:
        raise RuntimeError(f"{len(plan)} specs, expected {tc.EXPECTED_ROWS[args.stage]}")
    result = rc.run_stage(Path(args.run), args.stage, plan, WORKER)
    print(json.dumps({k: (v if not isinstance(v, list) else len(v)) for k, v in result.items()}))
    return 0 if result["complete"] else 1


if __name__ == "__main__":
    sys.exit(main())
