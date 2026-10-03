"""HID-search-v2 analysis from saved rows and archive bytes (BENCHMARK.md sections 5-7).

A study-specific adapter over the shared report owner: the population gate, the
verdict rule, the paired cell-stratified bootstrap (``report.cell_index_draws`` /
``report.stratified_bootstrap``), the equal-weight aggregate and the percentile
interval are all ``report``'s; nothing here re-implements them. No inference runs.

Primary: confirmation F01-F06, F12, 3 sizes x 20 replicates x {base, ragged};
s(x) = (bits(baseline_best) - bits(hid_full)) / n, mean within unit, within cell, then
equal cell means; seed 44001, 10,000 draws, percentile 95%.
Five targeted cumulative contrasts: one joint draw (seed 44002) over all 21 primary
cells against the frozen 20-unit index design; each contrast reads only its three
target cells; percentile 99% each (Bonferroni across five).
Descriptive (no verdicts): per family-size cells, three optional-interval summaries
(seeds 44003-44005) with full-versus-legacy from the same draws, estimates by
transfer size, resource/censoring rates, cost components and stage telemetry.
"""
from __future__ import annotations

from collections import defaultdict
from pathlib import Path

import numpy as np

from . import report as R
from . import validation as V
from .validation import HID_DEPLOYED

STRUCTURED = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")
ALL12 = tuple(f"F{i:02d}" for i in range(1, 13))
ARMS = ("hid_legacy", "hid_first_local", "hid_consensus_local", "hid_dense_local",
        "hid_global", "hid_full")
CONTRASTS = (("P_vs_L", "hid_first_local", "hid_legacy", "F06"),
             ("C_vs_P", "hid_consensus_local", "hid_first_local", "F06"),
             ("D_vs_C", "hid_dense_local", "hid_consensus_local", "F06"),
             ("G_vs_D", "hid_global", "hid_dense_local", "F06"),
             ("B_full_vs_G", "hid_full", "hid_global", "F12"))
REPS = 10000

ANALYSIS_PLAN_V2 = {
    "primary": {"role": "confirmation", "families": list(STRUCTURED), "method": "hid_full",
                "comparator": "baseline_best (minimum complete archive of the nine baselines)",
                "per_string": "(bits(baseline_best) - bits(hid_full)) / input_length",
                "weighting": "mean of base/ragged within a unit, mean of units within a "
                             "(family, base_length) cell, then the 21 cell means equally",
                "bootstrap": {"draws": REPS, "seed": 44001, "rng": "numpy.random.default_rng",
                              "scheme": "resample the 20 paired units with replacement within "
                                        "each cell, families/sizes/replicates ascending, all "
                                        "methods together",
                              "interval": "percentile [2.5, 97.5], numpy linear quantiles"},
                "gates": "whole-run engineering validity, then completeness of the declared "
                         "claim population, then availability of all nine baselines per "
                         "string (censoring -> inconclusive), then the interval; invalid or "
                         "incomplete -> not_assessed",
                "decision": {"supported": "lower bound > 0", "not_supported": "upper bound < 0",
                             "inconclusive": "interval touches or crosses 0"}},
    "targeted_contrasts": {
        "role": "confirmation", "draws": REPS, "seed": 44002,
        "joint_draw": "one draw over all 21 primary cells against the frozen 20-unit index "
                      "design in ascending family/size order, whatever rows are available; "
                      "each contrast dereferences only its complete target cells",
        "interval": "percentile [0.5, 99.5] (five two-sided 99% intervals)",
        "comparisons": [{"id": c[0], "added": c[1], "previous": c[2], "family": c[3],
                         "per_string": f"(bits({c[2]}) - bits({c[1]})) / n"} for c in CONTRASTS],
        "reading": {"supported": "lower bound > 0", "previous_better": "upper bound < 0",
                    "not_detected": "otherwise"},
        "caveat": "cumulative algorithm changes including their cost; not additive, not pure "
                  "mechanism effects, not an equal-work comparison"},
    "descriptive": {"all_family_confirmation_seed": 44003, "structured_transfer_seed": 44004,
                    "all_stress_seed": 44005, "draws": REPS, "interval": "percentile 95%",
                    "full_vs_legacy": "computed from the same draws",
                    "other_breakdowns": "estimates, counts and distributions only"},
    "hid_deployed_statuses": list(HID_DEPLOYED),
}


