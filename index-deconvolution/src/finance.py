"""finance.py

Binarise real daily price series and test whether their one-step dynamics admit
a deterministic Boolean-network explanation, using the same deconvolution logic
as the rest of the project (functional-support inference from observed
transitions).

The analysis is deliberately guarded against the overfitting trap: with many
predictors every observed pattern becomes unique and any next value is trivially
"reproduced", which is memorisation, not a causal law.  We therefore measure

  * the contradiction rate among predictor patterns that recur (the intrinsic
    non-determinism, free of overfitting), and
  * the best predictive accuracy of a small functional support, compared with
    the base rate,

so that a genuinely deterministic system (a cellular automaton, a gene-regulatory
network) is separated from a stochastic one (a market).

Standard library only; no third-party dependencies.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from itertools import combinations


# ---------------------------------------------------------------------------
# Loading and binarisation of real price data (Yahoo v8 chart JSON)
# ---------------------------------------------------------------------------

def load_yahoo_close(path: str) -> dict[str, float]:
    """Return a date-string -> close-price mapping from a Yahoo chart JSON file."""
    with open(path) as f:
        d = json.load(f)
    r = d["chart"]["result"][0]
    ts = r["timestamp"]
    close = r["indicators"]["quote"][0]["close"]
    out: dict[str, float] = {}
    for t, c in zip(ts, close):
        if c is None:
            continue
        day = datetime.fromtimestamp(t, tz=timezone.utc).strftime("%Y-%m-%d")
        out[day] = float(c)
    return out


def align_prices(paths: dict[str, str]) -> tuple[list[str], list[str], list[list[float]]]:
    """Align several tickers on their common trading days.

    Returns (tickers, dates, matrix) where matrix[t][j] is the close of ticker j
    on date t, over the sorted intersection of available dates.
    """
    tickers = list(paths)
    series = {tk: load_yahoo_close(p) for tk, p in paths.items()}
    common = set.intersection(*(set(s) for s in series.values()))
    dates = sorted(common)
    matrix = [[series[tk][day] for tk in tickers] for day in dates]
    return tickers, dates, matrix


def to_binary_states(matrix: list[list[float]]) -> list[list[int]]:
    """Binarise by the sign of the daily change: 1 if up, 0 otherwise.

    Returns a list of binary state vectors, one per day from the second onward.
    """
    states = []
    for t in range(1, len(matrix)):
        states.append([1 if matrix[t][j] > matrix[t - 1][j] else 0
                       for j in range(len(matrix[t]))])
    return states


# ---------------------------------------------------------------------------
# Determinism analysis of a binary state sequence
# ---------------------------------------------------------------------------

def _pattern(state: list[int], support: tuple[int, ...]) -> int:
    y = 0
    for j, c in enumerate(support):
        if state[c]:
            y |= (1 << j)
    return y


def contradiction_rate(states: list[list[int]], node: int,
                       support: tuple[int, ...]) -> tuple[float, int]:
    """Fraction of recurring predictor patterns that map to both outputs.

    Only patterns that occur at least twice are counted, so the measure reflects
    intrinsic non-determinism rather than the uniqueness of rare patterns.
    Returns (contradiction_rate, num_recurring_patterns).
    """
    outs: dict[int, list[int]] = {}
    for t in range(len(states) - 1):
        p = _pattern(states[t], support)
        outs.setdefault(p, []).append(states[t + 1][node])
    recurring = {p: v for p, v in outs.items() if len(v) >= 2}
    if not recurring:
        return 0.0, 0
    contradictory = sum(1 for v in recurring.values() if 0 in v and 1 in v)
    return contradictory / len(recurring), len(recurring)


def best_support_accuracy(states: list[list[int]], node: int,
                          n_nodes: int, max_k: int) -> tuple[float, tuple[int, ...]]:
    """Best in-sample accuracy of a deterministic function of a small support.

    For each support of size up to ``max_k`` the optimal deterministic Boolean
    function is the conditional majority per predictor pattern; its accuracy is
    the fraction of transitions it predicts correctly.  Returns the best accuracy
    and the support achieving it.
    """
    best_acc = 0.0
    best_support: tuple[int, ...] = ()
    total = len(states) - 1
    for k in range(1, max_k + 1):
        for support in combinations(range(n_nodes), k):
            counts: dict[int, list[int]] = {}
            for t in range(total):
                p = _pattern(states[t], support)
                counts.setdefault(p, [0, 0])[states[t + 1][node]] += 1
            correct = sum(max(c0, c1) for c0, c1 in counts.values())
            acc = correct / total
            if acc > best_acc:
                best_acc = acc
                best_support = support
    return best_acc, best_support


def base_rate(states: list[list[int]], node: int) -> float:
    """Accuracy of always predicting the more common next value of ``node``."""
    # Extract all values for the selected node across all consecutive state pairs
    node_values = [states[t + 1][node] for t in range(len(states) - 1)]
    # Count number of 1s in the extracted values
    ones = sum(node_values)
    # Calculate total number of observations
    total = len(node_values)
    # Calculate number of 0s
    zeros = total - ones
    # Print count summary for verification
    # print(f"Selected node: {node}, Number of 1s: {ones}, Number of 0s: {zeros}")
    # Return the ratio of the majority class (base prediction accuracy)
    return max(ones, zeros) / total


def daily_returns(matrix: list[list[float]]) -> list[list[float]]:
    """Simple daily returns; row t is the return from day t to day t+1."""
    return [[(matrix[t][j] - matrix[t - 1][j]) / matrix[t - 1][j]
             for j in range(len(matrix[t]))]
            for t in range(1, len(matrix))]


def sign_states(returns: list[list[float]]) -> list[list[int]]:
    """Binary up/down states from returns."""
    return [[1 if r > 0 else 0 for r in row] for row in returns]


def event_states(returns: list[list[float]], quantile: float = 0.70
                 ) -> tuple[list[int], list[list[int]]]:
    """Restrict to disruptive market days and binarise by sign there.

    A day is disruptive if its cross-sectional mean absolute return is above the
    given quantile of all days.  Returns (event_day_indices, sign_states_on_events)
    in chronological order, implementing the idea of keeping the key datapoints
    and discarding the quiet moves between them.
    """
    vol = [sum(abs(r) for r in row) / len(row) for row in returns]
    order = sorted(vol)
    thr = order[int(quantile * len(order))]
    idx = [t for t in range(len(returns)) if vol[t] >= thr]
    states = [[1 if returns[t][j] > 0 else 0 for j in range(len(returns[t]))]
              for t in idx]
    return idx, states


def fit_predictor(states: list[list[int]], node: int, n_nodes: int, max_k: int
                  ) -> tuple[tuple[int, ...], dict[int, int]]:
    """Best small-support lag-1 predictor: support plus conditional-majority map."""
    _, support = best_support_accuracy(states, node, n_nodes, max_k)
    counts: dict[int, list[int]] = {}
    for t in range(len(states) - 1):
        p = _pattern(states[t], support)
        counts.setdefault(p, [0, 0])[states[t + 1][node]] += 1
    func = {p: (1 if c1 >= c0 else 0) for p, (c0, c1) in counts.items()}
    return support, func


def directional_path(returns: list[list[float]], states: list[list[int]],
                     node: int, support: tuple[int, ...], func: dict[int, int]
                     ) -> dict:
    """Compare a real cumulative-return path with a model-directed one.

    The model predicts the sign of each next move from the previous state; the
    directed path keeps the real magnitude but the predicted sign, isolating
    directional skill.  Returns the two paths and directional statistics.
    """
    real_cum = [0.0]
    pred_cum = [0.0]
    correct = 0
    total = 0
    for t in range(len(states) - 1):
        real_r = returns[t + 1][node]
        p = _pattern(states[t], support)
        pred_sign = 1 if func.get(p, 1) == 1 else -1
        real_cum.append(real_cum[-1] + real_r)
        pred_cum.append(pred_cum[-1] + pred_sign * abs(real_r))
        if (pred_sign > 0) == (real_r > 0):
            correct += 1
        total += 1
    return {
        "real_cum": real_cum, "pred_cum": pred_cum,
        "directional_accuracy": correct / total if total else 0.0,
        "n_steps": total,
    }


def evaluate_out_of_sample(train: list[list[int]], test: list[list[int]],
                           returns_test: list[list[float]], node: int,
                           n_nodes: int, max_k: int) -> dict:
    """Fit the directional model on ``train`` and evaluate it on ``test``.

    Returns the out-of-sample directional accuracy and the real and model-directed
    cumulative paths on the test period.  Out-of-sample evaluation removes the
    look-ahead bias that inflates in-sample fit, and is the honest test of
    whether the market carries exploitable deterministic structure.
    """
    support, func = fit_predictor(train, node, n_nodes, max_k)
    real_cum = [0.0]
    pred_cum = [0.0]
    correct = 0
    total = 0
    for t in range(len(test) - 1):
        p = _pattern(test[t], support)
        pred_sign = 1 if func.get(p, 1) == 1 else -1
        rr = returns_test[t + 1][node]
        real_cum.append(real_cum[-1] + rr)
        pred_cum.append(pred_cum[-1] + pred_sign * abs(rr))
        if (pred_sign > 0) == (test[t + 1][node] > 0):
            correct += 1
        total += 1
    return {"support": list(support),
            "oos_accuracy": correct / total if total else 0.0,
            "real_cum": real_cum, "pred_cum": pred_cum, "n_steps": total}


def analyse(states: list[list[int]], max_k: int = 2) -> dict:
    """Determinism summary for a binary state sequence."""
    n = len(states[0])
    full = tuple(range(n))
    per_node = []
    for i in range(n):
        cr, nrec = contradiction_rate(states, i, full)
        acc, sup = best_support_accuracy(states, i, n, max_k)
        br = base_rate(states, i)
        per_node.append({
            "node": i, "contradiction_rate_full": cr,
            "recurring_patterns": nrec,
            "best_small_support": list(sup), "best_accuracy": acc,
            "base_rate": br, "lift_over_base": acc - br,
        })
    exact_nodes = sum(1 for p in per_node if p["best_accuracy"] >= 0.999)
    return {
        "n_nodes": n, "n_transitions": len(states) - 1,
        "mean_contradiction_rate": sum(p["contradiction_rate_full"] for p in per_node) / n,
        "mean_best_accuracy": sum(p["best_accuracy"] for p in per_node) / n,
        "mean_base_rate": sum(p["base_rate"] for p in per_node) / n,
        "mean_lift_over_base": sum(p["lift_over_base"] for p in per_node) / n,
        "exact_nodes": exact_nodes,
        "per_node": per_node,
    }
