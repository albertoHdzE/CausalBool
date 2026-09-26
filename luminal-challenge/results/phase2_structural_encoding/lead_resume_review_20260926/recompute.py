"""Independent recomputation of the third-round resume endpoints (review, 2026-09-26).

Standard library only. It imports nothing from ``research`` or ``tests_direct``,
and reads nothing the reporter or auditor wrote except COMPARISON.json, which is
compared at the end. Estimators follow plan/phase2_third_round/PROTOCOL.json
"statistics". The bootstrap uses its own draw order and several seeds, so
agreement with the reported interval does not depend on replaying the reporter's
random stream.

Usage (from luminal-challenge/): python3 <this file>
"""

from __future__ import annotations

import hashlib
import json
import math
import random
import statistics
from collections import defaultdict
from pathlib import Path

RUN = Path("results/phase2_structural_encoding/third_round_20260925_resume")
OUT = Path(__file__).resolve().parent / "RECOMPUTE.json"
FAMILIES = ["scalar", "vector", "mixed", "dependency", "aliasing"]
REPORTED = json.loads((RUN / "COMPARISON.json").read_text())


def strict(path: Path) -> list:
    raw = path.read_bytes()
    if not raw.endswith(b"\n"):
        raise SystemExit(f"{path}: torn final line")
    rows = []
    for i, line in enumerate(raw.split(b"\n")[:-1]):
        if not line.strip():
            raise SystemExit(f"{path}:{i}: blank line")
        rows.append(json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(
            ValueError(f"{path}:{i}: non-finite {c}"))))
    return rows


def quantile(xs, p):
    xs = sorted(xs)
    h = (len(xs) - 1) * p
    lo = math.floor(h)
    return xs[lo] + (h - lo) * (xs[min(lo + 1, len(xs) - 1)] - xs[lo])


def equal_family(values: dict, fam: dict) -> float:
    return statistics.fmean(statistics.fmean(values[s] for s in fam[f]) for f in FAMILIES)


def bootstrap(cost: dict, qual: dict, fam: dict, seed: int, draws: int = 10000):
    rng = random.Random(seed)
    cs, qs = [], []
    for _ in range(draws):
        c_f, q_f = [], []
        for f in FAMILIES:
            members = fam[f]
            pick = [members[rng.randrange(len(members))] for _ in members]
            c_f.append(statistics.fmean(cost[s] for s in pick))
            q_f.append(statistics.fmean(qual[s] for s in pick))
        cs.append(statistics.fmean(c_f))
        qs.append(statistics.fmean(q_f))
    return ([math.exp(quantile(cs, 0.0125)), math.exp(quantile(cs, 0.9875))],
            [math.exp(quantile(qs, 0.0125)), math.exp(quantile(qs, 0.9875))])


