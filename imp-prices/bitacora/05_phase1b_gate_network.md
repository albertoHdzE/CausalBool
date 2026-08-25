# Bitácora 05 — Phase 1b: the method as it actually is, and the same verdict

**Date:** 2026-08-18
**Status:** complete. 72 tests passing; `results/phase1b_gate_network.json`
(content sha256 `290893e291e79cc3`).
**Ledger entries produced:** C19–C22.
**Supersedes:** C15's *label* (not its numbers). Phase 1b is the version of B4
that is defensible in a paper.

---

## 1. Why Phase 1 had to be redone

The assessor raised two objections and both were correct.

**The instrument was wrong for this programme.** Phase 1 used a Shannon counting
code. Its model term is blind to structure by construction — a constant map, XOR
and a random map over the same inputs all cost *m*·log₂3 — which is exactly the
blindness BDM removes, and all three sibling packages use BDM. Using a counting
instrument here was a methodological discontinuity as well as a weakness.

**More seriously, the method was not being applied.** What Phase 1 built was a
parent set plus an *arbitrary lookup table*. That is the thing the index-set
method was invented to replace. Left out: the seventeen named gates, the
pivot/sumando factorisation, the network (one node was modelled), and the
validated deconvolution machinery. The arbitrary map costs *m*·log₂3 = 42.8 bits
at in-degree 3 where a named gate costs about 4.8 — roughly ten times more, and
that gap is most of the 15.56 bits Phase 1 reported as a defeat.

I had recorded this in bitácora 04 §7, but as a residual rather than as the
design. Burying a known weakness in a footnote is the actual failure here.

## 2. What Phase 1b does differently

| | Phase 1 | Phase 1b |
| --- | --- | --- |
| model class | arbitrary lookup table | 17 named gates from the validated forward model, LUT only as fallback |
| object | one conditional | a 14-node network: connectivity matrix + a gate per node |
| instrument | counting | BDM(model) + L(data \| model), counting retained alongside |
| binarisation | none (ternary) | three encodings, **all reported** |

The gate catalogue is *generated* by calling `apply_gate` from the vendored
`causalbool.py` over all 2^k inputs, so it cannot drift from the semantics it
represents, and nothing is reimplemented. REGULATORY and REGULATORY\_DNF were
pre-declared and are included; the DNF form is generated from the target function
rather than enumerated, and admitted only when it uses fewer clauses than the
function has minterms.

The primary binarisation is **thermometer**, because the three regimes are
ordered — they are labelled by mean monthly log return, so bear < stagnant < bull
is a fact about the fit, not a convention. Plain binary and one-hot are reported
too, whatever they show; reporting the best of three would be selection over
encodings, the error Level 4 records.

## 3. The controls, which decide whether any of this counts

**BDM resolution, checked rather than assumed.** imp-pathinfo established that
BDM can track object size rather than structure, so separation between structured
and random arrays was measured at each shape used:

| shape | separation | usable |
| --- | --- | --- |
| 14 × 14 (the network) | **32.6σ** | yes |
| 14 × 8 (the table array) | 25.1σ | yes |
| 4 × 4 | 3.2σ | **no** |

This is why the object scored is the whole network and not a single node's table,
and the 4 × 4 row is asserted as *unusable* in the test suite so that the limit
cannot be quietly forgotten.

**Positive control.** Rule 110 as a 14-node network: the gate network fits it
with **zero errors** and costs 258.94 bits against the CPT network's 714.98 — a
win of **456 bits**. The representation expresses what it was designed for.

**Negative control.** On independent binary noise the gate network *loses*
(+131.63 bits) and sits at a 46.3 per cent error rate, which is chance. The
accounting is not biased in our favour.

**Falsifiability of the gate class.** The family covers 17 of the 256 Boolean
functions of arity 3 — 6.6 per cent — and random draws matched a named gate 6.5
per cent of the time. The class tracks its own coverage exactly; it does not fit
anything.

## 4. The result: B4 refuted again, and more firmly

| binarisation | algorithmic (BDM) gate − CPT | counting gate − CPT | gate wins? |
| --- | --- | --- | --- |
| **thermometer** | 933.0 − 904.5 = **+28.5** | 781.8 − 730.7 = +51.1 | no, both |
| binary | 977.9 − 959.2 = +18.7 | 808.3 − 766.5 = +41.8 | no, both |
| one-hot | 1485.2 − 1471.9 = +13.3 | 1174.1 − 1118.6 = +55.5 | no, both |

**The conditional probability table wins under both instruments, on all three
binarisations.** The instruments agree everywhere, so the verdict is not an
artefact of either.

Two details worth keeping. First, BDM *narrows* the gap relative to counting
(+28.5 against +51.1 on the primary encoding), so the algorithmic instrument does
credit the gate network's structure — it simply does not credit it enough to
reverse the outcome. The assessor's objection was right about the instrument and
right that it would change the number; it did not change the sign. Second, on the
structure axis, where both matrices are 14 × 14 and size cannot confound, the
gate network's connectivity is *more* complex (BDM 156.45 against 123.37) and
denser (23 edges against 17). It selects a richer structure and still loses,
which is the C18 over-selection finding surviving into the corrected design.

## 5. The deepest finding: nothing here is gate-like

| binarisation | named gates | LUT fallbacks |
| --- | --- | --- |
| thermometer | **0** | 14 of 14 |
| binary | 1 (REGULATORY) | 13 of 14 |
| one-hot | 2 (CANALISING) | 19 of 21 |

Essentially **no node of this panel is describable by a named gate**. Every one
falls back to a general lookup table. This is a much stronger statement than
Phase 1 could make, and it is the honest answer to "is the index-set method
applicable to this problem": the family that names AND, XOR, MAJORITY,
CANALISING and REGULATORY names almost nothing here, because the conditionals are
not gate-shaped. They are noisy, near-random maps.

It is also self-consistent with everything measured before it. Gate 1.0 (C9, C10)
found no deterministic structure beyond persistence. A gate is a deterministic
object. If there is nothing deterministic, there is nothing for a gate to be.

## 6. What is now established, and what is not

**Established.** B4 is refuted with the method properly applied, the right
instrument, three binarisations, and controls that pass decisively in both
directions. This is the version that can go in a paper. The Phase 1 numbers
stand as measurements of a degenerate encoding; only their *label* was wrong, and
that is corrected in the ledger rather than deleted.

**Not established, and I will not claim it.** That the index-set method is
unsuitable for financial time series in general. What is shown is narrower: at
monthly frequency, on seven macro series binarised three ways, over 137
observations, at in-degree ≤ 3, the panel's conditionals are not gate-like and a
probabilistic encoding describes them more compactly. The rule-110 control in the
same run shows the representation working perfectly on a system that *is*
deterministic, which localises the failure to the data rather than the method.

**A residual I am not going to paper over.** Selection is by counting length per
node, with BDM applied to the assembled network, because a single node's 1 × 8
table is far below BDM's resolution. A design in which selection itself were
algorithmic would need a coarser node granularity or a CTM for small strings, and
is not attempted here.

## 7. Consequence

Phase 1 is closed for the second time, with the same verdict reached by a better
route. Every remaining hope in this project rests on Phase 2, and it now rests
there for a stated reason rather than by default: the monthly regime target has
no deterministic structure, so no representation built on exact functional
dependence can win on it. The clock target is where the deconvolution programme
found structure that survived nulls twelve times out of twelve, and where the base
rate does not defeat measurement.

## 8. Next

Phase 2, as pre-registered. First build: the confirmed-only pivot rule (R1),
which is the principal false-positive risk in the whole design.
