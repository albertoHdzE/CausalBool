# Delegated protocol: hierarchical index descriptions, version 1

Date: 2026-10-01. Status: **authorised implementation specification; no positive scientific result presumed**.

Scientific owner and final reviewer: the supervising Codex session. Implementing
developer: Claude Code. The user will return the developer's handoff for review.
This document and its annexes operationalise the accepted assessment in
`bitacora/33_generalization_scientific_review.md`.

## 0. Contract, authority, and completion

Implement, test, execute, and report the complete bounded study below. Do not stop
after a plan, after an encoder without inference, or after a notebook with selected
examples. Work through all phases without routine permission questions. There is
no authorisation to spend money, launch cloud jobs, push, merge, publish, or alter
sibling repositories. Do not commit unless the user separately requests it.

There are two independent outcomes:

1. **Engineering:** a lossless, deterministic, bounded implementation, executable
   benchmark, reproducible artefacts, and a complete review packet.
2. **Science:** evidence supporting, narrowing, rejecting, or leaving inconclusive
   the predefined advantage. A negative or inconclusive result is a valid completed
   study. A fabricated advantage, omitted failure, or uncharged field is not.

The claim under test is economical **description discovery** on the registered
families. Do not claim that the method computes Kolmogorov complexity, recovers a
unique generating mechanism, forecasts unseen suffixes, or establishes causality.
Prediction, causal identification, arbitrary new operators, real-world datasets,
and a manuscript submission are outside version 1.

Read in this order:

1. Repository `CLAUDE.md`, applicable `AGENTS.md`, `GOVERNANCE/CORE.md`,
   `GOVERNANCE/GLOSSARY.md` §1d–1e, and `GOVERNANCE/DESCRIPTION_LENGTHS.md`.
2. Bitacoras 32 and 33, notebook 15 and `notebooks/build_15.py`.
3. This file and all three normative annexes:
   - [wire format](protocols/hierarchy_v1/WIRE_FORMAT.md);
   - [benchmark and statistical plan](protocols/hierarchy_v1/BENCHMARK.md);
   - [acceptance and review checklist](protocols/hierarchy_v1/ACCEPTANCE.md).

For this stage, this specific protocol supersedes generic research suggestions in
`TRANSFERENCE.md`, `PROTOCOL_order_discovery.md`, and bitacora 33. It does not
redefine sumandos or change variants A–E. Statistical **comparison codecs** are
authorised here as actual decodable baselines, labelled as such; do not redefine
the project's algorithmic description-length variants using entropy or insert an
entropy estimate into our model-selection objective. Do not weaken existing tests
to accommodate the distinction.

Use graph MCP discovery first if available; otherwise record its absence and use
direct inspection. Do not install a plugin to satisfy this preference. Do not
start unrelated screen-identification, finance, or Boolean-network projects.

## 1. Scientific commitments

### 1.1 Object and observable

The input is a finite binary sequence `x`, including the empty sequence. Its
positions are zero-based from left to right. Address-coordinate bit j has weight
`2**j` (LSB coordinate indexing). Packing into bytes is MSB-first, as specified in
the wire annex. These are distinct conventions; test their conversion explicitly.

The main output is a byte archive that independently decodes to **exactly x**,
plus a report describing its inferred rules and search effort. All performance
claims concern the length of that archive, including headers and padding.

The proposed method is called **hierarchical index description v1 (HID-v1)**.
It is a code and search procedure. `archive_bits` is a measured code length under
that fixed language, not K, CTM, BDM, D_schema, or an entropy statistic.

### 1.2 Hierarchy and scope of inference

The representation is a DAG of reusable rules. Concatenation edges are ordered;
dictionary membership alone cannot supply sequence order. Back references transmit
reuse. Arithmetic-progression and schema nodes describe occurrence sets. A separate
patch node flips explicitly encoded positions. Sumandos remain fillings of a
schema's don't-care coordinates; **patches are never sumandos**.

Every hypothesis is selected by actual serialized archive length. Search heuristics
may prioritise proposals but must not decide the winning model using node count,
Python character count, a free permutation, a free dictionary, or a fitted score.

The literal archive is always available. On every completed inference:

`archive_bits(HID-v1(x)) <= archive_bits(literal(x))`.

