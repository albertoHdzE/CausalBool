"""exp09_deterministic_backbone.py  (Level 2)

Test whether a binarised market series has a deterministic backbone: schemata
(pivots) committed on training data that keep predicting out of sample.  Compared
against a time-shuffle control (temporal structure destroyed) and a deterministic
cellular-automaton control (which must be fully covered at perfect purity).

Rigour: schemata are found on training with high purity and a minimum firing
count, then applied unchanged to the test period.  The shuffle control shows how
much apparent determinism is an artefact of multiple testing.
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

from finance import align_prices, daily_returns, sign_states, base_rate  # noqa: E402
from ca_deconvolution import evolve_eca  # noqa: E402
from schema_pockets import find_pockets, evaluate_pockets  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "SPY"]

MAX_SUPPORT = 3
MIN_COUNT = 8
MIN_PURITY = 0.85


def market_states():
    paths = {t: os.path.join(DATA_DIR, f"{t}.json") for t in TICKERS
             if os.path.exists(os.path.join(DATA_DIR, f"{t}.json"))}
    tk, dates, M = align_prices(paths)
    return tk, sign_states(daily_returns(M))


def backbone_over_targets(states, split):
    train, test = states[:split], states[split:]
    n = len(states[0])
    cov = []
    acc = []
    for target in range(n):
        pockets = find_pockets(train, target, MAX_SUPPORT, MIN_COUNT, MIN_PURITY)
        r = evaluate_pockets(test, target, pockets)
        cov.append(r["coverage"])
        acc.append(r["accuracy_on_covered"] if r["covered"] else float("nan"))
    valid = [a for a in acc if a == a]  # drop NaN
    return {
        "mean_coverage": sum(cov) / len(cov),
        "mean_accuracy_on_covered": sum(valid) / len(valid) if valid else 0.0,
        "targets_with_coverage": len(valid),
    }


def run():
    out = {}
    tk, S = market_states()
    split = int(0.6 * len(S))
    n = len(S[0])
    br = sum(base_rate(S[split:], j) for j in range(n)) / n

    real = backbone_over_targets(S, split)

    # time-shuffle control: destroy temporal order, keep marginals
    rng = random.Random(7)
    Sh = S[:]
    rng.shuffle(Sh)
    shuffle = backbone_over_targets(Sh, split)

    # deterministic control: rule-110 CA
    rca = random.Random(110)
    ca = evolve_eca(110, [rca.randint(0, 1) for _ in range(9)], 400)
    csplit = int(0.6 * len(ca))
    ca_res = backbone_over_targets(ca, csplit)

    print(f"market: {n} tickers, {len(S)} days; base rate {br:.3f}")
    print("\n=== deterministic backbone, out of sample (schemata committed on train) ===")
    print(f"  REAL market   : coverage {real['mean_coverage']:.3f}, "
          f"accuracy-on-covered {real['mean_accuracy_on_covered']:.3f}")
    print(f"  SHUFFLE control: coverage {shuffle['mean_coverage']:.3f}, "
          f"accuracy-on-covered {shuffle['mean_accuracy_on_covered']:.3f}")
    print(f"  CA control     : coverage {ca_res['mean_coverage']:.3f}, "
          f"accuracy-on-covered {ca_res['mean_accuracy_on_covered']:.3f}")

    edge_real = real["mean_accuracy_on_covered"] - br
    edge_shuf = shuffle["mean_accuracy_on_covered"] - br
    print(f"\n  edge over base rate: real {edge_real:+.3f}  vs  shuffle {edge_shuf:+.3f}")
    verdict = ("a genuine deterministic backbone" if edge_real > edge_shuf + 0.03
               else "NOT distinguishable from a multiple-testing artefact")
    print(f"  verdict: the covered subset is {verdict}.")

    out = {"base_rate": br, "real": real, "shuffle": shuffle, "ca_control": ca_res,
           "edge_real": edge_real, "edge_shuffle": edge_shuf,
           "params": {"max_support": MAX_SUPPORT, "min_count": MIN_COUNT,
                      "min_purity": MIN_PURITY}}
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp09_deterministic_backbone.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwritten: results/exp09_deterministic_backbone.json")
    return out


if __name__ == "__main__":
    run()
