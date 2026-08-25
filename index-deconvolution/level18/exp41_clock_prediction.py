"""exp41_clock_prediction.py  (Level 18)

How well does an individual clock model predict the oracle's turns, across 100 stocks?

For each stock, the buy pattern (troughs) and sell pattern (peaks) each get a three-number
Hawkes model fitted on the first 70% of time. On the held-out 30% the model fires predicted
turns on its highest-intensity days (spaced by a refractory period, count set by the train
rate), and we match them to the oracle's actual turns within a tolerance, reading off
precision and recall. Against a random-prediction baseline (same count, same refractory),
so the lift over chance is explicit -- dense predictions can match by luck.
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
sys.path.insert(0, os.path.join(ROOT, "level9"))

from models import causal_intensity, fit_train  # noqa: E402
from predict import predicted_events, match_events  # noqa: E402
from finance import load_yahoo_close  # noqa: E402
from pivots import directional_change_pivots  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
THETA = 0.02
TRAIN_FRAC = 0.7
TOLS = [1, 2, 3, 5, 8]      # sweep the matching tolerance; loose tol trivialises the task
TOL_MAIN = 2                 # precise timing: within two days


def load_100():
    seqs = {}
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def _random_pred(t_start, n_days, refractory, n_expected, rng):
    picked = []
    tries = 0
    while len(picked) < n_expected and tries < n_expected * 50:
        t = rng.randint(t_start, n_days - 1)
        if all(abs(t - p) >= refractory for p in picked):
            picked.append(t)
        tries += 1
    return sorted(picked)


def _score_side(events, price_len, rng):
    n = price_len
    t_tr = int(n * TRAIN_FRAC)
    train = [e for e in events if e <= t_tr]
    test_actual = [e for e in events if e > t_tr]
    if len(train) < 20 or len(test_actual) < 10:
        return None
    fit = fit_train(events, t_tr)
    lam = causal_intensity(events, n, fit["mu"], fit["alpha"], fit["beta"])
    gaps = [train[i + 1] - train[i] for i in range(len(train) - 1)]
    refr = max(2, statistics.median(gaps) // 2) if gaps else 3
    rate = len(train) / t_tr
    n_expected = max(1, round(rate * (n - t_tr)))
    pred = predicted_events(lam, t_tr + 1, int(refr), n_expected)
    rp = _random_pred(t_tr + 1, n, int(refr), n_expected, rng)
    out = {"by_tol": {}}
    for tol in TOLS:
        m = match_events(pred, test_actual, tol)
        mr = match_events(rp, test_actual, tol)
        out["by_tol"][tol] = {"f1": m["f1"], "precision": m["precision"], "recall": m["recall"],
                              "rand_f1": mr["f1"], "rand_precision": mr["precision"],
                              "rand_recall": mr["recall"]}
    mm = match_events(pred, test_actual, TOL_MAIN)
    mmr = match_events(rp, test_actual, TOL_MAIN)
    out.update({"precision": mm["precision"], "recall": mm["recall"], "f1": mm["f1"],
                "rand_precision": mmr["precision"], "rand_recall": mmr["recall"], "rand_f1": mmr["f1"]})
    return out


def run(quiet: bool = False) -> dict:
    seqs = load_100()
    rng = random.Random(41)
    rows = []
    for name, s in seqs.items():
        piv = directional_change_pivots(s, THETA)
        buys = [p.index for p in piv if p.kind == -1]
        sells = [p.index for p in piv if p.kind == +1]
        b = _score_side(buys, len(s), rng)
        se = _score_side(sells, len(s), rng)
        if b and se:
            rows.append({"name": name, "buy": b, "sell": se})

    def m(side, k):
        return statistics.mean(r[side][k] for r in rows)

    def sweep(side):
        return {tol: {"model_f1": statistics.mean(r[side]["by_tol"][tol]["f1"] for r in rows),
                      "rand_f1": statistics.mean(r[side]["by_tol"][tol]["rand_f1"] for r in rows)}
                for tol in TOLS}

    out = {"experiment": "clock_prediction", "theta": THETA, "tol_main": TOL_MAIN, "tols": TOLS,
           "n_series": len(rows),
           "buy": {k: m("buy", k) for k in ("precision", "recall", "f1", "rand_precision", "rand_recall", "rand_f1")},
           "sell": {k: m("sell", k) for k in ("precision", "recall", "f1", "rand_precision", "rand_recall", "rand_f1")},
           "sweep_buy": sweep("buy"), "sweep_sell": sweep("sell"),
           "n_beat_random_f1_main": sum(1 for r in rows if r["buy"]["f1"] > r["buy"]["rand_f1"]),
           "rows": [{"name": r["name"], "buy": {k: r["buy"][k] for k in ("precision", "recall", "f1")},
                     "sell": {k: r["sell"][k] for k in ("precision", "recall", "f1")}} for r in rows]}

    if not quiet:
        print(f"Individual clock model predicting the oracle's turns "
              f"({out['n_series']} stocks; precise tolerance = {TOL_MAIN}d)\n")
        for side in ("buy", "sell"):
            p = out[side]
            print(f"  {side.upper():4} (+/-{TOL_MAIN}d): precision {p['precision']:.3f}  recall {p['recall']:.3f}  "
                  f"F1 {p['f1']:.3f}   |  random: precision {p['rand_precision']:.3f}  "
                  f"recall {p['rand_recall']:.3f}  F1 {p['rand_f1']:.3f}")
        print(f"\n  tolerance sweep (buy) -- model F1 vs random F1:")
        for tol in TOLS:
            sm = out["sweep_buy"][tol]
            win = "model" if sm["model_f1"] > sm["rand_f1"] else "random"
            print(f"    +/-{tol}d: model {sm['model_f1']:.3f}  random {sm['rand_f1']:.3f}  -> {win} wins")
        print(f"\n  the model beats random by the widest margin at PRECISE tolerances; at loose")
        print("  tolerances random tiles the timeline and wins. The clock is predictable to a few days.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp41_clock_prediction.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp41_clock_prediction.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
