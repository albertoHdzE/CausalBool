# Research notes: open threads from the causal deconvolution replication

Findings that arose while replicating Zenil, Kiani, Zea and Tegnér (2019) which are **not**
part of the replication verdict. They are recorded here as **seeds for future research** --
each is an opened line of work with evidence already attached, not a loose end to be tidied
away.

The framing matters and is deliberate. None of this is an attempt to defeat BDM. BDM is the
reason any of it is computable at all, and the questions below only became askable because
the Coding Theorem Method exists. The aim is to build on it.

Everything below is reproducible from `notebooks/paper_walkthrough.ipynb`, Part XIII.

---

## Thread 1 — Returning a number is not the same as returning a correct answer

**The observation.** BDM always answers. The index-set calculus often refuses. That looks
like a straight win for BDM until you ask what the answer is *for*.

**The hypothesis** (Alberto, 2026-08-01): where a process is evidently algorithmic, BDM
returns a value but that value need not be *correct* — it works on information content, and
finding a model is as impossible for it as for us; but on evidently algorithmic processes we
have at least the same power, and plausibly more, because we can exhibit the program.

**Evidence gathered so far.**

*BDM is many-to-one on mechanisms.* Running all 256 elementary rules from one shared initial
condition:

| | |
|---|---|
| BDM range over the 256 diagrams | 164 – 5445 bits |
| rule pairs within 0.5 bits of each other | 41 |
| rule pairs within 1.0 bits | 78 |
| rule pairs within 5.0 bits | 358 |
| **rules identified uniquely by the index-set calculus** | **256 / 256** |

Two genuinely different programs can receive the same number, and from the number alone the
mechanism cannot be recovered — a scalar has nowhere to put a rule. So "BDM always answers"
should be read as: *it always answers "how much structure?", never "which mechanism?"*.

*BDM exceeds a certified upper bound on algorithmic data.* Because we recover the actual
program, we can write a two-part code — `D(mechanism) + C(initial row) + log2(steps)` — and
that is a **certificate**, not an estimate: a program exists that reproduces the diagram
exactly, so `K(diagram) <= two-part code + O(1)` is a fact about that diagram.

| | |
|---|---|
| rules where BDM exceeds the certified bound | **254 / 256** |
| median ratio BDM / bound | 2.8× |
| maximum ratio | 29.5× |

Rules 110, 30 and 45 all have a mechanism costing 19.02 bits, yet BDM assigns their diagrams
3121, 4837 and 5238 bits. The spread is real — the outputs do look different — but it is a
property of what the program produced after 64 steps, not of the program.

**The counter-evidence, which must stay in view.** On uniform random data no program exists,
no certificate can be issued, and BDM's large value is simply correct. And for the trivial
rules the ratio falls to 1.0 or below: our two-part code still pays for a 64-bit seed that
rule 0 immediately erases, so ours is not always the tighter description either.

**Open questions.**

1. Is the over-estimate systematic in a characterisable way — a function of runtime, of
   Wolfram class, of the light-cone growth rate? If BDM ≈ f(steps) × program length on
   algorithmic data, that is a correction, not just a criticism.
2. Does the same gap appear for the biological networks of the 2019 paper
   (`imp-causal-paper/`), where BDM is used to rank real perturbations? That is where it
   would actually matter.
3. Is there a class of objects where BDM *under*-estimates against a certificate? None seen
   yet; worth looking, because it would bound the phenomenon.

---

## Thread 2 — The noise cliff, and how to cross it

**The observation.** The strict index-set consistency test dies at **0.1% noise** — one
flipped bit in about three and a half thousand — while BDM keeps returning usable numbers at
any corruption level.

**But the cliff is an artefact of the test, not of the calculus.** Replacing "every
observation must be consistent" with "take the rule agreeing with the most observations"
recovers rule 110 **correctly up to 20% noise**, breaking only at 35%.

