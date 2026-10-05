"""Status-aware tables, mode contributions, explanations, REPORT and DECISION.

Reads saved rows, references, the imported old-A3 records, traces and archive bytes
only; runs no encoder and rebuilds no candidate. Descriptive only (BENCHMARK section 3):
saving(X, Y) = (bits(Y) - bits(X)) / n, positive when X is shorter; averaged base/ragged
within replicate, replicates within the family-length cell, then the 24 cells equally.
No interval, test or bootstrap. The generic arithmetic (``saving``, ``aggregate``,
``sign_counts``, quantiles, CSV) is the multilevel-v1 report's, imported.
"""
from __future__ import annotations

import json
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from hierarchy import codes as C
from hierarchy.ledger import archive_ledger, explain_model
from hierarchy_multilevel.report import _csv, _f, _q, aggregate, load_json, load_references, saving, sign_counts

from .runner import AUG_ARMS, RUN_DIR, VALID_AUG, case_specs
from .search import MODES

ARMS_ALL = ("A0",) + AUG_ARMS
CONTRASTS = (("D0", "oldA3"), ("D1", "D0"), ("D2", "D1"),
             ("D0", "A0"), ("D1", "A0"), ("D2", "A0"),
             ("D0", "pair_grammar"), ("D1", "pair_grammar"), ("D2", "pair_grammar"),
             ("D0", "portfolio"), ("D1", "portfolio"), ("D2", "portfolio"),
             ("A0", "pair_grammar"), ("A0", "portfolio"), ("oldA3", "A0"))
LABELS = ("RELATION_GAIN_OBSERVED", "PERIOD_GAIN_OBSERVED", "CONTROL_ONLY_GAIN", "NO_RETAINED_GAIN")

__all__ = ["saving", "aggregate", "sign_counts"]


def load_rows(d: Path, specs) -> dict:
    """{(case_id, arm): row or None}; corrupt rows are recorded as 'corrupt_row'."""
    out = {}
    for s in specs:
        for arm in ARMS_ALL:
            p = d / "rows" / f"{s['case_id']}.{arm}.json"
            if not p.is_file():
                out[(s["case_id"], arm)] = None
                continue
            try:
                out[(s["case_id"], arm)] = load_json(p)
            except ValueError:
                out[(s["case_id"], arm)] = {"status": "corrupt_row", "validity": "invalid"}
    return out


def load_old(d: Path) -> dict:
    p = d / "old_a3.jsonl"
    if not p.is_file():
        return {}
    return {r["case_id"]: r for r in (json.loads(x) for x in p.read_text().splitlines() if x.strip())}


def evidence_state(specs, rows: dict, refs: dict, old: dict) -> dict:
    """INVALID > INCOMPLETE > VALID_COMPLETE (contract ``state_precedence``)."""
    invalid, incomplete = [], []
    for s in specs:
        cid = s["case_id"]
        r = refs.get(cid)
        if r is None:
            incomplete.append(f"{cid}: references missing")
        elif r["problems"]:
            invalid.append(f"{cid}: reference problems {r['problems']}")
        o = old.get(cid)
        if o is None:
            incomplete.append(f"{cid}: old A3 missing")
        elif o["problems"]:
            invalid.append(f"{cid}: old A3 problems {o['problems']}")
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


def bits_table(specs, rows: dict, refs: dict, old: dict) -> dict:
    """{case_id: {arm/reference: archive bits or None}} -- None is unavailable, never 0."""
    out = {}
    for s in specs:
        cid = s["case_id"]
        rec = {}
        for arm in ARMS_ALL:
            row = rows.get((cid, arm))
            ok = row is not None and (row.get("status") == "ok" if arm == "A0"
                                      else row.get("status") in VALID_AUG)
            rec[arm] = row["archive_bits"] if ok else None
        r = refs.get(cid)
        rec["pair_grammar"] = r["methods"]["pair_grammar"]["archive_bits"] if r else None
        rec["portfolio"] = r["portfolio"]["archive_bits"] if r else None
        o = old.get(cid)
        rec["oldA3"] = o["archive_bits"] if o and not o["problems"] else None
        out[cid] = rec
    return out


def contrasts(specs, bits: dict) -> dict:
    out = {}
    n = {s["case_id"]: s["n_bits"] for s in specs}
    for a, b in CONTRASTS:
        per = {cid: saving(bits[cid][a], bits[cid][b], n[cid]) for cid in bits}
        ag = aggregate(specs, per)
        out[f"{a}_vs_{b}"] = {"A": a, "B": b, "per_string": per, "pairs": ag["pairs"],
                              "cells": ag["cells"], "aggregate": ag["aggregate"],
                              "strings": sign_counts(list(per.values())),
                              "pairs_sign": sign_counts(list(ag["pairs"].values())),
                              "cells_sign": sign_counts(list(ag["cells"].values())),
                              "denominators": {"strings": len(per), "pairs": ag["n_pairs"],
                                               "cells": ag["n_cells"]}}
    return out


