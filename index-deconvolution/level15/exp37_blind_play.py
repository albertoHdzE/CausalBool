"""exp37_blind_play.py  (Level 15)

Play the buy and sell behaviour formulae blindly, out of sample, on one stock and on the
100-stock panel, and score them two ways -- timing and money -- each against a control.

  TIMING (does it work? tested honestly). Fit each formula on the first 70% of time; on
  the held-out 30%, forecast 'a turn within the next 10 days' from the causal intensity,
  and score the ranking by ROC area against a return-shuffle (which must sit at 0.5).

  MONEY (does it pay? tested honestly). Trade the confirmed turns causally (no
  look-ahead) and compare the terminal wealth with buy-and-hold and with the look-ahead
  oracle, to show the gap between hindsight and a blind play.
"""

from __future__ import annotations

import json
import math
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
sys.path.insert(0, os.path.join(ROOT, "level10"))

from blindplay import (oos_event_forecast, roc_auc, brier, reliability,  # noqa: E402
                       causal_dc_equity, buy_hold)
from finance import load_yahoo_close  # noqa: E402
from controls import return_shuffle  # noqa: E402
from pivots import directional_change_pivots  # noqa: E402
from hawkes import fit_hawkes  # noqa: E402
from oracle import optimal_trades, kappa_for_round_trip  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
THETA = 0.02
HORIZON = 10
TRAIN_FRAC = 0.7
DETAIL_STOCK = "CVS"    # a representative stock (OOS AUC ~ the panel mean 0.555)
N_NULL = 2


def load_100():
    seqs = {}
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def _events(series, kind):
    return [p.index for p in directional_change_pivots(series, THETA) if p.kind == kind]


def _auc_oos(ev, n_days):
    t_tr = int(n_days * TRAIN_FRAC)
    tr = [e for e in ev if e <= t_tr]
    if len(tr) < 10:
        return float("nan"), float("nan")
    f = fit_hawkes([float(e) for e in tr], float(t_tr))
    sc, lb = oos_event_forecast(ev, n_days, f["mu"], f["alpha"], f["beta"], t_tr, HORIZON)
    return roc_auc(sc, lb), brier(sc, lb)


def _timing_row(series, rng):
    n = len(series)
    out = {}
    for kind, side in ((-1, "buy"), (1, "sell")):
        ev = _events(series, kind)
        auc, br = _auc_oos(ev, n)
        nulls = []
        for _ in range(N_NULL):
            sh = return_shuffle(series, rng)
            a, _b = _auc_oos(_events(sh, kind), n)
            if a == a:
                nulls.append(a)
        out[side] = {"auc": auc, "brier": br,
                     "auc_null": statistics.mean(nulls) if nulls else float("nan")}
    return out


def _money_row(series):
    bh = buy_hold(series)
    causal = causal_dc_equity(series, THETA, cost=0.001)["wealth"]
    causal0 = causal_dc_equity(series, THETA, cost=0.0)["wealth"]
    orc = math.exp(optimal_trades(series, kappa_for_round_trip(THETA))["log_wealth"])
    return {"buy_hold": bh, "causal_cost": causal, "causal_free": causal0, "oracle": orc}


