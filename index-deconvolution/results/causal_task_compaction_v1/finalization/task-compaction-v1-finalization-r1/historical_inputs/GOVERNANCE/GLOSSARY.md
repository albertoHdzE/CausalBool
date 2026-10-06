># GOVERNANCE/GLOSSARY.md — synchronized copy
>
> **Canonical source of truth:** `~/Documents/projects/series-deconvolution/GLOSSARY.md`
> @ sibling commit `d26343a` (§1e — *pivot* is a finance term — 2026-09-07).
> Recopied 2026-09-07 by AUDIT04-F after the author-permitted sibling edit;
> previous syncs @ `b868cd0` (AUDIT01/T27), `77a5381` (AUDIT01/T1.4).
> On definitions this file outranks every other document in this repository.
> Verify freshness: `tools/check_glossary_sync.sh` (0=clean, 1=drift, 2=sibling absent).
---

## 1. THE DEFINITION

> **A pivot is a position that a *causal* process — one with no look-ahead — reproduces
> EXACTLY. What no such process reaches is the RESIDUAL.**

Source, and it is the project's founding object, not a Level-10 invention:

- `PROTOCOL_order_discovery.md:142-148` — *"The positions that a discovered process
  reproduces exactly are the pivots… The positions that no process reaches are the
  residual."*
- `bitacora/14_level3_behaviour_tables.md:63-64` — *"The pivots, the points and segments
  where **local determinism holds exactly**, are the gold."*
- Level 1, `experiments/exp01_connected_inputs_and_sumandos.py` (renamed 2026-09-07 from
  `exp01_pivots_sumandos.py`, see §1e) — the **essential variables that determine the
  output** vs the **free offsets that never change it**.

**Pivot = the exactly-determined part.** That is the whole of the shared definition, and
it is *all* that transfers between domains. **The name of the complement does not
transfer** — see §1c, which is the correction of 2026-08-22.

### 1a. In the Boolean indexing method

A coordinate is **free** exactly when the *schema under consideration* does not depend on
it, and the **free coordinates** contribute **sumandos** — offsets that never change the
result. The **connected inputs** `I_c` are the coordinates that can matter at all, so the
**disconnected** coordinates are free in every schema.

> **Free is per schema, not per node. Disconnected ⇒ free; free ⇏ disconnected.**
> This sentence is the whole of §1d, and it is the single most expensive confusion in
> the project's history — settled, then re-adopted, four times. Read §1d before writing
> the word *sumando* anywhere.

`P(I_c) = Σ_{i∈I_c} w(i)` is therefore **not "the pivots"**: it is the *decimal encoding of
the pivot set*. Call it the **decimal anchor**; `L` is the **decimal family**. Calling
`P(I_c)` "the AND pivot" conflates a set with its weight-sum, which is the specific slip
that made the word look like a misnomer. `Dec(L,S) = {ℓ+s}` unfolds anchor + sumandos into
the full repertoire — and *that* is where the word **deconvolution** comes from, in
`index-deconvolution` and in this project's name.

### 1b. In finance — the **financial pivot**

The **oracle** is God's answer key: the in-hindsight optimal buy/sell schedule under
round-trip cost `c`, computed **with the future visible** (exact O(N) DP).

> A **financial pivot** is an oracle action point that a **causal, one-pass** process — the
> directional-change construction at `θ = c` — recovers **exactly, with no look-ahead**.

The **residual** is the part of God's view that *requires* the future: swings a
look-ahead optimiser catches and a greedy one-pass construction cannot. Quoting
`bitacora/21`:

> *"The oracle is a globally optimal schedule; the directional-change construction is
> greedy and causal. The 0.4% of oracle points that are not pivots are swings a look-ahead
> optimiser catches that the greedy, one-pass construction misses — **the price paid for
> causality**."*

**Measured here, 2026-08-22**, over all 12 series × 4 θ (θ matched to `c` via
`kappa_for_round_trip`): containment **56,500 / 56,509 = 0.9998**, exact on **42 of 48**
(series, θ) pairs, oracle residual **784 / 57,284 = 1.37%**. Bitácora 21 reports 1.000,
11/12, and 0.4% on its own single-θ sweep of 12 series — same direction and order, wider
sweep here. Both are on the record; neither is quoted as the other.

