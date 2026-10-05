"""Status-aware tables, width-by-level gap map, explanations, REPORT and DECISION.

Reads saved rows, references, traces and archive bytes only; runs no encoder.
Descriptive only (BENCHMARK section 3): saving(A, B) = (bits(B) - bits(A)) / len(x),
positive when A is shorter; averaged base/ragged within replicate, replicates within
the family-length cell, then the 24 cells equally. No interval, test or bootstrap.
"""
from __future__ import annotations

import csv
import io
import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from hierarchy import codes as C
from hierarchy.ledger import archive_ledger, explain_model

from .runner import AUG_ARMS, RUN_DIR, VALID_AUG, case_specs

REFS = ("pair_grammar", "portfolio")
CONTRASTS = (("A1", "A0"), ("A2", "A1"), ("A3", "A2"), ("A2", "A0"), ("A3", "A0"),
             ("A1", "pair_grammar"), ("A2", "pair_grammar"), ("A3", "pair_grammar"),
             ("A1", "portfolio"), ("A2", "portfolio"), ("A3", "portfolio"),
             ("A0", "pair_grammar"), ("A0", "portfolio"))
STATES = ("INVALID", "INCOMPLETE", "VALID_COMPLETE")


def load_json(p: Path):
    return json.loads(p.read_text())


def load_rows(d: Path, specs) -> dict:
    """{(case_id, arm): row or None}; corrupt rows are recorded as 'corrupt_row'."""
    out = {}
    for s in specs:
        for arm in ("A0",) + AUG_ARMS:
            p = d / "rows" / f"{s['case_id']}.{arm}.json"
            if not p.is_file():
                out[(s["case_id"], arm)] = None
                continue
            try:
                out[(s["case_id"], arm)] = load_json(p)
            except ValueError:
                out[(s["case_id"], arm)] = {"status": "corrupt_row", "validity": "invalid"}
    return out


def load_references(d: Path) -> dict:
    p = d / "references.jsonl"
    if not p.is_file():
        return {}
    return {r["case_id"]: r for r in (json.loads(x) for x in p.read_text().splitlines() if x.strip())}


def evidence_state(specs, rows: dict, refs: dict) -> dict:
    """INVALID > INCOMPLETE > VALID_COMPLETE (contract ``state_precedence``)."""
    invalid, incomplete = [], []
    for s in specs:
        cid = s["case_id"]
        r = refs.get(cid)
        if r is None:
            incomplete.append(f"{cid}: references missing")
        elif r["problems"]:
            invalid.append(f"{cid}: reference problems {r['problems']}")
        a0 = rows.get((cid, "A0"))
        if a0 is None:
            incomplete.append(f"{cid}.A0: missing")
        elif a0.get("status") == "corrupt_row":
            invalid.append(f"{cid}.A0: corrupt row")
        elif a0.get("status") != "ok" or not a0.get("decode_ok"):
            invalid.append(f"{cid}.A0: status {a0.get('status')}")
        elif not a0.get("reproduction", {}).get("reproduced"):
            invalid.append(f"{cid}.A0: not reproduced {a0['reproduction']['mismatched_fields']}")
        for arm in AUG_ARMS:
            row = rows.get((cid, arm))
            if row is None:
                incomplete.append(f"{cid}.{arm}: missing")
            elif row.get("validity") == "invalid":
                invalid.append(f"{cid}.{arm}: {row.get('status')}")
            elif row.get("validity") == "unavailable" or row.get("status") not in VALID_AUG:
                incomplete.append(f"{cid}.{arm}: {row.get('status')}")
    state = "INVALID" if invalid else ("INCOMPLETE" if incomplete else "VALID_COMPLETE")
    return {"state": state, "invalid": invalid, "incomplete": incomplete}


