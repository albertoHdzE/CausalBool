#!/usr/bin/env python
"""Driver for the training campaign behind Tables 2 and 3.

The full campaign is 6 dataset families x 6 noise levels x 3 models x 2 modes
x 3 repetitions = 648 training runs (216 experimental cases).  Results are
appended to a JSONL ledger and completed cases are skipped, so the campaign can
be stopped and resumed freely.

Examples
--------
    python scripts/run_experiments.py --datasets FreeSolv --quiet
    python scripts/run_experiments.py --models t_hop --noise 0.0 0.1
    python scripts/run_experiments.py --epochs 200 --reps 3
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from imp_pathinfo import hyperparams as hp                       # noqa: E402
from imp_pathinfo.data import (DATASET_ORDER, NOISE_LEVELS, load_dataset,  # noqa: E402
                               scaffold_split, size_bins)
from imp_pathinfo.train import build_cache, run_experiment       # noqa: E402

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
DEFAULT_LEDGER = os.path.join(ROOT, 'results', 'runs.jsonl')


def load_ledger(path):
    done = set()
    if os.path.exists(path):
        with open(path) as fh:
            for line in fh:
                try:
                    r = json.loads(line)
                except json.JSONDecodeError:
                    continue
                done.add((r['model'], r['dataset'], r['use_path'], r['noise'],
                          r['run'], r.get('size_bin', -1)))
    return done


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--datasets', nargs='*', default=DATASET_ORDER)
    ap.add_argument('--models', nargs='*', default=hp.MODELS)
    ap.add_argument('--modes', nargs='*', type=int, default=[0, 1])
    ap.add_argument('--noise', nargs='*', type=float, default=NOISE_LEVELS)
    ap.add_argument('--reps', type=int, default=hp.REPETITIONS)
    ap.add_argument('--epochs', type=int, default=hp.EPOCHS)
    ap.add_argument('--device', default='auto',
                    help="'cpu', 'mps', 'cuda', or 'auto' (accelerate Graphormer only, "
                         "which is the only model large enough for the transfer cost "
                         "to pay off)")
    ap.add_argument('--ledger', default=DEFAULT_LEDGER)
    ap.add_argument('--size-bins', type=int, default=0, metavar='K',
                    help='Phase 1: split each dataset into K equal-count bins by '
                         'atom count and run the campaign separately within each. '
                         'The parent family\'s padding width, perturbation scale '
                         'and hyperparameters are held fixed across bins, so only '
                         'the molecules differ. Use a separate --ledger.')
    ap.add_argument('--min-per-bin', type=int, default=250,
                    help='refuse to bin a dataset if any bin falls below this')
    ap.add_argument('--quiet', action='store_true',
                    help='print one line per experimental case only')
    ap.add_argument('--dry-run', action='store_true',
                    help='list the outstanding cases without training')
    args = ap.parse_args()

    if args.size_bins and os.path.abspath(args.ledger) == DEFAULT_LEDGER:
        ap.error('--size-bins must write to its own --ledger, not the main campaign one')

    os.makedirs(os.path.dirname(args.ledger), exist_ok=True)
    done = load_ledger(args.ledger)
    t_start = time.time()
    n_done = n_skip = 0

    for ds_name in args.datasets:
        parent = load_dataset(ds_name)
        # A "unit" is one body of molecules trained as a whole: the family
        # itself, or one of its size bins.
        if args.size_bins:
            units = []
            for b in size_bins(parent, args.size_bins, args.min_per_bin):
                units.append((b['bin'], b['dataset'],
                              {k: b[k] for k in ('n', 'min_atoms', 'max_atoms', 'mean_atoms')}))
                print('{name} bin {bin}: {n} molecules, {min_atoms}-{max_atoms} atoms, '
                      'mean {mean_atoms:.2f}'.format(name=ds_name, **b), flush=True)
        else:
            units = [(-1, parent, {})]

        # held fixed across bins so that only the molecules differ
        parent_max_nodes = parent.max_nodes
        parent_noise_std = parent.node_feature_std() if args.size_bins else None

        for bin_id, dataset, bin_meta in units:
            split = scaffold_split(dataset)
            for model in args.models:
                for use_path in args.modes:
                    params = hp.get(model, ds_name, use_path)
                    pow_dim = params.get('pow_dim', 0) if model == 't_hop' else 0
                    cache = None
                    for noise in args.noise:
                        for run in range(args.reps):
                            key = (model, ds_name, use_path, noise, run, bin_id)
                            if key in done:
                                n_skip += 1
                                continue
                            if args.dry_run:
                                print('todo:', key)
                                n_done += 1
                                continue
                            if cache is None:
                                cache = build_cache(dataset, model, pow_dim, parent_max_nodes)
                            device = args.device
                            if device == 'auto':
                                import torch
                                device = ('mps' if model == 'graphormer'
                                          and torch.backends.mps.is_available() else 'cpu')
                            rec = run_experiment(dataset, model, use_path, noise, run,
                                                 epochs=args.epochs, device=device,
                                                 cache=cache, split=split,
                                                 verbose=not args.quiet, torch_seed=run,
                                                 max_nodes=parent_max_nodes,
                                                 noise_std=parent_noise_std)
                            if bin_id >= 0:
                                rec['size_bin'] = bin_id
                                rec.update(bin_meta)
                            with open(args.ledger, 'a') as fh:
                                fh.write(json.dumps(rec) + '\n')
                            n_done += 1
                            print('{model:11s} {dataset:14s} bin={bin_id} path={use_path} '
                                  'noise={noise:.1f} run={run} {metric}={test_score:.4f} '
                                  '({epochs_run} epochs, {seconds:.0f}s)'.format(
                                      metric=dataset.metric, bin_id=bin_id, **rec),
                                  flush=True)

    print(f'\ncompleted {n_done} runs, skipped {n_skip} already in the ledger, '
          f'{time.time() - t_start:.0f}s total', flush=True)


if __name__ == '__main__':
    main()
