# Claim-to-evidence table — task-compaction-v1-r1

| # | claim | evidence |
|---|---|---|
| C1 | Packet and the 21 scientific inputs were unchanged at start and at freeze | preflight hash check (26/26); `freeze.json` `inputs`; `logs/freeze_verify_*.json` |
| C2 | The stable partition is the coarsest output-preserving congruence on all of X, unique up to labels | `THEORY.md` §1–2 (proof); audit stage-induction check, 318 steps (`audit/audit.json` `denominators`) |
| C3 | Every saved stage is exactly the equivalence induced by the previous one, strictly refining until the first repeat | audit `check_stage_step` (per-block, two-way signature/label maps; not the producer's routine) |
| C4 | Decoders and macro tables are exact on every state and action | audit: 10,752 decoder states; 261,888 macro state/action entries; owner self-check |
| C5 | Witnesses are shortest, least-index, and replay in written order | audit: 294 witnesses replayed; least-index check per position; FX2/FX3/FX5 tests |
| C6 | Model tables are those of the accepted owner | audit: 85,504 entries vs `study.Model.q_table`; hand formula for 10,752 M2 and 256 M1 entries; FX8 hand check |
| C7 | Candidate decisions (decoding, closure, factorisation, comparisons) are correct for all 3,276 records | audit recomputation with its own fibre check; `candidates/cell_XX.jsonl` |
| C8 | INTERVENTION refines AUTO in every pair | `audit/audit.json` `intervention_refines_auto` (12/12) |
| C9 | The audit rejects decoder, macro, non-minimal-certificate and missing-plus-corrupt artifacts, with INVALID outranking missing | `audit/corruptions/corruptions.json` (4/4); COR3 validity True, minimality False |
| C10 | The implementation fails on each declared semantic mutant | `logs/mutations.json` (6/6, failing tests and sites recorded) |
| C11 | Exactly one production definition of each API function | `logs/owner_check.log` (scan + planted copy rejected) |
| C12 | Accepted behaviour preserved | `logs/regression_73.log` (73 passed on isolated revision) |
| C13 | One command reproduces the deterministic outputs | `run.sh`; `logs/reproduction_compare.json` (62/62 identical) |
| C14 | Patches apply and pass | `logs/patch_check.log` |
| C15 | No active or frozen file was modified | `logs/preservation_diff.json` (snapshots gzipped); `logs/git_before.txt` vs `logs/git_after.txt` |
| C16 | Primary outcomes: 3 EXACT_REDUCTION / 9 NO_REDUCTION; 11 MATCHES_OPTIMUM / 1 CANDIDATE_GAP | `production/summary.json`, `REPORT_TABLES.md` |

Not claimed: novelty; causal identification; minimal total description length; archive,
memory or runtime savings; grammar, self-similarity or spatial-scale interpretation of the
stages; any result beyond tau = 1, these four models, three tasks and two action regimes.
