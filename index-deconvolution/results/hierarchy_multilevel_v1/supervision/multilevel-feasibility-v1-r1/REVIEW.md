# Codex review — multilevel-feasibility-v1-r1

Date: 2026-10-04. **ACCEPTED as a completed exposed-data feasibility study,
with disclosed procedural deviations. No production adoption.**

The engineering evidence supports VALID_COMPLETE and the exploratory label
NO_RETAINED_GAIN. This acceptance does not turn the study into a confirmation
experiment or establish that abstraction, hierarchy or causal structure is absent.
The executor's original handoff and all study files remain unchanged; this separate
record supersedes its pending supervisor status.

## Evidence checked

`audit_review.py` and `audit_review.json` retain the supervisor's read-only check.
All 19 checks passed, with zero reported problems. No benchmark jobs were launched.

- Implementation lock SHA-256:
  `4d1908ab4ec81334bb626bbe025d8dce134e8b4d9df124ce2fba84be8bbcf003`.
  All 74 locked members match current files and snapshot contents; the 63-file
  executable closure is included. Snapshot identity matches the lock.
- Independently compared the 96 new A0 records to their hashed original rows,
  including every contract reproduction field and recursively removing only
  timing keys ending in `wall_s`.
- Re-executed the separately implemented arithmetic audit after reading its source:
  1,248 archive reads, 1,344 decodes, no errors. It uses the existing independent
  decoder, imports no reporting algorithm and launches no encoder. All contrasts,
  string/cell sign counts and denominators match. This is a rerun of the executor's
  independent audit, supplemented by the supervisor's own comparisons, not a claim
  that an entirely new decoder was written.
- Independently checked all 288 composite hashes against A0 and all saved trace
  hashes. Every augmentation status is `ok`. A3 has 4,244 evaluated views,
  1,840 saturated-branch records and 60 single-symbol-branch records. No work cap
  prevented a requested proposal. The median best-proposal excess is recomputed
  from traces, rather than copied from the handoff.
- Re-hashed all four old result trees (95,471 files), hierarchy sources, shared
  owners, protected notebooks, bitacora and notebook README against the original
  preservation records. All match. The complete current study tree is identical
  before and after the supervisor audit.
- Reviewed search construction, paid dictionary representation, exact tails,
  duplicate handling, strict improvement selection and branch stops against the
  protocol. Reviewed the saved 50-test success and notebook guard evidence;
  notebook builder/driver hashes match. The notebook and test suite were not
  rerun in this review. The guard revision narrows a textual false-positive check;
  it does not remove the underlying execution guard.

## Deviations and outstanding repository checks

The four pre-lock benchmark smoke inputs and fixture declaration written after
the first suite run violate the intended sequencing. They are accepted here as
documented exceptions for an explicitly exposed-data development study. The
no-subsequent-algorithm-tuning statement is executor testimony, not independently
recoverable source history. Neither exception permits calling this preregistered
or held-out evidence. Future phases must declare fixtures first and keep benchmark
execution behind the lock.

The hierarchy test failure is explained by its direct use of the now-frozen real
v3a run while asserting that no freeze exists. The failing assertion is present
in the unchanged owner source. Repair should later use an isolated unfrozen
fixture, under separate ownership authorization; do not alter old frozen sources
to make this phase green. The existing single-engine failures remain failures.
The scoped dirty-tree ci-local exception applies. Acceptance does not mean every
repository check passed.

The notebook driver's presentation revision is accepted with its separate hash
and retained failed attempt. No measurement correction or study rerun is required.

## Interpretation and next decision

All three composites equal A0 on every case. Positive comparison to pair_grammar
and negative comparison to the portfolio are inherited A0 performance, not gains
from abstraction. The proposal-to-A0 median excess describes this finite candidate
vocabulary and serializer, not an intrinsic cost of multilevel descriptions.

**Stop M2 as presently specified for improving archive length on these cases.**
This statement is conditional on retaining this proposal vocabulary, branch
pruning, patch limits and candidate construction. A3 exhausted that authorized
search here; choosing a subset or reordering independent candidates cannot uncover
a shorter archive that this search already evaluated and rejected. This is not
an exhaustive search of all mathematical views: saturation and single-symbol
descendants were deliberately pruned. Scheduling may reduce added compute, and
different representations or pruning rules would be new experiments.

The next defensible research question is whether dictionary entries can share
paid structure: for example, represent an internally periodic word using a repeat,
or related entries using a shared base plus exact exceptions, using the existing
wire grammar where possible. Periodicity in a dictionary is a motivation, not a
demonstrated net saving. A separate protocol must specify the finite candidate
set, full shared-DAG cost, baseline and ablations, fixtures declared before tests,
resource caps and fresh evaluation before making a generalization claim. This
review does not launch or authorize that later experiment.

The programme remains unfinished as a causal method: multi-width repetition,
grammar reuse and nested descriptions are structural evidence. Causal recovery
and scale-dependent self-similarity require separately defined targets and tests.
Keep accepted k=1 as the comparison incumbent.

## Accounting and preservation

Conservatively charge 300 seconds to supervisor report/verification, including
this review, audit construction/execution and the executor's disclosed uncharged
final one-line handoff edit. The audit subprocess used about 7.32 seconds; that
is included in the charge, not the whole review charge.

From the executor's recorded event timestamps: development 1,307.381935 s,
benchmark 78.511615 s, executor reporting 367.620891 s. With this supervisor
charge: reporting 667.620891 / 3,600 s; overall 2,053.514441 / 21,600 s.
The original ledger is preserved. No later-phase budget is created here.

Only this supervision directory is added by Codex. No implementation changes,
commits, pushes, publication, schedules or benchmark reruns.
