"""Reports of the Phase 2 next round (protocol 1.0) from raw stage rows.

Parts (each writes JSON with every number and a short Markdown reading):

- ``development``: FACTORIAL.json/.md (2x2 effects per budget, arm summaries,
  costs, attainment of 1%/5% targets, fixed-work diagnostics) and
  BOTTLENECKS.md (profile shares with reconciliation);
- ``comparison``: COMPARISON.json/.md (primary head-to-head, candidate
  endpoints and practical routes, descriptive budgets and controls, costs,
  repaired interruption counts, per-program losses);
- ``public``: PUBLIC_SCORE.json/.md (exact score per repetition, every
  per-program C/S/J);
- ``learning``: LEARNING_FEASIBILITY.json/.md (design gates, orderings,
  contrasts, secondary endpoint, economics).

Estimators are ``next_round_analysis``'s; this module only formats. A missing
stage is reported as missing, never as a zero.

Usage::

    PYTHONPATH=.reference:. python -m research.next_round_report --run DIR --part PART
"""

from __future__ import annotations

import argparse
import collections
import json
import statistics
from pathlib import Path
from typing import List

from research import next_round_analysis as a
from research import next_round_common as nrc
from research import optimization_common as oc


def _rows(run: Path, stage: str) -> List[dict]:
    path = Path(run) / "stages" / stage / "rows.jsonl"
    if not path.exists():
        raise FileNotFoundError(f"stage {stage} has no rows")
    return oc.read_rows(path)


def _expected(run: Path, stage: str) -> List[str]:
    return json.loads((Path(run) / "stages" / stage / "EXPECTED_KEYS.json").read_text())["keys"]


def _fmt(value, digits=4):
    if value is None:
        return "n/a"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


# --------------------------------------------------------------------------
# Development
# --------------------------------------------------------------------------


def development(run: Path) -> dict:
    rows = _rows(run, "D_factorial")
    comp = a.completeness(rows, _expected(run, "D_factorial"))
    families = a.families_of(rows)
    out = {"protocol_id": nrc.PROTOCOL_ID, "completeness": comp, "budgets": {}}
    for budget in nrc.BUDGETS:
        entry = {"factorial": a.factorial(rows, budget),
                 "arms": {arm: a.arm_summary(rows, arm, budget, 3)
                          for arm in nrc.DEVELOPMENT_ARMS}}
        paired = {}
        for arm in nrc.DEVELOPMENT_ARMS:
            if arm == nrc.REPAIRED_A4:
                continue
            result = a.paired(rows, arm, nrc.REPAIRED_A4, budget, budget, 3)
            boot = a.bootstrap(result["per_program"], families)
            paired[f"log(J_{arm}/J_{nrc.REPAIRED_A4})"] = {
                "estimate": boot["point_estimate"], "interval_95": boot["interval"],
                "wins_ties_losses_for_repaired_A4": [result["wins"], result["ties"],
                                                     result["losses"]]}
        entry["versus_repaired_A4_descriptive"] = paired
        out["budgets"][str(budget)] = entry
    out["targets"] = a.targets(rows, nrc.DEVELOPMENT_ARMS)
    fixed = _rows(run, "D_fixed_work")
    out["fixed_work"] = {"completeness": a.completeness(fixed, _expected(run, "D_fixed_work")),
                         "cells": a.fixed_work(fixed),
                         "note": ("equal charged-node limits; equal node count is not equal CPU "
                                  "work -- propagation certificates and validations are counted "
                                  "separately")}
    out["interruption_accounting"] = {
        arm: {"rows": sum(1 for r in rows if r["arm"] == arm),
              "interrupted_validation_total": sum(
                  (r.get("result") or {}).get("optimisation", {}).get(
                      "interrupted_validation_total", 0) for r in rows if r["arm"] == arm),
              "affected_queries": sum(
                  (r.get("result") or {}).get("optimisation", {}).get(
                      "interrupted_validation_queries", 0) for r in rows if r["arm"] == arm),
              "construction_interruptions": sum(
                  (r.get("result") or {}).get("optimisation", {}).get(
                      "construction_interruption_count", 0) for r in rows if r["arm"] == arm)}
        for arm in nrc.CELLS}
    oc.write_json(Path(run) / "FACTORIAL.json", out)
    Path(run, "FACTORIAL.md").write_text(_factorial_md(out))
    profiles = a.profiles(_rows(run, "D_profile"))
    Path(run, "BOTTLENECKS.md").write_text(_bottlenecks_md(profiles, out))
    oc.write_json(Path(run) / "BOTTLENECKS.json", profiles)
    return out


