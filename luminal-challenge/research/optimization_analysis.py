"""Estimators and decision rules of optimization protocol 1.0.

Every number the release reports comes from raw rows through this module; the
independent auditor (``optimization_audit``) re-derives the same numbers without
importing it. The family-stratified bootstrap and the percentile rule are the
accepted owners in ``run_structural_experiments``; they are reused, not copied.

Estimand conventions (fixed before any evaluation outcome was seen):

- quality effect of candidate B against control A on one program: the mean over
  paired repetitions r of ``log(J_A,r / J_B,r)``; positive favours B;
- population effect: the mean over families of the within-family mean of the
  program effects (equal family weights);
- runtime ratio: per program, the median over repetitions of each arm's time,
  then ``log(t_B / t_A)``; family-weighted; ``exp`` of that is the geometric
  ratio (below 1 means B is faster);
- ties: |effect| <= 1e-12.
"""

from __future__ import annotations

import collections
import math
import statistics
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from research import optimization_common as oc
from research import run_structural_experiments as rse


TIE = 1e-12
BOOTSTRAP_SEED = 2026092403
RESAMPLES = 10_000
PRIMARY_PERCENTILES = (0.025, 0.975)
H4_PERCENTILES = (0.0125, 0.9875)


def stage_rows(run: Path, stage: str) -> List[dict]:
    return oc.read_rows(Path(run) / "stages" / stage / "rows.jsonl")


def expected_keys(run: Path, stage: str) -> List[str]:
    import json

    return json.loads((Path(run) / "stages" / stage / "EXPECTED_KEYS.json").read_text())["keys"]


