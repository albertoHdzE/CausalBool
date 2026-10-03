# HID-v1 search specification (frozen with run `confirm-v1-r1`)

This file fixes everything about the search that can change a result at a cap,
and records every development-time decision with its evidence. It describes
`hierarchy/infer.py` and `hierarchy/candidates.py` as frozen; the source hashes
in `results/hierarchy_v1/confirm-v1-r1/freeze.json` are authoritative.

**Correctness amendment (2026-10-02).** Run `confirm-v1` was frozen with an earlier
copy of this file (sha256 `724404080301af9a…`, preserved in
`results/hierarchy_v1_supervision/confirm-v1/source_snapshot_confirm-v1.tar`). The
supervisor review (`bitacora/35_hierarchy_v1_supervisor_review.md`, R1–R5) led to
correctness fixes only: no SearchConfig value, proposal source, enumeration order,
scoring rule or wire byte changed. The one search-side change is §1/§3: an
expansion mismatch now raises instead of being counted. §7 and §8 were rewritten
for accuracy (R3, R4). The amendment record is
`results/hierarchy_v1/AMENDMENT_confirm-v1-r1.md`. Development
evidence lives under `results/hierarchy_v1/development/` (calibration scripts,
their JSON outputs, pilot `dev-v1`, pipeline smoke run `dev-smoke`). No
confirmation or transfer string was generated or scored before the freeze.

**Status of every result: best found under budget.** Nothing here certifies a
minimum. The schema cover delegated to `index-deconvolution/src/deconvolution.py`
(`minimal_dnf`) is Quine–McCluskey prime generation (worst case exponential in the
number of address coordinates) followed by a **greedy** set cover.

## 1. Inputs and outputs

`infer(bits: str, config: SearchConfig) -> InferenceResult`. The function sees the
bit string and the frozen, data-independent config only. It never receives a file
name, case id, family, seed, period, mask, boundary or noise mask; the benchmark
worker reads the string from stdin (`python -S -m hierarchy.benchmark --worker`).
The returned archive is decoded by the independent decoder before return; a
mismatch raises (engineering failure), never a silent fallback. A proposal of the
right length whose expansion differs from the input raises
`CandidateExpansionMismatch` inside `_Search.consider` (an internal semantic
failure: the worker exits non-zero and its row is `error`, never `ok`, a timeout, a
raw fallback or a rejected candidate). In `confirm-v1` such a proposal was counted
as `rejected_verify` and skipped; every retained row of that run has
`rejected_verify = 0`, so the change cannot alter any stored archive.

## 2. Configurations

`SearchConfig` defaults (protocol defaults unless marked *changed*):

| field | value | note |
|---|---|---|
| max_candidates | 512 | unique serialized archives per input |
| max_rules | 4096 | reachable records (counted with or without sharing per arm) |
| max_ap | 256 | AP entries per node |
| max_schema_clauses | 64 | per node |
| max_depth | 64 | inferred DAG depth |
| beam_width / rewrite_rounds / max_sites | 8 / 4 / 16 | |
| site_proposals | 1 | best local proposal per site (by local cost), see §5 |
| schema_max_len | 256 | substrings eligible for the schema source |
| schema_table_budget | **4096** (*changed* from an initial 65536) | padded table entries per input, §7 |
| max_relation_reps / max_relation_candidates | 64 / 8 | |
| patch cap | min(64, floor(L/16)) for a local substring of length L | |
| ap_single_runs / noisy_keep | 8 / 3 | |
| dyadic_min, fixed_widths, max_phases | 32; 8,16,32,64,128,256; 8 | |
| grammar_literal_thresholds | 0, 16, 64 | |
| split_min | 64 | |
| work_cap | **120,000,000** units (*changed* from an initial 60,000,000) | §7 |

Arms (`ABLATIONS`): `full`; `no_schema` (schema off); `no_arithmetic` (AP nodes and
proposals off; REPEAT remains); `no_transform` (XFORM off; patches remain); `flat`
(root is a primitive, a REPEAT of a primitive, or a CONCAT of primitives, optionally
under one PATCH; primitives are LITERAL, AP_UNION, SCHEMA_UNION; serialized
**without sharing**, i.e. one record per occurrence; grammar and transforms off;
segment descriptions restricted to primitives; no REPEAT-collapse of runs);
`fixed8` (segmentation at phase 0 only, so every boundary is a multiple of 8 from
position 0 with one trailing fragment; grammar terminals are whole bytes plus the
fragment; the local `split` proposal is off; global literal/period/AP/schema/noisy
proposals unchanged). `restricted_oracle` admits LITERAL, binary CONCAT and REPEAT,
at most 3 records, no sharing; proposals are the literal, REPEAT(LITERAL) at the
exact primitive period when it divides n, and every two-literal split.

The literal (raw) archive is outside the search and always a candidate.

## 3. Proposal enumeration order (fixed)

