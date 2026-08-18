"""Gate 1.0 — does the discretised panel contain deterministic structure at all?

This is the feasibility test of ``PROTOCOL_causal_timeseries.md`` section 2, and
it is pre-registered: if it fails, Phase 1 terminates and the outcome is reported
as a measured negative rather than modelled around.

The quantity is Level 1's **contradiction rate**: over input patterns observed
more than once, the fraction that map to more than one successor. A deterministic
system has contradiction zero. There are two traps in applying it here, and both
are handled explicitly.

**Trap 1 — vacuous determinism.** With seven ternary variables the input space
has 3^7 = 2187 states and the training window supplies 138 observations. Measured
on the full pattern, the contradiction rate is near zero because almost nothing
recurs. That is absence of data, not evidence of structure. Every statistic here
is therefore reported with its *recurrence* — the fraction of observations whose
pattern is seen more than once — and a contradiction rate computed on a handful
of recurring patterns is not interpretable however low it is.

**Trap 2 — selection over parent sets.** The method searches parent sets, so the
reported statistic is a minimum over many candidates and is biased downwards by
that search. Protocol rule R5 requires the bias to be counted rather than
assumed small. The null is therefore *best-of-search under a time-order shuffle*:
the identical search, over the identical candidates, on data whose successor
column has been permuted. Comparing a searched statistic against an unsearched
null is the artefact that Level 2 caught and reported as such.
"""

from __future__ import annotations

from dataclasses import dataclass
from itertools import combinations

import numpy as np
import pandas as pd


@dataclass(frozen=True)
class PatternStats:
    """Determinism statistics for one candidate parent set."""

    parents: tuple[str, ...]
    n: int                      #: observations used
    n_patterns: int             #: distinct input patterns realised
    n_recurring: int            #: patterns realised more than once
    recurrence: float           #: fraction of observations in a recurring pattern
    contradiction: float        #: fraction of recurring patterns with >1 successor
    lookup_accuracy: float      #: in-sample accuracy of the majority-vote table

    def as_dict(self) -> dict:
        return dict(parents="+".join(self.parents), k=len(self.parents), n=self.n,
                    n_patterns=self.n_patterns, n_recurring=self.n_recurring,
                    recurrence=round(self.recurrence, 4),
                    contradiction=round(self.contradiction, 4),
                    lookup_accuracy=round(self.lookup_accuracy, 4))


def encode(X: np.ndarray, n_values: int) -> np.ndarray:
    """Mixed-radix encoding of each row of ``X`` into a single integer."""
    codes = np.zeros(len(X), dtype=np.int64)
    for j in range(X.shape[1]):
        codes = codes * n_values + X[:, j]
    return codes


def _table(codes: np.ndarray, y: np.ndarray, n_codes: int, n_values: int) -> np.ndarray:
    """Contingency counts, pattern by successor value."""
    flat = np.bincount(codes * n_values + y, minlength=n_codes * n_values)
    return flat.reshape(n_codes, n_values)


def pattern_stats(X: np.ndarray, y: np.ndarray, parents: tuple[str, ...],
                  n_values: int = 3) -> PatternStats:
    """Determinism statistics of the map ``X -> y``.

    ``lookup_accuracy`` is the in-sample accuracy of the best lookup table on
    these patterns: predict, for each pattern, its most frequent successor. It is
    an optimistic quantity by construction — with enough patterns it reaches one
    — which is precisely why it is only ever read against the shuffle null.
    """
    n_codes = n_values ** X.shape[1]
    codes = encode(X, n_values)
    counts = _table(codes, y, n_codes, n_values)
    per_pattern = counts.sum(axis=1)

    realised = per_pattern > 0
    recurring = per_pattern > 1
    n_rec = int(recurring.sum())

    if n_rec:
        distinct_successors = (counts[recurring] > 0).sum(axis=1)
        contradiction = float((distinct_successors > 1).mean())
    else:
        contradiction = float("nan")

    return PatternStats(
        parents=parents,
        n=int(len(y)),
        n_patterns=int(realised.sum()),
        n_recurring=n_rec,
        recurrence=float(per_pattern[recurring].sum() / len(y)) if n_rec else 0.0,
        contradiction=contradiction,
        lookup_accuracy=float(counts.max(axis=1).sum() / len(y)),
    )


