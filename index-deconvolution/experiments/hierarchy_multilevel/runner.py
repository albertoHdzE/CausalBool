"""Parent-side execution: inputs, imported references, A0 jobs, augmentation jobs.

The owner watchdog machinery is reused, not copied: A0 jobs are the owner
``benchmark._Job`` with registry ``search-v2`` (the unchanged ``infer_v2`` worker) and
``benchmark._job_row``; augmentation jobs subclass ``_Job`` only to point at this
package's worker script and pass the A0 archive, checkpoint directory and lock.
At most two children are active; each has 30 s wall and 1 GiB RSS.

Augmentation status (one per job; ``validity`` decides evidence state):

  ok                         completed search (``stop_reason`` may be a normal work cap)
  watchdog_timeout_fallback  child killed at the wall limit; best parent-verified
  watchdog_rss_fallback      checkpoint, else A0, deployed (valid, search incomplete)
  invalid_decode_mismatch    a candidate failed the independent decoder (INVALID)
  invalid_checkpoint_corrupt a checkpoint's bytes disagree with its record or input
  invalid_crash              any other child failure
  invalid_lock               lock mismatch at the worker
  invalid_inconsistent       completed output disagrees with checkpoints/A0/input
  unavailable_baseline       A0 unavailable or invalid; job not launched (INCOMPLETE)
  (missing row)              never run (INCOMPLETE)

INVALID takes precedence over INCOMPLETE; neither yields a recommendation.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

from hierarchy import benchmark as B
from hierarchy.baselines import BASELINE_METHODS, select_best
from hierarchy.corpus import Case
from hierarchy.decode import decode_archive
from hierarchy.study import get_study

from .search import ARMS

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_multilevel_v1"
RUN_ID = "multilevel-feasibility-v1-r1"
RUN_DIR = ID_ROOT / "results" / "hierarchy_multilevel_v1" / RUN_ID
WORKER = Path(__file__).resolve().parent / "worker.py"
STUDY = "hierarchy-multilevel-v1"
WALL_S = 30.0
RSS = 1 << 30
MAX_CHILDREN = 2
AUG_ARMS = ("A1", "A2", "A3")
VALID_AUG = ("ok", "watchdog_timeout_fallback", "watchdog_rss_fallback")
REPRO_FIELDS = ("status", "archive_sha256", "archive_bits", "decode_ok", "selected_codec_id",
                "selected_method", "rule_count", "dag_depth", "candidate_count",
                "deterministic_work", "best_source", "trace", "config_sha256", "input_sha256",
                "n_bits", "search_counters")


def sha(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def write_json(path: Path, obj) -> None:
    B.atomic_write(path, (json.dumps(obj, indent=1, sort_keys=True) + "\n").encode())


def strip_wall(obj):
    """``search_counters`` with every key ending in ``wall_s`` removed recursively
    (``wall_s`` per stage and ``total_wall_s``)."""
    if isinstance(obj, dict):
        return {k: strip_wall(v) for k, v in obj.items() if not k.endswith("wall_s")}
    if isinstance(obj, list):
        return [strip_wall(v) for v in obj]
    return obj


# ---------------------------------------------------------------------------
# Inputs and imported references
# ---------------------------------------------------------------------------

def case_specs() -> list[dict]:
    return json.loads((PACKET / "CASES.json").read_text())["cases"]


def load_input(spec: dict) -> Case:
    """Decode the retained raw archive; validate its hash and the input hash and length."""
    ref = spec["references"]["raw"]
    data = (REPO / ref["archive_path"]).read_bytes()
    if sha(data) != ref["archive_sha256"]:
        raise ValueError(f"{spec['case_id']}: raw archive hash mismatch")
    bits = decode_archive(data)
    if sha(bits.encode("ascii")) != spec["input_sha256"] or len(bits) != spec["n_bits"]:
        raise ValueError(f"{spec['case_id']}: decoded input hash/length mismatch")
    return Case(spec["case_id"], "confirmation", spec["family"], spec["base_length"],
                spec["replicate"], spec["ragged"], bits)


def validate_references(spec: dict, bits: str) -> dict:
    """The nine saved baseline archives and the reconstructed portfolio minimum."""
    out = {"case_id": spec["case_id"], "methods": {}, "problems": []}
    arcs = {}
    for m in BASELINE_METHODS + ("hid_full", "baseline_best"):
        ref = spec["references"][m]
        data = (REPO / ref["archive_path"]).read_bytes()
        ok_hash = sha(data) == ref["archive_sha256"] and 8 * len(data) == ref["archive_bits"]
        ok_dec = decode_archive(data) == bits
        out["methods"][m] = {"archive_bits": 8 * len(data), "archive_sha256": sha(data),
                             "codec_id": data[4], "hash_ok": ok_hash, "decode_ok": ok_dec}
        if not (ok_hash and ok_dec):
            out["problems"].append(f"{m}: hash_ok={ok_hash} decode_ok={ok_dec}")
        if m in BASELINE_METHODS:
            arcs[m] = data
    best = select_best(arcs)
    minimum = min(len(a) for a in arcs.values())
    out["portfolio"] = {"selected_method": best, "archive_bits": 8 * len(arcs[best]),
                        "archive_sha256": sha(arcs[best]),
                        "methods_at_minimum": sorted(m for m, a in arcs.items() if len(a) == minimum),
                        "matches_saved_baseline_best":
                            sha(arcs[best]) == spec["references"]["baseline_best"]["archive_sha256"]}
    if not out["portfolio"]["matches_saved_baseline_best"]:
        out["problems"].append("portfolio reconstruction differs from saved baseline_best")
    return out


# ---------------------------------------------------------------------------
# A0 jobs (owner worker, owner row)
# ---------------------------------------------------------------------------

def a0_row_path(d: Path, case_id: str) -> Path:
    return d / "rows" / f"{case_id}.A0.json"


def aug_row_path(d: Path, case_id: str, arm: str) -> Path:
    return d / "rows" / f"{case_id}.{arm}.json"


def finish_a0(job, d: Path, lock_sha: str, spec: dict) -> dict:
    study = get_study("search-v2")
    from hierarchy.wire import encode_literal
    raw_bits = 8 * len(encode_literal(job.case.bits))
    row, _ = B._job_row(job, RUN_ID, lock_sha, raw_bits, study, WALL_S)
    row.update({"study": STUDY, "role": "exposed_baseline_reproduction",
                "rng_namespace": None, "evidence_role": "exposed_development",
                "lock_sha256": lock_sha, "arm": "A0", "arm_name": "k1"})
    saved = {r["method"]: r for r in json.loads((REPO / spec["source_rows_path"]).read_text())}
    old = saved["hid_full"]
    diffs = []
    for f in REPRO_FIELDS:
        a, b = row.get(f), old.get(f)
        if f == "search_counters":
            a, b = strip_wall(a), strip_wall(b)
        if a != b:
            diffs.append(f)
    row["reproduction"] = {"fields_compared": list(REPRO_FIELDS), "mismatched_fields": diffs,
                           "reproduced": not diffs,
                           "saved_row": spec["source_rows_path"],
                           "saved_worker_wall_ns_not_compared": old.get("worker_wall_ns")}
    write_json(a0_row_path(d, spec["case_id"]), row)
    return row


def a0_verified(d: Path, spec: dict, bits: str, lock_sha: str) -> tuple[bytes | None, dict | None, str]:
    """Parent verification of a persisted A0 before any use as incumbent."""
    p = a0_row_path(d, spec["case_id"])
    if not p.is_file():
        return None, None, "a0_row_missing"
    try:
        row = json.loads(p.read_text())
    except ValueError:
        return None, None, "a0_row_corrupt"
    if row.get("lock_sha256") != lock_sha:
        return None, row, "a0_row_other_lock"
    if row.get("status") != "ok" or not row.get("reproduction", {}).get("reproduced"):
        return None, row, "a0_not_ok_or_not_reproduced"
    ap = d / row["archive_path"]
    if not ap.is_file():
        return None, row, "a0_archive_missing"
    data = ap.read_bytes()
    if sha(data) != row["archive_sha256"] or row["input_sha256"] != sha(bits.encode()) \
            or row["n_bits"] != len(bits):
        return None, row, "a0_hash_or_input_mismatch"
    try:
        if decode_archive(data) != bits:
            return None, row, "a0_decode_mismatch"
    except Exception:  # noqa: BLE001 -- recorded as unusable
        return None, row, "a0_decode_error"
    return data, row, "ok"


# ---------------------------------------------------------------------------
# Augmentation jobs
# ---------------------------------------------------------------------------

class AugJob(B._Job):
    """Owner ``_Job`` (stdin feed, ``os.wait4`` watchdog, RSS from rusage) with this
    package's worker. ``extra_env`` is for watchdog fixtures only; the study passes {}."""

    def __init__(self, case, arm, d, a0_path: Path, lock_path: str, rss_limit: int = RSS,
                 extra_env: dict | None = None):
        self.arm, self.a0_path, self.lock_path = arm, a0_path, lock_path
        self.ckpt = d / "tmp" / f"{case.case_id}.{arm}.ckpt"
        if self.ckpt.exists():
            for f in self.ckpt.iterdir():
                f.unlink()
        self.extra_env = dict(extra_env or {})
        super().__init__(case, arm, d, registry="hierarchy-multilevel", rss_limit=rss_limit)

    def worker_argv(self, method: str) -> list[str]:
        envp = (["/usr/bin/env"] + [f"{k}={v}" for k, v in sorted(self.extra_env.items())]
                if self.extra_env else [])
        return envp + [sys.executable, "-S", "-B", str(WORKER), self.arm, str(self.a0_path),
                str(self.ckpt), str(self.tmp), self.lock_path, str(self.rss_limit)]


