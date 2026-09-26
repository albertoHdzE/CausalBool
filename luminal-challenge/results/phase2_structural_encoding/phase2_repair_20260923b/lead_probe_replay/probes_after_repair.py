"""The lead's six probes, re-run after the repair, with their outcomes recorded.

`probes_replayed.py` is the lead's `probes.py` with one line changed (the output
directory). It now stops at the third probe, because that probe installs a
`machine.check_case` mock whose whole purpose is to raise when the case validator
is reached: before the repair the sampler never reached it, and the lead recorded
three completions with zero case-validator calls. Its raising now *is* the
result, and it ends the script.

This file runs all six probes with that one step made non-fatal: the mock counts
calls and delegates to the real validator instead of raising, so the remaining
probes can run in the same process. Everything else is the lead's own probe body.

Probe 2 (the erased-evidence corruption) is applied to a NEW valid control, not to
`phase2_20260922_final`: the strengthened provenance deliberately rejects that
historical run because it predates the required metadata, so corrupting it would
prove nothing. The old run's outcome is recorded too, with its reason.
"""

from pathlib import Path
import contextlib
import io
import json
import shutil
import sys
import tempfile
from unittest.mock import patch

import machine

import direct_compiler as dc
import direct_contract as facts_owner
from research import run_structural_experiments as r
from research import check_structural_evidence as ck
from research import structural_encoding as se

ROOT = Path.cwd()
OUT = ROOT / "results/phase2_structural_encoding/phase2_repair_20260923b/lead_probe_replay"
HISTORICAL = ROOT / "results/phase2_structural_encoding/phase2_20260922_final"
REPAIRED = ROOT / "results/phase2_structural_encoding/phase2_repair_20260923b"
CONTRACT = ROOT / "plan/phase2"
findings = {}


def checker(path, contract=CONTRACT):
    buffer = io.StringIO()
    with contextlib.redirect_stdout(buffer):
        code = ck.main(["--run", str(path), "--contract", str(contract)])
    result = json.loads(buffer.getvalue())
    return {
        "exit": code,
        "findings": [item["check"] for item in result.get("findings", [])],
        "finding_count": result.get("finding_count"),
        "complete": result.get("artifacts_complete"),
        "inconclusive": result.get("inconclusive_count"),
    }


def resync(run):
    """Recompute the stage digests and row counts, as the review requires."""

    path = Path(run) / "manifest.json"
    manifest = json.loads(path.read_text())
    digests = dict(manifest.get("stage_digests") or {})
    for stage in ("preflight", "p0", "p1", "p2", "p3", "p4", "p5"):
        summary = Path(run) / stage / "summary.json"
        if summary.is_file():
            digests[stage] = r.file_digest(summary)
    manifest["stage_digests"] = digests
    manifest["row_counts"] = {
        str(item.relative_to(run)): sum(
            1 for line in item.read_text().splitlines() if line.strip()
        )
        for item in sorted(Path(run).rglob("*.jsonl"))
    }
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True))


# -- probe 1: the checker on an unmutated control ---------------------------

findings["checker_control_repaired"] = checker(REPAIRED)
findings["checker_control_historical"] = checker(HISTORICAL)
findings["checker_control_historical_note"] = (
    "The historical run predates the amendment: it records no amendment hashes "
    "and no raw sampling attempts, so the strengthened checker rejects it. That "
    "rejection is not evidence about the targeted mutation, which is why probe 2 "
    "uses a new valid control."
)

# -- probe 2: the erased-evidence corruption, on the new valid control ------

with tempfile.TemporaryDirectory(prefix="phase2-repair-probe-") as temporary:
    target = Path(temporary) / "copy"
    shutil.copytree(REPAIRED, target)
    summary_path = target / "p1/summary.json"
    payload = json.loads(summary_path.read_text())
    payload["fixtures"] = []
    payload["public_coverage"] = []
    summary_path.write_text(json.dumps(payload))
    (target / "p1/sampling_streams.jsonl").write_text("")
    gates = json.loads((target / "gates.json").read_text())
    gates["p1"]["status"] = "PASS"
    (target / "gates.json").write_text(json.dumps(gates))
    for name in ("decoder_rows.jsonl", "oracle_domains.jsonl",
                 "sampling_attempts.jsonl", "sampling_identities.jsonl"):
        (target / "p1" / name).unlink()
    # The lead's probe left the manifest alone. Recomputing the digests is the
    # harder test: it removes the hash disagreement and leaves only the content.
    findings["checker_empty_p1_without_rehash"] = checker(target)
    resync(target)
    findings["checker_empty_p1_rehashed"] = checker(target)

# -- probe 3: case validation on a constant legal domain --------------------

record = json.loads((CONTRACT / "FIXTURES.json").read_text())["fixtures"][0]
record = json.loads(json.dumps(record))
incumbent = record["incumbent"]
times = {
    str(index): cycle
    for cycle, bundle in enumerate(incumbent["bundles"])
    for ids in bundle.values()
    for index in ids
}
for key in record["time_domains"]:
    record["time_domains"][key] = [times[key]]