def _factorial_md(out: dict) -> str:
    lines = ["# Stage D: 2x2 catalog x traversal factorial (development, descriptive)", "",
             f"Rows {out['completeness']['observed']}/{out['completeness']['expected']}, "
             f"failed {out['completeness']['failed']}, timed out "
             f"{out['completeness']['timed_out']}. 100 development programs (seeds "
             "800000-800099, 20 per family) x 3 repetitions. log J differences, family-weighted; "
             "negative = the first-named level has LOWER J. Intervals: 95% program-within-family "
             "bootstrap, descriptive only (development data).", ""]
    for budget, entry in out["budgets"].items():
        f = entry["factorial"]
        lines += [f"## Budget {budget} s", "",
                  "| Contrast | Estimate | 95% interval |", "|---|---:|---|"]
        for key in ("catalog_effect_a4_minus_a3", "traversal_effect_heap_minus_dfs",
                    "interaction", "catalog_effect_under_heap", "catalog_effect_under_dfs",
                    "traversal_effect_under_a4", "traversal_effect_under_a3"):
            c = f[key]
            lines.append(f"| {key} | {c['estimate']:+.5f} | [{c['interval_95'][0]:+.5f}, "
                         f"{c['interval_95'][1]:+.5f}] |")
        lines += ["", "| Arm | mean log J | geo. compile s | geo. optimisation s | "
                  "geo. bootstrap s | geo. process s |", "|---|---:|---:|---:|---:|---:|"]
        for arm, s in entry["arms"].items():
            c = s["costs_geometric_median"]
            lines.append(f"| {arm} | {_fmt(s['family_mean_log_J'], 5)} | "
                         f"{_fmt(c['compile_seconds'])} | {_fmt(c['optimisation_seconds'])} | "
                         f"{_fmt(c['bootstrap_seconds'])} | {_fmt(c['process_seconds'])} |")
        lines.append("")
    lines += ["## Targets (J <= floor((1-r) J_bootstrap)); every row in the denominator", "",
              "| Arm | r | budget | attainment | median capped hitting time (s) |",
              "|---|---:|---:|---:|---:|"]
    for arm, entries in out["targets"]["arms"].items():
        for key, e in entries.items():
            rate, budget = key[1:].split("@")
            q = e["hitting_time_quantiles_capped"]
            median = q.get("0.5") if isinstance(q, dict) else "no trajectory"
            lines.append(f"| {arm} | {rate} | {budget} | {e['attainment']:.3f} | "
                         f"{_fmt(median) if median is not None else 'censored'} |")
    lines += ["", "Hitting times are descriptive diagnostics, not proof of speed equivalence. "
              "The earlier optimizer records no incumbent trajectory: attainment only.", "",
              "## Fixed-work diagnostic (10 profiling programs, no wall allowance)", "",
              "| Cell @ node limit | mean log J | charged nodes | certificates | validations "
              "| geo. compile s | stopped because |", "|---|---:|---:|---:|---:|---:|---|"]
    for key, e in out["fixed_work"]["cells"].items():
        lines.append(f"| {key} | {_fmt(e['family_mean_log_J'], 5)} | {e['charged_nodes_total']} "
                     f"| {e['propagation_certificates_total']} | {e['validations_total']} | "
                     f"{_fmt(e['compile_seconds_geometric'])} | {e['stopped_because']} |")
    lines += ["", out["fixed_work"]["note"], ""]
    return "\n".join(lines) + "\n"


def _bottlenecks_md(profiles: dict, factorial: dict) -> str:
    lines = ["# Stage D bottlenecks (separate cProfile runs; never timing rows)", "",
             "Ten profiling programs (first two seeds of each family), one run per arm and "
             "budget. Every function's exclusive time is attributed to one category; built-ins "
             "and shared helpers are split over their callers. `reconciliation` = profiled "
             "exclusive time / wall time of the profiled call. Profiling inflates call-heavy "
             "code, so shares, not seconds, are compared.", "",
             "| Arm @ budget | reconciliation | domain | propagation | frontier | encoding | "
             "validation | orchestration | largest |", "|---|---:|---:|---:|---:|---:|---:|---:|---|"]
    for key, p in profiles.items():
        s = p["shares"]
        lines.append(f"| {key} | {p['reconciliation_ratio']:.3f} | "
                     f"{s.get('domain_construction', 0):.3f} | {s.get('propagation', 0):.3f} | "
                     f"{s.get('frontier', 0):.3f} | {s.get('encoding_digest', 0):.3f} | "
                     f"{s.get('validation', 0):.3f} | {s.get('orchestration', 0):.3f} | "
                     f"{p['largest']} |")
    lines.append("")
    return "\n".join(lines) + "\n"


