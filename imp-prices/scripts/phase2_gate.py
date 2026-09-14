#!/usr/bin/env python
"""Phase 2, Gate 2.0 — is there enough monthly data to ask the clock question?

Phase 2 re-targets from the regime to the clock: not which way the price moves,
but when it reverses. Before any forecasting claim, the same discipline as Gate
1.0 applies — measure whether the sample can support the question at all, and
report a shortfall as a finding rather than modelling around it.

The threshold grid is pre-declared and every value is reported (rule R5).

Run:
    .venv/bin/python scripts/phase2_gate.py [--quiet]
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import warnings

warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd

from imp_prices import SERIES, TARGET, load_panel
from imp_prices.config import DATA, RESULTS
from imp_prices.pivots import (clean_prices, directional_change, leak_opportunities, legs,
                               short_wait_target)

#: Pre-declared. Monthly reversals of 5 to 25 per cent bracket what the
#: literature calls a correction through to a bear market.
THETA_GRID = (0.05, 0.08, 0.10, 0.15, 0.20, 0.25)

#: Minimum legs needed before a forecast comparison is worth running at all.
#: Fixed in advance: below this the out-of-sample split leaves too few decisions
#: for any null comparison to have power, which is the constraint GWP3
#: conclusion 5 identifies for this dataset.
MIN_LEGS_FOR_FORECAST = 30


def survey(prices, label, quiet, index=None):
    rows = []
    for theta in THETA_GRID:
        pv = directional_change(prices, theta)
        lg = legs(pv)
        tgt = short_wait_target(lg) if len(lg) > 10 else pd.DataFrame()
        leak = leak_opportunities(pv, len(prices))
        rows.append(dict(
            series=label, theta=theta, n_obs=len(prices), n_pivots=len(pv),
            n_legs=len(lg), n_target_rows=len(tgt),
            mean_lag=leak["mean_lag"], max_lag=leak["max_lag"],
            leak_fraction=leak["fraction_of_time"],
            mean_dt=round(float(lg["dt"].mean()), 2) if len(lg) else np.nan,
            base_rate=round(float(tgt["short"].mean()), 3) if len(tgt) else np.nan,
            usable=bool(len(lg) >= MIN_LEGS_FOR_FORECAST)))
    tab = pd.DataFrame(rows)
    if not quiet:
        print(f"\n  {label}  ({len(prices)} observations)")
        print(tab.drop(columns=["series", "n_obs"]).to_string(index=False))
    return tab


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--quiet", action="store_true")
    args = ap.parse_args()
    out = {"config": dict(theta_grid=list(THETA_GRID),
                          min_legs_for_forecast=MIN_LEGS_FOR_FORECAST)}

    if not args.quiet:
        print("=" * 78)
        print("GATE 2.0 — can the monthly sample support a clock question?")
        print("=" * 78)

    panel = load_panel()
    tabs = [survey(panel[TARGET].to_numpy(), f"monthly {TARGET}", args.quiet)]
    for s in ("WTI_CL", "Brent_BZ"):
        tabs.append(survey(panel[s].to_numpy(), f"monthly {s}", args.quiet))

    monthly = pd.concat(tabs, ignore_index=True)
    out["monthly"] = monthly.to_dict("records")

    # For contrast only: the daily series held for Phase 3. Not a Phase 2 result;
    # it is here to show what the sample constraint costs, in one number.
    daily_path = os.path.join(DATA, "daily", "oil_prices.csv")
    daily = pd.read_csv(daily_path, skiprows=3, header=None,
                        names=["Date", "Close", "High", "Low", "Open", "Volume"],
                        parse_dates=["Date"]).dropna(subset=["Close"])
    # AUDIT02/Q1-C: this script could not run at all. The daily series contains
    # the 2020-04-20 negative WTI settlement (-37.63), and validate_prices
    # rightly refuses it: a RELATIVE threshold theta is undefined once a price
    # crosses zero, so every directional-change pivot downstream would be
    # meaningless rather than merely noisy. The committed artefact therefore
    # predates the guard and was not reproducible.
    # Applying the declared policy (clean_prices: drop, never interpolate) and
    # REPORTING the exclusion, which is what the guard's own message instructs.
    daily_close, daily_dates, daily_excl = clean_prices(
        daily["Close"].to_numpy(), daily["Date"].to_numpy())
    out["daily_exclusion"] = daily_excl
    if not args.quiet and daily_excl["n_dropped"]:
        print(f"\n  daily series: excluded {daily_excl['n_dropped']} of "
              f"{daily_excl['n_in']} observations as non-positive "
              f"(dates: {daily_excl['dropped_dates']})")
    dtab = survey(daily_close, "daily WTI futures (Phase 3 data)", args.quiet)
    out["daily_for_contrast"] = dtab.to_dict("records")

    banner_usable = monthly[monthly["usable"]]
    out["gate_passes"] = bool(len(banner_usable) > 0)
    out["max_legs_monthly"] = int(monthly["n_legs"].max())
    out["best_monthly_theta"] = float(
        monthly.loc[monthly["n_legs"].idxmax(), "theta"])
    out["max_legs_daily"] = int(dtab["n_legs"].max())

    if not args.quiet:
        print("\n" + "=" * 78)
        print("VERDICT (Gate 2.0)")
        print("=" * 78)
        print(f"  most legs obtainable at monthly frequency : {out['max_legs_monthly']} "
              f"(at theta = {out['best_monthly_theta']})")
        print(f"  minimum declared necessary for a forecast : {MIN_LEGS_FOR_FORECAST}")
        print(f"  GATE 2.0 (monthly): {'PASS' if out['gate_passes'] else 'FAIL'}")
        print(f"  for contrast, daily data yields up to      : {out['max_legs_daily']} legs")
        print(f"  confirmation lag is always >= 1 step, mean "
              f"{monthly['mean_lag'].mean():.2f} months at monthly resolution")

    out["content_sha256"] = hashlib.sha256(
        json.dumps(out, sort_keys=True, default=str).encode()).hexdigest()
    os.makedirs(RESULTS, exist_ok=True)
    with open(os.path.join(RESULTS, "phase2_gate.json"), "w") as fh:
        json.dump(out, fh, indent=2, default=str)
    if not args.quiet:
        print(f"  content sha256 {out['content_sha256'][:16]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