def recommendation(state: str, bits: dict) -> dict:
    if state != "VALID_COMPLETE":
        return {"label": None, "reason": f"evidence state {state}: recommendation logic disabled"}
    d2_d1 = [c for c, r in bits.items() if r["D2"] < r["D1"]]
    d1_d0 = [c for c, r in bits.items() if r["D1"] < r["D0"]]
    d0_a0 = [c for c, r in bits.items() if r["D0"] < r["A0"]]
    if d2_d1:
        label = "RELATION_GAIN_OBSERVED"
    elif d1_d0:
        label = "PERIOD_GAIN_OBSERVED"
    elif d0_a0:
        label = "CONTROL_ONLY_GAIN"
    else:
        label = "NO_RETAINED_GAIN"
    return {"label": label, "order": list(LABELS),
            "d2_beats_d1_cases": d2_d1, "d1_beats_d0_cases": d1_d0, "d0_beats_a0_cases": d0_a0,
            "d2_beats_a0_cases": [c for c, r in bits.items() if r["D2"] < r["A0"]],
            "d1_beats_a0_cases": [c for c, r in bits.items() if r["D1"] < r["A0"]],
            "meaning": "exploratory label on 96 exposed strings; not statistical superiority, "
                       "generalization, causality or adoption"}


# ---------------------------------------------------------------------------
# Traces: workload, mode contributions, nesting
# ---------------------------------------------------------------------------

def _trace(d: Path, row) -> dict | None:
    if not row or not row.get("trace_path"):
        return None
    return load_json(d / row["trace_path"])


def workload(specs, rows: dict, d: Path, traces: dict) -> dict:
    out = {}
    for arm in AUG_ARMS:
        st, views, props, sel, counters, stop, modes = (Counter() for _ in range(7))
        for s in specs:
            row = rows.get((s["case_id"], arm))
            st[row["status"] if row else "missing"] += 1
            if not row:
                continue
            sv = row.get("selected") or {}
            if sv.get("source") in ("augmentation", "checkpoint"):
                sel[f"{sv['mode']}|{sv['proposal']}|w{sv['width']}|o{sv['origin']}|l{sv['level']}"] += 1
            if row.get("stop_reason"):
                stop[row["stop_reason"]] += 1
            for k, v in (row.get("counters") or {}).items():
                if isinstance(v, int) and not isinstance(v, bool):
                    counters[k] += v
            tr = traces.get((s["case_id"], arm))
            if tr:
                for v in tr["views"]:
                    views[v["status"]] += 1
                    for m in v.get("modes", []):
                        modes[f"{m['mode']}:{m.get('status')}"] += 1
                    for p in v["proposals"]:
                        props[f"{p['mode']}:{p['proposal']}:{p['status']}"] += 1
        out[arm] = {"job_status": dict(st), "view_status": dict(views), "mode_status": dict(modes),
                    "proposal_status": dict(sorted(props.items())), "counters": dict(counters),
                    "stop_reasons": dict(stop), "augmentation_selections": sum(sel.values()),
                    "selections_by_mode_proposal_view": dict(sorted(sel.items()))}
    return out


