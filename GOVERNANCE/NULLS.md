# NULLS — Nuisance-dimension declaration rule for null models

**Status:** ACTIVE · Established by **AUDIT_FIXING_PLAN_01 / T4.4** (2026-08-25).
**Authority:** procedural rule binding every future pre-registration in this
programme (CausalBool and sibling series-deconvolution); on *definitions*,
`GOVERNANCE/GLOSSARY.md` still outranks everything.

---

## §1 The rule

> **Before running any null model, declare three things in the pre-registration:**
>
> 1. **Response profile:** every dimension the statistic is known or suspected to
>    respond to (e.g. shape, density/marginals, alphabet size, sequence length,
>    codeword syntax, connectivity class).
> 2. **Held-fixed set:** all dimensions from (1) except the single one the
>    hypothesis claims to matter — these must be matched between data and null.
> 3. **Destroyed dimension:** exactly which dimension the randomization destroys.
>    If it destroys anything in the held-fixed set, the null is invalid as stated.

A null that fails any clause does not get run "to see what happens"; it gets
redesigned first. Two independent reversals in this programme share this single
mechanism (§2–§3): the randomization destroyed structure imposed by the
code/pipeline rather than by the data, because the nuisance dimensions were never
enumerated before the draw.

## §2 Case study 1 — imp-prices C22→C29: density confound in a BDM comparison

- **Claim under test (C22):** the gate-family network scores higher BDM than the
  CPT network on the structure axis ("the gate network is more complex"), both
  matrices matched at 14 × 14 (`imp-prices/FINDINGS.md:210`).
- **Reversal (C29):** shape was matched but *edge density was not* (17 vs 23
  edges) — and BDM responds to density. Density-matched random matrices at each
  edge count absorb ≈ +21.82 of the reported +33.08-bit gap: **66 % of the
  "structure" difference was a density artefact**, and the sentence was withdrawn
  (`FINDINGS.md:220`; audit trail `imp-prices/bitacora/07_datasaurus_audit.md`
  §1; machinery committed under AUDIT01/T2.2).
- **Rule failure:** the response profile omitted *density/marginal counts*; the
  held-fixed set declared only *shape*; the randomization silently destroyed
  edge count along with structure.
- **Correct form (now standard here):** hold shape AND edge count fixed,
  destroy structure alone, and compare each real network against its own-density
  null (z-scores), which is what C29 concluded with.

## §3 Case study 2 — series-deconvolution B1: codeword-syntax null

