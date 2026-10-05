"""Diagnostic job runner: reuses the existing process, watchdog, archive store and budget.

  DiagJob        ``hierarchy.benchmark._Job`` with only ``worker_argv`` overridden (the
                 Popen, stdin feed, ``os.wait4`` polling, wall kill and ru_maxrss are the
                 owner's); the worker is ``worker.py`` under ``python -S``.
  run_jobs       at most two concurrent workers, 30 s / 1 GiB each, jobs in the given
                 (case-id) order; one durable record per job; resume skips a record only
                 when its identity, kind, parameters and input hash are identical.
  budget         ``hierarchy.benchmark.CategoryBudget`` over this phase's own
                 ``execution_ledger.jsonl`` (never the accepted study's).

Timeouts, RSS breaches, worker errors and decode failures are explicit records; an
unfinished job at budget exhaustion is written as ``not_run``.
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from hierarchy.benchmark import (RSS_EXIT, CategoryBudget, _Job, atomic_write,
                                 sha256_file, store_archive)
from hierarchy.decode import decode_archive

from .common import RESULT_ROOT, RUN_DIR, RUN_ID, canonical_sha, utc

WORKER = Path(__file__).resolve().parent / "worker.py"
WALL_LIMIT_S = 30.0
RSS_LIMIT = 1 << 30
MAX_WORKERS = 2
ALLOWANCES = {"fixtures_development": 1800, "diagnostic_jobs": 10800,
              "report_verification": 1800}


def phase_study(result_root: Path = RESULT_ROOT):
    """The two attributes ``CategoryBudget`` reads, bound to this phase's result root."""
    return SimpleNamespace(name="search-diagnosis-v1", result_root=result_root,
                           resources=SimpleNamespace(allowance=ALLOWANCES.get))


class DiagJob(_Job):
    def __init__(self, case, kind: str, d: Path, params: dict, rss_limit: int = RSS_LIMIT):
        self.kind, self.params = kind, params
        super().__init__(case, kind, d, registry="search-diagnosis", rss_limit=rss_limit)

    def worker_argv(self, method: str) -> list[str]:
        return [sys.executable, "-S", str(WORKER), self.kind, str(self.tmp),
                json.dumps(self.params, sort_keys=True), str(self.rss_limit)]


def record_path(d: Path, section: str, cid: str, kind: str) -> Path:
    return d / "jobs" / section / f"{cid}.{kind}.json"


def _identity_key(identity_sha: str, case, kind: str, params: dict) -> dict:
    return {"identity_sha256": identity_sha, "case_id": case.case_id,
            "input_sha256": case.input_sha256, "kind": kind,
            "params_sha256": canonical_sha(params)}


def record_complete(p: Path, key: dict) -> bool:
    if not p.exists():
        return False
    rec = json.loads(p.read_text())
    if any(rec.get(k) != v for k, v in key.items()):
        raise RuntimeError(f"{p} was written under a different identity/input/parameters; "
                           "a repaired implementation needs a new attempt id")
    if rec["status"] == "not_run":
        return False
    for a in rec.get("archives", {}).values():
        f = p.parents[2] / a["path"]
        if not f.exists() or sha256_file(f) != a["sha256"]:
            return False
    return True


