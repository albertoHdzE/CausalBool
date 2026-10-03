"""HID-v1 analysis from saved rows only (benchmark annex B4, B6).

Nothing here runs inference. Every number comes from cases.jsonl, the corpus
manifest, diagnostics.json and the archives on disk. Presentation (figures,
notebook prose) lives in notebooks/build_16.py, outside the frozen sources.
"""
from __future__ import annotations

import json
import statistics
from collections import defaultdict
from pathlib import Path

import numpy as np

from . import validation as V
from .validation import HID_DEPLOYED

STRUCTURED = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")
CONTROLS = ("F07", "F08", "F09")
ABLATION_METHODS = ("hid_no_schema", "hid_no_arithmetic", "hid_no_transform", "hid_flat",
                    "hid_fixed8")

ANALYSIS_PLAN = {
    "primary_population": {"split": "confirmation", "families": list(STRUCTURED)},
    "per_string": "saving_bits = baseline_best_archive_bits - hid_full_archive_bits; "
                  "saving_per_input_bit = saving_bits / n_bits",
    "weighting": "mean of the base/ragged pair within a unit, then mean over units in "
                 "each (family, base_length) cell, then mean over cells (equal weights)",
    "primary_bootstrap": {"replicates": 10000, "seed": 33001, "rng": "numpy.random.default_rng",
                          "scheme": "within each cell resample units with replacement, "
                                    "keeping both lengths and all methods together",
                          "interval": "percentile 95%"},
    "verdict": {"supported": "95% interval entirely above 0, all baseline results "
                             "available, engineering gates pass",
                "not_supported": "95% interval entirely below 0",
                "inconclusive": "interval includes 0, or any baseline result censored"},
    "evidence_gates": {
        "population": "built from the declared design (families x base lengths x "
                      "replicates x base/ragged x required methods), never from present rows",
        "order": "engineering validity, then completeness of the claim's population, then "
                 "censoring, then the interval; a failed validity or completeness gate gives "
                 "verdict not_assessed whatever the interval; censoring gives inconclusive "
                 "whatever the interval's sign",
        "partial": "an aggregate over available units of an incomplete or censored "
                   "population is reported only as partial_diagnostic and never as the "
                   "endpoint"},
    "hid_deployed_statuses": list(HID_DEPLOYED),
    "ablations": {"methods": list(ABLATION_METHODS),
                  "per_string": "(ablation_bits - full_bits) / n_bits",
                  "replicates": 10000, "seed": 33002,
                  "interval": "percentile 99% (Bonferroni across five two-sided intervals)",
                  "joint_resampling": True},
    "descriptive": {"family_cells_seed": 33010, "transfer_seed": 33004,
                    "transfer_structured_aggregate_seed": 33005, "controls_seed": 33006,
                    "all_families_confirmation_seed": 43001,
                    "controls_and_all_families": "same endpoint, descriptive only",
                    "controls_vs_statistical_codes": "per control family, unweighted mean over "
                    "strings of (min(bernoulli, context) - hid_full) / n; descriptive only"},
}


# ---------------------------------------------------------------------------
# Loading
# ---------------------------------------------------------------------------

def load_rows(d: Path) -> list[dict]:
    p = d / "cases.jsonl"
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text().splitlines() if ln.strip()]


# ---------------------------------------------------------------------------
# Endpoint arithmetic
# ---------------------------------------------------------------------------

def string_saving(methods: dict) -> tuple[float | None, int | None, str]:
    """(saving per input bit, saving bits, availability) for one scored string."""
    hid = methods.get("hid_full")
    best = methods.get("baseline_best")
    if hid is None or best is None:
        return None, None, "missing_row"
    if hid["status"] not in HID_DEPLOYED or hid["archive_bits"] is None:
        return None, None, f"hid_{hid['status']}"
    if best["status"] != "ok":
        return None, None, f"baseline_{best['status']}"
    sav = best["archive_bits"] - hid["archive_bits"]
    return sav / hid["n_bits"], sav, "ok"


def string_saving_pb(methods):
    return string_saving(methods)[0]


def string_increment(methods: dict, ablation: str) -> float | None:
    full, abl = methods.get("hid_full"), methods.get(ablation)
    if not full or not abl or full["status"] not in HID_DEPLOYED or abl["status"] not in HID_DEPLOYED:
        return None
    return (abl["archive_bits"] - full["archive_bits"]) / full["n_bits"]


