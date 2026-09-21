"""Start the frozen final replication using the existing exact study owners."""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import fcntl
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from doppel_challenge.io import atomic_write_json, read_json
from doppel_challenge.records import seal, compute_sha256, scientific_digest
from doppel_challenge import joint_study as joint

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
OUT = ROOT / "doppel-challenge/results/joint_degree5_final_replication_v1"
PREVIOUS = ROOT / "doppel-challenge/results/joint_degree5_v2"
PREVIOUS_FINAL = ROOT / "doppel-challenge/results/joint_degree5_final_analysis_v1"
MAIN_SEEDS = tuple(range(1000, 1100))
PILOT_SEEDS = tuple(range(2000, 2003))


def require(ok, message):
    if not ok:
        raise ValueError(message)


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def checked(path):
    record = read_json(path)
    require(record["sha256"] == compute_sha256(record), f"canonical digest mismatch: {path}")
    require(record["scientific_digest"] == scientific_digest(record), f"scientific digest mismatch: {path}")
    return record


def verify_files(root, hashes):
    require(bool(hashes), "missing artifact hashes")
    for name, digest in hashes.items():
        path = (root / name).resolve()
        require(path.is_relative_to(root.resolve()) and sha(path) == digest, f"changed artifact: {name}")


def controller_sources():
    return {str(p.relative_to(ROOT)): sha(p) for p in (HERE/"run.py", HERE/"test_run.py", HERE/"PROTOCOL.md")}


def previous_release():
    release = checked(PREVIOUS_FINAL/"release.json")
    require(release["release_ready"] and not release["errors"], "previous final release not ready")
    verify_files(PREVIOUS_FINAL, release["artifact_hashes"])
    verify_files(ROOT, release["source_hashes"])
    parent = checked(PREVIOUS/"scientific_release.json")
    require(parent["release_ready"] and not parent["errors"], "previous experiment not ready")
    verify_files(PREVIOUS, parent["artifact_hashes"])
    require(parent["sha256"] == release["parent_record_sha256"] and sha(PREVIOUS/"scientific_release.json") == release["parent_file_sha256"], "parent link mismatch")
    require(parent["provenance"] == joint.study_provenance(), "frozen study sources/environment changed")
    return release


def assert_namespace(root):
    target = root.resolve()
    require(target.is_relative_to((ROOT/"doppel-challenge/results").resolve()), "output must be a study results directory")
    require(target not in ((ROOT/"doppel-challenge/results").resolve(),), "output needs a specific namespace")
    for protected in (PREVIOUS, PREVIOUS_FINAL):
        require(not target.is_relative_to(protected.resolve()) and not protected.resolve().is_relative_to(target), "output overlaps previous results")


def freeze(path, value):
    if path.exists():
        require(checked(path) == value, f"frozen configuration changed: {path}")
    else:
        atomic_write_json(path, value)


