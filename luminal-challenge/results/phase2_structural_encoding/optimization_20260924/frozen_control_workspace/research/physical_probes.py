"""Deterministic single-coordinate probes around the accepted direct bootstrap.

This module is deliberately independent of structural option filtering/search.
It forms one-field physical neighbors, validates them with the pinned machine,
and tests their representation in all four codecs.
"""
from __future__ import annotations

import time
from typing import Dict, Iterable, Iterator, List, Tuple

from research import structural_encoding as se
import machine
import direct_contract as dc


def proposals(domain: se.Domain) -> Iterator[Tuple[str, str, int, int]]:
    """Yield (field_kind, field_id, alternative_ordinal, value) in frozen order."""
    fields: List[Tuple[str, str, List[int], int]] = []
    for op_id in sorted(domain.time_domains):
        origin = domain.incumbent_times[op_id]
        alternatives = [v for v in domain.time_domains[op_id] if v != origin]
        fields.append(("time", str(op_id), alternatives, origin))
    for name in sorted(domain.address_domains, key=lambda item: domain.facts.producers[item]):
        origin = domain.incumbent_addresses[name]
        alternatives = [v for v in domain.address_domains[name] if v != origin]
        fields.append(("address", name, alternatives, origin))
    maximum = max((len(values) for _, _, values, _ in fields), default=0)
    for ordinal in range(maximum):
        for kind, field_id, values, _origin in fields:
            if ordinal < len(values):
                yield kind, field_id, ordinal, values[ordinal]