# --------------------------------------------------------------------------
# Comparison and public score
# --------------------------------------------------------------------------


def comparison(run: Path) -> dict:
    frozen = json.loads((Path(run) / "FROZEN_SELECTION.json").read_text())
    rows = _rows(run, "C_confirmation")
    expected = json.loads((Path(run) / "frozen_expected" / "C_confirmation.json").read_text())
    comp = a.completeness(rows, expected["keys"])
    candidate = frozen["candidate"]["frozen_candidate"]
    distinct = frozen["candidate"]["candidate_is_distinct_new"]
    families = a.families_of(rows)
    out = {"protocol_id": nrc.PROTOCOL_ID, "completeness": comp, "candidate": candidate,
           "primary": a.head_to_head(rows, nrc.EARLIER, nrc.REPAIRED_A4)}
    if distinct:
        out["candidate_endpoints"] = a.candidate_endpoints(rows, candidate,
                                                           [nrc.EARLIER, nrc.REPAIRED_A4])
    else:
        out["candidate_endpoints"] = {"verdict": "NOT_APPLICABLE",
                                      "reason": "the frozen candidate is a reference alias"}
    descriptive = {}
    arms = frozen["confirmation"]["budgeted_arms"]
    for budget in nrc.BUDGETS:
        for i, first in enumerate(arms):
            for second in arms[i + 1:]:
                result = a.paired(rows, first, second, budget, budget, 5)
                boot = a.bootstrap(result["per_program"], families)
                descriptive[f"log(J_{first}/J_{second})@{budget}"] = {
                    "estimate": boot["point_estimate"], "interval_95": boot["interval"],
                    "wins_ties_losses_for_second": [result["wins"], result["ties"],
                                                    result["losses"]]}
        for control in ("classical", "accepted_bootstrap"):
            for arm in arms:
                result = a.paired(rows, control, arm, None, budget, 5)
                boot = a.bootstrap(result["per_program"], families)
                descriptive[f"log(J_{control}/J_{arm}@{budget})"] = {
                    "estimate": boot["point_estimate"], "interval_95": boot["interval"],
                    "wins_ties_losses_for_arm": [result["wins"], result["ties"],
                                                 result["losses"]]}
    out["descriptive_unadjusted_95"] = descriptive
    out["costs"] = {f"{arm}@{budget}": a.arm_summary(rows, arm, budget, 5)["costs_geometric_median"]
                    for arm in arms for budget in nrc.BUDGETS}
    out["costs"].update({f"{c}@None": a.arm_summary(rows, c, None, 5)["costs_geometric_median"]
                         for c in ("classical", "accepted_bootstrap")})
    out["quality"] = {f"{arm}@{budget}": a.arm_summary(rows, arm, budget, 5)["family_mean_log_J"]
                      for arm in arms for budget in nrc.BUDGETS}
    out["targets"] = a.targets(rows, arms)
    out["interruption_accounting"] = {
        arm: {"interrupted_validation_total": sum(
            (r.get("result") or {}).get("optimisation", {}).get(
                "interrupted_validation_total", 0) for r in rows if r["arm"] == arm),
            "affected_queries": sum((r.get("result") or {}).get("optimisation", {}).get(
                "interrupted_validation_queries", 0) for r in rows if r["arm"] == arm),
            "construction_interruptions": sum(
                (r.get("result") or {}).get("optimisation", {}).get(
                    "construction_interruption_count", 0) for r in rows if r["arm"] == arm),
            "rows_with_successor_accounting": sum(
                1 for r in rows if r["arm"] == arm and "interrupted_validation_total" in
                ((r.get("result") or {}).get("optimisation") or {}))}
        for arm in arms}
    bootstrap_check = collections.Counter()
    for r in rows:
        result = r.get("result") or {}
        if "bootstrap_product" in result:
            bootstrap_check[(r["program_sha256"], result["bootstrap_product"])] += 1
    boots = {r["program_sha256"]: r["product"] for r in rows
             if r["arm"] == "accepted_bootstrap" and not r["failed_row"]}
    out["bootstrap_consistency"] = {
        "programs": len(boots),
        "successor_bootstrap_equals_accepted_bootstrap": all(
            boots.get(p) == j for (p, j) in bootstrap_check),
        "note": "each successor row records its own direct-bootstrap J"}
    oc.write_json(Path(run) / "COMPARISON.json", out)
    Path(run, "COMPARISON.md").write_text(_comparison_md(out))
    return out


