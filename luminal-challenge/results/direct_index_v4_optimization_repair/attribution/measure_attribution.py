"""Per-run measured attribution of optimiser time, by query outcome.

Finding R4 of the lead review: the worker's ``82.5% / 1.21x ceiling`` was a
heuristic built from aggregated medians and an assumption that every unfinished
query costs the whole timeout. It was presented as though it were a
decomposition. This script replaces it with a direct measurement.

It replays the optimiser's own target and window enumeration outside the
production path — production code is not modified and not instrumented — and
times each query individually, recording which declared limit stopped it. The
result is an attribution of wall-clock optimiser time to query outcomes, per
program, for the frozen v3 source and for the candidate.

Nothing here is a performance result for the candidate: it is a diagnostic
breakdown. The candidate's speed is measured by ``benchmark_optimization.py``
in fresh isolated processes.
"""

from __future__ import annotations

import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT), str(ROOT / ".reference")]

import machine  # noqa: E402
import direct_compiler as dcmp  # noqa: E402
import direct_constraints as dk  # noqa: E402
import direct_contract as dc  # noqa: E402
import direct_optimizer as do  # noqa: E402
import schema_index as si  # noqa: E402


def attribute(path: Path) -> dict:
    program = machine.load_program(path)
    facts = dc.derive(program)
    limits = dcmp.DEFAULT_LIMITS
    deadline = dcmp._Deadline(limits.total_seconds)
    counters = dcmp._Counters()
    times, addresses = dcmp.bootstrap(facts, limits, deadline, counters)
    cycles = max(times.values()) + 1
    memory = dc.footprint(facts, addresses)

    buckets: dict = {}
    cache = dk.CoverCache()
    total = 0.0
    for target_cycles, target_memory in do.targets_for(facts, cycles, memory):
        for window in do.windows_for(
            facts, times, addresses, scratch_first=target_memory < memory
        ):
            meter = si.Budget(
                seconds=limits.query_seconds,
                max_cover=limits.max_cover,
                max_visited=limits.max_visited,
                max_records=limits.max_records,
            ).start()
            started = time.perf_counter()
            try:
                query = dk.JointQuery(
                    facts, times, addresses, window, target_cycles, target_memory,
                    meter, cache,
                )
                expression = query.expression()
            except dk.Infeasible:
                outcome = "INFEASIBLE"
                elapsed = time.perf_counter() - started
            except si.BudgetExhausted as exc:
                outcome = f"UNKNOWN_CONSTRUCTION ({exc.reason})"
                elapsed = time.perf_counter() - started
            else:
                result = si.solve(expression, query.n, meter=meter)
                elapsed = time.perf_counter() - started
                if result.is_unknown:
                    outcome = f"UNKNOWN_SEARCH ({result.reason})"
                else:
                    outcome = result.status
            entry = buckets.setdefault(outcome, {"queries": 0, "seconds": 0.0})
            entry["queries"] += 1
            entry["seconds"] += elapsed
            total += elapsed

    for entry in buckets.values():
        entry["share_of_optimiser_seconds"] = (
            entry["seconds"] / total if total else 0.0
        )
    return {
        "program": program["name"],
        "operations": len(program["operations"]),
        "optimiser_seconds": total,
        "queries": sum(entry["queries"] for entry in buckets.values()),
        "by_outcome": dict(sorted(buckets.items())),
    }


def main() -> int:
    paths = sorted((ROOT / ".reference" / "programs").glob("*.json"))
    entries = [attribute(path) for path in paths]

    combined: dict = {}
    grand_total = 0.0
    for entry in entries:
        grand_total += entry["optimiser_seconds"]
        for outcome, bucket in entry["by_outcome"].items():
            acc = combined.setdefault(outcome, {"queries": 0, "seconds": 0.0})
            acc["queries"] += bucket["queries"]
            acc["seconds"] += bucket["seconds"]
    for acc in combined.values():
        acc["share_of_optimiser_seconds"] = (
            acc["seconds"] / grand_total if grand_total else 0.0
        )

    payload = {
        "scope": (
            "a measured attribution of optimiser wall-clock time to query "
            "outcome, replaying the optimiser's own enumeration outside the "
            "production path; production code is neither modified nor "
            "instrumented"
        ),
        "caveat": (
            "this is a single in-process diagnostic run, not a performance "
            "result; the candidate's speed is measured in fresh isolated "
            "processes by benchmark_optimization.py"
        ),
        "source_sha256": {
            name: __import__("hashlib").sha256((ROOT / name).read_bytes()).hexdigest()
            for name in ("schema_index.py", "direct_constraints.py",
                         "direct_optimizer.py", "direct_compiler.py")
        },
        "total_optimiser_seconds": grand_total,
        "by_outcome": dict(sorted(combined.items())),
        "per_program": entries,
    }
    destination = Path(__file__).with_name("attribution.json")
    destination.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    print(json.dumps({"total_optimiser_seconds": grand_total,
                      "by_outcome": payload["by_outcome"]}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
