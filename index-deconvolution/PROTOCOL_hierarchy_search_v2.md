# HID-search-v2: automatic discovery within the existing exact language

Date: 2026-10-02. Status: **delegation specification; implementation and prospective evaluation pending**.
Supervisor: Codex. Developer/executor: Claude Code. The developer returns evidence;
the supervisor decides acceptance. A negative scientific result can be accepted.

Read this document together with [the search specification](protocols/hierarchy_search_v2/SEARCH.md),
[the benchmark and analysis plan](protocols/hierarchy_search_v2/BENCHMARK.md),
[the acceptance checklist](protocols/hierarchy_search_v2/ACCEPTANCE.md), and
[the machine-readable contract](protocols/hierarchy_search_v2/study_contract.json).
The [kickoff prompt](KICKOFF_hierarchy_search_v2.md) delegates execution of this packet.
The annexes are normative. The contract records the same constants, not an
alternative design. Resolve any contradiction in writing **before generating
reserved cases**; do not silently choose the easier requirement.

## 1. Question, evidence and limits

The question is whether better automatic proposals, under a declared resource
policy, improve exact hierarchical descriptions enough to outperform the existing
baseline portfolio on fresh instances of the declared structured population.
This is an algorithm study using the existing ISD1/HID-v1 wire language; it is
not a new codec, a universal compression claim, or a causal-identification claim.

The accepted previous study has a negative primary result: saving
−0.0446156382 bits per input bit, 95% interval [−0.0536775270, −0.0358242637].
The `confirm-v1-r1` run is a correctness replay of `confirm-v1`, not an independent
replication. Exact reconstruction succeeded; aggregate superiority did not.
Neither result is an impossibility theorem about deconvolution.

The [post-hoc wall probe](bitacora/39_search_walls_and_first_input_only_probe.md)
found input-only consensus/dense-period/global-patch descriptions beating the
portfolio on all 16 previously inspected F06 transfer strings. On one string,
the complete archive fell from 50,728 to 16,992 bits, versus 25,936 for the
portfolio. That probe excludes the cost of rerunning legacy search and reused
observed data. It motivates this study; it does not establish generalization.
The earlier F12 witness uses supplied construction boundaries and remains a
metadata-assisted feasible description, never an automatic-search result.

We investigate four obstacles explicitly:

1. Corrupted first-block templates: estimate repeated phases by majority.
2. Missed periods and restricted corrections: dense period coverage and two
   legal placements of explicitly transmitted residual errors.
3. Mixed regimes and shifted boundaries: bounded, input-only segmentation.
4. Search versus representation cost: retain proposal telemetry and parse actual
   archive fields, without treating a free/no-overhead counterfactual as a codec.

The available evidence does not identify each obstacle's contribution to the
entire previous loss. The five cumulative comparisons below estimate changes to
an algorithm, including their computational cost; they are not pure causal
effects of independently varied mechanisms.

## 2. Authorized work and boundaries

Implement the specified six methods, development evaluation, prospective freeze,
fresh-instance benchmark, archive-based reporting, tests, notebook and handoff.
Proceed through these steps autonomously; no additional permission is required
to freeze or run this local, bounded study. Do not commit, push, publish, or alter
historical results. Do not promise or force a positive endpoint.

The wire format, decoder, baseline algorithms, original generators F01–F12,
legacy search and legacy FULL configuration stay unchanged. Use the existing
owners of model construction, serialization, exact schema cover, archive ledgers
and description lengths. In particular, do not create another
`src/description_lengths.py`, another deconvolution engine, or a second decoder.
The normative wire specification is
[WIRE_FORMAT.md](protocols/hierarchy_v1/WIRE_FORMAT.md).

Out of scope: new opcodes, entropy-coded leaves, learned codebooks, predictions
of unseen suffixes, BDM-based candidate ranking, adding search operators after
seeing reserved outcomes, and declaring unfamiliar-family generalization from
new seeds of familiar generators. Future work may address these separately.

## 3. Preserve provenance before editing the active package

The validator patch accepted in
[bitacora38](bitacora/38_hierarchy_validator_closure_accepted.md) is approved but
unapplied. Its SHA-256 is
`587d7bc0e0b9f598a80be99776655e3cc8d1df355cfa62884e7fbd8ee5809346`.
Its path is
`results/hierarchy_v1_supervision/confirm-v1-r1/validator_closure/validator_closure.patch`.

Before changing active sources:

1. Record the working-tree status without resetting or stashing other work.
   Verify the patch hash and the active r1 source hashes against freeze
   `f970efff16a2d08bf1dd22eee1386c164af5ba67b22137fefcf06cd182b27f5c`,
   accounting explicitly for the known pre-existing difference below.
