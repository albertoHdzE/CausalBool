#!/usr/bin/env python
"""Generate ``paper_walkthrough.ipynb`` from the cell list below.

Keeping the notebook in a plain Python file makes it reviewable in diffs; run
this script to regenerate the .ipynb, then execute the notebook.
"""

from __future__ import annotations

import json
import os

CELLS: list[tuple[str, str]] = []


def md(text: str):
    CELLS.append(('markdown', text.strip('\n')))


def code(text: str):
    CELLS.append(('code', text.strip('\n')))


# ============================================================================
md(r"""
# Algorithmic Complexity Predicts when Path Information Improves GNN Performance on Molecular Graphs

### A step-by-step replication

This notebook replicates, from the raw data upwards, the TMLR submission
*"Algorithmic Complexity Predicts when Path Information Improves Graph Neural
Networks Performance on Molecular Graphs"* (`paper/`).

**The paper's argument in one paragraph.** Many graph neural networks feed
themselves information about *paths* through the graph, on the assumption that
this always helps. The authors test that assumption on molecules: they train
three models (Graphormer, Mix-Hop and a new model of theirs, T-Hop) twice each
&mdash; once with path information and once without &mdash; on 36 molecular
datasets. Path information helps sometimes and hurts other times. They then ask
*when* it helps, and answer: it helps on datasets whose graphs are
**algorithmically simple**. Randomness is measured with the Block Decomposition
Method (BDM), benefit is measured with a quantity they define, the Path
Usefulness Measure (PUM), and the two are strongly negatively correlated.

**What this notebook does.** Every quantity in the paper is recomputed here:

| Paper artefact | What it is | Where in this notebook |
| --- | --- | --- |
| Table 1 | the six MoleculeNet datasets | §1 |
| Figure 1 | SMILES → list-of-edges graph conversion | §1 |
| Table 4, row 1 | the AOAC (mean BDM) of each dataset family | §2 |
| Definition 1, Lemma 1, Theorem 1 | the algebra behind T-Hop's tensors | §3 |
| Tables 2 and 3 | test scores with and without path information | §4 |
| PUM, dichotomy score Φ | how much path information helps | §5 |
| Table 4 | Pearson correlations, Figure 3 | §6 |
| Table 5 | clustering and Silhouette scores | §7 |
| — | a second, independent replication with the CausalBool index-set calculus | §9 |
| — | the two methods head to head: time, resources, accuracy, capability | §10 |

**Ground rules for this replication.** No code was copied from the authors'
repository. Their repository (mirrored read-only under `reference/`) was read to
recover experimental details that the paper does not state &mdash; the
Optuna-selected hyperparameters, the loss functions, the noise-injection scheme
&mdash; and everything was then written afresh in `src/imp_pathinfo/`. The
molecular data are the same CSV files that DGL-LifeSci downloads, so the
molecules and labels are the authors' own.
""")

md(r"""
## §0. Setup

Everything runs inside this folder's own virtual environment (`.venv`), which is
independent of every other replication in this repository. If the kernel below
is not the project kernel, start Jupyter with `.venv/bin/jupyter lab`.
""")

code(r"""
import os, sys, json, math, time, warnings
warnings.filterwarnings('ignore')

ROOT = os.path.abspath(os.path.join(os.getcwd(), '..')) if os.path.basename(os.getcwd()) == 'notebooks' else os.getcwd()
sys.path.insert(0, os.path.join(ROOT, 'src'))

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import torch

from imp_pathinfo import analysis as an
from imp_pathinfo import hyperparams as hp
from imp_pathinfo import paper_values as pv
from imp_pathinfo.data import DATASET_ORDER, NOISE_LEVELS, load_dataset, scaffold_split
from imp_pathinfo.bdm_complexity import bdm_engine, dataset_aoac, graph_bdm, graph_entropy
from imp_pathinfo.paths import (t_tensor_sparse, densify_t, simple_path_counts,
                                normalized_adjacency, shortest_paths)
from imp_pathinfo.train import build_cache, run_experiment

pd.set_option('display.width', 200)
plt.rcParams.update({'figure.dpi': 110, 'font.size': 9})
FIGDIR = os.path.join(ROOT, 'figures'); os.makedirs(FIGDIR, exist_ok=True)
RESDIR = os.path.join(ROOT, 'results'); os.makedirs(RESDIR, exist_ok=True)

print('python  ', sys.version.split()[0])
print('torch   ', torch.__version__, '| mps available:', torch.backends.mps.is_available())
print('root    ', ROOT)
""")

# ---------------------------------------------------------------- §1 datasets
md(r"""
## §1. The data

### 1.1 What the datasets are

The paper uses six datasets from **MoleculeNet**, a standard benchmark suite for
molecular machine learning. Each dataset is a list of molecules written as
SMILES strings, together with a property to predict. Three are regression tasks
scored by RMSE (lower is better) and three are binary classification tasks
scored by ROC-AUC (higher is better).

A molecule becomes a graph in the obvious way: **atoms are nodes, bonds are
edges**. The authors used DGL-LifeSci to do this conversion; here the same
conversion is done directly with RDKit, using the same canonical atom ordering
and the same 74-dimensional atom feature vector (`CanonicalAtomFeaturizer`) and
12-dimensional bond feature vector (`CanonicalBondFeaturizer`) so that the
inputs to the models are identical.
""")

code(r"""
datasets = {name: load_dataset(name) for name in DATASET_ORDER}

rows = []
for name, d in datasets.items():
    info = pv.DATASET_INFO[name]
    rows.append(dict(dataset=name, ours=len(d), paper=info['n_graphs'],
                     task=info['task'], type=info['type'], metric=info['metric'],
                     n_tasks=d.n_tasks, max_atoms=d.max_nodes,
                     mean_atoms=round(np.mean([g.n_nodes for g in d.graphs]), 1)))
table1 = pd.DataFrame(rows).set_index('dataset')
table1
""")

md(r"""
This is **Table 1** of the paper, with two extra columns.

Our graph counts sit a little below the published ones (for instance 642 against
643 for FreeSolv, 1480 against 1491 for ClinTox). The reason is mundane: the raw
CSV files contain a handful of SMILES strings that RDKit refuses to parse, and
those molecules are dropped. The paper appears to quote the raw row counts. The
difference is a fraction of a percent and, as §2 shows, does not move the
complexity numbers.

The `mean_atoms` column is worth keeping in mind for later: the datasets differ
enormously in molecule size, from 8.7 atoms on average in FreeSolv to about 34 in
BACE. That will turn out to matter for how the paper's complexity measure should
be read.

### 1.2 Figure 1: how a molecule becomes a graph

Figure 1 of the paper illustrates the conversion with methanoic acid (formic
acid, `OC=O`), the simplest organic acid. Let us rebuild that figure's three
matrices: the list of edges, the node features and the edge features.
""")

code(r"""
from imp_pathinfo.data import smiles_to_graph

methanoic = smiles_to_graph('OC=O', [0.0], [1.0])
print('SMILES: OC=O  ->  %d atoms, %d directed edges\n' % (methanoic.n_nodes, len(methanoic.src)))

print('1) list of edges (each column is one directed edge, as in DGL):')
print(np.vstack([methanoic.src, methanoic.dst]))

print('\n2) node feature matrix, shape', methanoic.node_feat.shape,
      '-- showing the non-zero columns only:')
nz = np.nonzero(methanoic.node_feat.sum(axis=0))[0]
print(pd.DataFrame(methanoic.node_feat[:, nz].astype(int), columns=[f'f{i}' for i in nz]))

print('\n3) edge feature matrix, shape', methanoic.edge_feat.shape, ':')
print(methanoic.edge_feat.astype(int))

print('\n4) adjacency matrix, the object BDM will actually look at:')
print(methanoic.adjacency())
""")

md(r"""
Two properties of this representation drive everything that follows.

* Each **bond becomes two directed edges**, so the adjacency matrix is symmetric
  with a zero diagonal.
* The **adjacency matrix knows nothing about the atoms**: swap every oxygen for
  a sulphur and it does not change. This is precisely why the paper can add
  noise to node and edge features without disturbing the graph structure, and
  therefore why all six members of a "dataset family" share one complexity
  value.

### 1.3 Dataset families

A **dataset family** is one original dataset plus five noisy copies of it. The
noise level is γ ∈ {0.0, 0.1, 0.2, 0.3, 0.4, 0.5}; at level γ, zero-mean
Gaussian noise with standard deviation γ·σ₀ is added to the features, where σ₀
is the feature standard deviation of the original dataset. γ = 0 *is* the
original dataset. Six families × six levels = the 36 datasets of the paper.

The authors' implementation adds the noise **per batch during training and
evaluation**, drawing one noise vector per batch from a seed derived from the
batch index, and broadcasting it across every atom in the batch. That is
reproduced exactly (`imp_pathinfo.train.make_batch`); it means the noise is a
per-batch feature perturbation rather than a fixed corruption of the stored
dataset.
""")

code(r"""
d = datasets['FreeSolv']
sigma0 = d.node_feature_std()
print('FreeSolv per-feature sigma_0: %d columns, mean %.4f, max %.4f'
      % (len(sigma0), sigma0.mean(), sigma0.max()))
print('noise standard deviations actually used, sigma = gamma * sigma_0:')
for g in NOISE_LEVELS:
    print(f'  gamma={g:.1f}  ->  mean sigma = {g*sigma0.mean():.4f}')
""")