**θ must equal c.** Comparing θ against a mismatched κ measures nothing.

### 1c. The two decompositions are **not the same shape** — corrected 2026-08-22

An earlier version of §1 read *"Pivot = the exactly-determined part; sumandos = the free
part"*, as if one dichotomy spanned both domains. **That is wrong**, and it is the error a
`CausalBool`-side agent most needs to see, because it silently exports a finance concept
into the Mathematica core and vice versa.

There are **two different decompositions**, and only the *first* term of each is a pivot:

| | **pivot / residual** | **decimal family / sumandos** |
|---|---|---|
| what it is | a partition of the oracle set **by causal reachability** | the **compressed form** of an exhaustive repertoire / complex behaviour |
| where | finance; any series under a causal model | the Boolean indexing method (Mathematica core) |
| lossless? | **No.** The residual is *lost* — it requires the future | **Yes.** `Dec(L,S) = {ℓ+s}` reconstructs the repertoire exactly |
| second term is… | what causality **cannot reach**: a failure, the price of causality | free offsets, **fully determined and enumerable**: part of an exact reconstruction |
| papers call it | — | *decimal* and *offset* |

**A residual is a failure; sumandos are a success.** Equating them inverts the epistemic
status of both. Two corollaries follow, and they are the practical test:

- In the Boolean indexing method **there is no residual**, because the compression is
  exact. Anything there called a residual is a category error.
- In finance **there are no sumandos**, because nothing there is a subset-sum lattice over
  free coordinates. Anything there called a sumando is a category error.

**The finer slip that produced the confusion.** In the Boolean method the coordinates split
into **connected** `I_c` and **free**. Each side then gets *its own decimal encoding*:

| coordinate set | its decimal encoding |
|---|---|
| **fixed by the schema** → the **pivot coordinates** | **decimal anchor** `P`, ranging over the **decimal family** `L` |
| **free in the schema** — do not change membership | **sumandos** `S` |

So *sumandos* is **not** the complement of the fixed coordinates: it is the complement's
**encoding**, and it stands parallel to the **decimal anchor**, which is the fixed set's
encoding. The complement of the **connected inputs** is the **free coordinates**.
`exp01_pivots_sumandos.py` named a **set** and an **encoding** side by side, and reading
that filename as a partition is how a lossless factorisation got mistaken for a lossy one.
*(That file has since been renamed — see §1e.)*

**Rule.** Write **pivot / residual** for causal reachability. Write **decimal family /
sumandos** (or *decimal / offset*) for the compressed form. Never cross them.

> **Amended 2026-09-07 by §1e.** This subsection formerly wrote "pivot coordinates" for
> the coordinates a schema fixes. That usage is withdrawn: *pivot* is now reserved for
> finance. Read **connected inputs** wherever this section previously said *pivot
> coordinates*.

---

### 1d. **Sumandos are NOT "the disconnected coordinates."** (author ruling, 2026-09-03)

This has now been settled and then re-adopted **four times**, and each recurrence has cost
a long conversation. The cause is always the same: a reader meets the function
`allOffsets[n, connected] := ... Complement[Range[n], connected] ...`, which computes only
the disconnected part, and promotes that implementation detail into the definition.

> **Definition.** The **sumandos** of a schema are the fillings of **its own don't-care
> positions**, wherever those positions fall. `Ω` is the offset family they generate.

**Rule 110 is the standing counterexample.** It has three inputs and **all three are
connected**. Under the wrong reading its free coordinates are empty, so `Ω = {0}`, there
are no sumandos and no compression, and `L` must list all five minterms. Under the correct
reading it is three schemata — `01*`, `10*`, `*10` — and **every one of their don't-cares
sits on a connected input**. The wrong reading cannot express the right one.

Established 2026-07-09 in `index-deconvolution/bitacora/11_gate_confusion_arity_schemata.md:83`
(*"the don't-cares … are exactly the sumandos"*); re-derived and re-verified 2026-09-03 in
`audit/AUDIT03_R3_description_length/probe_sumandos_two_readings.py`.

