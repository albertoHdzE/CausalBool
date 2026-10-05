"""Decision record and the key numbers quoted in REPORT.md / DECISION.md / HANDOFF.md.

Every value is read from the saved flags, tables and summaries; nothing is recomputed
from archives here. The recommendation rule is post-hoc reasoning over the fixed
cells, stated in ``RULE`` so the reader can check it against the printed counts.

``build`` is the one reporting pipeline: job records -> rows -> summaries -> flags ->
decision. The evidence gate is applied before the rule: INVALID when any evidence is
invalid, else INCOMPLETE when any intended record is unavailable (missing, not run,
timeout, RSS breach, worker error, graph-limited translation); the partial quantities
are still reported with intended and available denominators.
"""
from __future__ import annotations

from collections import Counter

from . import analysis as A

RULE = (
    "Evidence gates first: INVALID when any evidence is invalid (wrong decode, source/input "
    "hash mismatch, B0 deterministic mismatch, supplied reference not reproduced, H-C "
    "identity failure, D1 problem); otherwise INCOMPLETE when any intended job or conversion "
    "record is unavailable (missing, not_run, timeout, rss_limit, error, graph-limited). "
    "Then: a SEARCH signal exists when, in cells where hid_full loses to the portfolio, a "
    "same-language supplied-cut partition (D3) is shorter than the saved full archive in a "
    "majority of those strings while B8 (D2) changes at most a small minority; a "
    "REPRESENTATION signal exists when, among D4 strings whose portfolio winner was the "
    "translated method and HID loses, the translation has the same LENGTH as the saved full "
    "archive (H == T) in a majority, so that H - C = T - C there (equal length, not an equal "
    "proposal; byte identity is reported separately). Both signals in disjoint family groups "
    "-> BOTH_SEPARATELY; one -> its focused scope; neither -> NO_CLEAR_DIRECTION.")


def _sum_cells(by_cell: dict, key: str) -> int:
    return sum(v.get(key, 0) for v in by_cell.values())