# ---------------------------------------------------------------------------
# Per-string quantities
# ---------------------------------------------------------------------------

def _deployed(r) -> bool:
    return r is not None and r.get("status") in HID_DEPLOYED and r.get("archive_bits") is not None


def saving_vs(method: str, comparator: str):
    """(comparator bits - method bits) / n, or None when either is unavailable. A
    portfolio comparator must be ``ok`` (censoring is handled by the gate)."""
    def fn(methods: dict):
        a, b = methods.get(method), methods.get(comparator)
        if not _deployed(a):
            return None
        if comparator == "baseline_best":
            if b is None or b.get("status") != "ok":
                return None
        elif not _deployed(b):
            return None
        return (b["archive_bits"] - a["archive_bits"]) / a["n_bits"]
    return fn


SAVE_PORTFOLIO = saving_vs("hid_full", "baseline_best")
SAVE_LEGACY = saving_vs("hid_full", "hid_legacy")


# ---------------------------------------------------------------------------
# Primary, contrasts, descriptive aggregates
# ---------------------------------------------------------------------------

def _required(design):
    return ("hid_full", "baseline_best") + tuple(design["baselines"])


def primary(validation, design) -> dict:
    index = validation["_index"]
    gate = R.population_gate(validation, design, "confirmation", STRUCTURED, _required(design))
    agg = R.aggregate(index, design, "confirmation", STRUCTURED, [SAVE_PORTFOLIO], 44001,
                      0.95, gate)
    out = {"role": "confirmation", "families": list(STRUCTURED), "gate": gate,
           "required_units": agg["required_units"], "available_units": agg["available_units"],
           "evidence_validity": "valid" if gate["engineering_valid"] else "invalid",
           "evidence_completeness": "complete" if gate["complete"] else "incomplete",
           "censored_baselines": gate["censored_count"]}
    if "endpoint" in agg:
        e = agg["endpoint"]
        ci = e["intervals"][0]
        out.update({"estimate_mean_saving_per_input_bit": e["estimate"][0], "ci95": ci,
                    "bootstrap": {"draws": REPS, "seed": 44001, "draw_mean": e["draw_mean"][0],
                                  "draw_sd": e["draw_sd"][0]},
                    "cells": e["cells"], "units": e["units"],
                    "strings": 2 * e["units"],
                    **_string_counts(index, design, "confirmation", STRUCTURED, SAVE_PORTFOLIO)})
        out["verdict"] = R.verdict(ci, gate)
    else:
        out["verdict"] = R.verdict(None, gate) if not gate["assessable"] else "inconclusive"
        out["partial_diagnostic"] = R._first(agg.get("partial_diagnostic"))
    return out


def _string_counts(index, design, role, families, fn) -> dict:
    vals, bits = [], []
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design, role):
        if fam in families and cid in index:
            v = fn(index[cid])
            if v is not None:
                vals.append(v)
                bits.append(v * n)
    if not vals:
        return {}
    b = np.rint(bits)
    return {"strings_hid_better": int((b > 0).sum()), "strings_tied": int((b == 0).sum()),
            "strings_hid_worse": int((b < 0).sum()),
            "median_saving_per_input_bit": float(np.median(vals)),
            "mean_saving_bits_unweighted": float(np.mean(bits))}


