"""GWP3 pipeline: dataset allocation, HMM regime discretisation, hill-climbing
Bayesian network, replication of Alvi (2018, Section 4.3) and an improved,
strictly causal forecasting model.

Run:  ./.venv/bin/python gwp3_pipeline.py
Writes figures to ./figures and result tables to ./results.
"""

import json
import os
import warnings

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates as mdates
import matplotlib.patches as mpatches
import matplotlib.pyplot as plt
import networkx as nx
import numpy as np
import pandas as pd
from hmmlearn.hmm import CategoricalHMM, GaussianHMM
from matplotlib.collections import LineCollection
from matplotlib.colors import BoundaryNorm, ListedColormap
from pgmpy.inference import VariableElimination
from pgmpy.estimators import HillClimbSearch
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.parameter_estimator import DiscreteBayesianEstimator
from scipy import stats
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score

warnings.filterwarnings("ignore")

BASE = os.path.dirname(os.path.abspath(__file__))
FIG = os.path.join(BASE, "figures")
RES = os.path.join(BASE, "results")
DATA_IN = os.path.abspath(os.path.join(BASE, "..", "GWP1", "data",
                                       "sterilized_monthly_data.csv"))
os.makedirs(FIG, exist_ok=True)
os.makedirs(RES, exist_ok=True)

SERIES = ["WTI_CL", "Brent_BZ", "USD_Idx", "CPI", "Fed_Funds", "Ind_Prod", "WTI_Spot"]
TARGET = "WTI_Spot"           # series whose regime is forecast (paper: WTISPLC)
LABELS = ["Bear", "Stagnant", "Bull"]
SEED = 42
N_RESTARTS = 10
STICKY = 5.0                  # Dirichlet pseudo-counts on the transition diagonal
SCORES = ["k2", "bdeu", "bic-d"]
results = {}


# ===========================================================================
# Question 1 & 2 -- allocation of the data
# ===========================================================================
def load_and_split(train_frac=0.70, val_frac=0.15):
    df = pd.read_csv(DATA_IN, parse_dates=["Date"], index_col="Date")[SERIES]
    n = len(df)
    n_tr, n_va = int(round(n * train_frac)), int(round(n * val_frac))
    return (df, df.iloc[:n_tr], df.iloc[n_tr:n_tr + n_va], df.iloc[n_tr + n_va:])


def split_summary(df, train, val, test):
    rows = []
    for name, part in [("Training", train), ("Validation", val), ("Testing", test)]:
        r = np.log(part[TARGET]).diff().dropna()
        rows.append(dict(Set=name, Months=len(part),
                         Start=str(part.index[0].date()), End=str(part.index[-1].date()),
                         Share=round(100 * len(part) / len(df), 1),
                         Mean_price=round(float(part[TARGET].mean()), 2),
                         Mean_logret=round(float(r.mean()), 4),
                         Vol_logret=round(float(r.std()), 4),
                         Min_price=round(float(part[TARGET].min()), 2),
                         Max_price=round(float(part[TARGET].max()), 2)))
    return pd.DataFrame(rows)


# ===========================================================================
# Question 3 -- regime detection (parameters learned on the training set only)
# ===========================================================================
def parity_emission(series):
    """First-order integration of the series, replaced by the parity of the change."""
    d = series.diff().iloc[1:]
    return (d > 0).astype(int).values.reshape(-1, 1), d


def log_returns(series, clip=None):
    r = np.log(series).diff().iloc[1:]
    if clip is not None:
        r = r.clip(*clip)
    return r.values.reshape(-1, 1), r


def fit_categorical_hmm(x):
    """Baum-Welch with restarts; the highest-likelihood solution is retained."""
    best = None
    for s in range(N_RESTARTS):
        m = CategoricalHMM(n_components=3, n_iter=500, random_state=s, tol=1e-6)
        m.fit(x)
        ll = m.score(x)
        if best is None or ll > best[0]:
            best = (ll, m)
    return best[1], best[0]


def fit_gaussian_hmm(x):
    """Sticky (persistence-favouring) Gaussian HMM with restarts."""
    best = None
    for s in range(N_RESTARTS):
        m = GaussianHMM(n_components=3, covariance_type="diag", n_iter=1000,
                        random_state=s, transmat_prior=np.eye(3) * STICKY + 1.0)
        m.fit(x)
        ll = m.score(x)
        if best is None or ll > best[0]:
            best = (ll, m)
    return best[1], best[0]


def order_states(model, x, values):
    """Index the hidden states by the arithmetic mean of the underlying change,
    so that 0 = Bear, 1 = Stagnant, 2 = Bull."""
    st = model.predict(x)
    means = pd.Series(np.asarray(values).ravel()).groupby(st).mean()
    means = means.reindex(range(3)).fillna(means.mean())
    order = means.sort_values().index.tolist()
    return {int(old): new for new, old in enumerate(order)}, means.round(4).to_dict()


