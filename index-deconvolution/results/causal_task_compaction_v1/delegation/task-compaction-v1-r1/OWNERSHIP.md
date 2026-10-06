# Ownership ticket and isolated integration contract

Approved when NEXT_CLAUDE.md is forwarded: additive implementation in an isolated revision of **index-deconvolution/src/deconvolution.py**, its existing concept owner. No new production engine package. Source discovery in this preparation found canonical_partition, induced_map and commutation_failures there; no task minimizer was found in index-deconvolution/src or its tests. Verify with graph tools if available, otherwise targeted source search, before implementing.

Proposed public API (use these names unless a pre-existing equivalent is discovered):

    minimal_task_partition(outputs, transitions) -> dict
    distinguishing_task_word(outputs, transitions, stages, x, y) -> list[int] | None

outputs is a nonempty list/tuple of nonnegative built-in integers, not bool. transitions is a nonempty list/tuple of nonempty list/tuple tables of the same length N; entries are built-in integer state indices 0<=v<N, not bool. No generator consumption, implicit coercion, partial tables or state deletion. Validate all inputs first and raise ValueError for malformed contracts. Action IDs are positional in this API; thin orchestration associates the accepted named interventions. The generic owner need not know biological models or word candidates.

Return at least alpha, stages (P0 through one terminal repeated vector), representatives, decoder and a complete ordered list of macro transition tables. Use canonical_partition and the existing induced-map/commutation functions for their owned concepts. The witness helper returns None iff x and y are equivalent under the supplied verified stable certificate, [] when current outputs differ, otherwise a shortest distinguishing action-index word with lexicographic ties. Reject invalid state indices/certificate shapes; document that certificate correctness is separately audited. Do not build a second minimizer in the run-local producer.

Own new tests at index-deconvolution/tests/test_task_compaction.py in the isolated revision. Deliver unapplied patches against active deconvolution.py and the new test path, plus the exact source snapshot used. Both patches must pass git apply --check at handoff; do not apply them to the active tree.

Run-local code owns only declarations, serialization, experiment orchestration, independent certificate auditing and reports. The audit's independent partition checks are an explicit verification exception, not a competing production owner. Add a run-local AST owner check for the two public API definitions: exactly one production definition in the declared isolated owner; fixtures/audit may not define copies under other names. Plant a duplicate in a disposable fixture tree to show the owner check fails. Identify frozen snapshots as snapshots, not active alternatives. Do not edit governance to hide a guard failure.

Use the existing CausalBool venv. Build a layout-preserving source snapshot under the new run (or develop in /tmp and then deliver it): mirror index-deconvolution/src and the adopted source-r2 study path at its original relative depth, plus the declared EGFR input at its relative path. Preserve any additional read-only dependency layout needed by existing tests, recording hashes and origins. No install, .pth changes, new environment, active sibling edits or implicit path fallbacks. Assert resolved module paths and hashes before tests and production. Disable bytecode and pytest cache.

Source files from causalbool, ca_deconvolution, bnet, reprogramming and adopted study.py stay byte-identical. Only the isolated deconvolution owner and the new isolated test file are implementation changes; run-local orchestration is new. Model tables and candidate alpha values come from the accepted study adapter, never private reimplementations (hand oracle fixtures excepted).

Before any development write, record active git status and hashes of active src/tests, notebook19 and build_19.py, governing files, all prior scientific result trees and this delegation packet. Exclude only the new output directory and declared temporary workspaces. Existing dirty work is not yours to revert. At handoff compare hashes; distinguish the snapshot's time coverage honestly. Preserve original histories, including the recent broad commit; no cleanup, staging, commit, push, upload or schedule.

The prior gap dependency has no role here. Do not apply its upstream patch or modify series-deconvolution. Active adoption of the task-compaction owner extension belongs to Codex's subsequent review.