def mode_contributions(specs, traces: dict, rows: dict) -> dict:
    """Descriptive, from D2 traces (D1/D0 are nested subsets): per view the best archive of
    each mode, compared with O (and R(P) with P) of the SAME view; per string the best of
    each mode over all views. Not independent randomized effects."""
    per_string, view_cmp = {}, {f"{a}_vs_{b}": Counter() for a, b in
                                (("P", "O"), ("R(O)", "O"), ("R(P)", "P"), ("R(P)", "O"))}
    view_cmp_den = Counter()
    mode_vs_a0 = {m: Counter() for m in MODES}
    for s in specs:
        cid = s["case_id"]
        tr = traces.get((cid, "D2"))
        row = rows.get((cid, "D2"))
        if not tr:
            per_string[cid] = None
            continue
        best = {m: None for m in MODES}
        for v in tr["views"]:
            if v["status"] != "EVALUATED":
                continue
            mb = {m["mode"]: m["best_bits"] for m in v["modes"]}
            for m, x in mb.items():
                if x is not None and (best[m] is None or x < best[m]):
                    best[m] = x
                if x is not None:
                    mode_vs_a0[m]["shorter" if x < row["a0_archive_bits"] else
                                  ("equal" if x == row["a0_archive_bits"] else "longer")] += 1
                else:
                    mode_vs_a0[m]["unavailable"] += 1
            for a, b in (("P", "O"), ("R(O)", "O"), ("R(P)", "P"), ("R(P)", "O")):
                key = f"{a}_vs_{b}"
                if mb.get(a) is None or mb.get(b) is None:
                    view_cmp[key]["unavailable"] += 1
                    continue
                view_cmp_den[key] += 1
                view_cmp[key]["shorter" if mb[a] < mb[b] else ("equal" if mb[a] == mb[b] else "longer")] += 1
        per_string[cid] = {"best_bits_by_mode": best, "a0_bits": row["a0_archive_bits"] if row else None}
    return {"per_string": per_string, "same_view_comparisons": {k: dict(v) for k, v in view_cmp.items()},
            "same_view_denominators": dict(view_cmp_den),
            "view_mode_best_vs_a0": {m: dict(c) for m, c in mode_vs_a0.items()},
            "strings_where_mode_best_beats_O_best": {
                m: sum(1 for r in per_string.values() if r and r["best_bits_by_mode"][m] is not None
                       and r["best_bits_by_mode"]["O"] is not None
                       and r["best_bits_by_mode"][m] < r["best_bits_by_mode"]["O"]) for m in MODES[1:]},
            "note": "R(O)/R(P) contributions are read from the same traces; modes share views, "
                    "gaps and factories, so these are descriptive, not independent effects"}


def construction_summary(specs, traces: dict) -> dict:
    """Dictionary construction counts from D2 traces (periods, relations, hops, flags)."""
    c = Counter()
    flags, flips, hops = Counter(), Counter(), Counter()
    for s in specs:
        tr = traces.get((s["case_id"], "D2"))
        if not tr:
            continue
        for v in tr["views"]:
            if v["status"] != "EVALUATED":
                continue
            c["evaluated_views"] += 1
            c["dictionary_entries"] += v["k"]
            for m in v["modes"]:
                con = m.get("construction") or {}
                if m["mode"] == "P" and con:
                    c["period_replacements"] += con["replaced"]
                    c["views_with_period_replacement"] += con["replaced"] > 0
                    c["non_dividing_proper_periods"] += len(con["non_dividing_proper_period_ids"])
                if m["mode"] == "R(O)" and con:
                    c["relations_selected_R(O)"] += con["relations_selected"]
                    c["views_with_relation"] += con["relations_selected"] > 0
                    c["relation_comparisons_R(O)"] += con["comparisons"]
                    c["hop_cap_rejections_R(O)"] += con["eligible_by_flips_rejected_by_hop_cap"]
                    for r in con["relations"]:
                        flags[r["flags"]] += 1
                        flips[len(r["flip_positions"])] += 1
                        hops[r["hops"]] += 1
                if m["mode"] == "R(P)" and con:
                    c["relations_selected_R(P)"] += con["relations_selected"]
                    c["relation_comparisons_R(P)"] += con["comparisons"]
    return {"counts": dict(c), "relation_flags": dict(sorted(flags.items())),
            "relation_flip_counts": dict(sorted(flips.items())),
            "relation_hops": dict(sorted(hops.items()))}


def _norm(st):
    return "SERIALIZED_DECODED" if st == "DUPLICATE_ARCHIVE" else st


def nesting(specs, rows: dict, traces: dict, old: dict, bits: dict) -> dict:
    """Engineering invariants on complete searches: D0 <= old A3, D1 <= D0, D2 <= D1; every
    old-A3-evaluated view reappears in D0 mode O with identical proposal archive hashes;
    D1/D2 O-mode proposals equal D0's on every view."""
    viol, checked = [], Counter()
    for s in specs:
        cid = s["case_id"]
        r = bits[cid]
        comp = {a: (rows.get((cid, a)) or {}).get("status") == "ok" for a in AUG_ARMS}
        for a, b in (("D0", "oldA3"), ("D1", "D0"), ("D2", "D1")):
            if comp[a] and r[a] is not None and r[b] is not None:
                checked[f"{a}<={b}"] += 1
                if r[a] > r[b]:
                    viol.append(f"{cid}: {a} {r[a]} > {b} {r[b]}")
        t0 = traces.get((cid, "D0"))
        o = old.get(cid)
        if t0 and o and comp["D0"]:
            byk = {f"{v['level']}-{v['width']}-{v['origin']}": v for v in t0["views"]}
            for key, props in o["evaluated_view_proposals"].items():
                checked["old_view"] += 1
                v = byk.get(key)
                mine = [[p["proposal"], _norm(p["status"]), p["archive_sha256"]]
                        for p in (v or {}).get("proposals", []) if p["mode"] == "O"]
                theirs = [[a, _norm(b), h] for a, b, h in props]
                if v is None or v["status"] != "EVALUATED" or mine != theirs:
                    viol.append(f"{cid}: old A3 view {key} not reproduced in D0 mode O")
        for arm in ("D1", "D2"):
            t = traces.get((cid, arm))
            if t and t0 and comp[arm] and comp["D0"]:
                checked[f"{arm}_O_equals_D0"] += 1
                a = [[[p["proposal"], _norm(p["status"]), p["archive_sha256"]] for p in v["proposals"]
                      if p["mode"] == "O"] for v in t["views"]]
                b = [[[p["proposal"], _norm(p["status"]), p["archive_sha256"]] for p in v["proposals"]
                      if p["mode"] == "O"] for v in t0["views"]]
                if a != b:
                    viol.append(f"{cid}: {arm} mode O differs from D0")
    return {"checked": dict(checked), "violations": viol}


