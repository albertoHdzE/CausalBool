# Findings ledger — `imp-pathinfo-paper`

Everything established in this replication, with the evidence and where it lives.
Written to survive a context reset: a reader who has never seen the conversation
should be able to reconstruct the state of the work from this file alone.

Last updated: 2026-08-04.

---

## 1. The replication itself

Target: TMLR submission *"Algorithmic Complexity Predicts when Path Information
Improves GNN Performance on Molecular Graphs"* (`paper/`). Notebook:
`notebooks/paper_walkthrough.ipynb` (72 cells).

| artefact | status | note |
| --- | --- | --- |
| Table 1 | reproduced | counts within 1% (RDKit parse failures) |
| Figure 1 | reproduced | SMILES → list-of-edges |
| **Table 4 row 1 (AOAC)** | **exact** | 5 of 6 to 2 dp; ClinTox within 0.2% |
| AOAC ordering | **exact** | FreeSolv < ESOL < BBBP < ClinTox < Lipophilicity < BACE |
| Def. 1 / Lemma 1 / Theorem 1 | verified | numerically, 60 molecules |
| PUMs, dichotomy 29/24/33 of 36 | **exact** | |
| **Table 4 correlations** | **exact** | −0.84 / −0.19 / −0.81 / −0.82 |
| **Table 5 clusters + Silhouettes** | **exact** | all labels, all five scores |
| Table 2 | within run-to-run noise | median cell diff 0.024; verdict agrees 11/14 |
| Table 3 | 13 of 18 blocks | campaign status per `scripts/campaign_status.py`: runs 623 of 648 |
| T-Hop Φ from our own runs | **exact 33/36** | correlation −0.54 vs published −0.81 |

**Critical AOAC detail**: molecules with < 4 atoms have no complete 4×4 block, so
`pybdm` raises. They must be **excluded** from the mean, not counted as zero.
Counting them as zero gives 100.02 for FreeSolv instead of the published 105.61.

### Findings beyond the paper
1. **AOAC correlates with mean molecule size at r = +0.998.** BDM as applied is
   extensive.
2. **Mix-Hop's path mechanism is largely inoperative** in the authors' code:
   `curr_adj = adj * curr_adj` is a Hadamard, not matrix, power. Mix-Hop is
   precisely the outlier model (r = −0.19).
3. **Graphormer's structural bias is added after the softmax**, not to the logits.

---

## 2. The index-set mirror

`src/imp_pathinfo/causalbool_mirror.py`, `scripts/causalbool_mirror.py`,
walkthrough §9.

- Molecule as a Boolean network: `C` = bond adjacency, gate per atom from
  chemistry (terminal→NOT, aromatic→XOR, heteroatom neighbour→CANALISING, else
  MAJORITY).
- **Mechanism recovery is exact**: index set *and* gate for 100% of the 24,880 corpus atoms (1,197 molecules; 200-molecules/dataset cap, see the generated campaign-status block below)
  across all six datasets, with planted non-neighbour decoys rejected. Feasible
  because the index-set factorisation makes it node-local: largest local
  repertoire **512 rows** against full repertoires up to 2¹³⁶.
- **This is a certificate, not a measurement.** We generated the repertoire from
  gates *we chose*, so recovering them proves the code is correct — not anything
  about the molecule. A static graph has no observed dynamics to deconvolve, so
  the `imp-causal-paper` programme does not transfer directly.

---

## 3. The decisive result — the size confound

**The single most important finding in this repository.**

Correlation with the published PUMs, across the six dataset families:

| measure | reads | Graphormer | T-Hop | across | ordering |
| --- | --- | --- | --- | --- | --- |
| BDM AOAC | the paper's measure | −0.840 | −0.815 | −0.821 | — |
| `sumando_bits_k2` | overlap **mean** — degree-determined | −0.808 | −0.811 | −0.817 | same as BDM |
| `D_wiring` | degree only | −0.799 | −0.803 | −0.810 | same as BDM |
| `n_atoms` | no theory at all | −0.815 | −0.815 | −0.821 | same as BDM |
| **`sumando_spread_k2`** | **overlap *shape* — the only non-degree measure** | **−0.289** | **−0.548** | **−0.504** | **DIFFERENT** |
| `sumando_spread_k3` | same, order 3 | −0.709 | −0.836 | −0.816 | DIFFERENT |