def build_design(frame: pd.DataFrame, target: str, columns: list[str]):
    """Evidence at month *t*, successor at month *t + 1*.

    The successor is the target one month ahead, which is the "improved model"
    target of GWP3 section 6 — the network is asked to forecast rather than to
    reconstruct. Strict causality (rule R1) is structural here: the evidence row
    is strictly earlier than the label it carries.
    """
    X = frame[columns].to_numpy(dtype=np.int64)[:-1]
    y = frame[target].to_numpy(dtype=np.int64)[1:]
    return X, y


def scan(frame: pd.DataFrame, target: str, columns: list[str],
         max_indegree: int = 3, n_values: int = 3) -> pd.DataFrame:
    """Every parent set up to ``max_indegree``, with its determinism statistics."""
    X, y = build_design(frame, target, columns)
    idx = {c: j for j, c in enumerate(columns)}
    rows = []
    for k in range(1, max_indegree + 1):
        for parents in combinations(columns, k):
            cols = [idx[p] for p in parents]
            rows.append(pattern_stats(X[:, cols], y, parents, n_values).as_dict())
    return pd.DataFrame(rows)


def best_of_search(frame: pd.DataFrame, target: str, columns: list[str],
                   max_indegree: int, n_values: int,
                   min_recurrence: float) -> tuple[float, float]:
    """The searched statistics: best contradiction and best lookup accuracy.

    Candidates whose recurrence falls below ``min_recurrence`` are excluded, so
    that the search cannot win by finding a parent set nothing recurs under
    (trap 1). The exclusion is applied identically to the real data and to every
    shuffle, so it cannot bias the comparison.
    """
    tab = scan(frame, target, columns, max_indegree, n_values)
    ok = tab[tab["recurrence"] >= min_recurrence]
    if ok.empty:
        return float("nan"), float("nan")
    return float(ok["contradiction"].min()), float(ok["lookup_accuracy"].max())


