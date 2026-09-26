"""The declared stage machine, and the verdict a stage's evidence derives.

One owner for three statements that were previously implicit and disagreed with
each other:

* **the stage machine** -- which stages exist, what each depends on, and which
  stages one command line is *required* to produce;
* **the verdict vocabulary** -- validation failure, inconclusive, pass,
  not-applicable, not-run, blocked;
* **the reconciliation rule** -- a recorded gate label is evidence *about* a run,
  never the run's conclusion. Where the derived verdict and the recorded label
  disagree, the disagreement is the finding.

The 2026-09-23 repair review found that `check_structural_evidence` derived
incompleteness from the recorded statuses in `gates.json`, so editing one label
to `PASS` turned a failed coverage gate into `artifacts_complete=true` with exit
0 while the checker simultaneously reported the coverage shortfall. This module
exists so that no consumer can read a status label where a verdict is required.

It imports nothing from `run_structural_experiments` or
`check_structural_evidence`; both import it. The evidence *validation* itself --
the expensive independent recomputation -- stays in the checker, which owns it;
the runner reaches that validation through the checker's own command line in a
subprocess, so there is one implementation and no import cycle.
"""

from __future__ import annotations

from dataclasses import dataclass, field as _dataclass_field
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple


__all__ = [
    "STAGES",
    "ALL_STAGES",
    "DEPENDENCIES",
    "WORKER_STAGES",
    "INTERNAL_STAGES",
    "RUN_ID_PATTERN",
    "PASS",
    "FAIL",
    "INCONCLUSIVE",
    "NOT_RUN",
    "NOT_APPLICABLE",
    "BLOCKED",
    "VERDICTS",
    "StageOutcome",
    "validate_request",
    "required_stages",
    "derive_blocked",
    "reconcile",
    "completeness",
]


STAGES = ("preflight", "p0", "p1", "p2", "p3", "p4", "p5")
ALL_STAGES = STAGES + ("all",)

# P0 -> P1 -> {P2, P3}; P3's triage -> P4; P2 -> P5. H4 gates only the optional
# P5 model arm, which is why P4 is not a dependency of P5.
DEPENDENCIES: Dict[str, Tuple[str, ...]] = {
    "preflight": (),
    "p0": ("preflight",),
    "p1": ("p0",),
    "p2": ("p1",),
    "p3": ("p1",),
    "p4": ("p1", "p3"),
    "p5": ("p1", "p2"),
}

# Which stages launch measurement subprocesses, and which legitimately run none.
# A stage that runs no subprocess must not fabricate a command record, and a
# stage that launches workers must account for every one of them.
WORKER_STAGES = ("p2", "p4", "p5")
INTERNAL_STAGES = ("preflight", "p0", "p1", "p3")

RUN_ID_PATTERN = re.compile(r"^[A-Za-z0-9_-]+$")

PASS, FAIL, INCONCLUSIVE, NOT_RUN, NOT_APPLICABLE, BLOCKED = (
    "PASS", "FAIL", "INCONCLUSIVE", "NOT_RUN", "NOT_APPLICABLE", "BLOCKED_BY_GATE"
)

# The full vocabulary, in decreasing severity for reporting purposes. It is the
# protocol's `status_values` and is checked against it at load time by the
# checker, so the two cannot drift.
VERDICTS = (FAIL, INCONCLUSIVE, BLOCKED, NOT_RUN, NOT_APPLICABLE, PASS)


@dataclass
class StageOutcome:
    """What one stage's *evidence* establishes, independently of its label.

    ``verdict`` is derived. ``recorded`` is whatever the run wrote down, kept
    beside it so a reviewer can see the disagreement rather than only its
    consequence. ``required`` says whether the recorded command line obliged this
    stage to produce evidence at all.
    """

    stage: str
    verdict: str
    reason: str
    recorded: Optional[str] = None
    required: bool = False
    imported_from: Optional[str] = None
    evidence: Dict[str, object] = _dataclass_field(default_factory=dict)

    def to_row(self) -> dict:
        return {
            "stage": self.stage,
            "verdict": self.verdict,
            "reason": self.reason,
            "recorded": self.recorded,
            "required": self.required,
            "imported_from": self.imported_from,
            "evidence": dict(self.evidence),
        }

    @property
    def agrees(self) -> bool:
        """Whether the recorded label says the same thing as the evidence.

        An imported stage is recorded as ``BLOCKED_BY_GATE``/absent in the new
        run because it did not run there; its verdict comes from the run that
        produced it, so the two are compared through ``reconcile`` rather than
        here.
        """

        return self.recorded is None or self.recorded == self.verdict


