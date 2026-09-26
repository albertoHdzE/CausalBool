"""Lead review probes; run from luminal-challenge with PYTHONPATH=.reference:. ."""
import collections
import hashlib
import json
import math
from pathlib import Path
import statistics
from unittest import mock

ROOT = Path(__file__).resolve().parents[3]
BASE = ROOT / "results/phase2_structural_encoding"
RUN = BASE / "objective_index_20260924"


def rows(path):
    with path.open() as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def recount():
    serial = {(r["program_sha256"], r["repetition"]): r["cycles"] * r["scratch"]
              for r in rows(RUN / "stages/EVAL_public_serial/rows.jsonl")}
    grouped = collections.defaultdict(list)
    for name, path in (("new", RUN / "stages/EVAL_public/rows.jsonl"),
                       ("earlier", BASE / "optimization_20260924/stages/D_public/rows.jsonl")):
        for r in rows(path):
            if ((r["arm"] in ("A4_multiscale_search", "A0_frozen_phase2", "selected_nonmodel")
                 and r["budget_seconds"] == 0.1)
                    or (r["arm"] in ("accepted_default", "classical")
                        and r["budget_seconds"] is None)):
                assert not r["failed_row"]
                grouped[name, r["arm"], r["repetition"]].append(
                    math.log(serial[r["program_sha256"], r["repetition"]]
                             / (r["cycles"] * r["scratch"])))
    public = {}
    for name, arm in sorted({(n, a) for n, a, rep in grouped}):
        assert all(len(grouped[name, arm, rep]) == 8 for rep in range(15))
        public[f"{name}/{arm}"] = [math.exp(statistics.mean(grouped[name, arm, rep]) / 2)
                                   for rep in range(15)]
    cells = {}
    for r in rows(RUN / "stages/EVAL_compiler/rows.jsonl"):
        if ((r["budget_seconds"] == 0.1 and r["arm"] in (
                "A4_multiscale_search", "A0_frozen_phase2", "accepted_budgeted"))
                or r["arm"] == "classical"):
            assert not r["failed_row"] and r["product"] == r["cycles"] * r["scratch"]
            key = r["seed"], r["repetition"], r["arm"]
            assert key not in cells
            cells[key] = r
    fresh = {}
    for arm in ("A0_frozen_phase2", "accepted_budgeted", "classical"):
        effects, costs = [], []
        for seed in range(910000, 910200):
            effects.append(statistics.mean(math.log(
                cells[seed, rep, arm]["product"]
                / cells[seed, rep, "A4_multiscale_search"]["product"]) for rep in range(15)))
            costs.append(math.log(statistics.median(
                cells[seed, rep, "A4_multiscale_search"]["result"]["compile_seconds"]
                for rep in range(15)) / statistics.median(
                    cells[seed, rep, arm]["result"]["compile_seconds"] for rep in range(15))))
        # Each of the five families has exactly 40 programs: this is also the
        # equal-family mean prescribed by the protocol.
        effect = statistics.mean(effects)
        fresh[arm] = {"log_effect": effect, "geometric_J_reduction": 1 - math.exp(-effect),
                      "compile_ratio": math.exp(statistics.mean(costs)),
                      "wins_ties_losses": [sum(v > 1e-12 for v in effects),
                                           sum(abs(v) <= 1e-12 for v in effects),
                                           sum(v < -1e-12 for v in effects)]}
    headroom = []
    for path in sorted((RUN / "fixtures/evaluation").glob("*/split.json")):
        split = json.loads(path.read_text())
        oracle = json.loads((path.parent / "oracle.json").read_text())
        products = {r["identity"]: r["product"] for r in oracle["feasible"]}
        headroom.append(min(products[k] for k in split["test"])
                        < min(products[k] for k in split["train"]))
    assert len(headroom) == 30
    return {"public_scores": public, "fresh_primary": fresh,
            "learning_fixtures": len(headroom), "fixtures_with_test_headroom": sum(headroom)}


def interrupted_validation():
    import machine
    import direct_compiler as compiler
    import direct_contract as contract
    from research import objective_index_search as search, structural_encoding as encoding
    from tests_direct import generate_programs

    program = generate_programs.additional_program(800004)
    facts = contract.derive(program)
    compiled, _ = compiler.compile_with_report(program, compiler.DEFAULT_LIMITS, optimise=False)
    times = encoding.issue_cycles_of(program, compiled["bundles"])
    addresses = dict(compiled["scratch"])
    state = {"expired": False, "candidate": False, "checks": 0, "internal_interrupted": 0}
    real_check, real_consider = machine.check_compilation, search._Acceptor.consider

    def late_check(program, compiled):
        result = real_check(program, compiled)
        if state["candidate"]:
            state["expired"] = True
            state["checks"] += 1
        return result

    def consider(self, node):
        state["candidate"] = True
        try:
            return real_consider(self, node)
        finally:
            state["candidate"] = False
            state["internal_interrupted"] = self.report.interrupted_validations

    with mock.patch.object(machine, "check_compilation", late_check), \
            mock.patch.object(search._Acceptor, "consider", consider):
        _, _, report = search.multiscale_optimise(
            program, facts, times, addresses, budget_seconds=5.0,
            clock=lambda: 10.0 if state["expired"] else 0.0)
    assert state["internal_interrupted"] == 1 and report["accepted"] == 0
    return {"internal_interrupted_validations": state["internal_interrupted"],
            "accepted": report["accepted"],
            "reported_interrupted_attempt_count": report["interrupted_attempt_count"],
            "reported_interrupted_attempts": report["interrupted_attempts"],
            "statuses": report["statuses"],
            "reporting_defect_reproduced": report["interrupted_attempt_count"] == 0}


if __name__ == "__main__":
    result = recount()
    result["interruption_probe"] = interrupted_validation()
    source = ROOT / "research/objective_index_search.py"
    result["reviewed_search_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    Path(__file__).with_name("PROBES.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps({"recount": "PASS", "interruption_probe": result["interruption_probe"]}))
