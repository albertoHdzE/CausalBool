"""D1 saved-result map and D2-D4 summaries from saved rows, job records and archives.

Weighting wherever an aggregate is shown: mean of base/ragged within a paired unit, mean
of units within a cell, then equal cell weights. No bit pooling, no intervals, no tests.
A cell aggregate exists only when every unit of the cell is complete; otherwise the
cell is reported as partial with its denominators.
"""
from __future__ import annotations

import json
from collections import Counter, defaultdict

from hierarchy.baselines import BASELINE_METHODS, select_best
from hierarchy.ledger import BUCKETS, field_buckets

from . import common as K
from .runner import record_path

PRIMARY_FAMILIES = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")


# ---------------------------------------------------------------------------
# Weighting
# ---------------------------------------------------------------------------

def unit_cell_means(values: dict[str, float | None], ids) -> dict:
    """values: case_id -> per-string value (None = unavailable). Returns per-cell means."""
    units: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for cid in ids:
        m = K.parse_case_id(cid)
        units[m["cell"]][m["unit"]].append(values.get(cid))
    out = {}
    for cell, us in sorted(units.items()):
        complete = {u: v for u, v in us.items() if len(v) == 2 and None not in v}
        um = [sum(v) / 2 for v in complete.values()]
        out[cell] = {"units": len(us), "complete_units": len(complete),
                     "strings": sum(len(v) for v in us.values()),
                     "available_strings": sum(1 for v in us.values() for x in v if x is not None),
                     "mean": sum(um) / len(um) if len(complete) == len(us) and um else None,
                     "partial_mean": sum(um) / len(um) if um else None}
    return out


def equal_cell_mean(cells: dict) -> float | None:
    ms = [c["mean"] for c in cells.values()]
    return None if not ms or None in ms else sum(ms) / len(ms)


def counts_by_cell(labels: dict[str, str], ids) -> dict:
    out: dict[str, Counter] = defaultdict(Counter)
    for cid in ids:
        out[K.parse_case_id(cid)["cell"]][str(labels.get(cid))] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


# ---------------------------------------------------------------------------
# D1
# ---------------------------------------------------------------------------

def d1_map(log=print) -> dict:
    study_methods = ("hid_legacy", "hid_first_local", "hid_consensus_local", "hid_dense_local",
                     "hid_global", "hid_full") + BASELINE_METHODS + ("baseline_best",)
    ids = K.design_case_ids()
    problems: list[str] = []
    jsonl = defaultdict(dict)
    for ln in (K.BASE_RUN / "cases.jsonl").read_text().splitlines():
        r = json.loads(ln)
        if r["method"] in jsonl[r["case_id"]]:
            problems.append(f"duplicate cases.jsonl row {r['case_id']}/{r['method']}")
        jsonl[r["case_id"]][r["method"]] = r
    saved_files = sorted(p.stem for p in (K.BASE_RUN / "rows").glob("*.json"))
    if saved_files != ids:
        problems.append("rows/ membership differs from the derived design")
    if sorted(jsonl) != ids:
        problems.append("cases.jsonl membership differs from the derived design")
    per: dict[str, dict] = {}
    nrows = 0
    for i, cid in enumerate(ids):
        rows = K.saved_rows(cid)
        nrows += len(rows)
        if set(rows) != set(study_methods) or len(rows) != 16:
            problems.append(f"{cid}: method membership {sorted(rows)}")
            continue
        for m, r in rows.items():
            if jsonl[cid].get(m) != r:
                problems.append(f"{cid}/{m}: rows/ and cases.jsonl disagree")
            if r["freeze_sha256"] != K.BASE_FREEZE:
                problems.append(f"{cid}/{m}: freeze hash")
        case = K.load_case(cid, rows)
        arcs = {m: K.saved_archive(rows[m]) for m in BASELINE_METHODS}
        best = select_best(arcs)
        pb = rows["baseline_best"]
        if best != pb["selected_method"] or 8 * len(arcs[best]) != pb["archive_bits"] or \
                rows[best]["archive_sha256"] != pb["archive_sha256"]:
            problems.append(f"{cid}: nine-way portfolio minimum not reproduced")
        n = len(case.bits)
        rec = {"n": n, "input_sha256": case.input_sha256,
               "bits": {m: rows[m]["archive_bits"] for m in study_methods},
               "status": {m: rows[m]["status"] for m in K.HID_ARMS + ("baseline_best",)},
               "portfolio_method": best, "buckets": {}}
        for m in K.HID_ARMS + ("baseline_best",):
            data = K.saved_archive(rows[m])
            b = field_buckets(data)
            if sum(b.values()) != 8 * len(data):
                problems.append(f"{cid}/{m}: buckets do not sum")
            rec["buckets"][m] = b
        tel = rows["hid_full"]["search_counters"] or {}
        st = tel.get("stages", {})
        rec["selected_stage"] = tel.get("selected_stage")
        rec["B"] = {k: st.get("B", {}).get(k) for k in ("stop_reason", "cap_hit",
                                                         "archive_bits", "segments")}
        rec["L_stop"] = st.get("L", {}).get("stop_reason")
        rec["stage_caps"] = sorted(s for s, v in st.items() if v.get("candidate_cap_hit"))
        per[cid] = rec
        if (i + 1) % 448 == 0:
            log(f"D1 {i + 1}/{len(ids)} cases read")
    return {"ids": ids, "rows_read": nrows, "problems": problems, "per_case": per}


