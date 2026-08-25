"""PUM, dichotomy score, correlations and the clustering analysis.

Section 2.4 and Section 3.3 of the paper.  ``F(M_i, D_j^gamma)`` indicates
whether path information improved accuracy on one dataset variant; the Path
Usefulness Measure ``U_ij`` is the fraction of the six variants of a family for
which it did.  The paper then reports

* the dichotomy score ``Phi_i = (1/6) sum_j max(U_ij, 1 - U_ij)``;
* the Pearson correlation between a model's PUMs and the dataset families'
  AOAC values;
* a 2-means clustering of families by AOAC and, separately, by PUM, with
  Silhouette scores and inverted PUM labels (high PUM <-> low complexity).
"""

from __future__ import annotations

import numpy as np
from scipy.stats import pearsonr
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score


def path_helps(score_without: float, score_with: float, metric: str) -> bool:
    """``F(M_i, D_j^gamma)``: did path information improve the test metric?"""
    if metric == 'rmse':
        return score_with < score_without
    return score_with > score_without


def pum(scores_without, scores_with, metric: str) -> float:
    """PUM of Equation 6: fraction of the family's variants that path info helped."""
    flags = [path_helps(a, b, metric) for a, b in zip(scores_without, scores_with)]
    return float(np.mean(flags))


def dichotomy_score(pums) -> float:
    """``Phi_i``: how decisively a model separates helped from not-helped families."""
    pums = np.asarray(pums, dtype=float)
    return float(np.mean(np.maximum(pums, 1.0 - pums)))


def correlation(aoac, pums):
    """Pearson correlation between AOAC and PUM across the six dataset families."""
    r, p = pearsonr(np.asarray(aoac, dtype=float), np.asarray(pums, dtype=float))
    return float(r), float(p)


def cluster_1d(values, invert_labels: bool = False, seed: int = 0):
    """2-means clustering of a one-dimensional quantity, with Silhouette score.

    Cluster ids are relabelled so that ``0`` marks the low-value cluster; with
    ``invert_labels=True`` (used for PUMs, which the paper expects to run
    opposite to complexity) ``0`` marks the high-value cluster instead.
    """
    x = np.asarray(values, dtype=float).reshape(-1, 1)
    km = KMeans(n_clusters=2, n_init=10, random_state=seed).fit(x)
    labels = km.labels_
    centres = km.cluster_centers_.ravel()
    low = int(np.argmin(centres))
    labels = np.where(labels == low, 0, 1)
    if invert_labels:
        labels = 1 - labels
    if len(np.unique(labels)) < 2:
        return labels, float('nan')
    return labels, float(silhouette_score(x, labels))


def build_pum_table(results, aoac: dict, datasets, models, metrics: dict):
    """Assemble the PUM matrix (models x families) from raw experiment records.

    ``results`` is an iterable of dictionaries as returned by
    ``train.run_experiment``; runs are averaged before the comparison, matching
    the paper, which compares the three-run means of Table 3.
    """
    import pandas as pd

    df = pd.DataFrame(list(results))
    means = (df.groupby(['model', 'dataset', 'use_path', 'noise'])['test_score']
               .mean().reset_index())

    rows = {}
    for model in models:
        pums = []
        for ds in datasets:
            sub = means[(means.model == model) & (means.dataset == ds)]
            noises = sorted(sub.noise.unique())
            without = [sub[(sub.noise == g) & (sub.use_path == 0)].test_score.values for g in noises]
            with_ = [sub[(sub.noise == g) & (sub.use_path == 1)].test_score.values for g in noises]
            pairs = [(a[0], b[0]) for a, b in zip(without, with_) if len(a) and len(b)]
            pums.append(pum([a for a, _ in pairs], [b for _, b in pairs], metrics[ds])
                        if pairs else float('nan'))
        rows[model] = pums

    rows['across all models'] = list(np.nanmean(np.asarray([rows[m] for m in models]), axis=0))
    table = pd.DataFrame(rows, index=datasets).T
    table.columns = datasets
    return table, means
