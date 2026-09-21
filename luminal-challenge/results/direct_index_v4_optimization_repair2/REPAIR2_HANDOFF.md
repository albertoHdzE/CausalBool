# Repair of F1, F2 and the reporting refinements — handoff for lead review

Worker: Claude Opus 5, working linearly without subagents.
Responding to: [lead re-review](../direct_index_v4_optimization_repair/REVIEW.md),
verdict CHANGES_REQUIRED, 2026-09-20, reviewed commit `bb88b31`.
Machine-readable gate table: [gates.json](gates.json).

**Nothing here is accepted. Only the lead accepts.** No submission, push or
publication. This was an evidence-only repair: **no production file was
touched**, no speed experiment was run and no target was altered.

---

## Summary

Both findings are closed. Each was reproduced through the checker's real entry
point before anything was written, covered by regressions that failed on the
reviewed code, and then repaired.

| Finding | State | Observable, before → after |
|---|---|---|
| **F1** report controls its own interval protocol | **CLOSED** | `one_resample` → `all_passed=True` → **rejected**, `bootstrap_protocol:final` + `confidence_intervals:final` |
| **F2** required verification stages removable | **CLOSED** | `missing_verification_stages` → `all_passed=True` → **rejected**, five checks fail |
| Reporting refinements | **DONE** | both corrections made; the previous handoff carries a supersession header and is otherwise unaltered |

Two files changed, both of them evidence instruments:
`check_optimization_evidence.py` and `tests_direct/test_evidence_checker.py`.
Every production source hashes exactly as it did at `bb88b31`, and the export is
byte-identical: `d14bf39b450aaa5f…`, 2,652 lines.

The checker now runs **50 checks** (was 42) and the direct suite **340 tests**
(was 300).

---

## Reproduction, before any edit

The lead's own probe script was rerun unmodified against the reviewed tree. It
reproduced both findings exactly, and its output is byte-identical to the
`probes.json` the lead retained.

```
one_resample                  {'all_passed': True, 'failures': []}
missing_verification_stages   {'all_passed': True, 'failures': []}
```

Retained at
[`reproduction/lead_probes_before.txt`](reproduction/lead_probes_before.txt),
with the script itself copied beside it. The lead's `lead_review/probes.json` in
the previous round's tree is unchanged.

### The regressions failed before the repair

The new regressions were written next and run against the reviewed commit
`bb88b31` in a throwaway git worktree, with only the regression file's own
recorded hash adjusted so that the run would exercise the checker rather than
stop on the hash of the test file being introduced:

```
Ran 64 tests in 308.931s
FAILED (failures=46, errors=2)
```

All 18 pre-existing R3 regressions passed there, including the control — so the
46 failures and 2 errors are exactly the new F1 and F2 coverage, and nothing
else. The full list is at
[`reproduction/regressions_before_repair.txt`](reproduction/regressions_before_repair.txt).

---

## F1 — the report controlled its own confidence-interval protocol

**Cause.** `check_aggregates_and_intervals` recomputed each paired interval with

```python
seed=reported_interval.get("seed", seed),
resamples=reported_interval.get("resamples") or resamples,
```

taking both numbers out of the very interval it was auditing. An experiment run
at one resample was therefore recomputed at one resample, agreed with itself to
the last bit, and passed — while the printed detail still said ten thousand,
because the detail string interpolated the unused CLI default. The lead is right
that this recomputes a weakened experiment consistently instead of rejecting it.

**Repair.**

1. The protocol is fixed in the checker, as `EXPECTED_BOOTSTRAP_RESAMPLES =
   10000` and `EXPECTED_BOOTSTRAP_SEED = 20260920`, and a new check
   `bootstrap_protocol:<phase>` runs **before** any interval is recomputed. It
   requires the harness constants, the run-level seed, and every contract
   ratio's `resamples`, `seed` and complete field set to be the contract's, and
   requires the per-interval seed to agree with the run seed.
2. Every recomputation — bounds, aggregates and both target decisions — uses
   those fixed constants.
3. **`--resamples` is gone.** The lead's criterion was that an option must not
   relax an acceptance check; the honest way to satisfy that is not to have the
   option. A regression asserts that passing it now exits rather than running.