def launch_aug(case, arm, d, a0_path, lock_path, rss_limit=RSS, extra_env=None,
               fixture_wall: float | None = None) -> AugJob:
    job = AugJob(case, arm, d, a0_path, lock_path, rss_limit, extra_env)
    job.fixture_wall = fixture_wall
    return job


def read_checkpoints(ckpt: Path, bits: str, a0: bytes) -> dict:
    """Latest valid checkpoint (parent-verified), with corruption and partial writes
    reported. A record whose archive is missing is a partial write (ignored); an
    archive whose bytes disagree with its record, or do not decode to the input, or are
    not strictly shorter than A0 and every earlier checkpoint, is corruption."""
    out = {"valid": [], "partial": [], "corrupt": [], "best": None}
    if not ckpt.is_dir():
        return out
    prev = len(a0)
    for js in sorted(ckpt.glob("ckpt_*.json")):
        isd = js.with_suffix(".isd")
        try:
            rec = json.loads(js.read_text())
        except ValueError:
            out["corrupt"].append({"file": js.name, "reason": "unreadable_record"})
            continue
        if not isd.is_file():
            out["partial"].append({"file": js.name, "reason": "archive_missing"})
            continue
        data = isd.read_bytes()
        why = None
        if sha(data) != rec.get("archive_sha256") or 8 * len(data) != rec.get("archive_bits"):
            why = "bytes_disagree_with_record"
        else:
            try:
                if decode_archive(data) != bits:
                    why = "does_not_decode_to_input"
            except Exception as exc:  # noqa: BLE001
                why = f"decoder_error:{type(exc).__name__}"
        if why is None and len(data) >= prev:
            why = "not_strictly_shorter_than_previous"
        if why:
            out["corrupt"].append({"file": js.name, "reason": why})
            continue
        prev = len(data)
        out["valid"].append({"file": js.name, "seq": rec["seq"], "archive_bits": 8 * len(data),
                             "archive_sha256": sha(data), "source": rec})
        out["best"] = data
    out["orphan_archives"] = sorted(p.name for p in ckpt.glob("ckpt_*.isd")
                                    if not p.with_suffix(".json").is_file())
    out["partial_tmp_files"] = sorted(p.name for p in ckpt.glob(".*tmp*"))
    return out