# ---------------------------------------------------------------------------
# Runtime, rule-kind cost, view table, gap map
# ---------------------------------------------------------------------------

def runtime(specs, rows: dict) -> dict:
    a0 = [rows.get((s["case_id"], "A0")) for s in specs]
    out = {"physical": {"A0_worker_wall_s": _q([r["worker_wall_ns"] / 1e9 for r in a0 if r]),
                        "A0_peak_rss_bytes": _q([r["peak_rss_bytes"] for r in a0 if r])},
           "attributed_deployment": {}}
    tot = sum(r["worker_wall_ns"] for r in a0 if r) / 1e9
    for arm in AUG_ARMS:
        rs = [rows.get((s["case_id"], arm)) for s in specs]
        rs = [r for r in rs if r and r.get("worker_wall_ns") is not None]
        out["physical"][f"{arm}_worker_wall_s"] = _q([r["worker_wall_ns"] / 1e9 for r in rs])
        out["physical"][f"{arm}_peak_rss_bytes"] = _q([r["peak_rss_bytes"] for r in rs])
        out["attributed_deployment"][arm] = {
            "definition": "A0 worker wall + augmentation worker wall (the A0 run is charged in "
                          "full to every composite)",
            "deployment_wall_s": _q([r["deployment_wall_ns"] / 1e9 for r in rs]),
            "deployment_peak_rss_bytes": _q([r["deployment_peak_rss_bytes"] for r in rs]),
            "encode_wall_s_in_child": _q([r["encode_wall_ns"] / 1e9 for r in rs
                                          if r.get("encode_wall_ns") is not None])}
        tot += sum(r["worker_wall_ns"] for r in rs) / 1e9
    out["physical"]["all_new_jobs_worker_wall_s_sum"] = tot
    out["note"] = ("Physical totals count each executed job once. Attributed deployment cost "
                   "charges A0 to every composite. Imported baseline and old-A3 timings are from "
                   "other runs and are not compared.")
    return out


def rule_kind_cost(d: Path, rows: dict, specs) -> dict:
    out = {}
    for arm in ARMS_ALL:
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
                if led["codec_id"] != C.CODEC_HID and own != "envelope":
                    key = f"payload:{led['codec']}"
                tot[key] += 8 * f["bytes"]
        out[arm] = dict(sorted(tot.items()))
    return out


VIEW_FIELDS = ("case_id", "family", "base_length", "ragged", "n_bits", "level", "width", "origin",
               "span", "m", "k", "k_over_m", "status", "k_eq_m", "k_eq_1", "old_mask_status",
               "prefix_bits", "suffix_bits", "weak_support_fraction", "a0_bits",
               "O_best", "P_best", "R(O)_best", "R(P)_best", "P_minus_O", "R(O)_minus_O",
               "R(P)_minus_O", "best_minus_a0_per_bit", "period_replacements", "relations_R(O)",
               "max_hops_R(O)", "selected_here")


