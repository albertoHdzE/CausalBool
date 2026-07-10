"""pattern_dynamics.py  (Level 2)

A separate, more advanced level of the framework that treats the whole binarised
pattern as a single multidimensional unit, rather than as independent per-node
bits (Level 1).  The dynamics are a single map from the complete pattern at time
t to the complete pattern at time t+1, computed in one step - the "multi-tape"
or "multidimensional node" view.

This level does not touch the foundational Level 1 code (src/).  It is meant to
be compared against it: Level 1 factorises the transition into one Boolean
function per node (a product structure that compresses when the system is
structured); Level 2 keeps the vector whole and models the joint transition.

The point of the experiments is honest evaluation, not advocacy: for a
deterministic low-entropy system (a cellular automaton) the whole-pattern map is
exact, because patterns recur; for a market it fails, because the pattern space
is astronomically sparse and patterns essentially never recur.
"""

from __future__ import annotations

from collections import Counter


def _key(state):
    return tuple(state)


def whole_pattern_lookup(train_states):
    """Learn a map pattern_t -> most common pattern_{t+1} from a trajectory."""
    succ = {}
    for t in range(len(train_states) - 1):
        succ.setdefault(_key(train_states[t]), Counter())[_key(train_states[t + 1])] += 1
    return {p: c.most_common(1)[0][0] for p, c in succ.items()}


def evaluate_lookup(states, split):
    """Out-of-sample whole-pattern lookup.

    Returns exact-next-pattern match rate, per-bit accuracy, and the coverage
    (fraction of test patterns that were seen in training).  Unseen patterns fall
    back to predicting the pattern unchanged (persistence).
    """
    n = len(states[0])
    train, test = states[:split], states[split:]
    model = whole_pattern_lookup(train)
    exact = 0
    bit_correct = 0
    bit_total = 0
    seen = 0
    steps = 0
    for t in range(len(test) - 1):
        cur, nxt = _key(test[t]), test[t + 1]
        pred = model.get(cur, cur)  # persistence fallback if unseen
        if cur in model:
            seen += 1
        if list(pred) == nxt:
            exact += 1
        bit_correct += sum(1 for j in range(n) if pred[j] == nxt[j])
        bit_total += n
        steps += 1
    return {
        "exact_pattern_rate": exact / steps if steps else 0.0,
        "per_bit_accuracy": bit_correct / bit_total if bit_total else 0.0,
        "coverage_test_seen_in_train": seen / steps if steps else 0.0,
        "steps": steps,
    }


def evaluate_nearest_neighbour(states, split):
    """Predict the next pattern from the training pattern most similar (min
    Hamming distance) to the current one.  Generalises to unseen patterns."""
    n = len(states[0])
    train, test = states[:split], states[split:]
    pairs = [(train[t], train[t + 1]) for t in range(len(train) - 1)]
    bit_correct = 0
    bit_total = 0
    exact = 0
    steps = 0
    for t in range(len(test) - 1):
        cur, nxt = test[t], test[t + 1]
        best = min(pairs, key=lambda pr: sum(1 for j in range(n) if pr[0][j] != cur[j]))
        pred = best[1]
        if pred == nxt:
            exact += 1
        bit_correct += sum(1 for j in range(n) if pred[j] == nxt[j])
        bit_total += n
        steps += 1
    return {
        "exact_pattern_rate": exact / steps if steps else 0.0,
        "per_bit_accuracy": bit_correct / bit_total if bit_total else 0.0,
        "steps": steps,
    }


def base_rate_per_bit(states, split):
    """Per-bit accuracy of predicting each bit's more common test value."""
    n = len(states[0])
    test = states[split:]
    acc = 0.0
    for j in range(n):
        ones = sum(test[t + 1][j] for t in range(len(test) - 1))
        tot = len(test) - 1
        acc += max(ones, tot - ones) / tot
    return acc / n
