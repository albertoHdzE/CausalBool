# AUDIT03 — implementation pass after the R0.3 gate

## Context

**R0 is done, the gate has passed, and every open decision is now settled.**
`audit/METHOD_ACCOUNT.md` was written from the primary sources (`4cda3f2`); the
author's theory rulings are recorded (`0a2cc94`); the five outstanding
implementation decisions were taken in discussion on 2026-09-04.

### What the R0.3 gate settled (theory)

| ruling | consequence |
|---|---|
| **Holland ⊂ the method — by scope, not expressiveness.** Schemata answer a *query*; the `(L, Ω)` rule gives **total reproduction**, and that is the compression. | The comparison target for `(L, Ω)` is **BDM**, a whole-object complexity — never a per-query quantity. |
| **Schemata should be merged.** | Five published `DecimalRepertoire` tables move. |
| **`D_schema` is the measure.** No hybrid, nothing Shannon-derived. | Becomes the primary mechanism-side quantity. |
| **The manuscripts' ordering convention prevails** (LSB-first, `ORDERING.md §1`). | `02_cb_and.tex` corrected — and the correction *vindicates* the 2025 formula. |
| §6.4 coarse/fine are two levels; §8.5 BDM and Shannon are separate universes, both reported. | Confirmed as written. |

### The five decisions taken 2026-09-04

**A — `D_formula` is demoted, not deleted.** Report **both**: `D_formula`
relabelled *"length under the twelve-family catalogue"*, `D_schema` promoted to
primary as the catalogue-free measure. This is **not** the rejected hybrid — a
hybrid was one measure switching branch per node; this is two clearly-labelled
measures of two different things. `D_formula` is a valid length in a declared
language, and demoting it makes the catalogue-dependence visible rather than
deleting the evidence for it.

> **Consequence that must be written into the papers:** the ratio to the dataset
> measures moves from `1.87` to `1.63` orders of magnitude, so the phrase *"two
> orders of magnitude"* becomes **"a factor of ≈43"**. Qualitative claim survives;
> that wording does not.

**B — Shannon stays, as an explicitly-labelled dataset-side baseline.** Never as
*our* measure. Nothing is deleted from the 15 mentions; the guard `R6.1` is added
so that any *description-length* path becoming entropy-derived fails the suite.

**C — R5 stays frozen.** `Q2.1` decided: **accept on truth-table equality, report
the recovered name** (precedent: bitácora 11, 123 of 420 nodes recovered a
different *name* with an identical truth table, zero functional errors — a
relabelling is not a failure). `Q2.3` decided: **construct** an out-of-frame
refusal case rather than repurpose a real rule. `Q2.2` is a measurement conflict,
not a decision (`1.76` vs `1.17`, Stouffer `z = +3.27`), so the null under
W1.3/W1.4 stays untrustworthy and **R5 is not built on it in this pass**.

**D — commit and push the sibling glossary.** `series-deconvolution/GLOSSARY.md`
carries §1d and is uncommitted; the sync gate is green only because both copies
match on disk. **No Claude co-authorship in that commit either.**

**E — R7 is dropped.** My premise was false. Measured: `data/` is 85 MB and
`results/` 3 MB, while the 8.8 GB is **DepMap CSVs in history** — files gitignored
today but committed before (`OmicsExpressionTranscriptsTPMLogp1Profile.csv` alone
is 3,974 MB across ~15 files, ~20 GB raw). Removing them now reclaims nothing;
only a history rewrite would, and that **rewrites every commit SHA** — invalidating
every SHA cited in `METHOD_ACCOUNT.md`, `BASELINE.md`, `AUDIT03_PLAN.md` and the
commit messages. The provenance chain is worth more than the disk. Replaced by a
one-line policy note forbidding large binaries.

**Also settled, by measurement rather than by asking:** `D_schema` sums **per
node**. Overlap is a *query-level* phenomenon — `|C| = n` on the flagship (saving
exactly 0) and in 30% of the corpus; median `|C|/n = 0.942`.

### What remains genuinely blocked

- **Bio regeneration** — 3,977 of 5,204 corpus nodes (76.4%) have multi-valued
  threshold formulas, so **no Boolean truth table is derivable and no description
  length of any kind reaches them.** Blocked behind R4.
- **R4.2–R4.5** — deriving a closed form is research, not implementation. Its
  *gate* R4.1 is measurable now; the derivation follows that number.
- **R5** — per decision C.

---

## The pass, in execution order

### 1. R2a.2 — collapse the offset family *(cleared; no theory needed)*

