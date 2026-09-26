"""Estimators, selection and gates of the objective-index protocol 1.0.

Every reported number comes from raw rows through this module; the independent
auditor (``objective_index_audit``) re-derives them without importing it.

Owners reused, not copied: ``optimization_analysis.paired_quality`` and
``family_weighted`` (paired repetition logs averaged inside program; equal
family weights), ``run_structural_experiments.family_stratified_bootstrap``
(programs resampled within family) and ``optimization_analysis.public_scores``
(the pinned score formula, one score per repetition).

Conventions fixed before any evaluation outcome:

- quality effect of candidate B against control A on one program: the mean over
  paired repetitions r of log(J_A,r / J_B,r); positive favours B. Random-order
  seeds (fixture study) are averaged after repetitions, inside the fixture;
- population effect: mean over families of the within-family mean;
- bootstrap: 10,000 resamples, seed 2026092504, programs within family;
  Bonferroni three-comparison percentiles 1/120 and 119/120; conditional
  learned-compiler pair 0.0125/0.9875; descriptive 0.025/0.975;
- runtime: per program, the median over repetitions of each arm's time, then
  log(t_B / t_A), family-weighted; exp of it is the geometric ratio;
- ties: |effect| <= 1e-12.
"""

from __future__ import annotations

import collections
import math
import statistics
from typing import Dict, List, Optional, Sequence

from research import objective_index_common as oic
from research import optimization_analysis as oa
from research import run_structural_experiments as rse


TIE = 1e-12
RESAMPLES = 10_000
SEED = oic.SEED_BOOTSTRAP
BONFERRONI3 = (1 / 120, 119 / 120)
CONDITIONAL2 = (0.0125, 0.9875)
DESCRIPTIVE = (0.025, 0.975)
PRIMARY_BUDGET = oic.PRIMARY_BUDGET


def bootstrap(per_program: Dict[str, float], families: Dict[str, str],
              percentiles: Sequence[float]) -> dict:
    return rse.family_stratified_bootstrap(per_program, families, RESAMPLES, SEED,
                                           list(percentiles))


def summarise(per_program: Dict[str, float], families: Dict[str, str],
              percentiles: Sequence[float], extra: Optional[dict] = None) -> dict:
    """Point estimate, interval, wins/ties/losses and per-family means."""

    out = dict(extra or {})
    if not per_program:
        out.update(status="INCONCLUSIVE", programs=0, reason="no complete paired program")
        return out
    boot = bootstrap(per_program, families, percentiles)
    low, high = boot["intervals"][f"{percentiles[0]}-{percentiles[1]}"]
    grouped: Dict[str, List[float]] = collections.defaultdict(list)
    for program, value in per_program.items():
        grouped[families[program]].append(value)
    wins = sum(v > TIE for v in per_program.values())
    losses = sum(v < -TIE for v in per_program.values())
    out.update(
        point=oa.family_weighted(per_program, families), interval=[low, high],
        percentiles=list(percentiles), programs=len(per_program),
        families={f: len(v) for f, v in sorted(grouped.items())},
        family_means={f: statistics.mean(v) for f, v in sorted(grouped.items())},
        wins=wins, losses=losses, ties=len(per_program) - wins - losses,
        geometric_J_ratio_control_over_candidate=math.exp(oa.family_weighted(per_program,
                                                                            families)),
        verdict=("CANDIDATE_BETTER" if low > 0 else "CANDIDATE_WORSE" if high < 0
                 else "INCONCLUSIVE"))
    return out


def quality(rows: Sequence[dict], control: str, candidate: str, control_budget,
            candidate_budget, repetitions: int, percentiles: Sequence[float]) -> dict:
    paired = oa.paired_quality(rows, control, candidate, control_budget, candidate_budget,
                               repetitions)
    families = oa.families_of(rows)
    return summarise(paired["per_program"], families, percentiles, {
        "control": control, "candidate": candidate, "control_budget": control_budget,
        "candidate_budget": candidate_budget, "missing_pairs": len(paired["missing_pairs"]),
        "failed_pairs": len(paired["failed_pairs"])})


