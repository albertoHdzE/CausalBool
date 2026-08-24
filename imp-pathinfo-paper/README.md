> **Start here:** [`FINDINGS.md`](FINDINGS.md) — ledger of every established
> result with its evidence. [`NEXT_PHASES.md`](NEXT_PHASES.md) — the plan for the
> next three phases, plus a superseded-claims list and the standing rule for
> validating any new measure. [`PHASE1_PROTOCOL.md`](PHASE1_PROTOCOL.md) — the
> pre-registered within-dataset size test, its design and its result.
> [`notebooks/understanding_bdm.ipynb`](notebooks/understanding_bdm.ipynb) — what
> BDM actually computes, built from nothing, and where the size confound really
> lives.
>
> Reproduce Phase 1 with:
> ```bash
> .venv/bin/python scripts/run_experiments.py --datasets ESOL --models t_hop \
>     --size-bins 4 --ledger results/runs_sizebins.jsonl --quiet
> .venv/bin/python scripts/analyse_sizebins.py
> ```

# Replication: *Algorithmic Complexity Predicts when Path Information Improves GNN Performance on Molecular Graphs*

An independent, self-contained replication of the TMLR submission held in
[`paper/`](paper/). The paper asks when it is worth feeding path information to
a graph neural network on molecular data, and answers that it is worth it when
the graphs have **low algorithmic complexity**, measured with the Block
Decomposition Method (BDM).

Everything here is written from scratch on top of the shared CausalBool
methodology; no code is copied from the authors' repository, which is mirrored
read-only under `reference/` and was consulted only to recover experimental
details the paper omits.

---

## Headline result of the replication

| Paper artefact | Status |
| --- | --- |
| Table 1 — dataset descriptions | reproduced (counts within 1%, RDKit parse failures) |
| Figure 1 — SMILES → list-of-edges conversion | reproduced |
| **Table 4, row 1 — AOAC (mean BDM) per dataset family** | **exact**: 5 of 6 to two decimals, ClinTox within 0.2% |
| AOAC ascending order | **exact** |
| Definition 1 / Lemma 1 / Theorem 1 | verified numerically |
| PUM definition, dichotomy scores 29/36, 24/36, 33/36 | **exact** |
| **Table 4 — Pearson correlations −0.84 / −0.19 / −0.81 / −0.82** | **exact** |
| Figure 3 | reproduced |
| **Table 5 — clusterings and all five Silhouette scores** | **exact** |
| Table 2 — noise-free scores | reproduced within run-to-run noise (median cell difference 0.024; with/without verdict agrees in 11 of 14 compared cells) |
| Table 3 — full noise sweep | reproduced for 13 of 18 model×family blocks; coverage audited in the notebook |
| **T-Hop dichotomy score Φ = 33/36, from our own campaign** | **exact** |
| Correlation sign from our own campaign | reproduced, weaker (T-Hop r = −0.54 vs −0.81) |

The paper's analytical chain — complexity → PUM → correlation → clustering →
conclusion — reproduces end to end from the raw MoleculeNet CSVs. The one part
that cannot reproduce to the digit is the training itself: the authors report
means of three unseeded runs whose standard deviations are frequently larger
than the with/without differences the PUM counts.

---

## The CausalBool index-set mirror

Following the same programme as `imp-causal-paper/` and `imp-causalNet-paper/`,
the paper is replicated a **second time** with this repository's own method —
deterministic index sets, exact generating mechanisms and deconvolution — with
BDM removed entirely (`src/imp_pathinfo/causalbool_mirror.py`,
`scripts/causalbool_mirror.py`, notebook §9).

**A molecule as a Boolean network.** The connectivity matrix *is* the bond
adjacency; each atom gets a canonical gate fixed by its chemistry (terminal →
`NOT`, aromatic → `XOR`, bonded to a heteroatom → `CANALISING`, otherwise
`MAJORITY`). The model is then thrown away and recovered from behaviour alone.

**Mechanism recovery is exact.** Every index set and every gate is recovered for
**100% of ~25,000 atoms** across all six datasets, with non-neighbour decoys
planted in each atom's local universe and correctly rejected. This works because
the index-set factorisation decomposes a 2¹³⁶-row repertoire into one local
problem per atom: **the largest local repertoire ever enumerated is 512 rows.**

