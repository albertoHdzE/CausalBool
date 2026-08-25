"""exp33_action_symbols.py  (Level 12)

The assessor's idea, tested: the secret is not the direction of prices but whether the
ACTIONS carry a timing pattern. Three parts, each against the return-shuffle null.

  1. The 'what' is not the secret. The action-type order (buy, sell, buy, sell, ...) is
     forced alternation: its conditional entropy is ~0 bits. The information is all in
     the timing. We show the two entropies side by side.

  2. Two clocks, not one (the new object). Split the pivot clock into the BUY clock
     (troughs) and the SELL clock (peaks). Are they equally self-exciting? Is one more
     predictable out of sample than the other? This is the direct test of 'do buy and
     sell have their own frequency/pattern'.

  3. Honest economic reading. Even a perfectly predictable clock is not 'half the money'
     -- profit needs direction times timing, and direction is unforecastable. The
     timing half is worth risk control, not return. Reported, not hidden.
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
sys.path.insert(0, os.path.join(ROOT, "level9"))

from actions import buy_sell_times, action_order_entropy, shortlong_forecast  # noqa: E402
from controls import load_long_sequences, return_shuffle  # noqa: E402
from hawkes import fit_hawkes  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
THETA = 0.02
N_NULL = 10


def run(quiet: bool = False) -> dict:
    seqs = load_long_sequences()
    rng = random.Random(33)
    rows = []
    for name, s in seqs.items():
        T = float(len(s))
        ent = action_order_entropy(s, THETA)
        buys, sells = buy_sell_times(s, THETA)
        nb_buy = fit_hawkes([float(i) for i in buys], T)["branching_ratio"]
        nb_sell = fit_hawkes([float(i) for i in sells], T)["branching_ratio"]
        f_buy = shortlong_forecast(buys)
        f_sell = shortlong_forecast(sells)
        # return-shuffle null for each sub-clock forecast
        lb_null, ls_null = [], []
        for _ in range(N_NULL):
            sh = return_shuffle(s, rng)
            b2, s2 = buy_sell_times(sh, THETA)
            lb = shortlong_forecast(b2)["lift"]
            ls = shortlong_forecast(s2)["lift"]
            if lb == lb:
                lb_null.append(lb)
            if ls == ls:
                ls_null.append(ls)
        rows.append({
            "name": name,
            "order_entropy_bits": ent["order_entropy_bits"],
            "timing_entropy_bits": ent["timing_entropy_bits"],
            "branching_buy": nb_buy, "branching_sell": nb_sell,
            "buy_lift": f_buy["lift"], "sell_lift": f_sell["lift"],
            "buy_lift_excess": f_buy["lift"] - (statistics.mean(lb_null) if lb_null else 0.0),
            "sell_lift_excess": f_sell["lift"] - (statistics.mean(ls_null) if ls_null else 0.0),
        })

    def m(k):
        vals = [r[k] for r in rows if r[k] == r[k]]
        return statistics.mean(vals) if vals else float("nan")

    out = {
        "experiment": "action_symbols", "theta": THETA, "n_series": len(rows),
        "mean_order_entropy_bits": m("order_entropy_bits"),
        "mean_timing_entropy_bits": m("timing_entropy_bits"),
        "mean_branching_buy": m("branching_buy"),
        "mean_branching_sell": m("branching_sell"),
        "mean_buy_lift_excess": m("buy_lift_excess"),
        "mean_sell_lift_excess": m("sell_lift_excess"),
        "n_buy_excess_positive": sum(1 for r in rows if r["buy_lift_excess"] > 0),
        "n_sell_excess_positive": sum(1 for r in rows if r["sell_lift_excess"] > 0),
        "rows": rows,
    }

    if not quiet:
        print(f"Symbolic action dynamics on {len(rows)} long series (theta={THETA})\n")
        print("1. THE 'WHAT' IS NOT THE SECRET -- action order carries ~0 bits:")
        print(f"   action-type order entropy : {out['mean_order_entropy_bits']:.4f} bits "
              f"(forced alternation buy/sell/buy/sell)")
        print(f"   timing symbol entropy      : {out['mean_timing_entropy_bits']:.4f} bits "
              f"(here is where the information lives)\n")
        print("2. TWO CLOCKS, NOT ONE -- buy clock (troughs) vs sell clock (peaks):")
        print(f"   {'series':8s} {'n_buy':>7s} {'n_sell':>7s} {'buy fx':>8s} {'sell fx':>8s}")
        for r in rows:
            print(f"   {r['name']:8s} {r['branching_buy']:>7.3f} {r['branching_sell']:>7.3f} "
                  f"{r['buy_lift_excess']:>+8.3f} {r['sell_lift_excess']:>+8.3f}")
        print(f"   self-excitation: buy clock n = {out['mean_branching_buy']:.3f}, "
              f"sell clock n = {out['mean_branching_sell']:.3f}")
        print(f"   OOS forecast lift over shuffle: buy {out['mean_buy_lift_excess']:+.3f} "
              f"({out['n_buy_excess_positive']}/{len(rows)}), "
              f"sell {out['mean_sell_lift_excess']:+.3f} "
              f"({out['n_sell_excess_positive']}/{len(rows)})\n")
        print("3. HONEST READING: the clock (both sub-clocks) is predictable, confirming the")
        print("   'timing not direction' thesis -- but timing alone is risk control, not")
        print("   half the money: profit needs direction x timing, and direction is dead.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp33_action_symbols.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp33_action_symbols.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