**Why it matters quantitatively, not just terminologically.** The narrow reading sees
compression only from disconnected coordinates, so it cannot distinguish an OR from an XOR
of the same in-degree: both are "one gate with `n−d` free coordinates". The general reading
separates them exactly — an OR of in-degree 10 covers 1023 minterms with **10** schemata,
while an XOR of in-degree 10 covers 512 minterms and needs **512**, because none of its
minterms merge. A measure blind to that is not measuring the object.

**Permitted phrasing.** "The disconnected coordinates are free in every schema, and are the
special case always present" — true, and useful. **Forbidden phrasing.** Anything of the
form "the sumandos are / correspond to / are generated by the coordinates that do not feed
the node", stated as the definition. The special case may be *illustrated*; it may never be
*defined as* the general object.

---

### 1e. ***Pivot* is a finance term. It has no place in the method vocabulary.** (author ruling, 2026-09-07)

§1c and §3 previously permitted **pivot coordinates** inside the Boolean indexing method,
on the reasoning that *pivot* names one shared concept instantiated in two domains. That
permission is **withdrawn**. The author's ruling is that *pivot* denotes a specific kind of
set **in finance**, and that letting it stand anywhere near *decimals and sumandos* is a
standing invitation to re-import the lossy partition into a lossless factorisation — which
is confusion source #5, and which §1c diagnosed without removing the word that causes it.

> **Rule.** In the Boolean indexing method the vocabulary is:
>
> | object | name |
> |---|---|
> | the coordinates that can matter at all | **connected inputs** `I_c` |
> | the coordinates a given schema actually fixes | **essential variables** |
> | their decimal encoding | **decimal anchor** `P`, ranging over the **decimal family** `L` |
> | the coordinates a schema leaves free | **free coordinates** |
> | the fillings of those free positions | **sumandos** `S` (§1d) |
>
> The word *pivot* appears in none of these rows, and must not be introduced into any of
> them — not in prose, not in an identifier, not in a filename, not in a JSON key.

**Why a naming rule needed to become a ruling.** §1c already said the two decompositions
are not the same shape, and the confusion recurred anyway, because the word survived in the
code while the correction lived only in this file. A reader who meets `pivots_essential_bits`
in a dict does not consult a glossary; they conclude that pivots *are* the essential bits.
The remedy is to remove the word from the objects, not to explain it better.

**Scope.**

- **Method-sense uses are renamed** using the table above. Measured 2026-09-07: 17
  occurrences in 7 files, all in `index-deconvolution/` plus one paper-code file.
- **Finance-sense uses keep the concept and gain the proper name** — write **financial
  pivot** in prose (§1b, §3). `directional_change_pivots()` keeps its identifier: it names
  the *recovery method*, and §2 confusion source #1 is about defining a pivot by that
  method, not about the function's name.
- **Stored result keys and executed notebooks are not retro-edited** (§7). Renaming
  `"oos_gain_pivot"` (100 recorded occurrences), `"n_meta_pivots"` (12) and
  `"mean_oos_pivot"` would invalidate recorded Level 5–17 values; a terminology fix does not
  get to move measured numbers.
- **Ordinary-English uses are retired too** — see the superseding note in §8. Adjudicating
  a sense is exactly the work this ruling exists to abolish.

---

## 2. THE FIVE SOURCES OF CONFUSION — each an error to be fixed at source

