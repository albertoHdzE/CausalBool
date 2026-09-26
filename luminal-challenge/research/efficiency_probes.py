"""The lead's two probes, before and after the repairs (efficiency phase, Gate R).

Read-only: nothing measured or historical is edited. ``before`` runs the lead's
probes against what the lead probed (the parent solver ``next_round_search``
and the historical auditor ``next_round_audit``); ``after`` runs the same probes
against the repairs (``efficiency_search`` R0 and ``efficiency_audit``). The
construction probe is the lead's ``construction_probe`` with the module
swapped; the audit probe is the lead's in-memory report substitution.

Usage::

    PYTHONPATH=.reference:. python -m research.efficiency_probes --out DIR
"""

from __future__ import annotations

import argparse
import copy
import importlib.util
import json
from pathlib import Path
from unittest import mock

import direct_compiler as compiler
import direct_contract as contract

from research import efficiency_common as ec
from research import efficiency_search as es
from research import next_round_search as nrs
from research import structural_encoding as encoding

from tests_direct import generate_programs

RUN = ec.NEXT_ROUND_RUN


def construction_probe(search) -> dict:
    program = generate_programs.additional_program(800000)
    facts = contract.derive(program)
    compiled, _ = compiler.compile_with_report(program, compiler.DEFAULT_LIMITS, optimise=False)
    times = encoding.issue_cycles_of(program, compiled["bundles"])
    state = {"late": False}
    original = search.product_caps

    def late_caps(*args, **kwargs):
        result = original(*args, **kwargs)
        if result["status"] == "NO_STRICT_IMPROVEMENT":
            state["late"] = True
        return result

    with mock.patch.object(search, "product_caps", late_caps):
        _, _, report = search.multiscale_optimise(
            program, facts, times, dict(compiled["scratch"]), budget_seconds=0.1,
            clock=lambda: 1.0 if state["late"] else 0.0)
    assert state["late"]
    keys = ("construction_interruption_count", "construction_overrun_count",
            "construction_overrun_past_deadline_seconds", "late_terminal_reasons",
            "overshoot_seconds", "statuses", "accepted")
    return {"module": search.__name__, "version": search.VERSION,
            **{k: report.get(k, "<absent>") for k in keys},
            "late_queries": [q for q in report["queries"] if q["active_seconds"] > 0]}


def _module(path: Path, name: str):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _mutate(value):
    value = copy.deepcopy(value)
    value["contrasts"]["mechanism_signal"] = "PASS"
    for item in value["contrasts"].values():
        if isinstance(item, dict) and "interval_98_333" in item:
            item["passes"] = True
            item["interval_98_333"][1] = 999.0
    return value


def audit_probe(historical: bool) -> dict:
    if historical:
        module = _module(ec.ROOT / "research/next_round_audit.py", "lead_audit_before")
        audit = module.Audit(RUN)
        original = audit.load

        def altered(name):
            value = original(name)
            return _mutate(value) if name == "LEARNING_FEASIBILITY.json" and value else value

        audit.load = altered
    else:
        module = _module(ec.ROOT / "research/efficiency_audit.py", "lead_audit_after")
        audit = module.Audit(RUN)
        original = audit._read_report

        def altered(name):
            value = original(name)
            return _mutate(value) if name == "LEARNING_FEASIBILITY.json" and value else value

        audit.loader = altered
    result = audit.run_all()
    return {"auditor": module.__file__, "mutation": "false mechanism/component PASS and "
            "fabricated learning upper intervals", "status": result["status"],
            "checks": result["checks"], "finding_codes": result["finding_codes"],
            "findings_first": result["findings"][:6],
            "not_audited": result.get("not_audited"),
            "complete_coverage_claimed": result.get("complete_coverage_claimed")}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)
    out = {"before": {"construction": construction_probe(nrs), "false_gate": audit_probe(True)},
           "after": {"construction": construction_probe(es), "false_gate": audit_probe(False)}}
    path = Path(args.out)
    path.mkdir(parents=True, exist_ok=True)
    (path / "LEAD_PROBES_BEFORE_AFTER.json").write_text(json.dumps(out, indent=2) + "\n")
    print(json.dumps({
        "before": {"construction_count": out["before"]["construction"][
            "construction_interruption_count"], "audit": out["before"]["false_gate"]["status"]},
        "after": {"construction_count": out["after"]["construction"][
            "construction_interruption_count"], "overrun_count": out["after"]["construction"][
            "construction_overrun_count"], "audit": out["after"]["false_gate"]["status"],
            "audit_codes": out["after"]["false_gate"]["finding_codes"]}}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
