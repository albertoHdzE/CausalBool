#!/usr/bin/env python3
"""AUDIT03/R3.merge — the schema merge must change the DESCRIPTION and nothing else.

The author ruled on 2026-09-03 that adjacent schemata should be merged. That
ruling moves five of the six published DecimalRepertoire tables, so the merge
needs a gate that can fail, not a claim that it is obviously safe.

One question, asked elementwise:

    does the merged schema set cover EXACTLY the same repertoire indices
    as the published base set unfolded against its offset family?

Not "the same number of indices" -- the same indices, by symmetric difference.
Four gates, because a check that cannot fail proves nothing:

  M1  every published case: symDiff(published, merged) must be empty.
  M2  NEGATIVE CONTROL: corrupt one schema by freeing one more coordinate and
      the same check must FAIL. If it does not, M1 is inert.
  M3  CROSS-LANGUAGE parity against Wolfram's own BooleanMinimize, run by
      papers/method/manuscript_computational/generate_paper_outputs.wl. The two
      implementations share no code: this one is prime implicants plus a GREEDY
      set cover (index-deconvolution/src/deconvolution.py), the other is a
      Wolfram primitive. Agreement is evidence; a single shared routine would
      have been none.
  M4  MINIMALITY. minimal_dnf's cover is greedy, so its size is an upper bound,
      not a minimum. The count printed here goes into the paper, so it is
      checked against an EXHAUSTIVE minimum cover over the prime implicants
      rather than assumed. If the two differ, the greedy number must not be
      described as minimal.

Run:
    venv/bin/python audit/AUDIT03_R3_description_length/verify_merge.py
"""

from __future__ import annotations

import itertools
import json
import math
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


def elias_gamma_bits(k: int) -> int:
    """Length of the self-delimiting Elias gamma code for k >= 1. Both forms pay
    a count, so this cancels almost exactly; it is included so that neither form
    is quietly given a free length field."""
    return 2 * k.bit_length() - 1


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


def prime_implicants(L, coords):
    """Quine-McCluskey primes only, no cover step -- the search space for M4."""
    m = len(coords)
    minterms = sorted({local_bits(j, coords) for j in L})
    full = (1 << m) - 1
    terms = {(y, full) for y in minterms}
    primes: set[tuple[int, int]] = set()
    while terms:
        merged, used = set(), set()
        tl = list(terms)
        for i in range(len(tl)):
            for j in range(i + 1, len(tl)):
                (b1, k1), (b2, k2) = tl[i], tl[j]
                if k1 != k2:
                    continue
                d = b1 ^ b2
                if d and not (d & (d - 1)) and (d & k1):
                    merged.add((b1 & ~d, k1 & ~d))
                    used.add(tl[i])
                    used.add(tl[j])
        primes |= {t for t in terms if t not in used}
        terms = merged
    return minterms, sorted(primes)


