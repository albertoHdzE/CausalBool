"""Bounded CPU subprocess pipeline with one batched Wolfram reference lane."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import hashlib
import json
import math
import os
from pathlib import Path
import statistics
import subprocess
import time

from .full_behaviour import WOLFRAM_KERNEL
from .io import atomic_write_json, read_json
from .records import seal, scientific_digest
from .execution import run_with_timeout, CaseTimeout
from . import joint_study as joint

BATCH_SIZE = 48
WORKER_CHOICES = (8, 16, 24)


def wolfram_batch(cases, *, timeout_seconds=300):
    """One normal-exit transaction; every expected ID and output bit is checked.

    A killed/malformed batch cannot certify even a computed prefix. Timeout
    inside a normal-exit batch is retained as an individual case failure.
    """
    ids = [joint.network_hash(c) for c in cases]
    if not cases or len(ids) != len(set(ids)):
        raise ValueError("batch requires unique nonempty network IDs")
    payload = []
    for key, case in zip(ids, cases):
        params = [dict(p) for p in case["params"]]
        for p in params:
            if "canalisingIndex" in p:
                p["canalisingIndex"] += 1
        payload.append({"id": key, "cm": case["cm"], "dyn": case["dyn"], "params": params})
    code = ('$HistoryLength=0;Get["src/Packages/Integration/Gates.m"];'
            'Get["src/Packages/Integration/Experiments.m"];'
            'cases=ImportString[' + json.dumps(json.dumps(payload)) + ',"RawJSON"];'
            'out=Map[Function[p,Module[{pa,r,t},'
            'pa=Association[Table[i->p["params"][[i]],{i,Length[p["dyn"]]}]];t=AbsoluteTime[];'
            'r=TimeConstrained[Integration`Experiments`CreateRepertoiresDispatch[p["cm"],p["dyn"],pa]["RepertoireOutputs"],'
            + str(float(timeout_seconds)) + ',$Aborted];'
            'If[r===$Aborted,<|"id"->p["id"],"status"->"timeout"|>,'
            '<|"id"->p["id"],"status"->"completed","rows"->r,"elapsed_seconds"->(AbsoluteTime[]-t)|>]]],cases];'
            'WriteString["stdout",ExportString[out,"RawJSON"]];Exit[]')
    started = time.perf_counter()
    def failed(status, **details):
        return {key: {"status": status, "owner": "Wolfram", **details} for key in ids}
    try:
        proc = subprocess.run([WOLFRAM_KERNEL, "-noprompt", "-run", code], cwd=joint.ROOT,
                              text=True, capture_output=True, timeout=timeout_seconds)
    except subprocess.TimeoutExpired:
        return failed("timeout")
    except OSError as exc:
        return failed("process_failure", failure=str(exc))
    if proc.returncode:
        return failed("process_failure", exit_code=proc.returncode, failure=proc.stderr[-4000:])
    try:
        outputs = json.loads(proc.stdout)
        if (not isinstance(outputs, list) or len(outputs) != len(ids)
                or any(not isinstance(item, dict) for item in outputs)
                or sorted(item.get("id", "") for item in outputs) != sorted(ids)):
            raise ValueError("batch ID coverage mismatch")
        indexed = {item["id"]: item for item in outputs}
        results = {}
        for key, case in zip(ids, cases):
            item = indexed[key]
            if item.get("status") == "timeout":
                results[key] = {"status": "timeout", "owner": "Wolfram"}
                continue
            rows, n = item.get("rows"), case["network_size"]
            if (item.get("status") != "completed" or not isinstance(rows, list) or len(rows) != 2**n
                    or any(not isinstance(row, list) or len(row) != n
                           or any(type(bit) is not int or bit not in (0, 1) for bit in row) for row in rows)):
                raise ValueError(f"malformed matrix for {key}")
            results[key] = {"status": "completed", "process_status": "normal_exit", "owner": "Wolfram",
                            "output_sha256": hashlib.sha256(bytes(b for row in rows for b in row)).hexdigest(),
                            "elapsed_seconds": (time.perf_counter()-started)/len(cases)}
        return results
    except (ValueError, TypeError, KeyError) as exc:
        return failed("malformed_payload", failure=str(exc))


def finish_record(task, result, reference, manifest):
    key, case, family = task
    result = dict(result)
    if result.get("status") == "completed":
        result["wolfram_reference"] = reference
        if reference.get("status") != "completed":
            result.update(status="reference_owner_failure", accepted_validation=False)
        elif reference.get("output_sha256") != result.get("compression", {}).get("checked_output_sha256"):
            result.update(status="reconstruction_mismatch", accepted_validation=False)
    result.update(record_kind="joint_study_network", joint_schema_version=1,
                  manifest_sha256=manifest["sha256"], network_sha256=key,
                  network=joint.network_payload(case), family=family)
    if result.get("status") == "completed":
        check = joint.validate_joint_record(result, case, manifest)
        if not check["valid"]:
            result.update(status="malformed_or_mismatched_payload", accepted_validation=False,
                          validation_errors=check["errors"])
    return seal(result)


def _python_job(task, deadline, max_nodes, worker_seconds=300):
    remaining = deadline-time.monotonic()
    if remaining <= 0:
        return {"status": "stage_budget_exhausted", "accepted_validation": False}
    return joint.run_worker(task[1], min(worker_seconds, remaining), max_nodes)


def pipeline(jobs, manifest, *, workers, batch_size, deadline, on_batch=None, before_batch=None):
    """Threads orchestrate separate Python processes; no GIL-bound CPU threads.

    At most two bounded batches are retained. While Wolfram verifies the current
    batch, Python computes the next one. No second Wolfram process is launched.
    Results and callbacks always follow the frozen task order.
    """
    if workers < 1 or batch_size < 1:
        raise ValueError("workers and batch size must be positive")
    completed = []
    timings = []
    chunks = [jobs[i:i+batch_size] for i in range(0, len(jobs), batch_size)]
    limit = manifest["limits"]
    def submit(pool, chunk):
        return [pool.submit(_python_job, task, deadline, limit["max_nodes"], limit["worker_seconds"]) for task in chunk]
    with ThreadPoolExecutor(max_workers=workers) as python_pool, ThreadPoolExecutor(max_workers=1) as reference_pool:
        futures = None
        for index, chunk in enumerate(chunks):
            if time.monotonic() >= deadline:
                break
            if before_batch:
                before_batch()
            started = time.perf_counter()
            futures = futures or submit(python_pool, chunk)
            results = [f.result() for f in futures]
            good = [task[1] for task, row in zip(chunk, results) if row.get("status") == "completed"]
            remaining = deadline-time.monotonic()
            ref_future = (reference_pool.submit(wolfram_batch, good, timeout_seconds=min(limit["worker_seconds"], remaining))
                          if good and remaining > 0 else None)
            # A failed worker halts new dispatch, but already computed results
            # are still checkpointed with their explicit verification status.
            future_jobs = (submit(python_pool, chunks[index+1]) if len(good) == len(chunk)
                           and index+1 < len(chunks) and remaining > 0 else None)
            references = ref_future.result() if ref_future else {}
            rows = [finish_record(task, result, references.get(task[0], {"status": "not_run"}), manifest)
                    for task, result in zip(chunk, results)]
            timing = {"batch": index, "n_networks": len(chunk), "elapsed_seconds": time.perf_counter()-started,
                      "peak_worker_rss_bytes": max((r.get("peak_worker_rss_bytes", 0) for r in rows), default=0)}
            if on_batch:
                on_batch(rows, timing)
            else:
                completed.extend(rows)
            timings.append(timing)
            if any(not r.get("accepted_validation") for r in rows):
                if future_jobs:
                    for future in future_jobs:
                        future.cancel()
                break
            futures = future_jobs
    return completed, timings


def calibration_jobs(manifest):
    grouped = {}
    for task in joint.tasks(manifest):
        if task[2] != "stress":
            group = grouped.setdefault((task[1]["network_size"], task[2]), [])
            if len(group) < 4:
                group.append(task)
    return [task for key in sorted(grouped) for task in grouped[key]]


def choose_workers(trials, *, memory_budget_bytes, cpu_count):
    eligible = []
    for workers in sorted({t["workers"] for t in trials}):
        matching = [t for t in trials if t["workers"] == workers]
        peak = max(t["peak_worker_rss_bytes"] for t in matching)
        # Two times measured Python RSS per worker + 4 GiB for the coordinator,
        # buffered matrices and single Wolfram lane. This is a conservative
        # admission estimate, not a claim of a macOS hard memory limit.
        estimated = 2*peak*workers + 4*1024**3
        if workers <= max(1, cpu_count-4) and estimated <= memory_budget_bytes and all(t["passed"] for t in matching):
            eligible.append({"workers": workers, "median_seconds": statistics.median(t["elapsed_seconds"] for t in matching),
                             "estimated_peak_bytes": estimated})
    if not eligible:
        raise ValueError("no safe, validated concurrency configuration")
    fastest = min(e["median_seconds"] for e in eligible)
    return min((e for e in eligible if e["median_seconds"] <= 1.05*fastest), key=lambda e: e["workers"])


def calibrate(root, manifest):
    root = Path(root)
    if (root / "execution.json").exists():
        raise ValueError("execution profile already frozen; use its existing evidence or a new directory")
    cpu_count = os.cpu_count() or 1
    proc = subprocess.run(["sysctl", "-n", "hw.memsize"], text=True, capture_output=True)
    if proc.returncode:
        raise RuntimeError(f"cannot inspect memory for safe calibration: {proc.stderr}")
    memory_bytes = int(proc.stdout.strip())
    memory_budget = memory_bytes*2//3
    jobs = calibration_jobs(manifest)
    if len(jobs) != 48:
        raise ValueError("calibration requires four cases from each of the 12 planned size/family strata")
    baseline, trials, errors = [], [], []
    started = time.perf_counter()
    for i, task in enumerate(jobs):
        row = joint.run_worker(task[1], 300, manifest["limits"]["max_nodes"])
        ref = joint.wolfram_reference(task[1], timeout_seconds=300)
        record = finish_record(task, row, ref, manifest)
        baseline.append(record)
        atomic_write_json(root / "calibration/serial" / f"{task[0]}.json", record)
        if not record["accepted_validation"]:
            errors.append(f"serial_calibration_failure:{task[0]}")
            break
        print(json.dumps({"calibration": "serial", "completed": i+1, "total": len(jobs)}), flush=True)
    serial_seconds = time.perf_counter()-started
    if not errors:
        expected = [r["scientific_digest"] for r in baseline]
        # Reversed second sweep reduces systematic warm-up/order bias.
        for repeat, choices in enumerate((WORKER_CHOICES, tuple(reversed(WORKER_CHOICES)))):
            for workers in choices:
                if workers > max(1, cpu_count-4):
                    continue
                admission = 2*max(r["peak_worker_rss_bytes"] for r in baseline)*workers+4*1024**3
                if admission > memory_budget:
                    continue
                started = time.perf_counter()
                rows, batches = pipeline(jobs, manifest, workers=workers, batch_size=BATCH_SIZE,
                                         deadline=time.monotonic()+600)
                passed = len(rows) == len(expected) and all(r["accepted_validation"] for r in rows) and [r["scientific_digest"] for r in rows] == expected
                trial = {"workers": workers, "repeat": repeat, "elapsed_seconds": time.perf_counter()-started,
                         "passed": passed, "scientific_digests": [r["scientific_digest"] for r in rows],
                         "peak_worker_rss_bytes": max((r.get("peak_worker_rss_bytes", 0) for r in rows), default=0),
                         "batches": batches}
                trials.append(trial)
                atomic_write_json(root / f"calibration/trial_w{workers}_r{repeat}.json", seal(trial))
                print(json.dumps({k: trial[k] for k in ("workers", "repeat", "elapsed_seconds", "passed")}), flush=True)
                if not passed:
                    errors.append(f"serial_parallel_mismatch:w{workers}:r{repeat}")
                    atomic_write_json(root / f"calibration/failure_w{workers}_r{repeat}.json", seal({"rows": rows}))
                    break
            if errors:
                break
    chosen = None
    if not errors:
        try:
            chosen = choose_workers(trials, memory_budget_bytes=memory_budget, cpu_count=cpu_count)
        except ValueError as exc:
            errors.append(str(exc))
    report = seal({"record_kind": "joint_study_calibration", "manifest_sha256": manifest["sha256"],
                   "provenance": joint.study_provenance(), "cpu_count": cpu_count, "physical_memory_bytes": memory_bytes,
                   "memory_budget_bytes": memory_budget, "serial_seconds": serial_seconds, "trials": trials,
                   "passed": not errors, "errors": errors, "selected_workers": chosen["workers"] if chosen else None})
    atomic_write_json(root / "calibration/report.json", report)
    if chosen:
        atomic_write_json(root / "execution.json", seal({"record_kind": "joint_study_execution",
                          "provenance": manifest["provenance"], "calibration_sha256": report["sha256"],
                          "workers": chosen["workers"], "batch_size": BATCH_SIZE, "wolfram_lanes": 1,
                          "memory_budget_bytes": memory_budget, "estimated_peak_bytes": chosen["estimated_peak_bytes"],
                          "gpu_used": False, "memory_limit_kind": "measured_conservative_admission_not_OS_hard_limit"}))
    return report


def load_execution(root, pilot):
    root = Path(root)
    execution = read_json(root / "execution.json")
    report = read_json(root / "calibration/report.json")
    if (not report["passed"] or report["manifest_sha256"] != pilot["sha256"]
            or execution["calibration_sha256"] != report["sha256"]
            or execution["provenance"] != joint.study_provenance()
            or execution["workers"] != report["selected_workers"]):
        raise ValueError("missing, changed or stale concurrency calibration")
    return execution


def run_parallel_stage(root, manifest, execution):
    """Caller holds the stage file lock. Budgets are wall time, not CPU sums."""
    root = Path(root)
    if manifest["provenance"] != joint.study_provenance() or execution["provenance"] != manifest["provenance"]:
        raise ValueError("source mismatch")
    stage_root = root / manifest["stage"]
    state_path = stage_root / "progress.json"
    state = (read_json(state_path) if state_path.exists() else
             {"used_seconds": 0.0, "manifest_sha256": manifest["sha256"], "execution_sha256": execution["sha256"], "batches": []})
    if state["manifest_sha256"] != manifest["sha256"] or state.get("execution_sha256") != execution["sha256"]:
        raise ValueError("checkpoint configuration/execution mismatch")
    initial_used = state["used_seconds"]
    started = time.monotonic()
    deadline = started+max(0, manifest["limits"]["stage_seconds"]-initial_used)
    jobs = list(joint.tasks(manifest))
    pending, accepted = [], 0
    for task in jobs:
        path = stage_root / "networks" / f"{task[0]}.json"
        if path.exists():
            if not joint.validate_joint_record(read_json(path), task[1], manifest)["valid"]:
                raise ValueError("invalid/failed checkpoint; retained for diagnosis")
            accepted += 1
        else:
            pending.append(task)
    def before_batch():
        # Also covers the next prefetched batch. Reserve wall allowance rather
        # than workers*allowance. An interrupted reservation remains charged.
        state["used_seconds"] = min(manifest["limits"]["stage_seconds"],
                                    initial_used+time.monotonic()-started+2*manifest["limits"]["worker_seconds"])
        state["active_batch"] = True
        atomic_write_json(state_path, seal(state))
    def checkpoint(rows, timing):
        nonlocal accepted
        for row in rows:
            atomic_write_json(stage_root / "networks" / f"{row['network_sha256']}.json", row)
            accepted += int(row["accepted_validation"])
        state["batches"].append(timing)
        state.update(n_accepted=accepted, n_expected=len(jobs), last_batch_failed=any(not r["accepted_validation"] for r in rows))
        # Keep the reservation while prefetched children are still alive.
        atomic_write_json(state_path, seal(state))
        print(json.dumps({"stage": manifest["stage"], "accepted": accepted, "total": len(jobs),
                          "workers": execution["workers"], "used_seconds": round(initial_used+time.monotonic()-started, 2),
                          "last_batch_failed": state["last_batch_failed"]}), flush=True)
    stop_reason = "completed"
    if pending and time.monotonic() < deadline:
        pipeline(pending, manifest, workers=execution["workers"], batch_size=execution["batch_size"],
                 deadline=deadline, on_batch=checkpoint, before_batch=before_batch)
    audit = {"record_kind": "joint_study_audit", "stage": manifest["stage"], "manifest_sha256": manifest["sha256"],
             "n_expected": len(jobs), "n_accepted": accepted, "n_missing": len(jobs)-accepted,
             "release_ready": False, "errors": []}
    try:
        remaining = deadline-time.monotonic()
        if remaining <= 0:
            raise CaseTimeout("wall budget exhausted")
        def finalize():
            checked = joint.audit_stage(root, manifest)
            if checked["release_ready"]:
                joint.summarize_stage(root, manifest)
            return checked
        audit = run_with_timeout(finalize, remaining)
        if not audit["release_ready"]:
            stop_reason = "incomplete_or_failed_cases"
    except CaseTimeout:
        stop_reason = "stage_budget_exhausted"
        audit["errors"].append("stage_budget_exhausted_before_release")
    except (ValueError, KeyError) as exc:
        stop_reason = "finalization_failure"
        audit["errors"].append(str(exc))
    state.update(used_seconds=initial_used+time.monotonic()-started, active_batch=False,
                 n_accepted=accepted, n_expected=len(jobs))
    atomic_write_json(state_path, seal(state))
    audit.update(used_seconds=state["used_seconds"], execution_sha256=execution["sha256"], stop_reason=stop_reason)
    atomic_write_json(stage_root / "audit.json", seal(audit))
    return audit
