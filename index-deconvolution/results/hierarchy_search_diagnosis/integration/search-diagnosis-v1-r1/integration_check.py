"""Integration record for accepted report-r3: manifest check, protected-tree hashes, equality.

  integration_check.py before|after     (run from the repository root; writes only this directory)
"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
REPO = HERE.parents[4]
ID = REPO / "index-deconvolution"
R = ID / "results/hierarchy_search_diagnosis"
FU = R / "review_closure/search-diagnosis-v1-r1-followup"
MANIFEST = R / "supervision/search-diagnosis-v1-r1/closure_acceptance/integration_manifest.json"
PROTECTED_TREES = {
    "a1 run": R / "search-diagnosis-v1-r1",
    "first closure (incl. report-r2)": R / "review_closure/search-diagnosis-v1-r1",
    "follow-up closure (report-r3)": FU,
    "supervision": R / "supervision",
    "hierarchy owner": ID / "hierarchy",
    "search-v2 results (median repair unapplied)": ID / "results/hierarchy_search_v2",
    "bitacora": ID / "bitacora",
}
PROTECTED_FILES = [R / "execution_ledger.jsonl"] + [ID / "experiments/search_diagnosis" / f for f in
                   ("kernels.py", "worker.py", "runner.py", "common.py", "__init__.py", "tests/__init__.py",
                    "tests/test_d3_graph.py", "tests/test_kernels.py", "tests/test_runner.py")]
EQUAL = {ID / "experiments/search_diagnosis" / f: FU / "report-r3/source/search_diagnosis" / f
         for f in ("analysis.py", "report.py", "cli.py", "tests/test_reporting_pipeline.py",
                   "kernels.py", "worker.py", "runner.py", "common.py")}
EQUAL[ID / "notebooks/build_18.py"] = FU / "report-r3/source/build_18.py"
EQUAL[ID / "notebooks/18_hierarchy_search_diagnosis.ipynb"] = \
    FU / "corrected/18_hierarchy_search_diagnosis.report-r3.executed.ipynb"


def sha(p):
    return hashlib.sha256(p.read_bytes()).hexdigest()


def tree(root):
    files = sorted(p for p in root.rglob("*") if p.is_file() and "__pycache__" not in p.parts)
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + sha(p).encode() + b"\n")
    return {"files": len(files), "aggregate_sha256": h.hexdigest()}


def record():
    return {"trees": {k: tree(v) for k, v in PROTECTED_TREES.items()},
            "files": {str(p.relative_to(REPO)): sha(p) for p in PROTECTED_FILES}}


def main():
    which = sys.argv[1]
    out = HERE / which
    out.mkdir(exist_ok=True)
    st = subprocess.run(["git", "status", "--porcelain", "--", "index-deconvolution"], cwd=REPO,
                        capture_output=True, text=True).stdout
    (out / "git_status.txt").write_text(st)
    rec = record()
    if which == "before":
        m = json.loads(MANIFEST.read_text())
        rec["manifest"] = {"files": len(m["files"]), "mismatched":
                           sorted(k for k, v in m["files"].items() if not (REPO / k).exists() or sha(REPO / k) != v),
                           "must_be_absent_present": [k for k in m["must_be_absent"] if (REPO / k).exists()]}
        ok = not rec["manifest"]["mismatched"] and not rec["manifest"]["must_be_absent_present"]
    else:
        before = json.loads((HERE / "before/preservation.json").read_text())
        rec["protected_differences"] = [k for k in before["trees"] if before["trees"][k] != rec["trees"][k]] + \
            [k for k in before["files"] if before["files"][k] != rec["files"][k]]
        rec["equality"] = {str(a.relative_to(REPO)): {"accepted": str(b.relative_to(REPO)), "sha256": sha(a),
                                                     "equal": a.read_bytes() == b.read_bytes()}
                           for a, b in EQUAL.items()}
        rec["denominator"] = {"trees": len(before["trees"]), "files": len(before["files"]), "equality": len(EQUAL)}
        ok = not rec["protected_differences"] and all(v["equal"] for v in rec["equality"].values())
    rec["ok"] = ok
    (out / "preservation.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: v for k, v in rec.items() if k not in ("trees", "files", "equality")}))
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
