# Bitácora 03 — The comparison arm, and an arrow that points either way

**Date:** 2026-08-18
**Status:** parity gate complete; B5 complete; B4 not started.
**Tests:** 45 passing (15 new, 36 belief networks fitted).
**Ledger entries produced:** C11–C14.

---

## 1. What this step was for

The index-set network is to be measured against the belief network, so the belief
network has to be *ours* before the measurement means anything. Bitácora 01
established parity of the shared input — the discretised frames. This step
establishes parity of the comparison arm itself: the structure search, the K2
parameter estimator, the inference, the benchmarks and the inferential statistics.

It also delivers B5, the stability comparison, which the GWP3 report explicitly
records as missing evidence (§7, claim 7: "a structure meant to inform policy has
to be robust, and ours was not... the dissertation does not report any stability
analysis such as bootstrap edge frequencies").

## 2. What reproduces

Everything that determines an outcome, cell for cell against `results.json`:

- all 18 configurations of both specifications, on validation accuracy and error;
- the selected configuration of each specification — A: K2, unrestricted
  in-degree, expert-seeded, 24 edges; B: BIC-d, in-degree ≤ 2, unseeded, 4 edges,
  validation accuracy 58.62;
- the selected skeleton and the Markov blanket of the forecast node ({WTI\_CL}
  for B, all seven for A);
- every validation and test score, including the confusion matrices;
- the benchmarks: uninformed 34.48, majority 72.41, persistence **79.31**;
- the inferential statistics: exact binomial interval [56.46, 89.70] and both
  exact McNemar tests at *p* = 1.00.

The edge-count range of 2 to 25 across configurations (anchor A15) reproduces and
is now asserted as a test.

## 3. What does not reproduce, and why it is not a porting error

The validation grid does not reproduce **row for row**, and the investigation of
why is the substance of this entry.

The first symptom was a flapping test: grid B failed in one pytest run and passed
in the next, with no change to the code. Five consecutive runs in a single process
were identical, and identical to the reference. Running specification A before B
changed nothing. Churning the global numpy generator changed nothing.

Varying `PYTHONHASHSEED` changed the answer:

```
hashseed=0  MATCH      hashseed=3  MISMATCH
hashseed=1  MISMATCH   hashseed=4  MISMATCH
hashseed=2  MATCH      hashseed=5  MISMATCH
```

pgmpy's hill climbing breaks score ties in the iteration order of a hashed
collection. The hash seed is fixed at interpreter start-up, so this cannot be
controlled from inside a test; `scripts/phase1_stability.py` therefore
re-executes itself as a subprocess to vary it.

Measured across twelve seeds, per configuration:

| | specification A | specification B |
| --- | --- | --- |
| configurations whose validation accuracy varies | **0 of 18** | **0 of 18** |
| configurations whose edge count varies | 3 of 18 | 3 of 18 |
| which configurations | `bdeu/*/False` | `bdeu/*/True` |
| size of the disagreement | 1 edge | 1 edge |
| hash seeds reproducing every edge count | 9 of 12 | 5 of 12 |

The instability is confined to the Bayesian Dirichlet equivalent uniform score.
K2 and the discrete Bayesian information criterion do not tie. The row order of
the grid then moves because it is sorted on validation accuracy with ties broken
on edge count — so an unstable edge count reorders otherwise identical rows.

GWP3 did not record its hash seed, and it cannot be recovered. Row-for-row parity
is therefore not achievable *in principle*, and the tests were rewritten to say
so precisely rather than to chase a seed: every ranking input is asserted exactly,
and the discrepancy is asserted to be at most three configurations, confined to
BDeu, and off by one. Choosing a seed that happened to match would have been
fitting the test to the artefact.

## 4. The result: a Markov-equivalent pair, and an arrow that points either way

The stability sweep over twenty seeds returned something sharper than a count.

Specification B's **selected configuration is stable** — BIC-d, in-degree ≤ 2,
unseeded, four edges, validation accuracy 58.62, every time. Its **forecast
blanket is stable** — {WTI\_CL}, every time. Its **edge set is not**: two
distinct graphs occur.

```
variant 0:  Brent_BZ -> Ind_Prod,  Brent_BZ -> WTI_CL,  WTI_CL -> WTI_Spot,  WTI_CL -> forecast
variant 1:  Brent_BZ -> Ind_Prod,  WTI_CL -> Brent_BZ,  WTI_Spot -> WTI_CL,  WTI_CL -> forecast
```

Same skeleton. Identical v-structure sets (both empty). The two graphs are
therefore **Markov-equivalent**: they encode exactly the same conditional
independences and cannot be distinguished by any score based on them. They make
opposite causal statements.

GWP3 §6 and Figure 8 present the learned chain as
WTI\_Spot → WTI\_CL → Brent\_BZ. Variant 0 reverses both of those arrows. The
same code, on the same data, with the same selected configuration, learns the
chain in either direction depending on the interpreter's hash seed.

Specification A, by contrast, is orientation-stable: one distinct selected edge
set over twenty seeds. The instability is not universal — it lives exactly where
the score ties.

## 5. Why this is the strongest thing in Phase 1

The report's §7 criticism of the dissertation's policy claim is that the evidence
for structural robustness was never produced. C13 produces evidence, and it is
worse than the report supposed. It is not that the graph is sensitive to the
scoring function, which one might defend as a modelling choice with a rationale.
It is that the *selected* graph's causal orientation carries no information: it is
determined by a randomised string-hashing detail of the interpreter. The
predictive content is unaffected — the blanket is stably {WTI\_CL} and every
score reproduces exactly — but the arrow directions are the only part of the
figure a policy audience would read, and they are noise.

This is also the first point at which the two arms of the study differ for a
*structural* reason rather than a performance one. Functional connectivity in the
index-set calculus is defined by exact functional dependence: input *i* is
connected to output *k* if and only if flipping *i* changes *k*. That is a
directed fact about the dynamics, checkable one input at a time, with a printed
witness. It cannot be decided by a tie in an aggregate score because no aggregate
score is involved. And where the data genuinely fail to determine a dependence,
the method reports an explicit equivalence class — the ambiguity histogram of
Level 1, where 679 of 1700 nodes had a unique gate name and the rest carried
classes of up to size 7 — rather than resolving it silently and printing an arrow.

I want to be careful about how far that claim goes. What is established here is
the defect on the belief-network side, measured. The corresponding claim about the
index-set side is currently an argument from the method's definition, not a
measurement in this package. Turning it into a measurement is B4 and the rest of
Phase 1, and until then it stays labelled as an argument.

## 6. Two errors of mine, corrected

- I asserted the binomial interval as [56.46, **89.71**], reading the report's
  "89.7" as a rounding of a figure I had not checked. The record says 89.70. The
  test now asserts the record.
- The first version of the grid test demanded row-for-row parity, which sent me
  looking for a bug in the port for some time before the hash seed surfaced. The
  lesson is the same one as bitácora 02 §10: an assertion of reproducibility
  should be scoped to what is reproducible, and the scope should be measured
  rather than assumed.

## 7. Status of Phase 1

- **B5, stability: done.** C11–C14.
- **B4, description length of the two encodings: not started.** It needs the
  index-set encoder, which this package does not yet contain. This is the next
  piece of work and it is the one that turns §5's argument into a measurement.
- The Phase 1 forecasting contest remains **not attempted**, per protocol §2 and
  the Gate 1.0 verdict of bitácora 02. Nothing found here changes that: the
  belief network's predictive content is a stable {WTI\_CL} blanket, and Gate 1.0
  showed WTI\_CL to be the target under another name.

## 8. Next

Build the index-set encoder and measure B4: the self-delimiting description
length of the belief network's conditional structure against the index-set
network's, on the identical frames. Then Phase 2.
