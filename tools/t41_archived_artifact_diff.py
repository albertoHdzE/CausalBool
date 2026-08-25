#!/usr/bin/env python3
"""AUDIT01/T4.1 step-1 evidence: elementwise diff of the ARCHIVED mixed001 artifacts
(git 406a010, Status.txt dated Sat 22 Nov 2025) against their own baseline.

Establishes where the archived accuracyIndex=0.51875 lives (U8): if the archived
OutputsPredictiveIndex.csv is an all-zero matrix, its agreement with the baseline is
exactly the baseline zero-cell fraction -- i.e. the recorded number is the signature
of a dead prediction path, not of a partial ordering scramble.

Writes results/tests/mixed001FormulaVsExhaustive/rootcause/archived_artifact_diff.json
"""
import csv
import json
import subprocess
import sys
from pathlib import Path

REV = "406a010"
DIR = "results/tests/mixed001FormulaVsExhaustive"
OUT = Path(DIR) / "rootcause" / "archived_artifact_diff.json"


def load_archived(name: str):
    blob = subprocess.run(
        ["git", "show", f"{REV}:{DIR}/{name}"], capture_output=True, text=True, check=True
    ).stdout
    return [[int(float(x)) for x in row] for row in csv.reader(blob.splitlines()) if row]


def main() -> int:
    base = load_archived("OutputsBaseline.csv")
    idx = load_archived("OutputsPredictiveIndex.csv")
    ana = load_archived("OutputsPredictiveAnalytic.csv")
    cur_base = [
        [int(float(x)) for x in row]
        for row in csv.reader(open(f"{DIR}/OutputsBaseline.csv"))
        if row
    ]
    assert len(base) == len(idx) == len(ana) == 1024

    total = len(base) * len(base[0])
    mism_idx = sum(1 for rb, ri in zip(base, idx) for a, b in zip(rb, ri) if a != b)
    mism_ana = sum(1 for rb, ri in zip(base, ana) for a, b in zip(rb, ri) if a != b)
    idx_all_zero = all(v == 0 for r in idx for v in r)
    zero_cells = sum(1 for r in base for v in r if v == 0)
    zero_fraction = zero_cells / total
    per_node = {
        f"node{k+1}": {
            "mismatches": sum(1 for rb, ri in zip(base, idx) if rb[k] != ri[k]),
            "idxOnes": sum(1 for ri in idx if ri[k] == 1),
            "baseOnes": sum(1 for rb in base if rb[k] == 1),
        }
        for k in range(len(base[0]))
    }
    rep = {
        "git_rev": REV,
        "archived_status_txt_date": subprocess.run(
            ["git", "show", f"{REV}:{DIR}/Status.txt"], capture_output=True, text=True, check=True
        ).stdout.strip().splitlines()[-1],
        "total_cells": total,
        "index_path_mismatches_vs_archived_baseline": mism_idx,
        "index_path_agreement": round(1 - mism_idx / total, 5),
        "index_path_is_all_zero_matrix": idx_all_zero,
        "analytic_path_mismatches_vs_archived_baseline": mism_ana,
        "baseline_zero_cells": zero_cells,
        "baseline_zero_fraction": round(zero_fraction, 5),
        "identity_zero_fraction_equals_archived_accuracy_index": abs(zero_fraction - 0.51875) < 1e-12,
        "per_node_index_vs_base": per_node,
        "archived_baseline_identical_to_current": base == cur_base,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(rep, indent=1))
    print(json.dumps({k: v for k, v in rep.items() if k != "per_node_index_vs_base"}, indent=1))
    ok = (
        idx_all_zero
        and rep["identity_zero_fraction_equals_archived_accuracy_index"]
        and mism_ana == 0
        and rep["archived_baseline_identical_to_current"]
    )
    print("T41 ARCHIVED-DIFF " + ("OK" if ok else "UNEXPECTED"))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
