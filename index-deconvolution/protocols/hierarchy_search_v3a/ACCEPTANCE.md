# Required implementation gates and final handoff

## 1. Prefreeze checks (Claude executes; no routine approval pause)

- Packet constants/membership agree; source-state differences are explained and
  authorized; integration equality checks pass; historical median patch adopted
  exactly; protected owners and old result trees match the pre-edit snapshot.
- k=1 old behavior is preserved, including config serialization/hash, exact
  archive bytes, ties, cap exits and deterministic telemetry. All 1,792 retained
  full archives reproduce; all 208 treatment development jobs have valid records.
- Hand-computable fixtures exercise coarse rank/partition dedup, same-parent
  seeds, fewer than four seeds, independent refinement pools, level-major order,
  ties, converging paths, boundary clamping, step=1 termination, five-level limit,
  strict-commit and rejection, and a different k=4 path that can finish worse.
- Fixtures exhaust each deterministic cap during coarse work and mid-seed
  refinement; assert the exact best_seen archive, earliest tie and unresolved
  position. Trace requests/caches/rejections/cap-blocks match execution exactly;
  observer on/off leaves archives and deterministic work unchanged. Decoder
  disagreement is fatal; no oracle metadata reaches inference.
- Real-watchdog fixtures test timeout/RSS/status propagation, raw fallback and
  baseline censoring; deliberately tiny fixture limits are labelled as such.
  Resume corruption, changed identity, missing rows, duplicate rows and invalid
  evidence must fail the complete record-to-report pipeline. INVALID precedes
  INCOMPLETE; missing values never become zero; count jobs and sidecar events
  separately; explicit failed byte checks invalidate evidence.
- Tiny analytical fixtures verify six-cell weighting, actual n for ragged
  strings, paired units, fixed bootstrap RNG/order, 99% quantile endpoints and
  every verdict branch. Reserved-access tests reject generation before a fully
  validated study/source/config freeze, not merely an existing filename.
- Run the complete hierarchy suite once after final implementation (owners and
  orchestration changed), focused new tests and lint. Later reruns target actual
  edits/failures. Run relevant repository guards once; retain pre-existing
  single-engine failures separately and introduce no new duplicate owner. The
  existing dirty-tree ci-local exception applies only if its conditions still
  hold; document the exact alternative checks. Do not claim all guards passed.
- Freeze sources, imported repository dependency closure, tests, protocol/JSON,
  configuration/method registry, generator identity, input design, exposure
  inventory, analysis plan, budget, environment and prefreeze evidence. Archive
  executable closure, not just a git SHA or a subset of owner filenames. Resolve
  all imports in isolated workers. No reserved content enters prefreeze evidence.

## 2. Final required files under the new run/root

`IMPLEMENTATION_MAP.md`, immutable freeze JSON/hash and executable tar;
initial/final preservation manifests; environment; exposure inventory; development
job records/archives/trace and comparisons; intended prospective job manifest;
input/corpus manifests; row records and complete archives; per-arm B trace
sidecars; resource/attempt ledger; test/lint/guard logs; full verification and
read-only arithmetic audit; per-string/unit/cell tables; `REPORT.md`, machine
`DECISION.json`, readable `DECISION.md`; artifact-only notebook 20 and guarded
execution evidence from repository root and notebook directory; `HANDOFF.md`.

Every number in prose comes from saved artifacts. Notebook 19 must not import
encoder/search/generator modules or run an illustrative inference. Reuse the
reviewed artifact-only harness, allow decoder/ledger dependencies as needed,
block result writes/subprocesses, retain raw outputs and compare adjacent
same-name streams after coalescing. One guarded run per working directory is
enough after successful checks; rerun only to investigate a real change/failure.

## 3. Handoff checklist

The handoff must state: freeze/source identity; exact scope and primary verdict;
point estimate/99% interval or precise reason not assessed; target/control job,
string and paired-unit counts; unavailable/censored/invalid records and failed
traces; all baseline constituents and full archive costs; development exposure;
k=1 reproduction results; controlled code delta; telemetry meaning and observed
cap distribution; all discrepancies; cumulative time and remaining allowance;
preservation results; exact reproduce commands and artifact paths. Distinguish
baseline censoring from HID raw fallback. Report beneficial and harmful cases.

Do not write “final causal method.” State supported scope and what remains
unidentified. No result may rewrite the accepted search-v2 primary conclusion.

Stop with **ready for Codex review; not yet accepted**, including after INVALID,
INCOMPLETE or INCONCLUSIVE. No additional study, TILE change, combined version,
commit, push, publication or recurring process is authorized.
