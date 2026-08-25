"""exp06_market_simulation.py

Wider multi-sector market study.  Compares the determinism of two
characterisations of the same data (all days versus disruptive-event days),
fits the best small-support directional model per instrument, and generates a
model-directed price path to compare against reality.  Exports the comparison
data for the Wolfram notebook.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from finance import (align_prices, daily_returns, sign_states, event_states,
                     analyse, base_rate, best_support_accuracy,
                     evaluate_out_of_sample)

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(HERE, "finance", "data")
RESULTS_DIR = os.path.join(HERE, "results")

SECTORS = {
    "tech": ["AAPL", "MSFT", "NVDA", "GOOGL", "AMZN", "META"],
    "energy": ["XOM", "CVX", "COP"],
    "materials_gold": ["GLD", "NEM", "FCX"],
    "finance": ["JPM", "BAC", "GS"],
    "consumer_ag": ["ADM", "DE", "KO", "PG"],
    "healthcare": ["JNJ", "PFE", "UNH"],
    "index": ["SPY"],
}
REPRESENTATIVE = "SPY"


def all_tickers():
    out = []
    for v in SECTORS.values():
        out.extend(v)
    return [t for t in out if os.path.exists(os.path.join(DATA_DIR, f"{t}.json"))]


def run():
    tickers = all_tickers()
    paths = {t: os.path.join(DATA_DIR, f"{t}.json") for t in tickers}
    tk, dates, matrix = align_prices(paths)
    R = daily_returns(matrix)
    daily = sign_states(R)
    ev_idx, events = event_states(R, quantile=0.70)

    print(f"{len(tk)} instruments, {len(daily)} daily transitions, "
          f"{len(events)} disruptive-event days")

    daily_res = analyse(daily, max_k=2)
    event_res = analyse(events, max_k=2)

    print("\n=== determinism: all days vs disruptive-event days ===")
    print(f"  all days   : contradiction {daily_res['mean_contradiction_rate']:.3f}, "
          f"best acc {daily_res['mean_best_accuracy']:.3f}, base {daily_res['mean_base_rate']:.3f}, "
          f"exact {daily_res['exact_nodes']}/{daily_res['n_nodes']}")
    print(f"  event days : contradiction {event_res['mean_contradiction_rate']:.3f}, "
          f"best acc {event_res['mean_best_accuracy']:.3f}, base {event_res['mean_base_rate']:.3f}, "
          f"exact {event_res['exact_nodes']}/{event_res['n_nodes']}")

    # out-of-sample evaluation (train on the first 60%, test on the last 40%),
    # which removes the look-ahead bias that inflates any in-sample edge.
    s = int(0.60 * len(daily))
    train, test = daily[:s], daily[s:]
    R_test = R[s:]

    per_ticker = []
    for i, t in enumerate(tk):
        oos = evaluate_out_of_sample(train, test, R_test, i, len(tk), 2)
        per_ticker.append({"ticker": t, "oos_accuracy": oos["oos_accuracy"],
                           "base_rate": base_rate(test, i),
                           "support_size": len(oos["support"])})
    mean_oos = sum(p["oos_accuracy"] for p in per_ticker) / len(per_ticker)
    mean_base_test = sum(p["base_rate"] for p in per_ticker) / len(per_ticker)
    print("\n=== out-of-sample directional prediction (train 60% / test 40%) ===")
    print(f"  mean OOS directional accuracy : {mean_oos:.3f}")
    print(f"  mean base rate (test)         : {mean_base_test:.3f}")
    print(f"  mean OOS edge over base       : {mean_oos - mean_base_test:+.3f}")

    # representative instrument: out-of-sample model-directed path vs real
    ri = tk.index(REPRESENTATIVE)
    path = evaluate_out_of_sample(train, test, R_test, ri, len(tk), 2)
    print(f"\n=== {REPRESENTATIVE} out-of-sample directional model ===")
    print(f"  support size {len(path['support'])}, OOS accuracy {path['oos_accuracy']:.3f}, "
          f"base rate {base_rate(test, ri):.3f}")
    print(f"  real terminal {path['real_cum'][-1]:+.3f}, model-directed terminal {path['pred_cum'][-1]:+.3f}")

    summary = {
        "experiment": "market_simulation",
        "tickers": tk, "date_start": dates[0], "date_end": dates[-1],
        "sectors": SECTORS,
        "daily": {k: daily_res[k] for k in
                  ("mean_contradiction_rate", "mean_best_accuracy",
                   "mean_base_rate", "exact_nodes", "n_nodes")},
        "event": {k: event_res[k] for k in
                  ("mean_contradiction_rate", "mean_best_accuracy",
                   "mean_base_rate", "exact_nodes", "n_nodes")},
        "n_event_days": len(events),
        "out_of_sample": {"mean_oos_accuracy": mean_oos,
                          "mean_base_rate_test": mean_base_test,
                          "mean_edge": mean_oos - mean_base_test},
        "per_ticker": per_ticker,
        "representative": REPRESENTATIVE,
        "representative_oos_accuracy": path["oos_accuracy"],
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp06_market_simulation.json"), "w") as f:
        json.dump(summary, f, indent=2)

    # plot data for the Wolfram notebook (out-of-sample test period)
    test_dates = dates[s + 1: s + 1 + len(path["real_cum"])]
    plotdata = {
        "representative": REPRESENTATIVE,
        "dates": test_dates,
        "real_cum": path["real_cum"],
        "pred_cum": path["pred_cum"],
        "per_ticker": per_ticker,
        "oos_accuracy": path["oos_accuracy"],
        "base_rate": base_rate(test, ri),
        "mean_oos_accuracy": mean_oos,
        "mean_base_rate_test": mean_base_test,
        "daily_contradiction": daily_res["mean_contradiction_rate"],
        "event_contradiction": event_res["mean_contradiction_rate"],
    }
    with open(os.path.join(HERE, "finance", "market_plotdata.json"), "w") as f:
        json.dump(plotdata, f)

    print("\nwritten: results/exp06_market_simulation.json and finance/market_plotdata.json")
    return summary


if __name__ == "__main__":
    run()