def validate_request(request: object) -> List[str]:
    """Check a recorded CLI request against the declared stage machine.

    Returns a list of reasons; empty means the request is well formed. A run that
    records no request, or one naming a stage the machine does not declare, can
    not be checked against a required-stage set, so that is a failure rather than
    an absence.
    """

    reasons: List[str] = []
    if not isinstance(request, dict):
        return ["the run records no command-line request"]
    stage = request.get("stage")
    if stage not in ALL_STAGES:
        reasons.append(
            f"the recorded request names stage {stage!r}, which the stage machine "
            f"does not declare; declared: {list(ALL_STAGES)}"
        )
    run_id = request.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_PATTERN.match(run_id):
        reasons.append(f"the recorded run id {run_id!r} is not a legal run id")
    if "inputs" in request and request["inputs"] is not None and \
            not isinstance(request["inputs"], str):
        reasons.append("the recorded --inputs value is not a path")
    if stage == "all" and request.get("inputs"):
        reasons.append("--inputs applies to a single-stage invocation only")
    return reasons


def required_stages(request: dict) -> Tuple[str, ...]:
    """The stages one command line is obliged to produce evidence for.

    This is the runner's own rule, stated once: ``--stage all`` requires the whole
    machine; any single stage requires preflight and that stage. Deriving it from
    the *recorded request* is what stops a run from being judged complete because
    it silently produced less than it was asked for.
    """

    stage = request.get("stage")
    if stage == "all":
        return STAGES
    if stage == "preflight":
        return ("preflight",)
    if stage in STAGES:
        return ("preflight", stage)
    return ()


def derive_blocked(
    stage: str, verdicts: Dict[str, str]
) -> Optional[List[str]]:
    """Which of ``stage``'s dependencies are not PASS, by derived verdict.

    ``None`` means every dependency is PASS. The list is the blocking reason, and
    it is computed from derived verdicts only: a dependency labelled PASS whose
    evidence says otherwise blocks its dependants exactly as a dependency
    labelled INCONCLUSIVE does.
    """

    blocking = [
        dependency for dependency in DEPENDENCIES.get(stage, ())
        if verdicts.get(dependency) != PASS
    ]
    return blocking or None


def reconcile(outcome: StageOutcome) -> Optional[str]:
    """The reason a recorded label contradicts its evidence, or ``None``.

    The asymmetry is deliberate. A label *weaker* than the evidence (recorded
    INCONCLUSIVE where the evidence passes) is still a contradiction and is
    reported, because the run and its evidence must say the same thing; but the
    dangerous direction, and the one the review reproduced, is a label *stronger*
    than the evidence, and the message names it as such.
    """

    if outcome.recorded is None:
        if outcome.verdict in (NOT_RUN, NOT_APPLICABLE):
            return None
        return (
            f"{outcome.stage} has no recorded gate while its evidence derives "
            f"{outcome.verdict}"
        )
    if outcome.recorded == outcome.verdict:
        return None
    severity = {verdict: index for index, verdict in enumerate(VERDICTS)}
    recorded_rank = severity.get(outcome.recorded, -1)
    derived_rank = severity.get(outcome.verdict, -1)
    if recorded_rank > derived_rank:
        return (
            f"{outcome.stage} is recorded {outcome.recorded} while its evidence "
            f"derives only {outcome.verdict}: {outcome.reason}"
        )
    return (
        f"{outcome.stage} is recorded {outcome.recorded} while its evidence "
        f"derives {outcome.verdict}: {outcome.reason}"
    )


def completeness(
    outcomes: Sequence[StageOutcome], findings: Sequence[object]
) -> dict:
    """Derive the report's completeness fields and exit code from the verdicts.

    ``artifacts_complete`` means every *required* stage's evidence derives PASS
    and nothing contradicts anything else. It is never read off a recorded label,
    and an INCONCLUSIVE required stage keeps it false however that stage is
    labelled.
    """

    required = [outcome for outcome in outcomes if outcome.required]
    failing = [outcome.stage for outcome in required if outcome.verdict == FAIL]
    unmet = [
        outcome.stage for outcome in required
        if outcome.verdict not in (PASS, NOT_APPLICABLE)
    ]
    complete = not findings and not unmet and bool(required)
    if findings or failing:
        exit_code = 1
    elif unmet or not required:
        exit_code = 2
    else:
        exit_code = 0
    return {
        "required_stages": [outcome.stage for outcome in required],
        "required_unmet": unmet,
        "required_failed": failing,
        "artifacts_complete": complete,
        "exit_code": exit_code,
    }


def verdicts_of(outcomes: Iterable[StageOutcome]) -> Dict[str, str]:
    return {outcome.stage: outcome.verdict for outcome in outcomes}
