"""Estimators and decision rules of the Phase 2 next round (protocol 1.0).

Reads raw stage rows only. Owners reused, not restated: the family-stratified
program bootstrap (``run_structural_experiments.family_stratified_bootstrap``)
and the public-score arithmetic convention (serial denominator, geometric means
of cycle and scratch ratios, square root). The independent numerical auditor
(``next_round_audit``) must NOT import this module.

Conventions fixed before any development outcome was read:

- J = cycles * scratch; quality statistics use log J, lower is better.
- Repetitions are averaged inside a program (log J or paired log ratio);
  compile times use the per-program MEDIAN over repetitions; programs are the
  sampling unit, families are weighted equally.
- "Geometric median compile time" of an arm at a budget is
  exp(equal-family mean over programs of log(median compile_seconds)).
- Development intervals are descriptive (95%, seed 2026092602, 10,000
  resamples); confirmation intervals use the protocol percentiles.
"""

from __future__ import annotations

import collections
import math
import statistics
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from research import next_round_common as nrc
from research import run_structural_experiments as rse

TIE = 1e-12
TARGET_RATES = (0.01, 0.05)


# --------------------------------------------------------------------------
# Basic indexing
# --------------------------------------------------------------------------


def index(rows: Iterable[dict]) -> Dict[Tuple[str, str, object, int], dict]:
    out = {}
    for row in rows:
        key = (row["program_sha256"], row["arm"], row["budget_seconds"], row["repetition"])
        if key in out:
            raise ValueError(f"duplicate row {key}")
        out[key] = row
    return out


def families_of(rows: Iterable[dict]) -> Dict[str, str]:
    return {row["program_sha256"]: row["family"] for row in rows}


def family_mean(per_program: Dict[str, float], families: Dict[str, str]) -> float:
    grouped: Dict[str, List[float]] = collections.defaultdict(list)
    for program, value in per_program.items():
        grouped[families[program]].append(value)
    return statistics.mean(statistics.mean(v) for _, v in sorted(grouped.items()))


def family_breakdown(per_program: Dict[str, float], families: Dict[str, str]) -> dict:
    grouped: Dict[str, List[float]] = collections.defaultdict(list)
    for program, value in per_program.items():
        grouped[families[program]].append(value)
    return {f: {"n": len(v), "mean": statistics.mean(v)} for f, v in sorted(grouped.items())}


def bootstrap(per_program: Dict[str, float], families: Dict[str, str],
              percentiles: Sequence[float] = nrc.PRIMARY_PERCENTILES) -> dict:
    out = rse.family_stratified_bootstrap(per_program, families, nrc.RESAMPLES,
                                          nrc.SEED_BOOTSTRAP, list(percentiles))
    out["interval"] = out["intervals"][f"{percentiles[0]}-{percentiles[1]}"]
    return out


def completeness(rows: Sequence[dict], expected: Sequence[str]) -> dict:
    counts = collections.Counter(row["key"] for row in rows)
    expected_set = set(expected)
    return {"expected": len(expected), "observed": len(counts),
            "missing": sorted(expected_set - set(counts))[:20],
            "missing_count": len(expected_set - set(counts)),
            "unexpected_count": len(set(counts) - expected_set),
            "duplicates": sorted(k for k, n in counts.items() if n > 1)[:20],
            "failed": sum(1 for r in rows if r["failed_row"]),
            "timed_out": sum(1 for r in rows if r["timed_out"]),
            "complete": expected_set == set(counts) and all(n == 1 for n in counts.values())}


# --------------------------------------------------------------------------
# Quality and cost per arm
# --------------------------------------------------------------------------


def per_program_logj(rows: Sequence[dict], arm: str, budget, repetitions: int
                     ) -> Tuple[Dict[str, float], List[str]]:
    """Mean over repetitions of log J; programs with a failed/missing row are listed."""

    by_program: Dict[str, List[Optional[float]]] = collections.defaultdict(list)
    for row in rows:
        if row["arm"] == arm and row["budget_seconds"] == budget:
            by_program[row["program_sha256"]].append(
                None if row["failed_row"] else math.log(row["product"]))
    out, incomplete = {}, []
    for program, values in by_program.items():
        if len(values) == repetitions and all(v is not None for v in values):
            out[program] = statistics.mean(values)
        else:
            incomplete.append(program)
    return out, sorted(incomplete)