def bits_table(specs, rows: dict, refs: dict) -> dict:
    """{case_id: {arm/reference: archive bits or None}} -- None is unavailable, never 0."""
    out = {}
    for s in specs:
        cid = s["case_id"]
        rec = {}
        for arm in ("A0",) + AUG_ARMS:
            row = rows.get((cid, arm))
            ok = row is not None and (row.get("status") == "ok" if arm == "A0"
                                      else row.get("status") in VALID_AUG)
            rec[arm] = row["archive_bits"] if ok else None
        r = refs.get(cid)
        rec["pair_grammar"] = r["methods"]["pair_grammar"]["archive_bits"] if r else None
        rec["portfolio"] = r["portfolio"]["archive_bits"] if r else None
        out[cid] = rec
    return out


def saving(a, b, n):
    return None if a is None or b is None or not n else (b - a) / n


def aggregate(specs, per_string: dict) -> dict:
    """Base/ragged -> replicate -> cell -> equal-cell mean. Any missing value makes every
    level that contains it unavailable (no reduced-population aggregate)."""
    pairs, cells = defaultdict(list), defaultdict(list)
    for s in specs:
        pairs[(s["family"], s["base_length"], s["replicate"])].append(per_string[s["case_id"]])
    pair_val = {k: (None if any(v is None for v in vs) else sum(vs) / len(vs))
                for k, vs in pairs.items()}
    for (f, bl, rep), v in pair_val.items():
        cells[(f, bl)].append(v)
    cell_val = {k: (None if any(v is None for v in vs) else sum(vs) / len(vs))
                for k, vs in cells.items()}
    vals = list(cell_val.values())
    agg = None if any(v is None for v in vals) or not vals else sum(vals) / len(vals)
    return {"pairs": {f"{k[0]}-{k[1]}-{k[2]}": v for k, v in sorted(pair_val.items())},
            "cells": {f"{k[0]}-{k[1]}": v for k, v in sorted(cell_val.items())},
            "aggregate": agg, "n_pairs": len(pair_val), "n_cells": len(cell_val)}


def sign_counts(values) -> dict:
    vals = [v for v in values if v is not None]
    return {"better": sum(v > 0 for v in vals), "tie": sum(v == 0 for v in vals),
            "worse": sum(v < 0 for v in vals), "available": len(vals),
            "unavailable": sum(v is None for v in values)}


def contrasts(specs, bits: dict) -> dict:
    out = {}
    n = {s["case_id"]: s["n_bits"] for s in specs}
    for a, b in CONTRASTS:
        per = {cid: saving(bits[cid][a], bits[cid][b], n[cid]) for cid in bits}
        ag = aggregate(specs, per)
        out[f"{a}_vs_{b}"] = {"A": a, "B": b, "per_string": per, "pairs": ag["pairs"],
                              "cells": ag["cells"], "aggregate": ag["aggregate"],
                              "strings": sign_counts(list(per.values())),
                              "cells_sign": sign_counts(list(ag["cells"].values())),
                              "denominators": {"strings": len(per), "pairs": ag["n_pairs"],
                                               "cells": ag["n_cells"]}}
    return out


def recommendation(state: str, bits: dict) -> dict:
    if state != "VALID_COMPLETE":
        return {"label": None, "reason": f"evidence state {state}: recommendation logic disabled"}
    a3_beats_a0 = [c for c, r in bits.items() if r["A3"] < r["A0"]]
    a3_beats_a2 = [c for c, r in bits.items() if r["A3"] < r["A2"]]
    a2_beats_a0 = [c for c, r in bits.items() if r["A2"] < r["A0"]]
    if not a3_beats_a0:
        label = "NO_RETAINED_GAIN"
    elif not a3_beats_a2:
        label = "NO_ADDED_LEVEL_GAIN"
    else:
        label = "LEVEL_GAIN_OBSERVED"
    return {"label": label, "a3_beats_a0_strings": len(a3_beats_a0),
            "a3_beats_a2_strings": len(a3_beats_a2), "a2_beats_a0_strings": len(a2_beats_a0),
            "a3_beats_a0_cases": a3_beats_a0, "a3_beats_a2_cases": a3_beats_a2,
            "a2_beats_a0_cases": a2_beats_a0,
            "meaning": "exploratory label on 96 exposed strings; not statistical superiority, "
                       "generalization, causality or adoption"}


