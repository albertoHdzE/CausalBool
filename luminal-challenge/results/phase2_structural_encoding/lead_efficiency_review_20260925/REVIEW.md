# Lead review: assurance and propagation efficiency

2026-09-25 · Codex · `efficiency_20260925` · protocol 1.0.

**ACCEPTED_WITH_LIMITATIONS** as a bounded research release. Gate R is closed;
Gate P's **NO_JUSTIFIED_OPTIMIZATION** stop is accepted. No release-blocking
finding remains from this review. This is local research acceptance, not
production promotion or a performance-success claim.

The assurance repairs and the decision to stop at Gate P are supported. There
is no new engineering candidate or measured performance improvement in this
phase. The earlier practical enhancement target remains **TARGET_NOT_REACHED**.

## Findings and dispositions

**Construction accounting: CLOSED.** The successor preserves search and clock
reading order while checking every construction exit. The lead probe reproduces
the parent's zero count, then obtains one interruption and one overrun from R0,
with `UNKNOWN_DEADLINE` and the late cap proof retained as diagnostic evidence.
The search/model validation counts are separated and summed. No late incumbent
acceptance was found. The new regressions cover terminal exits, exact equality,
query/global expiry, resumes, validation discrepancies and the model seam.

**False learning PASS accepted by the auditor: CLOSED.** The successor auditor
recomputes both confidence endpoints and gate flags, training labels, pool
membership, returned orderings, yields, economics, public scores and export
membership. The lead's original false-PASS/upper-bound mutation now fails with
six `LEARNING_CONTRASTS` findings; the parent still accepts it. The unchanged
release passes 162,982 checks with zero findings. Its field map declares
unchecked metadata explicitly; this is not a complete semantic verification of
every field. Historical construction counts retain their old incomplete meaning.

**Historical source and ranker provenance: ACCEPTED WITH THE RECORDED SCOPE.**
The historical checker still has exactly one report-only source deviation and
420 oracle-capability flags. The successor accepts only the exact disclosed
hash pair/scope and the retained guarded replay. My rerun reports zero unapproved
findings. The old FAIL is preserved. I independently checked all 420 retained
replay rows, original ordering digests, allowed loaded modules, input-read paths
and copied input/code hashes. This review did not rerun the 420 rankers or treat
their replay as new efficacy evidence. Correcting the `importlib.machinery`
substring false positive by evaluating the retained rows is appropriate.

**Inherited snapshot failure: RESOLVED BY THE LEAD.** This was an environment
path mismatch, not a solver discrepancy. `snapshot_probe.py` captures the two
fresh checker reports without changing them. On Claude's snapshot the only
differing JSON field is `/run`: the first report names the snapshot's symlink
path; the second names its resolved live-workspace path. Their hashes therefore
correctly differ. See `SNAPSHOT_DIAGNOSIS.json` and its log.

I created a new snapshot using the same 74 hash-checked original source/test
files, retained the historical-result links, and gave temporary test results a
real directory inside that snapshot. The previously failing test then runs and
passes, with identical checker reports (`CLEAN_SNAPSHOT_RETEST.json`, log).
The first clean-snapshot attempt lacked historical evidence and skipped; that
attempt is retained as `CLEAN_SNAPSHOT_TEST.*` and is not counted as a pass.
The empty `.git` directory remains in the passing snapshot, so `.git` is not
the cause demonstrated by this probe. No frozen checker or test was weakened.

**Per-query learner: CLOSED FOR THIS ARCHITECTURE.** With sound bounds and
validator agreement, only strict improvements reach the observation hook, and
the first accepted improvement ends the query/epoch. At first model preparation
there can be at most one observation, including the half-allowance exception,
against the required 20. Faster propagation cannot fix that state-lifetime
constraint. This does not rule out other learning architectures. The historical
0/100 acquisition result remains a diagnostic, not an isolated timing estimate.

## Gate P and the stop decision

Accept **NO_JUSTIFIED_OPTIMIZATION** for the proposed mechanism and this bounded
phase. The ten development programs expose different dominant costs across
families. The rule-2 filter proposal predicts a fixed-work cost ratio of 0.9395
(about 6.1% saving), below the required plausible 20% saving. Even its zero-cost
scan calculation gives 0.8188 on this sample. No E1 was implemented and no E/C
candidate outcomes were generated. Stopping is the specified successful process
outcome, although it supplies no new speedup.

The following qualifications supersede broader wording in the worker's profile:

- These are diagnostic calculations on ten selected development programs with
  instrumentation overhead, not population bounds or confidence intervals. They
  do not establish that 20% improvement is impossible on another cohort.
- Low repetition of whole function inputs does not rule out caching shared
  subcomputations or incremental updates. The previous worklist result concerns
  that implementation; it does not exhaust all changes affecting multiple
  propagation components. Neither observation justifies implementing another
  candidate without a new measured case.
- There are **90 retained profile rows**, not the 80 stated in `PROFILE.md`:
  30 `time` and ten each of `timers`, `timers_split`, `profile`, `count`, `memory`
  and `parity`. The additional ten original `timers` rows were retained. This
  documentation count error does not change the selected split-timer estimates.
  It is corrected here without modifying historical artifacts.

The stdlib-only `recount.py` verifies the profile membership, 8,827 charged
fixed-work nodes, parity flags and reported component ratios. It reaggregates
the proposal's per-program predictions but does not independently validate its
128 ns microbenchmark assumption. Acceptance of the stop does not rely on a
proven achievable cost saving.

## Independent verification

| Check | Lead result |
|---|---|
| Locked assignment | PASS: 4 package files, 120 protected inputs |
| R0 freeze | 15 source/test hashes and exported compiler hash unchanged |
| Successor numerical audit | PASS: 162,982 checks, 0 findings, 0 unmapped fields |
| Successor evidence checker | PASS_WITH_APPROVED_HISTORICAL_DEVIATIONS, 0 unapproved |
| Before/after defect probes | Construction repaired; false audit PASS rejected |
| Focused efficiency suite, including inherited semantics explicitly bound to R0 | 93 tests pass in 421.893 s, exit 0, no skips |
| R0 standalone export, regenerated | Identical SHA256; 142 programs / 277 cases pass; pinned tests and score exit 0 |
| Previously failing inherited test, corrected snapshot | 1 run, 1 pass, no skip; reports identical |
| Replay/profile/source recount | PASS; 420 replay rows, 90 profile rows, no source drift |

Export SHA256:
`74c87b69e63063595d3283bb66986162297519bb1a8a2a87f2853fd7134d9ea9`.
The lead's export run is correctness verification. It overlapped tests and must
not be used as a new performance comparison. The complete 536-test live-tree
run and 442/443 original snapshot result remain Claude's retained evidence;
they are not presented as freshly rerun full suites by the lead.
Commands, exits, scope and final source hashes are retained in `VALIDATION.json`.

## Next action

Close this bounded assurance/efficiency round and retain R0 as the reviewed
research baseline. No further Claude repair assignment is required for the
reproduced release blockers. No additional benchmark sweep is justified by this
handoff. Production promotion, paper changes and external release remain outside
this review.

If further enhancement is chosen, its next task should first produce a measured
proposal for reducing shared work across propagation components, with a precise
parity obligation and cost estimate. The current per-query learner stays retired;
reopening learning would require a separate design for label acquisition and
state lifetime. Neither study has been launched or delegated here.
