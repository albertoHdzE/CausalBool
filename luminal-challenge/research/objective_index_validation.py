"""Finite proof-obligation checks of the solver ladder, with exact denominators.

One owner for the exhaustive evidence of protocol sections 4-6; the unit tests
assert on these functions and ``PRUNING_VALIDATION.json`` records their full
output. Every check prints its denominator, and a check over nothing is
reported as EMPTY, never PASS.

- ``cap_lemma``: strict improvements of every exhaustible fixture's UNCAPPED
  declared domain equal those of its capped domain, at every threshold, by the
  oracle and by A2-, A3- and A4-order searches run to exhaustion.
- ``propagation_soundness``: every propagation deletion, inconsistency, prune
  and bound holds for every oracle-feasible completion of its prefix; every
  certificate replays; planted unsound rules are detected.
- ``replay_artifacts``: deterministic fixed-work certificate streams on the
  first development program of each family (A3 and A4), re-run and replayed.
- ``rank_round_trips``: every propagated leaf's rank path is its codec index.
"""

from __future__ import annotations

import json
from pathlib import Path
import time
from typing import Callable, Dict, List, Optional
from unittest import mock


import direct_compiler as dcomp
import direct_constraints as dk
import direct_contract as dc
import schema_index as si

from research import objective_index_replay as oir
from research import objective_index_search as ois
from research import optimization_common as oc
from research import optimization_fixtures as ofx
from research import structural_encoding as se
from research import structural_oracle as so


BIG = si.Budget(seconds=1e6, max_cover=4096, max_visited=10_000_000, max_records=1_000_000)
ORACLE_MAX = 70_000


def bootstrap(program: dict):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    return facts, se.issue_cycles_of(program, compiled["bundles"]), dict(compiled["scratch"])


def original_fixtures() -> List[dict]:
    return json.loads((oc.ROOT / "plan" / "phase2" / "FIXTURES.json").read_text())["fixtures"]


_RECIPE: Dict[tuple, List[dict]] = {}


def recipe_fixtures(first: int = 920000, count: int = 30, cartesian_max: int = 12_000
                    ) -> List[dict]:
    """Per seed, the largest recipe candidate with Cartesian size <= cartesian_max.

    Legality/oracle work only; no candidate outcome is consulted.
    """

    key = (first, count, cartesian_max)
    if key in _RECIPE:
        return _RECIPE[key]
    from tests_direct import generate_programs as gp

    out = []
    for seed in range(first, first + count):
        program = gp.additional_program(seed)
        facts, times, addresses, incumbent = ofx.bootstrap(program)
        best = None
        for order, size, selected in ofx.candidate_tuples(
                ofx.producing_orders(facts, times, addresses)):
            for radius in (1, 2):
                record = ofx.domain_record(f"t{seed}:{order}:{size}:r{radius}", "t", program,
                                           facts, times, addresses, incumbent, selected, radius)
                size_c = ofx.cartesian(record)
                if size_c <= cartesian_max and (best is None or size_c > best[0]):
                    best = (size_c, record)
        if best is not None:
            out.append(best[1])
    _RECIPE[key] = out
    return out


def qualified_fixture_records(run: Optional[Path]) -> List[dict]:
    """Every qualified fixture of a run (development and evaluation), if present."""

    if run is None:
        return []
    out = []
    for cohort in ("development", "evaluation"):
        manifest = Path(run) / "fixtures" / cohort / "MANIFEST.json"
        if not manifest.exists():
            continue
        for fixture in json.loads(manifest.read_text())["fixtures"]:
            out.append(json.loads((Path(run) / "fixtures" / cohort / fixture["fixture_id"]
                                   / "record.json").read_text()))
    return out


def _key(times, addresses):
    return (tuple(sorted((int(k), v) for k, v in times.items())),
            tuple(sorted(addresses.items())))


def _incumbent(record):
    incumbent = record["incumbent"]
    return (se.issue_cycles_of(record["program"], incumbent["bundles"]),
            dict(incumbent["scratch"]))


# --------------------------------------------------------------------------
# Section 4
# --------------------------------------------------------------------------