def d1_tables(d1: dict) -> dict:
    ids, per = d1["ids"], d1["per_case"]

    def saving(a, b):
        return {c: (per[c]["bits"][b] - per[c]["bits"][a]) / per[c]["n"] for c in per}
    s_port, s_leg = saving("hid_full", "baseline_best"), saving("hid_full", "hid_legacy")
    cells_port, cells_leg = unit_cell_means(s_port, ids), unit_cell_means(s_leg, ids)
    prim_ids = [c for c in ids if c.startswith("confirmation-") and
                K.parse_case_id(c)["family"] in PRIMARY_FAMILIES]
    prim = unit_cell_means(s_port, prim_ids)
    cmp3 = {c: ("hid_full_shorter" if s_port[c] > 0 else "tie" if s_port[c] == 0
                else "portfolio_shorter") for c in per}
    buckets = {}
    for m in K.HID_ARMS + ("baseline_best",):
        buckets[m] = {b: {cell: v["mean"] for cell, v in unit_cell_means(
            {c: per[c]["buckets"][m][b] / per[c]["n"] for c in per}, ids).items()}
            for b in BUCKETS}
    return {
        "cells": sorted({K.parse_case_id(c)["cell"] for c in ids}),
        "saving_full_vs_portfolio": cells_port,
        "saving_full_vs_legacy": cells_leg,
        "full_vs_portfolio_string_counts": counts_by_cell(cmp3, ids),
        "portfolio_winner_counts": counts_by_cell(
            {c: per[c]["portfolio_method"] for c in per}, ids),
        "full_selected_stage_counts": counts_by_cell(
            {c: per[c]["selected_stage"] for c in per}, ids),
        "status_counts": {m: counts_by_cell({c: per[c]["status"][m] for c in per}, ids)
                          for m in K.HID_ARMS + ("baseline_best",)},
        "B_stop_reason_counts": counts_by_cell({c: per[c]["B"]["stop_reason"] for c in per}, ids),
        "B_cap_hit_counts": counts_by_cell({c: per[c]["B"]["cap_hit"] for c in per}, ids),
        "L_stop_reason_counts": counts_by_cell({c: per[c]["L_stop"] for c in per}, ids),
        "stage_candidate_cap_counts": counts_by_cell(
            {c: ",".join(per[c]["stage_caps"]) or "none" for c in per}, ids),
        "bucket_bits_per_input_bit": buckets,
        "accepted_primary_reproduction": {
            "label": "preservation check of the ACCEPTED primary point estimate, not a new "
                     "endpoint", "cells": len(prim), "estimate": equal_cell_mean(prim)},
    }


# ---------------------------------------------------------------------------
# Job records
# ---------------------------------------------------------------------------

def load_records(section: str, ids, kinds, run_dir=None) -> dict:
    out = {}
    for cid in ids:
        for k in kinds:
            p = record_path(run_dir or K.RUN_DIR, section, cid, k)
            out[(cid, k)] = json.loads(p.read_text()) if p.exists() else None
    return out


