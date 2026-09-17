"""Audited individual-reference recovery and bounded main-stage resumption."""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import copy
import fcntl
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from doppel_challenge import joint_study as joint
from doppel_challenge.io import atomic_write_json
from doppel_challenge.records import seal
from doppel_challenge.execution import run_with_timeout
from doppel_challenge.program_benchmark import wolfram_reference
from doppel_challenge.repertoire_program import compile_repertoire_program, serialize_program
from doppel_challenge.adapters import Network

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("frozen_final_controller", ROOT/"tools/joint_final_phase/run.py")
original = importlib.util.module_from_spec(spec)
spec.loader.exec_module(original)
checked, require = original.checked, original.require
MAX_BATCHES = 3
RESERVATION = 360


@contextmanager
def lock(path):
    with path.open("a") as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield


def sources():
    return {str(p.relative_to(ROOT)): original.sha(p) for p in
            (Path(__file__), HERE/"test_recover.py", HERE/"AMENDMENT.md")}


def amend(root):
    original.assert_namespace(root)
    config = original.verify_config(root)
    path = root/"reference_recovery/amendment.json"
    value = seal({"record_kind": "reference_recovery_amendment", "protocol_sha256": config["sha256"],
                  "authorization": "user requested investigation, fix and resume after reference timeout",
                  "sources": sources(), "max_timeout_batches": MAX_BATCHES,
                  "individual_timeout_seconds": 300, "reservation_seconds": RESERVATION,
                  "budget_seconds": config["budgets"]["main_seconds"],
                  "scope": "individual reference recovery only; preserve frozen experiment and failed evidence"})
    original.freeze(path, value)
    return value


def eligible(row):
    require(row.get("status") == "reference_owner_failure" and row.get("accepted_validation") is False,
            "not a failed reference checkpoint")
    require(row.get("wolfram_reference", {}).get("status") == "timeout", "only timeouts qualify")
    require(row["compression"]["status"] == "completed" and row["compression"]["accepted_validation"], "Python compression failed")
    require(row["dynamics"]["accepted_validation"], "Python dynamics failed")


def replacement(row, reference, manifest, amendment_sha, attempt_path):
    eligible(row)
    require(reference.get("status") == "completed" and reference.get("process_status") == "normal_exit", "reference did not exit normally")
    require(reference.get("output_sha256") == row["compression"]["checked_output_sha256"], "reference output mismatch")
    updated = copy.deepcopy(row)
    updated.update(status="completed", accepted_validation=True, wolfram_reference=reference,
                   reference_recovery={"previous_record_sha256": row["sha256"], "amendment_sha256": amendment_sha,
                                       "attempt": attempt_path, "method": "individual_wolfram_after_batch_timeout"})
    result = joint.validate_joint_record(updated, row["network"], manifest, replay=True)
    require(result["valid"], f"recovered record invalid: {result['errors']}")
    case = row["network"]
    net = Network(case["network_size"], case["cm"], case["dyn"], case["params"])
    require(serialize_program(compile_repertoire_program(net)).hex() == row["compression"]["payload_hex"], "fresh compilation mismatch")
    return seal(updated)


