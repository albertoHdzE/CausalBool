"""Derive the Phase 2 manuscript table from the retained accepted evidence."""
from pathlib import Path
import hashlib
import json

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
RUN_REL = "results/phase2_structural_encoding/phase2_repair_20260923c"
RUN = ROOT / RUN_REL
OUT = HERE / "generated"
EXPECTED_PROGRAMS = [f"0{i}_{name}.json" for i, name in enumerate([
    "scalar_pipeline", "scalar_dual_chain", "vector_axpy", "vector_bitmix",
    "mixed_broadcast", "parallel_memory", "scalar_selects", "vector_reduction"], 1)]
EXPECTED_UNION = [0, 234, 194, 55, 135, 16, 168, 17]


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def read_json(relative):
    path = ROOT / relative
    return json.loads(path.read_text()), path


def generate():
    p1_rel = RUN_REL + "/p1/summary.json"
    p0_rel = RUN_REL + "/p0/summary.json"
    paths = [
        RUN_REL + "/LEAD_ACCEPTANCE.md", RUN_REL + "/manifest.json",
        RUN_REL + "/gates.json", RUN_REL + "/hypotheses.json",
        RUN_REL + "/checker.json", p0_rel, p1_rel,
        "plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md",
        "plan/phase2/PROTOCOL.json",
    ]
    sources = {}
    docs = {}
    for rel in paths:
        docs[rel], path = read_json(rel) if rel.endswith(".json") else (None, ROOT / rel)
        sources[rel] = sha256(path)

    p1 = docs[p1_rel]
    gates = docs[RUN_REL + "/gates.json"]
    checker = docs[RUN_REL + "/checker.json"]
    p0 = docs[p0_rel]
    assert len(p1["fixtures"]) == 12 and len(p0["fixtures"]) == 12
    assert p1["exhausted_comparisons"] == 24
    assert all(set(fixture["codecs"]) == {"absolute", "static_rank", "structural_rank", "vector_block"}
               for fixture in p1["fixtures"])
    assert sum(codec["round_trips"] for fixture in p1["fixtures"]
               for codec in fixture["codecs"].values()) == 564
    assert p1["round_trip_failures"] == 0 and p1["defect_count"] == 0
    assert p1["sampling_raw_rows"] == p1["sampling_attempts_drawn"] == 160000
    assert p1["stream_count"] == 16 and p1["sampling_completions"] == 819
    assert p1["sampling_case_checks"] == 1356 and p1["sampling_discrepancy_count"] == 0
    assert p1["sampling_case_failures"] == 0
    assert p1["coverage_minimum"] == 100 and not p1["coverage_met"]
    assert p0["stage"] == "p0"
    assert gates["p0"]["status"] == "PASS"
    assert gates["p1"]["status"] == "INCONCLUSIVE"
    assert all(gates[f"p{i}"]["status"] == "BLOCKED_BY_GATE" for i in range(2, 6))
    assert checker["finding_count"] == 0 and checker["artifacts_internally_consistent"]
    assert checker["artifacts_complete"] is False and checker["scientific_success"] is False
    assert [r["program"] for r in p1["public_coverage"]] == EXPECTED_PROGRAMS
    assert [r["distinct_complete_union"] for r in p1["public_coverage"]] == EXPECTED_UNION
    assert all(r["raw_complete"] == 0 for r in p1["public_coverage"])
    assert all(r["meets_minimum"] == (r["distinct_complete_union"] >= p1["coverage_minimum"])
               for r in p1["public_coverage"])
    assert all(r["case_failures"] == 0 for r in p1["public_coverage"])

    raw_hashes = {}
    for name, expected in p1["raw_artifacts"].items():
        rel = RUN_REL + "/p1/" + name
        observed = sha256(ROOT / rel)
        assert observed == expected, f"raw artifact hash mismatch: {rel}"
        raw_hashes[rel] = observed

    rows = []
    for item in p1["public_coverage"]:
        status = "meets minimum" if item["meets_minimum"] else "below minimum"
        label = item["program"].split("_", 1)[1].removesuffix(".json").replace("_", " ")
        rows.append(
            f"{label} & {item['raw_complete']} & "
            f"{item['path_complete']} & {item['distinct_complete_union']} & {status} \\\\"
        )
    (OUT / "phase2_coverage_rows.tex").write_text("\n".join(rows) + "\n")
    metrics = {
        "run_id": "phase2_repair_20260923c",
        "run_date": "2026-09-23",
        "source_sha256": sources,
        "raw_artifact_sha256_verified_against_p1_summary": raw_hashes,
        "finite_checks": {"fixtures": 12, "codecs": 4, "exhausted_code_universes": 24,
                          "round_trips": 564, "round_trip_failures": 0},
        "sampling": {"attempts": 160000, "streams": 16, "completed_draws": 819,
                     "case_checks": 1356, "discrepancies": 0,
                     "raw_bit_completions": 0, "coverage_minimum_per_program": 100},
        "public_coverage": p1["public_coverage"],
        "stages": {"p0": "PASS", "p1": "INCONCLUSIVE",
                   "p2": "BLOCKED_BY_GATE", "p3": "BLOCKED_BY_GATE",
                   "p4": "BLOCKED_BY_GATE", "p5": "BLOCKED_BY_GATE"},
        "checker": {"findings": 0, "artifacts_internally_consistent": True,
                    "artifacts_complete": False, "scientific_success": False},
    }
    (OUT / "phase2_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n")
    return metrics


if __name__ == "__main__":
    result = generate()
    print(f"PASS: Phase 2 evidence derived; {len(result['public_coverage'])} public rows")