def runtime(rows: Sequence[dict], control: str, candidate: str, control_budget,
            candidate_budget, field: str, percentiles: Sequence[float]) -> dict:
    """Per-program median time over repetitions; log(candidate/control)."""

    def value(row: dict) -> float:
        return row["process_seconds"] if field == "process_seconds" else row["result"][field]

    times: Dict[tuple, List[float]] = collections.defaultdict(list)
    for row in rows:
        if row["failed_row"]:
            continue
        ident = row.get("fixture_id") or row["program_sha256"]
        if (row["arm"], row["budget_seconds"]) == (control, control_budget):
            times[(ident, "control")].append(value(row))
        if (row["arm"], row["budget_seconds"]) == (candidate, candidate_budget):
            times[(ident, "candidate")].append(value(row))
    families = oa.families_of(rows)
    per_program = {}
    for program in sorted(families):
        a, b = times.get((program, "control")), times.get((program, "candidate"))
        if a and b and statistics.median(a) > 0 and statistics.median(b) > 0:
            per_program[program] = math.log(statistics.median(b) / statistics.median(a))
    if not per_program:
        return {"status": "INCONCLUSIVE", "programs": 0, "field": field}
    boot = bootstrap(per_program, families, percentiles)
    low, high = boot["intervals"][f"{percentiles[0]}-{percentiles[1]}"]
    mean = oa.family_weighted(per_program, families)
    return {"field": field, "control": control, "candidate": candidate,
            "programs": len(per_program), "mean_log_ratio": mean,
            "geometric_ratio_candidate_over_control": math.exp(mean),
            "interval_log": [low, high], "interval_ratio": [math.exp(low), math.exp(high)],
            "percentiles": list(percentiles),
            "faster": high < 0, "slower": low > 0}


# --------------------------------------------------------------------------
# Development selection (section 3)
# --------------------------------------------------------------------------


def cell_complete(rows: Sequence[dict], arm: str, budget, programs: Sequence[str],
                  repetitions: int) -> dict:
    index = {(r["program_sha256"], r["repetition"]): r for r in rows
             if r["arm"] == arm and r["budget_seconds"] == budget}
    missing = [(p, r) for p in programs for r in range(repetitions) if (p, r) not in index]
    failed = [k for k, row in index.items() if row["failed_row"]]
    return {"missing": len(missing), "failed": len(failed),
            "complete_and_correct": not missing and not failed}


def select_arm(rows: Sequence[dict], expected: Sequence[str], repetitions: int = 3) -> dict:
    """Maximum equal-family mean paired log(J_A0/J_arm) at 0.1 s among eligible arms."""

    completeness = oa.completeness(rows, expected)
    programs = sorted({r["program_sha256"] for r in rows})
    control = "A0_frozen_phase2"
    control_cell = cell_complete(rows, control, PRIMARY_BUDGET, programs, repetitions)
    table = []
    for number, arm in enumerate(oic.ARMS):
        cell = cell_complete(rows, arm, PRIMARY_BUDGET, programs, repetitions)
        eligible = cell["complete_and_correct"] and control_cell["complete_and_correct"]
        entry = {"arm": arm, "number": number, "cell": cell, "eligible": eligible}
        if arm == control:
            entry.update(effect=0.0, compile_log_ratio=0.0)
        elif eligible:
            q = quality(rows, control, arm, PRIMARY_BUDGET, PRIMARY_BUDGET, repetitions,
                        DESCRIPTIVE)
            rt = runtime(rows, control, arm, PRIMARY_BUDGET, PRIMARY_BUDGET, "compile_seconds",
                         DESCRIPTIVE)
            entry.update(effect=q["point"], quality=q,
                         compile_log_ratio=rt["mean_log_ratio"], compile=rt)
        else:
            entry.update(effect=None, reason="INELIGIBLE: missing or failed cells")
        table.append(entry)
    eligible = [e for e in table if e["eligible"] and e.get("effect") is not None]
    best = max(e["effect"] for e in eligible)
    tied = [e for e in eligible if e["effect"] >= best - TIE]
    tied.sort(key=lambda e: (e["compile_log_ratio"], e["number"]))
    chosen = tied[0]
    return {"rule": "max equal-family mean paired log(J_A0/J_arm) at 0.1 s; |diff|<=1e-12 "
                    "ties -> lower paired geometric compile time (family-weighted mean log of "
                    "per-program median compile_seconds relative to A0) -> lowest arm number",
            "completeness": {k: (len(v) if isinstance(v, list) else v)
                             for k, v in completeness.items()},
            "table": table, "best_effect": best, "tie_group": [e["arm"] for e in tied],
            "selected_arm": chosen["arm"], "selected_effect": chosen["effect"]}


