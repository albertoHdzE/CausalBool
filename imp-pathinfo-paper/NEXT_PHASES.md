# Handoff — next three phases

Written 2026-08-04, at the end of the session that built this replication.
Companion to [`FINDINGS.md`](FINDINGS.md), which is the ledger of what is
*established*. This file is the plan for what comes *next*.

> **If this session was compacted, read this file and `FINDINGS.md` before acting
> on anything in the conversation summary.** Five claims were made and refuted
> during the session; §0 lists them so a lossy summary cannot resurrect them.

---

## §0. Superseded claims — do not act on these

Each was asserted, then refuted by measurement, in this session. If a summary
states any of them as current, it is wrong.

| # | superseded claim | what is actually true |
| --- | --- | --- |
| 1 | *"BDM's separation is an artefact of matrix layout"* | Relabelling-**averaged** BDM is a genuine invariant and still separates 88.8% of same-degree pairs. The 2-regular triple was an adversarial anecdote. |
| 2 | *"`D` already induces an algorithmic probability by Kraft"* | False as published. Kraft sum is 2.3–13.1 because `D` never pays for stating the **arity** `d`. Adding `log₂(n+1)` per node gives 0.32–0.46. That term is load-bearing, not bookkeeping. |
| 3 | *"`D` merely encodes; BDM estimates K"* | A recovered mechanism is an **exhibited program**, so `K ≤ D + c`. `D` is a computable *upper bound* on K. This was a scoring error against our own side. |
| 4 | *"The compressed representation separates as a single measure"* | The **per-node** compressed size separates 0%. Only **k ≥ 2 query overlap** does (97.6% / 100%). |
| 5 | *"Mean sumando bits is the structural repair"* | The **mean** is degree-determined and separates 0%, provably: `Σ_{i<j}|N(i)∩N(j)| = Σ_v C(d_v,2)`. Only the **spread** (76% / 95%) and the full **sorted profile** (97.6% / 100%) read topology. |
| 7 | *"BDM adds up the complexity of every block / counts blocks"* | **Wrong, and the author was right to reject it.** BDM sums over **distinct** blocks and charges repeats only `log₂ n_j`: 100 identical tiles cost 6.6 extra bits, not 2200. `K_CTM` is algorithmic probability from Turing-machine frequency, not a count. BDM separates 99.2% of same-degree pairs and spans 102–607 bits at fixed size. The defensible claim is only about **AOAC**, the dataset *average*. See `FINDINGS.md` §7 and `notebooks/understanding_bdm.ipynb`. |
| 6 | *"The causal layer only works up to ~20 atoms"* | True only of the **global landscape** (`2ⁿ`). A **query** program costs `2^|joinedNames|` with `|joinedNames| ≤ 4k` for degree ≤ 4 — measured at **0.001 ms and independent of n** up to n = 400. |

---

## §1. The scientific situation in one page

**What the paper claims.** GNNs benefit from path information on molecular
datasets with *low algorithmic complexity* (BDM). Evidence: correlation −0.84 /
−0.19 / −0.81 / −0.82 between BDM AOAC and the Path Usefulness Measure across six
dataset families, plus a matching two-cluster partition.

**What we established.** Every number reproduces exactly (see `FINDINGS.md` §1).
The replication is not in doubt.

**What we discovered.** The complexity axis is very nearly a **size** axis:

* AOAC correlates with mean molecule size at **r = +0.998**;
* every degree-driven measure — BDM, `D`, `D_wiring`, sumando mean, and *plain
  atom-counting* — lands at about **−0.82**;
* the one measure that is **not** a function of the degree sequence (sumando
  **spread**, k = 2) collapses to **−0.29** (Graphormer) / **−0.50** (across).

**The status of the paper's claim is therefore *unidentified*, not *refuted*.**
With six families and size varying from 8.9 to 34.1 atoms, "complexity predicts
PUM" and "size predicts PUM" fit the data equally well. Six points cannot choose.

**The whole point of the next phase is to make that choice.**

---

