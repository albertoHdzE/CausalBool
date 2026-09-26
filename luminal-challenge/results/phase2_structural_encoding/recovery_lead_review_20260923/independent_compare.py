"""Lead-only raw-row audit; does not import the research implementation.

Run after measurement stops: python independent_compare.py RUN OUTPUT.json
Audits the fixed deterministic candidate; conditional model inference belongs
to the separate P4/P5 gate review.
"""
import hashlib
import json
import math
from pathlib import Path
import random
import statistics
import sys


def quantile(values, fraction):
    position = (len(values) - 1) * fraction
    lower = math.floor(position)
    upper = math.ceil(position)
    return values[lower] + (position - lower) * (values[upper] - values[lower])


def interval(per_program, family_of):
    groups = {}
    for program in sorted(per_program):
        groups.setdefault(family_of[program], []).append(per_program[program])
    rng = random.Random(20261021)
    estimates = []
    for _ in range(10000):
        estimates.append(statistics.mean([
            statistics.mean([rng.choice(values) for _ in values])
            for _, values in sorted(groups.items())
        ]))
    estimates.sort()
    return {
        "point": statistics.mean([statistics.mean(values) for values in groups.values()]),
        "ci95": [quantile(estimates, .025), quantile(estimates, .975)],
        "programs": len(per_program),
        "families": {name: len(values) for name, values in sorted(groups.items())},
    }


def audit(run):
    p0 = json.loads((run / "p0/summary.json").read_text())
    cohorts = {
        "public": {entry["program_sha256"]: "public" for entry in p0["public"]},
        "heldout": {entry["program_sha256"]: entry["family"] for entry in p0["heldout"]["programs"]},
    }
    assert len(cohorts["public"]) == 8 and len(cohorts["heldout"]) == 100
    budgets = (.01, .1, 1.0)
    refs = ("accepted_bootstrap", "accepted_default", "classical")
    arms = ("accepted_budgeted", "structural_dfs", "structural_bound", "structural_expanded")
    output = {"audit_scope": "fixed-candidate P5 comparisons and exact raw membership",
              "primary": "heldout structural_bound versus accepted_budgeted at 0.1 seconds",
              "source_sha256": {}, "entries": []}
    for cohort, families in cohorts.items():
        path = run / "p5" / f"{cohort}_rows.jsonl"
        output["source_sha256"][str(path)] = hashlib.sha256(path.read_bytes()).hexdigest()
        rows = [json.loads(line) for line in path.open() if line.strip()]
        indexed = {}
        for row in rows:
            assert row["program_sha256"] in families
            assert row["corpus"] == cohort and row["stage"] == "p5"
            assert not row.get("failed_row") and not row.get("timed_out")
            assert row["exit_code"] == 0 and row["correctness"] == "PASS"
            assert row["cycles"] > 0 and row["scratch"] > 0
            assert row["product"] == row["cycles"] * row["scratch"]
            assert row.get("discrepancy_count", 0) == 0
            assert row.get("search_seed") is None
            key = (row["program_sha256"], row["arm"], row["budget_seconds"], row["repetition"])
            assert key not in indexed, ("duplicate", key)
            indexed[key] = row
        expected = {(pid, arm, None, repetition)
                    for pid in families for arm in refs for repetition in range(15)}
        expected.update((pid, arm, budget, repetition)
                        for pid in families for arm in arms for budget in budgets
                        for repetition in range(15))
        if any(row["arm"] == "structural_model" for row in rows):
            expected.update((pid, "structural_model", budget, repetition)
                            for pid in families for budget in budgets for repetition in range(15))
        assert set(indexed) == expected, (cohort, "membership mismatch")
        for budget in budgets:
            for control in ("accepted_budgeted", *refs):
                quality = {}
                compile_cost = {}
                process_cost = {}
                for pid in families:
                    candidate_rows = [indexed[pid, "structural_bound", budget, r] for r in range(15)]
                    control_rows = [indexed[pid, control, None if control in refs else budget, r]
                                    for r in range(15)]
                    quality[pid] = statistics.mean([
                        math.log(base["product"] / cand["product"])
                        for base, cand in zip(control_rows, candidate_rows)
                    ])
                    for metric, destination in (("compile_seconds", compile_cost),
                                                 ("process_seconds", process_cost)):
                        cand = statistics.median([r[metric] for r in candidate_rows])
                        base = statistics.median([r[metric] for r in control_rows])
                        assert math.isfinite(cand) and math.isfinite(base) and cand > 0 and base > 0
                        destination[pid] = math.log(cand / base)
                output["entries"].append({
                    "corpus": cohort, "budget": budget, "control": control,
                    "quality_log_control_over_candidate": interval(quality, families),
                    "compile_log_candidate_over_control": interval(compile_cost, families),
                    "process_log_candidate_over_control": interval(process_cost, families),
                    "wins": sum(value > 0 for value in quality.values()),
                    "ties": sum(value == 0 for value in quality.values()),
                    "losses": sum(value < 0 for value in quality.values()),
                    "per_program_quality": quality,
                })
    return output


if __name__ == "__main__":
    result = audit(Path(sys.argv[1]).resolve())
    with Path(sys.argv[2]).open("x") as output:
        json.dump(result, output, indent=2, allow_nan=False)
        output.write("\n")
    print("PASS: exact P5 membership and 24 independently recomputed contrasts")