def contrasts(validation, design) -> dict:
    """Five cumulative contrasts from ONE joint draw over the 21 declared primary cells."""
    index = validation["_index"]
    spec = design["splits"]["confirmation"]
    keys = [(f, bl) for f in sorted(set(STRUCTURED) & set(spec["families"]))
            for bl in sorted(spec["base_lengths"])]
    sizes = {k: len(spec["replicates"]) for k in keys}
    draws = R.cell_index_draws(sizes, REPS, 44002)
    out = {}
    for cid_, added, prev, fam in CONTRASTS:
        gate = R.population_gate(validation, design, "confirmation", (fam,), (added, prev))
        gate["censored_count"] = 0                  # HID statuses are deployed, never censored
        fn = saving_vs(added, prev)
        cells, unavailable = {}, []
        for cell, label, pair in R.design_units(index, design, "confirmation", (fam,)):
            v = R.unit_value(pair, fn)
            if v is None:
                unavailable.append(label)
            cells.setdefault(cell, []).append(v)
        item = {"added": added, "previous": prev, "family": fam, "gate": gate,
                "required_units": sum(len(v) for v in cells.values()),
                "available_units": sum(1 for v in cells.values() for x in v if x is not None)}
        if gate["assessable"] and not unavailable and cells:
            mats = {k: np.asarray(v, dtype=float) for k, v in cells.items()}
            point = float(np.mean([m.mean() for m in mats.values()]))
            boot = np.mean([mats[k][draws[k]].mean(axis=1) for k in sorted(mats)], axis=0)
            ci = R.percentile_interval(boot, 0.99)
            reading = ("supported" if ci[0] > 0 else "previous_better" if ci[1] < 0
                       else "not_detected")
            item.update({"estimate_per_input_bit": point, "ci99": ci, "reading": reading,
                         "cells": len(mats), "units": int(sum(m.size for m in mats.values())),
                         "draw_sd": float(boot.std())})
        else:
            item["reading"] = "not_assessed"
            avail = {k: [x for x in v if x is not None] for k, v in cells.items()}
            if any(avail.values()):
                item["partial_diagnostic"] = {
                    "label": "PARTIAL: available units only; not the prespecified contrast",
                    "estimate": float(np.mean([np.mean(v) for v in avail.values() if v])),
                    "unavailable_units": unavailable[:200]}
        out[cid_] = item
    return out


def describe_summary(validation, design, role, families, seed, note) -> dict | None:
    if role not in design["splits"]:
        return None
    index = validation["_index"]
    req = ("hid_full", "hid_legacy") + _required(design)
    gate = R.population_gate(validation, design, role, families, req)
    ag = R.aggregate(index, design, role, families, [SAVE_PORTFOLIO, SAVE_LEGACY], seed, 0.95,
                     gate)
    item = {"role": role, "families": list(families), "gate": gate, "seed": seed, "note": note,
            "required_units": ag["required_units"], "available_units": ag["available_units"]}
    if "endpoint" in ag:
        e = ag["endpoint"]
        item.update({"full_vs_portfolio": e["estimate"][0], "full_vs_portfolio_ci95": e["intervals"][0],
                     "full_vs_legacy": e["estimate"][1], "full_vs_legacy_ci95": e["intervals"][1],
                     "cells": e["cells"], "units": e["units"]})
    else:
        pd = ag.get("partial_diagnostic")
        item["partial_diagnostic"] = None if pd is None else {
            "label": pd["label"], "full_vs_portfolio": pd["estimate"][0],
            "full_vs_legacy": pd["estimate"][1], "units": pd["units"],
            "unavailable_count": pd["unavailable_count"]}
    return item


def describe_cells(validation, design, role) -> list[dict]:
    """Per (family, base_length): estimates, counts and distributions; no intervals."""
    if role not in design["splits"]:
        return []
    index = validation["_index"]
    spec = design["splits"][role]
    out = []
    for fam in spec["families"]:
        for bl in sorted(spec["base_lengths"]):
            row = {"family": fam, "base_length": bl, "units_required": len(spec["replicates"])}
            for key, fn in (("vs_portfolio", SAVE_PORTFOLIO), ("vs_legacy", SAVE_LEGACY)):
                units, strings = [], []
                for rep in sorted(spec["replicates"]):
                    pair = {rg: index.get(V.design_case_id(design, role, fam, bl, rep, rg))
                            for rg in (False, True)}
                    vals = [fn(p) for p in pair.values() if p is not None]
                    strings += [v for v in vals if v is not None]
                    if len(vals) == 2 and None not in vals:
                        units.append(sum(vals) / 2)
                d = {"units_complete": len(units), "strings": len(strings)}
                if units:
                    d["mean_per_input_bit"] = float(np.mean(units))
                    d["median_string_per_input_bit"] = float(np.median(strings))
                    d["strings_better"] = int(sum(v > 0 for v in strings))
                    d["strings_tied"] = int(sum(v == 0 for v in strings))
                    d["strings_worse"] = int(sum(v < 0 for v in strings))
                if len(units) < len(spec["replicates"]):
                    d["partial"] = True
                row[key] = d
            out.append(row)
    return out


