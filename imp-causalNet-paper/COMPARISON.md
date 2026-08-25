# Face to face: BDM causal deconvolution versus the index-set causal calculus

Every row below is backed by a run in `notebooks/paper_walkthrough.ipynb` (Part XIII), on the
same objects the paper itself uses — in several cases on the paper's own published figures.

## The one-line difference

> **Zenil's method** asks *"how long is the shortest program for this data?"* and reads
> structure off how that length reacts to poking. It answers for **any** object, **always**,
> **approximately**, and **never tells you what the program is**.
>
> **The index-set calculus** asks *"what is the program?"* and returns the smallest set of
> inputs plus the exact Boolean function — or a proof that none of the assumed form exists.
> It answers **only** where a mechanism class can be assumed, but **exactly**, **by name**,
> and **checkably**.

A scalar and a mechanism are different kinds of answer. Neither subsumes the other.

## Claim by claim

| # | Capability | Zenil et al. (BDM) | Index-set calculus | Advantage |
|---|---|---|---|---|
| 1 | Assign a complexity value to **any** binary object | yes — strings, images, graphs alike | **no** — needs an assumed mechanism class | theirs |
| 2 | Per-element information footprint | yes — the paper's core algorithm | yes, but a decision rather than a score | both |
| 3 | Fig. 1: separate a regular from a random string segment | yes — 29.5× ratio in mean \|I\| | yes — exact model one side, none the other | both |
| 4 | Fig. 1: return the **generating program** | **no** — drawn by hand in Figs. 1C–E, not inferred | yes — `b[i] = NOT b[i-1]`, inferred and run forward | **ours** |
| 5 | Fig. 1: locate the seam between mechanisms | approximately, from a break in the signature | exactly, at **bit 52**, with a proof bits 50–51 still fit | **ours** |
| 6 | Figs. 1F–G: separate CA of grossly different complexity | yes — Cliff's delta −0.770 | yes — rules 255 and 110 recovered exactly | both |
| 7 | Fig. 2: separate CA of **similar** complexity (60 vs 110) | **no** — delta 0.15 on their own figure | yes — 96.7% attribution | **ours** |
| 8 | Fig. 2: say **which rule** made each region | **no** — the footprint is unlabelled | yes — by rule number, from 256, unsupervised | **ours** |
| 9 | Recover a full Boolean network from a space-time diagram | no | yes — exact on the full 2¹² global map | **ours** |
| 10 | Fig. 3C: split a complete graph from a scale-free graph | **no** — planted edges at ranks 93/162/163 | **yes** — precision 1.00, recall 1.00, mechanism named | **ours** |
| 10b | Fig. 3D: split Erdős–Rényi from scale-free | no — planted edges near rank 500/980 | no — but *reports* that neither side has a law | neither |
| 11 | Sec. 3.2: split graphs of **low** algorithmic complexity | yes — planted edges at ranks 0, 1, 2 | yes — identical ranks 0, 1, 2 | both |
| 12 | Fig. 5: quantify robustness to added random links | yes — precision 1.000, FPR 0.000 | yes — same algorithm, index substituted | both |
| 13 | Sup. 8–9: beat entropy and compression on sensitivity | yes — 1325 distinct values vs 1 and 44 | not applicable — not a graded measure | theirs |
| 14 | Handle data with **no** deterministic mechanism | yes — degrades gracefully, always answers | **no** (strict) — fails at 0.1% noise | theirs |
| 15 | Rank two arbitrary unrelated objects | yes — a scalar does that by construction | **no** — mechanisms are not ordered | theirs |
| 16 | **Falsify its own answer** | no — a footprint cannot be run | yes — run the mechanism; it fails or it does not | **ours** |

Tally: **ours 7, both 5, theirs 4, neither 1.**

## The noise experiment — the fairest test

A clean rule-110 diagram, corrupted at a growing rate:

| noise | index-set, strict | index-set, majority vote | BDM |
|---|---|---|---|
| 0% | **rule 110** | rule 110 (100%) | 2910 |
| 0.1% | *no rule survives* | rule 110 (99.5%) | 3051 |
| 1% | *none* | rule 110 (97.7%) | 3504 |
| 5% | *none* | rule 110 (87.2%) | 5632 |
| 10% | *none* | rule 110 (77.6%) | 6301 |
| **20%** | *none* | **rule 110** (61.8%) | 6705 |
| 35% | *none* | wrong rule | 6807 |

Three conclusions, and the middle one is the important one.

1. **BDM never fails.** It returns a number at every level, rising monotonically with the
   corruption. A method that always answers can be pointed at data you do not yet understand.
2. **The strict test is brittle to the point of uselessness on noisy data.** One flipped bit
   in ~3500 destroys it. This is the real cost of demanding exactness, and it is why the
   index-set calculus cannot simply replace BDM.
3. **But a one-line robust variant is tough.** Taking the rule that agrees with the *most*
   observations, rather than all of them, recovers rule 110 correctly **up to 20% noise** —
   and across that entire range BDM returns only a growing number. It never returns "rule
   110", because a scalar has nowhere to put a rule number.

So the fair statement is not "ours is brittle, theirs is robust". It is: *the exact test is
brittle, a trivially robust version of it is not, and wherever the robust version works it
recovers something BDM is structurally incapable of returning.*

## What our method genuinely cannot do

Three limitations, none of which is a matter of implementation effort.

**It needs a mechanism class.** BDM works on anything because it assumes nothing. Ours must
be told what sort of thing might have generated the data — a Boolean function of a
neighbourhood, a recurrence over lags, a graph law. Where that class can be written down the
method is exact; where it cannot, the method is silent.

For graphs this was initially a hard limit, because a neighbourhood in an *unlabelled* graph
has no canonical index-set description. `graph_mechanism.py` resolves it by recognising laws
**structurally** rather than by index — a component either is or is not isomorphic to a
complete graph, star, `k`-ary tree, cycle or path — which is labelling-free and exact. The
limit that remains is the library: a graph generated by a law outside it, such as
preferential attachment, is reported as having no mechanism. That is correct in the strict
sense (attachment is stochastic, so there is no deterministic law) but it does mean the
method's reach is the reach of its library.

**It produces no comparable number.** You cannot ask which of two unrelated objects is "more
complex". Whenever the question is really about ranking or scoring, BDM is the right tool.

**Exhaustive verification costs 2ⁿ.** The `global_map_exact` guarantee is only computable for
narrow tapes. Beyond about twenty cells we can still recover mechanisms, but we can certify
only that they reproduce what was observed, not that they match the true map everywhere.

## Where this leaves the paper

The paper's introduction argues for our side of this. It criticises measures that "only
assign a number to data from which nothing else can be extracted", and promises access to
"the rules generating the data that represent the generative model".

That is the right ambition. What this replication shows is that **BDM does not deliver it** —
Figure 1's generating program is drawn rather than inferred, and Figure 2's footprint cannot
name either rule — while **index sets can**, on the same objects, including the paper's own
published figures.

The two are complements. BDM found nothing in Figure 2 because two programs of similar length
look alike to a length-based index; the index-set method separated it because it never
compares lengths. Conversely, on noisy data and on unlabelled graphs, BDM kept returning
usable numbers where ours returned nothing at all.


---

# Inside this paper only: the figure-by-figure parallel

The table above compares the methods in general. The question that matters for this
replication is narrower: **within the scope of this paper, can the index-set calculus do
everything BDM does?** Part XIV of the notebook answers it deliverable by deliverable.