| # | error | where it lives | correction |
|---|---|---|---|
| 1 | **Defining a pivot by its recovery *algorithm*** — "a pivot is a confirmed turning point; walk the series and when it reverses by θ…" | `notebooks/build_09.py` Step 1 → nb 09; `level5/pivots.py` | The θ-walk is **how pivots are recovered**, not what they *are*. They are the oracle points a causal process gets exactly right. **Both FIXED 2026-08-22**, notebook re-executed clean |
| 2 | **"perfect trades = pivots" as an identity** | `bitacora/21` early framing | Retracted by `bitacora/22`: **containment, not identity**; the oracle is the strictly larger set |
| 3 | **"it is only geometry, worth only interpretive"** — demoting the relation entirely | `bitacora/22`, `notebook 09` closing, and *my own* earlier text | Two different things were merged. The definition-level containment is **constitutive**: every *pivot* is an oracle point. **Amended 2026-08-23:** the *measured rate* (0.9998) is the θ-walk's **fidelity as a recovery method** — 6 exact ties + 3 walk errors in 56,509 outputs (`results/containment_exceptions.json`) — and what holds on a sine wave is that fidelity, expected of any sound method, not evidence about markets. Keep the definition, discard the "look, they agree!" claim |
| 4 | **`P(I_c)` called "the AND pivot"** | method papers, `CausalBool.m` | Conflates the pivot *set* with its decimal *encoding*. It is the **decimal anchor** |
| 5 | **Pairing *pivot* with *sumandos* as one dichotomy** — treating the free offsets as if they were the unreachable part | this GLOSSARY's own first settled draft, and the first draft of notebook 01 R1 | Two decompositions, different shapes: **pivot/residual is lossy**, **decimal-family/sumandos is lossless**. See **§1c**. Author-identified, 2026-08-22 |

**Consequence for §1b:** because the definition is causal-exact-recovery, the θ-walk's
universality (its fidelity is ~1 on a sine wave) is *expected and fine* — it says the
causal method almost never invents points outside the answer key (0.9987–0.9997 across
12 GBM seeds; the exceptions are ties and walk errors, which are not pivots). That is a
property of a sound recovery method, not a market claim.

---

## 3. Naming rules

- **pivot** — reserved for the concept in §1. In finance always write **financial pivot**.
- **residual** — what no causal process recovers. **Lossy.** Pairs with *pivot*, and only
  with *pivot*. Never appears in the Boolean indexing method, whose compression is exact.
- **decimal anchor** `P(I_c)`, **decimal family** `L`, **sumandos** `S` — never "pivot",
  and never "residual". **Lossless.** *Sumandos* pairs with *decimal family*, and only with
  it. Never appears in finance. Papers may say *decimal* and *offset*; both are correct.
- **free coordinates** — the complement of the **connected inputs**. This, not *sumandos*,
  is what the fixed coordinates are opposed to inside the Boolean method (§1c).
  ~~"the complement of the *pivot coordinates* … is what the word 'pivot' is opposed to
  inside the Boolean method"~~ — **struck 2026-09-07 by §1e**: *pivot* is finance-only, so
  it names nothing inside the method and cannot be the thing anything is opposed to.
- `directional_change_pivots()` keeps its name: it is the **causal recovery method**.
- ~~Ordinary English *pivot* ("Pivot to Hybrid Encoding", `PIVOT_HYBRID`) is unaffected~~ —
  **superseded 2026-09-07 by §1e**; see §8.

---

## 4. Other terminology corrected by the author — do not regress

*From `CausalBool/imp-pathinfo-paper/NEXT_PHASES.md`, amended by §2 above.*

- **output repertoire** — the `2ⁿ × n` table of what every node outputs. *Not* a
  "behaviour table".
- **Behaviour Table** — the thesis Chapter 4 *instrument*: columns `Node`, `node−1=pow`,
  `2^(pow−1)`, and the forward ratio. Its sum column is the **decimal anchor**
  ~~"AND pivot"~~.
- **sumandos** — decimal offsets: every subset sum of the free coordinates' weights,
  where *free* is **per schema** (§1d). *Not* the free nodes, and **not** the
  disconnected nodes.
- **DecimalRepertoire** — the **decimal family** `L`; `givePlaces` adds the whole sumandos
  list to each anchor.

---

## 5. Terms used in *this* project