def ablations(rows: Sequence[dict], repetitions: int, budgets=oic.BUDGETS,
              percentiles=DESCRIPTIVE) -> List[dict]:
    """Adjacent ladder steps at every budget: quality and compile-time cost."""

    out = []
    for budget in budgets:
        for control, candidate in zip(oic.ARMS, oic.ARMS[1:]):
            out.append({"budget": budget, "step": f"{control}->{candidate}",
                        "quality": quality(rows, control, candidate, budget, budget, repetitions,
                                           percentiles),
                        "compile": runtime(rows, control, candidate, budget, budget,
                                           "compile_seconds", percentiles),
                        "process": runtime(rows, control, candidate, budget, budget,
                                           "process_seconds", percentiles)})
    return out


def sensitivity(rows: Sequence[dict], selected: str, controls: Sequence[tuple],
                per_family_n: int = 40, repetitions: int = 3) -> dict:
    """Approximate minimum detectable effect for the fixed fresh sample size.

    SE = sqrt(sum_f sd_f^2 / n_f) / F from development program effects at 0.1 s;
    MDE = (z_{1-alpha/2} + z_{0.8}) * SE with Bonferroni alpha = 0.05/3. A design
    diagnostic; it changes no sample size and promises no power.
    """

    z_alpha = statistics.NormalDist().inv_cdf(1 - 0.05 / 3 / 2)
    z_power = statistics.NormalDist().inv_cdf(0.8)
    families = oa.families_of(rows)
    out = {"per_family_n": per_family_n, "z_alpha_bonferroni3": z_alpha, "z_power80": z_power,
           "contrasts": {}}
    for control, budget in controls:
        if control == selected and budget == PRIMARY_BUDGET:
            out["contrasts"][control] = {"note": "selected equals this control: identity"}
            continue
        paired = oa.paired_quality(rows, control, selected, budget, PRIMARY_BUDGET, repetitions)
        grouped: Dict[str, List[float]] = collections.defaultdict(list)
        for program, value in paired["per_program"].items():
            grouped[families[program]].append(value)
        sds = {f: (statistics.stdev(v) if len(v) > 1 else 0.0) for f, v in grouped.items()}
        se = math.sqrt(sum(sd ** 2 / per_family_n for sd in sds.values())) / max(len(sds), 1)
        out["contrasts"][control] = {
            "development_point": oa.family_weighted(paired["per_program"], families)
            if paired["per_program"] else None,
            "family_sd": sds, "standard_error": se,
            "mde_log_ratio": (z_alpha + z_power) * se}
    return out


# --------------------------------------------------------------------------
# Fixture learning study (section 8)
# --------------------------------------------------------------------------


def _fixture_index(rows: Sequence[dict]) -> Dict[tuple, dict]:
    return {(r["fixture_id"], r["arm"], r["budget_seconds"], r["repetition"]): r for r in rows}


