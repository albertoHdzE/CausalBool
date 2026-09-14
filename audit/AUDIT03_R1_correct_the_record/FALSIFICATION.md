# AUDIT03/R1.1 — falsifying my own MECHANICAL triage

**Date:** 2026-09-04 · **Evidence:** `falsification_evidence.json`, produced by
`falsify_mechanical_triage.py`

## The claim under test

> These 13 commits were settled solely by elementwise comparison against an
> exhaustive truth table, an independent implementation, or a byte-level diff,
> and none quotes a codelength or judges expressibility.

Two triggers move a commit MECHANICAL → ECONOMIC:

- **T1** — its **verdict** depends on a quantity measured in bits;
- **T2** — its **verdict** depends on a judgement about what the method *should*
  express.

The search was deliberately over-inclusive — every candidate marker in the
message *and* the full diff, 10 of 13 commits flagged — because the failure
mode being guarded against is my own blindness, and a narrow search would
reproduce it. Markers were then adjudicated one at a time, because **mentioning
bits is not the same as deciding by bits**.

## Outcome

**The claim survives. No commit is reclassified.** I did not break it, and I am
recording that rather than manufacturing a falsification to look thorough.

But it survives with **three qualifications**, and one of them I initially
scored as a hit.

### The near-miss, and why it is not a hit

`5646fbd` looked decisive. Its diff contains

> `D_formula=135.66`, `C_formula=23`, `ZIP=10016`, `H_total=10229.61`,
> `BDM=580.01`. Report each as observed-vs-expected

which is a list of **bit-valued acceptance criteria**. On inspection that text
is in `plans/now-in-mode-plan-idempotent-moon.md`, included in the same commit
— it is the *plan* for A1, not A1's verdict. The commit's actual report is
entirely counts and elementwise set comparisons: `d_q=21, c_q=10, μ_q=11,
R_q=2048`, `|Im(F)|=206`, basins `488/320/204/12` compared as state vectors,
`median |C_q|=10`. No codelength appears in the verdict.

**Qualification 1.** The commit therefore set itself five bit-valued acceptance
criteria and its report mentions none of them. They were either checked and not
reported, or not checked. That is a reporting gap in `5646fbd`, not a
reclassification, and it is recorded here rather than left for someone to
notice.

### Qualification 2 — `aca0842` draws a scope boundary

Its census records `512` multi-valued and `407` threshold formulas as
**REFUSED — needs >1 bit per node**. The verdict of the commit (INPUT sentinel
fixed, fixed points recovered) is mechanical, and "a multi-valued formula is not
a Boolean function" is a fact about the *data*, not a preference about the
method. T2 does not fire.

It is still load-bearing: those refusals are the ancestor of the **3,977 of
5,204 corpus nodes** that AUDIT03 now carries as its main open coverage item.
The boundary is contingent on the catalogue, which is precisely the presumption
`R1.2` corrects in the P9 framing.

### Qualification 3 — `d420b3b` published values on an execution-only verdict

The defect it fixed is real and mechanical: the BDM batch resolved `python3` to
the system interpreter, which has no `pybdm`, so every batch failed with
`ModuleNotFoundError` **while the script printed "Failed to parse BDM results"
and still exited 0**. The verdict — "the producer was broken and now runs" — is
an execution fact.

But the commit regenerates `bdm_knockouts`, so a set of **BDM values entered the
record on the strength of the script running**, not of the values being checked
against anything. T1 does not fire on the verdict; it does describe what the
commit published.

## Three classes of spurious marker

Worth naming, because they are why an unadjudicated keyword count would have
"found" seven falsifications that do not exist:

| class | example | commit |
|---|---|---|
| version strings | `14.2.0 for Mac OS X ARM (64-bit)` | `8463895` |
| variable names | `bits[[ci]]` — the input vector restricted to `Ic` | `8ebf794` (10 hits, all lexical) |
| ordering vocabulary | "bit-reversal transport", "MSB-convention row indices", "free bits `(v1,v3,v5,v6)`" | `2072d7c`, `5567064`, `85717ab` |

"Free bits" in `85717ab` means free *coordinates*, not a codelength. None of
these is a bit-quantity in the sense T1 means.

## Clean

`2ee4d59`, `b166b36`, `f245195` carry no marker of either kind in message or
diff.

## What this exercise is worth

It is a **negative result reported as a negative result**. The triage was
correct as far as T1 and T2 reach. What it does not certify is that the
*catalogue itself* was ever in question in these commits — several of them
(`0603eb4`, `2072d7c`, `5567064`) take "the twelve families" as the boundary of
what needs checking. That is not an error under the claim tested here, but it is
the same fixed-catalogue presumption that `R1.2` removes from the P9 framing,
and it is worth seeing that it runs through more of the record than P9 alone.
