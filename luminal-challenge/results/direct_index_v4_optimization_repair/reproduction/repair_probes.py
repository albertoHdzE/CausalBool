"""The lead's three rejection probes, replayed against the repaired code.

Mirrors ``results/direct_index_v4_optimization/lead_review/probes.py`` exactly
in what it injects, and differs from it only in where it points and in two
places noted below. Neither production files nor any recorded evidence are
modified: the evidence checker is driven over an in-memory mutation of a report
and the benchmark phase writes to a temporary directory.

Each probe records the *same* observable the lead recorded, so the before and
after are directly comparable. The expected results after repair are:

* ``control`` true and every evidence mutation false;
* ``phase_final_classical_drift_exit`` nonzero;
* ``expired_final_cover`` UNKNOWN rather than UNSAT.
"""

from __future__ import annotations

import argparse
import contextlib
import copy
import io
import json
from pathlib import Path
import sys
import tempfile
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / ".reference")]

import benchmark_optimization as b  # noqa: E402
import check_optimization_evidence as e  # noqa: E402
import schema_index as si  # noqa: E402

RESULTS = ROOT / "results/direct_index_v4_optimization_repair"
BASELINE = ROOT / "results/direct_index_v4_optimization/baseline"

out: dict = {}

# ---------------------------------------------------------------------------
# R3: the evidence checker must reject each corruption.
# ---------------------------------------------------------------------------

original = e.Checker.require
for label in [
    "control",
    "drop_extra_corpus",
    "erase_hashes",
    "forge_confidence_interval",
    "classical_product_drift",
    # Beyond the lead's set: a report may not define its own contract, and a
    # stored gate flag may not stand in for a recomputation.
    "reduce_arm_contract",
    "forge_gate_flag",
]:

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
        return data

    with patch.object(e.Checker, "require", altered):
        checker = e.Checker(RESULTS, BASELINE)
        result = checker.run()
    out[label] = {
        "all_passed": result["all_passed"],
        "failing": [c["check"] for c in result["checks"] if not c["passed"]],
    }

# ---------------------------------------------------------------------------
# R2: a detected control failure must reach the exit code.
# ---------------------------------------------------------------------------

payload = json.loads((RESULTS / "final/runs.json").read_text())
rows = payload["runs"]
for row in rows:
    if row["arm"] == "classical" and row["scratch"] % 2 == 0:
        row["cycles"] *= 2
        row["scratch"] //= 2
with tempfile.TemporaryDirectory() as temp:
    args = argparse.Namespace(
        output=temp, baseline=str(BASELINE), allow_existing=False, timeout=20.0,
        seed=20260920, repeats=15, quiet=True, skip_extra_corpus=True,
        # The lead's probe omitted this option, which did not exist then. Set
        # here so the run reaches gate evaluation rather than being refused
        # earlier for skipping the corpus; both refusals are nonzero.
        diagnostic=True, extra_repeats=3,
    )
    with patch.object(b.Bench, "run", return_value=(rows, [], [])), \
         patch.object(b, "paired_bootstrap", return_value={"low": 1, "high": 1}), \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        out["phase_final_classical_drift_exit"] = b.phase_final(args)
    measured = json.loads((Path(temp) / "runs.json").read_text())
    gate = measured["analysis"]["frozen_classical_integers"]
    out["phase_final_drift_gate"] = {
        "passed": gate["passed"], "checked": gate["checked"],
        "drift_count": len(gate["drift"]), "detail": gate["detail"],
    }
    out["phase_final_mandatory_gates"] = {
        name: entry["passed"]
        for name, entry in measured["acceptance_gates"].items()
    }

# An unmodified replay must still exit nonzero, because it skipped the corpus,
# and must say so rather than claiming acceptance.
clean = json.loads((RESULTS / "final/runs.json").read_text())["runs"]
with tempfile.TemporaryDirectory() as temp:
    args = argparse.Namespace(
        output=temp, baseline=str(BASELINE), allow_existing=False, timeout=20.0,
        seed=20260920, repeats=15, quiet=True, skip_extra_corpus=True,
        diagnostic=True, extra_repeats=3,
    )
    with patch.object(b.Bench, "run", return_value=(clean, [], [])), \
         patch.object(b, "paired_bootstrap", return_value={"low": 1, "high": 1}), \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        out["phase_final_clean_diagnostic_exit"] = b.phase_final(args)
    measured = json.loads((Path(temp) / "runs.json").read_text())
    out["phase_final_clean_diagnostic"] = {
        "acceptance_claimed": measured["acceptance_claimed"],
        "frozen_classical_integers": measured["analysis"][
            "frozen_classical_integers"]["passed"],
        "extra_corpus_evaluated": measured["acceptance_gates"][
            "extra_corpus_evaluated"]["passed"],
    }

# Skipping the mandatory corpus without saying so is refused before measuring.
measured_calls = []
with tempfile.TemporaryDirectory() as temp:
    args = argparse.Namespace(
        output=temp, baseline=str(BASELINE), allow_existing=False, timeout=20.0,
        seed=20260920, repeats=15, quiet=True, skip_extra_corpus=True,
        diagnostic=False, extra_repeats=3,
    )
    with patch.object(b.Bench, "run",
                      side_effect=lambda *a, **k: measured_calls.append(1) or ([], [], [])), \
         contextlib.redirect_stdout(io.StringIO()), \
         contextlib.redirect_stderr(io.StringIO()):
        out["phase_final_silent_skip_exit"] = b.phase_final(args)
    out["phase_final_silent_skip_measured"] = len(measured_calls)

# ---------------------------------------------------------------------------
# R1: the deadline must be observed before a terminal verdict.
# ---------------------------------------------------------------------------

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

# The same query inside its budget must still reach a completed verdict.
with patch.object(si.time, "monotonic", side_effect=lambda: 0.0):
    meter = si.Budget(seconds=1.0).start()
    expression = si.AllOf(
        (si.Leaf((si.Cube(2, 0, 0),)),
         si.Leaf((si.Cube(2, 1, 0), si.Cube(2, 2, 0))))
    )
    out["in_budget_final_cover"] = si.solve(expression, 2, meter=meter).to_dict()

destination = Path(__file__).with_name("repair_probes.json")
destination.write_text(json.dumps(out, indent=2) + "\n")
print(json.dumps(out, indent=2))
