"""gap-ranking-v1-r1 -- join sealed ranks with the original D labels; exact endpoints.

Usage: python join.py <production dir> [<results_d.jsonl> <nonf3_full_maps.json>]
Runs only after produce.py has sealed its outputs.  Verifies the seal, the trusted
hashes and the exact 2,730-row identity of results_d before reading any label.
Writes joined.json and joined_table.md into the production directory.
"""
from __future__ import annotations

import json
import os
import sys
from fractions import Fraction

HERE = os.path.dirname(os.path.abspath(__file__))
import routes  # noqa: E402

RESULTS_D_SHA = "7119aa72f6483e955aa1033cbde7d0ef144f34ea8a614a03ba66830354ad0e12"
NONF3_SHA = "3dc79653b540512de1e374e0a95d73b9abc8b02b80b5e7390d450ad73ea6959d"
RESULTS_D = os.path.join(routes.OUTCOME_TREE, "results_d.jsonl")
NONF3 = os.path.join(routes.OUTCOME_TREE, "nonf3_full_maps.json")
TAUS = (1, 2, 4, 8, 16)
OFFSETS = {"M1": 0, "M2": 675, "M3": 1350, "M4": 2025}
N_CANDS = {"M1": 135, "M2": 135, "M3": 135, "M4": 141}


class JoinError(RuntimeError):
    pass


def verify_seal(prod: str) -> dict:
    with open(os.path.join(prod, "seal.json")) as fh:
        seal = json.load(fh)
    for f, h in seal.items():
        if f == "counts":
            continue
        if routes.sha256(os.path.join(prod, f)) != h:
            raise JoinError(f"seal broken: {f}")
    return seal


def load_labels(path: str, expect_sha: str = RESULTS_D_SHA) -> dict:
    """(model, cand_id, tau) -> row; refuses any deviation from the trusted identity."""
    if routes.sha256(path) != expect_sha:
        raise JoinError("results_d trusted-input hash mismatch")
    rows = {}
    ids = set()
    with open(path) as fh:
        for line in fh:
            r = json.loads(line)
            key = (r["model"], r["cand_id"], r["tau"])
            want = OFFSETS[r["model"]] + 5 * r["cand_id"] + TAUS.index(r["tau"])
            if r["row"] != want:
                raise JoinError(f"row identity mismatch at {key}")
            if key in rows or r["row"] in ids:
                raise JoinError(f"duplicate outcome {key}")
            rows[key] = r
            ids.add(r["row"])
    expected = {(m, k, t) for m in OFFSETS for k in range(N_CANDS[m]) for t in TAUS}
    if set(rows) != expected or len(rows) != 2730:
        raise JoinError(f"coverage: {len(expected - set(rows))} missing, "
                        f"{len(set(rows) - expected)} unexpected")
    return rows


def constant_flags(path: str, expect_sha: str = NONF3_SHA) -> dict:
    """row -> CONSTANT_DYNAMICS | NONCONSTANT_DYNAMICS from the saved supplemental evidence."""
    if routes.sha256(path) != expect_sha:
        raise JoinError("nonf3_full_maps trusted-input hash mismatch")
    with open(path) as fh:
        ev = json.load(fh)
    out = {}
    for e in ev:
        const = all(len(set(dm["G"].values())) == 1 for dm in e["distinct_maps"])
        out[e["row"]] = "CONSTANT_DYNAMICS" if const else "NONCONSTANT_DYNAMICS"
    return out


def classify(delta: Fraction) -> str:
    return "EARLIER" if delta > 0 else ("TIE" if delta == 0 else "LATER")


def describe(c: dict) -> str:
    f = c["family"]
    if f == "F1":
        return f"F1 {c['g']} (w,o)=({c['w']},{c['o']})"
    if f == "F2":
        return f"F2 {c['g']}"
    if f == "F3":
        return f"F3 val block [{c['a']},{c['a'] + c['len']}) of (w,o)=({c['w']},{c['o']})"
    if f == "F4":
        return f"F4 {c['g']}o{c['g']} (w,o)=({c['w']},{c['o']}) o2={c['o2']}"
    return f"{f} {c.get('g')}"


