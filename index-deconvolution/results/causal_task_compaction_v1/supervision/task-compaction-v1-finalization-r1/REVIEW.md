# Finalization review — 2026-10-05

Decision: **PARTIALLY_ACCEPTED; audit closure required.** The integrated owner, portable
fixture, owner tests, documentation and governance entry are accepted within the exact
known-model state-compaction v1 contract. Leave those five active paths in place.
The saved scientific conclusions remain supported. Final evidence-tool acceptance is
withheld for the two reproducible findings below. No new study is justified.

## Independent checks

- RUN_ACTIVE_TESTS.sh: 125 tests pass; executable documentation examples pass.
- VERIFY_HISTORICAL.sh: 21 historical inputs match the original freeze; saved-data
  audit VALID_COMPLETE, zero invalid/missing/skipped; audit.json reproduces byte for
  byte; 20 run-local tests pass.
- Original 397, closure 153 and finalization 248 manifested files all match SHA-256
  and byte counts. All five active paths match logs/active_after.txt.
- The complete 52-case post-adoption matrix was independently rerun; its completion
  result is recorded in verification.json and matrix.log alongside this review.
- The active diff adds the reviewed compaction functions and one ownership row.
  Scientific expectations in r3 have one runtime authority; the independently checked
  table/certificate logic remains pinned to the historical implementation.

No scientific production was rerun. Full CI, vendor parity, the repository guards and
the entire 110,434-file preservation scan were not independently rerun this review.
The submitted preservation diff and guard comparison were read; their known failures
remain limitations, not passing checks.

## R1 — FX1 validation can silently skip or omit required checks

In audit_r3.check_fixture, `type(fx.get("fixture_id")) is str` can make `ok` false
without appending an issue. On a copy, setting fixture_id to 123 returns exit 0 and
VALID_COMPLETE, with no fixture_FX1 result at all. A wrong string `NOT_FX1` also passes.
Setting required coarsening to null passes because the inherited schema and certificate
allow omission of that check. All three probes used the explicit semantic-probe
integrity bypass and left the historical data untouched.

Required correction: validate the declared FX1 identity and model, every required
fixture field and its nullability; record an issue on every rejected branch. Count
the intended fixture and the completed checks explicitly. Keep scientific certificate
verification independent, including the validity-versus-minimality corruption test.

## R2 — integrity coverage is taken from the supplied seal itself

R2.check_seal, reused by r3, accepts a supplied empty sha256 map. On a copy, replacing
that map with {} returns exit 0, VALID_COMPLETE, and sealed=0 in NORMAL mode.
Removing only fixtures/FX1_identity.json likewise returns VALID_COMPLETE, sealed=59.
Thus the audit can claim completeness after dropping required integrity checks. The
external output manifest catches these changed bytes when separately checked, but
the audit's own completeness claim and declared seal-entry semantics are incorrect.

Required correction: derive the intended seal set and original hash values from an
independently pinned historical authority, not the candidate seal. Missing required
entries mean INCOMPLETE; malformed, extra or contradictory entries mean INVALID.
The semantic bypass may bypass byte mismatches for deliberate probes, never missing
coverage or schema validation. Normal mode must reject a changed file accompanied by
a newly matching candidate seal hash. Preserve the original freeze and manifests.

## Interpretation and nonblocking notes

The 24-cell conclusions have not changed: INTERVENTION has 3 reductions and 9 cases
requiring all states; AUTO has 10 reductions. This concerns the smallest exact grouping
for specified outputs and actions in a supplied finite model, not archive savings or
recovery of unknown causal mechanisms. Established theory is being implemented and
validated, not claimed as a new general causal theory.

FX3 is the correct two-step example; the earlier packet's FX2 wording was wrong. The
scoped test invocation is accepted. Historical snapshot verification correctly preserves
the old identities after adopting the new owner and governance bytes. Current-tree
historical checking must continue to disclose those two expected mismatches.

Use the ledger's conservative 1,607-second executor charge, not the message's roughly
1,410 seconds. Both are within 3,600 seconds. The existing nine single-engine failures
and two vendor-parity failures remain unresolved; full CI is not claimed.

The next packet is a bounded audit-only closure. Do not revert or alter the accepted
active implementation, launch another scientific phase, or resubmit the same evidence
without addressing R1 and R2.