def learning_contrast(rows: Sequence[dict], candidate: str, control_labels: Sequence[str],
                      budget, repetitions: int, percentiles: Sequence[float],
                      field: str = "best_test_J") -> dict:
    """log(J_control / J_candidate): repetitions, then seeds, inside each fixture."""

    index = _fixture_index(rows)
    fixtures = sorted({r["fixture_id"] for r in rows})
    families = {r["fixture_id"]: r["family"] for r in rows}
    per_fixture: Dict[str, float] = {}
    incomplete = []
    for fixture in fixtures:
        seed_means = []
        for label in control_labels:
            logs = []
            for rep in range(repetitions):
                a = index.get((fixture, label, budget, rep))
                b = index.get((fixture, candidate, budget, rep))
                if a is None or b is None or a["failed_row"] or b["failed_row"]:
                    break
                logs.append(math.log(a["result"][field] / b["result"][field]))
            if len(logs) != repetitions:
                incomplete.append(f"{fixture}|{label}")
                break
            seed_means.append(sum(logs) / len(logs))
        if len(seed_means) == len(control_labels):
            per_fixture[fixture] = sum(seed_means) / len(seed_means)
    return summarise(per_fixture, families, percentiles,
                     {"candidate": candidate, "controls": list(control_labels), "budget": budget,
                      "field": field, "incomplete": incomplete,
                      "fixtures_expected": len(fixtures)})


RANDOM_LABELS = tuple(f"random_{tag}" for tag in oic.RANDOM_ORDER_SEEDS)


def h_learn(rows: Sequence[dict], expected: Sequence[str], fixtures_expected: int = 30,
            repetitions: int = 15) -> dict:
    completeness = oa.completeness(rows, expected)
    defects = sum(r["result"].get("defect_count", 0) for r in rows if r.get("result"))
    failed = sum(1 for r in rows if r["failed_row"])
    contrasts = {
        "hamming": learning_contrast(rows, "tree", ["hamming"], PRIMARY_BUDGET, repetitions,
                                     BONFERRONI3),
        "random": learning_contrast(rows, "tree", RANDOM_LABELS, PRIMARY_BUDGET, repetitions,
                                    BONFERRONI3),
        "shuffled_tree": learning_contrast(rows, "tree", ["shuffled_tree"], PRIMARY_BUDGET,
                                           repetitions, BONFERRONI3),
    }
    complete = (completeness["complete"] and all(c.get("programs") == fixtures_expected
                                                 for c in contrasts.values()))
    lower_positive = all(c.get("interval", [0])[0] > 0 for c in contrasts.values())
    verdict = "PASS" if complete and defects == 0 and failed == 0 and lower_positive else "FAIL"
    return {"hypothesis": "H_LEARN: tree ranks unseen fixture candidates better than hamming, "
                          "random and shuffled_tree at 0.1 s (best_test_J endpoint)",
            "contrasts": contrasts, "complete_30_fixture_membership": complete,
            "defects": defects, "failed_rows": failed, "all_three_lower_bounds_positive":
            lower_positive, "verdict": verdict,
            "completeness": {k: (len(v) if isinstance(v, list) else v)
                             for k, v in completeness.items()}}


def learning_descriptive(rows: Sequence[dict], repetitions: int = 15) -> dict:
    out = {}
    for budget in oic.BUDGETS:
        for label, controls in (("ascending", ["ascending"]),
                                ("empirical_cover", ["empirical_cover"]),
                                ("hamming", ["hamming"]), ("random", list(RANDOM_LABELS)),
                                ("shuffled_tree", ["shuffled_tree"])):
            out[f"{label}@{budget}"] = learning_contrast(rows, "tree", controls, budget,
                                                         repetitions, DESCRIPTIVE)
    return out