def by_transfer_size(validation, design) -> dict:
    if "transfer" not in design["splits"]:
        return {}
    index = validation["_index"]
    out = {}
    for bl in sorted(design["splits"]["transfer"]["base_lengths"]):
        res = {}
        for key, fn in (("full_vs_portfolio", SAVE_PORTFOLIO), ("full_vs_legacy", SAVE_LEGACY)):
            cells = defaultdict(list)
            missing = 0
            for cell, label, pair in R.design_units(index, design, "transfer", STRUCTURED):
                if cell[1] != bl:
                    continue
                v = R.unit_value(pair, fn)
                if v is None:
                    missing += 1
                else:
                    cells[cell].append(v)
            res[key] = (float(np.mean([np.mean(v) for v in cells.values()])) if cells else None)
            res[f"{key}_units_unavailable"] = missing
        out[str(bl)] = dict(res, note="estimate only; structured families; equal cell weights")
    return out


# ---------------------------------------------------------------------------
# Resources, telemetry and cost components
# ---------------------------------------------------------------------------

def status_rates(validation, design) -> dict:
    out = {}
    for role in design["splits"]:
        n = sum(1 for _ in V.expected_cases(design, role))
        per = validation["status_counts"].get(role, {})
        out[role] = {m: {"expected": n, **{k: v for k, v in per.get(m, {}).items()}}
                     for m in design["methods"]}
    return out


def stage_telemetry(rows) -> dict:
    out: dict = {}
    for r in rows:
        if r["method"] not in ARMS or r.get("status") != "ok":
            continue
        t = r.get("search_counters") or {}
        key = f"{r['split']}|{r['method']}"
        o = out.setdefault(key, {"rows": 0, "selected_stage": defaultdict(int),
                                 "stage_strict_improvements": defaultdict(int),
                                 "stage_serialized": defaultdict(int),
                                 "stage_gate_rejections": defaultdict(int),
                                 "stage_graph_rejections": defaultdict(int),
                                 "stage_wall_s": defaultdict(float),
                                 "B_stop_reason": defaultdict(int), "B_cap_hit": 0,
                                 "B_root_trials": 0, "B_leaf_length_charge_per_n": 0.0})
        o["rows"] += 1
        o["selected_stage"][t.get("selected_stage")] += 1
        for s, st in t.get("stages", {}).items():
            o["stage_strict_improvements"][s] += st.get("strict_improvements", 0) or 0
            o["stage_serialized"][s] += st.get("serialized", 0) or 0
            o["stage_gate_rejections"][s] += st.get("gate_rejections", 0) or 0
            o["stage_graph_rejections"][s] += st.get("graph_rejections", 0) or 0
            o["stage_wall_s"][s] += st.get("wall_s", 0.0) or 0.0
            if s == "B":
                o["B_stop_reason"][st.get("stop_reason")] += 1
                o["B_cap_hit"] += int(bool(st.get("cap_hit")))
                o["B_root_trials"] += st["counts"]["root_trials"]
                o["B_leaf_length_charge_per_n"] += st["counts"]["leaf_length_charge"] / max(1, r["n_bits"])
    return {k: {kk: (dict(vv) if isinstance(vv, defaultdict) else vv) for kk, vv in v.items()}
            for k, v in sorted(out.items())}