def per_program_median(rows: Sequence[dict], arm: str, budget, field: str) -> Dict[str, float]:
    values: Dict[str, List[float]] = collections.defaultdict(list)
    for row in rows:
        if row["arm"] == arm and row["budget_seconds"] == budget and not row["failed_row"]:
            value = row["process_seconds"] if field == "process_seconds" else row["result"][field]
            values[row["program_sha256"]].append(value)
    return {p: statistics.median(v) for p, v in values.items()}


def geometric_time(rows: Sequence[dict], arm: str, budget, field: str = "compile_seconds"
                   ) -> Optional[float]:
    medians = per_program_median(rows, arm, budget, field)
    if not medians or min(medians.values()) <= 0:
        return None
    families = families_of(rows)
    return math.exp(family_mean({p: math.log(v) for p, v in medians.items()}, families))


COST_FIELDS = ("compile_seconds", "bootstrap_seconds", "optimisation_seconds",
               "validate_seconds", "import_seconds", "process_seconds")


def arm_summary(rows: Sequence[dict], arm: str, budget, repetitions: int) -> dict:
    families = families_of(rows)
    logj, incomplete = per_program_logj(rows, arm, budget, repetitions)
    out = {"arm": arm, "budget_seconds": budget, "programs": len(logj),
           "incomplete_programs": incomplete,
           "family_mean_log_J": family_mean(logj, families) if logj else None,
           "family_breakdown_log_J": family_breakdown(logj, families) if logj else None,
           "costs_geometric_median": {}}
    for field in COST_FIELDS:
        try:
            out["costs_geometric_median"][field] = geometric_time(rows, arm, budget, field)
        except KeyError:
            out["costs_geometric_median"][field] = None
    return out


def paired(rows: Sequence[dict], control: str, candidate: str, control_budget,
           candidate_budget, repetitions: int) -> dict:
    """Per-program mean paired log(J_control / J_candidate); positive favours candidate."""

    idx = index(rows)
    programs = sorted(families_of(rows))
    per_program: Dict[str, float] = {}
    missing, failed = [], []
    for program in programs:
        logs = []
        for r in range(repetitions):
            a = idx.get((program, control, control_budget, r))
            b = idx.get((program, candidate, candidate_budget, r))
            if a is None or b is None:
                missing.append(f"{program}|r{r}")
                continue
            if a["failed_row"] or b["failed_row"]:
                failed.append(f"{program}|r{r}")
                continue
            logs.append(math.log(a["product"] / b["product"]))
        if len(logs) == repetitions:
            per_program[program] = statistics.mean(logs)
    wins = sum(v > TIE for v in per_program.values())
    losses = sum(v < -TIE for v in per_program.values())
    return {"per_program": per_program, "missing_pairs": missing, "failed_pairs": failed,
            "wins": wins, "ties": len(per_program) - wins - losses, "losses": losses,
            "programs": len(per_program)}


def cost_ratio(rows: Sequence[dict], control: str, candidate: str, control_budget,
               candidate_budget, field: str = "compile_seconds") -> Dict[str, float]:
    """Per-program log(median candidate / median control)."""

    a = per_program_median(rows, control, control_budget, field)
    b = per_program_median(rows, candidate, candidate_budget, field)
    return {p: math.log(b[p] / a[p]) for p in sorted(set(a) & set(b)) if a[p] > 0 and b[p] > 0}


# --------------------------------------------------------------------------
# Stage D: factorial, targets, fixed work, profiles
# --------------------------------------------------------------------------

CATALOG_OF = {label: cell["catalog"] for label, cell in nrc.CELLS.items()}
TRAVERSAL_OF = {label: cell["traversal"] for label, cell in nrc.CELLS.items()}


