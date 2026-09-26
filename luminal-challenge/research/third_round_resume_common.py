"""Constants, run directory and the raw-stream runner of the third-round RESUME.

Authority: ``plan/CLAUDE_PHASE2_THIRD_ROUND_RESUME.md`` v1.0 and
``plan/phase2_third_round_resume/PROTOCOL.json`` (one source of its constants,
compared with the literals below by ``check_protocol_constants``). The parent
protocol and ``third_round_common`` stay authoritative for everything the resume
does not change; they are imported, never edited.

Why a new runner rather than ``third_round_common.run_stage``: the resume forbids
editing existing modules, and requires COMPLETE raw stdout/stderr for every new
process (the parent kept only tails). This runner keeps the parent's key, order,
freeze and no-retry discipline and adds ``raw/<n>.{stdout,stderr}`` files whose
hashes are recorded in the attempt ledger. Rows are parsed strictly: the row file
is written only by this runner, and every line must be one complete JSON object.
"""

from __future__ import annotations

import json
import math
import subprocess
import time
from pathlib import Path
from typing import List, Optional, Sequence

from research import optimization_common as oc
from research import third_round_common as tc

ROOT = oc.ROOT
RESULTS = oc.RESULTS
PACKAGE = ROOT / "plan" / "phase2_third_round_resume"
PROTOCOL_PATH = PACKAGE / "PROTOCOL.json"
PROTOCOL_ID = "luminal-phase2-third-improvement-resume-1.0"
PARENT_RUN = RESULTS / "third_round_20260925"
RUN_NAME = "third_round_20260925_resume"

KERNEL_SOURCE = "research/third_round_kernel.py"
KERNEL_SHA256 = "77c373e1d4e6a328c70c590d46ffdf5b5a82ec8ccd38f82de246821f2da5ff85"
KERNEL_SPEC_PREFIX_BYTES = 17377
OLD_CONSERVATIVE = 0.8268222321783514
MATCHED_OLD_ADAPTER = 0.7638230784259178
REPLAY_ONLY = 0.7422848903946956
CORRECTED_SPEEDUP_MEDIAN = 2.3649168298633314
OLD_SCOPE = ("tfix_shell", "tfix_copy", "precedence", "issue_capacity", "bounds_live",
             "bounds_product", "address_support", "child_domain_copy")
MATCHED_SCOPE = OLD_SCOPE + ("certificates", "propagation_setup", "address_pairs")
COMMON_BEFORE = "bd3a7b48d7d9535dea20fe5a8a70a17b993c292a476f67838981acb868d72f6d"
COMMON_AFTER = "3a0e4163eb450adc08d2860d68a28ca9c7fdb0d67bf77a82c0f27f0b77542632"
ADAPTER_STAGE = "R_adapter"
ADAPTER_ROWS = 90


def load_protocol() -> dict:
    return json.loads(PROTOCOL_PATH.read_text())


