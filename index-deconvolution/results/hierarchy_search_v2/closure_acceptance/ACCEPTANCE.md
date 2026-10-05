# HID-search-v2: supervisor acceptance with diagnostic erratum

Date: 2026-10-03. Supervisor: Codex.
Decision: **accepted** — complete study and corrected presentation; R1 and R2 closed.
Run: `search-confirm-v2-r1`.
Scientific freeze: `0f0a72ef2f9d9faac406b6d18594a45ba9dc71ff1d0331f38c6a3fead68e1d49`.
Scientific verdict: **inconclusive**, unchanged.

This decision supersedes the pending-acceptance status in the preserved developer
handoffs and the supervisor's initial `supervision/REVIEW.md`. It accepts the
frozen study together with the separately identified diagnostic median erratum
and the revised artifact-only notebook. It does not assert portfolio superiority,
causal identification, unfamiliar-family generalization, or a final general method.

## R1: accepted erratum; source repair approved for later integration

The accepted diagnostic supplement is
`../review_closure/diagnostic_median_erratum.json`, with readable companion
`DIAGNOSTIC_MEDIAN_ERRATUM.md`. Independent supervisor recomputation checked all
176 reference archives against their hashes, lengths, decoded input hashes and
saved rows, then recomputed the signed gaps and all eight cell medians. Exactly
five medians change; the values match the initial supervisor audit. Membership,
counts, means, median signs and the primary/contrast results are unchanged.

The source patch `R1_diagnostics_median_repair.patch` is approved, SHA-256
`e8da5c6ba731d4635295e867e04d3fe4d303adad42ffebeed18d744be1de96c5`.
It keeps aggregation in the existing owner and fixes even-count medians with
four focused regressions. Supervisor rerun: **4 passed, 21 deselected**.
The developer's retained pristine/patched full-suite logs report **385/389
passed**, with exactly those four additions. The documented mutation probe
fails the two tests that distinguish an upper-middle value from a median.

**Decision on adoption:** leave the active scientific source unchanged under
the existing freeze. Use the accepted erratum to interpret this historical run.
Apply the approved source patch when preparing the next source version, before
its freeze; it is not an amendment to the encoded rows or a new prospective run.
Do not regenerate historical diagnostics and silently replace their provenance.
The frozen diagnostics command still has the documented median defect; acceptance
of this study does not relabel that command as repaired.

## R2: presentation revision integrated

Applied only `R2_build_17_artifact_only.patch`, SHA-256
`37dc7f1f20a414a19de4a06ea51e82f881dd699f0a1252a2f14fec13ccc4d855`, to
`index-deconvolution/notebooks/build_17.py`. Regenerated notebook 17 and installed
the supervisor-executed version at its normal notebook path. Original builder
and executed notebook bytes are preserved beside this decision as `original_*`.

The notebook reads the explicitly identified saved case and all six arm archives,
checks their byte/input identities, reads telemetry, and displays the erratum's
medians with correction labels. It imports no inference or corpus owner.

Supervisor execution in the live checkout passed from both repository root and
notebook directory: **15 code cells, no errors, no unexecuted cells, no guard
refusals**. Only the five allowlisted hierarchy modules loaded. The primary
estimate, interval, inconclusive verdict and five contrasts match saved results.
All ten unchanged code cells retained identical text outputs. The original
notebook, used as a negative control, was refused at `hierarchy.search_v2`.
The builder and supervisor execution driver pass ruff.

Two setup limitations are retained rather than hidden: the sandbox first blocked
kernel startup (`kernel_probe.json`); after authorized execution outside that
sandbox, the first run's empty Matplotlib font cache attempted two font-discovery
subprocesses, which the guard blocked. Both notebook executions still completed,
but that guard check correctly failed. After cache initialization, the unchanged
harness passed in both directories. The cold-cache record is retained separately.

The builder is informational in the original freeze. Its new hash is explicitly
recorded in `integration_manifest.json`; its historical bytes remain in the
original snapshot and supervisor backup. Scientific source, protocol and config
identity remain unchanged, and the existing production freeze validator passes.

## Preservation, accounting and remaining boundaries

Before integration, independent rehashing found zero differences against the
developer's pre-correction record across nine protected trees, twelve named files,
62 freeze-named files and the recorded unrelated edits. After integration,
`preservation_after_integration.json` records the explicitly allowed presentation
and execution-ledger changes. The scientific run, both historical run trees,
active hierarchy package, protocol packet and notebook 16 remain unchanged.

The durable execution ledger records the developer's conservative 1,200-second
closure charge and a separate supervisor-review charge. Entries have unique
accounting IDs to avoid double charging. `resource_accounting.json` gives the
charges, derivation and cumulative totals; neither category nor overall limits
are increased or reset.

The pre-existing single-engine guard failure remains disclosed. Previous checks
are retained evidence, not a blanket waiver of repository guards for future work.
`make ci-local` was not run under the documented dirty-tree exception. No new
full encoding campaign or production report/verify rewrite was needed for this
closure; the original-source full verification remains preserved.

The shared `_nblib.py` path fallback and the historical HID-v1 quantile convention
are separate follow-up observations. Notebook 17 resolves its artifact root
explicitly and passed both working-directory tests. This review makes no finding
that the separately labeled historical quantiles are incorrect; those sources
and results were not changed.

This closes HID-search-v2 review. No next research phase was launched. Nothing
was committed, pushed or published by the supervisor.
