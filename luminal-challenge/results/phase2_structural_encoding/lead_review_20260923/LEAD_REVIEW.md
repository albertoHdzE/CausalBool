# Phase 2 independent lead review — 2026-09-23

**Verdict: CHANGES_REQUIRED.** Reviewer: Codex.
Reviewed handoff: `phase2_20260922_final/HANDOFF.md`.
Reviewed source HEAD: `1aef90681e3dead3ab1f560da8b7823ab66dabf4`, with the
uncommitted research implementation. Exact file hashes and a source snapshot are
in `review_provenance.json` and `reviewed_source/`. No candidate source was edited
by this review. The original plan/package and worker runs remain intact.

The P1 coverage shortfall is independently reproduced. Stopping the actual
campaign at that gate was correct. However, omitted validation, incomplete raw
evidence and reproducible fail-open checks prevent implementation acceptance.
The passing unit suite does not close these findings. P2–P5 remain unmeasured;
there is no accepted runtime, compression or discovery result.

## Independently established results

| Check | Outcome | Retained evidence |
|---|---|---|
| Frozen delegation and baseline locks | PASS, 12 package and 46 baseline entries | package verifier; source hashes |
| Four new unit modules | 162 tests PASS, exit 0 | `tests.log` |
| Fresh full campaign invocation | P0 PASS; P1 INCONCLUSIVE; P2–P5 blocked; exit 2 | `../lead_replay_20260923/`, `replay.log` |
| Separate integer Cartesian oracle, all twelve fixtures | 48 codec/fixture rows agree; 24 small bit universes exhausted; round trips checked for every feasible object in all four codecs | `independent_oracle.json`, `independent_checks.py` |
| Public sampling with reviewer-added full case execution and full raw retention | 160,000 draws; 819 completions; 1,356 case executions; no validator/case discrepancy | `independent_sampling_rows.jsonl`, `independent_checks.json` |
| Unchanged production verification | FAIL only at historical evidence stage, exit 1; other eleven stages pass, including 142-program acceptance | `production_verification/`, `production_verification.log` |
| Adversarial review probes | Six concrete integrity/implementation gaps reproduced | `probes.py`, `probes.json`, `probes.log` |

Public option-path completion counts reproduce exactly: 0, 234, 194, 55, 135,
16, 168, 17 in pinned program order. Raw-bit streams complete zero times.
All streams finish their 10,000 attempts. Programs 01, 04, 06 and 08 miss the
100-distinct-completion gate. These measurements support the stated poor
coverage of this sampling policy, not the impossibility of structural encoding.
The reviewer-added case validation supports these particular sampled outputs;
it does not retroactively make the worker's original evidence complete.

The independent production comparator completed with exit 0: 72 rows, zero
failures and all seven gates passing. Direct combined scores remain
2.008466202284657 in all three repetitions. See `production_comparison/`.

## R1 — P1 omits required case execution and discards most raw attempts [P1]

Locations: `research/run_structural_experiments.py:567` (`_run_stream`),
`:1442` (`stage_p1`); `research/structural_encoding.py:1006` (completed decode).

The stream calls `se.decode`, whose completion path checks static feasibility
and `machine.check_compilation`, but neither path calls `machine.check_case` for
public sampled compilations. The independent oracle checks cases for its tiny
fixtures, which does not validate these different public outputs.

The retained stream consists of totals, at most 50 distinct completed examples
and 20 failed examples. The code explicitly discards the full identity set and
retains no row for each draw. Consequently the original 160,000 draws cannot be
reconciled from raw retained attempts as the contract requires. The original
`decoder_rows.jsonl` contains tiny-domain rows, not the missing public stream.

Reproduction: `probes.py` supplies a zero-width legal domain and replaces
`machine.check_case` with an observable raising mock. Three completions occur
with **zero case-validator calls**. Source inspection establishes the retention
caps. The worker's assertion that the correctness obligations are fully
discharged is too strong for the delivered evidence.

Required repair: execute every program case for every completed attempt, retain
one replayable outcome per draw and complete validator/case denominators, and
fail visibly on any discrepancy. Preserve all old runs. Produce a new P1 run;
do not relabel the existing run as fully validated.

## R2 — Evidence checker accepts erased evidence as complete [P1]

Locations: `research/check_structural_evidence.py:274` (`check_p1`), `:155`
(`check_provenance`), `:486` (`check_intervals`), `:944` onward (final disposition).

The checker derives P1 fixture membership from reported rows rather than the
locked twelve fixtures. It derives expected stream count from the reported public
coverage list. It trusts reported `set_equality`, coverage counts and aggregate
statuses. It does not verify the stored stage digest against the modified P1
summary, nor require the raw P1 files used to substantiate its conclusions.

Reproduction on a temporary copy of the real run: replace P1 fixture and coverage
lists with empty lists, empty the stream file, delete both decoder/oracle row
files, and mark P1 PASS. Leave the manifest unchanged. The unmodified control
returns exit 2 (correctly inconclusive); the corrupted copy returns **exit 0,
zero findings, artifacts_complete=true**. The deleted evidence was not replaced
with valid evidence. This is an acceptance blocker.

The same design weakness extends to later-stage statistics: `check_intervals`
checks seed/count/percentile labels but does not recompute numerical intervals
from raw rows. These branches are unmeasured; their claims must remain unaccepted.

Required repair: independently derive all required keys, validate raw evidence
and exact counts, recompute gates/sets/statistics, verify stage and input hashes,
and reject inconsistencies between gate records and evidence. Empty or incomplete
required data must never become a pass. Add this complete corruption probe with
an unmodified real-run control, not merely a test that a check ID appears in text.

