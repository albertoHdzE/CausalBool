"""Standalone acceptance of successor arms on the 142-program direct corpus.

For each requested arm, every corpus program (public 8, regression 30,
additional 100, stress 4; 277 cases) is compiled from the original direct
bootstrap at the given optimisation budget, and the returned compilation is
checked by the pinned machine on every case. A program passes when the
compilation validates, J never exceeds its bootstrap J, no validator
rejection was seen during search and the budget was never renewed. The
denominator is printed and an empty corpus fails.

Arms: the four ablation cells by label, ``engineered:<cell>`` for the Stage E
variant, or ``export:<path>`` for an exported standalone compiler module
(loaded from its file, isolated from ``research``).

Usage::

    PYTHONPATH=.reference:. python -m research.next_round_acceptance --arm LABEL \
        [--budget 0.1] --output FILE
"""

from __future__ import annotations

import argparse
import importlib
import importlib.util
import json
import sys
import time
from pathlib import Path

import machine

import direct_compiler as dcomp
import direct_contract as dc

from research import next_round_common as nrc
from research import structural_encoding as se

from tests_direct import generate_programs as gp


def corpus():
    out = []
    for label, programs in (("public", gp.public_programs()),
                            ("regression", gp.regression_programs()),
                            ("additional", gp.additional_programs()),
                            ("stress", gp.stress_programs())):
        out.extend((label, program) for program in programs)
    return out


def compile_with(arm: str, program: dict, budget: float):
    facts = dc.derive(program)
    compiled, _ = dcomp.compile_with_report(program, dcomp.DEFAULT_LIMITS, optimise=False)
    times = se.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    j0 = (max(times.values()) + 1) * dc.footprint(facts, addresses)
    if arm.startswith("export:"):
        path = Path(arm.split(":", 1)[1])
        spec = importlib.util.spec_from_file_location("exported_compiler", path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        result = module.compile_program(program)
        return result, j0, {"discrepancy_count": 0, "budget_renewals": 0}
    if arm.startswith("engineered:"):
        module = importlib.import_module("research.next_round_engineered")
        cell = nrc.CELLS[arm.split(":", 1)[1]]
    else:
        module = importlib.import_module("research.next_round_search")
        cell = nrc.CELLS[arm]
    best_t, best_a, record = module.multiscale_optimise(
        program, facts, times, addresses, budget_seconds=budget, catalog=cell["catalog"],
        traversal=cell["traversal"])
    return dc.compilation(facts, best_t, best_a), j0, record


def accept(arm: str, budget: float) -> dict:
    programs = corpus()
    rows, failures = [], []
    cases_checked = 0
    for label, program in programs:
        started = time.perf_counter()
        try:
            compiled, j0, record = compile_with(arm, program, budget)
            cycles = machine.check_compilation(program, compiled)
            for case in program["cases"]:
                machine.check_case(program, compiled, case)
                cases_checked += 1
            scratch = machine.scratch_footprint(program, compiled)
            ok = (cycles * scratch <= j0 and record["discrepancy_count"] == 0
                  and record["budget_renewals"] == 0)
            row = {"corpus": label, "name": program["name"], "J": cycles * scratch,
                   "bootstrap_J": j0, "cases": len(program["cases"]),
                   "seconds": time.perf_counter() - started, "pass": ok}
        except Exception as exc:  # retained as a failure, never skipped
            row = {"corpus": label, "name": program["name"], "pass": False,
                   "error": f"{type(exc).__name__}: {exc}"}
        rows.append(row)
        if not row["pass"]:
            failures.append(row)
    status = "PASS" if programs and not failures and cases_checked == sum(
        len(p["cases"]) for _, p in programs) else "FAIL"
    return {"arm": arm, "budget_seconds": budget, "programs": len(programs),
            "cases_checked": cases_checked, "failures": failures,
            "improved_programs": sum(1 for r in rows if r.get("J", 0) < r.get("bootstrap_J", 0)),
            "status": status, "rows": rows}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--arm", required=True)
    parser.add_argument("--budget", type=float, default=nrc.PRIMARY_BUDGET)
    parser.add_argument("--output", required=True)
    args = parser.parse_args(argv)
    report = accept(args.arm, args.budget)
    Path(args.output).write_text(json.dumps(report, indent=1, sort_keys=True) + "\n")
    print(json.dumps({k: report[k] for k in ("arm", "programs", "cases_checked", "status",
                                             "improved_programs")}
                     | {"failures": len(report["failures"])}))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