def online_decode(model, x_full, relabel):
    """Filtered (real-time) decoding: the regime attributed to month t uses only
    the emissions observed up to and including t."""
    out = np.empty(len(x_full), dtype=int)
    for t in range(len(x_full)):
        _, seq = model.decode(x_full[:t + 1], algorithm="viterbi")
        out[t] = relabel[int(seq[-1])]
    return out


class RegimeDiscretiser:
    """Fits one HMM per series on the training window and decodes every month of
    the full sample in real time."""

    def __init__(self, kind):
        self.kind = kind          # "parity" or "gaussian"
        self.models, self.relabel, self.params, self.clip = {}, {}, {}, {}

    def _emit(self, series, clip=None):
        if self.kind == "parity":
            return parity_emission(series)
        return log_returns(series, clip)

    def fit(self, train):
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
                         state_means_raw={int(k): float(v_) for k, v_ in means.items()},
                         persistence=round(float(np.mean(np.diag(m.transmat_))), 4))
            if self.kind == "parity":
                entry["emissionprob"] = np.round(m.emissionprob_, 4).tolist()
            else:
                entry["means"] = np.round(m.means_.ravel(), 4).tolist()
                entry["sd"] = np.round(np.sqrt(m.covars_.ravel()), 4).tolist()
            self.params[s] = entry
        return self

    def transform(self, full_df):
        """Decode the whole sample; the splits are then taken from this frame, so
        the history preceding a hold-out month is used but never its future."""
        out = pd.DataFrame(index=full_df.index[1:])
        for s in SERIES:
            x, _ = self._emit(full_df[s], self.clip[s])
            out[s] = online_decode(self.models[s], x, self.relabel[s])
        return out


# ===========================================================================
# Question 4 -- structure learning by hill climbing, K2 parameter learning
# ===========================================================================
def expert_dag(nodes):
    """Prior structure from energy-market economics, the analogue of the EIA
    expert graph of the dissertation for our FRED and Yahoo variable set."""
    dag = DiscreteBayesianNetwork()
    dag.add_nodes_from(nodes)
    dag.add_edges_from([("Fed_Funds", "USD_Idx"), ("USD_Idx", "WTI_Spot"),
                        ("Ind_Prod", "WTI_Spot"), ("Brent_BZ", "WTI_Spot"),
                        ("WTI_CL", "WTI_Spot"), ("WTI_Spot", "CPI")])
    return dag


def as_categorical(data):
    """pgmpy identifies discrete variables from non-numeric dtypes."""
    return data.astype(str)


def learn_structure(data, scoring="k2", max_indegree=None, start_dag=None):
    hc = HillClimbSearch(as_categorical(data))
    dag = hc.estimate(scoring_method=scoring, max_indegree=max_indegree,
                      start_dag=start_dag, show_progress=False)
    model = DiscreteBayesianNetwork(list(dag.edges()))
    model.add_nodes_from(data.columns)
    return model


def fit_parameters(model, data, state_names):
    est = DiscreteBayesianEstimator(state_names=state_names, prior_type="K2")
    return model.fit(as_categorical(data), estimator=est)


def predict_regimes(model, data, target):
    """Inference on the belief network: the forecast column is removed and the
    most probable state of the target given the remaining evidence is returned."""
    evidence = as_categorical(data.drop(columns=[target]))
    evidence = evidence[[c for c in evidence.columns if c in model.nodes()]]
    return model.predict(evidence, n_jobs=1)[target].astype(int).values


def posterior_probabilities(model, data, target):
    """Posterior distribution over the target regime for every hold-out month."""
    infer = VariableElimination(model)
    evidence_cols = [c for c in model.nodes() if c != target and c in data.columns]
    rows = []
    for _, row in as_categorical(data).iterrows():
        q = infer.query([target], evidence={c: row[c] for c in evidence_cols},
                        show_progress=False)
        order = [q.state_names[target].index(str(k)) for k in [0, 1, 2]]
        rows.append(q.values[order])
    return np.vstack(rows)


def expected_return_rule(prob, state_means, margin=0.0):
    """Decision-theoretic rule: take the position whose expected monthly log
    return, under the posterior over regimes, is largest in absolute terms."""
    mu = np.array([state_means[k] for k in [0, 1, 2]])
    exp_ret = prob @ mu
    return np.where(exp_ret > margin, 2, np.where(exp_ret < -margin, 0, 1)), exp_ret


def brier_score(prob, y_true):
    onehot = np.zeros_like(prob)
    onehot[np.arange(len(y_true)), np.asarray(y_true)] = 1.0
    return round(float(np.mean(np.sum((prob - onehot) ** 2, axis=1))), 4)