| noise | strict | majority vote | BDM |
|---|---|---|---|
| 0% | rule 110 | rule 110 | 2910 |
| 0.1% | **fails** | rule 110 | 3051 |
| 5% | fails | rule 110 | 5632 |
| **20%** | fails | **rule 110** | 6705 |
| 35% | fails | wrong rule | 6807 |

Across that whole range BDM returns only a growing number, never a rule.

**Open questions.**

1. Majority vote is the crudest possible robustification. What is the *principled* one? A
   likelihood over index sets, a minimum-description-length trade-off between mechanism cost
   and exception cost (`D(model) + D(exceptions)`), or an interval-valued index set that
   admits "this cell is consistent with rules {60, 124}"?
2. The MDL form is attractive because it needs no threshold: accept the mechanism whose
   total cost, *including* a literal list of the observations it fails to explain, is
   smallest. At zero noise it reduces to the strict test automatically.
3. Where exactly is the information-theoretic limit? At 50% noise no method can recover
   anything. Between 20% and 50% there should be a computable boundary.
4. Does robustness scale with data volume? Majority vote at 20% noise used 3500 samples.
   Does 35% become recoverable with 35 000?

---

## Thread 3 — A measure from the mechanism side

**The idea** (Alberto): our method returns models, not numbers, which costs us the ability to
rank. Could we produce a number anyway — BDM over our recovered networks, or a description
length of our models?

**Prototype built.** `src/imp_causalnet_paper/measure.py`:

* `model_description_length` — index set plus minimal DNF, at `log2(3)` per stated position
  (a cell is absent, present, or present negated). Exact, closed-form.
* `two_part_code` — `D(mechanism) + C(seed) + log2(steps)`, the classical MDL quantity, and
  the certificate used in Thread 1.

**What works.** It is a genuine number, it is exact, and it is meaningful in a way BDM's is
not: it is the length of a program we actually have. It correctly ranks rule 0 < rule 204 <
rule 60 < rule 110 by mechanism cost.

**What does not, yet.** It is *coarse*: over all 256 elementary rules it takes only **8
distinct values**, because a 3-input rule can only have support 0–3 and a handful of DNF
terms. Spearman correlation with BDM across the 256 rules is only **+0.28**. As a ranking
device on small rule spaces it is nearly useless.

That is not a flaw so much as a statement of what it measures. Rules 110, 30 and 45 *are*
equally simple as programs. BDM separates them because their outputs differ; the model cost
does not, because their mechanisms do not.

**Open questions.**

1. The two quantities are complementary, not competing. Is the right object the **pair**
   `(mechanism cost, output complexity)`, or their ratio — a "runtime amplification factor"
   measuring how much apparent complexity a program manufactures per bit of its own
   description? Rule 30 would score very high, rule 204 near 1.
2. Would granularity improve on richer mechanism classes — Boolean networks with dozens of
   nodes, where support sizes and DNF term counts have real spread? The 8-value ceiling may
   be an artefact of elementary CA, not of the measure.
3. **This is a seed, not a duplicate.** The root project already has description lengths `D`
   and `D_v2` (`BioMetrics.m`, `papers/method/manuscript_formal`), but those measure a
   *given* network. What is new here is measuring a **recovered** one, and pairing it with
   the seed and the runtime to form a certificate. The line of work to open is therefore:
   take `D`/`D_v2` as the mechanism term, and build the two-part code on top of it as a
   first-class quantity of the calculus — `D(model) + C(input) + log2(runtime)` — with the
   certificate property as its defining feature. That is the thread; the prototype in
   `measure.py` is only its first stake in the ground.
4. Can the certificate be turned into a *general* tool — given any object, search for a
   short generating program in some class and report `min(BDM, two-part code)` as a strictly
   better estimator of `K` than either alone? That would be an actual improvement to BDM
   rather than a critique of it, and it is the most promising item on this page.

---

## Provenance

All figures and tables above are produced by Part XIII of
`notebooks/paper_walkthrough.ipynb` and are deterministic (seeded). The modules involved are
`measure.py`, `causal_models.py`, `causalbool_mirror.py` and `complexity.py`.
