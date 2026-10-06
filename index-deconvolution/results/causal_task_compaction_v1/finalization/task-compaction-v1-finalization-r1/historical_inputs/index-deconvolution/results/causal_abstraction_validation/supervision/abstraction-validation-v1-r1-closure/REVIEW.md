# Causal state grouping — closure accepted and adopted

Decision: **ACCEPTED. R1 and R2 are closed.** The previously accepted V/D/X scientific evidence and its conclusions are unchanged. Track G remains DEFERRED_DEPENDENCY. No new scientific phase is authorized by this review.

## Review evidence

- Independently verified 104 hash entries before integration: original freeze, output and presentation manifests, permitted edits, five metadata hash references, and every closure-manifest artifact. No mismatch.
- The five previously unresolved keys are draft_protocol_sha256 in freeze.json and core_original_sha256, packet_sha256, review_sha256, handoff_sha256 in output_manifest.json. All map to explicit files and all match. This closes the manifest uncertainty.
- All four patches passed git apply --check against the pre-adoption sources. Reviewed both repaired branches and their targeted mutation logs: restoring the original singleton rule changes INCOMPLETE to NO-HOLDOUT; restoring the representative branch hides a structural failure. These failures do not depend on a missing new field.
- Independently reran the isolated suite: 73 passed. After adoption, reran the active core suites plus the separately identified corrected study tests: 73 passed in 1.22 s. Ruff passed on all four adopted Python sources; git diff --check passed on the two active edits.
- Independently enumerated 93 small complete-input cases, covering all four complete-evidence coarse labels. All old fields matched exactly; new availability counts were zero. Claude's separate seeded comparison covers 20,000 complete inputs. The saved D maps were not reconstructed, and no production job was run. This is sufficient here because code inspection shows that the behavioral changes are confined to absent-record paths; complete-record branches retain their old calculations.
- The separate valid commutation test preserves failure index 2. All three malformed-domain cases now raise ValueError before evaluating the supplied macro function.

## Adoption and historical reproduction

Applied only Claude's R2 core and active-test patches to index-deconvolution/src/deconvolution.py and index-deconvolution/tests/test_abstraction.py. Their bytes exactly match the reviewed corrected sources.

Adopted R1 as a separate source revision at ../../abstraction-validation-v1-r1-source-r2/ with study.py, test_study.py and the original fixtures.json. The two corrected sources match Claude's artifacts byte for byte. Its directory depth preserves the original model-owner path resolution. No historical patch was applied in place.

adoption.json identifies every adopted file and preserves the two pre-adoption core/test files as .frozen.txt snapshots. This is a new source identity, not a retrospective amendment to the original scientific freeze. The old freeze still names the old core/test hashes, so checking it directly against the newly corrected active tree will correctly report those two differences. Historical reproduction must restore the recorded snapshots in an isolated copy. Do not update the old freeze to conceal the adoption.

All 74 non-bytecode files in the original run and delivered closure remained byte-identical during integration. The historical HANDOFF and Claude's closure retain their original status text; this review supersedes that pending status. review_check.py and review_check.json record the pre-adoption verification, and therefore the checker expects pre-adoption sources when rerun. integrate.py is a one-time adoption record, not a repeatable runner.

## Scope and interpretation

Use causal state grouping in new prose; state compaction denotes reduced state distinctions, not compressed archive length. Historical identifiers remain intact. FULL denotes the specified validity condition; the 11 constant-dynamics rows retain that label. Their limited usefulness is descriptive and does not invalidate the check. The post-hoc characterisation and supplemental recomputation remain labelled as such.

This closes the correction phase. It does not establish a general causal deconvolution method, compression improvement, fractal structure or biological interpretation. No remaining finding requires another Claude correction round. The unrelated historical repository guard failure and omitted make ci-local remain disclosed; no claim is made that every repository check passes.

No commits, pushes, publication, recurring tasks, sibling changes or production V/D/X/G jobs. Executor charge: 268/600 seconds. Supervisor review and adoption charged conservatively at 180/180 seconds; total correction charge 448/780 seconds. Review started 2026-10-05 17:27:22 UTC and finished within that reserve.
