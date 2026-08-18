"""Regime discretisation by hidden Markov model, ported from GWP3.

Two emission schemes are supported, and the difference between them is the
single largest effect in the whole source study (GWP3 conclusion 2).

``parity``
    The source dissertation's scheme. The series is differenced and each change
    is reduced to its sign, giving a two-symbol alphabet. The resulting chain is
    degenerate: the WTI spot transition diagonal is 0.000 and the state changes
    in 189 of 198 months.

``gaussian``
    The GWP3 modification. The emission is the monthly log return itself, capped
    at three training-sample standard deviations and modelled with a diagonal
    Gaussian, with sticky Dirichlet pseudo-counts on the transition diagonal.
    The chain becomes persistent: average diagonal 0.742, 52 switches.

**Strict causality (protocol rule R1).** Decoding is filtered, not smoothed. The
regime attributed to month *t* is obtained by running the Viterbi recursion on
emissions up to and including *t* only. Decoding a hold-out window as a whole,
as the source dissertation does, lets the state assigned to a month be
influenced by what happens later in the sample; GWP3 reproduced that choice once
and obtained a nominal one-month-ahead accuracy of 100 per cent, which is
leakage rather than skill.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from hmmlearn.hmm import CategoricalHMM, GaussianHMM

from .config import N_RESTARTS, N_STATES, SERIES, STICKY


def parity_emission(series: pd.Series):
    """Sign of the first difference: the source dissertation's alphabet."""
    d = series.diff().iloc[1:]
    return (d > 0).astype(int).values.reshape(-1, 1), d


def log_returns(series: pd.Series, clip=None):
    """Monthly log return, optionally capped at a symmetric pair of bounds."""
    r = np.log(series).diff().iloc[1:]
    if clip is not None:
        r = r.clip(*clip)
    return r.values.reshape(-1, 1), r


def fit_categorical_hmm(x: np.ndarray):
    """Baum-Welch with restarts; the highest-likelihood solution is retained."""
    best = None
    for s in range(N_RESTARTS):
        m = CategoricalHMM(n_components=N_STATES, n_iter=500, random_state=s, tol=1e-6)
        m.fit(x)
        ll = m.score(x)
        if best is None or ll > best[0]:
            best = (ll, m)
    return best[1], best[0]


def fit_gaussian_hmm(x: np.ndarray):
    """Sticky Gaussian HMM with restarts.

    The transition prior adds ``STICKY`` pseudo-counts to the diagonal, encoding
    the belief that market regimes last several months rather than swapping
    every month.
    """
    best = None
    for s in range(N_RESTARTS):
        m = GaussianHMM(n_components=N_STATES, covariance_type="diag", n_iter=1000,
                        random_state=s,
                        transmat_prior=np.eye(N_STATES) * STICKY + 1.0)
        m.fit(x)
        ll = m.score(x)
        if best is None or ll > best[0]:
            best = (ll, m)
    return best[1], best[0]


def order_states(model, x: np.ndarray, values):
    """Relabel hidden states by the arithmetic mean of the underlying change.

    After relabelling, 0 = bear, 1 = stagnant, 2 = bull, so that the state index
    carries an economic meaning rather than an arbitrary fitting order.
    """
    st = model.predict(x)
    means = pd.Series(np.asarray(values).ravel()).groupby(st).mean()
    means = means.reindex(range(N_STATES)).fillna(means.mean())
    order = means.sort_values().index.tolist()
    return {int(old): new for new, old in enumerate(order)}, means.round(4).to_dict()


def online_decode(model, x_full: np.ndarray, relabel: dict) -> np.ndarray:
    """Filtered (real-time) decoding. See the module docstring on rule R1."""
    out = np.empty(len(x_full), dtype=int)
    for t in range(len(x_full)):
        _, seq = model.decode(x_full[:t + 1], algorithm="viterbi")
        out[t] = relabel[int(seq[-1])]
    return out


class RegimeDiscretiser:
    """One HMM per series, fitted on the training window, decoding the full sample.

    Parameters are estimated on the training window alone. ``transform`` then
    decodes every month of the full sample in real time, so the history
    preceding a hold-out month is used but never its future.
    """

    def __init__(self, kind: str):
        if kind not in ("parity", "gaussian"):
            raise ValueError(f"unknown emission scheme: {kind!r}")
        self.kind = kind
        self.models: dict = {}
        self.relabel: dict = {}
        self.params: dict = {}
        self.clip: dict = {}

    def _emit(self, series, clip=None):
        if self.kind == "parity":
            return parity_emission(series)
        return log_returns(series, clip)

    def fit(self, train: pd.DataFrame) -> "RegimeDiscretiser":
        for s in SERIES:
            if self.kind == "gaussian":
                r = np.log(train[s]).diff().dropna()
                self.clip[s] = (float(r.mean() - 3 * r.std()),
                                float(r.mean() + 3 * r.std()))
            else:
                self.clip[s] = None
            x, v = self._emit(train[s], self.clip[s])
            m, ll = (fit_categorical_hmm(x) if self.kind == "parity"
                     else fit_gaussian_hmm(x))
            rel, means = order_states(m, x, v)
            self.models[s], self.relabel[s] = m, rel
            entry = dict(log_likelihood=round(float(ll), 3),
                         transmat=np.round(m.transmat_, 4).tolist(),
                         startprob=np.round(m.startprob_, 4).tolist(),
                         state_means_raw={int(k): float(w) for k, w in means.items()},
                         persistence=round(float(np.mean(np.diag(m.transmat_))), 4))
            if self.kind == "parity":
                entry["emissionprob"] = np.round(m.emissionprob_, 4).tolist()
            else:
                entry["means"] = np.round(m.means_.ravel(), 4).tolist()
                entry["sd"] = np.round(np.sqrt(m.covars_.ravel()), 4).tolist()
            self.params[s] = entry
        return self

    def transform(self, full_df: pd.DataFrame) -> pd.DataFrame:
        """Decode the whole sample. The first month is lost to differencing."""
        out = pd.DataFrame(index=full_df.index[1:])
        for s in SERIES:
            x, _ = self._emit(full_df[s], self.clip[s])
            out[s] = online_decode(self.models[s], x, self.relabel[s])
        return out


def regime_economics(prices: pd.Series, regimes: pd.Series) -> pd.DataFrame:
    """Latent meaning of each decoded state: months, mean log return, volatility.

    Reproduces GWP3 Table 9. ``regimes`` must be aligned to ``prices`` on the
    differenced index.
    """
    r = np.log(prices).diff().reindex(regimes.index)
    rows = []
    for k in range(N_STATES):
        mask = regimes.values == k
        rows.append(dict(State=k, Months=int(mask.sum()),
                         Mean_log_return=round(float(r[mask].mean()), 4),
                         Volatility=round(float(r[mask].std()), 4),
                         Share=round(100 * float(mask.mean()), 1)))
    return pd.DataFrame(rows)
