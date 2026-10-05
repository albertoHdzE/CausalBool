"""HID-search-v2 diagnostics, computed only after automatic rows exist (SEARCH.md 4).

* exact cost buckets of every deployed HID and portfolio archive (``ledger.field_buckets``,
  sums asserted equal to 8 x bytes), by role, family, size and method;
* stage yield and cost from the row telemetry;
* evaluation-only SUPPLIED-BOUNDARY REFERENCES for every F12 and S02 scored string:
  the generator's declared construction cuts mapped through its edits, partitioned with
  the same B leaf builder, sharing and serializer, saved and decoded. Signed gap
  (bits(hid_full) - min(reference, raw)) / n. A restricted feasible reference, not an
  oracle optimum and not a bound on all search error; never a benchmark method or an
  incumbent. The earlier handcrafted F12 witness is listed separately with its
  original post-hoc label.

Diagnostic outputs live under ``diagnostics/`` and ``diagnostics.json``, never in
``rows/`` or ``cases.jsonl``.
"""
from __future__ import annotations

import hashlib
import json
import statistics
import time
from collections import defaultdict
from pathlib import Path

from .decode import decode_archive
from .ledger import BUCKET_RULES, BUCKETS, field_buckets
from .segmentation import supplied_partition
from .study_corpus import boundary_reference_cuts, unit_metadata
from .wire import encode_literal

WITNESS = "index-deconvolution/results/hierarchy_v1_supervision/confirm-v1/F12_oracle_boundaries_witness.isd"
BUCKET_METHODS = ("hid_legacy", "hid_first_local", "hid_consensus_local", "hid_dense_local",
                  "hid_global", "hid_full", "baseline_best")


def _sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def buckets(d: Path, rows) -> dict:
    cache, acc = {}, {}
    checked = 0
    unavailable: list[str] = []
    for r in rows:
        if r["method"] not in BUCKET_METHODS or not r.get("archive_path"):
            continue
        h = r["archive_sha256"]
        if h not in cache:
            p = d / r["archive_path"]
            data = p.read_bytes() if p.is_file() else None
            ok = data is not None and _sha(data) == h
            cache[h] = field_buckets(data) if ok else None
            checked += int(ok)
        if cache[h] is None:
            unavailable.append(f"{r['case_id']}:{r['method']}")
            continue
        key = f"{r['split']}|{r['family']}|{r['base_length']}|{r['method']}"
        a = acc.setdefault(key, {"archives": 0, "bits": dict.fromkeys(BUCKETS, 0), "total": 0})
        a["archives"] += 1
        a["total"] += r["archive_bits"]
        for b in BUCKETS:
            a["bits"][b] += cache[h][b]
    for a in acc.values():
        if sum(a["bits"].values()) != a["total"]:
            raise AssertionError("bucket sums differ from archive lengths")
    return {"bucket_rules": BUCKET_RULES, "distinct_archives_parsed": checked,
            "unavailable_archives": unavailable[:200],
            "exact_sum_check": "every archive: sum of buckets == 8 x bytes (asserted)",
            "by_cell_method": {k: {"archives": v["archives"], "total_bits": v["total"],
                                   "bits": v["bits"]} for k, v in sorted(acc.items())}}


def stage_yield(rows) -> dict:
    out: dict = {}
    for r in rows:
        t = r.get("search_counters") or {}
        if r.get("status") != "ok" or "stages" not in t:
            continue
        key = f"{r['split']}|{r['family']}|{r['method']}"
        o = out.setdefault(key, {"rows": 0, "selected": defaultdict(int), "stages": {}})
        o["rows"] += 1
        o["selected"][t.get("selected_stage")] += 1
        for s, st in t["stages"].items():
            a = o["stages"].setdefault(s, defaultdict(float))
            for k in ("periods_attempted", "gate_rejections", "graph_rejections", "serialized",
                      "decoded", "duplicate_archives", "strict_improvements", "wall_s"):
                if isinstance(st.get(k), (int, float)):
                    a[k] += st[k]
            if s == "B":
                for k, v in st["counts"].items():
                    a[f"B_{k}"] += v
                a["B_cap_hit"] += int(bool(st.get("cap_hit")))
    return {k: {"rows": v["rows"], "selected": dict(v["selected"]),
                "stages": {s: dict(a) for s, a in v["stages"].items()}}
            for k, v in sorted(out.items())}


def boundary_gap_summary(items) -> dict:
    """Per role|family|base_length cell: counts and signed ``hid_full`` gap summaries.

    ``gap_median`` is the conventional sample median (``statistics.median``): the middle
    value for an odd count and the mean of the two middle values for an even count;
    ``None`` for a cell without gaps. Units are bits per input bit.
    """
    summary = defaultdict(lambda: {"strings": 0, "available": 0, "gaps": []})
    for it in items:
        k = f"{it['role']}|{it['family']}|{it['base_length']}"
        summary[k]["strings"] += 1
        if it.get("available"):
            summary[k]["available"] += 1
            if "gap_hid_full_per_input_bit" in it:
                summary[k]["gaps"].append(it["gap_hid_full_per_input_bit"])
    agg = {}
    for k, v in sorted(summary.items()):
        g = sorted(v["gaps"])
        agg[k] = {"strings": v["strings"], "available": v["available"],
                  "gap_mean": sum(g) / len(g) if g else None,
                  "gap_median": statistics.median(g) if g else None,
                  "automatic_shorter_than_reference": sum(1 for x in g if x < 0),
                  "automatic_longer_than_reference": sum(1 for x in g if x > 0),
                  "ties": sum(1 for x in g if x == 0)}
    return agg