def unit_value(pair: dict, fn) -> float | None:
    vals = [fn(pair[r]) for r in (False, True) if r in pair]
    if len(vals) != 2 or any(v is None for v in vals):
        return None
    return (vals[0] + vals[1]) / 2


def design_units(index: dict, design: dict, split: str, families):
    """Yield ((family, base_length), unit label, {ragged: {method: row}}) for EVERY
    declared unit of ``split`` in ``families`` (sorted), present or not."""
    spec = design["splits"][split]
    for fam in sorted(f for f in spec["families"] if f in families):
        for bl in sorted(spec["base_lengths"]):
            for rep in sorted(spec["replicates"]):
                pair = {}
                for rg in (False, True):
                    got = index.get(V.design_case_id(design, split, fam, bl, rep, rg))
                    if got is not None:
                        pair[rg] = got
                yield (fam, bl), V.unit_label(split, fam, bl, rep), pair


def cells_matrix(index: dict, design: dict, split: str, families, fns
                 ) -> tuple[dict, list[str], int]:
    """({cell: array(units x len(fns))}, unavailable unit labels, required units).

    The population is the declared design; a unit is unavailable if either string or
    any value is missing, censored or not deployed."""
    cells: dict = defaultdict(list)
    unavailable, required = [], 0
    for cell, label, pair in design_units(index, design, split, families):
        required += 1
        vec = [unit_value(pair, fn) for fn in fns]
        if any(v is None for v in vec):
            unavailable.append(label)
            continue
        cells[cell].append(vec)
    return ({k: np.asarray(v, dtype=float) for k, v in sorted(cells.items())},
            unavailable, required)


def weighted_mean(cells: dict) -> np.ndarray:
    return np.mean([m.mean(axis=0) for m in cells.values()], axis=0)


def cell_index_draws(sizes: dict, reps: int, seed: int) -> dict:
    """{cell: reps x size array of unit indices}, drawn cell by cell in sorted key
    order: the one RNG consumption pattern of the stratified bootstrap. A caller that
    must keep the draw sequence fixed whatever rows are available passes the declared
    unit count of EVERY design cell here."""
    rng = np.random.default_rng(seed)
    return {key: rng.integers(0, sizes[key], size=(reps, sizes[key])) for key in sorted(sizes)}


def stratified_bootstrap(cells: dict, reps: int, seed: int) -> np.ndarray:
    """reps x k matrix of the equal-weight aggregate under within-cell resampling."""
    draws = cell_index_draws({key: m.shape[0] for key, m in cells.items()}, reps, seed)
    k = next(iter(cells.values())).shape[1]
    acc = np.zeros((reps, k))
    for key, idx in draws.items():
        acc += cells[key][idx].mean(axis=1)
    return acc / len(draws)


def percentile_interval(draws: np.ndarray, level: float) -> tuple[float, float]:
    lo = (1 - level) / 2
    return float(np.quantile(draws, lo)), float(np.quantile(draws, 1 - lo))


# ---------------------------------------------------------------------------
# Evidence gates and decisions
# ---------------------------------------------------------------------------

def population_gate(validation: dict, design: dict, split: str, families, methods) -> dict:
    """Validity, completeness and censoring of one claim's population."""
    index = validation["_index"]
    missing, censored = [], []
    required = 0
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design, split):
        if fam not in families:
            continue
        required += 1
        have = index.get(cid, {})
        for m in methods:
            r = have.get(m)
            if r is None or r.get("status") == "not_run":
                missing.append(f"{cid}:{m}")
            elif r.get("status") in V.BASELINE_CENSORED + V.PORTFOLIO_CENSORED:
                censored.append(f"{cid}:{m}:{r['status']}")
    if not required:
        missing.append(f"empty population: no declared {split} strings in {sorted(families)}")
    valid = bool(validation["engineering_valid"])
    return {"engineering_valid": valid, "complete": not missing, "required_strings": required,
            "missing": missing[:200], "missing_count": len(missing),
            "censored": censored[:200], "censored_count": len(censored),
            "assessable": valid and not missing}


