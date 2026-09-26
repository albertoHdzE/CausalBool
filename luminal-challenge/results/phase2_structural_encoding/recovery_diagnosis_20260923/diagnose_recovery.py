"""Read-only D0 replay and aggregation for the accepted Phase 2 run."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).resolve().parents[3]
RUN = ROOT / "results/phase2_structural_encoding/phase2_repair_20260923c"
OUT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / ".reference"))
sys.path.insert(0, str(ROOT))
import machine
import direct_compiler as dcomp
import direct_contract as dc
from research import structural_encoding as se
from research import run_structural_experiments as runner


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def public_domain(name):
    path = ROOT / ".reference/programs" / name
    program = machine.load_program(path)
    facts = dc.derive(program)
    incumbent, report = dcomp.compile_with_report(
        program, dcomp.DEFAULT_LIMITS, optimise=False
    )
    record = runner.whole_program_record(name, "public", program, facts, incumbent)
    return program, facts, incumbent, report, se.Domain.from_record(record)


def prefix_failure_trace(domain, index):
    result = se.decode(domain, index, "structural_rank")
    trace = [dict(x) for x in result.decisions]
    item = {
        "index": str(index),
        "status": result.status,
        "reason": result.reason,
        "decisions_consumed": len(trace),
        "decisions": trace,
    }
    m = re.fullmatch(r"\('time', (\d+)\): no legal option remains", result.reason)
    if not m:
        item["terminal_constraint"] = "not an empty time-option list"
        return item
    op_id = int(m.group(1))
    times = {d["key"]: d["chosen"] for d in trace if d["kind"] == "time"}
    facts = domain.facts
    engine = facts.engine[op_id]
    limit = machine.ENGINE_LIMITS[engine]
    usage = Counter((facts.engine[k], v) for k, v in times.items())
    rejected = Counter()
    by_candidate = []
    for cycle in domain.ordered_domain(("time", op_id)):
        causes = []
        for pred, lag in facts.predecessors[op_id].items():
            ready = times[pred] + lag
            if cycle < ready:
                causes.append({"kind": "precedence", "predecessor": pred,
                               "candidate": cycle, "ready": ready})
        occupied = usage[(engine, cycle)]
        if occupied >= limit:
            causes.append({"kind": "engine_capacity", "engine": engine,
                           "cycle": cycle, "occupied": occupied, "limit": limit})
        for cause in causes:
            rejected[cause["kind"]] += 1
        by_candidate.append({"cycle": cycle, "causes": causes})
    item.update({
        "terminal_constraint": "time_options empty under exact local precedence/capacity tests",
        "failed_operation": op_id,
        "engine": engine,
        "engine_issue_limit": limit,
        "selected_prefix_times": {str(k): v for k, v in sorted(times.items())},
        "predecessor_readiness": [
            {"predecessor": pred, "issue_cycle": times[pred], "lag": lag,
             "earliest_legal_cycle": times[pred] + lag}
            for pred, lag in sorted(facts.predecessors[op_id].items())
        ],
        "cycles_surviving_precedence": [
            cycle for cycle in domain.ordered_domain(("time", op_id))
            if all(cycle >= times[pred] + lag
                   for pred, lag in facts.predecessors[op_id].items())
        ],
        "engine_cycles_saturated_by_prefix": [
            {"cycle": cycle, "occupied": usage[(engine, cycle)], "limit": limit}
            for cycle in domain.ordered_domain(("time", op_id))
            if usage[(engine, cycle)] >= limit
        ],
        "candidate_cycle_count": len(domain.ordered_domain(("time", op_id))),
        "rejection_cause_counts_nonexclusive": dict(rejected),
        "candidate_rejection_trace": by_candidate,
    })
    return item


def main():
    started = time.perf_counter()
    summary = json.loads((RUN / "p1/summary.json").read_text())
    streams = { (x["program_name"], x["stream"]): x
                for x in map(json.loads, (RUN / "p1/sampling_streams.jsonl").open()) }
    aggregates = defaultdict(lambda: {
        "attempts": 0, "status": Counter(), "depth": Counter(),
        "status_depth": defaultdict(Counter), "terminal": Counter(),
        "terminal_reason_exact": Counter(), "reason_kind": Counter(),
        "phase": Counter(), "case_checks": 0, "case_failures": 0,
        "unique_complete": set(), "complete_depth": Counter(),
    })
    first_path_rows = {}
    with (RUN / "p1/sampling_attempts.jsonl").open() as f:
        for line in f:
            row = json.loads(line)
            key = (row["program"], row["stream"])
            a = aggregates[key]
            a["attempts"] += 1
            status, depth = row["status"], row["decisions"]
            a["status"][status] += 1
            a["depth"][depth] += 1
            a["status_depth"][status][depth] += 1
            a["case_checks"] += row["cases_checked"]
            a["case_failures"] += row["case_failures"]
            reason = row["reason"]
            a["terminal_reason_exact"][reason] += 1
            m = re.match(r"\('([^']+)', ([^)]*)\): (.*)", reason)
            if m:
                kind, field, tail = m.groups()
                phase = "schedule" if kind == "time" else "allocation"
                a["phase"][phase] += 1
                a["terminal"][(status, kind, field)] += 1
                if tail == "no legal option remains":
                    reason_kind = "empty_legal_option_list"
                elif "rank " in tail and " is past " in tail:
                    reason_kind = "rank_out_of_legal_range"
                elif "is outside the declared domain" in tail:
                    reason_kind = "physical_value_out_of_declared_domain"
                elif "is declared but not legal in this state" in tail:
                    reason_kind = "declared_but_state_illegal"
                else:
                    reason_kind = tail.split(":", 1)[0]
                a["reason_kind"][(status, kind, field, reason_kind)] += 1
            else:
                a["phase"]["complete" if status == "COMPLETE" else "predecision"] += 1
            if status == "COMPLETE":
                a["unique_complete"].add(row["compilation_sha256"])
                a["complete_depth"][depth] += 1
            if row["stream"] == "option_paths" and row["attempt"] == 0:
                first_path_rows[row["program"]] = row

    public = {}
    for row in summary["public_coverage"]:
        name = row["program"]
        program, facts, incumbent, report, domain = public_domain(name)
        machine.check_compilation(program, incumbent)
        checked_cases = 0
        for case in program["cases"]:
            machine.check_case(program, incumbent, case)
            checked_cases += 1
        normal = se.normalise_compilation(facts, incumbent)
        codec_roundtrips = {}
        for codec in se.CODECS:
            code = se.encode(domain, normal, codec)
            decoded = se.decode(domain, code, codec)
            machine.check_compilation(program, decoded.compilation)
            decoded_cases = 0
            for case in program["cases"]:
                machine.check_case(program, decoded.compilation, case)
                decoded_cases += 1
            codec_roundtrips[codec] = {
                "status": decoded.status,
                "same_normalized_identity":
                    se.canonical_json(decoded.compilation) == se.canonical_json(normal),
                "canonical_reencode": se.encode(domain, decoded.compilation, codec) == code,
                "cycles": decoded.cycles, "scratch": decoded.scratch,
                "product": decoded.product, "case_checks": decoded_cases,
            }
        path_first = first_path_rows[name]
        path_stream = runner.stream_draw(domain, "structural_rank", "option_paths",
                                         int(streams[(name, "option_paths")]["seed"]))
        assert str(path_first["index"]) == str(path_stream())
        public[name] = {
            "program_sha256": row["program_sha256"],
            "domain_sha256": domain.digest(),
            "structural_rank_bits": row["bits"],
            "bootstrap": {
                "compiler_report_bootstrap_seconds": report.get("bootstrap", {}).get("seconds"),
                "machine_validation": "PASS",
                "case_checks": checked_cases,
                "codecs": codec_roundtrips,
            },
            "original_random_union": row["distinct_complete_union"],
            "minimum": summary["coverage_minimum"],
            "first_option_path_failure": prefix_failure_trace(
                domain, int(path_first["index"])
            ),
        }

    stream_report = []
    raw_fraction_samples = defaultdict(Counter)
    for (program, stream), a in sorted(aggregates.items()):
        stream_meta = streams[(program, stream)]
        terminal = [
            {"status": s, "kind": kind, "field": field, "count": count}
            for (s, kind, field), count in sorted(a["terminal"].items())
        ]
        reasons = [
            {"status": s, "kind": kind, "field": field, "reason_kind": why,
             "count": count}
            for (s, kind, field, why), count in sorted(a["reason_kind"].items())
        ]
        status_depth = {
            s: {str(depth): count for depth, count in sorted(dist.items())}
            for s, dist in sorted(a["status_depth"].items())
        }
        if stream == "raw_bits":
            domain = public_domain(program)[-1]
            layout = se.layout(domain, "structural_rank")
            for (_, kind, field, why), count in a["reason_kind"].items():
                if kind == "time" and why == "rank_out_of_legal_range":
                    exact = a["terminal_reason_exact"]
                    for reason, reason_count in exact.items():
                        m = re.fullmatch(
                            rf"\('time', {re.escape(str(field))}\): rank (\d+) is past (\d+) options",
                            reason,
                        )
                        if m:
                            legal_count = int(m.group(2))
                            width = layout.field(("time", int(field))).width
                            raw_fraction_samples[program][
                                (int(field), width, legal_count,
                                 legal_count / (1 << width))
                            ] += reason_count
        stream_report.append({
            "program": program, "stream": stream,
            "attempts_requested": stream_meta["attempts_requested"],
            "attempts_drawn": a["attempts"],
            "elapsed_seconds": stream_meta["seconds"],
            "time_cap_seconds": 60,
            "incomplete": stream_meta["incomplete"],
            "incomplete_reason": stream_meta["incomplete_reason"],
            "outcomes": dict(a["status"]),
            "distinct_complete": len(a["unique_complete"]),
            "case_checks": a["case_checks"], "case_failures": a["case_failures"],
            "decision_depth_by_status": status_depth,
            "terminal_field_counts": terminal,
            "terminal_reason_counts": reasons,
            "complete_depth_counts": dict(sorted(a["complete_depth"].items())),
            "schedule_allocation_phase_counts": dict(a["phase"]),
        })

    raw_artifacts = {}
    for name, expected in summary["raw_artifacts"].items():
        path = RUN / "p1" / name
        actual = sha256(path)
        raw_artifacts[name] = {"sha256": actual, "matches_summary": actual == expected,
                               "bytes": path.stat().st_size}
        assert actual == expected

    payload = {
        "historical_run": str(RUN.relative_to(ROOT)),
        "source_snapshot_digest": json.loads((RUN / "manifest.json").read_text())
            ["source_snapshot"]["snapshot_sha256"],
        "raw_artifacts": raw_artifacts,
        "original_p1": {
            "sampling_attempts": summary["sampling_attempts_drawn"],
            "streams": summary["stream_count"],
            "completions": summary["sampling_completions"],
            "case_checks": summary["sampling_case_checks"],
            "case_failures": summary["sampling_case_failures"],
            "discrepancies": summary["sampling_discrepancy_count"],
            "coverage_minimum": summary["coverage_minimum"],
            "coverage_met": summary["coverage_met"],
        },
        "streams": stream_report,
        "public_programs": public,
        "raw_local_rank_acceptance_examples": {
            name: [
                {"field": f"time:{field}", "width": width,
                 "legal_options": legal,
                 "local_rank_acceptance_fraction": fraction,
                 "terminal_draws": count}
                for (field, width, legal, fraction), count
                in sorted(values.items())
            ] for name, values in raw_fraction_samples.items()
        },
        "diagnostic_elapsed_seconds": round(time.perf_counter() - started, 3),
    }
    (OUT / "DIAGNOSIS.json").write_text(json.dumps(payload, indent=2) + "\n")
    print(json.dumps({"programs": len(public), "streams": len(stream_report),
                      "raw_files_hash_valid": True,
                      "elapsed_seconds": payload["diagnostic_elapsed_seconds"]}))


if __name__ == "__main__":
    main()
