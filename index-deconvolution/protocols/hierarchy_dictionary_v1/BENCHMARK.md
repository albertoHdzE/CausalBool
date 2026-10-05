# Dictionary feasibility design and gates

## 1. Cases and jobs

Use exactly the 96 cases in the pinned existing
`protocols/hierarchy_multilevel_v1/CASES.json`: F01..F12, base lengths1024/4096,
replicates3000/3001, base/ragged. Decode retained raw archives, verify input hash
and actual n; never regenerate inputs. These cases are exposed. No efficacy gate,
new holdout, benchmark smoke execution, tuning or corpus sweep before lock.

After lock, 96 fresh A0 jobs must reproduce the original saved `hid_full` records
using every field in the pinned multilevel-v1 contract, recursively removing
only keys ending in wall_s. All96 pass before 288 new independent D0/D1/D2
augmentation jobs, CASES order then arm order, <=2 active children overall.
384 new encoder jobs;288 composite rows are derived, not additional jobs.
Import/decode/hash the864 constituent baseline records and reconstruct96 portfolio
minima with the owner tie rule. Also import96 old A3 selected archives/rows and
their view eligibility masks for the D0 comparison; do not rerun old A3.
Those96 historical rows add no jobs and provide no fresh runtime comparison.

Reuse input/case/reference identities, not old generation code. Physical runtime
counts each worker once; each hypothetical composite is charged its full A0
worker cost plus its own augmentation. Keep historical timings separate.

## 2. Fixture declaration and tests

At most24 new distinct engineering inputs, each<=4099 bits. BEFORE any fixture
execution write exact constructions, bytes/hashes and expectations to
fixtures/declared_inputs.json. Any random input uses local seed63001. Reuse
declared cases across configurations; existing owner regression suites are
outside this24-input count. Fixture-definition changes need a versioned amendment
before execution, preserve prior declarations and count the union toward24.
No test input may be one of the96 benchmark strings. Do not search fixtures
until one beats A0; fixture efficacy does not choose the algorithm.

Required coverage:

- Empty/short, odd tails at multiple levels, both origins, k=1 and k=m with
  descendants still evaluated; forced grouping versus reuse.
- Exact internal periods and non-dividing shortest periods; replacement can
  increase total archive size despite shorter period bases.
- Exact complement/reversal/composition, and related words with0,8,9 flips;
  predecessor-window edge, first-appearance tie rules, nonzero word origin.
- Hop-depth8 boundary, no cycles, original versus already-rewritten donors,
  shared donor retained when otherwise unused, and full graph caps.
- Every mode preserves expansions and the full input; no free dictionary or
  exception bits; exact ledger sum. A hand-built shared-word witness must exercise
  smaller relation-mode full bytes than its corresponding O proposal, without
  requiring a gain over A0. Derive the expectation before running it.
- P disabled reproduces O; R disabled reproduces its base mode; D1 restricted
  to O reproduces D0; D2 restricted to O/P reproduces D1. On declared fixtures,
  D0 restricted to the old branch mask reproduces old A3 deterministic proposals,
  allowing differences only in new diagnostics/configuration labels.
- Parent-persisted owner-built A0 survives real watchdog termination at fixture
  limits. Cover timeout/RSS, crash, corrupt/missing checkpoints, incomplete atomic
  writes, resume identity mismatches, INVALID-over-INCOMPLETE and absent values
  through the entire record-to-report path.
- Meaningful mutations for donor misreference, omitted exception, dropped tail,
  free dictionary cost, incorrect relation-hop cap, free A0 runtime, and missing
  treated as zero. Mutations must fail assertions, not merely fail import.

Before lock run focused tests, existing hierarchy suite, relevant description
length tests, lint, and core-index/test-manifest/single-engine guards. Retain
pre-existing failures; do not edit frozen files to remove them. The scoped
ci-local dirty-tree exception remains; never state all checks passed.

## 3. Analysis

Saving(X,Y)=(bits(Y)-bits(X))/actual input n. Mean base/ragged within replicate,
replicates within family/base-length, then equal24-cell mean (48 paired units).
Report every per-string/pair/cell value and better/tie/worse count. Comparisons:
D0 vs oldA3 (changed pruning); D1 vs D0 (internal periods); D2 vs D1 (relations,
including combined period/relations); each D arm vs A0, pair_grammar and portfolio.
Report R(O) and R(P) contributions from traces descriptively, not as independent
randomized effects. More modes imply more work; measure this explicitly.
No bootstrap, significance, confidence interval, fractal or causal endpoint.

Evidence state INVALID > INCOMPLETE > VALID_COMPLETE. Missing values stay null,
with intended/available denominators; no aggregate on a silently reduced set.
Never evaluate recommendation logic unless VALID_COMPLETE. Valid watchdog
fallbacks remain observed deployed outcomes; distinguish them from completed
search, and never claim exhaustive absence of gain when search stopped early.

Fixed exploratory label, evaluated in this order:
1. RELATION_GAIN_OBSERVED if D2 beats D1 on any case.
2. PERIOD_GAIN_OBSERVED if D1 beats D0 anywhere, but condition1 is false.
3. CONTROL_ONLY_GAIN if D0 beats A0 anywhere, but conditions1/2 are false.
4. NO_RETAINED_GAIN otherwise.

Always show all incremental wins/losses and fallback counts alongside the label;
it is guidance about these algorithms on these cases, not adoption or proof of
mechanism. For complete searches D0 includes old A3's admissible candidates;
independently verify that no missing incumbent gain violates nesting. Imported
old A3 equals A0 here, but keep the comparison explicit.

## 4. Deliverables

Implementation map; versioned fixture declaration; all test/mutation/guard logs;
implementation lock and full import-closure snapshot; environment/import probe;
initial/final preservation; resource and attempt ledgers; intended jobs; baseline
reproduction gate; references; per-job rows/archives/traces/checkpoints;
summary/tables/gap maps and REPORT/DECISION; independent read-only arithmetic
audit; notebook22 and both guarded executions; HANDOFF with all acceptance items.
The notebook reads saved artifacts only: no encoder, generator, fitting, BDM
computation, subprocess or writes into result trees. Reuse the reviewed guard
and join adjacent same-name stream messages when comparing directories.

Stop at HANDOFF even if gains are promising. Do not run confirmation, enlarge
donor windows/flip caps, search rotations, tune widths or repair historical tests.