def boundary_references(study, run_id: str, d: Path, index: dict, roles) -> dict:
    out_dir = d / "diagnostics" / "boundary_reference"
    items = []
    for role in roles:
        spec = study.role(role)
        fams = [f for f in spec.families if f in ("F12", "S02")]
        if not fams:
            continue
        mp = d / f"corpus_manifest.{role}.jsonl"
        manifest = [json.loads(ln) for ln in mp.read_text().splitlines() if ln.strip()]
        meta = unit_metadata(manifest)
        cases, _ = study.role_cases(role, d)
        for c in cases:
            if c.family not in fams:
                continue
            N, params = meta[(c.family, c.base_length, c.replicate)]
            ref = boundary_reference_cuts(c.family, params, N, len(c.bits))
            have = index.get(c.case_id, {})
            full = have.get("hid_full")
            item = {"case_id": c.case_id, "role": role, "family": c.family,
                    "base_length": c.base_length, "replicate": c.replicate, "ragged": c.ragged,
                    "n_bits": len(c.bits), "label": "evaluation-only supplied-boundary "
                    "feasible reference (not an oracle optimum)"}
            raw_bits = 8 * len(encode_literal(c.bits))
            if not ref["available"]:
                item.update(available=False, reason=ref["reason"])
                items.append(item)
                continue
            part = supplied_partition(c.bits, ref["cuts"])
            arc = part["archive"]
            if arc is None:
                item.update(available=False, reason="partition violates graph limits")
                items.append(item)
                continue
            ok = decode_archive(arc) == c.bits
            if not ok:
                raise AssertionError(f"supplied-boundary reference of {c.case_id} does not decode")
            h = _sha(arc)
            p = out_dir / "archives" / h[:2] / f"{h}.isd"
            p.parent.mkdir(parents=True, exist_ok=True)
            if not p.exists():
                p.write_bytes(arc)
            feasible = min(8 * len(arc), raw_bits)
            item.update(available=True, cuts=ref["cuts"], derivation=ref["derivation"],
                        leaves=part["leaves"], reference_bits=8 * len(arc),
                        reference_archive=str(p.relative_to(d)), reference_sha256=h,
                        decode_ok=ok, raw_bits=raw_bits, feasible_bits=feasible)
            for m in ("hid_full", "hid_global", "hid_legacy"):
                r = have.get(m)
                if r is not None and r.get("archive_bits") is not None:
                    item[f"{m}_bits"] = r["archive_bits"]
                    item[f"{m}_status"] = r["status"]
                    item[f"gap_{m}_per_input_bit"] = (r["archive_bits"] - feasible) / len(c.bits)
            if full is None:
                item["note"] = "hid_full row absent"
            items.append(item)
    agg = boundary_gap_summary(items)
    (out_dir).mkdir(parents=True, exist_ok=True)
    (out_dir / "references.json").write_text(json.dumps(items, indent=1) + "\n")
    return {"label": "EVALUATION-ONLY supplied-boundary feasible references; truth used only "
                     "after automatic encoding; not an oracle optimum or bound on search error",
            "gap_definition": "(bits(method) - min(bits(reference), bits(raw))) / n; negative "
                              "means the automatic archive is shorter",
            "items_path": str((out_dir / "references.json").relative_to(d)),
            "by_cell": agg, "strings": len(items),
            "available": sum(1 for it in items if it.get("available"))}


def witness(index: dict) -> dict:
    from .study import REPO
    p = REPO / WITNESS
    if not p.exists():
        return {"available": False}
    data = p.read_bytes()
    bits = decode_archive(data)
    h = hashlib.sha256(bits.encode()).hexdigest()
    match = [cid for cid, m in index.items()
             if any(r.get("input_sha256") == h for r in m.values())]
    return {"label": "earlier handcrafted F12 witness: supplied construction boundaries, "
                     "metadata-assisted, POST-HOC; not an automatic-search result",
            "path": WITNESS, "archive_bits": 8 * len(data), "archive_sha256": _sha(data),
            "input_sha256": h, "matching_case_ids_in_this_run": sorted(match),
            "rows_for_match": {cid: {m: index[cid][m]["archive_bits"]
                                     for m in ("hid_legacy", "hid_full", "baseline_best")
                                     if m in index[cid]} for cid in sorted(match)}}


def run(study, run_id: str, validation: dict, roles) -> dict:
    t0 = time.time()
    d = study.run_dir(run_id)
    index = validation["_index"]
    rows = sorted((r for m in index.values() for r in m.values()),
                  key=lambda r: (r["case_id"], r["method"]))
    out = {"run_id": run_id, "study": study.name,
           "status": "diagnostic; computed after automatic rows; never a benchmark endpoint",
           "cost_buckets": buckets(d, rows), "stage_yield": stage_yield(rows),
           "supplied_boundary_references": boundary_references(study, run_id, d, index, roles),
           "handcrafted_witness": witness(index)}
    out["wall_s"] = time.time() - t0
    return out
