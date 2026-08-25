"""generate_finance_cases.py

Export the binarised market states and the deterministic control states, with
the Python determinism metrics, so the Wolfram side can recompute and confirm.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from finance import analyse
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "experiments"))
from exp05_financial import financial_states, control_states

HERE = os.path.dirname(os.path.abspath(__file__))


def main():
    tickers, dates, fin_states = financial_states()
    ctrl_rows = control_states(len(tickers), len(fin_states) + 1)

    fin = analyse(fin_states, max_k=2)
    ctrl = analyse(ctrl_rows, max_k=3)

    bundle = {
        "market": {
            "states": fin_states, "max_k": 2,
            "py_mean_contradiction": fin["mean_contradiction_rate"],
            "py_exact_nodes": fin["exact_nodes"],
        },
        "control": {
            "states": ctrl_rows, "max_k": 3,
            "py_mean_contradiction": ctrl["mean_contradiction_rate"],
            "py_exact_nodes": ctrl["exact_nodes"],
        },
    }
    with open(os.path.join(HERE, "finance_cases.json"), "w") as f:
        json.dump(bundle, f)
    print(f"market: mean_contradiction={fin['mean_contradiction_rate']:.3f} "
          f"exact={fin['exact_nodes']}/{fin['n_nodes']}")
    print(f"control: mean_contradiction={ctrl['mean_contradiction_rate']:.3f} "
          f"exact={ctrl['exact_nodes']}/{ctrl['n_nodes']}")
    print("wrote finance_cases.json")


if __name__ == "__main__":
    main()