def plot_posterior(index, prob, y_true, title, fname):
    fig, ax = plt.subplots(figsize=(12, 4.4))
    ax.stackplot(index, prob[:, 0], prob[:, 1], prob[:, 2],
                 colors=["#D62728", "#1F77B4", "#2CA02C"], alpha=0.75,
                 labels=["P(Bear)", "P(Stagnant)", "P(Bull)"])
    mark = {0: ("v", "#7F0000"), 1: ("o", "#08306B"), 2: ("^", "#00441B")}
    for k in [0, 1, 2]:
        sel = np.asarray(y_true) == k
        if sel.any():
            ax.scatter(np.array(index)[sel], np.full(sel.sum(), 1.03), s=40,
                       marker=mark[k][0], color=mark[k][1],
                       label=f"Realised {LABELS[k]}")
    ax.set_ylim(0, 1.1); ax.set_xlabel("Date")
    ax.set_ylabel("Posterior probability")
    ax.set_title(title); ax.legend(ncol=3, fontsize=8, loc="lower left")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def score_forecast(y_true, y_pred, shift=False):
    y_true = np.asarray(y_true)
    y_pred = np.roll(np.asarray(y_pred), 1) if shift else np.asarray(y_pred)
    err = float(np.mean(y_true != y_pred))
    return dict(error=round(100 * err, 2), accuracy=round(100 * (1 - err), 2),
                balanced_accuracy=round(100 * balanced_accuracy_score(y_true, y_pred), 2),
                macro_f1=round(100 * f1_score(y_true, y_pred, average="macro"), 2),
                n=int(len(y_true)),
                confusion=confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist(),
                y_true=y_true.tolist(), y_pred=y_pred.tolist())


def regime_economics(prices, regimes):
    """Latent meaning of each hidden state: the realised monthly log return of the
    WTI spot price during the months attributed to that state."""
    r = np.log(prices).diff().reindex(regimes.index)
    rows = []
    for k in [0, 1, 2]:
        sel = r[np.asarray(regimes.values) == k].dropna()
        rows.append(dict(State=k, Label=LABELS[k], Months=int(len(sel)),
                         Mean_log_return=round(float(sel.mean()), 4) if len(sel) else np.nan,
                         Volatility=round(float(sel.std()), 4) if len(sel) > 1 else np.nan,
                         Share=round(100 * len(sel) / len(regimes), 1)))
    return pd.DataFrame(rows)


def strategy_value(prices, index, y_pred):
    """Terminal value of one barrel traded on the signal, without transaction costs."""
    px = prices.loc[index]
    ret = px.pct_change().fillna(0.0).values
    pos = np.where(np.asarray(y_pred) == 2, 1.0, np.where(np.asarray(y_pred) == 0, -1.0, 0.0))
    return float(np.cumprod(1 + pos * ret)[-1] * float(px.iloc[0]))


def directional_metrics(prices, index, y_pred):
    """Economic reading of the forecast: a bull call is a long signal, a bear call
    a short signal, a stagnant call no position."""
    r = np.log(prices).diff().reindex(index).values
    calls = np.isin(y_pred, [0, 2])
    hits = ((np.asarray(y_pred) == 2) & (r > 0)) | ((np.asarray(y_pred) == 0) & (r < 0))
    n_calls = int(calls.sum())
    return dict(n_months=int(len(index)), n_directional_calls=n_calls,
                coverage=round(100 * n_calls / len(index), 2),
                hit_rate=round(100 * float(hits[calls].mean()), 2) if n_calls else np.nan)


def accuracy_ci(correct, n, conf=0.95):
    lo, hi = stats.binomtest(int(correct), int(n)).proportion_ci(conf)
    return [round(100 * lo, 2), round(100 * hi, 2)]


def mcnemar(y_true, pred_a, pred_b):
    """Exact McNemar test comparing two forecasting rules on the same months."""
    a = np.asarray(pred_a) == np.asarray(y_true)
    b = np.asarray(pred_b) == np.asarray(y_true)
    n01 = int((~a & b).sum()); n10 = int((a & ~b).sum())
    if n01 + n10 == 0:
        return dict(n01=n01, n10=n10, p_value=1.0)
    p = float(stats.binomtest(n10, n01 + n10, 0.5).pvalue)
    return dict(n01=n01, n10=n10, p_value=round(p, 4))


