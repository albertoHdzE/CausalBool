# Codex review — task-compaction-v1-r1

2026-10-05. Decision: **CHANGES_REQUESTED before adoption**. The saved scientific results reproduce; no incorrect optimum or candidate decision was found. This is not a rejection of the numerical findings, and not permission to change the scientific contract.

## Evidence independently checked

- `run.sh` executed into `/tmp/task_compaction_codex_20261005_repro`: VALID_COMPLETE, 24 cells, 3,276 candidate decisions, 85,504 owner transition entries, 318 stage steps, 261,888 macro entries, 294 witnesses.
- All 62 declared deterministic artifacts, including the audit, are byte-identical to the originals.
- All 397 output-manifest entries match both SHA-256 and byte count. Freeze verification checks 20 isolated files, 21 inputs and 18 run files.
- Scoped tests rerun against the delivered isolated revision: **109 passed** (73 accepted regressions, 31 new fixtures, 5 audit-label tests).
- Independently counted summary outcomes: INTERVENTION 3 reductions and 11 family matches; AUTO 10 reductions and 5 family matches.
- Independently checked every pair of M4/T1 INTERVENTION states: its partition equals projection onto {0,1,8,9}; exactly those four bits are essential to the saved grouping.
- Read the proof, owner patch, candidate/certificate audit and integration tests. The all-start, full-table, output-preserving congruence argument is sound. The witnesses do not by themselves establish minimality; the complete stage induction does.

The full 109,851-file preservation snapshot was not independently rehashed. Active core and tests have no tracked changes in the targeted status check. Full CI and the known repository-wide single-owner failures remain outside this acceptance evidence.

## R1 — audit completeness and failure handling (blocking acceptance)

Three probes on disposable copies expose real audit defects:

1. Replace `summary.json`'s `cells` with `[]`: audit exits 0 and reports VALID_COMPLETE. It compares the rows supplied but never requires the declared summary case set. A zero-row summary is not complete evidence.
2. Remove only `tables/M1.json`: audit reports INVALID because the available table count falls below the intended count, even though it also records the missing file. Missing evidence alone must be INCOMPLETE.
3. Replace `candidates/cell_00.jsonl` with malformed JSON: an uncaught JSONDecodeError exits without an audit record. Malformed available evidence must produce a structured INVALID result, and independently available evidence must still be checked.

These semantic probes used the audit's explicit `--bypass-integrity` mode, so a stale seal could not mask the intended check. In normal mode, missing sealed files must also be distinguished from present bytes with wrong hashes. The replacement audit must verify exact declared IDs and summaries, report intended/available counts, and preserve INVALID > INCOMPLETE precedence. It must not return success merely because an omitted artifact was never inspected.

## R2 — added public replay helper (blocking integration)

`task_word_path([[3,0]], 0, [0])` returns `[0,3]` despite a two-state domain. `task_word_path([[0]],0,None)` and `task_word_path([3],0,[])` leak TypeError. The function checks action indices but not the full transition contract or word container.

Approve this third public helper as an ownership extension only with complete input validation before replay. Use the same table/domain rules as the minimizer; word is a list/tuple of valid built-in integer action indices (empty allowed), x is a valid built-in integer state, bool excluded. Malformed calls raise ValueError. No generators or coercion. Preserve all valid-call results. New tests must catch actual invalid behavior, not simply a missing symbol.

## Integration and accounting conditions

- Move the declared fixture data used by the proposed core tests into a small versioned `tests/fixtures/task_compaction_v1.json` in the integration copy, with provenance back to the unchanged run fixture. Deliver its patch. The new test must work without this run directory. This is packaging, not a new scientific finding.
- The unchanged `repertoire_program.py` mirror is an acceptable read-only dependency; record it in the revised ownership/import manifest.
- Gzipped preservation snapshots are acceptable when both compressed and uncompressed identities are recorded.
- The historical ledger reports 1,685 seconds and explicitly excludes final handoff/manifest work estimated under 300 seconds. Record a conservative **300-second supplement** in a separate closure note: historical charge 1,985 seconds, with the handoff category 518/900. Do not overwrite or backdate the original ledger. The spoken approximately 1,750-second total is not a complete ledger.
- No production rerun, retuning, new tasks or interventions are required to close these findings. Use saved artifacts and declared small fixtures. Replacement audit/source revisions receive new identities; the original freeze remains unchanged.

## Conclusion and next step

The exact finite-model reference is useful: it separates a restricted candidate-family gap from a genuine no-reduction result under a fixed task. M4/T1 is the former; the nine full-state primary cells are the latter. This is state compaction given a known model, not recovery of an unknown causal system and not archive compression.

Delegate the bounded closure plus primary-literature positioning in `../../delegation/task-compaction-v1-r1-closure/NEXT_CLAUDE.md`. After acceptance, one integration/documentation round can finish this narrowly scoped v1 component. Any further research needs its own unresolved question and decision gate; no number of phases can promise a final general causal theory.

Reviewer setup disclosure: the first local hash checker compared digest strings with manifest metadata objects. Correcting it to use their `sha256` and `bytes` fields gives 397/397 matches. This was a reviewer-script error, not evidence corruption. The semantic probe outputs are retained separately.