Break equal-length ties in favour of literal; otherwise use lexicographic archive
bytes. A compact language can still lose on tiny examples because of overhead.
**Do not require HID-v1 to compress A64 or A72 below their raw-bit lengths.**

### 1.3 What constitutes generalisation

The search sees only the bit sequence and a frozen, data-independent SearchConfig.
It must never receive a generator name, seed, true period, schema mask, macro
boundary, noise mask, or ground-truth expression. Such information is available
only to corpus generation and subsequent evaluation.

Evidence is evaluated on disjoint seeds, unseen parameter ranges, larger sizes,
and designated held-out families, with the entire implementation frozen before
those outputs are scored. The benchmark annex defines the splits and endpoints.
Claims remain restricted to that distribution and resource budget.

## 2. Repository boundaries and ownership

The working tree already contains substantial uncommitted work. Before editing,
save `git status --porcelain=v1`, HEAD, and hashes of every existing file you will
touch under `results/hierarchy_v1/development/provenance/`. Save readable diffs for
the touched tracked files and copies of touched untracked files. Do not run
`git reset`, `git clean`, stash other work, or replace files from HEAD. A worktree
created from HEAD alone would omit the current notebook and owner changes; do not
use one unless all required working-tree inputs are explicitly transferred.

Create this package under `index-deconvolution/hierarchy/`:

| Module | Single responsibility |
|---|---|
| `model.py` | Immutable validated rule/DAG types; no data generation |
| `wire.py` | Canonical serialization, integer/bit packing, envelope construction |
| `decode.py` | Independent wire parser and bounded decoder, standard library only |
| `candidates.py` | Reusable deterministic proposal generators |
| `infer.py` | Bounded search, ablations, literal fallback, trace |
| `baselines.py` | Baseline encoders and deterministic baseline selection |
| `corpus.py` | Synthetic generators, split generation, manifests; never imported by inference |
| `benchmark.py` | Process isolation, resource accounting, resumable experiment rows |
| `diagnostics.py` | BDM experiments through the shared owner |
| `report.py` | Tables, plots, uncertainty, claim ledger from saved rows |
| `cli.py` | CLI orchestration only |
| `tests/` | Tests, independent tiny interpreter, tiny bounded oracle |
| `README.md`, `SEARCH_SPEC.md`, `TESTS.md` | Usage, frozen algorithm details, test inventory |

Use additional small modules if they separate an actual responsibility; document
them in the owner map. Do not duplicate encoders or scoring logic in notebooks.
Use the existing environment and standard library for codec/search/generation.
Existing numpy/matplotlib/pytest/pybdm may serve diagnostics, reporting, and tests.
No heavyweight framework or network dependency is needed.

Permitted shared edits, narrowly scoped:

- `src/description_lengths.py`: validate the 1-D interface; add the boundary mode
  below and `encoded_bit_length(payload: bytes) -> int`, returning exactly
  `8 * len(payload)` after strict bytes validation. This is the public archive-size
  measurement owner; it must not import the hierarchy package.
- `tests/analysis/test_description_lengths_values.py`: meaningful regression tests
  for those changes, retaining all current tests.
- `GOVERNANCE/CORE.md` and `GOVERNANCE/DESCRIPTION_LENGTHS.md`: register the new
  serializer/decoder ownership and archive-bit measurement as a distinct quantity.
  Existing variants A–E remain unchanged.
- Notebook 15's builder and generated notebook; notebook README.
- Bitacora 32: append dated errata and mark the broken quotation incomplete; do not
  silently rewrite historical measured tables or invent the missing quotation.
- New notebook 16 and builder, reports, figures, and stage-specific results.

Do not edit the exact deconvolution owner; import its existing schema-cover
implementation when needed. Its greedy cover is **not** a certified minimum.
Resolve its directory relative to this repository, following the existing shared
owner's import pattern; assert the loaded module/function source path is
`index-deconvolution/src/deconvolution.py`. The documented CLI PYTHONPATH does not
itself include that legacy source directory. Do not accidentally import a sibling
repository's same-named module through a local .pth file.
Do not alter other project notebooks, papers, financial data, vendors, or core
Boolean semantics. Preserve audit 33 and its JSON as historical evidence; rerun
its script with `--output` to a new stage-specific path.

