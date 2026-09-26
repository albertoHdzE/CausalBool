"""Local replay of propagation certificates (protocol section 5).

Each certificate names its rule and the local inputs that justify it. This
module re-derives the conclusion from those inputs and the program's own facts
and nothing else: it imports no search, no codec and no propagation code, so a
deletion that its emitter got wrong is not re-derived by the same mistake.

Replay checks LOCAL logic given the recorded inputs (for example that every
removed ``t_u`` really exceeds ``max(D_v) - lag`` for a real edge). It cannot
show that the recorded ``max(D_v)`` was the true domain maximum at that node;
the exhaustive oracle tests carry that obligation. Certificate hashes alone
are not a proof of soundness.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

import machine

import direct_contract as dc


def replay(facts: dc.ProgramFacts, certificate: Sequence) -> List[str]:
    """Problems with one certificate; an empty list means it replays."""

    rule = certificate[0]
    problems: List[str] = []
    if rule in ("PU", "PL"):
        _, u, v, lag, bound, removed = certificate
        if facts.predecessors[v].get(u) != lag:
            problems.append(f"{rule}: ({u}->{v}, lag {lag}) is not a program edge")
        if not removed:
            problems.append(f"{rule}: a certificate must remove something")
        for value in removed:
            if rule == "PU" and not value > bound - lag:
                problems.append(f"PU: t_{u}={value} is not above max(D_{v})-lag={bound - lag}")
            if rule == "PL" and not value < bound + lag:
                problems.append(f"PL: t_{v}={value} is not below min(D_{u})+lag={bound + lag}")
    elif rule == "EO":
        _, engine, cycle, ops, limit = certificate
        if machine.ENGINE_LIMITS.get(engine) != limit:
            problems.append(f"EO: {engine} limit is not {limit}")
        if any(facts.engine[op] != engine for op in ops):
            problems.append("EO: an operation is on another engine")
        if len(ops) <= limit:
            problems.append("EO: the singleton issues do not exceed the limit")
    elif rule == "EF":
        _, engine, cycle, op, limit = certificate
        if facts.engine[op] != engine or machine.ENGINE_LIMITS.get(engine) != limit:
            problems.append("EF: engine or limit mismatch")
    elif rule == "AL":
        _, u, v, max_av, min_av, wu, wv, removed = certificate
        if facts.width.get(u) != wu or facts.width.get(v) != wv:
            problems.append("AL: widths do not match the program")
        low, high = max_av - wu + 1, min_av + wv - 1
        if not removed:
            problems.append("AL: a certificate must remove something")
        for value in removed:
            if not low <= value <= high:
                problems.append(f"AL: a_{u}={value} has disjoint support in [{min_av}, {max_av}]")
    elif rule == "PB":
        _, lc, ls, best, lc_witness, ls_witness = certificate
        if lc * ls < best:
            problems.append(f"PB: {lc}*{ls} < {best} does not justify a prune")
        if lc_witness[0] == "floor" and lc != facts.cycle_lower_bound():
            problems.append("PB: LC floor witness disagrees with the program")
        if lc_witness[0] == "min_time" and lc != lc_witness[2] + 1:
            problems.append("PB: LC min_time witness does not give LC")
        if ls_witness[0] == "widest" and ls != facts.memory_lower_bound():
            problems.append("PB: LS widest witness disagrees with the program")
        if ls_witness[0] == "min_address" and ls != ls_witness[2] + facts.width[ls_witness[1]]:
            problems.append("PB: LS min_address witness does not give LS")
    elif rule == "EMPTY":
        if len(certificate) < 3:
            problems.append("EMPTY: missing its variable")
    else:
        problems.append(f"unknown rule {rule!r}")
    return problems


def replay_stream(facts: dc.ProgramFacts, certificates: Sequence[Sequence]) -> Dict[str, object]:
    """Replay every certificate; the denominator is printed so empty cannot pass."""

    failures = []
    counts: Dict[str, int] = {}
    for index, certificate in enumerate(certificates):
        counts[certificate[0]] = counts.get(certificate[0], 0) + 1
        problems = replay(facts, certificate)
        if problems:
            failures.append({"index": index, "certificate": repr(certificate)[:300],
                             "problems": problems})
    return {"replayed": len(certificates), "counts": dict(sorted(counts.items())),
            "failures": failures[:50], "failure_count": len(failures),
            "status": "PASS" if certificates and not failures else (
                "EMPTY" if not certificates else "FAIL")}