# ------------------------------------------------------------------- §2 BDM
md(r"""
## §2. Algorithmic complexity with BDM

### 2.1 The idea

The paper needs a number that says *how random the connectivity pattern of a
graph is*. Shannon entropy is the usual choice but it is blind to structure: the
string `0101010101...` and a random string with the same proportion of ones have
identical entropy, yet the first is generated by a two-line program and the
second is not.

**Algorithmic (Kolmogorov) complexity** *K(x)* is the length of the shortest
program that outputs *x*. It is uncomputable, but it can be approximated from
below through **algorithmic probability**: by the Coding Theorem, objects
produced often by randomly chosen small programs are exactly the objects with
short programs,

$$K(x) \approx -\log_2 m(x),$$

where *m(x)* is the frequency with which *x* appears in the output of a large
collection of small Turing machines. The **Coding Theorem Method (CTM)** builds
that frequency table by brute force. It only reaches very small objects &mdash;
for two-dimensional binary arrays, 4×4 blocks.

The **Block Decomposition Method (BDM)** extends CTM to larger objects. It cuts
the adjacency matrix into non-overlapping 4×4 blocks, looks up each block's CTM
value, and adds a `log2` term that charges for repetitions:

$$K_{BDM}(G, d) = \sum_{(r_j, n_j) \in A} K_{CTM}(r_j) + \log_2 n_j.$$

The intuition of that formula: a hundred copies of the same block need one
description plus an index, not a hundred descriptions. So a *regular* graph
&mdash; many repeated blocks &mdash; scores low, and an *irregular* one scores
high.

The authors used the public `pybdm` package; so does this replication.
""")

code(r"""
bdm = bdm_engine()

demo = {
    'all zeros (perfectly regular)': np.zeros((8, 8), dtype=int),
    'all ones': np.ones((8, 8), dtype=int),
    'checkerboard (regular)': np.indices((8, 8)).sum(axis=0) % 2,
    'diagonal band (a chain-like molecule)': (np.abs(np.subtract.outer(range(8), range(8))) == 1).astype(int),
    'uniformly random': np.random.default_rng(0).integers(0, 2, (8, 8)),
}
for label, mat in demo.items():
    print(f'{label:40s} BDM = {bdm.bdm(mat):8.3f}   entropy = {bdm.ent(mat):6.3f}')
""")

md(r"""
The ordering is the one the method promises: repetitive matrices are cheap, the
random matrix is expensive. Note also that BDM separates the checkerboard from
the random matrix even though a naive bit-frequency entropy would give them
similar scores &mdash; that separation is the whole reason the paper prefers BDM
over entropy.

### 2.2 BDM of a single molecule

Let us take one molecule apart block by block, so the formula is concrete.
""")

code(r"""
g = datasets['ESOL'].graphs[12]
A = g.adjacency().astype(int)
print('molecule:', g.smiles, '|', g.n_nodes, 'atoms')

d = 4
nb = A.shape[0] // d
blocks = {}
for i in range(nb):
    for j in range(nb):
        key = A[i*d:(i+1)*d, j*d:(j+1)*d].tobytes()
        blocks[key] = blocks.get(key, 0) + 1
print(f'{A.shape[0]}x{A.shape[0]} adjacency -> {nb*nb} complete 4x4 blocks '
      f'({A.shape[0] - nb*d} trailing rows/columns are ignored by pybdm), '
      f'{len(blocks)} of them distinct')

total = bdm.bdm(A)
print(f'\nK_BDM(G, 4) = {total:.3f} bits')
print(f'Shannon block entropy = {bdm.ent(A):.3f}')

fig, ax = plt.subplots(figsize=(3.2, 3.2))
ax.imshow(A, cmap='Greys', interpolation='nearest')
for k in range(1, nb + 1):
    ax.axhline(k*d - 0.5, color='tab:red', lw=0.8)
    ax.axvline(k*d - 0.5, color='tab:red', lw=0.8)
ax.set_title(f'{g.smiles}\nadjacency, 4x4 BDM partition', fontsize=8)
ax.set_xticks([]); ax.set_yticks([])
plt.tight_layout(); plt.show()
""")

md(r"""
The picture explains why molecular adjacency matrices score the way they do.
They are extremely sparse: most 4×4 blocks are entirely zero, and repeated
all-zero blocks are cheap. The complexity comes from the few blocks straddling
the diagonal where the bonds actually live.

### 2.3 Table 4, row 1: the AOAC of each dataset family

The paper's dataset-level number is the mean of *K<sub>BDM</sub>(G, 4)* over
every molecular graph in the family's noise-free member. The paper calls the
resulting ordering the **ascending order algorithmic complexity (AOAC)**.

One implementation detail decides whether the published numbers reproduce.
Molecules with fewer than four atoms contain no complete 4×4 block, so under
`pybdm`'s default `PartitionIgnore` scheme there is nothing left to score and
the library declines to return a value. Those molecules must be **left out of
the average** rather than counted as zero. Doing so reproduces the published
figures; counting them as zero does not.
""")

code(r"""
t0 = time.time()
aoac_rows = []
for name, d in datasets.items():
    values, mean, skipped = dataset_aoac(d)
    aoac_rows.append(dict(dataset=name, ours=round(mean, 2), paper=pv.AOAC[name],
                          difference=round(mean - pv.AOAC[name], 2),
                          n_scored=len(values), n_skipped=skipped,
                          mean_atoms=round(np.mean([g.n_nodes for g in d.graphs]), 1)))
aoac_df = pd.DataFrame(aoac_rows).set_index('dataset').loc[pv.AOAC_ORDER]
print('computed in %.0f s' % (time.time() - t0))
aoac_df
""")

code(r"""
ours = aoac_df['ours'].values
paper = aoac_df['paper'].values
exact = np.abs(ours - paper) < 0.01
print('datasets reproduced to two decimal places: %d of 6  -> %s'
      % (exact.sum(), ', '.join(aoac_df.index[exact])))
print('largest absolute deviation: %.2f bits (%.2f%%)'
      % (np.abs(ours - paper).max(), 100*np.abs((ours-paper)/paper).max()))
print('rank ordering identical:', list(aoac_df.sort_values('ours').index) == pv.AOAC_ORDER)
aoac = {k: v for k, v in zip(aoac_df.index, ours)}
json.dump(aoac, open(os.path.join(RESDIR, 'aoac.json'), 'w'), indent=2)
""")

md(r"""
**Five of the six values reproduce exactly**, to the two decimal places the paper
prints; ClinTox differs by 0.86 bits (0.2%), attributable to the eleven molecules
that RDKit rejects in our copy of the CSV. The ascending order &mdash; FreeSolv,
ESOL, BBBP, ClinTox, Lipophilicity, BACE &mdash; is identical, and it is that
ordering that the rest of the paper depends on.

### 2.4 What the AOAC is actually measuring

Before using these numbers, it is worth asking what drives them. The paper reads
low AOAC as "more regular, predictable, compressible structure". There is a
second, simpler reading available.

**Stated carefully, because the loose version of this is false.** BDM does *not*
sum over every block: it sums over every **distinct** block and charges repeats
only `log2` of their multiplicity, so a repetitive object stays cheap however
large it grows. BDM is extensive in the amount of *distinct structure*, not in
size, and on individual molecules it is a genuine structural measure — it
separates 99.2% of molecule pairs that share both atom count and degree
sequence. `understanding_bdm.ipynb` establishes this in detail.

The reading available here is narrower and concerns the **average**, not the
measure: because bounded chemical valence ties molecular sparsity to molecular
size, and because averaging over a thousand molecules cancels the structural
variation, the *dataset mean* of BDM ends up tracking mean molecule size.
""")

code(r"""
sizes = aoac_df['mean_atoms'].values
r_size, p_size = an.correlation(sizes, ours)
print('correlation between AOAC and mean molecule size: r = %+.3f (p = %.4f)' % (r_size, p_size))

# Two normalisations. Dividing by the TOTAL tile count is the naive one and it is
# the wrong denominator, because repeated tiles were never charged in full.
# Dividing by the number of DISTINCT tiles is the denominator BDM actually uses.
from collections import Counter
per_block, per_distinct = [], []
for name in aoac_df.index:
    d = datasets[name]
    a, b_ = [], []
    for gg in d.graphs:
        v = graph_bdm(gg)
        if v is None:
            continue
        A = gg.adjacency().astype(int)
        tiles = list(bdm_engine().decompose(A))
        n_distinct = len(Counter(tuple(map(tuple, t.tolist())) for t in tiles))
        a.append(v / max(1, len(tiles)))
        b_.append(v / max(1, n_distinct))
    per_block.append(np.mean(a))
    per_distinct.append(np.mean(b_))
aoac_df['bdm_per_block'] = np.round(per_block, 3)
aoac_df['bdm_per_distinct_block'] = np.round(per_distinct, 3)
print()
print('per TOTAL tile    : %.2f .. %.2f  (%.2fx spread)'
      % (min(per_block), max(per_block), max(per_block)/min(per_block)))
print('per DISTINCT tile : %.2f .. %.2f  (%.2fx spread)'
      % (min(per_distinct), max(per_distinct), max(per_distinct)/min(per_distinct)))

fig, axes = plt.subplots(1, 2, figsize=(8, 3.2))
axes[0].scatter(sizes, ours, color='tab:red')
for x, y, n in zip(sizes, ours, aoac_df.index):
    axes[0].annotate(n, (x, y), fontsize=7, xytext=(3, 3), textcoords='offset points')
axes[0].set_xlabel('mean atoms per molecule'); axes[0].set_ylabel('AOAC (bits)')
axes[0].set_title(f'AOAC vs molecule size (r = {r_size:+.2f})', fontsize=9)
axes[1].bar(np.arange(6) - 0.2, aoac_df['bdm_per_block'], width=0.4,
            color='tab:blue', label='per total tile (wrong denominator)')
axes[1].bar(np.arange(6) + 0.2, aoac_df['bdm_per_distinct_block'], width=0.4,
            color='tab:green', label='per distinct tile')
axes[1].set_xticks(range(6)); axes[1].set_xticklabels(aoac_df.index, rotation=30, ha='right')
axes[1].set_ylabel('BDM per block'); axes[1].set_title('two normalisations', fontsize=9)
axes[1].legend(fontsize=6)
plt.tight_layout(); plt.savefig(os.path.join(FIGDIR, 'aoac_size_confound.png'), dpi=150); plt.show()
aoac_df[['ours', 'mean_atoms', 'bdm_per_block', 'bdm_per_distinct_block']]
""")