def verdict(ci: tuple[float, float] | None, gate: dict) -> str:
    """Gates first, then the interval. Invalid or incomplete evidence is never
    assessed; a censored population is inconclusive whatever the interval's sign."""
    if not gate["engineering_valid"] or not gate["complete"]:
        return "not_assessed"
    if gate["censored_count"]:
        return "inconclusive"
    if ci[0] > 0:
        return "supported"
    if ci[1] < 0:
        return "not_supported"
    return "inconclusive"


def component_reading(ci: tuple[float, float] | None, gate: dict) -> str:
    if not gate["assessable"]:
        return "not_assessed"
    if ci[0] > 0:
        return "supported"
    return "ablation_better" if ci[1] < 0 else "not_detected"


def descriptive_reading(ci: tuple[float, float] | None, gate: dict) -> str:
    """Sign of a descriptive interval, after the same gates as a verdict."""
    return verdict(ci, gate)


def aggregate(index, design, split, families, fns, seed, level, gate) -> dict:
    """The equal-weight aggregate of ``fns`` with its interval when the gate passes
    and every declared unit is available; otherwise a labelled partial diagnostic."""
    cells, unavailable, required = cells_matrix(index, design, split, families, fns)
    out = {"split": split, "families": sorted(families), "required_units": required,
           "available_units": required - len(unavailable), "gate": gate}
    ok = gate["assessable"] and not gate["censored_count"] and not unavailable and cells
    if not cells:
        out["partial_diagnostic"] = None
        return out
    point = weighted_mean(cells)
    draws = stratified_bootstrap(cells, 10000, seed)
    cis = [percentile_interval(draws[:, i], level) for i in range(draws.shape[1])]
    body = {"estimate": [float(x) for x in point], "intervals": cis, "seed": seed,
            "level": level, "cells": len(cells),
            "units": int(sum(m.shape[0] for m in cells.values())),
            "draw_mean": [float(x) for x in draws.mean(axis=0)],
            "draw_sd": [float(x) for x in draws.std(axis=0)]}
    if ok:
        out["endpoint"] = body
    else:
        out["partial_diagnostic"] = dict(
            body, label="PARTIAL: available units only; not the prespecified endpoint",
            unavailable_units=unavailable[:200], unavailable_count=len(unavailable))
    return out


# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

def status_counts(validation: dict, design: dict) -> dict:
    out = {}
    for split in design["splits"]:
        n = sum(1 for _ in V.expected_cases(design, split))
        per = validation["status_counts"].get(split, {})
        out[split] = {}
        for m in design["methods"]:
            c = {k: v for k, v in per.get(m, {}).items() if k != "absent"}
            present = sum(c.values())
            out[split][m] = {"expected": n, "present": present, "absent": n - present, **c}
    return out


def describe_cells(index, design, split, families, seed, level=0.95) -> list[dict]:
    out = []
    if split not in design["splits"]:
        return out
    spec = design["splits"][split]
    rng_seed = seed
    for fam in families:
        if fam not in spec["families"]:
            continue
        for bl in sorted(spec["base_lengths"]):
            per, bits, avail = [], [], defaultdict(int)
            unit_vals = []
            for rep in sorted(spec["replicates"]):
                vals = []
                for rg in (False, True):
                    m = index.get(V.design_case_id(design, split, fam, bl, rep, rg))
                    if m is None:
                        avail["missing_case"] += 1
                        continue
                    spb, sb, a = string_saving(m)
                    avail[a] += 1
                    if spb is not None:
                        per.append(spb)
                        bits.append(sb)
                        vals.append(spb)
                if len(vals) == 2:
                    unit_vals.append(sum(vals) / 2)
            row = {"family": fam, "base_length": bl, "units_complete": len(unit_vals),
                   "units_required": len(spec["replicates"]), "availability": dict(avail)}
            if len(unit_vals) < len(spec["replicates"]):
                row["partial"] = True
            if unit_vals:
                arr = np.asarray(unit_vals)
                rng = np.random.default_rng(rng_seed)
                draws = arr[rng.integers(0, len(arr), size=(10000, len(arr)))].mean(axis=1)
                row.update({
                    "mean_saving_per_input_bit": float(arr.mean()),
                    "ci95_descriptive": percentile_interval(draws, level),
                    "mean_saving_bits": float(np.mean(bits)),
                    "median_saving_bits": float(np.median(bits)),
                    "median_saving_per_input_bit": float(np.median(per)),
                    "strings_hid_better": int(sum(b > 0 for b in bits)),
                    "strings_tied": int(sum(b == 0 for b in bits)),
                    "strings_hid_worse": int(sum(b < 0 for b in bits))})
            rng_seed += 1
            out.append(row)
    return out


