"""This run's controller ledger (PROTOCOL section 4): the multilevel-v1 ledger functions
(same caps, same span rules) pointed at ``<run>/ledger/resource_events.jsonl``.

    PYTHONPATH=experiments:.:../src ../venv/bin/python -B -m hierarchy_dictionary.ledger \
        start|stop|checkpoint CATEGORY NOTE | status
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

from hierarchy_multilevel import ledger as _L

ID_ROOT = Path(__file__).resolve().parents[2]
RUN_DIR = ID_ROOT / "results" / "hierarchy_dictionary_v1" / "dictionary-feasibility-v1-r1"
LEDGER = RUN_DIR / "ledger" / "resource_events.jsonl"
CAPS, TOTAL = _L.CAPS, _L.TOTAL
REPORT_STOP_OPTIONAL, REPORT_STOP_EXECUTOR = _L.REPORT_STOP_OPTIONAL, _L.REPORT_STOP_EXECUTOR


def state() -> dict:
    return _L.state(LEDGER)


def remaining(category: str) -> float:
    return _L.remaining(category, LEDGER)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "start":
        _L.start(sys.argv[2], " ".join(sys.argv[3:]), path=LEDGER)
    elif cmd == "stop":
        _L.stop(sys.argv[2], " ".join(sys.argv[3:]), path=LEDGER)
    elif cmd == "checkpoint":
        _L.checkpoint(sys.argv[2], " ".join(sys.argv[3:]), path=LEDGER)
    print(json.dumps(state(), indent=1))