Every degree-driven measure lands near −0.82. **The one measure that is not a
function of the degree sequence drops to −0.29 / −0.50.** Strip out size and
degree and most of the correlation goes with them.

Combined with r = +0.998 between AOAC and molecule size, this is the strongest
evidence that the paper's axis is **molecule size**, not structural complexity.

---

## 3b. Phase 1 — the within-dataset size test (2026-08-04)

Pre-registered in `PHASE1_PROTOCOL.md` before any run; ledger
`results/runs_sizebins.jsonl`; readout `scripts/analyse_sizebins.py`; figure
`figures/phase1_sizebins_esol.png`. ESOL split into four atom-count quartile
bins, T-Hop only, both modes × 6 noise levels × 3 repetitions = 144 runs, 918 s.
`max_nodes`, the noise vector and the hyperparameters are held at the
full-ESOL values, so only the molecules differ between bins.

| bin | atoms | n | mean atoms | mean BDM | PUM | path − no-path RMSE |
| --- | --- | --- | --- | --- | --- | --- |
| 0 | 1–8 | 337 | 6.24 | 49.0 | 3/6 | **−0.070** (helps) |
| 1 | 9–12 | 257 | 10.36 | 119.7 | 1/6 | +0.140 |
| 2 | 13–18 | 280 | 15.44 | 259.2 | 0/6 | +0.179 |
| 3 | 19–55 | 254 | 23.24 | 474.9 | 0/6 | **+0.524** (hurts) |

**H₁ supported** — but the binary PUM only just clears the pre-registered
threshold (spread exactly 3/6). The evidence is the continuous effect:
Spearman +0.721 between bin index and the RMSE penalty over the 24 (bin, noise)
cells, **permutation p = 0.0002**, and the same monotone ordering under three
independent aggregations (means, rep-wise, all 54 rep pairings).

**The paper's gradient exists inside a single dataset.** Family-level
explanations — different chemistry, task, label distribution — are therefore not
needed for it.

**What it does not settle, stated plainly.** Within ESOL, BDM and size remain
monotone together (49 → 475 against 6.2 → 23.2 atoms), so their correlations
with PUM are identical and this design cannot separate them. The anticipated
decoupling did not occur. Separating BDM from size still rests on §3 above.
Caveat: bin 0's rep-to-rep std is 0.505 RMSE against 0.11–0.21 elsewhere, and
3/6 is chance — read it as "path stops hurting", not "path helps".

**Lipophilicity replication (not pre-registered), 144 runs, 3368 s — the
prediction failed.** PUM is 0/6 in all four bins and the continuous penalty
shows no monotone trend (Spearman +0.366, p = 0.074). The reason is
interpretable rather than contradictory: Lipophilicity's *smallest* bin averages
18.0 atoms, above the crossover ESOL locates near 8, so the whole dataset sits
in the saturated regime. Relative penalties across both datasets, by mean bin
size (`figures/phase1_sizebins_both.png`):

| mean atoms | 6.2 | 10.4 | 15.4 | 23.2 | 18.0 | 25.2 | 30.0 | 36.2 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| penalty | −3.8% | +13.8% | +19.4% | +32.0% | +23.8% | +11.6% | +31.2% | +28.9% |

So the effect is **a crossover near eight atoms followed by a plateau**, not a
smooth monotone function of size. That refines H₁ rather than confirming it, and
it was not predicted. `analyse_sizebins.py` prints "H₀ supported" for
Lipophilicity; that output is a floor artefact of the binary PUM and is not a
claim.

---

## 4. Method adjudication — `notebooks/method_comparison.ipynb` (67 cells)

