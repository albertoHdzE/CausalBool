"""Closure integrity audit; writes only its own acceptance record."""
import json
import math
from fractions import Fraction
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "GOVERNANCE").is_dir())
BASE = HERE.parent.parent
CLOSURE = BASE / "review_closure/causal-target-spec-v1-r1"


def read(path):
    return json.loads(path.read_text())


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def snapshot(path):
    return {str(p.relative_to(ROOT)): digest(p) for p in path.rglob("*") if p.is_file()}


def main():
    before = snapshot(CLOSURE)
    pre, post = [read(CLOSURE / f"preservation_{s}.json") for s in ("before", "after")]
    manifest = read(CLOSURE / "evidence_manifest.json")
    checks = {}
    protected = {}
    for group, count in (("run_files", 20), ("supervision_files", 5), ("preserved_inputs", 25)):
        checks[group + "_records_equal"] = pre[group] == post[group] and len(post[group]) == count
        protected.update(post[group])
    checks["all_50_current_hashes_match"] = len(protected) == 50 and all(digest(ROOT / p) == h for p, h in protected.items())
    checks["original_run_exact_file_set"] = snapshot(BASE / "causal-target-spec-v1-r1") == post["run_files"]
    checks["original_supervision_exact_file_set"] = snapshot(BASE / "supervision/causal-target-spec-v1-r1") == post["supervision_files"]
    checks["all_12_output_hashes_match"] = len(manifest["outputs"]) == 12 and all(digest(ROOT / p) == h for p, h in manifest["outputs"].items())
    checks["manifest_matches_final_snapshot"] = digest(CLOSURE / "evidence_manifest.json") == post["manifest_sha256"]
    for p in CLOSURE.rglob("*.json"):
        read(p)
    for p in CLOSURE.rglob("*.jsonl"):
        for line in p.read_text().splitlines():
            json.loads(line)
    checks["all_json_and_jsonl_parse"] = True
    weights = [math.comb(16, j) * e for j, e in enumerate((2, 2, 10, 218))]
    checks["distribution_arithmetic"] = weights == [2, 32, 1200, 122080] and sum(weights) == 123314 and 2 * Fraction(1, 4) + 4 * Fraction(1, 8) == 1
    contract = read(CLOSURE / "corrected/target_contract.json")
    checks["machine_contract_no_execution"] = contract["primary_future_target"]["go_decision"] is False and contract["primary_future_target"]["prior_art"]["decision"] == "NO_JUSTIFIED_IMPLEMENTATION for the withdrawn draft query study"
    charges = json.loads((CLOSURE / "time_ledger.jsonl").read_text().splitlines()[-1])
    checks["budget_arithmetic"] = charges["conservative_charge_s"] == 417 and charges["cumulative_charged_s"] == 760 + 600 + 417 and charges["cumulative_charged_s"] + 300 <= 3600
    source_paths = {"arXiv:1706.06934v1": Path("/private/tmp/bshouty_costa_1706.06934.pdf"),
                    "Akutsu1999_PSB": Path("/private/tmp/ak99.pdf")}
    source_hashes = {name: digest(path) if path.is_file() else None for name, path in source_paths.items()}
    checks["retrieved_pdf_hashes_match"] = all(source_hashes[name] == manifest["retrieved_sources"][name]["sha256"] for name in source_paths)
    checks["closure_preserved_during_review"] = before == snapshot(CLOSURE)
    result = {"all_pass": all(checks.values()), "checks": checks,
              "closure_snapshot": before, "protected_snapshot": protected,
              "retrieved_pdf_hashes": source_hashes,
              "nonblocking_metadata_erratum": "The hash-matching Akutsu1999 PDF has 12 pages (pdfinfo); the closure records 10. See REVIEW.md.",
              "budget": {"executor_original_s": 760, "supervisor_original_s": 600,
                         "closure_s": 417, "supervisor_acceptance_charge_s": 300,
                         "total_s": 2077, "ceiling_s": 3600},
              "scope": "Hash/JSON/arithmetic checks. Scientific acceptance and qualified interpretation are in REVIEW.md. No scientific jobs or witness checker executed."}
    (HERE / "audit_acceptance.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"all_pass": result["all_pass"], "checks": checks, "closure_files": len(before)}, indent=2))
    return 0 if result["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