# ---------------------------------------------------------------------------
# Work, runtime, selections, rule-kind cost
# ---------------------------------------------------------------------------

def _q(vals):
    vals = sorted(v for v in vals if v is not None)
    if not vals:
        return {"n": 0, "min": None, "median": None, "mean": None, "max": None, "sum": None}
    return {"n": len(vals), "min": vals[0], "median": statistics.median(vals),
            "mean": sum(vals) / len(vals), "max": vals[-1], "sum": sum(vals)}


def workload(specs, rows: dict, d: Path) -> dict:
    out = {}
    for arm in AUG_ARMS:
        st = Counter()
        views, props, sel = Counter(), Counter(), Counter()
        counters = Counter()
        stop = Counter()
        for s in specs:
            row = rows.get((s["case_id"], arm))
            st[row["status"] if row else "missing"] += 1
            if not row:
                continue
            sel_src = (row.get("selected") or {}).get("source")
            if sel_src in ("augmentation", "checkpoint"):
                sv = row["selected"]
                sel[f"{sv['proposal']}|w{sv['width']}|o{sv['origin']}|l{sv['level']}"] += 1
            if row.get("stop_reason"):
                stop[row["stop_reason"]] += 1
            for k, v in (row.get("counters") or {}).items():
                if isinstance(v, int):
                    counters[k] += v
            if row.get("trace_path"):
                tr = load_json(d / row["trace_path"])
                for v in tr["views"]:
                    views[v["status"]] += 1
                    for p in v["proposals"]:
                        props[f"{p['proposal']}:{p['status']}"] += 1
        out[arm] = {"job_status": dict(st), "view_status": dict(views),
                    "proposal_status": dict(sorted(props.items())), "counters": dict(counters),
                    "stop_reasons": dict(stop),
                    "augmentation_selections": sum(sel.values()),
                    "selections_by_view_proposal": dict(sorted(sel.items()))}
    return out


def runtime(specs, rows: dict) -> dict:
    a0 = [rows.get((s["case_id"], "A0")) for s in specs]
    out = {"physical": {"A0_worker_wall_s": _q([r["worker_wall_ns"] / 1e9 for r in a0 if r]),
                        "A0_peak_rss_bytes": _q([r["peak_rss_bytes"] for r in a0 if r])},
           "attributed_deployment": {}}
    for arm in AUG_ARMS:
        rs = [rows.get((s["case_id"], arm)) for s in specs]
        rs = [r for r in rs if r and r.get("worker_wall_ns") is not None]
        out["physical"][f"{arm}_worker_wall_s"] = _q([r["worker_wall_ns"] / 1e9 for r in rs])
        out["physical"][f"{arm}_peak_rss_bytes"] = _q([r["peak_rss_bytes"] for r in rs])
        out["attributed_deployment"][arm] = {
            "definition": "A0 worker wall + augmentation worker wall (the reused A0 run is "
                          "charged in full to every composite)",
            "deployment_wall_s": _q([r["deployment_wall_ns"] / 1e9 for r in rs]),
            "deployment_peak_rss_bytes": _q([r["deployment_peak_rss_bytes"] for r in rs]),
            "encode_wall_s_in_child": _q([(r.get("encode_wall_ns") or 0) / 1e9 for r in rs
                                          if r.get("encode_wall_ns") is not None])}
    tot = sum(r["worker_wall_ns"] for r in a0 if r) / 1e9
    for arm in AUG_ARMS:
        tot += sum((rows.get((s["case_id"], arm)) or {}).get("worker_wall_ns") or 0
                   for s in specs) / 1e9
    out["physical"]["all_new_jobs_worker_wall_s_sum"] = tot
    out["note"] = ("Physical totals count each executed job once. Attributed deployment cost "
                   "charges A0 to every composite. Imported baseline timings are from another "
                   "run and are not compared.")
    return out


