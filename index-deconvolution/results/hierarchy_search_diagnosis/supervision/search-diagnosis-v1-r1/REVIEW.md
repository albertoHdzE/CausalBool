# Codex review: search-diagnosis-v1-r1

Date: 2026-10-03. Decision: **CHANGES REQUESTED; not yet accepted**.

The diagnostic jobs are complete. Do not rerun D2–D4. The retained computation
passes the independent byte/graph audit; the interpretation and reporting closure
below remain necessary. The accepted search-v2 conclusion is still inconclusive.
These diagnostics do not establish a final causal method.

## Findings

### R1 — P1: replace unsupported impossibility and exact-effect claims

`DECISION.md:47–49` says that when H = T no search change in the frozen language
can recover the loss. Lines 64–66 turn an observed 40–48-bit penalty for particular
repeat translations into a floor for any HID-v1-style DAG. Neither follows from
these measurements. Protocol §§7–8 expressly limit D4 to the translated proposal.
Even byte-identical H and T would not prove optimality over all HID descriptions.

There is also a concrete distinction between equal length and equal proposal:
**21 of the 282 losing H = T cases have different full and translated archive
bytes**. For example, `confirmation-F01-1024-3003-ragged|period`.
`audit.json.same_length_different_bytes` retains all 21 identifiers. Statements
that the search reached "the same proposal" must become length statements unless
structural identity is actually checked.

This also invalidates `NEXT_PROTOCOL_DRAFT.md:85–97`'s prediction of exact changes
in full-method H from subtracting fields in T. A future fully specified rewrite
can have an exact per-proposal T′ cost, accounting for graph sharing/pruning,
rule IDs, variable-length fields and the new wire envelope. That does not give
an exact full-search H′ prediction from H = T: the incumbent, proposals or search
path can differ. Disagreement in full H is not automatically a codec defect.

Correct all affected prose/drafts/bitacora/handoff, retaining H-C arithmetic and
proposal-specific measured penalties. `BOTH_SEPARATELY` may remain an exploratory
recommendation, but is not a proved decomposition or a reason to exclude future
same-language improvements. A blanket statement that combining changes makes
attribution impossible should likewise become a design preference for separate
contrasts; controlled ablations can identify effects.

### R2 — P2: output-cut proximity does not measure proposal coverage

`analysis.py:471–475` reads `jobs/D2/*B0.json.info.cuts`, the returned archive's
cut tuple. It does not read every proposed/evaluated cut. The independently
reproduced 129/252 statistic therefore describes proximity to **returned cuts**.
`REPORT.md:139–142`'s "never proposes the rest" and `DECISION.md:40–43`'s
dominant-proposal-mechanism claim are unsupported. A proposed cut could have
been rejected on an earlier partition; returned cuts cannot distinguish this
from never evaluating it. Strict reachability of some supplied-cut path also
does not establish that the automatic greedy path could reach that state.

Relabel the statistic and remove causal rankings among proposal location,
accepted path, refinement and leaf construction. D2 supports that the specific
B0→B8 cap increase changed only one output, not a universal exclusion of resource
limitations under other searches. Draft A can remain a hypothesis to investigate;
its development gate must not claim to measure proposal coverage using returned
cuts. Do not rerun B to obtain new telemetry for this closure. The falsification
paragraph must not identify leaf/language as the sole cause of a failed cut change.

Scope correction: F06, F07 and F11 were sampled as D2 controls. They were not
examined as D3/D4 targets; F08–F10 were covered by D1 only. Replace claims that
all F06–F11 were outside D2–D4 or entirely unexamined.

### R3 — P2: the end-to-end report fails on unavailable records

`analysis.decision_quantities` dereferences completed-only fields before
`report.decision` can apply its incomplete/invalid gates. In-memory probes of
copies of the saved tables produce:

| Scenario | Actual result |
|---|---|
| Missing D2 control B8 result | `KeyError: 'B8_bits'` at line 443 |
| D3 timeout | `KeyError: 'cheapest_all'` at line 455 |
| D4 graph-limit translation of the portfolio winner | `KeyError: 'T'` in the loss decomposition |

See `incomplete_reporting_probe.json`. No retained job was changed. The 27 tests
pass but exercise the runner's unavailable records without sending those records
through the final analysis/decision pipeline. Protocol §§5,7,8 require explicit
unavailable reporting with fixed denominators, not a crash or zero gain.

Repair in an isolated correction copy. Add meaningful pipeline tests for missing,
timeout/error and graph-limit records, plus invalid deterministic/source evidence.
Run the reporting gate before success-only calculations or make those calculations
availability-aware. Preserve complete/partial denominators; do not convert
unavailable values to zero. Emit a clearly incomplete/invalid decision where
required, and retain the actual completed-run values. This defect did not bias
the present complete jobs or their audited estimates.

## Independent checks

`audit.py` / `audit.json`:

- Original 1,792 cases / 28,672 archive hashes and lengths checked against D1;
  raw inputs independently decoded and hashed.
- Accepted primary point estimate exactly reproduced: 0.005605234982532739.
- Job membership and identities match: D2 416, D3 176, D4 576, all `ok`.
- All 6,943 distinct diagnostic archives hashed and decoded against retained inputs.
- All 208 B0 deterministic comparisons pass; retained B-selected final bytes match.
  The only B8 output change and shorter-than-H witness is
  `stress-S02-4096-4001-ragged`.
- All 5,632 supplied subsets and 176 reference hashes checked. Independent
  cardinality-ordered reachability reproduces the minima and 22 restricted barriers.
- All 1,152 D4 lengths, signed terms and byte buckets checked; no T < H and all T > C.
- Launch tar/hash, recorded input/design hashes and owner/packet hashes verified.
  The only changed recorded adapters are the disclosed analysis.py and cli.py.
- Four protected trees and 60 protected files rechecked: only the permitted
  notebook README change; no unexpected differences.

Supervisor focused tests: **27 passed in 0.90 s**. Ruff on adapters and notebook
builder: clean. Notebook execution evidence was inspected, not rerun by the
supervisor; the retained two-directory guarded checks pass. The earlier unexplained
text difference remains disclosed, not diagnosed. Corrected notebook evidence is
required with the closure. No full campaign or new diagnostic job was launched.

## Decisions on disclosed deviations

The computation may retain attempt `a1`: inspection of `reporting_changes.diff`
confirms analysis additions after the original D1–D4 table functions and CLI
report/preservation changes; frozen job kernels and imported owners match. This
is a narrow retrospective exception to protocol §3, not permission to repair
compute code under a1. Give the corrected report a **separate immutable reporting
revision identity**, archive its executable/reporting closure and input manifest,
and explicitly retain its post-hoc status. Do not overwrite a1's identity,
reporting_revisions.json, original reports or measured records.

Post-hoc recommendation rules, private owner reuse, the owner-preservation
superset, repaired bytecode incident and differing bucket semantics are acceptable
as disclosed. The pre-existing single-engine failure remains a failure; it does
not identify new diagnostic duplicate engines. The dirty-tree ci-local exception
continues for this narrow closure. No unrelated guard cleanup is authorized.

No algorithm draft is approved for implementation or confirmation. Draft A also
needs a finite total budget and fully specified scheduling/ties before it becomes
an executable protocol. Review-only work now consists of R1–R3 corrections and a
reproducible reporting revision. Nothing was committed, pushed or published.
