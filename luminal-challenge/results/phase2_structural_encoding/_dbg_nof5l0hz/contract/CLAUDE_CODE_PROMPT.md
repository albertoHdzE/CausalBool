# Copy this assignment into Claude Code

You are the implementing coder for the Luminal phase 2 research campaign.
Alberto has authorised this delegation. Codex owns the scientific specification
and the independent acceptance review. Work in:

`/Users/alberto/Documents/projects/CausalBool/luminal-challenge`

Start by reading, in full:

1. `AGENTS.md`, `plan/STATUS.md` and `plan/INDEX_ONLY_PLAN.md`.
2. `plan/OPTIMIZATION_PHASE_PLAN.md`.
3. `plan/PHASE2_STRUCTURAL_ENCODING_PLAN.md` (version 2.1).
4. `plan/phase2/IMPLEMENTATION_CONTRACT.md`.
5. All JSON files in `plan/phase2/`, `REVIEW_PROTOCOL.md` and `HANDOFF_TEMPLATE.md`.

Then run `python3 plan/phase2/verify_package.py`. A failure blocks affected work;
report it with its exact cause. Do not change the specification to pass it.
The already modified scientific plan belongs to Codex; preserve it.

Implement the entire research campaign described by the contract, progressing
through P0–P5 as their gates permit. Start with the ownership record, frozen inputs,
independent oracle and codec proofs/tests. Keep production unchanged. The contract
fixes all domains, field layouts, algorithms, arms, budgets, seeds, metrics, stage
dependencies and output requirements. Do not replace those choices with your own.
If a genuine contradiction prevents implementation, isolate it and report it;
otherwise continue autonomously. A null scientific result is legitimate completion.

You are not alone in the codebase. Edit only the contract's allowlisted new files
and new run directories. Preserve other changes. Do not delegate, change branches,
stash, reset, amend, commit, merge, push, submit or modify frozen evidence. Reuse
existing code owners; do not create alternative cube algebra or machine semantics.
No BDD, SAT/SMT library, classical seed or fallback may enter the candidate path.

Pay particular attention to these failure modes:

- Bit offsets stay fixed even when address traversal depends on the schedule.
- INVALID_CODE, DEAD_END, INTERRUPTED and a validator discrepancy are different.
- Locally legal choices may have no complete solution.
- Fixed external lifetimes can change when selected consumers move.
- An exact cover of observed elites cannot discover unseen indices.
- UNKNOWN and radius exhaustion do not prove unrestricted UNSAT.
- Oracle/training information must not leak into the candidate's timed search.
- Every attempted, failed and duplicate proposal remains in the denominator.
- A scientific gate that fails does not authorise tuning on held-out results.

Run the requested unit, mutation, independent-oracle, experimental and unchanged
production checks. Retain actual commands, complete logs, exit codes and hashes.
Implement and run the evidence checker against both real outputs and corrupted
fixtures. Do not rely on success banners or self-reported totals.

Your final response must give the modified-file list, run root, test/experiment
commands and outcomes, P0–P5 and H1–H4 dispositions, all failures and unrun stages,
and the completed HANDOFF.md path. End with `READY_FOR_REVIEW`. Only Codex may
mark the work accepted after independent review.
