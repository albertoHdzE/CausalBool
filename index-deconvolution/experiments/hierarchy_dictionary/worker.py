"""Augmentation child (thin adapter around ``search.augment``).

    python -S -B worker.py ARM A0_PATH CKPT_DIR OUT_PATH LOCK_PATH|- [RSS_LIMIT]

Launched by the owner ``benchmark._Job`` machinery (PYTHONPATH = index-deconvolution and
src only, ``-S``: no site .pth). Input bits on stdin. Exit codes: 0 complete; 3 decode
or expansion mismatch (INVALID); 4 lock mismatch or forbidden fixture hook under a lock;
5 unusable A0; 86 RSS (owner watchdog); anything else is a crash. Every strict
improvement is checkpointed as ``ckpt_NNNN.isd`` then ``ckpt_NNNN.json`` (atomic each);
every final view record is appended to ``views.jsonl``. On completion the trace
(``OUT.trace.json``) and the retained candidate archives (``OUT.cands.json``: sha256 ->
hex) are written before the archive itself. Fixture hooks (``HDD_FIXTURE_*``) exist for
the watchdog fixtures only and are refused whenever a lock is supplied.
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
from pathlib import Path

HERE = Path(__file__).resolve()
sys.path.insert(0, str(HERE.parents[1]))           # index-deconvolution/experiments

from hierarchy.benchmark import RSS_LIMIT_BYTES, _rss_watch, atomic_write  # noqa: E402
from hierarchy.segmentation import DecodeMismatch  # noqa: E402

from hierarchy_dictionary.search import ARMS, BaselineUnusable, augment  # noqa: E402

EXIT_DECODE, EXIT_LOCK, EXIT_A0 = 3, 4, 5
REPO = HERE.parents[3]
PREFIX = "HDD_FIXTURE_"


def check_lock(lock_path: str) -> list[str]:
    lock = json.loads(Path(lock_path).read_text())
    bad = [p for p, h in lock["closure"].items()
           if not (REPO / p).is_file() or hashlib.sha256((REPO / p).read_bytes()).hexdigest() != h]
    mods = {m: getattr(sys.modules[m], "__file__", None) for m in list(sys.modules)
            if m.split(".")[0] in ("hierarchy", "hierarchy_multilevel", "hierarchy_dictionary")}
    id_root = str(REPO / "index-deconvolution")
    bad += [f"import {m} from {f}" for m, f in mods.items() if f and not f.startswith(id_root)]
    return bad


def main(argv: list[str]) -> int:
    arm, a0_path, ckpt_dir, out_path, lock_path = argv[:5]
    rss = int(argv[5]) if len(argv) > 5 else RSS_LIMIT_BYTES
    threading.Thread(target=_rss_watch, args=(rss,), daemon=True).start()
    hooks = {k: v for k, v in os.environ.items() if k.startswith(PREFIX)}
    if lock_path != "-":
        problems = check_lock(lock_path) + [f"fixture hook {k} under a lock" for k in hooks]
        if problems:
            sys.stderr.write("LockMismatch: " + "; ".join(problems[:20]) + "\n")
            return EXIT_LOCK
    bits = sys.stdin.read()
    a0 = Path(a0_path).read_bytes()
    ck = Path(ckpt_dir)
    ck.mkdir(parents=True, exist_ok=True)
    seq = [0]
    stall_after = int(hooks.get(PREFIX + "STALL_AFTER_CHECKPOINTS", "-1"))
    crash_after = int(hooks.get(PREFIX + "CRASH_AFTER_CHECKPOINTS", "-1"))
    corrupt = hooks.get(PREFIX + "CORRUPT_CHECKPOINT") == "1"
    views_fh = open(ck / "views.jsonl", "a")

    def on_improve(arc: bytes, rec: dict) -> None:
        seq[0] += 1
        stem = ck / f"ckpt_{seq[0]:04d}"
        atomic_write(stem.with_suffix(".isd"), arc[:-1] + bytes([arc[-1] ^ 1]) if corrupt else arc)
        atomic_write(stem.with_suffix(".json"),
                     json.dumps(dict(rec, seq=seq[0]), sort_keys=True).encode())
        if seq[0] == crash_after:
            raise RuntimeError("fixture crash after checkpoint")
        if seq[0] == stall_after:
            while True:
                time.sleep(1)

    def on_view(rec: dict) -> None:
        views_fh.write(json.dumps({k: rec[k] for k in ("view_index", "level", "width", "origin",
                                                       "status")}, sort_keys=True) + "\n")
        views_fh.flush()

    t0 = time.perf_counter_ns()
    try:
        res = augment(bits, ARMS[arm], a0, on_improve, on_view)
    except DecodeMismatch as exc:
        sys.stderr.write(f"DecodeMismatch: {exc}\n")
        return EXIT_DECODE
    except BaselineUnusable as exc:
        sys.stderr.write(f"BaselineUnusable: {exc}\n")
        return EXIT_A0
    t1 = time.perf_counter_ns()
    trace = {"arm": arm, "config_name": res.config_name, "config_sha256": res.config_sha256,
             "selected": res.selected, "counters": res.counters, "stop_reason": res.stop_reason,
             "views": res.views}
    atomic_write(Path(out_path + ".trace.json"),
                 json.dumps(trace, sort_keys=True, separators=(",", ":")).encode())
    atomic_write(Path(out_path + ".cands.json"),
                 json.dumps({h: a.hex() for h, a in sorted(res.candidates.items())}).encode())
    atomic_write(Path(out_path), res.archive)
    sys.stdout.write(json.dumps({"encode_wall_ns": t1 - t0, "checkpoints": seq[0],
                                 "stop_reason": res.stop_reason, "selected": res.selected,
                                 "counters": res.counters}))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
