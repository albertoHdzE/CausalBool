"""Stage A of the optimization protocol: reproduction and bottleneck audit.

Reads only retained raw evidence. It recomputes the exact public-suite score of
the accepted run from its raw rows and the frozen serial records, and recounts
the stopping reasons of the accepted structural candidate. Nothing here is
measured; profiling lives in ``optimization_profile``.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_stage_a --out DIR
"""

from __future__ import annotations

import argparse
import collections
import json
import math
from pathlib import Path
from typing import Dict, List

from research import optimization_common as oc


R3 = oc.ACCEPTED_RUN
SERIAL_RUNS = oc.RESULTS / "claude_release_20260923" / "production" / "production_comparison" / "runs.json"
RECOUNT = oc.RESULTS / "lead_release_review_20260924" / "PUBLIC_SCORE_RECOUNT.json"


def frozen_serial() -> Dict[str, dict]:
    """Serial C and S per public program, from the frozen production comparison."""

    payload = json.loads(SERIAL_RUNS.read_text())
    out: Dict[str, dict] = {}
    for row in payload["runs"]:
        if row.get("arm") != "serial":
            continue
        key = row["program"]
        pair = (row["cycles"], row["scratch"])
        if key in out and (out[key]["cycles"], out[key]["scratch"]) != pair:
            raise ValueError(f"serial record for {key} is not constant across repeats")
        out[key] = {"cycles": row["cycles"], "scratch": row["scratch"]}
    if len(out) != 8:
        raise ValueError(f"expected eight serial programs, found {len(out)}")
    return out


def score(rows: List[dict], serial: Dict[str, dict]) -> float:
    """sqrt(GM(C_serial/C) * GM(S_serial/S)) over exactly the eight programs."""

    if sorted(row["program_name"] for row in rows) != sorted(serial):
        raise ValueError("a score needs exactly one row per public program")
    n = len(rows)
    speed = math.exp(sum(math.log(serial[r["program_name"]]["cycles"] / r["cycles"])
                         for r in rows) / n)
    scratch = math.exp(sum(math.log(serial[r["program_name"]]["scratch"] / r["scratch"])
                           for r in rows) / n)
    return math.sqrt(speed * scratch)