def rule_kind_cost(d: Path, rows: dict, specs) -> dict:
    out = {}
    for arm in ("A0",) + AUG_ARMS:
        tot = Counter()
        for s in specs:
            row = rows.get((s["case_id"], arm))
            if not row or not row.get("archive_path"):
                continue
            data = (d / row["archive_path"]).read_bytes()
            led = archive_ledger(data)
            kinds = {}
            if led["model"] is not None:
                kinds = {f"rule{i}": C.OP_NAMES[r.op] for i, r in enumerate(led["model"].rules)}
            for f in led["fields"]:
                own = f["owner"]
                key = kinds.get(own, own if not own.startswith("rule") else "rule?")
                if led["codec_id"] != C.CODEC_HID and own not in ("envelope",):
                    key = f"payload:{led['codec']}"
                tot[key] += 8 * f["bytes"]
        out[arm] = dict(sorted(tot.items()))
    return out


# ---------------------------------------------------------------------------
# Gap map and per-view table (from A3 traces; A1/A2 views are their nested subsets)
# ---------------------------------------------------------------------------

VIEW_FIELDS = ("case_id", "family", "base_length", "ragged", "n_bits", "arm", "level", "width",
               "origin", "span", "m", "k", "k_over_m", "status", "prefix_bits", "suffix_bits",
               "weak_support_fraction", "pooled_modal_gap", "pooled_irregular_fraction",
               "symbols_reused", "symbols_singleton", "dict_entries", "dict_proper_repeat",
               "best_bits", "a0_bits", "minus_a0_bits", "minus_a0_per_bit",
               "vs_previous_level_bits", "gap_status", "G0", "G1", "G2", "G3", "selected_here")


def view_rows(d: Path, specs, rows: dict, arm: str = "A3") -> list[dict]:
    out = []
    for s in specs:
        row = rows.get((s["case_id"], arm))
        if not row or not row.get("trace_path"):
            continue
        tr = load_json(d / row["trace_path"])
        sel = row.get("selected") or {}
        for v in tr["views"]:
            dg = v["description_gap"] or {}
            ev = v["status"] == "EVALUATED"
            r = {"case_id": s["case_id"], "family": s["family"], "base_length": s["base_length"],
                 "ragged": s["ragged"], "n_bits": s["n_bits"], "arm": arm,
                 **{k: v[k] for k in ("level", "width", "origin", "span", "m", "k", "k_over_m",
                                      "status", "prefix_bits", "suffix_bits")},
                 "weak_support_fraction": v["weak_support"]["fraction_of_n"] if ev else None,
                 "pooled_modal_gap": v["occurrence"]["pooled_modal_gap"] if ev else None,
                 "pooled_irregular_fraction": v["occurrence"]["pooled_irregular_fraction"] if ev else None,
                 "symbols_reused": v.get("symbols_reused"), "symbols_singleton": v.get("symbols_singleton"),
                 "dict_entries": len(v["dictionary_content"]) if ev else None,
                 "dict_proper_repeat": sum(c["proper_repeat"] for c in v["dictionary_content"]) if ev else None,
                 "best_bits": dg.get("best_bits"), "a0_bits": row["a0_archive_bits"],
                 "minus_a0_bits": dg.get("minus_a0_bits"),
                 "minus_a0_per_bit": (dg["minus_a0_bits"] / s["n_bits"]
                                      if dg.get("minus_a0_bits") is not None else None),
                 "vs_previous_level_bits": dg.get("vs_previous_level_bits"),
                 "gap_status": dg.get("status"),
                 "selected_here": sel.get("source") == "augmentation" and sel.get("view_index") == v["view_index"]}
            for p in v["proposals"]:
                r[p["proposal"]] = p["status"] if p["archive_bits"] is None else f"{p['status']}:{p['archive_bits']}"
            out.append(r)
    return out


