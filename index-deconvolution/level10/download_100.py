"""download_100.py  (Level 10)

Fetch long daily close histories for ~100 stocks from Yahoo v8, so the oracle /
clock claims can be stress-tested out of the twelve-survivor sample.

Uses explicit period1/period2 unix bounds with interval=1d (NOT range=max, which
silently downsamples to monthly).  Saves raw Yahoo chart JSON to finance/data_100/,
the same format the project loader (`load_yahoo_close`) already reads.  Polite:
a short sleep between requests, a couple of retries, standard library only.
"""

from __future__ import annotations

import json
import os
import sys
import time
import urllib.error
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
OUT_DIR = os.path.join(ROOT, "finance", "data_100")

# ~120 liquid US large-caps with long histories; we keep the first 100 that pass
# a minimum-length filter.  Deliberately diverse across sectors to avoid a
# single-sector artefact.
TICKERS = [
    "AAPL", "MSFT", "AMZN", "GOOGL", "META", "NVDA", "TSLA", "JPM", "JNJ", "V",
    "PG", "HD", "MA", "BAC", "DIS", "ADBE", "CRM", "NFLX", "XOM", "CVX",
    "KO", "PEP", "WMT", "CSCO", "INTC", "VZ", "T", "PFE", "MRK", "ABT",
    "ORCL", "NKE", "MCD", "HON", "UNH", "LLY", "COST", "TXN", "QCOM", "AMD",
    "IBM", "GE", "F", "GM", "CAT", "BA", "MMM", "CVS", "WBA", "GS",
    "MS", "C", "WFC", "AXP", "USB", "PNC", "UPS", "FDX", "LMT", "RTX",
    "NOC", "GD", "DE", "EMR", "DUK", "SO", "NEE", "D", "AEP", "EXC",
    "SLB", "COP", "OXY", "HAL", "PSX", "VLO", "MPC", "KMI", "WMB", "DOW",
    "DD", "LIN", "APD", "SHW", "CL", "KMB", "GIS", "K", "HSY", "SYY",
    "ADM", "MO", "PM", "CLX", "MDT", "SYK", "BSX", "ISRG", "GILD", "AMGN",
    "BIIB", "REGN", "VRTX", "CI", "HUM", "TMO", "DHR", "BDX", "BAX", "EW",
    "HCA", "MCK", "CAH", "AON", "MMC", "SPGI", "ICE", "CME", "COF", "SCHW",
]
MIN_POINTS = 2500              # ~10 years of trading days; enough pivots to fit
PERIOD1 = 0
PERIOD2 = 2000000000


def fetch(ticker: str, retries: int = 3) -> dict | None:
    url = (f"https://query1.finance.yahoo.com/v8/finance/chart/{ticker}"
           f"?period1={PERIOD1}&period2={PERIOD2}&interval=1d")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                return json.load(resp)
        except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as e:
            if attempt == retries - 1:
                print(f"  {ticker}: failed ({type(e).__name__})")
                return None
            time.sleep(2.0 * (attempt + 1))
    return None


def n_valid_points(d: dict) -> int:
    try:
        r = d["chart"]["result"][0]
        close = r["indicators"]["quote"][0]["close"]
        return sum(1 for c in close if c is not None)
    except (KeyError, IndexError, TypeError):
        return 0


def main(target: int = 100, quiet: bool = False) -> None:
    os.makedirs(OUT_DIR, exist_ok=True)
    kept = 0
    for tk in TICKERS:
        if kept >= target:
            break
        path = os.path.join(OUT_DIR, f"{tk}.json")
        if os.path.exists(path):                       # resume-friendly
            kept += 1
            continue
        d = fetch(tk)
        time.sleep(0.6)
        if d is None:
            continue
        npts = n_valid_points(d)
        if npts < MIN_POINTS:
            if not quiet:
                print(f"  {tk}: only {npts} points, skipped")
            continue
        with open(path, "w") as f:
            json.dump(d, f)
        kept += 1
        if not quiet:
            print(f"  [{kept:3d}] {tk}: {npts} points")
    print(f"kept {kept} tickers in {OUT_DIR}")


if __name__ == "__main__":
    main(quiet="--quiet" in sys.argv)
