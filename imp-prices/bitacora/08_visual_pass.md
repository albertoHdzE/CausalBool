# 08 — The visual pass

**Date:** 2026-08-21
**Notebook:** `notebooks/04_the_visual_pass.ipynb` — 23 cells, 0 errors, 7 figures
**Ledger:** C37–C41
**Generated from the executed notebook**, which is the analysis itself. Nothing
in this entry was computed outside it.

## Why this exists

The assessor's instruction was to restore the method's own discovery order. The
index-set calculus was not found by writing formulae. It was found by looking at
the distribution of ones and zeros, seeing a pattern, asking what table headers
would express it, and only then deriving the behaviour formulae, the formal
equations and — last — the statistics that justified what had already been seen.
Exactness and speed followed from that order.

Phases 1 and 2 ran it backwards. We binarised the regimes and went straight to
scoring gates against nulls. The binary matrix the whole method eats had never
been drawn. One figure existed in `figures/` for the entire project, and it
belonged to the Phase 3 opening.

## What the objects showed

The regime band answers the question before any statistic does. CPI is a single
unbroken bar across all 198 months. USD_Idx switches once, in 2012, and then does
nothing for six years. Ind_Prod is solid but for one interruption in 2020. Only
WTI_CL, Brent_BZ and WTI_Spot have texture — and the binary render makes plain
that these are three views of one asset.

Run counts over 198 months, which need no null because they are a property of the
object rather than a comparison:

| node | runs | node | runs |
| --- | --- | --- | --- |
| CPI.not_bear | 1 | Fed_Funds.bull | 22 |
| CPI.bull | 1 | Brent_BZ.not_bear | 23 |
| Fed_Funds.not_bear | 3 | Brent_BZ.bull | 27 |
| USD_Idx.not_bear | 4 | WTI_CL.bull | 30 |
| USD_Idx.bull | 4 | WTI_Spot.bull | 31 |
| Ind_Prod.not_bear | 5 | WTI_CL.not_bear | 33 |
| Ind_Prod.bull | 5 | WTI_Spot.not_bear | 39 |

CPI's two nodes are constant. Not nearly constant — constant, one run each.

The cause is separable from the symptom. CPI's log returns have sd = 0.00264
against WTI's 0.11726, a factor of about forty-four, and the three-state Gaussian
fit collapses: the middle state is empty for USD_Idx (175/0/23), CPI (198/0/0)
and Ind_Prod (6/0/192), with 29 non-convergence warnings. For three of seven
series the three-state model is a two-state model wearing a third label, and this
holds inside the 139 training rows on their own.

## The number that was stopped at the gate

Counting nodes that never change across the test window gives 8 of 14, which
reads as damning. Under a circular-shift reference that preserves each column's
run structure and randomises only where the test window falls, the null median is
6, the 5–95 percentile band is [4, 8], and the rank-based p is 0.1100.

So it is withdrawn: a restatement of the run structure, not a second finding. It
is logged as C41 because of *when* it was caught. C27 was caught by the assessor,
C29 by a deliberate audit, C36 by a later correction. C41 is the first stopped
before the claim was written, and the thing that stopped it was mechanical —
computing the reference distribution because the rule requires it in the same
sentence as the number.

## The support, which is the step that matters

An index set is exactly the set of input patterns mapping to an output of one.
Phases 1 and 1b fitted gates without once asking which input patterns the data
contains. Across all 364 node triples the median triple visits 5 of the 8 corners
of its cube, and the modal corner holds a median 0.697 of the rows.

A gate is a labelling of all eight corners. So a large part of what separates one
catalogue member from another is being decided on corners the panel never visits,
which means those members are the same gate as far as this data can tell. This is
not a defect of the method. It is a bound on what the panel can identify, and it
was knowable before a single gate was fitted.

## What this changes, and what it does not

Phase 1's verdict is unaltered: the panel carries no predictive content for the
one-month WTI regime beyond the regime's own persistence of 79.31 per cent (A11).
What changes is that the verdict now has a visible mechanism instead of an
inferred one. The candidate parents either do not move, or they are crude oil
under another name. No scoring rule, description length or gate catalogue could
have rescued that panel, and the earlier framing — that Gate 1.0 *explains* the
source dissertation's failure rather than reproducing it — is strengthened.

It says nothing about whether the method works. It says this panel cannot test
it. That is the distinction Phase 3 acts on: daily resolution, where the oil
series have texture at the scale the pivots live on, and the macro covariates
dropped rather than carried along as decoration.

## Method note

The order used here is now the standing order for Phase 3: render the object,
read it, and let the measurement be a check on something already seen. Sections 2
to 4 of the notebook contain no statistics deliberately. If a pattern is real it
should be visible; if it only appears after averaging, that is a fact about the
averaging.