def tune_on_validation(d_train, d_val, target, state_names, shift, seeded=(False, True)):
    """Search over scoring function, maximum in-degree and expert seeding; the
    validation set alone decides which candidate is carried to the testing set."""
    grid = []
    for scoring in SCORES:
        for indeg in [2, 3, None]:
            for seed_expert in seeded:
                start = expert_dag(list(d_train.columns)) if seed_expert else None
                try:
                    m = learn_structure(d_train, scoring, indeg, start)
                    m = fit_parameters(m, d_train, state_names)
                    s = score_forecast(d_val[target].values,
                                       predict_regimes(m, d_val, target), shift)
                except Exception as exc:
                    print(f"   [skipped] {scoring}/{indeg}/{seed_expert}: {exc}")
                    continue
                grid.append(dict(scoring=scoring, max_indegree=indeg,
                                 expert_seeded=seed_expert, n_edges=len(m.edges()),
                                 val_accuracy=s["accuracy"], val_error=s["error"],
                                 model=m))
                print(f"   {scoring:6s} in-degree={str(indeg):4s} expert={seed_expert!s:5s}"
                      f" edges={len(m.edges()):2d}  validation accuracy={s['accuracy']:6.2f}%")
    grid.sort(key=lambda r: (-r["val_accuracy"], r["n_edges"]))
    return grid


# ===========================================================================
# figures
# ===========================================================================
def plot_allocation(df, train, val, test):
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.plot(df.index, df[TARGET], color="black", lw=1.2, label="WTI spot price")
    for part, colour, lab in [(train, "#4C78A8", "Training (70%)"),
                              (val, "#F58518", "Validation (15%)"),
                              (test, "#54A24B", "Testing (15%)")]:
        ax.axvspan(part.index[0], part.index[-1], color=colour, alpha=0.18,
                   label=f"{lab}: {len(part)} months")
    ax.set_xlabel("Date"); ax.set_ylabel("US dollars per barrel")
    ax.set_title("Chronological allocation of the 199 monthly observations")
    ax.legend(loc="upper right", fontsize=9); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, "data_allocation.png"), dpi=150)
    plt.close(fig)


def plot_regimes(prices, regimes, title, fname):
    fig, ax = plt.subplots(figsize=(12, 5))
    x = mdates.date2num(prices.index.to_pydatetime())
    pts = np.array([x, prices.values]).T.reshape(-1, 1, 2)
    seg = np.concatenate([pts[:-1], pts[1:]], axis=1)
    cmap = ListedColormap(["#D62728", "#1F77B4", "#2CA02C"])
    lc = LineCollection(seg, cmap=cmap, norm=BoundaryNorm(range(4), cmap.N), lw=2)
    lc.set_array(np.asarray(regimes)[:-1])
    ax.add_collection(lc)
    ax.set_xlim(x.min(), x.max())
    ax.set_ylim(prices.min() * 0.9, prices.max() * 1.08)
    ax.xaxis.set_major_locator(mdates.YearLocator(2))
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
    ax.set_xlabel("Date"); ax.set_ylabel("US dollars per barrel"); ax.set_title(title)
    ax.legend(handles=[mpatches.Patch(color="#D62728", label="Bear"),
                       mpatches.Patch(color="#1F77B4", label="Stagnant"),
                       mpatches.Patch(color="#2CA02C", label="Bull")],
              loc="upper left", fontsize=9)
    ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def plot_regime_panel(prices_df, frame, title, fname):
    """One panel per modelled series, each price path coloured by the regime the
    hidden Markov model attributes to that series in that month."""
    cmap = ListedColormap(["#D62728", "#1F77B4", "#2CA02C"])
    norm = BoundaryNorm(range(4), cmap.N)
    fig, axes = plt.subplots(4, 2, figsize=(13, 12), sharex=True)
    axes = axes.ravel()
    for ax, s in zip(axes, SERIES):
        px = prices_df[s].loc[frame.index]
        x = mdates.date2num(px.index.to_pydatetime())
        pts = np.array([x, px.values]).T.reshape(-1, 1, 2)
        seg = np.concatenate([pts[:-1], pts[1:]], axis=1)
        lc = LineCollection(seg, cmap=cmap, norm=norm, lw=1.4)
        lc.set_array(np.asarray(frame[s].values)[:-1])
        ax.add_collection(lc)
        ax.set_xlim(x.min(), x.max())
        pad = 0.05 * (px.max() - px.min())
        ax.set_ylim(px.min() - pad, px.max() + pad)
        ax.xaxis.set_major_locator(mdates.YearLocator(4))
        ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
        ax.set_title(s, fontsize=10)
        ax.set_ylabel("Index level" if s in ("USD_Idx", "CPI", "Ind_Prod")
                      else ("Per cent" if s == "Fed_Funds" else "USD per barrel"),
                      fontsize=8)
        ax.grid(alpha=0.3)
        ax.tick_params(labelsize=8)
    for ax in axes[len(SERIES):]:
        ax.axis("off")
    for ax in axes[len(SERIES) - 2:len(SERIES)]:
        ax.set_xlabel("Date", fontsize=9)
    axes[len(SERIES)].legend(
        handles=[mpatches.Patch(color="#D62728", label="Bear"),
                 mpatches.Patch(color="#1F77B4", label="Stagnant"),
                 mpatches.Patch(color="#2CA02C", label="Bull")],
        loc="center", fontsize=11, frameon=False, title="Decoded regime")
    fig.suptitle(title, fontsize=13)
    fig.tight_layout(rect=[0, 0, 1, 0.97])
    fig.savefig(os.path.join(FIG, fname), dpi=150)
    plt.close(fig)


