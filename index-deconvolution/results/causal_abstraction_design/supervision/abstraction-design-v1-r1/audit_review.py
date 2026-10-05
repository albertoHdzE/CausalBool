"""Document-integrity and declaration arithmetic only; no model execution."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[5]
RUN = ROOT / "index-deconvolution/results/causal_abstraction_design/abstraction-design-v1-r1"
OUT = Path(__file__).resolve().parent


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    start = {p.name: digest(p) for p in RUN.iterdir() if p.is_file()}
    checks = {}
    inputs = json.loads((RUN / "input_manifest.json").read_text())
    outputs = json.loads((RUN / "output_manifest.json").read_text())
    before = json.loads((RUN / "preservation_before.json").read_text())
    after = json.loads((RUN / "preservation_after.json").read_text())
    checks["18_input_hashes"] = len(inputs["inputs_read"]) == 18 and all(
        digest(ROOT / row["path"]) == row["sha256"] for row in inputs["inputs_read"]
    )
    checks["11_output_hashes"] = len(outputs["outputs"]) == 11 and all(
        digest(RUN / row["path"]) == row["sha256"] for row in outputs["outputs"]
    )
    checks["56_preserved_hashes"] = len(before["files"]) == 56 and all(
        digest(ROOT / path) == sha for path, sha in before["files"].items()
    )
    checks["preservation_records_equal"] = before["files"] == after["files"]
    for path in RUN.iterdir():
        if path.suffix == ".json":
            json.loads(path.read_text())
        elif path.suffix == ".jsonl":
            for line in path.read_text().splitlines():
                json.loads(line)
    checks["json_parse"] = True
    checks["states_and_candidate_pairs"] = 3 * 256 + 1024 == 1792 and 3 * 135 * 5 + 141 * 5 == 2730
    checks["declared_pair_counts"] = (
        3 * 675 * 42 * 256 + 705 * 52 * 1024 == 59312640
        and 2025 * 256 + 705 * 1024 == 1240320
        and 30 * 5 * 3 + 36 * 5 == 630
    )
    checks["control_count_arithmetic"] = (
        sum([6400, 4352, 10752, 6400, 512, 256, 2304]) == 30976
        and 2048 + 16 + 16 == 2080
        and sum([9, 11, 7, 10, 8, 6, 9, 8, 7]) == 75
    )
    checks["review_budget_arithmetic"] = 738 + 300 == 1038 and 1800 - 1038 == 762
    checks["12_run_files_unchanged"] = len(start) == 12 and start == {
        p.name: digest(p) for p in RUN.iterdir() if p.is_file()
    }
    result = {"checks": checks, "all_pass": all(checks.values()),
              "run_hashes": start,
              "scope": "Integrity and arithmetic only; mathematical review is in REVIEW.md."}
    (OUT / "audit_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"checks": checks, "all_pass": result["all_pass"]}))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
