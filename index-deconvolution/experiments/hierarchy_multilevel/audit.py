"""Independent read-only arithmetic audit (ACCEPTANCE 8).

    (from index-deconvolution/) PYTHONPATH=experiments:.:../src ../venv/bin/python -B \
        -m hierarchy_multilevel.audit [OUT_JSON]

Reads CASES.json, the row files, the stored archive BYTES, the traces and
``summary.json``; recomputes every length, every reference minimum, every contrast at
every level, the denominators, the sign counts, the selection invariants and the
exploratory label with its own arithmetic. It imports nothing from ``report`` and runs
no encoder. Shared owners reused on purpose: ``hierarchy.decode`` (the independent
decoder, standard library only, which is the protocol's authority for exactness).
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

from hierarchy.decode import decode_archive

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
RUN = ID_ROOT / "results" / "hierarchy_multilevel_v1" / "multilevel-feasibility-v1-r1"
CASES = ID_ROOT / "protocols" / "hierarchy_multilevel_v1" / "CASES.json"
NINE = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma", "pair_grammar")
ARMS = ("A1", "A2", "A3")
TOL = 1e-12


def h(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def audit(run: Path = RUN) -> dict:
    cases = json.loads(CASES.read_text())["cases"]
    summ = json.loads((run / "summary.json").read_text())
    problems: list[str] = []
    bits: dict[str, dict] = {}
    n_of: dict[str, int] = {}
    archives_read = decodes = 0
    for c in cases:
        cid = c["case_id"]
        raw = (REPO / c["references"]["raw"]["archive_path"]).read_bytes()
        x = decode_archive(raw)
        decodes += 1
        if h(x.encode()) != c["input_sha256"] or len(x) != c["n_bits"]:
            problems.append(f"{cid}: input")
        n_of[cid] = len(x)
        rec: dict = {}
        # imported references and the portfolio minimum
        arcs = {}
        for m in NINE:
            data = (REPO / c["references"][m]["archive_path"]).read_bytes()
            archives_read += 1
            if h(data) != c["references"][m]["archive_sha256"]:
                problems.append(f"{cid}.{m}: reference hash")
            if decode_archive(data) != x:
                problems.append(f"{cid}.{m}: reference decode")
            decodes += 1
            arcs[m] = data
        lo = min(len(a) for a in arcs.values())
        tied = sorted((a[4], a, m) for m, a in arcs.items() if len(a) == lo)
        best = tied[0][2]
        if h(arcs[best]) != c["references"]["baseline_best"]["archive_sha256"]:
            problems.append(f"{cid}: portfolio minimum differs from saved baseline_best")
        rec["pair_grammar"] = 8 * len(arcs["pair_grammar"])
        rec["portfolio"] = 8 * lo
        # A0 and composites from stored bytes
        rows = {}
        for arm in ("A0",) + ARMS:
            p = run / "rows" / f"{cid}.{arm}.json"
            if not p.is_file():
                rec[arm] = None
                continue
            row = rows[arm] = json.loads(p.read_text())
            if not row.get("archive_path"):
                rec[arm] = None
                continue
            data = (run / row["archive_path"]).read_bytes()
            archives_read += 1
            if h(data) != row["archive_sha256"] or 8 * len(data) != row["archive_bits"]:
                problems.append(f"{cid}.{arm}: stored archive disagrees with row")
            if decode_archive(data) != x:
                problems.append(f"{cid}.{arm}: archive does not decode to the input")
            decodes += 1
            ok = row["status"] == "ok" if arm == "A0" else row["status"] in (
                "ok", "watchdog_timeout_fallback", "watchdog_rss_fallback")
            rec[arm] = 8 * len(data) if ok else None
        if "A0" in rows and rows["A0"].get("archive_sha256") != c["references"]["hid_full"]["archive_sha256"]:
            problems.append(f"{cid}: A0 archive differs from the saved k=1 archive")
        # selection invariants
        for arm in ARMS:
            row = rows.get(arm)
            if not row or row.get("validity") != "valid" or rec.get("A0") is None:
                continue
            a0 = rec["A0"]
            if rec[arm] > a0:
                problems.append(f"{cid}.{arm}: composite longer than A0")
            if row["status"] != "ok":
                continue
            tr = json.loads((run / row["trace_path"]).read_text())
            if h((run / row["trace_path"]).read_bytes()) != row["trace_sha256"]:
                problems.append(f"{cid}.{arm}: trace hash")
            cands = [(p["archive_bits"], v["view_index"], i, p) for v in tr["views"]
                     for i, p in enumerate(v["proposals"]) if p["archive_bits"] is not None
                     and p["status"] == "SERIALIZED_DECODED"]
            better = [t for t in cands if t[0] < a0]
            sel = row["selected"]
            if not better:
                if sel["source"] != "A0" or row["archive_sha256"] != rows["A0"]["archive_sha256"]:
                    problems.append(f"{cid}.{arm}: no shorter candidate but A0 not retained")
            else:
                first_min = min(better, key=lambda t: (t[0], t[1], t[2]))
                p = first_min[3]
                if sel.get("view_index") != first_min[1] or sel.get("proposal") != p["proposal"] \
                        or p["archive_sha256"] != row["archive_sha256"] or not p["accepted"]:
                    problems.append(f"{cid}.{arm}: selected archive is not the first strict minimum")
        bits[cid] = rec
    # recompute contrasts with own arithmetic
    pairs = [("A1", "A0"), ("A2", "A1"), ("A3", "A2"), ("A2", "A0"), ("A3", "A0"),
             ("A1", "pair_grammar"), ("A2", "pair_grammar"), ("A3", "pair_grammar"),
             ("A1", "portfolio"), ("A2", "portfolio"), ("A3", "portfolio"),
             ("A0", "pair_grammar"), ("A0", "portfolio")]
    complete = summ["evidence_state"]["state"] == "VALID_COMPLETE"
    recomputed = {}
    for a, b in pairs:
        per = {}
        for cid, r in bits.items():
            per[cid] = None if r[a] is None or r[b] is None else (r[b] - r[a]) / n_of[cid]
        cell_vals: dict = {}
        for c in cases:
            key = (c["family"], c["base_length"])
            cell_vals.setdefault(key, {}).setdefault(c["replicate"], []).append(per[c["case_id"]])
        cell_mean = {}
        for key, reps in cell_vals.items():
            rv = [None if None in v else sum(v) / len(v) for v in reps.values()]
            cell_mean[key] = None if None in rv else sum(rv) / len(rv)
        cv = list(cell_mean.values())
        agg = None if None in cv else sum(cv) / len(cv)
        name = f"{a}_vs_{b}"
        s = summ["contrasts"][name]
        mine = {"better": sum(v > 0 for v in per.values() if v is not None),
                "tie": sum(v == 0 for v in per.values() if v is not None),
                "worse": sum(v < 0 for v in per.values() if v is not None)}
        if any(s["strings"][k] != v for k, v in mine.items()):
            problems.append(f"{name}: string sign counts")
        cm = {"better": sum(v > 0 for v in cv if v is not None),
              "tie": sum(v == 0 for v in cv if v is not None),
              "worse": sum(v < 0 for v in cv if v is not None)}
        if any(s["cells_sign"][k] != v for k, v in cm.items()):
            problems.append(f"{name}: cell sign counts")
        if complete:
            if agg is None or s["aggregate"] is None or abs(agg - s["aggregate"]) > TOL:
                problems.append(f"{name}: aggregate {agg} vs {s['aggregate']}")
        elif s["aggregate"] is not None:
            problems.append(f"{name}: aggregate reported on an incomplete/invalid state")
        for cid, v in per.items():
            sv = s["per_string"][cid]
            if (v is None) != (sv is None) or (v is not None and abs(v - sv) > TOL):
                problems.append(f"{name}: per-string {cid}")
        if len(per) != 96 or len(cell_mean) != 24 or sum(len(r) for r in cell_vals.values()) != 48:
            problems.append(f"{name}: denominators")
        recomputed[name] = {"aggregate": agg, "strings": mine, "cells": cm}
    label = None
    if complete:
        if not any(r["A3"] < r["A0"] for r in bits.values()):
            label = "NO_RETAINED_GAIN"
        elif not any(r["A3"] < r["A2"] for r in bits.values()):
            label = "NO_ADDED_LEVEL_GAIN"
        else:
            label = "LEVEL_GAIN_OBSERVED"
    if label != summ["recommendation"]["label"]:
        problems.append(f"label {label} vs {summ['recommendation']['label']}")
    for cid, r in bits.items():
        for k, v in r.items():
            if summ["bits"][cid][k] != v:
                problems.append(f"bits {cid}.{k}: {v} vs {summ['bits'][cid][k]}")
    return {"pass": not problems, "problems": problems[:200], "problem_count": len(problems),
            "archives_read": archives_read, "decodes": decodes, "strings": len(cases),
            "recomputed": recomputed, "recommendation_label": label,
            "reused_owners": {"hierarchy.decode": "independent decoder (standard library only)"},
            "not_used": ["report.py", "any encoder", "summary aggregates as inputs"]}


if __name__ == "__main__":
    out = audit()
    dest = Path(sys.argv[1]) if len(sys.argv) > 1 else RUN / "arithmetic_audit.json"
    dest.write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out[k] for k in ("pass", "problem_count", "archives_read", "decodes",
                                          "recommendation_label")}))
    sys.exit(0 if out["pass"] else 1)