New hierarchy tests live in the package and have an explicit test command/inventory.
If you add any file under root `tests/`, declare it in the root test manifest;
do not change the global manifest policy or pytest discovery to make tests pass.

## 3. Phase H0 — repair the foundation

Implement the corrections listed in bitacora 33 §3 in notebook 15's **builder**,
then regenerate and execute the notebook. Include A24/AX64/AXM64/P1/P2/P3 as executed
cells with full length, scored length, dropped length, and block multiplicities.
Keep original drop-policy measurements explicitly labelled historical diagnostics.
Add a full-coverage comparison. Distinguish character counts from UTF-8 payload
bits and actual new archive bits. Use A64/A72/A24 consistently.

The corrected discussion must include: raw minimum BDM selects b=3 over 2..12 on
A72; P3 has 15 distinct 12-blocks out of 16; the finite slope is not an unbounded
law; invariance constants are not CTM error bars; and known BDM alternatives exist.
Do not describe the 17-character program for A64 as though it outputs A72.

Harden `ctm_1d`/`bdm_1d` without changing valid historical scores:

- Accept binary strings or one-dimensional sequences/arrays of integer/bool 0/1.
  Validate before conversion. Reject float data (even 0.0/1.0), nonbinary values,
  ragged/multidimensional data, empty input, and scalar input with clear ValueError.
- `block` and explicit `shift` must be integral, excluding bool; `1 <= block <= 12`
  and `1 <= shift <= block`. Reject a step that leaves internal gaps.
- Validate `remainder` against `raise`, `drop`, `recursive`; unknown policies fail.
- Preserve existing non-overlap `raise` and `drop` scores. For n < block, these
  modes raise a clear error rather than scoring zero blocks.
- `recursive` is allowed only with `shift=None`; delegate to pybdm's
  `PartitionRecursive` with `min_length=1` so no final bit disappears. For n < b,
  this scores the shorter available block. Verify partition coverage explicitly.
- Sliding `raise` requires `(n-block) % shift == 0`. Sliding `drop` reports its
  actual covered prefix in diagnostics. For all n >= b and shift=1 there is full
  coverage. Reject `recursive` with a sliding shift rather than guessing semantics.

Before rejecting previously accepted values, inspect actual callers. If a caller
relies on numeric 0.0/1.0, convert explicitly at that caller only if it lies within
the authorised stage; otherwise report the compatibility issue, do not change
unrelated consumers. A historical accidental cast of 0.5 to 0 must never survive.

H0 gate: targeted owner tests pass, notebook executes, old valid scores agree to
floating-point tolerance, and errata point to executed evidence.

## 4. Phase H1 — implement the language and independent decoder

The wire annex is normative. Implement it before inference. Decoder inputs are
only archive bytes and explicit resource limits. It must not read the original
string, JSON sidecars, source code, a generated dictionary, or a candidate object.
Do not use pickle, eval, executable embedded Python, or benchmark-specific cases.

The decoder may share opcode constants with the serializer, but not serializer
parsing code or the encoder's graph evaluator. Run it in a separate process with
only the decoder source, an optional shared constants module, and archive available
(plus the standard library). An independent test interpreter
must evaluate hand-written semantic rules separately from both wire paths.

Required public interfaces (dataclasses may hold the stated fields):

```python
encode_literal(bits: str) -> bytes
serialize_model(model: Model, n_bits: int) -> bytes
decode_archive(data: bytes, *, max_output_bits: int = 16777216,
               max_rules: int = 1000000) -> str
infer(bits: str, config: SearchConfig) -> InferenceResult
encode_baseline(bits: str, method: str) -> bytes
```

`InferenceResult` contains archive bytes, selected mode/model, archive_bits,
candidate counts, search-stop reason, deterministic work counters, and a trace of
accepted improvements. Runtime/memory are benchmark fields, not tie breakers.
The codec supports empty input through literal mode; inferred rules are nonempty.
Library bit-string inputs are strictly `str` containing only 0/1; invalid types
raise TypeError, invalid characters raise ValueError. This new API is deliberately
narrower than the existing CTM/BDM sequence/array interface.

H1 gate: exhaustive round trips of all 2^0 + ... + 2^10 = 2047 binary strings
through the literal path, hand-derived fixtures for every opcode, malformed input
tests, independent decoding, and exact byte accounting. Compression advantage is
not an H1 requirement.