def check_protocol_constants() -> dict:
    p = load_protocol()
    a, ad = p["accounting"], p["adapter"]
    checks = {
        "protocol_id": (p["protocol_id"], PROTOCOL_ID),
        "kernel": ((p["preserved_mechanism"]["source"], p["preserved_mechanism"]["sha256"]),
                   (KERNEL_SOURCE, KERNEL_SHA256)),
        "old": (a["old_conservative_ratio"], OLD_CONSERVATIVE),
        "matched_old_adapter": (a["matched_scope_ratio_with_old_adapter"], MATCHED_OLD_ADAPTER),
        "replay_only": (a["replay_only_ratio_sensitivity"], REPLAY_ONLY),
        "scope": (tuple(a["matched_timer_components"]), MATCHED_SCOPE),
        "gate": ((a["conservative_ratio_max"], a["overhead_multiplier"]),
                 (tc.MECHANISM_GATE["conservative_predicted_compile_ratio_max"],
                  tc.MECHANISM_GATE["replacement_and_extra_overhead_multiplier"])),
        "adapter": ((ad["stage"], ad["arm_id"], ad["mode_key"], ad["first_seed"],
                     ad["last_seed"], ad["repetitions"], ad["expected_rows"],
                     ad["order_seed"], ad["external_timeout_seconds"]),
                    (ADAPTER_STAGE, "adapter", "adapter", tc.DIAGNOSTIC[0], tc.DIAGNOSTIC[1],
                     3, ADAPTER_ROWS, tc.SEED_ARM_ORDER, tc.EXTERNAL_SECONDS)),
        "speedup": (p["corrected_kernel_speedup_median"], CORRECTED_SPEEDUP_MEDIAN),
        "dispositions": ((p["narrow_source_dispositions"][0]["before"],
                          p["narrow_source_dispositions"][0]["after"]),
                         (COMMON_BEFORE, COMMON_AFTER)),
        "inherited_rows": ({k: v for k, v in p["inherited_expected_rows"].items()},
                           {k: v for k, v in tc.EXPECTED_ROWS.items()
                            if k.startswith(("D_", "C_"))}),
        "confirmation": (tuple(p["inherited_confirmation_seeds"]), tc.CONFIRMATION),
        "confirmation_gate": (p["inherited_confirmation_gate"], tc.CONFIRMATION_GATE),
        "development_gate": (p["inherited_development_gate"], tc.DEVELOPMENT_GATE),
        "budget": ((p["combined_budget"]["measurement_wall_hours"],
                    p["combined_budget"]["active_development_hours"]),
                   (tc.WALL_CAP_HOURS, tc.DEV_CAP_HOURS)),
    }
    mismatches = {n: {"package": x, "module": y} for n, (x, y) in checks.items() if x != y}
    parent = tc.check_protocol_constants()
    return {"checked": len(checks), "mismatches": mismatches, "parent": parent,
            "status": "PASS" if checks and not mismatches and parent["status"] == "PASS"
            else "FAIL"}


def run_dir(suffix: Optional[str] = None) -> Path:
    return RESULTS / (RUN_NAME if suffix is None else f"{RUN_NAME}_{suffix}")


def fresh_run_dir() -> Path:
    candidate, n = run_dir(), 1
    while candidate.exists():
        n += 1
        candidate = run_dir(str(n))
    candidate.mkdir(parents=True)
    return candidate


# --------------------------------------------------------------------------
# Combined measurement budget (parent ledger + this run, no double counting)
# --------------------------------------------------------------------------


def combined_hours(run: Path) -> dict:
    parent = strict_rows(PARENT_RUN / "MEASUREMENT_WALL_LEDGER.jsonl")
    mine = strict_rows(Path(run) / "MEASUREMENT_WALL_LEDGER.jsonl")
    p = sum(float(r["process_seconds"]) for r in parent) / 3600
    m = sum(float(r["process_seconds"]) for r in mine) / 3600
    return {"parent_hours": p, "resume_hours": m, "total_hours": p + m,
            "parent_rows": len(parent), "resume_rows": len(mine)}


def cap_reached(run: Path) -> bool:
    return combined_hours(run)["total_hours"] >= tc.WALL_CAP_HOURS


# --------------------------------------------------------------------------
# Strict JSONL
# --------------------------------------------------------------------------


class StrictRowError(ValueError):
    pass