| term | meaning | defined in |
|---|---|---|
| **occurrence set** | the integer indices at which events occur — financial pivot times, binary flip times, or oracle action points | `operators.py` |
| **gaps** | first differences of an occurrence set; **the integer sequence we search OEIS with** | `operators.py` |
| **clock** | the point process of occurrence times | sibling §2 |
| **occurrence extractor** | any operator mapping a series to an occurrence set: `directional_change_pivots` (positive real), `binary_flip_times` (binary), `level_crossing_times`, `oracle_points` | `operators.py`, `oracle.py` |
| **operator group** | the declared, versioned, **hashed** set of operators in force for a run. Growing it mid-experiment invalidates every null | `operators.py` |
| **baseline** | `min(Elias, histogram)` — the length a match must strictly beat (G1) | `mdl.py` |
| **admissible code** | passes `validate_code_length` — **two-sided since 2026-08-23** (`bitacora/05` B2): an upper scale bound (`L ≤ 2×` a real code on random objects), a sampled Kraft check (`Σ 2^-L ≤ 1` over 64 distinct fixed-length objects), and an entropy floor (`mean L ≥ 0.95·n·H` on a declared uniform source). Still a tripwire, **not** a Kraft proof over the whole domain — a code tailored to the probe sources could pass. Raw BDM fails by design (too loose); `L(x)=0`, `L(x)=1`, `log2 len`, `½·Elias` and plug-in entropy all fail the lower bounds | `mdl.py` |
| **matching vocabulary** | normalizations + transforms + approximate matchers. **Retrieval only** | `matching.py` |

---

## 6. Named objects that do **not** exist yet

- **model-predicted oracle subset** — `level18/predict.py` fires predicted turns from a
  Hawkes intensity and scores them against the oracle for precision and recall. The
  correctly-predicted subset is *computable* but has never been named, extracted or
  studied. It is **not** the same as a financial pivot: a financial pivot is certified by
  a *reversal test*, this one by *a model's success*. A candidate Phase 2 channel.
- **oracle-only residual** — oracle action points that are not financial pivots. Measured:
  finds no OEIS window at all; 6 of 12 series too short to score.

---

## 7. Historical documents are **not** retro-edited

`bitacora/02` (the Phase 1 pre-registration) and `bitacora/03` (its results) use the bare
word *pivot* meaning **financial pivot**. They are **left exactly as committed**:

- A pre-registration's entire value is that it verifies unchanged after the run. Editing it
  is indistinguishable, in a diff, from moving the goalposts.
- A results bitácora records what was concluded and when. Corrections enter as **dated
  addenda**, never substitutions.

Read bare *pivot* in `bitacora/0*` as *financial pivot*, and fix nothing there. Applies to
every future pre-registration.

---

## 8. Propagation status

| repo / file | method-sense occurrences | status |
|---|---|---|
| `series-deconvolution` (this repo) | n/a | **done** — code, docs, notebook |
| `papers/method/manuscript_formal/method_paper.tex` | 9 | **all corrected**, uncommitted |
| `papers/method/manuscript_computational/comp_paper.tex` | 15 | **12 corrected**, uncommitted; 3 left — see note |
| `doc/finalpaper/together_full.tex` | 16 | **7 corrected**, uncommitted; 35 English-sense left untouched |
| `imp-pathinfo-paper/NEXT_PHASES.md` | 1 | corrected in place with a dated note, uncommitted |
| `index-deconvolution`, `imp-prices` finance code | ~~many~~ **17 method-sense in 7 files** | ~~no change needed — all finance-sense~~ **THIS ROW WAS FALSE.** Corrected 2026-09-07 — see below |

### Code identifiers — renamed together with the papers, 2026-08-21

Because *financial pivot* is now the proper name, the word must not survive as an
identifier for anything else. Paper listing and runnable source were renamed **in the same
pass**, so they cannot disagree:

| file | was | now |
|---|---|---|
| `generate_paper_outputs.wl` | `pivot5`, `(* AND pivot *)` | `decimalAnchor5`, `(* AND decimal anchor *)` |
| `corroboration_6node.wl` | local `pivot` | `decimalAnchor` (its data keys were *already* `"DecimalRepertoire"` / `"Sumandos"` — confirming the ruling) |
| `comp_paper.tex` listing | `pivot5` | `decimalAnchor5` — **0 occurrences of "pivot" remain; paper and code agree** |
| `src/causal/CausalBool.m` `findANDIndicesFormula` | local `pivot = Total[decC]`, output key `"Pivot"` | `decimalAnchor`, key `"DecimalAnchor"`. The key had no readers outside its definition site (checked), so this is safe |

