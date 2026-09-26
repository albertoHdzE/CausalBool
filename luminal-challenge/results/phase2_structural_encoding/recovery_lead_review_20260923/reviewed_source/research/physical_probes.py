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
    rows: List[dict] = []
    counter = {"INVALID_PHYSICAL": 0, "VALIDATED_COMPLETE": 0,
               "INTERRUPTED": 0, "DISCREPANCY": 0}
    identities = set()
    codec_roundtrips = 0
    exhausted = True
    for ordinal, (kind, field_id, alt, value) in enumerate(proposals(domain)):
        if ordinal >= max_proposals or time.perf_counter() - start >= seconds:
            exhausted = False
            break
        times = dict(domain.incumbent_times)
        addresses = dict(domain.incumbent_addresses)
        if kind == "time":
            times[int(field_id)] = value
        else:
            addresses[field_id] = value
        candidate = dc.compilation(domain.facts, times, addresses)
        row = {"attempt": ordinal, "field_kind": kind, "field_id": field_id,
               "alternative_ordinal": alt, "value": value, "status": None,
               "elapsed_seconds": time.perf_counter() - start}
        try:
            machine.check_compilation(program, candidate)
        except (machine.CompileError, machine.ProgramError) as exc:
            row.update(status="INVALID_PHYSICAL", reason=f"{type(exc).__name__}: {exc}",
                       elapsed_seconds=time.perf_counter() - start)
            counter["INVALID_PHYSICAL"] += 1
            rows.append(row)
            continue
        case_count = 0
        try:
            for case in program["cases"]:
                machine.check_case(program, candidate, case)
                case_count += 1
        except (machine.CompileError, machine.ProgramError) as exc:
            row.update(status="DISCREPANCY", reason=f"case {case_count}: {type(exc).__name__}: {exc}",
                       case_checks=case_count, elapsed_seconds=time.perf_counter() - start)
            counter["DISCREPANCY"] += 1
            rows.append(row)
            continue
        normal = se.normalise_compilation(domain.facts, candidate)
        identity = se.canonical_json(normal)
        c, s, j = se.objective(domain.facts, times, addresses)
        row.update(candidate=normal, identity_sha256=se.object_digest(normal),
                   case_checks=case_count, cycles=c, scratch=s, product=j,
                   codec_results={})
        discrepancy = None
        for codec in se.CODECS:
            try:
                index = se.encode(domain, normal, codec)
                decoded = se.decode(domain, index, codec)
                canonical = se.encode(domain, decoded.compilation, codec) if decoded.status == se.COMPLETE else None
            except (se.DomainError, se.CodecDefect) as exc:
                discrepancy = f"{codec}: {type(exc).__name__}: {exc}"
                row["codec_results"][codec] = {"status": "ERROR", "reason": discrepancy}
                break
            result_identity = (se.canonical_json(decoded.compilation)
                               if decoded.compilation is not None else None)
            row["codec_results"][codec] = {"index": str(index), "status": decoded.status,
                                           "identity": result_identity,
                                           "canonical_index": str(canonical) if canonical is not None else None}
            if decoded.status != se.COMPLETE or result_identity != identity or canonical != index:
                discrepancy = f"{codec}: identity/status/canonical re-encode mismatch"
                break
            if se.objective(domain.facts, decoded.times, decoded.addresses) != (c, s, j):
                discrepancy = f"{codec}: C/S/J mismatch"
                break
            codec_roundtrips += 1
        if discrepancy:
            row.update(status="DISCREPANCY", reason=discrepancy)
            counter["DISCREPANCY"] += 1
        else:
            row["status"] = "VALIDATED_COMPLETE"
            counter["VALIDATED_COMPLETE"] += 1
            identities.add(identity)
        row["elapsed_seconds"] = time.perf_counter() - start
        rows.append(row)
    elapsed = time.perf_counter() - start
    summary = {"attempted": len(rows), "counts": counter,
               "distinct_complete": len(identities), "identity_sha256": sorted(se.object_digest(json_loads(x)) for x in identities),
               "codec_roundtrips": codec_roundtrips, "elapsed_seconds": elapsed,
               "stopped_by": "exhausted" if exhausted else ("proposal_cap" if len(rows) >= max_proposals else "deadline"),
               "deadline_overshoot_seconds": max(0.0, elapsed - seconds) if not exhausted and len(rows) < max_proposals else 0.0,
               "proposal_cap_overshoot": 0,
               "exhausted": exhausted, "program_sha256": expected_program_sha256}
    return rows, summary


def json_loads(value: str):
    import json
    return json.loads(value)
