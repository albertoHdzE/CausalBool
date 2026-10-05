"""Controller wall-span ledger (PROTOCOL section 4): development, benchmark,
report_verification. One durable event stream ``<run>/ledger/resource_events.jsonl``.
A category's charge is the sum of its closed spans plus the open span to now. Spans
never overlap. The v3a ledger is not reused: its categories and run are hard-wired.

    PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m hierarchy_multilevel.ledger \
        start|stop CATEGORY NOTE | status
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ID_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ID_ROOT / "results" / "hierarchy_multilevel_v1" / "multilevel-feasibility-v1-r1"
LEDGER = RUN_DIR / "ledger" / "resource_events.jsonl"
CAPS = {"development": 10800.0, "benchmark": 7200.0, "report_verification": 3600.0}
TOTAL = 21600.0
REPORT_STOP_OPTIONAL = 3000.0
REPORT_STOP_EXECUTOR = 3300.0


def events(path: Path = LEDGER) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(x) for x in path.read_text().splitlines() if x.strip()]


def _append(ev: dict, path: Path = LEDGER) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    ev = dict(ev, utc=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    with open(path, "a") as fh:
        fh.write(json.dumps(ev, sort_keys=True) + "\n")
        fh.flush()
        os.fsync(fh.fileno())


def state(path: Path = LEDGER, now: float | None = None) -> dict:
    now = time.time() if now is None else now
    used = {c: 0.0 for c in CAPS}
    open_cat, open_t = None, None
    for e in events(path):
        if e["event"] == "start":
            if open_cat is not None:
                raise RuntimeError(f"ledger: {e['category']} started while {open_cat} open")
            open_cat, open_t = e["category"], e["t"]
        elif e["event"] == "stop":
            if e["category"] != open_cat:
                raise RuntimeError(f"ledger: stop {e['category']} while {open_cat} open")
            used[open_cat] += e["t"] - open_t
            open_cat, open_t = None, None
    if open_cat is not None:
        used[open_cat] += now - open_t
    return {"used_s": {k: round(v, 1) for k, v in used.items()},
            "remaining_s": {k: round(CAPS[k] - used[k], 1) for k in CAPS},
            "total_used_s": round(sum(used.values()), 1), "total_cap_s": TOTAL,
            "open": open_cat}


def remaining(category: str, path: Path = LEDGER) -> float:
    return state(path)["remaining_s"][category]


def start(category: str, note: str, t: float | None = None, path: Path = LEDGER) -> None:
    if category not in CAPS:
        raise KeyError(category)
    if state(path)["open"] is not None:
        raise RuntimeError("another category is open")
    _append({"event": "start", "category": category, "note": note,
             "t": time.time() if t is None else t}, path)


def stop(category: str, note: str, path: Path = LEDGER) -> None:
    _append({"event": "stop", "category": category, "note": note, "t": time.time()}, path)


def checkpoint(category: str, note: str, path: Path = LEDGER) -> None:
    _append({"event": "checkpoint", "category": category, "note": note, "t": time.time()}, path)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "start":
        start(sys.argv[2], " ".join(sys.argv[3:]),
              t=float(os.environ["HML_START_T"]) if os.environ.get("HML_START_T") else None)
    elif cmd == "stop":
        stop(sys.argv[2], " ".join(sys.argv[3:]))
    elif cmd == "checkpoint":
        checkpoint(sys.argv[2], " ".join(sys.argv[3:]))
    print(json.dumps(state(), indent=1))
