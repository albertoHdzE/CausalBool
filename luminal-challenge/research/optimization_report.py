"""Evaluation reports of optimization protocol 1.0 (frozen with the analysis).

Writes COMPARISON.json/.md, PUBLIC_SCORE.json/.md and MODEL_EVALUATION.json/.md
from raw stage rows through ``optimization_analysis``. It chooses nothing: every
configuration was frozen in FROZEN_SELECTION.json before these rows existed.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_report --run DIR --part PART
"""

from __future__ import annotations

import argparse
import json
import math
from pathlib import Path
from typing import Dict, List

from research import optimization_analysis as oa
from research import optimization_common as oc

BUDGETS = (0.01, 0.1, 1.0)


def _complete(run: Path, stage: str) -> dict:
    rows = oa.stage_rows(run, stage)
    status = oa.completeness(rows, oa.expected_keys(run, stage))
    return rows, {k: (v if not isinstance(v, list) else {"count": len(v), "first": v[:10]})
                  for k, v in status.items()}


def comparison(run: Path) -> dict:
    run = Path(run)
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    rows, status = _complete(run, "D_fresh_compiler")
    families = oa.families_of(rows)
    out = {"population": "fresh compiler cohort, seeds 810000-810199, 40 per family; "
                         "new instances of the same generator, not the private grader",
           "completeness": status, "freeze_sha256": oc.file_sha256(run / "FROZEN_SELECTION.json"),
           "selected_nonmodel": frozen["search"], "contrasts": {}, "runtime": {},
           "absolute": {}, "per_family": {}}
    identity = frozen["search"]["config"] is None
    primary = oa.paired_quality(rows, "frozen_phase2", "selected_nonmodel", 0.1, 0.1, 15)
    boot = oa.bootstrap(primary["per_program"], families)
    low, high = oa.interval_of(boot, oa.PRIMARY_PERCENTILES)
    effect = oa.family_weighted(primary["per_program"], families)
    out["primary"] = {
        "endpoint": "mean paired log(J_frozen_phase2 / J_selected_nonmodel) at 0.1 s; "
                    "repetitions within program, equal family weights; positive favours new",
        "effect": effect, "interval_95": [low, high],
        "geometric_J_reduction": 1 - math.exp(-effect),
        "interval_J_reduction": [1 - math.exp(-low), 1 - math.exp(-high)],
        "wins": primary["wins"], "ties": primary["ties"], "losses": primary["losses"],
        "programs": primary["programs"], "missing_pairs": len(primary["missing_pairs"]),
        "failed_pairs": len(primary["failed_pairs"]),
        "verdict": ("IDENTITY_CONTROL" if identity else oa.verdict(low, high)),
        "confirmatory_eligible": (status["complete"] and status["failed"]["count"] == 0 and
                                  primary["programs"] == 200),
        "resamples": boot["resamples"], "seed": boot["seed"]}
    per_family: Dict[str, List[float]] = {}
    for program, value in primary["per_program"].items():
        per_family.setdefault(families[program], []).append(value)
    out["per_family"]["primary"] = {
        f: {"programs": len(v), "mean": sum(v) / len(v),
            "wins": sum(x > oa.TIE for x in v), "losses": sum(x < -oa.TIE for x in v)}
        for f, v in sorted(per_family.items())}
    controls = [("accepted_budgeted", "same"), ("accepted_default", None),
                ("accepted_bootstrap", None), ("classical", None), ("frozen_phase2", "same")]
    for candidate in ("selected_nonmodel", "frozen_phase2"):
        for control, budget_rule in controls:
            if control == candidate:
                continue
            for budget in BUDGETS:
                cb = budget if budget_rule == "same" else None
                paired = oa.paired_quality(rows, control, candidate, cb, budget, 15)
                if not paired["programs"]:
                    continue
                b = oa.bootstrap(paired["per_program"], families)
                lo, hi = oa.interval_of(b, oa.PRIMARY_PERCENTILES)
                key = f"{candidate}@{budget}_vs_{control}@{cb}"
                out["contrasts"][key] = {
                    "effect": oa.family_weighted(paired["per_program"], families),
                    "interval_95_unadjusted": [lo, hi], "wins": paired["wins"],
                    "ties": paired["ties"], "losses": paired["losses"],
                    "programs": paired["programs"], "descriptive": True}
                for field in ("compile_seconds", "process_seconds"):
                    out["runtime"][f"{key}:{field}"] = oa.runtime_ratio(
                        rows, control, candidate, cb, budget, field,
                        with_interval=budget == 0.1)
    for arm in ("accepted_bootstrap", "accepted_default", "classical"):
        out["absolute"][f"{arm}@None"] = oa.absolute_times(rows, arm, None)
    for arm in ("accepted_budgeted", "frozen_phase2", "selected_nonmodel"):
        for budget in BUDGETS:
            out["absolute"][f"{arm}@{budget}"] = oa.absolute_times(rows, arm, budget)
    model_stage = run / "stages" / "D_fresh_model_compiler"
    if model_stage.exists():
        model_rows, model_status = _complete(run, "D_fresh_model_compiler")
        both = rows + model_rows
        paired = oa.paired_quality(both, "selected_nonmodel", "selected_model_compiler",
                                   0.1, 0.1, 15)
        b = oa.bootstrap(paired["per_program"], families)
        lo, hi = oa.interval_of(b, oa.PRIMARY_PERCENTILES)
        out["conditional_model_compiler"] = {
            "completeness": model_status,
            "effect": oa.family_weighted(paired["per_program"], families),
            "interval_95": [lo, hi], "verdict": oa.verdict(lo, hi), "wins": paired["wins"],
            "ties": paired["ties"], "losses": paired["losses"]}
    else:
        out["conditional_model_compiler"] = {"status": "BLOCKED_BY_H4_NEW_OR_NOT_RUN"}
    return out