def _comparison_md(out: dict) -> str:
    p = out["primary"]
    lines = ["# Stage C: head-to-head confirmation (200 fresh programs, 5 repetitions)", "",
             f"Rows {out['completeness']['observed']}/{out['completeness']['expected']}, failed "
             f"{out['completeness']['failed']}, timed out {out['completeness']['timed_out']}.", "",
             "## Primary (prespecified, one comparison)", "",
             f"Mean paired log(J_earlier / J_A4) at 0.1 s = **{p['estimate']:+.5f}**, 95% "
             f"[{p['interval_95'][0]:+.5f}, {p['interval_95'][1]:+.5f}] over {p['programs']} "
             f"programs: **{p['verdict']}**. A4 wins/ties/losses "
             f"{p['wins_ties_losses_for_A4']}; geometric compile ratio A4/earlier "
             f"{_fmt(p['compile_ratio_A4_over_earlier_geometric'], 3)}.", ""]
    ce = out["candidate_endpoints"]
    lines += ["## Frozen candidate endpoints (98.75% intervals, Bonferroni over four)", ""]
    if ce.get("verdict") == "NOT_APPLICABLE":
        lines.append(ce["reason"])
    else:
        lines += ["| Reference | J ratio | 98.75% | compile ratio | 98.75% | W/T/L |",
                  "|---|---:|---|---:|---|---|"]
        for ref in (nrc.EARLIER, nrc.REPAIRED_A4):
            e = ce[ref]
            lines.append(f"| {ref} | {e['J_ratio']:.5f} | [{e['J_ratio_interval_98_75'][0]:.5f}, "
                         f"{e['J_ratio_interval_98_75'][1]:.5f}] | {e['compile_ratio']:.4f} | "
                         f"[{e['compile_ratio_interval_98_75'][0]:.4f}, "
                         f"{e['compile_ratio_interval_98_75'][1]:.4f}] | {e['wins_ties_losses']} |")
        lines += ["", f"Routes: {ce['routes_passed']} -> **{ce['verdict']}**."]
    lines += ["", "## Descriptive (unadjusted 95%)", "", "| Contrast | Estimate | 95% |",
              "|---|---:|---|"]
    for key, e in out["descriptive_unadjusted_95"].items():
        lines.append(f"| {key} | {e['estimate']:+.5f} | [{e['interval_95'][0]:+.5f}, "
                     f"{e['interval_95'][1]:+.5f}] |")
    lines += ["", "## Costs (geometric median over programs of per-program medians, s)", "",
              "| Arm @ budget | compile | optimisation | bootstrap | validate | process |",
              "|---|---:|---:|---:|---:|---:|"]
    for key, c in out["costs"].items():
        lines.append(f"| {key} | {_fmt(c.get('compile_seconds'))} | "
                     f"{_fmt(c.get('optimisation_seconds'))} | {_fmt(c.get('bootstrap_seconds'))} "
                     f"| {_fmt(c.get('validate_seconds'))} | {_fmt(c.get('process_seconds'))} |")
    lines += ["", "## Repaired interruption accounting", ""]
    for arm, e in out["interruption_accounting"].items():
        lines.append(f"- {arm}: {e}")
    lines += ["", "The earlier optimizer's source is frozen and reports its own counters only.",
              ""]
    return "\n".join(lines) + "\n"


