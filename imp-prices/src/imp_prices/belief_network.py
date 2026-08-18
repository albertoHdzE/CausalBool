"""The probabilistic graphical model, ported from GWP3 as the comparison arm.

This is the object the index-set network is measured against. It is ported
literally rather than reimplemented, and asserted against
``reference/gwp3/results.json`` in ``tests/test_belief_network_parity.py``,
for the same reason the discretiser was: a comparison against a
reimplementation measures the reimplementation.

Two specifications, following GWP3 sections 5 and 6:

**A, the replication.** Parity emissions, a ``forecast`` node that duplicates the
current month's target regime, and the inferred state rolled forward one month.
The duplication makes the structure search learn a deterministic relationship, so
rolling it forward turns an accurate nowcast into a measure of regime
persistence. Under parity emissions persistence is near zero by construction, and
the specification scores below an uninformed guess.

**B, the improved model.** Log-return emissions and a ``forecast`` node defined
as the target regime of the *following* month, so the network forecasts rather
than reconstructs.
"""

from __future__ import annotations

import contextlib
import sys

import numpy as np
import pandas as pd
from pgmpy.estimators import HillClimbSearch
from pgmpy.inference import VariableElimination
from pgmpy.models import DiscreteBayesianNetwork
from pgmpy.parameter_estimator import DiscreteBayesianEstimator
from scipy import stats
from sklearn.metrics import balanced_accuracy_score, confusion_matrix, f1_score

from .config import SERIES, TARGET

SCORES = ["k2", "bdeu", "bic-d"]
INDEGREES = [2, 3, None]
STATE_NAMES = {c: ["0", "1", "2"] for c in list(SERIES) + ["forecast"]}


def expert_dag(nodes) -> DiscreteBayesianNetwork:
    """Prior structure from energy-market economics.

    The analogue of the dissertation's EIA expert graph for this variable set.
    GWP3 section 7, claim 4, notes that seeding the search with expert structure
    contradicts the dissertation's claim to require no prior expert knowledge.
    """
    dag = DiscreteBayesianNetwork()
    dag.add_nodes_from(nodes)
    dag.add_edges_from([("Fed_Funds", "USD_Idx"), ("USD_Idx", "WTI_Spot"),
                        ("Ind_Prod", "WTI_Spot"), ("Brent_BZ", "WTI_Spot"),
                        ("WTI_CL", "WTI_Spot"), ("WTI_Spot", "CPI")])
    return dag


def as_categorical(data: pd.DataFrame) -> pd.DataFrame:
    """pgmpy identifies discrete variables from non-numeric dtypes."""
    return data.astype(str)


def learn_structure(data, scoring="k2", max_indegree=None, start_dag=None):
    hc = HillClimbSearch(as_categorical(data))
    dag = hc.estimate(scoring_method=scoring, max_indegree=max_indegree,
                      start_dag=start_dag, show_progress=False)
    model = DiscreteBayesianNetwork(list(dag.edges()))
    model.add_nodes_from(data.columns)
    return model


def fit_parameters(model, data, state_names=None):
    """K2 prior (Cooper and Herskovits): avoids zero probabilities for
    unobserved but not impossible configurations, which maximum likelihood would
    assign given the sample size."""
    est = DiscreteBayesianEstimator(state_names=state_names or STATE_NAMES,
                                    prior_type="K2")
    return model.fit(as_categorical(data), estimator=est)


@contextlib.contextmanager
def _no_progress_bar():
    """Silence the progress bar pgmpy's ``predict`` raises unconditionally.

    ``DiscreteBayesianNetwork.predict`` calls ``tqdm.auto.tqdm`` with no option to
    disable it. Under ``tqdm.auto`` that resolves to an ipywidgets bar inside a
    notebook, and a widget view cannot be rendered outside the session that
    produced it: the saved notebook shows "Could not render content for
    application/vnd.jupyter.widget-view+json" instead of an output. That makes the
    notebook fail as evidence, so the bar is suppressed at the only place we
    control — our own wrapper.

    The module-level ``tqdm`` name is patched rather than the library file, so
    ``reference/`` and the installed package both stay untouched.
    """
    mod = sys.modules.get("pgmpy.models.DiscreteBayesianNetwork")
    original = getattr(mod, "tqdm", None) if mod is not None else None
    if original is not None:
        mod.tqdm = lambda iterable=None, *a, **k: iterable
    try:
        yield
    finally:
        if original is not None:
            mod.tqdm = original


def predict_regimes(model, data, target="forecast"):
    evidence = as_categorical(data.drop(columns=[target]))
    evidence = evidence[[c for c in evidence.columns if c in model.nodes()]]
    with _no_progress_bar():
        return model.predict(evidence, n_jobs=1)[target].astype(int).values