The three `allOffsets` sites differ **textually** (`corroboration_6node.wl` lacks
the `If[Length[ws]==0, {0}, …]` guard) but are **functionally identical**:
`Dot[{},{}]` is `0`, and over `n = 1..6` with every connected subset they agree on
**126 of 126** cases (`audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl`).

One owner; the other two import it; redundant definitions to `archive/` per policy,
not deleted. Add the symbol to `tools/check_single_engine.sh` **in the same
commit**. Re-run the three consuming producers and diff elementwise.

**DONE — `651aaa7`.** `CausalBoolCore.wl` owns `weights`, `allOffsets`,
`givePlaces`; originals archived; all three producers re-ran with **zero
artefact changes**; guard verified in both directions. The guard found a third
`givePlaces` site, which was *not* collapsed and the reason recorded in-script:
`TSK-MIXED-001:28` is a **different function sharing the name**, and
`Alpha.m`'s is computationally identical but `CausalBoolCore.wl` is standalone
by design.

**Gate semantics stay blocked** until the call contract is reconciled
(`KeyError 'pair'` vs `1` for `IMPLIES` at `d=1`) **and** the AUDIT02 135/135
Wolfram claim is *re-run rather than cited*.

### 2. R3.merge — implement merging, regenerate the five tables

Reuse `minimal_dnf` in `index-deconvolution/src/deconvolution.py`; do not rewrite
Quine–McCluskey. The WL query path (`mixedQueryRepresentation` in
`generate_paper_outputs.wl`) does not merge and must.

Measured, coverage verified identical in every case: **38 published rows → 20
schemata.** F1–F3 `6 → 4`, F4 `6 → 2`, S2 `12 → 4`, S1 unchanged. Restate the
tables in `comp_paper.tex` with an explicit old-vs-new note saying plainly that
**no behaviour changes — only the description gets shorter.**

**DONE — `4f75dfa`, `962cd6e`. One line of this item was wrong and is withdrawn.**

Merging implemented in the WL path via `BooleanMinimize`, deliberately *not* by
hand-rolling Quine–McCluskey, so that the Python gate stays an **independent**
implementation. Five gates, all green: `M1` elementwise cover (symDiff 0, 6/6),
`M2` negative control (fires 6/6), `M3` cross-language parity (form for form
identical, 6/6), `M4` minimality (**exhaustive** minimum cover over the primes
equals the reported size in every case — each prime is essential, so 20 is
forced, not a greedy artefact), `M5` length.

> **WITHDRAWN: "only the description gets shorter."** That sentence was written
> from a **count**, and the claim it supports is about **length**. Priced in a
> common coordinate — same `C_q` mask, same self-delimiting count, trit payload
> at `log2 3`, which is the *cheaper* of the two obvious schema codes and so
> generous to the merge — the merged form is shorter in **2 of 6** cases:
> F1–F3 `75.0 → 78.4` bits (**longer**), S1 `27.0 → 35.2` (**longer**),
> F4 `75.0 → 44.7`, S2 `137.0 → 78.4`; aggregate `464.0 → 393.5`, `0.85×`.
> A minimum cover minimises the **number of schemata**; minimising bits is a
> different objective, and the two part company when the rows saved are few and
> the coordinates freed are fewer. The aggregate saving is real; the per-case
> claim is not, and `comp_paper.tex` §4.1b says so explicitly.

Declared delta: paper-number gate `109 → 116` entries (`BASELINE.md`). Its own
line-keyed diff reported 37 added / 30 removed for **0 changed** — the `R6.4`
defect; checked instead by value multiset: **17 gained, 0 lost, 0 altered.**

### 3. R3.a/b — `D_schema` primary, `D_formula` demoted, and the BDM comparison

Manuscript work per decision **A**: relabel `D_formula`, promote `D_schema`, and
replace *"two orders of magnitude"* with **"a factor of ≈43"** wherever it occurs.

Then the comparison the author asked for:

- `D_schema` is invariant under coordinate relabelling — 200 relabellings, **1
  distinct value** for OR/XOR/MAJORITY/KOFN — placing it in **BDM's invariance
  class**, so the two are comparable in principle.
- **Proportionality is untested.** One point (BDM `580.01` vs `D_schema` `232.72`)
  is not a proportionality. Measure across many networks, report the correlation
  **with its null in the same sentence**, quote no ratio before that.
- State the expected direction and why: for a deterministic system
  `K(output) ≤ K(mechanism) + O(1)`, so BDM exceeding `D_schema` reflects BDM's
  known block-sum overestimate, already characterised in `imp-causal-paper`.

