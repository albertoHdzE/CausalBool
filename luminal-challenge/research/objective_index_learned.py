"""The conditional end-to-end learned compiler pair (protocol section 9).

Executed ONLY if the fixture gate H_LEARN passes. Implemented and frozen before
any fixture evaluation, as the protocol requires; passing the gate enables
execution, not development.

Per query of the selected solver (the solver's own controller calls these hooks
through ``learner_factory``): the first half of the query allowance is ordinary
non-model search whose distinct completed candidates are observed; the second
half case-validates those observations (they become the only labelled data),
requires at least 20 distinct validated objects, builds the SAME common pool and
depth-3 schema tree as the fixture study (``schema_ranker``), and walks the
tree-ordered pool. ``tree`` and ``shuffled_tree`` differ only in the label
permutation. Query domains and encodings are frozen throughout; no fixture
oracle or training data enters a compilation; no deadline is renewed. With too
little data, or once the pool is exhausted, the controller spends what remains
on non-model search.
"""

from __future__ import annotations

import time
from typing import Callable, Dict, List, Optional, Tuple

import machine

import direct_contract as dc

from research import objective_index_search as ois
from research import schema_ranker as sr
from research import structural_encoding as se


MODES = ("tree", "shuffled_tree")


class QueryLearner:
    """One query's observations, model and proposal walk."""

    def __init__(self, domain: se.Domain, mode: str,
                 clock: Callable[[], float] = time.perf_counter) -> None:
        if mode not in MODES:
            raise ValueError(f"unknown learned mode {mode!r}")
        self.domain = domain
        self.mode = mode
        self.clock = clock
        self.observations: Dict[str, dict] = {}
        self.validations = 0
        self.validation_budget = 10**9
        self.rejected: List[dict] = []
        self.status: Optional[str] = None
        self.reason = ""
        self.continued: Optional[str] = None
        self.queue: List[int] = []
        self.position = 0
        self.proposed = 0
        self.complete = 0
        self.info: dict = {}
        self.seconds = {"prepare": 0.0, "step": 0.0}

    # -- search phase ------------------------------------------------------

    def observe(self, item: dict) -> None:
        identity = item["identity"]
        if identity not in self.observations:
            self.observations[identity] = {"compilation": item["compilation"],
                                           "product": item["product"]}

    # -- model phase ---------------------------------------------------------

    def _validate(self, compilation: dict) -> bool:
        self.validations += 1
        try:
            machine.check_compilation(self.domain.program, compilation)
            for case in self.domain.program["cases"]:
                machine.check_case(self.domain.program, compilation, case)
        except (machine.CompileError, machine.ProgramError) as exc:
            self.rejected.append({"identity": se.object_digest(compilation), "error": str(exc),
                                  "source": f"learned_{self.mode}"})
            return False
        return True

    def prepare(self, deadline: float) -> str:
        """Validate observations, then build pool and tree; returns a status."""

        started = self.clock()
        try:
            return self._prepare(deadline)
        finally:
            self.seconds["prepare"] += self.clock() - started

    def _prepare(self, deadline: float) -> str:
        labelled: List[Tuple[int, int]] = []
        for identity, item in self.observations.items():
            if self.clock() >= deadline:
                return self._set("EXPIRED", "the allowance ended while validating observations")
            if self.validations >= self.validation_budget:
                return self._set("VALIDATION_CEILING", "aggregate validation ceiling")
            if not self._validate(item["compilation"]):
                continue
            try:
                index = se.encode(self.domain, item["compilation"], sr.CODEC)
            except se.DomainError as exc:
                self.rejected.append({"identity": identity, "error": f"encode: {exc}",
                                      "source": f"learned_{self.mode}"})
                continue
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
            pool = sr.candidate_pool(bits, indices, elite, seeds["pool"], check)
            fit = y if self.mode == "tree" else sr.shuffled_labels(y, seeds["shuffled"])
            check()
            tree = sr.fit_tree(bits, indices, fit)
            check()
            self.queue = sr.order_pool(pool["pool"], "tree", tree=tree)
        except TimeoutError:
            return self._set("EXPIRED", "the allowance ended while building the model")
        self.info.update(threshold=threshold, elite=len(elite), pool=pool["size"],
                         pool_sha256=pool["pool_sha256"],
                         ordering_sha256=sr.ordering_digest(self.queue),
                         leaves=len(tree.leaves))
        return self._set("READY", "")

    def _set(self, status: str, reason: str) -> str:
        self.status, self.reason = status, reason
        return status

    def step(self, best_product: int, until: float, hard_deadline: Optional[float] = None,
             first_only: bool = True) -> tuple:
        """Walk proposals until ``until``; validate only strict improvements.

        Returns ``("improved", times, addresses, product)``, ``("exhausted",)``
        or ``("deadline",)``. A candidate is credited only when fully validated
        before ``hard_deadline`` (default ``until``); the slice quantum is not
        an acceptance deadline.
        """

        started = self.clock()
        hard = until if hard_deadline is None else hard_deadline
        best = None
        try:
            while self.position < len(self.queue):
                if self.clock() >= until:
                    return self._finish_step(best, ("deadline",))
                index = self.queue[self.position]
                self.position += 1
                self.proposed += 1
                result = se.decode(self.domain, index, sr.CODEC)
                if result.status != se.COMPLETE:
                    continue
                self.complete += 1
                if result.product >= best_product:
                    continue
                if self.clock() >= hard or self.validations >= self.validation_budget:
                    return self._finish_step(best, ("deadline",))
                if not self._validate(result.compilation):
                    continue
                if self.clock() >= hard:
                    self.info["late_validations"] = self.info.get("late_validations", 0) + 1
                    return self._finish_step(best, ("deadline",))
                best = (dict(result.times), dict(result.addresses), result.product)
                best_product = result.product
                if first_only:
                    return self._finish_step(best, ("exhausted",))
            return self._finish_step(best, ("exhausted",))
        finally:
            self.seconds["step"] += self.clock() - started

    @staticmethod
    def _finish_step(best, otherwise: tuple) -> tuple:
        if best is not None:
            return ("improved",) + best
        return otherwise

    def summary(self) -> dict:
        return {"mode": self.mode, "status": self.status, "reason": self.reason,
                "validations": self.validations, "rejected": len(self.rejected),
                "proposed": self.proposed, "complete": self.complete,
                "continued_search": self.continued, "seconds": dict(self.seconds),
                **self.info}