4. Target declarations must be complete. Previously
   `if reported_target and met != ...` skipped an absent or truncated entry
   silently, so omitting a target avoided being compared against it. Each of the
   two contract targets must now carry all six fields, the contract's target
   value, and `measured`, `interval_low`, `interval_high` and `met` that agree
   with the recomputation; a target outside the contract is rejected.
5. The detail line now reports the settings actually enforced, and the contract
   block in `evidence_checks.json` carries `bootstrap_resamples: 10000` and
   `bootstrap_seed: 20260920` under a note that no option can change them.

**Cost control.** Recomputing eight intervals at ten thousand resamples costs
about 4.5 s, and the regression suite runs the checker 64 times. The intervals
are memoised on their exact inputs — rows, programs, arms, repetitions — which
is caching a pure deterministic function of its arguments and changes no
verdict. The evidence stage runs in **22 s**, down from 68 s at two hundred
resamples, while now recomputing at the full ten thousand.

**After:**

| Mutation | Before | After |
|---|---|---|
| bounds correct at **one** resample, declaring `resamples=1` | passed | **rejected** — `bootstrap_protocol:final`, `confidence_intervals:final` |
| bounds correct at 10,000 but seed 12345 | — | **rejected** — same two checks |
| run-level seed drifted | — | **rejected** |
| `resamples` or `seed` missing from an interval | — | **rejected** |
| a whole interval or ratio missing | — | **rejected** |
| a target declaration omitted, truncated or weakened | passed | **rejected** — `target_decisions:final` |
| a target invented outside the contract | — | **rejected** |

---

## F2 — required verification stages could be removed without rejection

**Cause.** `check_verification` asked for `status == "PASS"`, no failing record,
some positive **total** test count, and the corpus totals. A summary holding
only `schema` and `corpus` satisfies all four. The positive fixture in the
regression suite was itself that two-record summary, so the suite asserted the
hole rather than the contract — the lead's point, and it is the part of this
finding I find least defensible.

**Repair.** Twelve records are now required, one for each of the nine declared
test stages and each of `corpus`, `public_suite` and `cli`, split across seven
checks:

| Check | What it requires |
|---|---|
| `verification_stage_contract` | the verifier's own declared stage list and public-test count are still the contract's, so a stage dropped from `verify_direct.py` fails as readily as one dropped from a summary |
| `verification_stages` | exactly one record per required identity; missing, duplicated and unexpected identities all rejected |
| `verification_status` | summary PASS, no recorded failure, every record PASS with exit code 0 and not timed out, and `stages_run` covering the contract |
| `verification_test_counts` | a positive test count in **every** test stage |
| `verification_logs` | each record's log exists, its `Ran N tests` line equals the recorded count, and the recorded `stderr_tail` really is that log's tail |
| `verification_public_suite` | exactly 11 tests against a declared expectation of 11, exit 0 |
| `verification_corpus` | 142 programs and 277 cases, cross-checked against `isolated_corpus.json` row by row, against the materialised `corpus_manifest.json` and its input files, and against the export the corpus was actually checked with |
| `verification_cli` | the eight pinned public programs, each exit 0, JSON-only stdout, not timed out |
| `verification_export` | the summary's export hash and line count are the file on disk |

**The fixture is now complete and built explicitly.** It writes twelve records,
a log per logged stage whose `Ran N` line agrees with its record, and an
isolated-corpus evidence file. It does **not** read the surrounding run's
artifacts, which is what made the old one degenerate: the `evidence` stage runs
before `acceptance`, so anything the fixture reads from the tree may not have
been written yet. It materialises the 142 corpus programs itself through
`verify_direct.materialise_corpus` — the function that owns writing them — and
counts 277 cases from the inputs rather than asserting them.

That self-reference actually bit once in this round, on the first pass: the
fixture read `verification/corpus` before the acceptance stage had created it,
produced an empty corpus and failed six tests. The failing artifacts are
retained at
[`superseded_first_pass/`](superseded_first_pass/README.md) with the diagnosis,
rather than discarded.

**After:**

