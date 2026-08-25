"""exp08_level2_patterns.py  (Level 2)

Compare the whole-pattern dynamics (Level 2) against a deterministic control and
against the per-node baseline, out of sample.

Positive control: a rule-110 cellular automaton trajectory, a deterministic
low-entropy system whose patterns recur, where the whole-pattern lookup must be
exact.  Test subject: the real binarised market, where patterns essentially never
recur, so the whole-pattern view cannot generalise.
"""

from __future__ import annotations

import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import align_prices, daily_returns, sign_states  # noqa: E402
from ca_deconvolution import evolve_eca  # noqa: E402
from pattern_dynamics import (evaluate_lookup, evaluate_nearest_neighbour,  # noqa: E402
                              base_rate_per_bit)

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "SPY"]


def market_states():
    paths = {t: os.path.join(DATA_DIR, f"{t}.json") for t in TICKERS
             if os.path.exists(os.path.join(DATA_DIR, f"{t}.json"))}
    tk, dates, M = align_prices(paths)
    return sign_states(daily_returns(M))


def run():
    out = {}

    # deterministic positive control: rule-110 CA, patterns recur -> exact
    rng = random.Random(110)
    ca = evolve_eca(110, [rng.randint(0, 1) for _ in range(9)], 400)
    split = int(0.6 * len(ca))
    ca_lookup = evaluate_lookup(ca, split)
    print("=== Deterministic control (rule-110 CA, 9 cells) ===")
    print(f"  whole-pattern lookup: exact-pattern {ca_lookup['exact_pattern_rate']:.3f}, "
          f"per-bit {ca_lookup['per_bit_accuracy']:.3f}, "
          f"coverage {ca_lookup['coverage_test_seen_in_train']:.3f}")
    out["control_ca"] = ca_lookup

    # market
    S = market_states()
    split = int(0.6 * len(S))
    lk = evaluate_lookup(S, split)
    nn = evaluate_nearest_neighbour(S, split)
    br = base_rate_per_bit(S, split)
    print(f"\n=== Real market ({len(S[0])} tickers, {len(S)} days) ===")
    print(f"  base rate (per bit)            : {br:.3f}")
    print(f"  Level 2 whole-pattern lookup   : per-bit {lk['per_bit_accuracy']:.3f}, "
          f"exact-pattern {lk['exact_pattern_rate']:.3f}, "
          f"coverage {lk['coverage_test_seen_in_train']:.3f}")
    print(f"  Level 2 nearest-neighbour      : per-bit {nn['per_bit_accuracy']:.3f}, "
          f"exact-pattern {nn['exact_pattern_rate']:.3f}")
    out["market"] = {"base_rate": br, "lookup": lk, "nearest_neighbour": nn,
                     "n_tickers": len(S[0]), "n_days": len(S)}

    print("\nReading: the whole-pattern map is EXACT on the deterministic control "
          "(patterns recur) and FAILS to generalise on the market (test patterns "
          "were essentially never seen in training). Treating the complete pattern "
          "as one unit does not enhance the market prediction; it worsens coverage, "
          "the curse of dimensionality. Level 1's per-node factorisation uses the "
          "data far more efficiently, and neither beats the base rate out of sample.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp08_level2_patterns.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwritten: results/exp08_level2_patterns.json")
    return out


if __name__ == "__main__":
    run()
