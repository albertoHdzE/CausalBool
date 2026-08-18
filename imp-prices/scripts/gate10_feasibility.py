#!/usr/bin/env python
"""Gate 1.0 — the pre-registered feasibility test (PROTOCOL section 2).

Question: does the GWP3-discretised panel contain deterministic structure that a
gate-based model could find, over and above the two things already known to be
there — the dominance of the stagnant regime, and the persistence of the target?

The report separates three quantities, because conflating them is how this kind
of study produces a false positive:

  self       the target's own lagged regime as the only parent. This is the
             persistence benchmark of ledger anchor A11 in another guise, and it
             is not new structure.
  cross      parent sets drawn from the other six series only. This is the
             quantity that would justify a network at all.
  any        the unrestricted search, reported for completeness.

Each is compared against best-of-search under a time-order shuffle that
preserves the regime marginal exactly (rule R2), and every analyser is exercised
first on a deterministic positive control and two negative controls (rules R3,
R4).

Usage:
    .venv/bin/python scripts/gate10_feasibility.py [--shuffles N] [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time

import pandas as pd

from imp_prices import RegimeDiscretiser, SERIES, TARGET, load_and_split
from imp_prices.config import RESULTS
from imp_prices.controls import persistent_random_frame, random_frame, rule110_frame
from imp_prices.feasibility import (circular_shift_null, covariate_shift_null,
                                    coverage, scan, shuffle_null)

MIN_RECURRENCE = 0.5
MAX_INDEGREE = 3


def banner(title, quiet):
    if not quiet:
        print(f"\n{'=' * 78}\n{title}\n{'=' * 78}")


def run_block(frame, target, columns, n_values, shuffles, label, quiet, seed=42):
    """One scan against both nulls. The circular shift is the primary."""
    res = circular_shift_null(frame, target, columns, MAX_INDEGREE, n_values,
                              MIN_RECURRENCE)
    res["permutation"] = shuffle_null(frame, target, columns, MAX_INDEGREE,
                                      n_values, MIN_RECURRENCE, shuffles, seed)
    res["label"] = label
    res["n_columns"] = len(columns)
    if not quiet:
        perm = res["permutation"]
        print(f"  {label:<34s} lookup {res['observed_lookup_accuracy']:.4f}  |  "
              f"shift null {res['null_lookup_accuracy_mean']:.4f}"
              f"±{res['null_lookup_accuracy_sd']:.4f} "
              f"excess {res['excess_lookup_accuracy']:+.4f} p={res['p_lookup_accuracy']:.4f}"
              f"  |  perm null {perm['null_lookup_accuracy_mean']:.4f} "
              f"p={perm['p_lookup_accuracy']:.4f}")
    return res


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--shuffles", type=int, default=1000)
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    t0 = time.time()
    out = {"config": dict(shuffles=args.shuffles, max_indegree=MAX_INDEGREE,
                          min_recurrence=MIN_RECURRENCE)}

    # -- Controls first. A verdict on market data is void unless these pass. ---
    banner("CONTROLS (protocol rules R3, R4)", args.quiet)

    ca = rule110_frame(width=7, steps=200)
    ca_tab = scan(ca, "c0", list(ca.columns), MAX_INDEGREE, n_values=2)
    ca_best = ca_tab.loc[ca_tab["contradiction"].idxmin()]
    out["control_rule110"] = dict(best_parents=ca_best["parents"],
                                  contradiction=float(ca_best["contradiction"]),
                                  lookup_accuracy=float(ca_best["lookup_accuracy"]),
                                  recurrence=float(ca_best["recurrence"]),
                                  n_exact=int((ca_tab["contradiction"] == 0).sum()))
    if not args.quiet:
        print(f"  rule 110, positive control: best parents {ca_best['parents']}, "
              f"contradiction {ca_best['contradiction']:.4f}, "
              f"lookup accuracy {ca_best['lookup_accuracy']:.4f}")

    rnd = random_frame(width=7, steps=200, n_values=3)
    out["control_random"] = run_block(rnd, "c0", list(rnd.columns), 3,
                                      args.shuffles, "random, negative control",
                                      args.quiet)

    per = persistent_random_frame(width=7, steps=200, n_values=3, stay=0.75)
    others = [c for c in per.columns if c != "c0"]
    out["control_persistent_any"] = run_block(
        per, "c0", list(per.columns), 3, args.shuffles,
        "persistent random, any parents", args.quiet)
    out["control_persistent_cross"] = run_block(
        per, "c0", others, 3, args.shuffles,
        "persistent random, cross only", args.quiet)

    # -- The real panel. -------------------------------------------------------
    banner("THE PANEL (GWP3 log-return discretisation, training window)", args.quiet)

    split = load_and_split()
    disc = RegimeDiscretiser("gaussian").fit(split.train)
    frame = disc.transform(split.full)
    train = frame.reindex(split.train.index).dropna().astype(int)

    cov = coverage(train, SERIES)
    out["coverage"] = cov
    if not args.quiet:
        print(f"  observations {cov['n_observations']}, state space {cov['state_space']}, "
              f"distinct states {cov['distinct_states']} "
              f"(coverage {100 * cov['coverage']:.2f}%), "
              f"recurring states {cov['recurring_states']}, "
              f"max multiplicity {cov['max_multiplicity']}")

    base = float(train[TARGET].iloc[1:].value_counts(normalize=True).max())
    out["majority_base_rate"] = base
    if not args.quiet:
        print(f"  majority base rate of the one-month-ahead target: {base:.4f}")

    # Contemporaneous agreement: how much of "cross" is the target under another
    # name? WTI_CL and Brent are the same barrel as WTI_Spot.
    agree = {c: round(float((train[c] == train[TARGET]).mean()), 4)
             for c in SERIES if c != TARGET}
    out["contemporaneous_agreement"] = agree
    if not args.quiet:
        print("  contemporaneous regime agreement with the target: " +
              ", ".join(f"{c} {v:.3f}" for c, v in agree.items()))

    cross = [c for c in SERIES if c != TARGET]
    macro = ["USD_Idx", "CPI", "Fed_Funds", "Ind_Prod"]
    out["panel_self"] = run_block(train, TARGET, [TARGET], 3, args.shuffles,
                                  "self (persistence)", args.quiet)
    out["panel_cross"] = run_block(train, TARGET, cross, 3, args.shuffles,
                                   "cross (other six series)", args.quiet)
    out["panel_macro"] = run_block(train, TARGET, macro, 3, args.shuffles,
                                   "macro only (no oil series)", args.quiet)
    out["panel_any"] = run_block(train, TARGET, SERIES, 3, args.shuffles,
                                 "any (unrestricted search)", args.quiet)

    # -- The decisive question: does anything add to persistence? --------------
    banner("INCREMENT OVER PERSISTENCE (covariate-shift null)", args.quiet)
    inc_blocks = {
        "increment_all": ("all six others", cross),
        "increment_oil": ("the two oil futures", ["WTI_CL", "Brent_BZ"]),
        "increment_macro": ("the four macro series", macro),
    }
    for key, (label, extra) in inc_blocks.items():
        r = covariate_shift_null(train, TARGET, [TARGET], extra, MAX_INDEGREE)
        out[key] = r
        if not args.quiet:
            print(f"  adding {label:<24s} baseline {r['baseline_lookup_accuracy']:.4f} "
                  f"-> {r['observed_lookup_accuracy']:.4f}  increment "
                  f"{r['observed_increment']:+.4f}  (null {r['null_increment_mean']:+.4f}"
                  f"±{r['null_increment_sd']:.4f}, excess {r['excess_increment']:+.4f}, "
                  f"p={r['p_increment']:.4f})")

    # Positive control on the same statistic: the increment test must detect a
    # covariate that genuinely carries information.
    ctl = per.copy()
    ctl["c9"] = ctl["c0"].shift(-1).ffill().bfill().astype(int)  # true leading indicator
    r = covariate_shift_null(ctl, "c0", ["c0"], ["c9"], 2)
    out["control_increment_positive"] = r
    if not args.quiet:
        print(f"  control: a true leading indicator          increment "
              f"{r['observed_increment']:+.4f} excess {r['excess_increment']:+.4f} "
              f"p={r['p_increment']:.4f}  (must be significant)")

    tab = scan(train, TARGET, SERIES, MAX_INDEGREE)
    tab = tab.sort_values(["contradiction", "lookup_accuracy"],
                          ascending=[True, False])
    os.makedirs(RESULTS, exist_ok=True)
    tab.to_csv(os.path.join(RESULTS, "gate10_parent_sets.csv"), index=False)
    out["n_parent_sets"] = len(tab)
    out["recurrence_by_k"] = {
        int(k): round(float(g["recurrence"].mean()), 4)
        for k, g in tab.groupby("k")}

    if not args.quiet:
        print("\n  mean recurrence by in-degree: " +
              ", ".join(f"k={k}: {v:.3f}" for k, v in out["recurrence_by_k"].items()))
        print("\n  ten lowest-contradiction parent sets:")
        print(tab.head(10).to_string(index=False))

    # -- Verdict against the pre-registered criterion. -------------------------
    banner("VERDICT (PROTOCOL section 2, Gate 1.0)", args.quiet)
    crit = 0.05
    passes = {name: bool(out[f"panel_{name}"]["p_lookup_accuracy"] < crit)
              for name in ("self", "cross", "macro", "any")}
    out["criterion"] = dict(alpha=crit, passes=passes,
                            statistic="lookup_accuracy vs circular-shift null",
                            note="contradiction rate is saturated at this "
                                 "alphabet size and sample; see bitacora 02")
    out["gate_passes"] = passes["cross"]
    out["gate_passes_macro_only"] = passes["macro"]
    out["gate_increment_over_persistence"] = bool(out["increment_all"]["p_increment"] < crit)

    # Rule R6. Runtime is provenance, not a result: it is kept out of the
    # content hash so that determinism of the science is checkable by comparing
    # one number across runs.
    out["content_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True).encode()).hexdigest()
    out["provenance"] = dict(runtime_seconds=round(time.time() - t0, 1))

    if not args.quiet:
        for name, ok in passes.items():
            print(f"  {name:<8s} beats its shuffle null at alpha={crit}: {ok}")
        print(f"\n  GATE 1.0 (cross-variable structure): "
              f"{'PASS' if out['gate_passes'] else 'FAIL'}")
        print(f"  macro-only structure beyond persistence: "
              f"{'PASS' if out['gate_passes_macro_only'] else 'FAIL'}")
        print(f"  ANY increment over persistence alone: "
              f"{'PASS' if out['gate_increment_over_persistence'] else 'FAIL'}")
        print(f"  p-value floor at {out['panel_cross']['n_surrogates']} surrogates: "
              f"{1 / (out['panel_cross']['n_surrogates'] + 1):.4f}")
        print(f"  content sha256 {out['content_sha256'][:16]} "
              f"(runtime {out['provenance']['runtime_seconds']}s, excluded from the hash)")

    with open(os.path.join(RESULTS, "gate10_feasibility.json"), "w") as fh:
        json.dump(out, fh, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())