Eleven claims tried; **five were mine and all five were wrong**.

| # | claim | verdict |
| --- | --- | --- |
| A | BDM counts blocks in the random regime | upheld **only in that regime**, and narrowed further in §7 below — per-block constant 29.6 on dense random matrices, but it *does* track structure below ~20% rewiring, and on sparse molecular graphs it is not a count at all |
| B | BDM is not label-invariant | upheld but proves less than it seems — the relabelling *average* is an invariant |
| C | BDM sees what the index-set calculus cannot | upheld against layer 1 only |
| D | BDM's separation is a layout artefact | **MINE — REFUTED**: invariant BDM still separates 88.8% |
| E | We can separate via topology and behaviour tables | upheld |
| F | Perturbation is our native causal instrument | upheld in capacity; weakest discriminator at 84.8% |
| G | BDM's advantage is domain generality | upheld |
| H | `D` already induces an algorithmic probability | **MINE — REFUTED**: Kraft sum 2.3–13.1; adding `log₂(n+1)` for the arity gives 0.32–0.46 |
| I | `D` merely encodes; BDM estimates K | **MINE — REFUTED**: an exhibited program bounds K, so `K ≤ D + c` |
| J | The wiring term cannot be K-like | upheld **against our own side** |
| K | Compressed size separates as one measure | **MINE — REFUTED as stated**, upheld refined |

### Separation benchmark — 250 non-isomorphic real molecule pairs with identical degree sequences

| measure | invariant? | separates |
| --- | --- | --- |
| `D_wiring` | yes | **0.0%** |
| sumando **mean** (k=2) | yes | **0.0%** |
| node compressed size | yes | 0.0% |
| BDM, canonical layout | **no** | 99.2% |
| BDM, averaged over relabellings | yes | 88.8% |
| sumando **spread** (k=2) | yes | 76.4% |
| sumando **spread** (k=3) | yes | 95.2% |
| path index sets | yes | 99.2% |
| query overlap profile, order 2 | yes | 97.6% |
| **query overlap profile, order 3** | yes | **100.0%** |
| repertoire landscape (AND / XOR) | yes | 96.0 / 93.2% |
| knockout profile | yes | 84.8% |

**Why the mean fails, provably**:
`Σ_{i<j}|N(i)∪N(j)| = Σ(d_i+d_j) − Σ_{i<j}|N(i)∩N(j)|` and
`Σ_{i<j}|N(i)∩N(j)| = Σ_v C(d_v,2)`. Both terms are degree-determined.
Verified numerically on C12: 12 = 12.

### The four layers
| layer | reads | cost |
| --- | --- | --- |
| 1 wiring | degree sequence | O(n) |
| 2 path index sets | L-hop reachability | O(n·d^L) |
| 3 **query overlap** (`joinedNames`) | neighbourhood overlap | O(n^k·d) |
| 4 repertoire | exhaustive landscape + perturbation | O(2ⁿ) |

Layer 3 was missed in the first pass; it is the method's own machinery and the
strongest discriminator. Layer 4 dies at about n = 24.

### Objects and classes
- **Bitmap and sine wave cannot be generated by *any* network**: the same row has
  two different successors. A proof about the object, not a failed search.
- **Noise and random walk pass only vacuously** — all rows distinct, so any map is
  a function. MDL rejects the memorising fit.
- **Chaotic ECAs are recovered exactly** (rules 30, 45, 110 → unique), while
  *simple* rules leave several candidates (254 → 2, 50 → 8). **Randomness helps
  the deconvolution**; the limit is class membership, not randomness.
- Applied directly to images, `D_wiring` gives Spearman **0.000** against BDM and
  ranks a checkerboard the most complex of five.

**Scoreboard: index-set 8, BDM 3, tie 3.**

---

## 5. Teaching notebooks
- `notebooks/conceptualizing.ipynb` (53 cells) — index sets, perturbation,
  Behaviour Tables (thesis Ch. 4 reproduced exactly: node 4 ← {1,3,5,7},
  pivot 85), `onPossibleBehaviour` / `givePlaces` (Table 4.14 reproduced exactly).
