# Decision — closure of `causal-target-spec-v1-r1`

Supersedes `causal-target-spec-v1-r1/DECISION.md` (preserved unchanged). 2026-10-05.

## Disposition

**NO_JUSTIFIED_IMPLEMENTATION for the proposed query-recovery study.** The draft
`DRAFT_EXECUTION_PROTOCOL.md` is **withdrawn** (`corrected/DRAFT_WITHDRAWAL_ERRATUM.md`).

Reason: the original decision's own precondition P1 and falsifier F4 are met. Bshouty and Costa,
arXiv:1706.06934v1, §3.2 Theorem 2, give a deterministic non-adaptive exact learner for d-Junta with
O(d·2^d·log n) membership queries and n^{O(d)} time; with d = k it identifies every coordinate of a
network in C(n,k) from one shared query set under R4 (`LITERATURE_MAPPING.md` §2). Akutsu 1999,
Proposition 1, gives a further deterministic sufficient condition under chosen inputs. No error was
found in the supervisor's mapping, so there is nothing to report before code; no code was written.

## Exactly what is stopped

- The withdrawn draft as a study: arms ADAPT, RAND, FULL, BOOLNET, AKUTSU2003; confirmation sets A
  and B; the falsifiers F1–F3 as a programme of work.
- Any sampler for either distribution in erratum E3, any generator, learner, certifier
  implementation, oracle entry point in `src/deconvolution.py`, benchmark or run derived from the
  draft. Preconditions P2–P4 lapse and confer no approval.

## What is not stopped or concluded

- The corrected specifications (`corrected/`) stand as specifications: access regimes, target T\*,
  outcome taxonomy, the proofs in TARGET_CONTRACT §3 and §5, IDENTIFIABILITY W1–W4, the singleton
  certifier as a mathematical statement (its runtime unmeasured; "cheap" means only the stated
  finite operation count), and the abstraction contract.
- Known results do not exclude future improvements in query count or runtime, nor an implementation
  made for a separately justified engineering purpose (for example integration or replication of a
  known learner). Either would need its own motivation, its own comparison with existing exact
  learners, and its own authorisation; neither a full-table baseline nor RAND alone would establish
  a contribution.
- Multilevel abstraction validation is neither stopped nor started: it still lacks a named state
  space, candidate maps and allowed interventions (`NEXT_OPTIONS.md` (b)).
- The overall method is not declared complete, and multilevel causal abstraction is not declared
  impossible.
