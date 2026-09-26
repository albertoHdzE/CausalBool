"""Analysis of the third round: M0 diagnosis summary and the M2 prediction.

Estimators here are the REPORTER's. The independent auditor
(``third_round_audit.py``) recomputes every number from the raw rows with its
own code and does not import this module.
"""

from __future__ import annotations

import collections
import json
import math
import statistics
from pathlib import Path
from typing import Dict, List

from research import optimization_common as oc
from research import third_round_common as tc

# Components of the exclusive-timer ownership map (third_round_diagnosis.TIMED).
REPLACED = ("tfix_shell", "tfix_copy", "precedence", "issue_capacity", "bounds_live",
            "bounds_product", "address_support", "child_domain_copy")
COMPONENT_GROUPS = {
    "precedence": ("precedence",),
    "issue_capacity": ("issue_capacity",),
    "fixpoint_shell_and_copies": ("tfix_shell", "tfix_copy", "child_domain_copy"),
    "live_and_product_bounds": ("bounds_live", "bounds_product"),
    "address_support": ("address_support",),
    "address_pairs": ("address_pairs",),
    "certificates": ("certificates",),
    "options": ("options",),
    "validation": ("validation",),
    "state_copy": ("state_copy",),
    "setup_encoding": ("propagation_setup", "encoding"),
}


def _rows(run: Path, stage: str) -> List[dict]:
    return oc.read_rows(Path(run) / "stages" / stage / "rows.jsonl")


def equal_family_geomean(ratios: Dict[int, float]) -> float:
    if not ratios:
        raise ValueError("refusing an empty ratio set")
    families = collections.defaultdict(list)
    for seed, r in ratios.items():
        families[seed % 5].append(math.log(r))
    if len(families) != 5:
        raise ValueError(f"expected five families, got {len(families)}")
    return math.exp(statistics.mean(statistics.mean(v) for v in families.values()))


def diagnosis(run: Path) -> dict:
    rows = _rows(run, "M_diagnosis")
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("failed"):
            raise ValueError(f"failed diagnostic row {tc.row_key(r)}")
        by[(r["seed"], r["mode_key"])].append(r)
    reuse = json.loads((Path(run) / "stages" / "M_diagnosis" / "REUSE_COUNTS.json").read_text())
    programs = {}
    for seed in tc.diagnostic_seeds():
        times = sorted(r["compile_call_seconds"] for r in by[(seed, "work:10000")])
        t0 = statistics.median(times)
        timers = by[(seed, "exclusive_timers")][0]
        ex = timers["exclusive_seconds"]
        wall = timers["timed_call_wall_seconds"]
        groups = {g: sum(ex.get(c, 0.0) for c in cs) for g, cs in COMPONENT_GROUPS.items()}
        replaced = sum(ex.get(c, 0.0) for c in REPLACED)
        parity = by[(seed, "instrumentation_parity")][0]
        trace = by[(seed, "workload_trace")][0]
        memory = by[(seed, "peak_memory")][0]
        counts = reuse[str(seed)]["counts"]
        programs[str(seed)] = {
            "family": tc.family_of(seed), "T0_runs": times, "T0_median": t0,
            "timed_wall": wall, "timer_inflation": wall / t0,
            "exclusive_sum": sum(ex.values()), "untimed_remainder": timers[
                "untimed_remainder_seconds"],
            "reconciliation": (sum(ex.values()) + timers["untimed_remainder_seconds"]) / wall,
            "group_share_of_timed_wall": {g: v / wall for g, v in groups.items()},
            "replaced_share_of_timed_wall": replaced / wall,
            "calls": timers["calls"],
            "parity": parity["parity"], "timers_fingerprint_equal_plain":
                timers["fingerprint"] == parity["plain"],
            "trace_fingerprint_equal_plain": trace["fingerprint"] == parity["plain"],
            "workload_sha256": trace["workload_sha256"], "events": trace["events"],
            "tracemalloc_peak_bytes": memory["tracemalloc_peak_bytes"],
            "nodes": timers["nodes"],
            "replay_vs_capture_parity": reuse[str(seed)]["replay_vs_capture"]["parity"],
            "reuse": _reuse_view(counts)}
    pooled = collections.Counter()
    for seed in tc.diagnostic_seeds():
        for k, v in reuse[str(seed)]["counts"].items():
            pooled[k] += v
    fam = collections.defaultdict(list)
    for s, p in programs.items():
        fam[p["family"]].append(p["replaced_share_of_timed_wall"])
    return {"programs": programs, "pooled_reuse": _reuse_view(pooled),
            "family_mean_replaced_share": {f: statistics.mean(v) for f, v in fam.items()},
            "all_parity": all(p["parity"] and p["timers_fingerprint_equal_plain"]
                              and p["trace_fingerprint_equal_plain"]
                              and p["replay_vs_capture_parity"] for p in programs.values()),
            "programs_count": len(programs), "rows": len(rows)}


def _frac(a, b):
    return (a / b) if b else None


