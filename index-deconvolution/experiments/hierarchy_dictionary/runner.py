"""Parent-side execution: inputs, imported references and old A3, A0 jobs, augmentation.

Reused, not copied: inputs, reference validation (864 constituents + 96 portfolio
minima by the owner tie rule), A0 verification, checkpoint reading, resume validation
and the two-child queue are the multilevel-v1 runner functions (they are parameterised
by the run directory and pinned to the same CASES.json). A0 jobs are the owner
``benchmark._Job`` with registry ``search-v2`` and the owner ``_job_row``; augmentation
jobs subclass the multilevel ``AugJob`` only to launch this package's worker.

Augmentation status (one per job; ``validity`` decides evidence state):

  ok                         completed search (``stop_reason`` may be a normal work cap)
  watchdog_timeout_fallback  child killed at the wall limit; best parent-verified
  watchdog_rss_fallback      checkpoint, else A0, deployed (valid, search incomplete)
  invalid_decode_mismatch    a candidate failed the decoder or a mode word check (INVALID)
  invalid_checkpoint_corrupt a checkpoint's bytes disagree with its record or input
  invalid_crash              any other child failure
  invalid_lock               lock mismatch at the worker
  invalid_inconsistent       completed output disagrees with checkpoints/A0/input/side files
  unavailable_baseline       A0 unavailable or invalid; job not launched (INCOMPLETE)
  (missing row)              never run (INCOMPLETE)

INVALID takes precedence over INCOMPLETE; neither yields a recommendation.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hierarchy import benchmark as B
from hierarchy.decode import decode_archive
from hierarchy.study import get_study
from hierarchy.wire import encode_literal
from hierarchy_multilevel import runner as ML
from hierarchy_multilevel.runner import (MAX_CHILDREN, REPRO_FIELDS, RSS, WALL_S, a0_row_path,
                                         a0_verified, aug_row_path, aug_row_valid_for_resume,
                                         case_specs, load_input, read_checkpoints, run_queue,
                                         sha, strip_wall, validate_references, write_json)

from .search import ARMS

ID_ROOT = Path(__file__).resolve().parents[2]
REPO = ID_ROOT.parent
PACKET = ID_ROOT / "protocols" / "hierarchy_dictionary_v1"
CASES = ML.PACKET / "CASES.json"
RUN_ID = "dictionary-feasibility-v1-r1"
RUN_DIR = ID_ROOT / "results" / "hierarchy_dictionary_v1" / RUN_ID
WORKER = Path(__file__).resolve().parent / "worker.py"
STUDY = "hierarchy-dictionary-v1"
AUG_ARMS = ("D0", "D1", "D2")
VALID_AUG = ("ok", "watchdog_timeout_fallback", "watchdog_rss_fallback")

__all__ = ["MAX_CHILDREN", "WALL_S", "RSS", "a0_verified", "aug_row_valid_for_resume",
           "case_specs", "load_input", "read_checkpoints", "run_queue", "validate_references",
           "write_json", "sha", "a0_row_path", "aug_row_path"]


# ---------------------------------------------------------------------------
# A0 jobs (owner worker, owner row)
# ---------------------------------------------------------------------------

def finish_a0(job, d: Path, lock_sha: str, spec: dict) -> dict:
    study = get_study("search-v2")
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
                           "reproduced": not diffs, "saved_row": spec["source_rows_path"],
                           "saved_worker_wall_ns_not_compared": old.get("worker_wall_ns")}
    write_json(a0_row_path(d, spec["case_id"]), row)
    return row


# ---------------------------------------------------------------------------
# Augmentation jobs
# ---------------------------------------------------------------------------

class DictAugJob(ML.AugJob):
    """The multilevel ``AugJob`` (owner ``_Job`` stdin feed, ``os.wait4`` watchdog, RSS
    from rusage, checkpoint directory) launching this package's worker."""

    def worker_argv(self, method: str) -> list[str]:
        envp = (["/usr/bin/env"] + [f"{k}={v}" for k, v in sorted(self.extra_env.items())]
                if self.extra_env else [])
        return envp + [sys.executable, "-S", "-B", str(WORKER), self.arm, str(self.a0_path),
                       str(self.ckpt), str(self.tmp), self.lock_path, str(self.rss_limit)]


def launch_aug(case, arm, d, a0_path, lock_path, rss_limit=RSS, extra_env=None,
               fixture_wall: float | None = None) -> DictAugJob:
    job = DictAugJob(case, arm, d, a0_path, lock_path, rss_limit, extra_env)
    job.fixture_wall = fixture_wall
    return job


def _store_candidates(d: Path, data: bytes, bits: str) -> tuple[list[str], list[str]]:
    """Store every retained candidate archive content-addressed; returns (hashes, problems).
    Bytes are verified against their hash; they were decoded in the worker (or are A0)."""
    stored, problems = [], []
    for h, hx in sorted(json.loads(data.decode()).items()):
        arc = bytes.fromhex(hx)
        if sha(arc) != h:
            problems.append(f"candidate {h[:12]} bytes disagree with hash")
            continue
        B.store_archive(d, arc)
        stored.append(h)
    return stored, problems