def comparison_markdown(c: dict) -> str:
    p = c["primary"]
    lines = ["# Fresh compiler comparison (optimization protocol 1.0)", "",
             f"Population: {c['population']}.", "",
             f"Completeness: {c['completeness']['observed_rows']} rows observed, "
             f"{c['completeness']['expected']} expected, missing "
             f"{c['completeness']['missing']['count']}, failed {c['completeness']['failed']['count']}.",
             "", "## Primary (single optimization primary)", "",
             f"- Endpoint: {p['endpoint']}.",
             f"- Effect {p['effect']:.6f}, 95% family-stratified bootstrap interval "
             f"[{p['interval_95'][0]:.6f}, {p['interval_95'][1]:.6f}] "
             f"({p['resamples']} resamples, seed {p['seed']}).",
             f"- Geometric J reduction {100 * p['geometric_J_reduction']:.2f}% "
             f"(interval {100 * p['interval_J_reduction'][0]:.2f}% to "
             f"{100 * p['interval_J_reduction'][1]:.2f}%).",
             f"- Wins/ties/losses over {p['programs']} programs: {p['wins']}/{p['ties']}/{p['losses']}.",
             f"- Verdict: **{p['verdict']}**.", "", "## Per family (primary)", "",
             "| family | programs | mean log ratio | wins | losses |", "|---|---|---|---|---|"]
    for f, v in c["per_family"]["primary"].items():
        lines.append(f"| {f} | {v['programs']} | {v['mean']:.6f} | {v['wins']} | {v['losses']} |")
    lines += ["", "## Descriptive contrasts (unadjusted 95% intervals)", "",
              "| contrast | effect | interval | W/T/L | compile ratio (cand/ctrl) | process ratio |",
              "|---|---|---|---|---|---|"]
    for key, v in c["contrasts"].items():
        comp = c["runtime"].get(f"{key}:compile_seconds", {})
        proc = c["runtime"].get(f"{key}:process_seconds", {})
        lines.append(
            f"| {key} | {v['effect']:.5f} | [{v['interval_95_unadjusted'][0]:.5f}, "
            f"{v['interval_95_unadjusted'][1]:.5f}] | {v['wins']}/{v['ties']}/{v['losses']} | "
            f"{comp.get('geometric_ratio_candidate_over_control', float('nan')):.4g} | "
            f"{proc.get('geometric_ratio_candidate_over_control', float('nan')):.4g} |")
    lines += ["", "## Absolute runtime", "", "| arm | compile median | p95 | max | "
              "process median | overshoot max | peak RSS max |", "|---|---|---|---|---|---|---|"]
    for key, v in c["absolute"].items():
        if not v.get("rows"):
            continue
        lines.append(
            f"| {key} | {v['compile_seconds']['median']:.4g} | {v['compile_seconds']['p95']:.4g} | "
            f"{v['compile_seconds']['max']:.4g} | {v['process_seconds']['median']:.4g} | "
            f"{v.get('overshoot_seconds', {}).get('max', float('nan')):.4g} | "
            f"{v['peak_rss_bytes_max']} |")
    lines += ["", "## Conditional model compiler", "",
              "```", json.dumps(c["conditional_model_compiler"], indent=1)[:2000], "```", ""]
    return "\n".join(lines)


