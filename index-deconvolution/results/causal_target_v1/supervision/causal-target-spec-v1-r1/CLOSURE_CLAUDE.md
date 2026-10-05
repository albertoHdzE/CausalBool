# Claude Code — causal-target specification closure

Complete the correction task below without routine approval questions. Read
`REVIEW.md` beside this file first. The original phase is CHANGES REQUESTED.
This is a document/proof/literature closure, not an execution phase.

## Ownership and budget

You are not alone in this repository. Preserve others' changes and notebook19 /
build19. Write only into the new directory:

`index-deconvolution/results/causal_target_v1/review_closure/causal-target-spec-v1-r1/`

Do not rewrite the original run, supervisor review, packet, sources, notebooks,
old ledgers or historical results. No implementation, sampler, learner, encoder,
network generation, benchmark, notebook execution, installation, recurring task,
commit, push or publication. Do not execute the old draft, even partly.

Budget: at most 1,200 seconds controller wall including reading, retrieval,
corrections, verification and handoff. Stop optional work at 1,020 s. The existing
phase has 1,360 s charged (760 executor + 600 supervisor); keep that history.
Reserve 300 s for the next supervisor, all within the original 3,600 s ceiling.
Elapsed time is not permission to broaden scope. If sources cannot be accessed,
record the exact gap, finish what is independent, and hand off.

## Required corrections

1. **R1, literature and decision.** Read the primary Bshouty–Costa manuscript
   https://arxiv.org/pdf/1706.06934, definitions and §3.2/Theorem 2 with its
   prerequisites. Record page/theorem, class, query access, output, deterministic
   guarantee, query versus runtime costs and limits. Prove the coordinatewise
   mapping to the R4 network oracle, including shared non-adaptive queries.
   Apply the submitted P1/F4 rule: the decision becomes
   NO_JUSTIFIED_IMPLEMENTATION for this draft unless you find a precise error in
   that mapping, in which case report it with evidence and stop before any code.
   Record primary-source access/mapping for Akutsu 1999 and 2003 if obtainable
   within the cap; an inaccessible or unread paper remains explicitly unverified.
   Do not delay the decisive conclusion to complete an unnecessary broad survey.
   Withdraw the old draft via a new status/erratum document; never edit it.
   Do not claim known results exclude future improvements or implementation for
   a separately justified engineering purpose.

2. **R2, distribution.** Correct the “class-uniform” label with the probability
   calculation in REVIEW.md. Distinguish equal weighting of degrees from uniform
   distinct functions; state the correct degree weights for the latter. Use the
   supplied n=2,k=1 hand calculation. No sampler or sampled cases.

3. **R3, abstraction and outcomes.** Correct the abstraction scoring to check
   the full declared equation with supplied macro maps and beta. Include the
   q0/q1 counterexample, codomain/domain closure, identity intervention and
   missing-data denominators. Separate existence of individual induced maps
   from consistency with one declared macro intervention system. Correct the
   in-class qualification on INVALID and the distinction between unobserved
   values and values logically implied by a declared class. Update affected
   human/machine contracts consistently. Keep the four original witness records
   unchanged; the new counterexample is a labelled supervisor-requested proof
   illustration, not a retrospectively predeclared witness or a new empirical test.

## Deliverables and checks

- `corrected/`: self-contained corrected copies of affected specification files;
  an explicit draft-withdrawal erratum replaces a corrected executable draft.
- `LITERATURE_MAPPING.md`: primary sources, versions/URLs, retrieved identities,
  inspected sections, mathematical mapping and uninspected material.
- `CHANGELOG.md`: R1–R3 mapping, all changed claims, unchanged proof conclusions.
- `DECISION.md`: current disposition and exact scope of what is stopped.
- `NEXT_OPTIONS.md`: at most one page distinguishing (a) an explicitly motivated
  engineering integration/replication of known query learning, (b) multilevel
  abstraction validation requiring a named state space, candidate maps and allowed
  interventions, and (c) structural discovery from raw strings. State the missing
  decision for each. Do not invent a performance advantage, launch a follow-on,
  or write another execution protocol merely to keep the project moving.
- `evidence_manifest.json`, before/after preservation snapshots, `attempts.jsonl`,
  `time_ledger.jsonl`, and `HANDOFF.md`.

Before reading evidence, hash all twenty original run files, the supervisor
files you read and the 25 inputs in preservation_after.json. Recheck at handoff.
Record external drift without reverting it; scientific dependency changes must
be distinguished from your own changes. Include all additional local inputs and
retrieved source identities in the closure manifest. Do not claim more
preservation than you verified. Keep failed attempts.

Only document/hash/JSON checks and hand proof/arithmetic checks are needed.
Do not add a new test suite or re-execute the accepted 53-check witness artifact
just to fix prose. Verify human/JSON consistency and that every finding is
addressed. Finish HANDOFF.md marked **ready for Codex review; not yet accepted**,
report actual charges and unresolved limits, then stop.