def main() -> None:
    out: dict = {"checks": {}, "findings": []}
    stages = {s: strict(RUN / "stages" / s / "rows.jsonl")
              for s in ("C_fixed_work", "C_wall", "C_public", "C_export", "C_acceptance")}
    expected = {"C_fixed_work": 2000, "C_wall": 6000, "C_public": 280, "C_export": 1248,
                "C_acceptance": 284}
    for s, n in expected.items():
        rows = stages[s]
        # Export and acceptance rows record the CLI outcome as ``ok``; the others
        # carry the in-process ``correctness`` verdict.
        field, want = (("ok", True) if s in ("C_export", "C_acceptance")
                       else ("correctness", "PASS"))
        bad = [r for r in rows if r.get("failed") or r.get("exit_code") != 0
               or r.get(field) != want or r.get("timed_out")]
        out["checks"][f"{s}_rows"] = {"observed": len(rows), "expected": n, "bad": len(bad)}
        if len(rows) != n or bad:
            out["findings"].append(f"{s}: {len(rows)}/{n} rows, {len(bad)} bad")

    # Raw stdout: every row must be the JSON the worker printed, byte-hashed.
    raw_mismatch = 0
    raw_checked = 0
    for s in ("C_fixed_work", "C_wall", "C_public", "C_export"):
        for r in stages[s]:
            p = RUN / "stages" / s / "raw" / f"{r['raw_index']:05d}.stdout"
            b = p.read_bytes()
            raw_checked += 1
            if hashlib.sha256(b).hexdigest() != r["stdout_sha256"]:
                raw_mismatch += 1
                continue
            if s == "C_export":
                continue  # stdout is the compiled program itself; re-validated below
            payload = json.loads(b)
            if any(r.get(k) != v for k, v in payload.items()):
                raw_mismatch += 1
    out["checks"]["raw_stdout"] = {"checked": raw_checked, "mismatch": raw_mismatch}
    if raw_mismatch:
        out["findings"].append(f"raw stdout mismatch {raw_mismatch}")

    # Family membership from the cohort record, cross-checked against seeds.
    # Family comes from the cohort record by seed; the program file bytes are
    # re-hashed so the record cannot silently point at a different file.
    cohort = json.loads((RUN / "cohort" / "COHORT_CHECKED.json").read_text())["programs"]
    file_bad = sum(1 for p in cohort.values()
                   if hashlib.sha256(Path(p["path"]).read_bytes()).hexdigest() != p["file_sha256"])
    fw = stages["C_fixed_work"]
    fam_by_sha = {r["program_sha256"]: cohort[str(r["seed"])]["family"] for r in fw}
    out["checks"]["cohort"] = {"seeds": sorted(int(s) for s in cohort)[::199],
                               "programs": len(cohort), "file_hash_mismatch": file_bad,
                               "row_programs": len(fam_by_sha)}
    if file_bad or len(cohort) != 200 or len(fam_by_sha) != 200:
        out["findings"].append("cohort membership or file identity")

    by = defaultdict(dict)
    for r in fw:
        by[(r["program_sha256"], r["repetition"])][r["arm_id"]] = r
    parity_bad, node_bad, capped = 0, 0, 0
    for (sha, rep), d in by.items():
        if d["R0"]["fingerprint"] != d["C1"]["fingerprint"]:
            parity_bad += 1
        if d["R0"]["nodes"] != d["C1"]["nodes"] or d["R0"]["certificates"] != d["C1"]["certificates"]:
            node_bad += 1
        if d["R0"]["stopped_because"] != "pass_complete":
            capped += 1
    out["checks"]["fixed_work_parity"] = {"pairs": len(by), "fingerprint_mismatch": parity_bad,
                                          "node_or_certificate_mismatch": node_bad,
                                          "pairs_not_pass_complete": capped}

    shas = sorted({r["program_sha256"] for r in fw})
    fam ={f: sorted(s for s in shas if fam_by_sha.get(s) == f) for f in FAMILIES}
    out["checks"]["family_sizes"] = {f: len(v) for f, v in fam.items()}

    med = {arm: {s: statistics.median(by[(s, k)][arm]["compile_call_seconds"] for k in range(5))
                 for s in shas} for arm in ("R0", "C1")}
    cost = {s: math.log(med["C1"][s] / med["R0"][s]) for s in shas}

    wall = defaultdict(dict)
    for r in stages["C_wall"]:
        wall[(r["program_sha256"], r["repetition"], r["mode_key"])][r["arm_id"]] = r
    qual = {s: statistics.fmean(math.log(wall[(s, k, "wall:0.1")]["C1"]["J"]
                                         / wall[(s, k, "wall:0.1")]["R0"]["J"]) for k in range(5))
            for s in shas}

    point_c = math.exp(equal_family(cost, fam))
    point_q = math.exp(equal_family(qual, fam))
    intervals = {}
    for seed in (2026092802, 1, 2, 3):
        ci_c, ci_q = bootstrap(cost, qual, fam, seed)
        intervals[str(seed)] = {"cost": ci_c, "quality": ci_q}
    out["endpoints"] = {"cost_ratio": point_c, "quality_ratio": point_q,
                        "intervals_97_5_independent_draw_order": intervals,
                        "reported": {"cost_ratio": REPORTED["cost_ratio"],
                                     "quality_ratio": REPORTED["quality_ratio"],
                                     "intervals": REPORTED["intervals_97_5"]}}
    if abs(point_c - REPORTED["cost_ratio"]) > 1e-12 or abs(point_q - REPORTED["quality_ratio"]) > 1e-12:
        out["findings"].append("point estimate disagrees with COMPARISON.json")
    for seed, iv in intervals.items():
        if not (iv["cost"][1] <= 0.80 and iv["quality"][1] <= 1.01):
            out["findings"].append(f"gate fails under bootstrap seed {seed}")

    # --- Probes beyond the registered endpoints -------------------------------
    per_prog = sorted(math.exp(v) for v in cost.values())
    out["probes"] = {}
    out["probes"]["per_program_cost_ratio"] = {
        "min": per_prog[0], "q10": quantile(per_prog, .1), "median": quantile(per_prog, .5),
        "q90": quantile(per_prog, .9), "max": per_prog[-1],
        "programs_C1_slower": sum(1 for x in per_prog if x > 1)}

    # Cost against problem size (nodes explored, identical for both arms).
    nodes = {s: statistics.median(by[(s, k)]["R0"]["nodes"] for k in range(5)) for s in shas}
    tert = sorted(shas, key=lambda s: nodes[s])
    thirds = [tert[:67], tert[67:134], tert[134:]]
    out["probes"]["cost_by_nodes_tercile"] = [
        {"nodes_range": [nodes[t[0]], nodes[t[-1]]],
         "geo_ratio": math.exp(statistics.fmean(cost[s] for s in t)),
         "R0_median_s": statistics.median(med["R0"][s] for s in t)} for t in thirds]

    # Aggregate time rather than per-program geometric mean: total seconds saved.
    tot = {arm: sum(med[arm].values()) for arm in ("R0", "C1")}
    out["probes"]["summed_median_seconds"] = {**tot, "ratio": tot["C1"] / tot["R0"]}

    # Whole-process cost: add import time (C1 imports the extra kernel module).
    proc = {arm: {s: statistics.median(by[(s, k)][arm]["compile_call_seconds"]
                                       + by[(s, k)][arm]["import_seconds"] for k in range(5))
                  for s in shas} for arm in ("R0", "C1")}
    out["probes"]["cost_including_import"] = math.exp(equal_family(
        {s: math.log(proc["C1"][s] / proc["R0"][s]) for s in shas}, fam))
    out["probes"]["import_seconds_median"] = {
        arm: statistics.median(r["import_seconds"] for r in fw if r["arm_id"] == arm)
        for arm in ("R0", "C1")}
    out["probes"]["process_seconds_ratio"] = math.exp(equal_family(
        {s: math.log(statistics.median(by[(s, k)]["C1"]["process_seconds"] for k in range(5))
                     / statistics.median(by[(s, k)]["R0"]["process_seconds"] for k in range(5)))
         for s in shas}, fam))

    # Order and drift: which arm ran first in each pair, and does it matter?
    first = {"R0": [], "C1": []}
    for (s, k), d in by.items():
        f = "R0" if d["R0"]["raw_index"] < d["C1"]["raw_index"] else "C1"
        first[f].append(math.log(d["C1"]["compile_call_seconds"] / d["R0"]["compile_call_seconds"]))
    out["probes"]["arm_order"] = {f: {"pairs": len(v), "geo_ratio": math.exp(statistics.fmean(v))}
                                  for f, v in first.items() if v}
    pairs = sorted(by.values(), key=lambda d: min(d["R0"]["raw_index"], d["C1"]["raw_index"]))
    q = len(pairs) // 4
    out["probes"]["drift_by_time_quartile"] = [
        math.exp(statistics.fmean(math.log(d["C1"]["compile_call_seconds"]
                                           / d["R0"]["compile_call_seconds"])
                                  for d in pairs[i * q:(i + 1) * q])) for i in range(4)]

    # Wall mode: is the quality gain bought with extra wall time?
    for mode in ("wall:0.01", "wall:0.1", "wall:1.0"):
        lr_t, wins, losses, lose_unknown = [], 0, 0, 0
        for s in shas:
            for k in range(5):
                d = wall[(s, k, mode)]
                lr_t.append(math.log(d["C1"]["compile_call_seconds"] / d["R0"]["compile_call_seconds"]))
                if d["C1"]["J"] < d["R0"]["J"]:
                    wins += 1
                elif d["C1"]["J"] > d["R0"]["J"]:
                    losses += 1
                    if d["C1"]["unknown_queries"] > 0 or d["R0"]["unknown_queries"] > 0:
                        lose_unknown += 1
        out["probes"][f"{mode}_compile_call_time_geo_ratio"] = math.exp(statistics.fmean(lr_t))
        out["probes"][f"{mode}_W_L"] = [wins, losses]
        out["probes"][f"{mode}_losses_with_unknown_queries"] = lose_unknown

    # Quality at the primary allowance by family, and the direction per program.
    out["probes"]["quality_programs_better_equal_worse"] = [
        sum(1 for v in qual.values() if v < -1e-12), sum(1 for v in qual.values() if abs(v) <= 1e-12),
        sum(1 for v in qual.values() if v > 1e-12)]

    # Public score recomputation.
    pub = stages["C_public"]
    serial = {(r["program_sha256"], r["repetition"]): r for r in pub if r["arm_id"] == "serial"}
    scores = {}
    for arm in ("R0", "C1"):
        for mode in ("wall:0.01", "wall:0.1", "wall:1.0"):
            per = []
            for k in range(5):
                sel = [r for r in pub if r["arm_id"] == arm and r["mode_key"] == mode
                       and r["repetition"] == k]
                assert len(sel) == 8
                gc = statistics.fmean(math.log(serial[(r["program_sha256"], k)]["cycles"] / r["cycles"])
                                      for r in sel)
                gs = statistics.fmean(math.log(serial[(r["program_sha256"], k)]["scratch"] / r["scratch"])
                                      for r in sel)
                per.append(math.exp((gc + gs) / 2))
            scores[f"{arm}@{mode}"] = per
            if any(abs(a - b) > 1e-12 for a, b in zip(per, REPORTED["descriptive"]["public_scores"][f"{arm}@{mode}"])):
                out["findings"].append(f"public score {arm}@{mode} disagrees")
    out["public_scores"] = scores
    # Exported compilers: re-validate every retained stdout with the challenge's
    # own evaluator (.reference/machine.py, not ours), on every case.
    import sys
    sys.path.insert(0, ".reference")
    import machine  # noqa: E402
    all_cohort = json.loads((RUN / "cohort" / "COHORT_CHECKED.json").read_text())
    path_of = {p["program_sha256"]: p["path"] for p in all_cohort["corpus"]}
    for r in fw:
        path_of[r["program_sha256"]] = cohort[str(r["seed"])]["path"]
    ex_bad, ex_checked = [], 0
    for r in stages["C_export"]:
        program = machine.load_program(path_of[r["program_sha256"]])
        compiled = json.loads((RUN / "stages" / "C_export" / "raw"
                               / f"{r['raw_index']:05d}.stdout").read_bytes())
        try:
            cycles = machine.check_compilation(program, compiled)
            for case in program["cases"]:
                machine.check_case(program, compiled, case)
            scratch = machine.scratch_footprint(program, compiled)
        except Exception as exc:  # noqa: BLE001
            ex_bad.append([r["raw_index"], repr(exc)[:120]])
            continue
        ex_checked += 1
        if (cycles, scratch, cycles * scratch) != (r["cycles"], r["scratch"], r["J"]):
            ex_bad.append([r["raw_index"], "cycles/scratch/J differ from row"])
    out["checks"]["export_revalidated"] = {"rows": len(stages["C_export"]),
                                           "valid": ex_checked, "bad": ex_bad[:10]}
    if ex_bad or ex_checked != len(stages["C_export"]):
        out["findings"].append(f"export re-validation: {len(ex_bad)} bad")
    out["verdict_reproduced"] = (not out["findings"])
    OUT.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("findings", "endpoints")}, indent=1))
    print(json.dumps(out["probes"], indent=1))
    print(json.dumps(out["checks"], indent=1))


if __name__ == "__main__":
    main()