**DONE — `f9c437e`.** Measured by `audit/AUDIT03_R3_description_length/bdm_vs_dschema.py`
at **fixed `n = 10`**, so every output object is a `1024 × 10` matrix and size is
removed by construction rather than adjusted for.

| arm | result |
|---|---|
| `A1` `D_schema` ↔ BDM | `r = +0.388`, `ρ = +0.424`; permutation null on the pairing (10⁴, both marginals held) `[-0.136, +0.144]`, `p = 1e-4` |
| `A2` control `D_formula` | `r = +0.207` |
| `A3` control `Σd` | `r = +0.245` — **the degree budget beats the catalogue measure** |
| `A4` partial, `Σd` removed | `D_schema` `+0.311` (`p = 2e-4`); **`D_formula` `+0.020`** |
| `A5` knobs (seeds × `dmax` 3/4/5) | `D_schema` `[+0.317, +0.430]`, `D_formula` `[+0.114, +0.207]` |
| `A6` ordering | BDM `>` `D_schema` in **194 of 200**; six exceptions reported |

`A4` is the decisive arm and it settles the promotion: **the whole of
`D_formula`'s association with behaviour is the wiring budget.** `D_schema`
retains signal because the catalogue charges `log2 12` for XOR and OR alike.

Association is **moderate, not proportionality** (`r² ≈ 0.15`), and the papers
say so. The flagship `BDM/D_schema = 2.49` now carries its distribution in the
same sentence: **median `2.34`, range `0.86`–`5.03`.**

> Also measured, and it constrains the claim: `D_schema` is **invariant under
> rewiring** — 200 rewirings preserving every gate and in-degree give **one**
> distinct value (`232.72`) while behaviour moves in a median of 1012/1024 rows.
> `D_schema` discriminates gate **composition**, not wiring.

**Carried to R2b:** the formal paper's `mechanism_vs_dataset_table` is
machine-checked against `complexity_analysis.py`, which does not compute
`D_schema`. Rather than place an unproduced number inside a checked block, the
formal paper states `D_schema` in prose *outside* the block; the inventory
wiring lands with the single owner in item 4.

### 4. R2b — collapse the description length onto one owner

Unblocked now the measure is decided. Eight sites, split 4 with the in-degree
field and 4 without (`audit/AUDIT03_R2_collapse/census.py`). Elementwise parity per
merge, guard in the same commit. `GOVERNANCE/DESCRIPTION_LENGTHS.md` §1–§2 and the
T4.5 fixture move with it.

Carried, still unfixed and recorded: `D_v2` has no decodability proof at all;
input nodes are priced `0` in Wolfram and full cost in Python (729 nodes); the
T4.5 parity gate cannot see Wolfram drift.

**DONE — `7675b3d`.** Owners: `Integration`BioMetrics`` (Wolfram),
`src/description_lengths.py` (Python). Three MUnit files stopped redefining the
formula and now delegate.

| site | before | after |
|---|---|---|
| `TSK-THEORY-002` | 42.4413 | **55.3662** (`5·log2 6`) |
| `TSK-THEORY-004` | 28.509775 | **37.797487** (`4·log2 5`) |
| `TSK-MIXED-001` | 135.66005207461194 | **unchanged** — the control |

`TSK-THEORY-004` now equals the value `BASELINE.md` pins for
`TSK-BIO-METRICS-001`: the cross-check that the collapse landed. Both Theory
tests assert **inequalities**, so no verdict moved. `TSK-MIXED-001`'s copy — the
one that superseded `101.07` by `135.66` — turned out to be **dead code, never
called**.

`D_schema` now has a producer (`schema_normal_form_length`, reusing
`minimal_dnf`), so the **R3.a-b deferral is closed**: the formal paper's
machine-checked artefact block carries `232.72`.

> **Two gates were not watching, and neither said so.**
> 1. The T4.5 parity gate compared two *stored* numbers, so when R3.1 changed
>    `BioMetrics.m` the producer moved `25.9248 → 35.2125` **while the gate
>    reported OK**. It now executes the WL producer; planting the stale value
>    yields `WOLFRAM DRIFT`.
> 2. `verify_paper_artefacts.py` read `checks["json_expect"]`, but every entry
>    carries `json_expect` as a **sibling** of `checks` — so no produced JSON
>    value had ever been compared. Had it run it would have raised anyway
>    (`produced["D"]`). Three expectations are live for the first time.

`imp-pathinfo` is a **pinned exception**: its mirror omits the field, its
published tables depend on that, and the gate now asserts the gap is exactly
`n·log2(n+1)`. Its 41 tests pass unchanged.