def run(domain: se.Domain, program: dict, max_proposals: int = 10000,
        seconds: float = 60.0, expected_program_sha256: str = "") -> Tuple[List[dict], dict]:
    if domain.incumbent is None or domain.incumbent_times is None or domain.incumbent_addresses is None:
        raise se.DomainError("physical probes require the accepted direct bootstrap")
    start = time.perf_counter()
    deadline = start + seconds
    rows: List[dict] = []
    counter = {"INVALID_PHYSICAL": 0, "VALIDATED_COMPLETE": 0,
               "INTERRUPTED": 0, "DISCREPANCY": 0}
    identities = set()
    codec_counts = {codec: {"attempted": 0, "complete": 0, "interrupted": 0,
                            "discrepancy": 0, "machine_attempted": 0,
                            "machine_complete": 0, "case_attempted": 0,
                            "case_complete": 0} for codec in se.CODECS}
    case_checks = 0
    stopped_by = "exhausted"
    iterator = iter(proposals(domain))
    while True:
        if len(rows) >= max_proposals:
            stopped_by = "proposal_cap"
            break
        if time.perf_counter() >= deadline:
            stopped_by = "deadline"
            break
        try:
            kind, field_id, alt, value = next(iterator)
        except StopIteration:
            break
        ordinal = len(rows)
        times = dict(domain.incumbent_times)
        addresses = dict(domain.incumbent_addresses)
        if kind == "time":
            times[int(field_id)] = value
        else:
            addresses[field_id] = value
        candidate = dc.compilation(domain.facts, times, addresses)
        row = {"attempt": ordinal, "field_kind": kind, "field_id": field_id,
               "alternative_ordinal": alt, "value": value, "status": None,
               "elapsed_seconds": time.perf_counter() - start,
               "validation_counts": {"machine_attempted": 0, "machine_complete": 0,
                                     "case_attempted": 0, "case_complete": 0},
               "codec_counts": {codec: {"attempted": 0, "complete": 0,
                                        "machine_attempted": 0, "machine_complete": 0,
                                        "case_attempted": 0, "case_complete": 0}
                                for codec in se.CODECS}}
        def interrupted(phase: str) -> None:
            row.update(status="INTERRUPTED", interrupted_phase=phase,
                       elapsed_seconds=time.perf_counter() - start)
            counter["INTERRUPTED"] += 1
        if time.perf_counter() >= deadline:
            interrupted("construction")
            rows.append(row)
            stopped_by = "deadline"
            break
        try:
            row["validation_counts"]["machine_attempted"] += 1
            machine.check_compilation(program, candidate)
        except (machine.CompileError, machine.ProgramError) as exc:
            row.update(status="INVALID_PHYSICAL", reason=f"{type(exc).__name__}: {exc}")
            counter["INVALID_PHYSICAL"] += 1
            row["elapsed_seconds"] = time.perf_counter() - start
            rows.append(row)
            if time.perf_counter() >= deadline:
                stopped_by = "deadline"
                break
            continue
        row["validation_counts"]["machine_complete"] += 1
        if time.perf_counter() >= deadline:
            interrupted("machine_validation")
            rows.append(row)
            stopped_by = "deadline"
            break
        case_count = 0
        case_interrupted = False
        for case in program["cases"]:
            if time.perf_counter() >= deadline:
                interrupted("case_validation")
                case_interrupted = True
                break
            row["validation_counts"]["case_attempted"] += 1
            try:
                machine.check_case(program, candidate, case)
            except (machine.CompileError, machine.ProgramError) as exc:
                row.update(status="DISCREPANCY", reason=f"case {case_count}: {type(exc).__name__}: {exc}",
                           case_checks=case_count, elapsed_seconds=time.perf_counter() - start)
                counter["DISCREPANCY"] += 1
                case_interrupted = True
                break
            case_count += 1
            row["validation_counts"]["case_complete"] += 1
            if time.perf_counter() >= deadline:
                interrupted("case_validation")
                case_interrupted = True
                break
        if case_interrupted:
            if row["status"] == "INTERRUPTED":
                stopped_by = "deadline"
            rows.append(row)
            if row["status"] == "INTERRUPTED":
                break
            continue
        if case_count != len(program["cases"]):
            row.update(status="DISCREPANCY", reason="case validation did not cover every public case",
                       case_checks=case_count)
            counter["DISCREPANCY"] += 1
            rows.append(row)
            continue
        if time.perf_counter() >= deadline:
            interrupted("case_validation")
            rows.append(row)
            stopped_by = "deadline"
            break
        normal = se.normalise_compilation(domain.facts, candidate)
        identity = se.canonical_json(normal)
        c, s, j = se.objective(domain.facts, times, addresses)
        row.update(candidate=normal, identity_sha256=se.object_digest(normal),
                   case_checks=case_count, cycles=c, scratch=s, product=j,
                   issue_time_vector=[[op_id, times[op_id]] for op_id in sorted(times)],
                   address_map=[[name, addresses[name]] for name in sorted(addresses,
                                                                            key=lambda item: domain.facts.producers[item])],
                   changed_fields=[{"kind": kind, "id": field_id}],
                   codec_results={})
        discrepancy = None
        interrupted_codec = False
        for codec in se.CODECS:
            if time.perf_counter() >= deadline:
                interrupted(f"codec:{codec}:before")
                codec_counts[codec]["interrupted"] += 1
                interrupted_codec = True
                break
            try:
                row["codec_counts"][codec]["attempted"] += 1
                codec_counts[codec]["attempted"] += 1
                index = se.encode(domain, normal, codec)
                decoded = se.decode(domain, index, codec)
                canonical = se.encode(domain, decoded.compilation, codec) if decoded.status == se.COMPLETE else None
            except (se.DomainError, se.CodecDefect) as exc:
                discrepancy = f"{codec}: {type(exc).__name__}: {exc}"
                row["codec_results"][codec] = {"status": "ERROR", "reason": discrepancy}
                codec_counts[codec]["discrepancy"] += 1
                break
            result_identity = (se.canonical_json(decoded.compilation)
                               if decoded.compilation is not None else None)
            row["codec_results"][codec] = {"index": str(index), "status": decoded.status,
                                           "identity": result_identity,
                                           "canonical_index": str(canonical) if canonical is not None else None}
            if decoded.status != se.COMPLETE or result_identity != identity or canonical != index:
                discrepancy = f"{codec}: identity/status/canonical re-encode mismatch"
                codec_counts[codec]["discrepancy"] += 1
                break
            if se.objective(domain.facts, decoded.times, decoded.addresses) != (c, s, j):
                discrepancy = f"{codec}: C/S/J mismatch"
                codec_counts[codec]["discrepancy"] += 1
                break
            if time.perf_counter() >= deadline:
                interrupted(f"codec:{codec}:machine_validation_before")
                codec_counts[codec]["interrupted"] += 1
                interrupted_codec = True
                break
            row["codec_counts"][codec]["machine_attempted"] += 1
            codec_counts[codec]["machine_attempted"] += 1
            try:
                machine.check_compilation(program, decoded.compilation)
            except (machine.CompileError, machine.ProgramError) as exc:
                discrepancy = f"{codec}: decoded machine validation failed: {type(exc).__name__}: {exc}"
                codec_counts[codec]["discrepancy"] += 1
                break
            row["codec_counts"][codec]["machine_complete"] += 1
            codec_counts[codec]["machine_complete"] += 1
            if time.perf_counter() >= deadline:
                interrupted(f"codec:{codec}:machine_validation")
                codec_counts[codec]["interrupted"] += 1
                interrupted_codec = True
                break
            codec_case_failed = False
            for case_index, case in enumerate(program["cases"]):
                if time.perf_counter() >= deadline:
                    interrupted(f"codec:{codec}:case_validation_before")
                    codec_counts[codec]["interrupted"] += 1
                    interrupted_codec = True
                    codec_case_failed = True
                    break
                row["codec_counts"][codec]["case_attempted"] += 1
                codec_counts[codec]["case_attempted"] += 1
                try:
                    machine.check_case(program, decoded.compilation, case)
                except (machine.CompileError, machine.ProgramError) as exc:
                    discrepancy = (f"{codec}: decoded case {case_index} failed: "
                                   f"{type(exc).__name__}: {exc}")
                    codec_counts[codec]["discrepancy"] += 1
                    codec_case_failed = True
                    break
                row["codec_counts"][codec]["case_complete"] += 1
                codec_counts[codec]["case_complete"] += 1
                if time.perf_counter() >= deadline:
                    interrupted(f"codec:{codec}:case_validation")
                    codec_counts[codec]["interrupted"] += 1
                    interrupted_codec = True
                    codec_case_failed = True
                    break
            if codec_case_failed:
                break
            row["codec_counts"][codec]["complete"] += 1
            codec_counts[codec]["complete"] += 1
            if time.perf_counter() >= deadline:
                interrupted(f"codec:{codec}:roundtrip")
                codec_counts[codec]["interrupted"] += 1
                interrupted_codec = True
                break
        if discrepancy:
            row.update(status="DISCREPANCY", reason=discrepancy)
            counter["DISCREPANCY"] += 1
        elif interrupted_codec:
            row["candidate"] = normal
            row["identity_sha256"] = se.object_digest(normal)
            row["case_checks"] = case_count
            row["cycles"], row["scratch"], row["product"] = c, s, j
        else:
            row["status"] = "VALIDATED_COMPLETE"
            counter["VALIDATED_COMPLETE"] += 1
            identities.add(identity)
        row["elapsed_seconds"] = time.perf_counter() - start
        rows.append(row)
        if interrupted_codec:
            stopped_by = "deadline"
            break
    elapsed = time.perf_counter() - start
    complete_rows = [row for row in rows if row.get("status") == "VALIDATED_COMPLETE"]
    times_vectors = {tuple(tuple(pair) for pair in row["issue_time_vector"])
                     for row in complete_rows}
    address_maps = {tuple(tuple(pair) for pair in row["address_map"])
                    for row in complete_rows}
    per_field_values = {}
    for row in complete_rows:
        field = row["field_kind"] + ":" + row["field_id"]
        per_field_values.setdefault(field, set()).add(row["value"])
    per_field = {key: len(values) for key, values in sorted(per_field_values.items())}
    metrics = {key: [min(row[key] for row in complete_rows), max(row[key] for row in complete_rows)]
               if complete_rows else None for key in ("cycles", "scratch", "product")}
    summary = {"attempted": len(rows), "counts": counter,
               "distinct_complete": len(identities), "identity_sha256": sorted(se.object_digest(json_loads(x)) for x in identities),
               "codec_roundtrips": sum(entry["complete"] for entry in codec_counts.values()),
               "codec_counts": codec_counts, "case_checks": sum(row["validation_counts"]["case_complete"] for row in rows),
               "diversity": {"unique_issue_time_vectors": len(times_vectors),
                             "unique_address_maps": len(address_maps),
                             "per_field_changes": per_field,
                             **{key + "_range": value for key, value in metrics.items()}},
               "elapsed_seconds": elapsed,
               "stopped_by": stopped_by,
               "deadline_overshoot_seconds": max(0.0, elapsed - seconds),
               "proposal_cap_overshoot": 0,
               "exhausted": stopped_by == "exhausted", "program_sha256": expected_program_sha256}
    return rows, summary


def json_loads(value: str):
    import json
    return json.loads(value)