def finish_aug(job: AugJob, d: Path, lock_sha: str, a0: bytes, a0_row: dict) -> dict:
    case, res = job.case, job.done
    bits = case.bits
    row = {"run_id": RUN_ID, "study": STUDY, "lock_sha256": lock_sha, "case_id": case.case_id,
           "family": case.family, "base_length": case.base_length, "replicate": case.replicate,
           "ragged": case.ragged, "n_bits": len(bits), "input_sha256": sha(bits.encode()),
           "arm": job.arm, "arm_name": ARMS[job.arm].name, "config_sha256": ARMS[job.arm].sha256(),
           "status": None, "validity": None, "search_complete": False, "archive_path": None,
           "archive_sha256": None, "archive_bits": None, "decode_ok": None,
           "selected": None, "counters": None, "stop_reason": None, "trace_path": None,
           "trace_sha256": None, "exception": None, "stderr_log": None,
           "worker_wall_ns": res["worker_wall_ns"], "peak_rss_bytes": res["peak_rss_bytes"],
           "rss_method": B.RSS_METHOD, "encode_wall_ns": None, "exit": res["exit"],
           "timed_out": res["timed_out"],
           "a0_archive_sha256": a0_row["archive_sha256"], "a0_archive_bits": a0_row["archive_bits"],
           "a0_worker_wall_ns": a0_row["worker_wall_ns"], "a0_peak_rss_bytes": a0_row["peak_rss_bytes"],
           "deployment_wall_ns": None, "deployment_peak_rss_bytes": None, "checkpoints": None,
           "watchdog_limits": {"wall_s": WALL_S, "rss_bytes": job.rss_limit},
           "fixture_env": sorted(job.extra_env)}
    errtext = job.err.read_bytes().decode("utf-8", "replace") if job.err.exists() else ""
    ck = read_checkpoints(job.ckpt, bits, a0)
    row["checkpoints"] = {k: v for k, v in ck.items() if k != "best"}
    archive = None
    if res["timed_out"] or res["exit"] == B.RSS_EXIT:
        row["status"] = "watchdog_timeout_fallback" if res["timed_out"] else "watchdog_rss_fallback"
        archive = ck["best"] if ck["best"] is not None else a0
        row["selected"] = ({**ck["valid"][-1]["source"], "source": "checkpoint"}
                           if ck["best"] is not None else {"source": "A0"})
        row["exception"] = ("worker exceeded wall limit" if res["timed_out"]
                            else "worker exceeded RSS limit")
        if ck["corrupt"]:
            row["status"] = "invalid_checkpoint_corrupt"
    elif res["exit"] != 0:
        lines = [ln for ln in errtext.strip().splitlines() if ln.strip()]
        row["exception"] = (lines[-1] if lines else f"exit {res['exit']}")[:2000]
        row["status"] = {3: "invalid_decode_mismatch", 4: "invalid_lock",
                         5: "invalid_crash"}.get(res["exit"], "invalid_crash")
        if ck["corrupt"]:
            row["status"] = "invalid_checkpoint_corrupt"
        archive = a0                      # the parent still preserves A0 as deployed output
    else:
        try:
            archive = job.tmp.read_bytes()
            info = json.loads(res["stdout"].decode() or "{}")
            trace = Path(str(job.tmp) + ".trace.json").read_bytes()
        except (OSError, ValueError) as exc:
            row["status"], row["exception"] = "invalid_crash", f"{type(exc).__name__}: {exc}"
            archive = a0
        else:
            row["status"] = "ok"
            row["search_complete"] = True
            row["encode_wall_ns"] = info.get("encode_wall_ns")
            row["selected"] = info.get("selected")
            row["counters"] = info.get("counters")
            row["stop_reason"] = info.get("stop_reason")
            rel = f"traces/{case.case_id}.{job.arm}.json"
            B.atomic_write(d / rel, trace)
            row["trace_path"], row["trace_sha256"] = rel, sha(trace)
            last = ck["valid"][-1]["archive_sha256"] if ck["valid"] else a0_row["archive_sha256"]
            problems = []
            if ck["corrupt"]:
                row["status"] = "invalid_checkpoint_corrupt"
            if sha(archive) != last:
                problems.append("final archive differs from the last checkpoint/A0")
            if len(archive) > len(a0):
                problems.append("final archive longer than A0")
            if info.get("checkpoints") != len(ck["valid"]):
                problems.append("checkpoint count differs")
            if problems and row["status"] == "ok":
                row["status"], row["exception"] = "invalid_inconsistent", "; ".join(problems)
    if archive is not None:
        try:
            ok = decode_archive(archive) == bits
        except Exception:  # noqa: BLE001
            ok = False
        row["decode_ok"] = ok
        if not ok:
            row["status"] = "invalid_decode_mismatch"
        rel, h = B.store_archive(d, archive)
        row["archive_path"], row["archive_sha256"], row["archive_bits"] = rel, h, 8 * len(archive)
    row["validity"] = "valid" if row["status"] in VALID_AUG else "invalid"
    row["search_complete"] = row["status"] == "ok"
    row["deployment_wall_ns"] = a0_row["worker_wall_ns"] + res["worker_wall_ns"]
    row["deployment_peak_rss_bytes"] = max(a0_row["peak_rss_bytes"] or 0, res["peak_rss_bytes"] or 0)
    if errtext.strip() and row["validity"] == "invalid" or row["status"].startswith("watchdog"):
        log = d / "logs" / "stderr" / f"{case.case_id}.{job.arm}.log"
        B.atomic_write(log, errtext.encode())
        row["stderr_log"] = str(log.relative_to(d))
    partial = job.ckpt / "views.jsonl"
    if partial.is_file() and not row["search_complete"]:
        data = partial.read_bytes()
        rel = f"traces/partial/{case.case_id}.{job.arm}.views.jsonl"
        B.atomic_write(d / rel, data)
        row["partial_views_path"], row["partial_views_sha256"] = rel, sha(data)
    write_json(aug_row_path(d, case.case_id, job.arm), row)
    for p in (job.tmp, job.err, Path(str(job.tmp) + ".trace.json")):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    return row


