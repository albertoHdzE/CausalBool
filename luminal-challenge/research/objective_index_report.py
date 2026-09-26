"""Evaluation reports of the objective-index protocol 1.0 (frozen before evaluation).

Builds, from raw rows through ``objective_index_analysis`` only:

- ``LEARNING.json/.md``: H_LEARN (tree vs hamming, random, shuffled_tree at
  0.1 s, Bonferroni three-comparison intervals), the descriptive contrasts at
  every budget, fixed-work prefix metrics, discovery counts, and the original
  H4, which stays INCONCLUSIVE and is never relabelled;
- ``COMPARISON.json/.md``: the primary three-control quality claim at 0.1 s,
  descriptive ladder/budget/default/bootstrap contrasts, runtime ratios and
  absolute times, per-family results and, if run, the conditional learned pair;
- ``PUBLIC_SCORE.json/.md``: exact public scores per repetition, paired ratios,
  leave-one-program-out sensitivity and the log-J reconciliation.

Usage::

    PYTHONPATH=.reference:. python -m research.objective_index_report --run DIR --part PART
"""

from __future__ import annotations

import argparse
import collections
import json
from pathlib import Path
from typing import List

from research import objective_index_analysis as oia
from research import objective_index_common as oic
from research import optimization_analysis as oa
from research import optimization_common as oc


def _rows(run: Path, stage: str) -> List[dict]:
    return oc.read_rows(run / "stages" / stage / "rows.jsonl")


def _expected(run: Path, stage: str) -> List[str]:
    return json.loads((run / "stages" / stage / "EXPECTED_KEYS.json").read_text())["keys"]


def _fmt(x, digits=4):
    return "n/a" if x is None else f"{x:+.{digits}f}"


# --------------------------------------------------------------------------
# Learning
# --------------------------------------------------------------------------


def learning(run: Path) -> dict:
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    wall = _rows(run, "EVAL_model_wall")
    work = _rows(run, "EVAL_model_work")
    gate = oia.h_learn(wall, _expected(run, "EVAL_model_wall"))
    counts = collections.Counter()
    for row in wall:
        result = row.get("result") or {}
        for key, value in (result.get("discoveries") or {}).items():
            counts[f"{row['arm'].split('_')[0] if row['arm'].startswith('random') else row['arm']}"
                   f":{key}"] += value
    payload = {
        "protocol_id": oic.PROTOCOL_ID,
        "H_LEARN": gate,
        "descriptive_contrasts": oia.learning_descriptive(wall),
        "fixed_work": {"completeness": {k: (len(v) if isinstance(v, list) else v) for k, v in
                                        oa.completeness(work, _expected(run, "EVAL_model_work"))
                                        .items()},
                       "prefix_means": oia.fixed_work_summary(work),
                       "note": "prefixes 8/32/128/whole are nested measurements of one run per "
                               "fixture/arm/seed; they are not independent samples"},
        "discovery_counts_by_arm": dict(sorted(counts.items())),
        "design_diagnostic": frozen["learning"]["design_diagnostic_from_oracle_only"],
        "original_H4": {"verdict": "INCONCLUSIVE",
                        "note": "the accepted recovery_campaign_20260923_r3 H4 is unchanged; "
                                "H_LEARN is a separate, new fixture hypothesis"},
        "end_to_end_learning_hypothesis": ("ELIGIBLE_TO_RUN" if gate["verdict"] == "PASS"
                                           else "BLOCKED_BY_H_LEARN"),
    }
    oc.write_json(run / "LEARNING.json", payload)
    (run / "LEARNING.md").write_text(learning_markdown(payload))
    return payload


