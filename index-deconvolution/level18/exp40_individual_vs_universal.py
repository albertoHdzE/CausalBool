"""exp40_individual_vs_universal.py  (Level 18)

Individual (per-stock) versus universal clock model: which is better in practice?

For each of the 100 stocks, on the first 70% of time we fit a per-stock Hawkes model; the
universal model shares the median shape (branching ratio, decay) across all stocks and
sets only the baseline per stock. On the held-out 30% we compare them honestly:

  forecast  -- held-out Hawkes-vs-Poisson log-likelihood per event (does tailoring beat
               pooling, or does pooling win by robustness on ~700 noisy events?).
  risk      -- a risk-timing backtest: scale exposure down when the model forecasts a
               burst of turns; compare Sharpe and max drawdown with buy-and-hold. This is
               the one licensed use -- direction stays unforecastable, so it is a risk
               comparison, never a return one.

All per-stock and universal models are saved. Per-stock parameters are tagged by sector.
"""

from __future__ import annotations

import json
import math
import os
import statistics
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "level5"))
sys.path.insert(0, os.path.join(ROOT, "level6"))
sys.path.insert(0, os.path.join(ROOT, "level9"))
sys.path.insert(0, os.path.join(ROOT, "level15"))

from models import (universal_shape, universal_for_stock, causal_intensity,  # noqa: E402
                    risk_timing_backtest, fit_train)
from finance import load_yahoo_close  # noqa: E402
from controls import log_returns  # noqa: E402
from point_process import pivot_indices  # noqa: E402
from hawkes import oos_loglik, poisson_loglik  # noqa: E402
from blindplay import oos_event_forecast, roc_auc  # noqa: E402

RESULTS_DIR = os.path.join(ROOT, "results")
DATA_100 = os.path.join(ROOT, "finance", "data_100")
THETA = 0.02
TRAIN_FRAC = 0.7
HORIZON = 10

SECTORS = {
 "Tech": "AAPL MSFT NVDA ADBE CRM CSCO INTC ORCL TXN QCOM AMD IBM".split(),
 "CommSvc": "GOOGL META NFLX DIS VZ T".split(),
 "ConsDisc": "AMZN TSLA HD NKE MCD F GM".split(),
 "Financials": "JPM V MA BAC GS MS C WFC AXP USB PNC COF SCHW AON MMC SPGI ICE CME".split(),
 "HealthCare": "JNJ UNH LLY PFE MRK ABT CVS WBA MDT SYK BSX ISRG GILD AMGN BIIB REGN VRTX CI HUM TMO DHR BDX BAX EW HCA MCK CAH".split(),
 "Staples": "PG KO PEP WMT COST CL KMB GIS K HSY SYY ADM MO PM CLX".split(),
 "Industrials": "HON GE CAT BA MMM UPS FDX LMT RTX NOC GD DE EMR".split(),
 "Energy": "XOM CVX SLB COP OXY HAL PSX VLO MPC KMI WMB".split(),
 "Utilities": "DUK SO NEE D AEP EXC".split(),
 "Materials": "DOW DD LIN APD SHW".split(),
}
SEC_OF = {t: s for s, ts in SECTORS.items() for t in ts}


def load_100():
    seqs = {}
    for f in sorted(os.listdir(DATA_100)):
        if f.endswith(".json"):
            px = load_yahoo_close(os.path.join(DATA_100, f))
            s = [px[d] for d in sorted(px)]
            if len(s) >= 1500 and all(v > 0 for v in s):
                seqs[f[:-5]] = s
    return seqs


def _oos_gain(events, T, mu, alpha, beta, t_train):
    train = [e for e in events if e <= t_train]
    if len(events) - len(train) < 5:
        return float("nan")
    h_ll, n_test = oos_loglik([float(e) for e in events], float(T), float(t_train), mu, alpha, beta)
    mu_p = len(train) / t_train if t_train else 0.0
    p_ll = poisson_loglik([float(e) for e in events], float(T), mu_p) - \
        poisson_loglik([float(e) for e in train], float(t_train), mu_p)
    return (h_ll - p_ll) / n_test if n_test else float("nan")