def view_rows(specs, rows: dict, traces: dict, arm: str = "D2") -> list[dict]:
    out = []
    for s in specs:
        row = rows.get((s["case_id"], arm))
        tr = traces.get((s["case_id"], arm))
        if not tr:
            continue
        sel = row.get("selected") or {}
        for v in tr["views"]:
            ev = v["status"] == "EVALUATED"
            mm = {m["mode"]: m for m in v.get("modes", [])}
            r = {"case_id": s["case_id"], "family": s["family"], "base_length": s["base_length"],
                 "ragged": s["ragged"], "n_bits": s["n_bits"],
                 **{k: v[k] for k in ("level", "width", "origin", "span", "m", "k", "k_over_m",
                                      "status", "prefix_bits", "suffix_bits")},
                 "k_eq_m": v["branch_flags"]["k_eq_m"], "k_eq_1": v["branch_flags"]["k_eq_1"],
                 "old_mask_status": v["branch_flags"]["old_mask_status"],
                 "weak_support_fraction": v["weak_support"]["fraction_of_n"] if ev else None,
                 "a0_bits": row["a0_archive_bits"],
                 "best_minus_a0_per_bit": (v["description_gap"]["minus_a0_bits"] / s["n_bits"]
                                           if ev and v["description_gap"]["minus_a0_bits"] is not None else None),
                 "period_replacements": ((mm.get("P") or {}).get("construction") or {}).get("replaced"),
                 "relations_R(O)": ((mm.get("R(O)") or {}).get("construction") or {}).get("relations_selected"),
                 "max_hops_R(O)": ((mm.get("R(O)") or {}).get("construction") or {}).get("max_hops"),
                 "selected_here": sel.get("source") == "augmentation" and sel.get("view_index") == v["view_index"]}
            for m in MODES:
                r[f"{m}_best"] = (mm.get(m) or {}).get("best_bits")
            for m in ("P", "R(O)", "R(P)"):
                r[f"{m}_minus_O"] = (mm.get(m) or {}).get("minus_O_bits")
            out.append(r)
    return out


def gap_map(vrows: list[dict]) -> list[dict]:
    cells = defaultdict(list)
    for r in vrows:
        cells[(r["width"], r["level"])].append(r)
    out = []
    for (w, lv), rs in sorted(cells.items()):
        ev = [r for r in rs if r["status"] == "EVALUATED"]

        def med(key, pop=ev):
            vals = [r[key] for r in pop if r[key] is not None]
            return statistics.median(vals) if vals else None

        def cnt(key, pred, pop=ev):
            return sum(1 for r in pop if r[key] is not None and pred(r[key]))
        out.append({"width": w, "level": lv, "instances": len(rs), "evaluated": len(ev),
                    "ineligible_short": sum(r["status"] == "INELIGIBLE_SHORT" for r in rs),
                    "old_mask_would_skip": sum(r["old_mask_status"] is not None for r in ev),
                    "k_eq_m": sum(bool(r["k_eq_m"]) for r in ev),
                    "median_k_over_m": med("k_over_m"),
                    "median_best_minus_a0_per_bit": med("best_minus_a0_per_bit"),
                    "views_best_shorter_than_a0": cnt("best_minus_a0_per_bit", lambda x: x < 0),
                    "views_P_shorter_than_O": cnt("P_minus_O", lambda x: x < 0),
                    "views_P_longer_than_O": cnt("P_minus_O", lambda x: x > 0),
                    "views_RO_shorter_than_O": cnt("R(O)_minus_O", lambda x: x < 0),
                    "views_RO_longer_than_O": cnt("R(O)_minus_O", lambda x: x > 0),
                    "views_RP_shorter_than_O": cnt("R(P)_minus_O", lambda x: x < 0),
                    "median_P_minus_O_bits": med("P_minus_O"), "median_RO_minus_O_bits": med("R(O)_minus_O"),
                    "median_RP_minus_O_bits": med("R(P)_minus_O"),
                    "views_with_period_replacement": cnt("period_replacements", lambda x: x > 0),
                    "views_with_relation": cnt("relations_R(O)", lambda x: x > 0),
                    "selected_views": sum(1 for r in rs if r["selected_here"])})
    return out


# ---------------------------------------------------------------------------
# Explanations: selected archives and representative best candidates (saved bytes)
# ---------------------------------------------------------------------------

def _explain(d: Path, h: str) -> dict:
    data = (d / "archives" / h[:2] / f"{h}.isd").read_bytes()
    led = archive_ledger(data)
    model = led["model"]
    out = {"archive_sha256": h, "archive_bits": 8 * len(data),
           "ledger_reconciles_every_byte": sum(f["bytes"] for f in led["fields"]) == len(data),
           "bytes_by_owner": led["bytes_by_owner"]}
    if model is None:
        return dict(out, codec=led["codec"])
    refs = Counter(c for r in model.rules for c in r.refs())
    kind_bytes = Counter()
    kinds = {f"rule{i}": C.OP_NAMES[r.op] for i, r in enumerate(model.rules)}
    for f in led["fields"]:
        kind_bytes[kinds.get(f["owner"], f["owner"])] += f["bytes"]
    return dict(out, rule_count=len(model.rules), dag_depth=model.depth(),
                bytes_by_rule_kind=dict(sorted(kind_bytes.items())),
                rules_referenced_ge_2=sorted(i for i, c in refs.items() if c >= 2),
                xform_rules=[i for i, r in enumerate(model.rules) if r.op == C.OP_XFORM],
                patch_rules=[i for i, r in enumerate(model.rules) if r.op == C.OP_PATCH],
                repeat_rules=[i for i, r in enumerate(model.rules) if r.op == C.OP_REPEAT],
                rules=explain_model(model)[:96])