| figure | problem the paper states | their steps → result | our steps → result | verdict |
|---|---|---|---|---|
| 1A–B | separate two string segments made by different programs | perturb each bit → 29.5× ratio | minimal lag index sets → exact model one side, provably none the other | parallel |
| 1C–E | exhibit the generating program of `01ⁿ` | **drawn by hand** → a picture | infer the recurrence → `b[i] = NOT b[i-1]`, run forward | **ours stronger** |
| 1F–G | separate CA of grossly different complexity | BDM footprint → delta −0.770 | per-cell rule consistency → rules 255 and 110 recovered; Fig. 1F regenerated 4026/4026 | **ours stronger** |
| 2 | separate CA of **similar** complexity | BDM footprint → delta 0.15, **fails** | per-cell consistency → 96.7%, both rules named from 256 | **ours solves it** |
| 3A–B | deconvolve K-ary trees | minimal-loss edge removal → components | recognise the law → `kary_tree(k=2)`, any labelling | parallel |
| 3C | split a complete from a scale-free graph | signature cut → ranks 93/162/163, **fails** | peel the largest exact law → **precision 1.00, recall 1.00** | **ours solves it** |
| 3D | split E-R from scale-free | → rank ~500/980, fails | → correctly reports **no mechanism** on either side | both fail, ours says so |
| 3E | a hierarchy of source likelihood | order by algorithmic difference | peel by explanatory power → ordered, named, costed | parallel |
| 4 | deconvolve a 3-subgraph composite | signature + `log₂(2)+ε` → 2 of 4 planted edges | peel exact laws → both laws recovered, 2 of 4 edges | parallel |
| 5 | robustness to additive noise | sweep → precision 1.000, FPR 0.000 | same sweep → exact while a law survives | parallel |
| Sup. 8–9 | beat entropy and compression on sensitivity | count distinct values → 1325 vs 1 and 44 | **not applicable** — not a graded measure | theirs only |
| Alg. 1–2 | a parameter-free terminating criterion | cut where the gap exceeds `log₂(2)+ε` | accept a layer iff boundary edges < internal edges | parallel |

**Ten of twelve deliverables have a genuine parallel, and in four of those ours is stronger
or outright solves what BDM does not** — including Figs. 2 and 3C, the paper's two headline
demonstrations.

## What causal deconvolution means for a graph in our calculus

`graph_mechanism.py`. A graph made by a short program has an **index-set law**: a complete
graph joins every node to every index but its own; a star to one fixed index; a `k`-ary tree
node `i` to index `(i-1)//k`. These can be *recognised*, exactly — remove one edge from `K₁₂`
and the law is gone.

The deconvolution is then: **peel off the largest exactly-generated component, and keep it
only if detaching it costs fewer edges than it explains.** That acceptance test is not a
threshold we picked; it is the paper's own Section 3.2 inequality
`|P(G₁)| + |P(G₂)| + |P(e)| > |P(G₁G₂)|` read in index-set terms. It is why the 7-node clique
that occurs by chance inside Fig. 3D's random half is rejected — 21 internal edges against
178 boundary edges — with nothing fitted and no statistical test.

## The one exception, and the one caveat

**Sup. Figs. 8–9 have no parallel.** That experiment counts how many distinct *values* each
index produces, and we do not produce values. If the question is "how graded is your
measure?", the honest answer is that ours is not a measure.

**And the parallel is this complete only because the paper's test objects are deterministic
and noiseless by construction.** That is the regime the index-set calculus is built for. Move
to noisy data and the strict method stops answering while BDM keeps returning usable numbers
(see the noise table above). Within this paper that regime never arises — which is precisely
why the parallel holds as well as it does.

---

*Correction 2026-08-24 (AUDIT01/T2.3): the two "Cliff's delta −0.78" values above were
re-misquotations of the executed notebook output, which is **−0.770** (Part I cell,
Fig. 1F–G block; artifact `results/fig1_separation.json`). The capability tally in this
file ("ours 7, both 5, theirs 4, neither 1") was verified by machine count against the
table above (`results/capability_tally.json`) and is unchanged.*