def cell_endpoint(cell: dict, labels: dict, flags: dict) -> dict:
    mid, tau = cell["model"], cell["tau"]
    cands = {c["id"]: c for c in cell["candidates"]}
    if sorted(cell["gap_order"]) != sorted(cands) or sorted(cell["canonical_order"]) != sorted(cands):
        raise JoinError(f"rank list does not cover the candidate population at {mid} tau={tau}")
    full = {}
    for cid, c in cands.items():
        r = labels.get((mid, cid, tau))
        if r is None:
            raise JoinError(f"missing outcome {mid} {cid} {tau}")
        if r["candidate"] != c["candidate"]:
            raise JoinError(f"candidate identity mismatch {mid} {cid}")
        full[cid] = r["status"] == "FULL"
    N, m = len(cands), sum(full.values())
    out = {"model": mid, "tau": tau, "N": N, "m": m,
           "full_ids": sorted(c for c, v in full.items() if v),
           "gap_order": cell["gap_order"], "canonical_order": cell["canonical_order"]}
    if m == 0:
        out.update({"status": "NO_FULL_REFERENCE", "r_G": None, "r_C": None,
                    "random_expected": None, "delta_random": None, "delta_canonical": None,
                    "vs_random": None, "vs_canonical": None, "first_hit": None})
        return out
    rG = 1 + next(i for i, c in enumerate(cell["gap_order"]) if full[c])
    rC = 1 + next(i for i, c in enumerate(cell["canonical_order"]) if full[c])
    exp = Fraction(N + 1, m + 1)
    dR, dC = exp - rG, Fraction(rC - rG)
    hit = cell["gap_order"][rG - 1]
    row = OFFSETS[mid] + 5 * hit + TAUS.index(tau)
    out.update({
        "status": "AVAILABLE", "r_G": rG, "r_C": rC,
        "random_expected": {"num": N + 1, "den": m + 1,
                            "reduced": [exp.numerator, exp.denominator]},
        "delta_random": [dR.numerator, dR.denominator],
        "delta_canonical": [dC.numerator, dC.denominator],
        "vs_random": classify(dR), "vs_canonical": classify(dC),
        "first_hit": {"id": hit, "row": row, "candidate": cands[hit]["candidate"],
                      "description": describe(cands[hit]["candidate"]),
                      "score": cands[hit]["score"],
                      "dynamics": flags.get(row, "NOT_CHARACTERISED")},
        "canonical_first_hit": cell["canonical_order"][rC - 1],
    })
    return out


def frac_str(p) -> str:
    return "—" if p is None else (str(p[0]) if p[1] == 1 else f"{p[0]}/{p[1]}")


def main(prod: str, results_d: str = RESULTS_D, nonf3: str = NONF3) -> int:
    verify_seal(prod)                      # seal first, then labels
    with open(os.path.join(prod, "ranks.json")) as fh:
        ranks = json.load(fh)
    labels = load_labels(results_d)
    flags = constant_flags(nonf3)
    cells = [cell_endpoint(c, labels, flags) for c in ranks]
    if len(cells) != 20:
        raise JoinError("expected 20 cells")
    summary = {}
    for comp in ("vs_random", "vs_canonical"):
        summary[comp] = {k: sum(1 for c in cells if c[comp] == k)
                         for k in ("EARLIER", "TIE", "LATER")}
    summary["unavailable_cells"] = [[c["model"], c["tau"]] for c in cells
                                    if c["status"] == "NO_FULL_REFERENCE"]
    summary["constant_dynamics_first_hits"] = [
        [c["model"], c["tau"], c["first_hit"]["id"]] for c in cells
        if c["first_hit"] and c["first_hit"]["dynamics"] == "CONSTANT_DYNAMICS"]
    with open(os.path.join(prod, "joined.json"), "w") as fh:
        json.dump({"cells": cells, "summary": summary,
                   "inputs": {"results_d_sha256": RESULTS_D_SHA, "nonf3_sha256": NONF3_SHA}},
                  fh, sort_keys=True, indent=1)
        fh.write("\n")
    lines = ["| model | τ | N | m | r_G | r_C | (N+1)/(m+1) | Δ_random | Δ_canonical | vs random"
             " | vs canonical | first gap hit | dynamics |",
             "|---|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for c in cells:
        if c["status"] != "AVAILABLE":
            lines.append(f"| {c['model']} | {c['tau']} | {c['N']} | 0 | — | — | — | — | — |"
                         f" NO_FULL_REFERENCE | NO_FULL_REFERENCE | — | — |")
            continue
        e = c["random_expected"]
        lines.append(
            f"| {c['model']} | {c['tau']} | {c['N']} | {c['m']} | {c['r_G']} | {c['r_C']} |"
            f" {e['num']}/{e['den']} | {frac_str(c['delta_random'])} |"
            f" {frac_str(c['delta_canonical'])} | {c['vs_random']} | {c['vs_canonical']} |"
            f" #{c['first_hit']['id']} {c['first_hit']['description']} |"
            f" {c['first_hit']['dynamics']} |")
    with open(os.path.join(prod, "joined_table.md"), "w") as fh:
        fh.write("\n".join(lines) + "\n")
    print(json.dumps(summary))
    return 0


if __name__ == "__main__":
    sys.exit(main(*sys.argv[1:]))
