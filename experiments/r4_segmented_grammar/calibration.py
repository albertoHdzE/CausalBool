#!/usr/bin/env python3
"""R4 noise-envelope calibration v2 (post adversarial review F3).

Consumes ONLY the ApplyGate-generated, mirror-tested catalogue
(catalogue_from_gates.json; authority chain:
tools/r4_catalogue_mirror_test.py). Constants excluded (PROTOCOL :44).
Determinism: fixed seeds, sorted iteration, no hash-order dependence.

Event definitions (single, consistent throughout):
  E_mech(m, s, w): mechanism m reproduces positions s..s+w-1 exactly,
      predicting each position t from the string's ACTUAL preceding symbols.
      A mechanism's recurrence is fully described by its truth table tt,
      indexed by the lag-triple value st = b1 + 2*b2 + 4*b3 (b1 most recent),
      matching the WL exporter's convention; the support is baked into tt.
      Per (tt, w), P(E_mech) is EXACT via Markov DP on the 8-state triple.
  E_any(w) = OR of E_mech over distinct usable tables at one start;
      estimated empirically over all starts of seeded iid fair strings
      (+ binomial SE), with the sum-of-marginals printed AS A BOUND.

Raw-hit expectation columns are PRE-ECONOMICS envelopes (the segmenter's
strict-improvement acceptance is NOT modelled) and must be quoted as such.
"""
from __future__ import annotations

import json
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
CAT = HERE / "catalogue_from_gates.json"


def load_tables():
    cat = json.loads(CAT.read_text())
    tts = {tuple(m["tt"]) for m in cat["mechanisms"] if not m["constant"]}
    return sorted(tts)


def p_exact(tt, w):
    """Exact P(one start regenerates w positions) for one table.
    State == tt index (b1 + 2*b2 + 4*b3, b1 most recent). Each step: emit a
    fair bit, survive iff it equals tt[state]; rotate state right."""
    tt_arr = np.asarray(tt)
    probs = np.full(8, 1.0 / 8.0)
    for _ in range(w):
        nxt = np.zeros(8)
        for st in range(8):
            if probs[st] == 0.0:
                continue
            b = int(tt_arr[st])
            nst = (st >> 1) | (b << 2)
            nxt[nst] += probs[st] * 0.5
        probs = nxt
    return float(probs.sum())


def empirical_any(tables, w, n_strings=400, length=512, seed=20260825):
    """Empirical P(E_any) per start — the SAME OR-event the marginals bound."""
    rng = np.random.default_rng(seed)
    starts = np.arange(3, length - w + 1)
    total = n_strings * len(starts)
    hits = 0
    for _ in range(n_strings):
        s = rng.integers(0, 2, size=length).astype(np.int64)
        idx = s[2:length - 1] + 2 * s[1:length - 2] + 4 * s[0:length - 3]
        # idx[j] corresponds to position t = j + 3
        ok_stack = np.stack([np.asarray(tt)[idx] == s[3:] for tt in tables])
        cs = np.concatenate([np.zeros((len(tables), 1), dtype=int),
                             np.cumsum(ok_stack, axis=1)], axis=1)
        # start s covers t = s..s+w-1 -> ok-columns j = s-3 .. s+w-4
        j0 = starts - 3
        reproduced = (cs[:, j0 + w] - cs[:, j0]) == w      # (tables, starts)
        hits += int(reproduced.any(axis=0).sum())          # E_any = OR over tables
    ph = hits / total
    se = (max(ph * (1 - ph), 1e-12) / total) ** 0.5
    return ph, se


def main():
    tables = load_tables()
    print(f"usable distinct non-constant truth tables: {len(tables)}")
    ws = (8, 12, 14, 16, 20, 24)
    print("\nw    sum-of-marginals(BOUND)   empirical-P(any) +- SE"
          "      E[raw|2000 obs]  E[raw|7000 obs]")
    for w in ws:
        bound = min(sum(p_exact(t, w) for t in tables), 1.0)
        emp, se = empirical_any(tables, w)
        expected_hits = 400 * len(np.arange(3, 512 - w + 1)) * emp
        note = "" if expected_hits >= 25 else "  [<25 expected hits: weak resolution]"
        print(f"{w:<4} {bound:.3e}{'':18} {emp:.3e} +- {se:.1e}"
              f"   {2000 * emp:>14.2f}  {7000 * emp:>12.2f}{note}")
    print("\nnote: raw-hit columns are PRE-ECONOMICS envelopes (strict-improvement")
    print("acceptance NOT modelled); quote them only with that label.")


if __name__ == "__main__":
    main()