def evidence_status(r: dict | None, input_sha256: str | None = None) -> str:
    """Record status for reporting. ``ok``; an explicit UNAVAILABLE status (``missing``,
    ``not_run``, ``timeout``, ``rss_limit``, ``error``); or an INVALID status
    (``invalid_decode`` for a wrong decode, ``invalid_source`` for an input hash that
    differs from the saved case). Protocol §9: invalid evidence is never unavailable."""
    if r is None:
        return "missing"
    if input_sha256 is not None and r.get("input_sha256") != input_sha256:
        return "invalid_source"
    st = r.get("status", "missing")
    if st == "error" and str(r.get("exception") or "").startswith("wrong_decode"):
        return "invalid_decode"
    return st


def is_invalid(status: str) -> bool:
    return status.startswith("invalid_")


def resource_summary(recs: dict) -> dict:
    st = Counter((r or {}).get("status", "missing") for r in recs.values())
    walls = [r["worker_wall_ns"] / 1e9 for r in recs.values() if r and r.get("worker_wall_ns")]
    rss = [r["peak_rss_bytes"] for r in recs.values() if r and r.get("peak_rss_bytes")]
    return {"jobs": len(recs), "status": dict(st), "worker_wall_s_total": sum(walls),
            "worker_wall_s_max": max(walls, default=None),
            "peak_rss_bytes_max": max(rss, default=None)}


# ---------------------------------------------------------------------------
# D2
# ---------------------------------------------------------------------------

def d2_rows(recs: dict, ids) -> dict:
    out = {}
    for cid in ids:
        rows = K.saved_rows(cid)
        full = rows["hid_full"]
        B = (full["search_counters"] or {}).get("stages", {}).get("B", {})
        r0, r8 = recs[(cid, "B0")], recs[(cid, "B8")]
        n = full["n_bits"]
        row = {"n": n, "H": full["archive_bits"], "saved_B_bits": B.get("archive_bits"),
               "selected_stage": (full["search_counters"] or {}).get("selected_stage"),
               "B0_status": evidence_status(r0, full["input_sha256"]),
               "B8_status": evidence_status(r8, full["input_sha256"])}
        for name, r in (("B0", r0), ("B8", r8)):
            if row[f"{name}_status"] == "ok":
                row[f"{name}_bits"] = r["info"]["archive_bits"]
                row[f"{name}_stop"] = r["info"]["stop_reason"]
                row[f"{name}_cap_hit"] = r["info"]["cap_hit"]
                row[f"{name}_segments"] = r["info"]["segments"]
                row[f"{name}_root_trials"] = r["info"]["counts"]["root_trials"]
                row[f"{name}_wall_s"] = r["worker_wall_ns"] / 1e9
                row[f"{name}_rss"] = r["peak_rss_bytes"]
        if row["B0_status"] == "ok":
            from .kernels import DETERMINISTIC_B
            mism = [k for k in DETERMINISTIC_B
                    if json.loads(json.dumps(r0["info"][k])) != B.get(k)]
            row["B0_deterministic_mismatch"] = mism
            if row["selected_stage"] == "B":
                row["B0_bytes_equal_saved_final"] = \
                    r0["archives"]["output"]["sha256"] == full["archive_sha256"]
        if "B8_bits" in row:
            row["opportunity_per_input_bit"] = max(0, row["H"] - row["B8_bits"]) / n
            row["B8_shorter_than_H"] = row["B8_bits"] < row["H"]
            if "B0_bits" in row:
                row["B8_minus_B0_per_input_bit"] = (row["B8_bits"] - row["B0_bits"]) / n
        out[cid] = row
    return out


def d2_summary(rows: dict, targets, controls) -> dict:
    res = {}
    for name, ids in (("targets", targets), ("controls", controls)):
        res[name] = {
            "opportunity": unit_cell_means({c: rows[c].get("opportunity_per_input_bit")
                                            for c in ids}, ids),
            "B8_minus_B0": unit_cell_means({c: rows[c].get("B8_minus_B0_per_input_bit")
                                            for c in ids}, ids),
            "B8_shorter_than_H": counts_by_cell({c: rows[c].get("B8_shorter_than_H")
                                                 for c in ids}, ids),
            "B8_stop": counts_by_cell({c: rows[c].get("B8_stop") for c in ids}, ids),
            "B0_stop": counts_by_cell({c: rows[c].get("B0_stop") for c in ids}, ids),
            "witnesses": sorted(c for c in ids if rows[c].get("B8_shorter_than_H")),
            "B0_mismatch_cases": sorted(c for c in ids if rows[c].get("B0_deterministic_mismatch")),
            "B0_byte_identity": Counter(str(rows[c].get("B0_bytes_equal_saved_final"))
                                        for c in ids)}
        res[name]["B0_byte_identity"] = dict(res[name]["B0_byte_identity"])
        res[name]["equal_cell_mean_opportunity"] = equal_cell_mean(res[name]["opportunity"])
    return res