def controls_vs_statistical_codes(index, design, split="confirmation") -> dict:
    """Descriptive: HID-full against the better of the two statistical codes."""
    out = {}
    if split not in design["splits"]:
        return out
    for fam in CONTROLS:
        vals, n_req = [], 0
        for cid, sp, f, bl, rep, rg, n in V.expected_cases(design, split):
            if f != fam:
                continue
            n_req += 1
            m = index.get(cid, {})
            h, b, c = m.get("hid_full"), m.get("bernoulli"), m.get("context")
            if not (h and b and c) or h["status"] not in HID_DEPLOYED or \
                    b["status"] != "ok" or c["status"] != "ok":
                continue
            vals.append((min(b["archive_bits"], c["archive_bits"]) - h["archive_bits"])
                        / h["n_bits"])
        if n_req:
            out[fam] = {"strings": len(vals), "strings_required": n_req,
                        "mean_saving_per_input_bit_unweighted":
                            float(np.mean(vals)) if vals else None,
                        "strings_hid_shorter": int(sum(v > 0 for v in vals)),
                        "strings_tied": int(sum(v == 0 for v in vals)),
                        "strings_hid_longer": int(sum(v < 0 for v in vals)),
                        "scope": "descriptive comparator, not a hypothesis test"}
    return out


def resources(rows) -> dict:
    out = {}
    for m in sorted({r["method"] for r in rows}):
        rr = [r for r in rows if r["method"] == m]
        enc = [r["encode_wall_ns"] / 1e9 for r in rr if r["encode_wall_ns"] is not None]
        wk = [r["worker_wall_ns"] / 1e9 for r in rr if r["worker_wall_ns"] is not None]
        rss = [r["peak_rss_bytes"] for r in rr if r["peak_rss_bytes"] is not None]
        out[m] = {"encode_s_median": statistics.median(enc) if enc else None,
                  "encode_s_max": max(enc) if enc else None,
                  "encode_s_total": sum(enc) if enc else None,
                  "worker_s_total": sum(wk) if wk else None,
                  "peak_rss_mb_max": max(rss) / 2 ** 20 if rss else None}
    return out


