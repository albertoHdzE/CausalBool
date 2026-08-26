#!/usr/bin/env python
"""Threshold calibration for the Route 4 pre-registration (frozen 2026-08-25).

Design-time envelope arithmetic ONLY - no R4 route executes here. Answers one
question: on PURE NOISE, how often does some catalogue mechanism exactly
regenerate a window of w bits from its d-symbol seed context?

Method: enumerate distinct truth tables of the frozen catalogue (twelve
families, dedup, orientation-aware for implies/canalising) per support size
d in {1,2,3}; union bound over supports x mechanisms x fresh bits (w-d);
Monte Carlo ground truth on iid fair strings via sequential regeneration.

Used by PROTOCOL.md Addendum A2 (C2 budget derivation) and A1 motivation
(C4 multiple-comparisons envelope). Deterministic: rng seeded.
"""
from __future__ import annotations

import random
from itertools import combinations


def make_tt(d, fn):
    return tuple(fn([(v >> k) & 1 for k in range(d)]) for v in range(2 ** d))


def catalogue():
    tts = {1: set(), 2: set(), 3: set()}
    tts[1].add(make_tt(1, lambda b: b[0]))
    tts[1].add(make_tt(1, lambda b: 1 - b[0]))
    ops = [("and", lambda a, c: a & c), ("or", lambda a, c: a | c),
           ("xor", lambda a, c: a ^ c), ("nand", lambda a, c: 1 - (a & c)),
           ("nor", lambda a, c: 1 - (a | c)), ("xnor", lambda a, c: 1 - (a ^ c)),
           ("impl", lambda a, c: 1 - (a & (1 - c))), ("nimpl", lambda a, c: a & (1 - c))]
    for _, op in ops:
        tts[2].add(make_tt(2, lambda b, op=op: op(b[0], b[1])))
        tts[2].add(make_tt(2, lambda b, op=op: op(b[1], b[0])))
    tts[3].add(make_tt(3, lambda b: 1 if 2 * sum(b) > 3 else 0))          # MAJORITY ties->0
    for k in (1, 2, 3):
        tts[3].add(make_tt(3, lambda b, k=k: 1 if sum(b) >= k else 0))    # KOFN k-of-3
    for i in range(3):
        for v in (0, 1):
            for c in (0, 1):
                for dflt in (0, 1):
                    tts[3].add(make_tt(
                        3, lambda b, i=i, v=v, c=c, dflt=dflt: c if b[i] == v else dflt))
    return {d: sorted(tts[d]) for d in tts}


def p_union(cat, w):
    tot = 0.0
    for d in (1, 2, 3):
        n_sup = len(list(combinations((1, 2, 3), d)))
        tot += n_sup * len(cat[d]) * 2.0 ** (-(w - d))
    return min(tot, 1.0)


def mc_rate(cat, w, trials=20000, seed=20260825):
    rng = random.Random(seed)
    hits = 0
    L = w + 8
    for _ in range(trials):
        s = [rng.randint(0, 1) for _ in range(L)]
        hit = False
        for t in range(L - w + 1):
            win = s[t:t + w]
            for d in (1, 2, 3):
                found = False
                for g in cat[d]:
                    good = True
                    for k in range(w - d):
                        ctx = [win[k + d - 1 - j] for j in range(d)]
                        idx = sum(ctx[m] << m for m in range(d))
                        if g[idx] != win[k + d]:
                            good = False
                            break
                    if good:
                        found = True
                        break
                if found:
                    hit = True
                    break
            if hit:
                break
        if hit:
            hits += 1
    return hits / trials


def main():
    cat = catalogue()
    print("distinct catalogue TTs by support size:",
          {d: len(cat[d]) for d in cat})
    print("\nw    P(start regenerates|noise)  union      MC       E[raw hits|2000]  E[raw hits|7000]")
    for w in (14, 16, 20, 24, 28):
        pu = p_union(cat, w)
        pm = mc_rate(cat, w)
        print(f"{w:<4} {'':22} {pu:.3e}  {pm:.3e}  {2000 * pu:>14.2f}  {7000 * pu:>12.2f}")
    print("\nnote: raw pattern hits ignore the segmenter's strict-improvement")
    print("(economics) acceptance, which rejects isolated short spans; these")
    print("numbers are the pre-economics envelope, not expected transmissions.")


if __name__ == "__main__":
    main()