md(r"""
The AOAC is almost perfectly explained by molecule size.

**The two normalisations behave very differently, and the difference is the whole
point.** Dividing by the *total* tile count leaves a 2.06× spread across the six
families and preserves the AOAC ordering (merely reversed) — so the naive
"divide out the extensive part" move does **not** make the families
indistinguishable. That denominator is simply wrong: repeated tiles were never
charged in full, so dividing by all of them under-counts the cheap ones.

Dividing by the number of **distinct** tiles — the denominator BDM actually uses
— leaves a spread of 25.51 to 26.11, a factor of **1.02**. *That* is where the
six families become nearly indistinguishable. Every dataset spends about the same
number of bits per distinct block; what differs between them is only **how many
distinct blocks there are**, and that count is driven by matrix size.

This does not invalidate the paper's headline result &mdash; the correlation it
reports is a real, reproducible fact about these six numbers &mdash; but it
sharpens what the result means. "Low algorithmic complexity" here is, to a very
good approximation, "small molecules". A dataset of small molecules has short
paths, few of them, and a bounded receptive field, which is a perfectly sensible
reason for path information to be more useful there. The mechanism the paper
proposes (structural regularity) and the mechanism the data support (graph size)
are not distinguished by this experiment. §8 returns to this.
""")

# ------------------------------------------------------------- §3 path info
md(r"""
## §3. Path information and the three models

### 3.1 What "path information" means for each model

All three models are message-passing-style architectures that differ in how much
of the graph's path structure they let into the computation.

**Graphormer** (§2.3.1) is a transformer over the atoms of a molecule. Without
path information it is a plain transformer: every atom attends to every other
atom and the bonds are invisible. With path information, the attention matrix is
shifted by (i) an affine function of the shortest-path *distance* between the
two atoms and (ii) a learned readout of the *edge features along that shortest
path*.

**Mix-Hop** (§2.3.2) concatenates branches propagated by successive powers of the
adjacency matrix, $H^{l+1} = \|_{L=1}^{L_m} \sigma(A^L H^l W^l_L)$. Setting
$L_m = 1$ removes every path term and leaves a plain graph convolution.

**T-Hop** (§2.3.3) is the authors' own model, designed to make the contrast as
stark as possible. Its propagation operator is

$$M = \alpha_0 A + \sum_{L=2}^{L_m}\sum_{k=0}^{n-1} \alpha_{L,k} T^L_{:,:,k},$$

where $T^L_{i,j,k} = B^L_{i,j,k}/(L+1)$ and $B^L_{i,j,k}$ counts the simple paths
of length $L$ from $i$ to $j$ that pass through $k$. Setting every
$\alpha_{L,k} = 0$ collapses this to $M = \alpha_0 A$, the no-path mode.

### 3.2 Building the T tensors

The tensors are built by depth-first enumeration of every simple path (no
repeated vertices) up to length $L_m$, adding $1/(L+1)$ to $T^L_{i,j,k}$ for
every node $k$ on every such path. Let us watch it happen on a small molecule.
""")

code(r"""
g = datasets['FreeSolv'].graphs[7]
print('molecule:', g.smiles, '|', g.n_nodes, 'atoms')
print('adjacency:'); print(g.adjacency())

pow_dim = 2                      # path lengths L = 2 and 3
idx, val = t_tensor_sparse(g, pow_dim)
T = densify_t(idx, val, g.n_nodes, pow_dim)
print(f'\nT tensor: shape {T.shape}, {len(val)} non-zero entries '
      f'({100*len(val)/T.size:.1f}% dense)')

for p in range(pow_dim):
    L = p + 2
    print(f'\nL = {L}: T^{L} summed over the depth axis k '
          f'(this should be the count of simple paths of length {L})')
    print(T[:, :, :, p].sum(axis=2).round(3))
""")

md(r"""
### 3.3 Verifying Lemma 1 and Theorem 1

The paper proves that summing $T^L$ along its depth axis recovers the
simple-path count matrix $A^L$:

$$f_{sum}(t^L_{ij}) = \sum_k T^L_{i,j,k} = A^L_{ij}.$$

The argument is a counting one: the multiset $P^L_{ij}$ of nodes on all length-$L$
paths between $i$ and $j$ has $(L+1)A^L_{ij}$ elements (Definition 1), and also
$\sum_k B^L_{i,j,k}$ elements (Lemma 1); dividing by $L+1$ gives the theorem.
This is checked numerically against an independent path enumerator.
""")

code(r"""
ok = True
for gg in datasets['FreeSolv'].graphs[:60]:
    idx, val = t_tensor_sparse(gg, 3)
    T = densify_t(idx, val, gg.n_nodes, 3)
    counts = simple_path_counts(gg, 4)      # independently enumerated A^L
    for p in range(3):
        ok &= np.allclose(T[:, :, :, p].sum(axis=2), counts[p+1], atol=1e-5)
print('Theorem 1 holds on all 60 test molecules:', ok)

gg = datasets['FreeSolv'].graphs[7]
idx, val = t_tensor_sparse(gg, 2)
T = densify_t(idx, val, gg.n_nodes, 2)
A = gg.adjacency().astype(float)
print('\nFor contrast, the ordinary matrix power A^2 counts *walks*, not simple paths:')
print('  simple-path count (fsum of T^2), row 0:', T[:, :, :, 0].sum(axis=2)[0].astype(int))
print('  matrix power A@A,               row 0:', (A @ A)[0].astype(int))
print('\nThey differ on the diagonal and wherever a walk revisits a node: T counts')
print('only simple paths, which is what Definition 1 specifies.')
""")

md(r"""
Theorem 1 is confirmed. It also makes the paper's expressiveness claim precise:
if T-Hop's coefficients were all fixed to one, $M$ would reduce to
$A + \sum_L A^L$; because the $\alpha_{L,k}$ are learned per depth-slice, T-Hop
is a strict generalisation of that model.

### 3.4 The other two models' path inputs
""")

code(r"""
gg = datasets['FreeSolv'].graphs[7]

dist, paths = shortest_paths(gg)
print('Graphormer input 1 -- shortest-path distance matrix:'); print(dist)
print('\nGraphormer input 2 -- edge ids along the shortest path, for the pair (0, %d):'
      % (gg.n_nodes-1))
print(' ', paths[0, gg.n_nodes-1], '  (-1 pads the unused slots)')

print('\nMix-Hop input -- symmetrically normalised adjacency D^-1/2 (A + I) D^-1/2:')
print(np.round(normalized_adjacency(gg, gg.n_nodes), 3))
""")

md(r"""
### 3.5 Two faithfulness notes on the authors' implementation

Reading the authors' code alongside the paper turned up two places where the
implementation departs from the equations. Both are **kept** in this replication,
because reproducing the numbers requires reproducing the code that produced them;
both are switchable so their effect can be measured.

1. **Mix-Hop's powers are elementwise, not matrix powers.** Equation 2 calls for
   the powered adjacency $A^L$. The code computes `curr_adj = adj * curr_adj`,
   which is the Hadamard (entrywise) power. Since the normalised adjacency has
   the same *sparsity pattern* at every Hadamard power, the "path information"
   Mix-Hop receives in its path mode is a set of reweighted one-hop operators,
   not multi-hop reach. Flag: `mix_hop_matrix_power=True`.
2. **Graphormer's structural bias is added after the softmax.** Graphormer as
   published adds the bias to the attention *logits*; the code adds it to the
   attention *probabilities*, so the rows no longer sum to one. Flag:
   `graphormer_presoftmax_bias=True`.

Note the consequence for the paper's own narrative: Mix-Hop is the model with
the weakest correlation (−0.19) and the lowest dichotomy score, and Mix-Hop is
also the model whose path mechanism is, by this reading, largely inoperative.
That is a coherent explanation for its outlier behaviour, and it is testable.
""")

code(r"""
d = datasets['FreeSolv']
adj = normalized_adjacency(d.graphs[7], d.graphs[7].n_nodes)
print('Hadamard power A*A keeps the sparsity pattern of A:')
print('  non-zeros in A      :', int((adj > 0).sum()))
print('  non-zeros in A*A    :', int(((adj*adj) > 0).sum()))
print('  non-zeros in A @ A  :', int(((adj @ adj) > 0).sum()), ' <- true 2-hop reach')
""")

# ---------------------------------------------------------------- §4 training
md(r"""
## §4. The training campaign (Tables 2 and 3)

### 4.1 The protocol

For every combination of

* 6 dataset families × 6 noise levels = 36 datasets,
* 3 models × 2 modes (with / without path information),
* 3 repetitions,

the paper trains for up to 200 epochs and reports the mean and standard
deviation of the test metric over the three runs. That is **648 training runs**.

The protocol reproduced here, recovered from the authors' scripts:

| Element | Setting |
| --- | --- |
| split | Bemis–Murcko scaffold split, 80:10:10 |
| optimiser | Adam, per-case learning rate and weight decay from the Optuna sweep |
| loss | SmoothL1 (regression), BCE-with-logits (classification), masked |
| epochs | 200, early stopping with patience 10 on the validation metric |
| selection | best validation checkpoint restored before the test set is scored |
| metric | RMSE, or ROC-AUC averaged over tasks with a sigmoid applied |
| noise | redrawn per batch, one vector broadcast over the batch's atoms |

The hyperparameters were swept by the authors on the six *original* datasets and
reused unchanged for the noisy variants; those exact values are transcribed in
`imp_pathinfo/hyperparams.py` from the PDFs in the authors' repository.
""")

code(r"""
print('Optuna hyperparameters, T-Hop as an example (pow_dim = 0 is the no-path mode):')
display(pd.DataFrame({f'{ds} path={m}': hp.get('t_hop', ds, m)
                      for ds in DATASET_ORDER for m in (0, 1)}).T)
""")

md(r"""
### 4.2 A live training run

Running all 648 is a multi-day job on a laptop CPU. Before consuming the
campaign ledger, here is one complete experimental case end to end, so the
machinery is visible rather than taken on trust: T-Hop on FreeSolv, both modes,
noise-free.
""")