def _reuse_view(c) -> dict:
    return {
        "tf_calls": c.get("tf_calls", 0), "tf_child_calls": c.get("tf_child_calls", 0),
        "tf_sweeps": c.get("tf_sweeps", 0),
        "edge_evals": c.get("edge_evals", 0), "edge_fires": c.get("edge_fires", 0),
        "edge_evals_unchanged_fraction": _frac(c.get("edge_evals_unchanged", 0),
                                               c.get("edge_evals", 0)),
        "edge_fire_fraction": _frac(c.get("edge_fires", 0), c.get("edge_evals", 0)),
        "op_scans": c.get("op_scans", 0), "value_checks": c.get("value_checks", 0),
        "op_scans_unchanged_fraction": _frac(c.get("op_scans_unchanged", 0),
                                             c.get("op_scans", 0)),
        "op_scans_fired_fraction": _frac(c.get("op_scans_fired", 0), c.get("op_scans", 0)),
        "rule2_phases_singles_unchanged_fraction": _frac(
            c.get("rule2_phases_singles_unchanged", 0), c.get("rule2_phases", 0)),
        "peak_values_unchanged_after_child_fraction": _frac(
            c.get("peak_values_unchanged_after_child", 0), c.get("peak_values_after_child", 0)),
        "peak_children_all_unchanged_fraction": _frac(
            c.get("peak_children_all_unchanged", 0), c.get("peak_children", 0)),
        "prune_calls": c.get("prune_calls", 0),
        "prune_calls_address_phase": c.get("prune_calls_address_phase", 0),
        "af_calls": c.get("af_calls", 0), "af_root_calls": c.get("af_root_calls", 0),
        "af_sweeps": c.get("af_sweeps", 0), "pair_evals": c.get("pair_evals", 0),
        "pair_fires": c.get("pair_fires", 0),
        "pair_evals_unchanged_fraction": _frac(c.get("pair_evals_unchanged", 0),
                                               c.get("pair_evals", 0)),
        "pair_evals_cold_fraction": _frac(c.get("pair_evals_cold", 0), c.get("pair_evals", 0)),
    }


def prediction(run: Path) -> dict:
    """M2: ``T0 - O + N`` and ``T0 - O + 1.5 N`` per program, as fixed in MECHANISM_SPEC.json."""

    diag = json.loads((Path(run) / "DIAGNOSIS.json").read_text())
    rows = _rows(run, "M_kernel")
    by = collections.defaultdict(list)
    for r in rows:
        if r.get("failed"):
            raise ValueError(f"failed kernel row {tc.row_key(r)}")
        by[(r["seed"], r["arm_id"])].append(r)
    timers = {r["seed"]: r for r in _rows(run, "M_diagnosis") if r["mode_key"] == "exclusive_timers"}
    multiplier = tc.MECHANISM_GATE["replacement_and_extra_overhead_multiplier"]
    programs, ratio, conservative = {}, {}, {}
    parity_all = True
    for seed in tc.diagnostic_seeds():
        p = diag["programs"][str(seed)]
        t0 = p["T0_median"]
        base = by[(seed, "baseline_kernel")]
        shared = by[(seed, "shared_state_kernel")]
        if len(base) != tc.KERNEL_REPS or len(shared) != tc.KERNEL_REPS:
            raise ValueError(f"incomplete kernel rows for {seed}")
        parity = all(r["parity"]["parity"] for r in base + shared)
        parity_all &= parity
        o_replay = statistics.median(r["replay_seconds"] for r in base)
        ex = timers[seed]["exclusive_seconds"]
        o_timer = sum(ex.get(c, 0.0) for c in REPLACED) / p["timer_inflation"]
        O = min(o_replay, o_timer)
        n_kernel = statistics.median(r["replay_seconds"] for r in shared)
        n_integration = statistics.median(r["integration_estimate_seconds"] for r in shared)
        N = n_kernel + n_integration
        valid = 0 <= O <= t0
        pred = t0 - O + N
        cons = t0 - O + multiplier * N
        if not (valid and pred > 0 and cons > 0):
            raise ValueError(f"invalid model for {seed}: O={O}, T0={t0}")
        ratio[seed], conservative[seed] = pred / t0, cons / t0
        programs[str(seed)] = {
            "family": tc.family_of(seed), "T0": t0, "O_replay_median": o_replay,
            "O_timer_deflated": o_timer, "O": O, "O_source": "replay" if O == o_replay else "timer",
            "N_kernel_median": n_kernel, "N_integration_median": n_integration, "N": N,
            "baseline_replay_runs": [r["replay_seconds"] for r in base],
            "shared_replay_runs": [r["replay_seconds"] for r in shared],
            "events": base[0]["events"], "kernel_speedup_on_O": (o_replay / n_kernel
                                                                  if n_kernel else None),
            "T_pred": pred, "T_pred_conservative": cons,
            "ratio": ratio[seed], "ratio_conservative": conservative[seed], "parity": parity}
    families = collections.defaultdict(dict)
    for seed in ratio:
        families[tc.family_of(seed)][seed] = conservative[seed]
    gate = tc.MECHANISM_GATE["conservative_predicted_compile_ratio_max"]
    agg = equal_family_geomean(ratio)
    agg_c = equal_family_geomean(conservative)
    return {"programs": programs, "rows": len(rows),
            "predicted_ratio_equal_family": agg,
            "predicted_ratio_conservative_equal_family": agg_c,
            "family_conservative_geomean": {
                f: math.exp(statistics.mean(math.log(v) for v in d.values()))
                for f, d in families.items()},
            "kernel_parity_all": parity_all, "gate_max": gate,
            "gate_met": bool(parity_all and agg_c <= gate),
            "note": "development model on 30 selected development programs, not a confidence "
                    "bound or a promised compiler speedup"}