def gap_map(vrows: list[dict]) -> list[dict]:
    cells = defaultdict(list)
    for r in vrows:
        cells[(r["width"], r["level"])].append(r)
    out = []
    for (w, lv), rs in sorted(cells.items()):
        ev = [r for r in rs if r["status"] == "EVALUATED"]
        st = Counter(r["status"] for r in rs)
        gs = Counter(r["gap_status"] for r in ev)

        def med(key):
            vals = [r[key] for r in ev if r[key] is not None]
            return statistics.median(vals) if vals else None
        out.append({"width": w, "level": lv, "instances": len(rs), "evaluated": len(ev),
                    "ineligible_short": st.get("INELIGIBLE_SHORT", 0),
                    "saturated_branch": st.get("SATURATED_REPETITION_BRANCH", 0),
                    "single_symbol_branch": st.get("SINGLE_SYMBOL_BRANCH", 0),
                    "cap_not_reached": st.get("NOT_REACHED_VIEW_CAP", 0) + st.get("NOT_REACHED_REQUEST_CAP", 0),
                    "median_k_over_m": med("k_over_m"),
                    "views_saturated_k_eq_m": sum(1 for r in ev if r["k"] == r["m"]),
                    "median_weak_support_fraction": med("weak_support_fraction"),
                    "median_pooled_irregular_fraction": med("pooled_irregular_fraction"),
                    "irregular_fraction_unavailable": sum(1 for r in ev if r["pooled_irregular_fraction"] is None),
                    "shorter_than_a0": gs.get("SHORTER_THAN_A0", 0),
                    "no_shorter_candidate": gs.get("NO_SHORTER_CANDIDATE_AMONG_EVALUATED", 0),
                    "no_admissible_candidate": gs.get("NO_ADMISSIBLE_CANDIDATE", 0),
                    "median_minus_a0_per_bit": med("minus_a0_per_bit"),
                    "median_vs_previous_level_bits": med("vs_previous_level_bits"),
                    "selected_views": sum(1 for r in rs if r["selected_here"])})
    return out


def _intrinsic(v: dict) -> dict:
    """View fields that do not depend on what earlier views of the same job produced:
    a duplicate of an earlier archive is compared as serialized, and acceptance (which
    depends on the incumbent) and the enumeration index are dropped."""
    out = {k: x for k, x in v.items() if k not in ("view_index", "proposals", "description_gap")}
    out["proposals"] = [{**{k: x for k, x in p.items() if k not in ("accepted", "status")},
                         "status": "SERIALIZED_DECODED" if p["status"] == "DUPLICATE_ARCHIVE" else p["status"]}
                        for p in v["proposals"]]
    dg = dict(v["description_gap"] or {})
    out["description_gap_best_bits"] = dg.get("best_bits")
    return out


def nested_view_equality(d: Path, specs, rows: dict) -> dict:
    """A1 views == A2 width-8 views == A3 level-1 width-8 views; A2 == A3 level 1
    (deterministic projection; view_index renumbered by the arm's enumeration)."""
    from .search import strip_timing
    bad, checked = [], 0
    for s in specs:
        tr = {}
        for arm in AUG_ARMS:
            row = rows.get((s["case_id"], arm))
            if not row or not row.get("trace_path"):
                break
            tr[arm] = [_intrinsic(strip_timing(x)) for x in load_json(d / row["trace_path"])["views"]]
        else:
            checked += 1
            a3l1 = [v for v in tr["A3"] if v["level"] == 1]
            if tr["A2"] != a3l1:
                bad.append(f"{s['case_id']}: A2 != A3 level 1")
            if tr["A1"] != [v for v in tr["A2"] if v["width"] == 8]:
                bad.append(f"{s['case_id']}: A1 != A2 width 8")
    return {"strings_checked": checked, "mismatches": bad}


# ---------------------------------------------------------------------------
# Explanations of selected augmentation archives
# ---------------------------------------------------------------------------