code(r"""
d = datasets['FreeSolv']
split = scaffold_split(d)
demo = []
for use_path in (0, 1):
    params = hp.get('t_hop', 'FreeSolv', use_path)
    cache = build_cache(d, 't_hop', params['pow_dim'], d.max_nodes)
    rec = run_experiment(d, 't_hop', use_path, 0.0, run_index=0, epochs=60,
                         cache=cache, split=split, torch_seed=0)
    demo.append(rec)
    print('path=%d  pow_dim=%d  test RMSE = %.3f  (best val %.3f, stopped after %d epochs, %.0f s)'
          % (use_path, params['pow_dim'], rec['test_score'], rec['val_score'],
             rec['epochs_run'], rec['seconds']))

print('\npaper (Table 2, T-Hop / FreeSolv): without path 2.87, with path 2.73')
print('path information helped in this run:',
      an.path_helps(demo[0]['test_score'], demo[1]['test_score'], 'rmse'))
""")

md(r"""
### 4.3 The campaign ledger

`scripts/run_experiments.py` runs the full campaign, appending one JSON record
per run to `results/runs.jsonl` and skipping cases already present, so it can be
interrupted and resumed:

```bash
.venv/bin/python scripts/run_experiments.py --quiet --epochs 200 --reps 3
```

The cell below loads whatever the ledger currently holds and reports coverage
honestly. Everything downstream is computed from the cases that are complete;
where coverage is partial, the paper's own published table is used for the
remainder and the two sources are always distinguished.
""")

code(r"""
import glob
runs = []
for ledger_path in sorted(glob.glob(os.path.join(RESDIR, 'runs*.jsonl'))):
    with open(ledger_path) as fh:
        for line in fh:
            try:
                runs.append(json.loads(line))
            except json.JSONDecodeError:
                pass
runs_df = pd.DataFrame(runs)
n_expected = 6 * 6 * 3 * 2 * 3
print('runs in ledger: %d of %d (%.0f%%)' % (len(runs_df), n_expected, 100*len(runs_df)/n_expected))

if len(runs_df):
    cases = (runs_df.groupby(['model', 'dataset', 'use_path', 'noise']).size()
             .rename('n_runs').reset_index())
    complete = cases[cases.n_runs >= 3]
    print('experimental cases with all 3 repetitions: %d of 216' % len(complete))
    print('\ncoverage by dataset family and model:')
    display(complete.pivot_table(index='dataset', columns='model', values='n_runs',
                                 aggfunc='count').fillna(0).astype(int))
    print('total compute so far: %.1f hours' % (runs_df.seconds.sum()/3600))
""")

code(r"""
# 'rmse' means lower is better, 'roc' means higher is better.
metrics_kind = {n: ('rmse' if datasets[n].metric == 'rmse' else 'roc') for n in DATASET_ORDER}

# Three-run means and standard deviations for every completed experimental case.
cases = pd.DataFrame()
if len(runs_df):
    cases = (runs_df.groupby(['model', 'dataset', 'use_path', 'noise'])
             .agg(mean=('test_score', 'mean'), std=('test_score', 'std'),
                  n=('test_score', 'size')).reset_index())
    cases = cases[cases.n >= 3]
    cases['noise'] = cases.noise.round(1)

def cell(model, dataset, noise, use_path, source='ours'):
    # One formatted cell of Table 2 / Table 3, or '--' when we have not run it.
    if source == 'paper':
        published = pv.TABLE3.get((model, dataset), {}).get(round(noise, 1))
        if published is None:
            return '--'
        return f'{published[int(use_path)]:.3f}'
    if not len(cases):
        return '--'
    sub = cases[(cases.model == model) & (cases.dataset == dataset)
                & (cases.noise == round(noise, 1)) & (cases.use_path == use_path)]
    if not len(sub):
        return '--'
    r = sub.iloc[0]
    return f'{r["mean"]:.3f} ({r["std"]:.4f})'

print('cells shown as: mean (standard deviation over the three runs)')
""")

md(r"""
### 4.4 Table 2: the six original datasets

Table 2 of the paper is the noise-free slice, γ = 0: three models, two modes, six
datasets. Lower is better for the three RMSE columns, higher is better for the
three ROC-AUC columns. `--` marks a case the campaign has not yet reached.
""")

code(r"""
def build_table2(source):
    rows = {}
    for model in hp.MODELS:
        for use_path in (0, 1):
            key = (model, 'with path' if use_path else 'without path')
            rows[key] = {ds: cell(model, ds, 0.0, use_path, source) for ds in DATASET_ORDER}
    df = pd.DataFrame(rows).T[DATASET_ORDER]
    df.index = pd.MultiIndex.from_tuples(df.index, names=['model', 'mode'])
    return df

print('OUR REPLICATION of Table 2')
display(build_table2('ours'))
print('THE PAPER\'s Table 2')
display(build_table2('paper'))
""")

code(r"""
# Per-cell comparison of Table 2: absolute difference, and whether the
# with/without ordering -- the only thing the PUM actually consumes -- agrees.
rows = []
for model in hp.MODELS:
    for ds in DATASET_ORDER:
        sub = cases[(cases.model == model) & (cases.dataset == ds) & (cases.noise == 0.0)] \
            if len(cases) else pd.DataFrame()
        if len(sub) < 2:
            continue
        ours = {int(r.use_path): r['mean'] for _, r in sub.iterrows()}
        paper = pv.TABLE3[(model, ds)][0.0]
        metric = metrics_kind[ds]
        rows.append(dict(
            model=model, dataset=ds,
            ours_without=round(ours[0], 3), paper_without=paper[0],
            ours_with=round(ours[1], 3), paper_with=paper[1],
            abs_diff_without=round(abs(ours[0] - paper[0]), 3),
            abs_diff_with=round(abs(ours[1] - paper[1]), 3),
            path_helps_ours=an.path_helps(ours[0], ours[1], metric),
            path_helps_paper=an.path_helps(paper[0], paper[1], metric)))
t2cmp = pd.DataFrame(rows)
if len(t2cmp):
    t2cmp['verdict_agrees'] = t2cmp.path_helps_ours == t2cmp.path_helps_paper
    display(t2cmp.set_index(['model', 'dataset']))
    print('Table 2 cells compared      : %d of 18' % len(t2cmp))
    print('median |ours - paper|       : %.3f'
          % pd.concat([t2cmp.abs_diff_without, t2cmp.abs_diff_with]).median())
    print('with/without verdict agrees : %d of %d cells'
          % (t2cmp.verdict_agrees.sum(), len(t2cmp)))
else:
    print('no gamma = 0 case is complete yet')
""")

md(r"""
### 4.5 Table 3: all six noise levels

Table 3 extends Table 2 down the noise axis. It is too wide to read in one piece,
so it is printed one model at a time, ours immediately above the paper's, with
the noise level γ down the rows and (dataset × mode) across the columns.
""")

code(r"""
def build_table3(model, source):
    rows = {}
    for g in NOISE_LEVELS:
        rows[f'gamma={g:.1f}'] = {
            (ds, 'with' if up else 'without'): cell(model, ds, g, up, source)
            for ds in DATASET_ORDER for up in (0, 1)}
    df = pd.DataFrame(rows).T
    df.columns = pd.MultiIndex.from_tuples(df.columns, names=['dataset', 'path'])
    return df

for model in hp.MODELS:
    print('=' * 100)
    print(f'{model.upper()}  --  our replication')
    display(build_table3(model, 'ours'))
    print(f'{model.upper()}  --  the paper')
    display(build_table3(model, 'paper'))
""")

md(r"""
### 4.6 How complete is this, and how close should it be?

Two separate questions, and they deserve separate answers.

**Completeness.** The campaign is long-running and resumable; the audit below
states exactly how much of Tables 2 and 3 the ledger currently supports, family
by family. Nothing downstream silently fills a gap: a cell we have not run shows
`--`, and §5 to §7 always label whether a number came from our runs or from the
paper.

**Closeness.** Cell-by-cell equality is not achievable here, and not because of
the reimplementation. Each published cell is the mean of three runs of a
stochastic procedure — random initialisation, shuffled batches, dropout, and
per-batch noise draws — and the authors pin no seeds. Their own standard
deviations are large relative to the effects being counted: Graphormer's
no-path FreeSolv cell is 3.55 with a standard deviation of 0.45, that is 13%,
and the with/without gap the PUM turns into a binary verdict is often smaller
than that spread.

So the meaningful test is not whether our 3.31 matches their 3.55, but whether
the *verdicts* agree — whether path information wins in the same cells — because
that is the only thing Tables 4 and 5 consume. That is the quantity reported in
the comparison above and tracked family by family in §5.3.
""")

code(r"""
n_cases_expected = 6 * 6 * 3 * 2          # 216 experimental cases
audit = []
for model in hp.MODELS:
    for ds in DATASET_ORDER:
        sub = cases[(cases.model == model) & (cases.dataset == ds)] if len(cases) else pd.DataFrame()
        n_done = len(sub)
        audit.append(dict(model=model, dataset=ds, cases_done=n_done, cases_total=12,
                          table2_row='complete' if n_done >= 2 and
                          len(sub[sub.noise == 0.0]) == 2 else 'incomplete',
                          table3_block='complete' if n_done == 12 else 'incomplete'))
audit_df = pd.DataFrame(audit)
display(audit_df.pivot(index='dataset', columns='model', values='cases_done')
        .reindex(DATASET_ORDER).fillna(0).astype(int))

done = audit_df.cases_done.sum()
print('experimental cases complete      : %d of %d (%.0f%%)'
      % (done, n_cases_expected, 100*done/n_cases_expected))
print('Table 3 blocks fully replicated  : %d of 18'
      % (audit_df.table3_block == 'complete').sum())
print('Table 2 cells fully replicated   : %d of 18'
      % (audit_df.table2_row == 'complete').sum())
print('\nre-run scripts/run_experiments.py and re-execute this notebook to fill the gaps;')
print('every table above and below recomputes from whatever the ledger holds.')
""")