def backup(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    if destination.exists():
        require(original.sha(source) == original.sha(destination), f"archive collision: {destination}")
    else:
        shutil.copy2(source, destination)
    return original.sha(destination)


def reserve(progress, base_used, elapsed, budget):
    amount = base_used + elapsed + RESERVATION
    require(amount <= budget, "insufficient original stage budget for recovery")
    progress.update(used_seconds=amount, active_batch=True)
    return progress


def recover_batch(root, amendment):
    with lock(root/"main/run.lock"):
        manifest = checked(root/"main_manifest.json")
        audit = checked(root/"main/audit.json")
        progress_path = root/"main/progress.json"
        progress = checked(progress_path)
        require(audit["manifest_sha256"] == manifest["sha256"], "audit manifest mismatch")
        require(not progress["active_batch"], "interrupted active reservation requires inspection")
        errors = audit["errors"]
        require(0 < len(errors) <= 48, "not a single recoverable batch")
        require(all(set(e.get("errors", [])) == {"not_accepted", "wolfram_mismatch"} for e in errors), "other audit errors present")
        ids = [e["network_sha256"] for e in errors]
        require(len(ids) == len(set(ids)), "duplicate failed IDs")
        planned = {key: case for key, case, _ in joint.tasks(manifest) if key in set(ids)}
        require(set(planned) == set(ids), "failed IDs outside manifest")
        directory = root/"reference_recovery"
        prior = sorted(directory.glob("batch_*/plan.json"))
        require(len(prior) < MAX_BATCHES, "timeout recovery cap reached")
        old_ids = set()
        for p in prior:
            plan = checked(p)
            require((p.parent/"report.json").exists() and checked(p.parent/"report.json")["passed"], "earlier incomplete recovery requires inspection")
            old_ids.update(plan["network_ids"])
        require(not old_ids.intersection(ids), "individual references may not be retried automatically")
        batch = directory/f"batch_{len(prior)+1:03d}"
        started, base_used = time.monotonic(), progress["used_seconds"]
        budget = manifest["limits"]["stage_seconds"]
        rows = {}
        for key in ids:
            row = checked(root/"main/networks"/f"{key}.json")
            eligible(row)
            require(row["network"] == joint.network_payload(planned[key]), "network does not match manifest")
            require(set(joint.validate_joint_record(row, row["network"], manifest, replay=True)["errors"]) == {"not_accepted", "wolfram_mismatch"}, "stored Python validation failed")
            rows[key] = row
        archives = {}
        for name in ["main/audit.json", "main/progress.json", "controller_status.json", "controller.log", *[f"main/networks/{key}.json" for key in ids]]:
            archives[name] = backup(root/name, batch/"original"/name)
        plan = seal({"record_kind": "reference_recovery_batch_plan", "network_ids": ids,
                     "amendment_sha256": amendment["sha256"], "manifest_sha256": manifest["sha256"],
                     "original_used_seconds": base_used, "original_n_accepted": progress["n_accepted"], "archive_hashes": archives})
        atomic_write_json(batch/"plan.json", plan)
        replacements = {}
        for index, key in enumerate(ids, 1):
            atomic_write_json(progress_path, seal(reserve(progress, base_used, time.monotonic()-started, budget)))
            attempt_path = batch/"attempts"/f"{key}.json"
            require(not attempt_path.exists(), "attempt already exists")
            attempt = {"record_kind": "individual_reference_attempt", "network_sha256": key,
                       "previous_record_sha256": rows[key]["sha256"], "status": "running", "timeout_seconds": 300}
            atomic_write_json(attempt_path, seal(attempt))
            t = time.monotonic()
            ref = wolfram_reference(rows[key]["network"], timeout_seconds=300)
            attempt.update(reference=ref, elapsed_seconds=time.monotonic()-t, status=ref.get("status", "malformed"))
            atomic_write_json(attempt_path, seal(attempt))
            try:
                updated = run_with_timeout(lambda: replacement(rows[key], ref, manifest, amendment["sha256"], str(attempt_path.relative_to(root))), 60)
            except Exception as exc:
                attempt.update(status="rejected", error=f"{type(exc).__name__}: {exc}")
                atomic_write_json(attempt_path, seal(attempt))
                raise
            atomic_write_json(batch/"staged"/f"{key}.json", updated)
            replacements[key] = updated
            progress.update(used_seconds=base_used+time.monotonic()-started, active_batch=False)
            atomic_write_json(progress_path, seal(progress))
            print(json.dumps({"recovery_batch": len(prior)+1, "verified": index, "total": len(ids), "network_sha256": key,
                              "reference_seconds": attempt["elapsed_seconds"], "charged_seconds": progress["used_seconds"]}), flush=True)
        atomic_write_json(batch/"validated.json", seal({"record_kind": "validated_reference_replacements",
                          "plan_sha256": plan["sha256"], "replacements": {k:r["sha256"] for k,r in replacements.items()}}))
        # Every reference has passed before any failed scientific checkpoint changes.
        for key, updated in replacements.items():
            destination = root/"main/networks"/f"{key}.json"
            require(checked(destination)["sha256"] == rows[key]["sha256"], "checkpoint changed during recovery")
            atomic_write_json(destination, updated)
        progress.update(used_seconds=base_used+time.monotonic()-started, active_batch=False,
                        n_accepted=plan["original_n_accepted"]+len(ids), last_batch_failed=False)
        atomic_write_json(progress_path, seal(progress))
        report = seal({"record_kind": "reference_recovery_batch_report", "passed": True, "n_recovered": len(ids),
                       "plan_sha256": plan["sha256"], "amendment_sha256": amendment["sha256"],
                       "elapsed_seconds": time.monotonic()-started, "cumulative_used_seconds": progress["used_seconds"],
                       "replacements": {k:r["sha256"] for k,r in replacements.items()}})
        atomic_write_json(batch/"report.json", report)
        return report


def validate_recoveries(root):
    for path in sorted((root/"reference_recovery").glob("batch_*/plan.json")):
        plan = checked(path)
        original.verify_files(path.parent/"original", plan["archive_hashes"])
        report = checked(path.parent/"report.json")
        require(report["passed"] and report["plan_sha256"] == plan["sha256"], "recovery report failed")
        for key, digest in report["replacements"].items():
            require(checked(root/"main/networks"/f"{key}.json")["sha256"] == digest, "recovered checkpoint changed")


def run(root, recover_only=False):
    from doppel_challenge.joint_parallel import load_execution
    from doppel_challenge.joint_preflight import validate_preflight
    with lock(root/"controller.lock"):
        amendment = amend(root)
        original.run_subprocess(root, "reference_recovery_tests", [sys.executable, "-m", "pytest", str(HERE/"test_recover.py"), "-q"], 300)
        require(validate_preflight(root)["valid"], "preflight changed")
        require(original.previous_release()["sha256"] == original.verify_config(root)["previous_final_release_sha256"], "previous release changed")
        pilot, manifest = (checked(root/f"{s}_manifest.json") for s in ("pilot", "main"))
        original.assert_stage(checked(root/"pilot/audit.json"), pilot)
        require(checked(root/"forecast.json")["admitted"], "original forecast did not admit main")
        execution = load_execution(root, pilot)
        try:
            # Recover only an unhandled failed batch; a successful prior recovery
            # leaves the historical failed audit in place until normal finalization.
            audit = checked(root/"main/audit.json")
            last_report = sorted((root/"reference_recovery").glob("batch_*/report.json"))
            handled = {key for p in last_report for key in checked(p)["replacements"]}
            failed_ids = {e.get("network_sha256") for e in audit["errors"]}
            if failed_ids - handled:
                report = recover_batch(root, amendment)
                original.state(root, "references_recovered", n_recovered=report["n_recovered"], cumulative_used_seconds=report["cumulative_used_seconds"])
            validate_recoveries(root)
            if recover_only:
                return
            while True:
                original.verify_config(root)
                validate_recoveries(root)
                progress = checked(root/"main/progress.json")
                original.state(root, "main", workers=execution["workers"], expected=progress["n_expected"],
                               accepted_at_resume=progress["n_accepted"], reference_recovery_amendment_sha256=amendment["sha256"],
                               charged_seconds_at_resume=progress["used_seconds"])
                result = joint.run_stage(root, manifest, execution=execution)
                if result["release_ready"]:
                    original.assert_stage(result, manifest)
                    summary = checked(root/"main/summary.json")
                    require(summary["release_ready"] and summary["manifest_sha256"] == manifest["sha256"], "summary mismatch")
                    require(len(summary["catalogues"]) == 2*len(manifest["bases"]), "catalogue coverage")
                    original.verify_config(root)
                    validate_recoveries(root)
                    original.state(root, "computation_complete_awaiting_analysis", main_networks=result["n_accepted"],
                                   main_catalogues=len(summary["catalogues"]), main_audit_sha256=result["sha256"],
                                   main_summary_sha256=summary["sha256"], scientific_analysis_release_ready=False)
                    return
                recover_batch(root, amendment)
        except Exception as exc:
            original.state(root, "stopped", error=f"{type(exc).__name__}: {exc}", scientific_analysis_release_ready=False)
            raise


def launch(root):
    amend(root)
    with lock(root/"controller.lock"):
        pass
    env = dict(os.environ, PYTHONPATH=str(ROOT/"doppel-challenge/src"))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    with (root/"controller.log").open("a") as log:
        proc = subprocess.Popen([sys.executable, str(Path(__file__)), "--action", "run", "--out-dir", str(root)],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT,
                                stdin=subprocess.DEVNULL, start_new_session=True)
    atomic_write_json(root/f"recovery_launch_{proc.pid}.json", seal({"pid": proc.pid, "sources": sources()}))
    print(json.dumps({"pid": proc.pid, "log": str(root/"controller.log")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", choices=("recover", "launch", "run"), required=True)
    parser.add_argument("--out-dir", type=Path, default=original.OUT)
    args = parser.parse_args()
    root = args.out_dir.resolve()
    original.assert_namespace(root)
    if args.action == "launch":
        launch(root)
    else:
        run(root, recover_only=args.action == "recover")


if __name__ == "__main__":
    main()
