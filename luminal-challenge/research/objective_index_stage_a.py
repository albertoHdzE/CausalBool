"""Section 2 reproduction and development-only diagnosis (objective-index protocol 1.0).

1. Reproduce the accepted public-score recount from raw rows
   (``optimization_stage_a.public_recount``, the retained-evidence owner) and
   compare with the three exact values the protocol quotes.
2. Recount the accepted run's stopping reasons (``stopping_audit``) and
   improvement kinds -- the old 32-query cap among them.
3. Profile A0-equivalent and A1-A4 on DEVELOPMENT programs only (first two old
   held-out programs per family plus the eight public programs, the owner's
   population), outside every timing run: domain construction, option checks,
   state copying, propagation, decoding/encoding and validation.
4. Target coverage: on all 100 development programs, run A2 and A4 (untimed
   diagnosis, 1.0 s) and ask, for every accepted improvement, whether the new
   (C, S) lies in the union of the OLD target rectangles of the incumbent it
   improved. An improvement outside that union is a physical trade-off the
   product domain covers and the old targets omit.

Nothing here is a measured comparison; it informs no selection.

Usage::

    PYTHONPATH=.reference:. python -m research.objective_index_stage_a --out DIR
"""

from __future__ import annotations

import argparse
import cProfile
import io
import json
from pathlib import Path
import pstats
import time
from typing import Dict, List

import direct_compiler as dcomp
import direct_contract as dc
import direct_optimizer as dopt

from research import objective_index_search as ois
from research import optimization_common as oc
from research import optimization_profile as osp
from research import optimization_stage_a as osa
from research import run_structural_experiments as rse
from research import structural_encoding as se


EXPECTED_SCORES = {"structural_bound": 2.0327602339438613,
                   "accepted_default": 2.0084662022846573,
                   "classical": 1.9013791212645499}

PHASES = dict(osp.PHASES)
PHASES.update({
    "product_record": [("objective_index_search.py", "product_record")],
    "product_caps": [("objective_index_search.py", "product_caps")],
    "propagated_search": [("objective_index_search.py", "propagated_search")],
    "propagation_times": [("objective_index_search.py", "times_fixpoint")],
    "propagation_addresses": [("objective_index_search.py", "addresses_fixpoint")],
    "propagation_bound": [("objective_index_search.py", "product_bound")],
    "expander_children": [("objective_index_search.py", "children")],
    "state_copy": [("structural_encoding.py", "copy")],
    "recompute_lifetimes": [("structural_encoding.py", "recompute_lifetimes")],
    "decode": [("structural_encoding.py", "decode")],
    "catalog": [("objective_index_search.py", "build_catalog")],
    "normalise": [("structural_encoding.py", "normalise_compilation")],
    "object_digest": [("structural_encoding.py", "object_digest")],
})


def _bootstrap(program):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, se.issue_cycles_of(program, compiled["bundles"]), dict(compiled["scratch"])


def _phases(stats: pstats.Stats) -> Dict[str, float]:
    table: Dict[str, float] = {}
    for phase, keys in PHASES.items():
        total = 0.0
        for (filename, _line, name), (_cc, _nc, _tt, ct, _callers) in stats.stats.items():
            for suffix, func in keys:
                if filename.endswith(suffix) and name == func:
                    total += ct
        table[phase] = total
    return table


def profile_arm(program: dict, arm: str, budget: float) -> dict:
    facts, times, addresses = _bootstrap(program)

    def run():
        if arm == "A0_equivalent_cap32":
            return rse.structural_optimise(program, facts, times, addresses, "structural_bound",
                                           budget, min(0.1, budget), 32,
                                           {"query_max_cover": 4096, "search_max_nodes": 1_000_000,
                                            "search_max_candidate_validations": 100_000})
        return ois.optimise(program, facts, times, addresses, arm=arm, budget_seconds=budget)

    started = time.perf_counter()
    _, _, record = run()
    wall = time.perf_counter() - started
    profiler = cProfile.Profile()
    profiler.enable()
    run()
    profiler.disable()
    stats = pstats.Stats(profiler, stream=io.StringIO())
    return {"wall_seconds": wall, "stopped_because": record["stopped_because"],
            "accepted": record["accepted"], "statuses": record["statuses"],
            "profiled_total_seconds": stats.total_tt, "phase_cumulative_seconds": _phases(stats)}