def factorial(rows: Sequence[dict], budget, repetitions: int = 3) -> dict:
    """Descriptive 2x2 effects on per-program log J (negative = lower J)."""

    families = families_of(rows)
    cells = {}
    for label in nrc.CELLS:
        cells[label], _ = per_program_logj(rows, label, budget, repetitions)
    programs = sorted(set.intersection(*(set(v) for v in cells.values())))
    y = {(CATALOG_OF[l], TRAVERSAL_OF[l]): cells[l] for l in nrc.CELLS}

    def contrast(fn) -> dict:
        per_program = {p: fn(p) for p in programs}
        boot = bootstrap(per_program, families)
        return {"estimate": boot["point_estimate"], "interval_95": boot["interval"],
                "family_breakdown": family_breakdown(per_program, families),
                "programs": len(per_program)}

    return {
        "budget_seconds": budget, "programs": len(programs),
        "cell_family_mean_log_J": {l: family_mean({p: cells[l][p] for p in programs}, families)
                                   for l in nrc.CELLS},
        "catalog_effect_a4_minus_a3": contrast(lambda p: 0.5 * (
            (y["a4", "heap"][p] - y["a3", "heap"][p]) + (y["a4", "dfs"][p] - y["a3", "dfs"][p]))),
        "traversal_effect_heap_minus_dfs": contrast(lambda p: 0.5 * (
            (y["a4", "heap"][p] - y["a4", "dfs"][p]) + (y["a3", "heap"][p] - y["a3", "dfs"][p]))),
        "interaction": contrast(lambda p: (y["a4", "heap"][p] - y["a4", "dfs"][p])
                                - (y["a3", "heap"][p] - y["a3", "dfs"][p])),
        "catalog_effect_under_heap": contrast(lambda p: y["a4", "heap"][p] - y["a3", "heap"][p]),
        "catalog_effect_under_dfs": contrast(lambda p: y["a4", "dfs"][p] - y["a3", "dfs"][p]),
        "traversal_effect_under_a4": contrast(lambda p: y["a4", "heap"][p] - y["a4", "dfs"][p]),
        "traversal_effect_under_a3": contrast(lambda p: y["a3", "heap"][p] - y["a3", "dfs"][p]),
        "sign": "log J differences; negative means the first-named level has LOWER (better) J",
    }


def bootstrap_j(rows: Sequence[dict]) -> Dict[str, int]:
    """Each program's direct-bootstrap J, from successor rows (checked consistent)."""

    out: Dict[str, int] = {}
    for row in rows:
        result = row.get("result") or {}
        value = result.get("bootstrap_product")
        if value is None:
            continue
        previous = out.setdefault(row["program_sha256"], value)
        if previous != value:
            raise ValueError(f"inconsistent bootstrap J for {row['program_sha256']}")
    return out


def target_of(j_bootstrap: int, rate: float) -> int:
    return math.floor((1 - rate) * j_bootstrap)


def targets(rows: Sequence[dict], arms: Sequence[str], budgets=nrc.BUDGETS) -> dict:
    """Attainment of 1% and 5% targets at each budget and capped hitting times.

    Every (program, repetition) row is in the denominator. Hitting times come
    from the successor's improvement trajectories; a run that never reaches the
    target is censored at its budget (reported as such, never dropped). The
    earlier optimizer records no trajectory: it has attainment only.
    """

    base = bootstrap_j(rows)
    out = {"bootstrap_programs": len(base), "rates": list(TARGET_RATES), "arms": {}}
    for arm in arms:
        per_arm = {}
        for rate in TARGET_RATES:
            for budget in budgets:
                selected = [r for r in rows if r["arm"] == arm and r["budget_seconds"] == budget]
                reached, censored, failed, times = 0, 0, 0, []
                for row in selected:
                    if row["failed_row"]:
                        failed += 1
                        times.append(math.inf)
                        continue
                    target = target_of(base[row["program_sha256"]], rate)
                    hit = row["product"] <= target
                    reached += hit
                    trajectory = (row.get("result") or {}).get("trajectory")
                    if trajectory is None:
                        times.append(None)
                        continue
                    first = next((t for t, j in trajectory if j <= target), None)
                    if first is None:
                        censored += 1
                        times.append(math.inf)
                    else:
                        times.append(first)
                known = [t for t in times if t is not None]
                entry = {"rows": len(selected), "failed_rows_counted_unreached": failed,
                         "reached": reached,
                         "attainment": reached / len(selected) if selected else None}
                if known and len(known) == len(selected):
                    ordered = sorted(known)
                    entry["hitting_time_quantiles_capped"] = {
                        str(q): (None if ordered[int(q * (len(ordered) - 1))] == math.inf
                                 else ordered[int(q * (len(ordered) - 1))])
                        for q in (0.1, 0.25, 0.5, 0.75, 0.9)}
                    entry["censored_at_budget"] = censored + failed
                    entry["note"] = "None quantile = beyond the budget (censored)"
                else:
                    entry["hitting_time_quantiles_capped"] = "unavailable: no trajectory recorded"
                per_arm[f"r{rate}@{budget}"] = entry
        out["arms"][arm] = per_arm
    return out