def public(run: Path) -> dict:
    from research import optimization_stage_a as sa

    run = Path(run)
    rows, status = _complete(run, "D_public")
    model_stage = run / "stages" / "D_public_model_compiler"
    if model_stage.exists():
        rows = rows + oa.stage_rows(run, "D_public_model_compiler")
    scores = oa.public_scores(rows, sa.frozen_serial())
    ratios = {}
    for candidate in ("selected_nonmodel@0.1", "frozen_phase2@0.1"):
        for control in ("accepted_default@None", "classical@None", "frozen_phase2@0.1",
                        "accepted_budgeted@0.1"):
            if candidate != control and candidate in scores["arms"] and control in scores["arms"]:
                ratios[f"{candidate}_vs_{control}"] = oa.paired_score_ratios(scores, candidate,
                                                                             control)
    # Reconcile the score ratio with exp(mean log(J_control/J_candidate) / 2).
    reconcile = []
    index = {(r["program_sha256"], r["arm"], r["budget_seconds"], r["repetition"]): r
             for r in rows}
    programs = sorted({r["program_sha256"] for r in rows})
    a, b = scores["arms"]["selected_nonmodel@0.1"], scores["arms"]["accepted_default@None"]
    for rep in range(15):
        logs = [math.log(index[(p, "accepted_default", None, rep)]["product"] /
                         index[(p, "selected_nonmodel", 0.1, rep)]["product"]) for p in programs]
        predicted = math.exp(sum(logs) / len(logs) / 2)
        observed = a["scores"][rep] / b["scores"][rep]
        reconcile.append({"repetition": rep, "score_ratio": observed,
                          "exp_half_mean_log_J": predicted,
                          "agree_1e-12": abs(predicted - observed) <= 1e-12})
    per_program = []
    for name in scores["programs"]:
        entry = {"program": name, "serial": scores["serial"].get(name)}
        for key in ("selected_nonmodel@0.1", "frozen_phase2@0.1", "accepted_default@None",
                    "classical@None"):
            entry[key] = scores["arms"][key]["per_program_distinct_CSJ"].get(name)
        per_program.append(entry)
    sensitivity = leave_one_out(rows, scores, sa.frozen_serial())
    return {"scope": "exact fixed public suite of eight programs; descriptive; not a "
                     "significance test and not a private-grader claim",
            "formula": "S_arm = sqrt(GM_i(C_serial_i/C_arm_i) * GM_i(S_serial_i/S_arm_i))",
            "completeness": status, "scores": scores, "paired_score_ratios": ratios,
            "reconciliation_vs_accepted_default": reconcile,
            "reconciliation_all_agree": all(x["agree_1e-12"] for x in reconcile),
            "per_program": per_program, "leave_one_out": sensitivity}


