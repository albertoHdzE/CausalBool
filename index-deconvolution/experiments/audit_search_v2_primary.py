"""Independent arithmetic audit of the HID-search-v2 primary point estimate.

Reads cases.jsonl and the archive FILES of one run; does not import hierarchy.report,
hierarchy.report_v2 or any production endpoint function. It recomputes, from bytes on
disk: every archive length; the nine-baseline minimum per string (and checks the stored
baseline_best row against it); the declared 7 x 3 x 20 x 2 design; the equal-weight
unit -> cell -> population mean; and the sign convention (positive = HID shorter).
The production bootstrap is not re-implemented here (the production report remains
its sole owner); only the point estimate and the five contrast point estimates are.

  venv/bin/python index-deconvolution/experiments/audit_search_v2_primary.py RUN_DIR
Writes RUN_DIR/arithmetic_audit.json; exit 0 iff every check passes.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

FAMILIES = ("F01", "F02", "F03", "F04", "F05", "F06", "F12")
SIZES = (256, 1024, 4096)
REPS = tuple(range(3000, 3020))
BASELINES = ("raw", "rle", "gaps", "period", "bernoulli", "context", "zlib", "lzma",
             "pair_grammar")
CONTRASTS = {"P_vs_L": ("hid_first_local", "hid_legacy", "F06"),
             "C_vs_P": ("hid_consensus_local", "hid_first_local", "F06"),
             "D_vs_C": ("hid_dense_local", "hid_consensus_local", "F06"),
             "G_vs_D": ("hid_global", "hid_dense_local", "F06"),
             "B_full_vs_G": ("hid_full", "hid_global", "F12")}
TOL = 1e-12


def main(run: Path) -> int:
    rows = {}
    for line in (run / "cases.jsonl").read_text().splitlines():
        if line.strip():
            r = json.loads(line)
            rows[(r["case_id"], r["method"])] = r
    sizes: dict[str, int] = {}

    def nbits(r) -> int:
        p = run / r["archive_path"]
        if r["archive_path"] not in sizes:
            data = p.read_bytes()
            assert hashlib.sha256(data).hexdigest() == r["archive_sha256"], r["archive_path"]
            sizes[r["archive_path"]] = 8 * len(data)
        return sizes[r["archive_path"]]

    checks = {"strings": 0, "units": 0, "cells": 0, "portfolio_rows_checked": 0,
              "portfolio_mismatches": [], "stored_bits_mismatches": []}
    cell_means = []
    per_method_unit = {}
    for fam in FAMILIES:
        for n in SIZES:
            units = []
            for rep in REPS:
                pair = []
                for rg, extra in (("base", 0), ("ragged", 3)):
                    cid = f"confirmation-{fam}-{n}-{rep:04d}-{rg}"
                    full = rows[(cid, "hid_full")]
                    best = rows[(cid, "baseline_best")]
                    base_bits = [nbits(rows[(cid, m)]) for m in BASELINES]
                    bmin = min(base_bits)
                    if nbits(best) != bmin or best["archive_bits"] != bmin:
                        checks["portfolio_mismatches"].append(cid)
                    checks["portfolio_rows_checked"] += 1
                    fb = nbits(full)
                    if fb != full["archive_bits"]:
                        checks["stored_bits_mismatches"].append(cid)
                    length = n + extra
                    assert full["n_bits"] == length
                    pair.append((bmin - fb) / length)
                    checks["strings"] += 1
                    for m in ("hid_legacy", "hid_first_local", "hid_consensus_local",
                              "hid_dense_local", "hid_global", "hid_full"):
                        per_method_unit.setdefault((fam, n, rep, m), []).append(
                            nbits(rows[(cid, m)]) / length)
                units.append((pair[0] + pair[1]) / 2)
                checks["units"] += 1
            cell_means.append(sum(units) / len(units))
            checks["cells"] += 1
    estimate = sum(cell_means) / len(cell_means)
    contrasts = {}
    for k, (added, prev, fam) in CONTRASTS.items():
        cm = []
        for n in SIZES:
            u = [(per_method_unit[(fam, n, rep, prev)][0] - per_method_unit[(fam, n, rep, added)][0]
                  + per_method_unit[(fam, n, rep, prev)][1] - per_method_unit[(fam, n, rep, added)][1]) / 2
                 for rep in REPS]
            cm.append(sum(u) / len(u))
        contrasts[k] = sum(cm) / len(cm)
    summary = json.loads((run / "summary.json").read_text())
    prod = summary["primary"].get("estimate_mean_saving_per_input_bit")
    out = {"run": str(run), "script_sha256": hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
           "independent_estimate": estimate, "production_estimate": prod,
           "abs_difference": None if prod is None else abs(estimate - prod), "tolerance": TOL,
           "counts": {k: v for k, v in checks.items() if not isinstance(v, list)},
           "expected_counts": {"strings": 840, "units": 420, "cells": 21},
           "portfolio_mismatches": checks["portfolio_mismatches"],
           "stored_bits_mismatches": checks["stored_bits_mismatches"],
           "sign_convention": "(bits(baseline minimum) - bits(hid_full)) / n; positive = HID shorter",
           "weighting": "base/ragged mean per unit, unit mean per cell, equal cell means",
           "contrast_point_estimates": contrasts,
           "production_contrasts": {k: v.get("estimate_per_input_bit")
                                    for k, v in summary.get("contrasts", {}).items()},
           "distinct_archives_measured": len(sizes)}
    ok = (prod is not None and abs(estimate - prod) <= TOL
          and out["counts"]["strings"] == 840 and out["counts"]["units"] == 420
          and out["counts"]["cells"] == 21 and not checks["portfolio_mismatches"]
          and not checks["stored_bits_mismatches"]
          and all(abs(contrasts[k] - (out["production_contrasts"].get(k) or 1e9)) <= TOL
                  for k in contrasts))
    out["all_checks_pass"] = ok
    (run / "arithmetic_audit.json").write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({k: out[k] for k in ("independent_estimate", "production_estimate",
                                          "abs_difference", "all_checks_pass")}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1])))