def profile(programs: List[dict]) -> dict:
    rows = []
    for entry in programs:
        for arm in ("A0_equivalent_cap32",) + ois.ARM_LABELS:
            for budget in (0.1, 1.0):
                row = profile_arm(entry["program"], arm, budget)
                row.update(label=entry["label"], family=entry["family"], arm=arm, budget=budget)
                rows.append(row)
    totals: Dict[str, Dict[str, float]] = {}
    for row in rows:
        bucket = totals.setdefault(f"{row['arm']}@{row['budget']}", {"profiled_total_seconds": 0.0})
        bucket["profiled_total_seconds"] += row["profiled_total_seconds"]
        for phase, seconds in row["phase_cumulative_seconds"].items():
            bucket[phase] = bucket.get(phase, 0.0) + seconds
    shares = {key: {phase: (seconds / bucket["profiled_total_seconds"]
                            if bucket["profiled_total_seconds"] else None)
                    for phase, seconds in bucket.items() if phase != "profiled_total_seconds"}
              for key, bucket in totals.items()}
    return {"population": "DEVELOPMENT only: first two old held-out programs per family and "
                          "the eight public programs (optimization_profile owner's list)",
            "programs": [e["label"] for e in programs], "rows": rows, "totals": totals,
            "shares": shares,
            "note": "cumulative phase times overlap and are not additive; A0_equivalent_cap32 "
                    "is the accepted controller run from the CURRENT research tree for "
                    "profiling only, never a measured A0 row"}


def target_coverage(budget: float = 1.0) -> dict:
    """Improvements whose new (C, S) lies outside every old target rectangle."""

    from tests_direct import generate_programs as gp

    examples: List[dict] = []
    counts = {}
    for arm in ("A2_product_search", "A4_multiscale_search"):
        inside = outside = 0
        for seed in range(800000, 800100):
            program = gp.additional_program(seed)
            facts, times, addresses = _bootstrap(program)
            _, _, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                        budget_seconds=budget)
            for step in record["improvements"]:
                before, after = tuple(step["from_CS"]), tuple(step["to_CS"])
                targets = dopt.targets_for(facts, *before)
                if any(after[0] <= tc and after[1] <= tm for tc, tm in targets):
                    inside += 1
                    continue
                outside += 1
                if len(examples) < 25:
                    examples.append({"arm": arm, "seed": seed, "family": gp.FAMILIES[seed % 5],
                                     "from_CS": list(before), "to_CS": list(after),
                                     "from_J": before[0] * before[1],
                                     "to_J": after[0] * after[1],
                                     "old_targets": [list(t) for t in targets]})
        counts[arm] = {"improvements": inside + outside, "inside_old_rectangles": inside,
                       "outside_old_rectangles": outside}
    return {"population": "development seeds 800000-800099; untimed diagnosis at 1.0 s",
            "budget_seconds": budget, "counts": counts, "examples": examples,
            "meaning": "an 'outside' improvement is a validated physical compilation that "
                       "beats its incumbent's J while lying in no old target rectangle"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    parser.add_argument("--skip-profile", action="store_true")
    parser.add_argument("--recount-only", action="store_true")
    args = parser.parse_args(argv)
    out = Path(args.out)
    recount = osa.public_recount()
    keys = {"structural_bound": "structural_bound@0.1", "accepted_default": "accepted_default@None",
            "classical": "classical@None"}
    reproduction = {}
    for arm, value in EXPECTED_SCORES.items():
        entry = recount["arms"][keys[arm]]
        reproduction[arm] = {"expected": value, "recomputed_min": entry["min"],
                             "recomputed_max": entry["max"],
                             "abs_difference": max(abs(entry["min"] - value),
                                                   abs(entry["max"] - value)),
                             "agrees_within_1e-12": max(abs(entry["min"] - value),
                                                        abs(entry["max"] - value)) <= 1e-12}
    oc.write_json(out / "PUBLIC_RECOUNT_REPRODUCTION.json",
                  {"owner": "optimization_stage_a.public_recount", "expected": EXPECTED_SCORES,
                   "reproduction": reproduction,
                   "all_agree": all(v["agrees_within_1e-12"] for v in reproduction.values()),
                   "recount": recount})
    if args.recount_only:
        print(json.dumps(reproduction, indent=1))
        return 0
    oc.write_json(out / "STOPPING_AUDIT.json", {"stopping": osa.stopping_audit(),
                                                "improvement_kinds": osa.improvement_kinds()})
    if not args.skip_profile:
        oc.write_json(out / "PROFILE.json", profile(osp.development_profile_programs()))
    oc.write_json(out / "TARGET_COVERAGE.json", target_coverage())
    print(json.dumps(reproduction, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