def leave_one_out(rows, scores, serial) -> dict:
    """Score ratio selected_nonmodel/accepted_default with each program removed."""

    names = scores["programs"]
    out = {}
    first = {}
    for r in rows:
        if r["repetition"] == 0 and r.get("result"):
            first[(r["result"]["program_name"], r["arm"], r["budget_seconds"])] = r

    def s(arm, budget, keep):
        sp = math.exp(sum(math.log(serial[n]["cycles"] / first[(n, arm, budget)]["cycles"])
                          for n in keep) / len(keep))
        sc = math.exp(sum(math.log(serial[n]["scratch"] / first[(n, arm, budget)]["scratch"])
                          for n in keep) / len(keep))
        return math.sqrt(sp * sc)

    for left in names:
        keep = [n for n in names if n != left]
        out[left] = {
            "vs_accepted_default": s("selected_nonmodel", 0.1, keep) / s("accepted_default",
                                                                          None, keep),
            "vs_classical": s("selected_nonmodel", 0.1, keep) / s("classical", None, keep),
            "vs_frozen_phase2": s("selected_nonmodel", 0.1, keep) / s("frozen_phase2", 0.1,
                                                                      keep)}
    return {"repetition": 0, "ratios_without_program": out}


def public_markdown(p: dict) -> str:
    s = p["scores"]
    lines = ["# Exact public-suite score (optimization protocol 1.0)", "",
             f"Scope: {p['scope']}.", "", f"Formula: `{p['formula']}`.", "",
             f"Serial re-measured on 8 programs x 15 repetitions: matches frozen records = "
             f"{s['serial_matches_frozen']} ({s['serial_rows']} rows).", "",
             "| arm | min | max | geometric mean over repetitions | complete |",
             "|---|---|---|---|---|"]
    for key, v in s["arms"].items():
        lines.append(f"| {key} | {v['min']!r} | {v['max']!r} | {v['geometric_mean']!r} | "
                     f"{v['complete']} |")
    lines += ["", "## Paired score ratios", "",
              "| candidate vs control | strict gain every rep | improving/tied/worsening reps | "
              "ratio (rep 0) |", "|---|---|---|---|"]
    for key, v in p["paired_score_ratios"].items():
        lines.append(f"| {key} | {v['strict_improvement_every_repetition']} | "
                     f"{v['improving_repetitions']}/{v['tied_repetitions']}/"
                     f"{v['worsening_repetitions']} | {v['ratios'][0]!r} |")
    lines += ["", f"Score-ratio reconciliation with exp(mean log J ratio / 2), all 15 "
                  f"repetitions agree within 1e-12: {p['reconciliation_all_agree']}.", "",
              "## Per program C/S/J (distinct values over repetitions)", "",
              "| program | serial C,S | selected_nonmodel@0.1 | frozen_phase2@0.1 | "
              "accepted_default | classical |", "|---|---|---|---|---|---|"]
    for e in p["per_program"]:
        lines.append(f"| {e['program']} | {e['serial']} | {e['selected_nonmodel@0.1']} | "
                     f"{e['frozen_phase2@0.1']} | {e['accepted_default@None']} | "
                     f"{e['classical@None']} |")
    lines += ["", "## One-program-at-a-time sensitivity (repetition 0)", "",
              "| program removed | vs accepted_default | vs classical | vs frozen_phase2 |",
              "|---|---|---|---|"]
    for name, v in p["leave_one_out"]["ratios_without_program"].items():
        lines.append(f"| {name} | {v['vs_accepted_default']:.6f} | {v['vs_classical']:.6f} | "
                     f"{v['vs_frozen_phase2']:.6f} |")
    return "\n".join(lines) + "\n"