def decision(flags: dict, d1t: dict, s2: dict, s4: dict, res: dict,
             d1_problems: int) -> tuple[dict, dict]:
    ev = flags["evidence"]
    fb, fbar = flags["budget_opportunity_observed"], flags["restricted_path_barrier_observed"]
    fm, fp = flags["missed_baseline_structure_observed"], flags["proposal_representation_penalty_observed"]
    dec4 = flags["d4_loss_decomposition_where_portfolio_winner_was_translated"]["by_cell"]
    tot4 = Counter()
    for v in dec4.values():
        tot4.update(v)
    by3 = fbar["by_cell"]
    gates = {
        "all_jobs_ok": all(r["status"] == {"ok": r["jobs"]} for r in res.values()),
        "all_records_available": ev["complete"],
        "jobs": {k: r["jobs"] for k, r in res.items()},
        "unavailable": ev["unavailable"],
        "invalid_records": ev["invalid"]["records"],
        "B0_deterministic_mismatches": len(ev["invalid"]["B0_deterministic_mismatch"]),
        "B0_selected_bytes_mismatches": ev["invalid"]["B0_selected_bytes_mismatch"],
        "references_reproduced": f"{_sum_cells(by3, 'reference_reproduced')}/{_sum_cells(by3, 'strings')}",
        "references_not_reproduced": ev["invalid"]["reference_not_reproduced"],
        "identity_failures": sum(len(v) for v in fp["identity_failures"].values()),
        "d1_problems": d1_problems,
    }
    valid = not ev["invalid"]["any"] and d1_problems == 0
    complete = ev["complete"]
    loss3 = _sum_cells(by3, "H_gt_portfolio")
    loss3_better = _sum_cells(by3, "H_gt_portfolio_and_cheapest_all_lt_H")
    b8_changed = len(fb["witnesses"])
    search = rep = None                       # not evaluated on invalid or partial evidence
    if not valid:
        rec = "INVALID"
    elif not complete:
        rec = "INCOMPLETE"
    else:
        search = loss3 > 0 and 2 * loss3_better > loss3 and \
            2 * b8_changed < fb["denominator"]["target_strings"]
        rep = tot4["hid_loses"] > 0 and 2 * tot4["hid_loses_and_H_eq_T"] > tot4["hid_loses"]
        rec = ("BOTH_SEPARATELY" if search and rep else "SEARCH_FOCUSED" if search
               else "REPRESENTATION_FOCUSED" if rep else "NO_CLEAR_DIRECTION")
    cb = fb["control_behaviour"]
    numbers = {
        "d1_accepted_primary_estimate": d1t["accepted_primary_reproduction"]["estimate"],
        "d2_target_strings": fb["denominator"]["target_strings"],
        "d2_completed_B8_targets": fb["denominator"]["completed_B8_targets"],
        "d2_B8_witnesses": fb["witnesses"],
        "d2_B0_cap_hit_strings": fb["B0_cap_hit_strings"],
        "d2_controls_B8_differs": cb["B8_differs_from_B0"],
        "d2_controls_comparable": cb["comparable_controls"],
        "d2_control_strings": cb["control_strings"],
        "d2_equal_cell_mean_opportunity": fb["effect_equal_cell_mean_opportunity_per_input_bit"],
        "d2_partial_cells": fb["partial_cells"],
        "d3_strings": fbar["denominator"]["strings"],
        "d3_available_strings": fbar["denominator"]["available_strings"],
        "d3_subsets": fbar["denominator"]["subsets"],
        "d3_barrier_strings": _sum_cells(by3, "restricted_path_barrier"),
        "d3_barrier_kinds": fbar["barrier_kinds"],
        "d3_eligibility_obstructions": fbar["eligibility_obstructions"],
        "d3_cheapest_all_lt_H": _sum_cells(by3, "cheapest_all_lt_H"),
        "d3_cheapest_strict_lt_H": _sum_cells(by3, "cheapest_strict_lt_H"),
        "d3_cheapest_all_lt_portfolio": _sum_cells(by3, "cheapest_all_lt_portfolio"),
        "d3_cheapest_strict_lt_portfolio": _sum_cells(by3, "cheapest_strict_lt_portfolio"),
        "d3_H_gt_portfolio": loss3, "d3_H_gt_portfolio_and_cheapest_all_lt_H": loss3_better,
        "d3_returned_B0_cut_proximity": {k: v for k, v in
                                         fbar["descriptive_returned_B0_cut_proximity"].items()
                                         if k != "scope"},
        "d4_records": fp["denominator"]["conversion_records"],
        "d4_admissible": fp["denominator"]["admissible"],
        "d4_unavailable": fp["denominator"]["unavailable"],
        "d4_T_lt_H": {m: len(v) for m, v in fm["witnesses"].items()},
        "d4_T_gt_C": fp["penalty_records"],
        "d4_abs_T_minus_C_bits": fp["absolute_T_minus_C_bits"],
        "d4_translated_winner_strings": tot4["portfolio_winner_period"] + tot4["portfolio_winner_pair_grammar"],
        "d4_hid_loses": tot4["hid_loses"], "d4_hid_loses_H_eq_T": tot4["hid_loses_and_H_eq_T"],
        "d4_hid_loses_H_eq_T_identical_bytes": tot4["hid_loses_and_H_eq_T_identical_bytes"],
        "d4_hid_loses_H_eq_T_different_bytes": tot4["hid_loses_and_H_eq_T_different_bytes"],
        "d4_hid_loses_H_lt_T": tot4["hid_loses_and_H_lt_T"],
        "d4_hid_loses_translation_unavailable": tot4["hid_loses_translation_unavailable"],
    }
    basis = [] if valid and complete else [
        f"Evidence gate: {rec}. Unavailable {ev['unavailable']}; invalid {ev['invalid']['records']}, "
        f"B0 mismatches {gates['B0_deterministic_mismatches']}, references not reproduced "
        f"{len(gates['references_not_reproduced'])}, identity failures {gates['identity_failures']}, "
        f"D1 problems {d1_problems}. The rule is not evaluated; the lines below are partial."]
    basis += [
        f"D2: the B0 -> B8 cap increase changed the boundary output on {b8_changed} of "
        f"{fb['denominator']['completed_B8_targets']} completed targets "
        f"({fb['denominator']['target_strings']} intended) and on {cb['B8_differs_from_B0']} of "
        f"{cb['comparable_controls']} comparable controls ({cb['control_strings']} intended); "
        f"B0 hit a cap on {len(fb['B0_cap_hit_strings'])} strings.",
        f"D3 (truth-assisted, {numbers['d3_available_strings']} of {numbers['d3_strings']} strings "
        f"available): in {loss3} boundary-family strings where hid_full loses to the portfolio, "
        f"a supplied-cut partition is shorter than the saved full archive in {loss3_better}; "
        f"restricted path barriers in {numbers['d3_barrier_strings']} strings "
        f"({fbar['barrier_kinds']}), eligibility obstructions {fbar['eligibility_obstructions']}.",
        f"D4: {tot4['hid_loses']} strings where HID loses and the portfolio winner was the "
        f"translated method; equal length H == T in {tot4['hid_loses_and_H_eq_T']} "
        f"(byte-identical {tot4['hid_loses_and_H_eq_T_identical_bytes']}, different bytes "
        f"{tot4['hid_loses_and_H_eq_T_different_bytes']}), H < T in "
        f"{tot4['hid_loses_and_H_lt_T']}, translation unavailable "
        f"{tot4['hid_loses_translation_unavailable']}; no admissible translation shorter than H "
        f"({numbers['d4_T_lt_H']}), translations longer than their baseline "
        f"{fp['penalty_records']} of admissible {fp['denominator']['admissible']}.",
    ]
    dec = {"recommendation": rec, "rule": RULE, "gates": gates, "valid": valid,
           "complete": complete, "search_signal": search, "representation_signal": rep,
           "basis": basis, "flags": {k: v["value"] for k, v in flags.items() if "value" in v},
           "label": "post-hoc diagnostic recommendation; not a superiority claim"}
    return dec, numbers