def run(quiet: bool = False) -> dict:
    seqs = load_100()
    rng = random.Random(37)

    # A. one stock in detail (with reliability curve data)
    s = seqs[DETAIL_STOCK]
    n = len(s)
    t_tr = int(n * TRAIN_FRAC)
    detail = {"stock": DETAIL_STOCK, "n_days": n, "timing": {}, "money": _money_row(s)}
    for kind, side in ((-1, "buy"), (1, "sell")):
        ev = _events(s, kind)
        tr = [e for e in ev if e <= t_tr]
        f = fit_hawkes([float(e) for e in tr], float(t_tr))
        sc, lb = oos_event_forecast(ev, n, f["mu"], f["alpha"], f["beta"], t_tr, HORIZON)
        detail["timing"][side] = {"auc": roc_auc(sc, lb), "brier": brier(sc, lb),
                                  "base_rate": sum(lb) / len(lb) if lb else float("nan"),
                                  "reliability": reliability(sc, lb, 10)}

    # B. panel
    trows, mrows = [], []
    for name, seq in seqs.items():
        trows.append((name, _timing_row(seq, rng)))
        mrows.append((name, _money_row(seq)))

    def auc_stats(side):
        excess = [t[side]["auc"] - t[side]["auc_null"] for _, t in trows
                  if t[side]["auc"] == t[side]["auc"] and t[side]["auc_null"] == t[side]["auc_null"]]
        aucs = [t[side]["auc"] for _, t in trows if t[side]["auc"] == t[side]["auc"]]
        return {"mean_auc": statistics.mean(aucs) if aucs else float("nan"),
                "mean_excess": statistics.mean(excess) if excess else float("nan"),
                "n_beats_shuffle": sum(1 for e in excess if e > 0), "n": len(excess)}

    def money_stats():
        beat = sum(1 for _, m in mrows if m["causal_free"] > m["buy_hold"])
        beat_cost = sum(1 for _, m in mrows if m["causal_cost"] > m["buy_hold"])
        ratios = [m["causal_free"] / m["buy_hold"] for _, m in mrows if m["buy_hold"] > 0]
        orc_ratios = [m["oracle"] / m["buy_hold"] for _, m in mrows if m["buy_hold"] > 0]
        return {"n_causal_beats_bh_free": beat, "n_causal_beats_bh_cost": beat_cost,
                "n": len(mrows),
                "median_causal_over_bh": statistics.median(ratios) if ratios else float("nan"),
                "median_oracle_over_bh": statistics.median(orc_ratios) if orc_ratios else float("nan")}

    panel = {"n_series": len(trows), "buy": auc_stats("buy"), "sell": auc_stats("sell"),
             "money": money_stats(),
             "timing_rows": [{"name": nm, **t} for nm, t in trows],
             "money_rows": [{"name": nm, **m} for nm, m in mrows]}

    out = {"experiment": "blind_play", "theta": THETA, "horizon": HORIZON,
           "detail": detail, "panel": panel}

    if not quiet:
        print(f"Blind play of the buy/sell formulae, out of sample "
              f"({panel['n_series']} stocks, theta={THETA}, horizon={HORIZON}d)\n")
        d = detail
        print(f"A. One stock: {DETAIL_STOCK}")
        for side in ("buy", "sell"):
            ts = d["timing"][side]
            print(f"   TIMING {side:4}: OOS ROC-AUC {ts['auc']:.3f} "
                  f"(0.5 = no skill), Brier {ts['brier']:.3f}, base rate {ts['base_rate']:.3f}")
        m = d["money"]
        print(f"   MONEY: buy&hold {m['buy_hold']:.1f}x | causal play {m['causal_free']:.1f}x "
              f"(free) {m['causal_cost']:.2f}x (0.1% cost) | oracle {m['oracle']:.1e}x\n")

        print(f"B. Panel of {panel['n_series']} stocks:")
        for side in ("buy", "sell"):
            st = panel[side]
            print(f"   TIMING {side:4}: mean AUC {st['mean_auc']:.3f}, "
                  f"excess over shuffle {st['mean_excess']:+.3f}, "
                  f"beats shuffle on {st['n_beats_shuffle']}/{st['n']}")
        ms = panel["money"]
        print(f"   MONEY: causal play beats buy&hold on {ms['n_causal_beats_bh_free']}/{ms['n']} "
              f"(free), {ms['n_causal_beats_bh_cost']}/{ms['n']} (after 0.1% cost);")
        print(f"          median causal/buy&hold = {ms['median_causal_over_bh']:.2f}x, "
              f"median oracle/buy&hold = {ms['median_oracle_over_bh']:.1e}x\n")
        print("   VERDICT: TIMING works (weak but real, beats the shuffle); MONEY does not")
        print("   (blind causal play loses to buy&hold; only the look-ahead oracle pays).")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp37_blind_play.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp37_blind_play.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
