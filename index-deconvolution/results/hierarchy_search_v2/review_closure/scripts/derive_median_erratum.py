"""Derive the R1 diagnostic median erratum for search-confirm-v2-r1 from saved records.

Read-only on the run. Writes only ``review_closure/diagnostic_median_erratum.json``.
No reference partition is rebuilt and no string is generated: every input is a saved
archive, decoded with the frozen decoder.

The corrected cell summaries come from the single aggregation owner,
``hierarchy.diagnostics_v2.boundary_gap_summary``, in the ISOLATED PATCHED COPY named
by ``HID_PATCHED_ID`` (the repository's frozen package is not edited). They are
guarded by (a) an independent ``statistics.median`` recomputation here, (b) exact
equality of every quantity other than the median with the original ``diagnostics.json``
and (c) the supervisor's ``diagnostic_audit.json``. Every other module imported from
the patched copy must hash-equal its frozen bytes.

  HID_PATCHED_ID=/tmp/.../CausalBool/index-deconvolution PYTHONDONTWRITEBYTECODE=1 \
      venv/bin/python <this script>
"""
from __future__ import annotations

import hashlib
import json
import os
import statistics
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve()
REPO = HERE.parents[5]
BASE = REPO / "index-deconvolution/results/hierarchy_search_v2"
RUN = BASE / "search-confirm-v2-r1"
OUT = BASE / "review_closure/diagnostic_median_erratum.json"
REFS = RUN / "diagnostics/boundary_reference/references.json"
FREEZE_SHA = "0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49"

PATCHED_ID = Path(os.environ["HID_PATCHED_ID"]).resolve()
for _p in (str(REPO / "src"), str(PATCHED_ID)):
    while _p in sys.path:
        sys.path.remove(_p)
    sys.path.insert(0, _p)
sys.modules.pop("hierarchy", None)          # a sibling repo ships a module "hierarchy"
import hierarchy  # noqa: E402
from hierarchy import diagnostics_v2 as D  # noqa: E402
from hierarchy.decode import decode_archive  # noqa: E402


def sha_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha_file(p: Path) -> str:
    return sha_bytes(p.read_bytes())


