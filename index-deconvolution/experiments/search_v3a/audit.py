"""Independent read-only arithmetic audit of search-confirm-v3a-r1 (BENCHMARK.md 5).

    PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m search_v3a.audit

Reads archive bytes and row files only (no saved aggregate is an input): recomputes
every promised archive's hash and length, decodes it with the independent decoder to
the input whose hash the corpus manifest records, checks HID raw-fallback validity,
rebuilds the nine-way portfolio and its tie order and status, and recomputes the
per-string savings, the six cell means and the equal-cell point estimate with plain
Python. The bootstrap draws are inspected (count, cell order, shapes) through the
owner's ``cell_index_draws`` and the percentile interval is recomputed from those
indices. No encoding. Writes ``arithmetic_audit.json`` only.
"""
from __future__ import annotations

import hashlib
import json
from collections import defaultdict
from pathlib import Path

import numpy as np

from hierarchy import codes as C
from hierarchy.decode import decode_archive

ID_ROOT = Path(__file__).resolve().parents[2]
RUN = ID_ROOT / "results" / "hierarchy_search_v3a" / "search-confirm-v3a-r1"
PACKET = ID_ROOT / "protocols" / "hierarchy_search_v3a"
BASELINES = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma",
             "pair_grammar")
HID = ("hid_full", "hid_refine4")
PRIMARY = ("boundary", "boundary_large", "boundary_stress")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def manifest_hashes() -> dict:
    out = {}
    for p in sorted(RUN.glob("corpus_manifest.*.jsonl")):
        for line in p.read_text().splitlines():
            if line.strip():
                m = json.loads(line)
                base_id, rag_id = m["case_ids"]
                out[base_id], out[rag_id] = m["base_sha256"], m["full_sha256"]
    return out


def main() -> int:
    cases = json.loads((PACKET / "intended_cases.json").read_text())["cases"]
    want = manifest_hashes()
    problems, checked, decoded = [], 0, {}
    status = defaultdict(lambda: defaultdict(int))
    per_string = {}
    for c in cases:
        cid = c["case_id"]
        p = RUN / "rows" / f"{cid}.json"
        if not p.exists():
            problems.append(f"{cid}: rows file missing")
            continue
        rows = {}
        for r in json.loads(p.read_text()):
            if r["method"] in rows:
                problems.append(f"{cid}:{r['method']} duplicate")
            rows[r["method"]] = r
        arcs = {}
        for m in HID + BASELINES:
            r = rows.get(m)
            if r is None:
                problems.append(f"{cid}:{m} absent")
                continue
            status[m][r["status"]] += 1
            if not r.get("archive_path"):
                if r["status"] not in ("not_run", "error"):
                    problems.append(f"{cid}:{m} status {r['status']} without archive")
                continue
            data = (RUN / r["archive_path"]).read_bytes()
            checked += 1
            if sha(data) != r["archive_sha256"] or 8 * len(data) != r["archive_bits"]:
                problems.append(f"{cid}:{m} archive hash/length differs from the row")
            h = sha(data)
            if h not in decoded:
                s = decode_archive(data)
                decoded[h] = (len(s), sha(s.encode("ascii")))
            if decoded[h] != (c["n_bits"], want.get(cid)):
                problems.append(f"{cid}:{m} archive does not decode to the manifest input")
            if r["status"] in ("timeout_raw", "rss_limit_raw") and data[4] != C.CODEC_LITERAL:
                problems.append(f"{cid}:{m} raw fallback is not a literal archive")
            if r["status"] in ("ok", "timeout_raw", "rss_limit_raw") or m in BASELINES:
                arcs[m] = (r["status"], data)
        pb = rows.get("baseline_best")
        avail = {m: d for m, (st, d) in arcs.items() if m in BASELINES and st == "ok"}
        all_ok = len(avail) == len(BASELINES)
        if pb is None:
            problems.append(f"{cid}: portfolio row absent")
        elif avail:
            best = min(avail, key=lambda m: (len(avail[m]), avail[m][4], avail[m]))
            if pb["selected_method"] != best or pb["archive_bits"] != 8 * len(avail[best]):
                problems.append(f"{cid}: portfolio selection differs from the recomputed minimum")
            if (pb["status"] == "ok") != all_ok:
                problems.append(f"{cid}: portfolio status {pb['status']} with all_ok={all_ok}")
        a, b = arcs.get("hid_full"), arcs.get("hid_refine4")
        per_string[cid] = (None if a is None or b is None
                           else (8 * len(a[1]) - 8 * len(b[1])) / c["n_bits"])
    # plain-Python primary arithmetic
    units = defaultdict(dict)
    for c in cases:
        if c["role"] in PRIMARY:
            units[(c["role"], c["family"], c["base_length"])].setdefault(c["replicate"], []).append(
                per_string.get(c["case_id"]))
    cell_means, cell_units = {}, {}
    complete = True
    for k in sorted(units):
        vals = []
        for rep in sorted(units[k]):
            pair = units[k][rep]
            if len(pair) != 2 or any(v is None for v in pair):
                complete = False
                continue
            vals.append((pair[0] + pair[1]) / 2)
        cell_units[k] = vals
        cell_means["|".join(map(str, k))] = sum(vals) / len(vals) if vals else None
    out = {"archives_checked": checked, "distinct_archives_decoded": len(decoded),
           "strings": len(cases), "status_counts": {m: dict(v) for m, v in status.items()},
           "problems": problems[:500], "problem_count": len(problems),
           "cell_means": cell_means, "complete_primary_units": complete
           and all(len(v) == 20 for v in cell_units.values()) and len(cell_units) == 6}
    if out["complete_primary_units"]:
        point = sum(cell_means.values()) / 6
        draws_idx = __import__("hierarchy.report", fromlist=["x"]).cell_index_draws(
            {k: 20 for k in cell_units}, 10000, 55001)
        order = list(draws_idx)
        acc = np.zeros(10000)
        for k in order:
            acc += np.asarray(cell_units[k])[draws_idx[k]].mean(axis=1)
        acc /= 6
        lo, hi = float(np.quantile(acc, 0.005)), float(np.quantile(acc, 0.995))
        out["point_estimate"] = point
        out["bootstrap_inspection"] = {"cell_order": ["|".join(map(str, k)) for k in order],
                                       "shapes": [list(draws_idx[k].shape) for k in order],
                                       "ci99_recomputed": [lo, hi]}
        dec = json.loads((RUN / "DECISION.json").read_text())
        out["decision_point_equal"] = dec.get("estimate_bits_per_input_bit") is not None and \
            abs(dec["estimate_bits_per_input_bit"] - point) < 1e-12
        out["decision_ci_equal"] = dec.get("ci99") is not None and \
            max(abs(dec["ci99"][0] - lo), abs(dec["ci99"][1] - hi)) < 1e-12
        summ = json.loads((RUN / "summary.json").read_text())
        out["cell_means_equal"] = all(abs(summ["primary"]["cells"][k]["mean"] - v) < 1e-12
                                      for k, v in cell_means.items())
    out["pass"] = not problems and (not out["complete_primary_units"] or (
        out["decision_point_equal"] and out["decision_ci_equal"] and out["cell_means_equal"]))
    (RUN / "arithmetic_audit.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: out.get(k) for k in ("pass", "archives_checked", "problem_count",
                                              "point_estimate", "decision_point_equal",
                                              "decision_ci_equal", "cell_means_equal")}))
    return 0 if out["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