**The paper's result does not depend on BDM.** The canonical CausalBool
description length *D* = log₂n + Σᵥ [log₂|𝒢| + log₂C(n,dᵥ) + params] — exact,
closed-form, order-invariant, no CTM table — puts the six families in **exactly
the published ascending order** and reproduces the correlations:

| measure | Graphormer | T-Hop | across models | clusters | Silhouette |
| --- | --- | --- | --- | --- | --- |
| BDM AOAC (the paper) | −0.840 | −0.815 | −0.821 | `001111` | 0.707 |
| index-set `D` | −0.804 | −0.806 | −0.819 | `001111` | 0.721 |
| `saturation` | +0.892 | +0.856 | +0.874 | `001111` | 0.728 |
| **`path_surplus`** | **−0.917** (p=0.010) | **−0.907** (p=0.013) | **−0.907** | `001111` | 0.709 |
| `n_atoms` (no theory at all) | −0.815 | −0.815 | −0.821 | `001111` | 0.707 |

**Path usefulness is predictable without training anything.** Lifting the index
encoding to the *L*-hop index sets gives two quantities BDM cannot express:
*receptive saturation* (what fraction of a molecule a path-bounded model can
address — 80% of an average FreeSolv molecule against 28% of a BACE one) and
*path surplus*. `path_surplus` correlates with PUM at −0.91, **better than BDM**,
which is what one would hope for from a measure built out of path index sets.

**And it makes the size confound legible.** `n_atoms` alone matches BDM to three
decimals. The mirror does not rescue the paper's stated mechanism; it explains
what the axis is really tracking, in terms that can be checked rather than
approximated.

---

### Three findings beyond the paper

1. **The complexity axis is largely a size axis.** The published AOAC values
   correlate with mean molecule size at r = +0.998. BDM as applied here is
   extensive — larger adjacency matrices contain more 4×4 blocks and score
   higher almost independently of regularity. Dividing the extensive part out
   leaves the six families nearly indistinguishable and destroys the ordering.
   The paper's empirical regularity is real and reproducible; its stated
   *mechanism* (structural regularity) is not separated from the simpler
   alternative that small molecules have short and few paths.
2. **Mix-Hop's path mechanism is largely inoperative in the authors' code.**
   Equation 2 calls for the matrix power `A^L`; the implementation computes
   `curr_adj = adj * curr_adj`, a Hadamard power that preserves the sparsity
   pattern of `A` and so never reaches beyond one hop. Mix-Hop is precisely the
   model with the near-zero correlation (−0.19) and the disagreeing clustering.
3. **Graphormer's structural bias is added after the softmax**, not to the
   attention logits as in the published Graphormer, so attention rows no longer
   sum to one.

Both implementation deviations are retained by default (reproducing the numbers
requires reproducing the code that produced them) and are switchable via
`mix_hop_matrix_power` and `graphormer_presoftmax_bias`.

---

## Layout

```
paper/            the paper (PDF) and its extracted text
reference/        read-only mirrors: the authors' repo, and DGL-LifeSci 0.3.2 source
data/raw/         the six MoleculeNet CSVs, downloaded from data.dgl.ai
src/imp_pathinfo/
  featurizers.py    74-dim atom and 12-dim bond features (DGL-LifeSci canonical)
  data.py           dataset loading, graph construction, Bemis-Murcko scaffold split
  paths.py          T-Hop tensors, simple-path counts, normalised adjacency, shortest paths
  bdm_complexity.py BDM / AOAC on adjacency matrices
  models.py         Graphormer, Mix-Hop, T-Hop, each in both modes
  train.py          training loop, metrics, early stopping, batching, noise injection
  hyperparams.py    the authors' Optuna-selected hyperparameters, all 36 cases
  analysis.py       PUM, dichotomy score, correlations, clustering
  paper_values.py   transcribed published tables, for side-by-side comparison
  causalbool_mirror.py  the index-set mirror: molecular Boolean networks, deconvolution,
                        description length, L-hop index sets, saturation, path surplus
  method_comparison.py  the adjudication experiments: random-regime scan, relabelling
                        spread, repertoire landscapes, knockout profiles, Kraft sums
scripts/
  compute_bdm.py       Table 4, row 1 (minutes)
  run_experiments.py   the 648-run training campaign (resumable)
  causalbool_mirror.py the index-set mirror sweep (seconds)
notebooks/
  paper_walkthrough.ipynb   the didactic, cell-by-cell replication
  method_comparison.ipynb   the empirical adjudication: BDM vs the index-set calculus
  conceptualizing.ipynb     a question-driven course on the index-set method itself
  understanding_complexity_measures.ipynb  description length vs complexity measure
  _build_notebook.py        generator for the walkthrough
  _build_method_comparison.py  generator for the comparison
tests/            39 correctness checks
results/, figures/
```

