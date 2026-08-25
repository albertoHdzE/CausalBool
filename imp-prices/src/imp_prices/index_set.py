"""Index-set encoding of a node, and its description length in bits.

This is ledger entry B4: does the index-set representation describe the same
conditional relationship in fewer bits than a conditional probability table?

**Why the comparison has to be two-part.** Comparing model sizes alone is
meaningless — a model of zero bits that predicts nothing would win. The quantity
compared here is the total cost of transmitting the successor column to a
receiver who already holds the evidence columns:

    L_total = L(model) + L(data | model)

Both models are encoding exactly the same object: the target's regime at *t+1*
given the regimes at *t*. A smaller model that fits worse pays for it in the
second term. This is the standard minimum-description-length comparison and it
is the only version of B4 that cannot be won by choosing a flattering encoding.

**The two encodings.**

*Index-set model.* A parent set *C* and a map from each realised parent pattern
to a successor symbol — the multi-valued generalisation of a gate's one-set. The
map is deterministic, so it needs a residual code for the months it gets wrong.

*Conditional probability table.* The same parent set, with a probability
distribution over successor symbols for each realised pattern, estimated under
the K2 prior GWP3 uses. Its free parameters are transmitted at Rissanen's optimal
precision of ½log₂N bits each, which is the precision the Bayesian information
criterion assumes.

**Every code below is self-delimiting**, and the accounting is written out term by
term so a reader can check it rather than take it on trust. The marginal model —
no parents at all — is included as the baseline that both must beat before either
is worth discussing.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from itertools import combinations

import numpy as np
import pandas as pd

from .feasibility import build_design, encode


def log2(x: float) -> float:
    return math.log2(x)


def log2_binom(n: int, k: int) -> float:
    """log2 of the binomial coefficient, computed via lgamma for large n."""
    if k < 0 or k > n:
        return math.inf
    return (math.lgamma(n + 1) - math.lgamma(k + 1) - math.lgamma(n - k + 1)) / math.log(2)


def elias_gamma_bits(n: int) -> float:
    """Self-delimiting code length for a non-negative integer.

    Used wherever a count must be transmitted before the thing it counts. Elias
    gamma costs 2⌊log₂(n+1)⌋+1 bits, so the length itself is decodable without a
    separate agreement on field width.
    """
    return 2 * math.floor(log2(n + 1)) + 1


def structure_bits(n_candidates: int, n_parents: int, max_indegree: int) -> float:
    """Cost of naming a parent set.

    Two terms: the size of the set, over a known finite range, and which subset
    of that size. Identical for both encodings, so it cancels in any comparison
    at equal in-degree and is included only so that each total is a genuine
    code length rather than a difference.
    """
    return log2(max_indegree + 1) + log2_binom(n_candidates, n_parents)


def residual_bits(n: int, n_errors: int, alphabet: int) -> float:
    """Cost of correcting a deterministic map's mistakes.

    Three terms: how many errors there are, which observations they fall on, and
    what the true symbol was in each case. The middle term is the combinatorial
    code log₂C(N,e), which is the shortest code for an unordered set of positions
    and needs no assumption about how errors are distributed.
    """
    if n_errors == 0:
        return elias_gamma_bits(0)
    return (elias_gamma_bits(n_errors)
            + log2_binom(n, n_errors)
            + n_errors * log2(alphabet - 1))


@dataclass
class CodeLength:
    """A two-part code length, kept in its parts so it can be audited."""

    model: str
    parents: tuple[str, ...]
    n: int
    n_patterns: int
    structure: float
    parameters: float
    data: float
    extra: dict = field(default_factory=dict)

    @property
    def model_bits(self) -> float:
        return self.structure + self.parameters

    @property
    def total(self) -> float:
        return self.structure + self.parameters + self.data

    def as_dict(self) -> dict:
        d = dict(model=self.model, parents="+".join(self.parents) or "(none)",
                 k=len(self.parents), n_patterns=self.n_patterns,
                 structure_bits=round(self.structure, 2),
                 parameter_bits=round(self.parameters, 2),
                 data_bits=round(self.data, 2),
                 model_bits=round(self.model_bits, 2),
                 total_bits=round(self.total, 2),
                 bits_per_observation=round(self.total / self.n, 4))
        d.update({k: (round(v, 4) if isinstance(v, float) else v)
                  for k, v in self.extra.items()})
        return d


def _pattern_table(X: np.ndarray, y: np.ndarray, alphabet: int):
    """Counts of successor symbol per realised parent pattern."""
    if X.shape[1] == 0:
        codes = np.zeros(len(y), dtype=np.int64)
    else:
        codes = encode(X, alphabet)
    uniq, inv = np.unique(codes, return_inverse=True)
    counts = np.zeros((len(uniq), alphabet), dtype=np.int64)
    np.add.at(counts, (inv, y), 1)
    return counts


def index_set_code(X: np.ndarray, y: np.ndarray, parents, n_candidates: int,
                   max_indegree: int, alphabet: int = 3) -> CodeLength:
    """Parent set, deterministic map, and a residual code for its errors.

    The map assigns each realised pattern the symbol that occurs most often under
    it. Only *realised* patterns are transmitted: the receiver already holds the
    evidence columns and can therefore enumerate the patterns that occur, so
    spending bits on unrealised ones would be double counting. The conditional
    probability table below is given exactly the same allowance.
    """
    counts = _pattern_table(X, y, alphabet)
    n_patterns = len(counts)
    n_errors = int(counts.sum() - counts.max(axis=1).sum())
    return CodeLength(
        model="index-set",
        parents=tuple(parents),
        n=len(y),
        n_patterns=n_patterns,
        structure=structure_bits(n_candidates, len(parents), max_indegree),
        parameters=n_patterns * log2(alphabet),      # one symbol per pattern
        data=residual_bits(len(y), n_errors, alphabet),
        extra=dict(n_errors=n_errors,
                   map_accuracy=float(counts.max(axis=1).sum() / counts.sum())),
    )


def cpt_code(X: np.ndarray, y: np.ndarray, parents, n_candidates: int,
             max_indegree: int, alphabet: int = 3, prior: float = 1.0) -> CodeLength:
    """Parent set, conditional probability table, and the negative log likelihood.

    Parameters are transmitted at Rissanen's optimal precision, ½log₂N bits per
    free parameter, which is the precision the Bayesian information criterion
    assumes and the most favourable defensible choice for this side. Each
    realised pattern carries ``alphabet − 1`` free parameters.

    ``prior = 1.0`` is the K2 prior of Cooper and Herskovits, which is the
    estimator GWP3 uses; it also guarantees a finite code length, where maximum
    likelihood would assign zero probability to an unobserved but possible
    configuration and cost infinitely many bits.
    """
    counts = _pattern_table(X, y, alphabet)
    n_patterns = len(counts)
    probs = (counts + prior) / (counts + prior).sum(axis=1, keepdims=True)
    data_bits = float(-(counts * np.log2(probs)).sum())
    free = n_patterns * (alphabet - 1)
    return CodeLength(
        model="cpt",
        parents=tuple(parents),
        n=len(y),
        n_patterns=n_patterns,
        structure=structure_bits(n_candidates, len(parents), max_indegree),
        parameters=free * 0.5 * log2(len(y)),
        data=data_bits,
        extra=dict(n_free_parameters=free),
    )


def marginal_code(y: np.ndarray, n_candidates: int, max_indegree: int,
                  alphabet: int = 3, prior: float = 1.0) -> CodeLength:
    """No parents: the baseline both models must beat to be worth discussing."""
    return cpt_code(np.zeros((len(y), 0), dtype=np.int64), y, (), n_candidates,
                    max_indegree, alphabet, prior)


def scan_codes(frame: pd.DataFrame, target: str, columns: list[str],
               max_indegree: int = 3, alphabet: int = 3) -> pd.DataFrame:
    """Both encodings, over every parent set up to ``max_indegree``."""
    X, y = build_design(frame, target, columns)
    idx = {c: j for j, c in enumerate(columns)}
    rows = [marginal_code(y, len(columns), max_indegree, alphabet).as_dict()]
    for k in range(1, max_indegree + 1):
        for parents in combinations(columns, k):
            cols = [idx[p] for p in parents]
            for fn in (index_set_code, cpt_code):
                rows.append(fn(X[:, cols], y, parents, len(columns),
                               max_indegree, alphabet).as_dict())
    return pd.DataFrame(rows)


def best_by_total(table: pd.DataFrame, model: str) -> pd.Series:
    sub = table[table["model"] == model]
    return sub.loc[sub["total_bits"].idxmin()]


# ---------------------------------------------------------------------------
# Prequential code length: the same comparison without a precision convention
# ---------------------------------------------------------------------------

def prequential_bits(frame: pd.DataFrame, target: str, parents: list[str],
                     model: str, alphabet: int = 3, prior: float = 1.0,
                     burn_in: int = 12) -> dict:
    """Encode the successor column one symbol at a time, using only the past.

    The two-part codes above require a convention for parameter precision, and a
    reader is entitled to ask whether the conclusion turns on that convention.
    The prequential code length needs no such convention: at each step the model
    is refitted on the prefix and the next symbol costs −log₂ of the probability
    that model assigns it. Parameter cost is paid implicitly, through the poorer
    predictions an over-parameterised model makes early on.

    ``model="index-set"`` treats the deterministic map as a probability model:
    the predicted symbol receives 1 − ε and the others ε/(a−1), with ε estimated
    from the prefix under the same Laplace prior. Without that the map would
    assign probability zero to its own errors and the code length would diverge.
    """
    X, y = build_design(frame, target, parents) if parents else (
        np.zeros((len(frame) - 1, 0), dtype=np.int64),
        frame[target].to_numpy(np.int64)[1:])

    total = 0.0
    scored = 0
    for t in range(burn_in, len(y)):
        past_X, past_y, x_now = X[:t], y[:t], X[t:t + 1]
        counts = _pattern_table(past_X, past_y, alphabet)
        if past_X.shape[1] == 0:
            row = counts[0]
            probs = (row + prior) / (row + prior).sum()
        else:
            past_codes = encode(past_X, alphabet)
            uniq = np.unique(past_codes)
            now = encode(x_now, alphabet)[0]
            hit = np.where(uniq == now)[0]
            row = counts[hit[0]] if len(hit) else np.zeros(alphabet, dtype=np.int64)
            probs = (row + prior) / (row + prior).sum()

        if model == "index-set":
            # Collapse to a deterministic prediction plus a prefix-estimated
            # error rate, so that the map is scored as the map it is.
            pred = int(np.argmax(row)) if row.sum() else int(np.argmax(counts.sum(axis=0)))
            errs = int(counts.sum() - counts.max(axis=1).sum())
            eps = (errs + prior) / (counts.sum() + prior * alphabet)
            probs = np.full(alphabet, eps / (alphabet - 1))
            probs[pred] = 1.0 - eps
        total += -log2(float(probs[y[t]]))
        scored += 1

    return dict(model=model, parents="+".join(parents) or "(none)",
                prequential_bits=round(total, 2), n_scored=scored,
                bits_per_observation=round(total / scored, 4))


# ---------------------------------------------------------------------------
# Stability of the selected parent set (the index-set half of B5)
# ---------------------------------------------------------------------------

def block_bootstrap_indices(n: int, block: int, rng) -> np.ndarray:
    """Moving-block resample indices.

    Resampling is by blocks, not by individual months. An independent bootstrap
    of a serially dependent series destroys the persistence that dominates this
    target, and would make any selection look far more stable than it is. The
    block length used throughout is one year.
    """
    n_blocks = int(np.ceil(n / block))
    starts = rng.integers(0, n - block + 1, size=n_blocks)
    return np.concatenate([np.arange(s, s + block) for s in starts])[:n]


def bootstrap_parent_sets(frame: pd.DataFrame, target: str, columns: list[str],
                          max_indegree: int = 3, alphabet: int = 3,
                          n_boot: int = 500, seed: int = 42,
                          block: int = 12, scorer: str = "index-set") -> dict:
    """How often does each parent set win, under resampling?

    ``scorer`` selects the code length that decides the winner: ``"index-set"``
    or ``"cpt"``. Running both over the *identical* resamples is what makes the
    stability comparison like for like — same candidate space, same data, only
    the encoding differs. Comparing our bootstrap against the belief network's
    hash-seed sweep would compare two different questions.
    """
    code_fn = {"index-set": index_set_code, "cpt": cpt_code}[scorer]
    X, y = build_design(frame, target, columns)
    idx = {c: j for j, c in enumerate(columns)}
    candidates = [(parents, [idx[p] for p in parents])
                  for k in range(1, max_indegree + 1)
                  for parents in combinations(columns, k)]

    rng = np.random.default_rng(seed)
    wins: dict[tuple, int] = {}
    for _ in range(n_boot):
        take = block_bootstrap_indices(len(y), block, rng)
        Xb, yb = X[take], y[take]
        best, best_bits = None, math.inf
        for parents, cols in candidates:
            c = code_fn(Xb[:, cols], yb, parents, len(columns), max_indegree, alphabet)
            if c.total < best_bits:
                best, best_bits = parents, c.total
        wins[best] = wins.get(best, 0) + 1

    ranked = sorted(wins.items(), key=lambda kv: -kv[1])
    return dict(scorer=scorer, n_boot=n_boot, block=block,
                n_distinct_winners=len(wins),
                top=[dict(parents="+".join(p), frequency=round(c / n_boot, 4))
                     for p, c in ranked[:8]],
                modal_frequency=round(ranked[0][1] / n_boot, 4),
                modal_parents="+".join(ranked[0][0]))