- `notebooks/understanding_complexity_measures.ipynb` (49 cells) — description
  length vs complexity measure; the `D_wiring` failure, the *failed* mean repair,
  and the working spread/profile repair.

**Terminology, corrected by the author** (do not regress):
- **output repertoire** = what I once wrongly called a "behaviour table".
- **Behaviour Table** = the Ch. 4 *instrument* (Node / node−1=pow / 2^(pow−1) /
  ratios) whose sum column is the AND pivot `P(I_c)`.
- **Sumandos** = **decimal offsets**, every subset sum of the free coordinates'
  weights — *not* the free nodes. For the 7-node example: free coordinates
  {2,4,6}, sumandos {0,2,8,10,32,34,40,42}.

---

## 6. State and how to resume

- **41 tests pass**: `.venv/bin/python -m pytest -q`
- **Training campaign** (generated by `scripts/campaign_status.py` from the
  ledgers; quoted verbatim, see `results/campaign_status.txt`):

```
- runs: 623 of 648
- cells fully replicated (3/3): 207 of 216; partial cells: 1 [graphormer/Lipophilicity mode=0 noise=0.3: 2/3]
- missing cells (8): graphormer mode=0: Lipophilicity noises 0.4-0.5 | graphormer mode=1: Lipophilicity noises 0.0-0.5
- per model t_hop: 72/72 cells
- per model mix_hop: 72/72 cells
- per model graphormer: 63/72 cells
- size-bin study (separate ledger results/runs_sizebins.jsonl): 288 runs
- tests collected: 41 (pytest --collect-only)
- mirror corpus: 24,880 atoms over 1,197 molecules, exact recovery 24,880/24,880 = 100.00% — corpus is capped at the first 200 molecules per dataset (smaller datasets: ClinTox 199, FreeSolv 198); cap location: scripts/causalbool_mirror.py graphs[:200]
```

  Resume with the three per-model commands in `README.md`; notebooks glob
  `results/runs*.jsonl`.
- **Rebuild any notebook**: `notebooks/_build_<name>.py`, then
  `jupyter nbconvert --to notebook --execute --inplace --ExecutePreprocessor.kernel_name=imp-pathinfo <name>.ipynb`
- **Re-run the mirror**: `.venv/bin/python scripts/causalbool_mirror.py`

---

## 7. What BDM actually is — and the corrected form of the size claim (2026-08-04)

`notebooks/understanding_bdm.ipynb` (56 cells). Written after the author
objected, correctly, that describing BDM as "counting blocks" is far too strong
and that Zenil's group have defended the method against exactly that charge
since its introduction. **The objection is upheld.**

**BDM is not a count.** `K_BDM = Σ_{distinct blocks} K_CTM(r_j) + log₂ n_j`. The
sum runs over *distinct* blocks; repeats cost only a logarithm. Measured: a
40×40 object made of 100 identical 4×4 tiles costs **6.6 bits more** than one
tile, not 100 × 22 = 2200. `K_CTM` is not a count either — it is `−log₂` of the
frequency with which a vast collection of 2D Turing machines produces that
block, i.e. algorithmic probability via Levin's coding theorem.

**BDM reads structure, and our own benchmark proves it.** On the 250 pairs with
identical atom count *and* identical degree sequence, BDM separates **99.2%**
(88.8% relabel-averaged) where `D_wiring` separates 0%. At completely fixed size
(373 molecules of exactly 20 atoms, always 25 tiles) BDM spans **102–607 bits**,
a factor of six, and correlates with edge count at only **+0.19**. It is neither
a size measure nor a degree measure. On this domain it measures, at **r = +0.991**,
*how many distinct local wiring patterns a molecule contains*.

