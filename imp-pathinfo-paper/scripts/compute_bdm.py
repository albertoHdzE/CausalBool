#!/usr/bin/env python
"""Compute the AOAC of every dataset family (Table 4, first row).

Writes ``results/aoac.json`` and ``results/bdm_per_graph.csv`` and prints the
comparison against the published values.
"""

from __future__ import annotations

import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import numpy as np                                              # noqa: E402
import pandas as pd                                             # noqa: E402

from imp_pathinfo import paper_values as pv                      # noqa: E402
from imp_pathinfo.bdm_complexity import bdm_engine, dataset_aoac, graph_bdm  # noqa: E402
from imp_pathinfo.data import DATASET_ORDER, load_dataset        # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
RESDIR = os.path.join(ROOT, 'results')


def main():
    os.makedirs(RESDIR, exist_ok=True)
    engine = bdm_engine()
    aoac, rows, per_graph = {}, [], []

    for name in DATASET_ORDER:
        t0 = time.time()
        dataset = load_dataset(name)
        values, mean, skipped = dataset_aoac(dataset, engine)
        aoac[name] = mean
        rows.append(dict(dataset=name, aoac=round(mean, 2), paper=pv.AOAC[name],
                         difference=round(mean - pv.AOAC[name], 2),
                         n_scored=len(values), n_skipped=skipped,
                         seconds=round(time.time() - t0, 1)))
        for g in dataset.graphs:
            v = graph_bdm(g, engine)
            per_graph.append(dict(dataset=name, smiles=g.smiles, n_atoms=g.n_nodes,
                                  bdm=v))

    df = pd.DataFrame(rows).set_index('dataset').loc[pv.AOAC_ORDER]
    print(df.to_string())
    exact = (df.difference.abs() < 0.01).sum()
    print(f'\n{exact} of 6 dataset families reproduce the published AOAC to two decimals')
    print('ascending order identical:',
          list(df.sort_values('aoac').index) == pv.AOAC_ORDER)

    json.dump(aoac, open(os.path.join(RESDIR, 'aoac.json'), 'w'), indent=2)
    pd.DataFrame(per_graph).to_csv(os.path.join(RESDIR, 'bdm_per_graph.csv'), index=False)
    print(f'\nwrote {RESDIR}/aoac.json and {RESDIR}/bdm_per_graph.csv')


if __name__ == '__main__':
    main()