def unavailable_row(d: Path, spec: dict, arm: str, lock_sha: str, reason: str) -> dict:
    row = {"run_id": RUN_ID, "study": STUDY, "lock_sha256": lock_sha, "case_id": spec["case_id"],
           "family": spec["family"], "base_length": spec["base_length"],
           "replicate": spec["replicate"], "ragged": spec["ragged"], "n_bits": spec["n_bits"],
           "input_sha256": spec["input_sha256"], "arm": arm, "arm_name": ARMS[arm].name,
           "config_sha256": ARMS[arm].sha256(), "status": "unavailable_baseline",
           "validity": "unavailable", "search_complete": False, "archive_path": None,
           "archive_sha256": None, "archive_bits": None, "exception": reason}
    write_json(aug_row_path(d, spec["case_id"], arm), row)
    return row


def aug_row_valid_for_resume(d: Path, spec: dict, arm: str, lock_sha: str) -> bool:
    p = aug_row_path(d, spec["case_id"], arm)
    try:
        row = json.loads(p.read_text())
    except (OSError, ValueError):
        return False
    if row.get("lock_sha256") != lock_sha or row.get("status") not in VALID_AUG + (
            "invalid_decode_mismatch", "invalid_checkpoint_corrupt", "invalid_crash",
            "invalid_lock", "invalid_inconsistent"):
        return False
    ap = d / (row.get("archive_path") or "")
    return ap.is_file() and sha(ap.read_bytes()) == row.get("archive_sha256")


