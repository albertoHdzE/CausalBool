"""One durable execution path for exact small-N challenge studies."""
from __future__ import annotations

import hashlib
import json
import os
import platform
import signal
import sys
import time
from pathlib import Path
from typing import Any, Callable

from .adapters import Network
from .compression import (encode_repertoire, native_mechanism_encoding, ncd,
                          simple_baseline_lengths)
from .io import atomic_write_json, ensure_dir, read_json, read_jsonl
from .perturbations import (admissible_ball, changed_edges, graph_distance,
                            indegrees, is_admissible_perturbation, perturbation_id)
from .records import make_envelope, seal, scientific_digest
from .repertoire import compute_repertoire
from .stats import (constrained_optimum, expected_loss, jaccard,
                    jensen_shannon, kl, kl_ball_upper_bound, total_variation)
from .validation import validate_codec, validate_ncd, validate_repertoire


class CaseTimeout(TimeoutError):
    """A perturbation exceeded its declared wall-clock budget."""


def run_with_timeout(function: Callable[[], Any], timeout_seconds: float | None) -> Any:
    """Run a case with a POSIX alarm when a timeout is declared."""
    if timeout_seconds is None:
        return function()
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive or None")
    previous = signal.getsignal(signal.SIGALRM)
    def alarm_handler(signum: int, frame: Any) -> None:
        raise CaseTimeout(f"case exceeded {timeout_seconds} seconds")
    signal.signal(signal.SIGALRM, alarm_handler)
    signal.setitimer(signal.ITIMER_REAL, timeout_seconds)
    try:
        return function()
    finally:
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, previous)


def source_provenance() -> dict[str, Any]:
    """Capture reproducibility metadata without embedding machine paths."""
    root = Path(__file__).resolve().parents[2]
    digest = hashlib.sha256()
    files = sorted((root / "src").rglob("*.py"))
    for path in files:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_bytes())
    return {"python": sys.version, "platform": platform.platform(),
            "source_tree_sha256": digest.hexdigest(), "exact_state_space": True}


def _json_append(path: Path, record: dict[str, Any]) -> None:
    ensure_dir(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, sort_keys=True, separators=(",", ":"), allow_nan=False))
        handle.write("\n")
        handle.flush()
        os.fsync(handle.fileno())


def _metric_value(metric: dict[str, Any], key: str) -> float | None:
    value = metric.get(key)
    return value if isinstance(value, (int, float)) and value != float("inf") else None


def _base_record(A: list[list[int]], gates: list[str], params: list[dict], config_id: str) -> tuple[dict[str, Any], dict[str, Any]]:
    rep = compute_repertoire(Network(len(A), A, gates, params))
    validation = validate_repertoire(Network(len(A), A, gates, params), rep)
    if not validation["valid"]:
        raise ValueError(f"base network failed exact validation: {validation['errors']}")
    record = make_envelope("base_network", config_id=config_id, sweep_id=None)
    record.update({"A": A, "gates": gates, "params": params, "N": len(A),
                   "observable": "basin_weighted_attractor_repertoire",
                   "approximation": "none_exact_full_state_space",
                   "estimator_parameters": {}, "uncertainty": {"method": "exact"},
                   "process_status": "normal_exit", "accepted_validation": True,
                   "provenance": source_provenance(),
                   "repertoire": rep, "validation": validation,
                   "compressed": encode_repertoire(rep, include_schema=False),
                   "native_mechanism": {"bits": len(native_mechanism_encoding(A, gates, params)),
                                        "encoding": "canonical_mechanism_json_v1"},
                   "baseline_lengths": simple_baseline_lengths(rep)})
    return seal(record), rep