def cost_components(d: Path, rows, methods=("hid_legacy", "hid_full", "baseline_best")) -> dict:
    """Mean bits per bucket of the deployed archives, by role and method (exact sums)."""
    import hashlib

    from .decode import ArchiveError
    from .ledger import BUCKETS, field_buckets
    acc: dict = {}
    cache: dict = {}
    unavailable = []
    for r in rows:
        if r["method"] not in methods or not r.get("archive_path"):
            continue
        h = r["archive_sha256"]
        if h not in cache:
            p = d / r["archive_path"]
            data = p.read_bytes() if p.is_file() else None
            if data is None or hashlib.sha256(data).hexdigest() != h:
                cache[h] = None
            else:
                try:
                    cache[h] = field_buckets(data)
                except (ArchiveError, AssertionError, IndexError, ValueError):
                    cache[h] = None
        if cache[h] is None:              # validate_run has already made the run invalid
            unavailable.append(f"{r['case_id']}:{r['method']}")
            continue
        key = f"{r['split']}|{r['method']}"
        a = acc.setdefault(key, {"archives": 0, **dict.fromkeys(BUCKETS, 0), "total_bits": 0})
        a["archives"] += 1
        for b in BUCKETS:
            a[b] += cache[h][b]
        a["total_bits"] += r["archive_bits"]
    out = {}
    for k, a in sorted(acc.items()):
        n = a["archives"]
        out[k] = {"archives": n, "mean_total_bits": a["total_bits"] / n,
                  "mean_bits": {b: a[b] / n for b in BUCKETS},
                  "sum_check": sum(a[b] for b in BUCKETS) == a["total_bits"]}
    if unavailable:
        out["unavailable_archives"] = unavailable[:200]
    return out


# ---------------------------------------------------------------------------
# Summary and claim ledger
# ---------------------------------------------------------------------------