**Paper impact: none to the arguments.** Every flagship anchor identical
(`C_formula` 23, `D_formula` 135.66005, `D_schema` 232.71501, ZIP 10016,
`H_total` 10229.61016); no manuscript quotes any value that moved. The only edit
was a **synchronisation between the two papers** — comp's `43.0`/`44.0` →
`43.04`/`43.96`, matching the producer and the formal table.

### 5. R1 — correct the record

Falsify the MECHANICAL triage as a bounded exercise — given the claim and the
evidence, asked to **break** it. Reword the P9 census framing. **Supersede the
18.36 bits/node figure** in `CATALOGUE_EXPANSION.md`, which is a Shannon quantity.
Re-verify the W1.1 codec, on which I have been wrong in both directions.

**DONE — `c53379b`.**

- **R1.1 — the claim SURVIVES; nothing reclassified.** `5646fbd` looked
  decisive, but its bit-anchors are in the *plan file* committed alongside; its
  own report is counts and elementwise set comparisons. Three qualifications
  recorded, and three classes of spurious marker named (version strings,
  `bits[[ci]]` as a variable name, "free bits" = free *coordinates*) — an
  unadjudicated keyword count would have "found" seven falsifications that do
  not exist. `FALSIFICATION.md`.
- **R1.2 — I nearly reported a false finding.** `40/216` vs `34/222` is not an
  error: `canonical_expressible` means a canonical option *existed*, the per-row
  `extension_required` means one was *chosen*. Two exact partitions of two
  questions. **No number changes**, as predicted. The real defect was one key
  name meaning two things; keys renamed, all four counts published, framing
  reworded — the catalogue is fixed **by convention, not by the formalism**.