def explanations(d: Path, specs, rows: dict) -> list[dict]:
    out = []
    for s in specs:
        for arm in AUG_ARMS:
            row = rows.get((s["case_id"], arm))
            if not row or (row.get("selected") or {}).get("source") not in ("augmentation", "checkpoint"):
                continue
            data = (d / row["archive_path"]).read_bytes()
            led = archive_ledger(data)
            model = led["model"]
            reconciled = sum(f["bytes"] for f in led["fields"]) == len(data)
            refs = Counter(c for r in model.rules for c in r.refs())
            rules = explain_model(model)
            sel = row["selected"]
            prov = None
            if row.get("trace_path"):
                tr = load_json(d / row["trace_path"])
                v = tr["views"][sel["view_index"]]
                p = next(p for p in v["proposals"] if p["proposal"] == sel["proposal"])
                prov = {"view": {k: v[k] for k in ("level", "width", "origin", "span", "m", "k",
                                                  "prefix_bits", "suffix_bits")},
                        "proposal": p, "dictionary_depth": v["dictionary_depth"],
                        "pair_rule_depth": p["detail"].get("pair_rule_depth"),
                        "dictionary": v["dictionary"][:64], "dictionary_truncated": len(v["dictionary"]) > 64,
                        "token_span_bits": v["token_span_bits"], "bit_start_of_token_0": v["bit_start_of_token_0"],
                        "lower_cost_candidates_in_job": sorted(
                            {(x["archive_bits"], vv["view_index"], x["proposal"]) for vv in tr["views"]
                             for x in vv["proposals"] if x["archive_bits"] is not None
                             and x["archive_bits"] < row["a0_archive_bits"]})}
            nonterminal = [i for i, r in enumerate(model.rules) if r.op != C.OP_LITERAL]
            out.append({"case_id": s["case_id"], "arm": arm, "archive_bits": 8 * len(data),
                        "a0_bits": row["a0_archive_bits"], "selected": sel,
                        "ledger_reconciles_every_byte": reconciled,
                        "bytes_by_owner": led["bytes_by_owner"], "fields": led["fields"],
                        "rules": rules, "rule_count": len(model.rules), "dag_depth": model.depth(),
                        "nonterminal_rules": len(nonterminal),
                        "reused_rules_referenced_ge_2": sorted(i for i, c in refs.items() if c >= 2),
                        "repeat_rules": [i for i, r in enumerate(model.rules) if r.op == C.OP_REPEAT],
                        "single_reference_nonterminals_forced_grouping": sorted(
                            i for i in nonterminal if refs.get(i, 0) == 1 and model.rules[i].op == C.OP_CONCAT),
                        "provenance": prov})
    return out


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def _csv(rows: list[dict], fields=None) -> bytes:
    if not rows:
        return b""
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=list(fields or rows[0]), extrasaction="ignore")
    w.writeheader()
    for r in rows:
        w.writerow(r)
    return buf.getvalue().encode()