## §2. The recurring trap — read before proposing any new measure

Four separate quantities have now looked structural and turned out to be
functions of the degree sequence alone:

| quantity | separates 250 same-degree pairs | why it collapses |
| --- | --- | --- |
| `D_wiring` = `log₂ n + Σ log₂C(n,dᵥ)` | 0% | reads only `A.sum(axis=1)` |
| per-node compressed size | 0% | determined by `d` and the gate |
| mean pairwise overlap | 0% | `Σ|N(i)∩N(j)| = Σ_v C(dᵥ,2)` |
| cyclomatic number / ring count | 0% | `|E|−|V|+c`, and `|E| = Σdᵥ/2` |

**Standing rule: no measure enters the analysis until it has been run against the
250 same-degree pairs.** The test is one line:

```python
from imp_pathinfo import method_comparison as mc
from imp_pathinfo.data import DATASET_ORDER, load_dataset
pairs = mc.same_degree_pairs([load_dataset(n) for n in DATASET_ORDER],
                             min_atoms=6, max_atoms=13, max_pairs=250, seed=0)
sep = sum(1 for (_, A1, _), (_, A2, _) in pairs if my_measure(A1) != my_measure(A2))
```

Measures that pass: 1-WL colour hash (100%), Laplacian spectrum (100%), adjacency
spectrum (99.2%), query overlap profile k=3 (100%) and k=2 (97.6%), sumando spread
k=3 (95.2%) and k=2 (76.4%), path index sets (99.2%), repertoire landscape
(93–96%), gzip of canonical SMILES (92.8%), knockout profile (84.8%).

---

## §3. PHASE 1 — the within-dataset size test — **DONE, 2026-08-04**

> **Executed.** Protocol pre-registered in `PHASE1_PROTOCOL.md`, result in
> `FINDINGS.md` §3b. **H₁ supported**: within ESOL alone, PUM falls 3/6 → 1/6 →
> 0/6 → 0/6 across the four size bins and the RMSE penalty for path information
> rises monotonically −0.070 → +0.524 (permutation p = 0.0002).
>
> **One correction to the plan below.** §3 "Threat to validity" hoped BDM and
> size might decouple within a dataset and give a bonus discriminator. **They do
> not**: mean bin BDM 49 → 475 is monotone with mean bin atoms 6.2 → 23.2, so
> the two give identical correlations. Phase 1 removes the *family-level*
> confounds; it does **not** separate BDM from size. That separation still rests
> on `FINDINGS.md` §3.
>
> **A Lipophilicity replication was added afterwards (not pre-registered) and
> its prediction failed.** PUM is 0/6 in all four bins and the continuous
> penalty has no monotone trend (p = 0.074). Lipophilicity's smallest bin
> averages 18 atoms, above the crossover ESOL locates near 8, so it samples only
> the saturated regime. Combining both datasets, the effect is **a crossover
> near eight atoms followed by a 10–30% plateau**, not a smooth monotone
> function of size. Phase 3 should be framed against that shape, not a line.
>
> The plan as originally written follows, unedited.



### Goal
Decide whether PUM is driven by molecule size, using data the paper never
examined: variation **inside** a single dataset rather than across six.

### Hypotheses
* **H₁ (confound).** Within one dataset, PUM decreases as mean bin size rises.
  → the cross-dataset correlation is explained by size; the complexity
  interpretation is not needed.
* **H₀ (complexity survives).** PUM is flat across size bins within a dataset.
  → size is not sufficient, and something structural is doing work.

Both outcomes are publishable. H₁ is the more likely and the more useful.

### Why it is decisive
It breaks the confound by **design** rather than by statistics. Inside one
dataset, chemistry, task, label distribution, splitting policy and hyperparameters
are held fixed; only size varies. That is the control the paper lacks.

### Method
1. Pick **ESOL** (1128 molecules, 5–55 atoms, fast) — or FreeSolv if compute is
   tight, though its size range is narrower.
2. Split into 3–4 bins by atom count, each with enough molecules to train
   (≥ 250 suggested). Record mean atoms and mean BDM per bin.
