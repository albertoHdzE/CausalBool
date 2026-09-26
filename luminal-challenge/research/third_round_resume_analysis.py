"""Reporter of the resume: the corrected M arithmetic (resume plan section 3).

Original registered result (mismatched scope, old adapter) is recomputed and kept
beside the approved correction; replay-only O is a sensitivity only. The
independent auditor (``third_round_resume_audit``) does not import this module.
"""

from __future__ import annotations

import collections
import math
import statistics
from pathlib import Path

from research import third_round_common as tc
from research import third_round_resume_common as rc


def _geo(values: dict) -> float:
    fam = collections.defaultdict(list)
    for seed, v in values.items():
        fam[seed % 5].append(math.log(v))
    if len(fam) != 5 or any(len(v) != 6 for v in fam.values()):
        raise ValueError("expected 5 families x 6 programs")
    return math.exp(statistics.mean(statistics.mean(v) for v in fam.values()))


def recalibrated(run: Path) -> dict:
    parent = rc.PARENT_RUN
    m0 = rc.strict_rows(parent / "stages/M_diagnosis/rows.jsonl")
    mk = rc.strict_rows(parent / "stages/M_kernel/rows.jsonl")
    ad = rc.strict_rows(Path(run) / "stages" / rc.ADAPTER_STAGE / "rows.jsonl")
    by = collections.defaultdict(list)
    for r in m0 + mk + ad:
        if r.get("failed") or r.get("timed_out"):
            raise ValueError(f"failed row {tc.row_key(r)}")
        by[(r["seed"], r["mode_key"], r["arm_id"])].append(r)
    mult = tc.MECHANISM_GATE["replacement_and_extra_overhead_multiplier"]
    per, old, corr, corr_old_n, replay_only, speed = {}, {}, {}, {}, {}, {}
    for seed in tc.diagnostic_seeds():
        t0 = statistics.median(r["compile_call_seconds"] for r in by[(seed, "work:10000", "R0")])
        timer = by[(seed, "exclusive_timers", "R0")][0]
        infl = timer["timed_call_wall_seconds"] / t0
        ex = timer["exclusive_seconds"]
        base = by[(seed, "kernel", "baseline_kernel")]
        shared = by[(seed, "kernel", "shared_state_kernel")]
        adapt = by[(seed, "adapter", "adapter")]
        if not (len(base) == len(shared) == len(adapt) == 3):
            raise ValueError(f"incomplete rows for {seed}")
        o_replay = statistics.median(r["replay_seconds"] for r in base)
        o_old = min(o_replay, sum(ex.get(c, 0.0) for c in rc.OLD_SCOPE) / infl)
        o_matched = min(o_replay, sum(ex.get(c, 0.0) for c in rc.MATCHED_SCOPE) / infl)
        n_kernel = statistics.median(r["replay_seconds"] for r in shared)
        a_old = statistics.median(r["integration_estimate_seconds"] for r in shared)
        a_new = statistics.median(r["adapter_seconds"] for r in adapt)
        unmeasured = 0.0
        n_old = n_kernel + a_old
        n_new = n_kernel + max(a_old, a_new) + unmeasured
        if not (0 <= o_matched <= t0):
            raise ValueError(f"O outside [0, T0] for {seed}")
        old[seed] = (t0 - o_old + mult * n_old) / t0
        corr_old_n[seed] = (t0 - o_matched + mult * n_old) / t0
        corr[seed] = (t0 - o_matched + mult * n_new) / t0
        replay_only[seed] = (t0 - o_replay + mult * n_new) / t0
        speed[seed] = o_replay / n_kernel
        per[str(seed)] = {"family": tc.family_of(seed), "T0": t0, "timer_inflation": infl,
                          "O_replay": o_replay, "O_old_scope": o_old, "O_matched": o_matched,
                          "N_kernel": n_kernel, "adapter_old_median": a_old,
                          "adapter_repaired_median": a_new,
                          "adapter_repaired_runs": [r["adapter_seconds"] for r in adapt],
                          "unmeasured_upper": unmeasured, "N": n_new,
                          "point_ratio": (t0 - o_matched + n_new) / t0,
                          "conservative_ratio": corr[seed], "kernel_speedup": speed[seed]}
    fam = collections.defaultdict(list)
    for seed, v in corr.items():
        fam[tc.family_of(seed)].append(math.log(v))
    point = _geo({int(s): p["point_ratio"] for s, p in per.items()})
    result = {
        "programs": per,
        "original_registered_conservative": _geo(old),
        "corrected_scope_old_adapter_conservative": _geo(corr_old_n),
        "corrected_point": point,
        "corrected_conservative": _geo(corr),
        "replay_only_sensitivity_conservative": _geo(replay_only),
        "family_corrected_conservative": {f: math.exp(statistics.mean(v)) for f, v in fam.items()},
        "kernel_speedup_median": statistics.median(speed.values()),
        "kernel_speedup_range": [min(speed.values()), max(speed.values())],
        "adapter_over_N_kernel_max": max(p["adapter_repaired_median"] / p["N_kernel"]
                                         for p in per.values()),
        "gate_max": rc.load_protocol()["accounting"]["conservative_ratio_max"],
        "label": "post-hoc development accounting correction; original result retained; "
                 "not a measured compile-call ratio or a confidence bound"}
    result["gate_met"] = result["corrected_conservative"] <= result["gate_max"]
    return result
