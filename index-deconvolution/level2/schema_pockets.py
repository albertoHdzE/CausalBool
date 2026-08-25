"""schema_pockets.py  (Level 2)

Search for a deterministic backbone in a binarised time series: a set of schemata
(pivots) that predict a target bit with high purity, found on training data and
validated out of sample.  The days a schema fires are the pivots; the uncovered
days are the residual (the sumandos of this level), on which the search can
recurse.

The essential safeguard against the tautology of "select the matching points and
declare victory" is a strict train/test split (schemata are committed on training
and only then applied to unseen test days) and a time-shuffle control (the same
search on data with the temporal structure destroyed), which measures how much
apparent determinism appears by chance and multiple testing.
"""

from __future__ import annotations

from itertools import combinations, product


def find_pockets(train_states, target, max_support, min_count, min_purity):
    """Schemata over the lag-1 pattern that predict ``target`` with high purity.

    Returns a list of (support, values, prediction, purity, count) committed on
    the training data only.
    """
    n = len(train_states[0])
    pairs = [(train_states[t], train_states[t + 1][target])
             for t in range(len(train_states) - 1)]
    pockets = []
    for k in range(1, max_support + 1):
        for support in combinations(range(n), k):
            for values in product((0, 1), repeat=k):
                fires = [o for s, o in pairs
                         if all(s[support[j]] == values[j] for j in range(k))]
                cnt = len(fires)
                if cnt >= min_count:
                    ones = sum(fires)
                    pred = 1 if ones >= cnt - ones else 0
                    purity = max(ones, cnt - ones) / cnt
                    if purity >= min_purity:
                        pockets.append((support, values, pred, purity, cnt))
    return pockets


def evaluate_pockets(test_states, target, pockets):
    """Out-of-sample coverage and accuracy on the days some pocket fires."""
    total = len(test_states) - 1
    covered = 0
    correct = 0
    for t in range(total):
        s, nxt = test_states[t], test_states[t + 1][target]
        firing = [p for p in pockets
                  if all(s[p[0][j]] == p[1][j] for j in range(len(p[0])))]
        if firing:
            covered += 1
            votes = sum((1 if p[2] == 1 else -1) * p[4] for p in firing)
            pred = 1 if votes >= 0 else 0
            if pred == nxt:
                correct += 1
    return {"coverage": covered / total if total else 0.0,
            "accuracy_on_covered": correct / covered if covered else 0.0,
            "covered": covered, "total": total}
