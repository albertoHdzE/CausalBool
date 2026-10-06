# Audit-only closure protocol

## Scope and authorization

This packet authorizes a new run-local audit revision r4 and the tests, evidence and
verification command necessary to close the supervisor's R1 and R2. It does not
authorize changes to the integrated implementation or any historical artifact.
Read NEXT_CLAUDE.md and the pinned review before work. Verify this packet's manifest,
the original 397-file, closure 153-file and finalization 248-file output manifests,
and the five active hashes before developing. Record git status and a preservation
baseline before writing. If an input has drifted, stop dependent work and identify it;
do not repair or overwrite another workstream.

Write exclusively into the new output directory named in NEXT_CLAUDE.md and /tmp.
Keep notebook 19, build_19.py, all old result trees, active sources/tests/docs/governance,
the sibling repository, vendor copies and unrelated uncommitted work unchanged.

## R1: required fixture validation

The declared fixture is FX1_identity with outputs [0,0,1,1] and its identity action
table [[0,1,2,3]]. Bind identity, outputs and transitions to the pinned declaration.
Validate all required fixture fields, exact types, shapes, ranges and nullability.
In particular fixture_id must equal the declared string, K must be a non-boolean
integer, and coarsening must be present and non-null with the required shape.
Reuse existing certificate arithmetic for validity and minimality; do not import the
producer or minimizer to produce expected answers.

Every rejected branch must append a field-specific INVALID issue. An absent fixture
file is INCOMPLETE; a present malformed record or missing required field is INVALID.
Declare one intended fixture, distinguish availability from actual certificate checks,
and do not label a silently skipped check complete. On valid data its validity and
minimality checks must still run. Retain the corruption case whose identity partition
is valid but not minimal; a schema-only rejection is not a replacement for that test.

## R2: integrity coverage and authority

The intended seal has 60 entries. Anchor its exact path set and hash values to an
independently pinned original authority, for example the original seal validated
against the SHA-256 in the separately pinned original output manifest. Log that
authority explicitly. Do not derive intended coverage from the candidate seal being
audited; do not rewrite the seal or any historical manifest.

Rules, in both normal and semantic-probe modes:

- Missing seal file or required seal entries: INCOMPLETE, intended coverage stays 60.
- Present malformed seal, malformed hash, undeclared path or contradictory identity:
  INVALID, with the offending field/path. Reject paths outside the declared exact set.
- Missing declared data file: INCOMPLETE. Wrong present bytes: INVALID in normal mode.
- Invalid evidence outranks missing evidence; record both. Withhold aggregates unless
  the whole audit is VALID_COMPLETE.
- Bypass mode may bypass changed data bytes for semantic corruption tests. It cannot
  bypass missing seal entries, schema checks, the authority's identity, or its path set.
  A candidate seal that substitutes a hash contrary to the pinned authority remains
  INVALID; semantic probes do not need to rewrite seals.

Normal mode must reject simultaneous changes to a data file and its candidate seal
hash, even if they agree with each other. A removed integrity check must never make
the evidence look more complete. Counts must distinguish intended entries, available
entries, hashes actually compared and mismatches; do not count skipped work as done.

## Implementation boundary and historical identities

Give r4 its own source identity. Reuse the pinned r3 expected-value authority and
existing scientific primitives. Do not create another runtime copy of the scientific
calculation. A separately identified wrapper or versioned audit is permitted, with
an explicit hash-checked import graph. Fix the two findings without duplicating the
encoder, model, minimizer or production pipeline.

Continue using the finalization historical_inputs snapshot as a read-only explicit
root. Never reseal current active bytes as old inputs. Every scientific import must
still resolve to the original isolated sources. Preserve r3, its commands and all
its evidence. Provide a NEW verification command for r4 that works from any working
directory and writes only to a fresh user-specified destination. Do not imply the
old r3 command contains these new checks.

## Finite verification plan

Declare the complete test matrix before running it. Reuse all 52 prior cases, adjusted
only for the new identity and explicit historical root; document intended diagnostic
wording changes. Add at least these targeted cases on copies:

1. fixture_id=123, wrong string, missing identity field, and coarsening=null;
2. missing fixture file, and the existing valid-but-not-minimal fixture;
3. empty seal map and one deleted seal entry (test both normal and bypass modes);
4. undeclared seal entry and malformed hash;
5. a modified sealed data file together with its newly matching candidate seal hash;
6. a missing seal entry together with malformed fixture evidence, proving INVALID
   precedence and continued independent checking;
7. pristine data, yielding exactly 60 intended seal entries and one completed fixture.

Demonstrate that the new regression cases catch the old r3 behaviors described in the
review, and that restoring each faulty branch is caught for its behavioral reason.
No need to add mutations unrelated to these two findings. Never mistake a historical
input mismatch from the current tree for catching the intended defect: use the
explicit historical root for semantic probes.

Rerun the existing 20 run-local tests and new tests. Run the 125 active tests and
documentation examples once to confirm preservation. Lint new/changed run-local code.
Do not run make ci-local; the known guard and vendor failures need no repair or new
waiver. No full-CI claim.

Run r4 on the saved data twice into fresh destinations. Deterministic reports must be
byte-identical between those executions. Compare all 24 scientific cell results,
aggregates, 3,276 candidate decisions and 85,504 transition-entry counts with r3;
separate new coverage counts/provenance from unchanged scientific values. Any
scientific discrepancy stops acceptance and is reported; no production regeneration.

## Handoff and budget

Deliver HANDOFF.md, DECISION.md, CHANGELOG.md, the revised inventory and matrix, source
and output manifests, old/new regression evidence, logs, the new historical verification
command, source identities, before/after preservation and git status, and complete
attempt/time ledgers. Preserve failed attempts. Record unchanged hashes of the five
accepted active paths and all three old output manifests at the end.

Recommendation can be V1_READY_FOR_SUPERVISOR only if every acceptance item passes;
otherwise CORRECTION_INCOMPLETE. Do not claim supervisor acceptance yourself.

New executor allowance: 1,800 seconds total: 300 preflight/declaration, 600 development,
600 testing/verification, 300 handoff/manifests. No transfers or uncharged final writes.
Separate Codex reserve: 300 seconds. Keep historical charges 1,985 + 1,440 + 1,607
seconds unchanged; do not edit old ledgers. If the budget prevents completion, stop
with accurate evidence rather than relaxing checks or launching a follow-up phase.
