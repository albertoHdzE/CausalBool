# Codex acceptance — causal-target-spec-v1-r1 closure

2026-10-05. **ACCEPTED. R1, R2 and R3 are closed.** The accepted specification is
the original material as superseded by the closure's corrected files, decision,
withdrawal erratum and the interpretation notes below. The original run and the
closure retain their historical handoff labels; this separate review records
acceptance. No source patch or scientific implementation is adopted.

## Decision

Accept **NO_JUSTIFIED_IMPLEMENTATION for the proposed query-recovery study**.
Its draft is withdrawn, not executable. This is a scoped research decision,
not a declaration that the overall method is complete or cannot improve.

R1: the exact-learning class and query model map correctly coordinatewise to R4.
A target-independent non-adaptive query set can be shared across all output
coordinates; reconstruction work remains separate. The submitted P1/F4 rule
therefore applies. No practical finite-n query advantage is established.

R2: equal degree weights and uniform distinct functions are correctly separated.
The n=2,k=1 probabilities and n=16,k=3 weights are correct; no sampler was needed.

R3: the evaluation now distinguishes existence of per-intervention induced maps
from agreement with supplied macro maps and beta. The q0/q1 counterexample is
valid. The corrected full equation, codomain requirement, identity intervention,
failure-before-incompleteness rule and declared-pair denominators resolve the
scoring defect. INVALID is correctly qualified to the model class, and observed
versus class-entailed values are separated.

## Evidence and limits

`audit_acceptance.json` has fourteen passing checks, including all 50 protected
hashes, exact original run/supervision file sets, all 12 manifested outputs,
JSON/JSONL parsing, arithmetic and the two retrieved PDF hashes. All 15 closure
files remain unchanged. No witness script, learner, sampler or benchmark ran.
The proof/counterexample review is mathematical inspection, not empirical testing.

The 1999 sufficient condition is also visible in [Akutsu et al., Proposition 1](https://psb.stanford.edu/psb-online/proceedings/psb99/Akutsu.pdf).
Its functional interpretation follows because two functions with supports of
size at most K differ, if at all, on an assignment to their union of size at most
2K. This does not identify redundant declared input syntax. The decision does
not depend on its counting lower bound or on unread Akutsu 2003 results.

Nonblocking notes, recorded here without another closure cycle:

- The hash-matching `/private/tmp/ak99.pdf` has **12 pages**, confirmed by
  `pdfinfo`; the closure's “10 pp.” metadata is wrong. The PDF identity matches
  the manifest and the relevant proposition is present. Treat this review as
  the page-count erratum; do not rewrite the preserved manifest.
- “No numerical bound at n <= 16 was validated” is the accepted limitation.
  Do not strengthen it into “the papers contain no explicit constants”: the
  Bshouty–Costa construction includes explicit size expressions. Extracting a
  useful finite-n bound was not this closure's result.
- Preliminary induced-map existence is subject to codomain membership as well
  as the fibre condition. Constant/identity controls are existence controls;
  they cannot override a failure against incorrectly supplied macro maps or beta.
- On a restricted non-closed domain, the contract is a one-step statement.
  Iterating a macro model needs further domain/closure conditions. Exhaustive
  consistency on a finite declared domain is exact for that domain; fresh states
  or interventions are needed for a broader claim, not to re-prove an exhaustive
  finite check. CLASS-ENTAILED presupposes a nonempty valid version space.

Akutsu 2003 and unread abstraction literature remain explicitly unverified.
They are not blockers for the scoped withdrawal or for acceptance of the
self-contained finite deterministic contract.

## Next direction

Recommend option (b): a finite multilevel abstraction-validation design. It most
directly addresses the user's original interest. Define the dynamics, state
encoding, candidate maps, intervention semantics and scoring before running it.
Distinguish supplied abstraction validation from discovering an abstraction.
No compression extension or query learner is resumed by this recommendation.

`NEXT_CLAUDE.md` is a proposed design-only delegation for the user to send. It
delegates routine model/map choices so another clarification round is not
required. No follow-on work has been launched; its execution study remains
subject to review of a concrete protocol.

## Accounting

Original executor 760 s + original supervisor 600 s + closure 417 s + conservative
acceptance-review charge 300 s = **2,077 / 3,600 s**. This completes the current
phase. The next design delegation, if invoked, has its own declared allowance;
unused time is not transferred. Nothing committed, pushed or published.