def finish_record(job: DiagJob, key: dict, section: str, attempt: str, d: Path) -> dict:
    res = job.done
    rec = dict(key, section=section, attempt_id=attempt, finished_utc=utc(),
               worker_wall_ns=res["worker_wall_ns"], peak_rss_bytes=res["peak_rss_bytes"],
               wall_limit_s=WALL_LIMIT_S, rss_limit_bytes=job.rss_limit, exit=res["exit"],
               status=None, info=None, archives={}, exception=None)
    err = job.err.read_bytes().decode("utf-8", "replace") if job.err.exists() else ""
    if res["timed_out"]:
        rec["status"], rec["exception"] = "timeout", f"worker exceeded {WALL_LIMIT_S} s"
    elif res["exit"] == RSS_EXIT:
        rec["status"], rec["exception"] = "rss_limit", f"worker exceeded {job.rss_limit} bytes"
    elif res["exit"] != 0:
        lines = [ln for ln in err.strip().splitlines() if ln.strip()]
        rec["status"], rec["exception"] = "error", (lines[-1] if lines else f"exit {res['exit']}")
    else:
        try:
            out = json.loads(job.tmp.read_text())
        except (OSError, ValueError) as exc:
            rec["status"], rec["exception"] = "error", f"{type(exc).__name__}: {exc}"
        else:
            rec["status"], rec["info"] = "ok", out["info"]
            rec["compute_wall_ns"] = out["compute_wall_ns"]
            for name, hx in out["archives"].items():
                arc = bytes.fromhex(hx)
                ok = decode_archive(arc) == job.case.bits      # parent-side check as well
                rel, h = store_archive(d, arc)
                rec["archives"][name] = {"path": rel, "sha256": h, "bits": 8 * len(arc),
                                         "decode_ok": ok}
                if not ok:
                    rec["status"], rec["exception"] = "error", f"wrong_decode:{name}"
    if err.strip() and rec["status"] != "ok":
        log = d / "logs" / "stderr" / f"{job.case.case_id}.{job.kind}.log"
        atomic_write(log, err.encode())
        rec["stderr_log"] = str(log.relative_to(d))
    for p in (job.tmp, job.err):
        try:
            p.unlink()
        except FileNotFoundError:
            pass
    return rec


def run_jobs(jobs, section: str, identity_sha: str, attempt: str, d: Path = RUN_DIR,
             budget: CategoryBudget | None = None, log=print, job_class=DiagJob,
             wall_limit: float = WALL_LIMIT_S, rss_limit: int = RSS_LIMIT) -> dict:
    """``jobs``: iterable of (case, kind, params) in the fixed order."""
    stats = {"done": 0, "skipped": 0, "not_run": 0, "non_ok": 0}
    queue = []
    for case, kind, params in jobs:
        key = _identity_key(identity_sha, case, kind, params)
        if record_complete(record_path(d, section, case.case_id, kind), key):
            stats["skipped"] += 1
        else:
            queue.append((case, kind, params, key))
    running: list[tuple[DiagJob, dict]] = []
    stop = False
    while queue or running:
        if budget is not None and budget.expired():
            stop = True
        while not stop and queue and len(running) < MAX_WORKERS:
            case, kind, params, key = queue.pop(0)
            running.append((job_class(case, kind, d, params, rss_limit), key))
        if not running:
            break
        time.sleep(0.005)
        for job, key in list(running):
            if job.poll(wall_limit):
                running.remove((job, key))
                rec = finish_record(job, key, section, attempt, d)
                atomic_write(record_path(d, section, job.case.case_id, job.kind),
                             json.dumps(rec, sort_keys=True).encode())
                stats["done"] += 1
                if rec["status"] != "ok":
                    stats["non_ok"] += 1
                    log(f"{section} {job.case.case_id} {job.kind}: {rec['status']}")
                if budget is not None:
                    budget.save()
    for case, kind, params, key in queue:                # budget exhausted: explicit records
        rec = dict(key, section=section, attempt_id=attempt, status="not_run",
                   exception="diagnostic_jobs allowance exhausted", archives={})
        atomic_write(record_path(d, section, case.case_id, kind),
                     json.dumps(rec, sort_keys=True).encode())
        stats["not_run"] += 1
    return stats


def charge(category: str, job: str, seconds: float, root: Path = RESULT_ROOT) -> None:
    """Append an explicit charge (development/report time measured outside a runner)."""
    p = root / "execution_ledger.jsonl"
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "a") as fh:
        fh.write(json.dumps({"utc": utc(), "category": category, "job": job,
                             "run_id": RUN_ID, "seconds": seconds}) + "\n")


def used(category: str | None = None, root: Path = RESULT_ROOT) -> float:
    return CategoryBudget.category_used(phase_study(root), category)
