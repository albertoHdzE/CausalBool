#!/usr/bin/env python
"""Phase 1, ledger entry B4 — description length of the two encodings.

Does the index-set representation describe the same conditional relationship in
fewer bits than a conditional probability table? The comparison is two-part,
L(model) + L(data | model), on the identical frames, with the belief network's
parameters given Rissanen's optimal precision.

Controls run first and the verdict is void without them:

  rule 110       a deterministic system. The index-set encoding must win by a
                 wide margin; if it does not, the encoding cannot express the
                 structure it was designed for.
  random         independent uniform symbols. Neither encoding may beat the
                 marginal baseline. If the index-set side wins here, the bit
                 accounting is biased in its favour and the verdict is void.

Run:
    .venv/bin/python scripts/phase1_b4_description_length.py [--boot N] [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
import warnings

warnings.filterwarnings("ignore")

from imp_prices import RegimeDiscretiser, SERIES, TARGET, load_and_split
from imp_prices.config import RESULTS
from imp_prices.controls import random_frame, rule110_frame
from imp_prices.index_set import (best_by_total, bootstrap_parent_sets,
                                  prequential_bits, scan_codes)

MAX_INDEGREE = 3


def banner(t, quiet):
    if not quiet:
        print(f"\n{'=' * 78}\n{t}\n{'=' * 78}")


def compare(frame, target, columns, alphabet, label, quiet):
    """Best index-set code against best CPT code, and the marginal baseline."""
    tab = scan_codes(frame, target, columns, MAX_INDEGREE, alphabet)
    marg = tab[tab["k"] == 0].iloc[0]
    isb = best_by_total(tab[tab["k"] > 0], "index-set")
    cpt = best_by_total(tab[tab["k"] > 0], "cpt")
    out = dict(label=label, n=int(len(frame) - 1), alphabet=alphabet,
               marginal_total=float(marg["total_bits"]),
               index_set=isb.to_dict(), cpt=cpt.to_dict(),
               index_set_minus_cpt=round(float(isb["total_bits"] - cpt["total_bits"]), 2),
               index_set_beats_cpt=bool(isb["total_bits"] < cpt["total_bits"]),
               index_set_beats_marginal=bool(isb["total_bits"] < marg["total_bits"]),
               cpt_beats_marginal=bool(cpt["total_bits"] < marg["total_bits"]))
    if not quiet:
        print(f"  {label}")
        print(f"    marginal baseline (no parents)      {marg['total_bits']:9.2f} bits")
        for name, r in (("index-set", isb), ("CPT      ", cpt)):
            print(f"    {name}  {r['parents']:<26s} {r['total_bits']:9.2f} bits "
                  f"= model {r['model_bits']:8.2f} + data {r['data_bits']:8.2f}")
        d = out["index_set_minus_cpt"]
        verdict = "index-set WINS" if d < 0 else "CPT wins"
        print(f"    difference {d:+.2f} bits  ->  {verdict}"
              f"   (beats marginal: index-set {out['index_set_beats_marginal']}, "
              f"CPT {out['cpt_beats_marginal']})")
    return out, tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--boot", type=int, default=500)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    out = {"config": dict(max_indegree=MAX_INDEGREE, n_boot=args.boot)}

    # ---- controls ---------------------------------------------------------
    banner("CONTROLS — the verdict is void without these", args.quiet)
    ca = rule110_frame(width=7, steps=200)
    out["control_rule110"], _ = compare(ca, "c0", list(ca.columns), 2,
                                        "rule 110 (deterministic)", args.quiet)
    rnd = random_frame(width=7, steps=200, n_values=3)
    out["control_random"], _ = compare(rnd, "c0", list(rnd.columns), 3,
                                       "random (must favour neither)", args.quiet)

    # ---- the panel --------------------------------------------------------
    banner("THE PANEL — GWP3 log-return discretisation, training window", args.quiet)
    split = load_and_split()
    frame = RegimeDiscretiser("gaussian").fit(split.train).transform(split.full)
    train = frame.reindex(split.train.index).dropna().astype(int)

    out["panel"], tab = compare(train, TARGET, SERIES, 3,
                                "all seven candidate parents", args.quiet)
    tab.sort_values("total_bits").to_csv(
        os.path.join(RESULTS, "b4_code_lengths.csv"), index=False)

    # Same parent set for both, isolating the encoding from the selection.
    banner("LIKE FOR LIKE — both encodings on the belief network's own parent set",
           args.quiet)
    bn_parents = ["WTI_CL"]
    sub = tab[(tab["parents"] == "+".join(bn_parents))]
    pair = {r["model"]: r for _, r in sub.iterrows()}
    out["like_for_like"] = dict(
        parents="+".join(bn_parents),
        index_set_total=float(pair["index-set"]["total_bits"]),
        cpt_total=float(pair["cpt"]["total_bits"]),
        difference=round(float(pair["index-set"]["total_bits"]
                               - pair["cpt"]["total_bits"]), 2))
    if not args.quiet:
        for m in ("index-set", "cpt"):
            r = pair[m]
            print(f"  {m:<10s} {r['total_bits']:9.2f} bits = model {r['model_bits']:8.2f} "
                  f"+ data {r['data_bits']:8.2f}   ({r['n_patterns']} patterns)")
        print(f"  difference {out['like_for_like']['difference']:+.2f} bits")

    # ---- prequential: the same question without a precision convention ----
    banner("PREQUENTIAL CODE LENGTH — no parameter-precision convention", args.quiet)
    preq = []
    for parents in ([], bn_parents, list(best_by_total(tab[tab["k"] > 0],
                                                       "index-set")["parents"].split("+"))):
        for model in ("index-set", "cpt"):
            if not parents and model == "index-set":
                continue
            preq.append(prequential_bits(train, TARGET, parents, model))
    out["prequential"] = preq
    if not args.quiet:
        for r in preq:
            print(f"  {r['model']:<10s} {r['parents']:<26s} "
                  f"{r['prequential_bits']:9.2f} bits over {r['n_scored']} months "
                  f"({r['bits_per_observation']:.4f} per month)")

    # ---- stability of our own selection (index-set half of B5) ------------
    banner("STABILITY, LIKE FOR LIKE (identical moving-block resamples)", args.quiet)
    out["bootstrap"] = {}
    for scorer in ("index-set", "cpt"):
        b = bootstrap_parent_sets(train, TARGET, SERIES, MAX_INDEGREE, 3,
                                  n_boot=args.boot, seed=42, block=12, scorer=scorer)
        out["bootstrap"][scorer] = b
        if not args.quiet:
            print(f"  {scorer}: {b['n_distinct_winners']} distinct winning parent sets "
                  f"over {b['n_boot']} resamples; modal {b['modal_parents']} "
                  f"at {100 * b['modal_frequency']:.1f}%")
            for r in b["top"][:5]:
                print(f"      {r['parents']:<28s} {100 * r['frequency']:5.1f}%")

    # The belief network's own search, on the same resamples. This is the only
    # way to know whether the hash instability of C13 is accompanied by
    # statistical instability, or is separate from it.
    banner("THE BELIEF NETWORK'S OWN SEARCH ON THE SAME RESAMPLES", args.quiet)
    import numpy as np
    from imp_prices.belief_network import frame_B, learn_structure
    from imp_prices.index_set import block_bootstrap_indices

    B_train = frame_B(train)
    rng = np.random.default_rng(42)
    hc_wins = {}
    n_hc = min(args.boot, 120)
    for _ in range(n_hc):
        take = block_bootstrap_indices(len(B_train), 12, rng)
        boot_frame = B_train.iloc[take].reset_index(drop=True)
        try:
            m = learn_structure(boot_frame, "bic-d", 2, None)
            pa = tuple(sorted(m.get_parents("forecast")))
        except Exception:
            continue
        hc_wins[pa] = hc_wins.get(pa, 0) + 1
    ranked = sorted(hc_wins.items(), key=lambda kv: -kv[1])
    out["bootstrap"]["hill_climb"] = dict(
        n_boot=n_hc, n_distinct_winners=len(hc_wins),
        modal_parents="+".join(ranked[0][0]) or "(none)",
        modal_frequency=round(ranked[0][1] / n_hc, 4),
        top=[dict(parents="+".join(p) or "(none)", frequency=round(c / n_hc, 4))
             for p, c in ranked[:8]])
    if not args.quiet:
        h = out["bootstrap"]["hill_climb"]
        print(f"  hill climbing (BIC-d, in-degree <= 2): {h['n_distinct_winners']} distinct "
              f"parent sets for the forecast node over {h['n_boot']} resamples; "
              f"modal {h['modal_parents']} at {100 * h['modal_frequency']:.1f}%")
        for r in h["top"][:5]:
            print(f"      {r['parents']:<28s} {100 * r['frequency']:5.1f}%")

    # ---- verdict ----------------------------------------------------------
    banner("VERDICT (ledger B4)", args.quiet)
    controls_ok = (out["control_rule110"]["index_set_beats_cpt"]
                   and not out["control_random"]["index_set_beats_marginal"])
    out["controls_pass"] = bool(controls_ok)
    out["b4_index_set_wins"] = bool(out["panel"]["index_set_beats_cpt"])
    out["b4_anything_beats_marginal"] = bool(out["panel"]["index_set_beats_marginal"]
                                             or out["panel"]["cpt_beats_marginal"])
    if not args.quiet:
        print(f"  controls pass                              : {out['controls_pass']}")
        print(f"  B4, index-set beats CPT on the panel       : {out['b4_index_set_wins']}")
        print(f"  either encoding beats the marginal baseline: {out['b4_anything_beats_marginal']}")

    out["content_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    out["provenance"] = dict(runtime_seconds=round(time.time() - t0, 1))
    if not args.quiet:
        print(f"  content sha256 {out['content_sha256'][:16]} "
              f"(runtime {out['provenance']['runtime_seconds']}s)")

    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "b4_description_length.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    return 0


if __name__ == "__main__":
    sys.exit(main())
