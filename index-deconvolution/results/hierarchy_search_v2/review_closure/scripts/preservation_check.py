"""Read-only preservation record for the HID-search-v2 R1/R2 review closure.

  preservation_check.py before|after

Hashes every protected file and tree named by the closure kickoff and writes
``review_closure/baseline/preservation_<phase>.json``. ``after`` also compares with
``before`` and exits 1 on any difference. Tree aggregation reuses the existing owner
``experiments/preserve_confirm_v1_r1_sources.tree_hash``; nothing here writes outside
the correction package. Run with PYTHONDONTWRITEBYTECODE=1.
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from pathlib import Path

REPO = Path(__file__).resolve().parents[5]
ID = REPO / "index-deconvolution"
sys.path.insert(0, str(ID / "experiments"))
from preserve_confirm_v1_r1_sources import tree_hash  # noqa: E402  (existing owner)

BASE = ID / "results/hierarchy_search_v2"
OUT = BASE / "review_closure/baseline"
RUN = BASE / "search-confirm-v2-r1"

TREES = {
    "hierarchy_v1/confirm-v1": ID / "results/hierarchy_v1/confirm-v1",
    "hierarchy_v1/confirm-v1-r1": ID / "results/hierarchy_v1/confirm-v1-r1",
    "search-confirm-v2-r1": RUN,
    "search_v2/development": BASE / "development",
    "search_v2/prefreeze": BASE / "prefreeze",
    "search_v2/preservation": BASE / "preservation",
    "search_v2/supervision": BASE / "supervision",
    "hierarchy_package": ID / "hierarchy",
    "protocols/hierarchy_search_v2": ID / "protocols/hierarchy_search_v2",
}
FILES = [
    "index-deconvolution/notebooks/build_17.py",
    "index-deconvolution/notebooks/17_hierarchy_search_v2.ipynb",
    "index-deconvolution/notebooks/build_16.py",
    "index-deconvolution/notebooks/16_hierarchical_index_generalization.ipynb",
    "index-deconvolution/notebooks/_nblib.py",
    "index-deconvolution/PROTOCOL_hierarchy_search_v2.md",
    "index-deconvolution/KICKOFF_hierarchy_search_v2_closure.md",
    "index-deconvolution/results/hierarchy_search_v2/execution_ledger.jsonl",
    "index-deconvolution/results/hierarchy_search_v2/development_attempts.jsonl",
    "index-deconvolution/results/hierarchy_search_v2/implementation_map.md",
    "index-deconvolution/experiments/preserve_confirm_v1_r1_sources.py",
    "index-deconvolution/experiments/audit_search_v2_primary.py",
]


def sha_file(p: Path) -> str | None:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def frozen_sources() -> dict:
    """Every file the scientific freeze names, re-hashed and compared with the freeze."""
    f = json.loads((RUN / "freeze.json").read_text())
    out = {}
    for group in ("source_sha256", "protocol_sha256", "informational_sha256"):
        for rel, want in f[group].items():
            got = sha_file(REPO / rel)
            out[rel] = {"group": group, "frozen": want, "live": got, "match": got == want}
    return out


def unrelated_edits() -> dict:
    """sha256 of every tracked modified file outside the correction package (others' work)."""
    names = subprocess.run(["git", "diff", "--name-only"], cwd=REPO, capture_output=True,
                           text=True, check=True).stdout.split("\n")
    return {n: sha_file(REPO / n) for n in sorted(x for x in names if x)
            if "review_closure/" not in n}


def record() -> dict:
    return {"recorded_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "git_head": subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO, capture_output=True,
                                       text=True, check=True).stdout.strip(),
            "freeze_sha256_file": (RUN / "freeze.sha256").read_text().split()[0],
            "trees": {k: tree_hash(v) for k, v in TREES.items()},
            "files": {f: sha_file(REPO / f) for f in FILES},
            "frozen_sources": frozen_sources(),
            "unrelated_tracked_edits": unrelated_edits()}


def main() -> int:
    phase = sys.argv[1] if len(sys.argv) > 1 else ""
    if phase not in ("before", "after"):
        sys.exit("usage: preservation_check.py before|after")
    rec = record()
    fs = rec["frozen_sources"]
    rec["frozen_sources_summary"] = {"files": len(fs), "match": sum(v["match"] for v in fs.values())}
    if not fs or not rec["trees"]:
        sys.exit("refusing: empty protected set")
    code = 0
    if phase == "after":
        before = json.loads((OUT / "preservation_before.json").read_text())
        diffs = [f"{sec}:{k}" for sec in ("trees", "files", "frozen_sources", "unrelated_tracked_edits")
                 for k in set(before[sec]) | set(rec[sec]) if before[sec].get(k) != rec[sec].get(k)]
        rec["compared_with_before"] = {"differences": diffs, "identical": not diffs,
                                       "denominator": {s: len(before[s]) for s in
                                                       ("trees", "files", "frozen_sources",
                                                        "unrelated_tracked_edits")}}
        code = 0 if not diffs else 1
    (OUT / f"preservation_{phase}.json").write_text(json.dumps(rec, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"phase": phase, "trees": len(rec["trees"]), "files": len(rec["files"]),
                      "frozen_sources": rec["frozen_sources_summary"],
                      "unrelated_tracked_edits": len(rec["unrelated_tracked_edits"]),
                      **({"identical": rec["compared_with_before"]["identical"],
                          "differences": rec["compared_with_before"]["differences"]}
                         if phase == "after" else {})}))
    return code


if __name__ == "__main__":
    sys.exit(main())
