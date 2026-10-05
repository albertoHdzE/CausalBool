# Codex review: HID-search-v3a

Date: 2026-10-04. **Accepted as a valid, complete negative experiment.**
The k=4 treatment is **not adopted**. Retain the accepted search-v2 k=1 method.
This acceptance is recorded separately; the executor's original handoff and
decision retain their historical “not yet accepted” status without modification.

Run: `search-confirm-v3a-r1`.
Freeze: `05dd799d154e5e53a36bac7dca49f0438ca27b58b2df94c045eeca2fa6dd69e5`.

## Scientific decision

The fixed six-cell primary comparison is HARMFUL: saving of k=4 relative to k=1
is **-0.0063290600504822 bits per input bit**, with 99% interval
**[-0.00833260223670385, -0.004177554260442437]**. All 120 paired units are present.
This supports rejecting this treatment under the frozen scheduling and caps.
It neither rejects multilevel abstraction nor establishes a cause of the loss.
The association with shared length-budget exhaustion is descriptive. The
accepted search-v2 primary verdict remains inconclusive.

No new cap-aware, multilevel, TILE, combined, or confirmation experiment is
authorized by this review. No source rollback or application of additional
patches is needed to interpret the result. The implemented experimental arm may
remain available for reproducibility without becoming the accepted default.

## Supervisor verification

`audit_review.py` reads saved evidence, performs no encoding or generation, and
writes only its adjacent `audit_review.json`. Its completed run checked:

- Freeze identity; all 38 executable-source, 16 protocol and 17 prefreeze-evidence
  hashes; the snapshot hash and all 94 members against their declared hashes.
- Exact intended population and method membership: 256 strings, 2,816 encoder
  rows and 256 derived portfolio rows. Every archive hash, length, input identity
  and successful status was checked. All 2,653 distinct archives were decoded;
  duplicate archive bytes reuse the decoded result. Each portfolio selection
  and archive was reconstructed from the nine saved constituent archives.
- All 512 HID sidecar hashes and trace/telemetry consistency using the frozen
  trace validator. No inference was invoked.
- Primary paired arithmetic and the seeded, stratified bootstrap in a separate
  implementation. The point and both interval endpoints match the saved result.
- The retained development k=1 archives and deterministic fields against all
  1,792 accepted v2 records, using the read-only compatibility routine. All match.
- Development fingerprints reconstructed by substituting the recorded old
  `prospective.py` hash; all other source/config hashes agree. Recorded development
  row fingerprints match these reconstructions.
- Notebook 20's retained guarded-run evidence, current harness/builder hashes,
  delivered notebook equality to the saved notebook-directory execution, and
  executed/error-free code cells in both saved executions. No kernel was rerun.
- All 3,497 files under the frozen run are byte-identical before and after this
  audit. Notebook 19 is also unchanged by the review.

The independent arithmetic uses the same specified NumPy RNG and percentile
convention. Decoding, trace consistency and compatibility intentionally reuse
their respective reviewed owners; this is not an independent reimplementation
of those components. The recorded full suite (334 tests), description-length
suite (136 tests), lint and watchdog fixtures were reviewed, not rerun. No new
failure-path assurance beyond those retained tests is claimed.

A repository-wide `git diff --check` also reported whitespace in unrelated
`luminal-challenge/report/report.tex` and `papers/method/code/scalability_resource_envelope/`
edits. These were left untouched. The new review/design documents passed their
own whitespace check; no claim of a clean repository-wide diff is made.

## Disclosures and interpretations accepted

1. The user confirms the concurrent notebook-19/builder changes. They belong to
   the separate BDM workstream, outside the executable closure; preserving them
   was correct. The reviewed notebook-19 hash is recorded in `audit_review.json`.
2. The preflight adapter changed after development but before freezing. The
   fingerprint reconstruction establishes that it is the only closure-file
   difference. Development execution does not import this prospective adapter;
   the search/worker/configuration identities remained unchanged. The narrower
   claim about the edit's internal preflight-only contents rests on the executor's
   disclosure; reconstruction of a file hash does not recover its old source.
3. The disclosed pre-existing single-engine guard failures remain failures;
   this acceptance does not waive them repository-wide or assert that all CI
   checks passed. The scoped dirty-tree `make ci-local` exception remains as
   documented in the protocol and handoff.
4. The retained failed first notebook execution was a presentation correction,
   not a new encoder/search result. Successful run2 supplies the final notebook.
5. `ACCEPTANCE.md` section 2 contains one stale “Notebook 19” reference in its
   artifact-only instruction. The same section's required deliverables, the
   kickoff and the rest of the packet identify notebook 20. The artifact-only
   requirement is applied to study notebook 20, not to the user's BDM notebook.
6. Background checkpointed queues and role-boundary progression introduced no
   observed interruption, missing record, tuning or source-identity change. The
   retained evidence supports completion of the frozen design.

## Resource accounting

Closed controller spans supersede the handoff's mid-report totals:
development 2,939.749470 s; prospective 1,694.504343 s;
report/verification 747.088553 s; executor total 5,381.342366 s.

The supervisor audit took 184.804234 s. Charge a conservative **300 s** for this
supervisory automated review, including ancillary inspection, against its reserved
300 s. Record that charge here without rewriting the frozen execution ledger.
Combined charged total: **5,681.342366 / 28,800 s**;
report/verification including supervisor: **1,047.088553 / 3,600 s**.
The separate assessment/design discussion of notebook 19 is not another study
job. No historical charge or overrun has been removed or reassigned.

## Next development direction

See `protocols/hierarchy_multilevel/CONCEPT_REVIEW.md`. Section 3b supports
investigating symbol order and phrase structure across levels. Complete archive
cost, reversible dictionaries/tails, existing grammar baselines, and search
resource allocation must govern a future test. Compression or hierarchical
representation alone does not establish causal identification. Implementation
remains for Claude Code under a separately finalized protocol.