def prepare(root):
    assert_namespace(root)
    parent = previous_release()
    manifests = {"pilot": joint.make_manifest("pilot", seeds=PILOT_SEEDS),
                 "main": joint.make_manifest("main", seeds=MAIN_SEEDS)}
    prior_manifests = [checked(PREVIOUS/f"{s}_manifest.json") for s in ("main", "pilot")]
    prior_seeds = set().union(*(set(m["seeds"]) for m in prior_manifests))
    require(not (set(MAIN_SEEDS) & (set(PILOT_SEEDS) | prior_seeds)), "main seeds overlap previous/pilot seeds")
    require(not (set(PILOT_SEEDS) & prior_seeds), "pilot seeds overlap previous seeds")
    counts = {}
    ids = {}
    for stage, m in manifests.items():
        tasks = list(joint.tasks(m))
        ids[stage] = {key for key, _, _ in tasks}
        strata = Counter((case["network_size"], family) for _, case, family in tasks if family != "stress")
        counts[stage] = {"base_draws": len(m["bases"]), "catalogue_definitions": 2*len(m["bases"]),
                         "unique_networks": len(tasks), "strata": [{"n": n, "family": fam, "networks": count} for (n, fam), count in sorted(strata.items())]}
    previous_ids = {key for m in prior_manifests for key, _, _ in joint.tasks(m)}
    old_pilot = checked(PREVIOUS/"pilot_manifest.json")
    old_counts = Counter((case["network_size"], fam) for _, case, fam in joint.tasks(old_pilot) if fam != "stress")
    old_wall = checked(PREVIOUS/"pilot/audit.json")["used_seconds"]
    preliminary = old_wall * max(r["networks"]/old_counts[(r["n"],r["family"])] for r in counts["main"]["strata"])
    config = seal({"record_kind": "final_replication_protocol", "version": 1,
                   "controller_sources": controller_sources(), "study_provenance": joint.study_provenance(),
                   "previous_final_release_sha256": parent["sha256"],
                   "manifests": {s: m["sha256"] for s,m in manifests.items()}, "counts": counts,
                   "content_overlap": {"main_vs_previous_unique_networks": len(ids["main"] & previous_ids),
                                       "pilot_vs_previous_unique_networks": len(ids["pilot"] & previous_ids),
                                       "main_vs_pilot_unique_networks": len(ids["main"] & ids["pilot"])},
                   "preliminary_forecast": {"estimate_seconds": preliminary, "twice_estimate_seconds": 2*preliminary,
                                             "scope": "planning_only_previous_pilot; fresh pilot required for admission"},
                   "analysis_spec": {"replication_unit": "base_draw", "strata": ["family", "n", "kind"],
                                     "bootstrap_resamples": 5000, "bootstrap_seed": "20260911 + sorted stratum index",
                                     "previous_results_pooled": False, "hypothesis_test": None},
                   "budgets": {"pilot_seconds": 3600, "main_seconds": 86400, "calibration_seconds": 3600}})
    root.mkdir(parents=True, exist_ok=True)
    # Freeze before any scientific worker runs. Existing mismatches are fatal.
    for s, m in manifests.items():
        freeze(root/f"{s}_manifest.json", m)
    freeze(root/"protocol.json", config)
    return config


def verify_config(root):
    config = checked(root/"protocol.json")
    require(config["controller_sources"] == controller_sources(), "controller source changed after freeze")
    require(config["study_provenance"] == joint.study_provenance(), "study source changed after freeze")
    for stage, digest in config["manifests"].items():
        require(checked(root/f"{stage}_manifest.json")["sha256"] == digest, "manifest changed after freeze")
    return config


def state(root, phase, **details):
    status = seal({"record_kind": "final_replication_controller_status", "phase": phase,
                   "pid": os.getpid(), "updated_at": datetime.now(timezone.utc).isoformat(), **details})
    atomic_write_json(root/"controller_status.json", status)
    print(json.dumps(status), flush=True)


def run_subprocess(root, name, command, timeout):
    directory = root/"controller_attempts"
    directory.mkdir(exist_ok=True)
    index = len(list(directory.glob(f"{name}_*.json")))+1
    started = time.monotonic()
    try:
        proc = subprocess.run(command, cwd=ROOT, text=True, capture_output=True, timeout=timeout)
        record = {"name": name, "command": command, "returncode": proc.returncode, "stdout": proc.stdout, "stderr": proc.stderr,
                  "elapsed_seconds": time.monotonic()-started}
    except subprocess.TimeoutExpired:
        record = {"name": name, "command": command, "returncode": None, "status": "timeout", "elapsed_seconds": time.monotonic()-started}
    atomic_write_json(directory/f"{name}_{index:03d}.json", seal(record))
    require(record["returncode"] == 0, f"{name} failed; inspect controller_attempts/{name}_{index:03d}.json")


def assert_stage(result, manifest):
    require(result["release_ready"] and not result["errors"] and result["manifest_sha256"] == manifest["sha256"], f"{manifest['stage']} did not pass")
    require(result["n_missing"] == 0 and result["n_accepted"] == result["n_expected"] == sum(1 for _ in joint.tasks(manifest)), "stage coverage mismatch")


