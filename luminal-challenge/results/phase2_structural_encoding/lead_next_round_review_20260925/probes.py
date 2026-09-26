"""Read-only lead probes for the completed next-round release.

From luminal-challenge: PYTHONPATH=.reference:. ../venv/bin/python <this file>
Writes only LEAD_PROBES.json alongside this script. Original files are unchanged.
"""
import copy
import importlib.util
import json
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/phase2_structural_encoding/next_round_20260925"


def construction_probe():
    import direct_compiler as compiler
    import direct_contract as contract
    from research import next_round_search as search, structural_encoding as encoding
    from tests_direct import generate_programs

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
    return {"construction_interruption_count": report["construction_interruption_count"],
            "overshoot_seconds": report["overshoot_seconds"],
            "statuses": report["statuses"],
            "late_queries": [q for q in report["queries"] if q["active_seconds"] > 0]}


def audit_gate_probe():
    spec = importlib.util.spec_from_file_location("lead_audit", ROOT / "research/next_round_audit.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    audit = module.Audit(RUN)
    original = audit.load

    def altered(name):
        value = original(name)
        if name == "LEARNING_FEASIBILITY.json" and value:
            value = copy.deepcopy(value)
            value["contrasts"]["mechanism_signal"] = "PASS"
            for item in value["contrasts"].values():
                if isinstance(item, dict) and "interval_98_333" in item:
                    item["passes"] = True
                    item["interval_98_333"][1] = 999.0
        return value

    audit.load = altered
    result = audit.run_all()
    return {"mutation": "false mechanism/component PASS and fabricated learning upper intervals",
            **result}


if __name__ == "__main__":
    result = {"construction": construction_probe(), "false_gate": audit_gate_probe()}
    Path(__file__).with_name("LEAD_PROBES.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"construction_count": result["construction"]["construction_interruption_count"],
                      "mutated_audit_status": result["false_gate"]["status"]}))