## Running it

```bash
cd imp-pathinfo-paper
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
.venv/bin/python -m ipykernel install --user --name imp-pathinfo --display-name "imp-pathinfo (.venv)"

.venv/bin/python -m pytest -q                    # 18 correctness checks
.venv/bin/python scripts/compute_bdm.py          # Table 4, row 1 — exact, ~7 s
.venv/bin/python scripts/run_experiments.py --quiet   # Tables 2 and 3 — long
.venv/bin/jupyter lab notebooks/paper_walkthrough.ipynb
```

The notebook runs top to bottom with no errors and works from whatever fraction
of the training campaign is complete, always distinguishing our numbers from the
paper's.

### The training campaign

648 runs (6 families × 6 noise levels × 3 models × 2 modes × 3 repetitions), up
to 200 epochs each with early stopping. On an Apple-silicon laptop the whole
campaign is a multi-day job; it appends to `results/runs.jsonl`, skips completed
cases and can be interrupted and resumed at will:

```bash
.venv/bin/python scripts/run_experiments.py --datasets FreeSolv ESOL --models t_hop --quiet
.venv/bin/python scripts/run_experiments.py --dry-run          # list what is outstanding
```

`--device auto` puts Graphormer on the MPS backend (the only model large enough
for the transfer cost to pay off) and leaves the rest on CPU.

**Campaign status as shipped**: 490 of 648 runs, 162 of 216 experimental cases,
about 10 hours of compute. T-Hop is complete for all six families; Mix-Hop lacks
Lipophilicity and part of ClinTox; Graphormer lacks BBBP, ClinTox and
Lipophilicity. Re-run the three commands above to continue from where the
ledgers stop, then re-execute the notebook — it globs `results/runs*.jsonl` and
recomputes everything downstream.

### How the models compared where the campaign is complete

* **T-Hop reproduces well**: raw scores close to the published ones, four of six
  PUMs identical, dichotomy score exactly 33/36, correlation −0.54 against −0.81.
* **Graphormer partially**: FreeSolv exact at 6/6, ESOL 1/6 against 4/6.
* **Mix-Hop diverges** on ESOL with path information (`max_pow = 5`), where our
  RMSE climbs to 9.35 under noise against a published 1.63 — five stacked
  Hadamard-power branches with batch normalisation is a numerically delicate
  configuration.

## Implementation notes

**No DGL.** The authors used DGL 2.4.0 and DGL-LifeSci 0.3.2, which have no
usable macOS/arm64 wheels. The pieces that matter — `CanonicalAtomFeaturizer`,
`CanonicalBondFeaturizer`, `SMILESToBigraph`, `ScaffoldSplitter`, `Meter`,
`EarlyStopping` — were reimplemented directly on RDKit from the DGL-LifeSci
source in `reference/`, preserving allowable sets, canonical atom ordering,
edge ordering and metric definitions, so the model inputs are identical. The
molecular data are the same CSVs DGL-LifeSci downloads.

**Sparse path tensors.** T-Hop's `T` tensor is `n × n × n × pow_dim` per graph —
10 million entries for a 136-atom molecule, 400 MB per batch. The contraction
against the learnable coefficients is performed sparsely instead, which is
mathematically identical (`tests/test_replication.py` asserts dense/sparse
agreement to 1e-5) and makes the campaign tractable. The same applies to
Graphormer's edge-features-along-shortest-paths tensor.

**Structure caching.** The authors rebuild the path tensors inside the data
loader on every epoch. Since noise touches only features and never bonds, these
are computed once per dataset and reused — no numerical change.

## Provenance

- Paper: TMLR submission under double-blind review, `paper/`.
- Authors' code: <https://github.com/rahmanoladi/kaust_path_project> (commit
  mirrored in `reference/kaust_path_project`), including the hyperparameter PDFs
  that the paper itself does not contain.