class _SequentialLearner(QueryLearner):
    """The sequential controllers keep the best model proposal of the half."""

    def step(self, best_product, until, hard_deadline=None, first_only=False):
        return super().step(best_product, until, hard_deadline, first_only=False)


def optimise(program: dict, facts: dc.ProgramFacts, times: Dict[int, int],
             addresses: Dict[str, int], *, arm: str, budget_seconds: float, labels_mode: str,
             **kwargs) -> Tuple[Dict[int, int], Dict[str, int], dict]:
    """The selected solver with the learned query policy."""

    if labels_mode not in MODES:
        raise ValueError(labels_mode)
    if arm == "A4_multiscale_search":
        best_t, best_a, record = ois.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=budget_seconds,
            learner_factory=lambda domain: QueryLearner(domain, labels_mode), **kwargs)
    else:
        best_t, best_a, record = ois.sequential_optimise(
            program, facts, times, addresses, arm=arm, budget_seconds=budget_seconds,
            learner_factory=lambda domain: _SequentialLearner(domain, labels_mode), **kwargs)
    record["learned_mode"] = labels_mode
    models = [q.get("model") for q in record.get("queries", []) if q.get("model")]
    record["learned_summary"] = {
        "queries_with_model_state": len(models),
        "statuses": {s: sum(1 for m in models if m.get("status") == s)
                     for s in sorted({m.get("status") for m in models}, key=str)},
        "model_improvements": sum(1 for i in record.get("improvements", [])
                                  if i.get("source") == "model"),
        "validations": sum(m.get("validations", 0) for m in models)}
    return best_t, best_a, record
