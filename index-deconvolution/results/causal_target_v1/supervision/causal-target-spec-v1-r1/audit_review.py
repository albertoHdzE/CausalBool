"""Read-only artifact review; all new outputs remain beside this script."""
import importlib.util
import itertools
import json
import math
import subprocess
import sys
from hashlib import sha256
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = next(p for p in HERE.parents if (p / "GOVERNANCE").is_dir())
RUN = HERE.parent.parent / "causal-target-spec-v1-r1"


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def snapshot():
    return {str(p.relative_to(RUN)): digest(p) for p in RUN.rglob("*") if p.is_file()}


def main():
    before = snapshot()
    manifest = json.loads((RUN / "evidence_manifest.json").read_text())
    pre = json.loads((RUN / "preservation_before.json").read_text())
    post = json.loads((RUN / "preservation_after.json").read_text())
    checks = {}
    checks["executor_preservation_records_equal"] = pre["files"] == post["files"]
    drift = {p: {"recorded": h, "current": digest(ROOT / p)}
             for p, h in post["files"].items() if digest(ROOT / p) != h}
    checks["preserved_inputs_match_current"] = not drift
    checks["manifest_outputs_match"] = all(digest(RUN / p) == h for p, h in manifest["outputs"].items())
    checks["additional_read_inputs_match"] = all(
        digest(ROOT / p) == v["sha256"] for p, v in manifest["additional_files_read"].items())
    packet = subprocess.run(
        [sys.executable, "-B", str(ROOT / "index-deconvolution/protocols/causal_target_v1/check_packet.py")],
        capture_output=True, text=True, check=False)
    packet_result = json.loads(packet.stdout)
    checks["packet_13_checks"] = packet.returncode == 0 and packet_result["all_pass"] and len(packet_result["checks"]) == 13
    spec = importlib.util.spec_from_file_location("reviewed_witness_checker", RUN / "check_witnesses.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.OUT = HERE / "witness_rerun.json"
    checks["witness_rerun_exit0"] = module.main() == 0
    rerun = json.loads(module.OUT.read_text())
    checks["witness_rerun_exact_result"] = rerun == json.loads((RUN / "witness_results.json").read_text())

    # Independent finite arithmetic, without producer imports/functions.
    tables = list(itertools.product((0, 1), repeat=4))
    counts = [0, 0, 0]
    for table in tables:
        degree = sum(any(table[x] != table[x ^ (1 << j)] for x in range(4)) for j in range(2))
        counts[degree] += 1
    checks["independent_two_input_count"] = counts == [2, 4, 10]
    e = [2, 2, 10, 218]
    totals = {n: sum(math.comb(n, j) * e[j] for j in range(4)) for n in (50, 100, 200)}
    checks["distinct_counts_and_bounds"] = list(totals.values()) == [4285152, 35300302, 286520602] and [math.ceil(math.log2(v)) for v in totals.values()] == [23, 26, 29]
    states = list(itertools.product((0, 1), repeat=2))
    checks["independent_W1"] = (0, 0)[::-1] == (0, 0) and (0, 1)[::-1] != (0, 1)
    checks["independent_W2"] = all((a & b) == ((a & b) | (a & b & c)) for a, b, c in itertools.product((0, 1), repeat=3))
    projection = lambda x: x[0]
    parity = lambda x: x[0] ^ x[1]
    def fibre_ok(alpha, function):
        return all(alpha(function(x)) == alpha(function(y)) for x in states for y in states if alpha(x) == alpha(y))
    checks["independent_W3"] = fibre_ok(projection, lambda x: x) and not fibre_ok(projection, lambda x: (x[0] ^ x[1], x[1]))
    checks["independent_W4"] = fibre_ok(parity, lambda x: x) and not fibre_ok(parity, lambda x: (0, x[1]))
    checks["review_preserves_original_run"] = snapshot() == before
    result = {
        "artifact_checks_all_pass": all(checks.values()), "checks": checks,
        "current_input_drift": drift, "packet": packet_result,
        "counts": {"preserved_files": len(post["files"]), "manifest_outputs": len(manifest["outputs"]),
                   "additional_read_inputs": len(manifest["additional_files_read"]), "run_files": len(before),
                   "witness_checks": rerun["denominator"]},
        "run_hashes_before_and_after": before,
        "scope": "Artifact integrity and tiny witness arithmetic only. Scientific decision and specification findings are in REVIEW.md; passing here is not acceptance."
    }
    (HERE / "audit_review.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"all_pass": all(checks.values()), "checks": checks, "counts": result["counts"], "drift": drift}, indent=2))
    return 0 if all(checks.values()) else 1


if __name__ == "__main__":
    sys.exit(main())
