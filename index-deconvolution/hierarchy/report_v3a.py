"""HID-search-v3a analysis from saved rows, archives and trace sidecars (BENCHMARK.md 4-5).

A study-specific adapter over the shared report owner: ``report.design_units``,
``report.unit_value``, ``report.weighted_mean``, ``report.stratified_bootstrap`` (with
its ``cell_index_draws``), ``report.percentile_interval`` and ``report.verdict`` are
``report``'s; nothing here re-implements them. No inference runs here.

Primary: s(x) = (bits(hid_full) - bits(hid_refine4)) / n on the six target cells
(role, family, base_length), mean of base/ragged per unit, of the 20 units per cell,
then of the six cells equally; 10,000 draws, seed 55001, two-sided 99% percentile.
Decision: INVALID, then INCOMPLETE (any declared job absent or not_run), then
SUPPORTED (lower > 0), HARMFUL (upper < 0), INCONCLUSIVE otherwise.

Trace checks recompute the stage-B charges, cache hits, outcomes and summary of every
sidecar from its own events and compare them with the row's telemetry.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import report as R
from . import validation as V
from .validation import HID_DEPLOYED

PRIMARY_ROLES = ("boundary", "boundary_large", "boundary_stress")
CONTROL_ROLE = "controls"
HID = ("hid_full", "hid_refine4")
REPS, SEED, LEVEL = 10000, 55001, 0.99
TOLERANCE_BITS = 8
OUTCOMES = ("new_admissible", "new_graph_rejection", "cached_admissible",
            "cached_graph_rejection", "cap_blocked")
CHARGES = ("root_trials", "leaf_cache", "leaf_length_charge")
VERDICT_LABEL = {"supported": "SUPPORTED", "not_supported": "HARMFUL",
                 "inconclusive": "INCONCLUSIVE"}

ANALYSIS_PLAN_V3A = {
    "primary": {"roles": list(PRIMARY_ROLES), "cells": "(role, family, base_length), six",
                "per_string": "(bits(hid_full) - bits(hid_refine4)) / actual_n_bits",
                "positive_means": "k = 4 saves bits",
                "weighting": ["base_ragged_pair_mean", "within_cell_unit_mean",
                              "equal_six_cell_mean"],
                "bootstrap": {"owner": "hierarchy.report.stratified_bootstrap", "draws": REPS,
                              "seed": SEED, "rng": "numpy.random.default_rng",
                              "cell_order": "lexicographic (role, family, base_length)",
                              "unit_order": "replicate ascending",
                              "interval": "two-sided 99% percentile, numpy linear quantiles"},
                "hid_fallback": "validated raw archive cost with explicit timeout_raw/rss_limit_raw",
                "decision_precedence": ["INVALID", "INCOMPLETE", "SUPPORTED if lower > 0",
                                        "HARMFUL if upper < 0", "INCONCLUSIVE otherwise"]},
    "descriptive_only": ["six cell means and signed counts", "archive-size distributions",
                         "k=4 and k=1 versus portfolio where all nine constituents exist",
                         "control outcomes", "status, stage, work, wall, RSS",
                         "proposed/evaluated/returned trace counts"],
    "other_intervals": False,
    "hid_deployed_statuses": list(HID_DEPLOYED),
}


# ---------------------------------------------------------------------------
# Trace sidecars
# ---------------------------------------------------------------------------

def load_trace(d: Path, row: dict | None) -> tuple[dict | None, str]:
    if row is None:
        return None, "row_absent"
    st = row.get("trace_status")
    if st != "complete":
        return None, st or "missing"
    p = d / row["trace_path"]
    if not p.is_file():
        return None, "file_missing"
    data = p.read_bytes()
    if hashlib.sha256(data).hexdigest() != row.get("trace_sha256"):
        return None, "hash_mismatch"
    return json.loads(data), "complete"


def trace_problems(side: dict, row: dict) -> list[str]:
    """Every sidecar quantity recomputed from its events, against the row telemetry."""
    out = []
    if side.get("config_sha256") != row.get("config_sha256"):
        out.append("config hash differs from the row")
    if row.get("status") == "ok" and side.get("archive_sha256") != row.get("archive_sha256"):
        out.append("selected archive differs from the row")
    tele = (row.get("search_counters") or {}).get("stages", {}).get("B")
    inv = side.get("boundary_invocations") or []
    if tele is None or len(inv) != 1:
        return out + [f"expected one B invocation, got {len(inv)} (telemetry B: {tele is not None})"]
    t = inv[0]
    ev, c = t["events"], tele["counts"]
    if t.get("event_count") != len(ev) or len(ev) > t.get("max_events", 0):
        out.append("event count inconsistent or above the bound")
    if [e.get("position") for e in ev] != list(range(len(ev))):
        out.append("event positions are not the call order 0..n-1")
    if any(e.get("outcome") not in OUTCOMES for e in ev):
        out.append("unknown outcome")
    new = sum(e["outcome"].startswith("new_") for e in ev)
    cap = [i for i, e in enumerate(ev) if e["outcome"] == "cap_blocked"]
    done = [e for e in ev if e["outcome"] != "cap_blocked"]
    if new != c["root_trials"]:
        out.append(f"new evaluations {new} != root_trials {c['root_trials']}")
    if sum(e["outcome"] == "new_graph_rejection" for e in ev) != c["graph_rejections"]:
        out.append("new graph rejections differ from the counter")
    for ph, key in (("coarse", "coarse_trials"), ("refine", "refine_trials")):
        if sum(e["phase"] == ph for e in done) != c[key]:
            out.append(f"{ph} completed requests differ from {key}")
    if sum(e["phase"] == "initial" for e in ev) != 1 or ev[0]["phase"] != "initial":
        out.append("the first event is not the single initial request")
    if bool(cap) != bool(tele.get("cap_hit")) or (cap and cap != [len(ev) - 1]):
        out.append("cap-blocked events do not match the cap exit")
    for a, b in zip(ev, ev[1:]):
        if a["post"] != b["pre"]:
            out.append(f"charges change between events {a['position']} and {b['position']}")
            break
    for e in ev:
        if e["cache_hit"] and e["outcome"] != "cap_blocked" and e["pre"] != e["post"]:
            out.append(f"cached event {e['position']} changed a charge")
            break
        if e["cache_hit"] != e["outcome"].startswith("cached_") and e["outcome"] != "cap_blocked":
            out.append(f"event {e['position']} outcome disagrees with cache_hit")
            break
    if ev and ev[-1]["post"] != {k: c[k] for k in CHARGES}:
        out.append("final charges differ from the counters")
    rounds = max((e["round"] for e in ev), default=0)
    if rounds != c["rounds"]:
        out.append(f"last event round {rounds} != rounds {c['rounds']}")
    s = t["summary"]
    kinds = [m["kind"] for m in s]
    if not s or kinds[-1] != "final" or (tele.get("archive_bits") is not None and kinds[0] != "initial"):
        out.append("summary is not initial ... final")
    elif sum(k == "commit" for k in kinds) != c["commits"]:
        out.append("summary commits differ from the counter")
    else:
        fin = s[-1]
        if fin["cuts"] != tele["cuts"] or (fin["archive_bytes"] is not None
                                           and 8 * fin["archive_bytes"] != tele["archive_bits"]):
            out.append("final summary differs from the B output")
    return out


def _covered(supplied, cuts, tol: int) -> int:
    return sum(1 for s in supplied if any(abs(s - c) <= tol for c in cuts))


def trace_summary(d: Path, row: dict | None, supplied=None, tol: int = TOLERANCE_BITS) -> dict:
    """Counts of one HID row's trace; supplied-cut coverage only when ``supplied`` is
    given (development only: never on prospective data)."""
    side, st = load_trace(d, row)
    out = {"status": st}
    if side is None:
        return out
    out["problems"] = trace_problems(side, row)
    inv = side["boundary_invocations"][0]
    ev = inv["events"]
    proposed = sorted({e["cut"] for e in ev if "cut" in e})
    evaluated = sorted({e["cut"] for e in ev if "cut" in e and e["outcome"] != "cap_blocked"})
    fin = inv["summary"][-1]
    returned = list(fin["cuts"])
    out.update({"events": len(ev), "proposed_cuts": len(proposed),
                "evaluated_cuts": len(evaluated),
                "new_serialized_admissible": sum(e["outcome"] == "new_admissible" for e in ev),
                "graph_rejections": sum(e["outcome"].endswith("graph_rejection") for e in ev),
                "cached_requests": sum(e["outcome"].startswith("cached_") for e in ev),
                "cap_blocked": sum(e["outcome"] == "cap_blocked" for e in ev),
                "stop_reason": fin.get("stop_reason"), "final_source": fin.get("source"),
                "commits": sum(m["kind"] == "commit" for m in inv["summary"]),
                "returned_cuts": returned})
    if supplied is not None:
        sup = sorted(set(supplied))
        cov = {}
        for kind, cuts in (("proposed", proposed), ("evaluated", evaluated),
                           ("returned", returned)):
            cov[kind] = ({"numerator": _covered(sup, cuts, tol), "denominator": len(sup)}
                         if sup else {"numerator": None, "denominator": 0,
                                      "note": "no supplied cuts: unavailable"})
        out["supplied_coverage"] = cov
    return out


def trace_checks(index: dict, run_dir: Path, hid_methods) -> dict:
    """Validation hook: every ``ok`` HID row has a complete, consistent trace."""
    invalid, counts = [], defaultdict(int)
    for cid, have in sorted(index.items()):
        for m in hid_methods:
            r = have.get(m)
            if r is None or r.get("status") in (None, "not_run", "error"):
                continue
            side, st = load_trace(run_dir, r)
            counts[st] += 1
            if r["status"] == "ok":
                if side is None:
                    invalid.append(f"{cid}:{m} trace {st} on an ok HID row")
                    continue
                invalid += [f"{cid}:{m} trace: {p}" for p in trace_problems(side, r)]
            elif st != "unavailable_watchdog":
                invalid.append(f"{cid}:{m} {r['status']} row has trace status {st}")
    return {"invalid": invalid, "trace_status_counts": dict(counts)}


# ---------------------------------------------------------------------------
# Per-string quantities and the primary contrast
# ---------------------------------------------------------------------------

def _deployed(r) -> bool:
    return r is not None and r.get("status") in HID_DEPLOYED and r.get("archive_bits") is not None


def saving(methods: dict) -> float | None:
    a, b = methods.get("hid_full"), methods.get("hid_refine4")
    if not _deployed(a) or not _deployed(b):
        return None
    return (a["archive_bits"] - b["archive_bits"]) / a["n_bits"]


def vs_portfolio(method: str):
    def fn(methods: dict):
        a, p = methods.get(method), methods.get("baseline_best")
        if not _deployed(a) or p is None or p.get("status") != "ok":
            return None
        return (p["archive_bits"] - a["archive_bits"]) / a["n_bits"]
    return fn


def role_cells(index, design, roles, fn) -> tuple[dict, list, int]:
    """({(role, family, base_length): array(units x 1)}, unavailable units, required)."""
    cells, unavailable, required = defaultdict(list), [], 0
    for role in roles:
        if role not in design["splits"]:
            continue
        spec = design["splits"][role]
        for (fam, bl), label, pair in R.design_units(index, design, role, spec["families"]):
            required += 1
            v = R.unit_value(pair, fn)
            if v is None:
                unavailable.append(label)
            else:
                cells[(role, fam, bl)].append([v])
    return ({k: np.asarray(v, dtype=float) for k, v in sorted(cells.items())},
            unavailable, required)


def decision(validation: dict, design: dict) -> dict:
    index = validation["_index"]
    cells, unavailable, required = role_cells(index, design, PRIMARY_ROLES, saving)
    out = {"required_units": required, "available_units": required - len(unavailable),
           "engineering_valid": bool(validation["engineering_valid"]),
           "complete": bool(validation["complete"]),
           "cells": {"|".join(map(str, k)): {"units": int(m.shape[0]),
                                            "mean": float(m[:, 0].mean())}
                     for k, m in cells.items()}}
    if not out["engineering_valid"]:
        out.update(verdict="INVALID", reason="engineering invalidity; no inferential verdict")
    elif not out["complete"] or unavailable or len(cells) != 6 or \
            any(m.shape[0] != 20 for m in cells.values()):
        out.update(verdict="INCOMPLETE", reason="declared jobs absent/not_run or HID units "
                   "unavailable; no primary interval",
                   unavailable_units=unavailable[:200])
        if cells:
            out["partial_diagnostic"] = {"label": "PARTIAL: available units only; not the "
                                                  "prespecified endpoint",
                                         "equal_cell_mean": float(R.weighted_mean(cells)[0])}
    else:
        point = float(R.weighted_mean(cells)[0])
        draws = R.stratified_bootstrap(cells, REPS, SEED)
        ci = R.percentile_interval(draws[:, 0], LEVEL)
        gate = {"engineering_valid": True, "complete": True, "censored_count": 0}
        out.update(estimate_bits_per_input_bit=point, ci99=list(ci),
                   verdict=VERDICT_LABEL[R.verdict(ci, gate)],
                   bootstrap={"draws": REPS, "seed": SEED, "level": LEVEL,
                              "cell_order": ["|".join(map(str, k)) for k in sorted(cells)],
                              "draw_mean": float(draws[:, 0].mean()),
                              "draw_sd": float(draws[:, 0].std())})
    return out


# ---------------------------------------------------------------------------
# Descriptive tables
# ---------------------------------------------------------------------------

def _sign(v: float) -> str:
    return "better" if v > 0 else ("worse" if v < 0 else "tie")


def per_string(index, design, roles) -> list[dict]:
    out = []
    for role in roles:
        for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design, role):
            have = index.get(cid, {})
            a, b, p = have.get("hid_full"), have.get("hid_refine4"), have.get("baseline_best")
            s = saving(have)
            out.append({"case_id": cid, "role": sp, "family": fam, "base_length": bl,
                        "replicate": rep, "ragged": rg, "n_bits": n,
                        "hid_full_status": a and a["status"], "hid_refine4_status": b and b["status"],
                        "hid_full_bits": a and a["archive_bits"],
                        "hid_refine4_bits": b and b["archive_bits"],
                        "baseline_best_status": p and p["status"],
                        "baseline_best_bits": p and p["archive_bits"],
                        "baseline_best_method": p and p.get("selected_method"),
                        "hid_full_stage": a and a.get("best_source"),
                        "hid_refine4_stage": b and b.get("best_source"),
                        "saving_per_input_bit": s,
                        "sign": None if s is None else _sign(s)})
    return out


def per_unit(strings) -> list[dict]:
    units = defaultdict(dict)
    for s in strings:
        units[(s["role"], s["family"], s["base_length"], s["replicate"])][s["ragged"]] = s
    out = []
    for (role, fam, bl, rep), pair in sorted(units.items()):
        vals = [pair[r]["saving_per_input_bit"] for r in (False, True) if r in pair]
        ok = len(vals) == 2 and all(v is not None for v in vals)
        out.append({"role": role, "family": fam, "base_length": bl, "replicate": rep,
                    "unit_saving": (vals[0] + vals[1]) / 2 if ok else None})
    return out


def per_cell(strings, units) -> list[dict]:
    cells = defaultdict(lambda: {"strings": [], "units": []})
    for s in strings:
        cells[(s["role"], s["family"], s["base_length"])]["strings"].append(s)
    for u in units:
        cells[(u["role"], u["family"], u["base_length"])]["units"].append(u)
    out = []
    for k, v in sorted(cells.items()):
        us = [u["unit_saving"] for u in v["units"] if u["unit_saving"] is not None]
        ss = [s for s in v["strings"] if s["saving_per_input_bit"] is not None]
        dist = {}
        for m in ("hid_full_bits", "hid_refine4_bits", "baseline_best_bits"):
            xs = [s[m] for s in v["strings"] if s[m] is not None]
            dist[m] = ({"min": min(xs), "median": float(np.median(xs)), "max": max(xs),
                        "n": len(xs)} if xs else None)
        out.append({"cell": "|".join(map(str, k)), "units": len(v["units"]),
                    "available_units": len(us), "mean_unit_saving": float(np.mean(us)) if us else None,
                    "strings_better": sum(s["sign"] == "better" for s in ss),
                    "strings_tie": sum(s["sign"] == "tie" for s in ss),
                    "strings_worse": sum(s["sign"] == "worse" for s in ss),
                    "units_better": sum(x > 0 for x in us), "units_tie": sum(x == 0 for x in us),
                    "units_worse": sum(x < 0 for x in us), "archive_bits": dist})
    return out


def versus_portfolio(index, design) -> dict:
    out = {}
    for m in HID:
        cells, unavailable, required = role_cells(index, design, PRIMARY_ROLES, vs_portfolio(m))
        out[m] = {"equal_cell_mean": float(R.weighted_mean(cells)[0])
                  if cells and not unavailable else None,
                  "available_units": required - len(unavailable), "required_units": required,
                  "note": "descriptive; reported only when all nine constituents are available "
                          "for every primary unit"}
    return out


def resources(rows) -> dict:
    out = defaultdict(lambda: {"jobs": 0, "statuses": defaultdict(int), "worker_wall_s": 0.0,
                               "max_worker_wall_s": 0.0, "max_peak_rss_bytes": 0})
    for r in rows:
        if r["method"] == "baseline_best":
            continue
        o = out[r["method"]]
        o["jobs"] += 1
        o["statuses"][r["status"]] += 1
        w = (r.get("worker_wall_ns") or 0) / 1e9
        o["worker_wall_s"] += w
        o["max_worker_wall_s"] = max(o["max_worker_wall_s"], w)
        o["max_peak_rss_bytes"] = max(o["max_peak_rss_bytes"], r.get("peak_rss_bytes") or 0)
    return {m: dict(v, statuses=dict(v["statuses"]),
                    label="instrumented measurement (trace observer enabled for HID arms)")
            for m, v in sorted(out.items())}


def hid_telemetry(rows) -> dict:
    out = {}
    for m in HID:
        stops, stages, caps = defaultdict(int), defaultdict(int), defaultdict(int)
        for r in rows:
            if r["method"] != m or r["status"] != "ok":
                continue
            stages[r.get("best_source")] += 1
            b = (r.get("search_counters") or {}).get("stages", {}).get("B", {})
            stops[b.get("stop_reason")] += 1
            if b.get("cap_hit"):
                caps[b.get("stop_reason")] += 1
        out[m] = {"selected_stage": dict(stages), "B_stop_reason": dict(stops),
                  "B_cap_exits": dict(caps)}
    return out


def trace_table(index, design, run_dir: Path, roles) -> dict:
    agg = {}
    for m in HID:
        acc = defaultdict(list)
        status = defaultdict(int)
        for role in roles:
            for cid, *_ in V.expected_cases(design, role):
                t = trace_summary(run_dir, index.get(cid, {}).get(m))
                status[t["status"]] += 1
                if t["status"] == "complete":
                    for k in ("events", "proposed_cuts", "evaluated_cuts",
                              "new_serialized_admissible", "graph_rejections",
                              "cached_requests", "cap_blocked", "commits"):
                        acc[k].append(t[k])
                    acc["returned_cuts"].append(len(t["returned_cuts"]))
        agg[m] = {"trace_status": dict(status),
                  **{k: {"total": int(sum(v)), "mean": float(np.mean(v)), "max": int(max(v))}
                     for k, v in acc.items() if v}}
    return agg


def summarise(validation: dict, design: dict, run_dir: Path) -> dict:
    index = validation["_index"]
    rows = sorted((r for m in index.values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    pub = V.public(validation)
    strings = per_string(index, design, PRIMARY_ROLES + (CONTROL_ROLE,))
    units = per_unit(strings)
    cells = per_cell(strings, units)
    s = {"analysis_plan": ANALYSIS_PLAN_V3A,
         "validation": {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                                            "present_rows", "archives_checked",
                                            "distinct_archives_decoded")}
         | {k: pub[k][:200] for k in ("invalid", "incomplete", "censored", "duplicates",
                                       "unknown")}
         | {"trace_checks": validation.get("trace_checks", {}).get("trace_status_counts")},
         "primary": decision(validation, design),
         "cells": cells,
         "controls": [c for c in cells if c["cell"].startswith(CONTROL_ROLE + "|")],
         "changed_controls": [x for x in strings if x["role"] == CONTROL_ROLE
                              and x["sign"] not in ("tie", None)],
         "versus_portfolio": versus_portfolio(index, design),
         "hid_telemetry": hid_telemetry(rows),
         "resources": resources(rows),
         "status_counts": pub["status_counts"],
         "trace": trace_table(index, design, run_dir, PRIMARY_ROLES + (CONTROL_ROLE,)),
         "round_trips": {"decode_ok": sum(1 for r in rows if r["decode_ok"] is True),
                         "decode_failed": sum(1 for r in rows if r["decode_ok"] is False),
                         "with_archive": sum(1 for r in rows if r["archive_path"])}}
    s["censored_baselines"] = len(pub["censored"])
    s["portfolio_conclusion_blocked_by_censoring"] = bool(pub["censored"])
    return s, strings, units


# ---------------------------------------------------------------------------
# Development (inspected inputs; descriptive only)
# ---------------------------------------------------------------------------

def development_summary(records) -> dict:
    """Paired full-versus-refine4 counts and supplied-cut coverage, pair then cell."""
    out = {"label": "development on inspected retained inputs; descriptive; no efficacy gate"}
    for grp, pick in (("targets", True), ("controls", False)):
        rs = [r for r in records if r["target"] is pick]
        by_cell = defaultdict(lambda: defaultdict(list))
        signs = defaultdict(int)
        for r in rs:
            if r["full_bits"] is None or r["refine4_bits"] is None:
                signs["unavailable"] += 1
                continue
            v = (r["full_bits"] - r["refine4_bits"]) / r["n_bits"]
            signs[_sign(v)] += 1
            by_cell[r["cell"]][r["unit"]].append(v)
        cellm = {c: float(np.mean([np.mean(v) for v in u.values()])) for c, u in sorted(by_cell.items())}
        cell_signs = defaultdict(lambda: defaultdict(int))
        for r in rs:
            if r["full_bits"] is not None and r["refine4_bits"] is not None:
                cell_signs[r["cell"]][_sign(r["full_bits"] - r["refine4_bits"])] += 1
        g = {"strings": len(rs), "string_signs": dict(signs),
             "cell_mean_saving": cellm,
             "cell_string_signs": {c: dict(v) for c, v in sorted(cell_signs.items())},
             "equal_cell_mean_saving": float(np.mean(list(cellm.values()))) if cellm else None}
        for arm in ("full", "refine4"):
            ts = [r[f"{arm}_trace"] for r in rs]
            g[f"{arm}_trace_status"] = dict(_count(t["status"] for t in ts))
            ok = [t for t in ts if t["status"] == "complete"]
            g[f"{arm}_new_serialized_admissible_mean"] = (
                float(np.mean([t["new_serialized_admissible"] for t in ok])) if ok else None)
            g[f"{arm}_cap_stops"] = dict(_count(t["stop_reason"] for t in ok if t["cap_blocked"]))
            g[f"{arm}_stop_reasons"] = dict(_count(t["stop_reason"] for t in ok))
            if pick:
                g[f"{arm}_coverage"] = _coverage(rs, f"{arm}_trace")
        out[grp] = g
    return out


def _count(it) -> dict:
    c = defaultdict(int)
    for x in it:
        c[x] += 1
    return c


def _coverage(rs, key) -> dict:
    out = {}
    for kind in ("proposed", "evaluated", "returned"):
        num = den = 0
        cell = defaultdict(lambda: defaultdict(list))
        unavailable = 0
        for r in rs:
            cov = (r[key].get("supplied_coverage") or {}).get(kind)
            if not cov or not cov["denominator"]:
                unavailable += 1
                continue
            num += cov["numerator"]
            den += cov["denominator"]
            cell[r["cell"]][r["unit"]].append(cov["numerator"] / cov["denominator"])
        cm = [np.mean([np.mean(v) for v in u.values()]) for u in cell.values()]
        out[kind] = {"pooled_numerator": num, "pooled_denominator": den,
                     "pooled_proportion": num / den if den else None,
                     "pair_then_cell_mean_proportion": float(np.mean(cm)) if cm else None,
                     "strings_unavailable": unavailable}
    return out
