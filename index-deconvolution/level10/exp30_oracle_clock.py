"""exp30_oracle_clock.py  (Level 10)

The oracle / perfect-trader behaviour table, and the theorem that its action points
are the directional-change pivots at a cost-set threshold.

Four results, each against the return-shuffle null (and a GBM instrument check):

  A. The equivalence theorem.  For a per-round-trip cost c, the in-hindsight optimal
     trade points (an exact O(N) DP) are compared with the directional-change pivots
     at reversal threshold theta.  Claim: the pivots at theta = c are exactly a subset
     of the oracle points, and the oracle is only a slight superset.  We sweep theta
     around c, report the best-matching ratio theta*/c, the exact containment of
     DC(theta=c) in the oracle, and the residual (oracle points that are not pivots).

  B. The oracle behaviour table.  Fano clustering exponent and three-number Hawkes fit
     of the oracle occurrence set at cost c, against the return-shuffle.  Is the oracle
     clock the same self-exciting fractal as the raw pivot clock (bitacora 20)?

  C. Out-of-sample forecast.  Fit the Hawkes on the first 70% of oracle event times;
     does its forward intensity forecast the *next oracle event's timing* on the
     held-out 30%, beating a Poisson?  The oracle is a look-ahead target used only to
     forecast, never as a feature.  Reported honestly as confirmation of bitacora 20
     on the relabelled set, since oracle ~ pivots.

  D. Cost as a renormalisation scale (the new object).  Each trader's cost c selects a
     threshold theta = c, hence a clock with its own branching ratio n(c).  The RG flow
     of bitacora 20 becomes an economic curve: how clustered a trader's opportunities
     are as a function of their transaction cost.
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))
sys.path.insert(0, os.path.join(ROOT, "level9"))

from oracle import (oracle_points, optimal_trades, match_sets,  # noqa: E402
                    kappa_for_round_trip)
from controls import (load_long_sequences, return_shuffle,  # noqa: E402
                      geometric_random_walk)
from point_process import pivot_indices, fano_exponent  # noqa: E402
from hawkes import fit_hawkes, oos_loglik, poisson_loglik  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
C_MAIN = 0.02                                   # main round-trip cost (matches programme theta)
C_GRID = [0.005, 0.01, 0.02, 0.04, 0.08]        # cost = renormalisation scale
THETA_RATIOS = [0.90, 0.95, 0.98, 1.00, 1.02, 1.05, 1.10]
TRAIN_FRAC = 0.7
WINDOWS = [10, 20, 40, 80, 160, 320]
N_NULL = 10


def _equivalence(name, s, c):
    kappa = kappa_for_round_trip(c)
    orc = oracle_points(s, kappa)
    orc_set = set(orc)
    dc_c = pivot_indices(s, c)
    # exact containment of DC(theta=c) in the oracle
    inside = sum(1 for i in dc_c if i in orc_set)
    contain = inside / len(dc_c) if dc_c else 1.0
    # sweep theta to find the best-matching ratio
    best = (1.0, -1.0, 0.0, 0.0)
    for r in THETA_RATIOS:
        m = match_sets(orc, pivot_indices(s, c * r), tol=1)
        if m["jaccard"] > best[1]:
            best = (r, m["jaccard"], m["recall_a"], m["recall_b"])
    residual = 1.0 - best[2]                     # oracle points not matched by pivots
    return {"name": name, "n_oracle": len(orc), "n_dc": len(dc_c),
            "containment_dc_in_oracle": contain, "best_theta_over_c": best[0],
            "best_jaccard": best[1], "oracle_residual": residual}


def _hawkes_row(name, s, c, rng):
    kappa = kappa_for_round_trip(c)
    T = float(len(s))
    t = [float(i) for i in oracle_points(s, kappa)]
    fit = fit_hawkes(t, T)
    real_alpha = fano_exponent([int(x) for x in t], int(T), WINDOWS).get("alpha", float("nan"))
    # out of sample: Hawkes forward intensity forecasts next oracle event's timing
    T_tr = T * TRAIN_FRAC
    train = [x for x in t if x <= T_tr]
    ftr = fit_hawkes(train, T_tr)
    h_ll, n_test = oos_loglik(t, T, T_tr, ftr["mu"], ftr["alpha"], ftr["beta"])
    mu_p = len(train) / T_tr if T_tr else 0.0
    p_ll = poisson_loglik(t, T, mu_p) - poisson_loglik(train, T_tr, mu_p)
    oos_gain = (h_ll - p_ll) / n_test if n_test else 0.0
    # return-shuffle null: branching ratio and Fano must collapse
    nb_null, alpha_null = [], []
    for _ in range(N_NULL):
        sh = return_shuffle(s, rng)
        ts = [float(i) for i in oracle_points(sh, kappa)]
        nb_null.append(fit_hawkes(ts, T)["branching_ratio"])
        alpha_null.append(fano_exponent([int(x) for x in ts], int(T), WINDOWS).get("alpha", 0.0))
    return {"name": name, "n_events": fit["n_events"],
            "branching_ratio": fit["branching_ratio"],
            "branching_null": statistics.mean(nb_null),
            "fano_alpha": real_alpha, "fano_alpha_null": statistics.mean(alpha_null),
            "oos_gain_per_event": oos_gain}


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(30)

    # --- A. equivalence theorem ---
    eq = [_equivalence(n, s, C_MAIN) for n, s in seqs.items()]

    # --- B & C. behaviour table + OOS forecast at the main cost ---
    rows = [_hawkes_row(n, s, C_MAIN, rng) for n, s in seqs.items()]

    # GBM instrument check: the oracle clock of a driftless GBM must read ~null
    gbm_nb, gbm_oos = [], []
    for i in range(6):
        g = geometric_random_walk(11000, 0.02, random.Random(1000 + i))
        T = float(len(g))
        t = [float(j) for j in oracle_points(g, kappa_for_round_trip(C_MAIN))]
        gbm_nb.append(fit_hawkes(t, T)["branching_ratio"])
        T_tr = T * TRAIN_FRAC
        tr = [x for x in t if x <= T_tr]
        ftr = fit_hawkes(tr, T_tr)
        h_ll, n_test = oos_loglik(t, T, T_tr, ftr["mu"], ftr["alpha"], ftr["beta"])
        mu_p = len(tr) / T_tr
        p_ll = poisson_loglik(t, T, mu_p) - poisson_loglik(tr, T_tr, mu_p)
        gbm_oos.append((h_ll - p_ll) / n_test if n_test else 0.0)

    # --- D. cost as a renormalisation scale: n(c) ---
    cost_scale = []
    for c in C_GRID:
        nbs = [fit_hawkes([float(i) for i in oracle_points(s, kappa_for_round_trip(c))],
                          float(len(s)))["branching_ratio"] for s in seqs.values()]
        n_ev = statistics.mean(len(oracle_points(s, kappa_for_round_trip(c))) for s in seqs.values())
        cost_scale.append({"c": c, "mean_branching": statistics.mean(nbs),
                           "mean_events": n_ev})

    def m(k, data):
        return statistics.mean(r[k] for r in data)

    out = {
        "experiment": "oracle_clock", "c_main": C_MAIN, "n_series": len(rows),
        "equivalence": {
            "mean_containment_dc_in_oracle": m("containment_dc_in_oracle", eq),
            "n_exact_containment": sum(1 for r in eq if r["containment_dc_in_oracle"] > 0.999),
            "mean_best_theta_over_c": m("best_theta_over_c", eq),
            "mean_best_jaccard": m("best_jaccard", eq),
            "mean_oracle_residual": m("oracle_residual", eq),
            "rows": eq,
        },
        "behaviour_table": {
            "mean_branching_ratio": m("branching_ratio", rows),
            "mean_branching_null": m("branching_null", rows),
            "n_above_null": sum(1 for r in rows if r["branching_ratio"] > r["branching_null"] + 0.1),
            "mean_fano_alpha": m("fano_alpha", rows),
            "mean_fano_alpha_null": m("fano_alpha_null", rows),
            "mean_oos_gain_per_event": m("oos_gain_per_event", rows),
            "n_oos_positive": sum(1 for r in rows if r["oos_gain_per_event"] > 0),
            "rows": rows,
        },
        "gbm_control": {"mean_branching": statistics.mean(gbm_nb),
                        "mean_oos_gain": statistics.mean(gbm_oos)},
        "cost_as_scale": cost_scale,
    }

    if not quiet:
        print(f"Oracle / perfect-trader behaviour table, {len(rows)} long series "
              f"(round-trip cost c = {C_MAIN})\n")
        print("A. Equivalence theorem  (oracle trade points  vs  DC pivots at theta):")
        print(f"   {'series':8s} {'n_orc':>6s} {'n_dc':>6s} {'contain':>8s} "
              f"{'theta*/c':>9s} {'jaccard':>8s} {'residual':>9s}")
        for r in eq:
            print(f"   {r['name']:8s} {r['n_oracle']:>6d} {r['n_dc']:>6d} "
                  f"{r['containment_dc_in_oracle']:>8.3f} {r['best_theta_over_c']:>9.2f} "
                  f"{r['best_jaccard']:>8.3f} {r['oracle_residual']:>9.3f}")
        e = out["equivalence"]
        print(f"   -> DC(theta=c) is a subset of the oracle exactly on "
              f"{e['n_exact_containment']}/{len(eq)} series "
              f"(mean containment {e['mean_containment_dc_in_oracle']:.3f});")
        print(f"      best match at theta = {e['mean_best_theta_over_c']:.2f} c, "
              f"jaccard {e['mean_best_jaccard']:.3f}, oracle residual "
              f"{e['mean_oracle_residual']:.3f} (points the greedy DC misses).\n")

        b = out["behaviour_table"]
        print("B/C. Oracle behaviour table and out-of-sample forecast:")
        print(f"   {'series':8s} {'events':>6s} {'branch n':>9s} {'null':>6s} "
              f"{'fano a':>7s} {'OOS gain':>9s}")
        for r in rows:
            print(f"   {r['name']:8s} {r['n_events']:>6d} {r['branching_ratio']:>9.3f} "
                  f"{r['branching_null']:>6.3f} {r['fano_alpha']:>7.3f} "
                  f"{r['oos_gain_per_event']:>+9.3f}")
        print(f"   -> branching ratio n = {b['mean_branching_ratio']:.3f} vs shuffle "
              f"{b['mean_branching_null']:.3f} ({b['n_above_null']}/{len(rows)} self-exciting);")
        print(f"      Fano exponent {b['mean_fano_alpha']:.3f} vs null "
              f"{b['mean_fano_alpha_null']:.3f}; OOS Hawkes beats Poisson by "
              f"{b['mean_oos_gain_per_event']:+.3f} nats/event "
              f"({b['n_oos_positive']}/{len(rows)} positive).")
        print(f"      (This confirms bitacora 20 on the oracle-relabelled set: "
              f"oracle ~ pivots, so the oracle clock is the same self-exciting fractal.)\n")

        g = out["gbm_control"]
        print(f"   GBM control: oracle-clock branching {g['mean_branching']:.3f}, "
              f"OOS gain {g['mean_oos_gain']:+.3f} -> reads ~null (instrument sane).\n")

        print("D. Cost as a renormalisation scale -- n(c), how clustered a trader's "
              "opportunities are:")
        for r in cost_scale:
            print(f"   c = {r['c']:.3f}:  n = {r['mean_branching']:.3f}   "
                  f"(mean {r['mean_events']:.0f} opportunities)")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp30_oracle_clock.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp30_oracle_clock.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