def circular_shift_null(frame: pd.DataFrame, target: str, columns: list[str],
                        max_indegree: int = 3, n_values: int = 3,
                        min_recurrence: float = 0.5, min_gap: int = 6) -> dict:
    """Best-of-search against surrogates that preserve the target's own dynamics.

    **This is the primary null, and the reason is a defect found in the weaker
    one.** A random permutation of the successor column destroys not only its
    relation to the evidence but also its autocorrelation. Two persistent yet
    wholly independent processes align spuriously over a finite sample — the
    categorical analogue of spurious regression — and a permutation null cannot
    reproduce that, so it certifies the alignment as structure. Run on
    ``controls.persistent_random_frame``, which contains no cross-variable
    structure by construction, the permutation null returned p = 0.0196.

    The circular shift rotates the successor column against the evidence. It
    preserves the successor's marginal, its autocorrelation, its run-length
    distribution and its regime clustering *exactly*, and destroys only the
    alignment. Shifts within ``min_gap`` of either end are excluded because they
    leave the alignment largely intact.

    The surrogate set is enumerated exhaustively rather than sampled, so the
    result is deterministic and carries no seed. The attainable p-value is
    bounded below by 1 / (number of surrogates + 1).
    """
    obs_contra, obs_acc = best_of_search(frame, target, columns, max_indegree,
                                         n_values, min_recurrence)

    X, y = build_design(frame, target, columns)
    idx = {c: j for j, c in enumerate(columns)}
    candidates = [tuple(idx[p] for p in parents)
                  for k in range(1, max_indegree + 1)
                  for parents in combinations(columns, k)]

    n = len(y)
    shifts = [s for s in range(min_gap, n - min_gap + 1)]
    null_contra = np.empty(len(shifts))
    null_acc = np.empty(len(shifts))
    for b, s in enumerate(shifts):
        ys = np.roll(y, s)
        best_c, best_a = np.inf, -np.inf
        for cols in candidates:
            st = pattern_stats(X[:, list(cols)], ys, (), n_values)
            if st.recurrence < min_recurrence:
                continue
            if not np.isnan(st.contradiction):
                best_c = min(best_c, st.contradiction)
            best_a = max(best_a, st.lookup_accuracy)
        null_contra[b] = best_c
        null_acc[b] = best_a

    n_sur = len(shifts)
    return dict(
        null_kind="circular_shift",
        observed_contradiction=obs_contra,
        null_contradiction_mean=float(np.mean(null_contra)),
        null_contradiction_sd=float(np.std(null_contra)),
        excess_contradiction=float(obs_contra - np.mean(null_contra)),
        p_contradiction=float((np.sum(null_contra <= obs_contra) + 1) / (n_sur + 1)),
        observed_lookup_accuracy=obs_acc,
        null_lookup_accuracy_mean=float(np.mean(null_acc)),
        null_lookup_accuracy_sd=float(np.std(null_acc)),
        excess_lookup_accuracy=float(obs_acc - np.mean(null_acc)),
        p_lookup_accuracy=float((np.sum(null_acc >= obs_acc) + 1) / (n_sur + 1)),
        n_surrogates=n_sur,
        min_gap=min_gap,
        n_candidates=len(candidates),
        min_recurrence=min_recurrence,
    )


def covariate_shift_null(frame: pd.DataFrame, target: str, fixed: list[str],
                         extra: list[str], max_indegree: int = 3,
                         n_values: int = 3, min_recurrence: float = 0.5,
                         min_gap: int = 6) -> dict:
    """Does adding ``extra`` parents improve on ``fixed`` alone, beyond chance?

    The two previous nulls answer "is there structure". This one answers the
    question that actually decides whether a *network* is warranted: given that
    the target's own lagged regime already predicts it, do any other variables
    add anything?

    A raw comparison cannot answer it. Enlarging a parent set can only raise the
    in-sample accuracy of a lookup table, so the increment is positive by
    construction. Here the surrogates rotate the ``extra`` columns while leaving
    the target, the successor and the ``fixed`` columns aligned. Persistence,
    the marginal and every autocorrelation are preserved exactly; only the extra
    variables' alignment to the target is destroyed. The surrogate increment is
    therefore the increment attributable to nothing at all, and the comparison is
    like for like.
    """
    X, y = build_design(frame, target, fixed + extra)
    n_fixed = len(fixed)
    fixed_cols = tuple(range(n_fixed))
    extra_cols = list(range(n_fixed, n_fixed + len(extra)))

    def best(Xd) -> float:
        acc = -np.inf
        for k in range(0, max_indegree - n_fixed + 1):
            for combo in combinations(extra_cols, k):
                cols = list(fixed_cols) + list(combo)
                st = pattern_stats(Xd[:, cols], y, (), n_values)
                if st.recurrence < min_recurrence:
                    continue
                acc = max(acc, st.lookup_accuracy)
        return acc

    baseline = pattern_stats(X[:, list(fixed_cols)], y, (), n_values).lookup_accuracy
    observed = best(X)

    n = len(y)
    increments = []
    for s in range(min_gap, n - min_gap + 1):
        Xs = X.copy()
        Xs[:, extra_cols] = np.roll(X[:, extra_cols], s, axis=0)
        increments.append(best(Xs) - baseline)
    increments = np.asarray(increments)
    obs_inc = observed - baseline

    return dict(
        null_kind="covariate_circular_shift",
        baseline_lookup_accuracy=float(baseline),
        observed_lookup_accuracy=float(observed),
        observed_increment=float(obs_inc),
        null_increment_mean=float(np.mean(increments)),
        null_increment_sd=float(np.std(increments)),
        excess_increment=float(obs_inc - np.mean(increments)),
        p_increment=float((np.sum(increments >= obs_inc) + 1) / (len(increments) + 1)),
        n_surrogates=int(len(increments)),
        fixed=list(fixed),
        n_extra=len(extra),
    )


