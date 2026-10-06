"""task-compaction-v1 finalization -- expected-value authority for audit_r3 (revision r3).

A separately versioned REFACTOR of the expectation half of the frozen
../../../task-compaction-v1-r1/src/audit.py::audit_cell.  The frozen function computes each
candidate decision and the per-cell summary and then compares them with plain `!=`, which
conflates 1/True/1.0.  Here the same calculation RETURNS the expected values, in their exact
JSON form, and performs no comparison; audit_r3 compares type-exactly.  audit_r3 does not
call the frozen audit_cell, so exactly one copy of this calculation is live in the revised
audit.  Every primitive (determines, frac, first_appearance, TASK, study declarations) is the
frozen module's own, passed in as `A`; no producer, minimizer or owner helper is imported.

Changes against the frozen text (and nothing else):
  * comparisons and ledger calls removed; the function returns values;
  * tuples become lists and candidate rows carry every declared record field
    (record_id, cell_id, candidate descriptor) so the record can be compared whole;
  * null_reason is not computed (free text): its typed rule lives in audit_r3.
"""
from __future__ import annotations


def regime_tables(c, tabs_all):
    return tabs_all[:1] if c["regime"] == "AUTO" else tabs_all


def expected_outputs(A, c):
    return [A.TASK[c["task"]](x, c["n"]) for x in range(c["N"])]


def expected_candidates(A, c, alpha, tabs_all, decl, vecs, clos):
    """[(expected record, partition vector, theorem)] per declared candidate, in declaration
    order. `alpha` is the certificate-verified optimum. As in the frozen audit, a sufficient
    candidate's expected factors_through is True and `theorem` says whether alpha* really
    factors through it (False => INVALID, checked by audit_r3); None for insufficient ones."""
    N = c["N"]
    tables = regime_tables(c, tabs_all)
    h = expected_outputs(A, c)
    K = max(alpha) + 1
    rows = []
    for cand, a in zip(decl, vecs):
        key = (c["model"], cand["id"])
        if key not in clos:
            clos[key] = [A.determines(a, [a[t[x]] for x in range(N)]) for t in tabs_all]
        cl = clos[key][:len(tables)]
        dbad = A.determines(a, h)
        failing = [q for q, b in enumerate(cl) if b is not None]
        suff = dbad is None and not failing
        Kc = max(a) + 1
        rec = {"record_id": c["cell_id"] * 1000 + cand["id"], "cell_id": c["cell_id"],
               "candidate_id": cand["id"], "candidate": dict(cand), "K_candidate": Kc,
               "decodable": dbad is None, "decode_conflict": None if dbad is None else list(dbad),
               "closed": not failing, "failing_actions": failing,
               "closure_witnesses": {str(q): list(cl[q]) for q in failing},
               "task_sufficient": suff, "is_control": A.S.is_control(Kc, N)}
        theorem = (A.determines(a, alpha) is None and Kc >= K) if suff else None
        if suff:
            rec.update({"factors_through": True,
                        "K_minus_Kstar": Kc - K, "K_ratio": A.frac(Kc, K),
                        "identical_to_optimum": list(a) == alpha})
        else:
            rec.update({"factors_through": None, "K_minus_Kstar": None, "K_ratio": None,
                        "identical_to_optimum": None})
        rows.append((rec, tuple(a), theorem))
    return rows


def expected_summary(A, c, stages, alpha, tabs_all, decl, rows):
    """The per-cell summary the frozen audit recomputes, as exact JSON values."""
    n, N = c["n"], c["N"]
    tables = regime_tables(c, tabs_all)
    K = max(alpha) + 1
    recs = [r for r, _, _ in rows]
    vec = {r["candidate_id"]: v for r, v, _ in rows}
    suff = [r for r in recs if r["task_sufficient"]]
    best = min(suff, key=lambda m: (m["K_candidate"], m["candidate_id"])) if suff else None
    nc = [m for m in suff if m["is_control"] is not True]
    bnc = min(nc, key=lambda m: (m["K_candidate"], m["candidate_id"])) if nc else None
    P0 = stages[0]
    p0c = [A.determines(P0, [P0[t[x]] for x in range(N)]) for t in tables]
    ident = next(m for m, cd in zip(recs, decl) if cd["family"] == "C" and cd["g"] == "identity")
    fam = {cd["id"]: cd["family"] for cd in decl}

    def pick(m):
        return None if m is None else {"candidate_id": m["candidate_id"], "K": m["K_candidate"],
                                       "K_minus_Kstar": m["K_minus_Kstar"], "family": fam[m["candidate_id"]]}
    return {
        "cell": dict(c), "N": N, "K0": max(P0) + 1, "K_star": K, "K_star_over_N": A.frac(K, N),
        "capacity_saving_bits": n - (K - 1).bit_length(), "strict_rounds": len(stages) - 2,
        "outcome": "EXACT_REDUCTION" if K < N else "NO_REDUCTION",
        "storage_entries_excluded_from_capacity": {
            "state_to_group_map": N, "decoder": K, "macro_transition_tables": len(tables) * K,
            "action_labels": len(tables), "micro_action_tables": len(tables) * N},
        "baselines": {
            "identity": {"candidate_id": ident["candidate_id"], "K": N, "task_sufficient": ident["task_sufficient"]},
            "output_partition_P0": {"K": max(P0) + 1, "closed": all(b is None for b in p0c),
                                    "failing_actions": [q for q, b in enumerate(p0c) if b is not None],
                                    "closure_witnesses": {str(q): list(b) for q, b in enumerate(p0c) if b is not None}},
            "alpha_star": {"K": K}},
        "candidates": {
            "raw": len(recs), "distinct_partitions": len(set(vec.values())),
            "decodable_raw": sum(m["decodable"] for m in recs), "closed_raw": sum(m["closed"] for m in recs),
            "sufficient_raw": len(suff), "sufficient_distinct": len({vec[m["candidate_id"]] for m in suff}),
            "matching_optimum_raw": sum(bool(m["identical_to_optimum"]) for m in suff),
            "matching_optimum_distinct": len({vec[m["candidate_id"]] for m in suff if m["identical_to_optimum"]}),
            "best": pick(best), "best_lossless_control_excluded": pick(bnc),
            "comparison": None if best is None else
            ("MATCHES_OPTIMUM" if best["K_candidate"] == K else "CANDIDATE_GAP")}}