# ---------------------------------------------------------------------------
# D3
# ---------------------------------------------------------------------------

def segment_of(subset: tuple, c: int, n: int) -> tuple[int, int]:
    bounds = (0,) + tuple(subset) + (n,)
    for a, b in zip(bounds, bounds[1:]):
        if a < c < b:
            return a, b
    raise ValueError("cut already present")


def d3_graph(cuts, n: int, cost: dict, parent_min: int = 64, max_segments: int = 8) -> dict:
    """Reachability over supplied-cut subsets. ``cost``: subset tuple -> bits or None
    (graph limit). Edges add one cut; eligible when the split segment is >= parent_min,
    the children are positive (cuts are interior and distinct) and the result has at
    most max_segments segments; strict edges also need a strictly smaller archive."""
    cuts = tuple(sorted(cuts))
    edges = []
    for s in cost:
        for c in cuts:
            if c in s:
                continue
            t = tuple(sorted(s + (c,)))
            a, b = segment_of(s, c, n)
            elig = (b - a >= parent_min and len(t) + 1 <= max_segments
                    and cost[s] is not None and cost[t] is not None)
            delta = None if not elig else cost[t] - cost[s]
            edges.append({"from": list(s), "to": list(t), "cut": c, "parent": [a, b],
                          "eligible": elig, "delta_bits": delta,
                          "strict": bool(elig and delta < 0)})

    def reach(kind):
        seen, stack = {()}, [()]
        while stack:
            s = stack.pop()
            for e in edges:
                if tuple(e["from"]) == s and e[kind] and tuple(e["to"]) not in seen:
                    seen.add(tuple(e["to"]))
                    stack.append(tuple(e["to"]))
        return seen
    elig, strict = reach("eligible"), reach("strict")

    def best(space):
        cand = [(cost[s], len(s), s) for s in space if cost.get(s) is not None]
        return min(cand) if cand else None
    b_all, b_el, b_st = best(cost), best(elig), best(strict)
    out = {"subsets": len(cost), "eligibility_reachable": len(elig),
           "strict_reachable": len(strict),
           "cheapest_all": None if b_all is None else {"subset": list(b_all[2]), "bits": b_all[0]},
           "cheapest_eligible": None if b_el is None else {"subset": list(b_el[2]),
                                                             "bits": b_el[0]},
           "cheapest_strict": None if b_st is None else {"subset": list(b_st[2]),
                                                           "bits": b_st[0]},
           "edges": edges}
    out["restricted_path_barrier"] = bool(b_el and b_st and b_el[0] < b_st[0])
    out["eligibility_obstruction"] = bool(b_all and b_el and b_all[0] < b_el[0])
    if out["restricted_path_barrier"]:
        # Frontier edges leaving the strictly reachable set whose target can still reach,
        # by eligible edges, a subset cheaper than the best strictly reachable one.
        good = {s for s in elig if cost[s] is not None and cost[s] < b_st[0]}
        can = set(good)
        changed = True
        while changed:
            changed = False
            for e in edges:
                if e["eligible"] and tuple(e["to"]) in can and tuple(e["from"]) not in can:
                    can.add(tuple(e["from"]))
                    changed = True
        front = [e for e in edges if tuple(e["from"]) in strict and e["eligible"]
                 and not e["strict"] and tuple(e["to"]) in can]
        dmin = min(e["delta_bits"] for e in front)
        out["barrier"] = {"frontier_edges": len(front),
                          "equality_edges": sum(1 for e in front if e["delta_bits"] == 0),
                          "positive_edges": sum(1 for e in front if e["delta_bits"] > 0),
                          "min_delta_bits": dmin,
                          "kind": "equality" if dmin == 0 else "positive_cost_step"}
    return out


