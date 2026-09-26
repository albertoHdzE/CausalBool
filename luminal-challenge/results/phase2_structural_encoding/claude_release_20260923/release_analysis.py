"""Release-level renders of the accepted run, read from raw rows only.

Imports no research code. Writes RELEASE_ANALYSIS.json and prints a compact
text summary. Usage: python release_analysis.py RUN_DIR REPLICATE_RUN_DIR OUT.json

* primary per-program render: control/candidate J, C and S for every held-out
  program, and the sign of the change in each component (G1: render the object);
* distribution of the per-program primary log ratio (bins, not only a mean);
* reproducibility: per-program J of every arm/budget equal across the two runs,
  and per-program median compile time ratio (replicate / accepted);
* stopping reasons, optimisation seconds and budget overshoot per arm/budget;
* failures, timeouts and nonzero exits per corpus.
"""
import collections
import json
import math
import statistics
import sys
from pathlib import Path

REPS = 15


def rows(run: Path, corpus: str):
    return [json.loads(line) for line in (run / "p5" / f"{corpus}_rows.jsonl").open() if line.strip()]


def by_cell(data):
    cells = collections.defaultdict(list)
    for row in data:
        cells[(row["program_sha256"], row["arm"], row["budget_seconds"])].append(row)
    return cells


def main(run: Path, replicate: Path, out: Path) -> None:
    report = {"run": str(run), "replicate": str(replicate)}
    p0 = json.loads((run / "p0/summary.json").read_text())
    family = {e["program_sha256"]: e["family"] for e in p0["heldout"]["programs"]}
    name = {e["program_sha256"]: Path(e["path"]).name for e in p0["heldout"]["programs"]}
    held = rows(run, "heldout")
    cells = by_cell(held)

    # Primary render: structural_bound @0.1 against accepted_budgeted @0.1.
    render = []
    for pid in sorted(family):
        cand, ctrl = cells[(pid, "structural_bound", 0.1)], cells[(pid, "accepted_budgeted", 0.1)]
        assert len(cand) == REPS and len(ctrl) == REPS, (pid, len(cand), len(ctrl))
        cand_j = sorted({r["product"] for r in cand})
        ctrl_j = sorted({r["product"] for r in ctrl})
        cand_by_rep = {r["repetition"]: r for r in cand}
        ctrl_by_rep = {r["repetition"]: r for r in ctrl}
        effect = statistics.mean(math.log(ctrl_by_rep[k]["product"] / cand_by_rep[k]["product"])
                                 for k in range(REPS))
        c0, c1 = cand_by_rep[0], ctrl_by_rep[0]
        render.append({"program": name[pid], "family": family[pid],
                       "control_J_values": ctrl_j, "candidate_J_values": cand_j,
                       "control_C_S": [c1["cycles"], c1["scratch"]],
                       "candidate_C_S": [c0["cycles"], c0["scratch"]],
                       "delta_cycles": c0["cycles"] - c1["cycles"],
                       "delta_scratch": c0["scratch"] - c1["scratch"],
                       "mean_paired_log_ratio": effect})
    report["primary_render"] = render
    changed = [r for r in render if r["mean_paired_log_ratio"] != 0]
    report["primary_mechanism"] = {
        "programs": len(render), "changed": len(changed),
        "changed_by_family": dict(collections.Counter(r["family"] for r in changed)),
        "component_pattern": {
            f"C{c} S{s}": n for (c, s), n in collections.Counter(
                (("-" if r["delta_cycles"] < 0 else "+" if r["delta_cycles"] > 0 else "="),
                 ("-" if r["delta_scratch"] < 0 else "+" if r["delta_scratch"] > 0 else "="))
                for r in changed).most_common()},
    }
    edges = [0, 1e-12, 0.05, 0.1, 0.2, 0.4, 1.0, 10.0]
    hist = collections.Counter()
    for r in render:
        value = r["mean_paired_log_ratio"]
        if value < 0:
            hist["<0"] += 1
            continue
        for lo, hi in zip(edges, edges[1:]):
            if lo <= value < hi:
                hist[f"[{lo},{hi})"] += 1
                break
    report["primary_log_ratio_histogram"] = dict(hist)

    # Stopping reasons and overshoot.
    stops, seconds, overshoot = collections.Counter(), collections.defaultdict(list), collections.defaultdict(list)
    for corpus in ("public", "heldout"):
        for row in rows(run, corpus):
            opt = row.get("optimisation") or {}
            key = f"{corpus}|{row['arm']}|{row['budget_seconds']}"
            stops[f"{key}|{opt.get('stopped_because')}"] += 1
            if isinstance(opt.get("seconds"), (int, float)):
                seconds[key].append(opt["seconds"])
            if isinstance(opt.get("overshoot_seconds"), (int, float)) and row["budget_seconds"] is not None:
                overshoot[key].append(opt["overshoot_seconds"])
    report["stopping_reasons"] = dict(sorted(stops.items()))
    report["optimisation_seconds_median"] = {k: statistics.median(v) for k, v in sorted(seconds.items())}
    report["overshoot_seconds"] = {k: {"max": max(v), "p99": sorted(v)[int(0.99 * (len(v) - 1))],
                                       "positive_rows": sum(x > 0 for x in v), "rows": len(v)}
                                   for k, v in sorted(overshoot.items())}

    # Failures and exits, both corpora.
    report["failures"] = {}
    for corpus in ("public", "heldout"):
        data = rows(run, corpus)
        report["failures"][corpus] = {
            "rows": len(data), "failed_rows": sum(bool(r.get("failed_row")) for r in data),
            "timed_out": sum(bool(r.get("timed_out")) for r in data),
            "nonzero_exit": sum(r.get("exit_code") != 0 for r in data),
            "discrepancies": sum(r.get("discrepancy_count", 0) for r in data)}

    # Reproducibility against the replicate run (same measurement source).
    repro = {}
    for corpus in ("public", "heldout"):
        a, b = by_cell(rows(run, corpus)), by_cell(rows(replicate, corpus))
        same_keys = set(a) == set(b)
        j_equal = sum({r["product"] for r in a[k]} == {r["product"] for r in b[k]} for k in a if k in b)
        ratios = [statistics.median(r["compile_seconds"] for r in b[k]) /
                  statistics.median(r["compile_seconds"] for r in a[k]) for k in a if k in b]
        repro[corpus] = {"cells": len(a), "cell_keys_equal": same_keys,
                         "cells_with_identical_J_sets": j_equal,
                         "median_compile_ratio_replicate_over_run": statistics.median(ratios),
                         "compile_ratio_p05_p95": [sorted(ratios)[int(0.05 * (len(ratios) - 1))],
                                                   sorted(ratios)[int(0.95 * (len(ratios) - 1))]]}
    report["reproducibility"] = repro
    Path(out).open("x").write(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: report[k] for k in ("primary_mechanism", "primary_log_ratio_histogram",
                                             "failures", "reproducibility")}, indent=1))


if __name__ == "__main__":
    main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3]))
