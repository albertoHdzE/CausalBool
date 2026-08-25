"""MoleculeNet dataset loading, graph construction and scaffold splitting.

The six datasets are the exact CSV files that DGL-LifeSci downloads from
``https://data.dgl.ai/dataset/`` (see ``dgllife/data/*.py``), so the molecules,
labels and task definitions are identical to the ones the authors used.  Graph
construction follows ``dgllife.utils.SMILESToBigraph(add_self_loop=False)``:
atoms are renumbered into RDKit canonical order, every bond becomes a pair of
directed edges, and node/edge features come from the canonical featurisers.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from rdkit import Chem, RDLogger
from rdkit.Chem import rdmolfiles, rdmolops
from rdkit.Chem.Scaffolds import MurckoScaffold

from .featurizers import ATOM_FEATURE_SIZE, featurize_atoms, featurize_bonds

RDLogger.DisableLog('rdApp.*')

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
RAW_DIR = os.path.join(ROOT, 'data', 'raw')
CACHE_DIR = os.path.join(ROOT, 'data', 'cache')

# name -> (csv file, smiles column, task columns, task type, metric)
DATASET_SPECS = {
    'FreeSolv': ('SAMPL.csv', 'smiles', ['expt'], 'regression', 'rmse'),
    'ESOL': ('delaney-processed.csv', 'smiles',
             ['measured log solubility in mols per litre'], 'regression', 'rmse'),
    'Lipophilicity': ('Lipophilicity.csv', 'smiles', ['exp'], 'regression', 'rmse'),
    'BACE': ('bace.csv', 'mol', ['Class'], 'classification', 'roc_auc_score'),
    'BBBP': ('BBBP.csv', 'smiles', ['p_np'], 'classification', 'roc_auc_score'),
    'ClinTox': ('clintox.csv', 'smiles', ['FDA_APPROVED', 'CT_TOX'],
                'classification', 'roc_auc_score'),
}

DATASET_ORDER = ['FreeSolv', 'ESOL', 'Lipophilicity', 'BACE', 'BBBP', 'ClinTox']
NOISE_LEVELS = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5]


@dataclass
class MolGraph:
    """A single molecular graph in list-of-edges form."""

    smiles: str
    n_nodes: int
    src: np.ndarray          # (E,) int32
    dst: np.ndarray          # (E,) int32
    node_feat: np.ndarray    # (n_nodes, 74) float32
    edge_feat: np.ndarray    # (E, 12) float32
    label: np.ndarray        # (n_tasks,) float32
    mask: np.ndarray         # (n_tasks,) float32

    def adjacency(self) -> np.ndarray:
        a = np.zeros((self.n_nodes, self.n_nodes), dtype=np.int16)
        a[self.src, self.dst] = 1
        return a

    def neighbours(self) -> list:
        nb = [[] for _ in range(self.n_nodes)]
        for u, v in zip(self.src, self.dst):
            nb[int(u)].append(int(v))
        return nb


@dataclass
class MoleculeDataset:
    name: str
    graphs: list = field(default_factory=list)
    task_names: list = field(default_factory=list)
    task_type: str = 'regression'
    metric: str = 'rmse'

    def __len__(self):
        return len(self.graphs)

    @property
    def n_tasks(self):
        return len(self.task_names)

    @property
    def max_nodes(self):
        return max(g.n_nodes for g in self.graphs)

    @property
    def smiles(self):
        return [g.smiles for g in self.graphs]

    def node_feature_std(self) -> np.ndarray:
        """Per-column std over all atoms of the dataset (unbiased, as torch.std)."""
        feats = np.concatenate([g.node_feat for g in self.graphs], axis=0)
        return feats.std(axis=0, ddof=1)


def smiles_to_graph(smiles: str, label, mask) -> MolGraph | None:
    """Replicates dgllife SMILESToBigraph(add_self_loop=False, canonical order)."""
    mol = Chem.MolFromSmiles(smiles)
    if mol is None:
        return None
    new_order = rdmolfiles.CanonicalRankAtoms(mol)
    mol = rdmolops.RenumberAtoms(mol, list(new_order))

    src, dst = [], []
    for i in range(mol.GetNumBonds()):
        bond = mol.GetBondWithIdx(i)
        u, v = bond.GetBeginAtomIdx(), bond.GetEndAtomIdx()
        src.extend([u, v])
        dst.extend([v, u])

    return MolGraph(
        smiles=smiles,
        n_nodes=mol.GetNumAtoms(),
        src=np.asarray(src, dtype=np.int32),
        dst=np.asarray(dst, dtype=np.int32),
        node_feat=featurize_atoms(mol),
        edge_feat=featurize_bonds(mol),
        label=np.asarray(label, dtype=np.float32),
        mask=np.asarray(mask, dtype=np.float32),
    )


def load_dataset(name: str, verbose: bool = False) -> MoleculeDataset:
    """Load one of the six MoleculeNet datasets used in the paper."""
    if name not in DATASET_SPECS:
        raise ValueError(f'Unknown dataset {name!r}; choose from {list(DATASET_SPECS)}')
    csv_name, smiles_col, tasks, task_type, metric = DATASET_SPECS[name]
    df = pd.read_csv(os.path.join(RAW_DIR, csv_name))

    graphs, n_failed = [], 0
    for _, row in df.iterrows():
        values = [row[t] for t in tasks]
        mask = [0.0 if pd.isna(v) else 1.0 for v in values]
        label = [0.0 if pd.isna(v) else float(v) for v in values]
        g = smiles_to_graph(row[smiles_col], label, mask)
        if g is None or g.n_nodes == 0:
            n_failed += 1
            continue
        graphs.append(g)
    if verbose:
        print(f'{name}: {len(graphs)} graphs kept, {n_failed} SMILES failed RDKit parsing')

    return MoleculeDataset(name=name, graphs=graphs, task_names=tasks,
                           task_type=task_type, metric=metric)


def scaffold_split(dataset: MoleculeDataset, frac_train=0.8, frac_val=0.1):
    """Bemis-Murcko scaffold split, port of dgllife ScaffoldSplitter.

    ``scaffold_func='smiles'`` as used by the authors: groups are ordered by
    decreasing group size (ties broken by the smallest member index) and filled
    greedily into train, then validation, then test.
    """
    from collections import defaultdict

    scaffolds = defaultdict(list)
    for i, smi in enumerate(dataset.smiles):
        mol = Chem.MolFromSmiles(smi)
        try:
            Chem.rdmolops.FastFindRings(mol)
            key = MurckoScaffold.MurckoScaffoldSmiles(mol=mol, includeChirality=False)
            scaffolds[key].append(i)
        except Exception:
            continue

    scaffolds = {k: sorted(v) for k, v in scaffolds.items()}
    scaffold_sets = [s for _, s in sorted(scaffolds.items(),
                                          key=lambda x: (len(x[1]), x[1][0]),
                                          reverse=True)]

    n = len(dataset)
    train_cutoff = int(frac_train * n)
    val_cutoff = int((frac_train + frac_val) * n)
    train, val, test = [], [], []
    for group in scaffold_sets:
        if len(train) + len(group) > train_cutoff:
            if len(train) + len(val) + len(group) > val_cutoff:
                test.extend(group)
            else:
                val.extend(group)
        else:
            train.extend(group)
    return train, val, test


def size_bins(dataset: MoleculeDataset, n_bins: int = 4, min_per_bin: int = 250):
    """Split a dataset into equal-count bins by atom count.

    Bin edges are the atom-count quantiles, but molecules sharing an atom count
    are never split across two bins, so the bins are only approximately equal in
    size.  Each returned sub-dataset keeps the parent's ``name``, so that
    ``hyperparams.get`` still resolves to the family's published settings.

    Returns a list of dictionaries with the sub-dataset and its descriptive
    statistics; raises if any bin falls below ``min_per_bin``.
    """
    sizes = np.array([g.n_nodes for g in dataset.graphs])
    edges = np.quantile(sizes, np.arange(1, n_bins) / n_bins)
    # assign by atom count so that ties land together
    counts = sorted(set(sizes.tolist()))
    bin_of_count = {c: int(np.searchsorted(edges, c, side='left')) for c in counts}

    out = []
    for b in range(n_bins):
        idx = [i for i, s in enumerate(sizes) if bin_of_count[int(s)] == b]
        if len(idx) < min_per_bin:
            raise ValueError(f'{dataset.name} bin {b} has only {len(idx)} molecules '
                             f'(minimum {min_per_bin}); choose fewer bins')
        graphs = [dataset.graphs[i] for i in idx]
        sub = MoleculeDataset(name=dataset.name, graphs=graphs,
                              task_names=dataset.task_names,
                              task_type=dataset.task_type, metric=dataset.metric)
        bs = sizes[idx]
        out.append(dict(bin=b, dataset=sub, n=len(idx),
                        min_atoms=int(bs.min()), max_atoms=int(bs.max()),
                        mean_atoms=float(bs.mean())))
    return out