3. For each bin, run the **T-Hop** experiment exactly as in
   `scripts/run_experiments.py`: both modes, 6 noise levels, 3 repetitions.
   T-Hop is the right model — it is the fastest and it is the one whose PUM we
   reproduced exactly (Φ = 33/36).
4. Compute PUM per bin with `analysis.pum`, then correlate against mean bin size
   and against mean bin BDM.

### Practical notes
* Reuse `hyperparams.get('t_hop', 'ESOL', mode)` — do not re-sweep. State this as
  a limitation: hyperparameters were tuned on the whole dataset, not per bin.
* Scaffold splitting must be applied **within** each bin.
* Expected cost: T-Hop on ESOL is ~1 s/epoch, ~40 epochs to early stop, so
  4 bins × 2 modes × 6 noise × 3 reps ≈ 144 runs ≈ **2–4 hours**.
* Add a `--size-bin` option to `scripts/run_experiments.py` and a separate ledger
  (`results/runs_sizebins.jsonl`) so it cannot pollute the main campaign.

### Decision criterion
State it **before** running. Suggested: with 4 bins, report the Spearman
correlation between mean bin size and PUM, and the raw PUM values. Do not
over-interpret 4 points — the qualitative direction and the magnitude of the PUM
spread are what matter. If PUM spans ≥ 3/6 across bins in the predicted
direction, H₁ is supported.

### Threat to validity, to state in the write-up
Small molecules and large molecules differ in more than size (functional-group
diversity, ring content, label variance). Bin-level differences are therefore not
purely size effects. Report mean BDM per bin alongside, since within a dataset BDM
and size may decouple slightly — if they do, that is a bonus discriminator.

---

## §4. PHASE 2 — the scalable compressed-program measure

### Goal
Turn the index-set calculus's genuine advantage into a complexity measure that
**scales** and is **not** degree-determined.

### The advantage, measured
A query program `(DecimalRepertoire, Sumandos)` costs `2^|joinedNames|`, and
`|joinedNames| ≤ 4k` for chemistry. Measured at n = 400: **0.001 ms per query,
independent of n**. BDM is `O(n²)`; exhaustive landscape methods are `O(2ⁿ)` and
die at n ≈ 24. This is a real capability nobody else has.

### Hypothesis
The **length in bits** of the compressed program for a k-node query, aggregated
over queries, is a size-free complexity measure that (a) separates same-degree
graphs and (b) scales to hundreds of nodes.

### Screening test — run this first, it costs minutes
Does varying the **gates** add anything beyond the query geometry?

`joinedNames` does not depend on the gates at all. The `DecimalRepertoire` does.
So: fix a topology, sample many gate assignments, and ask whether the distribution
of program lengths separates same-degree pairs *better than* the gate-free
`query_overlap_profile` already does (97.6% / 100%).

* **If it does not** — drop the gate ensemble. The signal is geometric, the
  dynamics are a red herring, and the measure simplifies enormously.
* **If it does** — the ensemble is doing real work and Phase 2 proceeds with it.

### If the screen passes: build it
1. Define `program_bits(graph, k)` = mean (and spread) over k-node queries of
   `log₂|L| + (n − |joinedNames|)`, or the exact encoded length.
2. Run the 250-pair separation test (§2 standing rule).
3. Measure scaling to n = 1000 against BDM.
4. Rerun the paper's Table 4 / Table 5 with it and compare against
   `sumando_spread`, which is the current best size-free measure.

### Caution
Expect degree-determination unless k ≥ 2. That trap has fired four times
(§2). Screen before building.

---

## §5. PHASE 3 — reframe the axis to expressivity (1-WL)

### Goal
Replace an unanswerable question with an answerable one.

### The argument
Message-passing GNNs — which is exactly what Mix-Hop and T-Hop are — are
**provably bounded in expressive power by the 1-Weisfeiler-Leman test**. So the
1-WL colour histogram measures *what a GNN is capable of distinguishing at all*.