def build(d: Path = RUN_DIR, write: bool = True) -> dict:
    from hierarchy.benchmark import atomic_write
    specs = case_specs()
    rows = load_rows(d, specs)
    refs = load_references(d)
    st = evidence_state(specs, rows, refs)
    bits = bits_table(specs, rows, refs)
    con = contrasts(specs, bits)
    rec = recommendation(st["state"], bits)
    if st["state"] != "VALID_COMPLETE":
        for c in con.values():
            c["declared_aggregate_withheld"] = c["aggregate"] is not None
            c["aggregate"] = None
    vrows = view_rows(d, specs, rows, "A3")
    gm = gap_map(vrows)
    a0_rows = [rows.get((s["case_id"], "A0")) for s in specs]
    counts = {
        "strings": len(specs),
        "baseline_jobs_intended": len(specs), "baseline_jobs_with_rows": sum(r is not None for r in a0_rows),
        "baseline_reproduced": sum(1 for r in a0_rows if r and r.get("reproduction", {}).get("reproduced")),
        "augmentation_jobs_intended": 3 * len(specs),
        "augmentation_jobs_with_rows": sum(rows.get((s["case_id"], a)) is not None for s in specs for a in AUG_ARMS),
        "augmentation_rows_valid": sum((rows.get((s["case_id"], a)) or {}).get("validity") == "valid"
                                       for s in specs for a in AUG_ARMS),
        "search_complete": sum(bool((rows.get((s["case_id"], a)) or {}).get("search_complete"))
                               for s in specs for a in AUG_ARMS),
        "traces": sum(bool((rows.get((s["case_id"], a)) or {}).get("trace_path")) for s in specs for a in AUG_ARMS),
        "derived_composite_records": sum(bits[c][a] is not None for c in bits for a in AUG_ARMS),
        "imported_reference_records": sum(len(r["methods"]) - 2 for r in refs.values()),
        "imported_reference_problems": sum(len(r["problems"]) for r in refs.values()),
        "derived_portfolio_references": sum(1 for r in refs.values() if r["portfolio"]["matches_saved_baseline_best"]),
        "view_records_A3": len(vrows),
        "new_encoder_jobs": len(specs) + 3 * len(specs),
    }
    summary = {"schema": "hierarchy-multilevel-feasibility-v1", "run_id": d.name,
               "evidence_state": st, "recommendation": rec, "counts": counts,
               "bits": bits, "contrasts": con, "workload": workload(specs, rows, d),
               "runtime": runtime(specs, rows), "rule_kind_cost_bits": rule_kind_cost(d, rows, specs),
               "gap_map": gm, "nested_view_equality": nested_view_equality(d, specs, rows)}
    if write:
        ex = explanations(d, specs, rows)
        atomic_write(d / "summary.json", (json.dumps(summary, indent=1, sort_keys=True) + "\n").encode())
        atomic_write(d / "tables" / "views_A3.csv", _csv(vrows, VIEW_FIELDS))
        atomic_write(d / "tables" / "gap_map_A3.csv", _csv(gm))
        per = [{"case_id": s["case_id"], "family": s["family"], "base_length": s["base_length"],
                "replicate": s["replicate"], "ragged": s["ragged"], "n_bits": s["n_bits"],
                **bits[s["case_id"]],
                **{f"{a}_status": (rows.get((s["case_id"], a)) or {}).get("status") for a in ("A0",) + AUG_ARMS},
                **{f"{a}_selected": json.dumps({k: v for k, v in ((rows.get((s["case_id"], a)) or {}).get("selected") or {}).items() if k != "trace"}, sort_keys=True)
                   for a in AUG_ARMS}} for s in specs]
        atomic_write(d / "tables" / "per_string.csv", _csv(per))
        crow = [{"contrast": k, "aggregate": v["aggregate"], **{f"strings_{x}": y for x, y in v["strings"].items()},
                 **{f"cells_{x}": y for x, y in v["cells_sign"].items()}} for k, v in con.items()]
        atomic_write(d / "tables" / "contrasts.csv", _csv(crow))
        cells = [{"contrast": k, "cell": c, "saving": s} for k, v in con.items() for c, s in v["cells"].items()]
        atomic_write(d / "tables" / "contrast_cells.csv", _csv(cells))
        atomic_write(d / "explanations.jsonl",
                     "".join(json.dumps(e, sort_keys=True) + "\n" for e in ex).encode())
        decision = {"run_id": d.name, "engineering_verdict": st["state"],
                    "recommendation": rec["label"], "recommendation_detail": rec,
                    "invalid": st["invalid"][:50], "incomplete": st["incomplete"][:50],
                    "aggregates": {k: v["aggregate"] for k, v in con.items()},
                    "explanations": len(ex),
                    "scope": "descriptive, exposed data; no inference, generalization, "
                             "fractal or causal claim"}
        atomic_write(d / "DECISION.json", (json.dumps(decision, indent=1, sort_keys=True) + "\n").encode())
        atomic_write(d / "REPORT.md", render_report(summary, decision, ex).encode())
    return summary


def _f(x, nd=5):
    return "n/a" if x is None else (f"{x:.{nd}f}" if isinstance(x, float) else str(x))