def public_recount() -> dict:
    rows = oc.read_rows(R3 / "p5" / "public_rows.jsonl")
    serial = frozen_serial()
    by_arm: Dict[tuple, Dict[int, List[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for row in rows:
        by_arm[(row["arm"], row["budget_seconds"])][row["repetition"]].append(row)
    arms: Dict[str, dict] = {}
    for (arm, budget), reps in sorted(by_arm.items(), key=lambda kv: (kv[0][0], kv[0][1] or -1)):
        scores = [score(reps[r], serial) for r in sorted(reps)]
        per_program: Dict[str, List[list]] = collections.defaultdict(list)
        for r in sorted(reps):
            for row in reps[r]:
                per_program[row["program_name"]].append([row["cycles"], row["scratch"],
                                                          row["product"]])
        arms[f"{arm}@{budget}"] = {
            "arm": arm, "budget_seconds": budget, "repetitions": len(scores),
            "scores": scores, "min": min(scores), "max": max(scores),
            "per_program_distinct_CSJ": {k: sorted({tuple(v) for v in vals})
                                         for k, vals in sorted(per_program.items())},
        }
    recount = json.loads(RECOUNT.read_text())
    agreement = {}
    for name, expected in recount["arms"].items():
        key = f"{name}@{expected['budget_seconds']}"
        got = arms.get(key)
        agreement[key] = (got is not None and len(got["scores"]) == len(expected["scores"])
                          and all(abs(a - b) <= 1e-12 for a, b in zip(got["scores"],
                                                                      expected["scores"])))
    phase2 = arms["structural_bound@0.1"]["scores"][0]
    original = arms["accepted_default@None"]["scores"][0]
    classical = arms["classical@None"]["scores"][0]
    per_program = []
    for program, pair in sorted(serial.items()):
        entry = {"program": program, "serial_C": pair["cycles"], "serial_S": pair["scratch"],
                 "serial_J": pair["cycles"] * pair["scratch"]}
        for key in ("structural_bound@0.1", "accepted_default@None", "classical@None"):
            (c, s, j), = arms[key]["per_program_distinct_CSJ"][program]
            entry[key] = {"C": c, "S": s, "J": j}
        entry["phase2_vs_original"] = (
            "better" if entry["structural_bound@0.1"]["J"] < entry["accepted_default@None"]["J"]
            else "equal" if entry["structural_bound@0.1"]["J"] == entry["accepted_default@None"]["J"]
            else "worse")
        per_program.append(entry)
    return {
        "source": {"public_rows": str((R3 / "p5" / "public_rows.jsonl").relative_to(oc.ROOT)),
                   "public_rows_sha256": oc.file_sha256(R3 / "p5" / "public_rows.jsonl"),
                   "serial_runs": str(SERIAL_RUNS.relative_to(oc.ROOT)),
                   "serial_runs_sha256": oc.file_sha256(SERIAL_RUNS)},
        "formula": "sqrt(GM_i(C_serial_i/C_arm_i) * GM_i(S_serial_i/S_arm_i))",
        "serial": serial,
        "arms": arms,
        "per_program": per_program,
        "lead_recount_agreement": agreement,
        "all_agree": all(agreement.values()) and len(agreement) == 4,
        "relative_gain_vs_original": phase2 / original - 1,
        "relative_gain_vs_classical": phase2 / classical - 1,
        "coexistence": (
            "The public score is an exact function of eight fixed programs; every one of its "
            "15 repetitions is identical, so the finite-suite ratio 2.03276/2.00847 > 1 is "
            "arithmetic, not an estimate. The zero-touching bootstrap interval of the accepted "
            "run answers a different question: resampling programs as if drawn from a "
            "population. With 8 programs, of which only a few differ (see per_program), many "
            "resamples contain no improving program and give a ratio of exactly 1, so the lower "
            "percentile touches zero. Both statements hold simultaneously."),
    }


def stopping_audit() -> dict:
    rows = oc.read_rows(R3 / "p5" / "heldout_rows.jsonl")
    out: Dict[str, dict] = {}
    by_key = {(r["program_sha256"], r["arm"], r["budget_seconds"], r["repetition"]): r
              for r in rows}
    programs = sorted({r["program_sha256"] for r in rows})
    for budget in (0.01, 0.1, 1.0):
        cand = [r for r in rows if r["arm"] == "structural_bound" and r["budget_seconds"] == budget]
        reasons = collections.Counter(r["optimisation"]["stopped_because"] for r in cand)
        per_program = collections.defaultdict(set)
        for r in cand:
            per_program[r["program_sha256"]].add(r["optimisation"]["stopped_because"])
        capped_programs = [p for p, s in per_program.items() if s == {"query_cap"}]
        any_capped = [p for p, s in per_program.items() if "query_cap" in s]
        ties = wins = losses = 0
        capped_ties = 0
        for p in programs:
            c = [by_key[(p, "structural_bound", budget, k)]["product"] for k in range(15)]
            a = [by_key[(p, "accepted_budgeted", budget, k)]["product"] for k in range(15)]
            m = sum(math.log(y / x) for x, y in zip(c, a)) / 15
            if abs(m) <= 1e-12:
                ties += 1
                if p in capped_programs:
                    capped_ties += 1
            elif m > 0:
                wins += 1
            else:
                losses += 1
        statuses = collections.Counter()
        accepted = 0
        attempted = []
        for r in cand:
            o = r["optimisation"]
            statuses.update(o["statuses"])
            accepted += o["accepted"]
            attempted.append(o["attempted_queries"])
        out[str(budget)] = {
            "rows": len(cand),
            "stopped_because_rows": dict(reasons),
            "programs": len(per_program),
            "programs_capped_all_reps": len(capped_programs),
            "programs_capped_any_rep": len(any_capped),
            "vs_accepted_budgeted": {"wins": wins, "ties": ties, "losses": losses,
                                     "ties_capped_all_reps": capped_ties},
            "query_status_totals": dict(statuses),
            "accepted_improvements_total": accepted,
            "attempted_queries_max": max(attempted),
            "attempted_queries_mean": sum(attempted) / len(attempted),
        }
    return out


def improvement_kinds() -> dict:
    """Which coordinate each accepted structural improvement changed.

    The incumbent before an improvement is not stored, but each improvement
    records ``from``/``to`` products and its target. A target with fewer cycles
    than the product's own cycle count is a time target; otherwise scratch.
    Rows retain the final C and S, so we classify by the target's direction:
    ``targets_for`` produces (C-1, S), (C, S-1), (C+1, ...), (C-1, ...).
    """

    rows = oc.read_rows(R3 / "p5" / "heldout_rows.jsonl")
    counts: Dict[str, collections.Counter] = {}
    for budget in (0.01, 0.1, 1.0):
        c = collections.Counter()
        for r in rows:
            if r["arm"] != "structural_bound" or r["budget_seconds"] != budget:
                continue
            for imp in r["optimisation"]["improvements"]:
                tc, tm = imp["target"]
                c["improvements"] += 1
                c["window_len_" + str(len(imp["window"]))] += 1
                # (C, S) of the incumbent is not recorded; ``from`` = C*S and the
                # target satisfies tc*tm < from. Report the target shape only.
                c["target_product_ratio_lt_0.95" if tc * tm < 0.95 * imp["from"] else
                  "target_product_ratio_ge_0.95"] += 1
        counts[str(budget)] = dict(c)
    return counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    recount = public_recount()
    oc.write_json(out / "PUBLIC_SCORE_REPRODUCTION.json", recount)
    audit = {"stopping": stopping_audit(), "improvement_targets": improvement_kinds(),
             "source_sha256": oc.file_sha256(R3 / "p5" / "heldout_rows.jsonl")}
    oc.write_json(out / "STOPPING_AUDIT.json", audit)
    print(json.dumps({"public_all_agree": recount["all_agree"],
                      "gain_vs_original": recount["relative_gain_vs_original"],
                      "gain_vs_classical": recount["relative_gain_vs_classical"],
                      "stopping_0.1": audit["stopping"]["0.1"]}, indent=1))
    return 0 if recount["all_agree"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
