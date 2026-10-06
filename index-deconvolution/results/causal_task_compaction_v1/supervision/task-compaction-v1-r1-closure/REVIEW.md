# Closure review — task compaction v1

Decision: PARTIALLY_ACCEPTED. R2 and portable fixture packaging are accepted for integration. The complete saved scientific evidence reproduces; no numerical discrepancy found. R1 requires one bounded follow-up before claiming a robust audit. NO_NEW_STUDY_JUSTIFIED stands.

## Verified

Codex ran REGENERATE.sh into /tmp/task_compaction_review_r2_20261005: 125 owner/regression tests plus 12 run-local tests passed, all 23 declared matrix cases behaved as specified, and audit.json and matrix.json reproduce byte for byte. All 397 original output-manifest entries and all 153 closure entries match SHA-256 and length. Replacement patches pass the regeneration check. The reviewed replay validator checks all tables and the entire word before replay, rejecting bool and unsupported containers. The fixture no longer depends on the task-compaction run path.

These are scoped checks. Codex did not rehash the entire 110,263-file preservation snapshot or run full CI. Existing source/tests were not modified. A review setup read of root AGENTS.md found no on-disk file; user-supplied AGENTS instructions were followed, and graph tools were unavailable.

## R1 residual — authoritative field validation

Three disposable-copy probes all incorrectly return exit 0, VALID_COMPLETE, zero invalid and zero missing:

1. candidate_bool: cell_00 candidate 0 decodable=true changed to integer 1, and K_candidate=256 changed to float 256.0.
2. candidate_metadata: the same row cell_id changed to 999, and embedded candidate.g changed to invented. Its candidate_id and record_id stay intact.
3. summary_both_bool: identity.task_sufficient changed from true to integer 1 in BOTH the cell summary and summary.json. Exact comparison between these copies does not validate their types against the independently computed result.

Probe script and JSON/logs are beside this review. Probes use --bypass-integrity deliberately: this isolates semantic validation instead of allowing the unchanged seal to catch all mutations. Normal-mode hash checks remain required. There is no evidence these corruptions occur in the real dataset.

Required repair: a typed field inventory for every consumed scientific field, including nested summaries and candidate identity/declaration binding. Validate against independent computed expectations, not just two saved copies. Sharing frozen scientific calculations is allowed; inheriting their permissive equality is not. A separately identified r3 audit may wrap schema and metadata checks or extract the independently recomputed expected record for strict comparison, without importing the producer/minimizer. No duplicate solver is needed.

The strict aggregate-withholding rule is accepted. INVALID precedence and independent available checks remain mandatory.

## Literature and documentation

The established congruence/refinement interpretation and pairwise observability mapping are appropriate. The all-action GFB bound follows directly when the observable factors through the aggregate. None establishes research novelty for this implementation or its packaging. Replace “the novelty is the contract and its packaging” with a factual contribution statement, without a novelty claim.

Correct two prose overstatements in new documentation: approximation need not replace universal quantification with a probability measure (a worst-case tolerance is another possible future contract); no such contract is implemented here. Memory is not just Q*N: all refinement stages are retained, adding O(R*N) entries, with R=O(N), hence O(Q*N+N^2) worst-case storage for this implementation. Faster refinement variants discussed by Knuutila are not implemented.

## Integration hazards addressed by the next packet

Original freeze inputs include active deconvolution.py AND GOVERNANCE/CORE.md. Adoption changes their identities. Preserve exact original input bytes in a separately manifested historical snapshot BEFORE integration; historical evidence verification must use explicitly named frozen identities, never silently ignore current-tree differences or rewrite the old freeze.

The closure's proposed blanket edit to root MANIFEST.tsv/pytest.ini is not warranted: check_test_manifest.sh scans root tests/, while these tests live in index-deconvolution/tests/. Use an explicit scoped test command; do not widen global collection or classify a JSON fixture as a Python test.

Codex also ran imp-prices/tests/test_vendor_parity.py on the unmodified active tree: both causalbool.py and deconvolution.py already FAIL byte parity. This pre-existing integration limitation was absent from the handoff. Re-run and disclose it during adoption; do not modify imp-prices or silently waive/repair that independent workstream. The scoped adoption can proceed under this recorded limitation; full repository CI is not claimed.

## Next decision

One bounded finalization round is authorized by forwarding the new packet: repair run-local audit validation, then conditionally apply the already reviewed three core/test/fixture patches and add documentation after the explicit gates pass. No production rerun or new research phase. Final supervisor sign-off remains after the handoff, and integration does not imply a release or a final general causal theory.
