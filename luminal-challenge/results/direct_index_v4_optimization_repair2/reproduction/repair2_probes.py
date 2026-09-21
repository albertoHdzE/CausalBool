"""The lead's re-review probes, replayed against the repaired checker.

Mirrors ``results/direct_index_v4_optimization_repair/lead_review/probes.py``
in what it injects, and differs from it only in where it points: at this
round's evidence tree rather than the previous one, because the tree records
the hashes of the very sources being audited and an earlier round's tree would
fail on hash drift alone.

Nothing on disk is modified. The checker is driven over an in-memory mutation
of each report, so both the recorded evidence and the production files are left
exactly as they are.

Expected after the F1 and F2 repairs:

* ``control`` true and **every** mutation false, including ``one_resample`` and
  ``missing_verification_stages``, which passed before;
* ``expired_final_cover`` UNKNOWN rather than UNSAT, unchanged from R1.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
import sys
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / ".reference")]

import benchmark_optimization as b  # noqa: E402
import check_optimization_evidence as e  # noqa: E402
import schema_index as si  # noqa: E402

RESULTS = ROOT / "results/direct_index_v4_optimization_repair2"
BASELINE = ROOT / "results/direct_index_v4_optimization/baseline"

out: dict = {}
original = e.Checker.require

LABELS = [
    "control",
    # The lead's original four, from the first review.
    "drop_extra_corpus",
    "erase_hashes",
    "forge_confidence_interval",
    "classical_product_drift",
    # F1 and F2 of the re-review.
    "one_resample",
    "missing_verification_stages",
    # Beyond the lead's set, kept from the previous round and extended.
    "reduce_arm_contract",
    "forge_gate_flag",
    "wrong_bootstrap_seed",
    "omit_target_declaration",
    "duplicate_stage_for_a_missing_one",
    "zero_test_stage",
    "drop_cli_program",
]

for label in LABELS:

    def altered(self, path, label=label):
        data = original(self, path)
        if data is None:
            return data
        data = copy.deepcopy(data)
        if path == RESULTS / "final/runs.json":
            if label == "drop_extra_corpus":
                data["extra_corpus"] = None
            if label == "erase_hashes":
                data["provenance"]["source_sha256"] = {}
                data["provenance"]["test_sha256"] = {}
            if label == "forge_confidence_interval":
                for entry in data["analysis"]["ratios"].values():
                    entry["paired_bootstrap_95"].update(low=999, high=1000)
            if label in ("one_resample", "wrong_bootstrap_seed"):
                # Bounds that are mathematically correct for the protocol the
                # report declares. Only the declared protocol is wrong.
                seed = 12345 if label == "wrong_bootstrap_seed" else 20260920
                resamples = 10000 if label == "wrong_bootstrap_seed" else 1
                for name, baseline_arm, candidate_arm in b.RATIOS:
                    entry = data["analysis"]["ratios"].get(name)
                    if entry is None:
                        continue
                    entry["paired_bootstrap_95"] = b.paired_bootstrap(
                        data["runs"], data["analysis"]["programs"],
                        baseline_arm, candidate_arm,
                        data["analysis"]["repetitions"],
                        seed=seed, resamples=resamples,
                    )
            if label == "omit_target_declaration":
                data["performance_targets"].pop("full_candidate_vs_frozen", None)
            if label == "reduce_arm_contract":
                dropped = "frozen_bootstrap"
                data["analysis"]["arms"] = [
                    a for a in data["analysis"]["arms"] if a != dropped
                ]
                data["runs"] = [r for r in data["runs"] if r["arm"] != dropped]
            if label == "forge_gate_flag":
                data["analysis"]["frozen_classical_integers"]["passed"] = False
                data["acceptance_gates"]["frozen_classical_integers"]["passed"] = True
        if label == "classical_product_drift" and path == RESULTS / "comparison/runs.json":
            row = next(
                r for r in data["runs"]
                if r["arm"] == "classical" and r["scratch"] % 2 == 0
            )
            row["cycles"] *= 2
            row["scratch"] //= 2
        if path == RESULTS / "verification/summary.json":
            if label == "missing_verification_stages":
                data["records"] = [
                    r for r in data["records"]
                    if r.get("stage") == "schema" or r.get("step") == "corpus"
                ]
            if label == "duplicate_stage_for_a_missing_one":
                kept = [r for r in data["records"] if r.get("stage") != "export"]
                schema = next(r for r in kept if r.get("stage") == "schema")
                data["records"] = kept + [copy.deepcopy(schema)]
            if label == "zero_test_stage":
                for record in data["records"]:
                    if record.get("stage") == "constraints":
                        record["tests"] = 0
            if label == "drop_cli_program":
                for record in data["records"]:
                    if record.get("step") == "cli":
                        record["programs"] = record["programs"][:-1]
        return data

    with patch.object(e.Checker, "require", altered):
        result = e.Checker(RESULTS, BASELINE).run()
    out[label] = {
        "all_passed": result["all_passed"],
        "failing": [c["check"] for c in result["checks"] if not c["passed"]],
    }
    print(label, out[label], flush=True)

# R1's deadline probe, unchanged, so that a repair here cannot quietly undo it.
clock = [0.0]
with patch.object(si.time, "monotonic", side_effect=lambda: clock[0]):
    meter = si.Budget(seconds=1.0).start()
    expression = si.AllOf(
        (si.Leaf((si.Cube(2, 0, 0),)),
         si.Leaf((si.Cube(2, 1, 0), si.Cube(2, 2, 0))))
    )
    intersection = meter.intersection

    def advancing_intersection(count=1):
        intersection(count)
        if count == 2:
            clock[0] = 2.0

    meter.intersection = advancing_intersection
    out["expired_final_cover"] = si.solve(expression, 2, meter=meter).to_dict()
print("expired_final_cover", out["expired_final_cover"])

destination = Path(__file__).with_name("repair2_probes.json")
destination.write_text(json.dumps(out, indent=2) + "\n")
print(str(destination))