def _case_record(A: list[list[int]], A0: list[list[int]], gates: list[str], params: list[dict],
                 rep0: dict[str, Any], config_id: str, kind: str, elapsed: float,
                 *, target_state: int | None = None, process_status: str = "normal_exit",
                 failure: str | None = None) -> dict[str, Any]:
    started = time.perf_counter()
    rep = compute_repertoire(Network(len(A), A, gates, params))
    validation = validate_repertoire(Network(len(A), A, gates, params), rep)
    metrics = kl(rep, rep0)
    loss_params = {"targets": [rep0["support"][0] if target_state is None else target_state]}
    row = make_envelope("catalogue_row", config_id=config_id, sweep_id=None)
    dkl = _metric_value(metrics, "D_KL_nats")
    row.update({"A": A, "gates": gates, "params": params, "N": len(A),
                "observable": "basin_weighted_attractor_repertoire",
                "approximation": "none_exact_full_state_space",
                "estimator_parameters": {}, "uncertainty": {"method": "exact"},
                "provenance": source_provenance(),
                "perturbation_kind": kind, "perturbation_id": perturbation_id(A0, A, kind),
                "is_identity": graph_distance(A0, A) == 0,
                "changed_edges": changed_edges(A0, A), "graph_distance": graph_distance(A0, A),
                "indegrees": indegrees(A), "repertoire": rep,
                "loss_id": "L_SINGLE_TARGET", "loss_params": loss_params,
                "ell": expected_loss(rep, "L_SINGLE_TARGET", loss_params),
                "D_KL_nats": dkl, "infinite_kl": metrics["infinite_kl"],
                "divergence_status": metrics["divergence_status"],
                "p_mass_outside_q_support": metrics["p_mass_outside_q_support"],
                "conditional_D_KL_nats": metrics["conditional_D_KL_nats"],
                "support": jaccard(rep, rep0), "total_variation": total_variation(rep, rep0),
                "jensen_shannon": jensen_shannon(rep, rep0), "compression": ncd(rep, rep0),
                "native_mechanism": {"bits": len(native_mechanism_encoding(A, gates, params)),
                                     "encoding": "canonical_mechanism_json_v1"},
                "validation": {**validation, "codec": validate_codec(rep), "ncd": validate_ncd(rep, rep0)},
                "process_status": process_status,
                "accepted_validation": process_status == "normal_exit" and validation["valid"] and
                validate_codec(rep)["valid"] and validate_ncd(rep, rep0)["valid"],
                "failure": failure, "elapsed_seconds": elapsed + (time.perf_counter() - started)})
    return seal(row)


