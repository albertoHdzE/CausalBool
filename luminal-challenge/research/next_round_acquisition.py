"""Stage L economics trace: paid observation acquisition in a real query (section 7).

One development program per process at 0.1 s, run with the FROZEN existing
conditional learner (``objective_index_learned.QueryLearner``, labels mode
``tree``) inside the REPAIRED controller (``next_round_search.multiscale_
optimise``, repaired A4 cell). No oracle and no injected training: every
observation is what the query's own search half paid for. These rows are not
efficacy evidence.

``TimedLearner`` is ``QueryLearner`` with timers. ``_prepare`` is restated
statement for statement with clock readings around validation, encoding,
pool, fit and ordering (the parent times only the whole preparation); a test
asserts equal status, info and queue against the parent on real domains. It
also records the time left in the query and in the whole budget at the
search-half boundary (the moment ``prepare`` is called).

Per query, "reached 20" means the learner's existing gate: at least
``schema_ranker.MIN_TRAINING`` = 20 DISTINCT case-validated observations from
what the search half observed. The observed count at the boundary is kept too.

Usage (internal; the runner builds the spec)::

    PYTHONPATH=.reference:. python -m research.next_round_acquisition --spec JSON
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from typing import List, Tuple

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import next_round_search as nrs
from research import objective_index_learned as oil
from research import schema_ranker as sr
from research import structural_encoding as se

KIND = "next_round_acquisition"


class TimedLearner(oil.QueryLearner):
    """``QueryLearner`` with per-phase timers and boundary clocks; same decisions."""

    def __init__(self, domain, mode, global_deadline: float, clock=time.perf_counter):
        super().__init__(domain, mode, clock)
        self.global_deadline = global_deadline
        self.timers = {"validation": 0.0, "encode": 0.0, "pool": 0.0, "fit": 0.0,
                       "order": 0.0}
        self.boundary = None

    def prepare(self, deadline: float) -> str:
        now = self.clock()
        self.boundary = {"observed_distinct": len(self.observations),
                         "query_remaining_seconds": deadline - now,
                         "global_remaining_seconds": self.global_deadline - now}
        return super().prepare(deadline)

    def _validate(self, compilation: dict) -> bool:
        started = self.clock()
        try:
            return super()._validate(compilation)
        finally:
            self.timers["validation"] += self.clock() - started

    def _prepare(self, deadline: float) -> str:
        # Restated from ``objective_index_learned.QueryLearner._prepare`` with
        # timers only; every branch, status and value is the parent's.
        labelled: List[Tuple[int, int]] = []
        for identity, item in self.observations.items():
            if self.clock() >= deadline:
                return self._set("EXPIRED", "the allowance ended while validating observations")
            if self.validations >= self.validation_budget:
                return self._set("VALIDATION_CEILING", "aggregate validation ceiling")
            if not self._validate(item["compilation"]):
                continue
            started = self.clock()
            try:
                index = se.encode(self.domain, item["compilation"], sr.CODEC)
            except se.DomainError as exc:
                self.rejected.append({"identity": identity, "error": f"encode: {exc}",
                                      "source": f"learned_{self.mode}"})
                continue
            finally:
                self.timers["encode"] += self.clock() - started
            labelled.append((index, item["product"]))
        distinct = {index for index, _ in labelled}
        self.info.update(observations=len(self.observations), validated=len(labelled),
                         distinct=len(distinct))
        if len(distinct) < sr.MIN_TRAINING:
            return self._set("MODEL_UNAVAILABLE",
                             f"{len(distinct)} distinct validated objects < {sr.MIN_TRAINING}")
        labelled.sort()
        indices = [index for index, _ in labelled]
        products = [product for _, product in labelled]
        threshold, y = sr.labels(products)
        elite = sorted({i for i, label in zip(indices, y) if label})
        bits = se.layout(self.domain, sr.CODEC).width
        seeds = sr.arm_seeds(self.domain.digest())

        def check() -> None:
            if self.clock() >= deadline:
                raise TimeoutError

        try:
            started = self.clock()
            pool = sr.candidate_pool(bits, indices, elite, seeds["pool"], check)
            self.timers["pool"] += self.clock() - started
            fit = y if self.mode == "tree" else sr.shuffled_labels(y, seeds["shuffled"])
            check()
            started = self.clock()
            tree = sr.fit_tree(bits, indices, fit)
            self.timers["fit"] += self.clock() - started
            check()
            started = self.clock()
            self.queue = sr.order_pool(pool["pool"], "tree", tree=tree)
            self.timers["order"] += self.clock() - started
        except TimeoutError:
            return self._set("EXPIRED", "the allowance ended while building the model")
        self.info.update(threshold=threshold, elite=len(elite), pool=pool["size"],
                         pool_sha256=pool["pool_sha256"],
                         ordering_sha256=sr.ordering_digest(self.queue),
                         leaves=len(tree.leaves))
        return self._set("READY", "")

    def summary(self) -> dict:
        return dict(super().summary(), timers=dict(self.timers), boundary=self.boundary)


def measure(spec: dict) -> dict:
    if spec.get("kind") != KIND:
        raise ValueError("not an acquisition spec")
    program = machine.load_program(spec["program_path"])
    budget = float(spec["budget_seconds"])
    started = time.perf_counter()
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    learners: List[TimedLearner] = []
    timers: dict = {}
    optimise_started = time.perf_counter()
    global_deadline = optimise_started + budget

    def factory(domain):
        learner = TimedLearner(domain, "tree", global_deadline)
        learners.append(learner)
        return learner

    best_t, best_a, record = nrs.multiscale_optimise(
        program, facts, times, addresses, budget_seconds=budget, learner_factory=factory,
        timers=timers)
    compile_seconds = time.perf_counter() - started
    final = dc.compilation(facts, best_t, best_a)
    cycles = machine.check_compilation(program, final)
    for case in program["cases"]:
        machine.check_case(program, final, case)
    scratch = machine.scratch_footprint(program, final)
    queries = []
    for learner in learners:
        summary = learner.summary()
        queries.append({
            "status": summary["status"], "observed_distinct_at_boundary": (
                summary["boundary"] or {}).get("observed_distinct"),
            "reached_boundary": summary["boundary"] is not None,
            "distinct_validated": summary.get("distinct"),
            "reached_20_validated": (summary.get("distinct") or 0) >= sr.MIN_TRAINING,
            "query_remaining_seconds": (summary["boundary"] or {}).get(
                "query_remaining_seconds"),
            "global_remaining_seconds": (summary["boundary"] or {}).get(
                "global_remaining_seconds"),
            "validations": summary["validations"], "timers": summary["timers"],
            "proposed": summary["proposed"], "model_seconds": summary["seconds"]})
    totals = {name: sum(q["timers"][name] for q in queries)
              for name in ("validation", "encode", "pool", "fit", "order")}
    totals["construction"] = timers.get("construction", 0.0)
    totals["constructions"] = timers.get("constructions", 0)
    return {"kind": KIND + "_result", "program_name": program["name"],
            "program_sha256": spec["program_sha256"], "budget_seconds": budget,
            "cycles": cycles, "scratch": scratch, "product": cycles * scratch,
            "compile_seconds": compile_seconds, "optimisation_seconds": record["seconds"],
            "queries_with_learner": len(queries),
            "queries_reaching_boundary": sum(q["reached_boundary"] for q in queries),
            "queries_reaching_20_validated": sum(q["reached_20_validated"] for q in queries),
            "queries_observing_20_at_boundary": sum(
                (q["observed_distinct_at_boundary"] or 0) >= sr.MIN_TRAINING for q in queries),
            "cost_totals_seconds": totals, "queries": queries[:512],
            "accepted": record["accepted"],
            "model_improvements": sum(1 for i in record["improvements"]
                                      if i.get("source") == "model"),
            "interrupted_validation_total": record["interrupted_validation_total"],
            "discrepancy_count": record["discrepancy_count"],
            "correctness": "PASS" if record["discrepancy_count"] == 0 else "FAIL"}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--spec", required=True)
    args = parser.parse_args(argv)
    try:
        result = measure(json.loads(args.spec))
    except Exception as exc:  # retained by the harness as a failed row
        print(f"acquisition failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    sys.stdout.write(se.canonical_json(result) + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