for key in record["address_domains"]:
    record["address_domains"][key] = [incumbent["scratch"][key]]
domain = se.Domain.from_record(record)

real_check_case = machine.check_case
with patch.object(machine, "check_case", side_effect=real_check_case) as case:
    sink = r._ListSink()
    stream, identities = r.raw_bit_stream(
        domain, "structural_rank", 20260922, 3, 10, sink=sink,
        identity={"program": "lead_probe"},
    )
findings["sampler_case_validation"] = {
    "complete": stream["complete"],
    "case_calls": case.call_count,
    "cases_declared": stream["cases_declared"],
    "case_checks_recorded": stream["case_checks"],
    "raw_rows_written": stream["raw_rows_written"],
    "retained_completions": len(stream["completions"]),
    "display_excerpt": len(stream["complete_examples_excerpt"]),
    "lead_recorded_case_calls": 0,
}

# -- probe 4: resuming into P2 on an inconclusive P1 ------------------------

entered = []


def dummy_p2(run):
    prior = run.prior("p1")
    entered.append(prior["coverage_met"])
    return {"stage": "p2", "review_probe_only": True}


with tempfile.TemporaryDirectory(prefix="phase2-resume-", dir=OUT) as temporary, \
        patch.object(r, "RESULTS", Path(temporary)), \
        patch.dict(r.STAGE_FUNCTIONS, {"p2": dummy_p2}):
    with contextlib.redirect_stdout(io.StringIO()):
        code = r.main(
            ["--stage", "p2", "--run-id", "probe", "--contract", str(CONTRACT),
             "--inputs", str(REPAIRED)]
        )
    gates = json.loads((Path(temporary) / "probe" / "gates.json").read_text())
findings["resume_gate_bypass"] = {
    "exit": code,
    "entered_p2_with_prior_coverage": entered,
    "p2_status": gates["p2"]["status"],
    "p2_reason": gates["p2"]["reason"],
    "lead_recorded_exit": 0,
    "lead_recorded_entered": [False],
}

# -- probe 5: construction time debited from the search allowance ----------

program = machine.load_program(ROOT / ".reference/programs/02_scalar_dual_chain.json")
compiled, _ = dc.compile_with_report(program, optimise=False)
facts = facts_owner.derive(program)
issue_times = se.issue_cycles_of(program, compiled["bundles"])
addresses = compiled["scratch"]
limits = json.loads((CONTRACT / "PROTOCOL.json").read_text())["budgets"]
clock = [0.0]
original = r.matched_window_record
captured = []


class ReachedSearch(Exception):
    pass


def slow_construction(*args, **kwargs):
    result = original(*args, **kwargs)
    clock[0] += 1.0
    return result


def capture_search(domain_, incumbent_, arm_, budget_, **kwargs):
    captured.append(
        {"clock_at_search": clock[0], "budget_seconds": budget_.seconds,
         "deadline": kwargs.get("deadline")}
    )
    raise ReachedSearch


record_out = None
with patch.object(r.time, "perf_counter", side_effect=lambda: clock[0]), \
        patch.object(r, "matched_window_record", side_effect=slow_construction), \
        patch.object(r.ss, "search", side_effect=capture_search):
    try:
        _, _, record_out = r.structural_optimise(
            program, facts, issue_times, addresses, "structural_bound",
            0.01, 0.01, 32, limits,
        )
    except ReachedSearch:
        pass
findings["construction_budget_not_debited"] = {
    "global_budget": 0.01,
    "calls": captured,
    "stopped_because": None if record_out is None else record_out["stopped_because"],
    "interrupted_attempts": (
        [] if record_out is None else record_out["interrupted_attempts"]
    ),
    "lead_recorded_calls": [{"clock_at_search": 1.0, "budget_seconds": 0.01}],
}

# -- probe 6: the conditional model arm ------------------------------------

try:
    _, _, model_record = r.structural_optimise(
        program, facts, issue_times, addresses, r.MODEL_ARM, 0.1, 0.1, 32, limits,
    )
    findings["conditional_model_arm"] = {
        "exception": None,
        "arm": model_record["arm"],
        "attempted_queries": model_record["attempted_queries"],
        "phases": model_record["phases"],
        "lead_recorded": {"exception": "ValueError",
                          "message": "unknown search arm 'structural_model'"},
    }
except Exception as exc:  # noqa: BLE001 - the probe records whatever happens
    findings["conditional_model_arm"] = {
        "exception": type(exc).__name__, "message": str(exc)
    }

# -- probe 7: the reference manifest ---------------------------------------

original_digest = r.file_digest
reference_readme = ROOT / ".reference/README.md"
with patch.object(
    r, "file_digest",
    side_effect=lambda path: "0" * 64 if Path(path) == reference_readme
    else original_digest(path),
):
    findings["reference_manifest_entry_ignored"] = r.Contract(CONTRACT).verify_locks()
findings["reference_manifest_entry_ignored"]["lead_recorded"] = {
    "status": "PASS", "checked": 58, "findings": []
}

(OUT / "probes_after_repair.json").write_text(json.dumps(findings, indent=2) + "\n")
print(json.dumps(findings, indent=2))
