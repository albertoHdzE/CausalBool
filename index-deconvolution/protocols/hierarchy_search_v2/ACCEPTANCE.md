# Review and acceptance contract

Normative companion to [the protocol](../../PROTOCOL_hierarchy_search_v2.md).
The developer completes the evidence packet and reports `ready_for_review`.
Only the supervisor marks the implementation/study accepted. Positive compression
performance is not an engineering acceptance requirement.

## 1. Required implementation evidence

- An implementation map connects every SEARCH.md requirement to its owner,
  focused verification and retained output. There is one legacy inference engine,
  wire serializer, decoder and shared description-length owner.
- Historical snapshots match their freezes. Old run trees hash identically before
  and after this work. No old row, archive, freeze, notebook result or verification
  record has been overwritten. New result paths and study IDs are unambiguous.
- The approved validator patch's four-file changes are integrated once, recorded
  with the approved hash, and its tests are retained. Current inventories reflect
  actual tests; 331 is the starting integrated suite, not a future hardcoded total.
- Legacy scientific-owner hashes remain unchanged from the recorded initial state,
  including the disclosed pre-existing BDM trace addition. Historical snapshots
  instead use exactly the historical hashes, with no provenance waiver. All new scientific dependencies
  and resolved settings are frozen and archived. No global production monkeypatch
  or hidden family/seed/input-specific branch selects inference behavior.
- The six-method registry, study-role/RNG-namespace separation, derived portfolio
  row and Cartesian design validation work through the production CLI.
- Every newly introduced full-input proposal and every retained archive decodes
  exactly with the independent decoder. Legacy internal candidate checks remain
  unchanged; this requirement does not mandate editing the legacy inference owner. Winning
  archive costs equal 8*file length; raw fallback includes its actual envelope.
  Deterministic ties and successfully completed nesting hold.
- Whole-wrapper resource accounting includes legacy computation in every arm.
  Finite candidate, leaf, scan, rule, depth and segment caps have explicit counters.
  No timeout observation is silently excluded or replaced with another arm's work.

## 2. Focused tests that matter

Retain the inherited suite, add meaningful tests for these behavioral risks, and
run repository lint on every changed Python file. Do not add a test-count quota.

1. Consensus majority/tie, ragged phases, a period outside the old grid (including
   63), corrected first-block noise, zero errors, global >64 corrections and the
   whole-input residual gate. Use constructed examples; truth belongs in assertions
   and never in inference arguments.
2. Local blocks with nonzero phase offset, a short final block, exact eligibility
   boundaries and literal fallback. Verify original bytes after decoding, not just
   agreement between two encoder-side expansion functions.
3. Cumulative candidate preservation, deterministic ties, independent-arm legacy
   calls and repeated-run archive identity under generous resource limits.
   Include a raw-selected input and a case where an added proposal strictly wins.
4. Boundary parent eligibility versus one-bit children, exact coarse cut set,
   refinement/bracket ties, strict-improvement termination, prefix-scan/cache/root
   budgets, best completed candidate retention on exhaustion, and graph sharing.
   Tiny exhaustive cut enumeration is a diagnostic fixture, not an assertion that
   this heuristic is always globally optimal. Test the shortest-period heuristic
   without claiming its byte optimality over all periods.
5. Independent stdlib-only decoder in an isolated subprocess, long/ragged inputs,
   graph/resource bounds and exact field-ledger sums. Retain old wire golden tests.
6. Registry dispatch, namespace-role separation, base/ragged generation identity,
   stress draw order/edit coordinates, no-reserved-generation prefreeze guard,
   source mismatch refusal and resume requiring identical input/config hashes.
7. The approved missing/malformed archive, duplicate row and undeclared case/split
   regressions through report and verify. Missing methods remain incomplete;
   contradictory or undeclared rows remain invalid. Verify replaces stale success
   with `not_verified` before potentially failing work.
8. Timeout, memory limit, baseline censoring, inference error and interrupted-resume
   paths using small isolated test runs. Test the actual runner path with controlled
   test-only workers, not just a synthesized status dictionary. Production generators
   and encoders must not acquire fault-injection switches that change frozen results.
9. Hand-computable unequal-length pairs and unequal cell means expose accidental
   bit pooling/string-level independence. Test primary sign, all evidence gates,
   targeted contrast populations, zero-touching intervals and portfolio minima.
