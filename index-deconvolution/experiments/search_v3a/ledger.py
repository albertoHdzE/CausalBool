"""Controller wall-span ledger for HID-search-v3a (PROTOCOL section 4).

One durable event stream, ``<run>/ledger/resource_events.jsonl``: ``start`` and ``stop``
events per category (development, prospective, report_verification) and ``checkpoint``
events from runners. A category's charge is the sum of its closed spans plus, while a
span is open, the time to now. Spans never overlap across categories (``start`` refuses
while another category is open). Worker CPU/wall is reported separately from the rows.

    PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m search_v3a.ledger \
        start|stop CATEGORY NOTE   |   status
"""
from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path

ID_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ID_ROOT / "results" / "hierarchy_search_v3a" / "search-confirm-v3a-r1"
LEDGER = RUN_DIR / "ledger" / "resource_events.jsonl"
CAPS = {"development": 14400.0, "prospective": 10800.0, "report_verification": 3600.0}
TOTAL = 28800.0
REPORT_RESERVE = 600.0


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
                raise RuntimeError(f"ledger: stop {e['category']} without an open span")
            used[open_cat] += e["t"] - open_t
            open_cat, open_t = None, None
    if open_cat is not None:
        used[open_cat] += now - open_t
    return {"used_s": used, "open": open_cat, "caps_s": CAPS,
            "remaining_s": {c: CAPS[c] - used[c] for c in CAPS},
            "total_used_s": sum(used.values()), "total_cap_s": TOTAL}


def start(category: str, note: str, path: Path = LEDGER) -> None:
    if category not in CAPS:
        raise ValueError(category)
    st = state(path)
    if st["open"] is not None:
        raise RuntimeError(f"category {st['open']} is still open")
    _append({"event": "start", "category": category, "t": time.time(), "note": note}, path)


def stop(category: str, note: str, path: Path = LEDGER) -> None:
    if state(path)["open"] != category:
        raise RuntimeError(f"{category} is not open")
    _append({"event": "stop", "category": category, "t": time.time(), "note": note}, path)


class SpanBudget:
    """The budget interface ``hierarchy.benchmark.run_cases`` reads (``expired``,
    ``save``, ``elapsed``), over the open span of one category. ``margin_s`` keeps time
    to terminate and record running workers before the cap: no job starts inside it."""

    def __init__(self, category: str, job: str, margin_s: float = 90.0,
                 path: Path = LEDGER) -> None:
        if state(path)["open"] != category:
            raise RuntimeError(f"open a {category} span before running its jobs")
        self.category, self.job, self.margin, self.path = category, job, margin_s, path
        self.total = CAPS[category]

    def elapsed(self) -> float:
        return state(self.path)["used_s"][self.category]

    def expired(self) -> bool:
        return self.elapsed() > self.total - self.margin

    def save(self) -> None:
        _append({"event": "checkpoint", "category": self.category, "t": time.time(),
                 "job": self.job}, self.path)


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv[0] == "start":
        start(argv[1], " ".join(argv[2:]))
    elif argv[0] == "stop":
        stop(argv[1], " ".join(argv[2:]))
    print(json.dumps(state(), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