# ---------------------------------------------------------------------------
# Queue
# ---------------------------------------------------------------------------

def run_queue(jobs, launch, finish, log, budget_ok, poll_s: float = 0.02) -> dict:
    """Run ``jobs`` (in order) with at most two children; ``budget_ok()`` is consulted
    before every launch, and a refusal leaves the remaining jobs unlaunched."""
    pending = list(jobs)
    active = []
    launched = finished = 0
    refused = None
    while pending or active:
        while pending and len(active) < MAX_CHILDREN and refused is None:
            ok, why = budget_ok()
            if not ok:
                refused = why
                log(f"budget refusal: {why}; {len(pending)} jobs left unlaunched")
                break
            spec = pending.pop(0)
            job = launch(spec)
            launched += 1
            if job is None:
                finished += 1
                continue
            active.append((spec, job))
        if refused is not None and not active:
            break
        still = []
        for spec, job in active:
            if job.poll(WALL_S if not getattr(job, "fixture_wall", None) else job.fixture_wall):
                finish(spec, job)
                finished += 1
            else:
                still.append((spec, job))
        active = still
        if active:
            time.sleep(poll_s)
    return {"launched": launched, "finished": finished, "unlaunched": len(pending),
            "budget_refusal": refused}


def env_summary() -> dict:
    return {"pid": os.getpid(), "python": sys.executable}
