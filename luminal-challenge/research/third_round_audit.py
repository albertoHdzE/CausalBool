"""Independent numerical audit and identity check of the third round.

Does NOT import ``third_round_analysis`` (the reporter) or reuse its estimators.
Constants are read from ``plan/phase2_third_round/PROTOCOL.json`` directly;
file I/O is ``optimization_common``'s. Every finding names the field it concerns;
the report prints its denominators and refuses an empty input.

Numerical audit: recomputes, from the raw stage rows only, T0 (median of the
three fixed-work rows), the timer inflation, both O arms, N, the per-program
predicted ratios, the equal-family geometric means and the gate verdict, then
compares them with ``PREDICTION.json`` and ``MECHANISM_DECISION.json``.

Identity check: R0 source/export hashes, the locked assignment package, the
workload files against ``WORKLOAD_MANIFEST.json`` and the M0 rows, frozen expected
keys against the rows (one row per key, no failure), the ledger, and the
NOT_RUN state of every dependent stage (no row file may exist for them).

Usage::

    python -m research.third_round_audit --run RUN [--out FILE]
"""

from __future__ import annotations

import argparse
import gzip
import json
import math
import subprocess
import sys
from pathlib import Path

from research import optimization_common as oc

ROOT = oc.ROOT
PROTOCOL = json.loads((ROOT / "plan" / "phase2_third_round" / "PROTOCOL.json").read_text())
# The auditor's own list of the timer components counted as replaced work
# (written from MECHANISM_SPEC.json's consumer list, not copied from the reporter).
TIMER_REPLACED = {"precedence", "issue_capacity", "tfix_shell", "tfix_copy",
                  "child_domain_copy", "bounds_live", "bounds_product", "address_support"}
KEY = ("stage_id", "program_sha256", "repetition", "arm_id", "mode_key")
REL = 1e-9