def fixed_work(rows: Sequence[dict]) -> dict:
    families = families_of(rows)
    out = {}
    for label in sorted(nrc.CELLS):
        for limit in (1000, 10000, 50000):
            budget = f"work:{limit}"
            selected = [r for r in rows if r["arm"] == label and r["budget_seconds"] == budget]
            ok = [r for r in selected if not r["failed_row"]]
            logj = {r["program_sha256"]: math.log(r["product"]) for r in ok}
            work = [r["result"]["work"] for r in ok]
            out[f"{label}@{limit}"] = {
                "rows": len(selected), "failed": len(selected) - len(ok),
                "timed_out": sum(r["timed_out"] for r in selected),
                "family_mean_log_J": family_mean(logj, families) if logj else None,
                "charged_nodes_total": sum(w["charged_nodes"] for w in work),
                "charged_nodes_max": max((w["charged_nodes"] for w in work), default=None),
                "propagation_certificates_total": sum(w["propagation_certificates"]
                                                      for w in work),
                "validations_total": sum(w["validations"] for w in work),
                "compile_seconds_geometric": (math.exp(statistics.mean(
                    math.log(r["result"]["compile_seconds"]) for r in ok)) if ok else None),
                "stopped_because": dict(collections.Counter(
                    r["result"]["optimisation"]["stopped_because"] for r in ok)),
            }
    return out


def profiles(rows: Sequence[dict]) -> dict:
    out = {}
    for arm in nrc.DEVELOPMENT_ARMS:
        for budget in nrc.BUDGETS:
            selected = [r for r in rows if r["arm"] == arm and r["budget_seconds"] == budget
                        and not r["failed_row"]]
            if not selected:
                continue
            seconds = collections.Counter()
            total = wall = 0.0
            for row in selected:
                for category, value in row["result"]["category_seconds"].items():
                    seconds[category] += value
                total += row["result"]["profiled_tottime_total"]
                wall += row["result"]["profiled_call_wall_seconds"]
            out[f"{arm}@{budget}"] = {
                "programs": len(selected), "profiled_tottime_total": total,
                "profiled_call_wall_total": wall, "reconciliation_ratio": total / wall,
                "shares": {k: v / total for k, v in sorted(seconds.items())},
                "largest": max(seconds, key=seconds.get)}
    return out


# --------------------------------------------------------------------------
# Stage E selection
# --------------------------------------------------------------------------


def select(rows: Sequence[dict], arms: Sequence[str] = nrc.DEVELOPMENT_ARMS,
           budget: float = nrc.PRIMARY_BUDGET, repetitions: int = 3) -> dict:
    """Minimum equal-family mean log J at 0.1 s; ties within 1e-12 by lower
    geometric median compile time, then lexicographic arm ID."""

    families = families_of(rows)
    table = {}
    for arm in arms:
        logj, incomplete = per_program_logj(rows, arm, budget, repetitions)
        table[arm] = {"family_mean_log_J": family_mean(logj, families) if logj else math.inf,
                      "programs": len(logj), "incomplete": incomplete,
                      "geometric_median_compile_seconds": geometric_time(rows, arm, budget)}
    if any(entry["incomplete"] or entry["programs"] != len(families) for entry in table.values()):
        return {"status": "BLOCKED_INCOMPLETE", "table": table}
    best = min(entry["family_mean_log_J"] for entry in table.values())
    tied = sorted(arm for arm, entry in table.items()
                  if entry["family_mean_log_J"] - best <= TIE)
    chosen = sorted(tied, key=lambda a: (table[a]["geometric_median_compile_seconds"], a))[0]
    return {"status": "SELECTED", "selected_arm": chosen, "tie_group": tied,
            "rule": "min equal-family mean log J at 0.1 s (repetitions averaged within "
                    "program); ties within 1e-12 by lower geometric median compile time, then "
                    "lexicographic arm ID", "table": table}