## 5. Phase H2 — deterministic bounded discovery

### 5.1 Minimum search implementation

Implement the following candidate sources. They receive only their local bit
substring and immutable config. Every proposed description must be verified by
decoding/evaluation against that substring before it can enter a winning archive.

1. **Literal**: always available.
2. **Exact period**: use a linear string-period algorithm (prefix/Z function) to
   find the shortest finite-prefix period. Build repeat plus an explicit tail;
   offer it whenever at least two complete copies exist. No period oracle.
3. **AP supports**: for each foreground bit, get its positions. Greedily partition
   them into maximal consecutive constant-gap runs, consuming from left to right;
   a final singleton has step 1. Encode the resulting union if it has <=256 APs.
   Also propose each of the eight longest such runs individually with a patch for
   the remaining errors, subject to the correction cap below.
4. **Schema supports**: for both foreground bits on substrings of length <=256,
   pad the membership table to a power of two with each of 0 and 1 in turn, call
   the existing cover owner, translate clauses to masks/values, and verify on the
   unpadded domain. Tail filling is only a proposal device; the archive encodes
   the actual clipped domain. Discard candidates with >64 clauses. Report the
   coordinate lifting and confirm that don't-cares on connected inputs survive.
5. **Dictionary grammar**: build the deterministic pair-substitution grammar
   specified for the baseline, then translate its productions into literal and
   ordered concat DAG nodes. Charge every production/reference in HID's own format.
6. **Segmentation candidates**: exact dyadic splits down to length 32, plus fixed
   widths 8,16,32,64,128,256 at phases 0..min(7,width-1). Prefix and suffix fragments
   remain in the model. Repeated chunks may share a rule. Candidate production
   must cap total work; do not materialise all possible substrings of x.
7. **Relations and patches**: for at most 64 distinct literal/chunk representatives
   per proposal graph, ordered by decreasing reuse then lexical bits, look for exact
   complement, reversal, and rotations with r in {1,2,4,8} modulo length. Encode a
   transform only when it reproduces the target. For noisy periodic candidates,
   test periods 1..32 and 64,128,256 up to floor(n/2), repeating the observed first
   period; propose exact XOR patches for the three candidates with fewest errors
   (period breaks ties), only if errors <= min(64, floor(n/16)). Always charge base,
   transform, and correction positions. Insertions/deletions have no special opcode.

For segmentation, combine local choices by complete DAG serialization rather than
adding isolated leaf scores; shared definitions and reference widths affect cost.
At least one candidate must replace **all occurrences** of the same repeated
substructure together. This is the required joint change; a purely single-leaf
greedy algorithm is insufficient.

Start the search from literal, exact-period, global AP/schema candidates, grammar,
and segmented proposals. Normalize reachability and deterministic rule numbering
before every final cost comparison. Keep a beam of the eight shortest distinct
archives for four rewrite rounds. Per graph, examine at most 16 rewrite sites,
ordered by decreasing expanded substring length then rule ID. Intern identical
structural rules after rewrites, except where the flat ablation forbids sharing.
Do not intern merely by expanded output when that
would discard a different representation before its complete cost is evaluated.

Default deterministic limits: at most 512 fully serialized unique graph candidates
per input, 4096 reachable rules, 256 AP entries per node, 64 schema clauses per
node, maximum inferred DAG depth 64. A candidate exceeding a limit is skipped and
counted; a literal fallback is still returned. Use stable sorted iteration, explicit
tie breaking, and integer arithmetic. SearchConfig and counters record every cap.

These are initial development defaults. You may optimise algorithms and change
numeric caps **using only development data**, recording rationale and before/after
measurements in SEARCH_SPEC.md. Freeze the final values before confirmation. The
required candidate families and accounting rules cannot be silently removed.
SEARCH_SPEC.md must also fix proposal enumeration order, site traversal, beam
deduplication, and when each counter increments; these affect results at a cap.
Failure to fit the resource budget is a reportable result, not permission to insert
a shortcut keyed to a known family.

### 5.2 Ablations

Run five separately named configurations with the same frozen deterministic
budget. These are restricted searches, not post-hoc removal of bytes:

- `no_schema`: disable schema nodes/proposals.
- `no_arithmetic`: disable AP nodes/proposals; ordinary repetition remains.
- `no_transform`: disable XFORM nodes/proposals; patches remain.
- `flat`: allow a primitive root, one repeat of a primitive, or a root concat of
  primitives, optionally one patch of that entire result. Primitives are literal,
  AP, or schema. No nested concat/repeat, transform, or cross-child sharing.
- `fixed8`: constrain segmentation/grammar symbol boundaries to multiples of 8
  from position zero, with one explicit trailing fragment. Treat each full byte
  as an indivisible initial grammar symbol. Global primitive/AP/schema/period
  proposals remain, so this specifically tests adaptive segmentation.

The literal is included in every arm. An ablation may outperform the full bounded
search; record that as a search interaction, not a failed round-trip or a result
to suppress. Report actual work as well as the common cap.

### 5.3 Tiny oracle with a precisely limited claim

Implement an independent exhaustive enumerator for n<=8 over **expression trees**
of <=3 nodes using literal, binary concat, and repeat(count>=2). All literals are
nonempty, each intermediate expansion length <=n, and concat/repeat children are
earlier nodes. No sharing, AP, schema, transform, or patch is admitted in this
oracle. Include the outer raw mode. Enumerate all legal parameters within these
bounds, serialize complete candidate archives, and find the minimum per target.

Compare a dedicated restricted-search configuration to this oracle for every
target n<=8; record its gap and whether it actually exhausts that finite language.
Compare the full search descriptively, allowing it to beat the restricted oracle.
Never call the oracle a minimum over all HID DAGs or a minimum of K. The purpose
is to validate bounded search accounting and distinguish search failures from
language limitations; the small oracle does not certify large-input optimality.

Raw mode dominates many tiny examples, so a zero raw-inclusive gap alone is weak
evidence. Also enumerate all trees with <=3 nodes, literal leaves of length 1..4,
and output length <=64. Enumerate programs, not all 2^64 targets; build the exact
minimum map for the outputs those programs generate. Report **grammar-only** and
raw-inclusive minima separately, mark unrepresented targets as such, and include
nontrivial cases such as 64 identical bits (a repeat grammar can beat its raw
envelope). Test the restricted search against these generated targets as well.

H2 gate: inference is deterministic, automatic, metadata-blind, respects caps,
round-trips every returned archive, and never exceeds the literal archive size.

## 6. Phase H3 — baselines and pilot

Implement the wire-annex baseline codecs and independently decode their archives.
The fixed comparator portfolio is raw, RLE, gaps, period, Bernoulli-enumerative,
first-order-context-enumerative, zlib, lzma, and deterministic pair grammar.
Record the exact algorithm variant and library version. Do not call the pair
baseline SEQUITUR; it is the specified RePair-style variant, without a claim of
bit-identical compatibility with another implementation.

The baseline selector sends the chosen codec ID in the common envelope, so its
per-input minimum is itself a legitimate decodable code. Include this **strong
portfolio comparator**, every constituent, and raw packed size in reports. The
proposed arm consists of HID grammar or raw mode; do not quietly replace it with
the baseline portfolio and attribute that portfolio's gains to the hierarchy.

Run the development split only. Fix implementation bugs, identify performance
bottlenecks, and document search changes. Check the full schema bridge, polarity,
ragged boundaries, and high-level reuse on hand-written examples. Expose a rule
graph and a per-field byte breakdown for each accepted illustrative result.

The pilot is exploratory. Do not present its selected examples or fitted resource
settings as confirmatory evidence. Keep all pilot attempts in the development log.

## 7. Phase H4 — freeze, confirmation, and transfer

Follow the benchmark annex exactly. Write a freeze manifest **before generating
or scoring confirmation/transfer inputs**. It contains the protocol/annex hashes,
source hashes, SearchConfig, baseline parameters, Python/dependency versions,
generator specification, seed schedule, expected case counts, hardware, and
analysis plan. Do not hash only HEAD: important inputs are currently uncommitted.

Validate the manifest at run start and resume. A changed hashed scientific input
invalidates that confirmatory run. A post-freeze correctness fix requires a new
run ID and freeze, with the old run retained as invalidated and the full affected
benchmark rerun. A scientific change after seeing held-out results requires new
reserved seeds and explicit disclosure that the earlier families informed design;
do not relabel an explored test set as pristine. Report such a change for supervisor
review rather than claim the original confirmatory gate passed.