def explanations(d: Path, specs, rows: dict, traces: dict) -> list[dict]:
    out = []
    for s in specs:
        cid = s["case_id"]
        for arm in AUG_ARMS:
            row = rows.get((cid, arm))
            if row and (row.get("selected") or {}).get("source") in ("augmentation", "checkpoint"):
                out.append({"kind": "selected", "case_id": cid, "arm": arm, "a0_bits": row["a0_archive_bits"],
                            "selected": {k: v for k, v in row["selected"].items() if k != "trace"},
                            **_explain(d, row["archive_sha256"])})
        tr = traces.get((cid, "D2"))
        row = rows.get((cid, "D2"))
        if not tr:
            continue
        for mode in MODES:                      # representative best candidate per mode
            cands = [(m["best_bits"], v["view_index"], m, v) for v in tr["views"]
                     if v["status"] == "EVALUATED" for m in v["modes"]
                     if m["mode"] == mode and m["best_bits"] is not None]
            if not cands:
                continue
            bb, vi, m, v = min(cands, key=lambda t: (t[0], t[1]))
            con = dict(m.get("construction") or {})
            con.pop("comparison_flip_counts", None)
            con.pop("comparisons_first_j", None)
            out.append({"kind": "representative_best_candidate", "case_id": cid, "arm": "D2",
                        "mode": mode, "a0_bits": row["a0_archive_bits"],
                        "view": {k: v[k] for k in ("view_index", "level", "width", "origin", "span",
                                                   "m", "k", "prefix_bits", "suffix_bits")},
                        "proposal": m["best_proposal"], "construction": con,
                        **_explain(d, m["best_sha256"])})
    return out


# ---------------------------------------------------------------------------
# Writer
# ---------------------------------------------------------------------------

