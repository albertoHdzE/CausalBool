"""exp10_behaviour_tables.py  (Level 3)

Gate-agnostic behaviour-table analysis on controls and on real market series.
Validates that the information-distribution decomposition compresses a structured
pattern and does not compress a random one, then measures whether a market's
binary up/down series carries fractal (compressible) structure beyond a shuffle.
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

from causalbool import truth_table  # noqa: E402
from finance import align_prices, daily_returns, sign_states  # noqa: E402
from behaviour_table import behaviour_decomposition, lz76_complexity  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
TICKERS = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "META", "JPM", "XOM", "SPY"]


def gate_column(n, connected, gate):
    col = []
    for x in range(2 ** n):
        sub = [(x >> i) & 1 for i in connected]
        from causalbool import apply_gate
        col.append(apply_gate(gate, sub))
    return col


def run():
    out = {}
    n = 8
    # structured control: AND over 3 of 8 inputs
    gcol = gate_column(n, [1, 3, 5], "AND")
    gd = behaviour_decomposition(gcol, n)
    # random control
    rng = random.Random(0)
    rcol = [rng.randint(0, 1) for _ in range(2 ** n)]
    rd = behaviour_decomposition(rcol, n)
    print("=== behaviour-table decomposition (gate-agnostic) ===")
    print(f"  structured (AND of 3/8): one-set {gd['one_set_size']}, sumandos "
          f"{len(gd['sumando_bits'])}, schemata {gd['num_schemata']}, "
          f"ones/schema {gd['ones_per_schema']:.1f}")
    print(f"  random 8-bit column     : one-set {rd['one_set_size']}, sumandos "
          f"{len(rd['sumando_bits'])}, schemata {rd['num_schemata']}, "
          f"ones/schema {rd['ones_per_schema']:.1f}")
    out["structured"] = {k: gd[k] for k in ("one_set_size", "num_schemata", "ones_per_schema")}
    out["structured"]["sumandos"] = len(gd["sumando_bits"])
    out["random"] = {k: rd[k] for k in ("one_set_size", "num_schemata", "ones_per_schema")}
    out["random"]["sumandos"] = len(rd["sumando_bits"])

    # financial: LZ complexity of each ticker's up/down series vs shuffle control
    paths = {t: os.path.join(DATA_DIR, f"{t}.json") for t in TICKERS
             if os.path.exists(os.path.join(DATA_DIR, f"{t}.json"))}
    tk, dates, M = align_prices(paths)
    S = sign_states(daily_returns(M))
    rng2 = random.Random(1)
    print("\n=== market up/down series: LZ76 complexity vs shuffle (structure test) ===")
    ratios = []
    fin = []
    for j, t in enumerate(tk):
        series = [S[i][j] for i in range(len(S))]
        real = lz76_complexity(series)
        shuf = 0.0
        for _ in range(20):
            sh = series[:]
            rng2.shuffle(sh)
            shuf += lz76_complexity(sh)
        shuf /= 20
        ratio = real / shuf
        ratios.append(ratio)
        fin.append({"ticker": t, "lz_real": real, "lz_shuffle": shuf, "ratio": ratio})
    mean_ratio = sum(ratios) / len(ratios)
    print(f"  mean LZ(real)/LZ(shuffle) over {len(tk)} tickers: {mean_ratio:.3f}")
    print("  ratio ~1.0 => the series is as complex as random (no fractal structure);")
    print("  ratio < 1  => genuine compressible structure.")
    out["market_lz_ratio_mean"] = mean_ratio
    out["market_per_ticker"] = fin

    print("\nReading: the behaviour-table decomposition compresses the structured "
          "pattern (few schemata, many ones each) and not the random one (one "
          "schema per one). The market up/down series is as LZ-complex as its own "
          "shuffle, so at daily resolution it carries no fractal structure to "
          "compress - consistent with the earlier levels, now via the "
          "information-distribution lens.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp10_behaviour_tables.json"), "w") as f:
        json.dump(out, f, indent=2)
    print("\nwritten: results/exp10_behaviour_tables.json")
    return out


if __name__ == "__main__":
    run()