def model(run: Path) -> dict:
    run = Path(run)
    frozen = json.loads((run / "FROZEN_SELECTION.json").read_text())
    fixtures = json.loads((run / "fixtures" / "evaluation" / "MANIFEST.json").read_text())["fixtures"]
    rows, status = _complete(run, "C_model_evaluation")
    h4 = oa.h4_contrasts(rows, oa.expected_keys(run, "C_model_evaluation"), fixtures)
    out = {"original_H4": {"verdict": "INCONCLUSIVE",
                           "source": "recovery_campaign_20260923_r3 (historical, unchanged)",
                           "reason": "only one fixture/family qualified in the OLD experiment"},
           "H4_NEW": h4["H4_NEW"], "gate": h4["gate"], "budgets": h4["budgets"],
           "completeness": status, "selected_depth": frozen["model"]["selected_depth"],
           "counts": oa.model_counts(rows),
           "endpoint": "best_test_J = min(min_training_J, validated new TEST objects); "
                       "log(best_test_J_control / best_test_J_model); repetitions then uniform "
                       "seeds then fixtures, equal family weights; 97.5% family-stratified "
                       "bootstrap (.0125/.9875), 10000 resamples, seed 2026092403",
           "cost_accounting": "oracle enumeration and test-label bookkeeping are evaluator costs "
                              "(evaluator field of each row); training supplied by the harness "
                              "is not free end-to-end compiler learning"}
    descriptive = run / "stages" / "C_model_evaluation_depth1_descriptive"
    if descriptive.exists():
        extra = oa.stage_rows(run, "C_model_evaluation_depth1_descriptive")
        out["depth1_descriptive_counts"] = oa.model_counts(extra)
    return out


def model_markdown(m: dict) -> str:
    lines = ["# Model evaluation (optimization protocol 1.0)", "",
             "## Original H4 (historical, unchanged)", "",
             f"- {m['original_H4']['verdict']}: {m['original_H4']['reason']}.", "",
             "## H4_NEW (new study, qualified fixtures)", "",
             f"- Selected depth: {m['selected_depth']}.", f"- Endpoint: {m['endpoint']}.",
             f"- Gate: `{json.dumps(m['gate'])}`.", f"- **H4_NEW: {m['H4_NEW']}**.", "",
             "| budget | control | effect | 97.5% interval | 95% interval | W/T/L | fixtures |",
             "|---|---|---|---|---|---|---|"]
    for budget, entry in m["budgets"].items():
        for control, v in entry.items():
            if "effect" not in v:
                lines.append(f"| {budget} | {control} | - | - | - | - | 0 |")
                continue
            lines.append(f"| {budget} | {control} | {v['effect']:.6f} | "
                         f"[{v['interval_97_5'][0]:.6f}, {v['interval_97_5'][1]:.6f}] | "
                         f"[{v['interval_95'][0]:.6f}, {v['interval_95'][1]:.6f}] | "
                         f"{v['wins']}/{v['ties']}/{v['losses']} | {v['fixtures']} |")
    lines += ["", "## Counts per arm and budget", "", "```",
              json.dumps(m["counts"], indent=1)[:12000], "```", ""]
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--part", required=True, choices=["comparison", "public", "model"])
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    if args.part == "comparison":
        payload = comparison(run)
        oc.write_json(run / "COMPARISON.json", payload)
        (run / "COMPARISON.md").write_text(comparison_markdown(payload))
        print(json.dumps(payload["primary"]))
    elif args.part == "public":
        payload = public(run)
        oc.write_json(run / "PUBLIC_SCORE.json", payload)
        (run / "PUBLIC_SCORE.md").write_text(public_markdown(payload))
        print(json.dumps({k: v["strict_improvement_every_repetition"]
                          for k, v in payload["paired_score_ratios"].items()}))
    else:
        payload = model(run)
        oc.write_json(run / "MODEL_EVALUATION.json", payload)
        (run / "MODEL_EVALUATION.md").write_text(model_markdown(payload))
        print(json.dumps({"H4_NEW": payload["H4_NEW"], "gate": payload["gate"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