def plot_network(model, title, fname, highlight=("forecast",)):
    fig, ax = plt.subplots(figsize=(9.5, 6.5))
    G = nx.DiGraph(); G.add_nodes_from(model.nodes()); G.add_edges_from(model.edges())
    pos = nx.spring_layout(G, seed=SEED, k=1.3)
    colours = ["#FDE3C6" if n in highlight else "#DCE9F5" for n in G.nodes()]
    nx.draw_networkx_nodes(G, pos, node_size=2600, node_color=colours,
                           edgecolors="#37536B", ax=ax)
    nx.draw_networkx_edges(G, pos, arrows=True, arrowsize=18, width=1.4,
                           edge_color="#37536B", node_size=2600, ax=ax)
    nx.draw_networkx_labels(G, pos, font_size=9, ax=ax)
    ax.set_title(title); ax.axis("off")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def plot_confusion(cm, title, fname):
    cm = np.array(cm)
    fig, ax = plt.subplots(figsize=(5.4, 4.8))
    im = ax.imshow(cm, cmap="Blues")
    ax.set_xticks(range(3), LABELS); ax.set_yticks(range(3), LABELS)
    ax.set_xlabel("Forecast regime"); ax.set_ylabel("Realised regime")
    for i in range(3):
        for j in range(3):
            ax.text(j, i, cm[i, j], ha="center", va="center",
                    color="white" if cm[i, j] > cm.max() / 2 else "black")
    ax.set_title(title); fig.colorbar(im, ax=ax, label="Number of months")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def plot_timeline(index, y_true, y_pred, title, fname):
    y_true, y_pred = np.array(y_true), np.array(y_pred)
    fig, ax = plt.subplots(figsize=(12, 3.8))
    ax.step(index, y_true, where="mid", color="black", lw=1.8, label="Realised regime")
    ax.step(index, y_pred, where="mid", color="#F58518", lw=1.8, ls="--",
            label="Forecast regime")
    hit = y_true == y_pred
    ax.scatter(np.array(index)[hit], y_true[hit], s=44, color="#2CA02C", zorder=3,
               label="Correct")
    ax.scatter(np.array(index)[~hit], y_true[~hit], s=52, marker="x", color="#D62728",
               zorder=3, label="Incorrect")
    ax.set_yticks([0, 1, 2], LABELS); ax.set_ylim(-0.5, 2.5)
    ax.set_xlabel("Date"); ax.set_ylabel("Regime"); ax.set_title(title)
    ax.legend(ncol=4, fontsize=8, loc="upper center"); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def plot_accuracy_bars(table, title, fname):
    labels, vals = list(table.keys()), list(table.values())
    fig, ax = plt.subplots(figsize=(9.5, 4.8))
    bars = ax.bar(labels, vals, color="#4C78A8")
    bars[int(np.argmax(vals))].set_color("#2CA02C")
    ax.axhline(100 / 3, color="#D62728", ls="--", lw=1.2, label="Uninformed guess (33.3%)")
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width() / 2, v + 1, f"{v:.1f}", ha="center", fontsize=9)
    ax.set_ylabel("Accuracy on the testing set (%)"); ax.set_title(title)
    ax.set_ylim(0, max(vals) * 1.3); ax.legend(); ax.grid(alpha=0.3, axis="y")
    plt.setp(ax.get_xticklabels(), rotation=12, ha="right", fontsize=8)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


def plot_strategy(prices, signals, title, fname):
    """Long one barrel when a bull regime is forecast, short when a bear regime is
    forecast, flat otherwise; compared with holding one barrel throughout."""
    ret = prices.pct_change().fillna(0.0).values
    pos = np.where(np.asarray(signals) == 2, 1.0,
                   np.where(np.asarray(signals) == 0, -1.0, 0.0))
    strat = np.cumprod(1 + pos * ret) * float(prices.iloc[0])
    hold = np.cumprod(1 + ret) * float(prices.iloc[0])
    fig, ax = plt.subplots(figsize=(11, 4.8))
    ax.plot(prices.index, hold, color="#D62728", lw=1.6, label="Buy and hold (one barrel)")
    ax.plot(prices.index, strat, color="#2CA02C", lw=1.6, label="Regime-driven positioning")
    ax.set_xlabel("Date"); ax.set_ylabel("Value of the position (US dollars)")
    ax.set_title(title); ax.legend(); ax.grid(alpha=0.3)
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)
    return float(strat[-1]), float(hold[-1])


