"""exp13_forecast.py  (Level 4)

Out-of-sample forecast from the discovered structure, against a shuffle null.

Levels 1-3 established that the direction unit (the sign of the step) is not
forecastable.  Level 4 discovered a different unit -- the volatility unit, the top
magnitude bit of the first difference -- which survives the shuffle test and shows
persistent, self-similar memory (Hurst > 1/2).  The honest test of that discovery
is a committed, out-of-sample forecast of the volatility unit that beats both the
base rate and a time-shuffle of the same series.

Protocol discipline:
  * the rule is committed on the earlier part of the series (train) and evaluated
    only on the held-out later part (test);
  * the same rule is refitted and evaluated on a time-shuffle, which preserves the
    density and destroys the arrangement, so any real edge must exceed the shuffle;
  * the identical procedure is run on the sign unit as an internal control, which
    should show no edge.

The predictor is deliberately minimal -- a threshold on the count of ones in a
short trailing window -- so that a positive result reflects the persistence
structure, not the flexibility of the model.
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
from binarise import sign_bit, top_magnitude_bit  # noqa: E402

DATA_DIR = os.path.join(ROOT, "finance", "data")
RESULTS_DIR = os.path.join(ROOT, "results")
TRAIN_FRAC = 0.6
MAX_WINDOW = 10


def load_sequences() -> dict[str, list[float]]:
    seqs = {}
    for f in sorted(os.listdir(DATA_DIR)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_DIR, f))
            seqs[f[:-5]] = [px[d] for d in sorted(px)]
    return seqs


def _accuracy(bits, k, theta, lo, hi):
    """Accuracy of 'predict 1 iff trailing-k count >= theta' on bits[lo:hi]."""
    correct = total = 0
    for t in range(max(lo, k), hi - 1):
        pred = 1 if sum(bits[t - k + 1:t + 1]) >= theta else 0
        correct += (pred == bits[t + 1])
        total += 1
    return (correct / total, total) if total else (0.0, 0)


def fit_and_test(bits: list[int]) -> dict:
    """Commit (k, theta) on the train span, evaluate on the held-out test span."""
    n = len(bits)
    split = int(n * TRAIN_FRAC)
    best = (-1.0, 1, 1)
    for k in range(1, MAX_WINDOW + 1):
        for theta in range(1, k + 1):
            acc, tot = _accuracy(bits, k, theta, 0, split)
            if tot and acc > best[0]:
                best = (acc, k, theta)
    _, k, theta = best
    test_acc, test_tot = _accuracy(bits, k, theta, split, n)
    # base rate on the test span (predict the train-majority class)
    train_ones = sum(bits[:split])
    maj = 1 if train_ones >= split - train_ones else 0
    base_correct = sum(1 for t in range(max(split, 1), n) if bits[t] == maj)
    base_acc = base_correct / (n - max(split, 1)) if n - max(split, 1) else 0.0
    return {"k": k, "theta": theta, "test_acc": test_acc,
            "base_acc": base_acc, "edge": test_acc - base_acc, "n_test": test_tot}


def evaluate_unit(bits: list[int], n_shuffle: int, rng: random.Random) -> dict:
    real = fit_and_test(bits)
    shuf_edges = []
    b = bits[:]
    for _ in range(n_shuffle):
        rng.shuffle(b)
        shuf_edges.append(fit_and_test(b)["edge"])
    shuf_edge = statistics.mean(shuf_edges)
    return {"edge": real["edge"], "test_acc": real["test_acc"],
            "base_acc": real["base_acc"], "shuffle_edge": shuf_edge,
            "edge_vs_shuffle": real["edge"] - shuf_edge, "k": real["k"], "theta": real["theta"]}


def run(quiet: bool = False) -> dict:
    seqs = load_sequences()
    rng = random.Random(11)
    vol, sign = [], []
    for name, s in seqs.items():
        vol.append(evaluate_unit(top_magnitude_bit(s), 40, rng))
        sign.append(evaluate_unit(sign_bit(s), 40, rng))

    def summ(rows):
        return {
            "mean_edge": statistics.mean(r["edge"] for r in rows),
            "mean_shuffle_edge": statistics.mean(r["shuffle_edge"] for r in rows),
            "mean_edge_vs_shuffle": statistics.mean(r["edge_vs_shuffle"] for r in rows),
            "n_positive_vs_shuffle": sum(1 for r in rows if r["edge_vs_shuffle"] > 0),
            "n": len(rows),
        }

    vol_s, sign_s = summ(vol), summ(sign)
    # paired sign-test p-value (one-sided) that volatility beats its shuffle
    import math
    n = vol_s["n"]
    kpos = vol_s["n_positive_vs_shuffle"]
    p_sign = sum(math.comb(n, i) for i in range(kpos, n + 1)) / (2 ** n)

    out = {"experiment": "forecast_volatility_vs_sign",
           "train_frac": TRAIN_FRAC, "volatility": vol_s, "sign": sign_s,
           "sign_test_p_volatility_beats_shuffle": p_sign}

    if not quiet:
        print(f"sequences: {n}, train fraction: {TRAIN_FRAC}, held-out test on the last "
              f"{100*(1-TRAIN_FRAC):.0f}%\n")
        print("=== out-of-sample forecast edge over base rate (mean across sequences) ===")
        for label, s in (("VOLATILITY unit", vol_s), ("SIGN unit", sign_s)):
            print(f"  {label:16s}: edge {s['mean_edge']:+.4f}, shuffle edge {s['mean_shuffle_edge']:+.4f}, "
                  f"real-minus-shuffle {s['mean_edge_vs_shuffle']:+.4f}  "
                  f"({s['n_positive_vs_shuffle']}/{s['n']} beat shuffle)")
        print(f"\n  sign-test p(volatility beats its shuffle) = {p_sign:.4g}")
        verdict = ("YES - the volatility unit carries an out-of-sample forecastable edge that the "
                   "shuffle destroys; the direction unit does not."
                   if vol_s["mean_edge_vs_shuffle"] > 0 and p_sign < 0.05 else
                   "No significant out-of-sample edge beyond shuffle at this resolution.")
        print(f"  verdict: {verdict}")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp13_forecast.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp13_forecast.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