def build(rec2: dict, rec3: dict, rec4: dict, d1_cases: dict, d1_tables: dict,
          d1_problems: int, refs: dict, ids: dict) -> dict:
    """job records -> rows -> summaries -> flags -> decision, for any availability.
    ``ids``: {'targets', 'controls', 'd4'}; record dicts map (case, kind) -> record or None."""
    targets, controls, ids4 = ids["targets"], ids["controls"], ids["d4"]
    ids2 = sorted(targets + controls)
    d2 = A.d2_rows(rec2, ids2)
    s2 = A.d2_summary(d2, targets, controls)
    d3 = A.d3_rows(rec3, targets, d2, refs)
    d4 = A.d4_rows(rec4, ids4)
    s4 = A.d4_summary(d4, ids4)
    res = {"D2": A.resource_summary(rec2), "D3": A.resource_summary(rec3),
           "D4": A.resource_summary(rec4)}
    b0_cuts = {c: rec2[(c, "B0")]["info"]["cuts"] for c in ids2 if d2[c]["B0_status"] == "ok"}
    flags = A.decision_quantities(d1_cases, d2, s2, d3, d4, s4, res, targets, controls, ids4,
                                  b0_cuts=b0_cuts)
    dec, numbers = decision(flags, d1_tables, s2, s4, res, d1_problems)
    return {"d2_rows": d2, "d2_summary": s2, "d3_rows": d3, "d4_rows": d4, "d4_summary": s4,
            "resources": res, "flags": flags, "decision": dec, "key_numbers": numbers}