- Data: `https://data.dgl.ai/dataset/{FreeSolv,ESOL,lipophilicity,bace,bbbp,clintox}.zip`.
- BDM: [`pybdm`](https://pybdm-docs.readthedocs.io) 0.1.0, the implementation the
  paper cites, with the default 2-dimensional 4×4 CTM table.

### Head to head: BDM against the index-set calculus (notebook §10)

Measured rather than asserted, on four axes.

| criterion | better | measurement |
| --- | --- | --- |
| needs no model of the system | BDM | BDM takes any binary array; we need a connectivity matrix and a gate family |
| exactness | index-set | closed form vs an approximation from a finite CTM table |
| invariance to node labelling | index-set | BDM moves 35–44% under relabelling; ours does not move at all |
| sees beyond the degree sequence | tie | BDM only via labelling (not invariant); our path layers do it invariantly |
| estimates Kolmogorov complexity | BDM | ours is a description length and claims nothing more |
| recovers the generating mechanism | index-set | index set and gate for 100% of ~25,000 atoms |
| answers questions about paths | index-set | `path_surplus` r = −0.91 (p = 0.010) vs BDM −0.82 (p = 0.045) |
| computational cost | index-set | O(n) vs O(n²); ~1280× faster at n = 1024 |
| prior resources | index-set | nothing vs ~41 MB of precomputed CTM tables |
| reproduces this paper's conclusions | tie | identical ordering, identical clusters, correlations within 0.049 |
| applies outside graphs | BDM | images, strings, time series; ours needs a causal structure |

**Can the index-set method answer the same questions at the same accuracy?** For
this paper's question, yes: per-molecule agreement is Pearson 0.84–0.95 /
Spearman 0.85–0.96, the family ordering is identical, no cluster label changes,
and no published correlation moves by more than 0.049. For BDM's general question
— "how complex is this arbitrary object?" — no, and it does not claim to: our
method needs a system with a causal structure. For questions BDM cannot pose —
what generates each node, which inputs are causally essential, what does hop *L*
add over *L*−1 — only ours answers, and one of those produced the best predictor
of path usefulness found anywhere in the replication.

**The decisive experiment** (§10.5): a 12-cycle, three disjoint squares and two
disjoint hexagons are all 2-regular on 12 nodes. Our adjacency term gives all
three the same value — a real blind spot. BDM separates them in RDKit's canonical
layout (77.3 / 56.4 / 182.9), which looks like a clean win. But under 500 random
relabellings the three BDM distributions coincide (means 216.8 / 215.2 / 216.2,
P(a > b) = 0.50 in every pair): the separation was a property of the matrix
layout, not of the graph. `saturation` separates them invariantly at
0.545 / 0.273 / 0.455. The published AOAC values remain exactly reproducible —
canonical ordering is deterministic — but they measure the BDM of a canonical
adjacency *layout*, not of the molecular graph.

---

## `notebooks/method_comparison.ipynb` — the empirical adjudication

The head-to-head of §10 raised a methodological dispute worth settling properly.
This second notebook turns every claim on both sides into a measurement, and
records the verdicts — including two of my own claims that the evidence killed.

| # | Claim | Advanced by | Verdict |
| --- | --- | --- | --- |
| A | BDM counts blocks in the random regime | index-set | **upheld, qualified** — per-block BDM constant at 29.6 across a 16× size range, but it does track structure below ~20% rewiring |
| B | BDM is not invariant to node labelling | index-set | **upheld, proves less than it seems** — BDM moves 30–45%, but its relabelling average *is* an invariant |
| C | BDM sees structure the index-set calculus cannot | BDM | **upheld against layer 1 only** — wiring separates 0%, the full calculus 100% |
| D | BDM's separation is an artefact of layout | **me, earlier** | **REFUTED** — invariant BDM still separates 88.8% of real same-degree pairs; the 2-regular triple was an adversarial anecdote |
| E | The index-set calculus can separate via topology and behaviour tables | index-set | **upheld** — paths 99.2%, repertoire 93–96%, combined 100%, all invariant |
| F | Perturbation is the causal instrument, natively available | index-set | **upheld in capacity** — exact per-atom read-out, but the weakest discriminator at 84.8% |
| G | BDM's real advantage is domain generality, not randomness | BDM | **upheld** — BDM orders bitmaps, waveforms and noise; we are undefined on all of them |
| H | `D` already induces an algorithmic probability | **me, earlier** | **REFUTED, repaired** — Kraft sum is 2.3–13.1, so `D` is not a code; adding `log₂(n+1)` for the arity gives 0.32–0.46 |
| I | `D` is a computable **upper bound on K**, so scoring "estimates K" to BDM was wrong | index-set | **UPHELD — my scoring error, against our own side** |
| J | The wiring term **cannot** be K-like for graphs, being degree-only | against our own side | **UPHELD** — 0% separation is a proof, not a shortfall |
| K | The compressed representation separates as a single measure | index-set | **REFUTED as stated, UPHELD refined** — naive form 0%; query overlap order 3 = **100% from one invariant** |

### The decisive experiment

250 non-isomorphic pairs of **real molecules sharing a degree sequence**
(isomorphism verified, not heuristic):

| measure | invariant? | separated |
| --- | --- | --- |
| index-set wiring `D` | yes | 0.0% |
| node compressed size (naive "compression" reading) | yes | 0.0% |
| BDM, canonical layout | **no** | 99.2% |
| BDM, averaged over relabellings | yes | 88.8% |
| **path index sets** (polynomial) | yes | **99.2%** |
| **query overlap, order 2** (`O(n²)`, same as BDM) | yes | **97.6%** |
| **query overlap, order 3** — a *single* invariant | yes | **100.0%** |
| repertoire landscape, AND | yes | 96.0% |
| repertoire landscape, XOR | yes | 93.2% |
| knockout profile | yes | 84.8% |
| all index-set invariants | yes | 100.0% |

### Four layers with an explicit exchange rate

The central structural finding: the index-set calculus has a resolution dial that
BDM does not — wiring `O(n)` → path index sets `O(nd^L)` → **query overlap
`O(n^k d)`** → repertoire `O(2ⁿ)` — and **the best results come from the
polynomial layers**, not the exponential one. The query layer is the method's own
`joinedNames` machinery from `onPossibleBehaviour`, which I had missed entirely
in the first pass.

The concessions are equally clear: order-3 query overlap costs `O(n³)`, *worse*
than BDM; order 2 is cost-matched but fails the adversarial triple; and the causal
layer dies at about n = 24, so the perturbation apparatus is unavailable on a
136-atom molecule.

### The reframing that drove the revision

Sections 2–10 were written treating this as *measure versus measure*. It is not:
the index-set calculus is a **generative model class with an exact inverse**, and
`D` is a by-product of it. Deconvolution exhibits a *program that replays the
object exactly*, so `K ≤ D + c` — `D` is a computable upper bound on `K`, which
is precisely what BDM estimates and cannot compute. The Kraft repair from claim H
is what licenses that argument, making it load-bearing rather than bookkeeping.

The equivalence question is left **well posed and unsettled**: for objects a class
can generate, `D` bounds `K` from above while CTM estimates it by sampling — two
routes to the same quantity from opposite directions, testable on elementary
cellular automata, which lie in both classes and one of which (Rule 110) is
universal. The version that must *not* be advanced is the one resting on static
graph description lengths, which our own claim J refutes.

**Scoreboard: index-set 8, BDM 3, tie 3.** Neither dominates; the boundary is now
drawn by measurement. Four of the eleven claims tested were mine, and all four
were wrong — three from asserting a property instead of computing it.


---

## The decisive finding

Correlation with the published PUMs across the six dataset families:

| measure | what it reads | Graphormer | T-Hop | across | ordering |
| --- | --- | --- | --- | --- | --- |
| BDM AOAC | the paper's measure | −0.840 | −0.815 | −0.821 | — |
| `sumando_bits_k2` | overlap **mean** — degree-determined | −0.808 | −0.811 | −0.817 | same as BDM |
| `D_wiring` | degree only | −0.799 | −0.803 | −0.810 | same as BDM |
| `n_atoms` | no theory at all | −0.815 | −0.815 | −0.821 | same as BDM |
| **`sumando_spread_k2`** | **overlap *shape* — the only non-degree measure** | **−0.289** | **−0.548** | **−0.504** | **DIFFERENT** |

Every degree-driven measure lands near −0.82. The one measure that is not a
function of the degree sequence collapses to −0.29 / −0.50. Together with
r = +0.998 between AOAC and molecule size, this is the strongest evidence that the
paper's complexity axis is **molecule size**.

**`D_wiring` is not a complexity measure** and should not be used as one: it
separates 0 of 250 same-degree molecule pairs, and on images it correlates with
BDM at Spearman 0.000 while ranking a checkerboard as the most complex of five.
The *mean* overlap fails identically and provably, since
`Σ|N(i)∩N(j)| = Σ_v C(dᵥ,2)`. Only the **spread** (76% / 95%) and the full sorted
**profile** (97.6% / 100%) read topology.
