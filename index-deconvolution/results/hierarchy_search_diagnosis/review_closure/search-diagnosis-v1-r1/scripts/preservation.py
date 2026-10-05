"""Closure preservation record: before/after hashes of everything this closure must not touch.

  preservation.py before|after

Reuses the phase owner ``search_diagnosis.common.preservation_record`` (its four trees and
60 files) and its ``tree_hash``; adds the trees and files the closure kickoff names: the
whole a1 run, the supervision record, the phase ledger, the active diagnostic adapters and
tests, notebook 18, its builder and bitacora 42. ``__pycache__`` is excluded from the added
trees (bytecode is not a source). Writes only into this closure's ``verification/``.
"""
import hashlib
import json
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
CLOSURE = HERE.parent
ID = CLOSURE.parents[3]
REPO = ID.parent
sys.path[:0] = [str(ID / "experiments"), str(ID), str(REPO / "src")]
from search_diagnosis import common as K  # noqa: E402


def sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(root: Path) -> dict:
    files = sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + sha(p).encode() + b"\n")
    return {"files": len(files), "aggregate_sha256": h.hexdigest()}


EXTRA_TREES = {
    "a1 run (search-diagnosis-v1-r1, whole)": K.RUN_DIR,
    "supervision/search-diagnosis-v1-r1": K.RESULT_ROOT / "supervision" / "search-diagnosis-v1-r1",
    "active adapters experiments/search_diagnosis (no bytecode)": K.PKG,
}
EXTRA_FILES = [K.RESULT_ROOT / "execution_ledger.jsonl",
               ID / "notebooks" / "build_18.py", ID / "notebooks" / "18_hierarchy_search_diagnosis.ipynb",
               ID / "bitacora" / "42_hierarchy_search_diagnosis.md",
               ID / "KICKOFF_hierarchy_search_diagnosis_closure.md",
               ID / "results" / "hierarchy_search_v2" / "review_closure" / "R1_diagnostics_median_repair.patch"]


def record() -> dict:
    rec, status = K.preservation_record()
    rec["extra_trees"] = {k: tree(v) for k, v in EXTRA_TREES.items()}
    rec["extra_files"] = {str(p.relative_to(REPO)): sha(p) for p in EXTRA_FILES}
    return rec, status


def main() -> int:
    which = sys.argv[1]
    rec, status = record()
    out = HERE.parent / "verification"
    (out / f"git_status_{which}.txt").write_text(status)
    (out / f"preservation_{which}.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    if which == "after":
        before = json.loads((out / "preservation_before.json").read_text())
        cmp = K.compare_preservation(before, rec)
        for k in before["extra_trees"]:
            if before["extra_trees"][k] != rec["extra_trees"].get(k):
                cmp["differences"].append(f"extra_trees:{k}")
        for k, v in before["extra_files"].items():
            if rec["extra_files"].get(k) != v:
                cmp["differences"].append(f"extra_files:{k}")
        cmp["unchanged"] = not cmp["differences"]
        cmp["denominator"].update(extra_trees=len(before["extra_trees"]),
                                  extra_files=len(before["extra_files"]))
        (out / "preservation_comparison.json").write_text(json.dumps(cmp, indent=1) + "\n")
        print(json.dumps(cmp))
        return 0 if cmp["unchanged"] else 1
    print(json.dumps({"trees": len(rec["trees"]), "files": len(rec["files"]),
                      "extra_trees": rec["extra_trees"], "extra_files": len(rec["extra_files"])}))
    return 0


if __name__ == "__main__":
    sys.exit(main())
