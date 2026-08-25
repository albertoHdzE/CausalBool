"""The Phase 2 forecast: is the clock predictable, and does it beat its null?

Ledger B6. The target is the short-wait bit — whether the next interval between
turning points falls below the running median of those already seen. Near
balanced by construction, which is the escape from the base rate that made raw
accuracy uninformative on the regime target (A11, A13).

**The null is the load-bearing part.** A return shuffle permutes the log returns
and rebuilds the price path from them, then re-runs the entire pivot detection on
the surrogate. This preserves the fat-tailed marginal of the returns exactly and
destroys only their time order. It is the null the deconvolution programme
adopted at Level 5 after discovering that a driver-side "memory" of about 0.5
autocorrelation was a fat-tail artefact that a weaker null carried too.

Features are drawn only from legs whose closing pivot has been confirmed, so the
confirmed-only rule of :mod:`imp_prices.pivots` is enforced at the point of use
rather than trusted.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from .pivots import directional_change, legs, short_wait_target


def return_shuffle(prices: np.ndarray, rng) -> np.ndarray:
    """Permute log returns and rebuild the path: the marginal-preserving null."""
    p = np.asarray(prices, dtype=float)
    r = np.diff(np.log(p))
    return float(p[0]) * np.exp(np.concatenate([[0.0], np.cumsum(rng.permutation(r))]))


def clock_features(leg_table: pd.DataFrame, target: pd.DataFrame,
                   n_lags: int = 3) -> tuple[np.ndarray, np.ndarray]:
    """Lagged waits and moves, as of each decision point.

    Only legs already closed and confirmed at the decision point contribute, so
    the design matrix cannot contain a quantity the observer did not have.
    """
    dt = leg_table["dt"].to_numpy(float)
    dv = np.abs(leg_table["dv"].to_numpy(float))
    rows, ys = [], []
    for _, r in target.iterrows():
        i = int(r["leg"])
        if i - n_lags + 1 < 0:
            continue
        past_dt = dt[i - n_lags + 1:i + 1]
        past_dv = dv[i - n_lags + 1:i + 1]
        med = float(r["running_median"])
        rows.append(np.concatenate([
            (past_dt < med).astype(float),                  # short/long history
            [float(np.mean(past_dt) < med)],                # local pace
            [float(past_dv[-1] > np.median(dv[:i + 1]))],   # last move large?
        ]))
        ys.append(int(r["short"]))
    return np.asarray(rows), np.asarray(ys)


def _lookup_forecast(X: np.ndarray, y: np.ndarray, train_frac: float = 0.6):
    """Majority lookup over binary feature patterns, fitted on the prefix only.

    The model class is deliberately the same kind of object Phase 1 used: a map
    from a binary pattern to an outcome. What differs is the target, not the
    machinery, which is the point of the re-target.
    """
    n = len(y)
    n_tr = int(round(n * train_frac))
    if n_tr < 8 or n - n_tr < 6:
        return None
    Xtr, ytr, Xte, yte = X[:n_tr], y[:n_tr], X[n_tr:], y[n_tr:]
    codes_tr = (Xtr @ (2 ** np.arange(X.shape[1]))).astype(int)
    codes_te = (Xte @ (2 ** np.arange(X.shape[1]))).astype(int)
    table: dict[int, int] = {}
    for c in np.unique(codes_tr):
        m = codes_tr == c
        table[int(c)] = int(ytr[m].mean() >= 0.5)
    fallback = int(ytr.mean() >= 0.5)
    pred = np.array([table.get(int(c), fallback) for c in codes_te])
    return dict(n_train=n_tr, n_test=len(yte),
                accuracy=float((pred == yte).mean()),
                base_rate=float(max(yte.mean(), 1 - yte.mean())),
                train_base=float(max(ytr.mean(), 1 - ytr.mean())))


def clock_forecast(prices: np.ndarray, theta: float, n_lags: int = 3,
                   train_frac: float = 0.6):
    """Fit and score the short-wait forecast on one series at one threshold."""
    pv = directional_change(prices, theta)
    lg = legs(pv)
    if len(lg) < 15:
        return None
    tgt = short_wait_target(lg)
    if len(tgt) < 15:
        return None
    X, y = clock_features(lg, tgt, n_lags)
    if len(y) < 15:
        return None
    return _lookup_forecast(X, y, train_frac)


def forecast_vs_null(prices: np.ndarray, theta: float, n_null: int = 200,
                     n_lags: int = 3, train_frac: float = 0.6,
                     seed: int = 42) -> dict | None:
    """Observed forecast edge against the same pipeline on return-shuffled paths.

    The surrogate is passed through the *entire* pipeline — pivot detection,
    legs, running median, features, fit, score — so the null absorbs every
    incidental advantage the pipeline may confer, and only genuine temporal
    structure can survive it.
    """
    obs = clock_forecast(prices, theta, n_lags, train_frac)
    if obs is None:
        return None
    rng = np.random.default_rng(seed)
    accs, edges = [], []
    for _ in range(n_null):
        s = clock_forecast(return_shuffle(prices, rng), theta, n_lags, train_frac)
        if s is None:
            continue
        accs.append(s["accuracy"])
        edges.append(s["accuracy"] - s["base_rate"])
    if len(accs) < 20:
        return None
    accs, edges = np.asarray(accs), np.asarray(edges)
    obs_edge = obs["accuracy"] - obs["base_rate"]
    return dict(
        theta=theta, n_test=obs["n_test"], n_train=obs["n_train"],
        accuracy=round(obs["accuracy"], 4), base_rate=round(obs["base_rate"], 4),
        edge_over_base=round(obs_edge, 4),
        null_accuracy_mean=round(float(accs.mean()), 4),
        null_edge_mean=round(float(edges.mean()), 4),
        null_edge_sd=round(float(edges.std()), 4),
        excess_over_null=round(float(obs_edge - edges.mean()), 4),
        p_value=round(float((np.sum(edges >= obs_edge) + 1) / (len(edges) + 1)), 4),
        n_surrogates=len(edges))
