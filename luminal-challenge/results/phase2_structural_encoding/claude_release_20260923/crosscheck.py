"""Compare the run's COMPARISON.json with the lead's INDEPENDENT_COMPARISON.json.

Reads two JSON artifacts only; imports neither implementation. Every
difference is retained in CROSSCHECK.json with its magnitude; nothing is
rounded away. Usage: python crosscheck.py RUN_DIR INDEPENDENT.json OUT.json
"""
import json
import sys
from pathlib import Path

TOL = 1e-9


def main(run: Path, independent: Path, out: Path) -> int:
    mine = json.loads((run / "COMPARISON.json").read_text())
    lead = json.loads(independent.read_text())
    ours = {(e["corpus"], e["budget_seconds"], e["control"]): e for e in mine["entries"]}
    theirs = {(e["corpus"], e["budget"], e["control"]): e for e in lead["entries"]}
    report = {"entries_run": len(ours), "entries_independent": len(theirs),
              "key_sets_equal": set(ours) == set(theirs), "tolerance": TOL,
              "comparisons": [], "differences": []}
    if not ours or not theirs:
        report["differences"].append("an artifact holds zero entries; nothing was compared")
    for key in sorted(set(ours) & set(theirs), key=str):
        a, b = ours[key], theirs[key]
        checks = {}
        qa, qb = a["quality_log_control_over_candidate"], b["quality_log_control_over_candidate"]
        checks["quality_point"] = (qa.get("point_estimate"), qb["point"])
        checks["quality_ci95_low"] = (qa["intervals"]["0.025-0.975"][0], qb["ci95"][0])
        checks["quality_ci95_high"] = (qa["intervals"]["0.025-0.975"][1], qb["ci95"][1])
        checks["programs"] = (a["n_programs"], qb["programs"])
        checks["families"] = (qa.get("families"), qb["families"])
        checks["wins_ties_losses"] = ([a["wins"], a["ties"], a["losses"]],
                                      [b["wins"], b["ties"], b["losses"]])
        for metric, lead_key in (("compile", "compile_log_candidate_over_control"),
                                 ("process", "process_log_candidate_over_control")):
            ra, rb = a["runtime_log_candidate_over_control"][metric], b[lead_key]
            checks[f"{metric}_point"] = (ra.get("point_estimate"), rb["point"])
            checks[f"{metric}_ci95"] = (ra["intervals"]["0.025-0.975"], rb["ci95"])
        entry = {"key": list(key), "fields": {}}
        for field, (x, y) in checks.items():
            if isinstance(x, (int, float)) and isinstance(y, (int, float)) and not isinstance(x, bool):
                delta = abs(x - y)
                agree = delta <= TOL
            elif isinstance(x, list) and all(isinstance(v, float) for v in x + y):
                delta = max(abs(p - q) for p, q in zip(x, y))
                agree = len(x) == len(y) and delta <= TOL
            else:
                delta = None
                agree = x == y
            entry["fields"][field] = {"run": x, "independent": y, "abs_delta": delta, "agree": agree}
            if not agree:
                report["differences"].append({"key": list(key), "field": field, "run": x,
                                              "independent": y, "abs_delta": delta})
        # Program-level classification: sign of every per-program quality ratio.
        # The lead auditor keys by program digest; the run keys the same way.
        lead_per_program = b["per_program_quality"]
        run_primary = None
        if key == ("heldout", 0.1, "accepted_budgeted"):
            run_primary = mine["primary_h2"]["analysis"]["per_program_log_ratio"]
        entry["program_level_available_in_run"] = run_primary is not None
        if run_primary is not None:
            sign = lambda v: (v > 0) - (v < 0)
            mismatched = [p for p in lead_per_program
                          if p not in run_primary or sign(run_primary[p]) != sign(lead_per_program[p])
                          or abs(run_primary[p] - lead_per_program[p]) > TOL]
            entry["primary_program_level_mismatches"] = mismatched
            entry["primary_programs_compared"] = len(lead_per_program)
            if mismatched:
                report["differences"].append({"key": list(key), "field": "per_program_quality",
                                              "programs": mismatched})
        report["comparisons"].append(entry)
    report["agree"] = report["key_sets_equal"] and not report["differences"] and len(ours) == 24
    Path(out).open("x").write(json.dumps(report, indent=2) + "\n")
    print(f"entries={len(report['comparisons'])} differences={len(report['differences'])} "
          f"agree={report['agree']}")
    return 0 if report["agree"] else 1


if __name__ == "__main__":
    sys.exit(main(Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])))