def summarise(validation: dict, design: dict, primary_split: str = "confirmation") -> dict:
    """Every number from the validated row index. ``primary_split`` is "confirmation"
    for every confirmatory run; development runs use "development" and are labelled
    exploratory by their callers."""
    index = validation["_index"]
    rows = sorted((r for m in index.values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    dec = {"decode_ok": sum(1 for r in rows if r["decode_ok"] is True),
           "decode_failed": sum(1 for r in rows if r["decode_ok"] is False),
           "with_archive": sum(1 for r in rows if r["archive_path"])}
    pub = V.public(validation)
    eng = {k: pub[k] for k in ("engineering_valid", "complete", "expected_rows",
                               "present_rows", "archives_checked",
                               "distinct_archives_decoded")}
    eng.update({k: pub[k][:200] for k in ("invalid", "incomplete", "censored",
                                          "duplicates", "unknown")})
    eng["missing_units"] = {k: v[:200] for k, v in pub["missing_units"].items()}
    eng["missing_methods"] = pub["missing_methods"]
    summary = {"analysis_plan": ANALYSIS_PLAN, "status_counts": status_counts(validation, design),
               "round_trips": dec, "validation": eng}
    baselines = tuple(design["baselines"])

    # primary endpoint
    gate = population_gate(validation, design, primary_split, STRUCTURED,
                           ("hid_full", "baseline_best") + baselines)
    agg = aggregate(index, design, primary_split, STRUCTURED, [string_saving_pb], 33001,
                    0.95, gate)
    prim = {"split": primary_split, "gate": gate, "required_units": agg["required_units"],
            "available_units": agg["available_units"],
            "evidence_validity": "valid" if gate["engineering_valid"] else "invalid",
            "evidence_completeness": "complete" if gate["complete"] else "incomplete",
            "censored_baselines": gate["censored_count"]}
    if "endpoint" in agg:
        e = agg["endpoint"]
        ci = e["intervals"][0]
        prim.update({
            "estimate_mean_saving_per_input_bit": e["estimate"][0], "ci95": ci,
            "bootstrap": {"replicates": 10000, "seed": 33001,
                          "draw_mean": e["draw_mean"][0], "draw_sd": e["draw_sd"][0]},
            "cells": e["cells"], "units": e["units"],
            **_string_level(index, design, primary_split),
            "units_missing": [], "baseline_not_ok": []})
        prim["verdict"] = verdict(ci, gate)
    else:
        prim["verdict"] = verdict(None, gate) if not gate["assessable"] else "inconclusive"
        prim["partial_diagnostic"] = _first(agg.get("partial_diagnostic"))
        prim["units_missing"] = (agg.get("partial_diagnostic") or {}).get("unavailable_units", [])
        prim["baseline_not_ok"] = gate["censored"]
    summary["primary"] = prim

    # ablations, jointly resampled
    fns = [(lambda m, a=a: string_increment(m, a)) for a in ABLATION_METHODS]
    agate = population_gate(validation, design, primary_split, STRUCTURED,
                            ("hid_full",) + ABLATION_METHODS)
    agate["censored_count"] = 0          # HID statuses are deployed, never censored
    aagg = aggregate(index, design, primary_split, STRUCTURED, fns, 33002, 0.99, agate)
    summary["ablations_gate"] = agate
    summary["ablations"] = {}
    for i, a in enumerate(ABLATION_METHODS):
        if "endpoint" in aagg:
            e = aagg["endpoint"]
            summary["ablations"][a] = {
                "incremental_gain_per_input_bit": e["estimate"][i], "ci99": e["intervals"][i],
                "component_advantage": component_reading(e["intervals"][i], agate)}
        else:
            pdg = aagg.get("partial_diagnostic")
            summary["ablations"][a] = {
                "component_advantage": "not_assessed",
                "partial_diagnostic": None if pdg is None else {
                    "label": pdg["label"], "estimate": pdg["estimate"][i],
                    "interval": pdg["intervals"][i], "units": pdg["units"]}}
    summary["ablations_units_missing"] = (aagg.get("partial_diagnostic") or {}).get(
        "unavailable_units", [])

    # descriptive tables and aggregates
    all12 = tuple(f"F{i:02d}" for i in range(1, 13))
    summary["families_confirmation"] = describe_cells(index, design, "confirmation", all12, 33010)
    summary["transfer"] = describe_cells(index, design, "transfer", all12, 33004)
    req = ("hid_full", "baseline_best") + baselines
    for key, split, fams, seed, note in (
            ("transfer_structured_aggregate", "transfer", STRUCTURED, 33005,
             "descriptive; four units per cell"),
            ("controls_aggregate", primary_split, CONTROLS, 33006,
             "descriptive; equal-weight aggregate of F07-F09 against the nine-code portfolio"),
            ("all_families_confirmation_aggregate", primary_split, all12, 43001,
             "descriptive; all twelve families against the nine-code portfolio; not the "
             "primary population")):
        if split not in design["splits"]:
            continue
        g = population_gate(validation, design, split, fams, req)
        ag = aggregate(index, design, split, fams, [string_saving_pb], seed, 0.95, g)
        item = {"gate": g, "note": note, "seed": seed, "families": list(fams),
                "required_units": ag["required_units"], "available_units": ag["available_units"]}
        if "endpoint" in ag:
            item.update({"estimate": ag["endpoint"]["estimate"][0],
                         "ci95_descriptive": ag["endpoint"]["intervals"][0],
                         "units_missing": [],
                         "reading": descriptive_reading(ag["endpoint"]["intervals"][0], g)})
        else:
            item.update({"reading": verdict(None, g) if not g["assessable"] else "inconclusive",
                         "partial_diagnostic": _first(ag.get("partial_diagnostic"))})
        summary[key] = item
    summary["controls_vs_statistical_codes"] = controls_vs_statistical_codes(
        index, design, primary_split)
    summary["development"] = describe_cells(index, design, "development", all12, 33020)
    summary["resources"] = resources(rows)
    hashes = defaultdict(list)
    for r in rows:
        if r["method"] == "hid_full":
            hashes[r["input_sha256"]].append(r["case_id"])
    summary["duplicate_inputs"] = {h: ids for h, ids in hashes.items() if len(ids) > 1}
    summary["selected_baselines"] = _selected_counts(rows)
    summary["hid_stop_reasons"] = _stop_counts(rows)
    return summary


def _first(pdg: dict | None) -> dict | None:
    """A one-function partial diagnostic with scalar estimate and interval."""
    if pdg is None:
        return None
    return {"label": pdg["label"], "estimate": pdg["estimate"][0],
            "interval": pdg["intervals"][0], "units": pdg["units"], "cells": pdg["cells"],
            "unavailable_count": pdg["unavailable_count"]}


def _string_level(index, design, split) -> dict:
    per, bits = [], []
    for cid, sp, fam, bl, rep, rg, n in V.expected_cases(design, split):
        if fam in STRUCTURED and cid in index:
            spb, sb, a = string_saving(index[cid])
            if spb is not None:
                per.append(spb)
                bits.append(sb)
    if not bits:
        return {}
    return {"strings": len(bits), "mean_saving_bits": float(np.mean(bits)),
            "median_saving_bits": float(np.median(bits)),
            "mean_saving_per_input_bit_unweighted": float(np.mean(per)),
            "median_saving_per_input_bit": float(np.median(per)),
            "strings_hid_better": int(sum(b > 0 for b in bits)),
            "strings_tied": int(sum(b == 0 for b in bits)),
            "strings_hid_worse": int(sum(b < 0 for b in bits))}


def representative_ledgers(d: Path, rows) -> list[dict]:
    """One case per (split, family, base_length): lowest replicate, base length,
    the HID-full archive and the portfolio's selected archive, with byte ledgers
    read from the stored bytes and the decoded expansion cross-checked.

    A chosen archive that is missing, differs from its row's hash or does not decode
    is presented as ``unavailable`` with the reason; ``validate_run`` has already
    made such a run engineering-invalid, so nothing here is evidence of success."""
    import hashlib

    from .decode import ArchiveError, decode_archive
    from .ledger import archive_ledger, explain_model
    pick: dict = {}
    for r in rows:
        if r["ragged"] or r["method"] not in ("hid_full", "baseline_best") or not r["archive_path"]:
            continue
        key = (r["split"], r["family"], r["base_length"])
        cur = pick.get(key, {}).get("replicate")
        if cur is None or r["replicate"] < cur:
            pick[key] = {"replicate": r["replicate"]}
        if r["replicate"] == pick[key]["replicate"]:
            pick[key][r["method"]] = r
    out = []
    for key in sorted(pick):
        entry = {"split": key[0], "family": key[1], "base_length": key[2],
                 "replicate": pick[key]["replicate"]}
        for m in ("hid_full", "baseline_best"):
            r = pick[key].get(m)
            if r is None:
                continue
            p = d / r["archive_path"]
            if not p.is_file():
                entry[m] = _unavailable(r, "archive file missing")
                continue
            data = p.read_bytes()
            if hashlib.sha256(data).hexdigest() != r["archive_sha256"]:
                entry[m] = _unavailable(r, "archive hash differs from the row")
                continue
            try:
                decoded = decode_archive(data)
            except ArchiveError as exc:
                entry[m] = _unavailable(r, f"archive does not decode: {type(exc).__name__}: {exc}")
                continue
            led = archive_ledger(data)
            item = {"case_id": r["case_id"], "input_sha256": r["input_sha256"],
                    "archive_sha256": r["archive_sha256"], "archive_bits": 8 * len(data),
                    "codec": led["codec"], "bytes_by_owner": led["bytes_by_owner"],
                    "ledger_sum_bits": 8 * sum(f["bytes"] for f in led["fields"]),
                    "fields": led["fields"] if len(led["fields"]) <= 400 else
                    led["fields"][:400] + [{"truncated": len(led["fields"]) - 400}],
                    "decoded_sha256": _sha(decoded)}
            if led["model"] is not None:
                if led["model"].expand() != decoded:
                    raise AssertionError("encoder evaluator and decoder disagree")
                item["graph"] = explain_model(led["model"])
            entry[m] = item
        out.append(entry)
    return out


def _unavailable(r: dict, reason: str) -> dict:
    return {"case_id": r["case_id"], "archive_path": r["archive_path"],
            "archive_sha256": r["archive_sha256"], "unavailable": reason}


def _sha(s: str) -> str:
    import hashlib
    return hashlib.sha256(s.encode("ascii")).hexdigest()


def _selected_counts(rows) -> dict:
    out = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["method"] == "baseline_best" and r["selected_method"]:
            out[f"{r['split']}|{r['family']}"][r["selected_method"]] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


def _stop_counts(rows) -> dict:
    out = defaultdict(lambda: defaultdict(int))
    for r in rows:
        if r["method"].startswith("hid_"):
            out[f"{r['split']}|{r['method']}"][str(r["stop_reason"] or r["status"])] += 1
    return {k: dict(v) for k, v in sorted(out.items())}


# ---------------------------------------------------------------------------
# Claim ledger
# ---------------------------------------------------------------------------

LEDGER_STATUS = {"supported": "supported", "not_supported": "not_supported",
                 "inconclusive": "inconclusive", "not_assessed": "inconclusive"}


def _gate_note(gate: dict | None) -> str:
    if gate is None:
        return "no gate recorded"
    if not gate["engineering_valid"]:
        return "NOT ASSESSED: engineering validation failed"
    if not gate["complete"]:
        return f"NOT ASSESSED: population incomplete ({gate['missing_count']} rows absent)"
    if gate["censored_count"]:
        return f"inconclusive by censoring ({gate['censored_count']} censored rows)"
    return "gates passed: valid, complete, uncensored"


def claim_ledger(summary: dict, diagnostics: dict | None, run_id: str) -> list[dict]:
    """One row per headline claim. A ``not_assessed`` decision is written as status
    ``inconclusive`` (the protocol's four statuses) with the failed gate stated."""
    led = []
    base = f"results/hierarchy_v1/{run_id}"
    p = summary.get("primary", {})
    led.append({
        "id": "C1", "claim": "HID-v1 (full) yields an average code-length gain over the "
                             "strong decodable baseline portfolio on the prespecified "
                             "structured confirmation benchmark",
        "status": LEDGER_STATUS[p.get("verdict", "not_assessed")],
        "decision": p.get("verdict"), "evidence_gate": _gate_note(p.get("gate")),
        "metric": "equal-family, equal-size mean of (baseline_best_bits - hid_full_bits)/n",
        "estimate": p.get("estimate_mean_saving_per_input_bit"), "uncertainty": p.get("ci95"),
        "evidence": [f"{base}/summary.json#primary",
                     f"{base}/cases.jsonl (split=confirmation, "
                     f"families {','.join(STRUCTURED)}, methods hid_full, baseline_best)"],
        "domain": "families F01-F06, F12; base lengths 256, 1024, 4096 plus ragged +3; "
                  "replicates 1000-1019; frozen search budget",
        "caveat": "a code-length comparison of the best archive found under a fixed language "
                  "and budget; not K, not generator recovery, not prediction"})
    val = summary.get("validation", {})
    rt = summary.get("round_trips", {})
    c2 = bool(val.get("engineering_valid")) and rt.get("decode_failed") == 0
    led.append({
        "id": "C2", "claim": "Every stored archive decodes exactly to its input with the "
                             "independent decoder",
        "status": "supported" if c2 else "not_supported",
        "decision": "supported" if c2 else "not_supported",
        "evidence_gate": "engineering validation of every declared row and archive",
        "metric": "archives decoded and hash-matched / archives promised by row statuses",
        "estimate": {"archives_checked": val.get("archives_checked"),
                     "distinct_archives_decoded": val.get("distinct_archives_decoded"), **rt},
        "uncertainty": None,
        "evidence": [f"{base}/verification.json", f"{base}/summary.json#validation"],
        "domain": "all splits run under this run id", "caveat": "engineering claim"})
    for i, (a, v) in enumerate(sorted(summary.get("ablations", {}).items())):
        reading = v["component_advantage"]
        st = {"supported": "supported", "ablation_better": "not_supported",
              "not_detected": "inconclusive", "not_assessed": "inconclusive"}[reading]
        led.append({
            "id": f"C3.{i + 1}", "claim": f"The component removed in {a} contributes a "
                                          "code-length advantage to the full search",
            "status": st, "decision": reading,
            "evidence_gate": _gate_note(summary.get("ablations_gate")),
            "metric": "equal-weight mean of (ablation_bits - full_bits)/n",
            "estimate": v.get("incremental_gain_per_input_bit"), "uncertainty": v.get("ci99"),
            "evidence": [f"{base}/summary.json#ablations.{a}"],
            "domain": "structured confirmation population",
            "caveat": "99% Bonferroni intervals; describes the configured algorithm under the "
                      "frozen budget: removing a component also changes what the bounded "
                      "search reaches, so this is not a language-intrinsic contribution"})
    t = summary.get("transfer_structured_aggregate")
    if t:
        led.append({
            "id": "C4", "claim": "At 16,384 and 65,536 bits HID-v1 (full) has a positive "
                                 "equal-weight mean saving over the nine-code portfolio on "
                                 "the structured families",
            "status": LEDGER_STATUS[t["reading"]], "decision": t["reading"],
            "evidence_gate": _gate_note(t["gate"]),
            "metric": "primary endpoint arithmetic on the transfer split",
            "estimate": t.get("estimate"), "uncertainty": t.get("ci95_descriptive"),
            "evidence": [f"{base}/summary.json#transfer_structured_aggregate"],
            "domain": "transfer split, families F01-F06, F12, replicates 2000-2003 (four units "
                      "per cell), seed 33005",
            "caveat": "descriptive only. The reserved transfer seeds and the held-out families "
                      "F03, F10, F11, F12 were not used before the freeze, but 65,536-bit "
                      "development_resource probes (development families and parameter "
                      "ranges) informed the work-cap choice, so 65,536 bits is not an unseen "
                      "length"})
    c = summary.get("controls_aggregate")
    if c:
        led.append({
            "id": "C5", "claim": "On the statistical controls F07-F09 HID-v1 (full) has a "
                                 "positive equal-weight aggregate saving over the nine-code "
                                 "portfolio",
            "status": LEDGER_STATUS[c["reading"]], "decision": c["reading"],
            "evidence_gate": _gate_note(c["gate"]),
            "metric": "primary endpoint arithmetic, equal weights over F07-F09 cells",
            "estimate": c.get("estimate"), "uncertainty": c.get("ci95_descriptive"),
            "evidence": [f"{base}/summary.json#controls_aggregate",
                         f"{base}/summary.json#controls_vs_statistical_codes"],
            "domain": "confirmation F07-F09, seed 33006",
            "caveat": "descriptive. An aggregate over three families says nothing about each "
                      "family; failure to show an advantage is not equivalence. Against the "
                      "better of the Bernoulli and context codes alone the comparison differs "
                      "by family (controls_vs_statistical_codes, descriptive), because raw "
                      "fallback and code overheads enter both sides"})
    if diagnostics:
        led.append({
            "id": "C6", "claim": "Aligned/full-coverage BDM, with setting selection calibrated "
                                 "symmetrically on marginal-preserving nulls, separates the "
                                 "structured diagnostic objects from bit shuffles",
            "status": diagnostics.get("claim_status", "inconclusive"),
            "decision": diagnostics.get("claim_status"),
            "evidence_gate": "diagnostics.json written under a validated freeze and environment",
            "metric": "adaptive p-value (r+1)/(B+1), Holm-adjusted across ten objects",
            "estimate": {k: v["adaptive_p"] for k, v in diagnostics.get("objects", {}).items()},
            "uncertainty": "Monte Carlo, 199 nulls",
            "evidence": [f"{base}/diagnostics.json"],
            "domain": "replicate 1000, base length 1024, non-ragged",
            "caveat": "marginal shuffle null; says nothing beyond bit marginals for F09; "
                      "BDM is a diagnostic score, never stored bytes"})
    for cid, text in (("C7", "HID-v1 computes or estimates Kolmogorov complexity"),
                      ("C8", "An inferred description is the unique generating mechanism"),
                      ("C9", "Full-string compression establishes prediction of unseen suffixes"),
                      ("C10", "The study establishes causal identification or priority of "
                              "hierarchical grammar coding")):
        led.append({"id": cid, "claim": text, "status": "out_of_scope", "decision": None,
                    "evidence_gate": None, "metric": None,
                    "estimate": None, "uncertainty": None, "evidence": [
                        "PROTOCOL_hierarchical_index_generalization.md section 1"],
                    "domain": None, "caveat": "not tested by this design"})
    return led