def d3_rows(recs: dict, ids, d2: dict, refs: dict) -> dict:
    out = {}
    for cid in ids:
        r = recs[(cid, "D3")]
        ref = refs[cid]
        sha_in = K.saved_rows(cid)["hid_full"]["input_sha256"]
        row = {"status": evidence_status(r, sha_in), "n": ref["n_bits"],
               "supplied_cuts": ref["cuts"], "H": d2[cid]["H"],
               "B0": d2[cid].get("B0_bits"), "B8": d2[cid].get("B8_bits")}
        if row["status"] == "ok":
            info = r["info"]
            cost = {tuple(s["subset"]): s.get("archive_bits") for s in info["subsets"]}
            g = d3_graph(info["cuts"], ref["n_bits"], cost)
            full = cost[tuple(sorted(ref["cuts"]))]
            fullrec = next(s for s in info["subsets"] if s["subset"] == sorted(ref["cuts"]))
            row.update({k: v for k, v in g.items() if k != "edges"})
            row.update(empty_subset_bits=cost[()], full_subset_bits=full,
                       reference_reproduced=fullrec.get("archive_sha256") ==
                       ref["reference_sha256"] and full == ref["reference_bits"],
                       graph_limited=sum(1 for v in cost.values() if v is None),
                       charges=info["charges"], edges=g["edges"])
        out[cid] = row
    return out


# ---------------------------------------------------------------------------
# D4
# ---------------------------------------------------------------------------

def d4_rows(recs: dict, ids) -> dict:
    out = {}
    for cid in ids:
        rows = K.saved_rows(cid)
        r = recs[(cid, "D4")]
        H, P = rows["hid_full"]["archive_bits"], rows["baseline_best"]["archive_bits"]
        n = rows["hid_full"]["n_bits"]
        for m in ("period", "pair_grammar"):
            C = rows[m]["archive_bits"]
            row = {"case_id": cid, "method": m, "n": n, "H": H, "C": C, "portfolio": P,
                   "portfolio_method": rows["baseline_best"]["selected_method"],
                   "job_status": evidence_status(r, rows["hid_full"]["input_sha256"])}
            if row["job_status"] == "ok":
                info = r["info"][m]
                row["status"] = info["status"]
                row["rule_count"], row["dag_depth"] = info["rule_count"], info["dag_depth"]
                if info["status"] == "ok":
                    T = info["translated_bits"]
                    row.update(T=T, T_raw_clipped=info["raw_clipped_bits"],
                               H_minus_T=H - T, T_minus_C=T - C, H_minus_C=H - C,
                               identity_exact=(H - C) == (H - T) + (T - C),
                               T_minus_portfolio=T - P,
                               # equal length is not an equal proposal: compare the bytes
                               T_bytes_equal_H=r["archives"][m]["sha256"] ==
                               rows["hid_full"]["archive_sha256"],
                               translated_buckets=info["translated_buckets"],
                               baseline_buckets=info["baseline_buckets"])
                    if m == "period":
                        row["period"], row["shape"] = info["period"], info["shape"]
            else:
                row["status"] = row["job_status"]
            out[f"{cid}|{m}"] = row
    return out


def d4_summary(rows: dict, ids) -> dict:
    res = {}
    for m in ("period", "pair_grammar"):
        sub = {k.split("|")[0]: v for k, v in rows.items() if v["method"] == m}
        res[m] = {
            "status": counts_by_cell({c: sub[c]["status"] for c in ids}, ids),
            "H_minus_T": unit_cell_means({c: sub[c]["H_minus_T"] / sub[c]["n"]
                                          if "T" in sub[c] else None for c in ids}, ids),
            "T_minus_C": unit_cell_means({c: sub[c]["T_minus_C"] / sub[c]["n"]
                                          if "T" in sub[c] else None for c in ids}, ids),
            "H_minus_C": unit_cell_means({c: sub[c]["H_minus_C"] / sub[c]["n"]
                                          if "T" in sub[c] else None for c in ids}, ids),
            "T_shorter_than_H": counts_by_cell({c: sub[c].get("H_minus_T", 0) > 0
                                                if "T" in sub[c] else "unavailable"
                                                for c in ids}, ids),
            "T_longer_than_C": counts_by_cell({c: sub[c].get("T_minus_C", 0) > 0
                                               if "T" in sub[c] else "unavailable"
                                               for c in ids}, ids),
            "T_shorter_than_portfolio": counts_by_cell(
                {c: sub[c].get("T_minus_portfolio", 0) < 0 if "T" in sub[c]
                 else "unavailable" for c in ids}, ids),
            "identity_failures": sorted(c for c in ids if "T" in sub[c]
                                        and not sub[c]["identity_exact"]),
            "missed_witnesses": sorted(c for c in ids if sub[c].get("H_minus_T", 0) > 0),
            "penalty_cases": sum(1 for c in ids if sub[c].get("T_minus_C", 0) > 0),
            "admissible": sum(1 for c in ids if "T" in sub[c])}
    return res