1. `local_props(x)` on the whole input, in this order, each verified:
   literal; exact period (prefix function, offered when floor(n/p) >= 2:
   REPEAT(LIT(w), k) plus a trailing LITERAL when p does not divide n); for
   foreground '0' then '1': AP runs (greedy maximal consecutive constant-gap runs,
   final singleton step 1), AP cover (§4), the eight longest runs each with a patch
   of the remaining errors when 0 < errors <= cap; schema (if L <= 256 and budget
   allows) for foreground '0','1' x pad 0,1; noisy periods (periods 1..32, 64, 128,
   256 up to floor(L/2), base repeats the observed first period, the three with
   fewest errors, ties by smaller period, patched when 0 < errors <= cap); split
   (§5). Duplicates by node identity are dropped, first label kept.
2. Grammar: the W7 pair grammar on the bits (or on byte symbols in `fixed8`),
   translated to LITERAL/CONCAT nodes, each production whose expansion is <= T bits
   literalised, for T = 0, 16, 64; consecutive identical start symbols become REPEAT.
3. Segmentations: dyadic widths 32, 64, ... < n (phase 0), then fixed widths
   8..256 ascending, phases 0..min(7, w-1) ascending (phase 0 only in `fixed8`); a
   nonzero phase keeps its prefix fragment, the last chunk keeps the suffix. For
   each segmentation: (a) chunks described by `best_local` (cheapest local proposal
   without split; ties by label), identical chunks shared through interning,
   consecutive identical chunks collapsed into REPEAT; (b) except in `flat`, a
   chunk-level pair grammar over the chunk-description ids (offered only if it
   creates a rule).
4. Rewrite rounds (§5).

Counters: `proposed` increments for every root offered to `consider`;
`rejected_depth`, `rejected_structure` (arm language), `rejected_rules` before
serialization; `skipped_candidate_cap` and stop when `serialized_unique` has reached
`max_candidates`; otherwise the archive is serialized, `duplicate_archive` if its
bytes were already seen, else `serialized_unique` increments, the expansion is
verified (a mismatch raises `CandidateExpansionMismatch`, §1; the
`rejected_verify` counter is kept for row compatibility and is 0 in every completed
search) and the archive enters the pool. `local_prop_calls`, `schema_calls`, `schema_table_entries`,
`schema_budget_skips`, `schema_clause_cap`, `ap_entry_cap`, `patch_cap`,
`rewrite_sites`, `relation_found`, `rounds_completed` count what their names say.
`work_units`: L per local-proposal call, 2L for the period scan, 8L per AP cover,
64 x table size per schema call, 36L for the noisy-period scan, n per
segmentation, 16n per grammar run, 20L per relation representative, and the byte
length of every serialized candidate. Exceeding `work_cap` stops the search
(`stop_reason = work_cap`) and returns the best archive so far or the literal.

## 4. Additional proposal source: AP cover

Not in the protocol's minimum list; added during development because the
required greedy run partition cannot represent interleaved progressions (a union
of two APs yields alternating short runs). Candidate steps: the 8 most frequent
differences p[i+j] - p[i], 1 <= j <= 4 (ties: smaller step); for each step and
residue, maximal runs of consecutive members with >= 3 elements; runs chosen by
(-count, start, step) while they add >= 3 uncovered positions; the remainder is
partitioned by the run rule. Generic (no family knowledge); development effect:
F04 strings are represented by two triples instead of hundreds.

## 5. Rewrites, sites, beam