def posterior_probabilities(model, data, target="forecast"):
    infer = VariableElimination(model)
    cols = [c for c in model.nodes() if c != target and c in data.columns]
    rows = []
    for _, row in as_categorical(data).iterrows():
        q = infer.query([target], evidence={c: row[c] for c in cols},
                        show_progress=False)
        order = [q.state_names[target].index(str(k)) for k in (0, 1, 2)]
        rows.append(q.values[order])
    return np.vstack(rows)


def score_forecast(y_true, y_pred, shift=False) -> dict:
    y_true = np.asarray(y_true)
    y_pred = np.roll(np.asarray(y_pred), 1) if shift else np.asarray(y_pred)
    err = float(np.mean(y_true != y_pred))
    return dict(error=round(100 * err, 2), accuracy=round(100 * (1 - err), 2),
                balanced_accuracy=round(100 * balanced_accuracy_score(y_true, y_pred), 2),
                macro_f1=round(100 * f1_score(y_true, y_pred, average="macro"), 2),
                n=int(len(y_true)),
                confusion=confusion_matrix(y_true, y_pred, labels=[0, 1, 2]).tolist(),
                y_true=y_true.tolist(), y_pred=y_pred.tolist())


def accuracy_ci(correct, n, conf=0.95):
    lo, hi = stats.binomtest(int(correct), int(n)).proportion_ci(conf)
    return [round(100 * lo, 2), round(100 * hi, 2)]


def mcnemar(y_true, pred_a, pred_b) -> dict:
    """Exact McNemar test comparing two rules on the same months."""
    a = np.asarray(pred_a) == np.asarray(y_true)
    b = np.asarray(pred_b) == np.asarray(y_true)
    n01, n10 = int((~a & b).sum()), int((a & ~b).sum())
    if n01 + n10 == 0:
        return dict(n01=n01, n10=n10, p_value=1.0)
    return dict(n01=n01, n10=n10,
                p_value=round(float(stats.binomtest(n10, n01 + n10, 0.5).pvalue), 4))


def tune_on_validation(d_train, d_val, target, shift, seeded=(False, True),
                       state_names=None, verbose=False):
    """Eighteen configurations, decided on the validation window alone.

    Scoring function x maximum in-degree x expert seeding. Sorted by validation
    accuracy, ties broken towards the sparser graph.
    """
    grid = []
    for scoring in SCORES:
        for indeg in INDEGREES:
            for seed_expert in seeded:
                start = expert_dag(list(d_train.columns)) if seed_expert else None
                try:
                    m = learn_structure(d_train, scoring, indeg, start)
                    m = fit_parameters(m, d_train, state_names)
                    s = score_forecast(d_val[target].values,
                                       predict_regimes(m, d_val, target), shift)
                except Exception as exc:            # pragma: no cover
                    if verbose:
                        print(f"   [skipped] {scoring}/{indeg}/{seed_expert}: {exc}")
                    continue
                grid.append(dict(scoring=scoring, max_indegree=indeg,
                                 expert_seeded=seed_expert, n_edges=len(m.edges()),
                                 val_accuracy=s["accuracy"], val_error=s["error"],
                                 model=m))
    grid.sort(key=lambda r: (-r["val_accuracy"], r["n_edges"]))
    return grid


# ---------------------------------------------------------------------------
# The two experimental frames
# ---------------------------------------------------------------------------

def frame_A(discrete: pd.DataFrame) -> pd.DataFrame:
    """Replication frame: ``forecast`` duplicates the current target regime."""
    f = discrete[SERIES].copy()
    f["forecast"] = f[TARGET].values
    return f.astype(int)


def frame_B(discrete: pd.DataFrame) -> pd.DataFrame:
    """Improved frame: ``forecast`` is the target regime one month ahead."""
    f = discrete[SERIES].copy()
    f["forecast"] = discrete[TARGET].shift(-1)
    return f.dropna().astype(int)


def benchmarks(y_true, y_train_forecast, persistence, seed=42) -> dict:
    """The three reference rules of GWP3 Table 11, on the same months."""
    y_true = np.asarray(y_true)
    maj = int(pd.Series(y_train_forecast).mode()[0])
    rng = np.random.default_rng(seed)
    return dict(uninformed=round(100 * float(np.mean(
                    y_true == rng.integers(0, 3, len(y_true)))), 2),
                majority=round(100 * float(np.mean(y_true == maj)), 2),
                persistence=round(100 * float(np.mean(
                    y_true == np.asarray(persistence))), 2),
                majority_state=maj)