def cap_lemma(records: List[dict]) -> dict:
    fixtures = thresholds = nonempty = objects = 0
    violations: List[str] = []
    no_improvement_by_caps = 0
    for record in records:
        record = dict(record, target=None)
        facts = dc.derive(record["program"])
        times, addresses = _incumbent(record)
        window = tuple(record["selected_operations"])
        uncapped = so.enumerate_feasible(record, ORACLE_MAX)["feasible"]
        products = sorted({x["product"] for x in uncapped})
        j0 = (max(times.values()) + 1) * dc.footprint(facts, addresses)
        fixtures += 1
        for threshold in sorted(set([j0] + [p + 1 for p in products])):
            thresholds += 1
            improving = {_key(x["times"], x["addresses"]): x["product"]
                         for x in uncapped if x["product"] < threshold}
            caps = ois.product_caps(facts, times, addresses, window, objective=threshold)
            if caps["status"] != "OK":
                no_improvement_by_caps += 1
                if improving:
                    violations.append(f"{record['id']}@{threshold}: caps claim none")
                continue
            try:
                capped = ois.capped_record(record, facts, caps)
            except dk.Infeasible:
                if improving:
                    violations.append(f"{record['id']}@{threshold}: capped infeasible")
                continue
            oracle_capped = {_key(x["times"], x["addresses"]): x["product"]
                             for x in so.enumerate_feasible(capped, ORACLE_MAX)["feasible"]
                             if x["product"] < threshold}
            if oracle_capped != improving:
                violations.append(f"{record['id']}@{threshold}: oracle sets differ")
            domain = se.Domain.from_record(capped)
            for mode in ("ss_bound", "propagate"):
                _, extras = ois.propagated_search(domain, record["incumbent"], BIG, mode=mode,
                                                  collect=True, threshold=threshold)
                found = {_key({str(k): v for k, v in x["times"].items()}, x["addresses"]):
                         x["product"] for x in extras["collected"].values()}
                if found != improving:
                    violations.append(f"{record['id']}@{threshold}: {mode} set differs")
            lds = ois.lds_enumerate(domain, record["incumbent"], threshold)
            found = {_key({str(k): v for k, v in x["times"].items()}, x["addresses"]):
                     x["product"] for x in lds["collected"].values()}
            if lds["status"] != "EXHAUSTED" or found != improving:
                violations.append(f"{record['id']}@{threshold}: A4 heap set differs")
            pairs = [(d, lb) for d, lb, _ in lds["pop_order"]]
            if pairs != sorted(pairs):
                violations.append(f"{record['id']}@{threshold}: heap order not monotone")
            if improving:
                nonempty += 1
                objects += len(improving)
    status = "EMPTY" if thresholds == 0 else ("PASS" if not violations else "FAIL")
    return {"fixtures": fixtures, "thresholds": thresholds, "thresholds_with_improvements": nonempty,
            "improving_objects_compared": objects,
            "thresholds_proved_empty_by_caps": no_improvement_by_caps,
            "violations": violations[:50], "violation_count": len(violations), "status": status,
            "compared": "oracle(uncapped) vs oracle(capped) vs A2-order DFS vs A3 DFS vs A4 heap"}


# --------------------------------------------------------------------------
# Section 5
# --------------------------------------------------------------------------


