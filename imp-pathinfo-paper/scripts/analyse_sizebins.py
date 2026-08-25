#!/usr/bin/env python
"""Phase 1 readout: PUM per ESOL size bin against mean bin size and mean bin BDM.

The design and the decision criterion are pre-registered in
``PHASE1_PROTOCOL.md``; this script only reports.  It reads
``results/runs_sizebins.jsonl`` and writes ``results/sizebins_summary.csv``.
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np                                               # noqa: E402
import pandas as pd                                              # noqa: E402
from scipy.stats import spearmanr                                # noqa: E402

from imp_pathinfo import analysis as an                           # noqa: E402
from imp_pathinfo.bdm_complexity import bdm_engine, graph_bdm     # noqa: E402
from imp_pathinfo.data import load_dataset, size_bins             # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
LEDGER = os.path.join(ROOT, 'results', 'runs_sizebins.jsonl')


def main(dataset_name='ESOL', n_bins=4):
    records = [json.loads(line) for line in open(LEDGER) if line.strip()]
    df = pd.DataFrame(records)
    df = df[df.dataset == dataset_name]
    metric = 'rmse' if dataset_name in ('FreeSolv', 'ESOL', 'Lipophilicity') else 'roc_auc'

    parent = load_dataset(dataset_name)
    engine = bdm_engine()

    rows = []
    for b in size_bins(parent, n_bins):
        sub = df[df.size_bin == b['bin']]
        means = (sub.groupby(['use_path', 'noise'])['test_score'].mean().reset_index())
        noises = sorted(means.noise.unique())
        without, with_ = [], []
        for g in noises:
            a = means[(means.noise == g) & (means.use_path == 0)].test_score.values
            c = means[(means.noise == g) & (means.use_path == 1)].test_score.values
            if len(a) and len(c):
                without.append(float(a[0]))
                with_.append(float(c[0]))
        value = an.pum(without, with_, metric) if without else float('nan')

        scored = [graph_bdm(g, engine) for g in b['dataset'].graphs]
        bdm = np.mean([v for v in scored if v is not None])

        rows.append(dict(bin=b['bin'], atoms=f"{b['min_atoms']}-{b['max_atoms']}",
                         n=b['n'], mean_atoms=round(b['mean_atoms'], 2),
                         mean_bdm=round(float(bdm), 2),
                         cells=len(without), pum=round(value, 3),
                         pum_str=f'{value * 6:.0f}/6',
                         score_no_path=round(float(np.mean(without)), 4) if without else np.nan,
                         score_path=round(float(np.mean(with_)), 4) if with_ else np.nan))

    out = pd.DataFrame(rows).set_index('bin')
    print(out.to_string())
    out.to_csv(os.path.join(ROOT, 'results', 'sizebins_summary.csv'))

    complete = out[out.cells == 6]
    if len(complete) < n_bins:
        print(f'\n{len(complete)} of {n_bins} bins complete; verdict withheld')
        return

    spread = complete.pum.max() - complete.pum.min()
    direction = complete.pum.iloc[0] - complete.pum.iloc[-1]
    rho_size = spearmanr(complete.mean_atoms, complete.pum)
    rho_bdm = spearmanr(complete.mean_bdm, complete.pum)

    print(f'\nPUM spread across bins       {spread:.3f}  ({spread * 6:.0f}/6)')
    print(f'smallest bin minus largest   {direction:+.3f}  '
          f'({direction * 6:+.0f}/6, positive = predicted by H1)')
    print(f'Spearman PUM vs mean atoms   {rho_size.statistic:+.3f}   '
          '(descriptive only, 4 points)')
    print(f'Spearman PUM vs mean BDM     {rho_bdm.statistic:+.3f}   '
          '(descriptive only, 4 points)')

    # criterion fixed in PHASE1_PROTOCOL.md before any run.  A dataset whose PUM
    # is pinned at 0 or 1 in every bin carries no information about the trend:
    # the binary measure has no dynamic range, so a zero spread is a floor
    # effect and must not be read as H0.
    if complete.pum.nunique() == 1 and complete.pum.iloc[0] in (0.0, 1.0):
        verdict = ('DEGENERATE: PUM is pinned at the '
                   f'{"floor" if complete.pum.iloc[0] == 0 else "ceiling"} in every '
                   'bin, so the binary measure is uninformative here. Read the '
                   'continuous RMSE penalty instead; H0 is NOT supported by this.')
    elif spread >= 0.5 and direction >= 0.5:
        verdict = 'H1 SUPPORTED: PUM falls with molecule size within one dataset'
    elif spread <= 1 / 6 + 1e-9:
        verdict = 'H0 SUPPORTED: PUM is flat across size bins'
    else:
        verdict = 'INCONCLUSIVE by the pre-registered criterion'
    print('\nVERDICT:', verdict)


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--dataset', default='ESOL')
    ap.add_argument('--bins', type=int, default=4)
    a = ap.parse_args()
    main(a.dataset, a.bins)
