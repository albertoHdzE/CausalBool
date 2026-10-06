# Supervisor review: task-compaction v1 final audit closure

Decision: **ACCEPTED. Exact known-model state-compaction v1 is complete within its declared contract.**

Reviewed closure: `finalization_review_closure/task-compaction-v1-finalization-r1/`.
Accepted audit revision: r4, SHA-256 `f2b034984a89380fa6fc33f6109f5168557bba2d7ae94488dd13dc3bc635ec4a`.
This decision supersedes the pending audit status in the preceding supervisor review. It does not rewrite any historical handoff or manifest. The five previously accepted active files remain adopted without further changes.

## Findings closed

**R1 closed.** Fixture identity, outputs and transition table are bound type-exactly to FX1's declaration. Required fields have explicit rejection paths; missing files remain INCOMPLETE. Reports distinguish one intended fixture, availability, schema validity and the two completed certificate checks. The independent valid-but-nonminimal case still reaches the certificate and yields validity true, minimality false.

**R2 closed.** The original 60-entry seal is pinned independently and cross-checked against the separately pinned original output manifest. Candidate seals cannot choose their own intended coverage or substitute their own data identities. Missing entries are INCOMPLETE; malformed, undeclared or contradictory entries are INVALID. Semantic bypass permits changed data bytes only. INVALID takes precedence over INCOMPLETE and incomplete audits withhold aggregates.

The wrapper reuses pinned r3 and its scientific dependencies. It changes the two reviewed checks and revision reporting, without duplicating the scientific calculation. Existing r3 evidence and commands retain their original meaning.

## Reproduced verification

- `VERIFY_R4.sh` run from `/` into a fresh destination: VALID_COMPLETE, 60 intended seal entries, 60 agreeing entries, 60 compared hashes, zero mismatches, two completed fixture certificate checks; report byte-identical to the saved r4 report; 29 audit tests pass.
- Full declared matrix: 73/73 cases satisfy their required outcomes. Six old-r3 false acceptances reproduced. Six fault restorations across seven runs caught for their intended reasons, without tracebacks.
- Active regression suite: 125 tests pass; documentation examples pass.
- Scoped ruff and `git diff --check` pass.
- Independently re-hashed 397 + 153 + 248 + 112 = 910 output-manifest entries, checking byte lengths too; all match. Five active hashes match the accepted identities. Packet, freeze, isolated-source and 21-file historical snapshot checks pass.
- Independent recursive type-and-value comparison against the saved r3 report: every scientific section and every shared count agrees, including 24 cells, 3,276 candidate decisions and 85,504 transition entries.

`matrix.json`, `historical_audit.json`, `verification.json` and `preflight.json` retain the reproduced evidence. `verification.json` includes an independent typed comparison rather than relying only on the producer's comparison script.

## Preservation, budget and limits

The executor's 110,713-file before/after preservation scan reports no differences; its snapshots, git-status records and failed attempts were reviewed. This supervisor independently re-hashed the scoped manifests and active files, but did not repeat that entire repository-wide scan. No active or historical artifact was edited during review. No scientific study was rerun.

Executor charge: 711/1,800 seconds, including the declared allowance for final writes. Historical charges remain unchanged. The supervisor ledger records this review separately within its 300-second reserve.

Full CI, repository guards and vendor parity were not rerun. Their previously disclosed failures remain open repository matters; this is component acceptance, not an assertion that the whole repository passes CI. The mutation runner's reported source identity is the original source identity under which it executes the altered text; mutant IDs and retained mutation definitions identify those negative tests. This disclosed test-harness detail does not affect the genuine r4 identity or saved-data audit.

## Scientific conclusion and next action

The accepted component computes the coarsest state grouping preserving the declared output under every finite word of the declared actions in a fully specified finite deterministic model. This is an established mathematical construction with an exact implementation and checked evidence. It is not a new general causal-deconvolution theory, a method for identifying unknown causal models, an archive-compression gain, or a biological claim about EGFR.

The saved conclusions stand: three of twelve intervention cells admit reduction, and nine require all states. The non-contiguous EGFR task grouping demonstrates a limitation of the earlier contiguous candidate family within the supplied model and task.

**No correction delegation remains. No new study is justified by this closure.** Keep the integrated component and use `VERIFY_R4.sh` for the saved historical evidence. A future research phase needs a concrete new application or unresolved hypothesis and its own declared evidence target. There is no authorization here to commit, push, publish, schedule work, repair unrelated guards, or change historical artifacts.