def engineering_decision(rows: Sequence[dict], parent: str, variant: str,
                         budget: float = nrc.PRIMARY_BUDGET, repetitions: int = 3) -> dict:
    """Freeze the variant iff correct, not worse in dev mean log J, and >= 10% faster."""

    families = families_of(rows)
    parent_logj, pi = per_program_logj(rows, parent, budget, repetitions)
    variant_logj, vi = per_program_logj(rows, variant, budget, repetitions)
    if pi or vi:
        return {"status": "BLOCKED_INCOMPLETE", "parent_incomplete": pi, "variant_incomplete": vi}
    quality = family_mean(variant_logj, families) - family_mean(parent_logj, families)
    time_parent = geometric_time(rows, parent, budget)
    time_variant = geometric_time(rows, variant, budget)
    reduction = 1 - time_variant / time_parent
    return {"parent": parent, "variant": variant,
            "delta_family_mean_log_J_variant_minus_parent": quality,
            "geometric_median_compile_parent": time_parent,
            "geometric_median_compile_variant": time_variant,
            "compile_time_reduction": reduction,
            "quality_not_worse": quality <= TIE,
            "reduction_at_least_10pct": reduction >= 0.10}


# --------------------------------------------------------------------------
# Stage C
# --------------------------------------------------------------------------


def head_to_head(rows: Sequence[dict], earlier: str, a4: str, budget: float = 0.1,
                 repetitions: int = 5) -> dict:
    families = families_of(rows)
    result = paired(rows, earlier, a4, budget, budget, repetitions)
    boot = bootstrap(result["per_program"], families, nrc.PRIMARY_PERCENTILES)
    low, high = boot["interval"]
    verdict = "FAVOURS_A4" if low > 0 else "FAVOURS_EARLIER" if high < 0 else "INCONCLUSIVE"
    costs = cost_ratio(rows, earlier, a4, budget, budget)
    return {"endpoint": "mean paired log(J_earlier / J_A4) at 0.1 s", "programs":
            result["programs"], "estimate": boot["point_estimate"], "interval_95": [low, high],
            "verdict": verdict, "wins_ties_losses_for_A4": [result["wins"], result["ties"],
                                                            result["losses"]],
            "missing_pairs": len(result["missing_pairs"]), "failed_pairs": len(result["failed_pairs"]),
            "family_breakdown": family_breakdown(result["per_program"], families),
            "per_program_losses_for_A4": {p: v for p, v in result["per_program"].items()
                                          if v < -TIE},
            "compile_ratio_A4_over_earlier_geometric": (
                math.exp(family_mean(costs, families)) if costs else None)}