def learning_markdown(p: dict) -> str:
    g = p["H_LEARN"]
    lines = ["# Fixture learning study (H_LEARN)", "",
             f"**Verdict: {g['verdict']}.** Complete 30-fixture membership: "
             f"{g['complete_30_fixture_membership']}; defects {g['defects']}; failed rows "
             f"{g['failed_rows']}.", "",
             "Mean log(best_test_J control / best_test_J tree) at 0.1 s; positive favours the "
             "tree. Intervals are Bonferroni two-sided 98.33% (percentiles 1/120, 119/120), "
             "10,000 fixture-within-family resamples, seed 2026092504.", "",
             "| control | fixtures | point | interval | wins/ties/losses |",
             "|---|---|---|---|---|"]
    for name, c in g["contrasts"].items():
        interval = c.get("interval")
        lines.append(f"| {name} | {c.get('programs')} | {_fmt(c.get('point'))} | "
                     f"{'n/a' if interval is None else f'[{interval[0]:+.4f}, {interval[1]:+.4f}]'}"
                     f" | {c.get('wins')}/{c.get('ties')}/{c.get('losses')} |")
    d = p["design_diagnostic"]
    lines += ["", "## Design diagnostic fixed before evaluation (oracle and split only)", "",
              f"Evaluation fixtures with any TEST object strictly below the best training label: "
              f"{d['evaluation_fixtures_with_a_test_object_below_training_minimum']} of {d['of']}. "
              f"{d['consequence']}.", "",
              "## Descriptive (unadjusted 95%)", "",
              "| contrast | point | interval |", "|---|---|---|"]
    for name, c in p["descriptive_contrasts"].items():
        interval = c.get("interval")
        lines.append(f"| tree vs {name} | {_fmt(c.get('point'))} | "
                     f"{'n/a' if interval is None else f'[{interval[0]:+.4f}, {interval[1]:+.4f}]'} |")
    lines += ["", "## Fixed-work prefixes (descriptive; nested, not independent)", "",
              "| arm | prefix | mean complete | mean test complete | mean elite-level test |",
              "|---|---|---|---|---|"]
    for arm, by in p["fixed_work"]["prefix_means"].items():
        for key, v in by.items():
            lines.append(f"| {arm} | {key} | {v['mean_complete']:.2f} | "
                         f"{v['mean_complete_test']:.2f} | {v['mean_elite_level_test']:.2f} |")
    lines += ["", f"Original H4: {p['original_H4']['verdict']} ({p['original_H4']['note']}).",
              f"End-to-end learned compiler: {p['end_to_end_learning_hypothesis']}.", ""]
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Compiler comparison
# --------------------------------------------------------------------------


