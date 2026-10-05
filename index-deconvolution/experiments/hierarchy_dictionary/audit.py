"""Independent read-only arithmetic audit (ACCEPTANCE 7).

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_dictionary.audit [OUT_JSON]

Reads CASES.json, PREVIOUS_A3.json, the row files, the stored archive BYTES and the
traces; recomputes every length, the 96 reference minima (owner tie rule re-implemented
here as arithmetic: shortest, then lowest codec id), every contrast at string, pair and
cell level with full denominators, the sign counts, the selection invariants, the
nesting invariants and the exploratory label, then compares with ``summary.json``. It
imports nothing from ``report`` or ``search``, uses no summary aggregate as an input and
launches no encoder. Shared owner reused on purpose: ``hierarchy.decode`` (the
independent, standard-library decoder, which is the protocol's authority for exactness).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from hierarchy.decode import decode_archive

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
RUN = ID_ROOT / "results" / "hierarchy_dictionary_v1" / "dictionary-feasibility-v1-r1"
CASES = ID_ROOT / "protocols" / "hierarchy_multilevel_v1" / "CASES.json"
PREV = ID_ROOT / "protocols" / "hierarchy_dictionary_v1" / "PREVIOUS_A3.json"
NINE = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma", "pair_grammar")
ARMS = ("D0", "D1", "D2")
VALID = ("ok", "watchdog_timeout_fallback", "watchdog_rss_fallback")
PAIRS = (("D0", "oldA3"), ("D1", "D0"), ("D2", "D1"), ("D0", "A0"), ("D1", "A0"), ("D2", "A0"),
         ("D0", "pair_grammar"), ("D1", "pair_grammar"), ("D2", "pair_grammar"),
         ("D0", "portfolio"), ("D1", "portfolio"), ("D2", "portfolio"),
         ("A0", "pair_grammar"), ("A0", "portfolio"), ("oldA3", "A0"))
TOL = 1e-12


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def _signs(vals) -> dict:
    v = [x for x in vals if x is not None]
    return {"better": sum(x > 0 for x in v), "tie": sum(x == 0 for x in v), "worse": sum(x < 0 for x in v),
            "available": len(v), "unavailable": sum(x is None for x in vals)}


def audit(run: Path = RUN) -> dict:
    cases = json.loads(CASES.read_text())["cases"]
    prev = {r["case_id"]: r for r in json.loads(PREV.read_text())["records"]}
    summ = json.loads((run / "summary.json").read_text())
    problems: list[str] = []
    bits: dict[str, dict] = {}
    n_of: dict[str, int] = {}
    archives_read = decodes = cand_checked = 0
    decoded_ok: dict[str, str] = {}

    def decodes_to(data: bytes, x: str) -> bool:
        nonlocal decodes
        k = h(data)
        if k not in decoded_ok:
            decodes += 1
            decoded_ok[k] = decode_archive(data)
        return decoded_ok[k] == x

    complete_rows = 0
    for c in cases:
        cid = c["case_id"]
        raw = (REPO / c["references"]["raw"]["archive_path"]).read_bytes()
        x = decode_archive(raw)
        decodes += 1
        if h(x.encode()) != c["input_sha256"] or len(x) != c["n_bits"]:
            problems.append(f"{cid}: input")
        n_of[cid] = len(x)
        rec: dict = {}
        arcs = {}
        for m in NINE:
            data = (REPO / c["references"][m]["archive_path"]).read_bytes()
            archives_read += 1
            if h(data) != c["references"][m]["archive_sha256"]:
                problems.append(f"{cid}.{m}: reference hash")
            if not decodes_to(data, x):
                problems.append(f"{cid}.{m}: reference decode")
            arcs[m] = data
        lo = min(len(a) for a in arcs.values())
        best = sorted((a[4], m) for m, a in arcs.items() if len(a) == lo)[0][1]
        if h(arcs[best]) != c["references"]["baseline_best"]["archive_sha256"]:
            problems.append(f"{cid}: portfolio minimum differs from saved baseline_best")
        rec["pair_grammar"] = 8 * len(arcs["pair_grammar"])
        rec["portfolio"] = 8 * lo
        # imported old A3, from its own record
        p = prev[cid]
        oa = (REPO / p["archive_path"]).read_bytes()
        archives_read += 1
        okp = (h(oa) == p["archive_sha256"] and h((REPO / p["row_path"]).read_bytes()) == p["row_sha256"]
               and h((REPO / p["trace_path"]).read_bytes()) == p["trace_sha256"] and decodes_to(oa, x))
        if not okp:
            problems.append(f"{cid}: old A3 record")
        rec["oldA3"] = 8 * len(oa) if okp else None
        old_tr = json.loads((REPO / p["trace_path"]).read_text())
        rows = {}
        for arm in ("A0",) + ARMS:
            q = run / "rows" / f"{cid}.{arm}.json"
            if not q.is_file():
                rec[arm] = None
                continue
            row = rows[arm] = json.loads(q.read_text())
            if not row.get("archive_path"):
                rec[arm] = None
                continue
            data = (run / row["archive_path"]).read_bytes()
            archives_read += 1
            if h(data) != row["archive_sha256"] or 8 * len(data) != row["archive_bits"]:
                problems.append(f"{cid}.{arm}: stored archive disagrees with row")
            if not decodes_to(data, x):
                problems.append(f"{cid}.{arm}: archive does not decode to the input")
            ok = row["status"] == "ok" if arm == "A0" else row["status"] in VALID
            rec[arm] = 8 * len(data) if ok else None
        if "A0" in rows and rows["A0"].get("archive_sha256") != c["references"]["hid_full"]["archive_sha256"]:
            problems.append(f"{cid}: A0 archive differs from the saved k=1 archive")
        traces = {}
        for arm in ARMS:
            row = rows.get(arm)
            if not row or row.get("validity") != "valid" or rec.get("A0") is None:
                continue
            a0 = rec["A0"]
            if rec[arm] > a0:
                problems.append(f"{cid}.{arm}: composite longer than A0")
            if row["status"] != "ok":
                continue
            complete_rows += 1
            tb = (run / row["trace_path"]).read_bytes()
            if h(tb) != row["trace_sha256"]:
                problems.append(f"{cid}.{arm}: trace hash")
            tr = traces[arm] = json.loads(tb)
            for hh in row.get("candidate_archives") or []:
                data = (run / "archives" / hh[:2] / f"{hh}.isd").read_bytes()
                archives_read += 1
                cand_checked += 1
                if h(data) != hh or not decodes_to(data, x):
                    problems.append(f"{cid}.{arm}: candidate {hh[:12]} hash/decode")
            cands = []
            for v in tr["views"]:
                for m in v.get("modes", []):
                    lo_, hi_ = m["proposal_range"]
                    ps = [pp for pp in v["proposals"][lo_:hi_] if pp["archive_bits"] is not None]
                    mb = min((pp["archive_bits"] for pp in ps), default=None)
                    if mb != m["best_bits"]:
                        problems.append(f"{cid}.{arm}: view {v['view_index']} {m['mode']} best bits")
                    if m["best_sha256"] is not None and m["best_sha256"] not in (row.get("candidate_archives") or []):
                        problems.append(f"{cid}.{arm}: view {v['view_index']} {m['mode']} best archive not retained")
                for pp in v["proposals"]:
                    if pp["archive_bits"] is not None and pp["status"] == "SERIALIZED_DECODED":
                        cands.append((pp["archive_bits"], pp["request_ordinal"], pp))
            better = [t for t in cands if t[0] < a0]
            sel = row["selected"]
            if not better:
                if sel["source"] != "A0" or row["archive_sha256"] != rows["A0"]["archive_sha256"]:
                    problems.append(f"{cid}.{arm}: no shorter candidate but A0 not retained")
            else:
                first_min = min(better, key=lambda t: (t[0], t[1]))[2]
                if sel.get("mode") != first_min["mode"] or sel.get("proposal") != first_min["proposal"] \
                        or first_min["archive_sha256"] != row["archive_sha256"] or not first_min["accepted"]:
                    problems.append(f"{cid}.{arm}: selected archive is not the first strict minimum")
            req = [pp["request_ordinal"] for v in tr["views"] for pp in v["proposals"]
                   if pp.get("request_ordinal") is not None]
            if req != list(range(1, len(req) + 1)) or len(req) != tr["counters"]["requests"]:
                problems.append(f"{cid}.{arm}: request ordinals/counter")
        # nesting on complete searches
        for a, b in (("D0", "oldA3"), ("D1", "D0"), ("D2", "D1")):
            if a in traces and rec[a] is not None and rec[b] is not None and rec[a] > rec[b]:
                problems.append(f"{cid}: nesting {a} > {b}")
        if "D0" in traces:
            byk = {(v["level"], v["width"], v["origin"]): v for v in traces["D0"]["views"]}
            for v in old_tr["views"]:
                if v["status"] != "EVALUATED":
                    continue
                mv = byk.get((v["level"], v["width"], v["origin"]))
                mine = [pp["archive_sha256"] for pp in (mv or {}).get("proposals", []) if pp["mode"] == "O"]
                if mine != [pp["archive_sha256"] for pp in v["proposals"]]:
                    problems.append(f"{cid}: old A3 view {v['level']}-{v['width']}-{v['origin']} not in D0 O")
        bits[cid] = rec
    complete = summ["evidence_state"]["state"] == "VALID_COMPLETE"
    recomputed = {}
    for a, b in PAIRS:
        per = {cid: (None if r[a] is None or r[b] is None else (r[b] - r[a]) / n_of[cid])
               for cid, r in bits.items()}
        reps: dict = {}
        for c in cases:
            reps.setdefault((c["family"], c["base_length"]), {}).setdefault(c["replicate"], []).append(per[c["case_id"]])
        pair_vals, cell_mean = [], {}
        for key, rr in reps.items():
            rv = [None if None in v else sum(v) / len(v) for v in rr.values()]
            pair_vals += rv
            cell_mean[key] = None if None in rv else sum(rv) / len(rv)
        cv = list(cell_mean.values())
        agg = None if None in cv else sum(cv) / len(cv)
        name = f"{a}_vs_{b}"
        s = summ["contrasts"][name]
        mine, pm, cm = _signs(list(per.values())), _signs(pair_vals), _signs(cv)
        for lab, x, y in (("strings", mine, s["strings"]), ("pairs", pm, s["pairs_sign"]), ("cells", cm, s["cells_sign"])):
            if x != y:
                problems.append(f"{name}: {lab} sign counts {x} vs {y}")
        if complete:
            if agg is None or s["aggregate"] is None or abs(agg - s["aggregate"]) > TOL:
                problems.append(f"{name}: aggregate {agg} vs {s['aggregate']}")
        elif s["aggregate"] is not None:
            problems.append(f"{name}: aggregate reported on an incomplete/invalid state")
        for cid, v in per.items():
            sv = s["per_string"][cid]
            if (v is None) != (sv is None) or (v is not None and abs(v - sv) > TOL):
                problems.append(f"{name}: per-string {cid}")
        if len(per) != 96 or len(pair_vals) != 48 or len(cell_mean) != 24:
            problems.append(f"{name}: denominators {len(per)}/{len(pair_vals)}/{len(cell_mean)}")
        recomputed[name] = {"aggregate": agg, "strings": mine, "pairs": pm, "cells": cm}
    label = None
    if complete:
        if any(r["D2"] < r["D1"] for r in bits.values()):
            label = "RELATION_GAIN_OBSERVED"
        elif any(r["D1"] < r["D0"] for r in bits.values()):
            label = "PERIOD_GAIN_OBSERVED"
        elif any(r["D0"] < r["A0"] for r in bits.values()):
            label = "CONTROL_ONLY_GAIN"
        else:
            label = "NO_RETAINED_GAIN"
    if label != summ["recommendation"]["label"]:
        problems.append(f"label {label} vs {summ['recommendation']['label']}")
    for cid, r in bits.items():
        for k, v in r.items():
            if summ["bits"][cid][k] != v:
                problems.append(f"bits {cid}.{k}: {v} vs {summ['bits'][cid][k]}")
    return {"pass": not problems, "problems": problems[:200], "problem_count": len(problems),
            "archives_read": archives_read, "decodes": decodes, "candidate_archives_checked": cand_checked,
            "complete_rows_checked": complete_rows, "strings": len(cases),
            "recomputed": recomputed, "recommendation_label": label,
            "reused_owners": {"hierarchy.decode": "independent decoder (standard library only); "
                              "shared on purpose because exactness is defined by it"},
            "not_used": ["report.py", "search.py", "any encoder", "summary aggregates as inputs",
                         "old_a3.jsonl (old A3 re-read from PREVIOUS_A3.json)"]}


if __name__ == "__main__":
    out = audit()
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN / "arithmetic_audit.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("pass", "problem_count", "archives_read", "decodes",
                                          "candidate_archives_checked", "recommendation_label")}))
    sys.exit(0 if out["pass"] else 1)
