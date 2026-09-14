"""Frozen, resumable joint validation of one-step programs and long-run dynamics.

This study has its own versioned namespace. Legacy degree-three studies and
their denominators are never modified. The input state table is implicit in
the program; exhaustive materialization belongs only to validation and BDM.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import fcntl
import hashlib
import json
import os
from pathlib import Path
import random
import resource
import subprocess
import sys
import time

from .adapters import Network
from .execution import source_provenance, run_with_timeout, CaseTimeout
from .io import atomic_write_json, read_json
from .perturbations import ball, changed_edges, is_admissible_perturbation, perturbation_id
from .pilot_runner import make_network
from .program_benchmark import _worker as program_worker, mixed_cases, wolfram_reference
from .records import seal, scientific_digest
from .repertoire import compute_repertoire
from .repertoire_program import deserialize_program, iter_output_rows, compile_repertoire_program, serialize_program
from .stats import constrained_optimum, expected_loss, kl, total_variation, jensen_shannon, kl_ball_upper_bound
from .validation import validate_repertoire, validate_codec, validate_ncd

ROOT = Path(__file__).resolve().parents[3]
FAMILIES = ("ring", "sparse_random", "modular", "hub")
POLICY = dict(forbid_zero_indegree_nodes=True, max_indegree=5, allow_self_loops=False)
KINDS = ("EDGE_ADD", "EDGE_REMOVE")
BUDGETS = (0.0, 0.1, 0.25, 0.5)


def content_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()


def network_payload(case):
    return {"network_size": case["network_size"], "cm": case["cm"], "dyn": case["dyn"],
            "params": case.get("params") or [{} for _ in case["dyn"]]}


def network_hash(case):
    return content_hash(network_payload(case))


def study_provenance():
    """Bind Python, Wolfram owners, tests, dependencies and notebook *sources*."""
    files = {}
    for pattern in ("doppel-challenge/src/**/*.py", "doppel-challenge/tests/**/*.py",
                    "src/Packages/**/*.m", "tests/analysis/test_description*.py",
                    "doppel-challenge/pyproject.toml", "doppel-challenge/doc/*.md"):
        for path in sorted(ROOT.glob(pattern)):
            files[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    notebook = ROOT / "doppel-challenge/notebooks/01_exact_n8_walkthrough.ipynb"
    cells = json.loads(notebook.read_text())["cells"]
    files[str(notebook.relative_to(ROOT))] = content_hash([(c["cell_type"], c["source"]) for c in cells])
    return {**source_provenance(), "study_source_sha256": content_hash(files), "source_files": files}


def bounded_network(family, n, seed, max_indegree=5):
    """Construct a seeded bounded-indegree sample; persist original and edits.

    Oversized input rows are uniformly subsampled with a local SHA-seeded RNG.
    This is a declared construction, not rejection sampling or a perturbation.
    """
    original, gates = make_network(family, n, seed=seed)
    matrix = [row[:] for row in original]
    for target, row in enumerate(matrix):
        sources = [s for s, bit in enumerate(row) if bit and s != target]
        if len(sources) > max_indegree:
            rng = random.Random(int(content_hash(["bounded_indegree_v1", family, n, seed, target]), 16))
            sources = sorted(rng.sample(sources, max_indegree))
        matrix[target] = [int(s in sources) for s in range(n)]
    if not is_admissible_perturbation(matrix, gates=gates, **{**POLICY, "max_indegree": max_indegree}):
        raise ValueError("constructed base violates the declared policy")
    case = {"network_size": n, "cm": matrix, "dyn": gates, "params": [{} for _ in gates]}
    return case, {"rule": "bounded_indegree_v1", "generator_seed": seed,
                  "original_cm": original, "construction_changes": changed_edges(original, matrix)}


def stress_cases():
    # Keep gate stress (including self-loops and high arities) outside the sample.
    cases = mixed_cases()
    n = 8
    specs = [("XOR", {})]
    specs += [("MAJORITY", {"tiePolicy": p}) for p in ("strict", "atOrAbove")]
    specs += [("KOFN", {"k": k, "strict": strict}) for k in (-1, 0, n, n+1) for strict in (False, True)]
    specs += [("CANALISING", {"canalisingIndex": i, "canalisingValue": v, "canalisedOutput": o})
              for i in (0, n-1) for v in (0, 1) for o in (0, 1)]
    for i, (gate, params) in enumerate(specs):
        cases.append({"label": f"stress_{gate}_{i}", "network_size": n,
                      "cm": [[1]*n for _ in range(n)], "dyn": [gate]*n, "params": [params.copy() for _ in range(n)]})
    return cases


def exclusion_reasons(matrix, gates, policy):
    reasons = []
    if any(matrix[i][i] for i in range(len(matrix))):
        reasons.append("self_loop")
    if any(sum(row) == 0 for row in matrix):
        reasons.append("empty_input")
    if any(sum(row) > policy["max_indegree"] for row in matrix):
        reasons.append("indegree_limit")
    if not reasons and not is_admissible_perturbation(matrix, gates=gates, **policy):
        reasons.append("gate_arity")
    return reasons


def make_manifest(stage, *, sizes=(8, 10, 12), families=FAMILIES, seeds=None, include_stress=None):
    if stage not in ("pilot", "main"):
        raise ValueError("stage must be pilot or main")
    seeds = tuple(range(100, 103) if stage == "pilot" else range(20)) if seeds is None else tuple(seeds)
    bases = []
    # Interleave sizes so early timing records cover the full range.
    for seed in seeds:
        for family in families:
            for n in sizes:
                case, construction = bounded_network(family, n, seed)
                base = {"base_id": f"{family}_n{n}_s{seed}", "family": family, "seed": seed,
                        "network": case, "network_sha256": network_hash(case), "construction": construction,
                        "catalogues": {}}
                for kind in KINDS:
                    entries = []
                    for matrix in ball(case["cm"], 1, kind):
                        modified = {**case, "cm": matrix}
                        reasons = exclusion_reasons(matrix, case["dyn"], POLICY)
                        entries.append({"perturbation_id": perturbation_id(case["cm"], matrix, kind),
                                        "changed_edges": changed_edges(case["cm"], matrix),
                                        "network_sha256": network_hash(modified),
                                        "admissible": not reasons, "exclusion_reasons": reasons})
                    base["catalogues"][kind] = entries
                bases.append(base)
    include_stress = stage == "pilot" if include_stress is None else include_stress
    return seal({"record_kind": "joint_study_manifest", "joint_schema_version": 1, "stage": stage,
                 "provenance": study_provenance(), "policy": POLICY, "sizes": list(sizes),
                 "families": list(families), "seeds": list(seeds), "k": 1, "bases": bases,
                 "stress_cases": stress_cases() if include_stress else [],
                 "limits": {"stage_seconds": 3600 if stage == "pilot" else 86400,
                            "worker_seconds": 300, "max_nodes": 1_000_000},
                 "losses": ["L_SINGLE_TARGET", "L_LINEAR"], "KL_budgets": list(BUDGETS),
                 "primary_C": 0.25, "replication_unit": "base_network",
                 "target_selection": "support_sorted_index_seed_mod_cardinality"})


def frozen_manifest(root, stage, **kwargs):
    path = Path(root) / f"{stage}_manifest.json"
    candidate = make_manifest(stage, **kwargs)
    if path.exists():
        old = read_json(path)
        if old != candidate:
            raise ValueError("frozen manifest/configuration/source mismatch; use a new run directory")
        return old
    atomic_write_json(path, candidate)
    return candidate


def tasks(manifest):
    """Unique computational units; catalogue identities remain separately listed."""
    seen = set()
    for case in manifest["stress_cases"]:
        key = network_hash(case)
        if key not in seen:
            seen.add(key)
            yield key, network_payload(case), "stress"
    for base in manifest["bases"]:
        for entries in base["catalogues"].values():
            for entry in entries:
                if not entry["admissible"]:
                    continue
                key = entry["network_sha256"]
                if key in seen:
                    continue
                matrix = [row[:] for row in base["network"]["cm"]]
                for edge in entry["changed_edges"]:
                    matrix[edge["target"]][edge["source"]] = int(edge["operation"] == "add")
                case = {**base["network"], "cm": matrix}
                if network_hash(case) != key:
                    raise ValueError("manifest network/edge mismatch")
                seen.add(key)
                yield key, case, base["family"]


def joint_worker(case, timeout=300, max_nodes=1_000_000):
    started = time.perf_counter()
    compression = program_worker(case, timeout, max_nodes)
    if compression["status"] != "completed":
        return {"status": compression["status"], "compression": compression, "accepted_validation": False}
    net = Network(case["network_size"], case["cm"], case["dyn"], case["params"])
    t = time.perf_counter()
    rep = compute_repertoire(net)
    check = validate_repertoire(net, rep)
    check["codec"] = validate_codec(rep)
    restored = deserialize_program(bytes.fromhex(compression["payload_hex"]), n=net.n)
    decoded = [sum(bit << i for i, bit in enumerate(row)) for row in iter_output_rows(restored)]
    check["program_transition_map_equal"] = decoded == rep["transition_map"]
    check["division_invariant"] = serialize_program(compile_repertoire_program(net, division_size=net.n)) == bytes.fromhex(compression["payload_hex"])
    accepted = (check["valid"] and check["codec"]["valid"] and check["program_transition_map_equal"]
                and check["division_invariant"] and compression["bdm_original_output"]["status"] == "completed")
    return {"status": "completed" if accepted else "joint_validation_failure", "compression": compression,
            "dynamics": {"repertoire": rep, "validation": check, "accepted_validation": check["valid"] and check["codec"]["valid"]},
            "accepted_validation": accepted, "dynamics_seconds": time.perf_counter()-t,
            "peak_worker_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss * (1 if sys.platform == "darwin" else 1024)),
            "elapsed_seconds": time.perf_counter()-started}


def run_worker(case, timeout, max_nodes):
    env = dict(os.environ)
    for name in ("OPENBLAS_NUM_THREADS", "OMP_NUM_THREADS", "MKL_NUM_THREADS", "VECLIB_MAXIMUM_THREADS"):
        env[name] = "1"
    try:
        proc = subprocess.run([sys.executable, "-m", "doppel_challenge.joint_study", "--worker"],
                              input=json.dumps({"case": case, "timeout": timeout, "max_nodes": max_nodes}),
                              text=True, capture_output=True, timeout=timeout, cwd=ROOT, env=env)
    except subprocess.TimeoutExpired:
        return {"status": "timeout", "accepted_validation": False}
    except OSError as exc:
        return {"status": "process_failure", "accepted_validation": False, "failure": str(exc)}
    if proc.returncode:
        return {"status": "process_failure", "accepted_validation": False,
                "exit_code": proc.returncode, "failure": proc.stderr[-4000:]}
    try:
        result = json.loads(proc.stdout)
        if not isinstance(result, dict) or "status" not in result:
            raise ValueError("missing worker status")
        return result
    except (TypeError, ValueError) as exc:
        return {"status": "malformed_payload", "accepted_validation": False, "failure": str(exc)}


def validate_joint_record(record, case, manifest, *, replay=False):
    """Reject forged success flags; reconstruct the integration boundary again."""
    from .repertoire_program import program_metadata
    errors = []
    if record.get("manifest_sha256") != manifest["sha256"]:
        errors.append("manifest_mismatch")
    if record.get("network_sha256") != network_hash(case) or record.get("network") != network_payload(case):
        errors.append("network_mismatch")
    if record.get("status") != "completed" or not record.get("accepted_validation"):
        errors.append("not_accepted")
    try:
        c, d = record["compression"], record["dynamics"]
        p = deserialize_program(bytes.fromhex(c["payload_hex"]), n=case["network_size"])
        meta = program_metadata(p)
        for key in ("raw_bit_length", "program_bit_length", "canonical_program_sha256"):
            if c[key] != meta[key]:
                errors.append("program_metadata_mismatch")
        rows = list(iter_output_rows(p))
        digest = hashlib.sha256(bytes(bit for row in rows for bit in row)).hexdigest()
        if c["status"] != "completed" or not c["accepted_validation"]:
            errors.append("compression_not_accepted")
        if (c["checked_output_bits"] != case["network_size"] * 2**case["network_size"]
                or c["validation_scope"] != "exhaustive_all_output_bits"
                or digest != c["checked_output_sha256"]):
            errors.append("incomplete_output_verification")
        if [sum(bit << i for i, bit in enumerate(row)) for row in rows] != d["repertoire"]["transition_map"]:
            errors.append("transition_mismatch")
        ref = record["wolfram_reference"]
        if ref.get("status") != "completed" or ref.get("output_sha256") != digest:
            errors.append("wolfram_mismatch")
        bdm = c["bdm_original_output"]
        if (bdm["status"] != "completed" or bdm["value"] is None
                or bdm["provenance"]["original_output_sha256"] != digest
                or bdm["provenance"]["original_shape"] != [2**p.n, p.n]
                or bdm["provenance"]["version"] != "0.1.0"):
            errors.append("bdm_mismatch")
        v = d["validation"]
        if not d["accepted_validation"] or not all(v.get(k) is True for k in
                ("valid", "transition_map_equal", "attractor_cycles_equal", "basin_sizes_equal",
                 "phase_weights_equal", "exact_probabilities_equal", "program_transition_map_equal", "division_invariant")):
            errors.append("dynamics_not_accepted")
        rep = d["repertoire"]
        if sum(rep["counts"]) != rep["probability_denominator"] or sum(rep["basin_sizes"]) != 2**p.n:
            errors.append("probability_or_basin_coverage")
        if replay:
            net = Network(p.n, case["cm"], case["dyn"], case["params"])
            if not validate_repertoire(net, rep)["valid"]:
                errors.append("independent_replay_mismatch")
    except (KeyError, ValueError, TypeError, IndexError) as exc:
        errors.append(f"malformed_joint_record:{exc}")
    return {"valid": not errors, "errors": errors}


def audit_stage(root, manifest, *, replay=False):
    root = Path(root) / manifest["stage"]
    expected = list(tasks(manifest))
    errors, accepted, missing = [], 0, 0
    for key, case, _ in expected:
        path = root / "networks" / f"{key}.json"
        if not path.exists():
            missing += 1
            continue
        try:
            row = read_json(path)
            check = validate_joint_record(row, case, manifest, replay=replay)
            if check["valid"]:
                accepted += 1
            else:
                errors.append({"network_sha256": key, "errors": check["errors"]})
        except (OSError, ValueError) as exc:
            errors.append({"network_sha256": key, "errors": [str(exc)]})
    actual = {p.stem for p in (root / "networks").glob("*.json")}
    unexpected = actual - {key for key, _, _ in expected}
    if unexpected:
        errors.append({"unexpected_network_ids": sorted(unexpected)})
    for base in manifest["bases"]:
        for kind, entries in base["catalogues"].items():
            ids = [entry["perturbation_id"] for entry in entries]
            matrices = ball(base["network"]["cm"], 1, kind)
            if len(ids) != len(set(ids)) or ids != [perturbation_id(base["network"]["cm"], m, kind) for m in matrices]:
                errors.append({"catalogue_ids_mismatch": [base["base_id"], kind]})
            for entry, matrix in zip(entries, matrices):
                reasons = exclusion_reasons(matrix, base["network"]["dyn"], manifest["policy"])
                if entry["exclusion_reasons"] != reasons or entry["admissible"] != (not reasons):
                    errors.append({"exclusion_mismatch": [base["base_id"], kind, entry["perturbation_id"]]})
    return seal({"record_kind": "joint_study_audit", "manifest_sha256": manifest["sha256"],
                 "stage": manifest["stage"], "n_expected": len(expected), "n_accepted": accepted,
                 "n_missing": missing, "errors": errors,
                 "release_ready": bool(expected) and accepted == len(expected) and not errors})


def run_stage(root, manifest, *, execution=None):
    """One live writer per stage; concurrent resume cannot race checkpoints."""
    stage_root = Path(root) / manifest["stage"]
    stage_root.mkdir(parents=True, exist_ok=True)
    with (stage_root / "run.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError("another runner owns this stage") from exc
        if execution is not None:
            from .joint_parallel import run_parallel_stage
            return run_parallel_stage(root, manifest, execution)
        return _run_stage(root, manifest)


def _run_stage(root, manifest):
    """Sequential bounded workers, atomic records, conservative crash accounting."""
    root = Path(root)
    if study_provenance() != manifest["provenance"]:
        raise ValueError("source mismatch")
    stage_root = root / manifest["stage"]
    state_path = stage_root / "progress.json"
    state = read_json(state_path) if state_path.exists() else {"used_seconds": 0.0, "manifest_sha256": manifest["sha256"]}
    if state["manifest_sha256"] != manifest["sha256"]:
        raise ValueError("checkpoint configuration mismatch")
    limit = manifest["limits"]["stage_seconds"]
    session_started = time.perf_counter()
    session_used = state["used_seconds"]
    jobs = list(tasks(manifest))
    stop_reason = "completed"
    for index, (key, case, family) in enumerate(jobs):
        state["used_seconds"] = session_used + time.perf_counter()-session_started
        if state["used_seconds"] >= limit:
            stop_reason = "stage_budget_exhausted"
            break
        path = stage_root / "networks" / f"{key}.json"
        if path.exists():
            saved = read_json(path)
            if not validate_joint_record(saved, case, manifest)["valid"]:
                stop_reason = "invalid_or_failed_checkpoint"
                break
            continue
        remaining = limit-state["used_seconds"]
        if remaining <= 0:
            stop_reason = "stage_budget_exhausted"
            break
        # Reserve the full two-owner allowance before launch. On process death
        # the reservation remains charged, preventing a resume from resetting it.
        allowance = min(2*manifest["limits"]["worker_seconds"], remaining)
        previous_used = state["used_seconds"]
        state.update(used_seconds=previous_used+allowance, active_network=key)
        atomic_write_json(state_path, seal(state))
        started = time.perf_counter()
        result = run_worker(case, min(allowance, manifest["limits"]["worker_seconds"]), manifest["limits"]["max_nodes"])
        remaining_case = allowance-(time.perf_counter()-started)
        if result.get("status") == "completed" and remaining_case > 0:
            reference = wolfram_reference(case, timeout_seconds=min(remaining_case, manifest["limits"]["worker_seconds"]))
            result["wolfram_reference"] = reference
            if reference.get("status") != "completed":
                result.update(status="reference_owner_failure", accepted_validation=False)
            elif reference.get("output_sha256") != result.get("compression", {}).get("checked_output_sha256"):
                result.update(status="reconstruction_mismatch", accepted_validation=False)
        elif result.get("status") == "completed":
            result.update(status="stage_budget_exhausted", accepted_validation=False)
        result.update(record_kind="joint_study_network", joint_schema_version=1, manifest_sha256=manifest["sha256"],
                      network_sha256=key, network=network_payload(case), family=family,
                      elapsed_seconds=time.perf_counter()-started)
        if result.get("status") == "completed":
            check = validate_joint_record(result, case, manifest)
            if not check["valid"]:
                result.update(status="malformed_or_mismatched_payload", accepted_validation=False, validation_errors=check["errors"])
        atomic_write_json(path, seal(result))
        state.update(used_seconds=previous_used+(time.perf_counter()-started), active_network=None,
                     completed_this_pass=index+1, total=len(jobs), last_status=result["status"])
        atomic_write_json(state_path, seal(state))
        print(json.dumps({"stage": manifest["stage"], "case": index+1, "total": len(jobs),
                          "n": case["network_size"], "family": family, "status": result["status"],
                          "used_seconds": round(state["used_seconds"], 2)}), flush=True)
        if not result.get("accepted_validation"):
            stop_reason = "case_failure"
            break
    remaining = limit-(session_used+time.perf_counter()-session_started)
    try:
        if remaining <= 0:
            raise CaseTimeout("stage deadline reached")
        def finalize():
            result = audit_stage(root, manifest)
            if result["release_ready"]:
                summarize_stage(root, manifest)
            return result
        audit = run_with_timeout(finalize, remaining)
    except CaseTimeout:
        stop_reason = "stage_budget_exhausted"
        audit = {"record_kind": "joint_study_audit", "manifest_sha256": manifest["sha256"],
                 "stage": manifest["stage"], "n_expected": len(jobs), "release_ready": False,
                 "errors": ["stage_budget_exhausted_before_complete_release_audit"]}
    except (ValueError, KeyError) as exc:
        stop_reason = "finalization_failure"
        audit = {"record_kind": "joint_study_audit", "manifest_sha256": manifest["sha256"],
                 "stage": manifest["stage"], "n_expected": len(jobs), "release_ready": False,
                 "errors": [f"summary_or_audit_failure:{exc}"]}
    state["used_seconds"] = session_used+time.perf_counter()-session_started
    atomic_write_json(state_path, seal(state))
    audit["stop_reason"] = stop_reason
    audit["used_seconds"] = state["used_seconds"]
    atomic_write_json(stage_root / "audit.json", seal(audit))
    return audit


def summarize_stage(root, manifest):
    """Complete catalogues only; aggregate perturbations *within* each base."""
    root = Path(root)
    audit = audit_stage(root, manifest)
    if not audit["release_ready"]:
        raise ValueError("cannot summarize incomplete catalogues as an exact experiment")
    stage_root = root / manifest["stage"]
    groups = defaultdict(list)
    summaries = []
    for base in manifest["bases"]:
        read = lambda key: read_json(stage_root / "networks" / f"{key}.json")
        baseline_row = read(base["network_sha256"])
        baseline = baseline_row["dynamics"]["repertoire"]
        target = baseline["support"][base["seed"] % len(baseline["support"])]
        for kind, entries in base["catalogues"].items():
            rows, effects = [], []
            for entry in entries:
                if not entry["admissible"]:
                    continue
                record = read(entry["network_sha256"])
                rep = record["dynamics"]["repertoire"]
                if not validate_ncd(rep, baseline)["valid"]:
                    raise ValueError("distribution codec NCD invariant failure")
                identity = not entry["changed_edges"]
                row = {"perturbation_id": entry["perturbation_id"], "graph_distance": int(not identity),
                       "repertoire": rep}
                rows.append(row)
                if not identity:
                    metrics = kl(rep, baseline)
                    effects.append({"perturbation_id": entry["perturbation_id"],
                                    "network_sha256": entry["network_sha256"],
                                    "program_bits": record["compression"]["program_bit_length"],
                                    "raw_bits": record["compression"]["raw_bit_length"],
                                    "bdm": record["compression"]["bdm_original_output"]["value"],
                                    "delta_program_bits": record["compression"]["program_bit_length"]-baseline_row["compression"]["program_bit_length"],
                                    "delta_bdm": record["compression"]["bdm_original_output"]["value"]-baseline_row["compression"]["bdm_original_output"]["value"],
                                    "total_variation": total_variation(rep, baseline),
                                    "jensen_shannon": jensen_shannon(rep, baseline),
                                    "infinite_kl": metrics["infinite_kl"],
                                    "D_KL_nats": metrics["D_KL_nats"],
                                    "loss": expected_loss(rep, "L_SINGLE_TARGET", {"targets": [target]})})
            sensitivity = {}
            for loss, params in (("L_SINGLE_TARGET", {"targets": [target]}),
                                 ("L_LINEAR", {"weights": [1/base["network"]["network_size"]]*base["network"]["network_size"]})):
                sensitivity[loss] = []
                for budget in BUDGETS:
                    frontier = constrained_optimum(rows, baseline, budget, loss_id=loss, loss_params=params)
                    upper = kl_ball_upper_bound(baseline, budget, loss, params)["upper_bound"]
                    if frontier["V_k_C"] is not None and upper is not None and frontier["V_k_C"] > upper+1e-9:
                        raise ValueError("catalogue optimum exceeds KL relaxation")
                    sensitivity[loss].append({**frontier, "upper_bound": upper})
            descriptive = {name: sum(float(e[name]) for e in effects)/len(effects) if effects else None
                           for name in ("delta_program_bits", "delta_bdm", "total_variation", "jensen_shannon", "infinite_kl")}
            summary = {"base_id": base["base_id"], "family": base["family"], "n": base["network"]["network_size"],
                       "kind": kind, "n_admissible": len(rows), "n_excluded": len(entries)-len(rows),
                       "n_nonidentity": len(effects), "target_state": target, "descriptive": descriptive,
                       "sensitivity": sensitivity, "effects": effects}
            summaries.append(summary)
            groups[(base["family"], base["network"]["network_size"], kind)].append(descriptive)
    grouped = [{"family": f, "n": n, "kind": k, "n_bases": len(values),
                "equal_base_weight_means": {name: sum(v[name] for v in values if v[name] is not None)/sum(v[name] is not None for v in values)
                                             if any(v[name] is not None for v in values) else None for name in values[0]}}
               for (f, n, k), values in sorted(groups.items())]
    result = seal({"record_kind": "joint_study_summary", "manifest_sha256": manifest["sha256"],
                   "replication_unit": "base_network", "inference": "descriptive_only",
                   "release_ready": True, "catalogues": summaries, "groups": grouped})
    atomic_write_json(stage_root / "summary.json", result)
    return result


def forecast_main(root, pilot, main):
    try:
        final = read_json(Path(root) / "pilot/audit.json")
        summary = read_json(Path(root) / "pilot/summary.json")
        if (not final["release_ready"] or final["manifest_sha256"] != pilot["sha256"]
                or not summary["release_ready"] or summary["manifest_sha256"] != pilot["sha256"]):
            return {"admitted": False, "reason": "pilot_release_not_ready"}
    except (OSError, ValueError, KeyError):
        return {"admitted": False, "reason": "pilot_release_unavailable"}
    audit = audit_stage(root, pilot)
    if not audit["release_ready"]:
        return {"admitted": False, "reason": "pilot_not_complete_and_valid"}
    costs = defaultdict(list)
    for key, case, family in tasks(pilot):
        if family != "stress":
            row = read_json(Path(root) / "pilot/networks" / f"{key}.json")
            costs[(case["network_size"], family)].append(row["elapsed_seconds"])
    counts = defaultdict(int)
    for _, case, family in tasks(main):
        counts[(case["network_size"], family)] += 1
    if set(counts)-set(costs):
        return {"admitted": False, "reason": "unmeasured_size_family"}
    strata = [{"n": n, "family": f, "cases": count, "pilot_mean_seconds": sum(costs[n, f])/len(costs[n, f])}
              for (n, f), count in sorted(counts.items())]
    estimate = sum(s["cases"]*s["pilot_mean_seconds"] for s in strata)
    # Under the parallel runner the observed stage wall time includes batching,
    # queueing, audit and summary. Scale by the largest main/pilot stratum ratio,
    # deliberately retaining pilot stress and startup overhead in the estimate.
    method = "serial_stratum_mean"
    if final.get("execution_sha256"):
        ratio = max(count/len(costs[stratum]) for stratum, count in counts.items())
        estimate = final["used_seconds"] * ratio
        method = "parallel_observed_wall_time_times_maximum_stratum_count_ratio"
    return {"admitted": 2*estimate <= main["limits"]["stage_seconds"], "strata": strata,
            "estimate_seconds": estimate, "forecast_method": method, "safety_factor": 2, "conservative_seconds": 2*estimate,
            "budget_seconds": main["limits"]["stage_seconds"],
            "reason": "within_budget" if 2*estimate <= main["limits"]["stage_seconds"] else "forecast_exceeds_budget"}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out-dir", type=Path, default=ROOT / "doppel-challenge/results/joint_degree5_v2")
    parser.add_argument("--action", choices=("prepare", "calibrate", "pilot", "main", "audit", "forecast"), default="prepare")
    parser.add_argument("--worker", action="store_true")
    args = parser.parse_args()
    if args.worker:
        try:
            request = json.load(sys.stdin)
            result = joint_worker(request["case"], request["timeout"], request["max_nodes"])
        except Exception as exc:
            from .repertoire_program import ResourceLimitError
            status = ("resource_exhaustion" if isinstance(exc, ResourceLimitError) else
                      "timeout" if isinstance(exc, TimeoutError) else
                      "invalid_input" if isinstance(exc, ValueError) else "worker_failure")
            result = {"status": status, "accepted_validation": False, "failure": f"{type(exc).__name__}: {exc}"}
        print(json.dumps(result, allow_nan=False))
        return
    pilot = frozen_manifest(args.out_dir, "pilot")
    main_manifest = frozen_manifest(args.out_dir, "main")
    if args.action == "prepare":
        result = {"pilot_unique_networks": sum(1 for _ in tasks(pilot)),
                  "main_unique_networks": sum(1 for _ in tasks(main_manifest))}
    elif args.action == "audit":
        result = {m["stage"]: audit_stage(args.out_dir, m) for m in (pilot, main_manifest)}
    elif args.action == "forecast":
        result = forecast_main(args.out_dir, pilot, main_manifest)
        atomic_write_json(args.out_dir / "forecast.json", seal(result))
    else:
        from .joint_preflight import validate_preflight
        preflight = validate_preflight(args.out_dir)
        if not preflight["valid"]:
            raise ValueError(f"preflight blocked: {preflight}")
        from .joint_parallel import calibrate, load_execution
        if args.action == "calibrate":
            result = calibrate(args.out_dir, pilot)
            print(json.dumps({k: result[k] for k in ("passed", "selected_workers", "errors")}, indent=2))
            return
        execution = load_execution(args.out_dir, pilot)
        if args.action == "main":
            forecast = forecast_main(args.out_dir, pilot, main_manifest)
            atomic_write_json(args.out_dir / "forecast.json", seal(forecast))
            if not forecast["admitted"]:
                print(json.dumps(forecast, indent=2))
                return
        result = run_stage(args.out_dir, pilot if args.action == "pilot" else main_manifest, execution=execution)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
