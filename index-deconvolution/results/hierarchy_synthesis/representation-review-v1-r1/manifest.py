"""Evidence hash manifest (pre/post). Read-only; writes only into this directory.

    (from index-deconvolution/) ../venv/bin/python -B <this dir>/manifest.py pre|post
"""
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ID = HERE.parents[2]
REPO = ID.parent
D = ID / "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1"
FILES = [
    "PROTOCOL_hierarchy_dictionary_v1.md", "PROTOCOL_hierarchy_multilevel_v1.md",
    "protocols/hierarchy_dictionary_v1/SEARCH.md", "protocols/hierarchy_dictionary_v1/BENCHMARK.md",
    "protocols/hierarchy_dictionary_v1/ACCEPTANCE.md", "protocols/hierarchy_dictionary_v1/contract.json",
    "protocols/hierarchy_multilevel_v1/CASES.json", "protocols/hierarchy_multilevel_v1/contract.json",
    "protocols/hierarchy_multilevel/CONCEPT_REVIEW.md",
    "results/hierarchy_dictionary_v1/supervision/dictionary-feasibility-v1-r1/REVIEW.md",
    "results/hierarchy_dictionary_v1/supervision/dictionary-feasibility-v1-r1/NEXT_CLAUDE.md",
    "results/hierarchy_dictionary_v1/supervision/dictionary-feasibility-v1-r1/audit_review.json",
    "results/hierarchy_multilevel_v1/supervision/multilevel-feasibility-v1-r1/REVIEW.md",
    "results/hierarchy_multilevel_v1/multilevel-feasibility-v1-r1/HANDOFF.md",
    "results/hierarchy_search_v3a/supervision/search-confirm-v3a-r1/REVIEW.md",
    "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1/HANDOFF.md",
    "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1/summary.json",
    "results/hierarchy_dictionary_v1/dictionary-feasibility-v1-r1/implementation_lock.json",
    # owner sources read (read-only inspection or imported by the analysis)
    "hierarchy/decode.py", "hierarchy/ledger.py", "hierarchy/model.py", "hierarchy/wire.py",
    "hierarchy/codes.py", "hierarchy/infer.py", "hierarchy/search_v2.py", "hierarchy/consensus.py",
    "hierarchy/segmentation.py", "hierarchy/candidates.py",
    "experiments/hierarchy_multilevel/search.py", "experiments/hierarchy_dictionary/search.py",
]


def sha(p: Path):
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else None


def run_files() -> list[str]:
    """Every D2/A0 row and D2 trace, and every archive the analysis reads."""
    out = []
    for p in sorted((D / "rows").glob("*.json")):
        if p.name.endswith((".A0.json", ".D2.json")):
            out.append(p)
            row = json.loads(p.read_text())
            if row.get("trace_path"):
                out.append(D / row["trace_path"])
            out.append(D / row["archive_path"])
            for h in row.get("candidate_archives") or []:
                out.append(D / "archives" / h[:2] / f"{h}.isd")
    return sorted({q.relative_to(ID).as_posix() for q in out})


def main(stage: str) -> int:
    rec = {f: sha(ID / f) for f in FILES + run_files()}
    rec.update({f: sha(REPO / f) for f in ("index-deconvolution/notebooks/19_bdm_and_index_complexity.ipynb",
                                           "index-deconvolution/notebooks/build_19.py")})
    out = {"stage": stage, "files": len(rec), "missing": sorted(k for k, v in rec.items() if v is None),
           "hashes": rec,
           "note": "notebook 19 / build_19 hashed for record only; no claim that they equal any old snapshot"}
    (HERE / f"evidence_manifest_{stage}.json").write_text(json.dumps(out, indent=1, sort_keys=True) + "\n")
    if stage == "post":
        pre = json.loads((HERE / "evidence_manifest_pre.json").read_text())["hashes"]
        diff = sorted(k for k in set(pre) | set(rec) if pre.get(k) != rec.get(k))
        (HERE / "evidence_manifest_compare.json").write_text(json.dumps({"changed": diff}, indent=1) + "\n")
        print("changed:", diff)
    print(stage, out["files"], "files; missing", out["missing"])
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