The paper asks *"how complex is this graph?"* and then correlates that with GNN
behaviour. The better question is *"how much structure is visible to this model
class?"* — which is directly about the models under study, is deterministic, needs
no training, no CTM table, and scored **100%** on the same-degree pairs.

### Why it is not circular
Using a **trained** GNN embedding to explain GNN behaviour would be circular, and
would also make the measure depend on training data and objective. 1-WL is the
*theoretical ceiling* of the model class, computed combinatorially. It is a
property of the graph, not of any trained artefact.

### Method
1. Define a WL-based scalar per molecule (e.g. entropy of the colour histogram
   after 3 refinement rounds, or the number of distinct colours normalised).
2. Standing-rule test on the 250 pairs (expected: passes — the hash does).
3. Rerun Tables 4 and 5 with it.
4. Also test the **Laplacian spectrum** (100%) as a second, independent axis.

### Expected outcome, stated honestly in advance
With six families, this will probably *also* correlate at about −0.8, because it
will also be size-correlated. **That is not a failure** — it is the point. Phase 3
is about reframing and about a defensible axis for future work; Phase 1 is what
settles the confound.

---

## §6. References — where everything is

### Documents
| file | contents |
| --- | --- |
| `FINDINGS.md` | ledger of established results, with evidence |
| `README.md` | project overview, layout, how to run |
| `NEXT_PHASES.md` | this file |
| `paper/` | the target paper (PDF + extracted text) |
| `reference/kaust_path_project/` | authors' code (read-only), incl. the hyperparameter PDFs |
| `reference/dgllife_0.3.2/` | DGL-LifeSci source the featurisers were ported from |

### Notebooks (all execute with 0 errors)
| notebook | cells | purpose |
| --- | --- | --- |
| `paper_walkthrough.ipynb` | 72 | the replication, §9 the index-set mirror |
| `method_comparison.ipynb` | 67 | BDM vs index-set adjudication, 11 claims |
| `conceptualizing.ipynb` | 53 | course on the index-set method itself |
| `understanding_complexity_measures.ipynb` | 49 | description length vs complexity measure |
| `understanding_bdm.ipynb` | 56 | what BDM really computes; why "counting blocks" is wrong; where the size confound actually lives |

Each has a generator: `notebooks/_build_<name>.py`. Edit the generator, rebuild,
then execute:
```bash
.venv/bin/python notebooks/_build_<name>.py
cd notebooks && ../.venv/bin/jupyter nbconvert --to notebook --execute --inplace \
  --ExecutePreprocessor.timeout=3600 --ExecutePreprocessor.kernel_name=imp-pathinfo <name>.ipynb
```

### Code
| module | key functions |
| --- | --- |
| `data.py` | `load_dataset`, `scaffold_split` |
| `bdm_complexity.py` | `dataset_aoac`, `graph_bdm` |
| `causalbool_mirror.py` | `molecular_network`, `deconvolve_molecule`, `graph_description_length`, `sumando_bits` (degree-determined), `sumando_spread`, `receptive_saturation`, `path_surplus` |
| `method_comparison.py` | `same_degree_pairs`, `separation_benchmark`, `query_overlap_profile`, `landscape_signature`, `knockout_profile`, `is_trajectory`, `eca_spacetime`, `recover_eca_rule`, `kraft_sum`, `program_description_length`, `mdl_local_program` |
| `analysis.py` | `pum`, `dichotomy_score`, `correlation`, `cluster_1d` |
| `hyperparams.py` | the authors' Optuna settings, all 36 cases |
| `paper_values.py` | transcribed published tables |

### Root-project sources consulted
| path | what it gave |
| --- | --- |
| `index-deconvolution/src/causalbool.py` | forward method, gate semantics |
| `index-deconvolution/src/deconvolution.py` | `essential_variables`, `deconvolve_column` |
| `src/integration/Alpha.m` | `onPossibleBehaviour`, `givePlaces`, sumandos construction |
| `src/Packages/Integration/BioMetrics.m` | `encodeNodeCost`, the `log₂C(n,d)` term |
| `doc/Tesis-UNAM/Capitulo4/` | Behaviour Tables, behaviour formulae, Table 4.14 |
| `papers/method/manuscript_formal/method_paper.tex` | pivots, offsets, `Dec(L,Ω)` |

