#!/usr/bin/env python
"""Fetch daily instruments for Phase 3 (Yahoo v8; FRED is unreachable from here).

The endpoint requires explicit period1/period2 Unix timestamps: `range=max`
silently downsamples to monthly, a trap already recorded in the programme.
"""
from __future__ import annotations
import json, os, sys, time, urllib.request

TICKERS = {"CL=F": "WTI_futures", "BZ=F": "Brent_futures", "NG=F": "NatGas",
           "HO=F": "HeatingOil", "RB=F": "Gasoline", "GC=F": "Gold_control"}
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                   "data", "daily", "yahoo")


def fetch(tkr):
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{tkr}"
           f"?period1=0&period2={int(time.time())}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=60) as r:
        d = json.load(r)["chart"]["result"][0]
    ts = d["timestamp"]; cl = d["indicators"]["quote"][0]["close"]
    rows = [(time.strftime("%Y-%m-%d", time.gmtime(t)), c)
            for t, c in zip(ts, cl) if c is not None]
    return rows


if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for tkr, name in TICKERS.items():
        try:
            rows = fetch(tkr)
        except Exception as e:
            print(f"  {name:16s} FAILED {e}"); continue
        p = os.path.join(OUT, f"{name}.csv")
        with open(p, "w") as fh:
            fh.write("Date,Close\n")
            for d, c in rows:
                fh.write(f"{d},{c}\n")
        vals = [c for _, c in rows]
        print(f"  {name:16s} {len(rows):6d} rows  {rows[0][0]} to {rows[-1][0]}  "
              f"min {min(vals):9.3f}  max {max(vals):9.3f}  "
              f"{'NON-POSITIVE PRESENT' if min(vals) <= 0 else ''}")