def plot_transition_heatmaps(par, gau, fname):
    fig, axes = plt.subplots(1, 2, figsize=(10.5, 4.4))
    for ax, mat, name in [(axes[0], np.array(par), "Parity emissions (replication)"),
                          (axes[1], np.array(gau), "Log-return emissions (improved)")]:
        im = ax.imshow(mat, cmap="Purples", vmin=0, vmax=1)
        ax.set_xticks(range(3), ["State 1", "State 2", "State 3"])
        ax.set_yticks(range(3), ["State 1", "State 2", "State 3"])
        for i in range(3):
            for j in range(3):
                ax.text(j, i, f"{mat[i, j]:.2f}", ha="center", va="center",
                        color="white" if mat[i, j] > 0.5 else "black", fontsize=9)
        ax.set_title(name, fontsize=10)
        ax.set_xlabel("State at month t+1"); ax.set_ylabel("State at month t")
        fig.colorbar(im, ax=ax, fraction=0.046)
    fig.suptitle("Estimated transition matrices for the WTI spot price")
    fig.tight_layout(); fig.savefig(os.path.join(FIG, fname), dpi=150); plt.close(fig)


# ===========================================================================
def main():
    df, train, val, test = load_and_split()
    idx_tr, idx_va, idx_te = train.index, val.index, test.index
    summary = split_summary(df, train, val, test)
    results["split"] = summary.to_dict("records")
    print("Total monthly observations:", len(df))
    print(summary.to_string(index=False))
    plot_allocation(df, train, val, test)

    # ---- Question 3: two regime discretisations --------------------------
    disc = {}
    for kind in ["parity", "gaussian"]:
        d = RegimeDiscretiser(kind).fit(train)
        frame = d.transform(df)
        disc[kind] = dict(discretiser=d, frame=frame,
                          train=frame.loc[frame.index.intersection(idx_tr)],
                          val=frame.loc[frame.index.intersection(idx_va)],
                          test=frame.loc[frame.index.intersection(idx_te)])
        results[f"hmm_{kind}"] = d.params
        sw = int((np.diff(frame[TARGET].values) != 0).sum())
        print(f"\n[{kind}] WTI spot: {sw} regime switches over {len(frame)} months; "
              f"shares {frame[TARGET].value_counts(normalize=True).sort_index().round(3).to_dict()}")
        plot_regimes(df[TARGET].iloc[1:], frame[TARGET].values,
                     f"Decoded regimes of the WTI spot price ({kind} emissions)",
                     f"regimes_full_{kind}.png")
        for nm, part in [("train", "train"), ("validation", "val"), ("test", "test")]:
            sub = disc[kind][part]
            plot_regimes(df[TARGET].loc[sub.index], sub[TARGET].values,
                         f"Regimes on the {nm} set ({kind} emissions)",
                         f"regimes_{nm}_{kind}.png")
    results["regime_shares"] = {
        kind: {nm: disc[kind][p][TARGET].value_counts(normalize=True)
               .reindex([0, 1, 2]).fillna(0).round(3).to_dict()
               for nm, p in [("train", "train"), ("validation", "val"), ("test", "test")]}
        for kind in disc}
    results["regime_switches"] = {
        kind: int((np.diff(disc[kind]["frame"][TARGET].values) != 0).sum()) for kind in disc}
    for kind, label in [("gaussian", "log-return"), ("parity", "parity")]:
        plot_regime_panel(df, disc[kind]["frame"],
                          f"Decoded regimes of all seven modelled series ({label} emissions)",
                          f"regimes_panel_{kind}.png")
    plot_transition_heatmaps(results["hmm_parity"][TARGET]["transmat"],
                             results["hmm_gaussian"][TARGET]["transmat"],
                             "transition_matrices.png")

    state_names = {c: ["0", "1", "2"] for c in list(SERIES) + ["forecast"]}

    # ---- Question 4: replication of the paper's protocol -----------------
    print("\n=== Replication model (parity emissions, forecast node, paper protocol) ===")
    A = {k: disc["parity"][k].copy() for k in ["train", "val", "test"]}
    for k in A:
        A[k]["forecast"] = A[k][TARGET].values
    gridA = tune_on_validation(A["train"], A["val"], "forecast", state_names, shift=True)
    bestA = gridA[0]
    results["validation_grid_A"] = [{k: v for k, v in r.items() if k != "model"} for r in gridA]
    baseA = [r for r in gridA if r["scoring"] == "k2" and r["max_indegree"] is None
             and not r["expert_seeded"]][0]
    results["baseline_k2_A"] = {k: v for k, v in baseA.items() if k != "model"}
    results["selected_A"] = {k: v for k, v in bestA.items() if k != "model"}
    modelA = bestA["model"]
    results["edges_A_k2"] = [list(e) for e in baseA["model"].edges()]
    results["edges_A_selected"] = [list(e) for e in modelA.edges()]
    results["markov_blanket_A"] = sorted(modelA.get_markov_blanket("forecast"))
    plot_network(baseA["model"],
                 "Belief network learned by hill climbing (K2 score, training set)",
                 "network_k2_train.png")
    plot_network(modelA, "Replication model selected on the validation set",
                 "network_selected_A.png")
    sA_val = score_forecast(A["val"]["forecast"].values,
                            predict_regimes(modelA, A["val"], "forecast"), shift=True)
    sA_test = score_forecast(A["test"]["forecast"].values,
                             predict_regimes(modelA, A["test"], "forecast"), shift=True)
    results["modelA"] = dict(validation=sA_val, test=sA_test)
    print(f"Replication model: validation accuracy {sA_val['accuracy']}% "
          f"(error {sA_val['error']}%), test accuracy {sA_test['accuracy']}% "
          f"(error {sA_test['error']}%)")

    # ---- Question 5: improved, strictly causal forecasting model ---------
    print("\n=== Improved model (log-return emissions, target led by one month) ===")

    def lead(frame):
        f = frame[SERIES].copy()
        f["forecast"] = frame[TARGET].shift(-1)
        return f.dropna().astype(int)

    B = {k: lead(disc["gaussian"][k]) for k in ["train", "val", "test"]}
    gridB = tune_on_validation(B["train"], B["val"], "forecast", state_names, shift=False)
    bestB = gridB[0]
    results["validation_grid_B"] = [{k: v for k, v in r.items() if k != "model"} for r in gridB]
    results["selected_B"] = {k: v for k, v in bestB.items() if k != "model"}
    modelB = bestB["model"]
    sB_val = score_forecast(B["val"]["forecast"].values,
                            predict_regimes(modelB, B["val"], "forecast"))
    sB_test = score_forecast(B["test"]["forecast"].values,
                             predict_regimes(modelB, B["test"], "forecast"))
    results["modelB"] = dict(validation=sB_val, test=sB_test,
                             edges=[list(e) for e in modelB.edges()],
                             markov_blanket=sorted(modelB.get_markov_blanket("forecast")))
    results["cpd_forecast_B"] = str(modelB.get_cpds("forecast"))
    plot_network(modelB, "Improved predictive belief network (target led by one month)",
                 "network_predictive.png")
    print(f"Improved model: validation accuracy {sB_val['accuracy']}%, "
          f"test accuracy {sB_test['accuracy']}%")

    # ---- benchmarks -------------------------------------------------------
    yB = B["test"]["forecast"].values
    maj = int(pd.Series(B["train"]["forecast"]).mode()[0])
    persistence = B["test"][TARGET].values          # regime at t as forecast of t+1
    rng = np.random.default_rng(SEED)
    bench = {
        "Uninformed guess": round(100 * float(np.mean(yB == rng.integers(0, 3, len(yB)))), 2),
        "Majority regime": round(100 * float(np.mean(yB == maj)), 2),
        "Persistence": round(100 * float(np.mean(yB == persistence)), 2),
        "Belief network\n(replication)": sA_test["accuracy"],
        "Belief network\n(improved)": sB_test["accuracy"],
    }
    results["benchmarks_test"] = bench
    nB = len(yB)
    results["inference"] = dict(
        improved_accuracy_ci=accuracy_ci(round(sB_test["accuracy"] / 100 * nB), nB),
        replication_accuracy_ci=accuracy_ci(
            round(sA_test["accuracy"] / 100 * sA_test["n"]), sA_test["n"]),
        improved_vs_persistence=mcnemar(yB, sB_test["y_pred"], persistence),
        improved_vs_majority=mcnemar(yB, sB_test["y_pred"], np.full(nB, maj)))
    results["directional"] = dict(
        improved=directional_metrics(df[TARGET], B["test"].index, sB_test["y_pred"]),
        replication=directional_metrics(df[TARGET], A["test"].index, sA_test["y_pred"]))
    results["regime_economics"] = {
        kind: {nm: regime_economics(df[TARGET], disc[kind][p][TARGET]).to_dict("records")
               for nm, p in [("train", "train"), ("test", "test")]}
        for kind in disc}
    print("\nStatistical comparison:", results["inference"])
    print("Directional reading:", results["directional"])
    print("\nLatent meaning of the states (improved discretisation, training set):")
    print(regime_economics(df[TARGET], disc["gaussian"]["train"][TARGET]).to_string(index=False))
    plot_accuracy_bars(bench, "One-month-ahead regime forecast accuracy on the testing set",
                       "accuracy_comparison.png")

    plot_confusion(sA_test["confusion"], "Replication model, testing set",
                   "confusion_modelA_test.png")
    plot_confusion(sB_test["confusion"], "Improved model, testing set",
                   "confusion_modelB_test.png")
    plot_timeline(A["test"].index, sA_test["y_true"], sA_test["y_pred"],
                  "One-month-ahead regime forecasts, testing set (replication model)",
                  "timeline_modelA_test.png")
    plot_timeline(B["test"].index, sB_test["y_true"], sB_test["y_pred"],
                  "One-month-ahead regime forecasts, testing set (improved model)",
                  "timeline_modelB_test.png")

    pxA = df[TARGET].loc[A["test"].index]
    pxB = df[TARGET].loc[B["test"].index]
    sa, ha = plot_strategy(pxA, sA_test["y_pred"],
                           "Regime-driven positioning against buy and hold (replication model)",
                           "strategy_modelA.png")
    sb, hb = plot_strategy(pxB, sB_test["y_pred"],
                           "Regime-driven positioning against buy and hold (improved model)",
                           "strategy_modelB.png")
    results["strategy"] = dict(
        replication=dict(start=round(float(pxA.iloc[0]), 2), strategy=round(sa, 2),
                         buy_hold=round(ha, 2)),
        improved=dict(start=round(float(pxB.iloc[0]), 2), strategy=round(sb, 2),
                      buy_hold=round(hb, 2)))

    # ---- decision-theoretic reading of the posterior ----------------------
    state_means = {int(r["State"]): float(r["Mean_log_return"])
                   for r in results["regime_economics"]["gaussian"]["train"]}
    probB_val = posterior_probabilities(modelB, B["val"], "forecast")
    margin_grid = [0.0, 0.005, 0.01, 0.02, 0.03, 0.05]
    margin_search = []
    for mg in margin_grid:
        pv, _ = expected_return_rule(probB_val, state_means, mg)
        dm = directional_metrics(df[TARGET], B["val"].index, pv)
        sv = score_forecast(B["val"]["forecast"].values, pv)
        val_value = strategy_value(df[TARGET], B["val"].index, pv)
        margin_search.append(dict(margin=mg, coverage=dm["coverage"],
                                  hit_rate=dm["hit_rate"], accuracy=sv["accuracy"],
                                  terminal_value=round(val_value, 2)))
        print(f"   margin={mg:<6} validation coverage={dm['coverage']:5.1f}% "
              f"hit rate={dm['hit_rate']} accuracy={sv['accuracy']}% "
              f"terminal value={val_value:.2f}")
    best_margin = max(margin_search, key=lambda r: (r["terminal_value"], -r["margin"]))["margin"]
    results["margin_search"] = margin_search
    results["selected_margin"] = best_margin
    print(f"   selected margin: {best_margin}")
    probB = posterior_probabilities(modelB, B["test"], "forecast")
    rule_pred, exp_ret = expected_return_rule(probB, state_means, best_margin)
    sC_test = score_forecast(yB, rule_pred)
    results["modelC"] = dict(margin=best_margin, test=sC_test, brier=brier_score(probB, yB),
                             state_means=state_means,
                             expected_returns=np.round(exp_ret, 4).tolist(),
                             directional=directional_metrics(df[TARGET], B["test"].index,
                                                             rule_pred))
    plot_posterior(B["test"].index, probB, yB,
                   "Posterior regime probabilities for the coming month, testing set",
                   "posterior_modelC.png")
    sc, hc_ = plot_strategy(pxB, rule_pred,
                            "Regime-driven positioning against buy and hold (expected-return rule)",
                            "strategy_modelC.png")
    results["strategy"]["expected_return_rule"] = dict(
        start=round(float(pxB.iloc[0]), 2), strategy=round(sc, 2), buy_hold=round(hc_, 2))
    bench["Expected-return\nrule"] = sC_test["accuracy"]
    plot_accuracy_bars(bench, "One-month-ahead regime forecast accuracy on the testing set",
                       "accuracy_comparison.png")
    print("Expected-return rule:", {k: v for k, v in sC_test.items()
                                    if k not in ("y_true", "y_pred", "confusion")},
          "| Brier", results["modelC"]["brier"], "|", results["modelC"]["directional"])

    results["paper"] = dict(validation_error=67.86, validation_accuracy=32.14,
                            test_error=42.86, test_accuracy=57.14, n_test=28,
                            source="Alvi (2018), pp. 62-63")

    for kind in disc:
        for nm, p in [("train", "train"), ("validation", "val"), ("test", "test")]:
            disc[kind][p].to_csv(os.path.join(RES, f"discrete_{kind}_{nm}.csv"))
    with open(os.path.join(RES, "results.json"), "w") as fh:
        json.dump(results, fh, indent=2, default=str)
    print("\nResults written to", RES)
    return results


if __name__ == "__main__":
    main()