def render_report(s: dict, dec: dict, ex: list) -> str:
    L = [f"# HID multilevel v1 feasibility — {s['run_id']}", "",
         "Exploratory, descriptive study on 96 previously exposed strings. Not confirmation, "
         "not held-out performance; no interval, test, fractal or causal claim.", "",
         f"**Engineering verdict:** {dec['engineering_verdict']}  ",
         f"**Conditional exploratory label:** {dec['recommendation']}", ""]
    rec = s["recommendation"]
    if rec.get("label"):
        L += [f"A3 shorter than A0 on {rec['a3_beats_a0_strings']} of 96 strings; "
              f"A3 shorter than A2 on {rec['a3_beats_a2_strings']}; "
              f"A2 shorter than A0 on {rec['a2_beats_a0_strings']}.", ""]
    L += ["## Counts", "", "| item | value |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in s["counts"].items()]
    L += ["", "## Contrasts (saving = (bits(B) − bits(A)) / n; positive: A shorter)", "",
          "| contrast | equal-cell mean | strings better/tie/worse | cells better/tie/worse |",
          "|---|---:|---|---|"]
    for k, v in s["contrasts"].items():
        a, c = v["strings"], v["cells_sign"]
        L.append(f"| {k} | {_f(v['aggregate'], 6)} | {a['better']}/{a['tie']}/{a['worse']} "
                 f"(of {a['available']}) | {c['better']}/{c['tie']}/{c['worse']} (of {c['available']}) |")
    L += ["", "## Workload and selections", ""]
    for arm, w in s["workload"].items():
        L.append(f"* **{arm}** jobs {w['job_status']}; augmentation selected in "
                 f"{w['augmentation_selections']} strings {w['selections_by_view_proposal']}; "
                 f"views {w['view_status']}; stop {w['stop_reasons']}")
    rt = s["runtime"]
    L += ["", "## Runtime (seconds)", "",
          f"* Physical A0 worker wall: sum {_f(rt['physical']['A0_worker_wall_s']['sum'], 2)}, "
          f"max {_f(rt['physical']['A0_worker_wall_s']['max'], 3)}"]
    for arm in AUG_ARMS:
        p = rt["physical"][f"{arm}_worker_wall_s"]
        dpl = rt["attributed_deployment"][arm]["deployment_wall_s"]
        L.append(f"* {arm}: augmentation worker sum {_f(p['sum'], 2)}, max {_f(p['max'], 3)}; "
                 f"attributed deployment (A0 + augmentation) median {_f(dpl['median'], 3)}, "
                 f"max {_f(dpl['max'], 3)}")
    L += [f"* All new jobs, worker wall sum: {_f(rt['physical']['all_new_jobs_worker_wall_s_sum'], 2)}",
          "", "## Width-by-level map (A3 views; 192 instances per cell = 96 strings × 2 origins)", "",
          "| width | level | evaluated | ineligible | saturated-branch | single-branch | median k/m | "
          "median weak support | shorter than A0 | no shorter | no admissible | median (best−A0)/n |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for g in s["gap_map"]:
        L.append(f"| {g['width']} | {g['level']} | {g['evaluated']} | {g['ineligible_short']} | "
                 f"{g['saturated_branch']} | {g['single_symbol_branch']} | {_f(g['median_k_over_m'], 3)} | "
                 f"{_f(g['median_weak_support_fraction'], 3)} | {g['shorter_than_a0']} | "
                 f"{g['no_shorter_candidate']} | {g['no_admissible_candidate']} | "
                 f"{_f(g['median_minus_a0_per_bit'], 4)} |")
    L += ["", "These maps are diagnostics of this vocabulary on exposed data; they do not "
          "locate a universal word length or threshold.", "",
          f"## Explanations: {len(ex)} selected augmentation archives (explanations.jsonl)", ""]
    for e in ex[:12]:
        L.append(f"* {e['case_id']} {e['arm']}: {e['archive_bits']} bits vs A0 {e['a0_bits']}; "
                 f"{e['selected'].get('proposal')} w{e['selected'].get('width')} "
                 f"o{e['selected'].get('origin')} l{e['selected'].get('level')}; rules {e['rule_count']}, "
                 f"reused {len(e['reused_rules_referenced_ge_2'])}, forced-grouping CONCATs "
                 f"{len(e['single_reference_nonterminals_forced_grouping'])}; ledger reconciles "
                 f"{e['ledger_reconciles_every_byte']}")
    L += ["", f"Nested view equality: {s['nested_view_equality']['strings_checked']} strings, "
          f"{len(s['nested_view_equality']['mismatches'])} mismatches.", ""]
    return "\n".join(L) + "\n"