### Terminology — corrected by the author, do not regress
* **output repertoire** — the `2ⁿ × n` table of what every node outputs. *(Not a
  "behaviour table"; that was my error.)*
* **Behaviour Table** — the thesis Chapter 4 *instrument*: columns `Node`,
  `node−1=pow`, `2^(pow−1)`, and the forward ratio. Its sum column is the
  **decimal anchor** `P(I_c)`. *(Corrected 2026-08-21: previously written "the AND
  pivot". `AND` is a canonical gate and gates do not have pivots; the word* pivot
  *belongs to the financial pivot of the price work. The two components of the
  compressed form are the **decimal family** and the **sumandos**.)*
* **sumandos** — **decimal offsets**: every subset sum of the free coordinates'
  weights. *Not* the free nodes. For the 7-node example: free coordinates
  {2,4,6}, sumandos {0,2,8,10,32,34,40,42}.
* **DecimalRepertoire** — the anchor set `L`; `givePlaces` adds the whole sumandos
  list to each anchor.

---

## §7. Insights worth carrying forward

1. **Replication and validity are different questions.** We reproduced every
   number and *then* found the finding is probably a size effect. Both are true.
2. **Intuition about what "reads structure" is unreliable.** Four quantities that
   felt structural were degree-determined. Only the 250-pair test settles it.
3. **The method has a resolution dial BDM lacks** — wiring `O(n)` → path index
   sets `O(nd^L)` → query overlap `O(n^k d)` → repertoire `O(2ⁿ)` — and the best
   results come from the *polynomial* layers.
4. **Randomness helps deconvolution.** Chaotic ECAs (30, 45, 110) are recovered
   exactly; simple ones (254, 50) leave 2 and 8 candidates, because simple
   diagrams never exercise the whole neighbourhood space. The method's limit is
   **class membership**, not randomness.
5. **Some objects cannot be generated by any network** — the bitmap and sine wave
   have one row with two successors. A proof, not a failed search. And "possible"
   can be vacuous: all-distinct rows admit any map, which is memorisation.
6. **A static graph has no dynamics to deconvolve.** The mirror's deconvolution is
   a *certificate* that the code is right, not a measurement of the molecule.
7. **The equivalence question with BDM is well posed and open.** For objects a
   class generates, `D` bounds K from above while CTM estimates it by sampling —
   two routes to the same quantity. Clean test: ECAs, where both classes apply and
   Rule 110 is universal. Must **not** be argued from static graph description
   lengths (that is claim J).

---

## §8. State of the machine

* **41 tests pass**: `.venv/bin/python -m pytest -q`
* **Training campaign** (generated by `scripts/campaign_status.py`; verbatim):

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

  Resume:
```bash
.venv/bin/python scripts/run_experiments.py --models graphormer --ledger results/runs.jsonl --quiet
.venv/bin/python scripts/run_experiments.py --models t_hop     --ledger results/runs_thop.jsonl --quiet
.venv/bin/python scripts/run_experiments.py --models mix_hop   --ledger results/runs_mixhop.jsonl --quiet
```
* **Mirror sweep**: `.venv/bin/python scripts/causalbool_mirror.py` (~30 s)
* **BDM / AOAC**: `.venv/bin/python scripts/compute_bdm.py` (~7 s)
* Remaining gaps in the campaign: Graphormer on Lipophilicity only (8 cells +
  one 2-replicate cell — see the generated block above). None of the conclusions depend on
  them.

---

## §9. Suggested first action next session

```bash
cd imp-pathinfo-paper
.venv/bin/python -m pytest -q            # expect 39 passed
```

Then Phase 1, §3: add `--size-bin` to `scripts/run_experiments.py`, write the
binning helper, and launch ESOL. State the decision criterion in writing before
the first run completes.