| Mutation | Before | After |
|---|---|---|
| the lead's deletion, keeping only `schema` and `corpus` | passed | **rejected** — 5 checks fail |
| removing any **one** of the 12 required records | passed | **rejected**, all 12 cases |
| a duplicate standing in for a missing stage | passed | **rejected** |
| a stage record outside the contract | — | **rejected** |
| a stage reporting zero tests | passed | **rejected** |
| a stage FAIL, nonzero exit, or timed out | rejected | rejected |
| a summary-level failure | rejected | rejected |
| a count its log does not support, a missing log, a fabricated tail | passed | **rejected** |
| public suite at 10 tests | passed | **rejected** |
| a dropped, failing or non-JSON CLI program | passed | **rejected** |
| corpus evidence missing, short, failing, discrepant, for the wrong export, or naming a program outside the materialised set | passed | **rejected** |
| the summary's export hash drifted | passed | **rejected** |

---

## Reporting refinements

Both are corrected here and marked on the previous handoff with a supersession
header; nothing in that document was rewritten.

### 1. "Both speedups fell" was wrong, and the cause was not isolated

The bootstrap figure went **up**, 1.1371x → 1.1380x. And the attribution —
"the price of the correctness repair", "Correctness bought that 1.8%" — claimed
a causal decomposition those runs cannot support.

This round makes that plain, because it changed **no production code at all**
and remeasured the same binaries:

| Round | Production code | full_candidate_vs_frozen | 95% CI | bootstrap_candidate_vs_frozen | 95% CI |
|---|---|---:|---|---:|---|
| v4 (pre-R1) | before R1 | 1.9889x | 1.9841 – 1.9913 | 1.1371x | 1.1334 – 1.1406 |
| v4 repair | after R1 | 1.9536x | 1.9503 – 1.9567 | 1.1380x | 1.1326 – 1.1411 |
| **this round** | **identical to v4 repair** | **1.9471x** | 1.9396 – 1.9509 | **1.1337x** | 1.1280 – 1.1428 |

The last two rows share byte-identical sources and the same export
`d14bf39b450aaa5f…`, yet the full-direct figure differs by 0.0065x and the
intervals barely touch. The correct statement is therefore: **the full-direct
figure varies by a few tenths of a percent between runs on this machine, the
within-run intervals do not capture that variation, and the R1 clock reads
plausibly contribute to the v4→repair change but these runs do not isolate their
cost.** Nothing here separates the two.

### 2. The two slow classical medians are described, not diagnosed

Calling them "machine variation in the baseline arm" named a cause that was not
established. What is observed, in milliseconds:

| program | v4 | repair | **this round** |
|---|---:|---:|---:|
| parallel_memory | 0.3567 | 1.3935 | **1.4115** |
| scalar_selects | 0.3441 | 1.3763 | **1.3822** |
| the other six | 0.15 – 0.40 | within 2% of v4 | within 2% of v4 |

Two of eight classical medians are about four times larger than in the v4 round
and have stayed there across two subsequent rounds; the other six are stable to
about 2% throughout. So this is a step change that reproduces, not a transient,
and **its cause has not been established.** Any classical-relative ratio must be
read with the run it came from, and this round's classical-relative figures are
not comparable with the v4 round's.

---

## Results of this round

### Correctness

| Command | Exit | Result |
|---|---:|---|
| `verify_direct.py --stage all` | 0 | **PASS**, 12 stage records, **340 direct tests**, 11 public tests, **142 programs / 277 cases**, CLI 8/8 |
| `compare_direct.py --repeats 3` | 0 | 72 measurements, **all seven gates PASS** |
| `benchmark_optimization.py --phase final` | 0 | 600 public rows + 1,500 corpus rows, **every mandatory gate PASS** |
| `check_optimization_evidence.py` | 0 | **50 checks, all passing** |
| `repair2_probes.py` | 0 | control passes; **13 of 13 mutations rejected**; R1 still UNKNOWN |
| `git diff --check` | 0 | clean |

Combined public score, recomputed from the raw integers and identical for all
four direct arms: **2.008466202284657**, the accepted v3 value. Classical
**1.9013791212645499** in all three comparison repetitions. No per-program
product regressed; the frozen and candidate bootstrap arms produce identical
metrics on all eight programs.

Frozen evaluation corpus: 100 programs × 5 arms × 3 repetitions, 0 failures,
0 discrepancies, and **no corpus program is slower on either direct path this
run** — the previous round reported one on the bootstrap path, which reinforces
reading that as run-to-run variation.

### Performance — both targets still missed, and reported as missed