Use isolated worker processes, a watchdog, per-case atomic outputs, deterministic
case IDs, and resume only from records with matching hashes. Timeouts and errors
are rows, never missing files silently excluded from analysis. The benchmark
annex specifies the comparable fallback and how an incomplete study is labelled.

## 8. Phase H5 — evidence, notebook, and handoff

Generate reports exclusively from saved result rows. Create:

```text
index-deconvolution/results/hierarchy_v1/<run_id>/
  freeze.json
  corpus_manifest.jsonl
  cases.jsonl
  diagnostics.json
  summary.json
  claim_ledger.json
  verification.json
  logs/
  archives/                 # or a manifest to retained local archives
index-deconvolution/bitacora/34_hierarchy_v1_results.md
index-deconvolution/notebooks/build_16.py
index-deconvolution/notebooks/16_hierarchical_index_generalization.ipynb
index-deconvolution/hierarchy/HANDOFF.md
```

Do not overwrite another task's bitacora 34; if occupied, use the next available
number and record the path. Artefacts over 10 MB must remain external to history
with hashes and a regeneration command, according to repository policy. No cloud
upload is requested. Development, invalidated, confirmation, and transfer outputs
must be distinguishable by paths and status, not just prose.

The notebook must explain actual encoding/decoding, the period/schema distinction,
one learned graph, one incompressible or unsuccessful case, complete benchmark
tables, ablations, uncertainty, and resource limitations. Include actual archive
sizes alongside raw-bit length and raw-envelope length; never plot BDM as stored
bytes. Figures and numbers must be generated, not manually transcribed.

The claim ledger contains one row per headline claim with: claim text, status
(`supported`, `not_supported`, `inconclusive`, `out_of_scope`), exact evidence
paths/row IDs, metric, uncertainty, domain, and caveat. No “success” based merely
on tests passing. Follow the acceptance annex for the final developer report.

## 9. Commands the developer must provide

Implement these commands; they are a required CLI contract. Run from the repository
root with `PYTHONPATH=index-deconvolution:src` and the documented Python interpreter:

```sh
python -m hierarchy.cli selfcheck
python -m hierarchy.cli pilot --run-id dev-v1
python -m hierarchy.cli freeze --run-id confirm-v1
python -m hierarchy.cli benchmark --run-id confirm-v1 --split confirmation --resume
python -m hierarchy.cli benchmark --run-id confirm-v1 --split transfer --resume
python -m hierarchy.cli diagnostics --run-id confirm-v1
python -m hierarchy.cli report --run-id confirm-v1
python -m hierarchy.cli verify --run-id confirm-v1
python -m pytest index-deconvolution/hierarchy/tests tests/analysis/test_description_lengths_values.py -q
```

Also provide `encode --input <01-text-file> --output <archive>` and
`decode --input <archive> --output <01-text-file>`. Text CLI input may strip one
terminal newline only; otherwise reject whitespace/nonbinary input. The Python
API accepts exact bit strings without stripping. Decoder output is exact ASCII
0/1 bytes, with no appended newline. User data must not enter filenames or shell
commands unsafely.

`verify` exits nonzero for engineering invalidity, corrupted/missing required
artefacts, or an incomplete declared split. It exits zero for a complete, valid
study with a negative scientific result. Its JSON reports these dimensions
separately. Never make tests assert a favourable benchmark effect.

## 10. Developer discretion and escalation

Proceed independently on internal data structures, performance optimisations,
test organisation, and plot layout consistent with this specification. Record
meaningful decisions in SEARCH_SPEC.md. Keep public contracts and scientific
semantics stable. Do not ask the user to choose opcodes, thresholds, or defaults
already fixed here.

If a genuine contradiction prevents a correct implementation, finish independent
work, record the exact contradiction and options in HANDOFF.md, and identify the
smallest decision required. Do not silently change the hypothesis or wire format.
If resource/dependency restrictions prevent the full study, deliver all completed
work, resumable commands, and an explicitly incomplete status. Do not call a smoke
test a completed confirmatory benchmark.

The user will bring HANDOFF.md and the result location back to the supervising
session. The developer must not imply that supervision or independent acceptance
has already occurred.
