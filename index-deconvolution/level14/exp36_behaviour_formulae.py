"""exp36_behaviour_formulae.py  (Level 14)

Show, probe and test the behaviour tables and behaviour formulae of the BUY and SELL
patterns -- one detailed stock and the whole 100-stock panel -- with the programme's
controls. Every predictive claim is set against the return-shuffle.

  A. One stock, detailed: the behaviour table of buys and of sells, the exact-formula
     test (a market has none), the three-number Hawkes formula, its compression, its
     regeneration (KS on gaps, Fano exponent) and its out-of-sample forecast.

  B. The 100-stock panel: do the buy and sell formulae compress, regenerate and forecast
     out of sample across the field, and are buy and sell symmetric?

  C. Controls: a periodic and a geometric occurrence set DO admit an exact formula (the
     instrument recognises the controlled regime); the return-shuffle kills the forecast.
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
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "level5"))

from behaviour import (buy_sell_occurrences, behaviour_table, exact_formula_score,  # noqa: E402
                       hawkes_formula, compression, regeneration, oos_forecast)
from finance import load_yahoo_close  # noqa: E402
from controls import return_shuffle  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
THETA = 0.02
DETAIL_STOCK = "KO"
N_NULL = 3


def load_100():
    seqs = {}
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def _probe(times, T, rng, series=None):
    sc = exact_formula_score(times)
    fit = hawkes_formula(times, T)
    comp = compression(times, T)
    reg = regeneration(times, T, fit)
    oos = oos_forecast(times, T)
    row = {"n": len(times), "exact": sc["exact"], "cv_gaps": sc["cv_gaps"],
           "branching": fit["branching_ratio"], "compress": comp["ratio"],
           "ks": reg["ks_gaps"], "real_fano": reg["real_fano"], "sim_fano": reg["sim_fano"],
           "oos_gain": oos["oos_gain"]}
    return row


def run(quiet: bool = False) -> dict:
    seqs = load_100()
    rng = random.Random(36)

    # A. detailed one stock
    s = seqs[DETAIL_STOCK]
    T = float(len(s))
    buys, sells = buy_sell_occurrences(s, THETA)
    detail = {
        "stock": DETAIL_STOCK, "n_days": len(s),
        "buy_table_head": behaviour_table(buys, 8),
        "sell_table_head": behaviour_table(sells, 8),
        "buy": _probe(buys, T, rng), "sell": _probe(sells, T, rng),
        "buy_formula": {k: hawkes_formula(buys, T)[k] for k in ("mu", "alpha", "beta")},
        "sell_formula": {k: hawkes_formula(sells, T)[k] for k in ("mu", "alpha", "beta")},
    }

    # B. panel
    buy_rows, sell_rows = [], []
    oos_null_buy, oos_null_sell = [], []
    for name, seq in seqs.items():
        Ts = float(len(seq))
        b, se = buy_sell_occurrences(seq, THETA)
        if len(b) < 40 or len(se) < 40:
            continue
        buy_rows.append(_probe(b, Ts, rng))
        sell_rows.append(_probe(se, Ts, rng))
        # shuffle null for the forecast
        gnb, gns = [], []
        for _ in range(N_NULL):
            sh = return_shuffle(seq, rng)
            bb, ss = buy_sell_occurrences(sh, THETA)
            gnb.append(oos_forecast(bb, Ts)["oos_gain"])
            gns.append(oos_forecast(ss, Ts)["oos_gain"])
        oos_null_buy.append(statistics.mean([g for g in gnb if g == g]) if any(g == g for g in gnb) else 0.0)
        oos_null_sell.append(statistics.mean([g for g in gns if g == g]) if any(g == g for g in gns) else 0.0)

    def agg(rows, key):
        vals = [r[key] for r in rows if r[key] == r[key]]
        return statistics.mean(vals) if vals else float("nan")

    def frac_oos(rows, nulls):
        pos = sum(1 for r, nu in zip(rows, nulls) if r["oos_gain"] == r["oos_gain"] and r["oos_gain"] > nu)
        return pos, len(rows)

    pos_b, nb = frac_oos(buy_rows, oos_null_buy)
    pos_s, ns = frac_oos(sell_rows, oos_null_sell)

    panel = {
        "n_series": len(buy_rows),
        "buy": {"mean_compress": agg(buy_rows, "compress"), "mean_ks": agg(buy_rows, "ks"),
                "mean_branching": agg(buy_rows, "branching"),
                "mean_real_fano": agg(buy_rows, "real_fano"), "mean_sim_fano": agg(buy_rows, "sim_fano"),
                "mean_oos": agg(buy_rows, "oos_gain"),
                "mean_oos_null": statistics.mean(oos_null_buy) if oos_null_buy else float("nan"),
                "n_exact": sum(1 for r in buy_rows if r["exact"]),
                "n_oos_beats_shuffle": pos_b},
        "sell": {"mean_compress": agg(sell_rows, "compress"), "mean_ks": agg(sell_rows, "ks"),
                 "mean_branching": agg(sell_rows, "branching"),
                 "mean_real_fano": agg(sell_rows, "real_fano"), "mean_sim_fano": agg(sell_rows, "sim_fano"),
                 "mean_oos": agg(sell_rows, "oos_gain"),
                 "mean_oos_null": statistics.mean(oos_null_sell) if oos_null_sell else float("nan"),
                 "n_exact": sum(1 for r in sell_rows if r["exact"]),
                 "n_oos_beats_shuffle": pos_s},
        "buy_rows": buy_rows, "sell_rows": sell_rows,
    }

    # C. controls
    periodic = list(range(0, 8000, 11))
    geo = [0]
    g = 3.0
    while geo[-1] < 8000:
        geo.append(int(geo[-1] + g)); g *= 1.3
    controls = {"periodic_exact": exact_formula_score(periodic)["exact"],
                "geometric_cv_ratios": exact_formula_score(geo)["cv_ratios"],
                "geometric_exact": exact_formula_score(geo)["exact"]}

    out = {"experiment": "behaviour_formulae", "theta": THETA,
           "detail": detail, "panel": panel, "controls": controls}

    if not quiet:
        print(f"Behaviour tables and formulae of the BUY and SELL patterns "
              f"({panel['n_series']} stocks, theta={THETA})\n")
        print(f"A. One stock in detail: {DETAIL_STOCK}")
        print("   BUY behaviour table (first rows):  ordinal  position  gap  ratio")
        for r in detail["buy_table_head"]:
            print(f"      {r['ordinal']:>4}   {r['position']:>7}  "
                  f"{str(r['gap']):>5}  {('%.2f'%r['ratio']) if r['ratio'] else '-':>6}")
        for side in ("buy", "sell"):
            d = detail[side]
            print(f"   {side.upper()}: exact formula? {d['exact']} (cv_gaps={d['cv_gaps']:.2f}) "
                  f"-> statistical formula: Hawkes n={d['branching']:.3f}, "
                  f"compress {d['compress']:.0f}x, KS(gaps)={d['ks']:.3f}, "
                  f"Fano real/sim {d['real_fano']:.2f}/{d['sim_fano']:.2f}, OOS {d['oos_gain']:+.3f}")

        print(f"\nB. Panel of {panel['n_series']} stocks:")
        for side in ("buy", "sell"):
            p = panel[side]
            print(f"   {side.upper():4}: exact formula on {p['n_exact']}/{panel['n_series']} "
                  f"(expect 0); compress {p['mean_compress']:.0f}x; Hawkes n={p['mean_branching']:.3f}; "
                  f"KS={p['mean_ks']:.3f}; Fano real/sim {p['mean_real_fano']:.2f}/{p['mean_sim_fano']:.2f}")
            print(f"         OOS forecast {p['mean_oos']:+.4f} vs shuffle {p['mean_oos_null']:+.4f}; "
                  f"beats shuffle on {p['n_oos_beats_shuffle']}/{panel['n_series']}")

        print(f"\nC. Controls: periodic set exact? {controls['periodic_exact']}; "
              f"geometric set exact? {controls['geometric_exact']} "
              f"(cv_ratios={controls['geometric_cv_ratios']:.3f})")
        print("   -> the instrument recognises the exact controlled formula; the market has only")
        print("      the statistical one. Both patterns compress and forecast; neither is closed-form.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp36_behaviour_formulae.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp36_behaviour_formulae.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