def _median(xs):
    xs = sorted(xs)
    if not xs:
        raise ValueError("median of nothing")
    n = len(xs)
    return xs[n // 2] if n % 2 else (xs[n // 2 - 1] + xs[n // 2]) / 2.0


def _key(r):
    return "|".join(str(r[k]) for k in KEY)


def _close(a, b):
    return abs(a - b) <= REL * max(1.0, abs(a), abs(b))


def numerical_audit(rows_m0, rows_k, prediction, decision) -> dict:
    findings, checks = [], 0
    if not rows_m0 or not rows_k:
        raise ValueError("refusing to audit empty stages")
    first, last = PROTOCOL["diagnostic"]["first_seed"], PROTOCOL["diagnostic"]["last_seed"]
    seeds = list(range(first, last + 1))
    families = PROTOCOL["families"]
    t_reps = PROTOCOL["diagnostic"]["time_repetitions"]
    k_reps = PROTOCOL["diagnostic"]["kernel_repetitions"]
    mult = PROTOCOL["mechanism_gate"]["replacement_and_extra_overhead_multiplier"]
    gate = PROTOCOL["mechanism_gate"]["conservative_predicted_compile_ratio_max"]
    work, timer, base, shared = {}, {}, {}, {}
    for r in rows_m0:
        if r.get("failed") or r.get("timed_out"):
            findings.append(("M_diagnosis", _key(r), "failed row"))
            continue
        if r["mode_key"] == "work:10000":
            work.setdefault(r["seed"], []).append(r["compile_call_seconds"])
        elif r["mode_key"] == "exclusive_timers":
            timer.setdefault(r["seed"], []).append(r)
    for r in rows_k:
        if r.get("failed") or r.get("timed_out"):
            findings.append(("M_kernel", _key(r), "failed row"))
            continue
        target = base if r["arm_id"] == "baseline_kernel" else shared
        target.setdefault(r["seed"], []).append(r)
        checks += 1
        if not r["parity"]["parity"]:
            findings.append(("M_kernel", _key(r), "kernel parity false"))
    per_family_log = {f: [] for f in families}
    per_family_log_c = {f: [] for f in families}
    for seed in seeds:
        fam = families[seed % 5]
        if len(work.get(seed, [])) != t_reps or len(timer.get(seed, [])) != 1:
            findings.append(("M_diagnosis", seed, "wrong repetition count"))
            continue
        if len(base.get(seed, [])) != k_reps or len(shared.get(seed, [])) != k_reps:
            findings.append(("M_kernel", seed, "wrong repetition count"))
            continue
        t0 = _median(work[seed])
        t = timer[seed][0]
        inflation = t["timed_call_wall_seconds"] / t0
        o_timer = sum(v for k, v in t["exclusive_seconds"].items()
                      if k in TIMER_REPLACED) / inflation
        o_replay = _median([r["replay_seconds"] for r in base[seed]])
        O = min(o_timer, o_replay)
        N = (_median([r["replay_seconds"] for r in shared[seed]])
             + _median([r["integration_estimate_seconds"] for r in shared[seed]]))
        if not (0 <= O <= t0):
            findings.append(("prediction", seed, "O outside [0, T0]"))
        ratio = (t0 - O + N) / t0
        ratio_c = (t0 - O + mult * N) / t0
        if ratio <= 0 or ratio_c <= 0:
            findings.append(("prediction", seed, "non-positive predicted cost"))
            continue
        per_family_log[fam].append(math.log(ratio))
        per_family_log_c[fam].append(math.log(ratio_c))
        reported = prediction["programs"].get(str(seed))
        if reported is None:
            findings.append(("prediction.programs", seed, "missing"))
            continue
        for field, mine in (("T0", t0), ("O", O), ("N", N), ("ratio", ratio),
                            ("ratio_conservative", ratio_c), ("O_replay_median", o_replay),
                            ("O_timer_deflated", o_timer)):
            checks += 1
            if not _close(mine, reported[field]):
                findings.append((f"prediction.programs.{seed}.{field}", mine, reported[field]))
    if any(len(v) != (last - first + 1) // 5 for v in per_family_log.values()):
        findings.append(("prediction", "families", "unequal or missing family members"))
    agg = math.exp(sum(sum(v) / len(v) for v in per_family_log.values() if v) / len(families))
    agg_c = math.exp(sum(sum(v) / len(v) for v in per_family_log_c.values() if v)
                     / len(families))
    for field, mine in (("predicted_ratio_equal_family", agg),
                        ("predicted_ratio_conservative_equal_family", agg_c)):
        checks += 1
        if not _close(mine, prediction[field]):
            findings.append((field, mine, prediction[field]))
    parity_all = not any(f[2] == "kernel parity false" for f in findings)
    met = bool(parity_all and agg_c <= gate)
    checks += 3
    if prediction["gate_met"] != met:
        findings.append(("prediction.gate_met", met, prediction["gate_met"]))
    if decision["gate"]["met"] != met:
        findings.append(("decision.gate.met", met, decision["gate"]["met"]))
    expected_decision = "NO_JUSTIFIED_MECHANISM" if not met else "INTEGRATE_C1"
    if decision["decision"] != expected_decision:
        findings.append(("decision.decision", expected_decision, decision["decision"]))
    if not _close(decision["gate"]["registered_conservative_ratio"], agg_c):
        findings.append(("decision.gate.registered_conservative_ratio", agg_c,
                         decision["gate"]["registered_conservative_ratio"]))
    return {"checks": checks, "programs": len(seeds), "findings": findings,
            "recomputed": {"ratio": agg, "ratio_conservative": agg_c, "gate_met": met},
            "status": "PASS" if checks and not findings else "FAIL"}


def identity_check(run: Path) -> dict:
    findings, checks = [], 0
    b = PROTOCOL["baseline"]
    for path, digest in ((b["solver"], b["sha256"]), (b["export"], b["export_sha256"])):
        checks += 1
        if oc.file_sha256(ROOT / path) != digest:
            findings.append(("baseline", path, "hash differs"))
    proc = subprocess.run([sys.executable, str(ROOT / "plan/phase2_third_round/verify_package.py")],
                          cwd=str(ROOT), capture_output=True, text=True)
    checks += 1
    if proc.returncode != 0 or '"status": "PASS"' not in proc.stdout:
        findings.append(("package", "verify_package.py", proc.stdout[-500:]))
    manifest = json.loads((run / "WORKLOAD_MANIFEST.json").read_text())
    m0 = oc.read_rows(run / "stages/M_diagnosis/rows.jsonl")
    traced = {str(r["seed"]): r for r in m0 if r["mode_key"] == "workload_trace"}
    if not manifest["workloads"]:
        raise ValueError("refusing an empty workload manifest")
    for seed, item in manifest["workloads"].items():
        checks += 2
        raw = gzip.decompress(Path(item["path"]).read_bytes())
        if oc.sha256_bytes(raw) != item["sha256"]:
            findings.append(("workload", seed, "file differs from manifest"))
        if traced[seed]["workload_sha256"] != item["sha256"]:
            findings.append(("workload", seed, "manifest differs from M0 row"))
    for stage, expected in (("M_diagnosis", PROTOCOL["expected_rows"]["M_diagnosis"]),
                            ("M_kernel", PROTOCOL["expected_rows"]["M_kernel"])):
        keys = json.loads((run / "stages" / stage / "EXPECTED_KEYS.json").read_text())["keys"]
        rows = oc.read_rows(run / "stages" / stage / "rows.jsonl")
        seen = [_key(r) for r in rows]
        checks += 4
        if len(keys) != expected or len(set(keys)) != expected:
            findings.append((stage, "expected keys", len(keys)))
        if sorted(seen) != sorted(keys):
            findings.append((stage, "rows do not match expected keys one-to-one", len(seen)))
        if any(r.get("failed") or r.get("timed_out") for r in rows):
            findings.append((stage, "failed rows present", None))
        attempts = oc.read_rows(run / "stages" / stage / "ATTEMPTS.jsonl")
        if sum(1 for a in attempts if "finished_utc" in a) != expected:
            findings.append((stage, "attempt ledger count", len(attempts)))
    decision = json.loads((run / "MECHANISM_DECISION.json").read_text())
    for stage, state in decision["dependents"].items():
        checks += 1
        if not state.startswith("NOT_RUN") or (run / "stages" / stage).exists():
            findings.append((stage, "dependent stage not in a clean NOT_RUN state", state))
    ledger = oc.read_rows(run / "MEASUREMENT_WALL_LEDGER.jsonl")
    hours = sum(float(r["process_seconds"]) for r in ledger) / 3600.0
    checks += 1
    if hours > PROTOCOL["measurement_wall_cap_hours"]:
        findings.append(("ledger", "over cap", hours))
    return {"checks": checks, "findings": findings, "measurement_hours": hours,
            "ledger_rows": len(ledger), "status": "PASS" if checks and not findings else "FAIL"}


def audit(run: Path) -> dict:
    run = Path(run)
    rows_m0 = oc.read_rows(run / "stages/M_diagnosis/rows.jsonl")
    rows_k = oc.read_rows(run / "stages/M_kernel/rows.jsonl")
    prediction = json.loads((run / "PREDICTION.json").read_text())
    decision = json.loads((run / "MECHANISM_DECISION.json").read_text())
    numerical = numerical_audit(rows_m0, rows_k, prediction, decision)
    identity = identity_check(run)
    return {"numerical": numerical, "identity": identity,
            "status": "PASS" if numerical["status"] == identity["status"] == "PASS" else "FAIL"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    parser.add_argument("--out")
    args = parser.parse_args(argv)
    report = audit(Path(args.run))
    text = json.dumps(report, indent=1, sort_keys=True, default=str)
    if args.out:
        Path(args.out).write_text(text + "\n")
    print(json.dumps({"status": report["status"],
                      "numerical": {k: report["numerical"][k] for k in ("checks", "status")},
                      "numerical_findings": len(report["numerical"]["findings"]),
                      "identity": {k: report["identity"][k] for k in ("checks", "status")},
                      "identity_findings": len(report["identity"]["findings"]),
                      "measurement_hours": round(report["identity"]["measurement_hours"], 4)}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