def public(run: Path) -> dict:
    frozen = json.loads((Path(run) / "FROZEN_SELECTION.json").read_text())
    rows = _rows(run, "C_public")
    expected = json.loads((Path(run) / "frozen_expected" / "C_public.json").read_text())
    out = {"protocol_id": nrc.PROTOCOL_ID, "completeness": a.completeness(rows, expected["keys"]),
           "scores": a.public_score(rows, 5)}
    arms = frozen["confirmation"]["budgeted_arms"]
    ratios = {}
    for arm in arms:
        for other in arms:
            if arm == other:
                continue
            x = out["scores"]["arms"][f"{arm}@0.1"]["scores"]
            y = out["scores"]["arms"][f"{other}@0.1"]["scores"]
            ratios[f"{arm}/{other}@0.1"] = [None if u is None or v is None else u / v
                                            for u, v in zip(x, y)]
    out["paired_score_ratios_at_0.1"] = ratios
    oc.write_json(Path(run) / "PUBLIC_SCORE.json", out)
    lines = ["# Public score (fixed eight-program suite, 5 repetitions)", "",
             "S = sqrt(GM(C_serial/C) * GM(S_serial/S)); reconciled with "
             "exp(mean(log(J_serial/J))/2) (max gap listed). Descriptive; development-visible "
             "programs; no private-grader claim.", "",
             "| Arm @ budget | scores by repetition | max reconciliation gap |", "|---|---|---:|"]
    for key, e in out["scores"]["arms"].items():
        lines.append(f"| {key} | {', '.join(_fmt(s, 6) for s in e['scores'])} | "
                     f"{_fmt(e['max_reconciliation_gap'], 12)} |")
    lines += ["", "## Per-program C/S/J at 0.1 s (by repetition)", ""]
    for arm in arms:
        lines.append(f"### {arm}")
        for name, values in out["scores"]["arms"][f"{arm}@0.1"][
                "per_program_CSJ_by_repetition"].items():
            lines.append(f"- {name}: {values}")
        lines.append("")
    Path(run, "PUBLIC_SCORE.md").write_text("\n".join(lines) + "\n")
    return out


# --------------------------------------------------------------------------
# Learning
# --------------------------------------------------------------------------


def learning(run: Path) -> dict:
    from research import next_round_learning as nrl
    from research import next_round_ranker as nrr

    run = Path(run)
    ldir = run / "learning"
    out: dict = {"protocol_id": nrc.PROTOCOL_ID}
    dev_path = ldir / "DESIGN_DEVELOPMENT.json"
    out["development_design"] = (json.loads(dev_path.read_text())["gate"] if dev_path.exists()
                                 else "NOT_RUN")
    eval_path = ldir / "DESIGN_EVALUATION.json"
    if eval_path.exists():
        evaluation = json.loads(eval_path.read_text())
        out["evaluation_design"] = evaluation["gate"]
        out["evaluation_sensitivity"] = {d["fixture_id"]: d["sensitivity"]
                                         for d in evaluation["designs"]}
    else:
        out["evaluation_design"] = "NOT_RUN"
    qualification = ldir / "fixtures" / "evaluation" / "MANIFEST.json"
    if qualification.exists():
        manifest = json.loads(qualification.read_text())
        out["evaluation_qualification"] = {k: manifest[k] for k in (
            "status", "filled", "collisions", "pool", "quota_per_family")}
    order_path = run / "stages" / "L_orderings" / "rows.jsonl"
    if order_path.exists():
        rows = oc.read_rows(order_path)
        comp = a.completeness(rows, _expected(run, "L_orderings"))
        designs = {d["fixture_id"]: d for d in evaluation["designs"]}
        scores, secondary, families = {}, collections.defaultdict(dict), {}
        leaks = []
        for row in rows:
            result = row["result"]
            fixture = result["fixture_id"]
            if result.get("loaded_modules_with_oracle_access"):
                leaks.append(row["key"])
            evaluator = json.loads((ldir / "design" / "evaluation" / fixture
                                    / "EVALUATOR.json").read_text())
            s = nrl.score(result["ordered"], evaluator)
            scores.setdefault(fixture, {})[result["ordering"]] = s["yield"]
            secondary[fixture][result["ordering"]] = s["best_J_over_training_minimum"]
            secondary[fixture]["saturated"] = s["saturated"]
            families[fixture] = designs[fixture]["family"]
        complete = {f: s for f, s in scores.items() if len(s) == len(nrr.ORDERINGS)}
        out["orderings"] = {"completeness": comp, "fixtures_scored": len(complete),
                            "oracle_leaks_in_ranker_processes": leaks,
                            "mean_yield_by_ordering": {
                                o: statistics.mean(s[o] for s in complete.values())
                                for o in nrr.ORDERINGS},
                            "per_fixture_yield": complete,
                            "secondary_best_J_over_training_minimum": dict(secondary),
                            "saturated_fixtures": sum(1 for v in secondary.values()
                                                      if v.get("saturated"))}
        out["contrasts"] = nrl.contrasts(complete, families)
        constant = [r["result"]["fixture_id"] for r in rows
                    if r["result"]["ordering"] == "tree" and r["result"]["info"].get(
                        "constant_tree")]
        out["orderings"]["constant_trees"] = constant
    else:
        out["orderings"] = "NOT_RUN"
        out["contrasts"] = "NOT_RUN"
    acq_path = run / "stages" / "L_acquisition" / "rows.jsonl"
    if acq_path.exists():
        rows = oc.read_rows(acq_path)
        ok = [r for r in rows if not r["failed_row"]]
        with_query = [r for r in ok if r["result"]["queries_reaching_20_validated"] > 0]
        costs = collections.Counter()
        for r in ok:
            for k, v in r["result"]["cost_totals_seconds"].items():
                costs[k] += v
        boundary = [q for r in ok for q in r["result"]["queries"] if q["reached_boundary"]]
        fraction = len(with_query) / len(rows) if rows else None
        out["economics"] = {
            "completeness": a.completeness(rows, _expected(run, "L_acquisition")),
            "programs": len(rows), "programs_with_a_query_reaching_20_validated":
                len(with_query), "fraction": fraction,
            "threshold": nrc.LEARNING["minimum_acquisition_program_fraction"],
            "verdict": ("ECONOMICALLY_UNAVAILABLE" if fraction is None or fraction <
                        nrc.LEARNING["minimum_acquisition_program_fraction"] else "AVAILABLE"),
            "queries_with_learner": sum(r["result"]["queries_with_learner"] for r in ok),
            "queries_reaching_boundary": len(boundary),
            "queries_observing_20_at_boundary": sum(
                r["result"]["queries_observing_20_at_boundary"] for r in ok),
            "boundary_observed_distinct_quantiles": _quantiles(
                [q["observed_distinct_at_boundary"] or 0 for q in boundary]),
            "boundary_query_remaining_seconds_quantiles": _quantiles(
                [q["query_remaining_seconds"] for q in boundary]),
            "boundary_global_remaining_seconds_quantiles": _quantiles(
                [q["global_remaining_seconds"] for q in boundary]),
            "cost_totals_seconds": dict(costs),
            "model_improvements": sum(r["result"]["model_improvements"] for r in ok),
            "note": "diagnostic runs, not efficacy evidence; no oracle training injected"}
    else:
        out["economics"] = "NOT_RUN"
    oc.write_json(run / "LEARNING_FEASIBILITY.json", out)
    Path(run, "LEARNING_FEASIBILITY.md").write_text(_learning_md(out))
    return out