def comparison(run: Path) -> dict:
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    selected = frozen["selection"]["selected_arm"]
    rows = _rows(run, "EVAL_compiler")
    completeness = oa.completeness(rows, _expected(run, "EVAL_compiler"))
    primary = {}
    for control, budget in (("A0_frozen_phase2", 0.1), ("accepted_budgeted", 0.1),
                            ("classical", None)):
        if control == selected:
            primary[control] = {"identity": True, "point": 0.0, "interval": [0.0, 0.0],
                                "percentiles": list(oia.BONFERRONI3),
                                "note": "selected equals A0: superiority to A0 is impossible; "
                                        "reported as a tie"}
            continue
        primary[control] = oia.quality(rows, control, selected, budget, 0.1, 15,
                                       oia.BONFERRONI3)
    lows = [c["interval"][0] for c in primary.values()]
    claim = all(low > 0 for low in lows) and completeness["complete"]
    runtime = {}
    for control, budget in (("A0_frozen_phase2", 0.1), ("accepted_budgeted", 0.1),
                            ("classical", None)):
        if control == selected:
            continue
        for field in ("compile_seconds", "process_seconds"):
            runtime[f"{control}:{field}"] = oia.runtime(rows, control, selected, budget, 0.1,
                                                        field, oia.BONFERRONI3)
    descriptive = {}
    for budget in oic.BUDGETS:
        for control in ("A0_frozen_phase2", "accepted_budgeted"):
            if not (control == selected):
                descriptive[f"{selected}_vs_{control}@{budget}"] = oia.quality(
                    rows, control, selected, budget, budget, 15, oia.DESCRIPTIVE)
        for control in ("accepted_default", "accepted_bootstrap", "classical"):
            descriptive[f"{selected}@{budget}_vs_{control}"] = oia.quality(
                rows, control, selected, None, budget, 15, oia.DESCRIPTIVE)
        for arm in oic.ARMS:
            if arm != "A0_frozen_phase2":
                descriptive[f"{arm}_vs_A0@{budget}"] = oia.quality(
                    rows, "A0_frozen_phase2", arm, budget, budget, 15, oia.DESCRIPTIVE)
    ladder = oia.ablations(rows, 15)
    absolute = {f"{arm}@{budget}": oa.absolute_times(rows, arm, budget)
                for arm in ("accepted_budgeted",) + oic.ARMS for budget in oic.BUDGETS}
    absolute.update({f"{arm}@None": oa.absolute_times(rows, arm, None)
                     for arm in ("accepted_default", "accepted_bootstrap", "classical")})
    unknown = {}
    for row in rows:
        if row["arm"] in oic.NEW_ARMS and row.get("result"):
            opt = row["result"].get("optimisation") or {}
            bucket = unknown.setdefault(f"{row['arm']}@{row['budget_seconds']}",
                                        collections.Counter())
            for status, n in (opt.get("statuses") or {}).items():
                bucket[status] += n
            bucket[f"stopped:{opt.get('stopped_because')}"] += 1
    payload = {
        "protocol_id": oic.PROTOCOL_ID, "selected_arm": selected,
        "completeness": {k: (len(v) if isinstance(v, list) else v)
                         for k, v in completeness.items()},
        "primary": {"budget": 0.1, "contrasts": primary,
                    "claim_best_average_quality": claim,
                    "claim_text": ("best average output quality among A0, accepted_budgeted and "
                                   "classical at 0.1 s on this fresh population" if claim else
                                   "no three-control superiority claim"),
                    "rule": frozen["inference"]["primary"]},
        "runtime_primary_bonferroni": runtime,
        "descriptive_unadjusted_95": descriptive,
        "ladder_unadjusted_95": ladder,
        "absolute_times": absolute,
        "query_status_totals": {k: dict(v) for k, v in sorted(unknown.items())},
    }
    learned = learned_comparison(run, selected)
    if learned is not None:
        payload["conditional_learned"] = learned
    oc.write_json(run / "COMPARISON.json", payload)
    (run / "COMPARISON.md").write_text(comparison_markdown(payload))
    return payload


def learned_comparison(run: Path, selected: str):
    stage_tree = run / "stages" / "EVAL_learned_tree"
    if not stage_tree.exists():
        return None
    rows = (_rows(run, "EVAL_compiler") + _rows(run, "EVAL_learned_tree")
            + _rows(run, "EVAL_learned_shuffled_tree"))
    fresh = {e["program_sha256"] for e in
             json.loads((run / "FRESH_COHORT.json").read_text())["programs"]}
    rows = [r for r in rows if r["program_sha256"] in fresh]
    return {"tree_vs_selected": oia.quality(rows, selected, "learned_tree", 0.1, 0.1, 15,
                                            oia.CONDITIONAL2),
            "tree_vs_shuffled": oia.quality(rows, "learned_shuffled_tree", "learned_tree", 0.1,
                                            0.1, 15, oia.CONDITIONAL2)}