## R3 — Single-stage resume bypasses failed dependency gates [P1]

Locations: `research/run_structural_experiments.py:1201` (`Run.prior`), `:3025`
(main dependency handling), and the stage entry points.

`Run.prior` reads a summary and optionally verifies its hash but never requires
its gate to be PASS. Missing expected hashes are accepted. Main's blocking logic
checks gates populated in the new run and explicitly skips that block with
`--inputs`. Imported gate/source/contract identity is not fully validated.

Reproduction: use the real inconclusive P1 run as `--inputs`, request P2, and
replace only the expensive P2 body with a stub that reads P1 through the actual
`Run.prior`. The stub is entered with `coverage_met=false` and main exits **0**.
The stub avoids executing prohibited downstream experiments; it demonstrates
that the CLI's gate does not protect them. Actual stage P2 also calls `prior`
without an additional PASS check.

Required repair: validate imported dependency gate, required digest, immutable
inputs and source compatibility before entering a dependent stage; import the
full transitive dependency record. Missing or inconclusive dependencies block
the stage regardless of whether inputs are local or imported.

## R4 — Construction time is refunded to search [P2]

Locations: `research/run_structural_experiments.py:776` and `:840–869`.

The runner captures `remaining` before domain construction, then starts a new
search budget with that same amount after construction. This affects both
expanded and matched searches. A slow constructor can consume the entire global
allowance and still receive a fresh search interval. Reporting overshoot does
not correct this accounting error.

Reproduction with a controlled clock: under a 0.01-second global allowance, the
constructor advances time to 1.0 seconds. Search is nevertheless invoked with
another **0.01-second** allowance. This is not ordinary uninterruptible-call
overshoot: the already expired search is deliberately started.

Required repair: use a shared absolute deadline covering construction through
validation; recompute remaining time after every construction step and before
search or candidate acceptance. Add separate construction, search and validation
interruption probes. No new positive budget may be manufactured with `max` after
expiry. Keep the previously validated incumbent.

## R5 — Conditional model implementation is incomplete [P2]

Locations: `research/run_structural_experiments.py:966` (worker dispatch),
`:2445–2524` (P5); `research/structural_search.py:39` (accepted arms);
`research/structural_models.py:207`, `:369` (proposal expansion).

The CLI advertises `structural_model`, but dispatches it into the ordinary DFS
search, which rejects that arm. The direct probe raises
`ValueError: unknown search arm 'structural_model'`. P5 can mark its model arm
PASS when authorised, yet `_benchmark_corpus` schedules only the fixed non-model
arms; no model rows substantiate that PASS. This path was correctly not reached
in the real run, so there is no actual false performance result, but the delivered
conditional implementation is not complete.

Additionally, `model_expand` obtains its first proposal by calling
`cover_members`, which enumerates the entire expanded cover into a Python set
before yielding. This contradicts the specified lazy, budgeted proposal stream
and can exhaust memory before the first deadline check on a large cube.

Required repair: implement the exact half-search/half-model policy specified in
the contract, route and measure it explicitly, require its rows conditionally,
and test the authorised branch with controlled fixtures independent of whether
this campaign reaches H4. Generate union members lazily under the shared budget.
A disabled arm must be NOT_RUN, never PASS without measurements.

## R6 — Reference manifest verification reads the wrong key [P2]

Location: `research/run_structural_experiments.py:207–214`.

The reference manifest stores entries under `sha256`; `verify_locks` reads
`reference.get('files', {})`. The loop silently verifies zero reference entries.
The baseline lock independently covers important reference code/program files,
so this is not a claim that all reference protection is absent. It does leave
manifest-only entries unchecked and makes the claimed full reference check false.

Reproduction: make the digest function report a wrong hash for
`.reference/README.md`, a manifest entry not independently listed in the baseline
lock. `verify_locks` still returns PASS with 58 checks and zero findings.

Required repair: use the declared manifest schema, require nonempty complete
membership, verify the pinned commit, and test an entry outside the baseline lock.
A missing/wrong manifest key must fail instead of behaving as an empty scan.

## L1 — Lead-owned test-placement conflict: confirmed

Claude correctly reported `BLOCKER_recorded_hashes.md`. The original delegation
placed four new test modules in `tests_direct/`, while the unchanged historical
evidence checker requires every top-level Python file there to appear in frozen
historical provenance. This is a contradiction in my handoff, not an unauthorised
worker change. The independent canonical rerun reproduces the same two failures
with no protected-source drift and all other stages passing.

**Lead decision for repair:** relocate these four research tests into a new
`research_tests/` package with an empty `__init__.py`. Update research source
snapshot discovery, internal test references and current run instructions.
Leave the original historical tests, checker and evidence untouched. This scoped
path amendment is specified in REPAIR_HANDOFF.md; the original locked delegation
package remains as historical input. New runs must record both original package
hashes and this amendment's hash.

## Scientific disposition and next action

H1: INCONCLUSIVE as a campaign claim; the reviewer found agreement on the finite
fixtures and all independently replayed sampled outputs, with the same coverage
shortfall. H2–H4: NOT_RUN. Production integration: NOT_PROPOSED.

Repair R1–R6 and L1 before asking for acceptance. Do not bypass P1 or tune the
sampler to satisfy coverage in this repair. A later scientific amendment may
investigate sound future-feasibility bounds or a different declared sampling
policy; that is a separate experiment and must retain this result. The bounded
repair instructions are in REPAIR_HANDOFF.md.