10. End-to-end tiny fixture study: freeze, generate, encode, resume, report, verify,
    then deliberate corruption produces the correct non-success outcome. Keep
    fixture artifacts separate from scientific runs and forbid reserved keys.

If a platform makes a live memory-limit test nondeterministic, document that exact
limitation and test the watchdog/status propagation deterministically; do not say
a real memory breach was observed when it was simulated. Unit/fixture failures
must be fixed before the scientific freeze.

## 3. Full validation and report artifacts

Run the new study's `verify --full` after all declared rows exist, plus targeted
lint/tests, the single-engine guard and relevant repository guards. Inventory
all failures. A known `.kilo` duplicate-owner guard failure is acceptable only
with exact paths and evidence none were introduced by this work; it is not a
clean guard pass. Do not modify that worktree to make this assignment pass.
Run `make ci-local` if compatible with the existing working tree and execution
allowance; otherwise state it was not run and which equivalent relevant checks
were performed. Never claim repository-wide CI from a narrower command.

The notebook reads saved artifacts; it must not rerun inference or generate new
reserved cases. Execute it successfully and retain output/error checks. It must
show the negative historical result, exposure status, method stages, exact archive
examples, prospective population/counts, primary interval/gates, all five contrasts,
descriptive transfer/stress, overhead, supplied-boundary limitations and resource
failures. Figures must identify bits versus bits/input bit and paired-unit counts.
Do not overwrite notebook16 or alter its historical conclusion.

The final run includes:

| Artifact | Minimum contents |
|---|---|
| `freeze.json` and source snapshot | Complete hashes, environment, configs, contract, analysis and generator identities |
| Case/design manifests | Role and RNG namespace, paired unit, family, length, replicate, input hash; truth evaluation-only |
| `cases.jsonl`, `rows/`, archives | Exactly 1,792 cases and 28,672 unique case-method rows when complete; real content-addressed bytes |
| Telemetry/resource logs | Included stages, attempts/rejections, incumbents, caps, wall/memory, watchdog statuses, charged execution time |
| `summary.json` and claim ledger | Gate outcomes, primary, five contrasts, descriptive sections, counts and limitations |
| Diagnostics | Exact field accounting, stage yield, signed supplied-boundary gaps, explicit reference archives/metadata |
| Arithmetic audit | Independently reconstructed primary estimate, row counts, baseline minima and agreement tolerance |
| `verification.json` and check logs | Final status, source integrity, archive validation, suite/lint/guards/notebook evidence |
| Development record | Pilot/regression attempts, used inputs, corrections, runtime and explicit no-reserved-access declaration |
| `implementation_map.md` and deviations | Requirement-to-code/evidence links and every unresolved limitation |

Sidecars may use different filenames if the implementation map makes them
discoverable. The scientific row/role/method/config schemas and counts may not
silently change. Put diagnostic rows outside `rows/` and `cases.jsonl`; those
locations contain only the declared 16 benchmark methods.

## 4. Required handoff to the supervisor

Write `hierarchy/HANDOFF_SEARCH_V2.md` with:

1. Exact run ID, result root, freeze hash, code revision/snapshot and dirty-state
   disclosure. State `ready_for_review`, `incomplete` or `blocked_by_defect`, never
   self-assign supervisor acceptance.
2. What was implemented, which original owners remain identical, and where the
   approved validator patch and old-source snapshot were verified.
3. Commands executed with exit statuses, tests/lint/guard/notebook evidence and
   commands not run. Separate passed checks from known external failures.
4. Expected versus actual cases/rows/archives, exact-decoding results, resource
   events, resume history and cumulative experiment time.
5. Primary estimate/interval/gates and verdict; all five targeted comparisons;
   descriptive transfer and stress. A negative result is stated directly.
6. What the measurements say about templates, coverage, patch placement, boundaries
   and overhead, distinguishing evidence from explanations still untested.
7. Exposure/amendment history, unimplemented or untested paths, and any reason a
   result is not genuinely prospective. Replay is not replication.
8. Old-run before/after integrity evidence, reproducible read-only historical audit,
   and exact commands for the supervisor to review the new run without re-encoding.
9. Every modified/new file, any deviations needing a decision, and confirmation
   that nothing was committed, pushed or published.

Stop once the evidence packet is complete and handed off. If the primary is
negative, do not start another algorithm revision or reserved seed search inside
this assignment. If incomplete or defective, preserve everything and give a
precise recovery question; never present partial evidence as a completed study.