def finish_aug(job: DictAugJob, d: Path, lock_sha: str, a0: bytes, a0_row: dict) -> dict:
    case, res = job.case, job.done
    bits = case.bits
    row = {"run_id": RUN_ID, "study": STUDY, "lock_sha256": lock_sha, "case_id": case.case_id,
           "family": case.family, "base_length": case.base_length, "replicate": case.replicate,
           "ragged": case.ragged, "n_bits": len(bits), "input_sha256": sha(bits.encode()),
           "arm": job.arm, "arm_name": ARMS[job.arm].name, "modes": list(ARMS[job.arm].modes),
           "config_sha256": ARMS[job.arm].sha256(),
           "status": None, "validity": None, "search_complete": False, "archive_path": None,
           "archive_sha256": None, "archive_bits": None, "decode_ok": None,
           "selected": None, "counters": None, "stop_reason": None, "trace_path": None,
           "trace_sha256": None, "candidate_archives": None, "exception": None, "stderr_log": None,
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
    for v in ck["valid"]:                     # checkpoint archives are retained evidence
        B.store_archive(d, (job.ckpt / v["file"]).with_suffix(".isd").read_bytes())
    archive = None
    cands_path = Path(str(job.tmp) + ".cands.json")
    trace_path = Path(str(job.tmp) + ".trace.json")
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
            trace = trace_path.read_bytes()
            cands = cands_path.read_bytes()
        except (OSError, ValueError) as exc:
            row["status"], row["exception"] = "invalid_crash", f"{type(exc).__name__}: {exc}"
            archive = a0
        else:
            row["status"] = "ok"
            row["encode_wall_ns"] = info.get("encode_wall_ns")
            row["selected"] = info.get("selected")
            row["counters"] = info.get("counters")
            row["stop_reason"] = info.get("stop_reason")
            rel = f"traces/{case.case_id}.{job.arm}.json"
            B.atomic_write(d / rel, trace)
            row["trace_path"], row["trace_sha256"] = rel, sha(trace)
            stored, cprob = _store_candidates(d, cands, bits)
            row["candidate_archives"] = stored
            last = ck["valid"][-1]["archive_sha256"] if ck["valid"] else a0_row["archive_sha256"]
            problems = list(cprob)
            if ck["corrupt"]:
                row["status"] = "invalid_checkpoint_corrupt"
            if sha(archive) != last:
                problems.append("final archive differs from the last checkpoint/A0")
            if len(archive) > len(a0):
                problems.append("final archive longer than A0")
            if info.get("checkpoints") != len(ck["valid"]):
                problems.append("checkpoint count differs")
            if sha(archive) not in stored:
                problems.append("final archive missing from the candidate side file")
            if problems and row["status"] == "ok":
                row["status"], row["exception"] = "invalid_inconsistent", "; ".join(problems)
    if archive is not None:
        try:
            ok = decode_archive(archive) == bits
        except Exception:  # noqa: BLE001 -- recorded as a wrong decode
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
    for p in (job.tmp, job.err, trace_path, cands_path):
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


# ---------------------------------------------------------------------------
# Imported old A3 (multilevel-v1), validated, never rerun
# ---------------------------------------------------------------------------

def old_a3_records() -> dict:
    recs = json.loads((PACKET / "PREVIOUS_A3.json").read_text())["records"]
    return {r["case_id"]: r for r in recs}


def import_old_a3(rec: dict, bits: str) -> dict:
    """Hash-checked old A3 row, archive and trace; decode check; view eligibility mask and
    per-view proposal archive hashes for the D0 nesting comparison."""
    out = {"case_id": rec["case_id"], "problems": []}
    row_b = (REPO / rec["row_path"]).read_bytes()
    arc = (REPO / rec["archive_path"]).read_bytes()
    tr_b = (REPO / rec["trace_path"]).read_bytes()
    for what, data, h in (("row", row_b, rec["row_sha256"]), ("archive", arc, rec["archive_sha256"]),
                          ("trace", tr_b, rec["trace_sha256"])):
        if sha(data) != h:
            out["problems"].append(f"{what} hash")
    row, tr = json.loads(row_b), json.loads(tr_b)
    if decode_archive(arc) != bits:
        out["problems"].append("archive does not decode to the input")
    if row.get("archive_sha256") != sha(arc) or row.get("status") != "ok":
        out["problems"].append("row disagrees with archive or is not ok")
    out.update({"archive_bits": 8 * len(arc), "archive_sha256": sha(arc),
                "status": row.get("status"), "search_complete": row.get("search_complete"),
                "a0_archive_sha256": row.get("a0_archive_sha256"),
                "selected_source": (row.get("selected") or {}).get("source"),
                "view_mask": {f"{v['level']}-{v['width']}-{v['origin']}": v["status"]
                              for v in tr["views"]},
                "evaluated_view_proposals": {
                    f"{v['level']}-{v['width']}-{v['origin']}":
                        [[p["proposal"], p["status"], p["archive_sha256"]] for p in v["proposals"]]
                    for v in tr["views"] if v["status"] == "EVALUATED"}})
    return out
