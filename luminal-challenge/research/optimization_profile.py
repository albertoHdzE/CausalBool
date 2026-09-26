"""Stage A.3 profile of the frozen structural controller on development data only.

Profiled programs: the first two old held-out programs per family in manifest
order, plus the eight public programs. This runs outside every timing matrix;
cProfile inflates absolute times, so only the *shares* of each phase and the
un-profiled wall times are reported as findings.

Usage::

    PYTHONPATH=.reference:. python -m research.optimization_profile --out DIR
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import subprocess
import sys
import time
from typing import Dict, List

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import optimization_common as oc
from research import run_structural_experiments as rse
from research import structural_encoding as se


LIMITS = {
    "query_max_cover": 4096, "search_max_nodes": 1000000,
    "search_max_candidate_validations": 100000,
}

# Function names (file suffix, function) whose *cumulative* time defines a phase.
PHASES = {
    "domain_record": [("run_structural_experiments.py", "matched_window_record")],
    "domain_from_record": [("structural_encoding.py", "from_record")],
    "domain_digest": [("structural_encoding.py", "digest")],
    "layout": [("structural_encoding.py", "layout")],
    "search_total": [("structural_search.py", "search")],
    "option_generation": [("structural_encoding.py", "options")],
    "candidate_validation": [("machine.py", "check_case")],
    "check_compilation": [("machine.py", "check_compilation")],
    "validate_program": [("machine.py", "validate_program")],
    "derive_facts": [("direct_contract.py", "derive")],
    "serialisation": [("structural_encoding.py", "canonical_json")],
    "encode_best_index": [("structural_encoding.py", "encode")],
    "targets_windows": [("direct_optimizer.py", "targets_for"), ("direct_optimizer.py", "windows_for")],
}


def development_profile_programs() -> List[dict]:
    from tests_direct import generate_programs as gp

    out: List[dict] = []
    for family_index, family in enumerate(gp.FAMILIES):
        seeds = [s for s in range(800000, 800100) if gp.FAMILIES[s % 5] == family][:2]
        for seed in seeds:
            program = gp.additional_program(seed)
            out.append({"label": f"old_heldout:{seed}", "family": family, "program": program})
    for path in sorted((oc.ROOT / ".reference" / "programs").glob("*.json")):
        out.append({"label": f"public:{path.name}", "family": "public",
                    "program": machine.load_program(path)})
    return out


def _phase_seconds(stats: pstats.Stats) -> Dict[str, float]:
    table: Dict[str, float] = {}
    for phase, keys in PHASES.items():
        total = 0.0
        for (filename, _line, name), (_cc, _nc, _tt, ct, _callers) in stats.stats.items():
            for suffix, func in keys:
                if filename.endswith(suffix) and name == func:
                    total += ct
        table[phase] = total
    return table


def profile_one(program: dict, budget: float, max_queries: int) -> dict:
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])

    # Un-profiled wall time first, then the profiled run for phase shares.
    started = time.perf_counter()
    _, _, record = rse.structural_optimise(program, facts, times, addresses, "structural_bound",
                                           budget, min(0.1, budget), max_queries, LIMITS)
    wall = time.perf_counter() - started

    profiler = cProfile.Profile()
    profiler.enable()
    _, _, profiled = rse.structural_optimise(program, facts, times, addresses,
                                             "structural_bound", budget, min(0.1, budget),
                                             max_queries, LIMITS)
    profiler.disable()
    stats = pstats.Stats(profiler, stream=io.StringIO())
    total = stats.total_tt
    return {
        "wall_seconds": wall,
        "stopped_because": record["stopped_because"],
        "attempted_queries": record["attempted_queries"],
        "statuses": record["statuses"],
        "accepted": record["accepted"],
        "profiled_total_seconds": total,
        "profiled_stopped_because": profiled["stopped_because"],
        "phase_cumulative_seconds": _phase_seconds(stats),
    }


def import_seconds() -> dict:
    """Cold import cost of the worker's modules, in fresh interpreters."""

    out = {}
    for label, statement in (
        ("python_startup", "pass"),
        ("machine+direct_compiler", "import machine, direct_compiler"),
        ("research.run_structural_experiments",
         "import research.run_structural_experiments"),
    ):
        samples = []
        for _ in range(5):
            started = time.perf_counter()
            subprocess.run([sys.executable, "-c", statement], cwd=str(oc.ROOT), check=True,
                           env={"PYTHONPATH": f"{oc.ROOT / '.reference'}:{oc.ROOT}"})
            samples.append(time.perf_counter() - started)
        out[label] = {"samples": samples, "median": sorted(samples)[2]}
    return out


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = Path(args.out)
    programs = development_profile_programs()
    results = []
    for entry in programs:
        for budget, cap, label in ((0.1, 32, "frozen_cap32_0.1"),
                                   (1.0, 32, "frozen_cap32_1.0"),
                                   (1.0, 10 ** 9, "uncapped_1.0")):
            row = profile_one(entry["program"], budget, cap)
            row.update(label=entry["label"], family=entry["family"], config=label,
                       operations=len(entry["program"]["operations"]))
            results.append(row)
            print(entry["label"], label, round(row["wall_seconds"], 4), row["stopped_because"],
                  row["attempted_queries"], flush=True)
    totals: Dict[str, Dict[str, float]] = {}
    for row in results:
        bucket = totals.setdefault(row["config"], {"profiled_total_seconds": 0.0})
        bucket["profiled_total_seconds"] += row["profiled_total_seconds"]
        for phase, seconds in row["phase_cumulative_seconds"].items():
            bucket[phase] = bucket.get(phase, 0.0) + seconds
    shares = {config: {phase: (seconds / bucket["profiled_total_seconds"]
                               if bucket["profiled_total_seconds"] else None)
                       for phase, seconds in bucket.items() if phase != "profiled_total_seconds"}
              for config, bucket in totals.items()}
    payload = {
        "population": "DEVELOPMENT only: first two old held-out programs per family "
                      "(manifest order) and the eight public programs",
        "programs": [e["label"] for e in programs],
        "rows": results,
        "profiled_totals": totals,
        "profiled_shares_of_total": shares,
        "import_seconds": import_seconds(),
        "note": "cumulative phase times overlap (search_total contains option_generation and "
                "candidate_validation); shares are not additive.",
    }
    oc.write_json(out / "PROFILE.json", payload)
    print(json.dumps(shares, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