- **Claim under test:** decoder scores on integer sequences reflect
  discovered structure. *(GLOSSARY §1e — this line read "pivot-decoder" until 2026-09-07; the word is retired, and the decoder here is the sibling's codeword decoder.)*
- **Reversal:** the surrogate draw destroyed **codeword syntax** — the code-side
  framing bits added by the encoder/pipeline — rather than data structure. Scores
  of −22 to −34 against syntax-destroying surrogates measure the pipeline's own
  scaffolding, not the sequence ("density was matched; codeword syntax — the
  dominant nuisance — was not": sibling `bitacora/03_phase1_results.md:316`,
  `bitacora/05_adversarial_review.md:62`; corrected null construction in
  `bitacora/06_pivot_fidelity_and_g1b.md:77`).
- **Rule failure:** codeword syntax was a nuisance dimension of the *statistic*
  (it responds to pipeline-imposed structure) but appeared in no response
  profile, so the null destroyed it while the hypothesis only concerned data
  structure.
- **Correct form:** surrogates must preserve codeword framing (or the score must
  be conditioned on it); the destroyed dimension must be the claimed one.

## §4 Checklist template (append verbatim to future pre-registrations)

```
## Null-model declaration (NULLS.md §4)

- Statistic: <name, version, implementation path>
- Claimed dimension (the ONLY one the hypothesis concerns): <dimension>
- Response profile (everything the statistic may respond to):
    [ ] shape / length          … specified: ______
    [ ] density / marginals     … specified: ______
    [ ] alphabet / value range  … specified: ______
    [ ] code/pipeline syntax    … specified: ______   (framing bits, headers,
                                                     padding, ordering imposed
                                                     by the encoder)
    [ ] other: ______
- Held fixed between data and null (all of the above except claimed): ______
- Dimension destroyed by the randomization: ______
- Check: destroyed ∈ {claimed}?            yes / no  (must be yes)
- Check: nothing in held-fixed set varies? verified how: ______
- Seeds / determinism: ______
```

## §5 Adoption status

- Binding for new pre-registrations from 2026-08-25 (this plan's Wave-3+ tasks;
  successor plans inherit it).
- Pointer to be added to the series-deconvolution Phase-2 pre-registration TODO
  (**pointer only** — the sibling edit itself remains gated behind its own U6
  approval and is logged in AUDIT_FIXING_PLAN_01 Appendix D).
  **DONE 2026-08-25 (U6 granted):** pointer landed as a dated TRANSFERENCE.md
  addendum in series-deconvolution (commit `db6343d`, pushed) — that sibling has
  no standalone Phase-2 TODO file, so the living transfer document received it
  per T2.6 precedent. Binding for all sibling pre-registrations from this date.

---

## §6 The fourth law — response of headline statistics to parameters they are not about

> **A headline statistic is published together with its response to the run
> parameters it is not about** (null count, seed, node labelling, subsample
> rule), **and a statistic that moves monotonically in one of them may not
> be the headline.**

This is the symmetric counterpart of §1, which governs statistics **inside**
a null test. §1 catches the case where the null destroyed a dimension the
statistic was responding to; §6 catches the case where the statistic itself
moves under a run parameter that the headline does not name. The pattern is
the same: declare the response, then check it, then publish the response
beside the headline. Two reversals in this repository, both measured, share
this single mechanism (§6.1, §6.2).

### §6.1 Case study 1 — `gap_bits` against the null count (AUDIT04-H1.1)

- **Headline under test:** `gap_bits = D(best null) − D_bio`, the comparator
  reported in `Null_Generator_HPC.py` lines 363–411 and quoted in
  `GOVERNANCE/VERIFICATION.md` §5b. A negative value means the bio network
  is the *longer* one, the algorithmic-complexity reading.
- **Response profile measured:** the median gap to the best null moves
  monotonically with the null count across all three null kinds over 30
  networks, seed 42 (`audit/AUDIT04_H_comparator/FINDING.md` §5):
    - er: +21.05 → −7.62 → −25.81 (null counts 10, 100, 1000)
    - deg: −4.91 → −17.65 → −22.07
    - gate: −14.30 → −26.25 → −37.30
  The median gap to the **median** null (er: 50.28 → 44.61 → 41.73) and
  the median permutation tail `exceed` (er: 0.000 → 0.015 → 0.012) do not
  move under the same sweep.
- **Why the headline is the wrong one.** The null count is a run
  parameter the comparator is not about — a 10-null run and a 1000-null
  run use the *same* network; only the ensemble size varies. A comparator
  whose value depends on the ensemble size is reading the ensemble, not
  the network. The best-null gap can only become more negative as the
  null count grows (an order-statistic floor), and that is exactly the
  direction the measurement reports. The H1.5 verdict-change count
  (231 networks, 10 vs 1000 nulls) makes the same point at the
  decision-rule level: 16 of 231 cells change verdict, 4 from
  `separating(best)` to `separating(median)` and 12 the other way.
- **What the fourth law would have caught.** A pre-registration of the
  headline that did not include a sweep over the null count would have
  produced a +21.05 figure at 10 nulls and a −25.81 figure at 1000 nulls
  with no way to tell which was the network. The §6 rule requires both
  figures, with the run parameter named, in the same sentence as the
  headline. The §6.1 case study is the evidence: the best-null gap at
  any single null count is a reading of the ensemble size, not of the
  network.

### §6.2 Case study 2 — the two reported measures against node labelling (AUDIT04-H2.1)

- **Headline under test:** the two description-length measures reported
  side by side — Variant A (`row_run_index_set_length`) and BDM. Both
  are quoted in `GOVERNANCE/VERIFICATION.md` §5b and in the comp-paper
  Table 2 as the two algorithmic complexity readings for each network.
- **Response profile measured:** the spread of each measure under 200
  random node relabellings, at n = 16, seed 20260908
  (`audit/AUDIT04_H_measures/FINDING.md` §2):
    - chain: Variant A 61.31 bits, BDM 170.72 bits
    - hub: Variant A 28.61 bits, BDM 100.12 bits
    - checkerboard: Variant A **784.79 bits**, BDM 437.34 bits
    - random p=0.2: Variant A 89.92 bits, BDM 127.61 bits
  The node labelling is a parameter the headline is not about — a
  relabelling of the adjacency matrix is a graph isomorphism and changes
  no information. A measure that moves under a relabelling is reading
  the labelling, not the graph.
- **The headline that the response profile overturns.** The two
  `DECLARED_INVERSIONS` in
  `tests/analysis/test_complexity_measures_are_algorithmic.py:284-299`
  read the canonical Variant A cost on the checkerboard
  (1050.5 bits) as a property of the family. The 784.79-bit Variant A
  spread on the same family — min 134.89, max 919.68 — shows that
  1050.5 is the *worst-case* cost over labellings, not a graph
  property. A run-parameter-symmetric reading (§6) of the canonical
  1050.5 figure would have caught this: the same graph, in a different
  labelling, can cost an order of magnitude less.
- **What the fourth law would have caught.** A pre-registration of
  `DECLARED_INVERSIONS` that did not include a sweep over node
  labelling would have read 1050.5 bits as the family's complexity.
  The §6 rule requires the response profile beside the headline, in
  the same declaration. The §6.2 case study is the evidence: the
  declared inversion is the labelling response in disguise, and the
  declaration in `tests/analysis/test_complexity_measures_are_algorithmic.py`
  now carries the response profile beside the cause.

### §6.3 The combined rule

§1 (inside a null) and §6 (outside it) together:

1. **Inside a null:** declare the response profile, the held-fixed set,
   and the destroyed dimension. The destroyed dimension must be the
   claimed one; nothing in the held-fixed set may vary.
2. **Outside a null:** publish the response to the run parameters the
   headline is not about. A statistic that moves monotonically in one
   of them may not be the headline; if a sweep is not run, the
   response is *unknown* and the statistic is reported as such.

Both rules rest on the same root: a number whose value depends on
something the question does not name cannot answer the question. §1
names it for the null; §6 names it for the headline. The four laws of
the programme — measure; report the reference distribution; locate the
owner; report the response of the headline to the parameters it is not
about — are the four facets of the same diagnostic.

## §7 Adoption status

- The fourth law (§6) is binding for new headline statistics published
  in this programme from the date its first case study is committed
  (2026-09-08, AUDIT04-H2.4). It applies to all current and future
  pre-registrations, the same scope as §1.
- The case studies in §6.1 and §6.2 are evidence of the law, not its
  source. Two distinct defects in this repository — a comparator that
  read the null count instead of the network, and an inversion
  declaration that read the labelling instead of the family — share
  the same root cause and the same fix.