Beam = the 8 shortest distinct archives in the pool (ties: archive bytes). Each
round, every beam graph not yet expanded is rewritten: sites are all distinct
non-root nodes in deterministic postorder, sorted by decreasing expansion length
then postorder id, first 16. For each site its expansion receives `local_props`
(including `split`: CONCAT of `best_local` of the two halves at the largest power of
two below L, when L >= 64, not in flat/fixed8/restricted); proposals other than the
site itself are ranked by local cost (payload bytes of the subgraph alone; a
heuristic only) and the first `site_proposals` replace the site **everywhere it
occurs** (`NodeFactory.rebuild`: interned nodes make all occurrences one object —
the protocol's joint change). Then relations (not in flat/restricted/no_transform):
representatives are literal nodes plus non-literal root-concat children, ordered by
decreasing reference count then expansion, first 64; for each ordered pair a target
equal to `xform(source, flags, r)` for flags 0..3 and r in {0,1,2,4,8} mod L (no
identity, no duplicate rotation) becomes XFORM(source); the first 8 relations are
offered singly and all non-conflicting ones jointly. A round that leaves the beam
unchanged stops the search (`converged`).

Interning is structural (opcode, fields, child identities), never by expanded
output, so two descriptions of one substring both reach complete serialization.
Final selection: shortest archive; the literal wins ties; HID ties by archive bytes.

## 6. Determinism

Integer arithmetic only; no set of strings is iterated (dicts preserve insertion
order; sets of integers and of integer tuples iterate deterministically); the
cover owner's sets hold integer tuples. Tested: identical archive bytes, counters
and traces in fresh processes under PYTHONHASHSEED 0 and 12345. Workers run with
`python -S` and `PYTHONHASHSEED=0`. Wall time and RSS are recorded, never used.

## 7. Development measurements behind the two changed numbers

All on development data only (`results/hierarchy_v1/development/calibration/`).

* **schema_table_budget 65536 -> 4096.** Profiling a period-13 string of 1027 bits:
  7.6 s of 8.1 s were inside the owner's greedy cover (672 calls). Over the 128
  development strings the full search produced **54,040 total archive bits under
  budgets 65536, 16384 and 4096 alike**, at 166.7 s, 57.9 s and 22.4 s of summed
  encode time (max per string 5.61 s, 2.60 s, 0.54 s). Schema disabled: 54,440 bits.
  (`calib_1790951609.json`)
* **work_cap 60M -> 120M.** Development families at 65,536 bits (resource probe
  split `development_resource`, development parameter ranges): F06 improved from
  11,992 to 11,720 bits; F02, F05 unchanged; F07 (fair IID) took 9.0 s at 120M
  against 13.4 s at 240M. Peak RSS at 65,536 bits: <= 126 MB. (`workcap_probe.txt`,
  `devcmp_resource_*.json`)

**Design deviation (disclosed for R4).** The declared development size grid is
256/1024 bits. The work-cap probes above were an additional development experiment
at **65,536 bits**, outside that grid, and the setting was chosen partly from an
encoded length (F06 11,992 -> 11,720 bits). What this does and does not touch:

| object | used before the freeze? |
|---|---|
| reserved transfer seeds (replicates 2000-2003) and their strings | no |
| held-out families F03, F10, F11, F12 | no |
| confirmation strings (replicates 1000-1019) | no |
| the 65,536-bit **length** (development families F02, F05, F06, F07, development parameter ranges) | **yes** |

So the transfer split keeps genuine held-out seeds and families, but its largest
length is not an unseen length. Transfer remains descriptive.

## 8. Development observations (exploratory, not evidence)

Pilot `dev-v1` (128 strings, all arms, two workers): 2,048/2,048 archives decode;
no errors or timeouts. HID-full beat the portfolio only on F06 (noisy period).
Every HID result is the **best archive found under the frozen budget**; no
large-instance optimum in the HID language has been computed, so a loss cannot be
attributed to the language alone. Four separable contributors, none established as
the dominant one:

* **wire overhead (representational):** on periodic inputs the cheapest *known*
  HID description (REPEAT + trailing LITERAL + CONCAT) costs about 13 bytes more than
  the period codec's single field; every reference costs at least one byte and no
  reference stream is entropy-coded, so i.i.d. token streams (F02 odd replicates)
  and the biased-IID/Markov controls have no compact HID form;
* **proposal coverage:** segmentation proposals use fixed dyadic and fixed-width
  grids (no width 12, 13, 17 or 31; no region-boundary discovery), so a legal
  description aligned to other boundaries is never proposed;
* **caps:** candidate cap 512, patch cap min(64, L/16), schema budget 4,096 table
  entries and the 120 M work cap end some searches before their proposals are
  exhausted (in `confirm-v1` 44 of 1,440 confirmation full searches stopped at the
  candidate cap, 40 of them F12 at 4,096 bits);
* **search quality:** the beam, site and relation rules rank by local heuristics
  and can miss a shorter legal graph that the language contains.

The supervisor's post-hoc witness (`bitacora/35`, §4) shows that the fourth and
second contributors are real on at least one input: for
`transfer-F12-65536-2000-base` a legal archive in the **unchanged** language has
22,480 bits against 28,528 found by the frozen search (portfolio 23,240). That
witness used the generator's construction boundaries, i.e. evaluation-only
metadata; it is outside every benchmark result, never an inference input or tuning
target, and not an optimality certificate. Whether representation or search
dominates over the population is not established. Any change to the wire language
(for example an entropy-coded leaf or reference stream) is a new language version
with its own specification; it cannot be added under W3.

No operator was added in response. Deliberate interruption after 8 cases, resume,
and a fresh replay of 12 cases gave identical deterministic fields
(`dev-v1/resume_check.json`). Tiny oracle (`dev-v1/oracle.json`): the restricted
search equals the language minimum on all 511 targets with n <= 8 and all 960
generated targets (literal leaves 1..4, output <= 64); it does **not** exhaust the
language (it never proposes REPEAT of REPEAT or of a non-primitive root).

## 9. Decisions on the corpus (fixed before confirmation)

F01 and F06 rotate the primitive word to the **right** by r. F05 maps pattern
character k to the k-th sampled coordinate; patterns `01*`, `10*`, `*10`.
F02 even replicates use the fixed token sequence, odd ones draw tokens from the
structure stream. Development resource probes use split names starting with
`development`, which select development parameter ranges.

## 10. Ordering note

Notebook 15's "actual archive bits" column needs the H1 codec, so notebook 15 was
regenerated after H1/H2 were implemented; the owner hardening of H0 was completed
and tested first.
