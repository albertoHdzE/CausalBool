"""Field-by-field comparison of two HID-v1 runs over the same declared design (read-only).

For every (case, method) of the confirmation and transfer splits it compares the
archive bytes' hash and size, the portfolio selection, the codec, and every
deterministic search field; runtime and RSS are reported separately as fields that
may differ. Endpoints are compared from the two summary.json files. Writes one JSON.

    PYTHONPATH=index-deconvolution:src venv/bin/python \
        index-deconvolution/experiments/compare_hierarchy_runs.py confirm-v1 confirm-v1-r1
"""
from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "index-deconvolution"))
from hierarchy import validation as V  # noqa: E402
from hierarchy.report import load_rows  # noqa: E402

RESULTS = ROOT / "index-deconvolution/results/hierarchy_v1"
OUT_DIR = ROOT / "index-deconvolution/results/hierarchy_v1_corrections"
DETERMINISTIC = ("status", "archive_sha256", "archive_bits", "archive_path", "raw_bits",
                 "raw_archive_bits", "decode_ok", "selected_codec_id", "selected_method",
                 "rule_count", "dag_depth", "candidate_count", "deterministic_work",
                 "stop_reason", "search_counters", "best_source", "trace", "input_sha256",
                 "n_bits", "config_sha256", "exception_type")
IDENTITY = ("run_id", "freeze_sha256")
MAY_DIFFER = ("encode_wall_ns", "worker_wall_ns", "peak_rss_bytes", "stderr_log",
              "exception_message", "rss_method")
ENDPOINTS = ("primary", "ablations", "transfer_structured_aggregate", "controls_aggregate",
             "families_confirmation", "transfer")


def main(old_id: str, new_id: str) -> int:
    old, new = RESULTS / old_id, RESULTS / new_id
    design = V.production_design(["confirmation", "transfer"])
    a = {(r["case_id"], r["method"]): r for r in load_rows(old)}
    b = {(r["case_id"], r["method"]): r for r in load_rows(new)}
    expected = [(c[0], m) for c in V.expected_cases(design) for m in design["methods"]]
    if not expected:
        raise SystemExit("empty design: refusing to compare zero cases")
    diffs, absent, fields_seen = [], [], Counter()
    for key in expected:
        x, y = a.get(key), b.get(key)
        if x is None or y is None:
            absent.append({"key": "|".join(key), "old": x is not None, "new": y is not None})
            continue
        unknown = set(x) ^ set(y)
        for k in sorted(set(x) | set(y)):
            if k in MAY_DIFFER or k in IDENTITY:
                continue
            if k not in DETERMINISTIC and k not in V.ROW_FIELDS + ("case_id", "method", "split"):
                fields_seen[k] += 1
            if x.get(k) != y.get(k):
                diffs.append({"key": "|".join(key), "field": k, "old": x.get(k), "new": y.get(k)})
        if unknown:
            diffs.append({"key": "|".join(key), "field": "row schema", "old": sorted(set(x) - set(y)),
                          "new": sorted(set(y) - set(x))})
    old_bytes = {r["archive_sha256"]: (old / r["archive_path"]).read_bytes()
                 for r in a.values() if r.get("archive_path")}
    byte_mismatch = []
    for r in b.values():
        if r.get("archive_path"):
            data = (new / r["archive_path"]).read_bytes()
            if r["archive_sha256"] in old_bytes and old_bytes[r["archive_sha256"]] != data:
                byte_mismatch.append(r["archive_sha256"])
    so, sn = (json.loads((d / "summary.json").read_text()) for d in (old, new))
    endpoint_diffs = {}
    for k in ENDPOINTS:
        if k == "primary":
            keys = ("estimate_mean_saving_per_input_bit", "ci95", "cells", "units", "strings",
                    "mean_saving_bits", "median_saving_bits", "strings_hid_better",
                    "strings_tied", "strings_hid_worse", "verdict")
            pa = {kk: so[k].get(kk) for kk in keys}
            pb = {kk: sn[k].get(kk) for kk in keys}
        elif k in ("transfer_structured_aggregate", "controls_aggregate"):
            pa = {kk: so[k].get(kk) for kk in ("estimate", "ci95_descriptive")}
            pb = {kk: sn[k].get(kk) for kk in ("estimate", "ci95_descriptive")}
        elif k == "ablations":
            pa = {m: {kk: v.get(kk) for kk in ("incremental_gain_per_input_bit", "ci99",
                                               "component_advantage")} for m, v in so[k].items()}
            pb = {m: {kk: v.get(kk) for kk in ("incremental_gain_per_input_bit", "ci99",
                                               "component_advantage")} for m, v in sn[k].items()}
        else:
            strip = ("units_required", "partial")
            pa = [{kk: v for kk, v in r.items() if kk not in strip} for r in so[k]]
            pb = [{kk: v for kk, v in r.items() if kk not in strip} for r in sn[k]]
        endpoint_diffs[k] = {"identical": pa == pb}
        if pa != pb:
            endpoint_diffs[k].update(old=pa, new=pb)

    def resource(rows, f):
        v = [r[f] for r in rows.values() if r.get(f) is not None]
        return {"n": len(v), "sum": sum(v), "max": max(v) if v else None}
    out = {"old": old_id, "new": new_id,
           "old_freeze": (old / "freeze.sha256").read_text().strip(),
           "new_freeze": (new / "freeze.sha256").read_text().strip(),
           "expected_case_methods": len(expected), "compared": len(expected) - len(absent),
           "absent": absent[:100], "deterministic_fields": list(DETERMINISTIC),
           "fields_allowed_to_differ": list(MAY_DIFFER), "identity_fields": list(IDENTITY),
           "differences": diffs[:500], "difference_count": len(diffs),
           "differences_by_field": dict(Counter(d["field"] for d in diffs)),
           "distinct_archives": {"old": len(old_bytes),
                                 "new": len({r["archive_sha256"] for r in b.values() if r.get("archive_path")})},
           "archive_byte_mismatches_under_equal_hash": byte_mismatch,
           "endpoints": endpoint_diffs,
           "resources": {f: {"old": resource(a, f), "new": resource(b, f)}
                         for f in ("encode_wall_ns", "worker_wall_ns", "peak_rss_bytes")},
           "unclassified_fields_seen": dict(fields_seen)}
    out["identical_deterministic_behaviour"] = (not absent and not diffs and not byte_mismatch
                                                and all(v["identical"] for v in endpoint_diffs.values()))
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    path = OUT_DIR / f"compare_{old_id}_vs_{new_id}.json"
    path.write_text(json.dumps(out, indent=1, default=float) + "\n")
    print(json.dumps({k: out[k] for k in ("expected_case_methods", "compared", "difference_count",
                                          "differences_by_field", "distinct_archives",
                                          "identical_deterministic_behaviour")}, indent=1))
    print({k: v["identical"] for k, v in endpoint_diffs.items()})
    return 0 if out["identical_deterministic_behaviour"] else 1


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:3]))