def build(d: Path = RUN_DIR, write: bool = True) -> dict:
    from hierarchy.benchmark import atomic_write
    specs = case_specs()
    rows = load_rows(d, specs)
    refs = load_references(d)
    old = load_old(d)
    traces = {(s["case_id"], a): _trace(d, rows.get((s["case_id"], a))) for s in specs for a in AUG_ARMS}
    st = evidence_state(specs, rows, refs, old)
    bits = bits_table(specs, rows, refs, old)
    con = contrasts(specs, bits)
    rec = recommendation(st["state"], bits)
    if st["state"] != "VALID_COMPLETE":
        for c in con.values():
            c["declared_aggregate_withheld"] = c["aggregate"] is not None
            c["aggregate"] = None
    vrows = view_rows(specs, rows, traces, "D2")
    gm = gap_map(vrows)
    a0_rows = [rows.get((s["case_id"], "A0")) for s in specs]
    aug = [rows.get((s["case_id"], a)) for s in specs for a in AUG_ARMS]
    counts = {
        "strings": len(specs),
        "baseline_jobs_intended": len(specs), "baseline_jobs_with_rows": sum(r is not None for r in a0_rows),
        "baseline_reproduced": sum(1 for r in a0_rows if r and r.get("reproduction", {}).get("reproduced")),
        "augmentation_jobs_intended": len(AUG_ARMS) * len(specs),
        "augmentation_jobs_with_rows": sum(r is not None for r in aug),
        "augmentation_rows_valid": sum((r or {}).get("validity") == "valid" for r in aug),
        "search_complete": sum(bool((r or {}).get("search_complete")) for r in aug),
        "watchdog_fallbacks": sum((r or {}).get("status", "").startswith("watchdog") for r in aug),
        "traces": sum(bool((r or {}).get("trace_path")) for r in aug),
        "new_encoder_jobs_intended": len(specs) + len(AUG_ARMS) * len(specs),
        "new_encoder_jobs_with_rows": sum(r is not None for r in a0_rows) + sum(r is not None for r in aug),
        "derived_composite_records": sum(bits[c][a] is not None for c in bits for a in AUG_ARMS),
        "imported_reference_records": sum(len(r["methods"]) - 2 for r in refs.values()),
        "imported_reference_problems": sum(len(r["problems"]) for r in refs.values()),
        "derived_portfolio_references": sum(1 for r in refs.values() if r["portfolio"]["matches_saved_baseline_best"]),
        "imported_old_a3_records": len(old),
        "imported_old_a3_problems": sum(len(r["problems"]) for r in old.values()),
        "view_records_D2": len(vrows),
        "evaluated_views_D2": sum(r["status"] == "EVALUATED" for r in vrows),
    }
    summary = {"schema": "hierarchy-dictionary-feasibility-v1", "run_id": d.name,
               "evidence_state": st, "recommendation": rec, "counts": counts,
               "bits": bits, "contrasts": con, "workload": workload(specs, rows, d, traces),
               "mode_contributions": mode_contributions(specs, traces, rows),
               "construction": construction_summary(specs, traces),
               "runtime": runtime(specs, rows), "rule_kind_cost_bits": rule_kind_cost(d, rows, specs),
               "gap_map": gm, "nesting": nesting(specs, rows, traces, old, bits)}
    if write:
        ex = explanations(d, specs, rows, traces)
        atomic_write(d / "summary.json", (json.dumps(summary, indent=1, sort_keys=True) + "\n").encode())
        atomic_write(d / "tables" / "views_D2.csv", _csv(vrows, VIEW_FIELDS))
        atomic_write(d / "tables" / "gap_map_D2.csv", _csv(gm))
        per = [{"case_id": s["case_id"], "family": s["family"], "base_length": s["base_length"],
                "replicate": s["replicate"], "ragged": s["ragged"], "n_bits": s["n_bits"],
                **bits[s["case_id"]],
                **{f"{a}_status": (rows.get((s["case_id"], a)) or {}).get("status") for a in ARMS_ALL},
                **{f"{a}_selected": json.dumps({k: v for k, v in ((rows.get((s["case_id"], a)) or {}).get("selected") or {}).items() if k != "trace"}, sort_keys=True)
                   for a in AUG_ARMS}} for s in specs]
        atomic_write(d / "tables" / "per_string.csv", _csv(per))
        crow = [{"contrast": k, "aggregate": v["aggregate"], **{f"strings_{x}": y for x, y in v["strings"].items()},
                 **{f"pairs_{x}": y for x, y in v["pairs_sign"].items()},
                 **{f"cells_{x}": y for x, y in v["cells_sign"].items()}} for k, v in con.items()]
        atomic_write(d / "tables" / "contrasts.csv", _csv(crow))
        atomic_write(d / "tables" / "contrast_pairs_cells.csv", _csv(
            [{"contrast": k, "level": "pair", "unit": c, "saving": x} for k, v in con.items() for c, x in v["pairs"].items()]
            + [{"contrast": k, "level": "cell", "unit": c, "saving": x} for k, v in con.items() for c, x in v["cells"].items()]))
        atomic_write(d / "tables" / "per_string_contrasts.csv", _csv(
            [{"contrast": k, "case_id": c, "saving": x} for k, v in con.items() for c, x in v["per_string"].items()]))
        atomic_write(d / "explanations.jsonl",
                     "".join(json.dumps(e, sort_keys=True) + "\n" for e in ex).encode())
        decision = {"run_id": d.name, "engineering_verdict": st["state"],
                    "recommendation": rec["label"], "recommendation_detail": rec,
                    "invalid": st["invalid"][:50], "incomplete": st["incomplete"][:50],
                    "aggregates": {k: v["aggregate"] for k, v in con.items()},
                    "explanations": len(ex), "nesting_violations": len(summary["nesting"]["violations"]),
                    "scope": "descriptive, exposed data; no inference, confirmation, generalization, "
                             "fractal or causal claim"}
        atomic_write(d / "DECISION.json", (json.dumps(decision, indent=1, sort_keys=True) + "\n").encode())
        atomic_write(d / "REPORT.md", render_report(summary, decision, ex).encode())
    return summary


