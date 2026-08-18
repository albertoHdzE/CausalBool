#!/usr/bin/env python
"""Phase 2, ledger B6 — does the clock forecast beat its null?

Every threshold and every series is reported, whatever it shows (rule R5), and
the sign test across them is reported with the number of trials that produced it.

Run:  .venv/bin/python scripts/phase2_forecast.py [--null N] [--quiet]
"""
from __future__ import annotations
import argparse, hashlib, json, os, sys, warnings
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
from scipy import stats

from imp_prices import load_panel
from imp_prices.config import DATA, RESULTS
from imp_prices.clock import forecast_vs_null

THETA_GRID = (0.05, 0.08, 0.10)          # the thresholds Gate 2.0 declared usable
SERIES_MONTHLY = ("WTI_Spot", "WTI_CL", "Brent_BZ")


def run(prices, label, n_null, quiet):
    rows = []
    for th in THETA_GRID:
        r = forecast_vs_null(prices, th, n_null=n_null)
        if r is None:
            rows.append(dict(series=label, theta=th, skipped=True)); continue
        r.update(series=label, skipped=False); rows.append(r)
        if not quiet:
            print(f"    theta {th:<5} n_test {r['n_test']:3d}  acc {r['accuracy']:.3f} "
                  f"base {r['base_rate']:.3f}  edge {r['edge_over_base']:+.4f}  "
                  f"null edge {r['null_edge_mean']:+.4f}+/-{r['null_edge_sd']:.4f}  "
                  f"excess {r['excess_over_null']:+.4f}  p {r['p_value']:.4f}")
    return rows


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--null", type=int, default=200)
    ap.add_argument("--quiet", action="store_true")
    a = ap.parse_args()
    out = {"config": dict(theta_grid=list(THETA_GRID), n_null=a.null)}
    rows = []

    if not a.quiet:
        print("=" * 78); print("PHASE 2 / B6 — clock forecast against a return-shuffle null")
        print("=" * 78)
    panel = load_panel()
    for s in SERIES_MONTHLY:
        if not a.quiet: print(f"\n  monthly {s}")
        rows += run(panel[s].to_numpy(), f"monthly {s}", a.null, a.quiet)

    daily = pd.read_csv(os.path.join(DATA, "daily", "oil_prices.csv"), skiprows=3,
                        header=None, names=["Date","Close","High","Low","Open","Volume"],
                        parse_dates=["Date"]).dropna(subset=["Close"])
    if not a.quiet: print("\n  daily WTI futures (Phase 3 data, shown for contrast)")
    daily_rows = run(daily["Close"].to_numpy(), "daily WTI", a.null, a.quiet)

    tab = pd.DataFrame([r for r in rows if not r.get("skipped")])
    dtab = pd.DataFrame([r for r in daily_rows if not r.get("skipped")])
    out["monthly"] = tab.to_dict("records"); out["daily"] = dtab.to_dict("records")

    for name, t in (("monthly", tab), ("daily", dtab)):
        if t.empty: continue
        wins = int((t["excess_over_null"] > 0).sum()); n = len(t)
        p = float(stats.binomtest(wins, n, 0.5, alternative="greater").pvalue)
        out[f"{name}_signtest"] = dict(wins=wins, n=n, p_value=round(p, 4),
                                       mean_excess=round(float(t["excess_over_null"].mean()), 4),
                                       any_significant=bool((t["p_value"] < 0.05).any()))
        if not a.quiet:
            print(f"\n  {name}: beats null in {wins}/{n} cells, sign test p={p:.4f}, "
                  f"mean excess {t['excess_over_null'].mean():+.4f}, "
                  f"any cell p<0.05: {bool((t['p_value'] < 0.05).any())}")

    out["b6_monthly_supported"] = bool(out.get("monthly_signtest", {}).get("p_value", 1) < 0.05)
    if not a.quiet:
        print("\n" + "=" * 78); print("VERDICT (B6)"); print("=" * 78)
        print(f"  B6 supported on monthly data: {out['b6_monthly_supported']}")
    out["content_sha256"] = hashlib.sha256(json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "phase2_forecast.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    if not a.quiet: print(f"  content sha256 {out['content_sha256'][:16]}")
    return 0

if __name__ == "__main__":
    sys.exit(main())