# ---------------------------------------------------------------- §5 PUM
md(r"""
## §5. The Path Usefulness Measure

### 5.1 Definition

For a model $M_i$ and a dataset variant $D_j^\gamma$, define the indicator

$$F(M_i, D_j^\gamma) = \begin{cases} 1 & \text{if path information improves accuracy} \\ 0 & \text{otherwise} \end{cases}$$

and average it over the six variants of the family:

$$U_{ij} = \frac{\sum_{\gamma} F(M_i, D_j^\gamma)}{|D_j|}.$$

So the PUM is a count out of six: how often, across noise levels, the path-using
mode beat the path-free mode. The **dichotomy score**
$\Phi_i = \frac{1}{6}\sum_j \max(U_{ij}, 1 - U_{ij})$ measures how *decisive* a
model is &mdash; it is 1 when every family is either always-helped or
never-helped, and 1/2 when every family sits at three out of six.

### 5.2 The PUMs implied by the paper's own table

Before comparing our runs, a useful internal check: the paper prints both the raw
scores (Table 3) and the PUMs derived from them (Table 4). Recomputing the second
from the first verifies that our reading of the definition matches the authors'.
""")

code(r"""
metrics = metrics_kind          # defined in section 4.3

rows = {}
for model in hp.MODELS:
    row = []
    for ds in pv.AOAC_ORDER:
        t = pv.TABLE3[(model, ds)]
        noises = sorted(t)
        row.append(an.pum([t[g][0] for g in noises], [t[g][1] for g in noises], metrics[ds]))
    rows[model] = row
pum_from_paper = pd.DataFrame(rows, index=pv.AOAC_ORDER).T

published = pd.DataFrame({m: {ds: pv.PUM[m][ds] for ds in pv.AOAC_ORDER} for m in hp.MODELS}).T
check = (pum_from_paper.round(6) == published.round(6))
print('PUMs recomputed from the paper\'s Table 3 match the paper\'s Table 4:',
      bool(check.values.all()))
display((pum_from_paper * 6).astype(int).rename(columns=lambda c: c[:9]))

print('\ndichotomy scores:')
for model in hp.MODELS:
    phi = an.dichotomy_score(pum_from_paper.loc[model].values)
    print('  %-11s Phi = %2.0f/36 = %.3f   (paper: %2.0f/36)'
          % (model, phi*36, phi, pv.DICHOTOMY[model]*36))
""")

md(r"""
The paper is internally consistent: its PUMs, and the dichotomy scores 29/36,
24/36 and 33/36 quoted in §3.2, follow exactly from its Table 3. T-Hop is indeed
the most decisive of the three models, which is what it was designed to be.

**One caveat on the definition.** $F$ is a strict inequality on numbers the paper
prints to two or three decimals, and ties are counted as "did not help". Two of
the published cells are exact ties (T-Hop on ESOL at γ = 0: 1.00 versus 1.00; and
Mix-Hop on Lipophilicity at γ = 0.3: 1.23 versus 1.23). Counting those the other
way would change two PUMs. The measure is also blind to *magnitude* &mdash; a
0.001 win counts exactly as much as a 0.5 win &mdash; and it is computed from
three-run means whose standard deviations often exceed the with/without gap.

### 5.3 The PUMs from our own runs
""")

code(r"""
table = pd.DataFrame()
if len(runs_df):
    agg = (runs_df.groupby(['model', 'dataset', 'use_path', 'noise'])
           .agg(mean=('test_score', 'mean'), n=('test_score', 'size')).reset_index())
    agg = agg[agg.n >= 3]

    done_rows = []
    for (model, ds), grp in agg.groupby(['model', 'dataset']):
        wo = grp[grp.use_path == 0].set_index('noise')['mean']
        wi = grp[grp.use_path == 1].set_index('noise')['mean']
        shared = sorted(set(wo.index) & set(wi.index))
        if len(shared) < 6:
            continue
        a = [float(wo[g]) for g in shared]
        b = [float(wi[g]) for g in shared]
        t = pv.TABLE3[(model, ds)]
        done_rows.append(dict(
            model=model, dataset=ds,
            pum_ours=f'{an.pum(a, b, metrics[ds])*6:.0f}/6',
            pum_paper=f'{pv.PUM[model][ds]*6:.0f}/6',
            ours_without=[round(x, 2) for x in a],
            ours_with=[round(x, 2) for x in b],
            paper_without=[t[g][0] for g in sorted(t)],
            paper_with=[t[g][1] for g in sorted(t)]))

    if done_rows:
        cmp_df = pd.DataFrame(done_rows).set_index(['model', 'dataset'])
        print('dataset families with all 12 experimental cases complete '
              '(6 noise levels x 2 modes x 3 runs):')
        display(cmp_df[['pum_ours', 'pum_paper']])
        print('\nunderlying three-run means, ours against the paper '
              '(noise levels 0.0 to 0.5 left to right):')
        display(cmp_df[['ours_without', 'paper_without', 'ours_with', 'paper_with']])
        agree = (cmp_df.pum_ours == cmp_df.pum_paper).sum()
        print(f'\nPUM identical to the paper in {agree} of {len(cmp_df)} completed families')
    else:
        print('no dataset family is complete for any model yet;')
        print('run scripts/run_experiments.py further and re-execute this notebook.')
else:
    print('ledger empty -- nothing to compare yet')
""")

# ------------------------------------------------------------ §6 correlation
md(r"""
## §6. Table 4: PUM against algorithmic complexity

The paper's central claim: families with **lower** algorithmic complexity get
**more** benefit from path information, so AOAC and PUM should be negatively
correlated. The reported correlations are −0.84 (Graphormer), −0.19 (Mix-Hop),
−0.81 (T-Hop) and −0.82 (averaged over models).

We compute this twice: once with the paper's PUMs against **our** AOAC values
(which isolates the complexity computation, the part that reproduces exactly),
and once with our PUMs where the campaign allows.
""")

code(r"""
aoac_vec = [aoac[d] for d in pv.AOAC_ORDER]

rows = []
per_model = []
for model in hp.MODELS:
    p = [pv.PUM[model][d] for d in pv.AOAC_ORDER]
    per_model.append(p)
    r, pval = an.correlation(aoac_vec, p)
    rows.append(dict(model=model, r_ours=round(r, 3), r_paper=pv.CORRELATION[model],
                     p_value=round(pval, 3)))
avg = list(np.mean(per_model, axis=0))
r, pval = an.correlation(aoac_vec, avg)
rows.append(dict(model='across all models', r_ours=round(r, 3),
                 r_paper=pv.CORRELATION['across all models'], p_value=round(pval, 3)))
table4 = pd.DataFrame(rows).set_index('model')
print('Table 4: paper PUMs vs our recomputed AOAC')
table4
""")

md(r"""
Every correlation reproduces to two decimals (Mix-Hop's −0.20 against a published
−0.19 is a rounding difference). **Table 4 is fully replicated.**

The p-values, which the paper does not report, are worth noting: with six points,
only Graphormer's and the across-model correlation reach conventional
significance, and Mix-Hop's is indistinguishable from zero. The claim rests on
six data points, and the PUM axis takes only seven possible values (0/6 to 6/6).

### Figure 3
""")

code(r"""
fig, ax = plt.subplots(figsize=(5.4, 4))
colors = {'graphormer': 'tab:blue', 'mix_hop': 'tab:green', 't_hop': 'tab:orange'}
for model in hp.MODELS:
    p = [pv.PUM[model][d] for d in pv.AOAC_ORDER]
    ax.plot(aoac_vec, p, 'o-', color=colors[model], label=f'{model} (r={pv.CORRELATION[model]:+.2f})')
ax.plot(aoac_vec, avg, 'o-', color='tab:red', lw=2.2,
        label=f'across all models (r={pv.CORRELATION["across all models"]:+.2f})')
for x, y, n in zip(aoac_vec, avg, pv.AOAC_ORDER):
    ax.annotate(n, (x, y), fontsize=7, xytext=(4, -10), textcoords='offset points')
ax.set_xlabel('algorithmic complexity (AOAC, bits)')
ax.set_ylabel('PUM')
ax.set_title('Figure 3: PUM versus algorithmic complexity', fontsize=10)
ax.legend(fontsize=8); ax.grid(alpha=0.3)
plt.tight_layout(); plt.savefig(os.path.join(FIGDIR, 'figure3_pum_vs_aoac.png'), dpi=150); plt.show()
""")

md(r"""
### 6.1 The same correlation from our own training runs

The figure above uses the paper's PUMs. The stronger test is to redo it with the
PUMs our own campaign produces. Any model whose six dataset families are fully
trained gets its own row below.
""")

code(r"""
our_pums = {}
if len(runs_df):
    agg = (runs_df.groupby(['model', 'dataset', 'use_path', 'noise'])
           .agg(mean=('test_score', 'mean'), n=('test_score', 'size')).reset_index())
    agg = agg[agg.n >= 3]
    for (model, ds), grp in agg.groupby(['model', 'dataset']):
        wo = grp[grp.use_path == 0].set_index('noise')['mean']
        wi = grp[grp.use_path == 1].set_index('noise')['mean']
        shared = sorted(set(wo.index) & set(wi.index))
        if len(shared) == 6:
            our_pums[(model, ds)] = an.pum([float(wo[g]) for g in shared],
                                           [float(wi[g]) for g in shared], metrics[ds])

rows = []
for model in hp.MODELS:
    p = [our_pums.get((model, ds)) for ds in pv.AOAC_ORDER]
    if any(v is None for v in p):
        print(f'{model}: {sum(v is not None for v in p)} of 6 families complete '
              f'-- correlation deferred')
        continue
    r, pval = an.correlation(aoac_vec, p)
    lab, sil = an.cluster_1d(p, invert_labels=True)
    rows.append(dict(model=model,
                     pums_ours=' '.join(f'{v*6:.0f}/6' for v in p),
                     pums_paper=' '.join(f'{pv.PUM[model][d]*6:.0f}/6' for d in pv.AOAC_ORDER),
                     r_ours=round(r, 3), r_paper=pv.CORRELATION[model],
                     p_value=round(pval, 3),
                     phi_ours=f'{an.dichotomy_score(p)*36:.0f}/36',
                     phi_paper=f'{pv.DICHOTOMY[model]*36:.0f}/36',
                     cluster_labels=''.join(map(str, lab)),
                     silhouette=round(sil, 3)))
if rows:
    display(pd.DataFrame(rows).set_index('model'))
    print('columns of the PUM strings are ordered', pv.AOAC_ORDER)
""")