def _quantiles(values):
    values = sorted(v for v in values if v is not None)
    if not values:
        return None
    return {str(q): values[int(q * (len(values) - 1))] for q in (0.0, 0.25, 0.5, 0.75, 1.0)}


def _learning_md(out: dict) -> str:
    lines = ["# Stage L: learning mechanism and economics pilot", ""]
    lines.append(f"- Development design gate: `{json.dumps(out['development_design'])[:600]}`")
    lines.append(f"- Evaluation design gate: `{json.dumps(out['evaluation_design'])[:600]}`")
    if isinstance(out.get("contrasts"), dict):
        lines += ["", "| Contrast (tree minus control) | yield diff | 98.33% | +/0/- | passes |",
                  "|---|---:|---|---|---|"]
        for key in ("tree_minus_hamming", "tree_minus_random_mean", "tree_minus_shuffled_tree"):
            c = out["contrasts"][key]
            lines.append(f"| {key} | {c['estimate']:+.4f} | [{c['interval_98_333'][0]:+.4f}, "
                         f"{c['interval_98_333'][1]:+.4f}] | {c['positive']}/{c['zero']}/"
                         f"{c['negative']} | {c['passes']} |")
        lines.append(f"\nMechanism signal: **{out['contrasts']['mechanism_signal']}**.")
        lines.append(f"\nMean yield by ordering: "
                     f"{ {k: round(v, 4) for k, v in out['orderings']['mean_yield_by_ordering'].items()} }")
    if isinstance(out.get("economics"), dict):
        e = out["economics"]
        lines += ["", f"Economics: {e['programs_with_a_query_reaching_20_validated']}/"
                  f"{e['programs']} development programs had a query reaching 20 distinct "
                  f"case-validated observations (threshold {e['threshold']:.0%}): "
                  f"**{e['verdict']}**."]
    return "\n".join(lines) + "\n"


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--part", required=True,
                        choices=["development", "comparison", "public", "learning"])
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    result = {"development": development, "comparison": comparison, "public": public,
              "learning": learning}[args.part](run)
    print(json.dumps({"part": args.part, "keys": sorted(result)[:20]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
