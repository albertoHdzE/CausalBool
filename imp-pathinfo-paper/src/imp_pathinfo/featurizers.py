"""Atom and bond featurisation, reimplemented to match DGL-LifeSci 0.3.2.

The authors of the paper build their molecular graphs with
``dgllife.utils.CanonicalAtomFeaturizer`` (74 features per atom) and, for
Graphormer only, ``CanonicalBondFeaturizer`` (12 features per bond, since the
authors do not add self loops).  DGL does not ship usable macOS/arm64 wheels,
so the pieces of DGL-LifeSci that matter for this replication are reimplemented
here directly on top of RDKit.  Every allowable set below is copied verbatim
from ``dgllife/utils/featurizers.py`` so that the feature vectors are
bit-identical to the ones the authors trained on.

Reference source: ``reference/dgllife_0.3.2/dgllife/utils/featurizers.py``.
"""

from __future__ import annotations

import numpy as np
from rdkit import Chem

ATOM_TYPES = [
    'C', 'N', 'O', 'S', 'F', 'Si', 'P', 'Cl', 'Br', 'Mg', 'Na', 'Ca',
    'Fe', 'As', 'Al', 'I', 'B', 'V', 'K', 'Tl', 'Yb', 'Sb', 'Sn',
    'Ag', 'Pd', 'Co', 'Se', 'Ti', 'Zn', 'H', 'Li', 'Ge', 'Cu', 'Au',
    'Ni', 'Cd', 'In', 'Mn', 'Zr', 'Cr', 'Pt', 'Hg', 'Pb',
]
DEGREES = list(range(11))
IMPLICIT_VALENCES = list(range(7))
HYBRIDIZATIONS = [
    Chem.rdchem.HybridizationType.SP,
    Chem.rdchem.HybridizationType.SP2,
    Chem.rdchem.HybridizationType.SP3,
    Chem.rdchem.HybridizationType.SP3D,
    Chem.rdchem.HybridizationType.SP3D2,
]
TOTAL_NUM_HS = list(range(5))

BOND_TYPES = [
    Chem.rdchem.BondType.SINGLE,
    Chem.rdchem.BondType.DOUBLE,
    Chem.rdchem.BondType.TRIPLE,
    Chem.rdchem.BondType.AROMATIC,
]
BOND_STEREOS = [
    Chem.rdchem.BondStereo.STEREONONE,
    Chem.rdchem.BondStereo.STEREOANY,
    Chem.rdchem.BondStereo.STEREOZ,
    Chem.rdchem.BondStereo.STEREOE,
    Chem.rdchem.BondStereo.STEREOCIS,
    Chem.rdchem.BondStereo.STEREOTRANS,
]

ATOM_FEATURE_SIZE = (
    len(ATOM_TYPES) + len(DEGREES) + len(IMPLICIT_VALENCES) + 1 + 1
    + len(HYBRIDIZATIONS) + 1 + len(TOTAL_NUM_HS)
)  # == 74
BOND_FEATURE_SIZE = len(BOND_TYPES) + 1 + 1 + len(BOND_STEREOS)  # == 12


def _one_hot(x, allowable_set):
    return [float(x == s) for s in allowable_set]


def atom_features(atom) -> list:
    """The 74-dimensional CanonicalAtomFeaturizer vector for a single atom."""
    return (
        _one_hot(atom.GetSymbol(), ATOM_TYPES)
        + _one_hot(atom.GetDegree(), DEGREES)
        + _one_hot(atom.GetImplicitValence(), IMPLICIT_VALENCES)
        + [float(atom.GetFormalCharge())]
        + [float(atom.GetNumRadicalElectrons())]
        + _one_hot(atom.GetHybridization(), HYBRIDIZATIONS)
        + [float(atom.GetIsAromatic())]
        + _one_hot(atom.GetTotalNumHs(), TOTAL_NUM_HS)
    )


def bond_features(bond) -> list:
    """The 12-dimensional CanonicalBondFeaturizer vector for a single bond."""
    return (
        _one_hot(bond.GetBondType(), BOND_TYPES)
        + [float(bond.GetIsConjugated())]
        + [float(bond.IsInRing())]
        + _one_hot(bond.GetStereo(), BOND_STEREOS)
    )


def featurize_atoms(mol) -> np.ndarray:
    return np.asarray([atom_features(a) for a in mol.GetAtoms()], dtype=np.float32)


def featurize_bonds(mol) -> np.ndarray:
    """Edge features in bigraph order: bond ``i`` yields edges ``2i`` and ``2i+1``."""
    feats = []
    for i in range(mol.GetNumBonds()):
        f = bond_features(mol.GetBondWithIdx(i))
        feats.append(f)
        feats.append(f)
    if not feats:
        return np.zeros((0, BOND_FEATURE_SIZE), dtype=np.float32)
    return np.asarray(feats, dtype=np.float32)