def comparison_markdown(p: dict) -> str:
    lines = ["# Fresh compiler comparison", "",
             f"Selected (frozen on development): **{p['selected_arm']}**. Fresh cohort seeds "
             "910000-910199 (200 programs, 40 per family), 15 repetitions.", "",
             f"Completeness: {p['completeness']}.", "",
             "## Primary: output quality at 0.1 s (Bonferroni 98.33%)", "",
             "Mean paired log(J_control / J_selected); positive favours the selected solver.", "",
             "| control | programs | point | interval | wins/ties/losses |", "|---|---|---|---|---|"]
    for name, c in p["primary"]["contrasts"].items():
        interval = c.get("interval")
        lines.append(f"| {name} | {c.get('programs', 'identity')} | {_fmt(c.get('point'))} | "
                     f"[{interval[0]:+.4f}, {interval[1]:+.4f}] | "
                     f"{c.get('wins')}/{c.get('ties')}/{c.get('losses')} |")
    lines += ["", f"Claim: **{p['primary']['claim_text']}**.", "",
              "## Compile and process time (selected / control; Bonferroni 98.33%)", "",
              "| comparison | geometric ratio | interval |", "|---|---|---|"]
    for name, r in p["runtime_primary_bonferroni"].items():
        if r.get("programs"):
            lines.append(f"| {name} | {r['geometric_ratio_candidate_over_control']:.3f} | "
                         f"[{r['interval_ratio'][0]:.3f}, {r['interval_ratio'][1]:.3f}] |")
    lines += ["", "## Ladder steps (unadjusted 95%, descriptive)", "",
              "| budget | step | quality point | interval | compile ratio |", "|---|---|---|---|---|"]
    for step in p["ladder_unadjusted_95"]:
        q, c = step["quality"], step["compile"]
        interval = q.get("interval") or [float("nan")] * 2
        ratio = c.get("geometric_ratio_candidate_over_control")
        lines.append(f"| {step['budget']} | {step['step']} | {_fmt(q.get('point'))} | "
                     f"[{interval[0]:+.4f}, {interval[1]:+.4f}] | "
                     f"{'n/a' if ratio is None else f'{ratio:.3f}'} |")
    if "conditional_learned" in p:
        lines += ["", "## Conditional learned compiler (97.5%)", ""]
        for name, c in p["conditional_learned"].items():
            lines.append(f"- {name}: {_fmt(c.get('point'))} {c.get('interval')}")
    lines.append("")
    return "\n".join(lines)


# --------------------------------------------------------------------------
# Public score
# --------------------------------------------------------------------------


def public(run: Path) -> dict:
    from research import optimization_stage_a as osa

    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    selected = frozen["selection"]["selected_arm"]
    rows = _rows(run, "EVAL_public") + _rows(run, "EVAL_public_serial")
    controls = ["A0_frozen_phase2@0.1", "accepted_budgeted@0.1", "accepted_default@None",
                "classical@None"]
    controls = [c for c in controls if c != f"{selected}@0.1"]
    score = oia.public_score(rows, osa.frozen_serial(), f"{selected}@0.1", controls)
    payload = {"protocol_id": oic.PROTOCOL_ID, "selected_arm": selected,
               "formula": "sqrt(GM(C_serial/C_arm) * GM(S_serial/S_arm)), eight public "
                          "programs, one score per repetition",
               "score": score,
               "scope": "exact fixed public suite; not a population estimate and not the "
                        "private grader"}
    oc.write_json(run / "PUBLIC_SCORE.json", payload)
    lines = ["# Public score (exact fixed suite)", "", payload["formula"] + ".", "",
             "| arm | min | max | geometric mean over 15 repetitions |", "|---|---|---|---|"]
    for key, arm in sorted(score["scores"]["arms"].items()):
        if arm["min"] is not None:
            lines.append(f"| {key} | {arm['min']:.10f} | {arm['max']:.10f} | "
                         f"{arm['geometric_mean']:.10f} |")
    lines += ["", f"Selected: {selected}@0.1.", "", "| versus | improving | tied | worsening | "
              "strict every repetition |", "|---|---|---|---|---|"]
    for control, r in score["ratios"].items():
        lines.append(f"| {control} | {r['improving_repetitions']} | {r['tied_repetitions']} | "
                     f"{r['worsening_repetitions']} | {r['strict_improvement_every_repetition']} |")
    lines.append("")
    (run / "PUBLIC_SCORE.md").write_text("\n".join(lines))
    return payload


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--part", required=True, choices=["learning", "comparison", "public"])
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    payload = {"learning": learning, "comparison": comparison, "public": public}[args.part](run)
    brief = {"learning": lambda p: p["H_LEARN"]["verdict"],
             "comparison": lambda p: p["primary"]["claim_text"],
             "public": lambda p: {k: v["strict_improvement_every_repetition"]
                                  for k, v in p["score"]["ratios"].items()}}[args.part](payload)
    print(json.dumps(brief))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