2. Archive the r1 source/protocol dependency set and environment evidence outside
   both historical run directories. Suggested location:
   `results/hierarchy_v1_supervision/confirm-v1-r1/source_snapshot_confirm-v1-r1.tar`.
   Verify every member against the old freeze. Reuse a matching existing snapshot;
   never overwrite a conflicting artifact. Archive as a tar, not a duplicate
   source tree inside the repository that trips the single-engine guard.
3. Supply a read-only wrapper that extracts that snapshot to a temporary directory
   and can reproduce the historical numerical audit against saved archives.
   Old verification must not overwrite historical `verification.json`.
4. Apply the approved patch once. If already applied, verify its expected file
   changes; if neither the reviewed baseline nor patched state matches, stop
   that integration and report the exact conflict. Update current test inventory.
5. Record immutable before/after hashes of both old run trees. All new run data
   goes under `results/hierarchy_search_v2/`; all new code is a new source revision.

Do not relabel old rows with the new freeze. Source mismatch when using new
validators against an old freeze must remain visible; a labeled diagnostic
comparison is not production verification under that old identity.

**Known initial source difference, inspected for this delegation:** 17 of the 18
active frozen sources still match r1. `src/description_lengths.py` now has SHA-256
`b6fb6eaf1a81323bc81858cdadf22184315a7364602546275af0edb997018d36`, whereas r1 froze
`052786ca6f2e399cdf19a77743d5f4013f6856abf69a2034c4f944732775524e`.
The sole AST addition is `bdm_1d_trace`; all previous module statements/functions
are unchanged. It is existing work, not part of this assignment. Preserve the
active file and include its actual hash in the new freeze. Do not use the new
tracing function in inference. To construct the **historical** r1 snapshot, obtain
the old owner from
`/Users/alberto/Documents/projects/CausalBool_validator_closure/baseline/src/description_lengths.py`,
whose old hash has been verified, or another byte-identical retained source.
Never restore that old owner over the current working-tree file. See
[INITIAL_SOURCE_STATE.json](protocols/hierarchy_search_v2/INITIAL_SOURCE_STATE.json).
Recheck this recorded state before implementation; additional unexplained drift
requires investigation, not an automatic exception or source-hash override.

## 4. Implementation structure and ownership

Add a thin `hierarchy/search_v2.py` orchestrator plus focused proposal modules
(recommended `consensus.py` and `segmentation.py`). They take only bits and frozen
configuration. The legacy call remains `infer(bits, FULL)` from its existing owner.
Preserve hashes of `infer.py`, `candidates.py`, `model.py`, `wire.py`, `decode.py`,
`baselines.py`, and `corpus.py`, and of the shared scientific engines they invoke.
The approved patch changes orchestration/validation/reporting, not these owners.
Preservation here means no changes during this assignment to the recorded initial
state; the one pre-existing shared-owner addition in §3 is explicitly disclosed.

Extend the existing orchestration around an explicit immutable study specification
containing result root, roles, seed namespaces, case design, method registry,
configurations and analysis plan. Keep legacy behavior as the default study.
Avoid module-global monkeypatches to `SPLITS`, result paths or method lists in
production. Do not infer method dispatch solely from a `hid_` name prefix.
Extend shared validation, process isolation, resume and statistical helpers;
do not fork a second independent benchmark/validator/bootstrap implementation.
New study-specific adapters are appropriate. Preserve legacy fixture behavior.

The corpus/evaluation layer owns family labels, construction truth, seeds, paired
unit identity and metrics. Encoder workers receive only the bit string, method
configuration and resource policy. Neither new proposer imports the corpus or
loads old results. The runner may cache completed immutable rows for resume;
an encoder may not obtain a free incumbent from a previous run or another arm.

All six HID arms run independently, including a fresh legacy search inside each
extension arm. Shared work within one invocation is allowed and charged. Raw
fallback and exact decoding remain mandatory. Resource failures must be counted
in the population, not removed as inconvenient observations.

## 5. Execution sequence

1. **Preservation and integration:** perform §3; add the study registry and the
   approved validator closure. Run the inherited suite and lint.
2. **Implementation and fixtures:** implement SEARCH.md exactly; test tiny
   hand-authored/fixture-namespace data, determinism, nested candidates, limits,
   failure behavior and full CLI/report paths. Do not instantiate reserved keys.
