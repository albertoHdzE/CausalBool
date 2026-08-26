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

- **Claim under test:** pivot-decoder scores on integer sequences reflect
  discovered structure.
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