- **R1.3 — `18.36 bits/node` withdrawn.** Redone in pure program length: cost
  exact at `0.1155` bits/node (`600.9` over the corpus); saving reported as a
  per-in-degree **threshold** `s_max`, not invented. **On `d ≤ 2` expansion can
  never pay — 1,846 of 2,992 reachable nodes, 61.7%**, and the old figure
  charged a saving on every one. My own first calculation was wrong too
  (compared `2^d` against the schema form's *full* cost) and is corrected in
  place: 82.5% → 61.7%.
- **R1.4 — re-verification found a real defect.** The `ceil(log2 220)`
  accusation **stays withdrawn**. But `decode()` read the transmitted catalogue
  size and *threw it away*, deriving the width from its own catalogue — charged
  in every message, honoured in none, so a mismatched decoder would mis-read
  silently. Fixed. Single-bit-flip control: **177/200 → 200/200**; all 23
  survivors had been in the header, which is how the unused fields were found.

### 6. R4.1 — the thirteenth family's gate only

Measure what fraction of the 2,079 AND/OR/NOT `CUSTOM` formulas a
`REGULATORY_DNF` closed form reproduces **elementwise**. The 58,217-bit saving is
an upper bound and **may not be quoted until that fraction is known.**

**DONE — `688cba4`.** The question as posed **could not fail**: `REGULATORY_DNF`
is *unrestricted* DNF, hence functionally complete, so the answer is 100% by
construction — the defect `P9` found in `256/256`. Measured anyway rather than
argued: **2,273 of 2,273** exact cell by cell, negative control firing
**2,273 of 2,273**.

The two questions that *can* fail: **parse coverage 2,273 of 3,977 (57.2%)** —
714 level-indexed identifiers, 578 no formula, 407 threshold (exactly `R1.3`'s
count, by an independent route); and **compactness**, where family 13 beats a raw
table on only **387 of 2,273 nodes (17.0%)**. Net **`+48,517` bits**, superseding
`58,217`. Also found: **369 nodes whose formula variables disagree with `cm`**.

### 7. R6 — the remaining guards

`R6.1` a suite test that fails on any entropy-derived *description length*
(decision B). `R6.2` `verify-paper` to name each quoted bit-count's declared
language and decodability proof. `R6.4` **key the paper-number gate by content,
not line number** — it reported 91 moved entries for zero value changes, which
trains the reader to regenerate blindly.

**DONE — `98ea629`.** `R6.3` was already closed at `cbfe02a`.
`R6.1`: 9 tests, both arms verified by planting the defect; recorded that at the
node level the behavioural arm is **near-vacuous**, since the signature cannot
admit an ensemble. `R6.2`: all four bit-counts declared, including the two that
are **not** description lengths. It passed **vacuously** when first written —
the regex missed numbers inside LaTeX math — caught by unit-testing the pattern.
`R6.4`: 120 number-free lines inserted now gives *"64 moved, NO value changed"*
**PASS** (128 findings under the old keying); an altered value **FAILs** with its
multiset delta.

### 8. Housekeeping

Commit and push `series-deconvolution/GLOSSARY.md` (decision D). Add the
large-binary policy note (decision E). Update `audit/AUDIT03_PLAN.md` to match
this file.

**DONE — `3666ed5`** (sibling glossary was `677af59`). `GOVERNANCE/LARGE_BINARIES.md`
records the measurement — working tree **88 MB**, `.git` **11 GB**, top eight
historical blobs ~15.6 GB — and why a rewrite is refused: it invalidates every
cited SHA. `AUDIT03_PLAN.md` reconciled with a status section.

> **A new red appeared and was not one.** `OK=53 FAIL=2` with
> `NOTNetworkTests.m -> PASS (kernel exit=139)` — the test passed, the *kernel*
> segfaulted under contention. Verified rather than assumed: gate alone
> `OK=3 FAIL=0`, full suite run serially `OK=54 FAIL=1`. Recorded in
> `BASELINE.md` as a flake mode.

---

## Critical files

- `papers/method/manuscript_computational/generate_paper_outputs.wl` — query
  representation to make merging; owner of `allOffsets`.
- `index-deconvolution/src/deconvolution.py` — reuse `minimal_dnf`.
- `papers/method/manuscript_computational/comp_paper.tex` (17 `D_formula` sites),
  `papers/method/manuscript_formal/method_paper.tex` (5).
- `tools/check_single_engine.sh` — one added symbol per collapse.
- `src/description_lengths.py`, `src/integration/bio_D_experiment.py`,
  `src/Packages/Integration/BioMetrics.m` — the description-length collapse.
- `GOVERNANCE/DESCRIPTION_LENGTHS.md`, `tools/snapshot_paper_numbers.py`.

---

## Verification

```bash
# R2a.2 — parity BEFORE deletion, guard AFTER
HOME=$HOME /Applications/Wolfram.app/Contents/MacOS/WolframKernel -script \
  audit/AUDIT03_R2_collapse/probe_alloffsets_parity.wl          # 126/126, 0 differ
zsh tools/check_single_engine.sh                                 # new symbol listed

# R3.merge — merged tables must cover the identical index sets
venv/bin/python audit/AUDIT03_R3_description_length/verify_merge.py   # symDiff empty, all 6

# producers re-run and diffed elementwise after every collapse
HOME=$HOME .../WolframKernel -script papers/method/manuscript_computational/generate_paper_outputs.wl
HOME=$HOME .../WolframKernel -script papers/method/code/corroboration_6node/corroboration_6node.wl
HOME=$HOME .../WolframKernel -script papers/method/code/mixed_interaction_10node/mixed_interaction_10node.wl

# both manuscripts must still compile after the D_formula/D_schema surgery
(cd papers/method/manuscript_computational && pdflatex -halt-on-error comp_paper.tex)
(cd papers/method/manuscript_formal        && pdflatex -halt-on-error method_paper.tex)

# standing bar — must not move except where an intended delta is declared
zsh tests/MUnit/run-tests.sh --all     # OK=54 FAIL=1 TOTAL=55, sole red TopologiesTests
make closure                           # sync, conformance, single-engine clean;
                                       # verify-paper 7/1; paper-number gate will
                                       # move for D_schema — declare the delta
(cd index-deconvolution && ../venv/bin/python -m pytest -q)      # 146
(cd imp-prices && .venv/bin/python -m pytest -q -p no:warnings)  # 97
venv/bin/python -m pytest -q tests/analysis                      # 23
```

**Rules that hold throughout.**

- **No copy is deleted** until an elementwise parity run against the survivor is
  committed as evidence, and every collapse adds its guard in the same commit.
- **Every intended delta is declared** in `tests/MUnit/BASELINE.md` with its cause,
  as the `4·log2 5` move was.
- **No number enters a document without its reference distribution in the same
  sentence** — the BDM comparison lives or dies by this.
- `make closure` regenerates timing artefacts; verify only wall-time and memory
  moved and every structural anchor held, then **revert rather than commit noise**.
- **No Claude co-authorship in any commit**, in this repository or the sibling.

**Acceptance.** Items 1–8 delivered with their evidence; the five tables restated
with an old-vs-new note; `D_formula` demoted and `D_schema` primary in both
manuscripts, both compiling; the BDM comparison reported with its null; every bar
unmoved or its delta declared.

**Stop conditions.** Bio regeneration does not start (blocked behind R4).
R4.2–R4.5 do not start (they follow R4.1's measurement). R5 does not start
(`Q2.2` unresolved).