def render_report(s: dict, dec: dict, ex: list) -> str:
    L = [f"# HID dictionary relations v1 feasibility — {s['run_id']}", "",
         "Exploratory, descriptive study on 96 previously exposed strings. Not confirmation, "
         "not held-out performance; no interval, test, fractal or causal claim.", "",
         f"**Engineering verdict:** {dec['engineering_verdict']}  ",
         f"**Conditional exploratory label:** {dec['recommendation']}", ""]
    rec = s["recommendation"]
    if rec.get("label"):
        L += [f"D2 shorter than D1 on {len(rec['d2_beats_d1_cases'])} of 96 strings; D1 shorter than "
              f"D0 on {len(rec['d1_beats_d0_cases'])}; D0 shorter than A0 on {len(rec['d0_beats_a0_cases'])}; "
              f"D2 shorter than A0 on {len(rec['d2_beats_a0_cases'])}.", ""]
    L += ["## Counts", "", "| item | value |", "|---|---:|"]
    L += [f"| {k} | {v} |" for k, v in s["counts"].items()]
    L += ["", "## Contrasts (saving = (bits(B) − bits(A)) / n; positive: A shorter)", "",
          "| contrast | equal-cell mean | strings better/tie/worse | pairs | cells |", "|---|---:|---|---|---|"]
    for k, v in s["contrasts"].items():
        a, p, c = v["strings"], v["pairs_sign"], v["cells_sign"]
        L.append(f"| {k} | {_f(v['aggregate'], 6)} | {a['better']}/{a['tie']}/{a['worse']} (of {a['available']}) "
                 f"| {p['better']}/{p['tie']}/{p['worse']} (of {p['available']}) "
                 f"| {c['better']}/{c['tie']}/{c['worse']} (of {c['available']}) |")
    L += ["", "## Workload and selections", ""]
    for arm, w in s["workload"].items():
        L.append(f"* **{arm}** jobs {w['job_status']}; augmentation selected in "
                 f"{w['augmentation_selections']} strings {w['selections_by_mode_proposal_view']}; "
                 f"views {w['view_status']}; stop {w['stop_reasons']}; requests "
                 f"{w['counters'].get('requests')}, serialized {w['counters'].get('serialized')}, "
                 f"decoded {w['counters'].get('decoded')}, duplicates {w['counters'].get('duplicates')}, "
                 f"patch rejections {w['counters'].get('patch_rejections')}, graph rejections "
                 f"{w['counters'].get('graph_rejections')}, relation comparisons "
                 f"{w['counters'].get('relation_comparisons')}")
    mc = s["mode_contributions"]
    L += ["", "## Mode contributions (D2 traces; same view; descriptive)", "",
          "| comparison | shorter | equal | longer | unavailable |", "|---|---:|---:|---:|---:|"]
    for k, v in mc["same_view_comparisons"].items():
        L.append(f"| {k} | {v.get('shorter', 0)} | {v.get('equal', 0)} | {v.get('longer', 0)} | {v.get('unavailable', 0)} |")
    L += ["", f"Strings whose best mode-X archive (any view) beats the best O archive: "
          f"{mc['strings_where_mode_best_beats_O_best']}.", "",
          f"Construction: {s['construction']['counts']}; relation flags {s['construction']['relation_flags']}; "
          f"hops {s['construction']['relation_hops']}.", ""]
    rt = s["runtime"]
    L += ["## Runtime (seconds)", "",
          f"* Physical A0 worker wall: sum {_f(rt['physical']['A0_worker_wall_s']['sum'], 2)}, "
          f"max {_f(rt['physical']['A0_worker_wall_s']['max'], 3)}"]
    for arm in AUG_ARMS:
        p = rt["physical"][f"{arm}_worker_wall_s"]
        dpl = rt["attributed_deployment"][arm]["deployment_wall_s"]
        L.append(f"* {arm}: augmentation worker sum {_f(p['sum'], 2)}, max {_f(p['max'], 3)}; "
                 f"attributed deployment (A0 + augmentation) median {_f(dpl['median'], 3)}, max {_f(dpl['max'], 3)}")
    L += [f"* All new jobs, worker wall sum: {_f(rt['physical']['all_new_jobs_worker_wall_s_sum'], 2)}", "",
          "## Width-by-level map (D2 views; 192 instances per cell = 96 strings × 2 origins)", "",
          "| width | level | evaluated | ineligible | old mask would skip | median k/m | median (best−A0)/n | "
          "P<O | P>O | R(O)<O | R(O)>O | views with relation |",
          "|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for g in s["gap_map"]:
        L.append(f"| {g['width']} | {g['level']} | {g['evaluated']} | {g['ineligible_short']} | "
                 f"{g['old_mask_would_skip']} | {_f(g['median_k_over_m'], 3)} | "
                 f"{_f(g['median_best_minus_a0_per_bit'], 4)} | {g['views_P_shorter_than_O']} | "
                 f"{g['views_P_longer_than_O']} | {g['views_RO_shorter_than_O']} | "
                 f"{g['views_RO_longer_than_O']} | {g['views_with_relation']} |")
    sel = [e for e in ex if e["kind"] == "selected"]
    L += ["", "These maps are diagnostics of this vocabulary on exposed data; they do not locate a "
          "universal word length, threshold or mechanism.", "",
          f"## Explanations ({len(sel)} selected archives; {len(ex) - len(sel)} representative best "
          "candidates; explanations.jsonl)", ""]
    for e in sel[:24]:
        L.append(f"* {e['case_id']} {e['arm']}: {e['archive_bits']} bits vs A0 {e['a0_bits']}; "
                 f"{e['selected'].get('mode')} {e['selected'].get('proposal')} w{e['selected'].get('width')} "
                 f"o{e['selected'].get('origin')} l{e['selected'].get('level')}; ledger reconciles "
                 f"{e['ledger_reconciles_every_byte']}; bytes by rule kind {e.get('bytes_by_rule_kind')}")
    nst = s["nesting"]
    L += ["", f"Nesting invariants: checked {nst['checked']}; {len(nst['violations'])} violations.", ""]
    return "\n".join(L) + "\n"