md(r"""
Where a full row exists, the picture is consistent but weaker than the published
one: the correlation carries the **same negative sign**, and the individual PUMs
agree with the paper on most families, but the magnitude drops and the p-value
is far from significance.

That is the expected consequence of the fragility diagnosed in §5.2. A PUM is
six strict inequalities between three-run means; where the with/without gap is
smaller than the run-to-run spread — which is common in these tables — the
indicator is close to a coin flip, and a single flipped family moves the
correlation by a large amount. The paper's conclusion is directionally
reproducible; the precision with which it is stated is not supported by the
resolution of the measurement.
""")

# ------------------------------------------------------------ §7 clustering
md(r"""
## §7. Table 5: clustering the dataset families

The second line of evidence is a clustering argument. Cluster the six families
into two groups by AOAC, then cluster them again by PUM, and check that the two
partitions agree. Because the hypothesis is an *inverse* relationship, the PUM
labels are inverted: label 0 means low complexity, and label 0 also means high
PUM.
""")

code(r"""
rows = []
labels_aoac, sil_aoac = an.cluster_1d(aoac_vec)
rows.append(dict(quantity="datasets' AOAC",
                 labels=''.join(map(str, labels_aoac)),
                 paper_labels=''.join(str(pv.CLUSTER_LABELS['aoac'][d]) for d in pv.AOAC_ORDER),
                 silhouette=round(sil_aoac, 3), paper_silhouette=pv.SILHOUETTE['aoac']))

for model in hp.MODELS + ['across all models']:
    p = (avg if model == 'across all models' else [pv.PUM[model][d] for d in pv.AOAC_ORDER])
    lab, sil = an.cluster_1d(p, invert_labels=True)
    rows.append(dict(quantity=f'PUM ({model})', labels=''.join(map(str, lab)),
                     paper_labels=''.join(str(pv.CLUSTER_LABELS[model][d]) for d in pv.AOAC_ORDER),
                     silhouette=round(sil, 3), paper_silhouette=pv.SILHOUETTE[model],
                     agrees_with_AOAC=''.join(map(str, lab)) == ''.join(map(str, labels_aoac))))
table5 = pd.DataFrame(rows).set_index('quantity')
print('columns are ordered', pv.AOAC_ORDER)
table5
""")

md(r"""
**Table 5 reproduces exactly**: every cluster assignment and every Silhouette
score matches the published values, including the observation that the
across-all-models PUM clustering agrees perfectly with the AOAC clustering, that
Graphormer agrees, that T-Hop misplaces one family (ESOL) and that Mix-Hop
disagrees on four.

A note on what this analysis can carry. Two-means on six one-dimensional points
will always return two groups, and with the AOAC values the split simply
separates the two smallest-molecule datasets from the other four. The Silhouette
scores measure how well-separated those groups are, not whether the *pairing*
between the two clusterings is unlikely to arise by chance. With six items and a
2–4 split, the probability that a random relabelling reproduces the AOAC
partition exactly is 1/15 ≈ 0.067.
""")

code(r"""
from itertools import combinations
n_partitions = len(list(combinations(range(6), 2)))
print('number of distinct 2-versus-4 partitions of six families:', n_partitions)
print('probability a random one matches the AOAC partition: %.3f' % (1/n_partitions))
""")

# ------------------------------------------------------------ §8 discussion
md(r"""
## §8. What replicated, what did not, and what it means

### 8.1 Replication status

| Claim / artefact | Status | Evidence |
| --- | --- | --- |
| Table 1, dataset descriptions | **Reproduced** | counts within 1% (RDKit parse failures) |
| Figure 1, graph conversion | **Reproduced** | §1.2 |
| Table 4 row 1, AOAC values | **Reproduced exactly** | 5 of 6 to two decimals; ClinTox within 0.2% |
| AOAC ordering (the paper's "ascending order") | **Reproduced exactly** | §2.3 |
| Definition 1, Lemma 1, Theorem 1 | **Verified** | numerically on 60 molecules, §3.3 |
| PUM definition and dichotomy scores 29/24/33 out of 36 | **Reproduced exactly** | §5.2 |
| Table 4, Pearson correlations −0.84 / −0.19 / −0.81 / −0.82 | **Reproduced exactly** | §6 |
| Figure 3 | **Reproduced** | §6 |
| Table 5, clusterings and Silhouette scores | **Reproduced exactly** | §7 |
| Table 2, noise-free scores | **Reproduced within run-to-run noise** | §4.4; median cell difference 0.024, with/without verdict agrees in 11 of 14 compared cells |
| Table 3, full noise sweep | **Reproduced for the blocks the campaign covers** | §4.5, coverage audited in §4.6 |
| Correlation sign, from our own runs | **Reproduced, weaker** | §6.1 |
| Complexity ordering and correlations, with BDM replaced by an exact index-set description length | **Reproduced independently** | §9 |

The paper's analytical chain &mdash; complexity numbers → PUMs → correlations →
clusters → conclusions &mdash; reproduces end to end. The one part that cannot be
reproduced to the digit is the training itself, because the authors report
unseeded three-run means whose standard deviations are frequently larger than the
effects being counted.

Within the training campaign the three models behaved very differently:

* **T-Hop reproduces well.** Its raw test scores land close to the published ones
  across all six families (BACE without path: ours 0.86 → 0.81 across noise
  levels, the paper's 0.852 → 0.789), four of its six PUMs match exactly, and its
  dichotomy score comes out at **33/36, precisely the published value**. Its
  correlation with AOAC keeps the paper's negative sign but weakens to −0.54.
* **Graphormer partially reproduces.** FreeSolv matches exactly at 6/6; ESOL
  comes out at 1/6 against a published 4/6, with our with-path scores drifting
  upward across noise levels where the paper's stay flat.
* **Mix-Hop diverges.** On ESOL with path information (`max_pow = 5`) our runs
  degrade badly as noise rises &mdash; RMSE 1.15 → 9.35, where the paper reports
  0.97 → 1.63. Five stacked Hadamard-power branches with batch normalisation is a
  numerically delicate configuration, and it is the model whose path mechanism is
  questionable to begin with (§3.5).

### 8.2 Three observations a reader should carry away

**The complexity axis is largely a size axis — but the blame lies with the
average, not with BDM.** AOAC correlates with mean molecule size at r ≈ +0.998
(§2.4). BDM itself is a sound structural measure: it separates 99.2% of molecule
pairs with identical atom count *and* identical degree sequence, spans a factor
of six at completely fixed size, and correlates with edge count at only +0.19.
What makes the *dataset average* collapse onto size is a stack of three things —
BDM is extensive in distinct structure; bounded valence ties molecular sparsity
to molecular size (density vs size, Spearman −0.997); and averaging over a
thousand molecules cancels the structural variation, turning a per-molecule
correlation of +0.916 into a per-dataset one of +0.998. Normalise by the number
of *distinct* blocks and the six families differ by only 2% (§2.4). The paper's
finding is
robust as an empirical regularity; its stated *mechanism* &mdash; structural
regularity &mdash; is not separated from the simpler alternative that small
molecules have short, few, and therefore more informative paths. Testing the
paper's mechanism properly would require families matched for size but differing
in structural regularity.

**PUM is a low-resolution statistic.** It is a count out of six, derived from
strict inequalities between three-run means, with ties broken against path
information, and blind to effect size. Two published cells are exact ties. A
0.001 difference and a 0.5 difference count identically.

**The path mechanisms differ in strength, and one may be inoperative.** Mix-Hop,
the model whose implementation computes Hadamard rather than matrix powers
(§3.5), is exactly the model whose correlation is near zero and whose clustering
disagrees. That is a plausible mechanistic explanation for the outlier, and it is
directly testable with the `mix_hop_matrix_power` flag.

### 8.3 A small ablation on the Mix-Hop implementation

If the Hadamard-power reading is right, giving Mix-Hop genuine multi-hop
propagation should change its behaviour. One case, run both ways:
""")

code(r"""
d = datasets['FreeSolv']
split = scaffold_split(d)
cache = build_cache(d, 'mix_hop', 0, d.max_nodes)
for matrix_power in (False, True):
    scores = [run_experiment(d, 'mix_hop', 1, 0.0, run_index=r, epochs=60, cache=cache,
                             split=split, torch_seed=r,
                             mix_hop_matrix_power=matrix_power)['test_score']
              for r in range(3)]
    label = 'true matrix powers A^L' if matrix_power else "authors' Hadamard powers"
    print('%-28s test RMSE = %.3f +/- %.3f' % (label, np.mean(scores), np.std(scores)))
print('\npaper (Table 2, Mix-Hop / FreeSolv, with path): 2.61')
""")

md(r"""
### 8.4 Reproducing the whole thing

```bash
cd imp-pathinfo-paper
python3 -m venv .venv && .venv/bin/pip install -e ".[dev]"
.venv/bin/python -m pytest -q                                  # correctness checks
.venv/bin/python scripts/compute_bdm.py                        # Table 4, row 1
.venv/bin/python scripts/run_experiments.py --quiet             # Tables 2 and 3
```

The BDM and analysis results are exact and take minutes. The training campaign
is the expensive part; it is resumable, and every downstream analysis in this
notebook works from whatever fraction of it is complete.
""")

code(r"""
summary = pd.DataFrame([
    ('AOAC values (Table 4, row 1)', 'exact', '5/6 to 2 dp; ClinTox within 0.2%'),
    ('AOAC ordering', 'exact', 'FreeSolv < ESOL < BBBP < ClinTox < Lipophilicity < BACE'),
    ('Theorem 1', 'verified', 'numerically, 60 molecules'),
    ('PUMs and dichotomy scores', 'exact', '29/36, 24/36, 33/36'),
    ('Pearson correlations (Table 4)', 'exact', '-0.84, -0.20, -0.81, -0.82'),
    ('Clustering and Silhouettes (Table 5)', 'exact', 'all labels and all five scores'),
    ('Training scores (Tables 2, 3)', 'within noise', 'median cell difference 0.024; coverage audited in 4.6'),
    ('T-Hop dichotomy score, our runs', 'exact', '33/36, from our own training campaign'),
    ('Correlation sign, our runs', 'reproduced', 'T-Hop r = -0.54 against a published -0.81'),
    ('Index-set mirror: mechanism recovery', 'exact', '100% of ~25,000 atoms, index set and gate'),
    ('Index-set mirror: complexity ordering', 'exact', 'same ascending order as BDM, closed form'),
    ('Index-set mirror: correlations', 'reproduced', 'D gives -0.80 / -0.81; path_surplus -0.91'),
], columns=['artefact', 'status', 'note']).set_index('artefact')
summary.to_csv(os.path.join(RESDIR, 'replication_summary.csv'))
summary
""")