def propagation_soundness(records: List[dict],
                          mutate: Optional[Callable[[ois.Propagation], None]] = None) -> dict:
    violations: List[tuple] = []
    totals = {"fixtures": 0, "thresholds": 0, "events": 0, "kept": 0, "pruned": 0,
              "inconsistent": 0, "removed_values": 0, "improving_objects": 0,
              "completion_checks": 0, "certificates_replayed": 0}
    rule_counts: Dict[str, int] = {}
    for record in records:
        record = dict(record, target=None)
        domain = se.Domain.from_record(record)
        facts = domain.facts
        feasible = so.enumerate_feasible(record, ORACLE_MAX)["feasible"]
        objects = [({int(k): v for k, v in x["times"].items()}, x["addresses"], x["cycles"],
                    x["scratch"], x["product"]) for x in feasible]
        products = sorted({o[4] for o in objects})
        thresholds = sorted({products[0] + 1, products[len(products) // 2] + 1,
                             products[-1] + 1} if products else {1})
        stats = ois.PropagationStats(keep=True)
        events: List[dict] = []
        original = ois.Propagation.__init__

        def patched(self, *args, **kwargs):
            original(self, *args, **kwargs)
            if mutate is not None:
                mutate(self)

        for threshold in thresholds:
            totals["thresholds"] += 1
            before = len(events)
            with mock.patch.object(ois.Propagation, "__init__", patched):
                _, extras = ois.propagated_search(domain, record["incumbent"], BIG, stats=stats,
                                                  collect=True, audit=events.append,
                                                  threshold=threshold)
            for event in events[before:]:
                event["threshold"] = threshold
            truth = {_key({str(k): v for k, v in t.items()}, a)
                     for t, a, c, s, p in objects if p < threshold}
            found = {_key({str(k): v for k, v in x["times"].items()}, x["addresses"])
                     for x in extras["collected"].values()}
            totals["improving_objects"] += len(truth)
            if truth != found:
                violations.append((record["id"], threshold, "improving set differs"))
        totals["fixtures"] += 1
        totals["removed_values"] += sum(stats.removed_values.values())
        for rule, count in stats.counts.items():
            rule_counts[rule] = rule_counts.get(rule, 0) + count
        for event in events:
            j0 = event["threshold"]
            totals["events"] += 1
            totals[event["outcome"]] += 1
            prefix_t, prefix_a = event["times"], event["addresses"]
            consistent = [o for o in objects
                          if all(o[0][op] == t for op, t in prefix_t.items())
                          and all(o[1][n] == a for n, a in prefix_a.items())]
            totals["completion_checks"] += len(consistent)
            if event["outcome"] == "inconsistent":
                if consistent:
                    violations.append((record["id"], "inconsistent but a completion exists"))
                continue
            if event["outcome"] == "pruned" and any(o[4] < j0 for o in consistent):
                violations.append((record["id"], "pruned an improving completion"))
            for o in consistent:
                for op, values in event["D"].items():
                    if o[0][op] not in values:
                        violations.append((record["id"], "time deletion of a feasible value"))
                if event["A"] is not None:
                    for name, values in event["A"].items():
                        if o[1][name] not in values:
                            violations.append((record["id"], "address deletion"))
                if o[2] < event["LC"] or o[3] < event["LS"]:
                    violations.append((record["id"], "bound exceeds a completion"))
        replayed = oir.replay_stream(facts, stats.certificates)
        totals["certificates_replayed"] += replayed["replayed"]
        if replayed["failure_count"]:
            violations.append((record["id"], "certificate replay", replayed["failures"][:2]))
    status = "EMPTY" if totals["events"] == 0 else ("PASS" if not violations else "FAIL")
    return {"totals": totals, "rule_counts": dict(sorted(rule_counts.items())),
            "violations": [repr(v)[:300] for v in violations[:50]],
            "violation_count": len(violations), "status": status}


def planted_mutations(records: List[dict]) -> dict:
    """Unsound variants must be caught: an off-by-one lag and an inflated live peak."""

    def lag_plus_one(prop):
        prop.edges = tuple((u, v, lag + 1) for u, v, lag in prop.edges)

    def inflated_peak(prop):
        prop.static_peak = (prop.static_peak[0] + 1, prop.static_peak[1])

    out = {}
    for name, mutate in (("precedence_lag_plus_one", lag_plus_one),
                         ("static_live_peak_plus_one", inflated_peak)):
        result = propagation_soundness(records, mutate)
        out[name] = {"violation_count": result["violation_count"],
                     "detected": result["violation_count"] > 0}
    out["status"] = "PASS" if all(v["detected"] for v in out.values()) else "FAIL"
    return out


def rank_round_trips(records: List[dict]) -> dict:
    leaves = failures = 0
    for record in records:
        record = dict(record, target=None)
        domain = se.Domain.from_record(record)
        layout = se.layout(domain, "structural_rank")
        report = ois._new_report(domain, "rank_check", record["incumbent"])
        expander = ois.Expander(domain, "propagate", ois.PropagationStats(), report)
        root = expander.root(None)
        stack = [root] if root is not None else []
        while stack:
            node = stack.pop()
            if expander.is_leaf(node):
                keys = [("time", op) for op in domain.selected_operations] + [
                    ("address", name) for name in node.order]
                index = sum(rank << layout.field(key).offset
                            for rank, key in zip(node.ranks, keys))
                compiled = dc.compilation(domain.facts, node.state.times, node.state.addresses)
                decoded = se.decode(domain, index, "structural_rank")
                if (se.encode(domain, compiled, "structural_rank") != index
                        or decoded.status != se.COMPLETE
                        or decoded.identity != se.compilation_identity(domain.facts, compiled)):
                    failures += 1
                leaves += 1
                continue
            stack.extend(expander.children(node, lambda: None))
    return {"leaves": leaves, "failures": failures,
            "status": "EMPTY" if leaves == 0 else ("PASS" if failures == 0 else "FAIL")}


# --------------------------------------------------------------------------
# Replay artifacts (deterministic fixed work)
# --------------------------------------------------------------------------


def replay_artifacts(out_dir: Optional[Path] = None) -> dict:
    from tests_direct import generate_programs as gp

    results = {}
    for family in gp.FAMILIES:
        seed = next(s for s in range(800000, 800100) if gp.FAMILIES[s % 5] == family)
        program = gp.additional_program(seed)
        facts, times, addresses = bootstrap(program)
        for arm in ("A3_propagated_search", "A4_multiscale_search"):
            runs = []
            for _ in range(2):
                stats = ois.PropagationStats(keep=True)
                kwargs = dict(budget_seconds=1e6, query_seconds=1e6, node_ceiling=20_000,
                              stats=stats)
                if arm == "A4_multiscale_search":
                    kwargs.update(slice_seconds=1e6)
                _, _, record = ois.optimise(program, facts, times, addresses, arm=arm,
                                            limits=dict(ois.PER_QUERY_LIMITS,
                                                        search_max_nodes=2_000), **kwargs)
                runs.append((stats, record))
            (first, record), (second, _) = runs
            replayed = oir.replay_stream(facts, first.certificates)
            entry = {"seed": seed, "family": family, "arm": arm,
                     "stream_sha256": first.digest(), "stream_length": first.stream_length,
                     "rerun_stream_sha256": second.digest(),
                     "deterministic": first.digest() == second.digest(),
                     "counts": dict(sorted(first.counts.items())),
                     "replay": {k: replayed[k] for k in ("replayed", "failure_count", "status")},
                     "accepted": record["accepted"], "nodes": record["aggregate"]["nodes"]}
            if out_dir is not None:
                path = Path(out_dir) / f"replay_{family}_{arm}.jsonl"
                path.parent.mkdir(parents=True, exist_ok=True)
                with path.open("w") as handle:
                    for certificate in first.certificates:
                        handle.write(repr(certificate) + "\n")
                entry["certificates_file"] = path.name
                entry["certificates_file_sha256"] = oc.file_sha256(path)
            results[f"{family}:{arm}"] = entry
    ok = all(e["deterministic"] and e["replay"]["status"] in ("PASS", "EMPTY")
             for e in results.values())
    return {"artifacts": results, "status": "PASS" if ok else "FAIL",
            "work_limits": "node_ceiling 20000 per optimisation, 2000 nodes per query, "
                           "no wall-clock limit"}


def main(argv=None) -> int:
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--run", required=True)
    args = parser.parse_args(argv)
    run = Path(args.run).resolve()
    started = time.perf_counter()
    base = original_fixtures() + recipe_fixtures()
    qualified = qualified_fixture_records(run)
    payload = {
        "populations": {"original_fixtures": len(original_fixtures()),
                        "recipe_domains_920000_920029": len(recipe_fixtures()),
                        "qualified_fixtures": len(qualified)},
        "cap_lemma_original_and_recipe": cap_lemma(base),
        "cap_lemma_qualified": cap_lemma(qualified),
        "propagation_soundness_original_and_recipe": propagation_soundness(base),
        "propagation_soundness_qualified": propagation_soundness(qualified),
        "planted_mutations": planted_mutations(base),
        "rank_round_trips": rank_round_trips(base + qualified),
        "replay_artifacts": replay_artifacts(run / "pruning_replay"),
    }
    payload["seconds"] = time.perf_counter() - started
    payload["status"] = "PASS" if all(
        v.get("status") == "PASS" for k, v in payload.items() if isinstance(v, dict)
        and "status" in v) else "FAIL"
    oc.write_json(run / "PRUNING_VALIDATION.json", payload)
    print(json.dumps({k: (v.get("status") if isinstance(v, dict) else v)
                      for k, v in payload.items()}, indent=1))
    return 0 if payload["status"] == "PASS" else 1


if __name__ == "__main__":
    raise SystemExit(main())
