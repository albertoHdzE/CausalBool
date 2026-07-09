"""exp05_financial.py

Apply the deconvolution's functional-support analysis to real binarised daily
stock returns, and contrast it with a real deterministic system (a rule-110
cellular-automaton trajectory of the same shape) analysed by the identical code.

The point is not to claim markets are Boolean networks; it is to use the exact
deconvolution machinery as a test for deterministic causal structure.  A cellular
automaton is recovered as deterministic (contradiction rate zero, small-support
accuracy one); binarised markets are not (high contradiction rate, accuracy near
the base rate).  The same analyser gives both answers, which shows the market
result is a property of the data, not of the method.
"""

from __future__ import annotations

import json
import os
import random
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from finance import align_prices, to_binary_states, analyse
from ca_deconvolution import evolve_eca

HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(HERE, "finance", "data")
RESULTS_DIR = os.path.join(HERE, "results")

TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "SPY"]


def financial_states():
    paths = {tk: os.path.join(DATA_DIR, f"{tk}.json") for tk in TICKERS
             if os.path.exists(os.path.join(DATA_DIR, f"{tk}.json"))}
    tickers, dates, matrix = align_prices(paths)
    states = to_binary_states(matrix)
    return tickers, dates, states


def control_states(width, n_steps):
    """A real deterministic system: rule-110 CA trajectory of matching shape.

    Each cell depends on three neighbours, so a support of size up to 3 suffices;
    the analyser must report it as deterministic (contradiction rate 0, accuracy 1).
    """
    rng = random.Random(110)
    rows = evolve_eca(110, [rng.randint(0, 1) for _ in range(width)], n_steps)
    return rows


def run():
    tickers, dates, fin_states = financial_states()
    print(f"financial data: {len(tickers)} tickers, {len(fin_states)} daily transitions "
          f"({dates[0]} to {dates[-1]})")

    fin = analyse(fin_states, max_k=2)
    ctrl_rows = control_states(len(tickers), len(fin_states) + 1)
    ctrl = analyse(ctrl_rows, max_k=3)

    print("\n=== Real market data (binarised daily up/down) ===")
    print(f"  mean contradiction rate (recurring patterns): {fin['mean_contradiction_rate']:.3f}")
    print(f"  mean base rate                              : {fin['mean_base_rate']:.3f}")
    print(f"  mean best small-support accuracy (k<=2)     : {fin['mean_best_accuracy']:.3f}")
    print(f"  mean lift over base rate                    : {fin['mean_lift_over_base']:.3f}")
    print(f"  nodes reproduced exactly                    : {fin['exact_nodes']}/{fin['n_nodes']}")

    print("\n=== Deterministic control (rule-110 cellular automaton) ===")
    print(f"  mean contradiction rate (recurring patterns): {ctrl['mean_contradiction_rate']:.3f}")
    print(f"  mean best small-support accuracy (k<=3)     : {ctrl['mean_best_accuracy']:.3f}")
    print(f"  nodes reproduced exactly                    : {ctrl['exact_nodes']}/{ctrl['n_nodes']}")

    print("\nInterpretation: the cellular automaton is recovered as an exact "
          "deterministic network; the market is not, its one-step dynamics being "
          "close to the base rate and rich in contradictions. The deconvolution "
          "separates deterministic causal systems from stochastic ones.")

    summary = {
        "experiment": "financial",
        "tickers": tickers, "date_start": dates[0], "date_end": dates[-1],
        "financial": fin, "control_rule110": ctrl,
    }
    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp05_financial.json"), "w") as f:
        json.dump(summary, f, indent=2)
    print("\nwritten: results/exp05_financial.json")
    return summary


if __name__ == "__main__":
    run()