### The `index-deconvolution` row above was written without scanning the tree — 2026-09-07

The 2026-08-21/22 sweep renamed every method-sense `pivot` in the **Mathematica** core and
the papers, and then cleared the whole `index-deconvolution` tree on the assumption that it
was all finance. The **Python** side of the Boolean indexing method lives in that tree. So
the sweep's conclusion — *"zero `pivot` identifiers remain in the Mathematica core"* — was
true over a denominator chosen to exclude the files that still had the defect.

Counted 2026-09-07: **178** occurrences of `pivot` repo-wide in `CausalBool`, of which
**17 in 7 files** are method-sense. Two of the seventeen are the very objects §1c names as
the source of the confusion, and which §1c diagnosed while leaving them on disk:

| file | what it was | why it is the worst kind |
|---|---|---|
| `index-deconvolution/level3/behaviour_table.py` | dict key `"pivots_essential_bits"` | a wrong **identifier** is a definition that cannot be argued with |
| `index-deconvolution/experiments/exp01_pivots_sumandos.py` | the **filename** §1c quotes verbatim | the document that explains the error shipped alongside the file that commits it |

The remaining five: `deconvolution.py` ("PIVOT COORDINATES", ×2), `causalbool.py`
("pivot-shifted cosets"), `audit_legitimacy.py` ("connected (a pivot)"),
`tests/test_deconvolution.py` ("Pivots vs sumandos"), and
`papers/method/code/worked_example_7node/worked_example_7node.py` ("one pivot and N free
weights") — the last being **paper code missed by the paper sweep**.

**Guard:** the ruling is no longer prose only. `tests/analysis/test_sumandos_definition.py`
gains a `pivot` arm scanning the method trees, with the finance levels as a declared,
reasoned exception, a control that "financial pivot" must not fire, a printed denominator
and a refusal on zero files.

### ~~`PIVOT_HYBRID` is ordinary English — verified, keep it~~ — SUPERSEDED 2026-09-07

The earlier ruling is left visible rather than deleted, because it was reasoned and
because knowing it was reversed is more useful than not knowing it existed. It read:

> Checked in context: it is a **strategic redirection**, not our object —
> *"Action Code: `PIVOT_HYBRID`; Reason: Z-Score (0.00) > −2.0 indicates failure to separate
> Biological Complexity from the Null Model"*, i.e. "Pivot to Hybrid Encoding (70% BDM + 30%
> Motifs)". All 35 such uses in `together_full.tex` stay. Adopting **financial pivot** as the
> proper name is exactly what frees them: the technical term is now two words, so bare
> English *pivot* is unambiguous by construction.

**Why it is reversed.** The argument was that a two-word technical term makes the bare
English word safe. It is sound in principle and it failed in practice: a first pass under
this very ruling blind-substituted two English-sense uses and had to be reverted, and the
method-sense defect above survived three sweeps. Every one of those costs is the cost of
**adjudicating a sense**, and that is the work §1e abolishes. `PIVOT_HYBRID` and
`PIVOT_CELL` become `SWITCH_TO_HYBRID_ENCODING` and `SWITCH_TO_CELL_LINES`, which say what
they do and need no adjudication at all.

Two limits, both deliberate. Generated artefacts (`results/bio/Contingency_Report.md`) are
**regenerated**, not edited. Archives (`doc/`) are not rewritten, per §7 — and the count
"35 such uses in `together_full.tex`" was itself wrong: measured 2026-09-07, that file
contains **zero** occurrences of `PIVOT_HYBRID` or `PIVOT_CELL`.

*(A first pass here blind-substituted two English-sense uses and was reverted; every
replacement is now anchored to method vocabulary, never the bare word.)*

### Mathematica core — renamed and verified by execution, 2026-08-22

Two further senses existed in the core library, neither a financial pivot nor a decimal
anchor. Both are now renamed. **Verified by running the suite before and after: `OK=87
FAIL=0 TOTAL=87` in both runs, identical.**

| location | sense | now |
|---|---|---|
| `CausalBool.m` ~2181–2297 — `pivots` (+ a `currentPivot` comment) | *"pivot indexes, where sequences begin"* — block start offsets. A third sense | `sequenceStarts`; the comments now say **"NOT a pivot"** and point here |
| `CausalBool.m` + `Alpha.m` — `mechaPivot` (4 uses each) | IIT: *"mechanism (pivot for computation)"*, the reference mechanism purviews are scored against. A fourth sense | `wholeSystemMechanism`; the doc comments now say *"the reference mechanism for computation"* |

`purPivot` was listed here in an earlier draft. **It does not exist** — 0 occurrences in the
repository. The inventory was wrong; corrected on inspection.

`mechanism` was rejected as the new name: 69 bare uses of that symbol exist in each file, so
the rename risked capture. `wholeSystemMechanism` is descriptive and collision-free.

**Result: zero `pivot` identifiers remain in the Mathematica core** (`src/`, `papers/`) —
the only two occurrences are the guard comments that say *NOT a pivot*.

Re-run to prove nothing broke: `tests/MUnit/run-tests.sh --all` (87/87),
`corroboration_6node.wl` (*"Exact corroboration … True"*), `generate_paper_outputs.wl`
(6-node AND `True`, 10-node per-node `True`, F1–F4 and S1–S2 all `True`).

**Unrelated pre-existing defect found while re-running, not caused by any rename:**
`generate_paper_outputs.wl` reports `6-node XOR: False`, and line 423 prints
`=== ALL VERIFICATIONS PASSED ===` **unconditionally** — it is a banner, not a gate, so the
failure is easy to miss. `verifiedXOR` (line 108) is computed independently of
`decimalAnchor5`. Left for the author: it is their untracked script and fixing the XOR
derivation is a separate piece of work.

---

## 8a. Where the rest of the handoff lives

| document | role |
|---|---|
| `TRANSFERENCE.md` **§9** | orientation map for a new agent: file layout, the original research this stands on, the fifteen errors already made, standing rules |
| `TRANSFERENCE.md` **§5.0** | the oracle/pivot relation, rewritten — its previous text *was* confusion source #3 |
| `bitacora/04_two_decompositions.md` | confusion source #5 in full, with the executed lossy-vs-lossless demonstration |
| `notebooks/01_phase1_go_no_go.ipynb` **R1** | the definition, the five confusion sources, and both decompositions run side by side |
| `notebooks/01_phase1_go_no_go.ipynb` **R3** | cost-as-primitive, and the parity assertion against the sibling's original engines |
| `CausalBool` commits `cba2eec`, `4d9a959` (branch **`clean`**) | the propagation into the sibling programme |

---

## 9. How to use this file

1. Before writing *pivot*, check **§1e**. If it is a price turning point, write **financial
   pivot**. Otherwise do not write the word at all: the method's objects are **connected
   inputs**, **essential variables**, **decimal anchor**, **decimal family**, **free
   coordinates** and **sumandos**, and one of those six is the word you want.
2. Before quoting a relation between named objects, check §3 — direction, and the two
   readings.
3. New term minted → add it here **with its source**, in the same commit.
4. Term corrected → amend **in place**, dated, and say which documents are now stale.

---

## ADDENDUM 2026-08-24 (AUDIT_FIXING_PLAN_01 / T2.7) — precision note on the b21/b22 history

Wherever this GLOSSARY or TRANSFERENCE compresses the oracle/pivot correction
into one line ("21 stated an identity; 22 retracted it"), read the **three-step**
chain instead, per the V2 verification stamp of AUDIT_FIXING_PLAN_01
(2026-08-24):

1. `bitacora/21` established **containment-with-residual** and called the θ=c
   case an "identity" (bare "identity" only for θ=c), titling it the headline.
2. `bitacora/22` re-rated the **epistemics** ("true but geometry") without
   retracting any mathematics.
3. The #3 amendment in this GLOSSARY's confusion-source table then corrected
   22's demotion: definition-level containment is constitutive; the measured
   rate is the recovery method's fidelity.

No mathematics was retracted at any step. This note exists so the compressed
one-liner cannot mislead a court-style reader into thinking a result died when
only its interpretation was re-rated.