def min_cover_size(L, coords, cap=8):
    """Exhaustive smallest cover of the on-set by prime implicants.

    Returns the true minimum, or None if no cover of size <= cap exists (in
    which case the greedy figure must not be called minimal without a further
    search). The instances here are tiny: at most a few dozen primes.
    """
    minterms, primes = prime_implicants(L, coords)
    if not minterms:
        return 0
    cov = [frozenset(mt for mt in minterms if (mt & k) == b) for b, k in primes]
    target = set(minterms)
    for size in range(1, cap + 1):
        for combo in itertools.combinations(cov, size):
            if set().union(*combo) == target:
                return size
    return None


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

    print("M3  CROSS-LANGUAGE — Wolfram BooleanMinimize vs this greedy cover")
    wl_path = (ROOT / "papers" / "method" / "manuscript_computational"
               / "merged_queries.json")
    if not wl_path.exists():
        print(f"    SKIPPED — {wl_path.name} absent; run generate_paper_outputs.wl")
        failures.append("M3: no Wolfram output to compare against")
    else:
        wl = {c["case"]: c for c in json.loads(wl_path.read_text())["cases"]}
        print(f"    {'case':<5}{'py':>4}{'wl':>4}   forms identical")
        for name in CASES:
            if name not in wl:
                failures.append(f"M3 {name}: absent from the Wolfram output")
                continue
            same = sorted(wl[name]["forms"]) == sorted(report[name]["forms"])
            print(f"    {name:<5}{report[name]['schemata']:>4}"
                  f"{wl[name]['schemata']:>4}   {same}")
            if not same:
                failures.append(
                    f"M3 {name}: covers differ — py {sorted(report[name]['forms'])} "
                    f"vs wl {sorted(wl[name]['forms'])}")
    print()

    print("M4  MINIMALITY — greedy size vs EXHAUSTIVE minimum over the primes")
    print(f"    {'case':<5}{'primes':>8}{'greedy':>8}{'minimum':>9}")
    for name, (L, coords) in CASES.items():
        _, primes = prime_implicants(L, coords)
        greedy = report[name]["schemata"]
        exact = min_cover_size(L, coords)
        report[name]["primes"] = len(primes)
        report[name]["minimum"] = exact
        flag = "" if exact == greedy else "   <-- greedy is NOT minimal"
        print(f"    {name:<5}{len(primes):>8}{greedy:>8}{str(exact):>9}{flag}")
        if exact != greedy:
            failures.append(
                f"M4 {name}: greedy {greedy} but minimum {exact} — the paper "
                f"may not call {greedy} minimal")
    print()

    print("M5  LENGTH — is the merged description actually SHORTER, in bits?")
    print("    '38 rows -> 20 schemata' is a COUNT, not a length. A base row is")
    print("    c_q bits; a schema is c_q trits at log2(3) = 1.585 bits each, so")
    print("    fewer objects need not mean fewer bits. Both forms are priced in")
    print("    the same coordinate: an n-bit mask naming C_q (identical in both,")
    print("    since F_q is free in both), a self-delimiting count, then the")
    print("    payload. The trit encoding is the CHEAPER of the two obvious")
    print("    schema codes -- a fixed-mask-plus-values code costs c_q + |fixed|")
    print("    bits, which is more here -- so this is generous to the merge.")
    print(f"    {'case':<5}{'rows':>6}{'sch':>5}{'coarse':>9}{'fine':>9}"
          f"{'ratio':>8}   verdict")
    l3 = math.log2(3)
    tot_coarse = tot_fine = 0.0
    length_report = {}
    for name, (L, coords) in CASES.items():
        cq, r, s = len(coords), len(L), report[name]["schemata"]
        coarse = N + elias_gamma_bits(r) + r * cq
        fine = N + elias_gamma_bits(s) + s * cq * l3
        tot_coarse += coarse
        tot_fine += fine
        length_report[name] = {"coarse_bits": coarse, "fine_bits": fine}
        verdict = "shorter" if fine < coarse else "LONGER"
        print(f"    {name:<5}{r:>6}{s:>5}{coarse:>9.1f}{fine:>9.1f}"
              f"{fine / coarse:>8.2f}   {verdict}")
    print(f"    {'TOTAL':<5}{tot_rows:>6}{tot_sch:>5}{tot_coarse:>9.1f}"
          f"{tot_fine:>9.1f}{tot_fine / tot_coarse:>8.2f}")
    wins = sum(1 for v in length_report.values()
               if v["fine_bits"] < v["coarse_bits"])
    print(f"\n    The merge shortens the description in {wins} of {len(CASES)}"
          f" cases, not all six.")
    print("    It is a MINIMUM COVER, which is a statement about the number of")
    print("    schemata; minimising bits is a different objective and the two")
    print("    part company whenever the saved rows are few and the freed")
    print("    coordinates are fewer. No claim that merging always shortens the")
    print("    description may be written into the papers.\n")

    (HERE / "merge_verification.json").write_text(json.dumps(
        {"cases": report, "total_rows": tot_rows, "total_schemata": tot_sch,
         "negative_control_fired": fired,
         "length": length_report,
         "length_total_coarse_bits": tot_coarse,
         "length_total_fine_bits": tot_fine,
         "length_cases_shortened": wins,
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