def summarise(validation: dict, design: dict, run_dir: Path) -> dict:
    index = validation["_index"]
    rows = sorted((r for m in index.values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    pub = V.public(validation)
    eng = {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                               "present_rows", "archives_checked", "distinct_archives_decoded")}
    eng.update({k: pub[k][:200] for k in ("invalid", "incomplete", "censored", "duplicates",
                                          "unknown")})
    eng["missing_units"] = {k: v[:200] for k, v in pub["missing_units"].items()}
    eng["missing_methods"] = pub["missing_methods"]
    checks = validation.get("search_v2_checks", {})
    s = {"analysis_plan": ANALYSIS_PLAN_V2, "validation": eng,
         "round_trips": {"decode_ok": sum(1 for r in rows if r["decode_ok"] is True),
                         "decode_failed": sum(1 for r in rows if r["decode_ok"] is False),
                         "with_archive": sum(1 for r in rows if r["archive_path"])},
         "status_rates": status_rates(validation, design),
         "nesting": {k: checks.get(k) for k in ("nesting_pairs_checked",
                                                "resource_nesting_break_count")},
         "resource_nesting_breaks": (checks.get("resource_nesting_breaks") or [])[:200]}
    if "confirmation" in design["splits"]:
        s["primary"] = primary(validation, design)
        s["contrasts"] = contrasts(validation, design)
        s["all_family_confirmation"] = describe_summary(
            validation, design, "confirmation", ALL12, 44003,
            "descriptive; all twelve families; not the primary population")
    s["structured_transfer"] = describe_summary(
        validation, design, "transfer", STRUCTURED, 44004,
        "descriptive; 21 structured transfer cells, four units each")
    s["all_stress"] = describe_summary(validation, design, "stress", ("S01", "S02"), 44005,
                                       "descriptive; parameter-shift stress; four cells")
    s["transfer_by_size"] = by_transfer_size(validation, design)
    s["cells"] = {role: describe_cells(validation, design, role) for role in design["splits"]}
    s["stage_telemetry"] = stage_telemetry(rows)
    s["cost_components"] = cost_components(run_dir, rows)
    s["resources"] = R.resources(rows)
    s["selected_baselines"] = R._selected_counts(rows)
    return s


LEDGER_STATUS = R.LEDGER_STATUS


def claim_ledger(summary: dict, run_id: str, result_rel: str) -> list[dict]:
    base = f"{result_rel}/{run_id}"
    led = []
    p = summary.get("primary") or {}
    led.append({
        "id": "C1", "claim": "HID-search-v2 (hid_full) yields an average code-length saving "
                             "over the nine-baseline portfolio on fresh instances of the "
                             "declared structured confirmation population",
        "status": LEDGER_STATUS[p.get("verdict", "not_assessed")], "decision": p.get("verdict"),
        "evidence_gate": R._gate_note(p.get("gate")),
        "metric": "equal-cell mean of (bits(baseline_best) - bits(hid_full)) / n, paired units",
        "estimate": p.get("estimate_mean_saving_per_input_bit"), "uncertainty": p.get("ci95"),
        "evidence": [f"{base}/summary.json#primary"],
        "domain": "confirmation F01-F06, F12; 256, 1024, 4096 bits plus ragged +3; "
                  "replicates 3000-3019; namespace search_v2_confirmation",
        "caveat": "new instances of familiar generators, not unfamiliar families; a code length "
                  "under one fixed language and resource policy; not K, not generator recovery"})
    val, rt = summary.get("validation", {}), summary.get("round_trips", {})
    ok = bool(val.get("engineering_valid")) and rt.get("decode_failed") == 0
    led.append({"id": "C2", "claim": "Every stored archive decodes exactly to its input with "
                                     "the independent decoder",
                "status": "supported" if ok else "not_supported",
                "decision": "supported" if ok else "not_supported",
                "evidence_gate": "whole-run engineering validation",
                "metric": "archives decoded and hash-matched / archives promised",
                "estimate": {"archives_checked": val.get("archives_checked"),
                             "distinct_archives_decoded": val.get("distinct_archives_decoded"),
                             **rt},
                "uncertainty": None, "evidence": [f"{base}/verification.json"],
                "domain": "all roles of this run", "caveat": "engineering claim"})
    for i, (k, c) in enumerate((summary.get("contrasts") or {}).items()):
        st = {"supported": "supported", "previous_better": "not_supported",
              "not_detected": "inconclusive", "not_assessed": "inconclusive"}[c["reading"]]
        led.append({"id": f"C3.{i + 1}", "claim": f"{k}: adding the stage that turns "
                                                  f"{c['previous']} into {c['added']} saves code "
                                                  f"length on confirmation {c['family']}",
                    "status": st, "decision": c["reading"],
                    "evidence_gate": R._gate_note(c["gate"]),
                    "metric": f"equal-cell mean of (bits({c['previous']}) - bits({c['added']}))/n",
                    "estimate": c.get("estimate_per_input_bit"), "uncertainty": c.get("ci99"),
                    "evidence": [f"{base}/summary.json#contrasts.{k}"],
                    "domain": f"confirmation {c['family']}, 60 paired units, three size cells",
                    "caveat": "99% Bonferroni interval; cumulative algorithm change including its "
                              "cost; not additive, not a pure mechanism effect, and no rescue of a "
                              "failed primary test"})
    for cid, key, text in (("C4", "structured_transfer", "structured transfer (16,384-131,072 bits)"),
                           ("C5", "all_stress", "parameter-shift stress S01/S02"),
                           ("C6", "all_family_confirmation", "all twelve confirmation families")):
        t = summary.get(key)
        if t:
            led.append({"id": cid, "claim": f"Descriptive: hid_full versus the portfolio on {text}",
                        "status": "descriptive", "decision": None,
                        "evidence_gate": R._gate_note(t["gate"]),
                        "metric": "equal-cell mean saving per input bit (and versus hid_legacy)",
                        "estimate": t.get("full_vs_portfolio"),
                        "uncertainty": t.get("full_vs_portfolio_ci95"),
                        "evidence": [f"{base}/summary.json#{key}"], "domain": key,
                        "caveat": "descriptive only; no superiority verdict"})
    for cid, text in (("C7", "HID-search-v2 computes Kolmogorov complexity or a minimum "
                             "description length over all programs"),
                      ("C8", "A found description identifies the true generator"),
                      ("C9", "Fresh instances of familiar generators establish unfamiliar-family "
                             "generalization"),
                      ("C10", "Full-string compression establishes prediction of unseen suffixes")):
        led.append({"id": cid, "claim": text, "status": "out_of_scope", "decision": None,
                    "evidence_gate": None, "metric": None, "estimate": None,
                    "uncertainty": None, "evidence": ["PROTOCOL_hierarchy_search_v2.md section 7"],
                    "domain": None, "caveat": "not tested by this design"})
    return led