def run_catalogue(A0: list[list[int]], gates: list[str], *, out_dir: str | Path,
                  kind: str = "EDGE_ADD", k: int = 1, params: list[dict] | None = None,
                  seed: int = 0, forbid_zero_indegree_nodes: bool = True,
                  max_indegree: int | None = None, allow_self_loops: bool = True,
                  resume: bool = True, loss_params: dict[str, Any] | None = None,
                  C: float = 0.0, timeout_seconds: float | None = None,
                  network_label: str | None = None) -> dict[str, Any]:
    """Enumerate one perturbation family with atomic case checkpoints.

    A checkpoint is written before the manifest is advanced.  Re-running the
    same directory skips validated identifiers, making interruption/resume
    scientifically idempotent while retaining diagnostic failures.
    """
    root = Path(out_dir)
    ensure_dir(root)
    params = params or [{} for _ in gates]
    if not is_admissible_perturbation(
        A0, forbid_zero_indegree_nodes=forbid_zero_indegree_nodes,
        max_indegree=max_indegree, allow_self_loops=allow_self_loops, gates=gates,
    ):
        raise ValueError("base network is not admissible under the declared run policy")
    config_id = hashlib.sha256(json.dumps({"A": A0, "gates": gates, "params": params,
                                           "k": k,
                                           "kind": kind, "seed": seed, "C": C,
                                           "loss_params": loss_params,
                                           "forbid_zero_indegree_nodes": forbid_zero_indegree_nodes,
                                           "max_indegree": max_indegree,
                                           "allow_self_loops": allow_self_loops}, sort_keys=True).encode()).hexdigest()[:20]
    config = make_envelope("configuration", config_id=config_id, sweep_id=None)
    config.update({"N": len(A0), "k": k, "perturbation_kind": kind,
                   "orientation": "A[target][source]", "self_loop_policy": "allowed" if allow_self_loops else "forbidden",
                   "empty_input_policy": "forbid" if forbid_zero_indegree_nodes else "allow",
                   "max_indegree": max_indegree, "loss_id": "L_SINGLE_TARGET",
                   "params": params,
                   "loss_params": loss_params or {"target_selection": "first_sorted_baseline_state"},
                   "seed": seed, "network_label": network_label, "C": C,
                   "provenance": source_provenance(),
                   "observable": "basin_weighted_attractor_repertoire",
                   "approximation": "none_exact_full_state_space",
                   "estimator_parameters": {}, "uncertainty": {"method": "exact"},
                   "process_status": "normal_exit", "accepted_validation": True})
    config = seal(config)
    atomic_write_json(root / "config.json", config)
    base, rep0 = _base_record(A0, gates, params, config_id)
    atomic_write_json(root / "base.json", base)

    candidates = admissible_ball(A0, k, kind, forbid_zero_indegree_nodes=forbid_zero_indegree_nodes,
                                 max_indegree=max_indegree, allow_self_loops=allow_self_loops, gates=gates)
    all_candidates = admissible_ball(A0, k, kind, forbid_zero_indegree_nodes=False,
                                     max_indegree=None, allow_self_loops=True)
    excluded = len(all_candidates) - len(candidates)
    out_jsonl = root / "catalogue.jsonl"
    checkpoint_dir = root / "checkpoints"
    if not resume and out_jsonl.exists():
        # Explicit fresh-run mode is used for regeneration after a contract
        # change.  The caller has opted into replacing this run namespace;
        # normal operation keeps the append-only history and resumes.
        out_jsonl.unlink()
    existing: dict[str, dict[str, Any]] = {}
    history: list[dict[str, Any]] = []
    if resume and out_jsonl.exists():
        for row in read_jsonl(out_jsonl):
            if row.get("config_id") != config_id:
                raise ValueError("output directory belongs to a different scientific configuration")
            history.append(row)
            existing[row["perturbation_id"]] = row

    rows = list(existing.values())
    attempts_this_run = 0
    for matrix in candidates:
        pid = perturbation_id(A0, matrix, kind)
        if pid in existing and existing[pid].get("accepted_validation"):
            continue
        checkpoint_path = checkpoint_dir / f"{hashlib.sha256(pid.encode()).hexdigest()}.json"
        checkpoint_row: dict[str, Any] | None = None
        if resume and checkpoint_path.exists():
            try:
                candidate = read_json(checkpoint_path)
                if (candidate.get("config_id") == config_id and
                        candidate.get("perturbation_id") == pid):
                    checkpoint_row = candidate
            except (OSError, ValueError):
                checkpoint_row = None
        started = time.perf_counter()
        if checkpoint_row is not None:
            row = checkpoint_row
        else:
            try:
                chosen_targets = (loss_params or {}).get("targets")
                row = run_with_timeout(
                    lambda: _case_record(matrix, A0, gates, params, rep0, config_id, kind,
                                         time.perf_counter() - started,
                                         target_state=chosen_targets[0] if chosen_targets else None),
                    timeout_seconds,
                )
            except Exception as exc:  # preserve failures as diagnostic records
                row = make_envelope("diagnostic", config_id=config_id, sweep_id=None)
                row.update({"perturbation_kind": kind, "perturbation_id": pid,
                            "is_identity": graph_distance(A0, matrix) == 0,
                            "observable": "basin_weighted_attractor_repertoire",
                            "approximation": "none_exact_full_state_space",
                            "uncertainty": {"method": "exact"},
                            "provenance": source_provenance(),
                            "process_status": "timeout" if isinstance(exc, CaseTimeout) else "crash",
                            "failure_class": "timeout" if isinstance(exc, CaseTimeout) else "exception",
                            "accepted_validation": False,
                            "failure": f"{type(exc).__name__}: {exc}"})
                row = seal(row)
            atomic_write_json(checkpoint_path, row)
        # The JSONL is an append-only attempt history.  The manifest/summary
        # uses the latest row for each stable perturbation id, so a failed
        # attempt is retained without duplicating an accepted scientific row.
        _json_append(out_jsonl, row)
        attempts_this_run += 1
        if pid not in existing:
            rows.append(row)
        else:
            rows = [row if item.get("perturbation_id") == pid else item for item in rows]
        existing[pid] = row

    valid_rows = [r for r in rows if r.get("accepted_validation")]
    summary = {"config_id": config_id, "N": len(A0), "k": k, "network_label": network_label,
               "perturbation_kind": kind,
               "n_candidates_before_filter": len(all_candidates), "n_admissible": len(candidates),
               "n_excluded": excluded, "n_rows": len(rows),
               "n_attempt_records": len(history) + attempts_this_run,
               "n_accepted": len(valid_rows), "n_failures": len(rows) - len(valid_rows),
               "status": "completed" if len(valid_rows) == len(candidates) else "completed_with_failures",
               "provenance": config["provenance"],
               "scientific_digest": scientific_digest({"config_id": config_id,
                                                        "rows": rows})}
    nonidentity = [r for r in valid_rows if not str(r.get("perturbation_id", "")).endswith(":identity")]
    summary["descriptive_metrics"] = {
        "support_change_rate": (sum(r["support"]["support_jaccard"] > 0 for r in nonidentity) / len(nonidentity)
                                if nonidentity else 0.0),
        "finite_kl_rate": (sum(not r["infinite_kl"] for r in nonidentity) / len(nonidentity)
                           if nonidentity else 0.0),
        "mean_total_variation": (sum(r["total_variation"] for r in nonidentity) / len(nonidentity)
                                 if nonidentity else 0.0),
        "mean_jensen_shannon": (sum(r["jensen_shannon"] for r in nonidentity) / len(nonidentity)
                                if nonidentity else 0.0),
    }
    if valid_rows:
        params_for_loss = loss_params or {"targets": [rep0["support"][0]]}
        frontier = constrained_optimum(valid_rows, rep0, C, loss_params=params_for_loss)
        relaxation = kl_ball_upper_bound(rep0, C, "L_SINGLE_TARGET", params_for_loss)
        frontier["unconstrained_KL_ball_upper_bound"] = relaxation["upper_bound"]
        frontier["gap_upper_bound_minus_V"] = (
            relaxation["upper_bound"] - frontier["V_k_C"]
            if relaxation["upper_bound"] is not None and frontier["V_k_C"] is not None else None
        )
        summary["frontier"] = frontier
    atomic_write_json(root / "summary.json", summary)
    manifest = make_envelope("catalogue_manifest", config_id=config_id, sweep_id=None)
    manifest.update({
        "manifest_kind": "exact_catalogue",
        "catalogue_path": "catalogue.jsonl",
        "checkpoint_path": "checkpoints/",
        "expected_perturbation_ids": [perturbation_id(A0, matrix, kind) for matrix in candidates],
        "latest_perturbation_ids": sorted(existing),
        "n_attempt_records": len(history) + attempts_this_run,
        "n_latest_records": len(rows),
        "n_accepted": len(valid_rows),
        "n_failures": len(rows) - len(valid_rows),
        "scientific_digest": summary["scientific_digest"],
        "provenance": config["provenance"],
        "observable": "basin_weighted_attractor_repertoire",
        "approximation": "none_exact_full_state_space",
        "uncertainty": {"method": "exact"},
        "process_status": "normal_exit",
        "accepted_validation": all(r.get("accepted_validation") for r in rows),
    })
    atomic_write_json(root / "manifest.json", seal(manifest))
    atomic_write_json(root / "progress.json", {"completed": len(rows), "total": len(candidates),
                                                "remaining": max(0, len(candidates) - len(rows))})
    return summary
