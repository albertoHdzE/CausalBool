# Decision — `causal-target-spec-v1-r1`

**DRAFT_QUERY_RECOVERY**, with one unexecuted draft: `DRAFT_EXECUTION_PROTOCOL.md`, marked NOT
AUTHORIZED FOR EXECUTION. This is a choice of what to specify next. It is not a GO decision, it is
not a claim of headroom, and nothing in it has been run.

## Why this and not the alternatives

**For DRAFT_QUERY_RECOVERY.**
1. The target is finite and assessable: C(n,k), n ≤ 16, with ground truth by full table
   (TARGET_CONTRACT §3; EVALUATION_SPEC §1).
2. The phase produced an **exact, cheap certification criterion** for the class. Node i is
   identified iff every support T (|T| ≤ k) consistent with the answers has all 2^|T| projections
   observed, and all such fully determined tables are the same function. Two different tables on
   one T are different functions, and different T give one function only through equal essential
   sets and reduced tables. This yields IDENTIFIED / AMBIGUOUS without guessing, and makes W1-type
   errors impossible within the class. [F, argument in the draft §3]
3. Current source has no chosen-query arm (EXISTING_EVIDENCE §1, checked 2026-10-04), and the
   full-table route stops at the 2^n wall (`bitacora/01`).
4. Falsifiers can be stated before any run (draft §8).

**Against DRAFT_ABSTRACTION_VALIDATION, for now.** The contract (ABSTRACTION_CONTRACT §2–§3) is
complete, but there is nothing yet to validate. The missing information is specific:
(a) a labelled state space, i.e. a named network or class, on which an abstraction is wanted;
(b) a declared family A of candidate maps α from that space, which may come from the user's width
and origin views, but only once a pairing from states to strings is fixed (§5); and (c) a declared
intervention set Q with timing. Without (a)–(c) a validation run could only re-derive W3 and W4.
The author must supply them, or explicitly delegate their choice.

**Against NO_JUSTIFIED_IMPLEMENTATION.** A finite target, a certifier, fair baselines and
falsifiers exist. The draft could still lose its value: see precondition P1 below. If P1 shows that
the same class and access already have a published exact algorithm with a guarantee, the decision
reverts to NO_JUSTIFIED_IMPLEMENTATION. The draft would then merit at most a labelled replication.

## Preconditions before anyone may authorise the draft

- **P1, literature.** Read the primary sources and record their observation and perturbation
  models: Akutsu et al. 1999 [8] and 2003 [9], and the exact learning of k-juntas with membership
  queries. This phase did **not** access those sources. Their guarantees are not transferred and
  are not guessed.
- **P2, review.** Codex acceptance of this specification, including the Q_LB audit.
- **P3, generator scope.** Authorisation for the instance generators named in the draft §5. These
  are the owner `random_network` plus a class-uniform sampler, which does not exist yet.
- **P4, ownership.** Agreement that any implementation enriches `src/deconvolution.py` with an
  oracle-mode entry point under the monolithic-code law (it reuses `essential_variables` and
  `identify_gate`). It must not be a new parallel package.

## What remains unproved (first-class findings)

- No upper bound on chosen queries for C(n,k) is proved here. The Q_LB values at n ≥ 50 are valid
  worst-case lower bounds (EXISTING_EVIDENCE §2), but whether they are tight is unknown.
- The screen's S2 "headroom" is not established. It compared a worst-case bound with per-instance
  counts of a non-adaptive, non-certifying learner.
- Akutsu 2003 was not mapped onto the R4 access regime.
- Constructive abstraction (Beckers and Halpern) was not inspected.
- The transfer of static-SEM abstraction definitions to one-step dynamical maps (two-layer
  unrolling) is our construction, not a theorem of either paper.