def main() -> int:
    problems: list[str] = []
    freeze = json.loads((RUN / "freeze.json").read_text())
    if (RUN / "freeze.sha256").read_text().split()[0] != FREEZE_SHA:
        problems.append("freeze.sha256 differs from the assigned freeze")

    # -- identity of the code actually imported -------------------------------------
    pkg = Path(hierarchy.__file__).resolve().parent
    if pkg != PATCHED_ID / "hierarchy":
        sys.exit(f"refusing: hierarchy imported from {pkg}, not the patched copy")
    imported = {}
    for name, mod in sorted(sys.modules.items()):
        f = getattr(mod, "__file__", None)
        if name.startswith("hierarchy") and f:
            rel = "index-deconvolution/hierarchy/" + Path(f).resolve().relative_to(pkg).as_posix()
            got = sha_file(Path(f))
            frozen = freeze["source_sha256"].get(rel)
            imported[rel] = {"sha256": got, "frozen_sha256": frozen,
                             "equals_frozen": got == frozen}
            if rel != "index-deconvolution/hierarchy/diagnostics_v2.py" and got != frozen:
                problems.append(f"imported module differs from freeze: {rel}")

    # -- saved inputs ---------------------------------------------------------------
    items = json.loads(REFS.read_text())
    diag = json.loads((RUN / "diagnostics.json").read_text())
    sb = diag["supplied_boundary_references"]
    if sb["items_path"] != str(REFS.relative_to(RUN)):
        problems.append("diagnostics.json names a different references file")
    rows = defaultdict(dict)
    for ln in (RUN / "cases.jsonl").read_text().splitlines():
        if ln.strip():
            r = json.loads(ln)
            rows[r["case_id"]][r["method"]] = r
    if not items:
        sys.exit("refusing: no reference records")

    # -- per-record identity: archive bytes, length, decode -> input hash, gap ------
    rec_checks = {"records": len(items), "available": 0, "archive_sha_ok": 0, "length_ok": 0,
                  "decodes_to_case_input_sha256": 0, "hid_bits_equal_rows": 0,
                  "raw_bits_equal_rows": 0, "gap_recomputed_exactly": 0}
    for it in items:
        if not it.get("available"):
            continue
        rec_checks["available"] += 1
        cid = it["case_id"]
        data = (RUN / it["reference_archive"]).read_bytes()
        rec_checks["archive_sha_ok"] += sha_bytes(data) == it["reference_sha256"]
        rec_checks["length_ok"] += 8 * len(data) == it["reference_bits"]
        want_inputs = {r["input_sha256"] for r in rows[cid].values()}
        bits = decode_archive(data)
        ok_in = len(want_inputs) == 1 and sha_bytes(bits.encode()) in want_inputs \
            and len(bits) == it["n_bits"]
        rec_checks["decodes_to_case_input_sha256"] += ok_in
        rec_checks["hid_bits_equal_rows"] += all(
            it[f"{m}_bits"] == rows[cid][m]["archive_bits"] for m in ("hid_full", "hid_global", "hid_legacy"))
        rec_checks["raw_bits_equal_rows"] += it["raw_bits"] == rows[cid]["hid_full"]["raw_archive_bits"]
        feasible = min(it["reference_bits"], it["raw_bits"])
        rec_checks["gap_recomputed_exactly"] += (
            feasible == it["feasible_bits"]
            and (it["hid_full_bits"] - feasible) / it["n_bits"] == it["gap_hid_full_per_input_bit"])
    for k, v in rec_checks.items():
        if k != "records" and v != rec_checks["available"]:
            problems.append(f"record check {k}: {v} of {rec_checks['available']}")
    if rec_checks["available"] != len(items):
        problems.append("some references unavailable; medians cover available gaps only")

    # -- corrected summaries from the owner, guarded independently -----------------
    corrected = D.boundary_gap_summary(items)
    original = sb["by_cell"]
    if set(corrected) != set(original):
        problems.append("cell keys differ from the original diagnostics")
    audit = {a["cell"]: a for a in json.loads(
        (BASE / "supervision/diagnostic_audit.json").read_text())["median_disagreements"]}
    cells = {}
    unchanged_fields = ("strings", "available", "gap_mean", "automatic_shorter_than_reference",
                        "automatic_longer_than_reference", "ties")
    for k in sorted(original):
        members = [it for it in items if f"{it['role']}|{it['family']}|{it['base_length']}" == k]
        gaps = [it["gap_hid_full_per_input_bit"] for it in members
                if it.get("available") and "gap_hid_full_per_input_bit" in it]
        o, c = original[k], corrected[k]
        independent = statistics.median(gaps) if gaps else None
        if c["gap_median"] != independent:
            problems.append(f"{k}: owner median != independent statistics.median")
        for f in unchanged_fields:
            if o[f] != c[f]:
                problems.append(f"{k}: {f} differs ({o[f]} vs {c[f]})")
        s = sorted(gaps)
        n = len(s)
        changed = o["gap_median"] != c["gap_median"]
        a = audit.get(k)
        if changed and (a is None or a["correct_gap_median"] != c["gap_median"]
                        or a["stored_gap_median"] != o["gap_median"] or a["n"] != n):
            problems.append(f"{k}: correction disagrees with the supervisor audit")
        if not changed and a is not None:
            problems.append(f"{k}: supervisor audit lists a disagreement not reproduced")
        sign = lambda x: (x > 0) - (x < 0)  # noqa: E731
        cells[k] = {
            "n_gaps": n, "parity": "even" if n % 2 == 0 else "odd",
            "case_ids": sorted(it["case_id"] for it in members),
            "middle_order_statistics": (s[n // 2 - 1: n // 2 + 1] if n % 2 == 0 else s[n // 2: n // 2 + 1]) if n else [],
            "original_gap_median": o["gap_median"], "corrected_gap_median": c["gap_median"],
            "changed": changed,
            "difference_corrected_minus_original": (c["gap_median"] - o["gap_median"]) if n else None,
            "median_sign_original_corrected": [sign(o["gap_median"]), sign(c["gap_median"])] if n else None,
            "unchanged_quantities": {f: o[f] for f in unchanged_fields},
            "in_supervisor_audit": a is not None}
    if not cells:
        sys.exit("refusing: no cells")
    out = {
        "title": "HID-search-v2 diagnostic median erratum (review R1)",
        "scope": ("DIAGNOSTIC-ONLY. Corrects the descriptive gap_median of the evaluation-only "
                  "supplied-boundary reference summary (diagnostics.json#supplied_boundary_references"
                  ".by_cell). Primary estimate, interval, gates, contrasts, descriptive transfer/"
                  "stress, mean gaps and every row/archive are unaffected. Original diagnostics.json "
                  "and references.json are not modified. Not a new run, not a replication."),
        "units": "bits per input bit; gap = (bits(hid_full) - min(bits(reference), bits(raw))) / n; "
                 "negative means the automatic archive is shorter",
        "median_definition": "conventional sample median: middle value (odd n), mean of the two "
                             "middle values (even n); null for an empty cell",
        "defect": "frozen diagnostics_v2.py line 167 reported g[len(g) // 2] (upper middle order "
                  "statistic for even n)",
        "run_id": "search-confirm-v2-r1", "freeze_sha256": FREEZE_SHA,
        "input_sha256": {str(p.relative_to(REPO)): sha_file(p) for p in (
            REFS, RUN / "diagnostics.json", RUN / "cases.jsonl", RUN / "freeze.json",
            BASE / "supervision/diagnostic_audit.json")},
        "source_identity": {
            "frozen_diagnostics_v2_sha256": freeze["source_sha256"]["index-deconvolution/hierarchy/diagnostics_v2.py"],
            "patched_copy": str(PATCHED_ID), "imported_modules": imported},
        "derivation_script": {"path": str(HERE.relative_to(REPO)), "sha256": sha_file(HERE)},
        "record_checks": rec_checks,
        "cells_total": len(cells), "cells_changed": sum(c["changed"] for c in cells.values()),
        "cells": cells, "problems": problems, "all_checks_pass": not problems}
    OUT.write_text(json.dumps(out, indent=1) + "\n")
    print(json.dumps({"cells_total": out["cells_total"], "cells_changed": out["cells_changed"],
                      "record_checks": rec_checks, "problems": problems}))
    return 0 if not problems else 1


if __name__ == "__main__":
    sys.exit(main())