def shuffle_null(frame: pd.DataFrame, target: str, columns: list[str],
                 max_indegree: int = 3, n_values: int = 3,
                 min_recurrence: float = 0.5, n_shuffles: int = 1000,
                 seed: int = 42) -> dict:
    """Best-of-search against an i.i.d. permutation of the successor column.

    **Secondary null, retained for contrast and known to be too weak.** It
    preserves the regime marginal but destroys the successor's autocorrelation,
    so it answers "is the successor exchangeable" rather than "is the successor
    unrelated to the evidence given its own persistence". See
    ``circular_shift_null`` for the defect this caused and the remedy.
    """
    obs_contra, obs_acc = best_of_search(frame, target, columns, max_indegree,
                                         n_values, min_recurrence)

    X, y = build_design(frame, target, columns)
    idx = {c: j for j, c in enumerate(columns)}
    candidates = [tuple(idx[p] for p in parents)
                  for k in range(1, max_indegree + 1)
                  for parents in combinations(columns, k)]

    rng = np.random.default_rng(seed)
    null_contra = np.empty(n_shuffles)
    null_acc = np.empty(n_shuffles)
    for b in range(n_shuffles):
        yp = rng.permutation(y)
        best_c, best_a = np.inf, -np.inf
        for cols in candidates:
            st = pattern_stats(X[:, list(cols)], yp, (), n_values)
            if st.recurrence < min_recurrence:
                continue
            if not np.isnan(st.contradiction):
                best_c = min(best_c, st.contradiction)
            best_a = max(best_a, st.lookup_accuracy)
        null_contra[b] = best_c
        null_acc[b] = best_a

    # One-sided p-values, with the observation counted (add-one), so that a
    # p-value can never be reported as exactly zero.
    p_contra = float((np.sum(null_contra <= obs_contra) + 1) / (n_shuffles + 1))
    p_acc = float((np.sum(null_acc >= obs_acc) + 1) / (n_shuffles + 1))

    return dict(
        observed_contradiction=obs_contra,
        null_contradiction_mean=float(np.mean(null_contra)),
        null_contradiction_sd=float(np.std(null_contra)),
        excess_contradiction=float(obs_contra - np.mean(null_contra)),
        p_contradiction=p_contra,
        observed_lookup_accuracy=obs_acc,
        null_lookup_accuracy_mean=float(np.mean(null_acc)),
        null_lookup_accuracy_sd=float(np.std(null_acc)),
        excess_lookup_accuracy=float(obs_acc - np.mean(null_acc)),
        p_lookup_accuracy=p_acc,
        n_shuffles=n_shuffles,
        n_candidates=len(candidates),
        min_recurrence=min_recurrence,
        seed=seed,
    )


def coverage(frame: pd.DataFrame, columns: list[str], n_values: int = 3) -> dict:
    """Ledger entry B2: how much of the input space the sample actually visits."""
    X = frame[columns].to_numpy(dtype=np.int64)
    codes = encode(X, n_values)
    _, counts = np.unique(codes, return_counts=True)
    return dict(n_observations=int(len(codes)),
                state_space=int(n_values ** len(columns)),
                distinct_states=int(len(counts)),
                coverage=float(len(counts) / n_values ** len(columns)),
                recurring_states=int((counts > 1).sum()),
                max_multiplicity=int(counts.max()),
                observations_in_recurring=int(counts[counts > 1].sum()))
