# Stage A diagnosis: reproduction and bottlenecks (protocol 1.0)

Every number below is recomputed from retained raw rows. Nothing in this file selected a configuration: the Stage B rule did that.

## A.1 Reproduction

- Package verifier (full starting-hash mode, before any edit): PASS, exit 0. Log: `stage_a/commands/package_verifier.*`.
- Inherited policy-only verifier (`plan/claude_phase2_release/verify_package.py --policy-only`): PASS, exit 0. Log: `stage_a/commands/inherited_policy_verifier.*`.
- All research tests at start: 286 tests, OK, exit 0, 136.3 s. Log: `stage_a/commands/research_tests_start.*`.
- Public score recount from the raw `_r3` public rows and the frozen serial records (`stage_a/PUBLIC_SCORE_REPRODUCTION.json`): all 15 repetitions of each of the four lead-recounted arms agree with `PUBLIC_SCORE_RECOUNT.json` to 1e-12. Phase 2 scores 2.0327602339438613, original direct 2.0084662022846573 and classical 1.9013791212645499. The file lists all eight programs' C, S and J for each arm and all 15 scores.
- On that fixed suite, Phase 2 differs from original direct on exactly one program: vector_reduction J goes from 480 to 396 (S from 40 to 33). The other seven are equal.

**Why a strict finite-suite gain and a zero-touching interval coexist.** The public score is a deterministic function of eight fixed programs. All 15 repetitions are identical, so 2.03276 > 2.00847 is arithmetic, not an estimate. The accepted run's bootstrap interval answers a different question: it resamples programs as though they were drawn from a population. With one improving program among eight, many resamples contain no improving program. Those resamples give a ratio of exactly 1, so the lower percentile touches zero. Both statements hold at once, and neither says anything about the private grader.

## A.2 Stopping reasons of the accepted candidate (recounted, `_r3`, 100 held-out programs)

From `stage_a/STOPPING_AUDIT.json`, at 0.1 s (15 repetitions):

- Rows: 960 of 1,500 stop at the 32-query cap and 540 complete the pass. No row stops at the deadline.
- Programs capped in every repetition: **64 of 100**, which verifies the reported figure.
- Against accepted budgeted direct: 26 wins, 74 ties and 0 losses. **45 of the 74 ties** are programs capped in every repetition, which also verifies the reported figure.
- Query statuses summed over rows: INFEASIBLE 33,720, UNSAT 6,660, SAT 510, UNKNOWN 0.
- Accepted improvements: 510. Mean attempted queries: 27.26, maximum 32.

At 1.0 s the picture is the same: 960 capped rows and no deadline stops. The cap, not time, ended the search.

## A.3 Profile (DEVELOPMENT only)

Programs: the first two old held-out programs per family, in manifest order, plus the eight public programs. The profile ran outside every timing matrix. `stage_a/PROFILE.json` holds per-program wall times and cProfile cumulative shares; cProfile inflates absolute times, so only shares are quoted.

- Un-profiled wall time of the frozen controller: 1–10 ms per program, whether capped at 0.1 s or at 1.0 s. Removing the cap (1.0 s) still ends in `pass_complete` within 2–16 ms after 14–140 queries. **The frozen pass is short; the cap truncates it well before any deadline.**
- Shares of profiled time for the frozen configuration at 0.1 s, cumulative and overlapping:
  - `Domain.from_record` 39.7%, of which `machine.validate_program` 20.1%, `direct_contract.derive` 15.2% and incumbent `check_compilation` 13.5%;
  - the search itself 49.7%, of which option generation 7.5% and case validation 4.5%;
  - domain digest 6.6%;
  - serialisation 6.0%.
- About 82% of matched queries are INFEASIBLE, rejected before domain construction.
- Cold imports, median of 5 fresh interpreters:
  - bare interpreter 12.2 ms;
  - `machine` and `direct_compiler` 29.4 ms;
  - `research.run_structural_experiments` 45.6 ms.
  Imports dominate process time for these millisecond compilations.

**Engineering consequence (Stage B).** Re-validating the same program and incumbent on every query is repeated pure work. The `cached` build memoises it within one compilation, keyed by program object identity and incumbent canonical bytes.

## Development matrix diagnosis (Stage B rows, 0.1 s unless stated)

| arm | stop reasons (300 rows) | median compile s | median queries | UNKNOWN_SEARCH queries |
|---|---|---|---|---|
| frozen_phase2 | query_cap 192, pass_complete 108 | 0.0057 | 32 | 0 |
| new cap32_matched | identical to frozen (identity check) | 0.0057 | 32 | 0 |
| new cap512_matched | pass_complete 300 | 0.0069 | 44 | 0 |
| new cap512_wider | deadline 161, pass_complete 139 | 0.1005 | 62 | 155 |
| new cap512_wider @1.0 s | pass_complete 297, query_cap 3 | 0.1271 | 92 | 224 |

- Lifting the cap alone on the matched domain completes every pass. It gains only +0.00625 log over frozen at 0.1 s: 10 wins, 90 ties, 0 losses (`selection/search.json`). So the cap was a real truncation, but not where most of the headroom was.
- The wider domain supplies most of the development gain. It spends it by hitting the 0.1 s deadline in 54% of rows, and some eight-operation queries end UNKNOWN on their 0.1 s query allowance.
- The authorised construction-expiry correction (a query allowance expiring during domain construction) never triggered in any measured development row: QUERY_EXPIRED = 0. Its counterexample test (`research_tests/test_phase2_optimization.py`) exercises it with a real delay.

## A.4 Regression and mutation tests

Added in `research_tests/test_phase2_optimization.py` (20 tests, with real boundaries):
- window parity with the production owner on 216 cases;
- cap accounting;
- continuation after per-query expiry, with the frozen counterexample;
- genuine overall expiry;
- aggregate node and validation ceilings;
- retained late discrepancies;
- cached/reference build equality under deterministic limits;
- depth-2 proposal order and suppression;
- learner isolation, including a spy showing the worker hands the learner only training identities;
- split and elite rules;
- export audit refusals.

`research_tests/test_phase2_optimization_evidence.py` holds the checker and auditor mutation tests; see `final_checks/`.

No claim is made that classical wins are unreachable by our domains. Only the measured outcomes under the frozen domains, policies and limits are reported.