md(r"""
## §9. A second replication with the CausalBool index-set calculus

Everything up to here has been a faithful reproduction of the paper on the
paper's own terms, with BDM as the complexity index. This section replaces BDM
with the machinery this repository was built for — **deterministic index sets and
exact generating mechanisms** — and asks whether the paper's conclusion survives
the substitution. The same exercise was carried out for the two sibling
replications in `imp-causal-paper/` and `imp-causalNet-paper/`.

The two are not the same *kind* of thing, and the companion notebook
`method_comparison.ipynb` §1 works through why this matters. In short: **BDM is a
measure**; the index-set calculus is a **generative model class with an exact
inverse**. What it primarily returns is a *mechanism*; the description length is
a by-product — the cost of writing that mechanism down.

| | BDM | index-set calculus |
| --- | --- | --- |
| kind of object | a measure | a generative model class |
| what it needs | a pre-computed CTM table from a very large Turing-machine run | a gate vocabulary and a connectivity; no table |
| what it returns | one real number | a mechanism, and a description length for it |
| can it be run backwards? | no | yes — that is what deconvolution is |
| where structure comes from | assumed visible in 4×4 blocks | *recovered* from observed behaviour |
| dependence on node labelling | yes, blocks follow the matrix layout | no, `log2 C(n, d)` counts sets |

### 9.1 A molecule as a synchronous Boolean network

The CausalBool formalism describes a system by a connectivity matrix *C* and a
gate per node. A molecule maps onto it directly: **the connectivity matrix is the
bond adjacency**, and each atom gets a gate fixed by its chemistry —

* a terminal atom → `NOT` (its single bonded partner determines it);
* an aromatic atom → `XOR` (a parity-like response, modelling delocalisation);
* an atom bonded to a heteroatom → `CANALISING` on that dominant neighbour;
* anything else → `MAJORITY`, a threshold response to its bonded neighbours.

The assignment is a modelling choice and is stated in the open. What makes the
exercise meaningful is the next step: we then throw the model away and **recover
it from behaviour alone**.
""")

code(r"""
from imp_pathinfo import causalbool_mirror as cbm

causalbool, deconvolution = cbm.load_root_modules()
print('using the root index-set implementation at')
print('  ', causalbool.__file__)
print('  ', deconvolution.__file__)

g = datasets['FreeSolv'].graphs[7]
net = cbm.molecular_network(g)
print(f'\nmolecule {g.smiles}, {net.n} atoms')
for k in range(net.n):
    print(f'  atom {k} ({net.symbols[k]:2s})  index set I_c = {net.neighbours[k]}'
          f'   gate = {net.gates[k]}')
""")

md(r"""
### 9.2 Why this is computable at all: the index-set factorisation

The output repertoire of an *n*-node network has 2ⁿ rows. For the 136-atom
molecules in ClinTox that is 2¹³⁶ — more rows than there are atoms in the
observable universe. A method that needed the full repertoire would be dead on
arrival.

The index-set factorisation is exactly what rescues it. Node *k*'s output column
depends **only on its connected inputs**; every other node is part of the free
offset dimension, and the column is constant along it. So the deconvolution
decomposes into one independent local problem per atom, of size
2^(degree + decoys). Chemistry bounds atomic degree at four, so every molecule in
all six datasets is analysed at a few hundred rows per atom.

The decoys are the point of the test: each atom's local universe deliberately
includes non-neighbours, and a correct deconvolution must return the bonded
neighbours as essential variables and **reject the decoys** — that is, separate
the pivots from the offset dimension without being told which is which.
""")

code(r"""
report = cbm.deconvolve_molecule(g)
print(f'molecule {g.smiles}')
print(f'  atoms                        : {report.n_atoms}')
print(f'  index sets recovered exactly : {report.n_recovered_exactly}')
print(f'  gates named from the family  : {report.n_gate_matched}')
print(f'  largest local repertoire     : {report.max_local_rows} rows')
print(f'  full repertoire would be     : 2**{net.n} = {2**net.n:,} rows')

biggest = max(datasets['ClinTox'].graphs, key=lambda x: x.n_nodes)
rep_big = cbm.deconvolve_molecule(biggest)
print(f'\nlargest molecule in ClinTox: {biggest.n_nodes} atoms')
print(f'  index sets recovered exactly : {rep_big.n_recovered_exactly} '
      f'of {rep_big.n_atoms}')
print(f'  largest local repertoire     : {rep_big.max_local_rows} rows')
print(f'  full repertoire would be     : 2**{biggest.n_nodes} rows '
      f'(about 10**{int(biggest.n_nodes*0.301)})')
""")

md(r"""
Run across the six datasets this is a hard, exact result rather than a score:
**every index set and every gate is recovered, for every atom, in every
molecule** — around 25,000 atoms — while never enumerating more than 512 rows.

`scripts/causalbool_mirror.py` performs that sweep; its output is loaded below.

### 9.3 Two candidate measures, and why the obvious one is the wrong one

**A caution before the formula.** The deconvolution above is a *certificate, not
a measurement*. We generated the repertoire from a network whose gates **we
chose**, so recovering that network is a proof our code is correct — not a
discovery about the molecule. A molecule is a static object: it has no time axis
and no observed transitions, so there is nothing to perturb. The `imp-causal-paper`
programme, which recovers a generating rule from an *evolving* pattern, does not
transfer directly to a static graph, and it would be wrong to imply that it does.

That leaves the question of what to actually measure, and there are two answers.

**The obvious one, which is wrong.** The canonical CausalBool description length
of `src/Packages/Integration/BioMetrics.m`:

$$D = \log_2 n + \sum_v \Big[ \underbrace{\log_2 |\mathcal{G}|}_{\text{name the gate}} + \underbrace{\log_2 \binom{n}{d_v}}_{\text{name the index set}} + \underbrace{\text{parameters}}_{\text{gate-specific}} \Big].$$

The middle term is the price of stating *which* $d_v$ of the $n$ atoms feed atom
$v$. It is exact, needs no empirical distribution, and is invariant to atom
numbering — all true, and all beside the point, because **it reads only the
degree sequence**. Two non-isomorphic graphs with identical degrees receive
identical values; across 250 such pairs of real molecules it separates **zero**.
A quantity blind to everything beyond degrees is not measuring structure.
`notebooks/understanding_complexity_measures.ipynb` builds this from scratch and
shows it ranking a checkerboard as the most complex of five images.

**The right one: the size of the compressed answer.** When `onPossibleBehaviour`
answers a query about $k$ atoms it enumerates `joinedNames` — the *union* of their
index sets — and folds every remaining coordinate into the **sumandos**. The
offset family then has $2^{\,n-|joinedNames|}$ members, so

$$\log_2|\Omega| \;=\; n - |joinedNames|$$

is the number of bits the compressed answer spends on the free part. Averaged
over all $k$-atom queries this is **purely structural** — it needs no gates, so it
does not depend on any dynamics we impose — and it reads neighbourhood *overlap*,
which is genuine topology. **But the obvious way to reduce it to one number fails.** The *mean* of that
quantity over all pairs is itself degree-determined, because
$\sum_{i<j}|N(i)\cap N(j)| = \sum_v\binom{d_v}{2}$ — so it separates 0% of the 250
pairs, exactly like $D$. Only the **spread** of the profile (76% at $k=2$, 95% at
$k=3$) and the full sorted profile (100%) read topology.
`understanding_complexity_measures.ipynb` §11 works this through.

### 9.4 Path information, read off the index algebra

The paper's subject is path information, so the same encoding is lifted to the
**L-hop index sets**: $N_L(v)$, the set of atoms reachable from $v$ by a simple
path of length exactly $L$. This is the set-valued reading of precisely the
object T-Hop tensorises and Graphormer walks along, and it gives two quantities
that BDM cannot express:

* **receptive saturation** — the fraction of the molecule that a model with a
  path budget of $L$ hops can address at all, averaged over atoms;
* **path surplus** — $(D_{hop2} + \dots + D_{hopL})/D_{hop1}$, how much more
  description the path layers need than the bonds alone.

Both are computed from bonds only, so — exactly like the paper's AOAC — all six
noise variants of a family share one value. Neither requires training anything.
""")

code(r"""
mirror_csv = os.path.join(RESDIR, 'causalbool_mirror.csv')
mirror_json = os.path.join(RESDIR, 'causalbool_mirror.json')
if not os.path.exists(mirror_csv):
    print('run  .venv/bin/python scripts/causalbool_mirror.py  first')
else:
    mirror = pd.read_csv(mirror_csv, index_col=0).loc[pv.AOAC_ORDER]
    recovery = pd.DataFrame(json.load(open(mirror_json))['recovery']).T
    print('mechanism recovery across the six datasets '
          '(first 200 molecules of each):')
    display(recovery[['molecules', 'atoms', 'exact_fraction', 'gate_matched',
                      'max_local_rows', 'largest_molecule']])
    print('\nindex-set observables per dataset family, next to the paper\'s BDM AOAC:')
    display(mirror[['sumando_bits_k2', 'sumando_bits_k3', 'saturation', 'path_surplus',
                    'D', 'D_wiring', 'n_atoms', 'BDM_AOAC']].round(3))
""")