# ---------------------------------------------------------------------------
# Evidence flags and decision quantities
# ---------------------------------------------------------------------------

def _quantiles(xs) -> dict | None:
    xs = sorted(xs)
    if not xs:
        return None
    k = len(xs)
    med = xs[k // 2] if k % 2 else (xs[k // 2 - 1] + xs[k // 2]) / 2
    return {"n": k, "min": xs[0], "median": med, "max": xs[-1]}


def _evidence(d2: dict, d3: dict, d4: dict, s2: dict, s4: dict, ids2) -> dict:
    """Availability and validity of every intended record, before any success-only number.
    Unavailable records stay in their denominators; invalid evidence is listed by reason."""
    st2 = Counter(d2[c][f"{k}_status"] for c in ids2 for k in ("B0", "B8"))
    st3 = Counter(r["status"] for r in d3.values())
    st4 = Counter(r["job_status"] for r in d4.values())
    conv = Counter(r["status"] for r in d4.values())
    invalid_records = {
        "D2": sorted(f"{c}.{k}:{d2[c][f'{k}_status']}" for c in ids2 for k in ("B0", "B8")
                     if is_invalid(d2[c][f"{k}_status"])),
        "D3": sorted(f"{c}:{r['status']}" for c, r in d3.items() if is_invalid(r["status"])),
        "D4": sorted({f"{r['case_id']}:{r['job_status']}" for r in d4.values()
                      if is_invalid(r["job_status"])})}
    invalid = {
        "records": invalid_records,
        "B0_deterministic_mismatch": sorted(s2["targets"]["B0_mismatch_cases"] +
                                            s2["controls"]["B0_mismatch_cases"]),
        "reference_not_reproduced": sorted(c for c, r in d3.items()
                                           if r["status"] == "ok" and not r["reference_reproduced"]),
        "identity_failures": {m: s4[m]["identity_failures"] for m in s4}}
    invalid["any"] = bool(any(invalid_records.values()) or invalid["B0_deterministic_mismatch"]
                          or invalid["reference_not_reproduced"]
                          or any(invalid["identity_failures"].values()))
    unavailable = {s: {k: v for k, v in sorted(c.items()) if k != "ok" and not is_invalid(k)}
                   for s, c in (("D2", st2), ("D3", st3), ("D4_jobs", st4))}
    unavailable["D4_conversions"] = {k: v for k, v in sorted(conv.items())
                                     if k != "ok" and not is_invalid(k)}
    return {"intended": {"D2_jobs": 2 * len(ids2), "D3_jobs": len(d3),
                         "D4_jobs": len({r["case_id"] for r in d4.values()}),
                         "D4_conversion_records": len(d4)},
            "status": {"D2": dict(sorted(st2.items())), "D3": dict(sorted(st3.items())),
                       "D4_jobs": dict(sorted(st4.items())),
                       "D4_conversions": dict(sorted(conv.items()))},
            "unavailable": unavailable, "invalid": invalid,
            "complete": not any(unavailable.values()) and not any(invalid_records.values())}


def decision_quantities(d1: dict, d2: dict, s2: dict, d3: dict, d4: dict, s4: dict,
                        res: dict, targets, controls, ids4, near_bits: int = 8,
                        b0_cuts: dict | None = None) -> dict:
    """Flags and decision quantities over AVAILABLE records only, each with the intended
    and available denominators. Never dereferences a field an unavailable record lacks;
    never turns an unavailable value into zero. ``b0_cuts``: case -> cut tuple of the
    archive B0 RETURNED (default: read from the saved B0 records of this run)."""
    cell = lambda c: K.parse_case_id(c)["cell"]                     # noqa: E731
    P = {c: d1[c]["bits"]["baseline_best"] for c in d1}
    ids2 = sorted(targets + controls)
    flags = {"evidence": _evidence(d2, d3, d4, s2, s4, ids2)}
    ok2 = lambda c, k: d2[c][f"{k}_status"] == "ok"                # noqa: E731
    # D2
    wit = [{"case_id": c, "H": d2[c]["H"], "B0": d2[c].get("B0_bits"), "B8": d2[c]["B8_bits"],
            "n": d2[c]["n"], "portfolio": P[c], "B0_stop": d2[c].get("B0_stop"),
            "B8_stop": d2[c]["B8_stop"]} for c in s2["targets"]["witnesses"]]
    b0cap = sorted(c for c in targets + controls if d2[c].get("B0_cap_hit"))
    comparable = [c for c in controls if ok2(c, "B0") and ok2(c, "B8")]
    flags["budget_opportunity_observed"] = {
        "value": bool(wit), "witnesses": wit,
        "scope": "the specific B0 -> B8 cap increase on these strings; not a statement "
                 "about resource limits under other searches",
        "denominator": {"target_strings": len(targets), "completed_B8_targets":
                        sum(1 for c in targets if ok2(c, "B8")),
                        "completed_B0_and_B8_targets":
                        sum(1 for c in targets if ok2(c, "B0") and ok2(c, "B8"))},
        "prevalence_by_cell": s2["targets"]["B8_shorter_than_H"],
        "control_behaviour": {"B8_shorter_than_H": s2["controls"]["B8_shorter_than_H"],
                              "B8_differs_from_B0": sum(1 for c in comparable
                                                        if d2[c]["B8_bits"] != d2[c]["B0_bits"]),
                              "comparable_controls": len(comparable),
                              "control_strings": len(controls)},
        "B0_cap_hit_strings": b0cap,
        "effect_equal_cell_mean_opportunity_per_input_bit":
            s2["targets"]["equal_cell_mean_opportunity"],
        "partial_cells": sorted(k for k, v in s2["targets"]["opportunity"].items()
                                if v["mean"] is None),
        "resources": res["D2"]}
    # D3
    by: dict[str, Counter] = defaultdict(Counter)
    kinds = Counter()
    gaps = defaultdict(list)
    located = Counter()
    near_key = f"supplied_cut_with_returned_B0_cut_within_{near_bits}_bits"
    far_key = f"supplied_cut_without_returned_B0_cut_within_{near_bits}_bits"
    for c, r in d3.items():
        k = by[cell(c)]
        k["strings"] += 1
        mins = [r.get(x) for x in ("cheapest_all", "cheapest_eligible", "cheapest_strict")]
        if r["status"] != "ok" or None in mins:
            k[r["status"] if is_invalid(r["status"]) else
              "unavailable_" + (r["status"] if r["status"] != "ok" else "no_priced_minimum")] += 1
            continue
        k["available"] += 1
        al, el, st = (m["bits"] for m in mins)
        k["reference_reproduced"] += r["reference_reproduced"]
        k["restricted_path_barrier"] += r["restricted_path_barrier"]
        k["eligibility_obstruction"] += r["eligibility_obstruction"]
        k["cheapest_all_lt_H"] += al < r["H"]
        k["cheapest_strict_lt_H"] += st < r["H"]
        k["cheapest_all_lt_portfolio"] += al < P[c]
        k["cheapest_strict_lt_portfolio"] += st < P[c]
        k["H_gt_portfolio"] += r["H"] > P[c]
        k["H_gt_portfolio_and_cheapest_all_lt_H"] += r["H"] > P[c] and al < r["H"]
        if r["B0"] is None:
            k["B0_unavailable"] += 1
        else:
            k["cheapest_strict_lt_B0"] += st < r["B0"]
        if r["restricted_path_barrier"]:
            kinds[r["barrier"]["kind"]] += 1
        gaps[cell(c)].append((r["H"] - al) / r["n"])
        if st < r["H"]:
            if b0_cuts is None:
                p = record_path(K.RUN_DIR, "D2", c, "B0")
                cuts = json.loads(p.read_text())["info"]["cuts"] if ok2(c, "B0") else None
            else:
                cuts = b0_cuts.get(c)
            subset = r["cheapest_strict"]["subset"]
            if cuts is None:
                located["supplied_cuts_returned_B0_cuts_unavailable"] += len(subset)
                continue
            located["strings"] += 1
            for s in subset:
                near = any(abs(s - x) <= near_bits for x in cuts)
                located[near_key] += near
                located[far_key] += not near
    flags["restricted_path_barrier_observed"] = {
        "value": sum(v["restricted_path_barrier"] for v in by.values()) > 0,
        "space": "D3 supplied-cut subsets only (truth-assisted, B0 leaf heuristic)",
        "barrier_kinds": dict(kinds),
        "eligibility_obstructions": sum(v["eligibility_obstruction"] for v in by.values()),
        "by_cell": {k: dict(v) for k, v in sorted(by.items())},
        "effect_H_minus_cheapest_all_per_input_bit_by_cell":
            {k: _quantiles(v) for k, v in sorted(gaps.items())},
        "descriptive_returned_B0_cut_proximity": dict(
            located, scope="post hoc, descriptive. Each supplied cut of the cheapest strictly "
            "reachable subset, in strings where that subset is shorter than H, against the cut "
            "tuple of the archive B0 RETURNED (job record info.cuts). Returned cuts are not the "
            "cuts B proposed or evaluated: a cut may have been proposed and rejected, so this "
            "measures proximity to returned cuts, not proposal coverage."),
        "denominator": {"strings": len(d3),
                        "available_strings": sum(v["available"] for v in by.values()),
                        "subsets": sum(r["subsets"] for r in d3.values() if "subsets" in r)},
        "resources": res["D3"]}
    # D4
    loss: dict[str, Counter] = defaultdict(Counter)
    pen_loss = defaultdict(list)
    absolute = {"period": [], "pair_grammar": []}
    for r in d4.values():
        if "T" in r:
            absolute[r["method"]].append(r["T_minus_C"])
        if r["method"] != r["portfolio_method"]:
            continue
        k = loss[cell(r["case_id"])]
        k[f"portfolio_winner_{r['method']}"] += 1
        if r["H"] > r["portfolio"]:
            k["hid_loses"] += 1
            k["hid_loses_translation_unavailable"] += "T" not in r
            if "T" not in r:
                continue
            eq = r["H"] == r["T"]
            k["hid_loses_and_H_eq_T"] += eq
            k["hid_loses_and_H_eq_T_identical_bytes"] += eq and r["T_bytes_equal_H"]
            k["hid_loses_and_H_eq_T_different_bytes"] += eq and not r["T_bytes_equal_H"]
            k["hid_loses_and_H_lt_T"] += r["H"] < r["T"]
            pen_loss[cell(r["case_id"])].append(r["T_minus_C"] / r["n"])
    unavail4 = {m: len(ids4) - s4[m]["admissible"] for m in s4}
    missed = {m: s4[m]["missed_witnesses"] for m in s4}
    flags["missed_baseline_structure_observed"] = {
        "value": any(missed.values()), "witnesses": missed,
        "denominator": {"conversion_records": len(d4),
                        "admissible": {m: s4[m]["admissible"] for m in s4},
                        "unavailable": unavail4},
        "prevalence_by_cell": {m: s4[m]["T_shorter_than_H"] for m in s4},
        "effect_H_minus_T_per_input_bit_by_cell": {m: {k: v["mean"] for k, v in
                                                       s4[m]["H_minus_T"].items()} for m in s4},
        "resources": res["D4"]}
    flags["proposal_representation_penalty_observed"] = {
        "value": any(s4[m]["penalty_cases"] for m in s4),
        "qualification": "proposal-specific: the cost of THIS translation of THIS saved "
                         "proposal under the stated factory/pruning rules",
        "penalty_records": {m: s4[m]["penalty_cases"] for m in s4},
        "denominator": {"conversion_records": len(d4),
                        "admissible": {m: s4[m]["admissible"] for m in s4},
                        "unavailable": unavail4},
        "prevalence_by_cell": {m: s4[m]["T_longer_than_C"] for m in s4},
        "effect_T_minus_C_per_input_bit_by_cell": {m: {k: v["mean"] for k, v in
                                                       s4[m]["T_minus_C"].items()} for m in s4},
        "absolute_T_minus_C_bits": {m: _quantiles(v) for m, v in absolute.items()},
        "identity_failures": {m: s4[m]["identity_failures"] for m in s4},
        "resources": res["D4"]}
    flags["d4_loss_decomposition_where_portfolio_winner_was_translated"] = {
        "by_cell": {k: dict(v) for k, v in sorted(loss.items())},
        "T_minus_C_per_input_bit_among_losses": {k: _quantiles(v)
                                                 for k, v in sorted(pen_loss.items())},
        "reading": "H == T compares LENGTHS. Where it holds, H - C = T - C exactly, so the "
                   "loss to that baseline equals this translation's penalty; it does not mean "
                   "the search reached the same proposal (byte identity is counted separately) "
                   "and it is not a bound over HID descriptions. A translation that is "
                   "unavailable is counted as such, never as H == T or as a zero penalty."}
    return flags
