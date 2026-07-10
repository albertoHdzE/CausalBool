"""exp15_longdata.py  (Level 4)

Re-test the volatility unit on genuine multi-decade daily series (8-12 thousand
points each, versus the 753 of the aligned set).  Two predictions are checked.

  1. Self-similarity should be robust and sharper: the Hurst estimate has a wider
     range of scales to fit, so it should sit above 1/2 with less noise.

  2. Compression should now beat the model cost.  The two-state rule pays a model
     cost of about 2 log2(N) bits (grows only logarithmically), while the
     per-symbol persistence saving accumulates over all N symbols.  If the
     persistence is real, the total description-length gain must grow roughly
     linearly in N and finally exceed the model cost -- turning the marginal
     +3 bits of the short series into a decisive, robust compression.

The forecast is re-run out of sample against the shuffle to confirm the edge
survives at length.  Each long series is analysed independently (no alignment).
"""

from __future__ import annotations

import json
import os
import random
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, HERE)

from finance import load_yahoo_close  # noqa: E402
from binarise import top_magnitude_bit, sign_bit, trend_contamination  # noqa: E402
from occurrence_arithmetic import behaviour_table  # noqa: E402
from exp13_forecast import evaluate_unit  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data_long")
RESULTS_DIR = os.path.join(ROOT, "results")


def load_sequences():
    seqs = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_DIR, f))
            seqs[f[:-5]] = [px[d] for d in sorted(px)]
    return seqs


def run(quiet: bool = False) -> dict:
    seqs = load_sequences()
    rng = random.Random(15)
    rows = []
    for name, s in seqs.items():
        # scale-free volatility unit: on a multi-decade series the additive
        # difference tracks the price level (a trend), so the relative difference
        # is required.  The contamination guard records how bad the additive unit is.
        contam = trend_contamination(s)
        vbits = top_magnitude_bit(s, scale_free=True)
        bt = behaviour_table(vbits)
        # compression vs shuffle
        real_gain = bt["compression"]["gain_bits"]
        b = vbits[:]
        draws = []
        for _ in range(20):
            rng.shuffle(b)
            draws.append(behaviour_table(b)["compression"]["gain_bits"])
        shuf_gain = statistics.mean(draws)
        fc = evaluate_unit(vbits, 20, rng)
        fc_sign = evaluate_unit(sign_bit(s), 20, rng)
        rows.append({
            "name": name, "N": len(vbits),
            "additive_trend_contamination": contam,
            "hurst": bt["columns"]["memory_hurst"],
            "persistence_excess": bt["persistence_excess"],
            "gain_bits": real_gain, "gain_shuffle": shuf_gain,
            "gain_vs_shuffle": real_gain - shuf_gain,
            "vol_edge_vs_shuffle": fc["edge_vs_shuffle"],
            "sign_edge_vs_shuffle": fc_sign["edge_vs_shuffle"],
        })

    def m(k):
        return statistics.mean(r[k] for r in rows)

    n_compress = sum(1 for r in rows if r["gain_vs_shuffle"] > 0)
    n_abs_compress = sum(1 for r in rows if r["gain_bits"] > 0)
    n_forecast = sum(1 for r in rows if r["vol_edge_vs_shuffle"] > 0)
    out = {"experiment": "longdata_volatility", "n_series": len(rows),
           "mean_N": m("N"), "mean_additive_trend_contamination": m("additive_trend_contamination"),
           "mean_hurst": m("hurst"),
           "mean_gain_bits": m("gain_bits"), "mean_gain_vs_shuffle": m("gain_vs_shuffle"),
           "n_compress_vs_shuffle": n_compress, "n_absolute_compress": n_abs_compress,
           "mean_vol_edge_vs_shuffle": m("vol_edge_vs_shuffle"),
           "mean_sign_edge_vs_shuffle": m("sign_edge_vs_shuffle"),
           "n_forecast_beats_shuffle": n_forecast, "rows": rows}

    if not quiet:
        print(f"long series: {len(rows)}, mean length {m('N'):.0f} "
              f"(vs 752 in the aligned set)")
        print("scale-free (relative-difference) volatility unit; additive unit is "
              "trend-contaminated on these series\n")
        print(f"{'series':8s} {'N':>6s} {'contam':>7s} {'Hurst':>6s} {'gain_bits':>10s} "
              f"{'gain-shuf':>10s} {'vol_edge':>9s} {'sign_edge':>9s}")
        for r in rows:
            print(f"{r['name']:8s} {r['N']:>6d} {r['additive_trend_contamination']:>+7.2f} "
                  f"{r['hurst']:>6.3f} {r['gain_bits']:>10.1f} "
                  f"{r['gain_vs_shuffle']:>10.1f} {r['vol_edge_vs_shuffle']:>+9.4f} "
                  f"{r['sign_edge_vs_shuffle']:>+9.4f}")
        print(f"\n  mean additive-unit contamination {m('additive_trend_contamination'):+.2f} "
              f"(near 0 would mean the additive unit were safe; it is not)")
        print(f"  mean Hurst {m('hurst'):.3f} (vs 0.665 on 3-year data: wider scales sharpen it); "
              f"absolute compression on {n_abs_compress}/{len(rows)}, beats shuffle on "
              f"{n_compress}/{len(rows)} ({m('gain_vs_shuffle'):+.0f} bits mean)")
        print(f"  volatility forecast beats shuffle on {n_forecast}/{len(rows)} "
              f"(mean edge {m('vol_edge_vs_shuffle'):+.4f}); sign edge {m('sign_edge_vs_shuffle'):+.4f}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp15_longdata.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp15_longdata.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