md(r"""
The first table is the certificate: `exact_fraction` is 1.000 everywhere, and the
largest local repertoire ever enumerated is 512 rows against full repertoires of
up to 2¹³⁶.

The second table carries the replication. Read the `D` column against
`BDM_AOAC`: the index-set description length puts the six families in
**exactly the ascending order the paper reports** — FreeSolv, ESOL, BBBP,
ClinTox, Lipophilicity, BACE — without a CTM table, without an approximation and
without any dependence on atom numbering.

Look also at `saturation`: a three-hop model addresses 80% of an average FreeSolv
molecule and 28% of an average BACE molecule. That is the paper's complexity axis
restated as something mechanical and checkable.

### 9.5 Does the paper's central claim survive the substitution?
""")

code(r"""
if os.path.exists(mirror_csv):
    per_model = {m: [pv.PUM[m][d] for d in pv.AOAC_ORDER] for m in hp.MODELS}
    per_model['across all models'] = list(np.mean([per_model[m] for m in hp.MODELS], axis=0))

    rows = []
    for measure in ['BDM_AOAC', 'sumando_bits_k2', 'sumando_bits_k3', 'saturation',
                    'path_surplus', 'D', 'D_wiring', 'n_atoms']:
        x = mirror[measure].values.astype(float)
        row = {'measure': measure}
        for model, pums in per_model.items():
            r, pval = an.correlation(x, pums)
            row[model] = f'{r:+.3f} (p={pval:.3f})'
        labels, sil = an.cluster_1d(x, invert_labels=(measure == 'saturation'))
        row['clusters'] = ''.join(map(str, labels))
        row['silhouette'] = round(sil, 3)
        rows.append(row)
    mirror_corr = pd.DataFrame(rows).set_index('measure')
    print('correlation with the paper\'s PUMs, BDM in the first row for reference:')
    display(mirror_corr)
    print('cluster columns ordered', pv.AOAC_ORDER)
""")

md(r"""
Three things fall out.

**The claim survives, and does not depend on BDM.** Every deterministic index-set
measure reproduces the paper's correlations closely: `D` gives −0.80 for
Graphormer and −0.81 for T-Hop against the published −0.84 and −0.81, with the
same near-zero for Mix-Hop, the identical family ordering and the identical
two-cluster partition. The result is not an artefact of the CTM lookup table.

**But the choice of measure turns out to matter in exactly one way, and it is
decisive.** Every measure that is a function of the degree sequence — BDM, `D`,
`D_wiring`, the sumando *mean*, and plain atom-counting — lands near −0.82. The
one measure that is **not** degree-determined, the sumando **spread**, falls to
**−0.29** (Graphormer) and **−0.50** (across models).

Strip out size and degree, and most of the correlation goes with them. That is
the strongest evidence in this replication that the paper's axis is molecule size
(§2.4, r = +0.998) rather than structural complexity. The full argument is in
`method_comparison.ipynb` §11.7.3.

**But read that agreement correctly, because it is easy to over-claim.** `D` here
is dominated by its wiring term `log2 C(n, dᵥ)`, which is a function of the
**degree sequence alone**. `method_comparison.ipynb` §11.2 proves the consequence:
on 250 non-isomorphic molecule pairs that share a degree sequence, this term
separates **0%** of them. A quantity blind to all structure beyond degrees is not
approximating algorithmic complexity, and the agreement above is therefore *not*
evidence that two complexity measures concur. It is evidence that **both are
dominated by the same size-and-degree signal** — precisely the confound §2.4
identified when it found AOAC correlating with molecule size at r = +0.998.

The generative argument — that a recovered mechanism is a program, so its length
bounds *K* from above — applies to the **repertoire**, not to the wiring cost of
a static adjacency matrix. That distinction is worked through in
`method_comparison.ipynb` §11.1–11.2 and §11.6, and conflating the two is the
fastest way to lose the argument.

**The path-aware measures do better than BDM.** `path_surplus` reaches −0.907
(p = 0.013) against BDM's −0.821 (p = 0.045), and `saturation` reaches +0.874.
That is what one would hope for: a measure built out of the *path* index sets
predicts the usefulness of *path information* better than a generic complexity
measure does.

**But the honest reading is the one from §2.4.** `n_atoms` — the plain count of
atoms, no complexity theory involved — scores −0.821, matching BDM to three
decimals. Every measure in the table is strongly collinear with molecule size,
and with six data points there is no way to separate them statistically. The
index-set calculus does not rescue the paper's mechanism; it makes the situation
legible. What it adds is an *interpretation* of the axis that BDM leaves
mysterious: `saturation` says plainly that a path-bounded model sees most of a
FreeSolv molecule and a quarter of a BACE molecule, and that is a concrete reason
for path information to pay off in one case and not the other.

### 9.6 The same test against our own training runs
""")

code(r"""
if os.path.exists(mirror_csv) and our_pums:
    rows = []
    for model in hp.MODELS:
        p = [our_pums.get((model, ds)) for ds in pv.AOAC_ORDER]
        if any(v is None for v in p):
            continue
        for measure in ['BDM_AOAC', 'D', 'saturation', 'path_surplus', 'n_atoms']:
            r, pval = an.correlation(mirror[measure].values.astype(float), p)
            rows.append(dict(model=model, measure=measure, r=round(r, 3),
                             p_value=round(pval, 3)))
    if rows:
        display(pd.DataFrame(rows).pivot(index='measure', columns='model',
                                         values='r'))
        print('p-values are all well above 0.05: see the discussion below')
    else:
        print('no model has a complete six-family row from our own campaign yet')
""")

md(r"""
Against our own PUMs the index-set measures behave exactly like BDM: the same
negative sign, the same weakened magnitude (about −0.55), the same failure to
reach significance. They neither rescue the claim nor damage it — they track BDM
almost perfectly.

That is itself informative. The gap between the published −0.81 and our −0.55 is
**not** a disagreement about complexity, since two completely independent
complexity measures agree with each other to two decimals on the same molecules.
It is a property of the PUM side of the correlation: six strict inequalities
between three-run means, in a regime where the run-to-run spread often exceeds
the with/without gap.

### 9.7 What the mirror contributes

| Question | BDM answer | index-set answer |
| --- | --- | --- |
| Are the graph structures the ones we think? | not asked | **certified**: every index set and gate recovered from behaviour, 100% of ~25,000 atoms |
| Is the complexity ordering real? | 105.6 … 717.4 | **reproduced exactly** by a closed-form description length |
| Does the correlation depend on the CTM table? | unknowable from within | **no** — an exact measure gives −0.80 / −0.81 |
| Can we predict path usefulness without training? | not directly | **yes** — `path_surplus`, r = −0.91, p = 0.013 |
| What is the axis actually measuring? | unexplained | **receptive saturation**: 80% of a FreeSolv molecule visible in three hops, 28% of a BACE one |
| Is the mechanism separable from size? | no | **no**, and the index sets show why |

Reproduce this section with:

```bash
.venv/bin/python scripts/causalbool_mirror.py
```
""")

# ------------------------------------------------------- §10 pointer
md(r"""
## §10. Head to head: BDM against the index-set calculus

§9 showed the two methods reach the same conclusion. That leaves the sharper
questions — which is better, at what, and why; and whether the index-set calculus
can answer everything BDM can.

Those questions grew into a full adjudication with its own experiments, and they
now live in a dedicated notebook:

### → `method_comparison.ipynb`

It puts **eleven claims** on trial, from both sides, and records the verdicts —
including **four of my own claims that the evidence refuted**. A summary of the
findings, with the section of that notebook where each is measured:

| finding | evidence |
| --- | --- |
| BDM is `O(n²)`; the index-set layers are `O(n)` and `O(n d^L)` — about 1280× faster at n = 1024 | §8 |
| BDM needs ~41 MB of precomputed CTM tables; the index-set calculus needs none | §1.3 |
| BDM moves **30–45%** of its own value under atom relabelling; the index-set description length does not move at all | §3 |
| On this paper's question the two agree: identical family ordering, identical clusters, correlations within **0.049** | §10.3 |
| On 250 non-isomorphic molecule pairs sharing a degree sequence: the wiring term separates **0%**, BDM's invariant form **88.8%**, and a *single* index-set invariant (query overlap, order 3) **100%** | §5, §11.3 |
| The index-set calculus is a **generative model class**, so a recovered mechanism is a *program*: `K ≤ D + c`. My original scoreboard gave BDM the "estimates K" row and that was wrong | §11.1 |
| The wiring term **cannot** be K-like — it is degree-only, and applied to images it ranks a checkerboard as the most complex object of five | §11.2, §11.6 |
| BDM's real advantage is that it needs **no modelling commitment**, not that it handles randomness better | §9, §11.4 |
| Final scoreboard: **index-set 8, BDM 3, tie 3** — neither dominates | §12 |

**Why this notebook does not repeat the analysis.** It was duplicated here in an
earlier draft, and the duplicate went stale: it carried a verdict table that
`method_comparison.ipynb` §11 has since corrected. One authoritative account is
worth more than two divergent ones, so this section is now a pointer.

The single most important caveat for reading §9 above is the one in §9.5: the
agreement between BDM and the index-set description length on these six dataset
families is **not** two complexity measures concurring. Both are dominated by the
same size-and-degree signal.
""")

# ============================================================================

nb = {
    'cells': [
        {'cell_type': kind, 'metadata': {},
         **({'source': src.split('\n'), 'outputs': [], 'execution_count': None}
            if kind == 'code' else {'source': src.split('\n')})}
        for kind, src in CELLS
    ],
    'metadata': {
        'kernelspec': {'display_name': 'imp-pathinfo (.venv)', 'language': 'python',
                       'name': 'imp-pathinfo'},
        'language_info': {'name': 'python', 'version': '3.13'},
    },
    'nbformat': 4,
    'nbformat_minor': 5,
}

for cell in nb['cells']:
    cell['source'] = [line + '\n' for line in cell['source'][:-1]] + [cell['source'][-1]]

out = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'paper_walkthrough.ipynb')
with open(out, 'w') as fh:
    json.dump(nb, fh, indent=1)
print(f'wrote {out}: {len(nb["cells"])} cells '
      f'({sum(c["cell_type"] == "code" for c in nb["cells"])} code)')
