"""Document integrity and declaration arithmetic only; no model execution."""

import hashlib
import json
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[5]
BASE = ROOT / "index-deconvolution/results/causal_abstraction_design"
CLOSURE = BASE / "review_closure/abstraction-design-v1-r1"
ORIGINAL = BASE / "abstraction-design-v1-r1"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    before_review = {
        str(p.relative_to(CLOSURE)): digest(p)
        for p in CLOSURE.rglob("*") if p.is_file()
    }
    checks = []

    def record(name, count, failures):
        checks.append({"check": name, "count": count,
                       "pass": not failures, "failures": failures})

    for filename, key in [("input_manifest.json", "inputs_read"),
                          ("output_manifest.json", "outputs")]:
        rows = read(CLOSURE / filename)[key]
        record(filename, len(rows), [
            r["path"] for r in rows
            if digest(ROOT / r["path"]) != r["sha256"]
        ])

    before = read(CLOSURE / "preservation_before.json")["files"]
    after = read(CLOSURE / "preservation_after.json")["files"]
    record("preservation_snapshots_equal", len(before),
           [] if before == after else ["snapshot mismatch"])
    record("protected_current_hashes", len(after), [
        p for p, h in after.items() if digest(ROOT / p) != h
    ])
    earlier = read(ORIGINAL / "preservation_before.json")["files"]
    overlap = set(earlier) & set(before)
    record("earlier_preservation_anchor", len(overlap), [
        p for p in sorted(overlap) if earlier[p] != before[p]
    ])
    original_outputs = read(ORIGINAL / "output_manifest.json")["outputs"]
    record("original_outputs", len(original_outputs), [
        r["path"] for r in original_outputs
        if digest(ORIGINAL / r["path"]) != r["sha256"]
    ])

    parsed = 0
    for path in CLOSURE.rglob("*"):
        if path.suffix == ".json":
            read(path)
            parsed += 1
        elif path.suffix == ".jsonl":
            for line in path.read_text().splitlines():
                if line.strip():
                    json.loads(line)
            parsed += 1
    record("json_and_jsonl_parsing", parsed, [])

    audit_rows = [10 * j + j % 5 for j in range(273)]
    scales = Counter(r % 5 for r in audit_rows)
    valid = (len(set(audit_rows)) == 273 and min(audit_rows) >= 0
             and max(audit_rows) < 2730
             and [scales[i] for i in range(5)] == [55, 55, 55, 54, 54])
    record("prospective_audit_selection_arithmetic", 273,
           [] if valid else ["selection arithmetic"])
    counts = (3 * 135 * 5 + 141 * 5 == 2730
              and 3 * 675 * 42 * 256 + 705 * 52 * 1024 == 59312640
              and 6400 + 4352 + 10752 + 6400 + 512 + 256 + 2304 == 30976
              and 2048 + 16 + 16 == 2080
              and 1038 + 294 + 300 == 1632)
    record("declaration_and_budget_arithmetic", 5,
           [] if counts else ["arithmetic"])
    record("closure_unchanged_during_audit", len(before_review), [
        p for p, h in before_review.items() if digest(CLOSURE / p) != h
    ])
    output = {
        "scope": "document integrity and arithmetic; no scientific execution",
        "pass": all(c["pass"] for c in checks), "checks": checks,
        "late_snapshot_limit": "No claim of continuous preservation before its timestamp.",
        "audit_selection": {"rule": "10*j + j%5, j=0..272",
                            "tau_counts": [scales[i] for i in range(5)]},
        "closure_file_hashes": before_review,
    }
    target = Path(__file__).with_suffix(".json")
    target.write_text(json.dumps(output, indent=2) + "\n")
    print(json.dumps({"pass": output["pass"], "checks": len(checks),
                      "closure_files": len(before_review)}))
    return 0 if output["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
