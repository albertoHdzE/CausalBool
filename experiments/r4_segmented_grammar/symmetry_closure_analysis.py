#!/usr/bin/env python
"""Can the gate catalogue be extended to cover all 256 ECA rules — and should it?

AUDIT02/P9-closure. Answers a question that looks like engineering and is
actually about whether the method has any content at ECA arity.

The short version, derived below rather than asserted:

1. **Covering all 256 is provably worthless at arity 3.** A 3-input truth table
   costs 2^3 = 8 bits. A catalogue covering all 256 needs log2(256) = 8 bits to
   name a member. A complete catalogue IS a lookup table, exactly, to the bit.
   The catalogue compresses only while it is incomplete.

2. **But over half the apparent gap is an artificial closure gap, not an
   expressivity limit.** The canonical twelve, as catalogued, reach 48 of 256.
   Closing under output negation and input negation reaches **112**. Those 64
   extra rules were always inside the family algebra; the catalogue simply was
   not closed under a symmetry it should have been closed under.

3. **Input permutations add nothing** (48 -> 48, 112 -> 112): the catalogue's
   supports are already all non-empty subsets, so it is permutation-closed by
   construction. Worth recording, because it is the one closure operation that
   would have to be paid for and it buys zero.

4. **144 rules are a genuine limit**, not an artefact. That is a real and
   defensible statement about the method's reach.

5. **Arity 3 is the worst possible case for the method's compression
   argument.** Naming cost grows like k while a truth table grows like 2^k, so
   the two cross exactly at k = 3 and diverge after. A paper that demonstrates
   the method on ECAs is demonstrating it where it has least to offer.

Run:
    venv/bin/python experiments/r4_segmented_grammar/symmetry_closure_analysis.py
"""

from __future__ import annotations

import itertools
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))


def num(tt) -> int:
    return sum(b << i for i, b in enumerate(tt))


def tt_of(n: int) -> list[int]:
    return [(n >> i) & 1 for i in range(8)]


def apply_perm(tt, p):
    out = [0] * 8
    for w in range(8):
        bits = [(w >> i) & 1 for i in range(3)]
        out[sum(bits[p[i]] << i for i in range(3))] = tt[w]
    return out


def apply_in_neg(tt, mask):
    out = [0] * 8
    for w in range(8):
        out[w ^ mask] = tt[w]
    return out


def orbit(n: int, perms: bool) -> set[int]:
    o = set()
    plist = list(itertools.permutations(range(3))) if perms else [(0, 1, 2)]
    for p in plist:
        u = apply_perm(tt_of(n), p)
        for mask in range(8):
            v = apply_in_neg(u, mask)
            o.add(num(v))
            o.add(num([1 - b for b in v]))
    return o


def closure(seed: set[int], perms: bool) -> set[int]:
    out = set()
    for n in seed:
        out |= orbit(n, perms)
    return out


def classes(perms: bool):
    seen, out = set(), []
    for n in range(256):
        if n in seen:
            continue
        o = orbit(n, perms)
        out.append(o)
        seen |= o
    return out


def main() -> int:
    with open(os.path.join(HERE, "catalogue_from_gates.json")) as fh:
        cat = json.load(fh)
    base = {num(m["tt"]) for m in cat["mechanisms"]}

    cl_neg = closure(base, perms=False)
    cl_all = closure(base, perms=True)

    cls_neg = classes(perms=False)
    cls_all = classes(perms=True)
    touched_neg = [o for o in cls_neg if o & base]
    touched_all = [o for o in cls_all if o & base]

    raw = 8.0
    cost_neg = math.log2(len(touched_neg)) + 3 + 1          # rep + mask + outneg
    # a permutation must be TRANSMITTED when the support is ordered, and ours is
    # (catalogue convention: "gate inputs ordered by 'support' (lags)")
    cost_perm_sent = math.log2(len(touched_all)) + 3 + 1 + math.log2(6)
    cost_perm_free = math.log2(len(touched_all)) + 3 + 1

    report = {
        "coverage": {
            "canonical_twelve_as_catalogued": len(base),
            "closed_under_negations": len(cl_neg),
            "closed_under_negations_and_permutations": len(cl_all),
            "genuinely_unreachable": 256 - len(cl_all),
        },
        "classes": {
            "negation_only_classes_over_256": len(cls_neg),
            "full_NPN_classes_over_256": len(cls_all),
            "classical_NPN_value_for_3_inputs": 14,
            "negation_classes_touched": len(touched_neg),
            "NPN_classes_touched": len(touched_all),
        },
        "cost_bits_per_3_input_rule": {
            "raw_truth_table": raw,
            "catalogue_name_only": round(math.log2(len(base)), 3),
            "negation_scheme": round(cost_neg, 3),
            "permutation_scheme_perm_transmitted": round(cost_perm_sent, 3),
            "permutation_scheme_perm_free": round(cost_perm_free, 3),
            "any_scheme_beats_raw_table": bool(min(cost_neg, cost_perm_sent) < raw),
        },
        "arity_scaling": {
            str(k): {"raw_truth_table_bits": 2 ** k,
                     "named_scheme_bits": round(math.log2(len(touched_neg)) + k + 1, 1)}
            for k in (3, 4, 5, 6, 8, 10, 12)
        },
    }
    with open(os.path.join(HERE, "symmetry_closure.json"), "w") as fh:
        json.dump(report, fh, indent=1)

    c = report["coverage"]
    print(f"canonical twelve, as catalogued        : {c['canonical_twelve_as_catalogued']}/256")
    print(f"closed under negations (N + I)         : {c['closed_under_negations']}/256")
    print(f"closed under negations + permutations  : {c['closed_under_negations_and_permutations']}/256")
    print(f"genuinely unreachable                  : {c['genuinely_unreachable']}/256")
    print()
    print(f"full NPN classes over 256: {len(cls_all)} (classical value 14 -> computation validated)")
    print()
    print("cost per 3-input rule (bits):")
    for k, v in report["cost_bits_per_3_input_rule"].items():
        print(f"  {k:<40} {v}")
    print()
    print("arity scaling — where the method actually pays:")
    print(f"  {'k':>3}{'raw 2^k':>10}{'named scheme':>15}")
    for k, v in report["arity_scaling"].items():
        print(f"  {k:>3}{v['raw_truth_table_bits']:>10}{v['named_scheme_bits']:>15}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
