#!/usr/bin/env python
"""Run the CausalBool index-set mirror of the paper's analysis.

Computes, for every dataset family, a set of deterministic index-set
observables in place of BDM, then repeats the paper's Table 4 correlation and
Table 5 clustering with each of them.  Writes ``results/causalbool_mirror.json``
and ``results/causalbool_mirror.csv``.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402

from imp_pathinfo import analysis as an                          # noqa: E402
from imp_pathinfo import causalbool_mirror as cm                 # noqa: E402
from imp_pathinfo import hyperparams as hp                       # noqa: E402
from imp_pathinfo import paper_values as pv                      # noqa: E402
from imp_pathinfo.data import DATASET_ORDER, load_dataset        # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RESDIR = os.path.join(ROOT, 'results')

MEASURES = ['sumando_spread_k2', 'sumando_spread_k3', 'sumando_bits_k2', 'sumando_bits_k3', 'saturation', 'path_surplus',
            'D', 'D_wiring', 'D_per_atom', 'D_hop1', 'D_hop2', 'D_hop3',
            'D_path_total', 'n_atoms']


def main(limit=None, max_len=3):
    os.makedirs(RESDIR, exist_ok=True)

    print('== deconvolution check: recovering mechanisms from behaviour alone ==')
    recovery = {}
    for name in DATASET_ORDER:
        dataset = load_dataset(name)
        t0 = time.time()
        reports = [cm.deconvolve_molecule(g) for g in dataset.graphs[:200]
                   if g.n_nodes >= 2]
        atoms = sum(r.n_atoms for r in reports)
        exact = sum(r.n_recovered_exactly for r in reports)
        subset = sum(r.n_index_subset for r in reports)
        gates = sum(r.n_gate_matched for r in reports)
        rows = max(r.max_local_rows for r in reports)
        biggest = max(g.n_nodes for g in dataset.graphs)
        recovery[name] = dict(molecules=len(reports), atoms=atoms,
                              exact=exact, exact_fraction=exact / atoms,
                              index_subset=subset, gate_matched=gates,
                              max_local_rows=rows, largest_molecule=biggest,
                              seconds=round(time.time() - t0, 1))
        print(f'{name:14s} {len(reports):4d} molecules, {atoms:6d} atoms, '
              f'index set recovered exactly {100*exact/atoms:6.2f}%, '
              f'gate named {100*gates/atoms:6.2f}%, '
              f'largest local repertoire {rows} rows '
              f'(full repertoire would be 2**{biggest})')

    print('\n== index-set observables per dataset family ==')
    measures = {}
    for name in DATASET_ORDER:
        dataset = load_dataset(name)
        t0 = time.time()
        measures[name] = cm.dataset_index_measures(dataset, max_len=max_len, limit=limit)
        print(f'{name:14s} computed in {time.time() - t0:5.1f}s '
              f'({measures[name]["n_graphs"]} graphs)')

    df = pd.DataFrame(measures).T[MEASURES + ['n_graphs']]
    df['BDM_AOAC'] = [pv.AOAC[n] for n in df.index]
    df = df.loc[pv.AOAC_ORDER]
    print()
    print(df.round(3).to_string())

    print('\n== correlation of each observable with the paper\'s PUMs ==')
    per_model = {m: [pv.PUM[m][d] for d in pv.AOAC_ORDER] for m in hp.MODELS}
    per_model['across all models'] = list(np.mean([per_model[m] for m in hp.MODELS], axis=0))

    rows = []
    for measure in MEASURES + ['BDM_AOAC']:
        x = df[measure].values.astype(float)
        row = {'measure': measure}
        for model, pums in per_model.items():
            r, p = an.correlation(x, pums)
            row[f'r_{model}'] = round(r, 3)
            row[f'p_{model}'] = round(p, 3)
        rows.append(row)
    corr = pd.DataFrame(rows).set_index('measure')
    print(corr[[c for c in corr.columns if c.startswith('r_')]].to_string())

    print('\n== clustering the six families by each observable ==')
    aoac_labels, aoac_sil = an.cluster_1d(df['BDM_AOAC'].values.astype(float))
    clus = []
    for measure in MEASURES + ['BDM_AOAC']:
        x = df[measure].values.astype(float)
        # saturation runs opposite to a complexity: high saturation is "simple"
        invert = measure in ('saturation',)
        labels, sil = an.cluster_1d(x, invert_labels=invert)
        clus.append(dict(measure=measure, labels=''.join(map(str, labels)),
                         silhouette=round(sil, 3),
                         matches_BDM_clustering=''.join(map(str, labels)) ==
                         ''.join(map(str, aoac_labels))))
    clus_df = pd.DataFrame(clus).set_index('measure')
    print(clus_df.to_string())
    print('\ncolumns ordered', pv.AOAC_ORDER)

    out = dict(measures=measures, recovery=recovery,
               correlations=corr.to_dict(orient='index'),
               clustering=clus_df.to_dict(orient='index'))
    json.dump(out, open(os.path.join(RESDIR, 'causalbool_mirror.json'), 'w'), indent=2)
    df.to_csv(os.path.join(RESDIR, 'causalbool_mirror.csv'))
    print(f'\nwrote {RESDIR}/causalbool_mirror.json and .csv')


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--limit', type=int, default=None,
                    help='cap the molecules per dataset (for a quick pass)')
    ap.add_argument('--max-len', type=int, default=3, help='maximum path length L')
    a = ap.parse_args()
    main(limit=a.limit, max_len=a.max_len)