3. **Observed-data development:** run the fixed 96-string pilot and the 1,632-string
   regression in BENCHMARK.md. No scientific parameter tuning is authorized in
   this packet. Fix coding defects and rerun affected development checks; retain
   all attempts. A loss or slow boundary search is a result, not grounds to
   silently replace the algorithm. Record unexpected design problems explicitly.
4. **Prefreeze gate:** write implementation map, source snapshot, resolved config,
   environment, test results, development results, resource accounting and a
   no-reserved-access declaration. Freeze the entire executable dependency
   closure, not just the old hardcoded list of source files.
5. **Prospective execution:** generate and score the declared confirmation,
   transfer and stress cases only after a successful freeze. Use one designated
   run, `search-confirm-v2-r1`, under the new result root. Resume the same immutable
   identity after interruption; never reuse an old run ID for changed sources.
6. **Analysis and verification:** derive every result from retained rows/bytes,
   produce ledgers and claim gates, run full verification, execute the lightweight
   saved-artifact notebook, and produce the handoff. A complete negative study
   follows this same path and is ready for supervisor review.

Suggested CLI contract, from the repository root with the project's environment
and `PYTHONPATH=index-deconvolution:src`:

```text
python -m hierarchy.cli selfcheck --study search-v2
python -m hierarchy.cli pilot --study search-v2 --run-id dev-search-v2-pilot
python -m hierarchy.cli regression --study search-v2 --run-id dev-search-v2-regression
python -m hierarchy.cli freeze --study search-v2 --run-id search-confirm-v2-r1
python -m hierarchy.cli benchmark --study search-v2 --run-id search-confirm-v2-r1 --split confirmation --resume
python -m hierarchy.cli benchmark --study search-v2 --run-id search-confirm-v2-r1 --split transfer --resume
python -m hierarchy.cli benchmark --study search-v2 --run-id search-confirm-v2-r1 --split stress --resume
python -m hierarchy.cli diagnostics --study search-v2 --run-id search-confirm-v2-r1
python -m hierarchy.cli report --study search-v2 --run-id search-confirm-v2-r1
python -m hierarchy.cli verify --study search-v2 --run-id search-confirm-v2-r1 --full
```

These are required interfaces to implement, not claims that commands already
exist. A run-ID collision is an error unless it is a verified resume of exactly
the same freeze. Do not delete it to get a clean-looking run.

## 6. Resource and amendment policy

Per encoder invocation: 30 seconds, 1 GiB, at most two concurrent workers, using
the existing watchdog policy. Apply the same policy to all HID arms and all nine
baselines. Retain the original deterministic legacy work cap. The extensions
receive explicit additional finite budgets from SEARCH.md. This is equal external
resource policy, **not equal search effort or equal candidate counts**.

Automated study execution allowance is 12 cumulative wall-clock hours: up to four
for development jobs, six for reserved jobs, two for diagnostics/verification.
Track durable cumulative elapsed time across resumes and fixes. This excludes
human coding time but includes repeated experimental jobs. Do not reset clocks,
increase workers or shorten the population to finish. If exhausted, preserve the
incomplete run and return a handoff explaining exactly what remains. The data
design is not contingent on fast cases finishing first.

Before reserved execution, a protocol-level problem requires a written amendment
and supervisor decision if it changes methods, populations, caps, seeds or claim
rules. Routine implementation choices and defect repairs that restore the
specified behavior need no approval. After reserved results are accessed, do not
tune this study. Freeze-changing bug fixes require an amendment and a new run
identity; a replay of already viewed strings adds no independent evidence.
Return such a problem for supervision instead of repeatedly creating new seeds
until an endpoint passes. Never suppress a discovered defect to protect a freeze.

## 7. Deliverables and interpretation

Produce the implementation, focused tests, updated current documentation,
`notebooks/17_hierarchy_search_v2.ipynb` and its builder, a dated bitacora entry,
the preserved-source audit wrapper, and `hierarchy/HANDOFF_SEARCH_V2.md`.
Save the implementation map, freeze, source snapshot, manifests, row files,
archives, per-stage telemetry, resource logs, development attempts, report,
diagnostics, independent arithmetic check and verification in the new result tree.

The final handoff must distinguish: engineering validity, completeness, the
primary scientific verdict, the five targeted contrasts, descriptive transfer,
parameter-shift stress, and post-hoc diagnostics. Do not promote a successful
F06 mechanism comparison into whole-population superiority. Do not equate useful
compression with true-generator identification, minimum description length over
all programs, or Kolmogorov complexity.

This stage succeeds operationally when it supplies a reproducible answer and a
clear diagnosis. It supports superiority only if the prespecified primary test
and all relevant evidence gates support that conclusion. The supervisor will
review both the implementation and evidence before accepting either claim.
