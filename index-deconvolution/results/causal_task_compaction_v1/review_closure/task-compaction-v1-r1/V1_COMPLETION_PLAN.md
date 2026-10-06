# V1 completion plan: exact known-model task compaction

**Scope.** Inputs are a supplied finite deterministic model, a declared output and a
finite list of transition tables. The output is the coarsest all-state,
output-preserving congruence, with its certificate. Completion means an exact, tested,
documented small-model tool. It does **not** mean:

- scalability to arbitrary networks;
- recovery from incomplete or noisy data;
- causal identification;
- compression savings;
- a general causal theory.

## What the method can guarantee now (after this closure, if accepted)

1. **Exactness and minimality.** For valid inputs, `minimal_task_partition` returns the
   unique coarsest partition of all N states that preserves the output after every word,
   with stage certificate, decoder and macro tables, all checked on every state before
   returning (THEORY.md; Knuutila 2001, Prop. 4).
2. **Witnesses.** `distinguishing_task_word` returns a shortest, least-index separating
   word for any separated pair, given a verified certificate.
3. **Replay.** `task_word_path` replays only fully valid calls (R2). Malformed tables,
   states, actions or word containers raise ValueError before any step is taken.
4. **Saved results.** The saved 24-cell study is VALID_COMPLETE under an audit that also
   detects omission, duplication, malformed records and missing sealed artifacts (R1,
   23/23 matrix cases).
5. **K\* = N.** For a cell, K\* = N is equivalent to Definition-5 (pairwise)
   observability of the encoded BCN, and to nothing stronger (LITERATURE_MAP.md).

## Remaining work (one integration round, after Codex accepts this closure)

| step | deliverable | acceptance |
|---|---|---|
| I1 | apply `patches/*.patch` to the active tree (owner, `tests/test_task_compaction.py`, `tests/fixtures/task_compaction_v1.json`) | `git apply` clean; the three files are byte-identical to `isolated/`; 73 + 52 tests pass in the active venv; owner check passes and fails on a planted copy |
| I2 | declare the new test file and fixture in `tests/MUnit/MANIFEST.tsv` / `pytest.ini` as governance requires | `check_test_manifest` agrees; no new FAIL lines in `check_single_engine` |
| I3 | user-facing contract in the owner's docstring section plus a short worked example (FX2 two-step and the rule-150 reset pair) | runnable, with outputs asserted in tests |
| I4 | scoped validation command: the closure's `REGENERATE.sh` over the saved run | VALID_COMPLETE; matrix 23/23 |
| I5 | explicit limits: memory Q·N, worst case N rounds of O(Q·N), no symbolic scaling, all-start contract | stated beside the API |
| I6 | release checklist: provenance (run IDs, freeze, these SHA-256s), the GOVERNANCE/CORE.md owner entry for the three names | Codex sign-off |

No benchmark or rerun is required for I1–I6.

## Decision on further research

**NO_NEW_STUDY_JUSTIFIED** (see DECISION.md). A candidate question would be the exact
symbolic K\* at n beyond explicit tables under the same contract. It currently has no
concrete application demanding it. The closest prior methods read here (GFB and BBE)
change the object to variables or the domain to block-constant states, and the
same-contract symbolic literature was not read. Without a real need there is no
acceptance criterion to pre-register. Revisit only when an application supplies a model
too large for explicit tables together with a task whose answer depends on the exact
K\*. At that point, read the symbolic-bisimulation literature first.