| Target | Required | Measured | 95% paired CI | Met |
|---|---:|---:|---|---|
| Full-direct vs frozen v3 | ≥ 2.00x | **1.9471x** | 1.9396 – 1.9509 | **NO** |
| Bootstrap vs frozen v3 | ≥ 1.20x | **1.1337x** | 1.1280 – 1.1428 | **NO** |

Pooled median ratios, a different statistic and never mixed with the above:
2.3891x and 1.1699x.

Missing a target is not a gate and does not fail a run. It is an outcome of the
experiment, reported under `performance_targets`.

---

## Provenance

| Item | Value |
|---|---|
| Base commit | `bb88b31e5ec2166bc9c34d5fd540edac7320b7db` |
| Export | `d14bf39b450aaa5fe73c41a3236980e219089e527ae43007781d78e0059a5864`, 2,652 lines |
| Frozen v4 snapshot | `c0574395d339dae3b24e819955795c2a6165953c5966e46062c9bf9b18a50ce2` (reused, not remeasured) |
| `check_optimization_evidence.py` | `c7ac7a2b5b6836231c34667cf6985a1406d765852eea976339afab5923a3b20e` |
| `tests_direct/test_evidence_checker.py` | `8c03685b9c6f8b8ab130a2240b51af3c70dee639970cc79647e34f61fcb18755` |
| Every other source and test | unchanged from `bb88b31` |

The frozen v4 baseline, its snapshot and its 100-program evaluation corpus are
reused unchanged and were not overwritten. The whole chain was rerun **after**
the script hashes were final, so the checker's and the harness's own content is
inside the provenance it audits.

---

## Limitations, and what the lead should know

1. **Both engineering targets remain missed**, 1.9471x against 2.00x and
   1.1337x against 1.20x. No further speed work was attempted, as instructed.
2. **Between-run variation exceeds the within-run intervals.** Three
   measurements of the same two binaries give 1.9536x, 1.8951x and 1.9471x for
   full-direct. The reported 95% interval is timing uncertainty within one run
   on a fixed program suite; it is not a bound on what a rerun will produce. The
   1.8951x figure is the superseded first pass, retained.
3. **The cause of the two slow classical medians is unknown**, as above.
4. **The lead's retained `probes.py` still cannot be rerun against the previous
   tree** and now additionally would fail on hash drift, because this round
   changed the checker whose hash that tree records. The equivalent for this
   round is
   [`reproduction/repair2_probes.py`](reproduction/repair2_probes.py), which
   keeps every one of the lead's mutations and adds seven more. The lead's
   `probes.json` and `phase_exit_probes.json` are untouched.
5. **The interval memoisation is a cache.** It returns the same value the
   uncached call returns, keyed on the full input, and a cold run of the checker
   recomputes everything; but it is a correctness-bearing optimisation in an
   evidence instrument and deserves the lead's eye.
6. **The regressions follow the current round's tree.** `REPAIR_TREE` now points
   at `direct_index_v4_optimization_repair2`, because a tree records the hashes
   of the sources being exercised and an earlier tree fails on drift alone,
   which would say nothing about the checker. The suite skips cleanly if the
   tree is absent.
7. Single machine, ordinary load, eight public programs and 100 generated ones.

---

## Rerun instructions

```sh
PYTHONPATH=.reference python3 export_direct.py
PYTHONPATH=.reference:. python3 benchmark_optimization.py --phase final \
  --baseline results/direct_index_v4_optimization/baseline --repeats 15 \
  --seed 20260920 --output results/direct_index_v4_optimization_repair2/final
PYTHONPATH=.reference python3 compare_direct.py --repeats 3 --timeout 20 \
  --output results/direct_index_v4_optimization_repair2/comparison
PYTHONPATH=.reference python3 verify_direct.py --stage all --timeout 20 \
  --output results/direct_index_v4_optimization_repair2/verification
python3 check_optimization_evidence.py \
  --root results/direct_index_v4_optimization_repair2 \
  --baseline results/direct_index_v4_optimization/baseline
PYTHONPATH=.reference:. python3 \
  results/direct_index_v4_optimization_repair2/reproduction/repair2_probes.py
git diff --check -- luminal-challenge
```

The benchmark must run before the verification, because the `evidence` stage
audits the report the benchmark writes.

---

**READY_FOR_REVIEW.** F1 and F2 closed with entry-point evidence for each, both
reporting refinements made, both speed targets still missed and reported as
missed. Only the lead may record a verdict.