def candidate_endpoints(rows: Sequence[dict], candidate: str, references: Sequence[str],
                        budget: float = 0.1, repetitions: int = 5) -> dict:
    """The four confirmatory endpoints of a distinct new candidate (98.75% intervals).

    J ratio = J_candidate / J_reference: log is the NEGATIVE of the paired
    log(J_ref/J_cand); compile ratio = median candidate / median reference.
    """

    families = families_of(rows)
    out = {}
    routes = {"quality_route": True, "efficiency_route": True}
    for reference in references:
        quality = paired(rows, reference, candidate, budget, budget, repetitions)
        log_ratio = {p: -v for p, v in quality["per_program"].items()}
        qb = bootstrap(log_ratio, families, nrc.CANDIDATE_PERCENTILES)
        costs = cost_ratio(rows, reference, candidate, budget, budget)
        cb = bootstrap(costs, families, nrc.CANDIDATE_PERCENTILES)
        j_upper, c_upper = math.exp(qb["interval"][1]), math.exp(cb["interval"][1])
        out[reference] = {
            "J_ratio": math.exp(qb["point_estimate"]),
            "J_ratio_interval_98_75": [math.exp(x) for x in qb["interval"]],
            "compile_ratio": math.exp(cb["point_estimate"]),
            "compile_ratio_interval_98_75": [math.exp(x) for x in cb["interval"]],
            "programs_quality": quality["programs"], "programs_cost": len(costs),
            "wins_ties_losses": [quality["wins"], quality["ties"], quality["losses"]]}
        q = nrc.TARGETS["quality_route"]
        e = nrc.TARGETS["efficiency_route"]
        routes["quality_route"] &= (j_upper <= q["upper_J_ratio"]
                                    and c_upper <= q["upper_compile_ratio"])
        routes["efficiency_route"] &= (c_upper <= e["upper_compile_ratio"]
                                       and j_upper <= e["upper_J_ratio"])
    out["routes_passed"] = routes
    out["verdict"] = ("QUALITY_ROUTE" if routes["quality_route"] else
                      "EFFICIENCY_ROUTE" if routes["efficiency_route"] else "TARGET_NOT_REACHED")
    return out


def public_score(rows: Sequence[dict], repetitions: int = 5) -> dict:
    """S = sqrt(GM(C_serial/C) * GM(S_serial/S)) per repetition over the eight programs.

    Reconciled with exp(mean(log(J_serial/J)) / 2): since log J = log C + log S,
    the two expressions are algebraically identical; both are computed.
    """

    serial = {}
    for row in rows:
        if row["arm"] == "serial":
            key = row["program_sha256"]
            pair = (row["cycles"], row["scratch"])
            if serial.setdefault(key, pair) != pair:
                raise ValueError("serial differs across repetitions")
    idx = index(rows)
    programs = sorted(serial)
    if len(programs) != 8:
        raise ValueError(f"expected eight public programs, found {len(programs)}")
    arms = sorted({(r["arm"], r["budget_seconds"]) for r in rows if r["arm"] != "serial"},
                  key=lambda x: (x[0], -1 if x[1] is None else x[1]))
    names = {r["program_sha256"]: (r.get("result") or {}).get("program_name") for r in rows}
    out = {}
    for arm, budget in arms:
        scores, reconciled, per_program = [], [], collections.defaultdict(list)
        for rep in range(repetitions):
            chosen = [idx.get((p, arm, budget, rep)) for p in programs]
            if any(c is None or c["failed_row"] for c in chosen):
                scores.append(None)
                reconciled.append(None)
                continue
            speed = math.exp(statistics.mean(math.log(serial[c["program_sha256"]][0] / c["cycles"])
                                             for c in chosen))
            space = math.exp(statistics.mean(math.log(serial[c["program_sha256"]][1] / c["scratch"])
                                             for c in chosen))
            scores.append(math.sqrt(speed * space))
            reconciled.append(math.exp(statistics.mean(math.log(
                serial[c["program_sha256"]][0] * serial[c["program_sha256"]][1] / c["product"])
                for c in chosen) / 2))
            for c in chosen:
                per_program[names.get(c["program_sha256"]) or c["program_sha256"]].append(
                    [c["cycles"], c["scratch"], c["product"]])
        valid = [s for s in scores if s is not None]
        out[f"{arm}@{budget}"] = {
            "arm": arm, "budget_seconds": budget, "scores": scores,
            "reconciled_exp_half_mean_log": reconciled,
            "max_reconciliation_gap": max((abs(a - b) for a, b in zip(scores, reconciled)
                                           if a is not None), default=None),
            "min": min(valid) if valid else None, "max": max(valid) if valid else None,
            "complete": len(valid) == repetitions,
            "per_program_CSJ_by_repetition": dict(sorted(per_program.items()))}
    return {"serial": {names.get(k) or k: list(v) for k, v in serial.items()}, "arms": out}