def completeness(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    counts = collections.Counter(row["key"] for row in rows)
    expected_set = set(expected)
    return {
        "expected": len(expected),
        "observed_rows": len(rows),
        "distinct_observed": len(counts),
        "missing": sorted(expected_set - set(counts)),
        "duplicates": sorted(k for k, n in counts.items() if n > 1),
        "unexpected": sorted(set(counts) - expected_set),
        "failed": sorted(row["key"] for row in rows if row["failed_row"]),
        "complete": (expected_set == set(counts) and all(n == 1 for n in counts.values())),
    }


def _index(rows: Iterable[dict]) -> Dict[Tuple[str, str, Optional[float], int], dict]:
    out = {}
    for row in rows:
        ident = row.get("fixture_id") or row["program_sha256"]
        out[(ident, row["arm"], row["budget_seconds"], row["repetition"])] = row
    return out


def families_of(rows: Iterable[dict]) -> Dict[str, str]:
    return {(row.get("fixture_id") or row["program_sha256"]): row["family"] for row in rows}


def paired_quality(rows: Sequence[dict], control: str, candidate: str,
                   control_budget: Optional[float], candidate_budget: Optional[float],
                   repetitions: int) -> dict:
    """Per-program mean paired log(J_control / J_candidate)."""

    index = _index(rows)
    programs = sorted({(row.get("fixture_id") or row["program_sha256"]) for row in rows})
    per_program: Dict[str, float] = {}
    missing: List[str] = []
    failed: List[str] = []
    for program in programs:
        logs = []
        for r in range(repetitions):
            a = index.get((program, control, control_budget, r))
            b = index.get((program, candidate, candidate_budget, r))
            if a is None or b is None:
                missing.append(f"{program}|r{r}")
                continue
            if a["failed_row"] or b["failed_row"]:
                failed.append(f"{program}|r{r}")
                continue
            logs.append(math.log(a["product"] / b["product"]))
        if len(logs) == repetitions:
            per_program[program] = sum(logs) / len(logs)
    wins = sum(v > TIE for v in per_program.values())
    losses = sum(v < -TIE for v in per_program.values())
    return {"per_program": per_program, "missing_pairs": missing, "failed_pairs": failed,
            "wins": wins, "losses": losses, "ties": len(per_program) - wins - losses,
            "programs": len(per_program)}


def family_weighted(per_program: Dict[str, float], families: Dict[str, str]) -> float:
    grouped: Dict[str, List[float]] = collections.defaultdict(list)
    for program, value in per_program.items():
        grouped[families[program]].append(value)
    return statistics.mean(statistics.mean(v) for _, v in sorted(grouped.items()))


def bootstrap(per_program: Dict[str, float], families: Dict[str, str],
              percentiles: Sequence[float] = PRIMARY_PERCENTILES) -> dict:
    return rse.family_stratified_bootstrap(per_program, families, RESAMPLES, BOOTSTRAP_SEED,
                                           list(percentiles))


def interval_of(result: dict, percentiles: Sequence[float]) -> List[float]:
    return result["intervals"][f"{percentiles[0]}-{percentiles[1]}"]


def verdict(low: float, high: float) -> str:
    if low > 0:
        return "SUPPORTS_IMPROVEMENT"
    if high < 0:
        return "SUPPORTS_DEGRADATION"
    return "INCONCLUSIVE"


def runtime_ratio(rows: Sequence[dict], control: str, candidate: str,
                  control_budget: Optional[float], candidate_budget: Optional[float],
                  field: str, with_interval: bool = True) -> dict:
    """Per-program median time over repetitions, then log(candidate / control)."""

    def value(row: dict) -> float:
        if field == "process_seconds":
            return row["process_seconds"]
        return row["result"][field]

    times: Dict[Tuple[str, str], List[float]] = collections.defaultdict(list)
    for row in rows:
        if row["failed_row"]:
            continue
        ident = row.get("fixture_id") or row["program_sha256"]
        if (row["arm"], row["budget_seconds"]) in ((control, control_budget),
                                                     (candidate, candidate_budget)):
            times[(ident, row["arm"])].append(value(row))
    families = families_of(rows)
    per_program = {}
    for program in sorted(families):
        a, b = times.get((program, control)), times.get((program, candidate))
        if a and b and statistics.median(a) > 0 and statistics.median(b) > 0:
            per_program[program] = math.log(statistics.median(b) / statistics.median(a))
    if not per_program:
        return {"status": "INCONCLUSIVE", "programs": 0}
    mean = family_weighted(per_program, families)
    out = {"programs": len(per_program), "mean_log_ratio": mean,
           "geometric_ratio_candidate_over_control": math.exp(mean), "field": field}
    if with_interval:
        boot = bootstrap(per_program, families)
        low, high = interval_of(boot, PRIMARY_PERCENTILES)
        out["interval_log"] = [low, high]
        out["interval_ratio"] = [math.exp(low), math.exp(high)]
    return out


def absolute_times(rows: Sequence[dict], arm: str, budget: Optional[float]) -> dict:
    selected = [r for r in rows if r["arm"] == arm and r["budget_seconds"] == budget
                and not r["failed_row"]]
    if not selected:
        return {"rows": 0}

    def summary(values: List[float]) -> dict:
        values = sorted(values)
        return {"median": statistics.median(values), "p95": rse.percentile(values, 0.95),
                "max": values[-1]}

    out = {"rows": len(selected),
           "compile_seconds": summary([r["result"]["compile_seconds"] for r in selected]),
           "process_seconds": summary([r["process_seconds"] for r in selected]),
           "peak_rss_bytes_max": max(r["result"].get("peak_rss_bytes") or 0 for r in selected)}
    over = [r["result"].get("overshoot_seconds") for r in selected
            if r["result"].get("overshoot_seconds") is not None]
    if over:
        out["overshoot_seconds"] = summary(over)
    opt = [r["result"].get("optimisation") or {} for r in selected]
    if any("aggregate" in o for o in opt):
        out["nodes"] = summary([o["aggregate"]["nodes"] for o in opt if "aggregate" in o])
        out["attempted_queries"] = summary([o["attempted_queries"] for o in opt
                                            if "attempted_queries" in o])
    reasons = collections.Counter(o.get("stopped_because") for o in opt)
    out["stopped_because"] = dict(reasons)
    return out


# --------------------------------------------------------------------------
# Stage B selection
# --------------------------------------------------------------------------


def geometric_compile(rows: Sequence[dict], arm: str, budget: float) -> float:
    per_program: Dict[str, List[float]] = collections.defaultdict(list)
    for row in rows:
        if row["arm"] == arm and row["budget_seconds"] == budget and not row["failed_row"]:
            per_program[row["program_sha256"]].append(row["result"]["compile_seconds"])
    logs = [math.log(statistics.median(v)) for v in per_program.values()]
    return math.exp(sum(logs) / len(logs))


def select_search(rows: Sequence[dict], expected: Sequence[str], configs: Sequence[str]) -> dict:
    """The fixed selection rule of section 5 at 0.1 seconds."""

    from research import optimization_search as osr

    families = families_of(rows)
    status = completeness(rows, expected)
    by_arm_failed = collections.Counter(r["arm"] for r in rows if r["failed_row"])
    arm_keys = collections.defaultdict(set)
    for key in expected:
        arm_keys[key.split("|")[1]].add(key)
    present = {row["key"] for row in rows}
    table = []
    for config in configs:
        arm = f"new_{config}"
        complete = arm_keys[arm] <= present and not by_arm_failed[arm]
        control_complete = arm_keys["frozen_phase2"] <= present and not by_arm_failed["frozen_phase2"]
        entry = {"config": config, "arm": arm, "complete_and_correct": complete,
                 "control_complete_and_correct": control_complete,
                 "failed_rows": by_arm_failed[arm]}
        for budget in (0.01, 0.1, 1.0):
            paired = paired_quality(rows, "frozen_phase2", arm, budget, budget, 3)
            entry[f"effect_vs_frozen_{budget}"] = (family_weighted(paired["per_program"], families)
                                                   if paired["programs"] else None)
            entry[f"wins_ties_losses_{budget}"] = [paired["wins"], paired["ties"],
                                                   paired["losses"]]
            entry[f"programs_{budget}"] = paired["programs"]
            vs_budgeted = paired_quality(rows, "accepted_budgeted", arm, budget, budget, 3)
            entry[f"effect_vs_accepted_budgeted_{budget}"] = (
                family_weighted(vs_budgeted["per_program"], families)
                if vs_budgeted["programs"] else None)
            vs_classical = paired_quality(rows, "classical", arm, None, budget, 3)
            entry[f"effect_vs_classical_{budget}"] = (
                family_weighted(vs_classical["per_program"], families)
                if vs_classical["programs"] else None)
            entry[f"geometric_compile_seconds_{budget}"] = geometric_compile(rows, arm, budget)
        cap, policy = osr.parse_config(config)
        entry["cap"] = cap
        entry["policy"] = policy
        table.append(entry)
    eligible = [e for e in table if e["complete_and_correct"] and e["control_complete_and_correct"]
                and e["programs_0.1"] == 100]

    def order(entry: dict):
        return (entry["geometric_compile_seconds_0.1"],
                float("inf") if entry["cap"] is None else entry["cap"],
                0 if entry["policy"] == "matched" else 1)

    selected = None
    tie_group: List[str] = []
    if eligible:
        best = max(e["effect_vs_frozen_0.1"] for e in eligible)
        tied = [e for e in eligible if best - e["effect_vs_frozen_0.1"] <= TIE]
        tie_group = [e["config"] for e in tied]
        chosen = sorted(tied, key=order)[0]
        if best > TIE:
            selected = chosen
    decision = {
        "rule": "maximise family-weighted mean paired log(J_frozen_phase2/J_new) at 0.1 s over "
                "fully correct complete configurations; ties <=1e-12 broken by lower geometric "
                "compile time (GM over programs of per-program median compile_seconds), then "
                "smaller finite cap (null last), then matched before wider; best <=0 retains "
                "frozen_phase2 (NO_DEVELOPMENT_GAIN)",
        "completeness": {k: (v if not isinstance(v, list) else len(v)) for k, v in status.items()},
        "eligible": [e["config"] for e in eligible],
        "table": table,
        "best_effect_0.1": max((e["effect_vs_frozen_0.1"] for e in eligible), default=None),
        "tie_group_at_best": tie_group,
        "selected_config": selected["config"] if selected else None,
        "outcome": ("SELECTED" if selected else
                    ("NO_DEVELOPMENT_GAIN" if eligible else "ALL_NEW_CONFIGURATIONS_FAILED")),
    }
    if selected is None:
        decision["selected_compiler"] = "frozen_phase2"
    else:
        decision["selected_compiler"] = f"new_{selected['config']}"
    return decision


def engineering_decision(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    families = families_of(rows)
    status = completeness(rows, expected)
    out = {"completeness": {k: (v if not isinstance(v, list) else len(v))
                            for k, v in status.items()}, "budgets": {}}
    for budget in (0.01, 0.1, 1.0):
        paired = paired_quality(rows, "selected_reference", "selected_cached", budget, budget, 3)
        quality = family_weighted(paired["per_program"], families) if paired["programs"] else None
        compile_ratio = runtime_ratio(rows, "selected_reference", "selected_cached", budget,
                                      budget, "compile_seconds", with_interval=budget == 0.1)
        process_ratio = runtime_ratio(rows, "selected_reference", "selected_cached", budget,
                                      budget, "process_seconds", with_interval=budget == 0.1)
        variation = sum(1 for v in paired["per_program"].values() if abs(v) > TIE)
        out["budgets"][str(budget)] = {
            "quality_effect_cached_vs_reference": quality,
            "wins_ties_losses": [paired["wins"], paired["ties"], paired["losses"]],
            "programs_with_J_variation": variation, "programs": paired["programs"],
            "compile_ratio": compile_ratio, "process_ratio": process_ratio}
    primary = out["budgets"]["0.1"]
    quality_ok = (primary["quality_effect_cached_vs_reference"] is not None and
                  primary["quality_effect_cached_vs_reference"] >= -TIE)
    faster = (primary["compile_ratio"].get("mean_log_ratio", 0) < 0 or
              primary["process_ratio"].get("mean_log_ratio", 0) < 0)
    out["rule"] = ("adopt cached at 0.1 s only if its family-weighted quality is not lower "
                   "(tolerance 1e-12) and the paired geometric compile or process time decreases")
    out["quality_not_lower"] = quality_ok
    out["time_decreases"] = faster
    out["complete"] = status["complete"] and not status["failed"]
    out["adopted_build"] = "cached" if (quality_ok and faster and out["complete"]) else "reference"
    return out


def ablation_description(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    families = families_of(rows)
    status = completeness(rows, expected)
    out = {"completeness": {k: (v if not isinstance(v, list) else len(v))
                            for k, v in status.items()},
           "note": "descriptive; never triggers another round of selection", "budgets": {}}
    for budget in (0.01, 0.1, 1.0):
        paired = paired_quality(rows, "selected_dfs", "selected_bound", budget, budget, 3)
        out["budgets"][str(budget)] = {
            "quality_effect_bound_vs_dfs": (family_weighted(paired["per_program"], families)
                                            if paired["programs"] else None),
            "wins_ties_losses": [paired["wins"], paired["ties"], paired["losses"]],
            "compile_ratio_bound_over_dfs": runtime_ratio(
                rows, "selected_dfs", "selected_bound", budget, budget, "compile_seconds",
                with_interval=False)}
    return out


def minimum_detectable_effect(rows: Sequence[dict], arm: str, per_family_n: int = 40) -> dict:
    """Approximate MDE of the primary for 40 programs per family, from development.

    Uses the between-program SD of development effects within each family at 0.1 s:
    SE = sqrt(sum_f sd_f^2 / n_f) / F, MDE(two-sided 5%, 80% power) ~ 2.80 * SE.
    A design diagnostic only.
    """

    families = families_of(rows)
    paired = paired_quality(rows, "frozen_phase2", arm, 0.1, 0.1, 3)
    grouped: Dict[str, List[float]] = collections.defaultdict(list)
    for program, value in paired["per_program"].items():
        grouped[families[program]].append(value)
    sds = {f: (statistics.stdev(v) if len(v) > 1 else 0.0) for f, v in grouped.items()}
    se = math.sqrt(sum(sd ** 2 / per_family_n for sd in sds.values())) / len(sds)
    return {"arm": arm, "family_sd_of_program_effects": sds, "per_family_n": per_family_n,
            "standard_error": se, "mde_log_ratio_80pct_power": 2.80 * se,
            "note": "design diagnostic; does not change sample sizes or promise power"}


# --------------------------------------------------------------------------
# Model development and H4
# --------------------------------------------------------------------------


def select_depth(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    families = families_of(rows)
    status = completeness(rows, expected)
    table = {}
    for depth in (1, 2):
        arm = f"model_depth{depth}"
        for budget in (0.01, 0.1, 1.0):
            per_fixture: Dict[str, List[float]] = collections.defaultdict(list)
            for row in rows:
                if row["arm"] == arm and row["budget_seconds"] == budget and not row["failed_row"]:
                    per_fixture[row["fixture_id"]].append(
                        row["result"]["log_train_over_best_validation"])
            means = {f: statistics.mean(v) for f, v in per_fixture.items() if len(v) == 3}
            table[f"{arm}@{budget}"] = {
                "fixtures": len(means),
                "family_weighted_mean": family_weighted(means, families) if means else None,
                "per_fixture": means}
    d1 = table["model_depth1@0.1"]["family_weighted_mean"]
    d2 = table["model_depth2@0.1"]["family_weighted_mean"]
    complete = status["complete"] and not status["failed"]
    if not complete or d1 is None or d2 is None:
        selected, reason = None, "development matrix incomplete or failed; no depth frozen"
    elif d2 - d1 > TIE:
        selected, reason = 2, "depth 2 larger by more than 1e-12"
    else:
        selected, reason = 1, "depth 1 larger or tied within 1e-12"
    return {"rule": "family-weighted mean of log(min_training_J / best_validation_J with "
                    "training fallback) at 0.1 s over three repetitions; tie <=1e-12 -> depth 1; "
                    "test partitions never read",
            "completeness": {k: (v if not isinstance(v, list) else len(v))
                             for k, v in status.items()},
            "table": table, "selected_depth": selected, "reason": reason}


def h4_contrasts(rows: Sequence[dict], expected: Sequence[str], fixtures: Sequence[dict],
                 budgets: Sequence[float] = (0.01, 0.1, 1.0)) -> dict:
    """H4_NEW: selected_model versus one_bit and uniform_bits, per budget."""

    families = {f["fixture_id"]: f["family"] for f in fixtures}
    status = completeness(rows, expected)
    index = _index(rows)
    uniform_arms = sorted(a for a in {r["arm"] for r in rows} if a.startswith("uniform_bits_"))
    out = {"completeness": {k: (v if not isinstance(v, list) else len(v))
                            for k, v in status.items()}, "budgets": {}}
    defects = sum(1 for r in rows if r["failed_row"])
    for budget in budgets:
        per_control: Dict[str, Dict[str, float]] = {"one_bit": {}, "uniform_bits": {},
                                                    "empirical_cover": {}}
        for fixture in sorted(families):
            model = [index.get((fixture, "selected_model", budget, r)) for r in range(15)]
            if any(m is None or m["failed_row"] for m in model):
                continue
            for control in ("one_bit", "empirical_cover"):
                rows_c = [index.get((fixture, control, budget, r)) for r in range(15)]
                if any(c is None or c["failed_row"] for c in rows_c):
                    continue
                per_control[control][fixture] = statistics.mean(
                    math.log(c["result"]["best_test_J"] / m["result"]["best_test_J"])
                    for c, m in zip(rows_c, model))
            seed_means = []
            for arm in uniform_arms:
                rows_u = [index.get((fixture, arm, budget, r)) for r in range(15)]
                if any(u is None or u["failed_row"] for u in rows_u):
                    seed_means = None
                    break
                seed_means.append(statistics.mean(
                    math.log(u["result"]["best_test_J"] / m["result"]["best_test_J"])
                    for u, m in zip(rows_u, model)))
            if seed_means:
                per_control["uniform_bits"][fixture] = statistics.mean(seed_means)
        entry = {}
        for control, per_fixture in per_control.items():
            if not per_fixture:
                entry[control] = {"status": "INCONCLUSIVE", "fixtures": 0}
                continue
            boot = bootstrap(per_fixture, families, H4_PERCENTILES + PRIMARY_PERCENTILES)
            entry[control] = {
                "fixtures": len(per_fixture),
                "families": dict(collections.Counter(families[f] for f in per_fixture)),
                "effect": family_weighted(per_fixture, families),
                "interval_97_5": interval_of(boot, H4_PERCENTILES),
                "interval_95": interval_of(boot, PRIMARY_PERCENTILES),
                "wins": sum(v > TIE for v in per_fixture.values()),
                "losses": sum(v < -TIE for v in per_fixture.values()),
                "ties": sum(abs(v) <= TIE for v in per_fixture.values()),
                "per_fixture": per_fixture}
        out["budgets"][str(budget)] = entry
    primary = out["budgets"]["0.1"]
    informative = len({families[f] for f in families})
    lows = [primary[c]["interval_97_5"][0] for c in ("one_bit", "uniform_bits")
            if "interval_97_5" in primary[c]]
    highs = [primary[c]["interval_97_5"][1] for c in ("one_bit", "uniform_bits")
             if "interval_97_5" in primary[c]]
    accounted = all(primary[c].get("fixtures") == 30 for c in ("one_bit", "uniform_bits"))
    gate = {"all_30_fixtures_accounted": accounted and status["complete"],
            "informative_families": informative, "at_least_3_families": informative >= 3,
            "correctness_or_evidence_defects": defects, "lower_bounds": lows,
            "both_lower_bounds_positive": len(lows) == 2 and all(v > 0 for v in lows)}
    passed = (gate["all_30_fixtures_accounted"] and gate["at_least_3_families"] and
              defects == 0 and gate["both_lower_bounds_positive"])
    if passed:
        h4 = "PASS"
    elif len(highs) == 2 and all(v < 0 for v in highs) and defects == 0 and accounted:
        h4 = "MODEL_DISADVANTAGE"
    else:
        h4 = "INCONCLUSIVE"
    out["gate"] = gate
    out["H4_NEW"] = h4
    return out


def model_counts(rows: Sequence[dict]) -> dict:
    out: Dict[str, dict] = {}
    for row in rows:
        if row["failed_row"]:
            continue
        label = "uniform_bits" if row["arm"].startswith("uniform_bits_") else row["arm"]
        key = f"{label}@{row['budget_seconds']}"
        bucket = out.setdefault(key, collections.Counter())
        result = row["result"]
        bucket["rows"] += 1
        for name, value in result["counts"].items():
            if isinstance(value, bool):
                bucket[f"{name}_rows"] += int(value)
            else:
                bucket[name] += value
        for where, value in result["discoveries"].items():
            bucket[f"discoveries_{where}"] += value
        bucket["learner_seconds_total"] += result["learner_seconds"]
    return {k: dict(v) for k, v in sorted(out.items())}


# --------------------------------------------------------------------------
# Public score
# --------------------------------------------------------------------------


def public_scores(rows: Sequence[dict], serial_frozen: Dict[str, dict]) -> dict:
    """S_arm = sqrt(GM(C_serial/C_arm) * GM(S_serial/S_arm)), one per repetition."""

    names = {}
    for row in rows:
        if row.get("result"):
            names[row["program_sha256"]] = row["result"]["program_name"]
    serial_rows = [r for r in rows if r["arm"] == "serial"]
    serial_check = []
    serial: Dict[str, Tuple[int, int]] = {}
    for row in serial_rows:
        name = row["result"]["program_name"]
        pair = (row["cycles"], row["scratch"])
        serial.setdefault(name, pair)
        serial_check.append(pair == (serial_frozen[name]["cycles"], serial_frozen[name]["scratch"])
                            and pair == serial[name])
    arms = sorted({(r["arm"], r["budget_seconds"]) for r in rows if r["arm"] != "serial"},
                  key=lambda x: (x[0], -1 if x[1] is None else x[1]))
    index = _index(rows)
    programs = sorted(names)
    out = {}
    for arm, budget in arms:
        scores = []
        per_program = collections.defaultdict(list)
        for r in range(15):
            chosen = [index.get((p, arm, budget, r)) for p in programs]
            if any(c is None or c["failed_row"] for c in chosen):
                scores.append(None)
                continue
            speed = math.exp(sum(math.log(serial[names[c["program_sha256"]]][0] / c["cycles"])
                                 for c in chosen) / len(chosen))
            scratch = math.exp(sum(math.log(serial[names[c["program_sha256"]]][1] / c["scratch"])
                                   for c in chosen) / len(chosen))
            scores.append(math.sqrt(speed * scratch))
            for c in chosen:
                per_program[names[c["program_sha256"]]].append([c["cycles"], c["scratch"],
                                                                 c["product"]])
        valid = [s for s in scores if s is not None]
        out[f"{arm}@{budget}"] = {
            "arm": arm, "budget_seconds": budget, "scores": scores,
            "min": min(valid) if valid else None, "max": max(valid) if valid else None,
            "geometric_mean": (math.exp(sum(math.log(s) for s in valid) / len(valid))
                               if valid else None),
            "complete": len(valid) == 15,
            "per_program_distinct_CSJ": {k: sorted({tuple(x) for x in v})
                                         for k, v in sorted(per_program.items())}}
    return {"serial_matches_frozen": all(serial_check) and len(serial_check) == 120,
            "serial_rows": len(serial_check), "serial": {k: list(v) for k, v in serial.items()},
            "arms": out, "programs": [names[p] for p in programs]}


def paired_score_ratios(scores: dict, candidate: str, control: str) -> dict:
    a, b = scores["arms"][candidate]["scores"], scores["arms"][control]["scores"]
    ratios = [x / y if x is not None and y is not None else None for x, y in zip(a, b)]
    valid = [r for r in ratios if r is not None]
    return {"candidate": candidate, "control": control, "ratios": ratios,
            "strict_improvement_every_repetition": (len(valid) == 15 and
                                                    all(r > 1 + 1e-12 for r in valid)),
            "improving_repetitions": sum(r > 1 + 1e-12 for r in valid),
            "tied_repetitions": sum(abs(r - 1) <= 1e-12 for r in valid),
            "worsening_repetitions": sum(r < 1 - 1e-12 for r in valid)}