def run(root):
    from doppel_challenge.joint_preflight import validate_preflight
    from doppel_challenge.joint_parallel import load_execution
    config = verify_config(root)
    with (root/"controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        try:
            require(previous_release()["sha256"] == config["previous_final_release_sha256"], "previous release changed")
            require(shutil.disk_usage(root).free >= 30*1024**3, "less than 30 GiB disk headroom")
            state(root, "preflight", main_networks=config["counts"]["main"]["unique_networks"])
            run_subprocess(root, "controller_tests", [sys.executable, "-m", "pytest", str(HERE/"test_run.py"), "-q", f"--junitxml={root/'controller_tests.xml'}"], 300)
            if not validate_preflight(root)["valid"]:
                run_subprocess(root, "preflight", [sys.executable, "-m", "doppel_challenge.joint_preflight", "--out-dir", str(root)], 1800)
            require(validate_preflight(root)["valid"], "fresh preflight failed")
            verify_config(root)
            state(root, "calibration")
            if not (root/"execution.json").exists():
                # An earlier failed calibration is evidence, not permission to retry it.
                require(not (root/"calibration/report.json").exists(), "failed calibration retained; inspect before retry")
                run_subprocess(root, "calibration", [sys.executable, str(HERE/"run.py"), "--action", "calibrate", "--out-dir", str(root)], 3600)
            pilot, main = (checked(root/f"{s}_manifest.json") for s in ("pilot", "main"))
            execution = load_execution(root, pilot)
            state(root, "pilot", workers=execution["workers"], expected=config["counts"]["pilot"]["unique_networks"])
            pilot_audit = joint.run_stage(root, pilot, execution=execution)
            assert_stage(pilot_audit, pilot)
            verify_config(root)
            state(root, "forecast")
            forecast = joint.forecast_main(root, pilot, main)
            atomic_write_json(root/"forecast.json", seal(forecast))
            require(forecast["admitted"], f"main not admitted: {forecast['reason']}")
            require(validate_preflight(root)["valid"], "preflight became stale")
            state(root, "main", workers=execution["workers"], expected=config["counts"]["main"]["unique_networks"],
                  forecast_seconds=forecast["estimate_seconds"], conservative_seconds=forecast["conservative_seconds"])
            main_audit = joint.run_stage(root, main, execution=execution)
            assert_stage(main_audit, main)
            verify_config(root)
            summary = checked(root/"main/summary.json")
            require(summary["release_ready"] and summary["manifest_sha256"] == main["sha256"], "main summary failed")
            require(len(summary["catalogues"]) == config["counts"]["main"]["catalogue_definitions"], "catalogue summary coverage")
            state(root, "computation_complete_awaiting_analysis", main_networks=main_audit["n_accepted"],
                  main_catalogues=len(summary["catalogues"]), main_audit_sha256=main_audit["sha256"],
                  main_summary_sha256=summary["sha256"], scientific_analysis_release_ready=False)
        except Exception as exc:
            state(root, "stopped", error=f"{type(exc).__name__}: {exc}", scientific_analysis_release_ready=False)
            raise


def launch(root):
    config = verify_config(root)
    # Probe the controller lock without changing any running process.
    with (root/"controller.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    env = dict(os.environ, PYTHONPATH=str(ROOT/"doppel-challenge/src"))
    for name in ("OMP_NUM_THREADS", "OPENBLAS_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    with (root/"controller.log").open("a") as log:
        proc = subprocess.Popen([sys.executable, str(HERE/"run.py"), "--action", "run", "--out-dir", str(root)],
                                cwd=ROOT, env=env, stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                                start_new_session=True)
    atomic_write_json(root/f"launch_{proc.pid}.json", seal({"record_kind": "final_replication_launch", "pid": proc.pid,
                      "protocol_sha256": config["sha256"], "started_at": datetime.now(timezone.utc).isoformat()}))
    print(json.dumps({"pid": proc.pid, "status_file": str(root/"controller_status.json"), "log": str(root/"controller.log")}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--action", required=True, choices=("prepare", "launch", "run", "status", "calibrate"))
    parser.add_argument("--out-dir", type=Path, default=OUT)
    args = parser.parse_args()
    root = args.out_dir.resolve()
    assert_namespace(root)
    if args.action == "prepare":
        config = prepare(root)
        print(json.dumps({k: config[k] for k in ("counts", "content_overlap", "preliminary_forecast")}, indent=2))
    elif args.action == "launch":
        launch(root)
    elif args.action == "run":
        run(root)
    elif args.action == "status":
        print(json.dumps(checked(root/"controller_status.json"), indent=2))
    else:
        from doppel_challenge.joint_parallel import calibrate
        verify_config(root)
        report = calibrate(root, checked(root/"pilot_manifest.json"))
        require(report["passed"], "calibration failed")


if __name__ == "__main__":
    main()