def fixed_work_summary(rows: Sequence[dict]) -> dict:
    """Mean prefix metrics per arm and checkpoint (descriptive; prefixes are nested)."""

    per_arm: Dict[str, Dict[str, List[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    for row in rows:
        result = row.get("result") or {}
        arm = "random" if row["arm"].startswith("random_") else row["arm"]
        for prefix in result.get("prefixes") or []:
            key = "whole_pool" if prefix.get("whole_pool") else str(prefix["checkpoint"])
            per_arm[arm][key].append(prefix)
    out = {}
    for arm, by_checkpoint in sorted(per_arm.items()):
        out[arm] = {}
        for key, prefixes in sorted(by_checkpoint.items()):
            out[arm][key] = {
                "rows": len(prefixes),
                "mean_complete": statistics.mean(p["complete"] for p in prefixes),
                "mean_complete_test": statistics.mean(p["complete_test"] for p in prefixes),
                "mean_elite_level_complete": statistics.mean(p["elite_level_complete"]
                                                             for p in prefixes),
                "mean_elite_level_test": statistics.mean(p["elite_level_test"] for p in prefixes),
                "mean_log_train_over_best_test": statistics.mean(
                    p["log_train_over_best_test"] for p in prefixes)}
    return out


# --------------------------------------------------------------------------
# Public score (section 10)
# --------------------------------------------------------------------------


def public_score(rows: Sequence[dict], serial_frozen: Dict[str, dict], candidate: str,
                 controls: Sequence[str]) -> dict:
    scores = oa.public_scores(rows, serial_frozen)
    out = {"scores": scores, "ratios": {}, "reconciliation": {}, "leave_one_out": {}}
    names = scores["programs"]
    index = {}
    for row in rows:
        if row.get("result"):
            index[(row["result"]["program_name"], row["arm"], row["budget_seconds"],
                   row["repetition"])] = row
    serial = scores["serial"]
    for control in controls:
        out["ratios"][control] = oa.paired_score_ratios(scores, candidate, control)
        c_arm, c_budget = control.split("@")
        k_arm, k_budget = candidate.split("@")
        c_budget = None if c_budget == "None" else float(c_budget)
        k_budget = None if k_budget == "None" else float(k_budget)
        recon = []
        loo = {name: [] for name in names}
        for rep in range(15):
            rows_c = [index.get((n, c_arm, c_budget, rep)) for n in names]
            rows_k = [index.get((n, k_arm, k_budget, rep)) for n in names]
            if any(r is None for r in rows_c + rows_k):
                recon.append(None)
                continue
            mean_log = sum(math.log(a["product"] / b["product"])
                           for a, b in zip(rows_c, rows_k)) / len(names)
            ratio = out["ratios"][control]["ratios"][rep]
            recon.append({"score_ratio": ratio, "exp_half_mean_log_J": math.exp(mean_log / 2),
                          "abs_difference": abs(ratio - math.exp(mean_log / 2))})
            for drop in names:
                kept = [(a, b) for a, b, n in zip(rows_c, rows_k, names) if n != drop]

                def score(pairs, which):
                    speed = math.exp(sum(math.log(serial[n][0] / p[which]["cycles"])
                                         for p, n in zip(pairs, [x for x in names if x != drop]))
                                     / len(pairs))
                    scratch = math.exp(sum(math.log(serial[n][1] / p[which]["scratch"])
                                           for p, n in zip(pairs, [x for x in names if x != drop]))
                                       / len(pairs))
                    return math.sqrt(speed * scratch)

                loo[drop].append(score(kept, 1) / score(kept, 0))
        out["reconciliation"][control] = recon
        out["leave_one_out"][control] = {name: {"min": min(v), "max": max(v)}
                                         for name, v in loo.items() if v}
        per_program = {}
        for n in names:
            pairs = [(index.get((n, c_arm, c_budget, r)), index.get((n, k_arm, k_budget, r)))
                     for r in range(15)]
            pairs = [(a, b) for a, b in pairs if a and b]
            per_program[n] = {"improving_reps": sum(b["product"] < a["product"] for a, b in pairs),
                              "worsening_reps": sum(b["product"] > a["product"] for a, b in pairs),
                              "equal_reps": sum(b["product"] == a["product"] for a, b in pairs)}
        out.setdefault("per_program_vs", {})[control] = per_program
    return out