def _finite(value, where: str) -> None:
    if isinstance(value, float) and not math.isfinite(value):
        raise StrictRowError(f"non-finite number at {where}")
    if isinstance(value, dict):
        for k, v in value.items():
            _finite(v, f"{where}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _finite(v, f"{where}[{i}]")


def strict_rows(path: Path) -> List[dict]:
    """Every line must be one complete JSON object with finite numbers.

    A blank line, a malformed line or a trailing fragment (no final newline, or
    unparsable) raises: no torn material is silently ignored.
    """

    path = Path(path)
    if not path.exists():
        return []
    data = path.read_bytes()
    if data and not data.endswith(b"\n"):
        raise StrictRowError(f"{path}: final line has no newline (torn fragment)")
    rows = []
    for number, line in enumerate(data.decode("utf-8").split("\n")[:-1] if data else []):
        if not line.strip():
            raise StrictRowError(f"{path}:{number + 1}: blank line")
        try:
            row = json.loads(line, parse_constant=lambda c: (_ for _ in ()).throw(
                StrictRowError(f"{path}:{number + 1}: constant {c}")))
        except json.JSONDecodeError as exc:
            raise StrictRowError(f"{path}:{number + 1}: malformed ({exc})") from exc
        if not isinstance(row, dict):
            raise StrictRowError(f"{path}:{number + 1}: not an object")
        _finite(row, f"{path.name}:{number + 1}")
        rows.append(row)
    return rows


# --------------------------------------------------------------------------
# Runner with complete raw streams
# --------------------------------------------------------------------------


def run_stage(run: Path, stage: str, specs: Sequence[dict], module: str,
              timeout: float = tc.EXTERNAL_SECONDS) -> dict:
    out = Path(run) / "stages" / stage
    raw = out / "raw"
    raw.mkdir(parents=True, exist_ok=True)
    rows_path, attempts_path = out / "rows.jsonl", out / "ATTEMPTS.jsonl"
    keys = [tc.row_key(s) for s in specs]
    if len(set(keys)) != len(keys):
        raise RuntimeError(f"{stage}: duplicate keys in the plan")
    frozen = out / "EXPECTED_KEYS.json"
    if frozen.exists():
        if json.loads(frozen.read_text())["keys"] != keys:
            raise RuntimeError(f"{stage}: expected keys differ from the frozen list")
    else:
        oc.write_immutable_json(frozen, {"stage": stage, "count": len(keys), "keys": keys,
                                         "sha256": oc.object_sha256(keys)})
    done = {tc.row_key(r) for r in strict_rows(rows_path)}
    tried = {r["key"] for r in strict_rows(attempts_path)}
    for index, spec in enumerate(specs):
        key = tc.row_key(spec)
        if key in done:
            continue
        if key in tried:
            raise RuntimeError(f"{stage}: key {key} has an attempt but no row; lead review")
        if cap_reached(run):
            raise RuntimeError("combined measurement cap reached")
        argv = [oc.PYTHON, "-s", "-m", module, "--spec", json.dumps(spec, sort_keys=True)]
        oc.append_row(attempts_path, {"key": key, "index": index, "argv": argv,
                                      "started_utc": _utc()})
        started = time.perf_counter()
        timed_out = False
        try:
            proc = subprocess.run(argv, cwd=str(ROOT), capture_output=True, timeout=timeout,
                                  env=tc.worker_env())
            code, stdout, stderr = proc.returncode, proc.stdout, proc.stderr
        except subprocess.TimeoutExpired as exc:
            timed_out, code = True, None
            stdout, stderr = exc.stdout or b"", exc.stderr or b""
        seconds = time.perf_counter() - started
        (raw / f"{index:05d}.stdout").write_bytes(stdout)
        (raw / f"{index:05d}.stderr").write_bytes(stderr)
        tc.charge(run, stage, key, seconds)
        base = {k: spec[k] for k in tc.KEY_FIELDS + ("seed",)}
        base.update(process_seconds=seconds, exit_code=code, timed_out=timed_out,
                    raw_index=index, stdout_sha256=oc.sha256_bytes(stdout),
                    stderr_sha256=oc.sha256_bytes(stderr))
        oc.append_row(attempts_path, {"key": key, "index": index, "finished_utc": _utc(),
                                      "exit_code": code, "timed_out": timed_out,
                                      "process_seconds": seconds,
                                      "stdout_sha256": base["stdout_sha256"],
                                      "stderr_sha256": base["stderr_sha256"]})
        if timed_out or code != 0:
            oc.append_row(rows_path, dict(base, failed=True))
            continue
        try:
            result = json.loads(stdout)
            if not isinstance(result, dict):
                raise ValueError("stdout is not an object")
        except ValueError:
            oc.append_row(rows_path, dict(base, failed=True, stdout_not_json=True))
            continue
        oc.append_row(rows_path, dict(base, **result))
    return tc.check_rows(strict_rows(rows_path), keys)


def _utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def ordered(specs: List[dict]) -> List[dict]:
    """The parent's deterministic order key with the stage id of each spec."""

    return sorted(specs, key=lambda s: (tc.stable_seed([tc.SEED_ARM_ORDER, s["stage_id"],
                                                        s["program_sha256"], s["repetition"],
                                                        s["arm_id"], s["mode_key"]]),
                                        s["arm_id"], s["mode_key"]))