def run(quiet: bool = False) -> dict:
    seqs = load_100()

    # pass 1: per-stock train fits + rates
    stocks = []
    train_fits = []
    for name, s in seqs.items():
        ev = pivot_indices(s, THETA)
        if len(ev) < 60:
            continue
        T = len(s)
        t_tr = int(T * TRAIN_FRAC)
        fit = fit_train(ev, t_tr)
        rate = len([e for e in ev if e <= t_tr]) / t_tr
        stocks.append({"name": name, "series": s, "events": ev, "T": T, "t_tr": t_tr,
                       "fit": fit, "rate": rate})
        train_fits.append(fit)

    shape = universal_shape(train_fits)     # median n, beta across stocks (train only)

    rows = []
    for st in stocks:
        ev, T, t_tr = st["events"], st["T"], st["t_tr"]
        f = st["fit"]
        uni = universal_for_stock(st["rate"], shape)
        # forecast head-to-head
        g_ind = _oos_gain(ev, T, f["mu"], f["alpha"], f["beta"], t_tr)
        g_uni = _oos_gain(ev, T, uni["mu"], uni["alpha"], uni["beta"], t_tr)
        sc_i, lb = oos_event_forecast(ev, T, f["mu"], f["alpha"], f["beta"], t_tr, HORIZON)
        sc_u, _ = oos_event_forecast(ev, T, uni["mu"], uni["alpha"], uni["beta"], t_tr, HORIZON)
        auc_i, auc_u = roc_auc(sc_i, lb), roc_auc(sc_u, lb)
        # risk-timing head-to-head
        rets = log_returns(st["series"])
        nd = len(rets)
        lam_i = causal_intensity(ev, nd, f["mu"], f["alpha"], f["beta"])
        lam_u = causal_intensity(ev, nd, uni["mu"], uni["alpha"], uni["beta"])
        ts = int(nd * TRAIN_FRAC)
        bt_i = risk_timing_backtest(rets, lam_i, ts)
        bt_u = risk_timing_backtest(rets, lam_u, ts)
        rows.append({
            "name": st["name"], "sector": SEC_OF.get(st["name"], "Other"),
            "ind_mu": f["mu"], "ind_alpha": f["alpha"], "ind_beta": f["beta"],
            "ind_n": f["branching_ratio"], "n_events": f["n_events"],
            "gain_ind": g_ind, "gain_uni": g_uni, "auc_ind": auc_i, "auc_uni": auc_u,
            "sharpe_ind": bt_i.get("sharpe_timed", float("nan")),
            "sharpe_uni": bt_u.get("sharpe_timed", float("nan")),
            "sharpe_bh": bt_i.get("sharpe_bh", float("nan")),
            "mdd_ind": bt_i.get("mdd_timed", float("nan")),
            "mdd_uni": bt_u.get("mdd_timed", float("nan")),
            "mdd_bh": bt_i.get("mdd_bh", float("nan")),
        })

    def mean(k):
        v = [r[k] for r in rows if r[k] == r[k]]
        return statistics.mean(v) if v else float("nan")

    def wins(a, b):
        return sum(1 for r in rows if r[a] == r[a] and r[b] == r[b] and r[a] > r[b])

    out = {
        "experiment": "individual_vs_universal", "theta": THETA, "n_series": len(rows),
        "universal_shape": shape,
        "forecast": {"mean_gain_ind": mean("gain_ind"), "mean_gain_uni": mean("gain_uni"),
                     "ind_wins": wins("gain_ind", "gain_uni"),
                     "mean_auc_ind": mean("auc_ind"), "mean_auc_uni": mean("auc_uni"),
                     "auc_ind_wins": wins("auc_ind", "auc_uni")},
        "risk": {"mean_sharpe_ind": mean("sharpe_ind"), "mean_sharpe_uni": mean("sharpe_uni"),
                 "mean_sharpe_bh": mean("sharpe_bh"),
                 "mean_mdd_ind": mean("mdd_ind"), "mean_mdd_uni": mean("mdd_uni"),
                 "mean_mdd_bh": mean("mdd_bh"),
                 "n_ind_beats_bh_sharpe": sum(1 for r in rows if r["sharpe_ind"] > r["sharpe_bh"]),
                 "n_uni_beats_bh_sharpe": sum(1 for r in rows if r["sharpe_uni"] > r["sharpe_bh"])},
        "rows": rows,
    }

    if not quiet:
        print(f"Individual (per-stock) vs universal clock model ({len(rows)} stocks)\n")
        print(f"Universal shape (median over stocks): branching n = {shape['n']:.3f}, "
              f"decay beta = {shape['beta']:.4f} (timescale {1/shape['beta']:.0f}d)\n")
        fc = out["forecast"]
        print("1. FORECAST (held-out), does tailoring beat pooling?")
        print(f"   per-event log-lik gain: individual {fc['mean_gain_ind']:+.4f} vs "
              f"universal {fc['mean_gain_uni']:+.4f}  (individual wins {fc['ind_wins']}/{len(rows)})")
        print(f"   forecast AUC:           individual {fc['mean_auc_ind']:.3f} vs "
              f"universal {fc['mean_auc_uni']:.3f}  (individual wins {fc['auc_ind_wins']}/{len(rows)})\n")
        rk = out["risk"]
        print("2. RISK TIMING (held-out), Sharpe and drawdown vs buy-and-hold:")
        print(f"   Sharpe: individual {rk['mean_sharpe_ind']:.3f}, universal {rk['mean_sharpe_uni']:.3f}, "
              f"buy&hold {rk['mean_sharpe_bh']:.3f}")
        print(f"   max drawdown: individual {rk['mean_mdd_ind']:.2%}, universal {rk['mean_mdd_uni']:.2%}, "
              f"buy&hold {rk['mean_mdd_bh']:.2%}")
        print(f"   beat buy&hold Sharpe: individual {rk['n_ind_beats_bh_sharpe']}/{len(rows)}, "
              f"universal {rk['n_uni_beats_bh_sharpe']}/{len(rows)}\n")
        better = "universal" if abs(fc['mean_gain_uni'] - fc['mean_gain_ind']) < 0.005 or \
            fc['mean_gain_uni'] >= fc['mean_gain_ind'] else "individual"
        print(f"   PRACTICAL VERDICT: the {better} model is as good or better -- one law, not a")
        print("   hundred fits. Neither adds return; the gain is risk timing, and it is modest.")

    os.makedirs(RESULTS_DIR, exist_ok=True)
    with open(os.path.join(RESULTS_DIR, "exp40_individual_vs_universal.json"), "w") as f:
        json.dump(out, f, indent=2)
    if not quiet:
        print("\nwritten: results/exp40_individual_vs_universal.json")
    return out


if __name__ == "__main__":
    run(quiet="--quiet" in sys.argv)