**Where the size confound really comes from** — three things stacked, none of
them a defect of BDM:
1. BDM is extensive in *distinct structure*, correctly so;
2. bounded chemical valence saturates mean degree by ~13 atoms (1.76 → 2.17,
   then flat), forcing density to fall like 1/n — **density vs size Spearman
   −0.997**;
3. averaging over a dataset cancels the structural variation and leaves the
   systematic part: per-molecule BDM vs atoms **+0.916**, per-dataset AOAC vs
   mean atoms **+0.998**.

**Corrected claim, replacing all looser phrasings:** BDM is a sound structural
complexity measure and behaves like one on individual molecules. **AOAC — the
mean of BDM over a dataset — is not a structural measure of anything**, and is a
near-perfect proxy for mean molecule size. The problem is the aggregation step,
not the measure.

**Caveats recorded on both sides.** BDM depends on atom numbering: 200
relabellings of one molecule give 382–582 bits, a spread comparable to the
spread across genuinely different 20-atom molecules — though the relabelling
average is a true invariant and still separates 88.8%. At 4×4 resolution CTM
ranks a checkerboard (30.27) *above* a random draw (29.38), a boundary-condition
limit Zenil's group document. And contrary to their E. coli finding, on *our*
object BDM and Shannon block entropy correlate at **+0.92**, because on sparse
matrices both track the distinct-tile count — a domain-dependent result about
molecules, not a challenge to theirs.

**Consequence for our own method.** `D`, `D_wiring` and the sumando mean are all
extensive too, so averaging any of them over a dataset yields the same size
proxy. Only intensive quantities escape — which is why the sumando *spread* was
the one measure that broke the −0.82 pattern.

### Propagated corrections — audit of the other four notebooks

The correction was traced through every notebook. Three genuine errors were found
and fixed; all five notebooks rebuilt and re-executed with 0 errors and unchanged
cell counts.

| notebook | finding |
| --- | --- |
| `paper_walkthrough` §2.4 | **Error.** Claimed that "once the extensive part is divided out the six families are nearly indistinguishable, and the residual ordering is not the AOAC ordering". False with the denominator used: per *total* tile the spread is **2.06×** and the AOAC ordering survives (reversed, r = +0.808). Only per *distinct* tile — BDM's actual denominator — does it collapse, to **1.02×** (25.51–26.11). Both normalisations are now computed and plotted. |
| `paper_walkthrough` §8.2 | **Error.** "Bigger matrices score higher, nearly independently of regularity." Refuted by 99.2% same-degree separation and the factor-six spread at fixed size. Rewritten to blame the averaging step. |
| `method_comparison` §2 | **Error, mechanism backwards.** Claimed molecular BDM "is dominated by repeated all-zero blocks — the regime where the extensive term rules". Repeated blocks are exactly what *collapses* under the `log₂ n_j` rule, so sparsity is where BDM is **least** extensive in tiles. The scan behind claim A also uses density-0.5 Erdős–Rényi graphs, the opposite of molecules, so it never transferred. Claim A is now marked "upheld only for dense random graphs". |
| `understanding_complexity_measures` | No error. BDM's image ordering there is correct at image scale; a caveat was added noting the 4×4 checkerboard anomaly (30.27 vs 29.38) so BDM is not treated as infallible ground truth. |
| `conceptualizing` | No error. Cross-reference added — it already listed "what is BDM actually doing?" as an open question, which now has its own notebook. |

---

### Open questions
1. Can a factorised approximation carry the causal layer past n ≈ 24? The
   per-atom factorisation already works; the *global* landscape does not factorise.
2. Does the query-overlap advantage survive outside sparse bounded-degree graphs?
3. **The equivalence question with BDM** — defensible form: for objects a class
   generates, `D` bounds K from above while CTM estimates it by sampling. Clean
   test: elementary cellular automata (both classes apply; Rule 110 universal).
   Must **not** be argued from static graph description lengths (claim J).
4. Encodings #3 of the hierarchy — the closed-form set expressions (bands, parity
   classes, Hamming strata) — remain unimplemented and are the shortest of all.
