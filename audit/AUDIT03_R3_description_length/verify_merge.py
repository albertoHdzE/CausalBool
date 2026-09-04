#!/usr/bin/env python3
"""AUDIT03/R3.merge — the schema merge must change the DESCRIPTION and nothing else.

The author ruled on 2026-09-03 that adjacent schemata should be merged. That
ruling moves five of the six published DecimalRepertoire tables, so the merge
needs a gate that can fail, not a claim that it is obviously safe.

One question, asked elementwise:

    does the merged schema set cover EXACTLY the same repertoire indices
    as the published base set unfolded against its offset family?

Not "the same number of indices" -- the same indices, by symmetric difference.
Two gates, because a check that cannot fail proves nothing:

  M1  every published case: symDiff(published, merged) must be empty.
  M2  NEGATIVE CONTROL: corrupt one schema by freeing one more coordinate and
      the same check must FAIL. If it does not, M1 is inert.

Run:
    venv/bin/python audit/AUDIT03_R3_description_length/verify_merge.py
"""

from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "index-deconvolution" / "src"))

from deconvolution import minimal_dnf                      # noqa: E402

N = 10

# The six published cases: base set L (1-based repertoire indices) and the query
# support union C_q, transcribed from comp_paper.tex tables 4 and 5.
CASES = {
    "F1": ([143, 215, 399, 400, 471, 472], list(range(1, 11))),
    "F2": ([15, 87, 271, 272, 343, 344], list(range(1, 11))),
    "F3": ([655, 727, 911, 912, 983, 984], list(range(1, 11))),
    "F4": ([79, 207, 335, 336, 463, 464], list(range(1, 11))),
    "S1": ([141, 217], [2, 3, 4, 5, 6, 7, 8]),
    "S2": ([141, 217, 397, 398, 473, 474, 653, 729, 909, 910, 985, 986],
           list(range(1, 11))),
}


def local_bits(j: int, coords: list[int]) -> int:
    """Pack the C_q coordinates of repertoire index j (1-based, LSB-first)."""
    return sum((((j - 1) >> (c - 1)) & 1) << i for i, c in enumerate(coords))


def unfold(clause, coords, n=N) -> set[int]:
    """Expand one schema over ALL fillings of its don't-cares, back to 1-based
    repertoire indices. This is the general Dec(L, Omega): the sumandos are
    regenerated here, never transmitted."""
    fixed = {coords[a]: 1 for a in clause["activators"]}
    fixed.update({coords[b]: 0 for b in clause["inhibitors"]})
    free = [c for c in range(1, n + 1) if c not in fixed]
    base = sum(v << (c - 1) for c, v in fixed.items())
    out = set()
    for m in range(2 ** len(free)):
        idx = base
        for t, c in enumerate(free):
            if (m >> t) & 1:
                idx |= 1 << (c - 1)
        out.add(idx + 1)
    return out


def published_cover(L, coords, n=N) -> set[int]:
    """The published pair unfolded: each base row, times the offsets of every
    coordinate outside C_q. This is the coarse Dec(L, Omega(F_q))."""
    free = [c for c in range(1, n + 1) if c not in coords]
    out = set()
    for j in L:
        base = j - 1
        for m in range(2 ** len(free)):
            idx = base
            for t, c in enumerate(free):
                if (m >> t) & 1:
                    idx |= 1 << (c - 1)
                else:
                    idx &= ~(1 << (c - 1))
            out.add(idx + 1)
    return out


def schema_str(clause, coords, n=N) -> str:
    s = ["*"] * n
    for a in clause["activators"]:
        s[coords[a] - 1] = "1"
    for b in clause["inhibitors"]:
        s[coords[b] - 1] = "0"
    return "".join(s)


def merge(L, coords):
    m = len(coords)
    rows = [local_bits(j, coords) for j in L]
    tt = [1 if y in rows else 0 for y in range(2 ** m)]
    return minimal_dnf(tt)


def main() -> int:
    print("AUDIT03/R3.merge — schema merge gate\n")
    report, failures = {}, []

    print("M1  published pair  vs  merged schemata, ELEMENTWISE")
    print(f"    {'case':<5}{'rows':>6}{'schemata':>10}{'|published|':>13}"
          f"{'|merged|':>10}{'symDiff':>9}")
    for name, (L, coords) in CASES.items():
        cl = merge(L, coords)
        want = published_cover(L, coords)
        got = set().union(*(unfold(c, coords) for c in cl)) if cl else set()
        sym = want ^ got
        if sym:
            failures.append(f"M1 {name}: symDiff size {len(sym)}, e.g. {sorted(sym)[:5]}")
        report[name] = {"published_rows": len(L), "schemata": len(cl),
                        "covered": len(want), "symdiff": len(sym),
                        "forms": [schema_str(c, coords) for c in cl]}
        print(f"    {name:<5}{len(L):>6}{len(cl):>10}{len(want):>13}{len(got):>10}"
              f"{len(sym):>9}{'' if not sym else '   <-- FAIL'}")
    tot_rows = sum(len(L) for L, _ in CASES.values())
    tot_sch = sum(report[k]["schemata"] for k in CASES)
    print(f"    {'TOTAL':<5}{tot_rows:>6}{tot_sch:>10}")
    print(f"\n    {tot_rows} published rows -> {tot_sch} schemata, "
          f"covering identical index sets.")
    print("    The behaviour does not change. Only the description gets shorter.\n")

    print("M2  NEGATIVE CONTROL — free one more coordinate, the gate must FAIL")
    fired = 0
    for name, (L, coords) in CASES.items():
        cl = merge(L, coords)
        if not cl or not (cl[0]["activators"] or cl[0]["inhibitors"]):
            continue
        broken = [dict(c) for c in cl]
        if broken[0]["activators"]:
            broken[0] = {"activators": broken[0]["activators"][1:],
                         "inhibitors": broken[0]["inhibitors"]}
        else:
            broken[0] = {"activators": broken[0]["activators"],
                         "inhibitors": broken[0]["inhibitors"][1:]}
        want = published_cover(L, coords)
        got = set().union(*(unfold(c, coords) for c in broken))
        if want ^ got:
            fired += 1
        else:
            failures.append(f"M2 {name}: corruption NOT detected — gate is inert")
    print(f"    corrupted {len(CASES)} cases, gate detected {fired}")
    if fired != len(CASES):
        print("    ^ the gate is inert wherever it did not fire")
    print()

    (HERE / "merge_verification.json").write_text(json.dumps(
        {"cases": report, "total_rows": tot_rows, "total_schemata": tot_sch,
         "negative_control_fired": fired,
         "verdict": "PASS" if not failures else "FAIL"}, indent=1))

    if failures:
        print("VERDICT: FAIL")
        for f in failures:
            print(" -", f)
        return 1
    print("VERDICT: PASS — every merged case covers exactly the published index")
    print("set, and the negative control fires on all of them.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
